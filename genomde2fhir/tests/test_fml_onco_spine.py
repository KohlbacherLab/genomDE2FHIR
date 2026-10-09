"""FML stage 'onco_spine': mappers/fml/DatenkranzOncologyToMii.map (with the OncoMolecular / OncoPlanFollowUp stubs).

Skipped unless MB2027 (matchbox-2027 base URL) is set; HAPI2027 defaults to http://localhost:8092/fhir.
For 3 oncology files: push the maps, $transform -> Bundle, zero content errors, graph-aware parity with the Python
converter on the resources the spine emits, and an idempotent double ingest into HAPI.

Spine resources (Python builders patient, coverage, consent, research_consent, submission, onco.diagnosis, onco.tnm,
onco.ecog, onco.prior_procedures, onco.prior_diagnostics) are selected from both bundles with the same function, by
profile and by graph (prior-diagnostics reports = the episode's supportingInfo, their studies / analyses / variants;
MedicationStatements and therapy responses partOf a prior therapy; the diagnosis ECOG by its Python id or its FML
resource key). Normalised away on both sides: Patient.deceased[x] (follow-up stage), ClinicalImpression.investigation
(molecular stage), an empty identifier list (resource key only).

Wide run:  MB2027=http://localhost:8091/matchboxv3/fhir python genomde2fhir/tests/test_fml_onco_spine.py --n 30
"""
import base64
import collections
import importlib.util
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "genomde2fhir" / "src"))
from genomde2fhir.convert import convert  # noqa: E402
from genomde2fhir.identity import case_key  # noqa: E402
from genomde2fhir.validate import Hapi, Matchbox, validate_bundle  # noqa: E402

MB = os.environ.get("MB2027")
HAPI = os.environ.get("HAPI2027", "http://localhost:8092/fhir")
MAP = "https://genomde.de/fhir/StructureMap/DatenkranzOncologyToMii"
FILES = [  # ukdd (TNM as weitere-klassifikationen, research-consent-absent), DNPM (UICC TNM, embedded Broad Consent,
           # legacy priorDiagnostic), NCT (SNOMED TNM, prior variants)
    "example-data/synthData-v1/ukdd/synth_json_1.json",
    "example-data/oncology/OncologySubmission_044AFF6262356F2F8EC60039DC08AE36FBAA011DE29740CBC83E9FA5643E4640.json",
    "example-data/synthData-v1/nct/case_011.json",
]

SPINE_PROFILES = {
    "PatientPseudonymisiert", "coverage-de-basis", "mvgs-consent", "mii-pr-consent-einwilligung", "mvgs-research-consent-absent",
    "mvgs-inclusion-decision", "mii-pr-mtb-diagnose-primaertumor", "Diagnose", "mii-pr-onko-grading",
    "mii-pr-seltene-hpo-assessment", "mii-pr-onko-weitere-klassifikationen", "mii-pr-onko-tnm-klassifikation",
    "mii-pr-onko-tnm-t-kategorie", "mii-pr-onko-tnm-n-kategorie", "mii-pr-onko-tnm-m-kategorie", "anforderung-genetischer-test",
    "mii-pr-mtb-behandlungsepisode", "mii-pr-mtb-systemische-vortherapie",
}
ASSESSMENT_CS = "https://genomde.de/fhir/CodeSystem/mvgs-cs-genetic-diagnostic-assessment"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _profile(r):
    return (r.get("meta", {}).get("profile") or [""])[0].split("/")[-1]


def _refs(o):
    """All reference strings inside an element."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "reference" and isinstance(v, str):
                yield v
            else:
                yield from _refs(v)
    elif isinstance(o, list):
        for x in o:
            yield from _refs(x)


def _fml_key(dk: dict, role: str) -> str:
    """FML resource-key identifier value of a role (mappers/fml/README.md: base64url of '<case key>:<role>')."""
    md = dk.get("metaData") or {}
    ck = f"kdk:{(md.get('submission') or {}).get('submitterId', '')}:{md.get('localCaseId') or md.get('tanC', '')}"
    return base64.urlsafe_b64encode(f"{ck}:{role}".encode()).decode()


def spine_entries(bundle: dict, dk: dict) -> list:
    """Entries of the resources the spine map emits; applied to the Python and to the FML bundle alike."""
    ecog_id = case_key(dk, "oncology").id("Observation", "ecog", "diagnosis")
    ecog_key = _fml_key(dk, "ecog:diagnosis")
    by_url = {e["fullUrl"]: e for e in bundle.get("entry", [])}
    mine = set()
    for url, e in by_url.items():
        r = e["resource"]
        p = _profile(r)
        ecog = r["resourceType"] == "Observation" and (r.get("id") == ecog_id or any(
            i.get("value") == ecog_key for i in r.get("identifier", []) if "resource-key" in i.get("system", "")))
        if p in SPINE_PROFILES or ecog or \
                any(c.get("system") == ASSESSMENT_CS for c in r.get("code", {}).get("coding", [])):
            mine.add(url)
    for url, e in by_url.items():
        r = e["resource"]
        if _profile(r) == "mii-pr-mtb-behandlungsepisode":
            mine.update(set(_refs(r.get("supportingInfo", []))) & set(by_url))     # prior therapies + prior reports
    for url in list(mine):
        r = by_url[url]["resource"]
        if r["resourceType"] == "DiagnosticReport":
            mine.update(set(_refs(r.get("result", []))) & set(by_url))
            mine.update(set(_refs(r.get("extension", []))) & set(by_url))          # genomic study
    for url in list(mine):
        r = by_url[url]["resource"]
        if _profile(r) == "mii-pr-mtb-genomic-study":
            mine.update(set(_refs(r.get("extension", []))) & set(by_url))          # analysis
    vortherapie = {u for u in mine if _profile(by_url[u]["resource"]) == "mii-pr-mtb-systemische-vortherapie"}
    for url, e in by_url.items():
        if set(_refs(e["resource"].get("partOf", []))) & vortherapie:
            mine.add(url)                                                          # medication statements, responses
    return [e for u, e in by_url.items() if u in mine]


def parity(py_bundle: dict, fml_bundle: dict, dk: dict):
    """(equal, only-python, only-fml) multisets of canonical spine resources (spine_entries() on both bundles).
    Normalised on both sides: Patient.deceased[x] (follow-up stage), ClinicalImpression.investigation (molecular stage),
    an empty identifier list (resource key only)."""
    canonical = _load("run_corpus", REPO / "scripts" / "run_corpus.py").canonical

    def sub(entries):
        out = collections.Counter()
        for k, v in canonical({"entry": entries}).items():
            r = json.loads(k)
            if r.get("identifier") == []:
                r.pop("identifier")
            if r["resourceType"] == "Patient":
                r.pop("deceasedDateTime", None)
                r.pop("deceasedBoolean", None)
            if r["resourceType"] == "ClinicalImpression":
                r.pop("investigation", None)
            out[json.dumps(r, sort_keys=True)] += v
        return out
    p, f = sub(spine_entries(py_bundle, dk)), sub(spine_entries(fml_bundle, dk))
    return p & f, p - f, f - p


def push_maps(base: str) -> int:
    return _load("build_mvgs", REPO / "scripts" / "build_mvgs.py").push_maps(base)


def hapi_count(rtype: str) -> int:
    req = urllib.request.Request(f"{HAPI}/{rtype}?_summary=count", headers={"Cache-Control": "no-cache",
                                                                           "Accept": "application/fhir+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["total"]


def ingest_twice(bundle: dict) -> dict:
    hapi = Hapi(HAPI)
    types = sorted({e["resource"]["resourceType"] for e in bundle["entry"]})
    out = {}
    for run in (1, 2):
        before = {t: hapi_count(t) for t in types}
        ok, resp = hapi.transaction(bundle)
        after = {t: hapi_count(t) for t in types}
        statuses = collections.Counter(str((e.get("response") or {}).get("status", "")).split(" ")[0]
                                       for e in resp.get("entry", []))
        out[run] = {"ok": ok, "statuses": dict(statuses), "new": sum(after[t] - before[t] for t in types),
                    "error": None if ok else json.dumps(resp)[:300]}
    return out


def _brief(k: str) -> str:
    r = json.loads(k)
    return f"{r['resourceType']}: {k[:600]}"


def check_file(f: str, mb: Matchbox, ingest: bool = True, dk: dict | None = None, label: str | None = None) -> dict:
    mutated = dk is not None          # mutated inputs are converted without the schema gate (as in test_fml_common)
    dk = dk if mutated else json.loads((REPO / f).read_text(encoding="utf-8"))
    py, rep = convert(dk, f, check_input=not mutated)
    st, fml = mb.transform(dk, MAP)
    res = {"file": label or f, "python": rep.status, "http": st, "type": fml.get("resourceType")}
    if py is None or fml.get("resourceType") != "Bundle":
        res["error"] = json.dumps(fml)[:600]
        return res
    res["entries"] = len(fml.get("entry", []))
    # same classifier for both sides (source=dk: an unknown code copied verbatim from the input is data quality)
    v = validate_bundle(fml, mb, source=dk)
    res["content_errors"] = [f"{r['type']}/{r['profile']}: {i['expression']} :: {i['text'][:200]}"
                             for r in v["resources"] for i in r["issues"] if i["class"] == "content"]
    if res["content_errors"]:        # compare with the Python output of the same file (whole bundle, like the FML side)
        vp = validate_bundle(py, mb, source=dk)
        def errs(val):     # entry uuids differ between the two bundles
            return collections.Counter(f"{r['type']}/{r['profile']}: " + re.sub(r"urn:uuid:[0-9a-f-]{36}", "urn:uuid:*", i["text"][:200])
                                       for r in val["resources"] for i in r["issues"] if i["class"] == "content")
        py_errs, fml_errs = errs(vp), errs(v)
        res["python_content_errors"] = sorted(py_errs.elements())
        res["content_errors_not_in_python"] = sorted((fml_errs - py_errs).elements())
    else:
        res["python_content_errors"], res["content_errors_not_in_python"] = [], []
    eq, only_py, only_fml = parity(py, fml, dk)
    res.update(equal=sum(eq.values()), only_python=sorted(only_py.elements()), only_fml=sorted(only_fml.elements()))
    if ingest:
        res["ingest"] = ingest_twice(fml)
    return res


# ---- pytest ------------------------------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(not MB, reason="MB2027 not set (matchbox-2027 base URL)")

def _dx(dk):
    return dk["case"]["diagnosisOd"]


def _set(d, **kw):
    d.update(kw)
    return d


SCT_V = "http://snomed.info/sct/900000000000207008/version/20250201"
# Edge cases the corpus lacks, applied to FILES[2] (NCT; Python converts them with check_input=False)
MUTATIONS = {
    "tnm-prefixes-mixed": lambda dk: _set(_dx(dk), tnmClassifications=[
        {"system": "UICC", "code": "T2", "display": "ypT2", "version": "8th ed."},
        {"system": "UICC", "code": "N1", "display": "uN1", "text": "rN1", "version": "7. Auflage"},
        {"system": "http://snomed.info/sct", "code": "1229893007", "display": "ycM1a", "version": SCT_V},
        {"system": "http://snomed.info/sct", "code": "M0", "display": "M0", "version": "x"},
        {"system": "http://snomed.info/sct", "code": "999999", "display": "pT9", "version": SCT_V},
        {"system": "AJCC", "code": "T9", "version": "8th ed."}]),
    "tnm-clinical-one-edition": lambda dk: _set(_dx(dk), tnmClassifications=[
        {"system": "UICC", "code": "T1", "display": "cT1", "version": "8th ed."},
        {"system": "UICC", "code": "N0", "display": "cN0", "version": " 8 Aufl."}]),
    "icdo3-duplicate-topography": lambda dk: _set(_dx(dk), histology={"code": "C34.1", "system": "ICD-O-3", "version": "2019"},
                                                  topography={"code": "c341", "system": "ICD-O-3", "version": "Erste Revision"}),
    "icdo3-junk-and-swap": lambda dk: _set(_dx(dk), histology={"code": "xyz", "system": "foo", "version": "9", "display": "Junk"},
                                           topography={"code": "M8140/3", "system": "ICD-O3-T", "version": "3.1"}),
    "icdo3-two-morphologies": lambda dk: _set(_dx(dk), histology={"code": "M8140/3", "system": "ICD-O-3", "version": "2019"},
                                              topography={"code": "8500/3", "system": "ICD-O-3", "version": "2019", "display": "Duct"}),
    "icd-marks-and-dots": lambda dk: (_set(_dx(dk)["mainDiagnosis"], code="c34.1+", system="http://fhir.de/CodeSystem/dimdi/icd-10-gm",
                                           display="Lunge"),
                                      _set(_dx(dk), additionalDiagnoses=[
                                          {"code": "E1190*", "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "version": "2025", "date": "2020-01-01"},
                                          {"code": "orpha:558", "system": "http://www.orpha.net/", "version": "1"},
                                          {"code": "123", "system": "http://example.org/cs", "version": "1"}],
                                           germlineDiagnoses=[{"code": "I1234", "system": "https://www.alpha-id.de", "version": "2025"}],
                                           germlineDiagnosisConfirmed=True)),
    "no-primary": lambda dk: _set(_dx(dk)["mainDiagnosis"], code=""),
    "ecog-unknown": lambda dk: _set(_dx(dk), ecogPerformanceStatusScore="unknown"),
    "ecog-5": lambda dk: _set(_dx(dk), ecogPerformanceStatusScore="5"),
    "diagnosis-satellites": lambda dk: _set(_dx(dk), grading="3", diagnosticAssessment="partialGeneticDiagnosis", libraryType="wgs_lr",
                                            additionalClassification=[{"system": "Ann Arbor", "key": "IIA"}, {"system": "X"}, {"key": "orphan"},
                                                                      {"system": "dnpm-dip/mtb/diagnosis/kds-tumor-spread", "key": "local"}],
                                            hpoTerms=[{"code": "HP:0001250", "text": "Seizure"}, {"code": "", "display": "x"},
                                                      {"code": "HP:0000001", "system": "http://human-phenotype-ontology.org", "version": "2025", "display": "All"}]),
    "unknown-codes": lambda dk: (_set(_dx(dk), diagnosticAssessment="xyz", libraryType="foo", ecogPerformanceStatusScore="notApplicable"),
                                 _set(dk["metaData"], researchConsents=[{"presentationDate": "2024-01-01", "noScopeJustification": "foo"},
                                                                       {"presentationDate": "2024-02-01", "noScopeJustification": "patient unable to consent"}])),
    "prior-procedures-edge": lambda dk: _set(dk["case"], priorProcedures=[
        {"treatmentType": "Z", "therapyStartDate": "2021-01-01", "terminationReasonOBDS": "Q", "therapyResponse": "PR",
         "therapyResponseDate": "2021-06-01", "substances": [{"name": "Foo"}, {"code": {"system": "http://www.whocc.no/atc/", "code": "L01XC",
                                                                                         "version": "2024", "display": "mAbs"}, "name": "Bar"}]},
        {"treatmentType": "A", "intention": "P", "therapyStartDate": "2022-01-01", "therapyEndDate": "2022-05-01", "terminationReasonOBDS": "V",
         "substances": [{"code": {"system": "https://www.wido.de/publikationen-produkte/analytik/arzneimittel-klassifikation/", "code": "L01BC02", "version": "2025"}}]},
        {"treatmentType": "O", "intention": "K", "therapyStartDate": "2023-01-01", "therapyResponse": "XX"}]),
    "prior-diagnostics-edge": lambda dk: _set(dk["case"], priorDiagnostics=[
        {"type": "panel", "date": "2023-03-03", "complexVariants": ["complex 1", "", "complex 2"], "simpleVariants": [
            {"gene": {"code": "HGNC:7989", "display": "NRAS", "system": "http://www.genenames.org"},
             "transcript": {"code": "NM_002524", "version": "5", "system": "https://www.ncbi.nlm.nih.gov/refseq"},
             "dnaChange": "c.181C>A", "proteinChange": "p.Gln61Lys",
             "variantTypes": [{"system": "http://www.sequenceontology.org", "code": "SO:0001583", "version": "2024", "display": "missense"},
                              {"system": "x", "code": "SO:0001819", "version": "1"}]},
            {"gene": {"code": "", "display": "TP53"}, "transcript": {"code": "ENST00000269305.9", "system": "Ensembl"},
             "dnaChange": "n.100A>G", "proteinChange": "p.Arg1Ter"}]},
        {"type": "none", "complexVariants": ["only complex"]},
        {"type": "none", "date": "2020-01-01"},
        {"type": "exome", "date": "2019-01-01"},
        {"type": "genomeLongRead"}]),
}


@pytest.fixture(scope="module")
def mb():
    m = Matchbox(MB)
    assert push_maps(MB) == 0, "pushing the FML maps failed"
    return m


@pytest.mark.parametrize("f", FILES)
def test_onco_spine(mb, f):
    if not (REPO / f).is_file():
        pytest.skip(f"{f} not in this checkout")
    r = check_file(f, mb)
    assert r["type"] == "Bundle", r
    assert r["content_errors_not_in_python"] == [], r["content_errors"]
    assert r["only_python"] == [] and r["only_fml"] == [], ([_brief(k) for k in r["only_python"]], [_brief(k) for k in r["only_fml"]])
    assert r["equal"] >= 10
    first, second = r["ingest"][1], r["ingest"][2]
    assert first["ok"] and second["ok"], r["ingest"]
    assert second["new"] == 0 and set(second["statuses"]) == {"200"}, r["ingest"]


@pytest.mark.parametrize("mutation", sorted(MUTATIONS))
def test_onco_spine_edge_cases(mb, mutation):
    f = FILES[2]
    if not (REPO / f).is_file():
        pytest.skip(f"{f} not in this checkout")
    dk = json.loads((REPO / f).read_text(encoding="utf-8"))
    MUTATIONS[mutation](dk)
    r = check_file(f, mb, ingest=False, dk=dk, label=f"{f} [{mutation}]")
    assert r["type"] == "Bundle", r
    assert r["content_errors_not_in_python"] == [], r["content_errors"]
    assert r["only_python"] == [] and r["only_fml"] == [], ([_brief(k) for k in r["only_python"]], [_brief(k) for k in r["only_fml"]])


# ---- wide corpus run ---------------------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="files, spread over the oncology manifest")
    ap.add_argument("--ingest", type=int, default=5, help="files ingested twice into HAPI")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not MB:
        sys.exit("set MB2027")
    mbx = Matchbox(MB)
    print("push failures:", push_maps(MB))
    manifest = json.loads((REPO / "genomde2fhir" / "tests" / "corpus_manifest.json").read_text())
    spread = _load("run_corpus", REPO / "scripts" / "run_corpus.py").spread
    results, tot = [], collections.Counter()
    for i, f in enumerate(spread(manifest["oncology"]["valid"], a.n)):
        r = check_file(f, mbx, ingest=i < a.ingest)
        results.append(r)
        tot["files"] += 1
        tot["bundles"] += r["type"] == "Bundle"
        tot["content_errors"] += len(r.get("content_errors", []))
        tot["content_errors_not_in_python"] += len(r.get("content_errors_not_in_python", []))
        tot["equal"] += r.get("equal", 0)
        tot["only_python"] += len(r.get("only_python", []))
        tot["only_fml"] += len(r.get("only_fml", []))
        if "ingest" in r:
            tot["ingested"] += 1
            tot["ingest_ok"] += r["ingest"][1]["ok"] and r["ingest"][2]["ok"] and r["ingest"][2]["new"] == 0
        print(f"{r['file'][-60:]:60} {r['type']:16} errors={len(r.get('content_errors', []))} eq={r.get('equal')} "
              f"py-only={len(r.get('only_python', []))} fml-only={len(r.get('only_fml', []))}"
              + (f" ingest={r['ingest'][1]['statuses']}/{r['ingest'][2]['statuses']} new2={r['ingest'][2]['new']}" if "ingest" in r else ""))
    print(dict(tot))
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1))
