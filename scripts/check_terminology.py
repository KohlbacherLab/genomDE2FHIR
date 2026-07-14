#!/usr/bin/env python3
"""
check_terminology.py — deep terminology / coded-value check of the genomDE→MII mapping.

Automates the manual "NUM-OMICS" review: for every coded value the mapping cites
(LOINC codes, LOINC answer codes LA…, answer lists LL…, SNOMED CT), it asks a FHIR
terminology server ($lookup / $expand) whether the code EXISTS and what its official
display is, then flags:
  * INVALID   — code does not exist in its CodeSystem
  * MISMATCH  — official display shares no keyword with the concept the row maps
                (e.g. LOINC 94195-5 = "CPT2 gene…" cited for an HRD field)
and, for every DK enum field, checks each value for a target equivalent, flagging the
catch-all values (unknown/other/none/notAvailable/…) that have NO clinical code and must
be mapped structurally (dataAbsentReason / nullFlavor / .text / local CS).

tx.fhir.org carries LOINC + SNOMED only. German/OBO systems (ICD-10-GM, ICD-O-3, OPS,
ATC, Orphanet, Alpha-ID, HPO, HGNC, SO, UICC) are reported as NOT-CHECKED-HERE.

Usage:  python3 scripts/check_terminology.py            # -> docs/TERMINOLOGY-CHECK.md
        python3 scripts/check_terminology.py --tx URL   # alt terminology server
Network: needs the tx server (default https://tx.fhir.org/r4). Results cached in
scripts/.tx_cache.json so re-runs are offline for already-seen codes.
"""
import csv, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = Path("/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/schemas")
CSVS = ["mapping_kdk_oncology.csv", "mapping_kdk_rarediseases.csv", "mapping_grz.csv"]
TX = "https://tx.fhir.org/r4"
CACHE = ROOT / "scripts" / ".tx_cache.json"

LOINC = "http://loinc.org"
SNOMED = "http://snomed.info/sct"
CATCHALL = {"unknown", "other", "none", "notavailable", "na", "not_available",
            "yesbutstudyisunknown", "notdetermined", "notassessed"}
# systems tx.fhir.org (LOINC/SNOMED) cannot resolve — flagged, not failed
UNCHECKED_SYS = ["ICD-10-GM", "ICD-O-3", "OPS", "ATC", "Orpha", "ORPHA", "Alpha-ID",
                 "AlphaID", "HPO", "HGNC", "SO:", "UICC", "NCIt", "genomde.de"]

_cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}


def tx_lookup(system, code):
    """Return (exists: bool, display: str|None). Cached."""
    key = f"lookup|{system}|{code}"
    if key in _cache:
        e, d = _cache[key]; return e, d
    url = f"{TX}/CodeSystem/$lookup?" + urllib.parse.urlencode({"system": system, "code": code})
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/fhir+json"})
        d = json.load(urllib.request.urlopen(req, timeout=25))
        if d.get("resourceType") == "Parameters":
            disp = next((p.get("valueString") for p in d.get("parameter", []) if p.get("name") == "display"), None)
            res = (True, disp)
        else:                                   # OperationOutcome => not found
            res = (False, None)
    except urllib.error.HTTPError:
        res = (False, None)                     # 404/400 => code not valid
    except Exception as e:
        res = (None, f"tx-error: {e}")          # network problem — don't cache
        return res
    _cache[key] = res; CACHE.write_text(json.dumps(_cache)); time.sleep(0.1)
    return res


def tx_expand_ll(ll):
    """Expand a LOINC answer list LLxxxx-x -> {code: display}. Cached."""
    key = f"expand|{ll}"
    if key in _cache:
        return _cache[key]
    url = f"{TX}/ValueSet/$expand?" + urllib.parse.urlencode({"url": f"http://loinc.org/vs/{ll}"})
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/fhir+json"})
        d = json.load(urllib.request.urlopen(req, timeout=25))
        out = {c["code"]: c.get("display", "") for c in d.get("expansion", {}).get("contains", [])}
    except Exception:
        out = {}
    _cache[key] = out; CACHE.write_text(json.dumps(_cache))
    return out


CODE_PATTERNS = [
    ("loinc-answer", re.compile(r"\bLA\d{3,7}-\d\b")),
    ("loinc-answerlist", re.compile(r"\bLL\d{3,7}-\d\b")),
    ("loinc", re.compile(r"\b\d{4,7}-\d\b")),
]
STOP = set("the a an of in by for and or to with is are code system value profile mii onko mtb".split())
# domain synonyms: a genomDE field name -> concepts its correct LOINC/SNOMED display may use
# (literal token overlap misses synonyms like zygosity==allelic state, vitalStatus==disposition)
SYN = {
    "zygosity": {"allelic", "allele", "state"},
    "dnachange": {"dna", "hgvs", "change"}, "proteinchange": {"amino", "acid", "protein", "hgvs"},
    "vitalstatus": {"patient", "disposition", "vital", "deceased", "alive"},
    "ref": {"reference", "allele", "genomic"}, "alt": {"alternate", "allele", "genomic"},
    "gmfcs": {"motor", "gross", "function", "phenx"},
    "acmgclass": {"clinical", "significance", "pathogenic", "benign", "variation"},
    "genomicsource": {"germline", "somatic", "source"},
    "modeofinheritance": {"inheritance", "autosomal", "dominant", "recessive", "linked", "pattern"},
    "transcriptid": {"transcript", "reference", "sequence"}, "gene": {"gene", "studied"},
    "endposition": {"genomic", "allele", "start", "end"}, "startposition": {"genomic", "allele", "start", "end"},
    "referencegenome": {"grch", "genome", "reference", "build"},
    "expressiontype": {"expression", "rnaseq"},          # 82122-3/69548-6 legitimately fail -> flagged
    "ploidy": {"ploidy"},                                  # 81303-0 'HGVS version' fails -> flagged
    "hrdhigh": {"homologous", "recombination", "deficiency", "hrd"},  # 94195-5 CPT2 fails -> flagged
    "therapyresponse": {"regression", "tumour", "tumor", "response", "disease"},
}


SUBFIELDS = {"code", "display", "system", "version", "text", "value"}


def concept_tokens(row):
    """Keywords describing what this row is meant to encode (camel-split field + description + synonyms).
    For structural sub-fields (.code/.display/…) use the PARENT segment as the concept."""
    segs = [s.replace("[]", "") for s in row["path"].split(".")]
    tail = segs[-2] if segs[-1].lower() in SUBFIELDS and len(segs) > 1 else segs[-1]
    key = tail.lower()
    txt = re.sub(r"([a-z])([A-Z])", r"\1 \2", tail).lower() + " " + (row.get("description") or "").lower()
    toks = {w for w in re.findall(r"[a-z]{3,}", txt) if w not in STOP}
    syn = set().union(*[v for k, v in SYN.items() if k in key or key in k]) if any(k in key or key in k for k in SYN) else set()
    return toks | syn


def load_rows():
    rows = []
    for fn in CSVS:
        for r in csv.DictReader(open(ROOT / "mapping" / fn, newline="")):
            r["_tab"] = fn.replace("mapping_kdk_", "").replace("mapping_", "").replace(".csv", "")
            rows.append(r)
    return rows


# a code near one of these markers (either side) is a "we rejected/are unsure of this" note, not the active code
REJECT_CTX = re.compile(r"(was|wrong|reject|invalid|prior|does not|do not|not exist|deprecated|"
                        r"instead of|confirm|also not|not expression|no fixed)", re.I)


def _rejected(blob, start, end):
    return bool(REJECT_CTX.search(blob[max(0, start - 34):start]) or REJECT_CTX.search(blob[end:end + 40]))


def extract_codes(rows):
    """(system,code,kind) -> rows citing it. Skips codes documented as rejected ('was X', 'X is WRONG')."""
    hits = {}
    for r in rows:
        blob = " ".join(str(r.get(c) or "") for c in ("transform", "fhir_element", "reference", "mii_profile"))
        seen = set()
        for kind, pat in CODE_PATTERNS:
            for m in pat.finditer(blob):
                code = m.group()
                if code in seen or _rejected(blob, m.start(), m.end()):   # dup, or a rejected-code note
                    continue
                seen.add(code)
                hits.setdefault((LOINC, code, kind), []).append(r)
        if "SNOMED" in blob.upper():
            for m in re.finditer(r"\b\d{6,18}\b", blob):
                if not _rejected(blob, m.start(), m.end()):
                    hits.setdefault((SNOMED, m.group(), "snomed"), []).append(r)
    return hits


def main():
    global TX
    if "--tx" in sys.argv:
        TX = sys.argv[sys.argv.index("--tx") + 1]
    rows = load_rows()
    hits = extract_codes(rows)
    print(f"checking {len(hits)} distinct coded values across {len(rows)} rows via {TX} …", file=sys.stderr)

    invalid, mismatch, ok, neterr = [], [], [], []
    answers = {}     # field-path -> list of (code, display|INVALID) for answer codes/lists
    for (system, code, kind), rws in sorted(hits.items(), key=lambda x: (x[0][0], x[0][1])):
        exists, disp = tx_lookup(system, code)
        ctx = sorted({r["path"] for r in rws})
        if exists is None:
            neterr.append((system, code, disp, ctx)); continue
        is_answer = kind in ("loinc-answer", "loinc-answerlist")
        if not exists:
            invalid.append((system, code, kind, ctx))
            if is_answer:
                for p in ctx: answers.setdefault(p, []).append((code, "❌ INVALID"))
            continue
        if is_answer:      # answer values: existence-checked + rostered per field (not concept-matched)
            for p in ctx: answers.setdefault(p, []).append((code, disp))
            ok.append((system, code, disp, ctx)); continue
        # concept codes (Observation.code-level LOINC/SNOMED): does display overlap the field concept?
        dt = {w for w in re.findall(r"[a-z]{3,}", (disp or "").lower())}
        flagged = [r["path"] for r in rws if concept_tokens(r) and dt and not (concept_tokens(r) & dt)]
        if flagged:
            mismatch.append((system, code, disp, sorted(set(flagged))))
        else:
            ok.append((system, code, disp, ctx))

    # DK enum coverage
    import glob
    enum_fields = []
    for f in glob.glob(str(SCHEMA) + "/**/*.json", recursive=True):
        try: d = json.load(open(f))
        except Exception: continue
        def walk(o, path=""):
            if isinstance(o, dict):
                if isinstance(o.get("enum"), list):
                    enum_fields.append((path, o["enum"]))
                for k, v in o.items(): walk(v, path + "/" + k)
            elif isinstance(o, list):
                for x in o: walk(x, path)
        walk(d)
    catchall_fields = []
    for path, vals in enum_fields:
        ca = [v for v in vals if str(v).lower() in CATCHALL]
        if ca:
            catchall_fields.append((path.split("/properties/")[-1] if "/properties/" in path else path, vals, ca))

    # ---- report ----
    L = []
    L.append("# Terminology / coded-value check of the genomDE→MII mapping\n")
    L.append(f"Automated re-run of the NUM-OMICS review via `{TX}` (LOINC+SNOMED $lookup/$expand). "
             f"Checked **{len(hits)}** distinct coded values.\n")
    L.append(f"- INVALID (code does not exist): **{len(invalid)}**")
    L.append(f"- MISMATCH (display unrelated to the mapped concept): **{len(mismatch)}**")
    L.append(f"- OK (exists, display consistent): **{len(ok)}**")
    if neterr: L.append(f"- tx errors (re-run): {len(neterr)}")
    L.append("")
    L.append("## ❌ INVALID codes (do not exist)\n")
    L.append("| system | code | cited for |\n|---|---|---|")
    for s, c, k, ctx in invalid:
        L.append(f"| {s.split('/')[-1]} | `{c}` | {', '.join(ctx)[:90]} |")
    L.append("\n## ⚠️ MISMATCH — official display unrelated to the mapped field\n")
    L.append("| code | official display | cited for (suspect) |\n|---|---|---|")
    for s, c, disp, ctx in mismatch:
        L.append(f"| `{c}` | {disp} | {', '.join(ctx)[:80]} |")
    L.append("\n## 🔎 Answer-code roster (per field — eyeball for a rogue value)\n")
    L.append("Answer codes exist in LOINC (else marked INVALID above); their *display* is shown next to "
             "the field so a wrong-but-valid code stands out (e.g. an anatomy term among inheritance modes):\n")
    for p in sorted(answers):
        vals = "; ".join(f"`{c}`={d}" for c, d in answers[p])
        L.append(f"- **{p}** — {vals}")
    L.append(f"\n## ✅ Verified consistent ({len(ok)})\n")
    L.append("<details><summary>expand</summary>\n\n| code | display |\n|---|---|")
    for s, c, disp, ctx in ok:
        L.append(f"| `{c}` | {disp} |")
    L.append("\n</details>\n")
    L.append("## DK enum values with no clinical code → need STRUCTURAL mapping\n")
    L.append("Catch-all values (`unknown/other/none/notAvailable/…`) have no equivalent target concept; "
             "map them structurally, not to an invented code:\n")
    L.append("| policy | genomDE value | FHIR target |")
    L.append("|---|---|---|")
    L.append("| absence-of-value | `unknown`, `notAvailable` | `dataAbsentReason` = unknown / asked-unknown (Observation) or nullFlavor `UNK`; omit `value[x]` |")
    L.append("| free / uncoded | `other` | `.text` only, or a genomDE local CodeSystem concept; never force a wrong standard code |")
    L.append("| genuine negative | `none` | a real code where one exists (e.g. SNOMED 'none'/260413007) else dataAbsentReason |")
    L.append("| partial admin | `yesButStudyIsUnknown` | keep the boolean/flag; reference resource absent → `.display` note |")
    L.append("")
    L.append(f"Fields carrying such values ({len(catchall_fields)}):\n")
    L.append("| field | catch-all value(s) |\n|---|---|")
    for name, vals, ca in sorted(catchall_fields):
        L.append(f"| `{name}` | {', '.join(map(str, ca))} |")
    if neterr:
        L.append("\n## tx errors (re-run to resolve)\n")
        for s, c, msg, ctx in neterr: L.append(f"- {c}: {msg}")
    L.append("\n## Not checked here (not on tx.fhir.org)\n")
    L.append("LOINC + SNOMED are verified above. These systems need a German/OBO terminology "
             "server (BfArM TermServ, OLS) — verify separately: **" + ", ".join(UNCHECKED_SYS[:-1]) + "**.")
    out = ROOT / "docs" / "TERMINOLOGY-CHECK.md"
    out.write_text("\n".join(L) + "\n")
    print(f"\nINVALID={len(invalid)} MISMATCH={len(mismatch)} OK={len(ok)} neterr={len(neterr)}", file=sys.stderr)
    print(f"catch-all enum fields={len(catchall_fields)}", file=sys.stderr)
    print(f"wrote {out}", file=sys.stderr)
    # console summary of the actionable finds
    for s, c, k, ctx in invalid: print(f"INVALID  {c:12} cited for {ctx[0] if ctx else ''}")
    for s, c, disp, ctx in mismatch: print(f"MISMATCH {c:12} = {disp[:45]!r} cited for {ctx[0]}")


if __name__ == "__main__":
    main()
