1. RD Rows Wrong Vs SE Model
1. `case.diagnosisRd.diagnosticAssessment` -> current: mixed enum to `Condition.verificationStatus` -> should-be: exact SE map `noGeneticDiagnosis|geneticSuspectedDiagnosis|clinicalPhenotypeOnlyPartiallyResolved|geneticDiagnosisConfirmed` -> `unconfirmed|provisional|partial|confirmed`; `furtherGeneticDiagnosticRecommended` unresolved -> why: current uses non-SE codes and maps nonexistent source values.
2. `followUp.followUpRds[].followUpDate` -> current: `Observation.effectiveDateTime` -> should-be: Follow-Up/Encounter date -> why: SE Follow-Up is Encounter-like and records the follow-up date only.
3. `followUp.followUpRds[].diagnosisEstablished` -> current: boolean to `Condition.verificationStatus=confirmed` -> should-be: derived from genetic verification status `!= unconfirmed` -> why: current overwrites `provisional`/`partial`/`confirmed` distinction.
4. `case.priorRds[].hospitalizationDuration|hospitalizationPeriods` -> current: `Encounter.length|Encounter.period` -> should-be: aggregate coded hospitalization days/count bands -> why: SE crossed out period/duration and uses total-count/total-days value sets.
5. `case.priorRds[].diagnosticDate|diagnosticResult` -> current: `mii-pr-molgen-variante` with `DiagnosticReport.*` elements -> should-be: MolGen/SE sequencing `DiagnosticReport.effective[x]|conclusion` -> why: variant profile is an Observation, not a report.
6. `followUp.followUpRds[].phenotypes[].change` -> current: camelCase `newlyAdded|noLongerObserved`, `abated->noLongerObserved` -> should-be: MII codes `newly-added|no-longer-observed`, SE status history `improved|degraded|abated|unchanged` plus date -> why: current code forms do not match SE/MII value sets.
7. `case.diagnosisRd.diagnoses[]` -> current: bare core Diagnose `Condition.code.coding.*` -> should-be: SE ClinicalDiagnosis/GeneticDiagnosis profile with ORDO + ICD-10-GM + Alpha-ID-SE codings including versions -> why: SE requires all three coded systems where available.
8. `case.diagnosisRd.noMatchingCodeExists` -> current: boolean to `Condition.code.extension(data-absent-reason)` -> should-be: explicit coded missing reason `no-matching-code` when any required diagnosis coding is absent -> why: SE defines a code, not a bare boolean.
9. `case.diagnosisRd.libraryType|case.priorRds[].genomicTestType` -> current: generic `ServiceRequest.code` with source enum values -> should-be: SE NGS report type codes normalized to canonical hyphenated codes; `none` handled separately -> why: current value-set mapping is incomplete.
10. `case.diagnosisRd.diagnosticExtent|case.priorRds[].genomicStudyType` -> current: generic `ServiceRequest.code`, one prior value hardcoded -> should-be: SE family-control codes `single-genome|duo-genome|trio-genome` from actual source -> why: hardcoded/generic mapping violates SE cardinality and semantics.
11. `plan.carePlanRd.clinicalManagementDescriptions[]` -> current: `CarePlan.activity.detail.description` -> should-be: coded ClinicalManagementRecommendation type plus notes -> why: SE row is a coded recommendation, not free text.
12. `followUp.followUpRds[].diseaseProgression` -> current: DRAFT `Observation.valueCodeableConcept` -> should-be: diagnosis notes / `Condition.note` string `0..N` -> why: SE models progression as supplementary disease-course text.

2. Mapped Rows That Should Be Draft
1. `case.diagnosisRd.diagnosticExtent` -> MAPPED -> DRAFT -> generic `ServiceRequest.code`; no verified Seltene/MolGen target profile.
2. `case.diagnosisRd.libraryType` -> MAPPED -> DRAFT -> generic `ServiceRequest.code`; `none` and no-sequencing semantics unresolved.
3. `case.priorRds[].genomicStudyType|genomicTestType` -> MAPPED -> DRAFT -> generic `ServiceRequest.code`; target profile and value-set normalization unverified.
4. `case.diagnosisRd.molecularBoardDecisionDate` -> MAPPED -> DRAFT -> generic `CarePlan.created`; board type/SE therapyplan target unverified.
5. `plan.carePlanRd.molecularBoardDecisionDate` -> MAPPED -> DRAFT -> generic `CarePlan.created`; conflates indication-board vs therapy-board.
6. `plan.carePlanRd.{clinicalManagementRecommended,counsellingRecommended,reEvaluationRecommended,studyRecommended,therapyRecommended}` -> MAPPED -> DRAFT -> pseudo `CarePlan.activity(...)`; Seltene therapyplan expects referenced recommendation resources.
7. `plan.recommendedStudies[].{id,identifier,name,register}` -> MAPPED -> DRAFT -> generic `ResearchStudy`; should verify `mii-pr-seltene-studie` plus Studieneinschluss-Anfrage `ServiceRequest`.
8. `plan.recommendedTherapies[].identifier` -> MAPPED -> DRAFT -> generic `MedicationRequest`; should verify Seltene medication/non-medication/combination therapy recommendation profiles.

3. Top RD Open Issues
1. Decide explicit split between SE ClinicalDiagnosis and GeneticDiagnosis profiles for diagnosis rows and genetic evidence links.
2. Define board model: indication-board vs therapy-board, recording date, no-sequencing reason, and recommendation ownership.
3. Define canonical GMFCS target, code system, date handling, and initial vs follow-up observation behavior.
4. Define valid FHIR target for aggregate hospitalization count/day bands without using encounter periods.
5. Define prior-diagnostics target as MolGen/SE report/request bundle, including empty prior report and `none` handling.
6. Define study recommendation mapping through Seltene Studieneinschluss-Anfrage, not ResearchStudy alone.
7. Define therapy recommendation split across medication, non-medication, and combination profiles with category/type/supporting variants.
8. Resolve `furtherGeneticDiagnosticRecommended`: no direct SE `Condition.verificationStatus` target.
