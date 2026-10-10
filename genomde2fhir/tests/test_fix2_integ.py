"""Regression tests for the integration step of fix round 2.

R36 (cli handoff)  builders record a disposition for the undeclared input fields they convert, so cli._undeclared
                   reports them as converted: germlineDiagnoses[].date (onco diagnosis), the legacy keys
                   case.priorDiagnostic (onco prior) and case.priorRd (rd prior, only when it is read) and
                   plan.recommended*[].variantReferences (rd careplan, only when read as variants).
R68 (onco handoff) validate.NAMED_PROFILE also reads '(defined in <profile>)', so a candidate profile's invariant at a
                   tried reference target is 'candidate', not the target's own content; a message naming the
                   target's own profile chain (declared profile, its ancestors, core type) stays its own.

Inputs: the legacy-key fixtures under tests/fixtures/legacy_keys/ (derived from the 2026-08-09 mv_dummy example files,
whose revision no longer carries priorDiagnostic / priorRd / variantReferences) and the tracked onco_diagnosis
fixture, changed in memory; matchbox is faked.
"""
import copy
import json

import pytest

from genomde2fhir import convert
from genomde2fhir.cli import _undeclared, main
from genomde2fhir.validate import BASE_SD, NAMED_PROFILE, validate_bundle

from conftest import REPO
from test_fix_validate import MII, UNCHECKED_PT, _tnm, at, cls_of, iss

LEGACY = REPO / "genomde2fhir/tests/fixtures/legacy_keys"
ONCO = LEGACY / "onco_legacy_prior_diagnostic.json"          # case.priorDiagnostic (object)
RD = LEGACY / "rd_legacy_prior_rd_variant_references.json"     # case.priorRd, plan.recommended*[].variantReferences
DIAG_FULL = REPO / "genomde2fhir/tests/fixtures/onco_diagnosis/diagnosis_full.json"
THERAPY_REFS, STUDY_REFS = ("plan.recommendedTherapies[].variantReferences", "plan.recommendedStudies[].variantReferences")


def load(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(dk, strict=False):
    bundle, rep = convert(dk, "x", strict=strict, check_input=False)
    assert rep.status == "converted", rep.error
    return bundle, rep


def judged(rep, *pointers) -> list:
    """cli._undeclared for genomde-dk-validator 'unknown field' findings at these pointers."""
    rep.input_findings = [f"unknown field {p}" for p in pointers]
    return [d for _, d in _undeclared(rep)]


# ---- R36: undeclared fields a builder converts are 'converted' ---------------------------------------------------
def test_germline_diagnosis_date_is_converted_also_under_strict():
    dk = load(DIAG_FULL)
    dk["case"]["diagnosisOd"]["germlineDiagnoses"][0]["date"] = "2020-02-03"
    bundle, rep = run(dk, strict=True)   # no mapping row needed: no KeyError under strict
    assert "case.diagnosisOd.germlineDiagnoses[].date" in rep.covered
    assert any(r.get("recordedDate") == "2020-02-03" for r in (e["resource"] for e in bundle["entry"]))
    assert judged(rep, "/case/diagnosisOd/germlineDiagnoses/0/date") == ["converted"]


def test_legacy_prior_diagnostic_is_converted_when_a_report_is_emitted():
    _, rep = run(load(ONCO))
    assert judged(rep, "/case/priorDiagnostic") == ["converted"]
    dk = load(ONCO)
    dk["case"]["priorDiagnostic"] = {"type": "none", "date": "2026-04-21"}   # no prior test: nothing emitted
    _, rep = run(dk)
    assert "case.priorDiagnostic" not in rep.covered and judged(rep, "/case/priorDiagnostic") == ["not converted"]


def test_legacy_prior_rd_is_converted_only_when_read():
    _, rep = run(load(RD), strict=True)
    assert judged(rep, "/case/priorRd") == ["converted"]
    dk = load(RD)
    dk["case"]["priorRds"] = [dict(dk["case"]["priorRd"], diagnosticDate="2025-01-01")]   # priorRd is ignored then
    _, rep = run(dk)
    assert not any("legacy key case.priorRd" in m for _, m in rep.warnings)
    assert judged(rep, "/case/priorRd") == ["not converted"]


def test_variant_references_are_converted_only_when_read_as_variants():
    _, rep = run(load(RD), strict=True)
    assert judged(rep, "/plan/recommendedTherapies/0/variantReferences",
                  "/plan/recommendedStudies/0/variantReferences") == ["converted", "converted"]
    dk = load(RD)
    for rec in dk["plan"]["recommendedTherapies"] + dk["plan"]["recommendedStudies"]:
        rec["variants"] = list(rec["variantReferences"])   # the schema key wins: the legacy key is not read
    _, rep = run(dk)
    assert {THERAPY_REFS, STUDY_REFS}.isdisjoint(rep.covered)
    unknown = copy.deepcopy(load(RD))
    for rec in unknown["plan"]["recommendedTherapies"]:
        rec["variantReferences"] = ["no-such-variant"]                     # read, but nothing resolves
    _, rep = run(unknown)
    assert THERAPY_REFS not in rep.covered and STUDY_REFS in rep.covered


def test_cli_reports_the_legacy_keys_as_converted(tmp_path, capsys):
    pytest.importorskip("genomde_dk_validator")
    report = tmp_path / "rep.json"
    rc = main(["convert", str(ONCO), str(RD), "-o", str(tmp_path / "out"), "--report", str(report)])
    assert rc == 0
    capsys.readouterr()
    w = {x["path"]: x["message"] for f in json.loads(report.read_text())["files"] for x in f["warnings"]
         if "not declared" in x["message"]}
    for p in ("/case/priorDiagnostic", "/case/priorRd", "/plan/recommendedTherapies/0/variantReferences",
              "/plan/recommendedStudies/0/variantReferences"):
        assert w[p] == "field not declared in the input schema: converted", p
    assert w["/molecular/smallVariants/0/genes/0/system"].endswith(": not converted")   # really ignored


# ---- R68: '(defined in <profile>)' -----------------------------------------------------------------------------
TNM_T = MII + "modul-onko/StructureDefinition/mii-pr-onko-tnm-t-kategorie"
TNM_M = MII + "modul-onko/StructureDefinition/mii-pr-onko-tnm-m-kategorie"
TNM_BASE = MII + "modul-onko/StructureDefinition/mii-pr-onko-tnm-base"   # an intermediate ancestor (made up)


def test_named_profile_reads_defined_in():
    text = f"Constraint failed: tnm-sct-uicc-konsistenz: '...' (defined in {TNM_M}|2027.0.0-ballot.1)"
    assert NAMED_PROFILE.findall(text) == [TNM_M]
    assert NAMED_PROFILE.findall(f"The pattern [...] defined in the profile {TNM_M}|2027 not found") == [TNM_M]


def _with(text, ancestors=None):
    """TNM-Klassifikation.hasMember -> T-Kategorie (tried, its chain unchecked) plus one bundle-pass error at T."""
    b, mb = _tnm(pt_issues=UNCHECKED_PT, noise=False)
    mb.bundle_issues.append(iss(at(b, 2), text))
    mb.anc.update(ancestors or {})
    return validate_bundle(b, mb)


def test_candidate_invariant_defined_in_other_profile_is_candidate():
    out = _with(f"Constraint failed: tnm-sct-uicc-konsistenz: 'Wenn ein SNOMED CT Code ...' (defined in {TNM_M})")
    assert cls_of(out, "tnm-sct-uicc-konsistenz") == "candidate" and out["verdict"] == "INCONCLUSIVE"


@pytest.mark.parametrize("named,ancestors", [
    (TNM_T, None),                                             # the declared profile itself
    (BASE_SD + "Observation", None),                           # the core type (e.g. obs-6)
    (TNM_BASE, {TNM_T: {TNM_T, TNM_BASE, BASE_SD + "Observation"}}),   # an ancestor matchbox reports
])
def test_invariant_defined_in_own_chain_stays_own_content(named, ancestors):
    out = _with(f"Constraint failed: inv-1: 'own rule' (defined in {named})", ancestors)
    assert cls_of(out, "inv-1") == "content" and out["verdict"] == "FAIL"


# ---- R13 (cli handoff): the report names each input's output file -----------------------------------------------
def test_report_records_output_file(tmp_path, capsys):
    from test_fix2_cli import grz, write
    a, b = write(tmp_path / "a/case.json", grz()), write(tmp_path / "b/case.json", grz(localCaseId="other-case"))
    report, out = tmp_path / "rep.json", tmp_path / "out"
    assert main(["convert", str(a), str(b), "-o", str(out), "--report", str(report), "--no-input-check"]) == 0
    files = {f["file"]: f["output"] for f in json.loads(report.read_text())["files"]}
    assert files == {str(a): str(out / "case.bundle.json"), str(b): str(out / "b_case.bundle.json")}
    assert all(json.loads((out / n).read_text())["resourceType"] == "Bundle" for n in ("case.bundle.json", "b_case.bundle.json"))
    assert main(["convert", str(a), str(b), "-o", str(out), "--single-bundle", "all.json", "--report", str(report),
                 "--no-input-check"]) == 0
    assert {f["output"] for f in json.loads(report.read_text())["files"]} == {str(out / "all.json")}
    bad = write(tmp_path / "c/bad.json", {"metaData": {}})
    main(["convert", str(bad), "-o", str(out), "--report", str(report), "--no-input-check"])
    assert json.loads(report.read_text())["files"][0]["output"] == ""
    capsys.readouterr()
