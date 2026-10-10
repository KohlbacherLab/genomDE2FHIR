"""Regression tests for the onco_plan review fixes (onco.careplan, onco.followup):
R10 R11 R16 R21 R24 R30 R37 R51 F09 F10 F11 F12 F20 C3 (fix-findings.json)."""
import copy
from pathlib import Path

from conftest import load, resources

from genomde2fhir.builders import patient
from genomde2fhir.builders.onco import careplan
from genomde2fhir.context import Ctx
from genomde2fhir.identity import case_key

FIX = Path(__file__).parent / "fixtures"
FULL = FIX / "onco_plan" / "plan_full.json"            # plan with a combination (th-inlabel) and study NCT twice
FU = FIX / "onco_followup" / "followup_edge_cases.json"
SID = "https://genomde.de/fhir/sid/kdk-object-id"
CAUSED_BY = "http://hl7.org/fhir/StructureDefinition/procedure-causedBy"
ALPHA_ID = "http://fhir.de/CodeSystem/bfarm/alpha-id"
ICD10GM = "http://fhir.de/CodeSystem/bfarm/icd-10-gm"
ORPHA = "http://www.orpha.net"
PRIMARY = {"reference": "urn:uuid:00000000-0000-0000-0000-0000000000a1"}
TH, ST, PM, FUP = ("plan.recommendedSystemicTherapies[].", "plan.recommendedStudies[].", "plan.preventiveMeasures[].",
                   "followUp.followUpOds[].")


def atc(code, display=None):
    return {"code": {"code": code, "system": "http://fhir.de/CodeSystem/bfarm/atc", "version": "2025",
                     **({"display": display} if display else {})}}


def plan_ctx(dk, variant_ids=(), strict=False):
    """Patient + careplan only; primary tumour stubbed, ctx.ids pre-filled with the given molecular finding ids."""
    ctx = Ctx(dk, "oncology", case_key(dk, "oncology"), "2027", strict=strict)
    patient.build(ctx)
    ctx.refs["primary"] = PRIMARY
    for v in variant_ids:
        ctx.ids[("variant", v)] = {"reference": f"urn:uuid:variant-{v}"}
    careplan.build(ctx)
    return ctx


def res(ctx, rtype=None, profile=None):
    return resources(ctx.bundle.bundle(), rtype, profile)


def by_url(bundle):
    return {e["fullUrl"]: e["resource"] for e in bundle["entry"]}


def warned(rep, path, text):
    return [m for p, m in rep.warnings if p == path and text in m]


def ident_values(r):
    return [i["value"].rsplit("|", 1)[-1] for i in r.get("identifier", []) if i.get("system") == SID]


def codes(c):
    return [x["code"] for x in (c or {}).get("coding", [])]


# ---- R10: duplicate recommendation / measure identifiers never abort -------------------------------------
def test_r10_duplicate_recommendation_identifiers_convert(convert_dk):
    dk = load(FULL)
    plan = dk["plan"]
    plan["recommendedSystemicTherapies"].append(copy.deepcopy(plan["recommendedSystemicTherapies"][2]))  # th-compassionate
    plan["recommendedStudies"].append(dict(plan["recommendedStudies"][1], priority=7))                     # st-drks
    plan["preventiveMeasures"].append({"identifier": "pm-1", "type": "Colonoscopy"})
    bundle, rep = convert_dk(dk, "dup-ids")          # was: ValueError duplicate resource -> status error
    mrs = [r for r in resources(bundle, "MedicationRequest") if "th-compassionate" in ident_values(r)]
    assert len(mrs) == 2 and len({r["id"] for r in mrs}) == 2
    srs = [r for r in resources(bundle, "ServiceRequest") if "st-drks" in ident_values(r)]
    assert len(srs) == 2
    pms = [r for r in resources(bundle, "ServiceRequest") if "pm-1" in ident_values(r)]
    assert len(pms) == 2 and {r["code"]["text"] for r in pms} == {"Breast Imaging (MRI)", "Colonoscopy"}
    for path, value in ((TH, "th-compassionate"), (ST, "st-drks"), (PM, "pm-1")):
        assert warned(rep, path + "identifier", f"duplicate identifier {value!r}")
    cp = resources(bundle, "CarePlan", "mii-pr-mtb-therapieplan")[0]
    full = {e["fullUrl"] for e in bundle["entry"]}
    assert all(a["reference"]["reference"] in full for a in cp["activity"] if "reference" in a)


def test_r10_first_occurrence_stays_the_lookup_target():
    dk = load(FULL)
    first = dk["plan"]["recommendedSystemicTherapies"][2]
    dk["plan"]["recommendedSystemicTherapies"].append(dict(copy.deepcopy(first), substances=[atc("L01XE03")]))
    ctx = plan_ctx(dk)
    target = ctx.resource(ctx.ids[("therapy_recommendation", "th-compassionate")])
    assert codes(target["medicationCodeableConcept"]) == ["L01XX35"]


# ---- R21 (R10): repeated HPO code in one follow-up --------------------------------------------------------
def test_r21_repeated_followup_phenotype(convert_dk):
    dk = load(FU)
    dk["followUp"]["followUpOds"][0]["phenotypes"] = [
        {"code": "HP:0001250", "change": "improved"},
        {"code": "HP:0001250", "change": "degraded", "text": "second"}]
    bundle, rep = convert_dk(dk, "dup-phenotype")
    obs = [o for o in resources(bundle, "Observation", "mii-pr-seltene-hpo-assessment") if codes(o["code"]) == ["HP:0001250"]]
    assert len(obs) == 2
    changes = sorted(codes(o["component"][0]["interpretation"][0])[0] for o in obs)
    assert changes == ["degraded", "improved"]
    assert warned(rep, FUP + "phenotypes[].code", "repeated in one follow-up")


# ---- R11: combination ids independent of substance count, unique member identifiers ---------------------
def test_r11_combination_ids_stable_and_identifiers_unique():
    single = load(FULL)
    single["plan"]["recommendedSystemicTherapies"] = [single["plan"]["recommendedSystemicTherapies"][2]]  # one substance
    corr = copy.deepcopy(single)
    corr["plan"]["recommendedSystemicTherapies"][0]["substances"].append(atc("L01XE03", "Erlotinib"))
    a, b = plan_ctx(single), plan_ctx(corr)
    mr_a = res(a, "MedicationRequest")
    mr_b = {codes(r["medicationCodeableConcept"])[0]: r for r in res(b, "MedicationRequest")}
    assert len(mr_a) == 1 and len(mr_b) == 2
    # the correction rewrites the existing MedicationRequest (same id) instead of leaving it as an active orphan
    assert mr_b["L01XX35"]["id"] == mr_a[0]["id"]
    assert ident_values(mr_a[0]) == ["th-compassionate"]
    # fix round 2: the first member keeps the plain recommendation id (target of a logical causedBy), every member
    # additionally carries '<id>:<j>'
    assert ident_values(mr_b["L01XX35"]) == ["th-compassionate", "th-compassionate:0"]
    assert ident_values(mr_b["L01XE03"]) == ["th-compassionate:1"]
    rg = res(b, "RequestGroup")[0]
    assert ident_values(rg) == ["th-compassionate"]
    # every kdk-object-id value identifies exactly one resource of a type
    for rtype in ("MedicationRequest", "RequestGroup", "ServiceRequest", "ResearchStudy"):
        vals = [v for r in res(b, rtype) for v in ident_values(r)]
        assert len(vals) == len(set(vals))


# ---- R16: follow-up basedOn per substance of a combination ------------------------------------------------
def test_r16_followup_basedon_links_each_substance_to_its_member(convert_dk):
    dk = load(FULL)
    dk["followUp"]["followUpOds"] = [{
        "followUpDate": "2026-01-06", "metachroneDiagnoses": False, "ecogPerformanceStatusScore": "1",
        "vitalStatus": "living",
        "therapies": [{"reference": "th-inlabel", "therapyStartDate": "2025-11-11",
                       "substances": [atc("L01EC02", "Dabrafenib"), atc("L01EE01", "Trametinib"), atc("L01XE03")]}]}]
    bundle, _ = convert_dk(dk, "combo-followup")
    refs = by_url(bundle)
    ms = {codes(m["medicationCodeableConcept"])[0]: m
          for m in resources(bundle, "MedicationStatement", "systemtherapie-medication-statement")}
    for code in ("L01EC02", "L01EE01"):
        target = refs[ms[code]["basedOn"][0]["reference"]]
        assert target["resourceType"] == "MedicationRequest" and codes(target["medicationCodeableConcept"]) == [code]
    assert "basedOn" not in ms["L01XE03"]       # not a member of the combination: no (wrong) link
    proc = resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")[0]
    cb = [e for e in proc["extension"] if e["url"] == CAUSED_BY][0]["valueReference"]
    assert refs[cb["reference"]]["resourceType"] == "MedicationRequest"   # causedBy 0..1: first member


# ---- R24: same reference + start twice in one follow-up ---------------------------------------------------
def test_r24_two_therapies_same_reference_and_start_kept_apart(convert_dk):
    dk = load(FULL)
    dk["followUp"]["followUpOds"] = [{
        "followUpDate": "2026-03-10", "metachroneDiagnoses": False, "ecogPerformanceStatusScore": "1",
        "vitalStatus": "living",
        "therapies": [
            {"reference": "th-inlabel", "therapyStartDate": "2025-11-11", "therapyEndDate": "2026-02-01",
             "terminationReasonOBDS": "A", "substances": [atc("L01EC02")],
             "therapyResponse": "PD", "therapyResponseDate": "2026-01-15"},
            {"reference": "th-inlabel", "therapyStartDate": "2025-11-11", "therapyEndDate": "2026-03-01",
             "terminationReasonOBDS": "E", "substances": [atc("L01EE01")],
             "therapyResponse": "CR", "therapyResponseDate": "2026-01-15"}]}]
    bundle, rep = convert_dk(dk, "same-therapy-twice")
    procs = {p["performedPeriod"]["end"]: p for p in resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")}
    assert set(procs) == {"2026-02-01", "2026-03-01"}
    assert procs["2026-02-01"]["status"] == "stopped" and codes(procs["2026-02-01"]["outcome"]) == ["A"]
    assert procs["2026-03-01"]["status"] == "completed" and codes(procs["2026-03-01"]["outcome"]) == ["E"]
    resp = sorted(codes(o["valueCodeableConcept"])[0] for o in resources(bundle, "Observation", "mvgs-therapy-response"))
    assert resp == ["CR", "PD"]
    ms = {codes(m["medicationCodeableConcept"])[0]: m
          for m in resources(bundle, "MedicationStatement", "systemtherapie-medication-statement")}
    assert ms["L01EC02"]["status"] == "stopped" and ms["L01EC02"]["effectivePeriod"]["end"] == "2026-02-01"
    assert warned(rep, FUP + "therapies[].reference", "reported twice in one follow-up")


# ---- R30: follow-up diagnoses keep their source code system -----------------------------------------------
def test_r30_followup_diagnoses_keep_source_system(convert_dk):
    dk = load(FU)
    dk["followUp"]["followUpOds"][0]["additionalDiagnoses"] = [
        {"system": ICD10GM, "version": "2025", "code": "C187", "date": "2025-05-15"},
        {"system": "https://www.alpha-id.de", "version": "2025", "code": "I97525", "date": "2025-05-15"},
        {"system": "https://www.orpha.net", "version": "4.7", "code": "ORPHA:558", "date": "2025-05-15"},
        {"version": "2025", "code": "C34.1", "date": "2025-05-15"}]       # no system: ICD-10-GM
    bundle, rep = convert_dk(dk, "fu-dx-systems")
    got = {(c["code"]["coding"][0]["system"], c["code"]["coding"][0]["code"], c["code"]["coding"][0].get("version"))
           for c in resources(bundle, "Condition", "mii-pr-onko-diagnose-primaertumor")
           if c.get("recordedDate") == "2025-05-15"}
    assert got == {(ICD10GM, "C18.7", "2025"), (ALPHA_ID, "I97525", "2025"), (ORPHA, "558", "4.7"),
                   (ICD10GM, "C34.1", "2025")}
    assert not [m for _, m in rep.warnings if "coded as ICD-10-GM" in m]


# ---- R37: chronological, not positional, follow-up order --------------------------------------------------
def _final_states(bundle):
    procs = {p["performedPeriod"]["start"]: (p["status"], p["performedPeriod"].get("end"))
             for p in resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")}
    meds = sorted((codes(m["medicationCodeableConcept"])[0], m["status"])
                  for m in resources(bundle, "MedicationStatement", "systemtherapie-medication-statement"))
    return procs, meds


def test_r37_followups_in_date_order_whatever_the_array_order(convert_dk):
    dk = load(FU)
    rev = copy.deepcopy(dk)
    rev["followUp"]["followUpOds"].reverse()
    b1, _ = convert_dk(dk, "as-given")
    b2, _ = convert_dk(rev, "reversed")
    assert _final_states(b1) == _final_states(b2)
    procs, _ = _final_states(b2)
    assert procs["2025-03-01"] == ("stopped", "2025-08-15")     # was in-progress without end when reversed
    assert procs["2025-08-20"] == ("stopped", "2025-11-20")
    assert {e["fullUrl"] for e in b1["entry"]} == {e["fullUrl"] for e in b2["entry"]}


def test_r37_conflicting_death_dates_latest_followup_wins(convert_dk):
    dk = load(FU)
    fus = dk["followUp"]["followUpOds"]
    fus[1].update(vitalStatus="deceased", deathDate="2025-08-30")
    fus[2]["deathDate"] = "2025-11-20"                             # latest follow-up (2025-12-01)
    fus.reverse()
    bundle, rep = convert_dk(dk, "death-dates")
    tod = resources(bundle, "Observation", "mii-pr-onko-tod")
    assert len(tod) == 1 and tod[0]["effectiveDateTime"] == "2025-11-20"
    assert resources(bundle, "Patient")[0]["deceasedDateTime"] == "2025-11-20"
    assert warned(rep, FUP + "deathDate", "latest follow-up")


# ---- F12: name-only substance of an earlier report survives the replacing Procedure -----------------------
def test_f12_earlier_name_only_substance_kept(convert_dk):
    dk = load(FU)
    fus = dk["followUp"]["followUpOds"]
    fus[0]["therapies"][0]["substances"].append({"name": "Geheimsubstanz"})     # 735a636f / 2025-03-01, reported again
    bundle, rep = convert_dk(dk, "name-only-earlier")
    proc = next(p for p in resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")
                if p["performedPeriod"]["start"] == "2025-03-01")
    assert proc["performedPeriod"]["end"] == "2025-08-15"                      # the later report's state
    assert "Geheimsubstanz" in " ".join(n["text"] for n in proc.get("note", []))
    assert FUP + "therapies[].substances[].name" in rep.preserved


def test_f12_name_coded_later_not_listed_as_uncoded(convert_dk):
    dk = load(FU)
    fus = dk["followUp"]["followUpOds"]
    fus[0]["therapies"][0]["substances"].append({"name": "Pruefsubstanz Q"})
    fus[1]["therapies"][0]["substances"].append({**atc("L01XX99"), "name": "Pruefsubstanz Q"})
    bundle, _ = convert_dk(dk, "name-coded-later")
    proc = next(p for p in resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")
                if p["performedPeriod"]["start"] == "2025-03-01")
    assert "Pruefsubstanz Q" not in " ".join(n["text"] for n in proc.get("note", []))
    assert [m for m in resources(bundle, "MedicationStatement", "systemtherapie-medication-statement")
            if m["medicationCodeableConcept"].get("text") == "Pruefsubstanz Q"]


# ---- R51: same study recommended twice with another name / substance --------------------------------------
def test_r51_repeated_study_keeps_its_own_name_and_substance():
    dk = load(FULL)
    dup = next(s for s in dk["plan"]["recommendedStudies"] if s["identifier"] == "st-nct-dup")
    dup.update(name="A DIFFERENT TRIAL ARM", substances=[{**atc("L01FC01"), "name": "Daratumumab"},
                                                         {**atc("L01EC02", "Dabrafenib"), "name": "Dabrafenib"}])
    ctx = plan_ctx(dk, strict=True)
    studies = [r for r in res(ctx, "ResearchStudy") if r["identifier"][0]["value"] == "NCT01234567"]
    assert len(studies) == 1 and studies[0]["title"] == "BASKET-1"             # one study, first title
    sr = ctx.resource(ctx.ids[("study_recommendation", "st-nct-dup")])
    notes = [n["text"] for n in sr.get("note", [])]
    assert "Studienname laut dieser Empfehlung: A DIFFERENT TRIAL ARM" in notes
    assert "Studiensubstanz laut dieser Empfehlung: Daratumumab (L01FC01)" in notes
    assert not [n for n in notes if "Dabrafenib" in n]                          # already the study's focus
    assert {ST + "name", ST + "substances[].code.code"} <= ctx.report.preserved
    assert sr["supportingInfo"][0]["reference"] == f"urn:uuid:{studies[0]['id']}"


def test_r51_identical_repeat_adds_no_note():
    ctx = plan_ctx(load(FULL))
    sr = ctx.resource(ctx.ids[("study_recommendation", "st-nct-dup")])
    assert "note" not in sr


# ---- F20: placeholder study name ---------------------------------------------------------------------------
def test_f20_placeholder_study_name_dropped():
    dk = load(FULL)
    dk["plan"]["recommendedStudies"] = [dict(dk["plan"]["recommendedStudies"][1], name="N/A"),       # DRKS
                                        {"identifier": "st-name-only", "register": "other", "name": "unknown",
                                         "evidenceLevel": "m3", "priority": 2}]
    ctx = plan_ctx(dk)
    studies = res(ctx, "ResearchStudy")
    assert len(studies) == 1 and "title" not in studies[0]
    assert studies[0]["identifier"][0]["value"] == "DRKS00012345"
    dropped = {(p, v, why) for p, v, why in ctx.report.dropped}
    assert (ST + "name", "N/A", "placeholder study name") in dropped
    assert (ST + "name", "unknown", "placeholder study name") in dropped
    assert ST + "name" not in ctx.report.covered


# ---- C3 / F09: plan variant references ---------------------------------------------------------------------
def test_c3_cited_base_id_resolves_to_split_cnv_findings():
    dk = load(FULL)
    dk["plan"]["recommendedSystemicTherapies"][2]["variants"] = ["cnv1"]
    dk["plan"]["recommendedStudies"][1]["variants"] = ["cnv1"]
    ctx = plan_ctx(dk, variant_ids=["cnv1_TP53", "cnv1_ATRX", "cnv10_RET"])
    mr = ctx.resource(ctx.ids[("therapy_recommendation", "th-compassionate")])
    assert mr["reasonReference"] == [PRIMARY, {"reference": "urn:uuid:variant-cnv1_TP53"},
                                     {"reference": "urn:uuid:variant-cnv1_ATRX"}]
    sr = ctx.resource(ctx.ids[("study_recommendation", "st-drks")])
    assert [r["reference"] for r in sr["supportingInfo"][1:]] == ["urn:uuid:variant-cnv1_TP53",
                                                                  "urn:uuid:variant-cnv1_ATRX"]
    assert len([m for _, m in ctx.report.warnings if "'cnv1'" in m and "resolved to" in m]) == 1   # warned once
    assert "cnv1" not in [v for _, v, _ in ctx.report.dropped]


def test_c3_exact_identifier_wins_over_split_findings():
    dk = load(FULL)
    dk["plan"]["recommendedSystemicTherapies"][2]["variants"] = ["cnv1"]
    ctx = plan_ctx(dk, variant_ids=["cnv1", "cnv1_TP53"])
    mr = ctx.resource(ctx.ids[("therapy_recommendation", "th-compassionate")])
    assert mr["reasonReference"] == [PRIMARY, {"reference": "urn:uuid:variant-cnv1"}]


def test_f09_unresolvable_variant_reason():
    dk = load(FULL)
    dk["plan"]["recommendedSystemicTherapies"][2]["variants"] = ["66d47d07-3761-497d-8dd5-fae7a2e1f470"]
    ctx = plan_ctx(dk)
    assert (TH + "variants[]", "66d47d07-3761-497d-8dd5-fae7a2e1f470",
            "cited variant id not present in this submission") in ctx.report.dropped


# ---- F10: interventionRecommended=false with OP ------------------------------------------------------------
def test_f10_intervention_false_with_op_warns():
    dk = load(FULL)
    od = dk["plan"]["carePlanOd"]
    od.update(interventionRecommended=False, suitableInterventions=[], otherRecommendations=["OP"])
    ctx = plan_ctx(dk)
    cp = res(ctx, "CarePlan")[0]
    assert [codes(a["detail"]["code"]) for a in cp["activity"] if "detail" in a] == [["OP"]]
    assert warned(ctx.report, "plan.carePlanOd.interventionRecommended", "otherRecommendations[] contains OP")
    od["otherRecommendations"] = ["WW"]
    assert not warned(plan_ctx(dk).report, "plan.carePlanOd.interventionRecommended", "contains OP")


# ---- F11: Therapieplan basedOn the indication board --------------------------------------------------------
def test_f11_therapieplan_based_on_indication_board(convert_dk):
    for ps in ("2027", "2026"):
        bundle, _ = convert_dk(load(FULL), "board-link", profile_set=ps)
        refs = by_url(bundle)
        plan = resources(bundle, "CarePlan", "mii-pr-mtb-therapieplan")[0]
        board = refs[plan["basedOn"][0]["reference"]]
        assert board["resourceType"] == "CarePlan"
        assert board["meta"]["profile"][0].endswith("mvgs-inclusion-decision")
