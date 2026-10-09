"""FML stage 'onco_molecular': mappers/fml/OncoMolecular.map (called from DatenkranzOncologyToMii).

Skipped unless MB2027 (matchbox-2027 base URL) is set; HAPI2027 defaults to http://localhost:8092/fhir.
For 3 oncology files: push the maps, $transform -> Bundle, zero content errors on the molecular resources (none that the
Python output of the same resources does not have), graph-aware parity with the Python converter on the molecular
resources, and an idempotent double ingest into HAPI. Edge-case mutations cover what the corpus lacks
(expressionVariants, duplicate / missing identifiers, SBS name forms, unmapped codes, fusion profiles, HGVS forms).

Molecular resources (Python builders onco.molecular_*): the current NGS report = the item of the MTB Behandlungsepisode's
investigation, and its results. The episode itself enters the comparison with its investigation only (the spine test
covers the rest). The variant look-up used by the plan map (OncoMolFindingRef) is checked against Python's
ctx.ids[('variant', id)] semantics (first finding with the KDK identifier).

Wide run:  MB2027=http://localhost:8091/matchboxv3/fhir python genomde2fhir/tests/test_fml_onco_molecular.py --n 30
"""
import collections
import importlib.util
import json
import os
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
MAP = "https://genomde.de/fhir/StructureMap/DatenkranzOncologyToMii"
SID_FINDING = "https://genomde.de/fhir/sid/molecular-finding-id"
FILES = [  # NCT (small + RNA fusion + biomarkers incl. ploidy + SBS), DNPM (108 findings, CNV-heavy), ukdd (small variant + DNA fusion + CNV)
    "example-data/synthData-v1/nct/case_036.json",
    "example-data/synthData-v1/dnpm/OncologySubmission_B2A88F25BF17D1913417EFC81DE39E22CF2047AED143BEA183C33BBB000AFD68.json",
    "example-data/synthData-v1/ukdd/synth_json_501.json",
]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _profile(r):
    return (r.get("meta", {}).get("profile") or [""])[0].split("/")[-1]


def molecular_urls(bundle: dict) -> tuple[set, str | None]:
    """fullUrls of the current NGS report and its results; the episode's fullUrl."""
    by_url = {e["fullUrl"]: e["resource"] for e in bundle.get("entry", [])}
    ep = next((u for u, r in by_url.items() if _profile(r) == "mii-pr-mtb-behandlungsepisode"), None)
    mine = set()
    if ep:
        for inv in by_url[ep].get("investigation", []):
            for it in inv.get("item", []):
                rep = by_url.get(it.get("reference"))
                if rep is not None:
                    mine.add(it["reference"])
                    mine.update(x["reference"] for x in rep.get("result", []) if x.get("reference") in by_url)
    return mine, ep


def parity(py_bundle: dict, fml_bundle: dict):
    """(equal, only-python, only-fml) multisets of canonical molecular resources (+ the episode's investigation)."""
    canonical = _load("run_corpus", REPO / "scripts" / "run_corpus.py").canonical

    def sub(bundle):
        mine, ep = molecular_urls(bundle)
        out = canonical_subset(canonical, bundle, mine)
        if ep:
            for k, v in canonical_subset(canonical, bundle, {ep}).items():
                r = json.loads(k)
                if "investigation" in r:
                    out[json.dumps({"resourceType": r["resourceType"], "investigation": r["investigation"]}, sort_keys=True)] += v
        return out
    p, f = sub(py_bundle), sub(fml_bundle)
    return p & f, p - f, f - p


def canonical_subset(canonical, bundle: dict, urls: set) -> collections.Counter:
    """canonical() restricted to the entries in urls; references to the other entries are still labelled
    (they stay in the Bundle as stubs with type and profile only, whose own canonical strings cancel out)."""
    stubs = [{"fullUrl": e["fullUrl"], "resource": {"resourceType": e["resource"]["resourceType"],
                                                    "meta": e["resource"].get("meta", {})}}
             for e in bundle.get("entry", []) if e["fullUrl"] not in urls]
    full = canonical({"entry": [e for e in bundle.get("entry", []) if e["fullUrl"] in urls] + stubs})
    full.subtract(canonical({"entry": stubs}))
    out = collections.Counter()
    for k, v in full.items():
        if v <= 0:
            continue
        r = json.loads(k)
        if r.get("identifier") == []:
            r.pop("identifier")
        out[json.dumps(r, sort_keys=True)] += v
    return out


def finding_lookup(bundle: dict) -> dict:
    """KDK identifier -> canonical form of the first entry carrying that molecular-finding-id (what OncoMolFindingRef
    returns; Python: ctx.ids[('variant', id)])."""
    canonical = _load("run_corpus", REPO / "scripts" / "run_corpus.py").canonical
    first = {}
    for e in bundle.get("entry", []):
        for i in e["resource"].get("identifier", []):
            if i.get("system") == SID_FINDING:
                first.setdefault(i["value"].split("|", 2)[2], e["fullUrl"])
    return {vid: sorted(canonical_subset(canonical, bundle, {u})) for vid, u in first.items()}


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
    return f"{r['resourceType']}: {k[:700]}"


def _content(v: dict, entries: list, urls: set) -> list:
    """Content errors of the resources in urls (validate_bundle rows are in entry order, one profile per resource)."""
    rows = [r for r in v["resources"] if r["type"] != "Bundle"]
    out = []
    for e, r in zip(entries, rows):
        if e["fullUrl"] in urls:
            out += [f"{r['type']}/{(r['profile'] or '').split('/')[-1]}: {i['expression']} :: {i['text'][:200]}"
                    for i in r["issues"] if i["class"] == "content"]
    return out


def check_file(f: str, mb: Matchbox, ingest: bool = True, dk: dict | None = None, label: str | None = None) -> dict:
    mutated = dk is not None
    dk = dk if mutated else json.loads((REPO / f).read_text(encoding="utf-8"))
    py, rep = convert(dk, f, check_input=not mutated)
    st, fml = mb.transform(dk, MAP)
    res = {"file": label or f, "python": rep.status, "http": st, "type": fml.get("resourceType")}
    if py is None or fml.get("resourceType") != "Bundle":
        res["error"] = json.dumps(fml)[:600]
        return res
    mine, ep = molecular_urls(fml)
    res["entries"], res["molecular"] = len(fml.get("entry", [])), len(mine)
    v = validate_bundle(fml, mb, source=dk)
    res["content_errors_all"] = sum(1 for r in v["resources"] for i in r["issues"] if i["class"] == "content")
    res["content_errors"] = _content(v, fml["entry"], mine | {ep})
    if res["content_errors"]:
        py_mine, py_ep = molecular_urls(py)
        sub = {"entry": [e for e in py["entry"] if e["fullUrl"] in py_mine | {py_ep}]}
        vp = validate_bundle(sub, mb, bundle_level=False, source=dk)
        strip = lambda s: s.split(" :: ", 1)[0].split(":")[0] + " :: " + s.split(" :: ", 1)[1]  # noqa: E731
        py_errs = collections.Counter(strip(x) for x in _content(vp, sub["entry"], py_mine | {py_ep}))
        fml_errs = collections.Counter(strip(x) for x in res["content_errors"])
        res["python_content_errors"] = sorted(py_errs.elements())
        res["content_errors_not_in_python"] = sorted((fml_errs - py_errs).elements())
    else:
        res["python_content_errors"], res["content_errors_not_in_python"] = [], []
    eq, only_py, only_fml = parity(py, fml)
    res.update(equal=sum(eq.values()), only_python=sorted(only_py.elements()), only_fml=sorted(only_fml.elements()))
    fl = finding_lookup(fml)
    res["lookup_mismatch"] = sorted(k for k, x in finding_lookup(py).items() if fl.get(k) != x)
    if ingest:
        res["ingest"] = ingest_twice(fml)
    return res


# ---- pytest ------------------------------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(not MB, reason="MB2027 not set (matchbox-2027 base URL)")


def _mol(dk):
    return dk.setdefault("molecular", {})


def _set(d, **kw):
    d.update(kw)
    return d


GENE = {"code": "HGNC:1100", "display": "BRCA1", "system": "https://www.genenames.org/"}
# Edge cases the corpus lacks, applied to FILES[0] (NCT; Python converts them with check_input=False)
MUTATIONS = {
    "expression": lambda dk: _set(_mol(dk), expressionVariants=[
        {"identifier": "ev-1", "gene": GENE, "expressionType": "highExpression", "reference": "TCGA cohort"},
        {"identifier": "ev-2", "gene": {"code": "ENSG000001", "display": "X", "system": "http://www.ensembl.org"},
         "expressionType": "noExpression", "reference": ""},
        {"identifier": "ev-3", "gene": {"code": "HGNC:5", "display": "A1BG", "version": "2024"}, "expressionType": "normalExpression",
         "reference": "x"},
        {"identifier": "ev-4", "gene": GENE, "expressionType": "lowExpression", "reference": "y"},
        {"identifier": "ev-5", "gene": GENE, "expressionType": "weird", "reference": "z"}]),
    "only-expression": lambda dk: dk.update(molecular={"expressionVariants": [
        {"identifier": "ev-1", "gene": GENE, "expressionType": "lowExpression", "reference": "r"}]}),
    "duplicate-ids": lambda dk: _set(_mol(dk), copyNumberVariants=[
        {"identifier": "c1", "genomicSource": "somatic", "cnvType": "gain", "localization": "coding", "chromosome": "MT",
         "startPosition": 10, "endPosition": 5, "gene": {"code": "TP53", "display": "TP53", "system": "http://example.org/genes"}},
        {"identifier": "c1", "genomicSource": "germline", "cnvType": "completeLoss", "localization": "inRegulatoryElements",
         "chromosome": "X", "startPosition": 1},
        {"identifier": "c2", "genomicSource": "other", "cnvType": "bogus", "localization": "nowhere", "endPosition": 7,
         "chromosome": "01"},
        {"identifier": "c1", "genomicSource": "somatic", "cnvType": "heterozygousLoss", "localization": "coding"}],
        smallVariants=dk["molecular"]["smallVariants"] + [dict(dk["molecular"]["smallVariants"][0], dnaChange="c.1A>G")]),
    "small-variant-forms": lambda dk: _set(_mol(dk), smallVariants=[
        {"identifier": "s1", "genomicSource": "germline", "gene": {"code": "BRAF", "display": "BRAF", "system": "http://x.org/genes"},
         "transcriptId": {"code": "NM_004333", "version": "6", "system": "RefSeq"}, "dnaChange": " c.1799T>A ",
         "proteinChange": "p.Val600Glu", "chromosome": "MT", "startPosition": 100, "endPosition": 90, "ref": "T", "alt": "",
         "variantTypes": [{"system": "http://www.sequenceontology.org", "version": "2024", "code": "SO:0001583", "display": "missense"},
                          {"system": "local", "version": "1", "code": "snv"}, {"system": "", "version": "1", "code": "x"}],
         "localization": "inRegulatoryElements", "loh": True},
        {"identifier": "s2", "genomicSource": "somatic", "gene": {"code": "HGNC:1097", "display": ""},
         "transcriptId": {"code": "NR_000001.2", "system": "x"}, "dnaChange": "c.10A>G", "proteinChange": "p.(Arg2Ter)",
         "chromosome": "Y", "startPosition": 5, "endPosition": 6, "ref": "A", "alt": "G", "localization": "notInCodingAndNotInRegulatoryElements"},
        {"identifier": "s3", "genomicSource": "somatic", "gene": {"code": "HGNC:1097", "display": "BRAF"},
         "transcriptId": {"code": "ENST00000288602.11", "system": "Ensembl"}, "dnaChange": "n.5C>T", "proteinChange": "NM_1.1:p.X",
         "chromosome": "7", "startPosition": 5, "endPosition": 5, "ref": "C", "alt": "T", "localization": "coding", "loh": False},
        {"identifier": "s4", "genomicSource": "somatic", "gene": {"code": "HGNC:1097", "display": "BRAF"},
         "transcriptId": {"code": "weird-1", "system": "ensembl-ish"}, "dnaChange": "g.5C>T",
         "chromosome": "22", "startPosition": 5, "endPosition": 5, "ref": "C", "alt": "T", "localization": "coding"}]),
    "fusions-and-biomarkers": lambda dk: _set(_mol(dk), structuralVariants=[
        {"identifier": "f1", "genomicSource": "germline", "geneA": GENE, "geneB": {"code": "", "display": "X"},
         "structureType": "translocation", "sequenceType": "DNA", "localization": "coding", "description": "t(9;22)"},
        {"identifier": "f2", "genomicSource": "somatic", "geneA": {"code": "ALK", "display": "ALK", "system": "http://other"},
         "geneB": GENE, "structureType": "bogus", "sequenceType": "cDNA", "localization": "coding"}],
        complexBiomarkers=[{"identifier": "b1", "tmb": 5}, {"identifier": "b2", "hrdHigh": True},
                           {"identifier": "b3", "lstHigh": True, "taiHigh": False}, {"identifier": "b4"},
                           {"identifier": "b5", "ploidy": 2, "taiHigh": True}]),
    "sbs-forms": lambda dk: _set(_mol(dk), sbsSignatures=[
        {"identifier": "g1", "version": "COSMIC v3.4", "name": ["SBS 06", "sbs6", "SBS7A", "  ", "Signature X"]},
        {"identifier": "g2", "name": ["SBS-13b"]},
        {"identifier": "g3", "name": ["Other"]},
        {"identifier": "g4", "name": []}]),
    "no-findings": lambda dk: dk.update(molecular={"complexBiomarkers": [{"identifier": "b"}], "sbsSignatures": [{"identifier": "s", "name": [" "]}]}),
    "no-primary": lambda dk: _set(dk["case"]["diagnosisOd"]["mainDiagnosis"], code=""),
}


@pytest.fixture(scope="module")
def mb():
    m = Matchbox(MB)
    assert push_maps(MB) == 0, "pushing the FML maps failed"
    return m


def _assert_clean(r):
    assert r["type"] == "Bundle", r
    assert r["content_errors_not_in_python"] == [], r["content_errors"]
    assert r["only_python"] == [] and r["only_fml"] == [], ([_brief(k) for k in r["only_python"]], [_brief(k) for k in r["only_fml"]])
    assert r["lookup_mismatch"] == [], r["lookup_mismatch"]


@pytest.mark.parametrize("f", FILES)
def test_onco_molecular(mb, f):
    if not (REPO / f).is_file():
        pytest.skip(f"{f} not in this checkout")
    r = check_file(f, mb)
    _assert_clean(r)
    assert r["equal"] >= 5
    first, second = r["ingest"][1], r["ingest"][2]
    assert first["ok"] and second["ok"], r["ingest"]
    assert second["new"] == 0 and set(second["statuses"]) == {"200"}, r["ingest"]


@pytest.mark.parametrize("mutation", sorted(MUTATIONS))
def test_onco_molecular_edge_cases(mb, mutation):
    f = FILES[0]
    if not (REPO / f).is_file():
        pytest.skip(f"{f} not in this checkout")
    dk = json.loads((REPO / f).read_text(encoding="utf-8"))
    MUTATIONS[mutation](dk)
    r = check_file(f, mb, ingest=mutation == "duplicate-ids", dk=dk, label=f"{f} [{mutation}]")
    _assert_clean(r)
    if mutation == "no-findings":
        assert r["molecular"] == 0
    if "ingest" in r:
        assert r["ingest"][1]["ok"] and r["ingest"][2]["ok"] and r["ingest"][2]["new"] == 0, r["ingest"]


# ---- wide corpus run ---------------------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="files, spread over the oncology manifest")
    ap.add_argument("--ingest", type=int, default=5, help="files ingested twice into HAPI")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not MB:
        sys.exit("set MB2027")
    mbx = Matchbox(MB)
    if not a.no_push:
        print("push failures:", push_maps(MB))
    manifest = json.loads((REPO / "genomde2fhir" / "tests" / "corpus_manifest.json").read_text())
    spread = _load("run_corpus", REPO / "scripts" / "run_corpus.py").spread
    results, tot = [], collections.Counter()
    for i, f in enumerate(a.files or spread(manifest["oncology"]["valid"], a.n)):
        r = check_file(f, mbx, ingest=i < a.ingest)
        results.append(r)
        tot["files"] += 1
        tot["bundles"] += r["type"] == "Bundle"
        for k in ("content_errors", "content_errors_not_in_python", "python_content_errors", "only_python", "only_fml",
                  "lookup_mismatch"):
            tot[k] += len(r.get(k, []))
        tot["molecular"] += r.get("molecular", 0)
        tot["equal"] += r.get("equal", 0)
        if "ingest" in r:
            tot["ingested"] += 1
            tot["ingest_ok"] += r["ingest"][1]["ok"] and r["ingest"][2]["ok"] and r["ingest"][2]["new"] == 0
        print(f"{r['file'][-60:]:60} {r['type']:16} mol={r.get('molecular')} err={len(r.get('content_errors', []))} "
              f"eq={r.get('equal')} py-only={len(r.get('only_python', []))} fml-only={len(r.get('only_fml', []))}"
              + (f" ingest={r['ingest'][1]['statuses']}/{r['ingest'][2]['statuses']} new2={r['ingest'][2]['new']}" if "ingest" in r else "")
              + ("" if r["type"] == "Bundle" else " " + r.get("error", "")[:300]), flush=True)
    print(dict(tot))
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1))
