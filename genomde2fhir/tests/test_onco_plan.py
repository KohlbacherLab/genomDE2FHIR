"""onco.careplan / onco.recommendations: KDK OncologyPlan -> MTB Therapieplan + recommendations."""
from pathlib import Path

import pytest
from conftest import REPO, corpus, load, resources

from genomde2fhir.builders import patient
from genomde2fhir.builders.onco import careplan, recommendations
from genomde2fhir.context import Ctx
from genomde2fhir.data_access import mapping_rows
from genomde2fhir.identity import case_key

FIX = Path(__file__).parent / "fixtures" / "onco_plan"
FULL, FLAGS = FIX / "plan_full.json", FIX / "plan_flags_only.json"
MVGS_EXT = "https://genomde.de/fhir/StructureDefinition/"
PRIO = careplan.EX_PRIO
EVID = careplan.EX_EVIDENCE
PRIMARY = {"reference": "urn:uuid:00000000-0000-0000-0000-0000000000a1"}
# schema-valid corpus files in git (examples/) with therapy + study recommendations
EXAMPLES = sorted((REPO / "examples" / "oncology").glob("OncologySubmission_*.json"))[:4]


def run(dk, profile_set="2027", strict=True, variants=True):
    """Patient + plan builders only (primary tumour and variant references stubbed): independent of the
    diagnosis / molecular builders. Returns the Ctx."""
    ctx = Ctx(dk, "oncology", case_key(dk, "oncology"), profile_set, strict=strict)
    patient.build(ctx)
    ctx.refs["primary"] = PRIMARY
    if variants:
        for block in ("recommendedSystemicTherapies", "recommendedStudies"):
            for rec in (dk.get("plan") or {}).get(block) or []:
                for v in rec.get("variants") or []:
                    if v != "no-such-variant":
                        ctx.ids[("variant", v)] = {"reference": f"urn:uuid:variant-{v}"}
    careplan.build(ctx)
    recommendations.build(ctx)
    return ctx


def res(ctx, rtype=None, profile=None):
    return resources(ctx.bundle.bundle(), rtype, profile)


def ext_of(r, url):
    return [e for e in r.get("extension", []) if e["url"] == url]


def codes(concept):
    return [c["code"] for c in (concept or {}).get("coding", [])]


# ---- (a) corpus files -----------------------------------------------------------------------------------
@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name[19:31])
def test_corpus_example(path):
    dk = load(path)
    plan = dk["plan"]
    ctx = run(dk)
    cp = res(ctx, "CarePlan", "mii-pr-mtb-therapieplan")
    assert len(cp) == 1
    cp = cp[0]
    od = plan["carePlanOd"]
    assert cp["created"] == od["molecularBoardDecisionDate"]
    assert cp["intent"] == "plan" and cp["status"] == "active"
    assert cp["category"][0]["coding"][0]["system"] == careplan.CS_PLAN_TYPE
    assert cp["addresses"] == [PRIMARY]
    assert ctx.refs["careplan"]["reference"] == f"urn:uuid:{cp['id']}"

    therapies = plan.get("recommendedSystemicTherapies") or []
    mrs = res(ctx, "MedicationRequest", "mii-pr-mtb-therapieempfehlung")
    assert len(mrs) == sum(len(t["substances"]) for t in therapies)
    for t in therapies:
        ref = ctx.ids[("therapy_recommendation", t["identifier"])]
        mr = next(r for r in mrs if f"urn:uuid:{r['id']}" == ref["reference"])
        assert mr["identifier"][0]["value"].endswith("|" + t["identifier"])
        assert mr["authoredOn"] == od["molecularBoardDecisionDate"]
        assert ext_of(mr, PRIO)[0]["valuePositiveInt"] == t["priority"]
        assert codes(ext_of(mr, EVID)[0]["valueCodeableConcept"])[0] == t["evidenceLevel"]
        assert mr["reasonReference"][0] == PRIMARY                     # slice Primaertumor 1..1
        assert len(mr["reasonReference"]) == 1 + len(t.get("variants") or [])
        assert codes(mr["category"][0]) == [t["therapeuticStrategy"]]
        assert mr["medicationCodeableConcept"]["coding"][0]["code"] == t["substances"][0]["code"]["code"]
        use = ext_of(mr, MVGS_EXT + "mvgs-ex-recommendation-use-type")
        assert (use[0]["valueCoding"]["code"] if use else "unknown") == t["type"]

    studies = plan.get("recommendedStudies") or []
    srs = res(ctx, "ServiceRequest", "mii-pr-mtb-studieneinschluss-anfrage")
    assert len(srs) == len(studies)
    for s in studies:
        sr = next(r for r in srs if f"urn:uuid:{r['id']}" == ctx.ids[("study_recommendation", s["identifier"])]["reference"])
        assert sr["intent"] == "proposal" and codes(sr["code"]) == ["702475000"]
        assert ext_of(sr, PRIO)[0]["valuePositiveInt"] == s["priority"]
        assert codes(ext_of(sr, MVGS_EXT + "mvgs-ex-evidence-level")[0]["valueCodeableConcept"])[0] == s["evidenceLevel"]
        rs_ref = sr["supportingInfo"][0]["reference"]
        rs = next(r for r in res(ctx, "ResearchStudy") if f"urn:uuid:{r['id']}" == rs_ref)
        assert rs["identifier"][0] == {"system": careplan.REGISTER_SYSTEM[s["register"]], "value": s["id"]}
        assert rs.get("title") == careplan._real(s["name"]) and rs["status"] == "active"   # 'N/A' dropped (F20)

    n_flags = bool(od.get("counsellingRecommended")) + bool(od.get("reEvaluationRecommended"))
    other = set(od.get("otherRecommendations") or [])
    if od.get("interventionRecommended") and not od.get("suitableInterventions"):
        other.add("OP")
    assert len(cp["activity"]) == len(mrs) + len(srs) + n_flags + len(other)
    assert {codes(a["detail"]["code"])[0] for a in cp["activity"] if "detail" in a} == other
    assert len(res(ctx, "ServiceRequest", "humangenetische-beratung-auftrag")) == int(bool(od["counsellingRecommended"]))
    assert len(res(ctx, "ServiceRequest", "histologie-evaluation-auftrag")) == int(bool(od["reEvaluationRecommended"]))


def test_corpus_full_pipeline(convert_dk):
    """Integration: real primary tumour and variant Observations from the other builders."""
    path = EXAMPLES[0]
    bundle, rep = convert_dk(load(path), path.name)
    full = {e["fullUrl"] for e in bundle["entry"]}
    for mr in resources(bundle, "MedicationRequest", "mii-pr-mtb-therapieempfehlung"):
        assert all(r["reference"] in full for r in mr["reasonReference"])
    cp = resources(bundle, "CarePlan", "mii-pr-mtb-therapieplan")[0]
    assert all(a["reference"]["reference"] in full for a in cp["activity"] if "reference" in a)
    assert "plan.carePlanOd.molecularBoardDecisionDate" in rep.covered


def test_corpus_preventive_measures():
    files = [p for p in corpus("oncology") if (load(p).get("plan") or {}).get("preventiveMeasures")][:3]
    if not files:
        pytest.skip("no corpus file with preventiveMeasures in this checkout")
    for p in files:
        dk = load(p)
        ctx = run(dk)
        pms = [r for r in res(ctx, "ServiceRequest") if r.get("intent") == "plan"]
        assert len(pms) == len(dk["plan"]["preventiveMeasures"])
        for m in dk["plan"]["preventiveMeasures"]:
            assert ctx.ids[("preventive_measure", m["identifier"])]


# ---- (b) synthetic fixtures: enum values and edge cases ----------------------------------------------
def test_fixture_full_careplan_activities():
    ctx = run(load(FULL))
    cp = res(ctx, "CarePlan")[0]
    obds = [codes(a["detail"]["code"])[0] for a in cp["activity"] if "detail" in a]
    assert obds == ["WW", "AS", "WS", "OP", "ST", "KW", "SO"]           # all otherRecommendations, OP once
    assert all(a["detail"]["status"] == "not-started" for a in cp["activity"] if "detail" in a)
    refs = {a["reference"]["reference"] for a in cp["activity"] if "reference" in a}
    by_id = {f"urn:uuid:{r['id']}": r for r in res(ctx)}
    kinds = sorted({(by_id[r]["resourceType"], (by_id[r].get("meta", {}).get("profile") or ["-"])[0].split("/")[-1])
                    for r in refs})
    assert kinds == [("MedicationRequest", "mii-pr-mtb-therapieempfehlung"),
                     ("RequestGroup", "mii-pr-mtb-therapieempfehlung-kombination"),
                     ("ServiceRequest", "-"),
                     ("ServiceRequest", "mii-pr-mtb-histologie-evaluation-auftrag"),
                     ("ServiceRequest", "mii-pr-mtb-humangenetische-beratung-auftrag"),
                     ("ServiceRequest", "mii-pr-mtb-studieneinschluss-anfrage"),
                     ("ServiceRequest", "mii-pr-onko-therapieempfehlung-operation")]


def test_fixture_interventions():
    ctx = run(load(FULL))
    ops = res(ctx, "ServiceRequest", "therapieempfehlung-operation")
    assert len(ops) == 2
    op = ops[0]
    assert op["code"]["coding"][0] == {"system": "http://fhir.de/CodeSystem/bfarm/ops", "code": "5-870", "version": "2025",
                                       "display": "Partielle (brusterhaltende) Exzision der Mamma und Destruktion von Mammagewebe"}
    assert op["code"]["text"] == "Brusterhaltende Exzision" and op["intent"] == "proposal"
    flags = {e["url"]: e["valueBoolean"] for e in ext_of(op, MVGS_EXT + "mvgs-ex-intervention-purpose")[0]["extension"]}
    assert flags == {"therapeutic": False, "riskReducing": True}


def test_fixture_therapies():
    ctx = run(load(FULL))
    mr = lambda tid: next(r for r in res(ctx, "MedicationRequest")
                          if f"urn:uuid:{r['id']}" == ctx.ids[("therapy_recommendation", tid)]["reference"])
    # two substances -> two MedicationRequests grouped by a Kombination RequestGroup (code = strategy)
    rg = res(ctx, "RequestGroup", "therapieempfehlung-kombination")[0]
    assert len(rg["action"]) == 2 and codes(rg["code"]) == ["ZS"]
    assert ctx.ids[("therapy_recommendation_group", "th-inlabel")]["reference"] == f"urn:uuid:{rg['id']}"
    ev = ext_of(rg, EVID)[0]["valueCodeableConcept"]
    assert codes(ev) == ["m1A", "Z", "R"] and ev["text"] == "Zusatzverweis Z(FDA)"
    assert codes(mr("th-inlabel")["medicationCodeableConcept"]) == ["L01EC02"]
    # WHO ATC class + name; evidence 'undefined' is an MII code; unknown variant dropped
    off = mr("th-offlabel")
    assert off["medicationCodeableConcept"] == {"coding": [{"system": "http://www.whocc.no/atc", "code": "L01FX",
                                                            "version": "2025"}], "text": "Monoklonale Antikoerper"}
    assert codes(ext_of(off, EVID)[0]["valueCodeableConcept"]) == ["undefined", "is", "iv", "Z"]
    assert len(off["reasonReference"]) == 2
    assert ("plan.recommendedSystemicTherapies[].variants[]", "no-such-variant") in \
        [(p, v) for p, v, _ in ctx.report.dropped]
    # use types: 'unknown' -> extension omitted (dropped), others coded
    use = {t: (ext_of(mr(t), MVGS_EXT + "mvgs-ex-recommendation-use-type") or [{}])[0].get("valueCoding", {}).get("code")
           for t in ("th-inlabel", "th-offlabel", "th-compassionate", "th-unknown", "th-secprev")}
    assert use == {"th-inlabel": "inLabel", "th-offlabel": "offLabel", "th-compassionate": "compassionateUse",
                   "th-unknown": None, "th-secprev": "secPreventive"}
    assert ("plan.recommendedSystemicTherapies[].type", "unknown") in [(p, v) for p, v, _ in ctx.report.dropped]


def test_fixture_studies():
    ctx = run(load(FULL))
    studies = res(ctx, "ResearchStudy", "mii-pr-mtb-studie")
    assert len(studies) == 4                                   # NCT twice -> one study; unknown -> none
    ids = {(i.get("system"), i["value"]) for s in studies for i in s["identifier"]}
    assert ids == {(careplan.REGISTER_SYSTEM["NCT"], "NCT01234567"), (careplan.REGISTER_SYSTEM["DRKS"], "DRKS00012345"),
                   (careplan.REGISTER_SYSTEM["Eudra-CT/CTIS"], "2023-501234-12-00"), (None, "ISRCTN12345678")}
    nct = next(s for s in studies if s["identifier"][0]["value"] == "NCT01234567")
    assert nct["focus"][0] == {"coding": [{"system": "http://fhir.de/CodeSystem/bfarm/atc", "code": "L01EC02",
                                           "version": "2025", "display": "Dabrafenib"}], "text": "Dabrafenib"}
    sr = lambda sid: next(r for r in res(ctx, "ServiceRequest")
                          if f"urn:uuid:{r['id']}" == ctx.ids[("study_recommendation", sid)]["reference"])
    unknown = sr("st-unknown")
    # name 'unbekannt' and id 'n/a' are both placeholders (fix round 3, PLACEHOLDERS): no ResearchStudy and no note
    assert "supportingInfo" not in unknown and "note" not in unknown
    assert ("plan.recommendedStudies[].name", "unbekannt", "placeholder study name") in ctx.report.dropped
    assert sr("st-nct")["supportingInfo"][0] == sr("st-nct-dup")["supportingInfo"][0]
    assert len(sr("st-nct")["supportingInfo"]) == 2            # study + supporting variant
    ev = ext_of(sr("st-nct"), MVGS_EXT + "mvgs-ex-evidence-level")[0]["valueCodeableConcept"]
    assert codes(ev) == ["m1B", "Z"] and ev["text"] == "Zusatzverweis Z(FDA)"
    assert "plan.recommendedStudies[].register" in ctx.report.preserved          # 'other'


def test_fixture_preventive_measures():
    ctx = run(load(FULL))
    pm = [r for r in res(ctx, "ServiceRequest") if r["intent"] == "plan"]
    assert [r["code"]["text"] for r in pm] == ["Breast Imaging (MRI)", "Colonoscopy"]
    assert pm[0]["identifier"][0]["value"].endswith("|pm-1") and codes(pm[0]["category"][0]) == ["169443000"]
    assert ctx.ids[("preventive_measure", "pm-2")]["reference"] == f"urn:uuid:{pm[1]['id']}"


def test_fixture_flags_only():
    ctx = run(load(FLAGS))
    cp = res(ctx, "CarePlan")[0]
    assert [codes(a["detail"]["code"]) for a in cp["activity"] if "detail" in a] == [["OP"]]
    srs = res(ctx, "ServiceRequest")
    assert len(srs) == 1 and "studieneinschluss-anfrage" in srs[0]["meta"]["profile"][0]   # unspecific request
    assert not res(ctx, "MedicationRequest") and not res(ctx, "ResearchStudy")
    for k in ("studyRecommended", "counsellingRecommended", "reEvaluationRecommended", "interventionRecommended"):
        assert "plan.carePlanOd." + k in ctx.report.covered


def test_deterministic_ids_and_2026():
    a, b = run(load(FULL)), run(load(FULL))
    assert list(a.bundle.entries) == list(b.bundle.entries)
    c = run(load(FULL), profile_set="2026")
    assert len(c.bundle.entries) == len(a.bundle.entries)
    assert not [w for w in c.report.warnings if w[0] == "(profile)"]


def test_missing_primary_warns():
    dk = load(FLAGS)
    dk["plan"]["recommendedSystemicTherapies"] = load(FULL)["plan"]["recommendedSystemicTherapies"][2:3]
    ctx = Ctx(dk, "oncology", case_key(dk, "oncology"), "2027")
    patient.build(ctx)
    careplan.build(ctx)
    assert any("Primaertumor" in m for _, m in ctx.report.warnings)


# ---- (c) coverage of the mapping rows -----------------------------------------------------------------
def test_mapped_rows_covered():
    rows = {p: r for p, r in mapping_rows("oncology").items() if p.startswith("plan.")}
    handled = set()
    for f in [FULL, FLAGS, *EXAMPLES]:
        rep = run(load(f)).report
        handled |= rep.covered | rep.preserved
    missing = sorted(p for p, r in rows.items() if r["status"] == "MAPPED" and p not in handled)
    assert not missing, missing
    # DRAFT rows made mappable by REVIEW-TD A / REPRESENTATIONS (#3, #5, #15, #16) are handled too
    draft = sorted(p for p, r in rows.items() if r["status"] != "MAPPED" and p not in handled)
    assert not draft, draft


def test_edge_cases_single_flag_and_empty_substance():
    """One intervention flag only -> no (invalid) purpose extension, flag dropped not preserved;
    a therapy without coded/named substance -> no MedicationRequest and nothing covered for it."""
    dk = load(FLAGS)
    full = load(FULL)
    si = dict(full["plan"]["carePlanOd"]["suitableInterventions"][0])
    si.pop("interventionsIsRiskReducing")
    dk["plan"]["carePlanOd"]["suitableInterventions"] = [si]
    th = dict(full["plan"]["recommendedSystemicTherapies"][2], identifier="th-empty", substances=[{"code": {}}])
    dk["plan"]["recommendedSystemicTherapies"] = [th]
    ctx = run(dk, strict=False)
    op = res(ctx, "ServiceRequest", "therapieempfehlung-operation")[0]
    assert not ext_of(op, MVGS_EXT + "mvgs-ex-intervention-purpose")
    si_path = "plan.carePlanOd.suitableInterventions[].interventionIsTherapeutic"
    assert si_path not in ctx.report.preserved and si_path in [p for p, _, _ in ctx.report.dropped]
    assert not res(ctx, "MedicationRequest")
    assert ("plan.recommendedSystemicTherapies[].identifier", "th-empty") in [(p, v) for p, v, _ in ctx.report.dropped]
    assert "plan.recommendedSystemicTherapies[].priority" not in ctx.report.covered
