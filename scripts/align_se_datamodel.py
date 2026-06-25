#!/usr/bin/env python3
"""Apply the canonical DNPM SE (Rare Disease) Data Model to the RD mapping table.

Source: knowledge/dnpm-rd/se-datamodel-crosswalk.md + se-implementierungsleitfaden.md
(the authoritative DNPM↔BfArM-Datenkranz RD crosswalk, Confluence export).

Mostly CONFIRMS the existing RD alignment + pins exact value sets/cardinalities.
One real FIX: diagnosticAssessment = genetic Verification Status → Condition.verificationStatus
(was a DRAFT with an invalid placeholder profile). Audit trail. [[se-datamodel-crosswalk]]
"""
import csv
from pathlib import Path
MAP = Path(__file__).resolve().parent.parent / "mapping" / "mapping_kdk_rarediseases.csv"
DIAG = "https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose"
S = "[[se-datamodel-crosswalk]] DNPM SE Data Model"

# path -> dict of column updates
U = {
  # FIX: genetic verification status (not a bare Observation)
  "case.diagnosisRd.diagnosticAssessment": dict(
    mii_module="Diagnose", mii_profile=DIAG, fhir_element="Condition.verificationStatus", status="MAPPED",
    transform="(genetic) Verification Status -> condition-ver-status VS: noGeneticDiagnosis->unconfirmed, suspectedGeneticDiagnosis->provisional, clinicalPhenotypeOnlyPartiallyResolved->partial, geneticDiagnosisConfirmed->confirmed (SEFall: Bewertung der genetischen Diagnostik)", notes=S),
  # enrich (keep status)
  "case.diagnosisRd.diagnosticExtent": dict(
    transform="Family Control Level {single-genome, duo-genome, trio-genome}; SEFall: Empfehlung Diagnostik; required iff sequencing performed", notes=S),
  "molecular.copyNumberVariants[].type": dict(
    transform="RD CNV Type {gain, loss} ONLY (unlike MTB low-/high-level-gain) -> component:variant-type", notes=S),
  "plan.recommendedTherapies[].type": dict(
    transform="Therapy Category {symptomatic, causal} (SEPlan: Art der empfohlenen Therapie); no MII RD recommendation profile", notes=S),
  "plan.recommendedTherapies[].strategy": dict(
    transform="Therapy Type {systemic-medication, targeted-medication, prevention-medication, genetic, prophylactic, early-detection, combination, nutrition, other}; no MII RD profile", notes=S),
  "plan.carePlanRd.clinicalManagementDescriptions[]": dict(
    transform="Clinical Management Type (Ref. TNAMSE) {disease-specific-ambulatory-care, university-ambulatory-care, local-crd, other-crd, other-ambulatory-care, gp, specialist}", notes=S),
}
# prefix updates
PFX = {
  "case.diagnosisRd.diagnoses": dict(
    transform="SEFall: Diagnose-Codes; 1..3 codings ORDO (http://www.orpha.net) + ICD-10-GM + Alpha-ID (target system bfarm/alpha-id; source Alpha-ID-SE) OR set noMatchingCodeExists", notes=S),
  "case.diagnosisRd.phenotypes": dict(
    transform="HPO Coding code+version; status history {improved, degraded, abated->noLongerObserved, unchanged} (newlyAdded is DERIVED, not in DNPM source enum)", notes=S),
  "followUp.followUpRds[].phenotypes": dict(
    transform="HPO status-history entry per follow-up {improved, degraded, abated->noLongerObserved, unchanged}", notes=S),
}

def norm(p): return p.replace("[]", "")
def main():
    rows = list(csv.DictReader(open(MAP))); fields = list(rows[0].keys()); n = 0
    Un = {norm(k): v for k, v in U.items()}
    Pn = {norm(k): v for k, v in PFX.items()}
    for r in rows:
        np = norm(r["path"]); applied = False
        if np in Un:
            for c, v in Un[np].items(): r[c] = v
            applied = True
        else:
            for pre, v in Pn.items():
                if np == pre or np.startswith(pre + ".") or np.startswith(pre + "["):
                    for c, val in v.items(): r[c] = val
                    applied = True; break
        if applied: n += 1
    with open(MAP, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"mapping_kdk_rarediseases.csv: {n} rows updated from SE data model")
if __name__ == "__main__":
    main()
