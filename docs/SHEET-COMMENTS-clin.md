# Reviewer comments from the mapping Google Sheet

Ingested 14 cell comments (all by Lucien Clin, DNPM model author) and
attached to the matching `notes` in the mapping CSVs. Re-run `python3 scripts/ingest_sheet_comments.py`.

### [KDK oncology] `case.diagnosisOd.germlineDiagnosisConfirmed`
- cell `fhir_element` = `Observation.valueBoolean`
- **Lucien Clin:** I'd say that's wrong: The germline diagnosis ICD-10 codes map to Condition.code. This attribute corresponds to Condition.verificationStatus: https://hl7.org/fhir/condition-definitions.html#Condition.verificationStatus

### [KDK oncology] `case.diagnosisOd.histology.code`
- cell `fhir_element` = `Condition.extension(mii-ex-onko-histology-morphology-behavior-icdo3)`
- **Lucien Clin:** Why represent this as an extension on Condition, when e.g. TNM-Grading above is represented as an Observation. ICD-O-3-Morphology is also a finding resulting from histology, i.e. Observation.

### [KDK oncology] `case.diagnosisOd.tnmClassifications[].code`
- cell `fhir_element` = `Observation.hasMember -> T/N/M category Observations`
- **Lucien Clin:** Why represent the triple of conceps T,N,M as mutltiple Observation, instead of one composite Observation, i.e. as one Observation with 3 entries underObservation.component?

### [KDK oncology] `case.priorDiagnostics[].date`
- cell `fhir_element` = `Condition.recordedDate`
- **Lucien Clin:** I'd say that's wrong: should rather be DiagnosticReport.issued

### [KDK oncology] `case.priorDiagnostics[].type`
- cell `fhir_element` = `DiagnosticReport`
- **Lucien Clin:** Unprecise: DiagnosticReport.code

### [KDK oncology] `case.priorProcedures[].terminationReasonOBDS`
- cell `fhir_element` = `Procedure.outcome`
- **Lucien Clin:** I'd say that's wrong: The comment mentions "systemic therapies", so this object maps to MedicationStatement, and this attribute to MedicationStatement.statusReason: https://hl7.org/fhir/R4/medicationstatement-definitions.html#MedicationStatement.statusReason

### [KDK oncology] `case.priorProcedures[].treatmentType`
- cell `fhir_element` = `Procedure.extension(StellungZurOp)`
- **Lucien Clin:** See above: systemic therapy maps to MedicationStatement

### [KDK oncology] `followUp.followUpOds[].followUpDate`
- cell `fhir_element` = `Observation.effectiveDateTime`
- **Lucien Clin:** I'd say that's wrong: The follow-up (FU) object itself is not an Observation, but should rather be represented as an Encounter (with .class = virtual?). So the FU date maps to Encounter.period.start

### [KDK oncology] `followUp.followUpOds[].therapies[].terminationReasonOBDS`
- cell `fhir_element` = `Procedure.outcome`
- **Lucien Clin:** See above. systemic therapy is MedicationStatement, not Procedure

### [KDK oncology] `metaData.gender`
- cell `fhir_element` = `Patient.gender (+ extension:other-amtlich)`
- **Lucien Clin:** What's the need of this extension: the value set here (see at left) is already exactly FHIR AdministrativeGender: https://hl7.org/fhir/R4/valueset-administrative-gender.html

### [KDK oncology] `metaData.rejectionJustification`
- cell `fhir_element` = `None`
- **Lucien Clin:** I'd argue that this MUST be recorded as a decision on the CarePlan object of the indication board, why no sequencing is needed/requested: CarePlan.activity.detail.reasonCode

### [KDK oncology] `plan.carePlanOd.reEvaluationRecommended`
- cell `fhir_element` = `CarePlan.activity(reevaluation)`
- **Lucien Clin:** I'd argue that these pure boolean attributes are not required to be mapped in FHIR: if study inclusion recommendation objects occur with the CarePlan, then it obviously" studyRecommended = true, else false.

### [KDK oncology] `plan.recommendedStudies[].register`
- cell `fhir_element` = `ResearchStudy.identifier.system`
- **Lucien Clin:** Id argue that's wrong: resource ResearchStudy represents the definition/registration of a study. Here, however, it is a recommendation/request that the patient be included in a given study that must be represented. Thus, this should rather be represented e.g. as ServiceRequest with type "study inclusion" and containing a _Reference_ to the ResearchStudy

### [KDK rare diseases] `case.diagnosisRd.diagnosticAssessment`
- cell `fhir_element` = `Condition.verificationStatus`
- **Lucien Clin:** Strictly speaking, that's not fully correct: the values no_, suspected_ or confirmedGeneticDiagnosis correspond to Condition.verificationStatus values. BUT value "furtherGeneticDiagnosticRecommended" is _not_ a verification status, is it a recommendation/request that further diagnostics be performed. This must thus be represented as part of a CarePlan/ServiceRequest.
