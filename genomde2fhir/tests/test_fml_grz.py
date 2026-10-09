"""FML stage 'grz': mappers/fml/DatenkranzGrzToMii.map (imports DatenkranzCommon) against the Python GRZ builders.

Skipped unless MB2027 (matchbox-2027 base URL) is set; HAPI2027 defaults to http://localhost:8092/fhir.
For 3 GRZ files: push the maps, $transform -> Bundle, zero content errors (except those the Python output has as
well), graph-aware parity with the Python converter on the whole Bundle (canonical() from scripts/run_corpus.py:
ids, resource-key identifiers and Provenance ignored) and an idempotent double ingest into HAPI.

Wide run over the corpus (+ edge-case mutations):
  MB2027=http://localhost:8091/matchboxv3/fhir python genomde2fhir/tests/test_fml_grz.py --n 60
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
MAP_URL = "https://genomde.de/fhir/StructureMap/DatenkranzGrzToMii"
MAPS = ["DatenkranzCommon.map", "DatenkranzGrzToMii.map"]
FILES = ["example-data/grz/grz-edge-correction-multi-donor.json",                  # MTB, 2 donors, relation other
         "example-data/synthData-v1/grz/submission/synth_submission_000.json",     # floats, ICD-O-3 claimed for UBERON
         "example-data/synthData-v1/grz/submission/synth_submission_005.json"]     # MolGen, trio (FamilyMemberHistory)
BASE = FILES[0]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strip_empty(o):
    """canonical() leaves 'identifier': [] when the resource key was the only identifier."""
    if isinstance(o, dict):
        return {k: _strip_empty(v) for k, v in o.items() if v != []}
    if isinstance(o, list):
        return [_strip_empty(x) for x in o]
    return o


def parity(py_bundle: dict, fml_bundle: dict):
    """(equal, only-python, only-fml) multisets of canonical resources."""
    canonical = _load("run_corpus", REPO / "scripts" / "run_corpus.py").canonical

    def sub(b):
        out = collections.Counter()
        for k, v in canonical(b).items():
            r = _strip_empty(json.loads(k))
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


def content_errors(bundle: dict, mb: Matchbox) -> list[str]:
    v = validate_bundle(bundle, mb)
    return sorted({f"{r['type']}/{(r['profile'] or '').split('/')[-1]}: {_expr(i)} :: "
                   f"{i['text'][:160]}" for r in v["resources"] for i in r["issues"] if i["class"] == "content"})


def _expr(i):
    return re.sub(r"\[\d+\]", "[]", re.sub(r"^Bundle\.entry\[\d+\]\.resource/\*\w+/[^*]*\*/", "", i["expression"]))


# ---- edge cases the corpus lacks (applied to BASE; Python converts them with check_input=False) ----------------------
BROAD_CONSENT_FILE = "example-data/grz/synthetic-coverage-basis-via-pkv.json"   # KDK oncology file, embedded MII Broad Consent


def _broad_consent() -> dict:
    return copy.deepcopy(json.loads((REPO / BROAD_CONSENT_FILE).read_text(encoding="utf-8"))["metaData"]["researchConsents"][0])


def _ld(dk, i=0, j=0):
    return dk["donors"][i]["labData"][j]


def _set(d, **kw):
    d.update(kw)
    return d


def _pop(d, *keys):
    for k in keys:
        d.pop(k, None)
    return d


MUTATIONS = {
    "no-index-donor": lambda dk: _set(dk["donors"][0], relation="mother"),
    "relatives": lambda dk: (_set(dk["donors"][1], relation="sister", gender="other"),
                             dk["donors"].append(_set(copy.deepcopy(dk["donors"][1]), donorPseudonym="c0ffee", relation="child",
                                                      gender="diverse", labData=[]))),
    "second-index": lambda dk: _set(dk["donors"][1], relation="index"),
    "donor-without-pseudonym": lambda dk: _set(dk["donors"][1], donorPseudonym=""),
    "rare-molgen": lambda dk: _set(dk["submission"], diseaseType="rare", genomicStudyType="duo", genomicStudySubtype="germline-only"),
    "no-lab-name": lambda dk: _pop(dk["submission"], "labName"),
    "coverage-skt": lambda dk: _set(dk["submission"], coverageType="SKT"),
    "no-local-case-id": lambda dk: _pop(dk["submission"], "localCaseId"),
    "icdo3-site": lambda dk: _set(_ld(dk), tissueOntology={"name": "ICD-O-3", "version": "2019"}, tissueTypeId="C34.1",
                                  tissueTypeName="Oberlappen der Lunge"),
    "snomed-code": lambda dk: _set(_ld(dk), tissueOntology={"name": "SNOMED CT", "version": "http://snomed.info/sct/900000000000207008"},
                                   tissueTypeId="119297000", tissueTypeName="Blood specimen"),
    "snomed-label-version": lambda dk: _set(_ld(dk), tissueOntology={"name": "snomed", "version": "2024.03"},
                                            tissueTypeId="119297000", tissueTypeName="Blood specimen"),
    "uberon-unmapped": lambda dk: _set(_ld(dk), tissueOntology={"name": "UBERON", "version": "2024"},
                                       tissueTypeId="UBERON:0001977", tissueTypeName="serum"),
    "uberon-contradiction": lambda dk: _set(_ld(dk), tissueOntology={"name": "UBERON", "version": "2024"},
                                            tissueTypeId="UBERON:0002046", tissueTypeName="saliva"),
    "uberon-subset-label": lambda dk: _set(_ld(dk), tissueOntology={"name": "UBERON", "version": "2024"},
                                           tissueTypeId="UBERON:0001150", tissueTypeName="Pancreas"),
    "uberon-bare-code": lambda dk: _set(_ld(dk), tissueOntology={"name": "Uberon", "version": "2024"},
                                        tissueTypeId="0000178", tissueTypeName="blood"),
    "unknown-ontology": lambda dk: _set(_ld(dk), tissueOntology={"name": "CL", "version": "1"},
                                        tissueTypeId="CL:0000084", tissueTypeName="T cell"),
    "no-tissue-id": lambda dk: _pop(_ld(dk), "tissueTypeId"),
    "barcode-na": lambda dk: _set(_ld(dk), barcode=" NA "),
    "ffpe": lambda dk: _set(_ld(dk), sampleConservation="ffpe"),
    "cryo": lambda dk: _set(_ld(dk), sampleConservation="cryo-frozen"),
    "conservation-other": lambda dk: _set(_ld(dk), sampleConservation="other"),
    "no-sample-date": lambda dk: _pop(_ld(dk), "sampleDate"),
    "tcc-methods": lambda dk: _set(_ld(dk), tumorCellCount=[{"count": 40.0, "method": "other"}, {"count": 41, "method": "unknown"},
                                                           {"count": 42.5, "method": "bioinformatics"}, {"count": 43}]),
    "rna-other-library": lambda dk: _set(_ld(dk), sequenceType="rna", libraryType="other", sequencingLayout="other",
                                         fragmentationMethod="unknown"),
    "panel-tso500": lambda dk: _set(_ld(dk), libraryType="panel_lr", enrichmentKitDescription="TruSight Oncology 500 (TSO-500)",
                                    enrichmentKitManufacturer="Illumina"),
    "panel-other-kit": lambda dk: _set(_ld(dk), libraryType="panel", enrichmentKitDescription="Custom in-house panel",
                                       enrichmentKitManufacturer="other"),
    "no-enrichment": lambda dk: _set(_ld(dk), enrichmentKitManufacturer="none", enrichmentKitDescription="na"),
    "enrichment-none-named": lambda dk: _set(_ld(dk), enrichmentKitManufacturer="none", enrichmentKitDescription="Kit X"),
    "devices-absent": lambda dk: _set(_ld(dk), sequencerModel="n/a", sequencerManufacturer="other", kitName="unknown",
                                      kitManufacturer="Illumina", libraryPrepKit="Kit Y", libraryPrepKitManufacturer="notApplicable"),
    "callers": lambda dk: _ld(dk)["sequenceData"]["callerUsed"].extend([{"name": "GATK", "version": "4.5"}, {"name": "na", "version": "1"},
                                                                         {"name": "Strelka"}]),
    "no-sequence-data": lambda dk: _pop(_ld(dk), "sequenceData"),
    "qc-partial": lambda dk: (_pop(_ld(dk)["sequenceData"], "minCoverage", "nonCodingVariants", "percentBasesAboveQualityThreshold"),
                              _set(_ld(dk)["sequenceData"], meanDepthOfCoverage=30.0, targetedRegionsAboveMinCoverage=0.9)),
    "qc-pct-no-q": lambda dk: _set(_ld(dk)["sequenceData"], percentBasesAboveQualityThreshold={"percent": 90.0}),
    "molgen-layout": lambda dk: (_set(dk["submission"], diseaseType="hereditary"), _set(_ld(dk), sequencingLayout="reverse")),
    "research-consent-absent": lambda dk: _set(dk["donors"][0], researchConsents=[
        {"presentationDate": "2026-04-02", "noScopeJustification": "patient refuses to sign consent"},
        {"presentationDate": "2026-04-03", "noScopeJustification": "not a reason"},
        {"presentationDate": "2026-04-04", "scope": {}, "noScopeJustification": "patient unable to consent"}]),
    "research-consent-migrated": lambda dk: [_set(d, researchConsents=[
        _broad_consent(), {"presentationDate": "2026-04-02", "noScopeJustification": "patient refuses to sign consent"},
        _set(_broad_consent(), presentationDate="2026-05-05")]) for d in dk["donors"]],
    "mv-consent-unusable": lambda dk: _set(dk["donors"][1]["mvConsent"], scope=[{"date": "2020-01-01", "domain": "x", "type": "permit"}]),
    "duplicate-labdata-name": lambda dk: dk["donors"][0]["labData"].append(
        _set(copy.deepcopy(_ld(dk)), barcode="ATCG09", sampleDate="2026-05-01")),
    "special-chars": lambda dk: (_set(dk["submission"], localCaseId="CASE 7/a|b&c"), _set(dk["donors"][0], donorPseudonym="p 1/x|y"),
                                 _set(_ld(dk), labDataName="lab data #1&2")),
}


INGEST_MUTATIONS = {"special-chars", "duplicate-labdata-name", "relatives", "research-consent-absent", "panel-tso500",
                    "research-consent-migrated"}
FIXTURES = sorted(str(p.relative_to(REPO)) for d in ("grz_donors", "grz_labdata")
                  for p in (REPO / "genomde2fhir" / "tests" / "fixtures" / d).glob("*.json"))


def check_file(f: str, mb: Matchbox, ingest: bool = True, mutation: str | None = None, py_errors: bool = False) -> dict:
    dk = json.loads((REPO / f).read_text(encoding="utf-8"))
    if mutation:
        MUTATIONS[mutation](dk)
    py, rep = convert(dk, f, check_input=not mutation and "/fixtures/" not in f)
    st, fml = mb.transform(dk, MAP_URL)
    res = {"file": f + (f" [{mutation}]" if mutation else ""), "python": rep.status, "http": st,
           "type": fml.get("resourceType")}
    if py is None or fml.get("resourceType") != "Bundle":
        res["error"] = json.dumps(fml)[:600]
        return res
    res["entries"] = len(fml.get("entry", []))
    fml_err = content_errors(fml, mb)
    py_err = content_errors(py, mb) if (fml_err or py_errors) else []
    res["content_errors"] = [e for e in fml_err if e not in py_err]   # errors the Python output does not have
    res["shared_errors"] = [e for e in fml_err if e in py_err]
    eq, only_py, only_fml = parity(py, fml)
    res.update(equal=sum(eq.values()), only_python=list(only_py.elements()), only_fml=list(only_fml.elements()))
    if ingest:
        res["ingest"] = ingest_twice(fml)
    return res


# ---- pytest ------------------------------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(not MB, reason="MB2027 not set (matchbox-2027 base URL)")


@pytest.fixture(scope="module")
def mb():
    m = Matchbox(MB)
    assert push_maps(MB) == 0, "pushing DatenkranzCommon + DatenkranzGrzToMii failed"
    return m


@pytest.mark.parametrize("f", FILES)
def test_grz_file(mb, f):
    if not (REPO / f).is_file():
        pytest.skip(f"{f} not in this checkout")
    r = check_file(f, mb)
    assert r["type"] == "Bundle", r
    assert r["content_errors"] == [], r["content_errors"]
    assert r["only_python"] == [] and r["only_fml"] == [], (r["only_python"], r["only_fml"])
    assert r["equal"] >= 10
    first, second = r["ingest"][1], r["ingest"][2]
    assert first["ok"] and second["ok"], r["ingest"]
    assert second["new"] == 0 and set(second["statuses"]) == {"200"}, r["ingest"]


def test_grz_research_consent_migrated(mb):
    """The GRZ corpus carries only empty scopes; an embedded MII Broad Consent per donor (DkResearchConsent)."""
    if not (REPO / BASE).is_file() or not (REPO / BROAD_CONSENT_FILE).is_file():
        pytest.skip("example files not in this checkout")
    r = check_file(BASE, mb, ingest=True, mutation="research-consent-migrated", py_errors=True)
    assert r["type"] == "Bundle", r
    assert r["content_errors"] == [], r["content_errors"]
    assert r["only_python"] == [] and r["only_fml"] == [], (r["only_python"], r["only_fml"])
    first, second = r["ingest"][1], r["ingest"][2]
    assert first["ok"] and second["ok"], r["ingest"]
    assert second["new"] == 0 and set(second["statuses"]) == {"200"}, r["ingest"]


# ---- wide corpus run ---------------------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25, help="corpus files, spread over the manifest (0 = none, -1 = all)")
    ap.add_argument("--ingest", type=int, default=5, help="corpus files ingested twice into HAPI")
    ap.add_argument("--mutations", default="all", help="comma list, 'all' or 'none'")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not MB:
        sys.exit("set MB2027")
    mbx = Matchbox(MB)
    print("push failures:", push_maps(MB))
    manifest = json.loads((REPO / "genomde2fhir" / "tests" / "corpus_manifest.json").read_text())
    spread = _load("run_corpus", REPO / "scripts" / "run_corpus.py").spread
    files = manifest["grz"]["valid"] if a.n < 0 else spread(manifest["grz"]["valid"], a.n) if a.n else []
    results, tot = [], collections.Counter()

    def account(r, kind):
        results.append(r)
        tot[kind + ".files"] += 1
        tot[kind + ".bundle"] += r["type"] == "Bundle"
        tot[kind + ".entries"] += r.get("entries", 0)
        tot[kind + ".content_err_files"] += bool(r.get("content_errors"))
        tot[kind + ".shared_err_files"] += bool(r.get("shared_errors"))
        tot[kind + ".equal"] += r.get("equal", 0)
        tot[kind + ".diff_files"] += bool(r.get("only_python") or r.get("only_fml"))
        if "ingest" in r:
            tot[kind + ".ingested"] += 1
            tot[kind + ".ingest_ok"] += r["ingest"][1]["ok"] and r["ingest"][2]["ok"] and r["ingest"][2]["new"] == 0
        if r.get("error") or r.get("content_errors") or r.get("only_python") or r.get("only_fml") or \
                ("ingest" in r and not (r["ingest"][1]["ok"] and r["ingest"][2]["new"] == 0)):
            print(json.dumps(r, indent=1, ensure_ascii=False)[:4000])

    for i, f in enumerate(files):
        account(check_file(f, mbx, ingest=i < a.ingest), "corpus")
    for f in FIXTURES if a.mutations != "none" else []:
        account(check_file(f, mbx, ingest=True, py_errors=True), "fixture")
    muts = [] if a.mutations == "none" else list(MUTATIONS) if a.mutations == "all" else a.mutations.split(",")
    for mu in muts:
        account(check_file(BASE, mbx, ingest=mu in INGEST_MUTATIONS, mutation=mu, py_errors=True), "edge")
    print(dict(sorted(tot.items())))
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1, ensure_ascii=False))
