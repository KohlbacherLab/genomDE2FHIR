#!/usr/bin/env python3
"""One-shot bootstrap: draft MII KDS target columns into the mapping tables.

Fills mii_module / mii_profile / fhir_element / transform / status by matching
each leaf's path against ordered prefix rules (longest prefix wins), then refines
fhir_element by coding-triple suffix (.code/.system/.display/.version/.date).

SAFE TO RE-RUN: only fills rows whose status is TODO/empty. Hand edits (any other
status) are never overwritten. The CSV stays canonical; this is just the draft
seed for the "full draft then review" pass. Profile canonicals are NAMES, not
URLs — exact canonicals get resolved/verified against the locked KDS package
during the mapper phase (status DRAFT flags everything as review-pending).

Usage: draft_targets.py
"""
import csv
from pathlib import Path

MAP = Path(__file__).resolve().parent.parent / "mapping"

# Each rule: (path_prefix, module, profile, base_element, transform, status)
# Longest matching prefix wins. Paths are matched with [] stripped.
# status: DRAFT = mapped, review-pending | NOMAP = intentionally not mapped

# --- shared metaData (Submission) — applies to both KDK branches ---
META = [
    ("metaData.birthDate",        "Person", "Patient", "Patient.birthDate", "partial date allowed", "DRAFT"),
    ("metaData.gender",           "Person", "Patient", "Patient.gender", "+ gender-amtlich-de ext for divers/unbestimmt; ConceptMap to administrative-gender", "DRAFT"),
    ("metaData.addressAGS",       "Person", "Patient", "Patient.address.extension(AGS Gemeindeschluessel)", "fhir.de address AGS extension", "DRAFT"),
    ("metaData.localCaseId",      "Person", "Patient", "Patient.identifier", "site-local case/patient id; system=site-defined", "DRAFT"),
    ("metaData.tanC",             "Person", "Patient", "Patient.identifier", "TAN pseudonym; system=MV-defined pseudonym id", "DRAFT"),
    ("metaData.coverageType",     "Fall",   "Coverage", "Coverage.type", "GKV/PKV/etc -> Coverage.type (VersicherungsArtDeBasis)", "DRAFT"),
    ("metaData.mvConsent.scope",  "Consent","Consent", "Consent (Modellvorhaben)", "MV-specific consent scopes; embedded object", "DRAFT"),
    ("metaData.mvConsent",        "Consent","Consent", "Consent (Modellvorhaben)", "MV participation consent", "DRAFT"),
    ("metaData.researchConsents", "Consent","Consent", "Consent (MII Broad Consent)", "scope is embedded MII IG Consent v2025 FHIR object -> passthrough", "DRAFT"),
    # MV process metadata -> not part of clinical KDS
    ("metaData.decisionToInclude","",       "", "", "MV board inclusion decision; administrative", "NOMAP"),
    ("metaData.molecularBoardDecisionDate","","", "", "MTB decision date; -> Onkologie MTB/CarePlan if needed", "NOMAP"),
    ("metaData.rejectionJustification","",  "", "", "administrative", "NOMAP"),
    ("metaData.submission",       "",       "", "", "submission/transport provenance -> Bundle/Provenance, not KDS clinical", "NOMAP"),
    ("metaData",                  "Person", "Patient", "Patient", "see metaData.* sub-rules", "DRAFT"),
]

ONCOLOGY = META + [
    # --- diagnosis ---
    ("case.diagnosisOd.mainDiagnosis",    "Diagnose",  "Condition (Primaerdiagnose)", "Condition.code", "ICD-10-GM coding triple; +version; Onkologie Primaertumor", "DRAFT"),
    ("case.diagnosisOd.additionalDiagnoses","Diagnose","Condition", "Condition.code", "ICD-10-GM coding triple", "DRAFT"),
    ("case.diagnosisOd.germlineDiagnoses","Diagnose",  "Condition", "Condition.code", "germline/hereditary tumour syndrome diagnosis", "DRAFT"),
    ("case.diagnosisOd.histology",        "Onkologie", "Observation (Histologie)", "Observation.valueCodeableConcept", "ICD-O-3 morphology", "DRAFT"),
    ("case.diagnosisOd.topography",       "Onkologie", "Condition / Observation", "Condition.bodySite", "ICD-O-3 topography", "DRAFT"),
    ("case.diagnosisOd.grading",          "Onkologie", "Observation (Grading)", "Observation.valueCodeableConcept", "tumour grading", "DRAFT"),
    ("case.diagnosisOd.tnmClassifications","Onkologie","Observation (TNM)", "Observation.component", "TNM (c/p prefix, UICC version)", "DRAFT"),
    ("case.diagnosisOd.additionalClassification","Onkologie","Observation", "Observation", "other staging classifications (key/system)", "DRAFT"),
    ("case.diagnosisOd.ecogPerformanceStatusScore","Onkologie","Observation (ECOG)", "Observation.valueCodeableConcept", "ECOG performance status", "DRAFT"),
    ("case.diagnosisOd.diagnosticAssessment","Onkologie","Observation", "Observation.valueCodeableConcept", "genetic diagnostic evaluation (HT only)", "DRAFT"),
    ("case.diagnosisOd.germlineDiagnosisConfirmed","Onkologie","Observation", "Observation.valueBoolean", "hereditary tumour syndrome confirmed flag", "DRAFT"),
    ("case.diagnosisOd.hpoTerms",         "MolGen",    "Observation (Phaenotyp HPO)", "Observation.valueCodeableConcept", "HPO term", "DRAFT"),
    ("case.diagnosisOd",                  "Diagnose",  "Condition", "Condition", "see diagnosisOd.* sub-rules", "DRAFT"),
    # --- prior procedures / diagnostics ---
    ("case.priorProcedures.substances",   "Medikation","Medication", "Medication.code", "ATC/substance of prior systemic therapy", "DRAFT"),
    ("case.priorProcedures",              "Prozedur",  "Procedure", "Procedure.code", "OPS coding +version; prior treatment", "DRAFT"),
    ("case.priorDiagnostics.simpleVariants","MolGen",  "Observation (Variante)", "Observation", "prior molecular variant (Genomics Reporting variant); VERIFY MolGen profile canonical", "DRAFT"),
    ("case.priorDiagnostics",             "MolGen",    "DiagnosticReport (MolGen)", "DiagnosticReport", "prior molecular diagnostics report", "DRAFT"),
    # --- molecular (MolGen / Genomics Reporting) ---
    ("molecular.smallVariants",           "MolGen", "Observation (SmallVariant)", "Observation", "Genomics Reporting variant; HGNC gene, transcript, HGVS; VERIFY profile+HGNC version", "DRAFT"),
    ("molecular.copyNumberVariants",      "MolGen", "Observation (CopyNumberVariant)", "Observation", "Genomics Reporting CNV; VERIFY profile", "DRAFT"),
    ("molecular.structuralVariants",      "MolGen", "Observation (StructuralVariant)", "Observation", "Genomics Reporting SV / fusion (geneA/geneB); VERIFY profile", "DRAFT"),
    ("molecular.expressionVariants",      "MolGen", "Observation (Expression)", "Observation", "expression variant; VERIFY profile", "DRAFT"),
    ("molecular.complexBiomarkers",       "MolGen", "Observation (Biomarker)", "Observation", "TMB/MSI/HRD etc complex biomarkers; VERIFY profile", "DRAFT"),
    ("molecular.sbsSignatures",           "MolGen", "Observation (Signature)", "Observation", "SBS mutational signatures; VERIFY profile", "DRAFT"),
    ("molecular",                         "MolGen", "DiagnosticReport (MolGen)", "DiagnosticReport", "molecular report container; VERIFY", "DRAFT"),
    # --- plan ---
    ("plan.recommendedSystemicTherapies.substances","Medikation","Medication", "Medication.code", "ATC substance of recommended therapy", "DRAFT"),
    ("plan.recommendedSystemicTherapies","Onkologie","CarePlan / MedicationRequest", "CarePlan.activity", "MTB systemic therapy recommendation", "DRAFT"),
    ("plan.recommendedStudies.substances","Medikation","Medication", "Medication.code", "study drug substance", "DRAFT"),
    ("plan.recommendedStudies",          "Onkologie","CarePlan / ResearchStudy", "CarePlan.activity", "recommended clinical study (NCT/EudraCT)", "DRAFT"),
    ("plan.carePlanOd.suitableInterventions","Onkologie","CarePlan", "CarePlan.activity", "suitable interventions (OPS/type)", "DRAFT"),
    ("plan.carePlanOd",                  "Onkologie","CarePlan", "CarePlan", "oncology care plan / MTB protocol", "DRAFT"),
    ("plan.preventiveMeasures",          "Onkologie","CarePlan", "CarePlan.activity", "preventive measures", "DRAFT"),
    ("plan",                             "Onkologie","CarePlan", "CarePlan", "see plan.* sub-rules", "DRAFT"),
    # --- followUp ---
    ("followUp.followUpOds.therapies.substances","Medikation","Medication", "Medication.code", "ATC substance of administered therapy", "DRAFT"),
    ("followUp.followUpOds.therapies",   "Medikation","MedicationStatement", "MedicationStatement", "systemic therapy given", "DRAFT"),
    ("followUp.followUpOds.additionalDiagnoses","Diagnose","Condition", "Condition.code", "new diagnoses at follow-up", "DRAFT"),
    ("followUp.followUpOds.phenotypes",  "MolGen",   "Observation (Phaenotyp HPO)", "Observation.valueCodeableConcept", "HPO at follow-up", "DRAFT"),
    ("followUp.followUpOds.preventiveMeasures","Onkologie","CarePlan", "CarePlan.activity", "preventive measures at follow-up", "DRAFT"),
    ("followUp.followUpOds",             "Onkologie","Observation (Verlauf/Response)", "Observation", "follow-up status / RECIST response", "DRAFT"),
    ("followUp",                         "Onkologie","Observation (Verlauf)", "Observation", "see followUp.* sub-rules", "DRAFT"),
]

RAREDISEASES = META + [
    ("case.diagnosisRd.diagnoses",        "Diagnose", "Condition", "Condition.code", "ORPHAcode / Alpha-ID-SE / ICD-10-GM / OMIM", "DRAFT"),
    ("case.diagnosisRd.phenotypes",       "MolGen",   "Observation (Phaenotyp HPO)", "Observation.valueCodeableConcept", "HPO term", "DRAFT"),
    ("case.diagnosisRd",                  "Diagnose", "Condition", "Condition", "see diagnosisRd.* sub-rules", "DRAFT"),
    ("case.priorRds",                     "MolGen",   "DiagnosticReport (MolGen)", "DiagnosticReport", "prior rare-disease diagnostics", "DRAFT"),
    ("molecular.smallVariants",           "MolGen", "Observation (SmallVariant)", "Observation", "Genomics Reporting variant; ACMG criteria, HGNC gene; VERIFY profile+HGNC version", "DRAFT"),
    ("molecular.copyNumberVariants",      "MolGen", "Observation (CopyNumberVariant)", "Observation", "CNV; ACMG criteria; VERIFY profile", "DRAFT"),
    ("molecular.structuralVariants",      "MolGen", "Observation (StructuralVariant)", "Observation", "SV; ACMG criteria; VERIFY profile", "DRAFT"),
    ("molecular",                         "MolGen", "DiagnosticReport (MolGen)", "DiagnosticReport", "molecular report container; VERIFY", "DRAFT"),
    ("plan.recommendedTherapies",        "Onkologie","CarePlan / MedicationRequest", "CarePlan.activity", "therapy recommendation (RD)", "DRAFT"),
    ("plan.recommendedStudies",          "Onkologie","CarePlan / ResearchStudy", "CarePlan.activity", "recommended study", "DRAFT"),
    ("plan.carePlanRd",                  "Onkologie","CarePlan", "CarePlan", "rare-disease care plan", "DRAFT"),
    ("plan",                             "Onkologie","CarePlan", "CarePlan", "see plan.* sub-rules", "DRAFT"),
    ("followUp.followUpRds.phenotypes",  "MolGen",   "Observation (Phaenotyp HPO)", "Observation.valueCodeableConcept", "HPO at follow-up", "DRAFT"),
    ("followUp.followUpRds",             "Onkologie","Observation (Verlauf)", "Observation", "follow-up status", "DRAFT"),
    ("followUp",                         "Onkologie","Observation (Verlauf)", "Observation", "see followUp.* sub-rules", "DRAFT"),
]

GRZ = [
    # submission/transport metadata -> GRZ data node, not MII clinical KDS
    ("submission",                        "", "", "", "GRZ submission/transport metadata; not MII KDS clinical (Provenance at most)", "NOMAP"),
    # donor-level
    ("donors.mvConsent.scope",            "Consent", "Consent", "Consent (Modellvorhaben)", "MV consent scope", "DRAFT"),
    ("donors.mvConsent",                  "Consent", "Consent", "Consent (Modellvorhaben)", "MV participation consent", "DRAFT"),
    ("donors.researchConsents",           "Consent", "Consent", "Consent (MII Broad Consent)", "scope=embedded MII Consent object", "DRAFT"),
    # labData / specimen / sequencing
    ("donors.labData.tissueOntology",     "Biobank", "Specimen", "Specimen.type", "tissue ontology (BTO/SNOMED) -> Specimen.type", "DRAFT"),
    ("donors.labData.tumorCellCount",     "Biobank", "Observation", "Observation.valueQuantity", "tumour cell content %", "DRAFT"),
    ("donors.labData.sequenceData.files", "", "", "", "raw sequencing files (FASTQ/BAM/VCF) live in GRZ; not ingested into MII KDS", "NOMAP"),
    ("donors.labData.sequenceData",       "MolGen", "Observation / DocumentReference", "Observation", "sequencing run metadata; caller/quality -> MolGen method/device; VERIFY", "DRAFT"),
    ("donors.labData",                    "Biobank", "Specimen", "Specimen", "lab/specimen metadata; see labData.* sub-rules", "DRAFT"),
    ("donors",                            "Person", "Patient", "Patient", "donor = patient; demographics", "DRAFT"),
]

TABLES = {
    "mapping_kdk_oncology.csv":     ONCOLOGY,
    "mapping_kdk_rarediseases.csv": RAREDISEASES,
    "mapping_grz.csv":              GRZ,
}

CODING_SUFFIX = {
    "code": ".coding.code", "system": ".coding.system",
    "display": ".coding.display", "version": ".coding.version",
}

def norm(path):
    return path.replace("[]", "")

def match(path, rules):
    np = norm(path)
    best = None
    for rule in rules:
        pref = rule[0]
        if np == pref or np.startswith(pref + ".") or np.startswith(pref + "["):
            if best is None or len(pref) > len(best[0]):
                best = rule
    return best

def refine_element(base, path):
    """Append coding-triple suffix to a CodeableConcept/Coding base element."""
    if not base:
        return base
    last = norm(path).rsplit(".", 1)[-1]
    if last in CODING_SUFFIX and base.split(".")[-1] not in ("coding", "code", "system", "display", "version"):
        # only refine when the base looks like a CodeableConcept target
        if any(tok in base for tok in (".code", "valueCodeableConcept", ".coding", "Condition.code", "Medication.code", "Procedure.code")):
            return base + CODING_SUFFIX[last]
    if last == "date" and base:
        return base  # keep; onset/effective handled per resource in mapper
    return base

def apply(table_file, rules):
    p = MAP / table_file
    with open(p) as f:
        rows = list(csv.DictReader(f))
        fields = rows[0].keys() if rows else []
    filled = 0
    for r in rows:
        if r["status"] not in ("", "TODO"):
            continue
        m = match(r["path"], rules)
        if not m:
            continue
        _, module, profile, base, transform, status = m
        r["mii_module"] = module
        r["mii_profile"] = profile
        r["fhir_element"] = refine_element(base, r["path"]) if module else ""
        r["transform"] = transform
        r["status"] = status
        filled += 1
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fields))
        w.writeheader()
        w.writerows(rows)
    draft = sum(1 for r in rows if r["status"] == "DRAFT")
    nomap = sum(1 for r in rows if r["status"] == "NOMAP")
    todo = sum(1 for r in rows if r["status"] == "TODO")
    print(f"{table_file}: filled {filled} | DRAFT={draft} NOMAP={nomap} TODO={todo} (n={len(rows)})")

def main():
    for tf, rules in TABLES.items():
        apply(tf, rules)

if __name__ == "__main__":
    main()
