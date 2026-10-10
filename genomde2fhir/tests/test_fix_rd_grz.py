"""Regression tests for review findings of group rd_grz (RD builders, GRZ lab data).

R09/R22/F02/F03 RD follow-up ids keyed by followUpDate      F18 deathDate before onset/consent/board -> warning
R56 RD diagnoses: DIMDI ICD-10-GM / Alpha-ID namespace       R66 2026 Therapieplan: study request in two slices
F15 compHet coded inside LL381-5                              F16 RD localization keeps the KDK value as text
F17 genes[].display is used, so no 'unknown field' finding   R29 GRZ ICD-O-3 bodySite edition / code normalised
R45 2026 SpecimenCore: processing.extension:temperaturbedingungen (data-absent-reason)
"""
import copy
from pathlib import Path

import pytest
from conftest import load, resources

from genomde2fhir import convert
from genomde2fhir.builders import patient
from genomde2fhir.builders.rd import variants
from genomde2fhir.context import Ctx
from genomde2fhir.identity import case_key
from genomde2fhir.report import Report

FIX = Path(__file__).parent / "fixtures"
RD_ENUMS = FIX / "rd_plan_followup" / "rd_plan_followup_all_enums.json"
RD_VARIANTS = FIX / "rd_variants" / "rd-variants-edge-cases.json"
GRZ_DUO = FIX / "grz_labdata" / "grz-labdata-rd-duo.json"
LOINC = "http://loinc.org"
ICD10GM = "http://fhir.de/CodeSystem/bfarm/icd-10-gm"
ALPHA_ID = "http://fhir.de/CodeSystem/bfarm/alpha-id"
ICDO3 = "http://terminology.hl7.org/CodeSystem/icd-o-3"
DAR = "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
TEMPERATURE = ("https://www.medizininformatik-initiative.de/fhir/ext/modul-biobank/StructureDefinition/"
               "Temperaturbedingungen")
STUDY_REQ = "mii-pr-seltene-studieneinschluss-anfrage"


def run(dk, profile_set="2027", strict=True):
    bundle, rep = convert(dk, "<fix_rd_grz>", profile_set, strict=strict)
    assert rep.status == "converted", rep.error or rep.input_findings
    return bundle, rep


def has_profile(r, name):
    return any(p.split("|")[0].endswith("/" + name) for p in r.get("meta", {}).get("profile", []))


def warnings(rep, path):
    return [m for p, m in rep.warnings if p == path]


# ---- R09 / R22 / F02 / F03: RD follow-up ids keyed by followUpDate ------------------------------------------
def followup_ids(bundle, dk) -> dict:
    """{(type, effective date, code): id} of the follow-up resources (impression, HPO, GMFCS, Vitalstatus)."""
    dates = {fu["followUpDate"] for fu in dk["followUp"]["followUpRds"]}
    out = {}
    for r in resources(bundle):
        if r.get("effectiveDateTime") not in dates:     # e.g. the diagnosis GMFCS (board date)
            continue
        if r["resourceType"] == "ClinicalImpression":
            out[("ClinicalImpression", r["effectiveDateTime"], None)] = r["id"]
        elif r["resourceType"] == "Observation" and r.get("effectiveDateTime") and (
                has_profile(r, "mii-pr-seltene-hpo-assessment") or has_profile(r, "Vitalstatus")
                or r["code"]["coding"][0]["code"] == "707621005"):
            out[("Observation", r["effectiveDateTime"], r["code"]["coding"][0]["code"])] = r["id"]
    return out


def test_rd_followup_submissions_do_not_overwrite_each_other():
    base = load(RD_ENUMS)
    fus = base["followUp"]["followUpRds"]
    first, second = copy.deepcopy(base), copy.deepcopy(base)   # same submitterId + localCaseId = same case
    first["followUp"]["followUpRds"] = [fus[0]]                # 2026-05-15
    second["followUp"]["followUpRds"] = [fus[1]]               # 2026-06-15: the newer visit only
    ids1, ids2 = followup_ids(run(first)[0], first), followup_ids(run(second)[0], second)
    assert len(ids1) == len(ids2) == 5      # impression, 2 HPO assessments, GMFCS, Vitalstatus
    assert not set(ids1.values()) & set(ids2.values()), "a later follow-up must not PUT over the earlier one"
    # a submission carrying both visits keeps the ids of each visit
    both = copy.deepcopy(base)
    both["followUp"]["followUpRds"] = [fus[1], fus[0]]         # order does not matter either
    ids_both = followup_ids(run(both)[0], both)
    assert set(ids1.values()) | set(ids2.values()) == set(ids_both.values())


def test_rd_followup_same_date_gets_index_and_warning():
    dk = load(RD_ENUMS)
    fus = dk["followUp"]["followUpRds"]
    dup = copy.deepcopy(fus[1])
    dup["followUpDate"] = fus[0]["followUpDate"]
    dk["followUp"]["followUpRds"] = [fus[0], dup]
    bundle, rep = run(dk)
    cis = resources(bundle, "ClinicalImpression")
    assert len(cis) == 2 and len({r["id"] for r in cis}) == 2
    vital = [r for r in resources(bundle, "Observation") if has_profile(r, "Vitalstatus")]
    assert len({r["id"] for r in vital}) == 2
    assert any("two follow-ups dated 2026-05-15" in m for m in warnings(rep, "followUp.followUpRds[].followUpDate"))


def test_rd_followup_id_is_date_keyed():
    dk = load(RD_ENUMS)
    fu = dk["followUp"]["followUpRds"][0]
    dk["followUp"]["followUpRds"] = [fu]
    bundle, _ = run(dk)
    key = case_key(dk, "rare-disease")
    (ci,) = resources(bundle, "ClinicalImpression")
    assert ci["id"] == key.id("ClinicalImpression", "followup", fu["followUpDate"], "impression")


# ---- F18: deathDate before onset / consent / board: warning, value kept --------------------------------------
def test_rd_death_date_before_case_dates_warns_and_keeps_value():
    dk = load(RD_ENUMS)
    last = dk["followUp"]["followUpRds"][-1]
    last["deathDate"] = "2005-05"            # generator artifact: birth month + 24 years
    bundle, rep = run(dk)
    (pat,) = resources(bundle, "Patient")
    assert pat["deceasedDateTime"] == "2005-05"
    msgs = [m for m in warnings(rep, "followUp.followUpRds[].deathDate") if m.startswith("data quality")]
    for path in ("case.diagnosisRd.symptomOnsetDate", "metaData.mvConsent.presentationDate",
                 "metaData.mvConsent.scope[].date", "metaData.molecularBoardDecisionDate",
                 "case.diagnosisRd.molecularBoardDecisionDate", "plan.carePlanRd.molecularBoardDecisionDate"):
        assert sum(path + " " in m for m in msgs) == 1, (path, msgs)


def test_rd_plausible_death_date_no_warning():
    dk = load(RD_ENUMS)     # deathDate 2026-09, after every case date (same month as nothing later)
    bundle, rep = run(dk)
    assert resources(bundle, "Patient")[0]["deceasedDateTime"] == "2026-09"
    assert not [m for m in warnings(rep, "followUp.followUpRds[].deathDate") if m.startswith("data quality")]


# ---- R56: DIMDI namespace normalised to BfArM ------------------------------------------------------------
def test_rd_diagnosis_dimdi_systems_normalised():
    dk = load(RD_ENUMS)
    for dx in dk["case"]["diagnosisRd"]["diagnoses"]:
        if dx["system"].endswith("icd-10-gm"):
            dx.update(system="http://fhir.de/CodeSystem/dimdi/icd-10-gm", code="C179")
        elif "Alpha-ID" in dx["system"]:
            dx["system"] = "http://fhir.de/CodeSystem/dimdi/alpha-id"
    bundle, rep = run(dk)
    cond = next(r for r in resources(bundle, "Condition") if has_profile(r, "mii-pr-seltene-genetic-diagnosis")
                or has_profile(r, "mii-pr-seltene-clinical-diagnosis"))
    by_system = {c["system"]: c for c in cond["code"]["coding"]}
    assert by_system[ICD10GM]["code"] == "C17.9" and by_system[ICD10GM]["version"] == "2026"
    assert by_system[ALPHA_ID]["code"] == "I135711"
    assert not any("dimdi" in s.lower() for s in by_system)
    assert not warnings(rep, "case.diagnosisRd.diagnoses[].system")
    assert any("'C179' normalised to 'C17.9'" in m for m in warnings(rep, "case.diagnosisRd.diagnoses[].code"))


# ---- R66: 2026 Therapieplan: study request not in activity (would match two slices) ---------------------------
def test_rd_careplan_2026_study_request_not_in_activity():
    dk = load(RD_ENUMS)
    bundle, rep = run(dk, "2026")
    idx = {e["fullUrl"]: e["resource"] for e in bundle["entry"]}
    (cp,) = [r for r in resources(bundle, "CarePlan") if has_profile(r, "mii-pr-seltene-therapieplan")]
    studies = [r for r in resources(bundle, "ServiceRequest") if has_profile(r, STUDY_REQ)]
    assert studies
    targets = [idx[a["reference"]["reference"]] for a in cp["activity"] if "reference" in a]
    assert not [t for t in targets if has_profile(t, STUDY_REQ)]
    for sr in studies:      # linked the other way round: request.basedOn -> the Therapieplan
        assert sr["basedOn"] == [{"reference": f"urn:uuid:{cp['id']}"}]
    assert rep.representations["seltene-2026-study-request-basedon-careplan"] == len(studies)


def test_rd_careplan_2027_study_request_stays_activity():
    bundle, _ = run(load(RD_ENUMS), "2027")
    (cp,) = [r for r in resources(bundle, "CarePlan") if has_profile(r, "mii-pr-seltene-therapieplan")]
    studies = [r for r in resources(bundle, "ServiceRequest") if has_profile(r, STUDY_REQ)]
    refs = {a["reference"]["reference"] for a in cp["activity"] if "reference" in a}
    assert studies and all(f"urn:uuid:{sr['id']}" in refs for sr in studies)
    assert not any("basedOn" in sr for sr in studies)


# ---- F15 / F16 / F17: RD variants -------------------------------------------------------------------------
def variant_ctx(dk, findings=()):
    rep = Report(file="<fix_rd_grz>")
    rep.input_findings = list(findings)
    ctx = Ctx(dk, "rare-disease", case_key(dk, "rare-disease"), "2027", rep, True)
    patient.build(ctx)
    variants.build(ctx)
    return ctx


def test_rd_comphet_in_bound_answer_list():
    dk = load(RD_VARIANTS)
    sv = dk["molecular"]["smallVariants"][0]
    sv["zygosity"] = "compHet"
    ctx = variant_ctx(dk)
    obs = next(r for r in resources(ctx.bundle.bundle(), "Observation") if r["id"] == ctx.id(
        "Observation", "rd-variant", "small", sv["identifier"]))
    (z,) = [c for c in obs["component"] if c["code"]["coding"][0]["code"] == "53034-5"]
    codings = z["valueCodeableConcept"]["coding"]
    assert codings[0] == {"system": LOINC, "code": "LA6706-1", "display": "Heterozygous"}   # in LL381-5
    assert codings[1]["code"] == "LA26217-2"        # the precise KDK meaning stays coded
    n = sum(v.get("zygosity") == "compHet" for k in ("smallVariants", "copyNumberVariants", "structuralVariants")
            for v in dk["molecular"].get(k) or [])
    assert ctx.report.representations["zygosity-comphet-heterozygous-plus-la26217-2"] == n


def test_rd_localization_keeps_kdk_value_as_text():
    dk = load(RD_VARIANTS)
    ctx = variant_ctx(dk)
    kons = [r for r in resources(ctx.bundle.bundle(), "Observation")
            if has_profile(r, "mii-pr-molgen-molekulare-konsequenz")]
    assert kons
    texts = [c["valueCodeableConcept"].get("text") for k in kons for c in k["component"]]
    assert texts and all(texts)
    sv = dk["molecular"]["smallVariants"][0]
    first = next(k for k in kons if k["id"] == ctx.id("Observation", "rd-consequence", "small", sv["identifier"]))
    assert [c["valueCodeableConcept"]["text"] for c in first["component"]] == [x["code"] for x in sv["localization"]]


def test_rd_gene_display_is_not_reported_unknown():
    dk = load(RD_VARIANTS)
    pointer = "/molecular/smallVariants/0/genes/0"
    ctx = variant_ctx(dk, [f"unknown field {pointer}/display", f"unknown field {pointer}/system"])
    # fix round 3 (R36): display is emitted (gene-studied coding.display) and covered as a converted undeclared field;
    # the validator's findings stay (the CLI reports display 'converted', --strict rejects it), system is not emitted
    assert ctx.report.input_findings == [f"unknown field {pointer}/display", f"unknown field {pointer}/system"]
    assert "molecular.smallVariants[].genes[].display" in ctx.report.covered
    assert not [p for p in ctx.report.covered if p.endswith("genes[].system")]


def test_rd_gene_display_full_conversion():
    from genomde2fhir.io import input_check_available
    if not input_check_available():
        pytest.skip("genomde-dk-validator not installed")
    _, rep = run(load(RD_VARIANTS))
    # fix round 3 (R36): the finding is kept and the path covered, so the CLI judges it 'converted'
    shown = [f for f in rep.input_findings if f.endswith("/display") and "/genes/" in f]
    assert shown and "molecular.smallVariants[].genes[].display" in rep.covered


# ---- R29: GRZ ICD-O-3 bodySite edition and code ---------------------------------------------------------
def grz_with(profile_set="2027", **labdata):
    dk = load(GRZ_DUO)
    dk["donors"][0]["labData"][0].update(labdata)
    bundle, rep = run(dk, profile_set)
    spec = next(r for r in resources(bundle, "Specimen")
                if any(i["value"].endswith("|index-wes") for i in r.get("identifier", [])))
    return spec, rep


@pytest.mark.parametrize("given,expected", [("Zweite Revision", "2019"), ("rev2", "2019"), ("3.2", "2019"),
                                            ("ICD-O-3.1", "2014"), ("erste revision", "2014"), ("2019", "2019")])
def test_grz_icdo3_edition_normalised(given, expected):
    spec, rep = grz_with(tissueTypeId="C34.1", tissueTypeName="Oberlappen",
                         tissueOntology={"name": "ICD-O-3", "version": given})
    (c,) = spec["collection"]["bodySite"]["coding"]
    assert (c["system"], c["code"], c["version"]) == (ICDO3, "C34.1", expected)
    assert "donors[].labData[].tissueOntology.version" in rep.covered


@pytest.mark.parametrize("given", ["2024", "ICD-O-3"])
def test_grz_icdo3_unknown_edition_dropped_with_warning(given):
    spec, rep = grz_with(tissueTypeId="C34.1", tissueTypeName="Oberlappen",
                         tissueOntology={"name": "ICD-O-3", "version": given})
    (c,) = spec["collection"]["bodySite"]["coding"]
    assert "version" not in c and c["code"] == "C34.1"
    assert warnings(rep, "donors[].labData[].tissueOntology.version")
    assert ("donors[].labData[].tissueOntology.version", given) in [(p, v) for p, v, _ in rep.dropped]


def test_grz_icdo3_undotted_topography_normalised():
    spec, rep = grz_with(tissueTypeId="C341", tissueTypeName="Oberlappen",
                         tissueOntology={"name": "ICD-O-3", "version": "2019"})
    (c,) = spec["collection"]["bodySite"]["coding"]
    assert (c["code"], c["version"]) == ("C34.1", "2019")
    assert any("normalised to 'C34.1'" in m for m in warnings(rep, "donors[].labData[].tissueTypeId"))


# ---- R45: 2026 SpecimenCore processing needs Temperaturbedingungen ----------------------------------------
@pytest.mark.parametrize("conservation", ["ffpe", "cryo-frozen"])
def test_grz_2026_processing_has_temperature_extension(conservation):
    spec, rep = grz_with("2026", sampleConservation=conservation)
    (pr,) = spec["processing"]
    (e,) = pr["extension"]
    assert e == {"url": TEMPERATURE, "valueRange": {"extension": [{"url": DAR, "valueCode": "unknown"}]}}
    assert rep.representations["specimen-2026-temperature-data-absent"] == 1


def test_grz_2027_processing_without_temperature_extension():
    spec, _ = grz_with("2027", sampleConservation="ffpe")
    (pr,) = spec["processing"]
    assert "extension" not in pr and pr["procedure"]["coding"]
