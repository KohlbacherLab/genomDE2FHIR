"""matchbox $validate / $transform and HAPI transaction client, with a structured issue classifier.

Verdict classes per issue (severity error/fatal only; warnings are reported, never fail):
  content      - a real conformance error in our output                      -> FAIL
  unchecked    - a binding to a terminology the configured tx server cannot
                 serve (German BfArM systems, MedDRA, licensed editions)      -> INCONCLUSIVE
  waived       - a known defect of the ballot packages, listed in WAIVERS     -> reported, not failing
  source       - an unknown code that occurs verbatim in the input file (data quality of the submission)
                                                                                -> DATA-QUALITY
  cascade      - a reference/slice failure caused by errors of the referenced resource (counted there)
Definitive "code is not in the code system" messages are `content`, unless the code comes from the input.
Each resource is validated alone against its declared profiles (own issues); a whole-Bundle pass adds only the
reference-resolution issues, which become `cascade` when the referenced resources have own errors.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

MESSAGE_ID_EXT = "http://hl7.org/fhir/StructureDefinition/operationoutcome-message-id"
# code systems tx.fhir.org cannot validate (licensed / national); errors that only say "cannot check" -> unchecked
UNAVAILABLE_SYSTEMS = (
    "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "http://fhir.de/CodeSystem/bfarm/ops",
    "http://fhir.de/CodeSystem/bfarm/atc", "http://fhir.de/CodeSystem/bfarm/alpha-id",
    "http://terminology.hl7.org/CodeSystem/icd-o-3", "urn:oid:2.16.840.1.113883.6.43.1",
    "http://www.orpha.net", "http://www.meddra.org", "http://fhir.de/CodeSystem/ifa/pzn",
    "http://human-phenotype-ontology.org", "http://www.genenames.org", "http://varnomen.hgvs.org",
    "http://www.sequenceontology.org", "http://www.ensembl.org", "http://www.ncbi.nlm.nih.gov/refseq",
    "https://www.uicc.org/resources/tnm", "https://cancer.sanger.ac.uk/cosmic",
)
UNCHECKED_PATTERNS = re.compile(
    r"(could not be found, so the code cannot be validated|cannot be validated|unable to check|"
    r"no versions of this code system are known|not known to the terminology server|"
    r"unknown code ?system|unable to (validate|expand)|terminology service|error expanding valueset|"
    r"a definition for codesystem .* could not be found|valueset .* not found|"
    r"cannot validate code|was not found by the terminology server|timed out|"
    r"version '?(2014|2019)'? could not be found|ICD-O-3 (Morphologie|Topographie))", re.I)
# terminology the server cannot check for this version / at all, recognised before the source-data rule
TERMINOLOGY_LIMIT = re.compile(r"(ICD-O-3 (Morphologie|Topographie)|icd-o-3.*version|version '?(2014|2019)'? could not be found|"
                               r"timed out|HGVS validation request)", re.I)
REFERENCE_ARTEFACT = re.compile(r"(a matching slice is required|Unable to find a profile match for|"
                                r"Unable to resolve resource with reference 'urn:uuid|"
                                r"Unable to find a match for profile .* among choices)", re.I)
UNKNOWN_CODE = re.compile(r"Unknown code ['\"]([^'\"]+)['\"]", re.I)
VS_CODES = re.compile(r"\(codes? = [^#]*#(.*)\)\s*$")
DEFINITIVE_INVALID = re.compile(r"(unknown code ['\"]|is not a valid code|not found in (the )?code ?system|"
                                r"code .* is not in the code ?system)", re.I)

# known ballot-package defects (docs/2027-BALLOT-DIFF.md); each: profile substring, expression regex, text regex
WAIVERS = [
    {"id": "mtb-therapieplan-servicerequest-slices", "profile": "mii-pr-mtb-therapieplan",
     "expression": r"CarePlan\.activity", "text": r"(ServiceRequest|does not match any of the allowed types|profile)"},
    {"id": "molgen-variante-value-closed-snapshot", "profile": "variante",
     "expression": r"Observation\.value", "text": r"(closed|not allowed|slic)"},
    {"id": "biobank-lagerprozess-extension-1..*", "profile": "mii-pr-biobank-specimen",
     "expression": r"Specimen\.processing", "text": r"extension.*minimum required"},
    {"id": "mtb-qc-extension-context", "profile": "genomic-study-analysis",
     "expression": r"Procedure", "text": r"mii-ex-mtb-genomic-study-analysis-qc.*not allowed to be used at this point"},
    {"id": "mtb-rna-seq-component-slices-without-code", "profile": "mii-pr-mtb-rna-seq",
     "expression": r"Observation\.component", "text": r"Slicing cannot be evaluated: Could not match discriminator \(code\)"},
    {"id": "mtb-ngs-bericht-result-slice-overlap", "profile": "mii-pr-mtb-",
     "expression": r"(investigation|supportingInfo|result|derivedFrom)", "text": r"Unable to find a profile match .*mii-pr-mtb-ngs-bericht"},
    {"id": "mtb-ngs-bericht-result-slice-overlap", "profile": "mii-pr-mtb-ngs-bericht",
     "expression": r"DiagnosticReport\.result", "text": r"(Tumorzellgehalt|matches more than one slice|max allowed = 1)"},
]


def _http(method, url, body=None, ctype="application/fhir+json", timeout=180):
    data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": ctype, "Accept": "application/fhir+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as ex:
        raw = ex.read()
        try:
            return ex.code, json.loads(raw)
        except Exception:
            return ex.code, {"resourceType": "OperationOutcome",
                             "issue": [{"severity": "fatal", "code": "exception", "diagnostics": raw[:500].decode(errors="replace")}]}


class Matchbox:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def validate(self, resource: dict, profile: str | None = None) -> dict:
        q = "?profile=" + urllib.parse.quote(profile) if profile else ""
        return _http("POST", f"{self.base}/{resource['resourceType']}/$validate{q}", resource)[1]

    def transform(self, source: dict, map_url: str) -> tuple[int, dict]:
        return _http("POST", f"{self.base}/StructureMap/$transform?source=" + urllib.parse.quote(map_url), source)

    def put(self, resource: dict) -> tuple[int, dict]:
        """Create/update a conformance resource (StructureDefinition, StructureMap, ConceptMap, ...) by its id."""
        return _http("PUT", f"{self.base}/{resource['resourceType']}/{resource['id']}", resource)


class Hapi:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def transaction(self, bundle: dict) -> tuple[bool, dict]:
        status, resp = _http("POST", self.base, bundle, timeout=600)
        ok = status < 300 and resp.get("resourceType") == "Bundle" and all(
            str((e.get("response") or {}).get("status", "")).startswith(("200", "201")) for e in resp.get("entry", []))
        return ok, resp

    def count(self, rtype: str) -> int:
        return _http("GET", f"{self.base}/{rtype}?_summary=count")[1].get("total", -1)


def message_id(issue: dict) -> str:
    for e in issue.get("extension", []):
        if e.get("url") == MESSAGE_ID_EXT:
            return e.get("valueString", "")
    return ""


def issue_text(issue: dict) -> str:
    return issue.get("diagnostics") or (issue.get("details") or {}).get("text", "")


def norm_expr(expr: str) -> str:
    """'Bundle.entry[3].resource/*Observation/abc*/.component[1]' -> 'Observation.component[1]'."""
    return re.sub(r"^Bundle\.entry\[\d+\]\.resource/\*(\w+)/[^*]*\*/", r"\1", expr)


def classify_issue(issue: dict, profile: str = "", source_text: str = "") -> str:
    """'info' (not an error) | 'content' | 'unchecked' | 'source' | 'waived:<id>'"""
    if issue.get("severity") not in ("error", "fatal"):
        return "info"
    text, mid = issue_text(issue), message_id(issue)
    expr0 = " ".join(norm_expr(e) for e in (issue.get("expression", []) or issue.get("location", [])))
    for w in WAIVERS:
        if w["profile"] in profile and re.search(w["expression"], expr0) and re.search(w["text"], text):
            return f"waived:{w['id']}"
    if TERMINOLOGY_LIMIT.search(text):
        return "unchecked"
    m = UNKNOWN_CODE.search(text) or (VS_CODES.search(text) if "None of the codings provided" in text else None)
    if m and source_text:
        code = m.group(1).strip()
        if len(code) > 2 and (f'"{code}"' in source_text or f'"{code.split(":")[-1]}"' in source_text):
            return "source"
    expr = " ".join(norm_expr(e) for e in (issue.get("expression", []) or issue.get("location", [])))
    for w in WAIVERS:
        if w["profile"] in profile and re.search(w["expression"], expr) and re.search(w["text"], text):
            return f"waived:{w['id']}"
    if DEFINITIVE_INVALID.search(text) and "cannot be validated" not in text:
        return "content"
    mentions_unavailable = any(s in text for s in UNAVAILABLE_SYSTEMS)
    if (UNCHECKED_PATTERNS.search(text) or mid.upper().startswith(("TERMINOLOGY_TX_SYSTEM", "UNKNOWN_CODESYSTEM"))) \
            and (mentions_unavailable or "terminology" in text.lower()):
        return "unchecked"
    return "content"


def _own_issues(oo: dict, prof: str, source_text: str) -> list[dict]:
    out = []
    for i in oo.get("issue", []):
        if i.get("severity") == "information":
            continue
        text = issue_text(i)
        if i.get("severity") in ("error", "fatal") and REFERENCE_ARTEFACT.search(text):
            continue   # judged in bundle context
        out.append({"class": classify_issue(i, prof or "", source_text), "severity": i.get("severity"), "text": text[:500],
                    "expression": (i.get("expression") or i.get("location") or [""])[0], "message_id": message_id(i)})
    return out


def validate_bundle(bundle: dict, mb: Matchbox, bundle_level: bool = True, source: dict | None = None) -> dict:
    """Validate every resource against its declared profiles, then the Bundle for reference resolution.
    Returns {verdict, resources: [{type, id, profile, issues: [{class, severity, text, expression, message_id}]}]}.
    Verdict: FAIL (content) > DATA-QUALITY (source) > INCONCLUSIVE (unchecked) > PASS."""
    source_text = json.dumps(source, ensure_ascii=False) if source is not None else ""
    out, by_url = [], {}
    for e in bundle.get("entry", []):
        res = e["resource"]
        for prof in (res.get("meta", {}).get("profile") or [None]):
            row = {"type": res["resourceType"], "id": res.get("id"), "profile": prof,
                   "issues": _own_issues(mb.validate(res, prof), prof, source_text)}
            out.append(row)
            by_url.setdefault(e.get("fullUrl"), []).append(row)
    if bundle_level:
        entries = bundle.get("entry", [])
        brow = {"type": "Bundle", "id": bundle.get("id"), "profile": None, "issues": []}
        pending = []   # (row, issue dict, referenced url or None, own url)
        for i in mb.validate(bundle).get("issue", []):
            if i.get("severity") not in ("error", "fatal"):
                continue
            text = issue_text(i)
            expr = (i.get("expression") or i.get("location") or [""])[0]
            mi = re.match(r"Bundle\.entry\[(\d+)\]", expr)
            own = entries[int(mi.group(1))].get("fullUrl") if mi and int(mi.group(1)) < len(entries) else None
            if not REFERENCE_ARTEFACT.search(text):
                # issues only visible in bundle context (e.g. slices discriminated by resolve()) are added once
                # these come from resolving references (candidate-profile matching) and never appear when the
                # resource is validated alone: a listed package defect stays 'waived', everything else is a cascade
                rows = by_url.get(own) or [brow]
                if text[:500] not in {x["text"] for r in rows for x in r["issues"]}:
                    cls = classify_issue(i, rows[0].get("profile") or "", source_text)
                    rows[0]["issues"].append({"class": cls if cls.startswith("waived") or cls == "info" else "cascade",
                                              "severity": i.get("severity"), "text": text[:500], "expression": expr,
                                              "message_id": message_id(i)})
                continue
            m = re.search(r"urn:uuid:[0-9a-f-]{36}", text)
            rows = by_url.get(own) or [brow]
            issue = {"class": None, "severity": i.get("severity"), "text": text[:500], "expression": expr,
                     "message_id": message_id(i)}
            rows[0]["issues"].append(issue)
            pending.append((issue, m.group(0) if m else None, own, (i, rows[0].get("profile") or "")))
        # listed package defects are decided first: a resource failing only through a waived defect still taints
        # the resources that reference it (e.g. Therapieplan -> Behandlungsepisode -> NGS report result slices)
        for issue, _, _, (raw, prof) in pending:
            cls = classify_issue(raw, prof, source_text)
            if cls.startswith("waived"):
                issue["class"] = cls
        # a reference failure is a cascade when the referenced resource has errors of its own or is itself tainted
        tainted = {u for u, rows in by_url.items() if any(x["class"] not in ("info", None) for r in rows for x in r["issues"])}
        changed = True
        while changed:
            changed = False
            for issue, ref, own, _ in pending:
                if issue["class"] is None and (ref in tainted if ref else bool(tainted - {own})):
                    issue["class"] = "cascade"
                    if own and own not in tainted:
                        tainted.add(own)
                    changed = True
        for issue, ref, own, (raw, prof) in pending:
            if issue["class"] is None:
                issue["class"] = classify_issue(raw, prof, source_text)
        if brow["issues"]:
            out.append(brow)
    classes = {i["class"] for r in out for i in r["issues"]}
    verdict = "FAIL" if "content" in classes else "DATA-QUALITY" if "source" in classes else \
              "INCONCLUSIVE" if "unchecked" in classes else "PASS"
    return {"verdict": verdict, "resources": out}
