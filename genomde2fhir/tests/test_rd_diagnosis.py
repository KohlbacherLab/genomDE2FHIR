"""rd.diagnosis + rd.prior: KDK case.diagnosisRd / case.priorRds[] -> Seltene / MolGen resources."""
from pathlib import Path

import pytest
from conftest import corpus, first_with, load, resources

from genomde2fhir.data_access import mapping_rows

FIX = Path(__file__).parent / "fixtures" / "rd_diagnosis"
SELTENE = "https://www.medizininformatik-initiative.de/fhir/ext/modul-seltene/StructureDefinition/"
MOLGEN = "https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition/"
GENETIC = SELTENE + "mii-pr-seltene-genetic-diagnosis"
CLINICAL = SELTENE + "mii-pr-seltene-clinical-diagnosis"
REQUEST = MOLGEN + "anforderung-genetischer-test"
REPORT = MOLGEN + "molekulargenetischer-befundbericht"
STUDY_DESIGN = "https://genomde.de/fhir/StructureDefinition/mvgs-ex-genomic-study-design"
HPO = "http://human-phenotype-ontology.org"


def _condition(bundle):
    conds = resources(bundle, "Condition")
    assert len(conds) == 1
    return conds[0]


def _by_id(bundle):
    return {e["fullUrl"]: e["resource"] for e in bundle["entry"]}


def _codes(cc):
    return {(c.get("system"), c.get("code")) for c in (cc or {}).get("coding", [])}


def _assessment(value):
    return lambda dk: ((dk.get("case") or {}).get("diagnosisRd") or {}).get("diagnosticAssessment") == value


@pytest.mark.parametrize("assessment,profile,status", [
    ("confirmedGeneticDiagnosis", GENETIC, "confirmed"),
    ("partialGeneticDiagnosis", GENETIC, "differential"),
    ("suspectedGeneticDiagnosis", GENETIC, "provisional"),
    ("noGeneticDiagnosis", CLINICAL, "unconfirmed"),
])
def test_corpus_condition(convert_dk, assessment, profile, status):
    f, dk = first_with("rare-disease", _assessment(assessment))
    bundle, rep = convert_dk(dk, str(f))
    d = dk["case"]["diagnosisRd"]
    cond = _condition(bundle)
    assert cond["meta"]["profile"] == [profile]
    # rd.followup raises an unconfirmed status to confirmed when the latest follow-up says diagnosisEstablished
    fus = (dk.get("followUp") or {}).get("followUpRds") or []
    latest = max(fus, key=lambda x: x.get("followUpDate") or "") if fus else {}
    allowed = {status, "confirmed"} if status == "unconfirmed" and latest.get("diagnosisEstablished") else {status}
    assert {c for _, c in _codes(cond["verificationStatus"])} <= allowed
    systems = {c["system"] for c in cond["code"]["coding"]}
    assert systems == {"http://fhir.de/CodeSystem/bfarm/icd-10-gm", "http://www.orpha.net",
                       "http://fhir.de/CodeSystem/bfarm/alpha-id"}
    orpha = next(c for c in cond["code"]["coding"] if c["system"] == "http://www.orpha.net")
    assert not orpha["code"].startswith("ORPHA:")
    assert all(c.get("version") for c in cond["code"]["coding"])
    assert cond["onsetDateTime"] == d["symptomOnsetDate"]
    assert cond["recordedDate"] == d["molecularBoardDecisionDate"]
    patient = next(e["fullUrl"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    assert cond["subject"] == {"reference": patient}
    idx = _by_id(bundle)
    details = [x["reference"] for ev in cond["evidence"] for x in ev["detail"]]
    assert details and all(r in idx for r in details)        # all evidence resolves inside the bundle
    if profile == GENETIC and isinstance(dk.get("molecular"), dict):
        gen = [ev for ev in cond["evidence"] if ("http://snomed.info/sct", "106221001") in _codes((ev.get("code") or [{}])[0])]
        assert gen and idx[gen[0]["detail"][0]["reference"]]["resourceType"] == "DiagnosticReport"
    # phenotypes -> one HPO assessment each
    hpo = resources(bundle, "Observation", "mii-pr-seltene-hpo-assessment")
    pheno_codes = {p["code"] for p in d["phenotypes"]}
    mine = [o for o in hpo if o["code"]["coding"][0]["code"] in pheno_codes and "effectiveDateTime" not in o]
    assert {o["code"]["coding"][0]["code"] for o in mine} == pheno_codes
    assert all(o["code"]["coding"][0]["system"] == HPO and o["code"]["coding"][0]["version"] for o in mine)
    assert all(o["component"][0]["valueCodeableConcept"]["coding"][0]["code"] == "LA9633-4" for o in mine)
    assert "case.diagnosisRd.diagnoses[].code" in rep.covered


def test_corpus_gmfcs_request_and_prior(convert_dk):
    f, dk = first_with("rare-disease", lambda dk: (dk.get("case") or {}).get("diagnosisRd", {}).get("diagnosisGmfcs")
                       and (dk.get("case") or {}).get("priorRd"))
    bundle, rep = convert_dk(dk, str(f))
    d, pr = dk["case"]["diagnosisRd"], dk["case"]["priorRd"]
    gm = [o for o in resources(bundle, "Observation") if ("http://snomed.info/sct", "707621005") in _codes(o["code"])]
    assert len(gm) == 1
    levels = {"I": "LA16552-4", "II": "LA15151-6", "III": "LA15150-8", "IV": "LA16556-5", "V": "LA16558-1"}
    assert _codes(gm[0]["valueCodeableConcept"]) == {("http://loinc.org", levels[d["diagnosisGmfcs"]])}
    assert "case.diagnosisRd.diagnosisGmfcs" in rep.preserved
    reqs = resources(bundle, "ServiceRequest", REQUEST)
    seq = [r for r in reqs if r["intent"] == "order" and r["status"] == "active"]
    assert len(seq) == 1 and seq[0]["authoredOn"] == d["molecularBoardDecisionDate"]
    design = {"singleGenome": "single", "duoGenome": "duo", "trioGenome": "trio"}[d["diagnosticExtent"]]
    assert seq[0]["extension"][0]["url"] == STUDY_DESIGN and seq[0]["extension"][0]["valueCoding"]["code"] == design
    # legacy singular priorRd -> one prior report + request
    prior_reports = [r for r in resources(bundle, "DiagnosticReport", REPORT) if r.get("basedOn")]
    assert len(prior_reports) == 1
    assert prior_reports[0]["effectiveDateTime"] == pr["diagnosticDate"]
    prior_req = _by_id(bundle)[prior_reports[0]["basedOn"][0]["reference"]]
    assert ("https://genomde.de/fhir/CodeSystem/mvgs-cs-genomic-test-type", pr["genomicTestType"]) in _codes(prior_req["code"])
    assert any(w[0] == "case.priorRds[]" and "legacy" in w[1] for w in rep.warnings)
    eps = resources(bundle, "EpisodeOfCare")
    assert len(eps) == 1 and eps[0]["period"]["start"] == pr["zseContactDate"]


def test_fixture_further_none_priors(convert_dk):
    dk = load(FIX / "rd_further_none_priors.json")
    bundle, rep = convert_dk(dk, "rd_further_none_priors")
    idx = _by_id(bundle)
    cond = _condition(bundle)
    assert cond["meta"]["profile"] == [CLINICAL]
    assert cond["verificationStatus"]["text"] == "Further genetic diagnostics recommended"
    assert any("noMatchingCodeExists" in n["text"] for n in cond["note"])
    assert "case.diagnosisRd.noMatchingCodeExists" in rep.preserved
    # second ICD-10-GM code: slice icd10-gm is 0..1 -> first kept, second dropped
    icd = [c for c in cond["code"]["coding"] if c["system"] == "http://fhir.de/CodeSystem/bfarm/icd-10-gm"]
    assert [c["code"] for c in icd] == ["C17.9"]
    assert ("case.diagnosisRd.diagnoses[].code", "E34.0") in {(p, v) for p, v, _ in rep.dropped}
    # evidence: no molecular-report entry for a clinical diagnosis, one HPO entry per distinct phenotype
    assert len(cond["evidence"]) == 2 and all(ev["code"][0]["coding"][0]["system"] == HPO for ev in cond["evidence"])
    # duplicate phenotype emitted once, text kept
    hpo = resources(bundle, "Observation", "mii-pr-seltene-hpo-assessment")
    first = dk["case"]["diagnosisRd"]["phenotypes"][0]
    same = [o for o in hpo if o["code"]["coding"][0]["code"] == first["code"]]
    assert len(same) == 1 and same[0]["code"]["text"] == first["text"]
    # libraryType none -> doNotPerform; furtherGeneticDiagnosticRecommended -> proposal in the CarePlan
    reqs = resources(bundle, "ServiceRequest", REQUEST)
    seq = [r for r in reqs if r["intent"] == "order" and r["status"] == "active"]
    assert len(seq) == 1 and seq[0]["doNotPerform"] is True
    assert seq[0]["extension"][0]["valueCoding"]["code"] == "trio"
    further = [r for r in reqs if r["intent"] == "proposal"]
    assert len(further) == 1
    fullurl = "urn:uuid:" + further[0]["id"]
    careplans = resources(bundle, "CarePlan", "mii-pr-seltene-therapieplan")
    assert any(a.get("reference", {}).get("reference") == fullurl for cp in careplans for a in cp.get("activity", []))
    # priors: 'none' yields no request/report; others yield request + report
    prior_reports = [r for r in resources(bundle, "DiagnosticReport", REPORT) if r.get("basedOn")]
    assert len(prior_reports) == 4
    concl = {idx[r["basedOn"][0]["reference"]]["code"]["coding"][0]["code"]: r.get("conclusion") for r in prior_reports}
    assert concl["single"] is None                                   # diagnosticResult 'other' -> dropped
    assert concl["array"].startswith("Structural variant")
    by_type = {idx[r["basedOn"][0]["reference"]]["code"]["coding"][0]["code"]: idx[r["basedOn"][0]["reference"]]
               for r in prior_reports}
    assert _codes(by_type["array"]["code"]) >= {
        ("http://hl7.org/fhir/uv/genomics-reporting/CodeSystem/genomic-study-method-type-cs", "microarray")}
    assert _codes(by_type["karyotyping"]["code"]) >= {
        ("http://hl7.org/fhir/uv/genomics-reporting/CodeSystem/genomic-study-method-type-cs", "karyotyping")}
    assert len(by_type["single"]["code"]["coding"]) == 1                 # single-gene: local code only
    assert by_type["single"]["extension"][0]["valueCoding"]["code"] == "duo"
    assert by_type["array"]["extension"][0]["valueCoding"]["code"] == "trio"
    dropped = {(p, v) for p, v, _ in rep.dropped}
    assert ("case.priorRds[].genomicTestType", "none") in dropped
    assert ("case.priorRds[].diagnosticResult", "other") in dropped
    # hospitalisation bands: 'unknown' -> dataAbsentReason, bands -> local codes
    hosp = [o for o in resources(bundle, "Observation")
            if o["code"]["coding"][0]["system"].startswith("https://genomde.de/fhir/CodeSystem/mvgs-cs-hospitalization")]
    assert len(hosp) == 10
    dar = [o for o in hosp if "dataAbsentReason" in o]
    assert len(dar) == 2 and all("valueCodeableConcept" not in o for o in dar)
    vals = {(o["code"]["coding"][0]["code"], o["valueCodeableConcept"]["coding"][0]["code"]) for o in hosp if "valueCodeableConcept" in o}
    assert ("hospitalization-periods", "moreThanFifteen") in vals and ("hospitalization-duration", "moreThanFifty") in vals
    # ZSE: earliest date, one episode, warned
    eps = resources(bundle, "EpisodeOfCare")
    assert len(eps) == 1 and eps[0]["period"]["start"] == "2023-09"
    assert not [w for w in rep.warnings if w[0] in ("(reference)", "(structure)")]


def test_fixture_confirmed_without_molecular(convert_dk):
    dk = load(FIX / "rd_confirmed_no_molecular.json")
    bundle, rep = convert_dk(dk, "rd_confirmed_no_molecular")
    cond = _condition(bundle)
    assert cond["meta"]["profile"] == [GENETIC]
    # no molecular block -> no genetic-evidence entry; one HPO-coded entry per phenotype satisfies evidence 1..*
    phen = {p["code"] for p in dk["case"]["diagnosisRd"]["phenotypes"]}
    assert len(cond["evidence"]) == len(phen)
    assert {ev["code"][0]["coding"][0]["code"] for ev in cond["evidence"]} == phen
    assert all(ev["code"][0]["coding"][0]["system"] == HPO for ev in cond["evidence"])
    idx0 = _by_id(bundle)
    for ev in cond["evidence"]:
        target = idx0[ev["detail"][0]["reference"]]
        assert target["code"]["coding"][0]["code"] == ev["code"][0]["coding"][0]["code"]
    assert "note" not in cond
    assert "case.diagnosisRd.noMatchingCodeExists" in rep.covered
    seq = [r for r in resources(bundle, "ServiceRequest", REQUEST) if r["status"] == "active"]
    assert seq[0]["code"]["text"] == "Whole genome sequencing (long read)"
    assert seq[0]["extension"][0]["valueCoding"]["code"] == "duo"
    gm = [o for o in resources(bundle, "Observation") if ("http://snomed.info/sct", "707621005") in _codes(o["code"])]
    assert _codes(gm[0]["valueCodeableConcept"]) == {("http://loinc.org", "LA16552-4")}
    idx = _by_id(bundle)
    types = {}
    for r in resources(bundle, "DiagnosticReport", REPORT):
        req = idx[r["basedOn"][0]["reference"]]
        types[req["code"]["coding"][0]["code"]] = req
    assert set(types) == {"genomeLongRead", "exome", "panel", "genomeShortRead"}
    mtb = "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/CodeSystem/mii-cs-mtb-genomic-analysis-method-type"
    assert (mtb, "whole-genom-sequencing") in _codes(types["genomeLongRead"]["code"])
    assert (mtb, "whole-exom-sequencing") in _codes(types["exome"]["code"])
    assert (mtb, "gene-panel") in _codes(types["panel"]["code"])
    assert not [w for w in rep.warnings if w[0] in ("(reference)", "(structure)")]


@pytest.mark.parametrize("profile_set", ["2026", "2027"])
def test_profile_sets_no_crash(convert_dk, profile_set):
    files = [FIX / "rd_further_none_priors.json"] + corpus("rare-disease")[:2]
    for f in files:
        bundle, _ = convert_dk(load(f), str(f), profile_set=profile_set)
        assert len(resources(bundle, "Condition")) == 1


def test_coverage_all_rows(convert_dk):
    rows = [p for p in mapping_rows("rare-disease") if p.startswith(("case.diagnosisRd.", "case.priorRds[]."))]
    handled = set()
    inputs = [load(f) for f in sorted(FIX.glob("*.json"))]
    for want in ("confirmedGeneticDiagnosis", "noGeneticDiagnosis"):
        inputs.append(first_with("rare-disease", _assessment(want))[1])
    for dk in inputs:
        _, rep = convert_dk(dk)
        handled |= rep.covered | rep.preserved | {p for p, _, _ in rep.dropped}
    missing = [p for p in rows if p not in handled]
    assert not missing, missing
