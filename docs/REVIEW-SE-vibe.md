(1) **WRONG vs SE model**
case.diagnosisRd.diagnoses[].system → `http://fhir.de/CodeSystem/bfarm/alpha-id` → should-be `http://fhir.de/CodeSystem/bfarm/alpha-id-se` → SE model requires AlphaID-SE CS (rows 2–5)
case.diagnosisRd.diagnoses[].code/system/version → implies ORDO+ICD-10-GM+AlphaID optional → should-be ALL THREE required unless noMatchingCodeExists → SE validator enforces triple-coding (rows 2–5, 11)
case.diagnosisRd.diagnosticAssessment → uses `furtherGeneticDiagnosticRecommended` enum value → should-be removed → no DNPM source can emit this value (row 7)
case.diagnosisRd.diagnosisGmfcs → single Observation.valueCodeableConcept → should-be repeating effective-dated Observation with GMFCS CodeSystem → SE GMFCSStatus is temporal (row 6)
followUp.followUpRds[].gmfcs → same single Observation issue → same GMFCS CodeSystem + repeating requirement (row 29)
case.diagnosisRd.molecularBoardDecisionDate → maps to Encounter.period.start → should-be indicationCarePlan.issuedOn (INDICATION board) → conflates two distinct board dates (row 10)
plan.carePlanRd.molecularBoardDecisionDate → maps to CarePlan.created → should-be latest careplan.issuedOn (MOLECULAR board) → distinct from case-level date (row 119)
case.priorRds[].genomicStudyType → trusted enum → should-be flagged unreliable → upstream hard-coded to `single` (row 20)
case.priorRds[].hospitalizationPeriods → `moreThanFifteen` → should-be `moreThanFifteen` matches but cardinality note: SE models as count of Hospitalization objects, not banded enum (row 23)
case.priorRds[].hospitalizationDuration → `moreThanFifty` → same banded vs count concern (row 22)

(2) **MAPPED but should be DRAFT (unverified target)**
molecular.copyNumberVariants[].localization[].code → Observation.component without verified component path → component path unclear in MolGen IG (row 72)
molecular.smallVariants[].localization[].code → Observation.component:transcript-ref-seq.valueCodeableConcept.coding.code → verify component exists in mii-pr-molgen-variante (row 92)
molecular.structuralVariants[].localization[].code → Observation.component,localization → same verification needed (row 110)
molecular.*.diagnosticSignificance → Observation.note → moved off 53037-8 to avoid ACMG collision but no canonical component confirmed (rows 66, 86, 105)
molecular.*.segregationAnalysis → Observation.note → no canonical component; verify profile binding (rows 76, 97, 114)
molecular.*.publications[] → Observation.derivedFrom / extension(PMID) → no MII canonical for PMID references (rows 75, 95, 113)
plan.recommendedTherapies[].strategy → MedicationRequest.note → no MII RD recommendation profile; verify target path (row 129)
plan.recommendedTherapies[].type → MedicationRequest.extension(offLabel) → no MII RD profile confirmed (row 132)
plan.carePlanRd.clinicalManagementDescriptions[] → CarePlan.activity.detail.description → verify against mii-pr-seltene-therapieempfehlung slice (row 116)

(3) **Top RD open issues**
AlphaID-SE vs AlphaID code system mismatch: mapping emits `bfarm/alpha-id` but SE requires `bfarm/alpha-id-se`; MII Seltene IG uses non-SE URL
EpisodeOfCare vs Encounter: SE models Fall as EpisodeOfCare; MII Fall is Encounter only; board dates map to two different semantic objects
Recommendation profiles: need to replace generic CarePlan/ServiceRequest/ResearchStudy/MedicationRequest with concrete MII RD profiles (mii-pr-seltene-therapieempfehlung, -studieneinschluss-anfrage)
GMFCS canonical: no MII/DNPM CodeSystem; must declare local CS + model as repeating effective-dated Observation
priorRds.genomicStudyType hard-coded to `single` upstream — unreliable source value
Triple-coding enforcement: Diagnosis requires ICD-10-GM AND ORPHA AND AlphaID-SE, else noMatchingCodeExists; current mapping implies optional
