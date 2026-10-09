"""onco.followup: followUp.followUpOds[] -> Verlauf, ECOG, Vitalstatus, Tod, follow-up diagnoses, HPO phenotypes,
systemic therapies (Procedure + MedicationStatement), therapy responses, preventive-measure results."""
import copy
import json
from pathlib import Path

import pytest

from conftest import corpus, load, resources
from genomde2fhir.data_access import mapping_rows

FIXTURE = Path(__file__).parent / "fixtures" / "onco_followup" / "followup_edge_cases.json"
P = "followUp.followUpOds[]."
MII = "https://www.medizininformatik-initiative.de/fhir/"
ECOG_CS = MII + "ext/modul-onko/CodeSystem/mii-cs-onko-allgemeiner-leistungszustand-ecog"
VITAL_CS = MII + "core/modul-person/CodeSystem/Vitalstatus"
RESPONSE_CS = MII + "ext/modul-mtb/CodeSystem/mii-cs-mtb-response-befund-beurteilung"
ENDE_GRUND_CS = MII + "ext/modul-onko/CodeSystem/mii-cs-onko-therapie-ende-grund"
CAUSED_BY = "http://hl7.org/fhir/StructureDefinition/procedure-causedBy"
OCCURRED_FOLLOWING = "http://hl7.org/fhir/StructureDefinition/condition-occurredFollowing"
METACHRONOUS = "https://genomde.de/fhir/StructureDefinition/mvgs-ex-metachronous-tumor"
SID_KDK_OBJECT = "https://genomde.de/fhir/sid/kdk-object-id"


def fus(dk):
    return (dk.get("followUp") or {}).get("followUpOds") or []


def codes(cc_, system=None):
    return [c["code"] for c in (cc_ or {}).get("coding", []) if system is None or c.get("system") == system]


def by_ref(bundle):
    return {e["fullUrl"]: e["resource"] for e in bundle["entry"]}


def ext(r, url):
    return [e for e in r.get("extension", []) if e["url"] == url]


def therapy_files(n=3):
    out = []
    for f in corpus("oncology"):
        dk = load(f)
        if any(fu.get("therapies") for fu in fus(dk)) and (dk.get("plan") or {}).get("recommendedSystemicTherapies"):
            out.append(f)
        if len(out) >= n:
            break
    if len(out) < n:
        pytest.skip("not enough oncology corpus files with follow-up therapies")
    return out


# ---- (a) corpus -----------------------------------------------------------------------------------
@pytest.mark.parametrize("idx", range(3))
def test_corpus_followups(convert_dk, idx):
    f = therapy_files()[idx]
    dk = load(f)
    bundle, rep = convert_dk(dk, str(f))
    refs = by_ref(bundle)
    dates = {fu["followUpDate"] for fu in fus(dk)}

    vital = resources(bundle, "Observation", "modul-person/StructureDefinition/Vitalstatus")
    assert len(vital) == len(fus(dk))
    want = {"living": "L", "deceased": "T"}
    assert sorted(codes(v["valueCodeableConcept"], VITAL_CS)[0] for v in vital) == \
        sorted(want[fu["vitalStatus"]] for fu in fus(dk))

    # follow-up ECOG (the case ECOG has no follow-up date)
    ecog = [o for o in resources(bundle, "Observation", "allgemeiner-leistungszustand-ecog")
            if o.get("effectiveDateTime") in dates]
    valid = [fu for fu in fus(dk) if fu["ecogPerformanceStatusScore"] in ("0", "1", "2", "3", "4")]
    assert len(ecog) == len(valid)
    for o in ecog:
        assert codes(o["valueCodeableConcept"], ECOG_CS)[0] in "01234"
        assert codes(o["valueCodeableConcept"], "http://loinc.org")     # 2027: coding:loinc
        if "primary" in rep.covered or o.get("focus"):
            assert o["focus"][0]["reference"] in refs

    verlauf = resources(bundle, "Observation", "mii-pr-onko-verlauf")
    if verlauf:
        assert {v["effectiveDateTime"] for v in verlauf} == dates
        assert all(refs[v["focus"][0]["reference"]]["resourceType"] == "Condition" for v in verlauf)

    procs = resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")
    n_ther = {(t["reference"], t["therapyStartDate"]) for fu in fus(dk) for t in fu.get("therapies") or []}
    assert len(procs) == len(n_ther)
    for p in procs:
        assert p["performedPeriod"]["start"]
        assert p["status"] in ("in-progress", "stopped", "completed")
        cb = ext(p, CAUSED_BY)
        assert cb, "every corpus therapy references a recommendation"
        target = cb[0]["valueReference"]
        if "reference" in target:
            assert refs[target["reference"]]["resourceType"] == "MedicationRequest"
        else:
            assert target["identifier"]["system"] == SID_KDK_OBJECT
    meds = [m for m in resources(bundle, "MedicationStatement", "systemtherapie-medication-statement")
            if any(r["reference"] in {e["fullUrl"] for e in bundle["entry"] if e["resource"] in procs}
                   for r in m["partOf"])]
    assert meds and all(codes(m["medicationCodeableConcept"], "http://fhir.de/CodeSystem/bfarm/atc") for m in meds)

    responses = resources(bundle, "Observation", "mvgs-therapy-response")
    n_resp = {(t["reference"], t["therapyStartDate"], t.get("therapyResponseDate"))
              for fu in fus(dk) for t in fu.get("therapies") or [] if t.get("therapyResponse")}
    assert len(responses) == len(n_resp)
    for o in responses:
        assert codes(o["valueCodeableConcept"], RESPONSE_CS)[0] in {"CR", "PR", "SD", "PD"}
        assert refs[o["partOf"][0]["reference"]]["resourceType"] == "Procedure"

    for fu in fus(dk):
        if fu.get("deathDate"):
            pat = resources(bundle, "Patient")[0]
            assert pat["deceasedDateTime"] in {x.get("deathDate") for x in fus(dk)}
            assert resources(bundle, "Observation", "mii-pr-onko-tod")
    assert P + "vitalStatus" in rep.covered and P + "therapies[].therapyStartDate" in rep.covered


# ---- (b) synthetic edge cases -------------------------------------------------------------------
@pytest.fixture
def edge(convert_dk):
    dk = load(FIXTURE)
    bundle, rep = convert_dk(dk, "followup_edge_cases")
    return dk, bundle, rep


def test_ecog_catch_all_values(edge):
    dk, bundle, rep = edge
    ecog = [o for o in resources(bundle, "Observation", "allgemeiner-leistungszustand-ecog")
            if o.get("effectiveDateTime") == "2025-06-01"]
    assert len(ecog) == 1
    assert codes(ecog[0]["valueCodeableConcept"]) == ["U"]            # unknown -> obds U, no LOINC code
    assert "dataAbsentReason" not in ecog[0]
    dropped = {(p, v) for p, v, _ in rep.dropped}
    assert (P + "ecogPerformanceStatusScore", "5") in dropped
    assert (P + "ecogPerformanceStatusScore", "notApplicable") in dropped
    assert not [o for o in resources(bundle, "Observation", "allgemeiner-leistungszustand-ecog")
                if o.get("effectiveDateTime") in ("2025-09-01", "2025-12-01")]


def test_vitalstatus_last_contact_and_death(edge):
    dk, bundle, rep = edge
    vital = {codes(v["valueCodeableConcept"])[0] + v["effectiveDateTime"]: v
             for v in resources(bundle, "Observation", "Vitalstatus")}
    assert "L2025-05-20" in vital          # living: established at the last contact
    assert "L2025-09-01" in vital
    dead = vital["T2025-12-01"]            # deceased: follow-up date; last contact kept as note
    assert "2025-11-01" in dead["note"][0]["text"]
    assert resources(bundle, "Patient")[0]["deceasedDateTime"] == "2025-11-20"
    tod = resources(bundle, "Observation", "mii-pr-onko-tod")
    assert len(tod) == 1 and tod[0]["effectiveDateTime"] == "2025-11-20"
    verlauf = {v["effectiveDateTime"]: v for v in resources(bundle, "Observation", "mii-pr-onko-verlauf")}
    assert set(verlauf) == {"2025-06-01", "2025-09-01", "2025-12-01"}
    tod_url = next(e["fullUrl"] for e in bundle["entry"] if e["resource"] is tod[0])
    assert verlauf["2025-12-01"]["hasMember"] == [{"reference": tod_url}]
    assert "hasMember" not in verlauf["2025-06-01"]
    assert P + "lastContactDate" in rep.covered and P + "lastContactDate" in rep.preserved


def test_metachronous_diagnoses_2027(edge):
    dk, bundle, rep = edge
    conds = [c for c in resources(bundle, "Condition", "mii-pr-onko-diagnose-primaertumor") if ext(c, OCCURRED_FOLLOWING)]
    assert len(conds) == 1
    c = conds[0]
    assert codes(c["code"]) == ["C18.7"] and c["code"]["coding"][0]["version"] == "2025"
    assert c["recordedDate"] == "2025-05-15"
    assert codes(c["category"][0]) == ["55342001"]
    assert "clinicalStatus" not in c                      # not in the source
    assert ext(c, "http://hl7.org/fhir/StructureDefinition/condition-assertedDate")[0]["valueDateTime"] == "2025-05-15"
    assert by_ref(bundle)[ext(c, OCCURRED_FOLLOWING)[0]["valueReference"]["reference"]]["resourceType"] == "Condition"
    verlauf = {v["effectiveDateTime"]: v for v in resources(bundle, "Observation", "mii-pr-onko-verlauf")}
    assert not ext(verlauf["2025-06-01"], METACHRONOUS)                     # derived from occurredFollowing
    assert ext(verlauf["2025-09-01"], METACHRONOUS)[0]["valueBoolean"] is True   # true without diagnoses
    assert ext(verlauf["2025-12-01"], METACHRONOUS)[0]["valueBoolean"] is False
    assert P + "metachroneDiagnoses" in rep.covered and P + "metachroneDiagnoses" in rep.preserved


def test_metachronous_diagnoses_2026(convert_dk):
    bundle, rep = convert_dk(load(FIXTURE), "followup_edge_cases", profile_set="2026")
    conds = [c for c in resources(bundle, "Condition") if codes(c["code"]) == ["C18.7"]]
    assert len(conds) == 1 and not ext(conds[0], OCCURRED_FOLLOWING)       # 2026 slice targets fruehere-tumorerkrankung only
    verlauf = {v["effectiveDateTime"]: v for v in resources(bundle, "Observation", "mii-pr-onko-verlauf")}
    assert ext(verlauf["2025-06-01"], METACHRONOUS)[0]["valueBoolean"] is True
    ecog = [o for o in resources(bundle, "Observation", "allgemeiner-leistungszustand-ecog")
            if o.get("effectiveDateTime") == "2025-06-01"]
    assert ecog and all(not codes(o["valueCodeableConcept"], "http://loinc.org") for o in ecog)
    assert all("basedOn" not in m for m in resources(bundle, "MedicationStatement", "systemtherapie-medication-statement"))


def test_phenotypes(edge):
    dk, bundle, rep = edge
    obs = {codes(o["code"])[0]: o for o in resources(bundle, "Observation", "mii-pr-seltene-hpo-assessment")}
    assert len(obs) == 5
    expect = {"HP:0002027": ("newly-added", "LA9633-4"), "HP:0001945": ("improved", "LA9633-4"),
              "HP:0012378": ("degraded", "LA9633-4"), "HP:0002013": ("no-longer-observed", "LA9634-2"),
              "HP:0001824": ("unchanged", "LA9633-4")}
    for code, (change, presence) in expect.items():
        comp = obs[code]["component"][0]
        assert codes(comp["interpretation"][0]) == [change]
        assert codes(comp["valueCodeableConcept"]) == [presence]
        assert obs[code]["code"]["coding"][0]["system"] == "http://human-phenotype-ontology.org"
    assert obs["HP:0002027"]["code"]["text"] == "Bauchschmerzen"


def test_therapies(edge):
    dk, bundle, rep = edge
    refs = by_ref(bundle)
    procs = resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")
    assert len(procs) == 3
    by_start = {p["performedPeriod"]["start"]: p for p in procs}
    # recommended therapy, updated by the second follow-up (same reference + start date -> same resource)
    rec = by_start["2025-03-01"]
    assert rec["performedPeriod"]["end"] == "2025-08-15" and rec["status"] == "stopped"
    assert codes(rec["outcome"], ENDE_GRUND_CS) == ["P"] and codes(rec["statusReason"]) == ["progression"]
    target = refs[ext(rec, CAUSED_BY)[0]["valueReference"]["reference"]]
    assert target["resourceType"] == "MedicationRequest"
    # study-based therapy: no conformant link, kept as note
    study = by_start["2025-01-10"]
    assert not ext(study, CAUSED_BY) and "Studienempfehlung" in study["note"][0]["text"]
    assert study["status"] == "completed" and codes(study["outcome"]) == ["E"]
    # reference that is no recommendation of the plan in this submission: the therapy's own "new identifier"
    # (KDK schema) -> Procedure.identifier, no causedBy; name-only substance in note
    later = by_start["2025-08-20"]
    assert not ext(later, CAUSED_BY)
    assert [(i["system"], i["value"].rsplit("|", 1)[-1]) for i in later["identifier"]] == \
        [(SID_KDK_OBJECT, "rec-from-earlier-submission")]   # value "<submitterId>|<caseKey>|<id>"
    assert later["status"] == "stopped" and codes(later["outcome"]) == ["T"]
    assert "Experimentelle Substanz XY" in later["note"][0]["text"]
    assert P + "therapies[].reference" in rep.preserved
    meds = resources(bundle, "MedicationStatement", "systemtherapie-medication-statement")
    mine = [m for m in meds if m["partOf"][0]["reference"] in
            {e["fullUrl"] for e in bundle["entry"] if e["resource"] in procs}]
    assert {codes(m["medicationCodeableConcept"])[0] for m in mine} == {"L01FX07", "L01XX", "L01XA04"}
    cls = next(m for m in mine if codes(m["medicationCodeableConcept"]) == ["L01XX"])
    assert cls["medicationCodeableConcept"]["text"] == "Prüfsubstanz ABC"
    # substance reported only by the first follow-up takes the final therapy state of the later one
    assert cls["status"] == "stopped" and cls["effectivePeriod"] == {"start": "2025-03-01", "end": "2025-08-15"}
    blin = next(m for m in mine if codes(m["medicationCodeableConcept"]) == ["L01FX07"])
    assert blin["status"] == "stopped"
    assert refs[blin["basedOn"][0]["reference"]]["resourceType"] == "MedicationRequest"   # 2027 basedOn


def test_therapy_reference_without_plan(convert_dk):
    """Follow-up submission without the plan: unresolved reference -> logical causedBy by KDK identifier."""
    dk = load(FIXTURE)
    dk.pop("plan")
    bundle, rep = convert_dk(dk, "followup_no_plan")
    procs = {p["performedPeriod"]["start"]: p for p in resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")}
    lr = ext(procs["2025-08-20"], CAUSED_BY)[0]["valueReference"]
    assert lr["type"] == "MedicationRequest" and lr["identifier"]["system"] == SID_KDK_OBJECT
    assert lr["identifier"]["value"].endswith("|rec-from-earlier-submission")
    assert "identifier" not in procs["2025-08-20"]
    lr = ext(procs["2025-03-01"], CAUSED_BY)[0]["valueReference"]
    assert lr["identifier"]["value"].endswith("|735a636f-fb9c-4b9b-adf3-0ab09f8e731e")
    assert P + "therapies[].reference" in rep.covered


def test_response_date_without_response(convert_dk):
    dk = load(FIXTURE)
    t = dk["followUp"]["followUpOds"][1]["therapies"][1]
    t.update(therapyResponseDate="2025-09-01", therapyResponseSource="Tumorboard")
    _, rep = convert_dk(dk, "followup_response_date_only")
    dropped = {p for p, _, _ in rep.dropped}
    assert {P + "therapies[].therapyResponseDate", P + "therapies[].therapyResponseSource"} <= dropped


def test_therapy_responses(edge):
    dk, bundle, rep = edge
    resp = {o["effectiveDateTime"]: o for o in resources(bundle, "Observation", "mvgs-therapy-response")}
    assert {d: codes(o["valueCodeableConcept"])[0] for d, o in resp.items()} == \
        {"2025-05-30": "PR", "2025-02-20": "SD", "2025-08-10": "PD"}
    assert resp["2025-05-30"]["note"][0]["text"] == "Datenquelle: Arztbrief"
    assert "method" not in resp["2025-05-30"]
    assert {P + "therapies[]." + f for f in ("therapyResponse", "therapyResponseDate", "therapyResponseSource")} \
        <= rep.preserved


def test_preventive_measure_results(edge):
    dk, bundle, rep = edge
    refs = by_ref(bundle)
    obs = {o["effectiveDateTime"]: o for o in resources(bundle, "Observation")
           if "mvgs-cs-preventive-measure-result" in json.dumps(o.get("code"))}
    assert {d: codes(o["valueCodeableConcept"])[0] for d, o in obs.items()} == \
        {"2025-05-02": "noFindings", "2025-05-10": "malignoma", "2025-10-01": "unclear"}
    assert refs[obs["2025-05-02"]["basedOn"][0]["reference"]]["resourceType"] == "ServiceRequest"
    assert obs["2025-05-02"]["method"]["text"] == "Colonoscopy"
    assert obs["2025-05-10"]["basedOn"][0]["identifier"]["value"].endswith("|pm-earlier-submission")


def test_followup_ids_keyed_by_date(convert_dk):
    """A follow-up submission carrying only the newest follow-up reuses the ids of the full document."""
    full = load(FIXTURE)
    only_last = copy.deepcopy(full)
    only_last["followUp"]["followUpOds"] = full["followUp"]["followUpOds"][-1:]
    b1, _ = convert_dk(full, "full")
    b2, _ = convert_dk(only_last, "last")
    ids1 = {r["id"] for r in resources(b1, "Observation", "Vitalstatus")}
    ids2 = {r["id"] for r in resources(b2, "Observation", "Vitalstatus")}
    assert len(ids1) == 3 and ids2 < ids1


# ---- (c) coverage ---------------------------------------------------------------------------------
def test_block_coverage(convert_dk):
    rows = {p: r for p, r in mapping_rows("oncology").items() if p.startswith(P)}
    assert rows, "mapping rows missing"
    done = set()
    for f in [FIXTURE] + therapy_files():
        _, rep = convert_dk(load(f), str(f))
        done |= rep.covered | rep.preserved
    known_uncoverable = {}
    missing = {p for p, r in rows.items() if r["status"] in ("MAPPED", "DRAFT")} - done - set(known_uncoverable)
    assert not missing, sorted(missing)
