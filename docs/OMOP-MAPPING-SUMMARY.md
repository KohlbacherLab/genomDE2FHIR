# genomDE Datenkranz → OMOP CDM — first mapping pass: results & issues

A second mapping target (alongside FHIR/MII-KDS). Tables: `mapping/mapping_omop_*.csv`
(same source leaves, OMOP target columns). Grounded in deep web research ingested to
`knowledge/omop/` (oncology+genomics, rare-disease) and `knowledge/research/fhir-to-omop-tooling.md`.

## Robustness — OMOP vs FHIR (same 428 leaves)

| Target | MAPPED | DRAFT | NOMAP |
|--------|-------:|------:|------:|
| **FHIR / MII KDS** | **315** | 73 | 40 |
| **OMOP CDM** | **79** | 237 | 112 |

Per branch (OMOP): oncology 54/121/54 · rare-disease 16/90/26 · GRZ 9/26/32.
(MAPPED lowered 89→79 after the real-world-adoption review — see below — corrected
over-grading: regimen-episode demoted, RECIST/intent/termination de-MAPPED.)

The gap is the headline result: OMOP cleanly captures **~21%** of leaves vs **~74%** for
FHIR. OMOP is strong on the analytic clinical *core* and weak on genomics, oncology
attributes, rare-disease specifics, and anything recommendation-shaped.

## What maps cleanly (MAPPED, 79)
Standard-OMOP clinical spine, all with a real vocabulary path:
- **Demographics** → `person` (+ `location` for AGS); **death/vital status** → `death`.
- **Diagnoses** (ICD-10-GM, ICD-O-3) → `condition_occurrence` (source concept + SNOMED standard);
  ICD-O-3 histology+topography precoordinated into the diagnosis concept.
- **Procedures** (OPS) → `procedure_occurrence`; **substances** (ATC) → `drug_exposure` (→RxNorm).
- **Hospitalizations / follow-up visits** → `visit_occurrence`; **specimen/tissue** → `specimen`.

## What maps only with loss / immaturity (DRAFT, 237)
- **Oncology attributes** — grading & TNM → `measurement` via the OHDSI **Cancer Modifier** /
  **AJCC** vocabularies (Ed.7 loaded, Ed.8 contested); ECOG → measurement [concept_id to verify].
- **Therapy regimen / episode** — systemic therapy → `episode` (Treatment Regimen 32531) +
  HemOnc; MTB decision → `episode`. Episode model is real but "under development".
- **Molecular variants** — small variants → `measurement` via the **OMOP Genomic Extension**
  (~55k *known* variants by HGVS/HGNC); zygosity/VAF/read-depth → `*_source_value` only.
- **RD diagnoses** — ORPHA is **not** an OMOP vocabulary → route via SNOMED (long-tail loss,
  ~3k/7k coverage), ORPHA + Alpha-ID-SE kept as source (Alpha-ID-SE has no concept).
- **HPO phenotypes** → `observation`; HPO is a **source** vocab only (since OHDSI v20260227),
  so not natively cohort-queryable; onset OK, status-history has no pattern.
- **GMFCS / trio** → local concept / `fact_relationship` (no blessed pattern).
- **GRZ sequencing QC / reference-genome build** → `measurement` with local concepts (no home).

## What has no OMOP home (NOMAP, 112)
- **Care-plan recommendations** (therapy / study / clinical-management, both branches) — OMOP is
  an *observational* model; there is no recommendation table. **Biggest semantic loss.**
- **Treatment intent** and **RECIST response** — no standard OMOP concept.
- **CNV / gene fusion / RNA expression / mutational signatures** — no/thin OMOP model.
- **HRD, tumour purity** — no standard concept.
- **Sequencing device/kit metadata, raw files** — out of OMOP scope.
- **Consent**, MV-administrative fields, transport metadata.

## Key issues
1. **No native variant table in OMOP CDM v5.4.** Variants live as Genomic-Extension
   *measurement* concepts (known/clinically-relevant only) → novel/VUS lost. Full G-CDM is a
   bespoke, low-adoption prototype, somatic-centric (germline ACMG class+criteria absent).
2. **Reference-genome build (GRCh37/38) has no OMOP field** — coordinate-provenance liability.
3. **Vocabulary immaturity** for RD: ORPHA absent; HPO source-only; Alpha-ID-SE/GMFCS absent.
4. **Recommendations / intent / RECIST have no analytic home** — inherent to OMOP's purpose.
5. **Terminology mapping is largely manual** (Athena + Usagi); the German ETL paper reports
   ICD-10-GM/OPS items that could not be represented at all.
6. **Tooling gap** — only `OHDSI/ETL-German-FHIR-Core` (MIRACUM/MII) does MII-KDS-FHIR→OMOP, and
   it is stale (2023, recruitment-scoped) with no genomics or oncology episodes; the HL7
   FHIR-to-OMOP IG is pre-ballot.

## Recommendation
- **FHIR MII KDS stays the authoritative target.** OMOP = a **downstream secondary-use analytic
  projection** with explicitly documented losses — do not pretend it captures variants/CNV/
  fusion/QC/intent/RECIST/HRD/recommendations faithfully.
- **Build route (hybrid):** clinical core → OMOP **via FHIR** (fork/extend ETL-German-FHIR-Core —
  the only "map once" win); **genomics, oncology episodes, and rare disease → direct** genomDE→OMOP
  (no FHIR leverage; target the immature Genomic-CDM + Oncology Extension, accept the gaps).
- Keep the mapping table as the single source of truth carrying **both** FHIR canonicals and
  OMOP concept targets per leaf.

_Status semantics: MAPPED = clean standard-OMOP home; DRAFT = mappable but lossy / immature
extension / unverified concept / local-concept-only; NOMAP = no OMOP home. Concept ids tagged
[VERIFY] in the per-row notes need Athena confirmation (the OMOP analogue of the FHIR P0)._

## Real-world adoption review (Belenkaya 2021 + npj 2025 scoping review + RD-CDM/RareLink)

Deep adversarial research on *actual* OMOP use for precision oncology + rare disease
(`knowledge/omop/omop-oncology-realworld.md`, `omop-rare-disease-realworld.md`):

- **Model-defined ≠ deployed.** Our first pass encoded what the OMOP Oncology Extension
  *defines*; the npj 2025 scoping review (49 studies) shows those structures are barely
  adopted and independently re-derives our gap list — its "cannot represent without
  extension" set = **staging/TNM, ECOG, histological grade, treatment intent, lines of
  therapy, biomarkers, genetic/molecular variants**. Even **DEATH and Visit_occurrence are
  "minimally used"**; the **Cancer Modifier isn't named in any study**; **no MTB-on-OMOP
  project exists**. → these stay DRAFT/GAP with a "real-world non-adoption" note, not promoted.
- **Belenkaya 2021** is a design paper: only **SEER-observed ICD-O-3 combos** precoordinated,
  grade/stage modifiers for **breast & prostate only**, episodes "rarely available in
  structured form", genomics **deferred**, RECIST/intent **never mentioned**.
- **Over-grading corrected:** `priorProcedures[].{therapyResponse,therapyResponseDate}` →
  measurement/DRAFT (no OMOP RECIST concept); `intention`, `terminationReasonOBDS` → NOMAP
  (no concept; lost when folded into a procedure); regimen `treatmentType` episode → DRAFT
  (low adoption). `libraryType` → procedure_occurrence (the test is a procedure).
- **Rare disease — the decisive finding:** the community **RD-CDM (Graefe et al., Sci Data
  2025; RareLink, npj Genomic Med 2025) is deliberately NOT OMOP** — it is ERDRI-CDS + **HL7
  FHIR + GA4GH Phenopackets**, and RareLink ships **no OMOP path** because "a representation
  purely in OMOP cannot retain the full semantic/structural precision." A separate
  "OMOP-based RD-CDM" (TU Dresden) is feasibility scaffolding (HPO via SOURCE_TO_CONCEPT_MAP
  = "temporary", no onset/verification-status field).
- **ORPHA `VERIFY` flag resolved:** ORPHA is **confirmed NOT in Athena** (2026) → local
  vocab (concept_id >2bn) + Usagi + SNOMED standard; long-tail RD loss; **Alpha-ID-SE has no
  OMOP target** (source-value only). **HPO** is a *source* vocab only → not cohort-queryable;
  **excluded/refuted phenotypes are structurally unmapped** (OMOP absence convention).
- **RD genomics:** OMOP Genomic vocab + VRS/KOIOS (OHDSI 2025, bioRxiv 2026) are **cancer-
  scoped**; germline ACMG class/criteria, zygosity, inheritance, de-novo, segregation, trio
  are **unmodelled** (ACMG appears only as a gene-list filter). Pedigree only via fact_relationship.

**Strengthened recommendation:** this now rests on published evidence, not just model
inspection — **FHIR MII KDS is authoritative; OMOP is a lossy secondary analytic export.**
For rare disease specifically, the field's own RD-CDM is FHIR+Phenopackets *by design*, so
do not over-invest in an OMOP RD representation beyond the analytic clinical core.

_References: Belenkaya 2021 [PMC8140810]; npj scoping review 2025 [PMC11973147]; Graefe
RD-CDM (Sci Data 2025); RareLink (npj Genomic Med 2025)._

## FHIR→OMOP tooling deep-dive — HL7 IG + mihubx/MIRACUM ETL (additional insights)

Analysed the HL7 FHIR-to-OMOP IG (v1.0.0) and downloaded/analysed the mihubx "fhir-to-omop"
tool — engine = the deployed **MIRACUM `org.miracum.etl.fhirtoomop`** ETL
(`knowledge/research/fhir-to-omop-mihubx-etl.md`). Applied as row annotations to the OMOP table:

- **"Map once via FHIR" is real for the clinical core** — the ETL handles Patient/Condition/
  Observation/Procedure/Medication(+Statement/Admin)/Encounter. Our OMOP spine rows
  (diagnoses→condition_occurrence, procedures→procedure_occurrence, substances→drug_exposure,
  death, visits) are now tagged **VALIDATED by a deployed ETL** (genomDE→MII-KDS-FHIR→ETL→OMOP).
- **Domain-driven routing** — the ETL chooses condition/measurement/observation/procedure by the
  *standard concept's `domain_id`*, not a fixed rule. Coded-finding rows (grade/TNM/ECOG/HPO/
  biomarkers) annotated "table = concept domain", matching the HL7 IG's Value-as-Concept pattern.
- **RD diagnoses gain a concrete ORPHA→SNOMED bridge** — the ETL ships `orpha_snomed_mapping.csv`
  (5,906 ORPHA→SNOMED Condition maps), applied by its ConditionMapper. Cited on the RD diagnosis
  rows (still DRAFT: long-tail coverage loss; Alpha-ID-SE has no target).
- **TNM/grade/stage have a concrete implementation path** — the ETL's `post_process_stage.sql` /
  `post_process_severity.sql` link a stage/severity finding to the diagnosis Condition via
  `post_process_map` + fact_relationship. Annotated on grading/TNM (status stays DRAFT — npj 2025
  real-world non-adoption still holds; this is *how* to do it, not evidence it's done).
- **Diagnosesicherheit / verificationStatus** handled by the ETL (SOURCE_TO_CONCEPT_MAP
  diagnostic-confidence) — informs germlineDiagnosisConfirmed / RD verification rows.
- **Genomics has NO FHIR→OMOP path** — no Specimen/variant mapper in the ETL (matches the HL7 IG
  excluding genomics). Variant/CNV/fusion/QC/ref-genome rows annotated "direct-to-OMOP-Genomic-CDM
  only" — unchanged conclusion, now confirmed from the deployed tool's source.

Net: this **strengthens the hybrid build recommendation** with a concrete, deployed reference
implementation for the clinical core (and a ready ORPHA→SNOMED + stage-linkage pattern), while
re-confirming genomics/oncology-attributes/RD-specifics as the direct-mapping frontier.
