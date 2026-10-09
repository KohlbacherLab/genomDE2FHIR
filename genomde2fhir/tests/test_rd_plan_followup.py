"""rd.careplan + rd.followup: Seltene Therapieplan, recommendations, follow-up resources."""
import csv
from pathlib import Path

import pytest

from conftest import REPO, corpus, load, resources

FIX = Path(__file__).parent / "fixtures" / "rd_plan_followup"
SELTENE = "https://www.medizininformatik-initiative.de/fhir/ext/modul-seltene/"
CS_STRATEGY = SELTENE + "CodeSystem/mii-cs-seltene-therapieempfehlung-strategie"
CS_TYPE = SELTENE + "CodeSystem/mii-cs-seltene-therapieempfehlung-typ"
CS_CHANGE = SELTENE + "CodeSystem/mii-cs-seltene-hpo-change-status"
CS_PLAN_REC = "https://genomde.de/fhir/CodeSystem/mvgs-cs-rd-plan-recommendation"
P_MED = "mii-pr-seltene-therapieempfehlung"
P_NONMED = "mii-pr-seltene-therapieempfehlung-nicht-medikamentoes"
MED_STRATEGIES = {"systemic-medication", "targeted-medication", "prevention-medication", "gene-therapy", "combination"}
NONMED_STRATEGIES = {"prophylactic", "early-detection", "nutrition", "other"}
PREFIXES = ("plan.carePlanRd.", "plan.recommendedStudies[].", "plan.recommendedTherapies[].", "followUp.followUpRds[].")


def by_id(bundle):
    return {e["fullUrl"]: e["resource"] for e in bundle["entry"]}


def has_profile(r, name):
    return any(p.endswith("/" + name) for p in r.get("meta", {}).get("profile", []))


def codes(cc_, system):
    return [c["code"] for c in (cc_ or {}).get("coding", []) if c.get("system") == system]


def strategy_of(r):
    return next(c for cat in r.get("category", []) for c in codes(cat, CS_STRATEGY))


@pytest.fixture(scope="module")
def fixture_runs():
    from genomde2fhir import convert
    out = {}
    for name in ("rd_plan_followup_all_enums", "rd_plan_followup_minimal"):
        bundle, rep = convert(load(FIX / f"{name}.json"), name, "2027", strict=True)
        assert rep.status == "converted", rep.error
        out[name] = (bundle, rep)
    return out


@pytest.fixture(scope="module")
def corpus_runs():
    from genomde2fhir import convert
    files = corpus("rare-disease")[:4]
    assert len(files) >= 3
    out = []
    for f in files:
        bundle, rep = convert(load(f), str(f), "2027")
        assert rep.status == "converted", rep.error
        out.append((load(f), bundle, rep))
    return out


# ---- corpus -------------------------------------------------------------------------------------
def test_corpus_careplan_and_recommendations(corpus_runs):
    for dk, bundle, _ in corpus_runs:
        plan = dk["plan"]
        cps = [r for r in resources(bundle, "CarePlan") if has_profile(r, "mii-pr-seltene-therapieplan")]
        assert len(cps) == 1
        cp = cps[0]
        assert cp["created"] == plan["carePlanRd"]["molecularBoardDecisionDate"]
        assert cp["intent"] == "proposal" and cp["subject"]["reference"].startswith("urn:uuid:")
        flag_codes = {c for a in cp["activity"] if "detail" in a for c in codes(a["detail"]["code"], CS_PLAN_REC)}
        assert "study-inclusion" in flag_codes and "therapy" in flag_codes
        activity_refs = {a["reference"]["reference"] for a in cp["activity"] if "reference" in a}
        idx = by_id(bundle)
        for rt in plan["recommendedTherapies"]:
            recs = [r for r in idx.values()
                    if any(i.get("value", "").endswith("|" + rt["identifier"]) for i in r.get("identifier", []))]
            assert len(recs) == 1
            rec = recs[0]
            strat = strategy_of(rec)
            if strat in MED_STRATEGIES:
                assert rec["resourceType"] == "MedicationRequest" and has_profile(rec, P_MED)
                assert rec["medicationCodeableConcept"]["extension"][0]["valueCode"] == "unknown"
            else:
                assert rec["resourceType"] == "ServiceRequest" and has_profile(rec, P_NONMED)
                assert rec["code"]["text"]
            assert codes(next(c for c in rec["category"] if codes(c, CS_TYPE)), CS_TYPE) == [rt["type"]]
            # variants resolved to the converted variant Observations
            assert rec["reasonReference"] and all(r["reference"] in idx for r in rec["reasonReference"])
            assert any(f"urn:uuid:{rec['id']}" == a for a in activity_refs)
        for rs in plan["recommendedStudies"]:
            req = next(r for r in resources(bundle, "ServiceRequest", "studieneinschluss-anfrage")
                       if r["identifier"][0]["value"].endswith("|" + rs["identifier"]))
            assert req["intent"] == "proposal"
            assert req["code"]["coding"][0]["code"] == "702475000"
            study = idx[req["supportingInfo"][0]["reference"]]
            assert study["resourceType"] == "ResearchStudy" and study["identifier"][0]["value"] == rs["id"]
            assert "title" not in study          # corpus names are the placeholder "N/A"


def test_corpus_followups(corpus_runs):
    for dk, bundle, rep in corpus_runs:
        fus = dk["followUp"]["followUpRds"]
        vit = resources(bundle, "Observation", "modul-person/StructureDefinition/Vitalstatus")
        assert len(vit) == len(fus)
        assert {v["valueCodeableConcept"]["coding"][0]["code"] for v in vit} == \
               {{"living": "L", "deceased": "T"}[f["vitalStatus"]] for f in fus}
        n_ph = sum(len(f["phenotypes"]) for f in fus)
        fu_hpo = [o for o in resources(bundle, "Observation", "mii-pr-seltene-hpo-assessment")
                  if o.get("component", [{}])[0].get("interpretation")]
        assert len(fu_hpo) == n_ph
        for o in fu_hpo:
            assert o["code"]["coding"][0]["system"] == "http://human-phenotype-ontology.org"
        cis = resources(bundle, "ClinicalImpression", "mii-pr-seltene-clinical-impression")
        assert cis and cis[0]["summary"] == fus[0]["diseaseProgression"]
        pat = resources(bundle, "Patient")[0]
        if any(f.get("deathDate") for f in fus):
            assert pat["deceasedDateTime"] == max(f["deathDate"] for f in fus if f.get("deathDate"))


# ---- synthetic fixture: enums and edge cases ------------------------------------------------------
def test_fixture_strategy_split(fixture_runs):
    bundle, rep = fixture_runs["rd_plan_followup_all_enums"]
    meds = [r for r in resources(bundle, "MedicationRequest") if has_profile(r, P_MED)]
    nonmeds = [r for r in resources(bundle, "ServiceRequest") if has_profile(r, P_NONMED)]
    assert {strategy_of(r) for r in meds} == MED_STRATEGIES
    assert {strategy_of(r) for r in nonmeds} == NONMED_STRATEGIES
    for r in meds + nonmeds:   # 2027 slicing by coding.system: exactly one coding per category, unversioned CS
        assert all(len(c["coding"]) == 1 and "version" not in c["coding"][0] for c in r["category"])
        assert not any("Evidenzgraduierung" in e.get("url", "") or "evidenzgraduierung" in e.get("url", "")
                       for e in r.get("extension", []))
    other = next(r for r in nonmeds if strategy_of(r) == "other")
    assert other["code"]["text"] == "Physiotherapie"
    assert any("Physiotherapie" in n["text"] for n in other["note"])
    comb = next(r for r in meds if strategy_of(r) == "combination")
    assert any("Enzymersatz" in n["text"] for n in comb["note"])
    assert ("plan.recommendedTherapies[].variants[]", "no-such-variant",
            "variant id not found among the converted variants") in rep.dropped


def test_fixture_studies(fixture_runs):
    bundle, rep = fixture_runs["rd_plan_followup_all_enums"]
    studies = resources(bundle, "ResearchStudy", "mii-pr-studie-studie")
    systems = {s["identifier"][0].get("system") for s in studies}
    assert "https://www.medizininformatik-initiative.de/fhir/modul-mtb/sid/nct" in systems
    assert "https://www.medizininformatik-initiative.de/fhir/modul-studie/sid/drks" in systems
    assert "https://www.medizininformatik-initiative.de/fhir/modul-studie/sid/eudract" in systems
    other = next(s for s in studies if not s["identifier"][0].get("system"))   # register 'other'
    assert other["identifier"][0] == {"type": {"text": "Studienregister: other"}, "value": "LOC-77"}
    assert "plan.recommendedStudies[].register" in rep.preserved
    # duplicate NCT study shared; unknown studies and the DRKS entry without id/name get no ResearchStudy
    assert len(studies) == 4
    reqs = resources(bundle, "ServiceRequest", "studieneinschluss-anfrage")
    assert len(reqs) == 8
    req = {r["identifier"][0]["value"].rsplit("|", 1)[-1]: r for r in reqs}
    assert "supportingInfo" not in req["rdpf-study-unknown"] and "note" not in req["rdpf-study-unknown"]
    named = req["rdpf-study-unknown-named"]
    assert "supportingInfo" not in named
    assert named["note"][0]["text"] == "Empfohlene Studie (nicht identifiziert): Basket trial for ciliopathies"
    assert "supportingInfo" not in req["rdpf-study-noid"]
    assert req["rdpf-study-nct"]["supportingInfo"] == req["rdpf-study-nct-dup"]["supportingInfo"]
    assert any(s.get("title") == "Gene therapy trial X" for s in studies)
    dropped = {(p, v) for p, v, _ in rep.dropped}
    assert ("plan.recommendedStudies[].register", "DRKS") in dropped          # register without study id
    assert ("plan.recommendedStudies[].id", "unknown") in dropped              # placeholder id
    assert ("plan.recommendedStudies[].register", "yesButStudyIsUnknown") not in dropped


def test_fixture_duplicate_identifier(fixture_runs):
    bundle, rep = fixture_runs["rd_plan_followup_all_enums"]
    dup = [r for r in resources(bundle) if any(i.get("value", "").endswith("|rdpf-ther-4") for i in r.get("identifier", []))]
    assert len(dup) == 2 and len({r["id"] for r in dup}) == 2
    assert any("duplicate recommendation identifier" in m for _, m in rep.warnings)


def test_fixture_careplan_activities(fixture_runs):
    bundle, _ = fixture_runs["rd_plan_followup_all_enums"]
    cp = resources(bundle, "CarePlan", "mii-pr-seltene-therapieplan")[0]
    flag_codes = [c for a in cp["activity"] if "detail" in a for c in codes(a["detail"]["code"], CS_PLAN_REC)]
    assert "genetic-counselling" not in flag_codes             # counsellingRecommended = false
    assert {"study-inclusion", "re-evaluation", "therapy"} <= set(flag_codes)
    assert {"gp", "specialist", "localCrd", "otherCrd", "diseaseSpecificAmbulatoryCare",
            "universityAmbulatoryCare", "otherAmbulatoryCare"} <= set(flag_codes)
    assert all(not ("detail" in a and "reference" in a) for a in cp["activity"])   # cpl-3
    n_refs = sum(1 for a in cp["activity"] if "reference" in a)
    assert n_refs >= 10 + 8                                      # 10 therapies + 8 study requests (+ bag items)
    assert cp["addresses"]


def test_fixture_minimal_plan(fixture_runs):
    bundle, rep = fixture_runs["rd_plan_followup_minimal"]
    cp = resources(bundle, "CarePlan", "mii-pr-seltene-therapieplan")[0]
    assert not any("detail" in a for a in cp.get("activity", []))
    for p in ("studyRecommended", "counsellingRecommended", "reEvaluationRecommended", "therapyRecommended",
              "clinicalManagementRecommended"):
        assert "plan.carePlanRd." + p in rep.covered
    pat = resources(bundle, "Patient")[0]
    assert pat["deceasedBoolean"] is True and "deceasedDateTime" not in pat
    cond = next(r for r in resources(bundle, "Condition") if "genetic-diagnosis" in r["meta"]["profile"][0])
    assert codes(cond["verificationStatus"], "http://terminology.hl7.org/CodeSystem/condition-ver-status") == ["confirmed"]
    assert any(p == "followUp.followUpRds[].diagnosisEstablished" and "not overwritten" in m for p, m in rep.warnings)


def test_fixture_followups(fixture_runs):
    bundle, rep = fixture_runs["rd_plan_followup_all_enums"]
    hpo = [o for o in resources(bundle, "Observation", "mii-pr-seltene-hpo-assessment")
           if o.get("component", [{}])[0].get("interpretation")]
    assert len(hpo) == 10
    change = {o["component"][0]["interpretation"][0]["coding"][0]["code"] for o in hpo}
    assert change == {"newly-added", "improved", "degraded", "no-longer-observed", "unchanged"}
    for o in hpo:
        c = o["component"][0]
        assert c["code"]["coding"][0]["code"] == "260411009"
        present = c["valueCodeableConcept"]["coding"][0]["code"]
        assert present == ("LA9634-2" if codes(c["interpretation"][0], CS_CHANGE) == ["no-longer-observed"] else "LA9633-4")
    full = next(o for o in hpo if o["code"].get("text") == "palm finding")
    assert full["code"]["coding"][0] == {"system": "http://human-phenotype-ontology.org", "code": "HP:0100871",
                                         "version": "2025-10-22", "display": "Abnormal palm morphology"}
    assert full["derivedFrom"]                                  # baseline assessment of the same HPO term

    gm = [o for o in resources(bundle, "Observation") if codes(o.get("code"), "http://snomed.info/sct") == ["707621005"]]
    fu_levels = {o["valueCodeableConcept"]["coding"][0]["code"] for o in gm if "effectiveDateTime" in o
                 and o["effectiveDateTime"] >= "2026-05"}
    assert fu_levels == {"LA16552-4", "LA15151-6", "LA15150-8", "LA16556-5", "LA16558-1"}
    assert "followUp.followUpRds[].gmfcs" in rep.preserved

    vit = resources(bundle, "Observation", "modul-person/StructureDefinition/Vitalstatus")
    assert [v["valueCodeableConcept"]["coding"][0]["code"] for v in sorted(vit, key=lambda v: v["effectiveDateTime"])] \
        == ["L", "L", "L", "L", "T"]
    assert resources(bundle, "Patient")[0]["deceasedDateTime"] == "2026-09"

    cis = sorted(resources(bundle, "ClinicalImpression"), key=lambda c: c["effectiveDateTime"])
    assert len(cis) == 5
    assert [bool(c.get("finding")) for c in cis] == [False, False, False, True, True]
    assert [n["text"] for c in cis[:3] for n in c["note"]] == ["Diagnose nicht gesichert (Follow-up)"] * 3
    assert cis[1]["summary"] == "Langsam progredient."
    # latest follow-up established -> unconfirmed clinical diagnosis raised to confirmed
    cond = by_id(bundle)[cis[-1]["problem"][0]["reference"]]
    assert cond["verificationStatus"]["coding"][0]["code"] == "confirmed"


def test_profile_set_2026_no_crash(convert_dk):
    for f in [FIX / "rd_plan_followup_all_enums.json"] + corpus("rare-disease")[:2]:
        bundle, _ = convert_dk(load(f), str(f), profile_set="2026")
        assert resources(bundle, "CarePlan")


# ---- coverage ---------------------------------------------------------------------------------------
KNOWN_UNCOVERABLE = {}   # every MAPPED row of the block is exercised by corpus + fixture


def test_mapped_paths_covered(fixture_runs, corpus_runs):
    rows = [r for r in csv.DictReader((REPO / "mapping" / "mapping_kdk_rarediseases.csv").open())
            if r["path"].startswith(PREFIXES) and r["status"] == "MAPPED"]
    assert rows
    seen = set()
    for _, rep in fixture_runs.values():
        seen |= rep.covered | rep.preserved
    for _, _, rep in corpus_runs:
        seen |= rep.covered | rep.preserved
    missing = [r["path"] for r in rows if r["path"] not in seen and r["path"] not in KNOWN_UNCOVERABLE]
    assert not missing, missing
