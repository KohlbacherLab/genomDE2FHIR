#!/usr/bin/env python3
"""Promote RD rows to concrete MII Seltene-Erkrankungen profiles (crawl-verified,
pkg de.medizininformatikinitiative.kerndatensatz.seltene@2026.0.0) + apply the
RD adversarial-review (codex+vibe) corrections grounded in the SE Data Model.

Big win: the generic CarePlan/ServiceRequest/ResearchStudy/MedicationRequest RD
recommendation rows + the core Diagnose rows now target real Seltene profiles.
Plus fixes: hospitalization (banded codes, not Encounter.period/length);
diagnosticAssessment furtherGeneticDiagnosticRecommended has no ver-status target.
[[docs/REVIEW-SE-codex]] [[se-datamodel-crosswalk]]
"""
import csv
from pathlib import Path
MAP = Path(__file__).resolve().parent.parent / "mapping" / "mapping_kdk_rarediseases.csv"
SEL = "https://www.medizininformatik-initiative.de/fhir/ext/modul-seltene/StructureDefinition/"
P = {k: SEL + v for k, v in {
  "gendiag": "mii-pr-seltene-genetic-diagnosis", "careplan": "mii-pr-seltene-therapieplan",
  "therec": "mii-pr-seltene-therapieempfehlung", "studyreq": "mii-pr-seltene-studieneinschluss-anfrage",
  "study": "mii-pr-seltene-studie", "clinimpr": "mii-pr-seltene-clinical-impression",
}.items()}
R = "[[docs/REVIEW-SE-codex]] seltene@2026.0.0"

EXACT = {
  "case.diagnosisRd.diagnosticAssessment": dict(mii_module="Seltene", mii_profile=P["gendiag"],
    fhir_element="Condition.verificationStatus", status="MAPPED",
    transform="genetic Verification Status -> condition-ver-status: noGeneticDiagnosis->unconfirmed, suspectedGeneticDiagnosis->provisional, clinicalPhenotypeOnlyPartiallyResolved->partial, geneticDiagnosisConfirmed->confirmed. CAVEAT: 'furtherGeneticDiagnosticRecommended' has NO ver-status target (fallback/note required)", notes=R),
  "case.diagnosisRd.noMatchingCodeExists": dict(mii_module="Seltene", mii_profile=P["gendiag"],
    fhir_element="Condition.code.extension(data-absent-reason)", status="MAPPED",
    transform="coded missing reason 'no-matching-code' when not all 3 of ICD-10-GM/ORDO/Alpha-ID-SE available", notes=R),
  "case.diagnosisRd.symptomOnsetDate": dict(mii_module="Seltene", mii_profile=P["gendiag"], fhir_element="Condition.onsetDateTime", notes=R),
  "followUp.followUpRds[].diagnosisEstablished": dict(mii_module="Seltene", mii_profile=P["gendiag"],
    fhir_element="Condition.verificationStatus (derived)", status="MAPPED",
    transform="DERIVED: established iff verificationStatus != unconfirmed; do NOT overwrite provisional/partial/confirmed", notes=R),
  "followUp.followUpRds[].diseaseProgression": dict(mii_module="Seltene", mii_profile=P["clinimpr"],
    fhir_element="ClinicalImpression.summary / Condition.note", status="MAPPED", transform="disease-course free text (SEVerfolgung)", notes=R),
  # FIX: hospitalization = banded count/day codes, NOT Encounter periods
  "case.priorRds[].hospitalizationPeriods": dict(mii_module="", mii_profile="Observation",
    fhir_element="Observation.valueCodeableConcept", status="DRAFT",
    transform="BANDED count code {none,up-to-five,up-to-ten,up-to-fifteen,over-fifteen,unknown} (SE: Number of hospitalizations total) — NOT Encounter.period; no MII profile", notes=R),
  "case.priorRds[].hospitalizationDuration": dict(mii_module="", mii_profile="Observation",
    fhir_element="Observation.valueCodeableConcept", status="DRAFT",
    transform="BANDED days code {none,up-to-five,up-to-fifteen,up-to-fifty,over-fifty,unknown} (SE: Number of hospitalization days total) — NOT Encounter.length; no MII profile", notes=R),
}
PFX = {
  "case.diagnosisRd.diagnoses": dict(mii_module="Seltene", mii_profile=P["gendiag"],
    transform="MII Seltene genetic-diagnosis (clinical-diagnosis if not genetically confirmed); 1..3 codings ICD-10-GM + ORDO (http://www.orpha.net) + Alpha-ID (target bfarm/alpha-id; source Alpha-ID-SE) OR noMatchingCodeExists", notes=R),
  "plan.carePlanRd": dict(mii_module="Seltene", mii_profile=P["careplan"], notes=R),
  "plan.recommendedTherapies": dict(mii_module="Seltene", mii_profile=P["therec"], status="MAPPED",
    transform="MII Seltene Therapieempfehlung (-nicht-medikamentoes / -kombination by Therapy Type); Category {symptomatic,causal}, Type {systemic-medication,targeted-medication,prevention-medication,genetic,prophylactic,early-detection,combination,nutrition,other}", notes=R),
  "plan.recommendedStudies": dict(mii_module="Seltene", mii_profile=P["studyreq"], status="MAPPED",
    transform="MII Seltene Studieneinschluss-Anfrage (ServiceRequest) -> mii-pr-seltene-studie (ResearchStudy); registries NCT/DRKS/Eudra-CT", notes=R),
}

def norm(p): return p.replace("[]", "")
def main():
    rows = list(csv.DictReader(open(MAP))); fields = list(rows[0].keys()); n = 0
    En = {norm(k): v for k, v in EXACT.items()}
    Pn = {norm(k): v for k, v in PFX.items()}
    for r in rows:
        np = norm(r["path"]); hit = None
        if np in En: hit = En[np]
        else:
            for pre, v in sorted(Pn.items(), key=lambda kv: -len(kv[0])):
                if np == pre or np.startswith(pre + ".") or np.startswith(pre + "["):
                    hit = v; break
        if hit:
            for c, val in hit.items(): r[c] = val
            n += 1
    with open(MAP, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"mapping_kdk_rarediseases.csv: {n} rows -> concrete Seltene profiles / fixes")
if __name__ == "__main__":
    main()
