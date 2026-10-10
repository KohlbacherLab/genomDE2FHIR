"""matchbox $validate / $transform and HAPI transaction client, with a structured issue classifier.

Bundle verdict, by precedence:  ERROR > FAIL > DATA-QUALITY > INCONCLUSIVE > PASS
  ERROR         validation could not run: matchbox unreachable or timed out, an HTTP error, a response that is not
                a non-empty OperationOutcome, or a profile matchbox does not know. Never PASS.
  FAIL          at least one `content` issue
  DATA-QUALITY  at least one `source` issue (and no content issue)
  INCONCLUSIVE  at least one `unchecked` issue
  PASS          none of these. Warnings (`info`), `waived`, `cascade` and `candidate` issues are reported, never fail.

Issue classes (severity error/fatal; warnings are kept as `info`, except dangling urn:uuid references = content):
  validator-error  the validation call itself failed                                          -> ERROR
  content          a conformance error in our output                                          -> FAIL
  source           an unknown code of an external code system the converter copies verbatim (HGVS, SNOMED, ...)
                   that is exactly the value of a field of the input file, or HGVS composed only of such values
                   (_from_source); never a coding of a system the value set does not admit   -> DATA-QUALITY
                   Limitation (R17): the test is on the value, not on how it got there, so a raw KDK enum value
                   that reaches a SNOMED/LOINC coding through a missing ConceptMap entry (a converter defect) is
                   also classed `source`, not `content`.
  unchecked        the tx server cannot decide: a terminology/edition it does not serve (BfArM systems, ICD-O-3
                   2014/2019, ...) for a coding the binding admits, a tx timeout, or a reference failure whose
                   target is only unchecked
                                                                                               -> INCONCLUSIVE
  waived:<id>      a known ballot-package defect listed in WAIVERS                            -> reported
  cascade          a reference/profile-match failure whose target (or a resource the target references) has a
                   content/source/waived error of its own, which is counted there             -> reported
  candidate        an error of a resource against a profile it does not declare (nor derives from), raised while
                   matchbox tried it as the target of a failing reference; that reference failure is classified
                   itself                                                                     -> reported
Each resource is validated alone against its declared profiles (own issues). The whole-Bundle pass adds what only the
Bundle context shows: Bundle rules (bdl-*, entry.request, fullUrl) and the reference-dependent issues (profile
matches of reference targets, slices discriminated by resolve(), dangling references). A reference failure is never
dropped: it is `cascade` / `unchecked` only when its target's own errors (followed through the target's references)
explain it, otherwise `content`; only targets that can be of a profile the reference (or the resolve() slice) allows
count, so a reference to the wrong kind of resource is `content` whatever that resource's errors.
"""
import http.client
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from .io import dumps, loads
from .systems import HGVS as HGVS_SYSTEM

MESSAGE_ID_EXT = "http://hl7.org/fhir/StructureDefinition/operationoutcome-message-id"
NO_RESPONSE = 599   # pseudo HTTP status of _http when no response arrived (refused, DNS, timeout, broken connection)
VALIDATOR_UNREACHABLE = "genomde2fhir-validator-unreachable"   # message ids of synthetic validator-error issues
VALIDATOR_FAILED = "genomde2fhir-validator-failed"
DANGLING_ID = "genomde2fhir-dangling-reference"
# code systems tx.fhir.org cannot validate (licensed / national); errors that only say "cannot check" -> unchecked.
# ICD-O-3 is not listed: tx.fhir.org serves edition 2000, only the editions 2014/2019 (TERMINOLOGY_LIMIT) are unknown
UNAVAILABLE_SYSTEMS = (
    "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "http://fhir.de/CodeSystem/bfarm/ops",
    "http://fhir.de/CodeSystem/bfarm/atc", "http://fhir.de/CodeSystem/bfarm/alpha-id",
    "http://www.orpha.net", "http://www.meddra.org", "http://fhir.de/CodeSystem/ifa/pzn",
    "http://human-phenotype-ontology.org", "http://www.genenames.org", "http://varnomen.hgvs.org",
    "http://www.sequenceontology.org", "http://www.ensembl.org", "http://www.ncbi.nlm.nih.gov/refseq",
    "https://www.uicc.org/resources/tnm", "https://cancer.sanger.ac.uk/cosmic",
)
# external code systems whose codes the converter copies verbatim from the input (candidates for `source`); MII,
# genomDE and HL7 code systems the converter maps into are deliberately absent
VERBATIM_SYSTEMS = (
    "http://varnomen.hgvs.org", "http://snomed.info/sct", "http://loinc.org", "http://www.genenames.org",
    "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "http://fhir.de/CodeSystem/bfarm/ops",
    "http://fhir.de/CodeSystem/bfarm/atc", "http://www.whocc.no/atc", "http://fhir.de/CodeSystem/bfarm/alpha-id",
    "http://www.orpha.net", "http://human-phenotype-ontology.org", "http://www.sequenceontology.org",
    "http://www.ensembl.org", "http://www.ncbi.nlm.nih.gov/refseq", "https://cancer.sanger.ac.uk/cosmic",
    "http://terminology.hl7.org/CodeSystem/icd-o-3", "urn:oid:2.16.840.1.113883.6.43.1", "http://www.meddra.org",
    "http://fhir.de/CodeSystem/ifa/pzn", "https://www.uicc.org/resources/tnm",
    "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl",
)
UNCHECKED_PATTERNS = re.compile(
    r"(could not be found, so the code cannot be validated|cannot be validated|unable to check|"
    r"no versions of this code system are known|not known to the terminology server|"
    r"unknown code ?system|unable to (validate|expand)|terminology service|error expanding valueset|"
    r"a definition for codesystem .* could not be found|valueset .* not found|"
    r"cannot validate code|was not found by the terminology server|timed out)", re.I)
TX_PHRASE = re.compile(r"terminology (server|service)", re.I)
# the tx server cannot decide, recognised before the source-data rule: the ICD-O-3 editions the MII value sets pin
# (tx.fhir.org knows only 2000), tx timeouts
TERMINOLOGY_LIMIT = re.compile(
    r"(CodeSystem '(http://terminology\.hl7\.org/CodeSystem/icd-o-3|urn:oid:2\.16\.840\.1\.113883\.6\.43\.1)' "
    r"version '(2014|2019)' could not be found|timed out|HGVS validation request)", re.I)
# an HGVS expression the converter composes: '<reference sequence>[(<gene symbol>)]:<notation>'
HGVS_COMPOSED = re.compile(r"^([^\s():]+)(?:\(([^\s()]+)\))?:(\S+)$")
UNKNOWN_CODE = re.compile(r"Unknown code ['\"]([^'\"]+)['\"](?: in the CodeSystem ['\"]([^'\"]+)['\"])?", re.I)
VS_CODES = re.compile(r"\(codes? = (.*)\)\s*$")
VS_URL = re.compile(r"value set '.*?' \(([a-z][\w+.-]*:[^\s|)]+)")
DEFINITIVE_INVALID = re.compile(r"(unknown code ['\"]|is not a valid code|not found in (the )?code ?system|"
                                r"code .* is not in the code ?system)", re.I)
PROFILE_NOT_FOUND = re.compile(r"validation for profile '[^']*' not found", re.I)
# reference-dependent messages (judged in Bundle context)
CANT_MATCH = re.compile(r"Unable to find a profile match for (\S+) among choices: (.*)$", re.S)
REF_FAILURE = re.compile(r"(Unable to find a match for profile .* among choices|"
                         r"Unable to resolve resource with reference 'urn:uuid)", re.I)
SLICE_MISSING = re.compile(r"Slice '(?P<id>(?P<path>[A-Za-z][\w.\[\]]*):[^']*)': a matching slice is required")
DEFINITIVE_REF = re.compile(r"(Invalid Resource target type|Multiple matches in bundle for reference|"
                            r"Unable to resolve resource with reference|URN reference is not locally contained)", re.I)
DANGLING_WARNING = re.compile(r"URN reference is not locally contained within the bundle", re.I)
# a profile the message was raised against, and messages that do not depend on reference resolution
NAMED_PROFILE = re.compile(r"(?:\(from |defined in the profile |in the profile |\(defined in )(https?://[^\s|()#]+)")
TERMINOLOGY_MSG = re.compile(r"(None of the codings provided are in the value set|Unknown code |is not in the value set|"
                             r"The pattern \[|but is fixed to )", re.I)
URN = re.compile(r"urn:uuid:[0-9a-f-]{36}")
BASE_SD = "http://hl7.org/fhir/StructureDefinition/"

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
    # MTB-22, in matchbox's own shapes: the overflow of the Tumorzellgehalt slice (core Observation profile) is reported
    # at the DiagnosticReport itself, the slice overlaps at the result. The converter puts no Tumorzellgehalt
    # Observation into an NGS-Bericht, so the overflow is always the overlap.
    {"id": "mtb-ngs-bericht-result-slice-overlap", "profile": "mii-pr-mtb-ngs-bericht",
     "expression": r"^DiagnosticReport$",
     "text": r"^DiagnosticReport\.result:Tumorzellgehalt: max allowed = 1, but found"},
    {"id": "mtb-ngs-bericht-result-slice-overlap", "profile": "mii-pr-mtb-ngs-bericht",
     "expression": r"^DiagnosticReport\.result(\[\d+\])?$", "text": r"Element matches more than one slice - "},
    # any other 'max allowed = 1' is deliberately not waived: a duplicated TMB/HRD/Ploidie result is content (R15)
]


def _not_run(text: str, mid: str = VALIDATOR_FAILED) -> dict:
    """An OperationOutcome standing for 'validation did not run' (classified validator-error -> verdict ERROR)."""
    return {"resourceType": "OperationOutcome", "issue": [{
        "severity": "fatal", "code": "exception", "diagnostics": text[:1000],
        "extension": [{"url": MESSAGE_ID_EXT, "valueCode": mid}]}]}


def _http(method, url, body=None, ctype="application/fhir+json", timeout=180, headers=None):
    """(status, parsed JSON body). Never raises for network trouble: no response -> (NO_RESPONSE, OperationOutcome),
    a body that is not JSON -> (status, OperationOutcome); both carry a validator-error message id. An empty body
    gives {} (callers check the shape). Bodies are written with io.dumps and read with io.loads, so io.Num decimals
    keep their written precision on the wire and in responses."""
    data = None if body is None else (body if isinstance(body, bytes) else dumps(body, indent=None).encode())
    try:
        # built inside the try: Request() itself raises ValueError for a URL without a scheme ('matchbox/fhir')
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Content-Type": ctype, "Accept": "application/fhir+json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                status, raw = r.status, r.read()
        except urllib.error.HTTPError as ex:
            status, raw = ex.code, ex.read()
    except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError) as ex:   # incl. timeouts, bad URLs
        return NO_RESPONSE, _not_run(f"{method} {url}: no response ({getattr(ex, 'reason', None) or ex})",
                                     VALIDATOR_UNREACHABLE)
    if not raw.strip():
        return status, {}
    try:
        return status, loads(raw)   # io.Num: $transform output keeps its decimal spelling (parity sees 58.50 vs 58.5)
    except ValueError:
        return status, _not_run(f"{method} {url}: HTTP {status}, not JSON: {raw[:300].decode(errors='replace')}")


def is_unreachable(oo) -> bool:
    """True for the OperationOutcome _http returns when the server did not answer at all."""
    return isinstance(oo, dict) and any(message_id(i) == VALIDATOR_UNREACHABLE for i in oo.get("issue", []))


class Matchbox:
    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self._ancestors, self._slices, self._vs = {}, {}, {}

    def validate(self, resource: dict, profile: str | None = None) -> dict:
        """The OperationOutcome of $validate, or a validator-error OperationOutcome when the call failed (HTTP
        error, no response, not a non-empty OperationOutcome): never an empty or foreign body."""
        q = "?profile=" + urllib.parse.quote(profile) if profile else ""
        what = f"matchbox $validate {resource.get('resourceType')}{' ' + profile if profile else ''}"
        status, oo = _http("POST", f"{self.base}/{resource.get('resourceType')}/$validate{q}", resource)
        if is_unreachable(oo):
            return oo
        if not isinstance(oo, dict) or oo.get("resourceType") != "OperationOutcome":
            return _not_run(f"{what}: HTTP {status}, response is not an OperationOutcome: {json.dumps(oo)[:300]}")
        if status >= 300:
            first = issue_text((oo.get("issue") or [{}])[0])
            return _not_run(f"{what}: HTTP {status}: {first[:300]}")
        if not oo.get("issue"):   # matchbox always reports at least an information issue
            return _not_run(f"{what}: HTTP {status}, empty OperationOutcome")
        return oo

    def ancestors(self, url: str) -> set | None:
        """The profile and its baseDefinition chain (canonicals without version); None if matchbox cannot tell."""
        url = url.split("|")[0]
        if url not in self._ancestors:
            chain, cur = [], url
            while cur and cur not in chain and len(chain) < 20:
                chain.append(cur)
                if cur.startswith(BASE_SD):
                    break
                st, b = _http("GET", f"{self.base}/StructureDefinition?url={urllib.parse.quote(cur, safe=':/')}"
                                     "&_elements=url,baseDefinition", timeout=60)
                ents = b.get("entry") if st < 300 and isinstance(b, dict) else None
                if not ents:
                    chain = None
                    break
                cur = ((ents[0].get("resource") or {}).get("baseDefinition") or "").split("|")[0]
            self._ancestors[url] = set(chain) if chain is not None else None
        return self._ancestors[url]

    def _search(self, rtype: str, url: str) -> dict | None:
        """The first conformance resource of `rtype` with this canonical (exact url search, version not matched, as in
        ancestors()); None if matchbox cannot tell."""
        st, b = _http("GET", f"{self.base}/{rtype}?url={urllib.parse.quote(url.split('|')[0], safe=':/')}", timeout=60)
        ents = b.get("entry") if st < 300 and isinstance(b, dict) else None
        return (ents[0].get("resource") or None) if ents else None

    def slice_targets(self, profile: str, element_id: str) -> set | None:
        """type[].targetProfile (canonicals without version) of the element `element_id` (a slice such as
        'MedicationRequest.reasonReference:Primaertumor') in the snapshot of `profile`; None if matchbox cannot tell
        or the element names no target profile."""
        url = profile.split("|")[0]
        if url not in self._slices:
            sd = self._search("StructureDefinition", url)
            self._slices[url] = None if sd is None else {
                el.get("id"): {t.split("|")[0] for ty in el.get("type", []) for t in ty.get("targetProfile", [])}
                for el in (sd.get("snapshot") or {}).get("element", [])}
        return (self._slices[url] or {}).get(element_id) or None

    def vs_systems(self, url: str) -> set | None:
        """The code systems a value set admits (compose.include[].system, followed through include.valueSet); None if
        matchbox cannot tell."""
        url = url.split("|")[0]
        if url not in self._vs:
            self._vs[url] = None   # also stops include cycles
            vs, out = self._search("ValueSet", url), set()
            for inc in ((vs or {}).get("compose") or {}).get("include", []):
                subs = [self.vs_systems(u) for u in inc.get("valueSet", [])]
                if None in subs:
                    out = None
                    break
                out |= {inc["system"]} if inc.get("system") else set()
                out = out.union(*subs)
            self._vs[url] = out or None
        return self._vs[url]

    def packages(self, prefix: str = "de.medizininformatikinitiative.kerndatensatz.") -> dict | None:
        """{packageId: {versions}} of the loaded packages whose id starts with prefix (matchbox lists each loaded
        package as an ImplementationGuide); None when the server cannot tell (no answer, not a search Bundle)."""
        st, b = _http("GET", f"{self.base}/ImplementationGuide?_elements=packageId,version&_count=1000", timeout=60)
        if st >= 300 or not isinstance(b, dict) or b.get("resourceType") != "Bundle":
            return None
        out = {}
        for e in b.get("entry", []):
            r = e.get("resource") or {}
            if str(r.get("packageId", "")).startswith(prefix):
                out.setdefault(r["packageId"], set()).add(str(r.get("version", "")))
        return out

    def transform(self, source: dict, map_url: str) -> tuple[int, dict]:
        return _http("POST", f"{self.base}/StructureMap/$transform?source=" + urllib.parse.quote(map_url), source)

    def put(self, resource: dict) -> tuple[int, dict]:
        """Create/update a conformance resource (StructureDefinition, StructureMap, ConceptMap, ...) by its id."""
        return _http("PUT", f"{self.base}/{resource['resourceType']}/{resource['id']}", resource)


class Hapi:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def transaction(self, bundle: dict) -> tuple[bool, dict]:
        """(ok, response). No response or a non-Bundle answer is not ok; is_unreachable(response) tells which."""
        status, resp = _http("POST", self.base, bundle, timeout=600)
        resp = resp if isinstance(resp, dict) else {"response": resp}
        ok = status < 300 and resp.get("resourceType") == "Bundle" and all(
            str((e.get("response") or {}).get("status", "")).startswith(("200", "201")) for e in resp.get("entry", []))
        return ok, resp

    def count(self, rtype: str) -> int:
        """Total of `rtype` (-1 on failure); no-cache, since HAPI caches _summary=count searches."""
        st, body = _http("GET", f"{self.base}/{rtype}?_summary=count", headers={"Cache-Control": "no-cache"})
        return body.get("total", -1) if st < 300 and isinstance(body, dict) else -1


def message_id(issue: dict) -> str:
    for e in issue.get("extension", []):
        if e.get("url") == MESSAGE_ID_EXT:
            return e.get("valueCode") or e.get("valueString") or ""
    return ""


def issue_text(issue: dict) -> str:
    return issue.get("diagnostics") or (issue.get("details") or {}).get("text", "")


def norm_expr(expr: str) -> str:
    """'Bundle.entry[3].resource/*Observation/abc*/.component[1]' -> 'Observation.component[1]'."""
    return re.sub(r"^Bundle\.entry\[\d+\]\.resource/\*(\w+)/[^*]*\*/", r"\1", expr)


def _expr(issue: dict) -> str:
    return (issue.get("expression") or issue.get("location") or [""])[0]


def _source_values(obj) -> frozenset:
    """Every scalar value (not key) of the input file, as strings."""
    out = set()

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str):
            out.add(o.strip())
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            out.add(str(o))
    walk(obj)
    return frozenset(out)


def _offending_codes(text: str) -> list[tuple[str, str]]:
    """(system, code) of an 'Unknown code' or 'None of the codings provided' message; system '' if not named."""
    m = UNKNOWN_CODE.search(text)
    if m:
        return [((m.group(2) or "").split("|")[0], m.group(1))]
    m = VS_CODES.search(text) if "None of the codings provided" in text else None
    if not m:
        return []
    parts = re.split(r", (?=[^\s,#]+#)", m.group(1))
    return [(p.split("#", 1)[0].split("|")[0], p.split("#", 1)[1]) for p in parts if "#" in p]


def _from_source(code: str, source_values: frozenset, system: str = "") -> bool:
    """The code is verbatim the whole value of an input field. For HGVS also an expression the converter composes
    from input parts ('<reference sequence>[(<gene symbol>)]:<notation>', molecular_variants.transcript_accession and
    qualify_hgvs), but only when EVERY part is verbatim the whole value of an input field: the notation (the c./g./p.
    field), the gene symbol if present (gene.display), and the reference sequence either as one value (the
    transcript code) or as '<accession>.<version>' with both parts input values (transcriptId code + version).
    Deliberate simplification: any field of the input counts, the converter records no per-field provenance."""
    code = code.strip()
    if len(code) <= 2:
        return False
    if code in source_values:
        return True
    m = HGVS_COMPOSED.match(code) if system == HGVS_SYSTEM else None
    if not m:
        return False
    ref, gene, notation = m.groups()
    accession, _, version = ref.rpartition(".")
    return len(notation) > 2 and notation in source_values and (gene is None or gene in source_values) and (
        ref in source_values or (bool(accession) and accession in source_values and version in source_values))


def _tx_cannot_check(text: str) -> bool:
    return bool(TERMINOLOGY_LIMIT.search(text)) or (
        bool(re.search(r"could not be found, so the code cannot be validated|Unable to check whether the code is in "
                       r"the value set", text)) and any(s in text for s in UNAVAILABLE_SYSTEMS))


def _admitted(text: str, vs_systems) -> set | None:
    """The code systems the value set of a 'None of the codings provided' message includes; None = cannot tell."""
    m = VS_URL.search(text) if "None of the codings provided" in text else None
    return vs_systems(m.group(1)) if vs_systems and m else None


def _undecidable_below(issue: dict, siblings, admitted: set | None) -> bool:
    """A value-set membership error ('None of the codings provided') the tx server cannot decide: one of the offending
    codings has a system that a sibling at or below the error's element reports the tx server cannot check (it names
    the system, or is a tx timeout / HGVS request failure), AND that system is admissible for the binding (in
    `admitted`, the value set's systems; None = cannot tell, then admitted). A coding of a system the value set does
    not include is definitively no member, whether or not its system can be checked: the error stays content."""
    expr, text = _expr(issue), issue_text(issue)
    below = [issue_text(s) for s in siblings or [] if s is not issue and expr
             and (_expr(s) == expr or _expr(s).startswith(expr + ".")) and _tx_cannot_check(issue_text(s))]
    return bool(below) and any((admitted is None or system in admitted) and any(
        system in t or "timed out" in t or (system == HGVS_SYSTEM and "HGVS" in t) for t in below)
        for system, _ in _offending_codes(text) if system)


def classify_issue(issue: dict, profile: str = "", source_values=frozenset(), siblings=None, vs_systems=None) -> str:
    """'info' (not an error) | 'validator-error' | 'content' | 'unchecked' | 'source' | 'waived:<id>'.
    source_values: the scalar values of the input file (or its JSON text); siblings: the other issues of the same
    OperationOutcome and vs_systems: value set url -> admitted code systems (a value-set error is unchecked when the
    tx server could not check an admissible coding below it, see _undecidable_below; a coding of a system the value
    set does not admit is a converter error, never `source`)."""
    if issue.get("severity") not in ("error", "fatal"):
        return "info"
    text, mid = issue_text(issue), message_id(issue)
    if mid in (VALIDATOR_UNREACHABLE, VALIDATOR_FAILED) or PROFILE_NOT_FOUND.search(text) or (
            issue.get("code") == "exception" and not _expr(issue)):
        return "validator-error"
    if isinstance(source_values, str):   # the input file as JSON text (former signature)
        source_values = _source_values(json.loads(source_values)) if source_values else frozenset()
    expr = " ".join(norm_expr(e) for e in (issue.get("expression", []) or issue.get("location", [])))
    for w in WAIVERS:
        if w["profile"] in profile and re.search(w["expression"], expr) and re.search(w["text"], text):
            return f"waived:{w['id']}"
    if TERMINOLOGY_LIMIT.search(text):
        return "unchecked"
    admitted = _admitted(text, vs_systems)
    if "None of the codings provided" in text and _undecidable_below(issue, siblings, admitted):
        return "unchecked"
    codes = _offending_codes(text)
    if codes and source_values and all(s in VERBATIM_SYSTEMS and (admitted is None or s in admitted)
                                       and _from_source(c, source_values, s) for s, c in codes):
        return "source"
    if DEFINITIVE_INVALID.search(text) and "cannot be validated" not in text:
        return "content"
    mentions_unavailable = any(s in text for s in UNAVAILABLE_SYSTEMS)
    if (UNCHECKED_PATTERNS.search(text) or mid.upper().startswith(("TERMINOLOGY_TX_SYSTEM", "UNKNOWN_CODESYSTEM"))) \
            and (mentions_unavailable or TX_PHRASE.search(text)):
        return "unchecked"
    return "content"


# ---- reference helpers ------------------------------------------------------------------------------------------

def _element_values(obj, name: str) -> list:
    """All values of elements called `name` anywhere in obj ('value[x]' matches valueReference, ...)."""
    base = name[:-3] if name.endswith("[x]") else None
    out = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == name or (base and k.startswith(base) and k[len(base):len(base) + 1].isupper()):
                    out.extend(v if isinstance(v, list) else [v])
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return out


def _references(obj, path: str = ""):
    """(path, reference) of every Reference.reference string in obj."""
    if isinstance(obj, dict):
        if isinstance(obj.get("reference"), str):
            yield path, obj["reference"]
        for k, v in obj.items():
            if k != "reference":
                yield from _references(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for n, v in enumerate(obj):
            yield from _references(v, f"{path}[{n}]")


def _slice_refs(resource, text: str):
    """For a missing required slice: the references the sliced element holds when it is a Reference element of
    this resource (a slice discriminated by resolve()), else None (a coding/extension/... slice, or the element is
    absent: then no reference resolution can satisfy it)."""
    m = SLICE_MISSING.search(text)
    if not m or not isinstance(resource, dict):
        return None
    vals = _element_values(resource, m.group("path").split(".")[-1])
    refs = [v["reference"] for v in vals if isinstance(v, dict) and isinstance(v.get("reference"), str)]
    return refs or None


def _refs_at(resource, expr: str) -> list[str]:
    """References at (below) the element an issue expression points at."""
    m = re.match(r"^Bundle\.entry\[\d+\]\.resource(?:/\*\w+/[^*]*\*/)?\.?(.*)$", expr) or \
        re.match(r"^[A-Z]\w*\.?(.*)$", expr)
    path = re.sub(r"\.ofType\((\w)(\w*)\)", lambda x: x.group(1).upper() + x.group(2), m.group(1) if m else "")
    nodes = [resource]
    for step in [s for s in path.split(".") if s]:
        sm = re.match(r"^(\w+)(?:\[(\d+)\])?$", step)
        if not sm:
            break
        nxt = []
        for n in nodes:
            v = n.get(sm.group(1)) if isinstance(n, dict) else None
            vs = v if isinstance(v, list) else ([] if v is None else [v])
            nxt += vs[int(sm.group(2)):int(sm.group(2)) + 1] if sm.group(2) is not None else vs
        nodes = nxt
    return [r for n in nodes for _, r in _references(n)]


def _reference_dependent(text: str, resource) -> bool:
    """Errors that validating a resource alone cannot judge (its urn:uuid references do not resolve)."""
    return bool(CANT_MATCH.search(text) or REF_FAILURE.search(text)) or _slice_refs(resource, text) is not None


def _record(issue: dict, cls) -> dict:
    return {"class": cls, "severity": issue.get("severity"), "text": issue_text(issue)[:500],
            "expression": _expr(issue), "message_id": message_id(issue)}


def _own_issues(oo: dict, prof, source_values, resource=None, vs_systems=None) -> tuple[list, list]:
    """(issues, deferred): deferred are reference-dependent errors, judged in Bundle context."""
    issues, out, deferred = oo.get("issue", []), [], []
    for i in issues:
        if i.get("severity") == "information":
            continue
        cls = classify_issue(i, prof or "", source_values, issues, vs_systems)
        if cls != "validator-error" and i.get("severity") in ("error", "fatal") \
                and _reference_dependent(issue_text(i), resource):
            deferred.append(_record(i, cls))
            continue
        out.append(_record(i, cls))
    return out, deferred


def _plausible_target(target: dict, choices, mb) -> bool:
    """False when the target cannot be of any of the reference's (or slice's) target profiles, so the reference points
    at the wrong kind of resource whatever the target's own errors are: it declares profiles and none is (or derives
    from) one of them, or it declares none and its resource type is not the type of any of them. True when matchbox
    cannot tell."""
    choices = {c.split("|")[0] for c in choices}
    base = BASE_SD + str(target.get("resourceType"))
    declared = {p.split("|")[0] for p in (target.get("meta") or {}).get("profile") or []}
    if base in choices or declared & choices:
        return True
    lookup = getattr(mb, "ancestors", None)
    if lookup is None:
        return True   # no profile hierarchy available: cannot tell
    for p in declared or choices:   # declared profiles: derived from a choice? none: a choice of this resource type?
        anc = lookup(p)
        if anc is None or (anc & choices if declared else base in anc):
            return True
    return False


def _own_chain(res: dict, mb) -> set:
    """The resource's declared profiles with their baseDefinition chains (as far as matchbox can tell) and its core
    type: an error naming one of them, e.g. '(defined in <base profile>)' of an obs-6 invariant, is the resource's own,
    not a candidate profile's."""
    declared = {p.split("|")[0] for p in (res.get("meta") or {}).get("profile") or []}
    out = declared | {BASE_SD + str(res.get("resourceType"))}
    lookup = getattr(mb, "ancestors", None)
    for p in declared if lookup else ():
        out |= lookup(p) or set()
    return out


def _slice_choices(text: str, profile, mb):
    """The target profiles of the missing required slice of `text` (from the profile the message names, else the
    row's), None when matchbox cannot tell."""
    m, named = SLICE_MISSING.search(text), NAMED_PROFILE.findall(text)
    lookup, prof = getattr(mb, "slice_targets", None), named[0] if named else profile
    return lookup(prof, m.group("id")) if m and prof and lookup else None


def _bundle_pass(oo: dict, bundle: dict, by_url: dict, brow: dict, source_values, mb) -> None:
    """Add the issues only the Bundle context shows to the rows and classify them (see the module docstring)."""
    entries = bundle.get("entry", [])
    res_by_url = {e.get("fullUrl"): e.get("resource") or {} for e in entries}
    issues = oo.get("issue", [])
    seen = {u: {x["text"] for r in rows for x in r["issues"]} for u, rows in by_url.items()}
    seen[None] = {x["text"] for x in brow["issues"]}

    def locate(expr):
        m = re.match(r"Bundle\.entry\[(\d+)\](\.resource)?", expr)
        if m and m.group(2) and int(m.group(1)) < len(entries) and entries[int(m.group(1))].get("fullUrl") in by_url:
            return entries[int(m.group(1))].get("fullUrl")
        return None   # the Bundle itself, an entry's request/fullUrl, or an unknown entry

    # resources matchbox tried as targets of failing references (candidate-profile errors are reported at them)
    tried = set()
    for i in issues:
        if i.get("severity") in ("error", "fatal"):
            text, own = issue_text(i), locate(_expr(i))
            m = CANT_MATCH.search(text)
            if m:
                tried |= set(URN.findall(m.group(1)))
            elif REF_FAILURE.search(text):
                tried |= set(URN.findall(text))
            if own:
                tried |= set(_slice_refs(res_by_url.get(own), text) or [])

    pending, candidates = [], []   # (record, targets, choices or None) / (record, own url, fallback class)
    for i in issues:
        sev = i.get("severity")
        if sev == "information":
            continue
        text, expr = issue_text(i), _expr(i)
        own = locate(expr)
        if text[:500] in seen[own]:
            continue   # judged in the own pass
        seen[own].add(text[:500])
        row = by_url[own][0] if own else brow
        res = res_by_url.get(own) if own else None
        cls = classify_issue(i, row.get("profile") or "", source_values, issues, getattr(mb, "vs_systems", None))
        rec = _record(i, cls)
        row["issues"].append(rec)
        if sev not in ("error", "fatal"):
            rec["class"] = "content" if DANGLING_WARNING.search(text) else "info"
            continue
        if cls.startswith("waived") or cls == "validator-error":
            continue
        if own is None:   # Bundle rules: bdl-*, Bundle.type, entry.request, entry.fullUrl
            rec["class"] = "content"
            continue
        m = CANT_MATCH.search(text)
        if m:
            rec["class"] = None
            pending.append((rec, URN.findall(m.group(1)) or [m.group(1)], m.group(2).split(", ")))
            continue
        if DEFINITIVE_REF.search(text):   # wrong target type, duplicate or missing fullUrl
            rec["class"] = "content"
            continue
        refs = _slice_refs(res, text)
        if refs is not None:   # a resolve() slice: its target profiles as for a profile match (None: cannot tell)
            rec["class"] = None
            pending.append((rec, refs, _slice_choices(text, row.get("profile"), mb)))
            continue
        if REF_FAILURE.search(text):
            rec["class"] = None
            pending.append((rec, URN.findall(text) or _refs_at(res, expr), None))
            continue
        named = set(NAMED_PROFILE.findall(text))
        if (named and not named & _own_chain(res, mb)) or (not named and TERMINOLOGY_MSG.search(text)):
            rec["class"] = None   # a profile the resource does not declare (it would show in the own pass otherwise)
            candidates.append((rec, own, cls))
        else:
            rec["class"] = cls    # e.g. a slice overflow (max allowed) or a resolve() invariant in its own profile
    for rec, own, cls in candidates:
        rec["class"] = "candidate" if own in tried else cls

    # dangling urn:uuid references, also when matchbox words them differently (HAPI rejects them: HAPI-0541)
    for e in entries:
        u, res = e.get("fullUrl"), e.get("resource") or {}
        if u not in by_url:
            continue
        for path, ref in _references(res):
            if ref.startswith("urn:uuid:") and ref not in res_by_url and not any(ref in t for t in seen[u]):
                seen[u].add(ref)
                by_url[u][0]["issues"].append({
                    "class": "content", "severity": "error", "expression": f"{res.get('resourceType')}.{path}",
                    "text": f"Reference {ref} is not the fullUrl of any entry of the Bundle (dangling reference)",
                    "message_id": DANGLING_ID})

    # state of every resource: tainted (own content/source/waived error) > unchecked > clean, followed through the
    # resources it references (matchbox checks a candidate target together with its own references)
    state = {}
    for u, rows in by_url.items():
        cls = {x["class"] or "" for r in rows for x in r["issues"]}
        state[u] = 2 if cls & {"content", "source"} or any(c.startswith("waived") for c in cls) else \
            1 if "unchecked" in cls else 0
    edges = {u: {r for _, r in _references(res_by_url.get(u))} & set(by_url) for u in by_url}
    changed = True
    while changed:
        changed = False
        for u, outs in edges.items():
            s = max([state[u]] + [state[t] for t in outs])
            if s > state[u]:
                state[u], changed = s, True
    for rec, targets, choices in pending:
        if not targets or any(t not in by_url for t in targets):
            rec["class"] = "content"   # dangling or undeterminable target
            continue
        # judged only by the targets that can be of a profile the reference / slice allows; none -> wrong resource
        worst = max((state[t] for t in targets if choices is None or _plausible_target(res_by_url[t], choices, mb)),
                    default=0)
        rec["class"] = "cascade" if worst == 2 else "unchecked" if worst == 1 else "content"


def validate_bundle(bundle: dict, mb: Matchbox, bundle_level: bool = True, source: dict | None = None) -> dict:
    """Validate every resource against its declared profiles, then the Bundle for reference resolution.
    Returns {verdict, resources: [{type, id, profile, issues: [{class, severity, text, expression, message_id}]}]}
    (rows in entry order, one per declared profile, a Bundle row last if it has issues), plus 'error' (and
    'unreachable': True when matchbox did not answer) for verdict ERROR.
    Verdict: ERROR (validator-error) > FAIL (content) > DATA-QUALITY (source) > INCONCLUSIVE (unchecked) > PASS.
    bundle_level=False skips the Bundle pass: reference-dependent errors are then kept as `unchecked`."""
    source_values = _source_values(source) if source is not None else frozenset()
    out, by_url, deferred, aborted = [], {}, [], None
    entries = bundle.get("entry", [])
    for n, e in enumerate(entries):
        res = e.get("resource") or {}
        for prof in (res.get("meta", {}).get("profile") or [None]):
            oo = mb.validate(res, prof)
            issues, dfr = _own_issues(oo, prof, source_values, res, getattr(mb, "vs_systems", None))
            row = {"type": res.get("resourceType"), "id": res.get("id"), "profile": prof, "issues": issues}
            out.append(row)
            by_url.setdefault(e.get("fullUrl"), []).append(row)
            deferred += [(row, d) for d in dfr]
            if is_unreachable(oo):
                aborted = f"validation aborted at entry {n + 1}/{len(entries)}: {issue_text(oo['issue'][0])}"
                break
        if aborted:
            break
    brow = {"type": "Bundle", "id": bundle.get("id"), "profile": None, "issues": []}
    judged = False
    if bundle_level and not aborted:
        oo = mb.validate(bundle)
        if any(classify_issue(i) == "validator-error" for i in oo.get("issue", [])):
            for i in oo["issue"]:   # the failure itself; other errors could not be judged, information is dropped
                cls = classify_issue(i)
                if i.get("severity") != "information":
                    brow["issues"].append(_record(i, cls if cls in ("validator-error", "info") else "unchecked"))
            aborted = aborted or (is_unreachable(oo) and issue_text(oo["issue"][0]))
        else:
            _bundle_pass(oo, bundle, by_url, brow, source_values, mb)
            judged = True
    if not judged:   # never dropped: without the Bundle context reference-dependent errors cannot be decided
        for row, d in deferred:
            d["class"] = "unchecked" if d["class"] in ("content", "source") else d["class"]
            row["issues"].append(d)
    if aborted and not brow["issues"]:
        brow["issues"].append({"class": "validator-error", "severity": "fatal", "text": aborted[:500],
                               "expression": "", "message_id": VALIDATOR_UNREACHABLE})
    if brow["issues"]:
        out.append(brow)
    classes = {i["class"] for r in out for i in r["issues"]}
    verdict = "ERROR" if "validator-error" in classes else "FAIL" if "content" in classes else \
        "DATA-QUALITY" if "source" in classes else "INCONCLUSIVE" if "unchecked" in classes else "PASS"
    result = {"verdict": verdict, "resources": out}
    if verdict == "ERROR":
        result["error"] = next(i["text"] for r in out for i in r["issues"] if i["class"] == "validator-error")
        if aborted:
            result["unreachable"] = True
    return result
