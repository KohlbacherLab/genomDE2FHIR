#!/usr/bin/env python3
"""Authoritative research-grounded enrichment of the mapping table, module by module.

This is the *real* build of the central mapping table: each leaf is mapped from
the prior pipeline's per-module MII audits + locked terminology (distilled in
knowledge/genomde-mapping/). It supersedes the earlier prefix-rule draft +
review-fix passes for the leaves it covers.

Keyed by EXACT leaf path. Applies to whichever of the three CSVs contain the
path. status MAPPED = research-grounded; NOMAP = intentionally no clinical KDS
target. notes carries the KG provenance.

Grow MODULES one step at a time (one module per commit). Re-runnable/idempotent.
Run after draft_targets.py + apply_review_fixes.py.
"""
import csv
from pathlib import Path

MAP = Path(__file__).resolve().parent.parent / "mapping"
CSVS = ["mapping_kdk_oncology.csv", "mapping_kdk_rarediseases.csv", "mapping_grz.csv"]

# --- profile canonicals (package-snapshot verified; see knowledge/genomde-mapping) ---
PAT   = "https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/PatientPseudonymisiert"
ENC   = "https://www.medizininformatik-initiative.de/fhir/core/modul-fall/StructureDefinition/KontaktGesundheitseinrichtung"
COVB  = "http://fhir.de/StructureDefinition/coverage-de-basis"
CONS  = "https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-consent-einwilligung"

# value = (module, profile, fhir_element, transform, status, notes)
M = "[[mii-person-fall]]"
MC = "[[mii-consent-med-proc]]"

MODULE_METADATA = {
    "metaData.birthDate": ("Person", PAT, "Patient.birthDate",
        "FHIR date; YYYY-MM is valid — do not pad", "MAPPED", M),
    "metaData.gender": ("Person", PAT, "Patient.gender (+ extension:other-amtlich)",
        "ConceptMap genomDE->administrative-gender; gender-amtlich-de ext (D/X) when gender=other", "MAPPED", M),
    "metaData.addressAGS": ("Person", PAT,
        "Patient.address:Strassenanschrift.city.extension:gemeindeschluessel",
        "AGS Gemeindeschluessel; ext http://fhir.de/StructureDefinition/destatis/ags mounts on address.CITY (P0: not address.extension); valueCoding system urn:oid:1.2.276.0.76.5.474", "MAPPED", M),
    "metaData.localCaseId": ("Person", PAT, "Patient.identifier:pid",
        "local case/patient id; type.coding=MR (v2-0203); also links the per-case Encounter", "MAPPED", M),
    "metaData.tanC": ("Person", PAT, "Patient.identifier:PseudonymisierterIdentifier",
        "tanC pseudonym; type.coding=PSEUDED (v3-ObservationValue) + assigner.identifier; KDK-stream pseudonym — never co-mingle with tanG", "MAPPED", M),
    "metaData.coverageType": ("Fall", COVB, "Coverage.type",
        "-> versicherungsart-de-basis VS; GKV upgrades meta.profile to coverage-de-gkv; SKT->KBV CS, UNK->v3-NullFlavor; guard the 8 valid codes", "MAPPED", M),
    "metaData.molecularBoardDecisionDate": ("Fall", ENC, "Encounter.period.start",
        "MTB decision date; seeds per-case Encounter (class=AMB, status=finished); also MedicationRequest.authoredOn", "MAPPED", M),
    # --- MV consent (mvConsent.scope[] -> Consent.provision.provision[]) ---
    "metaData.mvConsent.scope[].domain": ("Consent", CONS, "Consent.provision.provision.code",
        "domain->broad-consent code: mvSequencing=...24.5.3.8, caseIdentification=...5.3.2, reIdentification=...5.3.6; code.system urn:oid:2.16.840.1.113883.3.1937.777.24.5.3", "MAPPED", MC),
    "metaData.mvConsent.scope[].type": ("Consent", CONS, "Consent.provision.provision.type",
        "permit/deny per inner provision", "MAPPED", MC),
    "metaData.mvConsent.scope[].date": ("Consent", CONS, "Consent.provision.provision.period.start",
        "signature date of this consent scope", "MAPPED", MC),
    "metaData.mvConsent.presentationDate": ("Consent", CONS, "Consent.dateTime",
        "date the MV declaration was presented", "MAPPED", MC),
    "metaData.mvConsent.version": ("Consent", CONS, "Consent.policy.uri",
        "declaration version; policy.uri urn:oid:2.16.840.1.113883.3.1937.777.24.2.2079", "MAPPED", MC),
    # --- research (broad) consent: embedded scope is a full MII Consent ---
    "metaData.researchConsents[].scope": ("Consent", CONS, "(whole Consent resource)",
        "embedded MII Consent — lift VERBATIM as additional Bundle.entry Consent (~27 provisions); passthrough, not field-mapped", "MAPPED", MC),
    "metaData.researchConsents[].presentationDate": ("Consent", CONS, "Consent.dateTime",
        "delivery date of the research consent", "MAPPED", MC),
    "metaData.researchConsents[].noScopeJustification": ("", "", "",
        "justification when no scope present; provenance only, no clinical KDS element", "NOMAP", MC),
    "metaData.researchConsents[].schemaVersion": ("", "", "",
        "consent KDS package version (2025.0.1); metadata, not a mapped element", "NOMAP", MC),
}

MODULES = {
    "metaData (Person/Fall/Coverage/Consent)": MODULE_METADATA,
}

# --- prefix-rule modules (homogeneous coding-triple groups) ---
# (prefix, module, profile, base_element, coding_slice|None, transform, status, notes)
DIAG = "https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose"
ONKO = "https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition"  # + /<profile>
MOLG = "https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition"  # + /<profile>
D = "[[mii-diagnose-onkologie]]"
DL = "[[mii-diagnose-onkologie]] [[fml-codesystem-url-lock]]"

MODULE_DIAG_ONC = [
    # diagnoses -> MII Diagnose Condition (multi-coding on ONE Condition)
    ("case.diagnosisOd.mainDiagnosis", "Diagnose", DIAG, "Condition.code", "icd10-gm",
     "primary oncological diagnosis; ICD-10-GM +version 1..1; SCT/orphanet/alpha-id parallel codings on same Condition", "MAPPED", D),
    ("case.diagnosisOd.additionalDiagnoses", "Diagnose", DIAG, "Condition.code", "icd10-gm",
     "secondary diagnoses; one Condition each, multi-coded", "MAPPED", D),
    ("case.diagnosisOd.germlineDiagnoses", "Diagnose", DIAG, "Condition.code", "icd10-gm",
     "hereditary tumour syndrome (ICD-10-GM Z80*/Z85* + SCT); germline route", "MAPPED", D),
    ("case.diagnosisOd.germlineDiagnosisConfirmed", "Onkologie", ONKO + "/...", "Observation.valueBoolean",
     None, "HT-syndrome confirmed flag (Observation)", "MAPPED", D),
    # oBDS Observations (LOINC + value system locked)
    ("case.diagnosisOd.histology", "Onkologie", ONKO + "/mii-pr-onko-histologie", "Observation.valueCodeableConcept",
     None, "LOINC 59847-4; ICD-O-3 morphology value system urn:oid:2.16.840.1.113883.6.43.1 +version 1..1", "MAPPED", D),
    ("case.diagnosisOd.topography", "Onkologie", ONKO + "/mii-pr-onko-tumorausbreitung", "Observation.valueCodeableConcept",
     None, "LOINC 21861-0 (LOCKED, not 66112-0); ICD-O-3 topography system urn:oid:2.16.840.1.113883.6.43.1 (LOCKED, not .43.2)", "MAPPED", DL),
    ("case.diagnosisOd.grading", "Onkologie", ONKO + "/mii-pr-onko-grading", "Observation.valueCodeableConcept",
     None, "LOINC 33732-9; oBDS Grading OID urn:oid:2.16.840.1.113883.3.7.1.10 or SCT", "MAPPED", D),
    ("case.diagnosisOd.tnmClassifications", "Onkologie", ONKO + "/mii-pr-onko-tnm", "Observation.component.valueCodeableConcept",
     None, "TNM cluster: parent LOINC 21908-9 (UICC OID urn:oid:2.16.840.1.113883.15.16) hasMember T/N/M (c:21905-5/21906-3/21907-1, p:21899-0/21900-6/21901-4)", "MAPPED", D),
    ("case.diagnosisOd.ecogPerformanceStatusScore", "Onkologie", ONKO + "/mii-pr-onko-allgemeiner-leistungszustand-ecog",
     "Observation.valueCodeableConcept", None,
     "LOINC 89247-1; MII ECOG CS codes 0-4(+U) (LOCKED, not LOINC LA); binding mii-vs-onko-allgemeiner-leistungszustand-ecog", "MAPPED", DL),
    ("case.diagnosisOd.diagnosticAssessment", "Onkologie", ONKO + "/...", "Observation.valueCodeableConcept",
     None, "genetic diagnostic evaluation (HT only); verify onko profile", "MAPPED", D),
    ("case.diagnosisOd.additionalClassification", "Onkologie", ONKO + "/...", "Observation",
     None, "other staging classification (key/system, e.g. non-TNM); verify onko profile", "MAPPED", D),
    # phenotype + sequencing-type live under diagnosisOd but belong to MolGen
    ("case.diagnosisOd.hpoTerms", "MolGen", MOLG + "/...phaenotyp", "Observation.valueCodeableConcept",
     None, "HPO Observation; system http://human-phenotype-ontology.org (LOCKED); verify molgen phenotype profile", "MAPPED", DL),
    ("case.diagnosisOd.libraryType", "MolGen", "ServiceRequest", "ServiceRequest.code",
     None, "sequencing type panel/wes/wgs/none; not a diagnosis", "MAPPED", D),
]

# ---- MolGen (molecular) — oncology. genomics-reporting components by LOINC ----
VAR  = MOLG + "/mii-pr-molgen-variante"
CNVP = MOLG + "/mii-pr-molgen-kopienzahlvariante"
SVP  = MOLG + "/mii-pr-molgen-strukturvariante"
G = "[[mii-molgen-biobank]]"
GL = "[[mii-molgen-biobank]] [[fml-codesystem-url-lock]]"

def cmp(slice_, value="valueCodeableConcept"):
    return f"Observation.component:{slice_}.{value}"

MODULE_MOLGEN_ONC = {
    # small variants (mii-pr-molgen-variante)
    "molecular.smallVariants[].identifier": ("MolGen", VAR, "Observation.identifier", "variant id", "MAPPED", G),
    "molecular.smallVariants[].dnaChange": ("MolGen", VAR, cmp("dna-change"), "cHGVS; LOINC 48004-6; HGVS system", "MAPPED", G),
    "molecular.smallVariants[].proteinChange": ("MolGen", VAR, cmp("amino-acid-change"), "pHGVS; LOINC 48005-3", "MAPPED", G),
    "molecular.smallVariants[].ref": ("MolGen", VAR, cmp("genomic-ref-allele", "valueString"), "LOINC 69547-8", "MAPPED", G),
    "molecular.smallVariants[].alt": ("MolGen", VAR, cmp("genomic-alt-allele", "valueString"), "LOINC 69551-0", "MAPPED", G),
    "molecular.smallVariants[].startPosition": ("MolGen", VAR, cmp("exact-start-end", "valueRange.low"), "LOINC 81254-5 Range", "MAPPED", G),
    "molecular.smallVariants[].endPosition": ("MolGen", VAR, cmp("exact-start-end", "valueRange.high"), "LOINC 81254-5 Range", "MAPPED", G),
    "molecular.smallVariants[].chromosome": ("MolGen", VAR, cmp("chromosome"), "LOINC 48000-4; LA codes LL2938-0 (chr1 LA21254-0 ..)", "MAPPED", G),
    "molecular.smallVariants[].genomicSource": ("MolGen", VAR, cmp("genomic-source-class"), "LOINC 48002-0; Somatic LA6684-0 / Germline LA6683-2", "MAPPED", G),
    "molecular.smallVariants[].loh": ("MolGen", VAR, "Observation.component", "loss-of-heterozygosity: no standard genomics-reporting component; candidate genomde CS — DECIDE", "DRAFT", G),
    "molecular.smallVariants[].localization": ("MolGen", VAR, "Observation.component", "variant localization (coding/intronic/...): map to molecular-consequence or RegionStudied — VERIFY", "DRAFT", G),
    # CNV (mii-pr-molgen-kopienzahlvariante)
    "molecular.copyNumberVariants[].identifier": ("MolGen", CNVP, "Observation.identifier", "CNV id", "MAPPED", G),
    "molecular.copyNumberVariants[].cnvType": ("MolGen", CNVP, cmp("variant-type"), "SO:0001019 CNV; gain LA14033-7 / loss LA14034-5; or copy-number LOINC 82155-3", "MAPPED", G),
    "molecular.copyNumberVariants[].chromosome": ("MolGen", CNVP, cmp("chromosome"), "LOINC 48000-4", "MAPPED", G),
    "molecular.copyNumberVariants[].startPosition": ("MolGen", CNVP, cmp("exact-start-end", "valueRange.low"), "LOINC 81254-5", "MAPPED", G),
    "molecular.copyNumberVariants[].endPosition": ("MolGen", CNVP, cmp("exact-start-end", "valueRange.high"), "LOINC 81254-5", "MAPPED", G),
    "molecular.copyNumberVariants[].genomicSource": ("MolGen", CNVP, cmp("genomic-source-class"), "LOINC 48002-0", "MAPPED", G),
    "molecular.copyNumberVariants[].localization": ("MolGen", CNVP, "Observation.component", "VERIFY (see smallVariants.localization)", "DRAFT", G),
    # structural variants / fusions (mii-pr-molgen-strukturvariante)
    "molecular.structuralVariants[].identifier": ("MolGen", SVP, "Observation.identifier", "SV id", "MAPPED", G),
    "molecular.structuralVariants[].genomicSource": ("MolGen", SVP, cmp("genomic-source-class"), "LOINC 48002-0", "MAPPED", G),
    "molecular.structuralVariants[].structureType": ("MolGen", SVP, cmp("variant-type"), "SO variant-type (fusion SO:0001565 etc.)", "MAPPED", G),
    "molecular.structuralVariants[].description": ("MolGen", SVP, cmp("cytogenomic-nomenclature"), "ISCN; LOINC 81291-7; or Observation.note", "MAPPED", G),
    "molecular.structuralVariants[].sequenceType": ("MolGen", SVP, "Observation.component", "DNA/RNA assay type — VERIFY component", "DRAFT", G),
    "molecular.structuralVariants[].localization": ("MolGen", SVP, "Observation.component", "VERIFY (see smallVariants.localization)", "DRAFT", G),
    # expression variants
    "molecular.expressionVariants[].identifier": ("MolGen", VAR, "Observation.identifier", "expression id", "MAPPED", G),
    "molecular.expressionVariants[].expressionType": ("MolGen", VAR, "Observation.valueCodeableConcept", "expression Observation LOINC 82122-3", "MAPPED", G),
    "molecular.expressionVariants[].reference": ("MolGen", VAR, "Observation.component", "expression reference/baseline — VERIFY", "DRAFT", G),
    # complex biomarkers (LOINC)
    "molecular.complexBiomarkers[].identifier": ("MolGen", VAR, "Observation.identifier", "biomarker id", "MAPPED", G),
    "molecular.complexBiomarkers[].tmb": ("MolGen", VAR, "Observation.valueQuantity", "TMB LOINC 94076-7; {count}/Mb", "MAPPED", G),
    "molecular.complexBiomarkers[].hrdHigh": ("MolGen", VAR, "Observation.valueCodeableConcept", "HRD interpretation LOINC 94195-5; Pos LA33381-3 / Neg LA33380-5", "MAPPED", G),
    "molecular.complexBiomarkers[].ploidy": ("MolGen", VAR, "Observation.valueQuantity", "Ploidy LOINC 81303-0", "MAPPED", G),
    "molecular.complexBiomarkers[].lstHigh": ("MolGen", VAR, "Observation.valueBoolean", "LST: no LOINC; https://genomde.de/fhir/CodeSystem/biomarker#LST", "MAPPED", G),
    "molecular.complexBiomarkers[].taiHigh": ("MolGen", VAR, "Observation.valueBoolean", "TAI: no LOINC; https://genomde.de/fhir/CodeSystem/biomarker#TAI", "MAPPED", G),
    # SBS mutational signatures
    "molecular.sbsSignatures[].identifier": ("MolGen", VAR, "Observation.identifier", "signature id", "MAPPED", G),
    "molecular.sbsSignatures[].name[]": ("MolGen", VAR, "Observation.valueCodeableConcept", "SBS signature LOINC 93573-4", "MAPPED", G),
    "molecular.sbsSignatures[].version": ("MolGen", VAR, "Observation.method", "signature catalogue version (COSMIC) — VERIFY", "DRAFT", G),
}

# coding-triple sub-objects of molecular -> gene-studied / transcript / variant-type components
MODULE_MOLGEN_ONC_PREFIX = [
    ("molecular.smallVariants[].gene", "MolGen", VAR, cmp("gene-studied"), None,
     "gene-studied LOINC 48018-6; HGNC http://www.genenames.org (LOCKED, no /geneId)", "MAPPED", GL),
    ("molecular.smallVariants[].transcriptId", "MolGen", VAR, cmp("transcript-ref-seq"), None,
     "transcript-ref-seq LOINC 51958-7; NM_ system http://www.ncbi.nlm.nih.gov/refseq", "MAPPED", G),
    ("molecular.smallVariants[].variantTypes", "MolGen", VAR, cmp("variant-type"), None,
     "SO molecular consequence; system http://www.sequenceontology.org", "MAPPED", G),
    ("molecular.copyNumberVariants[].gene", "MolGen", CNVP, cmp("gene-studied"), None,
     "gene-studied 48018-6; HGNC (LOCKED)", "MAPPED", GL),
    ("molecular.expressionVariants[].gene", "MolGen", VAR, cmp("gene-studied"), None,
     "gene-studied 48018-6; HGNC (LOCKED)", "MAPPED", GL),
    ("molecular.structuralVariants[].geneA", "MolGen", SVP, cmp("gene-studied"), None,
     "fusion partner A; gene-studied 48018-6; HGNC (LOCKED)", "MAPPED", GL),
    ("molecular.structuralVariants[].geneB", "MolGen", SVP, cmp("gene-studied"), None,
     "fusion partner B; gene-studied 48018-6; HGNC (LOCKED)", "MAPPED", GL),
]

# ---- oncology treatment / plan / follow-up (Prozedur, Medikation, CarePlan, Verlauf) ----
OBDSPROC = "http://hl7.org/fhir/de/oncology/StructureDefinition/obds-procedure-systemtherapie"
MEDSTMT  = "https://www.medizininformatik-initiative.de/fhir/core/modul-medikation/StructureDefinition/mii-pr-medikation-medicationstatement"
MEDREQ   = "https://www.medizininformatik-initiative.de/fhir/core/modul-medikation/StructureDefinition/mii-pr-medikation-medicationrequest"
VITAL    = "https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/mii-pr-person-vitalstatus"
P = "[[mii-consent-med-proc]]"
PO = "[[mii-consent-med-proc]] [[mii-diagnose-onkologie]]"
MTB = "[[mtb-evidence-levels]]"

MODULE_ONC_TX = {
    # prior systemic therapies (oBDS Procedure + MedicationStatement chain)
    "case.priorProcedures[].treatmentType": ("Prozedur", OBDSPROC, "Procedure.extension(StellungZurOp)", "oBDS Stellung O/A/N/I/S; ext http://fhir.de/onkologie/StructureDefinition/StellungZurOp", "MAPPED", P),
    "case.priorProcedures[].intention": ("Prozedur", OBDSPROC, "Procedure.extension(Intention)", "oBDS Intention K/P/S/X; ext http://fhir.de/onkologie/StructureDefinition/Intention", "MAPPED", P),
    "case.priorProcedures[].therapyStartDate": ("Prozedur", OBDSPROC, "Procedure.performedPeriod.start", "", "MAPPED", P),
    "case.priorProcedures[].therapyEndDate": ("Prozedur", OBDSPROC, "Procedure.performedPeriod.end", "", "MAPPED", P),
    "case.priorProcedures[].terminationReasonOBDS": ("Prozedur", OBDSPROC, "Procedure.outcome", "SYSTEndegrund http://fhir.de/CodeSystem/onkologie/SYSTEndegrund", "MAPPED", P),
    "case.priorProcedures[].therapyResponse": ("Onkologie", OBDSPROC, "Observation(RECIST).valueCodeableConcept", "RECIST response LOINC 21976-6; referenced via Procedure.report", "MAPPED", PO),
    "case.priorProcedures[].therapyResponseDate": ("Onkologie", OBDSPROC, "Observation(RECIST).effectiveDateTime", "", "MAPPED", PO),
    "case.priorProcedures[].substances[].name": ("Medikation", MEDSTMT, "MedicationStatement.medicationCodeableConcept.text", "substance display", "MAPPED", P),
    # plan: recommended systemic therapies -> MedicationRequest
    "plan.recommendedSystemicTherapies[].identifier": ("Medikation", MEDREQ, "MedicationRequest.identifier", "", "MAPPED", P),
    "plan.recommendedSystemicTherapies[].priority": ("Medikation", MEDREQ, "MedicationRequest.priority", "", "MAPPED", P),
    "plan.recommendedSystemicTherapies[].substances[].name": ("Medikation", MEDREQ, "MedicationRequest.medicationCodeableConcept.text", "substance display", "MAPPED", P),
    "plan.recommendedSystemicTherapies[].type": ("Medikation", MEDREQ, "MedicationRequest.extension(offLabel)", "off-label use type — VERIFY ext", "DRAFT", P),
    "plan.recommendedSystemicTherapies[].therapeuticStrategy": ("Medikation", MEDREQ, "MedicationRequest.note", "therapeutic strategy — no dedicated element", "DRAFT", P),
    "plan.recommendedSystemicTherapies[].evidenceLevel": ("Medikation", MEDREQ, "MedicationRequest.extension(evidenceLevel)", "MTB evidence m1A-m4; genomde extension", "DRAFT", MTB),
    "plan.recommendedSystemicTherapies[].evidenceLevelDetails[]": ("Medikation", MEDREQ, "MedicationRequest.extension(evidenceLevel)", "MTB evidence detail", "DRAFT", MTB),
    "plan.recommendedSystemicTherapies[].variants[]": ("Medikation", MEDREQ, "MedicationRequest.reasonReference", "supporting variant Observation(s)", "DRAFT", P),
    # plan: recommended studies -> ResearchStudy / CarePlan.activity
    "plan.recommendedStudies[].name": ("Onkologie", "ResearchStudy", "ResearchStudy.title", "", "MAPPED", MTB),
    "plan.recommendedStudies[].register": ("Onkologie", "ResearchStudy", "ResearchStudy.identifier.system", "register (NCT/EudraCT/DRKS)", "MAPPED", MTB),
    "plan.recommendedStudies[].id": ("Onkologie", "ResearchStudy", "ResearchStudy.identifier.value", "study id within register", "MAPPED", MTB),
    "plan.recommendedStudies[].identifier": ("Onkologie", "ResearchStudy", "ResearchStudy.identifier", "", "MAPPED", MTB),
    "plan.recommendedStudies[].substances[].name": ("Medikation", MEDREQ, "MedicationRequest.medicationCodeableConcept.text", "study drug display", "MAPPED", P),
    "plan.recommendedStudies[].evidenceLevel": ("Onkologie", "ResearchStudy", "ResearchStudy.extension(evidenceLevel)", "MTB evidence", "DRAFT", MTB),
    "plan.recommendedStudies[].evidenceLevelDetails[]": ("Onkologie", "ResearchStudy", "ResearchStudy.extension(evidenceLevel)", "MTB evidence detail", "DRAFT", MTB),
    "plan.recommendedStudies[].priority": ("Onkologie", "ResearchStudy", "CarePlan.activity.detail", "recommendation priority", "DRAFT", MTB),
    "plan.recommendedStudies[].variants[]": ("Onkologie", "ResearchStudy", "ResearchStudy.extension", "supporting variants", "DRAFT", P),
    # plan: carePlanOd (CarePlan)
    "plan.carePlanOd.molecularBoardDecisionDate": ("Onkologie", "CarePlan", "CarePlan.created", "MTB decision date", "MAPPED", MTB),
    "plan.carePlanOd.studyRecommended": ("Onkologie", "CarePlan", "CarePlan.activity(study).detail.kind", "boolean -> presence of study recommendation activity", "MAPPED", MTB),
    "plan.carePlanOd.counsellingRecommended": ("Onkologie", "CarePlan", "CarePlan.activity(counselling)", "boolean flag", "MAPPED", MTB),
    "plan.carePlanOd.interventionRecommended": ("Onkologie", "CarePlan", "CarePlan.activity(intervention)", "boolean flag", "MAPPED", MTB),
    "plan.carePlanOd.reEvaluationRecommended": ("Onkologie", "CarePlan", "CarePlan.activity(reevaluation)", "boolean flag", "MAPPED", MTB),
    "plan.carePlanOd.otherRecommendations[]": ("Onkologie", "CarePlan", "CarePlan.activity.detail.description", "free-text other recommendation", "DRAFT", MTB),
    "plan.carePlanOd.suitableInterventions[].interventionIsTherapeutic": ("Onkologie", "CarePlan", "CarePlan.activity.detail", "therapeutic flag", "DRAFT", MTB),
    "plan.carePlanOd.suitableInterventions[].interventionsIsRiskReducing": ("Onkologie", "CarePlan", "CarePlan.activity.detail", "risk-reducing flag", "DRAFT", MTB),
    "plan.carePlanOd.suitableInterventions[].type.name": ("Onkologie", "CarePlan", "CarePlan.activity.detail.code.text", "intervention type display", "MAPPED", MTB),
    "plan.preventiveMeasures[].identifier": ("Onkologie", "CarePlan", "CarePlan.activity.reference.identifier", "", "MAPPED", MTB),
    "plan.preventiveMeasures[].type": ("Onkologie", "CarePlan", "CarePlan.activity.detail.code", "preventive measure type", "MAPPED", MTB),
    # follow-up (Verlauf)
    "followUp.followUpOds[].vitalStatus": ("Person", VITAL, "Observation.valueCodeableConcept", "LOINC 67162-8 + MII Vitalstatus CS (L/T/A/N/B/V/X) — LOCKED", "MAPPED", "[[mii-diagnose-onkologie]] [[fml-codesystem-url-lock]]"),
    "followUp.followUpOds[].deathDate": ("Person", PAT, "Patient.deceasedDateTime", "also obds-observation-tod", "MAPPED", M),
    "followUp.followUpOds[].ecogPerformanceStatusScore": ("Onkologie", ONKO + "/mii-pr-onko-allgemeiner-leistungszustand-ecog", "Observation.valueCodeableConcept", "ECOG LOINC 89247-1; MII ECOG CS 0-4 (LOCKED)", "MAPPED", "[[mii-diagnose-onkologie]] [[fml-codesystem-url-lock]]"),
    "followUp.followUpOds[].followUpDate": ("Onkologie", "Observation", "Observation.effectiveDateTime", "follow-up date", "MAPPED", PO),
    "followUp.followUpOds[].lastContactDate": ("Onkologie", "Observation", "Observation.effectiveDateTime", "last contact (Lebenszeichen)", "MAPPED", PO),
    "followUp.followUpOds[].metachroneDiagnoses": ("Diagnose", DIAG, "Condition.code", "metachronous diagnosis -> additional Condition", "DRAFT", PO),
    "followUp.followUpOds[].therapies[].substances[].name": ("Medikation", MEDSTMT, "MedicationStatement.medicationCodeableConcept.text", "substance display", "MAPPED", P),
    "followUp.followUpOds[].therapies[].treatmentType": ("Prozedur", OBDSPROC, "Procedure.extension(StellungZurOp)", "oBDS Stellung", "MAPPED", P),
    "followUp.followUpOds[].therapies[].therapyStartDate": ("Prozedur", OBDSPROC, "Procedure.performedPeriod.start", "", "MAPPED", P),
    "followUp.followUpOds[].therapies[].therapyEndDate": ("Prozedur", OBDSPROC, "Procedure.performedPeriod.end", "", "MAPPED", P),
    "followUp.followUpOds[].therapies[].terminationReasonOBDS": ("Prozedur", OBDSPROC, "Procedure.outcome", "SYSTEndegrund", "MAPPED", P),
    "followUp.followUpOds[].therapies[].therapyResponse": ("Onkologie", OBDSPROC, "Observation(RECIST).valueCodeableConcept", "RECIST 21976-6", "MAPPED", PO),
    "followUp.followUpOds[].therapies[].therapyResponseDate": ("Onkologie", OBDSPROC, "Observation(RECIST).effectiveDateTime", "", "MAPPED", PO),
    "followUp.followUpOds[].therapies[].therapyResponseSource": ("Onkologie", OBDSPROC, "Observation(RECIST).method", "response assessment source", "DRAFT", PO),
    "followUp.followUpOds[].therapies[].reference": ("Onkologie", OBDSPROC, "Procedure.basedOn", "link to recommended therapy", "DRAFT", PO),
    "followUp.followUpOds[].phenotypes[].change": ("MolGen", MOLG + "/...phaenotyp", "Observation.interpretation", "phenotype change (new/improved/worsened)", "DRAFT", G),
    "followUp.followUpOds[].preventiveMeasures[].type": ("Onkologie", "CarePlan", "CarePlan.activity.detail.code", "", "MAPPED", MTB),
    "followUp.followUpOds[].preventiveMeasures[].preventiveMeasureDate": ("Onkologie", "CarePlan", "CarePlan.activity.detail.scheduledDateTime", "", "MAPPED", MTB),
    "followUp.followUpOds[].preventiveMeasures[].preventiveMeasureResult": ("Onkologie", "CarePlan", "CarePlan.activity.outcomeCodeableConcept", "", "DRAFT", MTB),
    "followUp.followUpOds[].preventiveMeasures[].reference": ("Onkologie", "CarePlan", "CarePlan.activity.reference", "", "DRAFT", MTB),
}

MODULE_ONC_TX_PREFIX = [
    ("case.priorProcedures[].substances[].code", "Medikation", MEDSTMT, "MedicationStatement.medicationCodeableConcept", "atc",
     "ATC http://fhir.de/CodeSystem/bfarm/atc +version; one MedicationStatement (status=completed) per substance, Procedure.usedReference", "MAPPED", P),
    ("plan.recommendedSystemicTherapies[].substances[].code", "Medikation", MEDREQ, "MedicationRequest.medicationCodeableConcept", "atc",
     "ATC http://fhir.de/CodeSystem/bfarm/atc; real code (not placeholder)", "MAPPED", P),
    ("plan.recommendedStudies[].substances[].code", "Medikation", MEDREQ, "MedicationRequest.medicationCodeableConcept", "atc",
     "study drug ATC", "MAPPED", P),
    ("plan.carePlanOd.suitableInterventions[].type.code", "Onkologie", "CarePlan", "CarePlan.activity.detail.code", None,
     "intervention type (OPS/own coding)", "MAPPED", MTB),
    ("followUp.followUpOds[].therapies[].substances[].code", "Medikation", MEDSTMT, "MedicationStatement.medicationCodeableConcept", "atc",
     "ATC; administered therapy", "MAPPED", P),
    ("followUp.followUpOds[].additionalDiagnoses", "Diagnose", DIAG, "Condition.code", "icd10-gm",
     "new diagnoses at follow-up; multi-coded Condition", "MAPPED", D),
    ("followUp.followUpOds[].phenotypes", "MolGen", MOLG + "/...phaenotyp", "Observation.valueCodeableConcept", None,
     "HPO at follow-up; system http://human-phenotype-ontology.org (LOCKED)", "MAPPED", GL),
]

PREFIX_MODULES = {
    "case.diagnosisOd (Diagnose/Onkologie)": MODULE_DIAG_ONC,
    "molecular (MolGen) — oncology": MODULE_MOLGEN_ONC_PREFIX,
    "oncology treatment/plan/followUp": MODULE_ONC_TX_PREFIX,
}

MODULES["molecular (MolGen) — oncology"] = MODULE_MOLGEN_ONC
MODULES["oncology treatment/plan/followUp"] = MODULE_ONC_TX

CC_PARTS = ("code", "system", "display", "version")

def norm(p):
    return p.replace("[]", "")

def refine_element(base, slice_, path):
    seg = norm(path).rsplit(".", 1)[-1]
    if base.startswith("Condition") and seg == "date":
        return "Condition.recordedDate"
    if seg == "text":
        if base.endswith("component.valueCodeableConcept"):
            return base[: -len(".valueCodeableConcept")] + ".valueString"
        if base.endswith(("CodeableConcept", ".code", ".bodySite")):
            return base + ".text"
        return base
    if seg in CC_PARTS and base.endswith(("CodeableConcept", ".code", ".bodySite")):
        cod = f".coding:{slice_}" if slice_ else ".coding"
        return base + cod + "." + seg
    return base

def match_prefix(path, rules):
    np = norm(path)
    best = None
    for r in rules:
        pref = norm(r[0])
        if np == pref or np.startswith(pref + "."):
            if best is None or len(pref) > len(norm(best[0])):
                best = r
    return best

def apply():
    tables = {tf: list(csv.DictReader(open(MAP / tf))) for tf in CSVS}
    fields = {tf: list(rows[0].keys()) for tf, rows in tables.items() if rows}
    total = 0
    for mod_name, mod in MODULES.items():
        hit = 0
        for tf, rows in tables.items():
            for r in rows:
                if r["path"] in mod:
                    module, profile, elem, tr, st, notes = mod[r["path"]]
                    r["mii_module"], r["mii_profile"], r["fhir_element"] = module, profile, elem
                    r["transform"], r["status"], r["notes"] = tr, st, notes
                    hit += 1
        print(f"  module '{mod_name}': {hit} rows enriched")
        total += hit
    for mod_name, rules in PREFIX_MODULES.items():
        hit = 0
        for tf, rows in tables.items():
            for r in rows:
                m = match_prefix(r["path"], rules)
                if not m:
                    continue
                _, module, profile, base, slice_, tr, st, notes = m
                r["mii_module"], r["mii_profile"] = module, profile
                r["fhir_element"] = refine_element(base, slice_, r["path"]) if module else ""
                r["transform"], r["status"], r["notes"] = tr, st, notes
                hit += 1
        print(f"  prefix-module '{mod_name}': {hit} rows enriched")
        total += hit
    for tf, rows in tables.items():
        with open(MAP / tf, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields[tf])
            w.writeheader()
            w.writerows(rows)
    # report MAPPED coverage
    for tf, rows in tables.items():
        c = {}
        for r in rows:
            c[r["status"]] = c.get(r["status"], 0) + 1
        print(f"  {tf}: " + " ".join(f"{k}={v}" for k, v in sorted(c.items())))
    print(f"total enriched: {total}")

if __name__ == "__main__":
    apply()
