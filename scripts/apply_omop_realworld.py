#!/usr/bin/env python3
"""Apply real-world OMOP research revisions (Belenkaya 2021 + npj 2025 scoping review +
RD-CDM/RareLink findings) to the OMOP mapping tables.

knowledge/omop/omop-oncology-realworld.md + omop-rare-disease-realworld.md.
Corrects over-grading (spine over-matched priorProcedures sub-fields to MAPPED
procedure) and hardens GAP notes with real-world non-adoption evidence.
"""
import csv
from pathlib import Path
MAP = Path(__file__).resolve().parent.parent / "mapping"
PO = "[[omop-oncology-realworld]]"
PR = "[[omop-rare-disease-realworld]]"

# exact-path FORCE overrides: path -> (table, field, vocab, transform, status, prov)
FIX = {
 "mapping_omop_kdk_oncology.csv": {
  "case.priorProcedures[].therapyResponse": ("measurement", "value_as_concept_id", "—", "RECIST: NO standard OMOP concept (absent from Oncology Extension + npj 2025 review)", "DRAFT", PO),
  "case.priorProcedures[].therapyResponseDate": ("measurement", "measurement_date", "—", "date of RECIST response; no concept", "DRAFT", PO),
  "case.priorProcedures[].intention": ("", "", "—", "treatment INTENT: no OMOP concept; lost when folded into a procedure", "NOMAP", PO),
  "case.priorProcedures[].terminationReasonOBDS": ("", "", "—", "no standard OMOP concept; source_value at most", "NOMAP", PO),
  "case.priorProcedures[].treatmentType": ("episode", "episode (Treatment Regimen 32531)", "HemOnc", "regimen episode — LOW real-world adoption (npj 2025: Episode in few studies)", "DRAFT", PO),
  "case.diagnosisOd.libraryType": ("procedure_occurrence", "procedure_concept_id", "SNOMED", "the genomic test is a PROCEDURE", "DRAFT", PO),
 },
 "mapping_omop_kdk_rarediseases.csv": {
  "case.diagnosisRd.libraryType": ("procedure_occurrence", "procedure_concept_id", "SNOMED", "the genomic test is a PROCEDURE", "DRAFT", PR),
 },
}
# prefix NOTE-append (keep mapping, force status, append evidence note + provenance)
NOTE = {
 "mapping_omop_kdk_oncology.csv": [
  ("case.diagnosisOd.grading", "DRAFT", "real-world NON-adoption (npj 2025 gap list: grade), not just uncertainty", PO),
  ("case.diagnosisOd.tnmClassifications", "DRAFT", "real-world NON-adoption (npj 2025 gap list: staging/TNM)", PO),
  ("case.diagnosisOd.ecogPerformanceStatusScore", "DRAFT", "real-world NON-adoption (npj 2025 gap list: ECOG)", PO),
  ("followUp.followUpOds[].ecogPerformanceStatusScore", "DRAFT", "real-world NON-adoption (npj 2025: ECOG)", PO),
  ("molecular", "DRAFT", "real-world NON-adoption (npj 2025: genetic/molecular variants & biomarkers; omics 'yet unexplored')", PO),
  ("followUp.followUpOds[].vitalStatus", "MAPPED", "DEATH minimally used + under-reported in real OMOP oncology", PO),
  ("followUp.followUpOds[].deathDate", "MAPPED", "DEATH minimally used + under-reported", PO),
  ("followUp.followUpOds[].followUpDate", "DRAFT", "Visit_occurrence weakly adopted in oncology OMOP", PO),
  ("plan", "NOMAP", "no MTB-on-OMOP exists; OMOP oncology Episode model omits tumor-board recommendations", PO),
 ],
 "mapping_omop_kdk_rarediseases.csv": [
  ("case.diagnosisRd.diagnoses", "DRAFT", "ORPHA NOT in Athena (confirmed 2026): local vocab >2bn + Usagi + SNOMED standard; long-tail loss; Alpha-ID-SE source-value only", PR),
  ("case.diagnosisRd.phenotypes", "DRAFT", "HPO source-only vocab (non-queryable); excluded/refuted unmapped (OMOP absence convention); MONDO bridge option", PR),
  ("followUp.followUpRds[].phenotypes", "DRAFT", "HPO source-only; status-history no OMOP pattern", PR),
  ("molecular.smallVariants", "DRAFT", "OMOP Genomic (HGVS/HGNC); VRS/KOIOS emerging but cancer-scoped; ACMG=gene-list filter only (no germline classification); zygosity/segregation/inheritance/trio unmodelled", PR),
  ("molecular.copyNumberVariants", "DRAFT", "OMOP Genomic cancer-scoped; germline CNV unmodelled", PR),
  ("molecular.structuralVariants", "DRAFT", "OMOP Genomic cancer-scoped; germline SV unmodelled", PR),
  ("plan", "NOMAP", "do NOT map recommendations to drug/procedure (=administered/performed, semantic error); no OMOP recommendation home; real RD-CDM is FHIR/Phenopackets (Graefe 2025/RareLink)", PR),
 ],
}
def norm(p): return p.replace("[]", "")
def addnote(r, note, prov):
    if prov in r["notes"]: return
    extra = " | ".join(x for x in (note, prov) if x)
    r["notes"] = (r["notes"] + " | " + extra) if r["notes"] else extra
def main():
    for fn in FIX:
        rows = list(csv.DictReader(open(MAP / fn))); fields = list(rows[0].keys()); nf = nn = 0
        fixmap = {norm(k): v for k, v in FIX[fn].items()}
        for r in rows:
            np = norm(r["path"])
            if np in fixmap:
                tbl, fld, voc, tr, st, prov = fixmap[np]
                r["omop_table"], r["omop_field"], r["omop_vocab"], r["omop_transform"], r["status"] = tbl, fld, voc, tr, st
                addnote(r, "", prov); nf += 1
                continue
            for pre, st, note, prov in NOTE.get(fn, []):
                p = norm(pre)
                if np == p or np.startswith(p + ".") or np.startswith(p + "["):
                    r["status"] = st; addnote(r, note, prov); nn += 1; break
        with open(MAP / fn, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
        print(f"{fn}: {nf} fixed, {nn} re-noted")
if __name__ == "__main__":
    main()
