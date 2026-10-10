"""Regression tests of the FML fix stage (findings R25, R26, R46, R52, R53, R54, R62, R69; round 2: test_fix2_fml.py) and of the FML
mirror of the Python fix stage (identity, oncology plan / follow-up / molecular, rare disease, GRZ).

Offline (always run):
  - no production map derives an array position by value equality (R26, R52, R62): positions come from counters;
  - every input of the FML test modules is in the repository, none under the untracked example-data/synthData-v1/,
    and a missing input fails instead of skipping (R46).
With MB2027 (matchbox-2027 base URL; HAPI2027 defaults to http://localhost:8092/fhir):
  - every mutation scenario (in-repo fixtures + a mutation) converts on both paths with zero differences under
    canonical() of scripts/run_corpus.py, and the FML Bundle has no duplicate fullUrl or conditional request.url;
  - scenario-specific checks of the original failure (e.g. R52 no HTTP 500, R69 no HTTP 500, HTEST labels);
  - a GRZ submission with two donors of one pseudonym fails on both paths (Python 'duplicate resource');
  - double ingest into HAPI of the duplicate-item scenarios: one response per request entry, the second POST only 200.
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
from genomde2fhir.io import loads  # noqa: E402
from genomde2fhir.validate import Hapi, Matchbox  # noqa: E402

MB = os.environ.get("MB2027")
HAPI = os.environ.get("HAPI2027", "http://localhost:8092/fhir")
FML = REPO / "mappers" / "fml"
FX = REPO / "genomde2fhir" / "tests" / "fixtures"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_RC = _load("run_corpus", REPO / "scripts" / "run_corpus.py")

# ---- inputs (all tracked in the repository) ------------------------------------------------------------------------
ONC = REPO / "example-data/oncology/OncologySubmission_044AFF6262356F2F8EC60039DC08AE36FBAA011DE29740CBC83E9FA5643E4640.json"
PLAN = FX / "onco_plan/plan_full.json"
FU = FX / "onco_followup/followup_edge_cases.json"
DX = FX / "onco_diagnosis/diagnosis_full.json"
PRIOR = FX / "onco_prior/prior_all_enums.json"
SV = FX / "onco_variants/synthetic_small_variants.json"
BIO = FX / "onco_biomarkers/synthetic_biomarkers.json"
CNV = FX / "onco_cnv_sv/cnv_sv_enums.json"
RD = FX / "rd_plan_followup/rd_plan_followup_all_enums.json"
RDV = FX / "rd_variants/rd-variants-edge-cases.json"
RDX = FX / "rd_diagnosis/rd_further_none_priors.json"
GRZ = REPO / "example-data/grz/grz-paired-onco-01.json"
GRZL = FX / "grz_labdata/grz-labdata-onco-edge.json"
GRZD = FX / "grz_donors/all_relations.json"
ATC = "http://fhir.de/CodeSystem/bfarm/atc"

CONSENT = {"resourceType": "Consent", "id": "c1", "status": "active",
           "scope": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/consentscope", "code": "research"}]},
           "category": [{"coding": [{"system": "http://loinc.org", "code": "57016-8"}]}],
           "patient": {"reference": "Patient/123"}, "dateTime": "2025-02-11",
           "contained": [{"resourceType": "Practitioner", "id": "doctor", "name": [{"family": "Doe"}]},
                         {"resourceType": "Organization", "id": "unused", "name": "X"}],
           "performer": [{"reference": "#doctor"}, {"reference": "#missing"}],
           "policy": [{"uri": "2.16.840.1.113883.3.1937.777.24.2.2079"}],
           "provision": {"type": "deny", "period": {"start": "2025-02-11"}}}


def _dup(lst, k=0):
    lst.append(copy.deepcopy(lst[k]))


def _set(o, **kw):
    o.update(kw)


def _fu_therapy(ref, start, end, reason, resp, code="L01XX35"):
    return {"reference": ref, "therapyStartDate": start, "therapyEndDate": end, "terminationReasonOBDS": reason,
            "substances": [{"code": {"code": code, "system": ATC, "version": "2025"}}], "therapyResponse": resp}


def _fus(d):
    return d["followUp"]["followUpOds"]


# name -> (branch, input, mutation)
SCENARIOS = {
    # identity: case key '<CK>' escaped, '|test' for test submissions, HTEST label, case-scoped donor pseudonym
    "test-submission-onco": ("oncology", ONC, lambda d: (_set(d["metaData"]["submission"], type="test"),
                                                          _set(d["metaData"], localCaseId="C1"))),
    "escaped-local-case-id": ("oncology", ONC, lambda d: (_set(d["metaData"], localCaseId="a|b\\c"),
                                                           _set(d["metaData"]["submission"], type="initial"))),
    "tanc-fallback": ("oncology", ONC, lambda d: d["metaData"].pop("localCaseId", None)),
    "test-submission-rd": ("rare-disease", RD, lambda d: _set(d["metaData"]["submission"], type="test")),
    "test-submission-grz": ("grz", GRZ, lambda d: _set(d["submission"], submissionType="test")),
    "grz-escaped-pseudonym": ("grz", GRZD, lambda d: _set(d["donors"][1], donorPseudonym="rel|1")),
    "grz-addition-own-study": ("grz", GRZ, lambda d: _set(d["submission"], submissionType="addition", tanG="B" * 64,
                                                            submissionDate="2026-01-01")),
    "rc-contained": ("oncology", ONC, lambda d: _set(d["metaData"], researchConsents=[
        {"presentationDate": "2025-02-11", "scope": copy.deepcopy(CONSENT)}])),
    "rc-no-policy": ("oncology", ONC, lambda d: _set(d["metaData"], researchConsents=[
        {"scope": {k: v for k, v in CONSENT.items() if k != "policy"}}])),
    # R26: identical array items are separate resources (Python keeps both, keyed by position)
    "rc-dup": ("oncology", ONC, lambda d: _set(d["metaData"], researchConsents=[{"scope": copy.deepcopy(CONSENT)}] * 2)),
    "R26-dup-small-variant": ("oncology", SV, lambda d: _dup(d["molecular"]["smallVariants"])),
    "R26-dup-cnv": ("oncology", CNV, lambda d: _dup(d["molecular"]["copyNumberVariants"])),
    "R26-dup-sv": ("oncology", CNV, lambda d: _dup(d["molecular"]["structuralVariants"])),
    "R26-dup-biomarker": ("oncology", BIO, lambda d: _dup(d["molecular"]["complexBiomarkers"])),
    "R26-dup-expression": ("oncology", BIO, lambda d: _dup(d["molecular"]["expressionVariants"])),
    "R26-dup-sbs": ("oncology", BIO, lambda d: _dup(d["molecular"]["sbsSignatures"])),
    "R26-dup-sbs-name": ("oncology", BIO, lambda d: d["molecular"]["sbsSignatures"][0]["name"].append(
        d["molecular"]["sbsSignatures"][0]["name"][0])),
    "R26-dup-hpo": ("oncology", DX, lambda d: _dup(d["case"]["diagnosisOd"]["hpoTerms"])),
    "R26-dup-additional-dx": ("oncology", DX, lambda d: _dup(d["case"]["diagnosisOd"]["additionalDiagnoses"])),
    "R26-dup-germline": ("oncology", DX, lambda d: _dup(d["case"]["diagnosisOd"]["germlineDiagnoses"])),
    "R26-dup-prior-procedure": ("oncology", ONC, lambda d: _dup(d["case"]["priorProcedures"])),
    "R26-dup-prior-substance": ("oncology", ONC, lambda d: _dup(d["case"]["priorProcedures"][0]["substances"])),
    "R26-dup-prior-diagnostic": ("oncology", PRIOR, lambda d: _dup(d["case"]["priorDiagnostics"])),
    "R26-dup-therapy": ("oncology", PLAN, lambda d: _dup(d["plan"]["recommendedSystemicTherapies"], 1)),
    "R26-dup-combination": ("oncology", PLAN, lambda d: _dup(d["plan"]["recommendedSystemicTherapies"], 0)),
    "R26-dup-combination-substance": ("oncology", PLAN, lambda d: _dup(d["plan"]["recommendedSystemicTherapies"][0]["substances"])),
    "R26-dup-study": ("oncology", PLAN, lambda d: _dup(d["plan"]["recommendedStudies"])),
    "R26-dup-preventive": ("oncology", PLAN, lambda d: _dup(d["plan"]["preventiveMeasures"])),
    "R26-dup-intervention": ("oncology", ONC, lambda d: _set(d["plan"]["carePlanOd"], suitableInterventions=[
        {"type": {"name": "OP"}}, {"type": {"name": "OP"}}])),
    "R26-dup-fu-diagnosis": ("oncology", FU, lambda d: _dup(_fus(d)[0]["additionalDiagnoses"])),
    "R26-rd-dup-variant": ("rare-disease", RDV, lambda d: _dup(d["molecular"]["smallVariants"])),
    "R26-rd-dup-phenotype": ("rare-disease", RDX, lambda d: _dup(d["case"]["diagnosisRd"]["phenotypes"])),
    "R26-rd-dup-therapy": ("rare-disease", RD, lambda d: _dup(d["plan"]["recommendedTherapies"])),
    "R26-rd-dup-study": ("rare-disease", RD, lambda d: _dup(d["plan"]["recommendedStudies"])),
    "R26-rd-dup-followup": ("rare-disease", RD, lambda d: _dup(d["followUp"]["followUpRds"])),
    "R26-grz-dup-labdata": ("grz", GRZL, lambda d: _dup(d["donors"][0]["labData"])),
    "R26-grz-dup-tumor-cell-count": ("grz", GRZL, lambda d: [_dup(ld["tumorCellCount"]) for ld in d["donors"][0]["labData"]
                                                             if ld.get("tumorCellCount")][:1]),
    "R26-grz-dup-caller": ("grz", GRZL, lambda d: [_dup(ld["sequenceData"]["callerUsed"]) for ld in d["donors"][0]["labData"]
                                                   if (ld.get("sequenceData") or {}).get("callerUsed")][:1]),
    # R52: a repeated TNM item no longer fails the transform
    "R52-dup-tnm": ("oncology", ONC, lambda d: _dup(d["case"]["diagnosisOd"]["tnmClassifications"])),
    # R53: empty optional strings are not copied
    "R53-empty-tanc": ("oncology", ONC, lambda d: _set(d["metaData"], tanC="")),
    "R53-empty-mv-consent-version": ("oncology", ONC, lambda d: _set(d["metaData"]["mvConsent"], version="")),
    "R53-empty-labdataname": ("grz", GRZL, lambda d: _set(d["donors"][0]["labData"][0], labDataName="")),
    # R25 / R37 / R62: the latest follow-up (followUpDate order) wins; identical follow-ups emit once
    "R25-preventive-updated": ("oncology", FU, lambda d: _fus(d)[1].setdefault("preventiveMeasures", []).append(
        {"reference": "pm-colon-1", "preventiveMeasureDate": "2025-10-01", "preventiveMeasureResult": "noFindings"})),
    "R25-preventive-earlier-date-later-array": ("oncology", FU, lambda d: _fus(d).append(
        {"followUpDate": "2025-01-01", "preventiveMeasures": [
            {"reference": "pm-colon-1", "preventiveMeasureDate": "2025-10-01", "preventiveMeasureResult": "malignoma"}]})),
    "R37-reversed-followups": ("oncology", FU, lambda d: _fus(d).reverse()),
    "R37-undated-followup": ("oncology", FU, lambda d: _fus(d).append(
        {k: v for k, v in copy.deepcopy(_fus(d)[2]).items() if k != "followUpDate"})),
    "R62-identical-followup": ("oncology", FU, lambda d: _dup(_fus(d), 1)),
    "R62-identical-followup-plan": ("oncology", PLAN, lambda d: _dup(_fus(d))),
    # R69: an integral priority written as a decimal does not fail the transform and is kept (round 2)
    "R69-priority-decimal": ("oncology", PLAN, lambda d: (_set(d["plan"]["recommendedSystemicTherapies"][0], priority=1.0),
                                                          _set(d["plan"]["recommendedStudies"][0], priority=4.0))),
    # mirrored Python fixes: plan and follow-up
    "R21-phenotype-twice": ("oncology", FU, lambda d: _set(_fus(d)[0], phenotypes=[
        {"code": "HP:0001250", "change": "improved"}, {"code": "HP:0001250", "change": "degraded"}])),
    "R16-combination-basedon": ("oncology", PLAN, lambda d: _fus(d)[0]["therapies"].append(
        {"reference": "th-inlabel", "therapyStartDate": "2025-11-11", "substances": [
            {"code": {"code": "L01EC02", "system": ATC}}, {"code": {"code": "L01EE01", "system": ATC}},
            {"code": {"code": "L01XX99", "system": ATC}}]})),
    "R24-therapy-twice-in-followup": ("oncology", PLAN, lambda d: _set(_fus(d)[0], therapies=[
        _fu_therapy("th-inlabel", "2025-11-11", "2026-02-01", "A", "PD"),
        _fu_therapy("th-inlabel", "2025-11-11", "2026-03-01", "E", "CR")])),
    "R30-diagnosis-systems": ("oncology", FU, lambda d: _set(_fus(d)[0], additionalDiagnoses=[
        {"system": "https://www.alpha-id.de", "code": "I97525", "version": "2025", "date": "2025-01-01"},
        {"system": "https://www.orpha.net", "code": "ORPHA:558", "version": "4.7", "date": "2025-01-02"},
        {"code": "C187", "date": "2025-01-03"}, {"system": "http://snomed.info/sct", "code": "363406005", "date": "2025-01-04"}])),
    "F12-names-across-reports": ("oncology", FU, lambda d: (
        _fus(d)[1]["therapies"][1]["substances"].append({"name": "Geheimsubstanz"}),
        _fus(d)[2]["therapies"][0]["substances"].append({"name": "Zweite"}))),
    "F12-name-now-coded": ("oncology", FU, lambda d: _fus(d)[2]["therapies"][0]["substances"].append(
        {"name": "Experimentelle Substanz XY", "code": {"code": "L01XX99"}})),
    "F20-placeholder-name": ("oncology", PLAN, lambda d: _set(d["plan"]["recommendedStudies"][1], name="N/A")),
    "F20-placeholder-only": ("oncology", PLAN, lambda d: _set(d["plan"]["recommendedStudies"][1], id="", name="unknown")),
    "R51-repeated-study": ("oncology", PLAN, lambda d: _set(d["plan"]["recommendedStudies"][5], name="A DIFFERENT TRIAL ARM",
        substances=[{"code": {"code": "L01FC01", "display": "Daratumumab", "system": ATC}}])),
    "C3-cited-twice": ("oncology", ONC, lambda d: _set(d["plan"]["recommendedSystemicTherapies"][0],
                                                       variants=d["plan"]["recommendedSystemicTherapies"][0].get("variants", []) * 2)),
    # mirrored Python fixes: molecular and spine
    "R49-uicc-display": ("oncology", DX, lambda d: _set(d["case"]["diagnosisOd"], tnmClassifications=[
        {"code": "T2", "system": "https://www.uicc.org/resources/tnm", "version": "8th ed."},
        {"code": "N1mi", "system": "https://www.uicc.org/resources/tnm", "version": "UICC 8"},
        {"code": "NX", "system": "https://www.uicc.org/resources/tnm", "version": "8"}])),
    "R23-editions": ("oncology", DX, lambda d: _set(d["case"]["diagnosisOd"], tnmClassifications=[
        {"code": "T2", "system": "https://www.uicc.org/resources/tnm", "version": "2025-03-01"},
        {"code": "N0", "system": "https://www.uicc.org/resources/tnm", "version": "10. Auflage"},
        {"code": "M0", "system": "https://www.uicc.org/resources/tnm", "version": "TNM8"}])),
    "F01-tumor-spread": ("oncology", DX, lambda d: _set(d["case"]["diagnosisOd"], additionalClassification=[
        {"key": "tumor-free", "system": "dnpm-dip/mtb/diagnosis/kds-tumor-spread"},
        {"key": "metastasized", "system": "dnpm-dip/mtb/diagnosis/kds-tumor-spread"},
        {"key": "weird", "system": "dnpm-dip/mtb/diagnosis/kds-tumor-spread"}, {"key": "x", "system": "other"}])),
    "F01-tumor-spread-no-date": ("oncology", DX, lambda d: (d["case"]["diagnosisOd"]["mainDiagnosis"].pop("date", None),
        _set(d["case"]["diagnosisOd"], additionalClassification=[{"key": "local", "system": "dnpm-dip/mtb/diagnosis/kds-tumor-spread"}]))),
    "F08-topography-T": ("oncology", DX, lambda d: _set(d["case"]["diagnosisOd"], topography={
        "code": "T", "display": "Topographie", "system": "urn:oid:2.16.840.1.113883.6.43.1", "version": "Zweite Revision"})),
    "F19-legacy-prior": ("oncology", PRIOR, lambda d: d["case"].__setitem__("priorDiagnostic", d["case"].pop("priorDiagnostics")[0])),
    "R55-unversioned-refseq": ("oncology", SV, lambda d: (
        _set(d["molecular"]["smallVariants"][0], transcriptId={"code": "NM_000546"}, dnaChange="c.524G>A"),
        _set(d["molecular"]["smallVariants"][1], transcriptId={"code": "NM_000546", "version": "6"}, dnaChange="c.524G>A"))),
    "R15-biomarker-reports": ("oncology", BIO, lambda d: None),
    "R15-biomarkers-only": ("oncology", BIO, lambda d: _set(d, molecular={"complexBiomarkers": [
        {"identifier": "a", "tmb": 3.1}, {"identifier": "b", "tmb": 7}]})),
    # mirrored Python fixes: rare disease and GRZ
    "F15-comphet": ("rare-disease", RDV, lambda d: [_set(v, zygosity="compHet") for v in d["molecular"]["smallVariants"]]),
    "R56-dimdi": ("rare-disease", RDX, lambda d: _set(d["case"]["diagnosisRd"], diagnoses=[
        {"system": "http://fhir.de/CodeSystem/dimdi/icd-10-gm", "code": "C179", "version": "2025"},
        {"system": "http://fhir.de/CodeSystem/dimdi/alpha-id", "code": "I12345", "version": "2025"}])),
    "rd-followup-same-date": ("rare-disease", RD, lambda d: d["followUp"]["followUpRds"].append(
        dict(copy.deepcopy(d["followUp"]["followUpRds"][0]), vitalStatus="living"))),
    "R29-icdo3": ("grz", GRZL, lambda d: _set(d["donors"][0]["labData"][0], tissueTypeId="C341",
                                               tissueOntology={"name": "ICD-O-3", "version": "Zweite Revision"})),
    "R29-icdo3-other-edition": ("grz", GRZL, lambda d: _set(d["donors"][0]["labData"][0], tissueTypeId="c34",
                                                             tissueOntology={"name": "ICD-O-3", "version": "2024"})),
}
INGEST = ["R26-dup-small-variant", "R26-dup-therapy", "R62-identical-followup", "R25-preventive-updated",
          "R26-grz-dup-labdata", "R26-rd-dup-variant"]


def scenario(name):
    branch, path, fn = SCENARIOS[name]
    dk = loads(Path(path).read_text(encoding="utf-8"))
    fn(dk)
    return branch, dk


# ---- offline guards -------------------------------------------------------------------------------------------------
def test_no_value_equality_positions_in_production_maps():
    """R26 / R52 / R62: an index found by value equality gives identical items one key (silent merge in HAPI, or an
    HTTP 500 for TNM); every production map uses counters instead."""
    for m in sorted(FML.glob("*.map")):
        text = "\n".join(line for line in m.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("//"))
        assert not re.search(r"select\(iif\(\$this = %", text), m.name
        assert not re.search(r"\.where\([^()]*\)\.(first|last)\(\) = %", text), m.name


def test_fml_test_inputs_are_in_the_repository():
    """R46: the FML test modules read only files of the checkout (no untracked synthData-v1 copies) and fail instead
    of skipping when one is missing."""
    for t in sorted((REPO / "genomde2fhir" / "tests").glob("test_fml_*.py")):
        text = t.read_text(encoding="utf-8")
        assert "synthData-v1" not in text, t.name
        assert not re.search(r"pytest\.skip\([^)]*not in this checkout", text), t.name
        for path in re.findall(r"\"((?:example-data|examples|genomde2fhir/tests/fixtures)/[^\"]+\.json)\"", text):
            assert (REPO / path).is_file(), f"{t.name}: {path}"


def test_scenario_inputs_exist():
    for name, (_, path, _) in SCENARIOS.items():
        assert Path(path).is_file(), (name, path)


# ---- matchbox ---------------------------------------------------------------------------------------------------------
needs_mb = pytest.mark.skipif(not MB, reason="MB2027 not set (matchbox-2027 base URL)")


@pytest.fixture(scope="module")
def mb():
    build = _load("build_mvgs", REPO / "scripts" / "build_mvgs.py")
    assert build.push_maps(MB) == 0, "pushing the production maps failed"
    return Matchbox(MB)


def both(mb, name):
    branch, dk = scenario(name)
    py, rep = convert(dk, name, check_input=False)
    st, fml = mb.transform(dk, _RC.MAPS[branch])
    return py, rep, st, fml


def resources(bundle, rtype=None, profile=None):
    out = [e["resource"] for e in bundle.get("entry", [])]
    if rtype:
        out = [r for r in out if r["resourceType"] == rtype]
    if profile:
        out = [r for r in out if any(p.endswith(profile) for p in r.get("meta", {}).get("profile", []))]
    return out


@needs_mb
@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario_parity(mb, name):
    py, rep, st, fml = both(mb, name)
    assert py is not None, (rep.status, rep.error)
    assert st < 300 and fml.get("resourceType") == "Bundle", (st, json.dumps(fml)[:600])
    a, b = _RC.canonical(py), _RC.canonical(fml)
    assert a == b, (sorted((a - b).elements())[:3], sorted((b - a).elements())[:3])
    for what in ("fullUrl", "request"):
        vals = collections.Counter(e[what] if what == "fullUrl" else e[what]["url"] for e in fml["entry"])
        assert not [v for v, n in vals.items() if n > 1], f"duplicate {what}"


@needs_mb
def test_r52_duplicate_tnm_item_is_two_categories(mb):
    py, _, st, fml = both(mb, "R52-dup-tnm")
    assert st == 200
    grouping = resources(fml, profile="mii-pr-onko-tnm-klassifikation")[0]
    assert len(grouping["hasMember"]) == len(resources(py, profile="mii-pr-onko-tnm-klassifikation")[0]["hasMember"])


@needs_mb
def test_r69_decimal_priority_is_kept_not_http_500(mb):
    py, _, st, fml = both(mb, "R69-priority-decimal")
    assert st == 200

    def prio(b):
        return [x["valuePositiveInt"] for r in resources(b) for x in r.get("extension", [])
                if x["url"].endswith("mii-ex-mtb-empfehlung-prioritaet")]
    assert sorted(prio(fml)) == sorted(prio(py))
    # therapy 0 (a combination: RequestGroup + 2 members) priority 1.0 and study 0 priority 4.0 are kept as integers
    assert all(isinstance(v, int) for v in prio(fml)) and prio(fml).count(4) >= prio(py).count(4) >= 1


@needs_mb
def test_r53_empty_strings_not_copied(mb):
    _, _, _, fml = both(mb, "R53-empty-tanc")
    pat = resources(fml, "Patient")[0]
    assert not [i for i in pat["identifier"] if i["system"].endswith("tan-c")]
    _, _, _, fml = both(mb, "R53-empty-mv-consent-version")
    assert not [r for r in resources(fml, profile="mvgs-consent") if "policyRule" in r]
    py, _, _, fml = both(mb, "R53-empty-labdataname")
    ids = sorted(i["value"] for r in resources(fml, "Specimen") for i in r["identifier"] if i["system"].endswith("grz-lab-data-name"))
    assert ids == sorted(i["value"] for r in resources(py, "Specimen") for i in r["identifier"]
                         if i["system"].endswith("grz-lab-data-name"))
    assert any(v.endswith("|#0") for v in ids), ids


@needs_mb
def test_r25_latest_preventive_result_wins(mb):
    # pm-colon-1 on 2025-10-01: 'unclear' in the follow-up of 2025-12-01, re-reported by an earlier-dated follow-up
    # (2025-09-01 in the array before it, 2025-01-01 after it): the latest followUpDate wins, one Observation
    for name in ("R25-preventive-updated", "R25-preventive-earlier-date-later-array"):
        py, _, _, fml = both(mb, name)
        for b in (py, fml):
            res = [r["valueCodeableConcept"]["coding"][0]["code"] for r in resources(b, "Observation")
                   if r.get("code", {}).get("coding", [{}])[0].get("code") == "preventive-measure-result"
                   and r.get("effectiveDateTime") == "2025-10-01"]
            assert res == ["unclear"], (name, res)


@needs_mb
def test_r62_identical_followups_emit_once(mb):
    py, _, _, fml = both(mb, "R62-identical-followup")
    assert len(resources(fml, "Procedure")) == len(resources(py, "Procedure"))


@needs_mb
def test_identity_test_submission(mb):
    py, _, _, fml = both(mb, "test-submission-onco")
    htest = {"system": "http://terminology.hl7.org/CodeSystem/v3-ActReason", "code": "HTEST", "display": "test health data"}
    assert all(htest in r.get("meta", {}).get("security", []) for r in resources(fml))
    pat = resources(fml, "Patient")[0]
    assert [i["value"] for i in pat["identifier"] if i["system"].endswith("local-case-id")] == ["260840108|C1|test"]
    mfid = [i["value"] for r in resources(fml) for i in r.get("identifier", []) if i["system"].endswith("molecular-finding-id")]
    assert mfid and all(v.startswith("260840108|C1|test|") for v in mfid)
    _, _, _, fml = both(mb, "escaped-local-case-id")
    pat = resources(fml, "Patient")[0]
    assert [i["value"] for i in pat["identifier"] if i["system"].endswith("local-case-id")] == ["260840108|a\\|b\\\\c"]
    assert not [r for r in resources(fml) if "security" in r.get("meta", {})]


@needs_mb
def test_identity_grz_case_scoped_donor_and_study_per_submission(mb):
    _, _, _, fml = both(mb, "test-submission-grz")
    donor = [i["value"] for r in resources(fml, "Patient") for i in r["identifier"] if i["system"].endswith("donor-pseudonym")]
    assert donor and all(v.count("|") >= 3 and "|test|" in v for v in donor), donor
    keys = set()
    for name in ("grz-addition-own-study", "test-submission-grz"):
        _, _, _, fml = both(mb, name)
        study = [r for r in resources(fml, "Procedure") if r["meta"]["profile"][0].endswith("genomic-study")][0]
        keys.add(next(i["value"] for i in study["identifier"] if i["system"].endswith("resource-key")))
    assert len(keys) == 2


@needs_mb
def test_research_consent_contained_and_policy(mb):
    _, _, _, fml = both(mb, "rc-contained")
    con = resources(fml, profile="mii-pr-consent-einwilligung")[0]
    assert [c["id"] for c in con["contained"]] == ["doctor"]
    assert {"reference": "#doctor"} in con["performer"]
    assert {"display": "#missing (missing contained resource)"} in con["performer"]
    _, _, _, fml = both(mb, "rc-no-policy")
    con = [r for r in resources(fml, "Consent") if r.get("scope", {}).get("coding", [{}])[0].get("code") == "research"][0]
    assert "meta" not in con or not con["meta"].get("profile")
    assert con["policyRule"]["extension"][0]["valueCode"] == "unknown"


@needs_mb
def test_grz_duplicate_donor_pseudonym_fails_on_both_paths(mb):
    dk = loads(GRZD.read_text(encoding="utf-8"))
    dk["donors"].append(dict(copy.deepcopy(dk["donors"][1]), gender="other"))
    py, rep = convert(dk, "dup-donor", check_input=False)
    st, fml = mb.transform(dk, _RC.MAPS["grz"])
    assert py is None and rep.status == "error"
    assert st >= 300 and fml.get("resourceType") != "Bundle"
    assert "Check condition failed" in json.dumps(fml)


@needs_mb
@pytest.mark.parametrize("name", INGEST)
def test_duplicate_items_ingest_without_silent_merge(mb, name):
    """R26 / R62: HAPI answers one response per request entry (no merged duplicate), the second POST creates nothing."""
    _, _, st, fml = both(mb, name)
    assert st == 200
    hapi = Hapi(HAPI)
    for run in (1, 2):
        ok, resp = hapi.transaction(fml)
        assert ok, json.dumps(resp)[:300]
        statuses = [str((e.get("response") or {}).get("status", "")) for e in resp.get("entry", [])]
        assert len(statuses) == len(fml["entry"])
        if run == 2:
            assert all(s.startswith("200") for s in statuses), collections.Counter(statuses)
