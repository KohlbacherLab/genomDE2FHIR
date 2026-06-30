#!/usr/bin/env python3
"""Annotate the OMOP mapping with insights from the deployed mihubx/MIRACUM FHIR->OMOP
ETL + HL7 FHIR-to-OMOP IG (knowledge/research/fhir-to-omop-mihubx-etl.md).
Note-only (idempotent on the provenance tag); statuses unchanged.
"""
import csv
from pathlib import Path
MAP = Path(__file__).resolve().parent.parent / "mapping"
PROV = "[[fhir-to-omop-mihubx-etl]]"
VALID = "VALIDATED by deployed mihubx/MIRACUM FHIR->OMOP ETL (map-once-via-FHIR)"
DOMAIN = "OMOP target table = resolved standard concept's domain_id (measurement|observation|condition), not fixed"
STAGE = "impl path: stage/severity -> diagnosis-Condition linkage (post_process_map + fact_relationship); table=concept domain"
NOFHIR = "no FHIR->OMOP mapper exists (genomics out of scope in ETL + HL7 IG) -> direct-to-OMOP-Genomic-CDM only"
VERIF = "ETL ConditionMapper handles verificationStatus + Diagnosesicherheit (SOURCE_TO_CONCEPT_MAP diagnostic-confidence)"

NOTES = {
 "mapping_omop_kdk_oncology.csv": [
  ("case.diagnosisOd.mainDiagnosis", VALID), ("case.diagnosisOd.additionalDiagnoses", VALID),
  ("case.diagnosisOd.germlineDiagnoses", VALID), ("followUp.followUpOds[].additionalDiagnoses", VALID),
  ("case.priorProcedures", VALID), ("followUp.followUpOds[].therapies", VALID),
  ("case.diagnosisOd.grading", STAGE + " | " + DOMAIN), ("case.diagnosisOd.tnmClassifications", STAGE + " | " + DOMAIN),
  ("case.diagnosisOd.ecogPerformanceStatusScore", DOMAIN), ("followUp.followUpOds[].ecogPerformanceStatusScore", DOMAIN),
  ("case.diagnosisOd.germlineDiagnosisConfirmed", VERIF), ("case.diagnosisOd.hpoTerms", DOMAIN + " (HPO source vocab)"),
  ("molecular", NOFHIR),
 ],
 "mapping_omop_kdk_rarediseases.csv": [
  ("case.diagnosisRd.diagnoses", VALID + " | concrete ORPHA->SNOMED bridge available (MIRACUM orpha_snomed_mapping.csv, 5,906->Condition); long-tail loss remains"),
  ("case.diagnosisRd.diagnosticAssessment", VERIF),
  ("case.diagnosisRd.phenotypes", DOMAIN + " (HPO source vocab)"),
  ("followUp.followUpRds[].phenotypes", DOMAIN + " (HPO source vocab)"),
  ("molecular", NOFHIR),
 ],
 "mapping_omop_grz.csv": [
  ("donors[].labData[].sequenceData", NOFHIR), ("donors[].labData[].libraryType", NOFHIR),
 ],
}
def norm(p): return p.replace("[]", "")
def main():
    for fn, rules in NOTES.items():
        rows = list(csv.DictReader(open(MAP / fn))); fields = list(rows[0].keys()); n = 0
        for r in rows:
            np = norm(r["path"])
            for pre, note in rules:
                p = norm(pre)
                if np == p or np.startswith(p + ".") or np.startswith(p + "["):
                    if PROV in r["notes"]:
                        break
                    add = note + " | " + PROV
                    r["notes"] = (r["notes"] + " | " + add) if r["notes"] else add
                    n += 1
                    break
        with open(MAP / fn, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
        print(f"{fn}: {n} rows annotated")
if __name__ == "__main__":
    main()
