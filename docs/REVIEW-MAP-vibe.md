mappers/python/genomde_to_fhir.py:Patient.identifier -> tanC missing type.coding with PSEUDED (v3-ObservationValue) per mapping_kdk_oncology.csv row 126 -> add type={"coding":[{"system":"http://terminology.hl7.org/CodeSystem/v3-ObservationValue","code":"PSEUDED"}]}
mappers/python/genomde_to_fhir.py:Patient.identifier -> localCaseId not emitted as identifier:pid with type=MR per row 108 -> add identifier with system urn:local:case-id, type={"coding":[{"system":"http://terminology.hl7.org/CodeSystem/v2-0203","code":"MR"}]}
mappers/python/genomde_to_fhir.py:Condition.code.coding.system -> mainDiagnosis using OID urn:oid:2.16.840.1.113883.6.43.1 instead of required http://fhir.de/CodeSystem/bfarm/icd-10-gm per row 27 -> fix cc() default_system for ICD-10-GM
mappers/python/genomde_to_fhir.py:Condition.bodySite.coding.system -> topography using OID instead of required http://terminology.hl7.org/CodeSystem/icd-o-3 per rows 37-40 -> override default_system in bodySite call
mappers/python/genomde_to_fhir.py:Consent.provision -> missing provision.provision[].period.start from mvConsent.scope[].date (row 111) -> add period={"start": sc.get("date")} to each ConsentProvision
mappers/python/genomde_to_fhir.py:Consent.provision.provision[].code.system -> domain codes must use urn:oid:2.16.840.1.113883.3.1937.777.24.5.3 per row 112 -> override code system in provision code
mappers/python/genomde_to_fhir.py:Observation (ECOG) -> code missing SNOMED CT 423740007 coding per row 10 -> add {"system":"http://snomed.info/sct","code":"423740007"} to ecog_obs code
mappers/fml/genomde-oncology-to-mii.map:Patient -> tanC missing type.coding=PSEUDED per row 126 -> add identifier.type coding in TanIdentifier group
mappers/fml/genomde-oncology-to-mii.map:Patient -> localCaseId not mapped to identifier:pid per row 108 -> add group for localCaseId identifier
mappers/fml/genomde-oncology-to-mii.map:Coverage -> missing beneficiary reference per row 105 -> add cov.beneficiary = reference(pat) in Coverage group
mappers/fml/genomde-oncology-to-mii.map:Coverage -> payor is null instead of reference(pat) -> fix cov-payor to use valid reference
mappers/fml/genomde-oncology-to-mii.map:Consent -> missing category per row 121 -> add con.category coding LOINC 57016-8
mappers/fml/genomde-oncology-to-mii.map:Consent.provision -> missing provision.provision[].period.start from scope[].date (row 111) -> add period.start mapping in Consent group
mappers/fml/genomde-oncology-to-mii.map:Consent.provision.provision[].code.system -> must be urn:oid:2.16.840.1.113883.3.1937.777.24.5.3 per row 112 -> fix code.system in consent scope mapping
mappers/fml/genomde-oncology-to-mii.map:Condition -> missing subject reference per mapping implication -> add cond.subject = reference(pat) in PrimaryDiagnosis and AdditionalDx groups
mappers/fml/genomde-oncology-to-mii.map:Condition.bodySite -> system must be http://terminology.hl7.org/CodeSystem/icd-o-3 per row 37 -> fix Coding group for topography
mappers/fml/genomde-oncology-to-mii.map:Condition.code -> mainDiagnosis must use http://fhir.de/CodeSystem/bfarm/icd-10-gm per row 27 -> fix Coding group for mainDiagnosis
mappers/fml/genomde-oncology-to-mii.map:Observation (ECOG) -> missing subject reference and SNOMED code -> add obs.subject = reference(pat) and code.coding SNOMED 423740007 in Ecog group
mappers/fml/genomde-oncology-to-mii.map:Observation (VitalStatus) -> missing subject reference -> add obs.subject = reference(pat) in VitalStatus group
mappers/fml/genomde-oncology-to-mii.map:Procedure -> missing subject reference -> add proc.subject = reference(pat) in PriorProcedure group
mappers/fml/genomde-oncology-to-mii.map:MedicationStatement -> missing subject reference -> add ms.subject = reference(pat) in PriorMedication group
mappers/python/genomde_to_fhir.py:Consent.policy.uri -> value should be OID urn:oid:2.16.840.1.113883.3.1937.777.24.2.2079 per row 114, not raw string -> validate and convert policy.uri to OID
mappers/python/genomde_to_fhir.py:Observation (VitalStatus) -> value system using Vitalstatus instead of locked MII CS per row 102 -> use https://www.medizininformatik-initiative.de/fhir/core/modul-person/CodeSystem/Vitalstatus
mappers/fml/genomde-oncology-to-mii.map:Coverage -> payor[0] is null literal, not reference(pat) -> fix to proper reference syntax
mappers/python/genomde_to_fhir.py:Condition.code.coding.version -> ICD-10-GM version should be present per row 31 -> ensure version is passed through in cc()
mappers/fml/genomde-oncology-to-mii.map:Observation (ECOG) -> code missing second coding SNOMED 423740007 per row 10 -> add second coding to ecog-code rule
mappers/python/genomde_to_fhir.py:Coverage.type.coding -> system must be http://fhir.de/CodeSystem/versicherungsart-de-basis per row 105, but no code validation against valid set -> add guard for 8 valid codes (GKV/PKV/BG/SEL/SOZ/GPV/PPV/BEI/SKT/UNK)
mappers/fml/genomde-oncology-to-mii.map:Condition -> bodySite coding for topography using OID urn:oid:2.16.840.1.113883.6.43.2 instead of http://terminology.hl7.org/CodeSystem/icd-o-3 per rows 37-40 -> fix system in topo Coding group
mappers/fml/genomde-oncology-to-mii.map:MedicationStatement -> partOf missing in FML, Python has it -> add ms.partOf = reference(proc) in PriorMedication group
mappers/python/genomde_to_fhir.py:Procedure.performedPeriod -> FML maps therapyStartDate to performed (Period) but Python uses performedPeriod correctly -> no issue, FML needs fix to use performedPeriod
mappers/fml/genomde-oncology-to-mii.map:Procedure.performed -> using performed (Period) but should be performedPeriod per FHIR R4 -> change performed to performedPeriod in PriorProcedure group
