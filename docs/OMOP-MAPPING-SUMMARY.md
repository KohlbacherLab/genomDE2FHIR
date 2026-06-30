# genomDE Datenkranz → OMOP CDM — first mapping pass: results & issues

A second mapping target (alongside FHIR/MII-KDS). Tables: `mapping/mapping_omop_*.csv`
(same source leaves, OMOP target columns). Grounded in deep web research ingested to
`knowledge/omop/` (oncology+genomics, rare-disease) and `knowledge/research/fhir-to-omop-tooling.md`.

## Robustness — OMOP vs FHIR (same 428 leaves)

| Target | MAPPED | DRAFT | NOMAP |
|--------|-------:|------:|------:|
| **FHIR / MII KDS** | **315** | 73 | 40 |
| **OMOP CDM** | **89** | 229 | 110 |

Per branch (OMOP): oncology 60/117/52 · rare-disease 20/86/26 · GRZ 9/26/32.

The gap is the headline result: OMOP cleanly captures **~21%** of leaves vs **~74%** for
FHIR. OMOP is strong on the analytic clinical *core* and weak on genomics, oncology
attributes, rare-disease specifics, and anything recommendation-shaped.

## What maps cleanly (MAPPED, 89)
Standard-OMOP clinical spine, all with a real vocabulary path:
- **Demographics** → `person` (+ `location` for AGS); **death/vital status** → `death`.
- **Diagnoses** (ICD-10-GM, ICD-O-3) → `condition_occurrence` (source concept + SNOMED standard);
  ICD-O-3 histology+topography precoordinated into the diagnosis concept.
- **Procedures** (OPS) → `procedure_occurrence`; **substances** (ATC) → `drug_exposure` (→RxNorm).
- **Hospitalizations / follow-up visits** → `visit_occurrence`; **specimen/tissue** → `specimen`.

## What maps only with loss / immaturity (DRAFT, 229)
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

## What has no OMOP home (NOMAP, 110)
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
