"""Fix round 2, group fml: the FML maps mirror the round-2 Python fixes and the reopened FML findings.

Offline (always run):
  - R69 (Python half): a priority written as an integral decimal (1.0, 1e0) keeps its extension; positiveInt range;
  - R46: no FML test input is a copy outside git (fixtures/fix_fml is gone, every input is tracked).
With MB2027 (matchbox-2027 base URL; HAPI2027 defaults to http://localhost:8092/fhir), every scenario converts on both
paths with zero differences under canonical() of scripts/run_corpus.py and no duplicate fullUrl / conditional URL, plus
scenario checks:
  - R43 meta.source on every FML resource = Python's; R06 genomic study key; R39 contained / urn:uuid / '#' canonicals;
  - R53 no '' inside the copied datatypes of the embedded Broad Consent; R69 integral-decimal priorities kept;
  - R11 combination member 0 carries '<id>' and '<id>:0'; R24 follow-up therapies told apart by substances; F12 note;
    R30 no Condition for a code empty after normalisation; F20 study substances as request notes;
  - RD-BASEDON the Seltene Therapieplan is basedOn the indication board;
  - R26 identifiers equal to a generated suffix keep separate keys (therapy, combination, study, preventive measure,
    GRZ labData); a remaining collision fails the transform like Python's 'duplicate resource'.
Inputs: tracked fixtures only, mutated inline."""
import collections
import copy
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "genomde2fhir" / "src"))
from genomde2fhir.convert import convert  # noqa: E402
from genomde2fhir.io import loads  # noqa: E402
from genomde2fhir.validate import Hapi, Matchbox  # noqa: E402

MB = os.environ.get("MB2027")
HAPI = os.environ.get("HAPI2027", "http://localhost:8092/fhir")
FX = REPO / "genomde2fhir" / "tests" / "fixtures"
PLAN = FX / "onco_plan/plan_full.json"                 # th-inlabel = combination L01EC02 + L01EE01
FU = FX / "onco_followup/followup_edge_cases.json"
SV = FX / "onco_variants/synthetic_small_variants.json"
CONSENT = FX / "consent/onco_edge.json"                # embedded MII Broad Consent + absence entries
RD = FX / "rd_plan_followup/rd_plan_followup_all_enums.json"
GRZ = FX / "grz_labdata/grz-labdata-rd-duo.json"
GRZL = FX / "grz_labdata/grz-labdata-onco-edge.json"
ATC = "http://fhir.de/CodeSystem/bfarm/atc"
PRIO = "mii-ex-mtb-empfehlung-prioritaet"
KDK_ID = "https://genomde.de/fhir/sid/kdk-object-id"
KEY = "https://genomde.de/fhir/sid/resource-key"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_RC = _load("run_corpus", REPO / "scripts" / "run_corpus.py")


def resources(bundle, rtype=None, profile=None):
    out = [e["resource"] for e in (bundle or {}).get("entry", [])]
    if rtype:
        out = [r for r in out if r["resourceType"] == rtype]
    if profile:
        out = [r for r in out if any(p.endswith(profile) for p in r.get("meta", {}).get("profile", []))]
    return out


def prio(bundle):
    return sorted(x["valuePositiveInt"] for r in resources(bundle) for x in r.get("extension", []) if x["url"].endswith(PRIO))


# ---- scenario builders ----------------------------------------------------------------------------------------------
def atc(code, **kw):
    return {"code": {"code": code, "system": ATC, "version": "2025"}, **kw}


def fu(date, *therapies):
    return {"followUpDate": date, "metachroneDiagnoses": False, "ecogPerformanceStatusScore": "1", "vitalStatus": "living",
            "therapies": list(therapies)}


def therapy(subs, end=None, reason=None, response=None, names=(), ref="th-inlabel", start="2025-11-11"):
    t = {"reference": ref, "therapyStartDate": start, "substances": [atc(s) for s in subs] + [{"name": n} for n in names]}
    if end:
        t["therapyEndDate"] = end
    if reason:
        t["terminationReasonOBDS"] = reason
    if response:
        t.update(therapyResponse=response, therapyResponseDate="2026-01-15")
    return t


A = dict(subs=["L01EC02"], end="2026-02-01", reason="A", response="PD")
B = dict(subs=["L01EE01"], end="2026-03-01", reason="E", response="CR")


def followups(*fus):
    def m(d):
        d["followUp"]["followUpOds"] = copy.deepcopy(list(fus))
    return m


def scope(mutate):
    def m(d):
        mutate(d["metaData"]["researchConsents"][0]["scope"])
    return m


def suffixed(path, k=0, key="identifier"):
    """[.., x, x, '<x>#<i>']: a copy of item k and an item whose identifier equals the suffix the copy gets."""
    def m(d):
        lst = d
        for p in path:
            lst = lst[p]
        lst.append(copy.deepcopy(lst[k]))
        x = copy.deepcopy(lst[k])
        x[key] = f"{lst[k][key]}#{len(lst) - 1}"
        lst.append(x)
    return m


QR = {"resourceType": "QuestionnaireResponse", "id": "qr", "status": "completed", "questionnaire": "#q"}
Q = {"resourceType": "Questionnaire", "id": "q", "status": "active"}
SENDER = "urn:uuid:0b6f3e3e-1111-4222-8333-444455556666"


def _rc_canonical(sc):
    sc["contained"] = [copy.deepcopy(QR), copy.deepcopy(Q), {"resourceType": "Organization", "id": "unused", "name": "x"}]
    sc["sourceReference"] = {"reference": "#qr"}
    sc["extension"].append({"url": "http://example.org/x", "valueCanonical": "#q3"})
    sc["contained"].append(dict(Q, id="q3"))


def _rc_backref(sc):
    sc["contained"] = [{"resourceType": "Provenance", "id": "signing", "target": [{"reference": "#"}],
                        "recorded": "2025-01-01T00:00:00Z", "agent": [{"who": {"display": "Studienzentrale"}}]},
                       {"resourceType": "Organization", "id": "unused", "name": "nobody"}]


def _rc_urn(sc):
    sc["performer"] = [{"reference": SENDER}, {"reference": "Practitioner/1", "display": "Dr X"}]
    sc["sourceReference"] = {"reference": SENDER}
    sc["extension"][0]["extension"][0]["valueReference"] = {"reference": SENDER}


def _rc_policy(sc):
    sc["contained"] = [dict(Q, id="q2")]
    sc["policy"] = sc.get("policy", []) + [{"uri": "#q2"}, {"uri": "#missing"}, {"authority": "#gone", "uri": "#q2"}]


def _rc_empties(sc):
    sc["policyRule"] = {"text": ""}
    sc["identifier"] = [{"type": {"text": ""}, "system": "urn:x", "value": "1", "period": {"start": ""}}]
    sc["provision"]["provision"][0]["code"][0]["text"] = ""
    sc["provision"]["provision"][1]["action"] = [{"text": ""}, {"coding": [{"code": "access", "display": ""}]}]
    sc["extension"] += [{"url": "http://example.org/s", "valueString": ""},
                        {"url": "http://example.org/q", "valueQuantity": {"value": 1, "unit": "mg"}},
                        {"url": "http://example.org/b", "valueBoolean": False}]
    sc["extension"][0]["extension"][1]["valueCoding"]["display"] = ""
    sc["extension"][0]["extension"][0]["valueReference"]["display"] = "Studie X"
    sc["sourceAttachment"] = {"title": "", "url": "http://example.org/doc", "contentType": ""}
    sc["provision"]["actor"] = [{"role": {"text": "", "coding": [
        {"system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType", "code": "PRCP"}]}, "reference": {"display": "Arzt"}}]
    sc["provision"]["securityLabel"] = [{"system": "", "code": "N"}]
    sc["provision"]["dataPeriod"] = {"start": "2025-01-01", "end": ""}


def _r30(d):
    _fu = d["followUp"]["followUpOds"][0]
    _fu["metachroneDiagnoses"] = True
    _fu["additionalDiagnoses"] = [
        {"system": "https://www.orpha.net", "code": "ORPHA:", "date": "2025-05-15"},
        {"system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "code": " ", "date": "2025-05-15"},
        {"code": "+", "date": "2025-05-15"}, {"system": "http://snomed.info/sct", "code": "  ", "date": "2025-05-16"},
        {"system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "code": "C187", "version": "2025", "date": "2025-05-15"}]


def _f12(d):
    fus = d["followUp"]["followUpOds"]
    t0, t1 = fus[0]["therapies"][0], fus[1]["therapies"][0]
    fus[2]["therapies"].append(copy.deepcopy(t1))
    t0["substances"] += [{"name": "Pruefsubstanz Q"}, {"name": "Pruefsubstanz R"}, {"name": "Pruefsubstanz S"}]
    t1["substances"] += [atc("L01XX99", name="Pruefsubstanz Q"),
                         {"code": {"code": "L01XX98", "system": ATC, "version": "2025", "display": "Pruefsubstanz R"}}]


def _f20(study):
    def m(d):
        d["plan"]["recommendedStudies"] = [{"identifier": "st-x", "evidenceLevel": "m3", "priority": 1, **study, "substances": [
            atc("L01EA01", name="Imatinib"), {"code": {"code": "L01XX01", "display": "Disp"}}, {"name": "OnlyName"},
            {"code": {"code": "L01XX02"}}]}]
    return m


def _prio(spelling):
    """priorities written with this JSON number spelling (therapy 1 and study 0 of the full plan)"""
    def text(raw):
        d = json.loads(raw)
        d["plan"]["recommendedSystemicTherapies"][1]["priority"] = 777777
        d["plan"]["recommendedStudies"][0]["priority"] = 888888
        return json.dumps(d).replace("777777", spelling).replace("888888", spelling)
    return text


def _colon_id(d):
    t = d["plan"]["recommendedSystemicTherapies"]
    c = copy.deepcopy(t[1])
    c["identifier"] = t[0]["identifier"] + ":1"   # the key of member 1 of combination t[0]
    t.append(c)


def _index_literal(d):
    t = d["plan"]["recommendedSystemicTherapies"]
    t[2]["identifier"] = "index-3"
    t[3].pop("identifier", None)


def _lab_noname(d):
    ld = d["donors"][0]["labData"]
    ld[0].pop("labDataName", None)
    ld.append(dict(copy.deepcopy(ld[1]), labDataName="#0"))


def _local_case_id(value, stype="initial"):
    def m(d):
        d["metaData"]["localCaseId"] = value
        d["metaData"]["submission"]["type"] = stype
    return m


# name -> (branch, input, mutation of the parsed input, or text -> text for number spellings)
SCENARIOS = {
    # R43 / R06 identity
    "R43-meta-source-escaped": ("oncology", SV, _local_case_id("a b%c|d\\e\tf")),
    "R43-meta-source-test": ("oncology", SV, _local_case_id("C1", "test")),
    "R43-meta-source-rd": ("rare-disease", RD, lambda d: None),
    "R43-meta-source-grz": ("grz", GRZ, lambda d: d["submission"].update(submissionType="followup", submissionDate="2026-05-01")),
    # R39 embedded Broad Consent
    "R39-canonical-contained": ("oncology", CONSENT, scope(_rc_canonical)),
    "R39-backref-contained": ("oncology", CONSENT, scope(_rc_backref)),
    "R39-sender-urn-uuid": ("oncology", CONSENT, scope(_rc_urn)),
    "R39-policy-missing-canonical": ("oncology", CONSENT, scope(_rc_policy)),
    "R39-policy-only-missing": ("oncology", CONSENT, scope(lambda sc: sc.update(policy=[{"uri": "#missing"}]))),
    # R53 empty strings inside copied datatypes
    "R53-empty-in-datatypes": ("oncology", CONSENT, scope(_rc_empties)),
    "R53-empty-policyrule": ("oncology", CONSENT, scope(lambda sc: (sc.pop("policy"), sc.update(
        policyRule={"text": "", "coding": [{"display": ""}]})))),
    # R69 integral decimals
    **{f"R69-priority-{s}": ("oncology", PLAN, _prio(s)) for s in ("1.0", "10.00", "1e0", "1.5e1", "15e-1", "2147483648")},
    # R11 / R24 / F12 / R30 / F20 oncology plan and follow-up
    "R24-split": ("oncology", PLAN, followups(fu("2026-03-10", therapy(**A), therapy(**B)))),
    "R24-split-reversed": ("oncology", PLAN, followups(fu("2026-03-10", therapy(**B), therapy(**A)))),
    "R24-subset-later": ("oncology", PLAN, followups(fu("2026-03-10", therapy(**A), therapy(**B)),
                                                     fu("2026-05-10", therapy(["L01EE01"], end="2026-04-01", reason="E")))),
    "R24-reverse-later": ("oncology", PLAN, followups(fu("2026-03-10", therapy(**A), therapy(**B)), fu(
        "2026-05-10", therapy(["L01EE01"], end="2026-04-01", reason="E"), therapy(["L01EC02"], end="2026-02-05", reason="A")))),
    "R24-exact-duplicate": ("oncology", PLAN, followups(fu("2026-03-10", therapy(**A), therapy(**A)))),
    "R24-ambiguous-later": ("oncology", PLAN, followups(fu("2026-03-10", therapy(**A), therapy(**B)), fu(
        "2026-05-10", therapy(["L01EC02", "L01EE01"], end="2026-04-01", reason="E")))),
    "R24-earlier-date-later-array": ("oncology", PLAN, followups(fu("2026-05-10", therapy(["L01EE01"], end="2026-04-01", reason="E")),
                                                                 fu("2026-03-10", therapy(**A), therapy(**B)))),
    "R24-superset-pair": ("oncology", PLAN, followups(fu("2026-03-10", therapy(**A), therapy(**B)), fu(
        "2026-05-10", therapy(["L01EC02", "L01XX99"], end="2026-04-01", reason="E", response="SD"), therapy(["L01EE01"], response="PR")))),
    "R24-names": ("oncology", PLAN, followups(fu("2026-03-10", therapy([], names=["Alpha"]), therapy([], names=["Beta"])),
                                              fu("2026-05-10", therapy([], names=["Beta", "Gamma"], end="2026-04-01")))),
    "R24-single-then-split": ("oncology", PLAN, followups(fu("2026-01-10", therapy(["L01EC02", "L01EE01"])),
                                                          fu("2026-03-10", therapy(**A), therapy(**B)),
                                                          fu("2026-05-10", therapy(["L01EC02"], end="2026-06-01", reason="E")))),
    "R24-same-date": ("oncology", PLAN, followups(fu("2026-03-10", therapy(**A), therapy(**B)),
                                                  fu("2026-03-10", therapy(["L01EE01"], end="2026-04-01", reason="E", response="PD")))),
    "R24-empty-substances": ("oncology", PLAN, followups(fu("2026-03-10", therapy([]), therapy([], response="PD")))),
    "F12-coded-in-between": ("oncology", FU, _f12),
    "R30-empty-after-normalisation": ("oncology", FU, _r30),
    "F20-placeholder-study": ("oncology", PLAN, _f20({"register": "other", "id": "", "name": "N/A"})),
    "F20-unknown-study": ("oncology", PLAN, _f20({"register": "yesButStudyIsUnknown", "id": "X-1", "name": "Some trial"})),
    # R26 identifiers equal to a generated suffix, a member key, or 'index-<i>'
    "R26-therapy-suffix-id": ("oncology", PLAN, suffixed(["plan", "recommendedSystemicTherapies"], 1)),
    "R26-combination-suffix-id": ("oncology", PLAN, suffixed(["plan", "recommendedSystemicTherapies"], 0)),
    "R26-study-suffix-id": ("oncology", PLAN, suffixed(["plan", "recommendedStudies"], 0)),
    "R26-preventive-suffix-id": ("oncology", PLAN, suffixed(["plan", "preventiveMeasures"], 0)),
    "R26-member-key-id": ("oncology", PLAN, _colon_id),
    "R26-index-literal-id": ("oncology", PLAN, _index_literal),
    "R26-grz-labdata-suffix-name": ("grz", GRZL, suffixed(["donors", 0, "labData"], 0, "labDataName")),
    "R26-grz-labdata-generated-name": ("grz", GRZL, _lab_noname),
}
INGEST = ["R26-therapy-suffix-id", "R26-grz-labdata-suffix-name", "R24-exact-duplicate"]


def scenario(name):
    branch, path, fn = SCENARIOS[name]
    raw = Path(path).read_text(encoding="utf-8")
    if name.startswith("R69-"):
        return branch, loads(fn(raw))
    dk = loads(raw)
    fn(dk)
    return branch, dk


# ---- offline -----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("spelling, kept", [("1", 1), ("1.0", 1), ("4.00", 4), ("1e0", 1), ("1.5e1", 15), ("100e-2", 1),
                                            ("2147483647", 2147483647), ("1.5", None), ("15e-1", None), ("0", None),
                                            ("0.0", None), ("2147483648", None), ("-1", None)])
def test_r69_integral_decimal_priority_kept_in_python(spelling, kept):
    dk = loads(_prio(spelling)(PLAN.read_text(encoding="utf-8")))
    py, rep = convert(dk, "prio", check_input=False)
    assert rep.status == "converted", rep.error
    base = loads(PLAN.read_text(encoding="utf-8"))
    for item in (base["plan"]["recommendedSystemicTherapies"][1], base["plan"]["recommendedStudies"][0]):
        item.pop("priority", None)
    without = prio(convert(base, "base", check_input=False)[0])
    assert prio(py) == sorted(without + ([kept, kept] if kept else []))
    dropped = [v for p, v, why in rep.dropped if p.endswith("priority")]
    assert (not dropped) if kept else len(dropped) == 2


def test_r46_fml_inputs_tracked_in_git():
    """No FML test reads a copy that git does not track (the synthData-v1 copies in fixtures/fix_fml are gone)."""
    assert not (FX / "fix_fml").exists()
    try:
        tracked = set(subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True, check=True).stdout.split())
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    import re
    for t in sorted((REPO / "genomde2fhir" / "tests").glob("test_fml_*.py")):
        for path in re.findall(r"\"((?:example-data|examples|genomde2fhir/tests/fixtures)/[^\"]+\.json)\"", t.read_text(encoding="utf-8")):
            assert path in tracked, f"{t.name}: {path} is not tracked by git"
    for _, path, _ in SCENARIOS.values():
        assert str(Path(path).relative_to(REPO)) in tracked, path


# ---- matchbox -----------------------------------------------------------------------------------------------------------
needs_mb = pytest.mark.skipif(not MB, reason="MB2027 not set (matchbox-2027 base URL)")


@pytest.fixture(scope="module")
def mb():
    build = _load("build_mvgs", REPO / "scripts" / "build_mvgs.py")
    assert build.push_maps(MB) == 0, "pushing the production maps failed"
    return Matchbox(MB)


def both(mb, name=None, branch=None, dk=None):
    if name:
        branch, dk = scenario(name)
    py, rep = convert(dk, name or "fix2", check_input=False)
    st, fml = mb.transform(dk, _RC.MAPS[branch])
    return py, rep, st, fml


def assert_parity(py, rep, st, fml):
    assert py is not None, (rep.status, rep.error)
    assert st < 300 and fml.get("resourceType") == "Bundle", (st, json.dumps(fml)[:600])
    a, b = _RC.canonical(py), _RC.canonical(fml)
    assert a == b, (sorted((a - b).elements())[:2], sorted((b - a).elements())[:2])
    for what in ("fullUrl", "request"):
        vals = collections.Counter(e[what] if what == "fullUrl" else e[what]["url"] for e in fml["entry"])
        assert not [v for v, n in vals.items() if n > 1], f"duplicate {what}"


@needs_mb
@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario_parity(mb, name):
    assert_parity(*both(mb, name))


@needs_mb
@pytest.mark.parametrize("name", [n for n in SCENARIOS if n.startswith("R43-")] + ["R24-split", "R39-canonical-contained"])
def test_r43_meta_source_on_every_resource(mb, name):
    py, _, _, fml = both(mb, name)
    want = {r.get("meta", {}).get("source") for r in resources(py) if r["resourceType"] != "Provenance"}
    assert len(want) == 1 and None not in want, want
    assert [r.get("meta", {}).get("source") for r in resources(fml)] == list(want) * len(resources(fml))
    assert " " not in next(iter(want)) and "\t" not in next(iter(want))


@needs_mb
def test_r06_correction_shares_the_initial_genomic_study(mb):
    def study_key(stype, date):
        dk = loads(GRZ.read_text(encoding="utf-8"))
        dk["submission"].update(submissionType=stype, submissionDate=date)
        _, _, st, fml = both(mb, branch="grz", dk=dk)
        assert st == 200
        [s] = [r for r in resources(fml, "Procedure") if r["meta"]["profile"][0].endswith("-genomic-study")]
        return next(i["value"] for i in s["identifier"] if i["system"] == KEY)
    initial = study_key("initial", "2026-01-01")
    assert study_key("correction", "2026-02-02") == initial       # a correction rewrites the initial study
    assert len({initial, study_key("followup", "2026-04-04"), study_key("addition", "2026-05-05")}) == 3


@needs_mb
def test_r39_contained_and_sender_references(mb):
    def con(name):
        _, _, _, fml = both(mb, name)
        return [r for r in resources(fml, "Consent") if r.get("scope", {}).get("coding", [{}])[0].get("code") == "research"][0]
    c = con("R39-canonical-contained")
    assert [x["id"] for x in c["contained"]] == ["qr", "q", "q3"] and c["sourceReference"] == {"reference": "#qr"}
    assert [x["id"] for x in con("R39-backref-contained")["contained"]] == ["signing"]
    c = con("R39-sender-urn-uuid")
    assert c["performer"][0] == {"display": f"{SENDER} (sender system)"} and "sourceReference" not in c
    assert not [x for x in c.get("extension", []) if x["url"].endswith("DomainReference")]
    c = con("R39-policy-missing-canonical")
    assert [p.get("uri") for p in c["policy"]][1:] == ["#q2", "#q2"] and "authority" not in c["policy"][2]
    c = con("R39-policy-only-missing")
    assert "policy" not in c and "profile" not in c["meta"] and c["policyRule"]["extension"][0]["valueCode"] == "unknown"


@needs_mb
def test_r53_no_empty_strings_in_the_embedded_consent(mb):
    for name in ("R53-empty-in-datatypes", "R53-empty-policyrule"):
        _, _, _, fml = both(mb, name)
        for c in resources(fml, "Consent"):
            assert '""' not in json.dumps(c), name
    _, _, _, fml = both(mb, "R53-empty-in-datatypes")
    c = [r for r in resources(fml, "Consent") if r.get("contained") is None and r.get("policy")][0]
    assert {"url": "http://example.org/q", "valueQuantity": {"value": 1, "unit": "mg"}} in c["extension"]
    assert {"url": "http://example.org/b", "valueBoolean": False} in c["extension"]


@needs_mb
def test_r69_integral_decimal_priorities_kept(mb):
    for spelling, kept in (("1.0", 1), ("10.00", 10), ("1e0", 1), ("1.5e1", 15), ("15e-1", None), ("2147483648", None)):
        py, _, st, fml = both(mb, f"R69-priority-{spelling}")
        assert st == 200 and prio(fml) == prio(py), spelling
        assert (prio(fml).count(kept) >= 2) if kept else True, (spelling, prio(fml))


@needs_mb
def test_r11_combination_member_zero_carries_the_plain_id(mb):
    dk = loads(PLAN.read_text(encoding="utf-8"))
    py, _, _, fml = both(mb, branch="oncology", dk=dk)
    for b in (py, fml):
        ids = sorted(tuple(i["value"].rsplit("|", 1)[1] for i in r.get("identifier", []) if i["system"] == KDK_ID)
                     for r in resources(b, "MedicationRequest") if any(i["value"].endswith("|th-inlabel:0") for i in r.get("identifier", [])))
        assert ids == [("th-inlabel", "th-inlabel:0")], ids


@needs_mb
def test_r24_follow_up_therapies_by_substances(mb):
    def procs(b):
        return sorted((r["status"], (r.get("performedPeriod") or {}).get("end")) for r in resources(b, "Procedure", "mii-pr-mtb-systemische-therapie"))
    _, _, _, a = both(mb, "R24-split")
    _, _, _, b = both(mb, "R24-split-reversed")
    assert procs(a) == procs(b) == [("completed", "2026-03-01"), ("stopped", "2026-02-01")]
    _, _, _, f = both(mb, "R24-exact-duplicate")
    assert len(resources(f, "Procedure", "mii-pr-mtb-systemische-therapie")) == 1
    assert len(resources(f, "Observation", "mvgs-therapy-response")) == 1
    _, _, _, f = both(mb, "R24-ambiguous-later")
    assert len(resources(f, "Procedure", "mii-pr-mtb-systemische-therapie")) == 3


@needs_mb
def test_f12_r30_f20_notes_and_conditions(mb):
    _, _, _, fml = both(mb, "F12-coded-in-between")
    proc = next(p for p in resources(fml, "Procedure", "mii-pr-mtb-systemische-therapie") if p["performedPeriod"]["start"] == "2025-03-01")
    note = " ".join(n["text"] for n in proc.get("note", []))
    assert "Pruefsubstanz S" in note and "Pruefsubstanz Q" not in note and "Pruefsubstanz R" not in note
    _, _, _, fml = both(mb, "R30-empty-after-normalisation")
    conds = [c for c in resources(fml, "Condition", "mii-pr-onko-diagnose-primaertumor") if c.get("recordedDate") in ("2025-05-15", "2025-05-16")]
    assert [c["code"]["coding"][0]["code"] for c in conds] == ["C18.7"]
    _, _, _, fml = both(mb, "F20-unknown-study")
    sr = next(r for r in resources(fml, "ServiceRequest", "studieneinschluss-anfrage")
              if any(i["value"].endswith("|st-x") for i in r.get("identifier", [])))
    assert [n["text"] for n in sr["note"]] == [
        "Empfohlene Studie (nicht identifiziert): Some trial X-1", "Studiensubstanz laut dieser Empfehlung: Imatinib (L01EA01)",
        "Studiensubstanz laut dieser Empfehlung: Disp (L01XX01)", "Studiensubstanz laut dieser Empfehlung: OnlyName",
        "Studiensubstanz laut dieser Empfehlung: (L01XX02)"]


@needs_mb
def test_rd_therapieplan_based_on_indication_board(mb):
    dk = loads(RD.read_text(encoding="utf-8"))
    assert dk["metaData"].get("molecularBoardDecisionDate")
    py, rep, st, fml = both(mb, branch="rare-disease", dk=dk)
    assert_parity(py, rep, st, fml)
    board = next(e["fullUrl"] for e in fml["entry"] if e["resource"].get("meta", {}).get("profile", [""])[0].endswith("mvgs-inclusion-decision"))
    [plan] = resources(fml, "CarePlan", "mii-pr-seltene-therapieplan")
    assert plan["basedOn"] == [{"reference": board}]
    dk["metaData"].pop("molecularBoardDecisionDate")
    _, _, _, fml = both(mb, branch="rare-disease", dk=dk)
    assert "basedOn" not in resources(fml, "CarePlan", "mii-pr-seltene-therapieplan")[0]


@needs_mb
def test_r26_remaining_collision_fails_on_both_paths(mb):
    dk = loads(SV.read_text(encoding="utf-8"))
    suffixed(["molecular", "smallVariants"], 0)(dk)          # Python: 'duplicate resource'
    py, rep, st, fml = both(mb, branch="oncology", dk=dk)
    assert py is None and "duplicate resource" in rep.error
    assert st >= 300 and "Check condition failed" in json.dumps(fml)


@needs_mb
@pytest.mark.parametrize("name", INGEST)
def test_ingest_twice_without_silent_merge(mb, name):
    _, _, st, fml = both(mb, name)
    assert st == 200
    hapi = Hapi(HAPI)
    for run in (1, 2):
        ok, resp = hapi.transaction(fml)
        assert ok, json.dumps(resp)[:300]
        statuses = [str((e.get("response") or {}).get("status", "")) for e in resp.get("entry", [])]
        assert len(statuses) == len(fml["entry"])
        if run == 2:
            assert all(s.startswith("200") for s in statuses), collections.Counter(statuses)
