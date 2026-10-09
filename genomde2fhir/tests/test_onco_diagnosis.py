"""onco.diagnosis / onco.tnm / onco.ecog: KDK case.diagnosisOd -> primary tumour, satellites, TNM, ECOG."""
import copy
import csv
from pathlib import Path

import pytest

from conftest import REPO, load, resources

from genomde2fhir.systems import ICD10GM, ICDO3, ORPHA, ALPHA_ID, SNOMED, UICC, LOINC, HPO

FIX = Path(__file__).parent / "fixtures" / "onco_diagnosis"
P_PRIMARY = "mii-pr-mtb-diagnose-primaertumor"
P_TNM = "mii-pr-onko-tnm-"
CORPUS = {
    "dnpm": "example-data/synthData-v1/dnpm/OncologySubmission_044AFF6262356F2F8EC60039DC08AE36FBAA011DE29740CBC83E9FA5643E4640.json",
    "nct_sct_tnm": "example-data/synthData-v1/nct/case_022.json",
    "ukdd": "example-data/synthData-v1/ukdd/synth_json_10.json",
    "onc_wgs_lr": "example-data/oncology/OncologySubmission_58FBFB8CE6303B9E38E5F54E7E6536872CDBA2D8C0CDE99CAC7EC8F204DDCF06.json",
}


def by_profile(bundle, frag):
    return resources(bundle, profile=frag)


def one(bundle, frag):
    rs = by_profile(bundle, frag)
    assert len(rs) == 1, [r["id"] for r in rs]
    return rs[0]


def dx_ecog(bundle):
    """ECOG observations of the diagnosis block (follow-up ECOGs carry effectiveDateTime)."""
    return [r for r in by_profile(bundle, "allgemeiner-leistungszustand-ecog") if "effectiveDateTime" not in r]


def codes(cc_):
    return {(c.get("system"), c.get("code")) for c in (cc_ or {}).get("coding", [])}


def ref_of(r):
    return {"reference": f"urn:uuid:{r['id']}"}


# ---- corpus -----------------------------------------------------------------------------------------------------------
def test_corpus_dnpm_primary_and_satellites(convert_dk):
    b, rep = convert_dk(load(REPO / CORPUS["dnpm"]))
    cond = one(b, P_PRIMARY)
    assert (ICD10GM, "C78.0") in codes(cond["code"])
    assert cond["code"]["coding"][0]["version"] == "2026"
    assert (SNOMED, "55342001") in codes(cond["category"][0])
    assert cond["recordedDate"] == "2023-02-01"
    asserted = [e for e in cond["extension"] if e["url"].endswith("condition-assertedDate")]
    assert asserted[0]["valueDateTime"] == "2023-02-01"
    morph = [e for e in cond["extension"] if e["url"].endswith("morphology-behavior-icdo3")][0]
    assert morph["valueCodeableConcept"]["coding"][0] == {"system": ICDO3, "code": "8253/2", "version": "2019",
                                                         "display": "Muzinöses Adenocarcinoma in situ [C34.-]"}
    # topography 'T' is no ICD-O-3 code -> Condition.note, all sub-fields preserved, no bodySite
    assert "bodySite" not in cond
    assert cond["note"] == [{"text": "Topography (ICD-O-3 T, as delivered): T Topographie"}]
    assert {f"case.diagnosisOd.topography.{k}" for k in ("code", "system", "version", "display")} <= rep.preserved
    # UICC strings T3/N3/M0 (system 'UICC', 8th ed.) -> three category observations + grouping
    cats = [r for r in by_profile(b, P_TNM) if "klassifikation" not in r["meta"]["profile"][0]]
    assert sorted(c["valueCodeableConcept"]["coding"][0]["code"] for c in cats) == ["M0", "N3", "T3"]
    assert all(c["method"]["coding"][0]["code"] == "8" for c in cats)
    group = one(b, "mii-pr-onko-tnm-klassifikation")
    assert (SNOMED, "399390009") in codes(group["code"])          # no c/p prefix delivered
    assert {m["reference"] for m in group["hasMember"]} == {f"urn:uuid:{c['id']}" for c in cats}
    # ECOG 4 -> obds + LOINC answer; focus primary
    ecog, = dx_ecog(b)
    assert codes(ecog["valueCodeableConcept"]) >= {(LOINC, "LA9626-8")}
    assert ecog["focus"] == [ref_of(cond)]
    # grading M; kds-tumor-spread -> weitere Klassifikationen with SNOMED
    grading = one(b, "mii-pr-onko-grading")
    assert grading["valueCodeableConcept"]["coding"][0]["code"] == "M"
    assert "_effectiveDateTime" in grading
    wk = one(b, "weitere-klassifikationen")
    assert wk["code"]["text"] == "dnpm-dip/mtb/diagnosis/kds-tumor-spread"
    assert wk["valueCodeableConcept"] == {"coding": [{"system": SNOMED, "code": "58899004", "display": "No evidence of tumor"}],
                                         "text": "tumor-free"}
    sr = [r for r in resources(b, "ServiceRequest") if (r.get("code") or {}).get("coding", [{}])[0].get("code") == "whole-genom-sequencing"]
    assert len(sr) == 1 and sr[0]["reasonReference"] == [ref_of(cond)]
    assert sr[0]["meta"]["profile"] == ["https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition/anforderung-genetischer-test"]


def test_corpus_nct_snomed_tnm(convert_dk):
    b, rep = convert_dk(load(REPO / CORPUS["nct_sct_tnm"]))
    n = one(b, "mii-pr-onko-tnm-n-kategorie")
    assert n["valueCodeableConcept"]["coding"][0] == {"system": UICC, "code": "N3b", "display": "N3b"}
    sct = n["valueCodeableConcept"]["coding"][1]
    assert sct["system"] == SNOMED and sct["code"] == "1353054002" and "cN3b " in sct["display"]   # tnm-sct-uicc-konsistenz
    assert n["code"]["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] == "c"
    assert (SNOMED, "399534004") in codes(n["code"])
    group = one(b, "mii-pr-onko-tnm-klassifikation")
    assert (SNOMED, "399537006") in codes(group["code"])          # all matched items clinical
    # unmatched (AJCC / unknown SNOMED) items -> weitere Klassifikationen code.text TNM
    wk = [r for r in by_profile(b, "weitere-klassifikationen") if r["code"]["text"] == "TNM"]
    assert wk and all(r["valueCodeableConcept"]["text"] for r in wk)
    assert "case.diagnosisOd.tnmClassifications[].code" in rep.preserved
    # HPO from the jax.org system -> HPO system
    hpo = by_profile(b, "hpo-assessment")
    assert hpo and all(r["code"]["coding"][0]["system"] == HPO for r in hpo)


def test_corpus_ukdd_diagnoses_and_assessment(convert_dk):
    b, rep = convert_dk(load(REPO / CORPUS["ukdd"]))
    diag = by_profile(b, "modul-diagnose/StructureDefinition/Diagnose")
    systems = {c["code"]["coding"][0]["system"] for c in diag}
    assert systems == {ICD10GM, ORPHA, ALPHA_ID}
    assert all(not c["code"]["coding"][0]["code"].startswith("ORPHA") for c in diag)
    germ = [c for c in diag if c.get("category")]
    assert germ and all(c["verificationStatus"]["coding"][0]["code"] in ("confirmed", "unconfirmed") for c in germ)
    ecog, = dx_ecog(b)
    assert ecog["valueCodeableConcept"]["coding"] == [{"system": ecog["valueCodeableConcept"]["coding"][0]["system"], "code": "U",
                                                       "display": "Unbekannt"}]
    ass = [r for r in resources(b, "Observation") if (r.get("code") or {}).get("coding", [{}])[0].get("code") == "genetic-diagnostic-assessment"]
    assert len(ass) == 1 and ass[0]["valueCodeableConcept"]["coding"][0]["system"].endswith("mvgs-cs-genetic-diagnostic-assessment")


def test_corpus_wgs_lr(convert_dk):
    b, _ = convert_dk(load(REPO / CORPUS["onc_wgs_lr"]))
    sr = [r for r in resources(b, "ServiceRequest") if (r.get("code") or {}).get("text") == "Whole genome sequencing, long read"]
    assert len(sr) == 1 and sr[0]["code"]["coding"][0]["code"] == "whole-genom-sequencing"


@pytest.mark.parametrize("histo,topo,morph,site,note_n", [
    ("C02.0", "M8761/0", "8761/0", "C02.0", 0),     # swapped by the sender (UKDD corpus) -> both placed, warned
    ("M8600/3", "M9510/3", "8600/3", None, 1),      # morphology in both fields -> second one as note
    ("C57.1", "C25.0", None, "C25.0", 1),           # topography in both fields -> histology one as note
    ("C57.1", "C57.1", None, "C57.1", 0),           # exact duplicate -> dropped
])
def test_icdo3_wrong_field(convert_dk, histo, topo, morph, site, note_n):
    dk = load(FIX / "diagnosis_drops.json")
    sysv = {"system": ICDO3, "version": "2019"}
    dk["case"]["diagnosisOd"]["histology"] = {"code": histo, **sysv}
    dk["case"]["diagnosisOd"]["topography"] = {"code": topo, **sysv}
    b, rep = convert_dk(dk)
    cond = one(b, P_PRIMARY)
    m = [e["valueCodeableConcept"]["coding"][0]["code"] for e in cond["extension"] if e["url"].endswith("morphology-behavior-icdo3")]
    assert m == ([morph] if morph else [])
    assert [c["coding"][0]["code"] for c in cond.get("bodySite", [])] == ([site] if site else [])
    assert len(cond.get("note", [])) == note_n
    dropped = {p for p, _, _ in rep.dropped}
    for f in ("histology", "topography"):                          # every delivered sub-field has a disposition
        for k in ("code", "system", "version"):
            p = f"case.diagnosisOd.{f}.{k}"
            assert p in rep.covered | rep.preserved | dropped, p


# ---- synthetic fixtures ----------------------------------------------------------------------------------------------
def test_fixture_full(convert_dk):
    b, rep = convert_dk(load(FIX / "diagnosis_full.json"))
    cond = one(b, P_PRIMARY)
    assert cond["code"]["coding"][0] == {"system": ICD10GM, "code": "C34.1", "version": "2026",
                                         "display": "Bösartige Neubildung: Oberlappen (-Bronchus)"}
    assert cond["bodySite"][0]["coding"][0] == {"system": ICDO3, "code": "C34.1", "version": "2019", "display": "Oberlappen der Lunge"}
    morph = [e for e in cond["extension"] if e["url"].endswith("morphology-behavior-icdo3")][0]
    assert morph["valueCodeableConcept"]["coding"][0]["code"] == "8140/3"
    diag = by_profile(b, "modul-diagnose/StructureDefinition/Diagnose")
    add = [c for c in diag if not c.get("category")]
    assert {c["code"]["coding"][0]["code"] for c in add} == {"E11.9", "145", "I100393"}
    assert all(c["recordedDate"] for c in add)
    germ = [c for c in diag if c.get("category")]
    assert len(germ) == 2 and all(c["verificationStatus"]["coding"][0]["code"] == "confirmed" for c in germ)
    assert all("_recordedDate" in c for c in germ)                 # no date in the schema -> data-absent-reason
    # TNM: ypT2 (pathological SNOMED, y prefix), N0 (UICC string, 8th ed.), cM1a (clinical SNOMED), AJCC cM1 unmatched
    t = one(b, "mii-pr-onko-tnm-t-kategorie")
    assert t["modifierExtension"][0]["url"].endswith("mii-ex-onko-tnm-y-praefix")
    assert t["code"]["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] == "p"
    assert t["valueCodeableConcept"]["coding"][1]["version"] == "http://snomed.info/sct/900000000000207008/version/20240401"
    n = one(b, "mii-pr-onko-tnm-n-kategorie")
    assert n["method"]["coding"][0]["code"] == "8" and "extension" not in n["code"]
    m = one(b, "mii-pr-onko-tnm-m-kategorie")
    assert m["valueCodeableConcept"]["coding"][0]["code"] == "M1a" and "version" not in m["valueCodeableConcept"]["coding"][1]
    group = one(b, "mii-pr-onko-tnm-klassifikation")
    assert (SNOMED, "399390009") in codes(group["code"]) and len(group["hasMember"]) == 3
    wk = by_profile(b, "weitere-klassifikationen")
    texts = {r["code"]["text"]: r for r in wk}
    assert texts["TNM"]["valueCodeableConcept"]["text"] in ("cT2 cN0 cM1a", "cM1")
    assert texts["FIGO"]["dataAbsentReason"]["coding"][0]["code"] == "unknown"
    assert "valueCodeableConcept" not in texts["FIGO"]
    ecog, = dx_ecog(b)
    assert [c["code"] for c in ecog["valueCodeableConcept"]["coding"]] == ["U"]
    assert one(b, "mii-pr-onko-grading")["valueCodeableConcept"]["coding"][0]["code"] == "U"
    hpo = one(b, "hpo-assessment")
    assert hpo["code"] == {"coding": [{"system": HPO, "code": "HP:0003002", "version": "2025-05-06", "display": "Breast carcinoma"}],
                           "text": "Mammakarzinom"}
    assert "case.diagnosisOd.diagnosticAssessment" in rep.preserved


def test_fixture_drops(convert_dk):
    b, rep = convert_dk(load(FIX / "diagnosis_drops.json"))
    dropped = {p for p, _, _ in rep.dropped}
    assert {"case.diagnosisOd.ecogPerformanceStatusScore", "case.diagnosisOd.libraryType",
            "case.diagnosisOd.germlineDiagnosisConfirmed"} <= dropped
    assert not dx_ecog(b)
    cond = one(b, P_PRIMARY)
    assert len(cond["note"]) == 2 and not any(e["url"].endswith("morphology-behavior-icdo3") for e in cond["extension"])
    assert "bodySite" not in cond
    # UICC string in a SNOMED field (T2 with text pT2) accepted; unknown M9 -> weitere Klassifikationen
    t = one(b, "mii-pr-onko-tnm-t-kategorie")
    assert t["valueCodeableConcept"]["coding"] == [{"system": UICC, "code": "T2", "display": "T2"}]
    assert t["code"]["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] == "p"
    assert any(r["valueCodeableConcept"]["text"] == "M9" for r in by_profile(b, "weitere-klassifikationen"))
    assert not [r for r in resources(b, "ServiceRequest") if "sequencing" in str(r.get("code"))]


@pytest.mark.parametrize("score,obds,loinc", [("0", "0", "LA9622-7"), ("1", "1", "LA9623-5"), ("2", "2", "LA9624-3"),
                                              ("3", "3", "LA9625-0"), ("4", "4", "LA9626-8"), ("unknown", "U", None),
                                              ("5", None, None), ("notApplicable", None, None)])
def test_ecog_values(convert_dk, score, obds, loinc):
    dk = load(FIX / "diagnosis_drops.json")
    dk["case"]["diagnosisOd"]["ecogPerformanceStatusScore"] = score
    b, rep = convert_dk(dk)
    obs = dx_ecog(b)
    if obds is None:
        assert not obs and ("case.diagnosisOd.ecogPerformanceStatusScore", score) in {(p, v) for p, v, _ in rep.dropped}
        return
    got = {c["system"].split("/")[-1]: c["code"] for c in obs[0]["valueCodeableConcept"]["coding"]}
    assert got["mii-cs-onko-allgemeiner-leistungszustand-ecog"] == obds
    assert got.get("loinc.org") == loinc
    assert (SNOMED, "423740007") in codes(obs[0]["code"])


@pytest.mark.parametrize("value", ["noGeneticDiagnosis", "suspectedGeneticDiagnosis", "furtherGeneticDiagnosticRecommended",
                                   "confirmedGeneticDiagnosis", "partialGeneticDiagnosis"])
def test_diagnostic_assessment_values(convert_dk, value):
    dk = load(FIX / "diagnosis_drops.json")
    dk["case"]["diagnosisOd"]["diagnosticAssessment"] = value
    b, _ = convert_dk(dk)
    obs = [r for r in resources(b, "Observation")
           if (r["code"].get("coding") or [{}])[0].get("code") == "genetic-diagnostic-assessment"]
    assert obs[0]["valueCodeableConcept"]["coding"][0]["code"] == value


@pytest.mark.parametrize("lt,code", [("panel", "gene-panel"), ("wes", "whole-exom-sequencing"),
                                     ("wgs", "whole-genom-sequencing"), ("wgs_lr", "whole-genom-sequencing"), ("none", None)])
def test_library_type(convert_dk, lt, code):
    dk = load(FIX / "diagnosis_drops.json")
    dk["case"]["diagnosisOd"]["libraryType"] = lt
    b, _ = convert_dk(dk)
    got = [r["code"]["coding"][0]["code"] for r in resources(b, "ServiceRequest")
           if r["code"]["coding"][0]["system"].endswith("mii-cs-mtb-genomic-analysis-method-type")]
    assert got == ([code] if code else [])


def test_grading_all_codes(convert_dk):
    for g in ["0", "1", "2", "3", "4", "5", "X", "L", "M", "H", "B", "U", "T"]:
        dk = load(FIX / "diagnosis_drops.json")
        dk["case"]["diagnosisOd"]["grading"] = g
        b, _ = convert_dk(dk)
        assert one(b, "mii-pr-onko-grading")["valueCodeableConcept"]["coding"][0]["code"] == g


def test_profile_set_2026(convert_dk):
    b, _ = convert_dk(load(FIX / "diagnosis_full.json"), profile_set="2026")
    t = one(b, "mii-pr-onko-tnm-t-kategorie")
    assert "modifierExtension" not in t                            # y prefix: no 2026 element
    assert [c["system"] for c in t["valueCodeableConcept"]["coding"]] == [UICC]   # SNOMED coding 2027 only
    one(b, P_PRIMARY)


def test_ids_deterministic(convert_dk):
    dk = load(FIX / "diagnosis_full.json")
    b1, _ = convert_dk(copy.deepcopy(dk))
    b2, _ = convert_dk(dk)
    assert [e["fullUrl"] for e in b1["entry"]] == [e["fullUrl"] for e in b2["entry"]]


# ---- coverage ---------------------------------------------------------------------------------------------------------
def test_mapped_rows_covered(convert_dk):
    rows = list(csv.DictReader((REPO / "mapping" / "mapping_kdk_oncology.csv").open(newline="")))
    block = {r["path"] for r in rows if r["path"].startswith("case.diagnosisOd.")}
    mapped = {r["path"] for r in rows if r["path"].startswith("case.diagnosisOd.") and r["status"] == "MAPPED"}
    seen = set()
    for dk in [load(FIX / "diagnosis_full.json"), load(FIX / "diagnosis_drops.json")] + [load(REPO / f) for f in CORPUS.values()]:
        _, rep = convert_dk(dk)
        seen |= {p for p in rep.covered | rep.preserved if p.startswith("case.diagnosisOd.")}
    assert mapped - seen == set()
    # DRAFT rows of the block (additionalClassification, diagnosticAssessment) are implemented too
    assert block - seen == set()
