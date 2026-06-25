Followed `docs/REVIEW-BRIEF-3.md`; ranked highest-impact first.

**Ranked Issues**
1. `mapping/mapping_kdk_rarediseases.csv:7 case.diagnosisRd.diagnosticAssessment` -> current: `Onkologie` + placeholder profile + `MAPPED` -> issue: invented/unverified canonical, wrong module -> fix: mark `DRAFT`; map to verified Diagnose/SE status semantics.
2. `mapping/mapping_kdk_rarediseases.csv:61-115 molecular.*Variants` -> current: `mii-pr-molgen-*` canonicals `MAPPED` -> issue: these exact URLs were not found in crawled MII IGs; MolGen canonical validity is not proven -> fix: verify against pinned MolGen package or switch to crawled canonical; otherwise `DRAFT`.
3. `mapping/mapping_kdk_oncology.csv:177-185 structuralVariants[].geneA/geneB` -> current: `component:gene-studied` -> issue: fusion profiles distinguish `five-prime-gene` / `three-prime-gene`; orientation is lost -> fix: map A/B only with explicit 5-prime/3-prime rule, otherwise `DRAFT`.
4. `mapping/mapping_kdk_oncology.csv:133,155`; `mapping/mapping_kdk_rarediseases.csv:65,85` -> current: `component:chromosome` -> issue: crawled MTB/MolGen-derived profiles use `component:chromosome-identifier` -> fix: replace element path.
5. `mapping/mapping_kdk_oncology.csv:76 followUp.*.ecogPerformanceStatusScore` -> current: `LOINC 89247-1` -> issue: current MII Onko ECOG uses SNOMED `423740007` and optional LOINC `89262-0`; row contradicts IG and row 10 -> fix: use SNOMED + optional `89262-0`; value from MII ECOG CS.
6. `mapping/mapping_kdk_oncology.csv:16 diagnosisGrading` -> current: oBDS grading OID or SCT -> issue: MII grading value set is `mii-cs-onko-grading`; code also includes SNOMED `371469007` -> fix: use MII grading CS value, code `33732-9` + `371469007`.
7. `mapping/mapping_kdk_rarediseases.csv:22-24` -> current: profile `EpisodeOfCare` but `Encounter.*` paths -> issue: resource/profile mismatch; MII Fall is Encounter, DNPM SE episode is separate -> fix: model DNPM `EpisodeOfCare` explicitly or use MII Encounter profile, not both.
8. `mapping/mapping_kdk_rarediseases.csv:6,29 GMFCS` -> current: bare `Observation`, `MAPPED` -> issue: no verified MII canonical; DNPM has effective-dated repeating GMFCS semantics -> fix: `DRAFT`; define local profile/CS and earliest/pre-follow-up selection rules.
9. `mapping/mapping_grz.csv:5-9,11-12,16-19,38-40` -> current: bare `Device`, `MAPPED` -> issue: no MII Device profile found in crawl; lab kit/software/sequencer metadata target is unproven -> fix: `DRAFT` or map through verified MolGen analysis/device structure.
10. `mapping/mapping_kdk_oncology.csv:86-89,109,191-205`; `mapping/mapping_kdk_rarediseases.csv:10,116-122` -> current: generic `CarePlan`, mostly `MAPPED` -> issue: ignores concrete Tumorkonferenz/MTB recommendation semantics and RD first/latest careplan split -> fix: use verified Onko/MTB profiles or downgrade.
11. `mapping/mapping_kdk_rarediseases.csv:8-9,20-21`; `mapping/mapping_kdk_oncology.csv:26` -> current: generic `ServiceRequest`, `MAPPED` -> issue: no profile canonical; row 20 admits hardcoded upstream assumption -> fix: verify MolGen request/genomic-study target or mark `DRAFT`.
12. `mapping/mapping_kdk_oncology.csv:67,99` -> current: Procedure profile with `Observation(RECIST).effectiveDateTime` -> issue: element path is not on target profile -> fix: create/link response/Verlauf Observation and put date there.
13. `mapping/mapping_grz.csv:41-44 tissueOntology` -> current: BTO-only `Specimen.type`, `MAPPED` -> issue: Biobank profile expects SNOMED slice; note already flags MIIUP-04 risk -> fix: require SCT translation, keep BTO as additional coding, or `DRAFT`.
14. `mapping/mapping_grz.csv:52 donors[].relation` -> current: bare `FamilyMemberHistory`, `MAPPED` -> issue: unprofiled; Seltene/MolGen family-history profiles exist -> fix: use verified Familienanamnese profile or downgrade.
15. `mapping/mapping_kdk_rarediseases.csv:2-5,11 diagnosisRd` -> current: AlphaID target noted as `alpha-id` -> issue: DNPM source is AlphaID-SE while lock target is AlphaID; canonicalization rule is underspecified -> fix: state AlphaID-SE source to locked AlphaID target, enforce ICD-10-GM+ORPHA+AlphaID/noMatchingCodeExists.
16. `mapping/mapping_kdk_rarediseases.csv:123-128` -> current: bare `ResearchStudy` / `MedicationRequest`, `MAPPED` -> issue: no verified MII/RD canonical; latest-careplan rule not explicit -> fix: target verified profiles or `DRAFT`.
17. `mapping/mapping_grz.csv:4 barcode` -> current: maps possible `"na"` into `Specimen.accessionIdentifier` -> issue: sentinel becomes false identifier -> fix: populate only real barcode; otherwise omit/use data-absent handling.
18. `mapping/mapping_kdk_oncology.csv:77-78 followUpDate/lastContactDate` -> current: bare `Observation`, `MAPPED` -> issue: no profile/code; likely belongs to Verlauf, Vitalstatus, Tod, or Encounter context -> fix: reprofile or downgrade.

**Robustness Verdicts**
| Area | Verdict |
|---|---|
| Oncology: diagnosis/topography/TNM/morphology | high |
| Oncology: ECOG/grading/follow-up response | medium |
| Oncology: MTB recommendations/CarePlan/ServiceRequest | low |
| Oncology: molecular variant element paths | medium |
| Rare diseases: diagnosis coding | medium |
| Rare diseases: MolGen variants | low |
| Rare diseases: GMFCS, care episode, board/plan/study/therapy | low |
| Rare diseases: HPO/phenotype basics | medium |
| GRZ: Consent/Person | high |
| GRZ: Biobank Specimen/tissue ontology | medium |
| GRZ: sequencing devices/QC/family relation | low |
