"""Fix round 2 regression tests (group onco: onco.careplan, onco.followup, onco.tnm): R11 R24 R30 F12 F20 R67 R68.

Small synthetic inputs built from tracked fixtures (onco_plan, onco_followup, onco_diagnosis), modified inline.
The matchbox-backed R68 checks run only with MB2027 (matchbox-2027 base URL)."""
import copy
import os
from pathlib import Path

import pytest
from conftest import load, resources

from genomde2fhir.systems import SNOMED

FIX = Path(__file__).parent / "fixtures"
PLAN = FIX / "onco_plan" / "plan_full.json"            # th-inlabel = combination L01EC02 + L01EE01
FU = FIX / "onco_followup" / "followup_edge_cases.json"
DIAG_FULL = FIX / "onco_diagnosis" / "diagnosis_full.json"
DIAG_DROPS = FIX / "onco_diagnosis" / "diagnosis_drops.json"
SID = "https://genomde.de/fhir/sid/kdk-object-id"
CAUSED_BY = "http://hl7.org/fhir/StructureDefinition/procedure-causedBy"
FUP, ST = "followUp.followUpOds[].", "plan.recommendedStudies[]."
MB = os.environ.get("MB2027")


def atc(code, **kw):
    return {"code": {"code": code, "system": "http://fhir.de/CodeSystem/bfarm/atc", "version": "2025"}, **kw}


def codes(c):
    return [x["code"] for x in (c or {}).get("coding", [])]


def by_url(bundle):
    return {e["fullUrl"]: e["resource"] for e in bundle["entry"]}


def profile(r):
    return r.get("meta", {}).get("profile", [""])[0].rsplit("/", 1)[-1]


def caused_by(proc):
    return next(e["valueReference"] for e in proc.get("extension", []) if e["url"] == CAUSED_BY)


def procs(bundle):
    return resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")


def meds(bundle):
    """MedicationStatements of the follow-up therapies (partOf a systemische-therapie Procedure)."""
    urls = {f"urn:uuid:{p['id']}" for p in procs(bundle)}
    return [m for m in resources(bundle, "MedicationStatement", "systemtherapie-medication-statement")
            if any(r["reference"] in urls for r in m.get("partOf", []))]


def warned(rep, text):
    return [m for _, m in rep.warnings if text in m]


def fu(date, *therapies):
    return {"followUpDate": date, "metachroneDiagnoses": False, "ecogPerformanceStatusScore": "1",
            "vitalStatus": "living", "therapies": list(therapies)}


def therapy(subs, end=None, reason=None, response=None, ref="th-inlabel", start="2025-11-11"):
    t = {"reference": ref, "therapyStartDate": start, "substances": [atc(s) for s in subs]}
    if end:
        t["therapyEndDate"] = end
    if reason:
        t["terminationReasonOBDS"] = reason
    if response:
        t.update(therapyResponse=response, therapyResponseDate="2026-01-15")
    return t


# ---- R11: a logical causedBy resolves to exactly one MedicationRequest -------------------------------------------
def _holders(bundle, value):
    return [r for r in resources(bundle, "MedicationRequest")
            if any(i.get("system") == SID and i["value"] == value for i in r.get("identifier", []))]


@pytest.mark.parametrize("ref", ["th-inlabel", "th-compassionate"])      # combination, single substance
def test_r11_logical_causedby_matches_the_in_submission_target(convert_dk, ref):
    dk = load(PLAN)
    dk["followUp"]["followUpOds"] = [fu("2026-01-06", therapy(["L01EC02"], ref=ref))]
    with_plan, _ = convert_dk(copy.deepcopy(dk), "plan-and-followup")
    target = caused_by(procs(with_plan)[0])["reference"]                  # causedBy within the submission
    dk.pop("plan")
    later, _ = convert_dk(dk, "followup-only")
    logical = caused_by(procs(later)[0])
    assert logical["type"] == "MedicationRequest" and logical["identifier"]["system"] == SID
    holders = _holders(with_plan, logical["identifier"]["value"])
    assert [f"urn:uuid:{r['id']}" for r in holders] == [target]           # exactly one, the first member


def test_r11_logical_target_survives_a_correction_adding_a_partner(convert_dk):
    single = load(PLAN)
    single["plan"]["recommendedSystemicTherapies"] = [single["plan"]["recommendedSystemicTherapies"][2]]
    corr = copy.deepcopy(single)
    corr["plan"]["recommendedSystemicTherapies"][0]["substances"].append(atc("L01XE03"))
    b1, _ = convert_dk(single, "single")
    b2, _ = convert_dk(corr, "correction")
    value = next(i["value"] for i in resources(b1, "MedicationRequest")[0]["identifier"] if i["system"] == SID)
    assert value.endswith("|th-compassionate")
    h1, h2 = _holders(b1, value), _holders(b2, value)
    assert len(h1) == len(h2) == 1 and h1[0]["id"] == h2[0]["id"]          # same resource before and after
    assert [i["value"].rsplit("|", 1)[-1] for i in h1[0]["identifier"]] == ["th-compassionate"]   # single: no ':0'
    member = [r for r in resources(b2, "MedicationRequest") if r["id"] != h2[0]["id"]][0]
    assert [i["value"].rsplit("|", 1)[-1] for i in member["identifier"]] == ["th-compassionate:1"]


# ---- R24: entries sharing reference + start are told apart by substances, not array position ------------------
A = dict(subs=["L01EC02"], end="2026-02-01", reason="A", response="PD")   # stopped for toxicity
B = dict(subs=["L01EE01"], end="2026-03-01", reason="E", response="CR")


def _state(bundle, ids=False):
    """{substance codes of the Procedure's MedicationStatements: (Procedure status, end, outcome)} (or: Procedure id)"""
    out = {}
    for p in procs(bundle):
        url = f"urn:uuid:{p['id']}"
        subs = tuple(sorted(codes(m["medicationCodeableConcept"])[0] for m in meds(bundle)
                            if m["partOf"][0]["reference"] == url))
        out[subs] = p["id"] if ids else (p["status"], p["performedPeriod"].get("end"), codes(p.get("outcome"))[:1])
    return out


def test_r24_split_ids_independent_of_array_order(convert_dk):
    dk = load(PLAN)
    dk["followUp"]["followUpOds"] = [fu("2026-03-10", therapy(**A), therapy(**B))]
    rev = copy.deepcopy(dk)
    rev["followUp"]["followUpOds"][0]["therapies"].reverse()
    b1, rep = convert_dk(dk, "as-given")
    b2, _ = convert_dk(rev, "reversed")
    assert _state(b1, ids=True) == _state(b2, ids=True)                    # same id per substance, either order
    assert _state(b1) == _state(b2) == {("L01EC02",): ("stopped", "2026-02-01", ["A"]),
                                        ("L01EE01",): ("completed", "2026-03-01", ["E"])}
    assert warned(rep, "reported twice in one follow-up; kept apart by their substances")


def test_r24_later_subset_report_updates_only_its_part(convert_dk):
    dk = load(PLAN)
    dk["followUp"]["followUpOds"] = [fu("2026-03-10", therapy(**A), therapy(**B)),
                                     fu("2026-05-10", therapy(["L01EE01"], end="2026-04-01", reason="E"))]
    bundle, rep = convert_dk(dk, "subset")
    assert _state(bundle) == {("L01EC02",): ("stopped", "2026-02-01", ["A"]),      # untouched (was overwritten)
                              ("L01EE01",): ("completed", "2026-04-01", ["E"])}
    assert len([m for m in meds(bundle) if codes(m["medicationCodeableConcept"]) == ["L01EE01"]]) == 1
    assert not warned(rep, "match no single part")


def test_r24_later_report_in_reverse_order_keeps_states_with_substances(convert_dk):
    dk = load(PLAN)
    dk["followUp"]["followUpOds"] = [
        fu("2026-03-10", therapy(**A), therapy(**B)),
        fu("2026-05-10", therapy(["L01EE01"], end="2026-04-01", reason="E"),
           therapy(["L01EC02"], end="2026-02-05", reason="A"))]
    bundle, _ = convert_dk(dk, "reversed-later")
    assert _state(bundle) == {("L01EC02",): ("stopped", "2026-02-05", ["A"]),
                              ("L01EE01",): ("completed", "2026-04-01", ["E"])}


def test_r24_exact_duplicate_entry_gives_one_procedure(convert_dk):
    dk = load(PLAN)
    dk["followUp"]["followUpOds"] = [fu("2026-03-10", therapy(**A), therapy(**A))]
    bundle, rep = convert_dk(dk, "exact-duplicate")
    assert len(procs(bundle)) == 1 and len(meds(bundle)) == 1
    assert len(resources(bundle, "Observation", "mvgs-therapy-response")) == 1
    # fix round 3 (R24): identical entries are one report (no 'later entry replaces' by array order)
    assert warned(rep, "with the same substances [L01EC02] and the same content: one Procedure")


def test_r24_ambiguous_later_report_is_its_own_procedure_and_warned(convert_dk):
    dk = load(PLAN)
    dk["followUp"]["followUpOds"] = [fu("2026-03-10", therapy(**A), therapy(**B)),
                                     fu("2026-05-10", therapy(["L01EC02", "L01EE01"], end="2026-04-01", reason="E"))]
    bundle, rep = convert_dk(dk, "ambiguous")
    st = _state(bundle)
    assert st[("L01EC02",)] == ("stopped", "2026-02-01", ["A"]) and st[("L01EE01",)][1] == "2026-03-01"
    assert ("L01EC02", "L01EE01") in st and len(procs(bundle)) == 3
    assert warned(rep, "its substances match no single part")


# ---- R30: an empty / normalised-away follow-up diagnosis code never aborts ----------------------------------------
def test_r30_empty_code_after_normalisation_dropped(convert_dk):
    dk = load(FU)
    dk["followUp"]["followUpOds"][0]["additionalDiagnoses"] = [
        {"system": "https://www.orpha.net", "code": "ORPHA:", "version": "", "date": "2025-05-15"},
        {"system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "code": " ", "version": "", "date": "2025-05-15"},
        {"code": "+", "version": "", "date": "2025-05-15"},
        {"system": "https://www.orpha.net", "code": "ORPHA:", "version": "4.7", "date": "2025-05-15"},
        {"system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "code": "C187", "version": "2025",
         "date": "2025-05-15"}]
    bundle, rep = convert_dk(dk, "empty-codes")              # was: TypeError -> status error, no bundle
    conds = [c for c in resources(bundle, "Condition", "mii-pr-onko-diagnose-primaertumor")
             if c.get("recordedDate") == "2025-05-15"]
    assert [codes(c["code"]) for c in conds] == [["C18.7"]]       # no Condition without code
    dropped = [(v, why) for p, v, why in rep.dropped if p == FUP + "additionalDiagnoses[].code"]
    assert sorted(v for v, _ in dropped) == sorted(["ORPHA:", " ", "+", "ORPHA:"])
    assert all(why == "empty code after normalisation: no Condition" for _, why in dropped)


# ---- F12: a name coded by any earlier report is not listed as uncoded again --------------------------------------
def test_f12_name_coded_in_an_intermediate_report_stays_out_of_the_note(convert_dk):
    dk = load(FU)
    fus = dk["followUp"]["followUpOds"]          # therapy 735a636f / 2025-03-01: follow-ups 1 and 2 report it
    t0, t1 = fus[0]["therapies"][0], fus[1]["therapies"][0]
    assert t0["reference"] == t1["reference"] and t0["therapyStartDate"] == t1["therapyStartDate"] == "2025-03-01"
    fus[2]["therapies"].append(copy.deepcopy(t1))   # follow-up 3 reports it again, without Q and R
    t0["substances"].append({"name": "Pruefsubstanz Q"})
    t1["substances"].append(atc("L01XX99", name="Pruefsubstanz Q"))
    t0["substances"].append({"name": "Pruefsubstanz R"})
    t1["substances"].append({"code": {"code": "L01XX98", "system": "http://fhir.de/CodeSystem/bfarm/atc",
                                      "version": "2025", "display": "Pruefsubstanz R"}})   # coded, display only
    bundle, rep = convert_dk(dk, "coded-in-between")
    proc = next(p for p in procs(bundle) if p["performedPeriod"]["start"] == "2025-03-01")
    note = " ".join(n["text"] for n in proc.get("note", []))
    assert "Pruefsubstanz Q" not in note and "Pruefsubstanz R" not in note
    assert {"L01XX99", "L01XX98"} <= {codes(m["medicationCodeableConcept"])[0] for m in meds(bundle)}


# ---- F20: substances of a study without ResearchStudy are kept as request note -----------------------------------
@pytest.mark.parametrize("study", [
    {"register": "other", "id": "", "name": "N/A"},                     # no identifier, placeholder name
    {"register": "yesButStudyIsUnknown", "id": "N/A", "name": "N/A"},   # unidentified study
])
def test_f20_study_substances_without_researchstudy_preserved(convert_dk, study):
    dk = load(PLAN)
    dk["plan"]["recommendedStudies"] = [{"identifier": "st-x", "evidenceLevel": "m3", "priority": 1, **study,
                                         "substances": [atc("L01EA01", name="Imatinib")]}]
    bundle, rep = convert_dk(dk, "study-substances")
    assert not resources(bundle, "ResearchStudy")
    sr = next(r for r in resources(bundle, "ServiceRequest", "studieneinschluss-anfrage")
              if any(i["value"].endswith("|st-x") for i in r.get("identifier", [])))
    assert "Studiensubstanz laut dieser Empfehlung: Imatinib (L01EA01)" in [n["text"] for n in sr["note"]]
    assert {ST + "substances[].code.code", ST + "substances[].name"} <= rep.preserved


# ---- R67: UICC 9th-edition strings under 2026 are text only ---------------------------------------------------------
def test_r67_snomed_labelled_uicc_string_text_only_2026(convert_dk):
    dk = load(DIAG_DROPS)
    dk["case"]["diagnosisOd"]["tnmClassifications"] = [
        {"code": "M1c1", "system": SNOMED, "version": "9", "display": "M1c1"},
        {"code": "T1b3", "system": SNOMED, "display": "pT1b3",
         "version": "http://snomed.info/sct/900000000000207008/version/20240401"},
        {"code": "M1c2", "system": "UICC", "version": "9", "display": "Fernmetastasen"},
        {"code": "N0", "system": "UICC", "version": "8", "display": "N0"}]
    b, rep = convert_dk(dk, "r67", profile_set="2026")
    wk = [o for o in resources(b, "Observation", "mii-pr-onko-weitere-klassifikationen") if o["code"].get("text") == "TNM"]
    assert sorted(o["valueCodeableConcept"]["text"] for o in wk) == ["M1c1", "M1c2 (Fernmetastasen)", "pT1b3"]
    assert all("coding" not in o["valueCodeableConcept"] for o in wk)         # never a SNOMED coding of a UICC code
    assert "http://snomed.info/sct/900000000000207008/version/20240401" in [v for _, v, _ in rep.dropped]
    b27, _ = convert_dk(dk, "r67", profile_set="2027")
    assert not [o for o in resources(b27, "Observation", "mii-pr-onko-weitere-klassifikationen")
                if o["code"].get("text") == "TNM"]


# ---- R68: 2026 y/r/a symbols keep their (must-support) focus -------------------------------------------------------
def test_r68_full_fixture_y_symbol_2026(convert_dk):
    b, rep = convert_dk(load(DIAG_FULL), "full", profile_set="2026")
    (group,) = resources(b, "Observation", "mii-pr-onko-tnm-klassifikation")
    members = [by_url(b)[m["reference"]] for m in group["hasMember"]]
    (y,) = [m for m in members if profile(m) == "mii-pr-onko-tnm-y-symbol"]   # SNOMED ypT2 -> one y-symbol
    assert y["focus"] == group["focus"]                                    # focus 0..* MS: the primary tumour
    assert "tnm-yra-symbol-2026" in rep.representations


needs_mb = pytest.mark.skipif(not MB, reason="MB2027 (matchbox-2027 base URL) not set")


@needs_mb
def test_r68_y_symbol_valid_against_its_profile():
    from genomde2fhir import convert
    from genomde2fhir.validate import Matchbox
    b, _ = convert(load(DIAG_FULL), "full", "2026")
    y = next(r for r in resources(b, "Observation", "mii-pr-onko-tnm-y-symbol"))
    oo = Matchbox(MB).validate(y, y["meta"]["profile"][0])
    assert not [i for i in oo["issue"] if i["severity"] in ("error", "fatal")], oo


@needs_mb
def test_r68_full_fixture_2026_not_fail():
    """The candidate invariant tnm-sct-uicc-konsistenz '(defined in <m-kategorie>)' at the y-symbol is 'candidate'."""
    from genomde2fhir import convert
    from genomde2fhir.validate import Matchbox, validate_bundle
    dk = load(DIAG_FULL)
    b, _ = convert(copy.deepcopy(dk), "full", "2026")
    res = validate_bundle(b, Matchbox(MB), source=dk)
    assert res["verdict"] != "FAIL", [(r["profile"], i["text"][:200]) for r in res["resources"] for i in r["issues"]
                                      if i["class"] == "content"]
