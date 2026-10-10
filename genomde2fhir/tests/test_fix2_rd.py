"""Regression tests for fix round 2, group rd (RD builders).

R54         an empty new key counts as absent: 'priorRds: []' / 'variants: []' next to the pre-1.6.5 key read the
            legacy key, as the FML does (matchbox parses [] as a missing key)
RD-BASEDON  the Seltene Therapieplan points basedOn at the indication-board CarePlan (mvgs-inclusion-decision);
            CarePlan.basedOn is 0..* CarePlan in seltene 2026.0.1 and 2027.0.0-ballot
"""
import copy
from pathlib import Path

import pytest
from conftest import load, resources

from genomde2fhir import convert
from genomde2fhir.builders import patient
from genomde2fhir.builders.rd import careplan
from genomde2fhir.context import Ctx
from genomde2fhir.identity import case_key
from genomde2fhir.report import Report

FIX = Path(__file__).parent / "fixtures"
RD_ENUMS = FIX / "rd_plan_followup" / "rd_plan_followup_all_enums.json"       # legacy case.priorRd, variants[]
RD_VARIANTS = FIX / "rd_variants" / "rd-variants-edge-cases.json"              # legacy variantReferences
THERAPIEPLAN = "mii-pr-seltene-therapieplan"
BOARD = "mvgs-inclusion-decision"
PRIOR_LEGACY_WARNING = "legacy key case.priorRd (KDK < 1.6.5) read as priorRds"
VARIANT_LEGACY_WARNING = "non-schema key 'variantReferences' read as 'variants'"


def run(dk, profile_set="2027", strict=True):
    bundle, rep = convert(dk, "<fix2_rd>", profile_set, strict=strict)
    assert rep.status == "converted", rep.error or rep.input_findings
    return bundle, rep


def recommendations(dk) -> list[dict]:
    plan = dk.get("plan") or {}
    return (plan.get("recommendedTherapies") or []) + (plan.get("recommendedStudies") or [])


def prior_resources(bundle) -> list[tuple]:
    """(type, profile) of the resources rd.prior emits (request, report, band Observations, ZSE episode)."""
    out = []
    for r in resources(bundle):
        prof = " ".join(r.get("meta", {}).get("profile", []))
        if r["resourceType"] == "ServiceRequest" and r.get("status") == "completed" and "anforderung-genetischer-test" in prof:
            out.append(("ServiceRequest", "prior-test"))
        elif r["resourceType"] == "DiagnosticReport" and "molekulargenetischer-befundbericht" in prof \
                and r.get("basedOn"):
            out.append(("DiagnosticReport", "prior-report"))
        elif r["resourceType"] == "Observation" and r.get("code", {}).get("coding", [{}])[0].get("code") in (
                "hospitalization-duration", "hospitalization-periods"):
            out.append(("Observation", r["code"]["coding"][0]["code"]))
        elif r["resourceType"] == "EpisodeOfCare":
            out.append(("EpisodeOfCare", "zse"))
    return sorted(out)


def therapieplan(bundle) -> dict:
    (plan,) = resources(bundle, "CarePlan", THERAPIEPLAN)
    return plan


def reason_refs(bundle) -> dict:
    """{recommendation identifier value: sorted reasonReference strings} of the RD recommendations."""
    out = {}
    for r in resources(bundle):
        if r["resourceType"] in ("MedicationRequest", "ServiceRequest") and r.get("identifier") \
                and r.get("intent") == "proposal":
            out[r["identifier"][0]["value"]] = sorted(x["reference"] for x in r.get("reasonReference", []))
    return out


# ---- R54: an empty new key counts as absent (FML parity) -----------------------------------------------------
@pytest.mark.parametrize("profile_set", ["2027", "2026"])
def test_r54_empty_prior_rds_reads_legacy_prior_rd(profile_set):
    legacy_only = load(RD_ENUMS)
    assert "priorRds" not in legacy_only["case"] and legacy_only["case"].get("priorRd")
    empty_new = copy.deepcopy(legacy_only)
    empty_new["case"]["priorRds"] = []
    b_legacy, rep_legacy = run(legacy_only, profile_set)
    b_empty, rep_empty = run(empty_new, profile_set)
    # the FML reads the legacy key here: request, report, both band Observations, the ZSE episode
    assert prior_resources(b_empty) == prior_resources(b_legacy) == [
        ("DiagnosticReport", "prior-report"), ("EpisodeOfCare", "zse"), ("Observation", "hospitalization-duration"),
        ("Observation", "hospitalization-periods"), ("ServiceRequest", "prior-test")]
    assert b_empty == b_legacy, "'priorRds: []' must convert exactly like an absent priorRds"
    assert ("case.priorRds[]", PRIOR_LEGACY_WARNING) in rep_empty.warnings
    # the prior-findings report is supportingInfo of the Therapieplan (rd report + prior report)
    assert len(therapieplan(b_empty)["supportingInfo"]) == 2


def test_r54_non_empty_prior_rds_still_wins_over_legacy_key():
    dk = load(RD_ENUMS)
    entry = copy.deepcopy(dk["case"]["priorRd"])
    entry.update(genomicTestType="exome", hospitalizationDuration="upToFifty")   # legacy: genomeShortRead, upToFive
    dk["case"]["priorRds"] = [entry]
    b, rep = run(dk)
    (sr,) = [r for r in resources(b, "ServiceRequest") if r.get("status") == "completed"]
    assert sr["code"]["coding"][0]["code"] == "exome"
    (dur,) = [r for r in resources(b, "Observation") if r["code"]["coding"][0]["code"] == "hospitalization-duration"]
    assert dur["valueCodeableConcept"]["coding"][0]["code"] == "upToFifty"
    assert ("case.priorRds[]", PRIOR_LEGACY_WARNING) not in rep.warnings


def test_r54_empty_legacy_prior_rd_is_absent_too():
    dk = load(RD_ENUMS)
    dk["case"]["priorRd"] = []
    b, rep = run(dk)
    assert prior_resources(b) == []
    assert ("case.priorRds[]", PRIOR_LEGACY_WARNING) not in rep.warnings


def test_r54_empty_variants_reads_legacy_variant_references():
    legacy_only = load(RD_VARIANTS)
    recs = recommendations(legacy_only)
    assert recs and all(r.get("variantReferences") and "variants" not in r for r in recs)
    for r, vid in zip(recs, ("SNV-1", "CNV-1")):    # the fixture's legacy ids cite no converted variant
        r["variantReferences"] = [vid]
    empty_new = copy.deepcopy(legacy_only)
    for r in recommendations(empty_new):
        r["variants"] = []
    b_legacy, _ = run(legacy_only)
    b_empty, rep_empty = run(empty_new)
    refs = reason_refs(b_empty)
    assert refs == reason_refs(b_legacy)
    # each recommendation cites its legacy variant (plus the diagnosis Condition)
    assert refs and all(any(x.startswith("urn:uuid:") for x in v) and len(v) == 2 for v in refs.values())
    assert b_empty == b_legacy, "'variants: []' must convert exactly like an absent variants key"
    assert sum(m == VARIANT_LEGACY_WARNING for _, m in rep_empty.warnings) == len(recs)


def test_r54_empty_variants_reads_legacy_key_on_all_enums():
    """variants[] moved to variantReferences with 'variants: []' left behind: same reasons as the original."""
    base = load(RD_ENUMS)
    moved = copy.deepcopy(base)
    for r in recommendations(moved):
        if r.get("variants"):
            r["variantReferences"], r["variants"] = r["variants"], []
    assert reason_refs(run(moved)[0]) == reason_refs(run(base)[0])


def test_r54_non_empty_variants_still_wins_over_legacy_key():
    base = load(RD_ENUMS)
    dk = copy.deepcopy(base)
    for r in recommendations(dk):
        if r.get("variants"):
            r["variantReferences"] = ["no-such-legacy-variant"]
    b, rep = run(dk)
    assert reason_refs(b) == reason_refs(run(base)[0])
    assert VARIANT_LEGACY_WARNING not in [m for _, m in rep.warnings]
    assert not any(v == "no-such-legacy-variant" for _, v, _ in rep.dropped)


# ---- RD-BASEDON: Therapieplan.basedOn -> indication board ------------------------------------------------------
@pytest.mark.parametrize("profile_set", ["2027", "2026"])
def test_rd_therapieplan_based_on_indication_board(profile_set):
    b, _ = run(load(RD_ENUMS), profile_set)
    (board,) = [e for e in b["entry"] if BOARD in " ".join(e["resource"].get("meta", {}).get("profile", []))]
    assert therapieplan(b)["basedOn"] == [{"reference": board["fullUrl"]}]


@pytest.mark.parametrize("profile_set", ["2027", "2026"])
def test_rd_therapieplan_without_indication_board_has_no_based_on(profile_set):
    """No indication board (the schema requires its date, so the builder runs on a context without it)."""
    dk = load(RD_ENUMS)
    ctx = Ctx(dk, "rare-disease", case_key(dk, "rare-disease"), profile_set, Report(file="<fix2_rd>"), True)
    patient.build(ctx)
    careplan.build(ctx)
    assert "indication_board" not in ctx.refs
    (plan,) = [e["resource"] for e in ctx.bundle.entries.values()
               if e["resource"]["resourceType"] == "CarePlan"]
    assert "basedOn" not in plan
