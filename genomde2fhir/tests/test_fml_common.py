"""FML stage 'common': mappers/fml/DatenkranzCommon.map through the probe maps in mappers/fml/test.

Skipped unless MB2027 (matchbox-2027 base URL) is set; HAPI2027 defaults to http://localhost:8092/fhir.
For 3 files (one per branch): push the maps, $transform -> Bundle, zero content errors, graph-aware parity with the
Python converter on the resources DatenkranzCommon emits, and an idempotent double ingest into HAPI.

Wide run over the corpus:  MB2027=http://localhost:8091/matchboxv3/fhir python genomde2fhir/tests/test_fml_common.py --n 25
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
SM = "https://genomde.de/fhir/StructureMap/"
PROBES = {"oncology": SM + "CommonKdkOncologyProbe", "rare-disease": SM + "CommonKdkRareDiseaseProbe",
          "grz": SM + "CommonGrzProbe"}
MAPS = ["DatenkranzCommon.map", "CommonKdkOncologyProbe.map", "CommonKdkRareDiseaseProbe.map", "CommonGrzProbe.map",
        "CommonDatatypesProbe.map"]
FILES = {"oncology": "example-data/grz/synthetic-coverage-basis-via-pkv.json",
         "rare-disease": "example-data/rarediseases/RareDiseasesSubmission_06B1EE824EDF30E43FAA6FF4DCFC5E00FD9A772ACCE0E4AD0BC593F6834F6566.json",
         "grz": "example-data/grz/grz-edge-correction-multi-donor.json"}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _codes(cc_list):
    return {c.get("code") for cc in (cc_list if isinstance(cc_list, list) else [cc_list]) for c in (cc or {}).get("coding", [])}


def common_resource(r: dict, branch: str) -> bool:
    """Resources DatenkranzCommon emits (on the normalized canonical form: no meta, so decided on content)."""
    t = r.get("resourceType")
    if t == "Coverage":
        return True
    if t == "Consent":     # MV consent (patient-privacy) and the migrated MII Broad Consent (research)
        return bool({"patient-privacy", "research"} & _codes(r.get("scope")))
    if branch == "grz":
        return False          # GRZ Patients are built by DatenkranzGrzToMii, the probe only has placeholders
    if t == "Patient":
        return True
    if t == "CarePlan":
        return "indication-board" in _codes(r.get("category", []))
    return False


def parity(py_bundle: dict, fml_bundle: dict, branch: str):
    """(equal, only-python, only-fml) multisets of canonical resources restricted to the common resources."""
    rc = _load("run_corpus", REPO / "scripts" / "run_corpus.py")
    # label-only references: the Common probe maps emit placeholder GRZ Patients and Patients without the follow-up
    # deceased[x], so deep references (the target's content hash) would differ for Consent.patient etc.
    canonical = lambda b: rc.canonical(b, deep=False)  # noqa: E731

    def sub(b):
        out = collections.Counter()
        for k, v in canonical(b).items():
            r = json.loads(k)
            if common_resource(r, branch):
                if r.get("identifier") == []:    # harmless no-op: canonical() omits an emptied identifier list
                    r.pop("identifier")
                if r["resourceType"] == "Patient":   # set by the branch follow-up builders, not by Common
                    r.pop("deceasedDateTime", None)
                    r.pop("deceasedBoolean", None)
                out[json.dumps(r, sort_keys=True)] += v
        return out
    p, f = sub(py_bundle), sub(fml_bundle)
    return p & f, p - f, f - p


def push_maps(base: str) -> int:
    build = _load("build_mvgs", REPO / "scripts" / "build_mvgs.py")
    bad = 0
    for m in build.map_files(test_maps=True):
        if m.name in MAPS:
            st, body = build._send("POST", f"{base.rstrip('/')}/StructureMap", m.read_bytes(), "text/fhir-mapping")
            bad += st >= 300
    return bad


def hapi_count(rtype: str) -> int:
    """Uncached total (HAPI caches _summary=count searches; Hapi.count() can return a stale number)."""
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


def _md(dk):
    return dk["metaData"]


def _set(d, **kw):
    d.update(kw)
    return d


def _drop(d, *keys):
    for k in keys:
        d.pop(k, None)
    return d


def _rc(dk):
    return _md(dk)["researchConsents"][0]


def _scope(dk):
    return _rc(dk)["scope"]


def _rc_generic(dk):
    """Every element research_consent.KEEP carries over, with references into the sender's system."""
    s = _scope(dk)
    s.update(identifier=[{"system": "urn:x", "value": "c1", "assigner": {"reference": "Organization/7"}}], language="de",
             performer=[{"reference": "Patient/abc"}], organization=[{"reference": "Organization/1", "display": "UKT"}],
             sourceReference={"reference": "DocumentReference/9"}, policyRule={"text": "MII BC v1.6d"},
             policy=[{"uri": "2.16.840.1.113883.3.1937.777.24.2.2079", "authority": "1.2.276.0.76"}, {"uri": "http://example.org/p"}],
             verification=[{"verified": True, "verifiedWith": {"reference": "RelatedPerson/3"}, "verificationDate": "2025-02-11"}])
    s["extension"] += [{"url": "http://example.org/ext", "valueReference": {"reference": "Practitioner/1"}},
                       {"url": "http://example.org/nested", "extension": [{"url": "a", "valueString": "x"},
                                                                          {"url": "b", "valueReference": {"reference": "Device/2", "display": "dev"}}]}]
    s["extension"][0]["extension"][0]["valueReference"]["display"] = "MII Broad Consent study"   # DomainReference kept
    p = s["provision"]
    p.update(actor=[{"role": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType", "code": "PRCP"}]},
                     "reference": {"reference": "Organization/5"}}],
             data=[{"meaning": "instance", "reference": {"reference": "Observation/1"}}])
    p["provision"][0].update({"class": [{"system": "http://hl7.org/fhir/resource-types", "code": "Observation"}],
                              "purpose": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActReason", "code": "HRESCH"}],
                              "securityLabel": [{"system": "http://terminology.hl7.org/CodeSystem/v3-Confidentiality", "code": "R"}],
                              "dataPeriod": {"start": "2020-01-01"}})


CS_CONSENT = "https://www.medizininformatik-initiative.de/fhir/modul-consent/CodeSystem/"
# Edge cases the corpus lacks, applied to the oncology file (Python converts them with check_input=False)
MUTATIONS = {
    "ags-8-digits": lambda dk: _set(_md(dk), addressAGS="08416041"),
    "gender-other": lambda dk: _set(_md(dk), gender="other"),
    "gender-not-fhir": lambda dk: _set(_md(dk), gender="diverse"),
    "local-case-id": lambda dk: _set(_md(dk), localCaseId="CASE 7/a|b"),
    "no-presentation-date": lambda dk: _drop(_md(dk)["mvConsent"], "presentationDate"),
    "unusable-scope-entries": lambda dk: _md(dk)["mvConsent"]["scope"].extend([
        {"date": "2020-01-01", "domain": "notADomain", "type": "permit"},
        {"date": "2019-01-01", "domain": "reIdentification", "type": "maybe"}]),
    "no-usable-scope": lambda dk: _set(_md(dk)["mvConsent"], scope=[{"date": "2020-01-01", "domain": "x", "type": "permit"}]),
    "rejected": lambda dk: _set(_md(dk), decisionToInclude=False, rejectionJustification="probablyCommonDisease"),
    "rejected-unknown-reason": lambda dk: _set(_md(dk), decisionToInclude=False, rejectionJustification="nope"),
    "accepted-with-reason": lambda dk: _set(_md(dk), decisionToInclude=True, rejectionJustification="otherReason"),
    "no-decision": lambda dk: _drop(_md(dk), "decisionToInclude"),
    "no-decision-with-reason": lambda dk: _set(_drop(_md(dk), "decisionToInclude"), rejectionJustification="otherReason"),
    "no-board-date": lambda dk: _drop(_md(dk), "molecularBoardDecisionDate"),
    "coverage-skt": lambda dk: _set(_md(dk), coverageType="SKT"),
    "coverage-unk": lambda dk: _set(_md(dk), coverageType="UNK"),
    # embedded MII Broad Consent (DkResearchConsent = research_consent._migrate)
    "rc-all-elements": _rc_generic,
    "rc-embedded-date": lambda dk: (_drop(_rc(dk), "presentationDate"), _set(_scope(dk), dateTime="2025-03-01")),
    "rc-categories-missing": lambda dk: _set(_scope(dk), category=[
        {"coding": [{"system": "http://fhir.de/ConsentManagement/CodeSystem/ResultType", "code": "consent-status"}]}]),
    "rc-only-loinc": lambda dk: _set(_scope(dk), category=[{"coding": [{"system": "http://loinc.org", "code": "57016-8"}]},
                                                          {"coding": [{"system": "urn:y", "code": "z"}], "text": "t"}]),
    "rc-only-mii-2027": lambda dk: _set(_scope(dk), category=[{"coding": [
        {"system": CS_CONSENT + "mii-cs-consent-version-modules", "code": "2.16.840.1.113883.3.1937.777.24.2.184"}]}]),
    "rc-not-a-consent": lambda dk: _set(_rc(dk), scope={"resourceType": "Patient", "id": "p"}),
    "rc-no-status": lambda dk: _drop(_scope(dk), "status"),
    "rc-domain-reference-without-domain": lambda dk: _set(_scope(dk)["extension"][0],
                                                           extension=_scope(dk)["extension"][0]["extension"][1:]),
    "rc-provision-depth-3": lambda dk: _set(_scope(dk)["provision"]["provision"][0], provision=[
        {"type": "permit", "code": [{"coding": [{"system": "urn:x", "code": "deep"}]}]}]),
    "rc-several": lambda dk: _md(dk)["researchConsents"].extend([
        _set(json.loads(json.dumps(_rc(dk))), presentationDate="2025-06-01"),
        {"presentationDate": "2025-01-01", "noScopeJustification": "patient refuses to sign consent"}]),
}


def check_file(f: str, mb: Matchbox, ingest: bool = True, mutation: str | None = None) -> dict:
    dk = json.loads((REPO / f).read_text(encoding="utf-8"))
    if mutation:
        MUTATIONS[mutation](dk)
    py, rep = convert(dk, f, check_input=not mutation)
    st, fml = mb.transform(dk, PROBES[rep.branch])
    res = {"file": f + (f" [{mutation}]" if mutation else ""), "branch": rep.branch, "python": rep.status, "http": st,
           "type": fml.get("resourceType")}
    if py is None or fml.get("resourceType") != "Bundle":
        res["error"] = json.dumps(fml)[:400]
        return res
    v = validate_bundle(fml, mb)
    res["content_errors"] = [f"{r['type']}/{r['profile']}: {i['expression']} :: {i['text'][:200]}"
                             for r in v["resources"] for i in r["issues"] if i["class"] == "content"]
    eq, only_py, only_fml = parity(py, fml, rep.branch)
    res.update(equal=sum(eq.values()), only_python=list(only_py.elements()), only_fml=list(only_fml.elements()))
    if ingest:
        res["ingest"] = ingest_twice(fml)
    return res


# ---- pytest ------------------------------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(not MB, reason="MB2027 not set (matchbox-2027 base URL)")


@pytest.fixture(scope="module")
def mb():
    m = Matchbox(MB)
    assert push_maps(MB) == 0, "pushing DatenkranzCommon + probes failed"
    return m


@pytest.mark.parametrize("branch", sorted(FILES))
def test_common_groups(mb, branch):
    if not (REPO / FILES[branch]).is_file():
        pytest.fail(f"{FILES[branch]} not in this checkout")
    r = check_file(FILES[branch], mb)
    assert r["type"] == "Bundle", r
    assert r["content_errors"] == [], r["content_errors"]
    assert r["only_python"] == [] and r["only_fml"] == [], (r["only_python"], r["only_fml"])
    assert r["equal"] >= (2 if branch == "grz" else 4)
    first, second = r["ingest"][1], r["ingest"][2]
    assert first["ok"] and second["ok"], r["ingest"]
    assert second["new"] == 0 and set(second["statuses"]) == {"200"}, r["ingest"]


# content errors of the input itself, which Python carries over in the same way
EXPECTED_ERRORS = {  # mii-pr-consent-einwilligung allows 2 provision levels; the logical model declares 3
    "rc-provision-depth-3": "Consent.provision.provision.provision: max allowed = 0"}


@pytest.mark.parametrize("mutation", sorted(MUTATIONS))
def test_common_edge_cases(mb, mutation):
    if not (REPO / FILES["oncology"]).is_file():
        pytest.fail(f"{FILES['oncology']} not in this checkout")
    r = check_file(FILES["oncology"], mb, ingest=False, mutation=mutation)
    assert r["type"] == "Bundle", r
    assert [e for e in r["content_errors"] if EXPECTED_ERRORS.get(mutation, "\0") not in e] == [], r["content_errors"]
    assert r["only_python"] == [] and r["only_fml"] == [], (r["only_python"], r["only_fml"])


def test_common_datatypes(mb):
    """Dk datatype groups (CommonDatatypesProbe) == genomde2fhir.builders.common helpers."""
    from genomde2fhir.builders.common import coding, identifier, period, src_cc, src_coding
    if not (REPO / FILES["oncology"]).is_file():
        pytest.fail(f"{FILES['oncology']} not in this checkout")
    dk = json.loads((REPO / FILES["oncology"]).read_text(encoding="utf-8"))
    md, dx = dk["metaData"], dk["case"]["diagnosisOd"]["mainDiagnosis"]
    icd = "http://fhir.de/CodeSystem/bfarm/icd-10-gm"
    expected = {
        "coding": src_coding(dx), "coding-system": src_coding(dx, icd), "cc": src_cc(dx), "cc-system": src_cc(dx, icd),
        "code-coding": coding("http://hl7.org/fhir/administrative-gender", md["gender"]),
        "identifier": identifier("https://genomde.de/fhir/sid/tan-c", md["tanC"]),
        "period": period(md["mvConsent"]["presentationDate"], md["molecularBoardDecisionDate"]),
        "period-start": period(md["mvConsent"]["presentationDate"]),
        "period-end": period(end=md["mvConsent"]["presentationDate"]),
    }
    st, out = mb.transform(dk, SM + "CommonDatatypesProbe")
    assert out.get("resourceType") == "Parameters", out
    got = {p["name"]: next(v for k, v in p.items() if k.startswith("value")) for p in out["parameter"]}
    assert got == expected


# ---- wide corpus run ---------------------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25, help="files per branch, spread over the manifest")
    ap.add_argument("--ingest", type=int, default=3, help="files per branch ingested twice into HAPI")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not MB:
        sys.exit("set MB2027")
    mbx = Matchbox(MB)
    print("push failures:", push_maps(MB))
    manifest = json.loads((REPO / "genomde2fhir" / "tests" / "corpus_manifest.json").read_text())
    spread = _load("run_corpus", REPO / "scripts" / "run_corpus.py").spread
    results = []
    for br in ("oncology", "rare-disease", "grz"):
        tot = collections.Counter()
        for i, f in enumerate(spread(manifest[br]["valid"], a.n) if a.n else []):
            r = check_file(f, mbx, ingest=i < a.ingest)
            results.append(r)
            tot["files"] += 1
            tot["bundle"] += r["type"] == "Bundle"
            tot["content_err_files"] += bool(r.get("content_errors"))
            tot["equal"] += r.get("equal", 0)
            tot["diff_files"] += bool(r.get("only_python") or r.get("only_fml"))
            if "ingest" in r:
                tot["ingested"] += 1
                tot["ingest_ok"] += r["ingest"][1]["ok"] and r["ingest"][2]["ok"] and r["ingest"][2]["new"] == 0
            if r.get("error") or r.get("content_errors") or r.get("only_python") or r.get("only_fml"):
                print(json.dumps(r, indent=1)[:3000])
        print(br, dict(tot))
    tot = collections.Counter()
    for mu in MUTATIONS:
        r = check_file(FILES["oncology"], mbx, ingest=mu == "local-case-id", mutation=mu)
        results.append(r)
        tot["files"] += 1
        tot["bundle"] += r["type"] == "Bundle"
        tot["content_err_files"] += bool(r.get("content_errors"))
        tot["diff_files"] += bool(r.get("only_python") or r.get("only_fml"))
        if r.get("error") or r.get("content_errors") or r.get("only_python") or r.get("only_fml") or \
                ("ingest" in r and not (r["ingest"][1]["ok"] and r["ingest"][2]["new"] == 0)):
            print(json.dumps(r, indent=1)[:3000])
    print("edge cases", dict(tot))
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1))
