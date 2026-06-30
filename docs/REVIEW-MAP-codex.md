1. `mappers/python/genomde_to_fhir.py:map_oncology; mappers/fml/*:all -> 166 MAPPED rows collapse to 11 sample resources; molecular rows are absent -> add MTB Observations for small variants, CNVs, fusions, RNA-seq, HRD/TMB/ploidy/biomarkers per mapping_kdk_oncology.csv.`

2. `mappers/fml/DatenkranzOncology.logical.json:elements -> logical model omits most MAPPED source paths, so FML cannot map them -> expand logical model before claiming FML coverage.`

3. `mappers/python/genomde_to_fhir.py:TODO; mappers/fml:all -> CarePlan/recommendedStudies/recommendedSystemicTherapies/studyInclusion MAPPED rows are not emitted -> create CarePlan/request/therapy recommendation resources per table.`

4. `mappers/python/genomde_to_fhir.py:diagnosis/followUp; mappers/fml:CaseBlock/FollowUpBlock -> TNM, grading, HPO phenotypes, germline diagnoses, follow-up diagnoses/therapies are MAPPED but missing -> emit the mapped Conditions/Observations/Procedures/MedicationStatements.`

5. `mappers/fml/genomde-oncology-to-mii.map:main -> /tmp/sample_fml_bundle.json is an invalid transaction Bundle: no entry.fullUrl and no entry.request -> set stable fullUrl and Bundle.entry.request.method/url for every entry.`

6. `mappers/fml/genomde-oncology-to-mii.map:references -> FML sample drops subject/patient/beneficiary references; MII profiles require e.g. Observation.subject 1..1, Consent.patient 1..1 -> fix reference() materialization and regression-test sample output.`

7. `mappers/python/genomde_to_fhir.py:P["consent"]; mappers/fml:Consent -> wrong Consent canonical includes core/modul-consent -> use https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-consent-einwilligung.`

8. `mappers/python/genomde_to_fhir.py:Consent; mappers/fml:Consent -> MV consent semantics are wrong/incomplete: category slices, policy OID, provision OID code system/codes, periods, and researchConsents[].scope passthrough are missing or wrong -> implement MII Consent.category, Consent.policy.uri, Consent.provision.provision.code, period.start, and lift embedded scope Consent resources verbatim.`

9. `mappers/python/genomde_to_fhir.py:Patient; mappers/fml:Patient -> TAN/local identifiers miss Patient.identifier:PseudonymisierterIdentifier.type.coding=PSEUDED -> add the required identifier type slice coding.`

10. `mappers/python/genomde_to_fhir.py:VitalStatus; mappers/fml:VitalStatus -> copies living/deceased into MII Vitalstatus, but allowed codes are L/T/A/N/B/V/X; category:survey also missing -> map living->L, deceased->T and add Observation.category:survey.`

11. `mappers/python/genomde_to_fhir.py:ECOG; mappers/fml:ECOG -> ECOG values are passed through, so 5/unknown/notApplicable become invalid; FML also omits required Observation.code.coding:snomed=423740007 -> normalize to MII ECOG codes 0-4/U or reject, and add SNOMED coding.`

12. `mappers/python/genomde_to_fhir.py:PrimaryDiagnosis; mappers/fml:PrimaryDiagnosis -> ICD-O-3 histology/topography systems are passed through from source OIDs; mapping table expects http://terminology.hl7.org/CodeSystem/icd-o-3, and FML omits histology extension entirely -> canonicalize systems and emit histology/topography slices consistently.`

13. `mappers/python/genomde_to_fhir.py:PriorProcedure; mappers/fml:PriorProcedure -> treatmentType/intention/terminationReasonOBDS/therapyResponse/therapyResponseDate are MAPPED but dropped -> populate Procedure.extension:StellungZurOp, Procedure.extension:Intention, Procedure.outcome, and MTB response Observation.`

14. `mappers/fml/genomde-oncology-to-mii.map:MedicationStatement -> FML MedicationStatement lacks required MII elements MedicationStatement.partOf, subject, and effective[x] -> link to Procedure, set patient subject, and carry therapyStart/therapyEnd into effectivePeriod.`

15. `mappers/python/genomde_to_fhir.py:Coverage; mappers/fml:Coverage -> Coverage is profile-poor/invalid: Python uses patient as payor, FML sample has null payor and no beneficiary/profile -> map coverage type to the intended MII Coverage profile, beneficiary, identifier, and real payor/display.`
