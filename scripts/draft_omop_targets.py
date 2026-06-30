#!/usr/bin/env python3
"""First-pass OMOP targets — the STANDARD-OMOP clinical spine only.

Fills the uncontroversial mappings (person/location/death, condition_occurrence for
diagnoses, procedure_occurrence, drug_exposure) that don't depend on the in-flight
oncology/genomic/rare-disease research. Oncology attributes (histology/grade/TNM/ECOG),
molecular variants, phenotypes/GMFCS, episodes and care-plan recommendations are LEFT
as TODO — they need the research (OMOP Oncology episode model + Genomic-CDM).

Safe to re-run: only fills rows whose status is TODO/empty.
"""
import csv
from pathlib import Path
MAP = Path(__file__).resolve().parent.parent / "mapping"

# (prefix, omop_table, omop_field, omop_vocab, transform, status)
META = [
 ("metaData.birthDate", "person", "birth_datetime / year_of_birth", "-", "partial date -> year/month", "DRAFT"),
 ("metaData.gender", "person", "gender_concept_id", "Gender", "male/female/other/unknown -> Gender concepts (source in gender_source_value)", "DRAFT"),
 ("metaData.addressAGS", "location", "location.* (person.location_id)", "-", "AGS Gemeindeschluessel -> location_source_value/county", "DRAFT"),
 ("metaData.localCaseId", "person", "person_source_value", "-", "site-local id", "DRAFT"),
 ("metaData.tanC", "person", "person_source_value / person.person_id", "-", "pseudonym", "DRAFT"),
 ("metaData.coverageType", "payer_plan_period", "payer_concept_id", "-", "GKV/PKV -> payer (or omit)", "DRAFT"),
 ("metaData.mvConsent", "observation", "observation (consent)", "-", "OMOP has NO consent model; represent as observation or out-of-scope", "DRAFT"),
 ("metaData.researchConsents", "observation", "observation (consent)", "-", "no OMOP consent model; observation or out-of-scope", "DRAFT"),
 ("metaData.decisionToInclude", "", "", "-", "administrative; not OMOP-analytic", "NOMAP"),
 ("metaData.rejectionJustification", "", "", "-", "administrative", "NOMAP"),
 ("metaData.molecularBoardDecisionDate", "episode", "episode (MTB) — see research", "-", "deferred to OMOP-oncology episode research", "TODO"),
 ("metaData.submission", "", "", "-", "transport/provenance; not OMOP clinical", "NOMAP"),
]
DIAG_ONC = [
 ("case.diagnosisOd.mainDiagnosis", "condition_occurrence", "condition_source_value/condition_source_concept_id + condition_concept_id", "ICD-10-GM (source) -> SNOMED (standard)", "ICD-10-GM coding; .date -> condition_start_date", "DRAFT"),
 ("case.diagnosisOd.additionalDiagnoses", "condition_occurrence", "condition_source_concept_id + condition_concept_id", "ICD-10-GM -> SNOMED", "", "DRAFT"),
 ("case.diagnosisOd.germlineDiagnoses", "condition_occurrence", "condition_source_concept_id + condition_concept_id", "ICD-10-GM -> SNOMED", "germline dx", "DRAFT"),
]
PRIOR_ONC = [
 ("case.priorProcedures.substances", "drug_exposure", "drug_source_concept_id + drug_concept_id", "ATC (source) -> RxNorm (standard)", "substance of prior therapy", "DRAFT"),
 ("case.priorProcedures", "procedure_occurrence", "procedure_source_value + procedure_concept_id", "OPS (source) -> SNOMED (standard)", "prior procedure; dates -> procedure_date", "DRAFT"),
]
FU_ONC = [
 ("followUp.followUpOds[].therapies.substances", "drug_exposure", "drug_source_concept_id + drug_concept_id", "ATC -> RxNorm", "administered therapy substance", "DRAFT"),
 ("followUp.followUpOds[].additionalDiagnoses", "condition_occurrence", "condition_source_concept_id + condition_concept_id", "ICD-10-GM -> SNOMED", "", "DRAFT"),
 ("followUp.followUpOds[].vitalStatus", "death", "death.death_type_concept_id / person", "-", "alive/dead -> death record if deceased", "DRAFT"),
 ("followUp.followUpOds[].deathDate", "death", "death.death_date", "-", "", "DRAFT"),
]
DIAG_RD = [
 ("case.diagnosisRd.diagnoses", "condition_occurrence", "condition_source_concept_id + condition_concept_id", "ORPHA/ICD-10-GM/Alpha-ID-SE (source) -> SNOMED (standard); VERIFY ORPHA vocab in OMOP", "all-three coding; date -> condition_start_date", "DRAFT"),
]
GRZ_RULES = [
 ("donors[].gender", "person", "gender_concept_id", "Gender", "donor sex", "DRAFT"),
 ("donors[].donorPseudonym", "person", "person_source_value", "-", "donor pseudonym", "DRAFT"),
 ("donors[].relation", "fact_relationship", "fact_relationship (person-person)", "-", "trio/family relation; index donor = the person", "DRAFT"),
 ("donors[].mvConsent", "observation", "observation (consent)", "-", "no OMOP consent model", "DRAFT"),
 ("donors[].researchConsents", "observation", "observation (consent)", "-", "no OMOP consent model", "DRAFT"),
 ("donors[].labData[].tissueOntology", "specimen", "specimen_concept_id / anatomic_site_concept_id", "BTO/SNOMED", "tissue type", "DRAFT"),
 ("donors[].labData[].tissueTypeId", "specimen", "specimen_concept_id", "BTO/SNOMED", "tissue code", "DRAFT"),
 ("donors[].labData[].tissueTypeName", "specimen", "specimen_source_value", "-", "tissue display", "DRAFT"),
 ("donors[].labData[].tumorCellCount", "measurement", "value_as_number", "-", "tumour cell content %", "DRAFT"),
 ("donors[].labData[].sampleDate", "specimen", "specimen_date", "-", "collection date", "DRAFT"),
 ("donors[].labData[].sampleConservation", "specimen", "specimen.* (preservation)", "-", "fresh/FFPE etc.", "DRAFT"),
 # NB: labData sequencing/device/QC/files (sequenceData.*, *Kit*, sequencer*, library*,
 # fragmentation*, sequencingLayout, sequenceType/Subtype, barcode, labDataName, files[])
 # are intentionally LEFT as TODO -> need the OMOP Genomic-CDM research.
 ("submission", "", "", "-", "GRZ transport metadata; not OMOP clinical", "NOMAP"),
]
TABLES = {
 "mapping_omop_kdk_oncology.csv": META + DIAG_ONC + PRIOR_ONC + FU_ONC,
 "mapping_omop_kdk_rarediseases.csv": META + DIAG_RD,
 "mapping_omop_grz.csv": GRZ_RULES,
}
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
            n += 1
        with open(MAP / tf, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
        import collections; c = collections.Counter(r["status"] for r in rows)
        print(f"{tf}: filled {n} | {dict(c)}")
if __name__ == "__main__":
    main()
