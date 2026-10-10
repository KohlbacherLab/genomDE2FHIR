"""FML stage 'onco_plan_followup': mappers/fml/OncoPlanFollowUp.map (sub-map of DatenkranzOncologyToMii).

Skipped unless MB2027 (matchbox-2027 base URL) is set; HAPI2027 defaults to http://localhost:8092/fhir.
For 3 oncology inputs tracked in git (FILES: the full-plan fixture and two example-data files; a missing one fails,
it is never skipped): push the maps, $transform -> Bundle, no content error on the plan / follow-up resources that the
Python output of the same resources does not have, graph-aware parity with the Python converter on those resources
(onco/careplan.py, onco/followup.py, Patient.deceased[x]), and an idempotent double ingest into HAPI. Edge cases the
corpus lacks run as mutations of one file (ingest only for some); repeated identifiers / HPO codes
(test_onco_plan_followup_duplicate_ids) are compared with Python too: a repeated identifier is a further resource
('<id>#<i>'), never a 'duplicate resource' error.

Plan / follow-up resources are selected from both bundles by profile and graph: MTB Therapieplan, therapy
recommendations (+ Kombination), study inclusion requests, ResearchStudy, counselling / histology re-evaluation /
operation requests, preventive-measure ServiceRequests (SNOMED 169443000) and their results, Tod, Verlauf, Vitalstatus,
follow-up diagnoses (mii-pr-onko-diagnose-primaertumor), follow-up ECOG / HPO (dated), systemische Therapie with its
MedicationStatements and responses (partOf).

References are labelled by the target's type/profile over the WHOLE bundle (canonical() of scripts/run_corpus.py does
it over the passed entries only); conditional references 'T?identifier=<resource-key>|k' are resolved like HAPI does.
Normalised: references to molecular findings are dropped on the Python side when the FML bundle has no molecular
finding with that identifier (a guard from before OncoMolecular reached parity; the result counts how often it applies
as 'variant-refs-without-molecular'); an empty identifier list (resource key only). meta (profile, source, security)
and ids are not compared here; meta.source parity is test_fix2_fml.py (R43).

Wide run:  MB2027=http://localhost:8091/matchboxv3/fhir python genomde2fhir/tests/test_fml_onco_plan_followup.py --n 30
"""
import collections
import copy
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "genomde2fhir" / "src"))
from genomde2fhir.convert import convert  # noqa: E402
from genomde2fhir.validate import Matchbox, validate_bundle  # noqa: E402

MB = os.environ.get("MB2027")
MAP = "https://genomde.de/fhir/StructureMap/DatenkranzOncologyToMii"
KEY_SYS = "https://genomde.de/fhir/sid/resource-key"
FINDING_SYS = "https://genomde.de/fhir/sid/molecular-finding-id"
FILES = [  # full plan (preventive measures, counselling, studies, combinations), oncology (variant references, death),
           # DNPM (oBDS codes, follow-up); all tracked in git
    "genomde2fhir/tests/fixtures/onco_plan/plan_full.json",
    "example-data/oncology/OncologySubmission_2980C67615BFCCAC783BAB12CC54041D6D2EAE014112425D565A4F74E2860F05.json",
    "example-data/oncology/OncologySubmission_044AFF6262356F2F8EC60039DC08AE36FBAA011DE29740CBC83E9FA5643E4640.json",
]

PLAN_PROFILES = {
    "mii-pr-mtb-therapieplan", "mii-pr-mtb-therapieempfehlung", "mii-pr-mtb-therapieempfehlung-kombination",
    "mii-pr-mtb-studieneinschluss-anfrage", "mii-pr-mtb-studie", "mii-pr-mtb-humangenetische-beratung-auftrag",
    "mii-pr-mtb-histologie-evaluation-auftrag", "mii-pr-onko-therapieempfehlung-operation", "mii-pr-onko-tod",
    "mii-pr-onko-verlauf", "Vitalstatus", "mii-pr-onko-diagnose-primaertumor", "mii-pr-mtb-systemische-therapie",
}
DATED = {"mii-pr-onko-allgemeiner-leistungszustand-ecog", "mii-pr-seltene-hpo-assessment"}   # follow-up = has a date
PARTOF = {"mii-pr-mtb-systemtherapie-medication-statement", "mvgs-therapy-response"}          # partOf systemische-therapie
PM_RESULT_CS = "https://genomde.de/fhir/CodeSystem/mvgs-cs-preventive-measure-result"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SPINE = _load("test_fml_onco_spine", Path(__file__).parent / "test_fml_onco_spine.py")


def _profile(r):
    return (r.get("meta", {}).get("profile") or [""])[0].split("/")[-1]


def _key(r):
    return next((i.get("value") for i in r.get("identifier", []) if i.get("system") == KEY_SYS), None)


def resolver(bundle: dict):
    """reference string -> resource (urn:uuid fullUrls and HAPI-style conditional resource-key references)."""
    by_url = {e["fullUrl"]: e["resource"] for e in bundle.get("entry", [])}
    by_key = {(r["resourceType"], _key(r)): r for r in by_url.values() if _key(r)}

    def get(ref: str):
        if ref in by_url:
            return by_url[ref]
        if "?identifier=" + KEY_SYS + "|" in ref:
            t, k = ref.split("?identifier=" + KEY_SYS + "|", 1)
            return by_key.get((t, k))
        return None
    return get


def mine(bundle: dict) -> list:
    """Entries of the plan / follow-up resources."""
    get = resolver(bundle)
    out = []
    for e in bundle.get("entry", []):
        r, p = e["resource"], _profile(e["resource"])
        cats = r.get("category", [])
        codes = {c.get("code") for cat in (cats if isinstance(cats, list) else [cats]) for c in cat.get("coding", [])}
        sel = p in PLAN_PROFILES or (p in DATED and "effectiveDateTime" in r) \
            or (r["resourceType"] == "ServiceRequest" and "169443000" in codes) \
            or (r["resourceType"] == "Observation" and any(c.get("system") == PM_RESULT_CS for c in r.get("code", {}).get("coding", []))) \
            or (p in PARTOF and any(_profile(get(x.get("reference", "")) or {}) == "mii-pr-mtb-systemische-therapie"
                                    for x in r.get("partOf", [])))
        if sel:
            out.append(e)
    return out


def canonical(bundle: dict, entries: list, drop_refs: set = frozenset()) -> collections.Counter:
    """canonical() of scripts/run_corpus.py, with references labelled over the whole bundle, references in drop_refs
    removed, and stricter: only the narrative (resource-level 'text') is ignored, not CodeableConcept.text /
    Annotation.text (run_corpus.canonical drops every 'text' key)."""
    get = resolver(bundle)

    def label(r):
        return f"{r['resourceType']}/{_profile(r)}"

    def norm(o, top=False):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                if k in ("id", "meta") or (top and k == "text"):
                    continue
                if k == "reference" and isinstance(v, str):
                    tgt = get(v)
                    out[k] = label(tgt) if tgt else v.split("/")[0]
                elif k == "identifier" and isinstance(v, list):
                    ids = [i for i in v if KEY_SYS not in i.get("system", "")]
                    if ids:
                        out[k] = norm(ids)
                else:
                    out[k] = norm(v)
            return out
        if isinstance(o, list):
            keep = [x for x in o if not (isinstance(x, dict) and isinstance(x.get("reference"), str) and x["reference"] in drop_refs)]
            return sorted((norm(x) for x in keep), key=lambda x: json.dumps(x, sort_keys=True))
        return o
    c = collections.Counter()
    for e in entries:
        r = norm(e["resource"], top=True)
        c[json.dumps({k: v for k, v in r.items() if v not in ([], {})}, sort_keys=True, ensure_ascii=False)] += 1
    return c


def deceased(bundle: dict) -> dict:
    pat = next((e["resource"] for e in bundle.get("entry", []) if e["resource"]["resourceType"] == "Patient"), {})
    return {k: v for k, v in pat.items() if k.startswith("deceased")}


def parity(py: dict, fml: dict):
    """(equal, only-python, only-fml, normalised) multisets of canonical plan / follow-up resources."""
    fml_findings = {i["value"] for e in fml.get("entry", []) for i in e["resource"].get("identifier", [])
                    if i.get("system") == FINDING_SYS}
    drop = set()
    for e in py.get("entry", []):
        vals = {i["value"] for i in e["resource"].get("identifier", []) if i.get("system") == FINDING_SYS}
        if vals and not vals & fml_findings:
            drop.add(e["fullUrl"])
    used = sum(1 for e in mine(py) for x in json.dumps(e["resource"]).split('"reference": "')[1:]
               if x.split('"')[0] in drop)
    p, f = canonical(py, mine(py), drop), canonical(fml, mine(fml))
    return p & f, p - f, f - p, {"variant-refs-without-molecular": used}


def _uuidless(text: str) -> str:
    return re.sub(r"urn:uuid:[0-9a-f-]{36}", "urn:uuid:*", text)


def content_errors(bundle: dict, mb: Matchbox, dk: dict, select: list) -> list:
    """Content errors of the selected entries (validate_bundle over the whole bundle, rows mapped back to entries)."""
    v = validate_bundle(bundle, mb, source=dk)
    rows, i = v["resources"], 0
    sel = {id(e) for e in select}
    out = []
    for e in bundle.get("entry", []):
        n = len(e["resource"].get("meta", {}).get("profile") or [None])
        if id(e) in sel:
            for r in rows[i:i + n]:
                out += [f"{r['type']}/{(r['profile'] or '').split('/')[-1]}: {x['expression']} :: {_uuidless(x['text'])[:200]}"
                        for x in r["issues"] if x["class"] == "content"]
        i += n
    for r in rows[i:]:                                   # bundle-level row
        out += [f"Bundle: {x['expression']} :: {_uuidless(x['text'])[:200]}" for x in r["issues"] if x["class"] == "content"]
    return out


def check_file(f: str, mb: Matchbox, ingest: bool = True, dk: dict | None = None, label: str | None = None,
               validate: bool = True) -> dict:
    mutated = dk is not None
    dk = dk if mutated else json.loads((REPO / f).read_text(encoding="utf-8"))
    py, rep = convert(dk, f, check_input=not mutated)
    st, fml = mb.transform(dk, MAP)
    res = {"file": label or f, "python": rep.status, "http": st, "type": fml.get("resourceType")}
    if py is None or fml.get("resourceType") != "Bundle":
        res["error"] = json.dumps(fml)[:800] if fml.get("resourceType") != "Bundle" else f"python: {rep.error}"
        return res
    res["entries"] = len(fml.get("entry", []))
    res["mine"] = len(mine(fml))
    res["content_errors"] = content_errors(fml, mb, dk, mine(fml)) if validate else []
    if res["content_errors"]:
        py_errs = collections.Counter(x.split(" :: ")[0].split(":")[0] + " :: " + x.split(" :: ")[1]
                                      for x in content_errors(py, mb, dk, mine(py)))
        fml_errs = collections.Counter(x.split(" :: ")[0].split(":")[0] + " :: " + x.split(" :: ")[1] for x in res["content_errors"])
        res["python_content_errors"] = sorted(py_errs.elements())
        res["content_errors_not_in_python"] = sorted((fml_errs - py_errs).elements())
    else:
        res["python_content_errors"], res["content_errors_not_in_python"] = [], []
    eq, only_py, only_fml, norm = parity(py, fml)
    res.update(equal=sum(eq.values()), only_python=sorted(only_py.elements()), only_fml=sorted(only_fml.elements()),
               normalised=norm, deceased_python=deceased(py), deceased_fml=deceased(fml))
    if ingest:
        res["ingest"] = SPINE.ingest_twice(fml)
    return res


# ---- edge cases (applied to FILES[2], DNPM: plan with therapies / study, one follow-up) -----------------------------
ATC = "http://fhir.de/CodeSystem/bfarm/atc"


def _plan(dk):
    return dk["plan"]


def _fu(dk):
    return dk["followUp"]["followUpOds"]


def _sub(code, display=None, name=None, system=ATC):
    s = {"code": {"code": code, "system": system, "version": "2025"}} if code else {}
    if display:
        s.setdefault("code", {})["display"] = display
    if name:
        s["name"] = name
    return s


def m_combination(dk):
    t = _plan(dk)["recommendedSystemicTherapies"][0]
    t["substances"] = [_sub("L01XA01", "Cisplatin"), _sub(None, name="Foo"), _sub("L01BC02", name="5-FU",
                       system="https://www.wido.de/publikationen-produkte/analytik/arzneimittel-klassifikation/")]
    t["evidenceLevelDetails"] = ["Z(FDA)", "Z", "is", "xx"]
    t["type"], t["priority"], t["therapeuticStrategy"] = "inLabel", 0, "CIZ"
    _plan(dk)["recommendedSystemicTherapies"].append({"identifier": "only-names", "type": "unknown", "evidenceLevel": "m9",
                                                      "priority": 2, "therapeuticStrategy": "XX",
                                                      "substances": [_sub(None, name="Bar")]})
    _fu(dk)[0]["therapies"][0]["reference"] = t["identifier"]


def m_studies(dk):
    s0 = _plan(dk)["recommendedStudies"][0]
    _plan(dk)["recommendedStudies"] = [
        s0,
        dict(s0, identifier="st-2", priority=4, evidenceLevelDetails=["Z(FDA)"]),       # same study again: one ResearchStudy
        {"identifier": "st-3", "register": "yesButStudyIsUnknown", "name": "Basket", "id": "X-1", "evidenceLevel": "m3",
         "priority": 1, "variants": ["nope"]},
        {"identifier": "st-4", "register": "other", "name": "Local", "id": "LOC-7", "evidenceLevel": "undefined",
         "priority": 2, "substances": [_sub("L01XA01", "Cisplatin"), _sub(None, name="Foo"), {"code": {"code": "", "display": "Disp"}}]},
        {"identifier": "st-5", "register": "NCT", "name": "", "id": "NCT01234567", "evidenceLevel": "m1A", "priority": 3},
        {"identifier": "st-6", "register": "DRKS", "name": "Named only", "id": "", "evidenceLevel": "m1A", "priority": 3},
    ]
    _fu(dk)[0]["therapies"][0]["reference"] = "st-4"         # therapy from a study recommendation: note


def m_careplan_flags(dk):
    cp = _plan(dk)["carePlanOd"]
    cp.update(studyRecommended=True, counsellingRecommended=False, reEvaluationRecommended=True, interventionRecommended=True,
              otherRecommendations=["CH", "CH", "XX", "OP", "KW"], molecularBoardDecisionDate="")
    cp["suitableInterventions"] = [
        {"interventionIsTherapeutic": True, "interventionsIsRiskReducing": False,
         "type": {"code": {"system": "http://fhir.de/CodeSystem/bfarm/ops", "version": "2025", "code": "5-870", "display": "Mamma"},
                  "name": "Mastektomie"}},
        {"interventionIsTherapeutic": True,
         "type": {"code": {"system": "http://snomed.info/sct", "version": "x", "code": ""}, "name": "OP ohne Code"}}]
    _plan(dk)["recommendedStudies"] = []
    _plan(dk)["preventiveMeasures"] = [{"identifier": "pm-1", "type": "MRT Mamma"}, {"identifier": "pm-2", "type": ""}]


def m_intervention_flag_only(dk):
    cp = _plan(dk)["carePlanOd"]
    cp.update(interventionRecommended=True, otherRecommendations=[])
    cp.pop("suitableInterventions", None)


def m_followup_rich(dk):
    fu = _fu(dk)[0]
    fu.update(metachroneDiagnoses=True, vitalStatus="deceased", lastContactDate="2026-01-02", deathDate="2026-03-04",
              ecogPerformanceStatusScore="unknown",
              additionalDiagnoses=[{"code": "c50.9+", "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "version": "2025",
                                    "date": "2025-12-01", "display": "Brust"},
                                   {"code": "C61", "version": "2025", "date": "2025-12-02"}],
              phenotypes=[{"code": "HP:0001250", "change": "noLongerObserved", "text": "Seizure"},
                          {"code": "HP:0000001", "change": "foo", "version": "2025", "display": "All"},
                          {"code": "HP:0000002", "change": "newlyAdded"}],
              preventiveMeasures=[{"reference": "pm-x", "preventiveMeasureDate": "2026-01-05", "preventiveMeasureResult": "malignoma",
                                   "type": "Koloskopie"},
                                  {"reference": "", "preventiveMeasureDate": "", "preventiveMeasureResult": "noFindings"},
                                  {"reference": "pm-y", "preventiveMeasureDate": "2026-01-06", "preventiveMeasureResult": "bogus"}])
    t = fu["therapies"][0]
    t.update(terminationReasonOBDS="Q", therapyResponse="PR", therapyResponseDate="", therapyResponseSource="Arztbrief",
             substances=t["substances"] + [_sub(None, name="Foo"), _sub(None, name="Bar")])
    _plan(dk)["preventiveMeasures"] = [{"identifier": "pm-x", "type": "Koloskopie"}]


def m_followup_two(dk):
    """Two follow-ups: the therapy and a diagnosis are reported again (replaced), a substance only earlier, same date
    twice, deceased without a death date; the plan does not recommend the therapy (own identifier)."""
    fu0 = _fu(dk)[0]
    fu0.pop("deathDate", None)
    t0 = fu0["therapies"][0]
    t0.update(reference="own-therapy-1", therapyEndDate="", terminationReasonOBDS="")
    t0["substances"] = [_sub("L01XA01", "Cisplatin"), _sub("L01BC02", "Fluorouracil")]
    t0.pop("therapyResponse", None)
    fu0.update(metachroneDiagnoses=True, additionalDiagnoses=[{"code": "C61", "version": "2025", "date": "2025-12-02"}])
    fu1 = copy.deepcopy(fu0)      # same diagnosis again (keyed by code + date): the later report replaces it
    fu1.update(vitalStatus="deceased", ecogPerformanceStatusScore="5", metachroneDiagnoses=False)
    fu1.pop("lastContactDate", None)
    t1 = fu1["therapies"][0]
    t1.update(therapyEndDate="2026-05-01", terminationReasonOBDS="E")
    t1["substances"] = [_sub("L01XA01", "Cisplatin-neu", name="Cis")]
    _fu(dk).append(fu1)


def m_no_plan(dk):
    """Follow-up submission without plan: logical causedBy / basedOn; no primary tumour (no Verlauf, flag on Vitalstatus)."""
    dk.pop("plan", None)
    dk["case"]["diagnosisOd"]["mainDiagnosis"]["code"] = ""
    fu = _fu(dk)[0]
    fu.update(vitalStatus="living", lastContactDate="2026-02-10", metachroneDiagnoses=True,
              preventiveMeasures=[{"reference": "pm-1", "preventiveMeasureDate": "2026-01-05", "preventiveMeasureResult": "unclear"}])


def m_therapy_repeated(dk):
    """The same therapy (reference + start) twice in one follow-up, the copy with cisplatin added: two Procedures told
    apart by their substances (onco.followup._FollowUp.therapy_id, never the array index), each with its own
    response."""
    fu = _fu(dk)[0]
    t = copy.deepcopy(fu["therapies"][0])
    t["therapyResponse"] = "CR"
    t["substances"] = t["substances"] + [_sub("L01XA01", "Cisplatin")]
    fu["therapies"].append(t)


def m_followup_identical_therapy(dk):
    """A later follow-up repeats the therapy unchanged (an identical JSON object): one Procedure, MedicationStatement
    and response."""
    fu1 = copy.deepcopy(_fu(dk)[0])
    fu1.update(followUpDate="2026-06-01", vitalStatus="deceased", deathDate="2026-05-30")
    _fu(dk).append(fu1)


def m_special_chars(dk):
    """URL-unsafe local ids (space, &, |, %) in recommendation / therapy references: base64url resource keys."""
    t0 = _plan(dk)["recommendedSystemicTherapies"][0]
    t0["identifier"] = "rec 1&x|%"
    _fu(dk)[0]["therapies"][0]["reference"] = "rec 1&x|%"
    _plan(dk)["recommendedStudies"][0]["id"] = "DRKS 0001&|%"


MUTATIONS = {f.__name__[2:]: f for f in (m_combination, m_studies, m_careplan_flags, m_intervention_flag_only,
                                          m_followup_rich, m_followup_two, m_no_plan, m_therapy_repeated,
                                          m_followup_identical_therapy, m_special_chars)}


def m_duplicate_ids(dk):
    """A KDK identifier twice in the therapy, study and preventive-measure arrays, an HPO code twice in one follow-up."""
    for k in ("recommendedSystemicTherapies", "recommendedStudies"):
        _plan(dk)[k].append(dict(copy.deepcopy(_plan(dk)[k][0]), priority=4))
    _plan(dk)["preventiveMeasures"] = [{"identifier": "a", "type": "x"}, {"identifier": "a", "type": "y"}]
    _fu(dk)[0]["phenotypes"] = [{"code": "HP:0000001", "change": "improved"}, {"code": "HP:0000001", "change": "degraded"}]


# ---- pytest ------------------------------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(not MB, reason="MB2027 not set (matchbox-2027 base URL)")


@pytest.fixture(scope="module")
def mb():
    m = Matchbox(MB)
    assert SPINE.push_maps(MB) == 0, "pushing the FML maps failed"
    return m


def _assert_parity(r):
    assert r["only_python"] == [] and r["only_fml"] == [], (r["only_python"], r["only_fml"])
    assert r["deceased_python"] == r["deceased_fml"], (r["deceased_python"], r["deceased_fml"])


@pytest.mark.parametrize("f", FILES)
def test_onco_plan_followup(mb, f):
    if not (REPO / f).is_file():
        pytest.fail(f"{f} not in this checkout")
    r = check_file(f, mb)
    assert r["type"] == "Bundle", r
    assert r["content_errors_not_in_python"] == [], r["content_errors"]
    _assert_parity(r)
    assert r["equal"] >= 3
    first, second = r["ingest"][1], r["ingest"][2]
    assert first["ok"] and second["ok"], r["ingest"]
    assert second["new"] == 0 and set(second["statuses"]) == {"200"}, r["ingest"]


@pytest.mark.parametrize("mutation", sorted(MUTATIONS))
def test_onco_plan_followup_edge_cases(mb, mutation):
    f = FILES[2]
    if not (REPO / f).is_file():
        pytest.fail(f"{f} not in this checkout")
    dk = json.loads((REPO / f).read_text(encoding="utf-8"))
    MUTATIONS[mutation](dk)
    r = check_file(f, mb, ingest=mutation in ("studies", "followup_two", "special_chars"), dk=dk, label=f"{f} [{mutation}]")
    assert r["type"] == "Bundle", r
    assert r["content_errors_not_in_python"] == [], r["content_errors"]
    _assert_parity(r)
    if "ingest" in r:
        first, second = r["ingest"][1], r["ingest"][2]
        assert first["ok"] and second["ok"], r["ingest"]
        assert second["new"] == 0 and set(second["statuses"]) == {"200"}, r["ingest"]


def test_onco_plan_followup_duplicate_ids(mb):
    """A repeated identifier is a further recommendation / measure (careplan._rid '<id>#<i>'), a repeated HPO code a
    further assessment (followup '<code>#<j>'): parity with Python, every conditional PUT URL of the Bundle is unique,
    and the Bundle validates."""
    f = FILES[2]
    if not (REPO / f).is_file():
        pytest.fail(f"{f} not in this checkout")
    dk = json.loads((REPO / f).read_text(encoding="utf-8"))
    m_duplicate_ids(dk)
    st, fml = mb.transform(dk, MAP)
    assert fml.get("resourceType") == "Bundle", fml
    urls = [e["request"]["url"] for e in fml["entry"]]
    assert len(urls) == len(set(urls)), [u for u in set(urls) if urls.count(u) > 1]
    r = check_file(f, mb, ingest=True, dk=dk, label=f"{f} [duplicate_ids]")
    assert r["content_errors_not_in_python"] == [], r["content_errors"]
    _assert_parity(r)
    assert r["ingest"][2]["new"] == 0 and set(r["ingest"][2]["statuses"]) == {"200"}, r["ingest"]


# ---- wide corpus run ---------------------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="files, spread over the oncology manifest")
    ap.add_argument("--ingest", type=int, default=5, help="files ingested twice into HAPI")
    ap.add_argument("--files", nargs="*", help="explicit files instead of the spread")
    ap.add_argument("--mutations", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--validate", type=int, default=10 ** 6, help="validate only the first N files")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not MB:
        sys.exit("set MB2027")
    mbx = Matchbox(MB)
    if not a.no_push:
        print("push failures:", SPINE.push_maps(MB))
    manifest = json.loads((REPO / "genomde2fhir" / "tests" / "corpus_manifest.json").read_text())
    spread = _load("run_corpus", REPO / "scripts" / "run_corpus.py").spread
    files = a.files or spread(manifest["oncology"]["valid"], a.n)
    jobs = [(f, None, f) for f in files]
    if a.mutations:
        for name, fn in MUTATIONS.items():
            dk = json.loads((REPO / FILES[2]).read_text(encoding="utf-8"))
            fn(dk)
            jobs.append((FILES[2], dk, f"[{name}]"))
    results, tot = [], collections.Counter()
    for i, (f, dk, label) in enumerate(jobs):
        r = check_file(f, mbx, ingest=i < a.ingest, dk=dk, label=label, validate=i < a.validate)
        results.append(r)
        tot["files"] += 1
        tot["bundles"] += r["type"] == "Bundle"
        tot["mine"] += r.get("mine", 0)
        tot["content_errors"] += len(r.get("content_errors", []))
        tot["content_errors_not_in_python"] += len(r.get("content_errors_not_in_python", []))
        tot["equal"] += r.get("equal", 0)
        tot["only_python"] += len(r.get("only_python", []))
        tot["only_fml"] += len(r.get("only_fml", []))
        tot["deceased_diff"] += r.get("deceased_python") != r.get("deceased_fml")
        for k, v in (r.get("normalised") or {}).items():
            tot["norm:" + k] += v
        if "ingest" in r:
            tot["ingested"] += 1
            tot["ingest_ok"] += r["ingest"][1]["ok"] and r["ingest"][2]["ok"] and r["ingest"][2]["new"] == 0
        print(f"{r['file'][-60:]:60} {r['type']:16} mine={r.get('mine')} errors={len(r.get('content_errors', []))}"
              f"/{len(r.get('content_errors_not_in_python', []))} eq={r.get('equal')} "
              f"py-only={len(r.get('only_python', []))} fml-only={len(r.get('only_fml', []))}"
              + (f" ingest={r['ingest'][1]['statuses']}/{r['ingest'][2]['statuses']} new2={r['ingest'][2]['new']}" if "ingest" in r else "")
              + (f" ERROR {r.get('error')}" if r.get("error") else ""))
    print(dict(tot))
    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=1, ensure_ascii=False))
