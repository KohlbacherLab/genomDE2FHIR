#!/usr/bin/env python3
"""Fill research-grounded OMOP targets for the rows the spine left TODO.

Sources: knowledge/omop/omop-oncology-genomics.md, omop-rare-disease.md,
knowledge/research/fhir-to-omop-tooling.md. Honest status:
  MAPPED = clean standard-OMOP home; DRAFT = mappable but lossy / immature ext /
  unverified concept / local-concept-only; NOMAP = no OMOP home (observational model).
"""
import csv, collections
from pathlib import Path
MAP = Path(__file__).resolve().parent.parent / "mapping"
R = "[[knowledge/omop]] research 2026-06-30"

ONC = [
 # oncology clinical attributes
 ("case.diagnosisOd.histology", "condition_occurrence", "condition_concept_id (precoordinated)", "ICD-O-3 histology+topography -> one SNOMED/ICD-O-3 concept", "or Cancer-Modifier measurement", "DRAFT"),
 ("case.diagnosisOd.topography", "condition_occurrence", "condition_concept_id (precoordinated) / bodySite", "ICD-O-3", "inside precoordinated dx concept", "DRAFT"),
 ("case.diagnosisOd.grading", "measurement", "value_as_concept_id", "Cancer Modifier vocab (meas_event link to condition)", "", "DRAFT"),
 ("case.diagnosisOd.tnmClassifications", "measurement", "value_as_concept_id", "AJCC 'TNM Finding by AJCC/UICC' (Ed.7 loaded; Ed.8 contested)", "per cT/cN/cM + stage group", "DRAFT"),
 ("case.diagnosisOd.ecogPerformanceStatusScore", "measurement", "value_as_number/value_as_concept_id", "LOINC/SNOMED [VERIFY concept_id]", "", "DRAFT"),
 ("case.diagnosisOd.diagnosticAssessment", "observation", "value_as_concept_id", "no standard; local/source", "GAP", "DRAFT"),
 ("case.diagnosisOd.germlineDiagnosisConfirmed", "measurement", "value_as_concept_id", "no standard; local", "GAP", "DRAFT"),
 ("case.diagnosisOd.additionalClassification", "measurement", "value_as_concept_id", "no standard; local", "GAP", "DRAFT"),
 ("case.diagnosisOd.hpoTerms", "observation", "observation_concept_id", "HPO (source vocab since OHDSI v20260227)", "non-standard -> not natively queryable", "DRAFT"),
 # prior dx / molecular
 ("case.priorDiagnostics", "measurement", "Genomic Extension measurement concepts", "HGVS/HGNC via OMOP Genomic Extension (Koios); novel/VUS lost", "GAP: no native variant table in v5.4", "DRAFT"),
 ("case.priorProcedures[].intention", "", "", "no standard OMOP concept for treatment intent", "GAP", "NOMAP"),
 ("case.priorProcedures[].treatmentType", "episode", "episode (Treatment Regimen 32531) / drug_exposure", "HemOnc regimen; stellung has no standard", "GAP (no intent/stellung concept)", "DRAFT"),
 ("case.priorProcedures[].terminationReasonOBDS", "", "", "no standard; drug/episode source_value", "GAP", "NOMAP"),
 ("case.priorProcedures[].therapyResponse", "measurement", "value_as_concept_id", "RECIST has NO standard OMOP concept set", "GAP", "DRAFT"),
 ("molecular.smallVariants", "measurement", "measurement_concept_id / value_as_concept_id [VERIFY]", "OMOP Genomic Extension (~55k known variants via HGVS/HGNC); novel lost", "GAP: zygosity/VAF/read-depth -> source_value only", "DRAFT"),
 ("molecular.copyNumberVariants", "measurement", "—", "no OMOP CNV model", "GAP", "DRAFT"),
 ("molecular.structuralVariants", "measurement", "—", "no OMOP fusion/SV model", "GAP", "DRAFT"),
 ("molecular.expressionVariants", "measurement", "—", "no OMOP expression model", "GAP", "DRAFT"),
 ("molecular.complexBiomarkers[].tmb", "measurement", "value_as_number", "TMB LOINC/SNOMED [VERIFY]", "", "DRAFT"),
 ("molecular.complexBiomarkers", "measurement", "value_as_number/concept", "MSI LOINC/SNOMED [VERIFY]; HRD/LST/TAI/ploidy no standard", "GAP", "DRAFT"),
 ("molecular.sbsSignatures", "measurement", "—", "no OMOP mutational-signature concept", "GAP", "DRAFT"),
 # plan (recommendations) — OMOP has no recommendation home
 ("plan.recommendedSystemicTherapies.substances", "drug_exposure", "drug_concept_id", "ATC->RxNorm; but it's a RECOMMENDATION not exposure -> semantically NOMAP", "GAP", "NOMAP"),
 ("plan.recommendedSystemicTherapies", "", "", "OMOP observational: no therapy-recommendation table", "GAP", "NOMAP"),
 ("plan.recommendedStudies", "", "", "no OMOP study-recommendation table", "GAP", "NOMAP"),
 ("plan.carePlanOd", "episode", "episode (MTB) at most", "OMOP has no care-plan/recommendation model", "GAP", "NOMAP"),
 ("plan.preventiveMeasures", "", "", "no OMOP recommendation home", "GAP", "NOMAP"),
 ("metaData.molecularBoardDecisionDate", "episode", "episode (MTB disease/treatment episode)", "OMOP-oncology episode model", "", "DRAFT"),
 # followUp
 ("followUp.followUpOds[].therapies[].therapyResponse", "measurement", "value_as_concept_id", "RECIST no standard OMOP concept", "GAP", "DRAFT"),
 ("followUp.followUpOds[].phenotypes", "observation", "observation_concept_id", "HPO source vocab", "status-history: no OMOP pattern", "DRAFT"),
 ("followUp.followUpOds[].ecogPerformanceStatusScore", "measurement", "value_as_number", "LOINC/SNOMED [VERIFY]", "", "DRAFT"),
 ("followUp.followUpOds[].metachroneDiagnoses", "condition_occurrence", "condition_concept_id", "SNOMED", "", "DRAFT"),
 ("followUp.followUpOds[].preventiveMeasures", "", "", "no OMOP recommendation home", "GAP", "NOMAP"),
 ("followUp.followUpOds[].therapies", "drug_exposure", "drug_concept_id + episode", "ATC->RxNorm; HemOnc regimen episode", "", "DRAFT"),
 ("followUp.followUpOds[].followUpDate", "visit_occurrence", "visit_start_date", "follow-up visit", "", "DRAFT"),
 ("followUp.followUpOds[].lastContactDate", "observation", "observation_date", "last-contact", "", "DRAFT"),
]
RD = [
 ("case.diagnosisRd.diagnoses", "condition_occurrence", "condition_concept_id + source", "SNOMED standard; ORPHA+Alpha-ID-SE as SOURCE (ORPHA NOT an OMOP vocab; ~3k/7k SNOMED coverage)", "GAP: long-tail RD loss; Alpha-ID-SE no concept", "DRAFT"),
 ("case.diagnosisRd.phenotypes", "observation", "observation_concept_id", "HPO source vocab (Feb 2026); not standard/queryable", "GAP: excluded/refuted + status-history no pattern", "DRAFT"),
 ("case.diagnosisRd.diagnosisGmfcs", "measurement", "value_as_number/source", "no OMOP GMFCS concept -> local", "GAP", "DRAFT"),
 ("case.diagnosisRd.diagnosticExtent", "fact_relationship", "fact_relationship + local concept", "single/duo/trio: no 'trio' concept", "GAP", "DRAFT"),
 ("case.diagnosisRd.diagnosticAssessment", "observation", "value_as_concept_id", "verification status no clean OMOP home", "GAP", "DRAFT"),
 ("case.priorRds", "visit_occurrence", "visit_occurrence", "hospitalization count -> visits", "", "DRAFT"),
 ("molecular.smallVariants", "measurement", "G-CDM Variant_Occurrence (somatic-focused)", "HGVS/HGNC; germline ACMG class+criteria ABSENT in OMOP", "GAP: ACMG/zygosity/segregation/de-novo", "DRAFT"),
 ("molecular.copyNumberVariants", "measurement", "G-CDM (partial)", "CNV partial", "GAP", "DRAFT"),
 ("molecular.structuralVariants", "measurement", "G-CDM (partial)", "SV partial", "GAP", "DRAFT"),
 ("plan.recommendedTherapies", "", "", "no OMOP recommendation table", "GAP", "NOMAP"),
 ("plan.recommendedStudies", "", "", "no OMOP study-recommendation table", "GAP", "NOMAP"),
 ("plan.carePlanRd", "", "", "no OMOP care-plan/recommendation model", "GAP", "NOMAP"),
 ("followUp.followUpRds[].phenotypes", "observation", "observation_concept_id", "HPO source vocab", "status-history no pattern", "DRAFT"),
 ("followUp.followUpRds[].gmfcs", "measurement", "value_as_number", "no GMFCS concept -> local", "GAP", "DRAFT"),
]
GRZ = [
 ("donors[].labData[].sequenceData.files", "", "", "raw genomic files — out of OMOP scope", "", "NOMAP"),
 ("donors[].labData[].sequenceData.referenceGenome", "measurement", "—", "no OMOP reference-genome-build field (coordinate-provenance liability)", "GAP", "DRAFT"),
 ("donors[].labData[].sequenceData", "measurement", "value_as_number (local)", "coverage/quality QC: no OMOP home (G-CDM partial)", "GAP", "DRAFT"),
 ("donors[].labData[].libraryType", "measurement", "—", "sequencing metadata: no OMOP home", "GAP", "DRAFT"),
 ("donors[].labData[].sequenceType", "measurement", "—", "no OMOP home", "GAP", "DRAFT"),
 ("donors[].labData[].sequenceSubtype", "measurement", "—", "no OMOP home", "GAP", "DRAFT"),
 ("donors[].labData[].sequencingLayout", "", "", "no OMOP home", "GAP", "NOMAP"),
 ("donors[].labData[].fragmentationMethod", "", "", "no OMOP home", "GAP", "NOMAP"),
 ("donors[].labData[].kitName", "", "", "device/kit metadata: no OMOP home", "GAP", "NOMAP"),
 ("donors[].labData[].kitManufacturer", "", "", "no OMOP home", "GAP", "NOMAP"),
 ("donors[].labData[].libraryPrepKit", "", "", "no OMOP home", "GAP", "NOMAP"),
 ("donors[].labData[].libraryPrepKitManufacturer", "", "", "no OMOP home", "GAP", "NOMAP"),
 ("donors[].labData[].enrichmentKitDescription", "", "", "no OMOP home", "GAP", "NOMAP"),
 ("donors[].labData[].enrichmentKitManufacturer", "", "", "no OMOP home", "GAP", "NOMAP"),
 ("donors[].labData[].sequencerModel", "", "", "no OMOP home", "GAP", "NOMAP"),
 ("donors[].labData[].sequencerManufacturer", "", "", "no OMOP home", "GAP", "NOMAP"),
 ("donors[].labData[].barcode", "specimen", "specimen.specimen_source_id", "sample barcode", "", "DRAFT"),
 ("donors[].labData[].labDataName", "", "", "label only", "GAP", "NOMAP"),
]
TABLES = {"mapping_omop_kdk_oncology.csv": ONC, "mapping_omop_kdk_rarediseases.csv": RD, "mapping_omop_grz.csv": GRZ}
def norm(p): return p.replace("[]", "")
def match(path, rules):
    np = norm(path); best = None
    for r in rules:
        pre = norm(r[0])
        if np == pre or np.startswith(pre + ".") or np.startswith(pre + "["):
            if best is None or len(pre) > len(norm(best[0])): best = r
    return best
def main():
    for tf, rules in TABLES.items():
        rows = list(csv.DictReader(open(MAP / tf))); fields = list(rows[0].keys()); n = 0
        for r in rows:
            if r["status"] not in ("", "TODO"): continue
            m = match(r["path"], rules)
            if not m: continue
            _, tbl, fld, vocab, tr, st = m
            r["omop_table"], r["omop_field"], r["omop_vocab"], r["omop_transform"], r["status"] = tbl, fld, vocab, tr, st
            r["notes"] = (r["notes"] + " | " if r["notes"] else "") + R
            n += 1
        with open(MAP / tf, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
        c = collections.Counter(r["status"] for r in rows)
        print(f"{tf}: +{n} | {dict(c)}")
if __name__ == "__main__":
    main()
