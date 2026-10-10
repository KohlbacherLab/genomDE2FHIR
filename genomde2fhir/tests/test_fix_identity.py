"""Regression tests for the identity review findings (R05 R06 R07 R08/F05 R14 R42/F07 R43 R63 R65 R39 R50 C6/F06).

Small synthetic variants of the committed fixtures; no corpus, no server."""
import json
from pathlib import Path

import pytest
from conftest import resources

from genomde2fhir import convert
from genomde2fhir.builders import patient, research_consent
from genomde2fhir.bundle import structural_errors
from genomde2fhir.context import Ctx
from genomde2fhir.identity import case_key, rid
from genomde2fhir.report import summarize
from genomde2fhir.systems import SID_DONOR, SID_LOCAL_CASE

FIX = Path(__file__).parent / "fixtures"
ONCO = FIX / "onco_variants" / "synthetic_small_variants.json"     # KDK oncology, localCaseId, smallVariants
CONSENT = FIX / "consent" / "onco_edge.json"                        # KDK oncology with an embedded Broad Consent
GRZ = FIX / "grz_labdata" / "grz-labdata-rd-duo.json"               # GRZ initial, index + mother with labData
HTEST = {"system": "http://terminology.hl7.org/CodeSystem/v3-ActReason", "code": "HTEST", "display": "test health data"}
BROAD = "https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-consent-einwilligung"
MOLECULAR_FINDING = "https://genomde.de/fhir/sid/molecular-finding-id"
EXT_ANALYSIS = "http://hl7.org/fhir/uv/genomics-reporting/StructureDefinition/genomic-study-analysis-ext"


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def kdk(stype: str, **md) -> dict:
    dk = load(ONCO)
    dk["metaData"]["submission"]["type"] = stype
    dk["metaData"].update(md)
    return dk


def grz(stype: str, **sub) -> dict:
    dk = load(GRZ)
    dk["submission"]["submissionType"] = stype
    dk["submission"].update(sub)
    return dk


def run(dk, name="<fix>", **kw):
    bundle, rep = convert(dk, name, **kw)
    assert rep.status == "converted", rep.error or rep.input_findings
    return bundle, rep


def ids(bundle) -> set:
    return {e["fullUrl"] for e in bundle["entry"]}


def identifier_values(bundle, system: str | None = None) -> set:
    return {(i["system"], i["value"]) for r in resources(bundle) for i in r.get("identifier", [])
            if i.get("value") and (system is None or i["system"] == system)}


def ident(r, system):
    return next((i["value"] for i in r.get("identifier", []) if i["system"] == system), None)


def provenance(bundle) -> dict:
    [prov] = resources(bundle, "Provenance")
    return prov


def activity_code(prov):
    return [c["code"] for c in prov["activity"].get("coding", [])]


# ---- R05: test submissions ----------------------------------------------------------------------------------------
EXTERNAL = {"https://genomde.de/fhir/sid/le-id", "https://genomde.de/fhir/sid/genomic-data-center",
            "https://genomde.de/fhir/sid/clinical-data-node"}
# lab-data identifiers are built in builders/grz/labdata.py (handoff: case-scoped ctx.key.scoped / sender_scoped)
LABDATA = {"https://genomde.de/fhir/sid/grz-lab-data-name", "https://genomde.de/fhir/sid/grz-sample-barcode"}


def real_and_test(make):
    real, _ = run(make("initial"))
    tdk = make("test")
    if "metaData" in tdk:      # a TAN is per submission: the test submission has its own
        tdk["metaData"]["tanC"] = "E" * 64
    else:
        tdk["submission"]["tanG"] = "e" * 64
    test, rep = run(tdk)
    return real, test, rep


@pytest.mark.parametrize("make", [kdk, grz], ids=["kdk", "grz"])
def test_r05_test_submission_never_shares_ids_or_identifiers_with_real_data(make):
    real, test, rep = real_and_test(make)
    assert not ids(real) & ids(test), "a test submission overwrites the real case"
    shared = identifier_values(real) & identifier_values(test)
    # only identifiers of external entities stay equal: the sender / data-node Organizations
    assert {s for s, _ in shared} - LABDATA <= EXTERNAL, shared
    for r in resources(test):
        assert HTEST in r["meta"]["security"], r["resourceType"]
    assert not any("security" in r.get("meta", {}) for r in resources(real))
    assert rep.test and rep.submission_type == "test"
    assert any("test submission" in m for _, m in rep.warnings)
    assert not structural_errors(test)


def test_r05_grz_labdata_identifiers_marked_for_test():
    real, test, _ = real_and_test(grz)
    assert not {s for s, _ in identifier_values(real) & identifier_values(test)} & LABDATA


def test_r05_test_case_key_marker_cannot_collide_with_a_real_case_id():
    # a real localCaseId 'X|test' must not meet the test namespace of case 'X'
    real = case_key(kdk("initial", localCaseId="X|test"), "oncology")
    test = case_key(kdk("test", localCaseId="X"), "oncology")
    assert real.id("Patient") != test.id("Patient")
    assert real.scoped() != test.scoped() and test.scoped().endswith("|X|test")


def test_r05_local_case_id_identifier_marks_test():
    b, _ = run(kdk("test"))
    [pat] = resources(b, "Patient")
    md = load(ONCO)["metaData"]
    assert ident(pat, SID_LOCAL_CASE) == f"{md['submission']['submitterId']}|{md['localCaseId']}|test"


# ---- R07 / R65: one Provenance per submission, v3-DataOperation by type ---------------------------------------------
@pytest.mark.parametrize("make", [kdk, grz], ids=["kdk", "grz"])
def test_r07_r65_provenance_per_submission_with_consistent_activity(make):
    codes, prov_ids = {}, set()
    for stype, date in (("initial", "2026-01-01"), ("followup", "2026-02-01"), ("addition", "2026-03-01"),
                        ("correction", "2026-04-01"), ("test", "2026-05-01")):
        dk = make(stype)
        (dk["metaData"]["submission"] if "metaData" in dk else dk["submission"])[
            "date" if "metaData" in dk else "submissionDate"] = date
        b, _ = run(dk)
        prov = provenance(b)          # exactly one, also for GRZ (no contradicting second Provenance)
        codes[stype] = activity_code(prov)
        prov_ids.add(prov["id"])
        assert prov["occurredDateTime"] == date and prov["recorded"] == f"{date}T00:00:00Z"
        assert len(prov["target"]) == len(b["entry"]) - 1
    assert codes == {"initial": ["CREATE"], "followup": ["APPEND"], "addition": ["APPEND"],
                     "correction": ["UPDATE"], "test": []}
    assert len(prov_ids) == 5, "a later submission overwrites the earlier submission's Provenance"


def test_r07_same_submission_resent_keeps_its_provenance_id():
    a, _ = run(kdk("initial"))
    b, _ = run(kdk("initial"))
    assert provenance(a)["id"] == provenance(b)["id"]


def test_r07_tan_is_part_of_the_provenance_key():
    a, _ = run(kdk("followup"))
    b, _ = run(kdk("followup", tanC="F" * 64))
    assert provenance(a)["id"] != provenance(b)["id"]


def test_r07_grz_provenance_agents_reference_the_submission_organizations():
    b, _ = run(grz("initial"))
    prov = provenance(b)
    orgs = {"urn:uuid:" + o["id"] for o in resources(b, "Organization")}
    refs = [a["who"].get("reference") for a in prov["agent"] if a["type"]["coding"][0]["code"] != "assembler"]
    assert len(refs) == 3 and set(refs) <= orgs


# ---- R06: GRZ genomic study per submission ------------------------------------------------------------------------
def study(bundle):
    [st] = [r for r in resources(bundle, "Procedure")
            if any(p.endswith("-genomic-study") for p in r.get("meta", {}).get("profile", []))]
    return st


def test_r06_addition_gets_its_own_genomic_study():
    init, _ = run(grz("initial"))
    add = grz("addition", tanG="ab" * 32, submissionDate="2026-06-01", genomicStudySubtype="germline-only")
    add["donors"][0]["labData"][0]["labDataName"] = "index-wgs-addition"
    add["donors"] = add["donors"][:1]
    addb, _ = run(add)
    s1, s2 = study(init), study(addb)
    assert s1["id"] != s2["id"], "the addition overwrites the initial submission's genomic study"
    a1 = {e["valueReference"]["reference"] for e in s1.get("extension", []) if e["url"] == EXT_ANALYSIS}
    a2 = {e["valueReference"]["reference"] for e in s2.get("extension", []) if e["url"] == EXT_ANALYSIS}
    assert len(a1) == 2 and len(a2) == 1 and not a1 & a2      # each study lists its own submission's labData
    # the same submission re-sent (same TAN-G and date) rewrites its own study
    again, _ = run(grz("initial"))
    assert study(again)["id"] == s1["id"]


# ---- R08 / F05: tanC fallback warning and summary count ---------------------------------------------------------------
def test_r08_tanc_fallback_is_warned_and_counted():
    dk = kdk("followup")
    dk["metaData"].pop("localCaseId")
    _, rep = run(dk)
    assert rep.case_key_fallback
    assert any(p == "metaData.localCaseId" and "case key = tanC" in m for p, m in rep.warnings)
    _, rep_local = run(kdk("followup"))
    assert not rep_local.case_key_fallback and not any("case key = tanC" in m for _, m in rep_local.warnings)
    assert summarize([rep, rep_local])["case_key_tan_fallback"] == 1


def test_r08_grz_tang_fallback_is_warned():
    dk = grz("initial")
    dk["submission"].pop("localCaseId")
    _, rep = run(dk, check_input=False)          # localCaseId is required in the GRZ schema
    assert rep.case_key_fallback and any("case key = tanG" in m for _, m in rep.warnings)


# ---- R14: donor pseudonym identifiers are case-scoped -----------------------------------------------------------------
def test_r14_literal_index_pseudonym_does_not_collide_across_cases():
    vals = []
    for case in ("CASE-A", "CASE-B"):
        dk = grz("initial", localCaseId=case)
        dk["donors"][0]["donorPseudonym"] = "index"
        b, _ = run(dk)
        [index] = [p for p in resources(b, "Patient") if ident(p, SID_LOCAL_CASE)]
        vals.append(ident(index, SID_DONOR))
    assert vals == ["260840108|CASE-A|index", "260840108|CASE-B|index"]


def test_r14_labdata_identifier_is_case_scoped():
    vals = []
    for case in ("CASE-A", "CASE-B"):
        dk = grz("initial", localCaseId=case)
        dk["donors"][0]["donorPseudonym"] = "index"
        b, _ = run(dk)
        vals.append(identifier_values(b, "https://genomde.de/fhir/sid/grz-lab-data-name"))
    assert not vals[0] & vals[1]


# ---- R42 / F07: report carries the submission type ----------------------------------------------------------------------
def test_r42_report_lists_submission_type_and_test_flag():
    _, rep = run(kdk("correction"))
    d = rep.to_dict()
    assert d["submission_type"] == "correction" and d["test"] is False
    assert d["submission_date"] == load(ONCO)["metaData"]["submission"]["date"] and d["case_key_fallback"] is False
    _, rep_t = run(grz("test"))
    assert rep_t.to_dict()["test"] is True and rep_t.to_dict()["submission_type"] == "test"
    s = summarize([rep, rep_t])
    assert s["submission_types"] == {"correction": 1, "test": 1} and s["test_submissions"] == 1


def test_r42_submission_type_preserved_only_when_represented():
    # meta.source (R43, round 2) carries date and type on every resource, also without the Provenance
    _, rep = run(kdk("initial"), provenance=False)
    assert {"metaData.submission.type", "metaData.submission.date"} <= rep.preserved
    assert rep.representations["meta-source"] == 2 and "submission-provenance" not in rep.representations
    _, rep = run(kdk("initial"))
    assert {"metaData.submission.type", "metaData.submission.date"} <= rep.preserved
    assert rep.representations["submission-provenance"] == 2
    _, rep = run(kdk("test"), provenance=False)           # the HTEST label still carries 'test'
    assert "metaData.submission.type" in rep.preserved


# ---- R43: removed items stay on the server; the per-submission Provenance makes them detectable -------------------------
def test_r43_removed_items_are_found_by_comparing_submission_provenances():
    init_dk = kdk("initial")
    corr_dk = kdk("correction")
    corr_dk["metaData"]["submission"]["date"] = "2026-07-01"
    removed = corr_dk["molecular"]["smallVariants"].pop(0)["identifier"]       # the correction withdraws 'sv-1'
    init, _ = run(init_dk)
    corr, _ = run(corr_dk)
    p1, p2 = provenance(init), provenance(corr)
    assert p1["id"] != p2["id"]
    stale = {t["reference"] for t in p1["target"]} - {t["reference"] for t in p2["target"]}
    stale_resources = [e["resource"] for e in init["entry"] if e["fullUrl"] in stale]
    assert stale_resources and all(r["resourceType"] != "Provenance" for r in stale_resources)
    found = {i["value"] for r in stale_resources for i in r.get("identifier", []) if i["system"] == MOLECULAR_FINDING}
    assert any(v.endswith("|" + removed) for v in found), found


# ---- R63: escaping of '|' in id and identifier components -----------------------------------------------------------------
def test_r63_separator_in_components_does_not_collide():
    a = case_key(kdk("initial", localCaseId="case"), "oncology")
    b = case_key(kdk("initial", localCaseId="case|Observation|small-variant"), "oncology")
    assert a.id("Observation", "small-variant", "Observation|small-variant|v") != b.id("Observation", "small-variant", "v")
    assert rid("a|b", "c") != rid("a", "b|c") and rid("a\\", "|b") != rid("a\\|", "b")
    assert a.scoped("x|y") != case_key(kdk("initial", localCaseId="case|x"), "oncology").scoped("y")


def test_r63_ids_unchanged_for_plain_components():
    # escaping only touches '|' and '\\': the ids of ordinary inputs stay what earlier releases emitted
    k = case_key(kdk("initial", localCaseId="CASE-1"), "oncology")
    assert k.id("Patient") == rid("kdk", k.submitter_id, "CASE-1", "Patient")
    assert k.scoped("v") == f"{k.submitter_id}|CASE-1|v"


def test_r63_local_case_id_identifier_escapes_separator():
    b, _ = run(kdk("initial", localCaseId="CASE 7/a|b"))
    [pat] = resources(b, "Patient")
    assert ident(pat, SID_LOCAL_CASE).endswith("|CASE 7/a\\|b")


# ---- research consent: contained (R39), no policy (R50), drops (C6 / F06) ----------------------------------------------
def consent_run(mutate):
    dk = load(CONSENT)
    mutate(dk["metaData"]["researchConsents"][0]["scope"])
    ctx = Ctx(dk, "oncology", case_key(dk, "oncology"), "2027", strict=True)
    patient.build(ctx)
    research_consent.build(ctx)
    bundle = {"entry": list(ctx.bundle.entries.values())}
    [con] = resources(bundle, "Consent")
    return con, ctx.report, bundle


def test_r39_referenced_contained_resources_are_kept_unreferenced_dropped():
    def mutate(sc):
        sc["contained"] = [{"resourceType": "Practitioner", "id": "doctor", "name": [{"family": "Example"}],
                            "qualification": [{"code": {"text": "x"}, "issuer": {"reference": "Organization/o9"}}]},
                           {"resourceType": "Organization", "id": "unused", "name": "nobody"}]
        sc["performer"] = [{"reference": "#doctor"}]
        sc["organization"] = [{"reference": "#missing"}]
    con, rep, bundle = consent_run(mutate)
    assert [c["id"] for c in con["contained"]] == ["doctor"]
    assert con["performer"] == [{"reference": "#doctor"}]
    # the contained resource's own sender-system reference is stripped like the others
    assert con["contained"][0]["qualification"][0]["issuer"] == {"display": "Organization/o9 (sender system)"}
    assert con["organization"] == [{"display": "#missing (missing contained resource)"}]
    assert ("metaData.researchConsents[].scope", "contained Organization/unused", "contained resource neither "
            "referenced from the carried-over elements nor referring to the Consent") in rep.dropped
    assert not structural_errors(bundle)


def test_r50_consent_without_policy_is_not_claimed_as_einwilligung():
    def mutate(sc):
        sc.pop("policy")
    con, rep, bundle = consent_run(mutate)
    assert BROAD not in con.get("meta", {}).get("profile", [])
    assert con["policyRule"]["extension"][0]["url"].endswith("data-absent-reason")     # core ppc-1
    assert "metaData.researchConsents[].scope" in rep.preserved
    assert "metaData.researchConsents[].scope" not in rep.covered
    assert any("without policy" in m for _, m in rep.warnings)
    assert not structural_errors(bundle)


def test_r50_consent_with_policy_rule_only_keeps_it():
    def mutate(sc):
        sc.pop("policy")
        sc["policyRule"] = {"text": "local rule"}
    con, rep, _ = consent_run(mutate)
    assert con["policyRule"] == {"text": "local rule"} and "meta" not in con


def test_c6_f06_discarded_sub_elements_are_reported_as_dropped():
    def mutate(sc):
        sc["text"] = {"status": "generated", "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">Name</div>"}
        sc["implicitRules"] = "http://example.org/rules"
    con, rep, _ = consent_run(mutate)
    drops = {v: r for p, v, r in rep.dropped if p == "metaData.researchConsents[].scope"}
    sc = load(CONSENT)["metaData"]["researchConsents"][0]["scope"]
    assert f"id {sc['id']}" in drops
    assert any(v.startswith("meta ") and "lastUpdated" in v for v in drops)
    assert "text (narrative)" in drops and "Name" not in " ".join(drops)        # no narrative content in the report
    assert "patient display, reference" in drops and "Pseudonym" not in " ".join(drops)
    assert "implicitRules http://example.org/rules" in drops
    assert any(v.startswith("DomainReference ResearchStudy/") and "domain + status" in r for v, r in drops.items())
    assert any(v.startswith("dateTime ") for v in drops)     # embedded dateTime replaced by presentationDate
    assert "extension" not in con
