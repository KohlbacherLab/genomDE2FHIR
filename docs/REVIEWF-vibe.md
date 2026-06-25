# Final Adversarial Review Output

## 1. NEW correctness issues NOT already in docs/SYNTHESIS.md

- **Fusion gene orientation loss**: mapping_kdk_oncology.csv:178-185 maps `structuralVariants[].geneA`/`geneB` to generic `Observation.component:gene-studied.valueCodeableConcept`; MII MTB DNA/RNA fusion profiles define **`five-prime-gene`** and **`three-prime-gene`** components for orientation. knowledge/mii-kds/.../NGS_Bericht_Variante_DNA_Fusion_Observation.md:1

- **Chromosome component path mismatch**: mapping_kdk_rarediseases.csv:65,85 and mapping_kdk_oncology.csv:133,155 map chromosome to `Observation.component:chromosome.valueCodeableConcept`; MII variant profiles require **`component:chromosome-identifier`** (LOINC 48000-4). knowledge/mii-kds/.../NGS_Bericht_Variante_Einfache_Var.md:1

- **ECOG LOINC conflict in MAPPED rows**: mapping_kdk_oncology.csv:10 uses LOINC **89262-0**; :76 uses **89247-1** for the same semantic. dnpm-datenmodell/crosswalk.md:163 confirms canonical is 89247-1. knowledge/dnpm-datenmodell/crosswalk.md:163

## 2. SYNTHESIS open questions RESOLVED or INFORMED by knowledge/bih-cei/REVIEW.md or crawl

- **#2 ECOG code conflict** → **RESOLVED**: dnpm-datenmodell ECOG profile (http://bwhc.de/mtb/obs-ecog-performance-status) binds LOINC **89247-1**. knowledge/dnpm-datenmodell/crosswalk.md:163

- **#3 RECIST vs Verlauf-Gesamtbeurteilung** → **RESOLVED**: BIH-CEI A2 cites **mCODE CancerDiseaseStatus/Response Assessment** with LOINC **21976-6** as the value-set anchor for PD/SD/PR/CR, stronger than bare SNOMED 396432002. knowledge/bih-cei/REVIEW.md:A2,95

- **#4 Fusion gene orientation** → **RESOLVED**: MII MTB fusion profiles use **`five-prime-gene`**/`**three-prime-gene**` components, not generic gene-studied. knowledge/mii-kds/.../NGS_Bericht_Variante_DNA_Fusion_Observation.md:1

- **#5 chromosome component** → **RESOLVED**: MII variant profiles define **`component:chromosome-identifier`** (LOINC 48000-4), not `component:chromosome`. knowledge/mii-kds/.../NGS_Bericht_Variante_Einfache_Var.md:1

- **#6 AlphaID-SE → AlphaID** → **INFORMED**: BIH-CEI B3 confirms ORPHA-centric diagnosis; **AlphaID is German-specific** and correct for MII Seltene. knowledge/bih-cei/REVIEW.md:B3,77

- **#7 EpisodeOfCare vs Encounter** → **INFORMED**: dnpm-datenmodell shows **EpisodeOfCare** is required for MTB-Behandlungs-Episode (block 3); DNPM uses distinct EpisodeOfCare ("Fall"). knowledge/dnpm-datenmodell/overview-and-cardinalities.md:32

- **#8 GMFCS** → **INFORMED**: BIH-CEI B4 confirms not modelled in RareLink/ERKER; **local CodeSystem required**. knowledge/bih-cei/REVIEW.md:B4,82

- **#11 MTB recommendations** → **INFORMED**: BIH-CEI A7 surfaces complex biomarkers (TMB, MSI-h, HRD); confirms **`mii-pr-mtb-therapieempfehlung`**, **`-studieneinschluss-anfrage`**, **`-behandlungsepisode`** as concrete MTB profiles instead of generic CarePlan. knowledge/bih-cei/REVIEW.md:A7,56

- **#14 Block-level cardinalities** → **RESOLVED**: dnpm-datenmodell V2.1 provides full block cardinality table with MVH-pflicht markings. knowledge/dnpm-datenmodell/overview-and-cardinalities.md:1

- **#1 TNM enrichment** → **INFORMED**: BIH-CEI A1 adds **UICC value system** + per-category LOINC codes **21905-5** (cT), **21906-3** (cN), **21907-1** (cM) and suggests Condition.stage for overall AJCC stage. knowledge/bih-cei/REVIEW.md:A1,20

- **#12 Consent category 3rd coding** → **INFORMED**: dnpm-rd/rd-bfarm-mapping.md confirms DNPM→BfArM consent mapping uses LOINC **89247-1** and MII broad-consent codes; fhir.de consent-status coding is additional. knowledge/dnpm-rd/rd-bfarm-mapping.md:46

- **#9 GRZ sequencing Device/QC** → **OPEN**: No MII Device profile found in crawl; BIH-CEI notes DNPM Datenmodell marks much as optional/not-Datenkranz. knowledge/bih-cei/REVIEW.md:A9,69

- **#10 Biobank Specimen.type SNOMED slice (MIIUP-04)** → **OPEN**: mapping_grz.csv:43 notes **SCT slice required but KDK has only BTO**. knowledge/bih-cei/REVIEW.md:B1,64

## 3. MAPPED rows to downgrade to DRAFT (unverified canonical/element)

- mapping_kdk_oncology.csv:178-185 `structuralVariants[].geneA.*`/`geneB.*` → **DRAFT** (path should be `five-prime-gene`/`three-prime-gene` per MII MTB fusion profile, not generic gene-studied)

- mapping_kdk_rarediseases.csv:65,85 `molecular.copyNumberVariants[].chromosome`/`molecular.smallVariants[].chromosome` → **DRAFT** (path should be `component:chromosome-identifier` per MII MolGen profile)

- mapping_kdk_oncology.csv:133,155 `molecular.copyNumberVariants[].chromosome`/`molecular.smallVariants[].chromosome` → **DRAFT** (path should be `component:chromosome-identifier` per MII MTB profile)

- mapping_grz.csv:4 `donors[].labData[].barcode` → **DRAFT** (value 'na' must not map to Specimen.accessionIdentifier; needs null-handling per SYNTHESIS #13)
