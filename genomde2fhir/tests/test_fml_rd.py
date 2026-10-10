"""FML stage 'rd': mappers/fml/DatenkranzRareDiseaseToMii.map (imports DatenkranzCommon).

Skipped unless MB2027 (matchbox-2027 base URL) is set; HAPI2027 defaults to http://localhost:8092/fhir.
For 3 rare-disease files (one per sub-corpus) and a set of edge-case mutations: push the maps, $transform -> Bundle,
zero content errors (validate_bundle) and graph-aware parity with the Python converter (canonical() from
scripts/run_corpus.py); for the 3 files also an idempotent double ingest into HAPI.

Input shape. matchbox drops every property the logical model DatenkranzRareDisease does not declare when it parses
the input (quirk Q6). The non-schema keys of the corpus that Python reads (the pre-1.6.5 keys case.priorRd and
plan.recommended*[].variantReferences, genes[].display, the embedded Broad Consent researchConsents[].scope) are
declared as extras of the logical model (scripts/schema_to_logical.py EXTRAS), so the corpus files are compared raw.
The edge-case mutations are applied to the *declared shape* of FILES[0] (declared_shape(): legacy keys renamed to the
schema names, undeclared properties removed), the input the mutations are written for.

Wide run:  MB2027=http://localhost:8091/matchboxv3/fhir python genomde2fhir/tests/test_fml_rd.py --n 42 [--declared]
"""
import collections
import copy
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
from genomde2fhir.validate import Hapi, Matchbox, validate_bundle  # noqa: E402

MB = os.environ.get("MB2027")
HAPI = os.environ.get("HAPI2027", "http://localhost:8092/fhir")
MAP_URL = "https://genomde.de/fhir/StructureMap/DatenkranzRareDiseaseToMii"
MAPS = ["DatenkranzCommon.map", "DatenkranzRareDiseaseToMii.map"]
FILES = [
    "example-data/rarediseases/RareDiseasesSubmission_06B1EE824EDF30E43FAA6FF4DCFC5E00FD9A772ACCE0E4AD0BC593F6834F6566.json",
    "example-data/rarediseases/RareDiseasesSubmission_9CCF7812F458C024A5D35754087C22A48E935AC16BA0056C61CE3F8A9CE846F3.json",
    "examples/rarediseases/RareDiseasesSubmission_4B8581EA6277B9C60B04DD2304B40ED1C57B886FAD33E28C3C6575A76CCE248F.json",
]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_SD = json.loads((REPO / "mvgs-ig/input/StructureDefinition-DatenkranzRareDisease.json").read_text())
DECLARED = {e["path"].split(".", 1)[1]: e["type"][0]["code"] for e in _SD["differential"]["element"] if "." in e["path"]}
LOGICAL = {"BackboneElement", "string", "integer", "decimal", "boolean"}   # else a FHIR datatype (extras): kept whole


def declared_shape(dk: dict) -> dict:
    """The input as matchbox sees it once the logical model declares the schema keys: case.priorRd -> priorRds,
    variantReferences -> variants, every property the logical model does not declare removed."""
    dk = copy.deepcopy(dk)
    case = dk.get("case") or {}
    if "priorRd" in case and "priorRds" not in case:
        v = case.pop("priorRd")
        case["priorRds"] = v if isinstance(v, list) else [v]
    for k in ("recommendedTherapies", "recommendedStudies"):
        for r in (dk.get("plan") or {}).get(k) or []:
            if "variantReferences" in r and "variants" not in r:
                r["variants"] = r.pop("variantReferences")

    def walk(o, p):
        if isinstance(o, dict):
            for k in list(o):
                q = f"{p}.{k}" if p else k
                if q not in DECLARED:
                    o.pop(k)
                    continue
                if DECLARED[q] in LOGICAL:
                    walk(o[k], q)
        elif isinstance(o, list):
            for x in o:
                walk(x, p)
    walk(dk, "")
    return dk


def parity(py_bundle: dict, fml_bundle: dict):
    """(equal, only-python, only-fml) multisets of canonical resources."""
    canonical = _load("run_corpus", REPO / "scripts" / "run_corpus.py").canonical

    def sub(b):
        out = collections.Counter()
        for k, v in canonical(b).items():
            r = json.loads(k)
            if r.get("identifier") == []:    # harmless no-op: canonical() omits an emptied identifier list
                r.pop("identifier")
            out[json.dumps(r, sort_keys=True)] += v
        return out
    p, f = sub(py_bundle), sub(fml_bundle)
    return p & f, p - f, f - p


def push_maps(base: str) -> int:
    build = _load("build_mvgs", REPO / "scripts" / "build_mvgs.py")
    bad = 0
    for m in build.map_files():
        if m.name in MAPS:
            st, body = build._send("POST", f"{base.rstrip('/')}/StructureMap", m.read_bytes(), "text/fhir-mapping")
            bad += st >= 300
    return bad


def hapi_count(rtype: str) -> int:
    """Uncached total (HAPI caches _summary=count searches)."""
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


# ---- edge cases the corpus lacks (applied to the declared shape of FILES[0]; Python runs with check_input=False) ----
def _dx(dk):
    return dk["case"]["diagnosisRd"]


def _fu(dk):
    return dk["followUp"]["followUpRds"]


def _var(dk, kind="smallVariants", i=0):
    return dk["molecular"][kind][i]


def _set(d, **kw):
    d.update(kw)
    return d


def _drop(d, *keys):
    for k in keys:
        d.pop(k, None)
    return d


def _m_dx_codes(dk):
    _dx(dk)["diagnoses"] = [
        {"code": "e1190+", "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm/", "version": "2026", "display": "D"},
        {"code": "G35", "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "version": "2026"},
        {"code": "orpha:558", "system": "http://www.orpha.net", "version": "4.7"},
        {"code": "I1234", "system": "http://fhir.de/CodeSystem/bfarm/alpha-id", "version": "2025", "display": "A"},
        {"code": "Q87.4", "system": "http://example.org/other", "display": "x"},
        {"code": "", "system": "http://www.orpha.net"}]


def _m_variants(dk):
    v = _var(dk)
    v.update(chromosome="X", externalId="VCV000012345.1", cdnaChange="c.123_124delinsA^G", gdnaChange="no hgvs",
             proteinChange=" p.Arg12Cys ", acmgCriteria=[{"value": "PS1", "modifier": "xx"}, {"value": "PM2"}],
             publications=["PMID: 123", "doi:10.1/x", ""], modeOfInheritance="unclear", diagnosticSignificance="nope",
             localization=[{"code": "codingRegion"}, {"code": "unknownRegion"}], segregationAnalysis="notPerformed")
    _drop(v, "zygosity")
    dk["molecular"]["smallVariants"].append(dict(copy.deepcopy(v), chromosome="23", externalId="123",
                                                 startPosition=5, endPosition=9, localization=[]))
    dk["molecular"]["smallVariants"].append(dict(copy.deepcopy(v), chromosome="Y", acmgClass="7", publications=[],
                                                 acmgCriteria=[], modeOfInheritance="", diagnosticSignificance="",
                                                 localization=[{"code": "nope"}], identifier="other-id"))


def _m_plan(dk):
    pl = dk["plan"]
    vid = _var(dk)["identifier"]
    pl["recommendedTherapies"] = [
        {"identifier": "T1", "type": "causal", "strategy": "other", "strategyOther": "Physio", "variants": [vid, vid, "nope"]},
        {"identifier": "T1", "type": "weird", "strategy": "combination", "strategyCombination": "A+B", "variants": []},
        {"identifier": "T3", "type": "symptomatic", "strategy": "invented"},
        {"identifier": "T4", "type": "symptomatic", "strategy": "earlyDetection"}]
    pl["recommendedStudies"] = [
        {"identifier": "S1", "register": "yesButStudyIsUnknown", "name": "Study X", "id": "N/A", "variants": [vid]},
        {"identifier": "S2", "register": "other", "name": "Local trial", "id": "LOC-1"},
        {"identifier": "S3", "register": "NCT", "name": "N/A", "id": "NCT01234567"},
        {"identifier": "S4", "register": "NCT", "name": "unknown", "id": "NCT01234567"}]
    pl["carePlanRd"].update(clinicalManagementRecommended=True, clinicalManagementDescriptions=["gp", "bogus"],
                            studyRecommended=False)


def _m_followups(dk):
    f0 = _fu(dk)[0]
    f0.update(gmfcs="II", vitalStatus="deceased", diagnosisEstablished=False)
    _drop(f0, "deathDate")
    f0["phenotypes"] = [{"code": "HP:0100871", "change": "improved", "system": "https://hpo.jax.org"},
                        {"code": "X:1", "change": "weird", "system": "http://example.org/x", "display": "x"},
                        {"code": "HP:0000001", "change": "newlyAdded"}]
    _fu(dk).append({"followUpDate": f0["followUpDate"], "diagnosisEstablished": True, "vitalStatus": "living",
                    "diseaseProgression": "stable"})
    _fu(dk).append({"followUpDate": "2099-01-01", "diagnosisEstablished": False, "vitalStatus": "deceased",
                    "deathDate": "2099-01"})


MUTATIONS = {
    "local-case-id": lambda dk: _set(dk["metaData"], localCaseId="RD 7/a|b"),
    "dx-codes": _m_dx_codes,
    "no-matching-code": lambda dk: _set(_dx(dk), noMatchingCodeExists=True),
    "dup-phenotype": lambda dk: _dx(dk)["phenotypes"].append(dict(_dx(dk)["phenotypes"][0], display="other display")),
    "no-genetic-dx-established": lambda dk: (_set(_dx(dk), diagnosticAssessment="noGeneticDiagnosis"),
                                             _set(_fu(dk)[0], diagnosisEstablished=True)),
    "further-diagnostics": lambda dk: (_set(_dx(dk), diagnosticAssessment="furtherGeneticDiagnosticRecommended"),
                                       _set(_fu(dk)[0], diagnosisEstablished=False)),
    "no-assessment": lambda dk: (_drop(_dx(dk), "diagnosticAssessment"), _set(_fu(dk)[0], diagnosisEstablished=False)),
    "genetic-without-evidence": lambda dk: (_set(_dx(dk), diagnosticAssessment="confirmedGeneticDiagnosis", phenotypes=[]),
                                            dk.pop("molecular")),
    "no-board-date": lambda dk: _drop(_dx(dk), "molecularBoardDecisionDate"),
    "library-none": lambda dk: _set(_dx(dk), libraryType="none", diagnosticExtent="quadGenome"),
    "library-unknown": lambda dk: _set(_dx(dk), libraryType="nanopore", diagnosisGmfcs="VI"),
    "prior-entries": lambda dk: _set(dk["case"], priorRds=[
        {"genomicTestType": "none", "genomicStudyType": "duo", "diagnosticResult": "other", "hospitalizationPeriods": "upToTen",
         "hospitalizationDuration": "moreThanFifty", "zseContactDate": "2024-05"},
        {"genomicTestType": "single", "genomicStudyType": "trio", "diagnosticResult": "other", "hospitalizationPeriods": "x",
         "hospitalizationDuration": "unknown", "zseContactDate": "2023-11", "diagnosticDate": "2023-12-01"},
        {"genomicTestType": "array", "genomicStudyType": "quad", "diagnosticResult": "unclearVariantInGeneticDisease",
         "hospitalizationPeriods": "moreThanFifteen", "hospitalizationDuration": "none", "zseContactDate": "2025-01"},
        {"genomicTestType": "karyotyping", "genomicStudyType": "single", "diagnosticResult": "noPathogenicVariantDetected",
         "hospitalizationPeriods": "upToFifteen", "hospitalizationDuration": "upToFifteen", "zseContactDate": "2025-01"}]),
    "variants": _m_variants,
    "dup-variant-id": lambda dk: dk["molecular"]["smallVariants"].append(copy.deepcopy(_var(dk)) | {"chromosome": "2"}),
    "plan": _m_plan,
    "followups": _m_followups,
    "research-consent-absent": lambda dk: _set(dk["metaData"], researchConsents=[
        {"presentationDate": "2026-01-02", "noScopeJustification": "patient refuses to sign consent"},
        {"presentationDate": "2026-01-03", "noScopeJustification": "not in the enum"}]),
}


def check(f: str, mb: Matchbox, ingest: bool = False, mutation: str | None = None, raw: bool = True) -> dict:
    dk = json.loads((REPO / f).read_text(encoding="utf-8"))
    if not raw:
        dk = declared_shape(dk)
    if mutation:
        MUTATIONS[mutation](dk)
    py, rep = convert(dk, f, check_input=not mutation)
    st, fml = mb.transform(dk, MAP_URL)
    res = {"file": f + (f" [{mutation}]" if mutation else "") + (" (raw)" if raw else ""), "python": rep.status,
           "http": st, "type": fml.get("resourceType")}
    if py is None or fml.get("resourceType") != "Bundle":
        res["error"] = json.dumps(fml)[:600] if fml.get("resourceType") != "Bundle" else rep.error
        return res
    v = validate_bundle(fml, mb)
    res["content_errors"] = [f"{r['type']}/{r['profile']}: {i['expression']} :: {i['text'][:200]}"
                             for r in v["resources"] for i in r["issues"] if i["class"] == "content"]
    if mutation:   # mutated inputs may carry invalid source data: compare with the Python output's errors
        vp = validate_bundle(py, mb)
        res["py_content_errors"] = [f"{r['type']}/{r['profile']}: {i['expression']} :: {i['text'][:200]}"
                                    for r in vp["resources"] for i in r["issues"] if i["class"] == "content"]

        def errs(val):     # multiset of normalised errors (entry uuids differ between the two bundles)
            return collections.Counter(f"{r['type']}/{r['profile']}: " + re.sub(r"urn:uuid:[0-9a-f-]{36}", "urn:uuid:*",
                                                                             i["text"][:200])
                                       for r in val["resources"] for i in r["issues"] if i["class"] == "content")
        res["content_errors_not_in_python"] = sorted((errs(v) - errs(vp)).elements())
    eq, only_py, only_fml = parity(py, fml)
    res.update(equal=sum(eq.values()), only_python=list(only_py.elements()), only_fml=list(only_fml.elements()),
               entries=len(fml["entry"]))
    if ingest:
        res["ingest"] = ingest_twice(fml)
    return res


# ---- pytest ------------------------------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(not MB, reason="MB2027 not set (matchbox-2027 base URL)")


@pytest.fixture(scope="module")
def mb():
    m = Matchbox(MB)
    assert push_maps(MB) == 0, "pushing DatenkranzCommon + DatenkranzRareDiseaseToMii failed"
    return m


@pytest.mark.parametrize("f", FILES)
def test_rd_file(mb, f):
    if not (REPO / f).is_file():
        pytest.fail(f"{f} not in this checkout")
    r = check(f, mb, ingest=True)
    assert r["type"] == "Bundle", r
    assert r["content_errors"] == [], r["content_errors"]
    assert r["only_python"] == [] and r["only_fml"] == [], (r["only_python"], r["only_fml"])
    assert r["equal"] >= 40
    first, second = r["ingest"][1], r["ingest"][2]
    assert first["ok"] and second["ok"], r["ingest"]
    assert second["new"] == 0 and set(second["statuses"]) == {"200"}, r["ingest"]


@pytest.mark.parametrize("mutation", sorted(MUTATIONS))
def test_rd_edge_cases(mb, mutation):
    if not (REPO / FILES[0]).is_file():
        pytest.fail(f"{FILES[0]} not in this checkout")
    r = check(FILES[0], mb, mutation=mutation, raw=False)
    assert r["type"] == "Bundle", r
    assert r["content_errors_not_in_python"] == [], (r["content_errors"], r["py_content_errors"])
    assert r["only_python"] == [] and r["only_fml"] == [], (r["only_python"], r["only_fml"])


# ---- wide corpus run ---------------------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=42, help="rare-disease files, spread over the manifest")
    ap.add_argument("--ingest", type=int, default=3, help="files ingested twice into HAPI")
    ap.add_argument("--declared", action="store_true", help="the declared shape of the files instead of the raw files")
    ap.add_argument("--mutations", action="store_true", help="also the edge-case mutations")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not MB:
        sys.exit("set MB2027")
    mbx = Matchbox(MB)
    print("push failures:", push_maps(MB))
    manifest = json.loads((REPO / "genomde2fhir" / "tests" / "corpus_manifest.json").read_text())
    spread = _load("run_corpus", REPO / "scripts" / "run_corpus.py").spread
    results, tot, diffs = [], collections.Counter(), collections.Counter()
    jobs = [(f, None, i < a.ingest) for i, f in enumerate(spread(manifest["rare-disease"]["valid"], a.n) if a.n else [])]
    if a.mutations:
        jobs += [(FILES[0], m, False) for m in MUTATIONS]
    for f, mu, ing in jobs:
        r = check(f, mbx, ingest=ing, mutation=mu, raw=not (a.declared or mu))
        results.append(r)
        tot["files"] += 1
        tot["bundle"] += r["type"] == "Bundle"
        tot["content_err_files"] += bool(r.get("content_errors"))
        tot["equal"] += r.get("equal", 0)
        tot["diff_files"] += bool(r.get("only_python") or r.get("only_fml"))
        for x in r.get("only_python", []):
            diffs["PY  " + x[:200]] += 1
        for x in r.get("only_fml", []):
            diffs["FML " + x[:200]] += 1
        if "ingest" in r:
            tot["ingested"] += 1
            tot["ingest_ok"] += r["ingest"][1]["ok"] and r["ingest"][2]["ok"] and r["ingest"][2]["new"] == 0
        if r.get("error") or r.get("content_errors") or ("ingest" in r and r["ingest"][2]["new"]):
            print(json.dumps(r, indent=1)[:3000])
    print(dict(tot))
    for k, v in diffs.most_common(30):
        print(v, k)
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1))
