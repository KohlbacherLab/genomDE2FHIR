"""FML integration: all production maps in mappers/fml/ together, against the Python converter, per branch.

Skipped unless MB2027 (matchbox-2027 base URL) is set; HAPI2027 defaults to http://localhost:8092/fhir.

For one file per branch (oncology, rare disease, GRZ) the test
  1. pushes every production map (scripts/build_mvgs.py push_maps, imported maps first);
  2. $transforms the raw file with the branch's main map and requires a transaction Bundle;
  3. validates the Bundle (validate_bundle, classified with the source file like the Python path) and requires that
     it has no content error the Python output of the same file does not have;
  4. checks graph-aware parity (canonical() from scripts/run_corpus.py: ids, resource-key identifiers, Provenance
     ignored) on the *declared shape* of the file: exact equality, see declared_shape();
  5. requires exact parity on the raw file too (the properties the logical model still leaves undeclared are read by
     neither converter);
  6. POSTs the FML Bundle to HAPI twice: both 2xx, the second answers only 200 and creates no resource.

Why the declared shape. matchbox drops every property the logical model (mvgs-ig/input/StructureDefinition-
Datenkranz*.json) does not declare when it parses the input (engine quirk Q6), so the maps cannot see them. The non-schema
keys that Python reads (the pre-1.6.5 legacy keys case.priorRd, case.priorDiagnostic and plan.*.variantReferences,
genes[].display, germlineDiagnoses[].date and the embedded Broad Consent researchConsents[].scope) are declared as
extras of the logical models (scripts/schema_to_logical.py EXTRAS). declared_shape() renames the legacy keys to their
schema names (as the Python builders treat them) and removes every property the model does not declare (FHIR datatype
elements of the extras are kept whole), so both converters get the same input. The raw-file differences are listed in
mappers/fml/README.md 'Parity with the Python converter'.

Wide run (also what docs/E2E-REPORT-2027.md's FML row is checked against):
  MB2027=http://localhost:8091/matchboxv3/fhir python genomde2fhir/tests/test_fml_integration.py --n 20 --ingest 5
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
MAPS = {"oncology": "https://genomde.de/fhir/StructureMap/DatenkranzOncologyToMii",
        "rare-disease": "https://genomde.de/fhir/StructureMap/DatenkranzRareDiseaseToMii",
        "grz": "https://genomde.de/fhir/StructureMap/DatenkranzGrzToMii"}
MODELS = {"oncology": "DatenkranzOncology", "rare-disease": "DatenkranzRareDisease", "grz": "DatenkranzGrz"}
FILES = {  # one per branch, each with non-schema properties (legacy keys / extras, exercises declared_shape)
    "oncology": "example-data/oncology/OncologySubmission_2980C67615BFCCAC783BAB12CC54041D6D2EAE014112425D565A4F74E2860F05.json",
    "rare-disease": "example-data/rarediseases/RareDiseasesSubmission_06B1EE824EDF30E43FAA6FF4DCFC5E00FD9A772ACCE0E4AD0BC593F6834F6566.json",
    "grz": "example-data/synthData-v1/grz/submission/synth_submission_005.json",
}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_RC = _load("run_corpus", REPO / "scripts" / "run_corpus.py")
_DECLARED = {}


def declared(branch: str) -> dict:
    """{element path below the root: type code} of the logical model (schema elements and declared extras)."""
    if branch not in _DECLARED:
        sd = json.loads((REPO / "mvgs-ig" / "input" / f"StructureDefinition-{MODELS[branch]}.json").read_text())
        _DECLARED[branch] = {e["path"].split(".", 1)[1]: e["type"][0]["code"] for e in sd["differential"]["element"]
                             if "." in e["path"]}
    return _DECLARED[branch]


def _opaque(code: str) -> bool:
    """A FHIR datatype element (the extras of the embedded Broad Consent): matchbox parses its content itself."""
    return code not in ("BackboneElement", "string", "integer", "decimal", "boolean")


def declared_shape(dk: dict, branch: str) -> dict:
    """The input as the maps see it once the logical model declares the schema keys: legacy keys renamed to their
    schema names (as the Python builders treat them), every property the logical model does not declare removed."""
    dk = copy.deepcopy(dk)
    case = dk.get("case") if isinstance(dk.get("case"), dict) else {}
    if branch == "rare-disease" and "priorRd" in case and "priorRds" not in case:
        v = case.pop("priorRd")
        case["priorRds"] = v if isinstance(v, list) else [v]
    if branch == "oncology" and isinstance(case.get("priorDiagnostic"), dict):
        case["priorDiagnostics"] = (case.get("priorDiagnostics") or []) + [case.pop("priorDiagnostic")]
    for k in ("recommendedTherapies", "recommendedStudies"):
        for r in (dk.get("plan") or {}).get(k) or []:
            if isinstance(r, dict) and "variantReferences" in r and "variants" not in r:
                r["variants"] = r.pop("variantReferences")
    names = declared(branch)

    def walk(o, p):
        if isinstance(o, dict):
            for k in list(o):
                q = f"{p}.{k}" if p else k
                if q not in names:
                    o.pop(k)
                    continue
                if not _opaque(names[q]):
                    walk(o[k], q)
        elif isinstance(o, list):
            for x in o:
                walk(x, p)
    walk(dk, "")
    return dk


def undeclared_paths(dk: dict, branch: str) -> list[str]:
    names, out = declared(branch), set()

    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                q = f"{p}.{k}" if p else k
                if q not in names:
                    out.add(q)
                elif not _opaque(names[q]):
                    walk(v, q)
        elif isinstance(o, list):
            for x in o:
                walk(x, p)
    walk(dk, "")
    return sorted(out)


def _strip_empty(o):
    """canonical() leaves 'identifier': [] when the resource key was the only identifier."""
    if isinstance(o, dict):
        return {k: _strip_empty(v) for k, v in o.items() if v != []}
    if isinstance(o, list):
        return [_strip_empty(x) for x in o]
    return o


def parity(py_bundle: dict, fml_bundle: dict):
    """(equal, only-python, only-fml) multisets of canonical resources over the whole Bundle."""
    def sub(b):
        return collections.Counter({json.dumps(_strip_empty(json.loads(k)), sort_keys=True): v
                                    for k, v in _RC.canonical(b).items()})
    p, f = sub(py_bundle), sub(fml_bundle)
    return p & f, p - f, f - p


def content_errors(bundle: dict, mb: Matchbox, source: dict) -> collections.Counter:
    """Content errors as '<type>/<profile tail>: <expression without indices> :: <text without urn:uuids>'."""
    v = validate_bundle(bundle, mb, source=source)
    out = collections.Counter()
    for r in v["resources"]:
        for i in r["issues"]:
            if i["class"] == "content":
                expr = re.sub(r"\[\d+\]", "[]", re.sub(r"^Bundle\.entry\[\d+\]\.resource/\*\w+/[^*]*\*/", "", i["expression"]))
                text = re.sub(r"urn:uuid:[0-9a-f-]{36}", "urn:uuid:*", i["text"][:200])
                out[f"{r['type']}/{(r['profile'] or '').split('/')[-1]}: {expr} :: {text}"] += 1
    return out


def push_maps(base: str) -> int:
    build = _load("build_mvgs", REPO / "scripts" / "build_mvgs.py")
    return build.push_maps(base)


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


def check(f: str, branch: str, mb: Matchbox, ingest: bool = False, validate: bool = True) -> dict:
    raw = json.loads((REPO / f).read_text(encoding="utf-8"))
    res = {"file": f, "branch": branch, "undeclared": undeclared_paths(raw, branch)}
    # raw file: what a site actually sends
    py, rep = convert(raw, f)
    st, fml = mb.transform(raw, MAPS[branch])
    res.update(python=rep.status, http=st, type=fml.get("resourceType"))
    if py is None or fml.get("resourceType") != "Bundle":
        res["error"] = json.dumps(fml)[:600] if fml.get("resourceType") != "Bundle" else rep.error
        return res
    res["entries"], res["python_entries"] = len(fml["entry"]), len(py["entry"])
    fe, pe = (content_errors(fml, mb, raw), content_errors(py, mb, raw)) if validate else ({}, {})
    fe, pe = collections.Counter(fe), collections.Counter(pe)
    res["content_errors"] = sorted(fe.elements())
    res["python_content_errors"] = sorted(pe.elements())
    res["content_errors_not_in_python"] = sorted((fe - pe).elements())
    eq, only_py, only_fml = parity(py, fml)
    res.update(raw_equal=sum(eq.values()), raw_only_python=sorted(only_py.elements()),
               raw_only_fml=sorted(only_fml.elements()))
    # declared shape: both converters see the same input
    ds = declared_shape(raw, branch)
    if ds == raw:
        res.update(equal=res["raw_equal"], only_python=res["raw_only_python"], only_fml=res["raw_only_fml"])
    else:
        py2, _ = convert(ds, f, check_input=False)
        st2, fml2 = mb.transform(ds, MAPS[branch])
        if fml2.get("resourceType") != "Bundle":
            res["error"] = "declared shape: " + json.dumps(fml2)[:600]
            return res
        eq, only_py, only_fml = parity(py2, fml2)
        res.update(equal=sum(eq.values()), only_python=sorted(only_py.elements()), only_fml=sorted(only_fml.elements()))
    if ingest:
        res["ingest"] = ingest_twice(fml)
    return res


# ---- pytest ------------------------------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(not MB, reason="MB2027 not set (matchbox-2027 base URL)")


@pytest.fixture(scope="module")
def mb():
    assert push_maps(MB) == 0, "pushing the production maps failed"
    return Matchbox(MB)


@pytest.mark.parametrize("branch", sorted(FILES))
def test_integration(mb, branch):
    f = FILES[branch]
    if not (REPO / f).is_file():
        pytest.skip(f"{f} not in this checkout")
    r = check(f, branch, mb, ingest=True)
    assert r["type"] == "Bundle", r
    assert r["content_errors_not_in_python"] == [], r["content_errors_not_in_python"]
    assert r["only_python"] == [] and r["only_fml"] == [], (r["only_python"], r["only_fml"])
    assert r["raw_only_python"] == [] and r["raw_only_fml"] == [], (r["raw_only_python"], r["raw_only_fml"])
    assert r["equal"] >= 10
    first, second = r["ingest"][1], r["ingest"][2]
    assert first["ok"] and second["ok"], r["ingest"]
    assert second["new"] == 0 and set(second["statuses"]) == {"200"}, r["ingest"]


def test_maps_load_in_import_order():
    build = _load("build_mvgs", REPO / "scripts" / "build_mvgs.py")
    names = [m.name for m in build.map_files()]
    assert names[0] == "DatenkranzCommon.map"
    assert names.index("OncoMolecular.map") < names.index("DatenkranzOncologyToMii.map")
    assert names.index("OncoPlanFollowUp.map") < names.index("DatenkranzOncologyToMii.map")


# ---- wide corpus run ---------------------------------------------------------------------------------------
def _label(s: str) -> str:
    r = json.loads(s)
    code = ((r.get("code") or {}).get("coding") or [{}])[0].get("code")
    return f"{r['resourceType']}|{code}" if code else r["resourceType"]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="files per branch, spread over the manifest (-1 = all)")
    ap.add_argument("--ingest", type=int, default=3, help="files per branch ingested twice into HAPI")
    ap.add_argument("--branches", default="oncology,rare-disease,grz")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--no-validate", action="store_true", help="transform, parity and ingest only (fast)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not MB:
        sys.exit("set MB2027")
    mbx = Matchbox(MB)
    if not a.no_push:
        print("push failures:", push_maps(MB))
    manifest = json.loads((REPO / "genomde2fhir" / "tests" / "corpus_manifest.json").read_text())
    results = []
    for br in a.branches.split(","):
        files = sorted(manifest[br]["valid"])
        files = files if a.n < 0 else _RC.spread(files, a.n)
        tot, raw_diff, ds_diff, undecl = (collections.Counter() for _ in range(4))
        for i, f in enumerate(files):
            r = check(f, br, mbx, ingest=i < a.ingest, validate=not a.no_validate)
            results.append(r)
            tot["files"] += 1
            tot["bundle"] += r["type"] == "Bundle"
            tot["fml_content_errors"] += len(r.get("content_errors", []))
            tot["python_content_errors"] += len(r.get("python_content_errors", []))
            tot["content_errors_not_in_python"] += len(r.get("content_errors_not_in_python", []))
            tot["raw_equal_files"] += not (r.get("raw_only_python") or r.get("raw_only_fml"))
            tot["declared_equal_files"] += not (r.get("only_python") or r.get("only_fml"))
            tot["equal_resources"] += r.get("raw_equal", 0)
            undecl.update(r["undeclared"])
            for side in ("python", "fml"):
                raw_diff.update(f"{side:6} {_label(x)}" for x in r.get(f"raw_only_{side}", []))
                ds_diff.update(f"{side:6} {_label(x)}" for x in r.get(f"only_{side}", []))
            if "ingest" in r:
                tot["ingested"] += 1
                i1, i2 = r["ingest"][1], r["ingest"][2]
                tot["ingest_ok"] += i1["ok"] and i2["ok"] and i2["new"] == 0 and set(i2["statuses"]) == {"200"}
            if r.get("error") or r.get("content_errors_not_in_python") or r.get("only_python") or r.get("only_fml") \
                    or ("ingest" in r and r["ingest"][2]["new"]):
                print(json.dumps({k: v for k, v in r.items() if k not in ("raw_only_python", "raw_only_fml")},
                                 indent=1)[:4000])
        print(f"== {br}: {dict(tot)}")
        print("   undeclared properties:", dict(undecl.most_common()))
        print("   raw differences:", dict(raw_diff.most_common(25)))
        print("   declared-shape differences:", dict(ds_diff.most_common(25)))
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1))
