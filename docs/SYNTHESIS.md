# Mapping state synthesis (adversarial review round 3 + robustness)

Source: codex review round 3 (docs/REVIEW3-codex.md; vibe round 3 failed on a
network error) + the central mapping tables, cross-checked against the crawled
MII IGs and the ingested references (obds-to-fhir, dnpm-rd, kohlbacherlab, MolGen
paper). 428 leaves total.

## Robustness overview (MAPPED split into confidence tiers)

| Branch | High | Medium | Low | **MAPPED** | DRAFT | NOMAP | Total |
|--------|-----:|-------:|----:|-----------:|------:|------:|------:|
| KDK oncology | 42 | 104 | 28 | **174** | 45 | 10 | 229 |
| KDK rare diseases | 26 | 12 | 65 | **103** | 19 | 10 | 132 |
| GRZ | 13 | 12 | 16 | **41** | 6 | 20 | 67 |
| **Total** | **81** | **128** | **109** | **318** | **70** | **40** | **428** |

- **High** (≈25% of mapped): verified canonical + exact element + no ambiguity —
  demographics/Consent/Coverage (Person/Fall/Consent), ICD-10-GM diagnosis codings
  (Diagnose), MTB primary-diagnosis incl. ICD-O-3 morphology/topography.
- **Medium** (≈40%): right module + plausible element, but element/component path or
  binding not fully package-verified — TNM/ECOG/grading (Onkologie), MTB & MolGen
  variant components, HPO (Seltene), Biobank Specimen/tissue.
- **Low** (≈34%): right module/intent but shaky target — generic CarePlan/
  ServiceRequest/ResearchStudy, RD MolGen variants (unverified canonicals), GMFCS,
  GRZ sequencing Device/QC, MTB recommendation profiles.

## Per-area robustness verdict (codex round 3)

| Area | Verdict |
|------|---------|
| Oncology: diagnosis / topography / TNM / morphology | high |
| Oncology: ECOG / grading / follow-up response | medium |
| Oncology: molecular variant element paths | medium |
| Oncology: MTB recommendations / CarePlan / ServiceRequest | low |
| Rare diseases: diagnosis coding | medium |
| Rare diseases: HPO / phenotype basics | medium |
| Rare diseases: MolGen variants | low |
| Rare diseases: GMFCS / care episode / board / plan / study / therapy | low |
| GRZ: Consent / Person | high |
| GRZ: Biobank Specimen / tissue ontology | medium |
| GRZ: sequencing devices / QC / family relation | low |

## Open questions (must resolve to raise robustness)

1. **MTB/MolGen profile canonicals** — validate every `ext/modul-mtb` and
   `ext/modul-molgen` canonical + element binding against the **pinned package
   snapshot** (MolGen 2026.0.4, MTB module). Crawled-IG existence ≠ exact element
   paths. (codex #2)
2. **ECOG code conflict** — DNPM-on-FHIR uses LOINC `89247-1`; obds-to-fhir uses
   `89262-0`; our table currently has both. Which does the MII MTB ECOG profile bind?
3. **RECIST vs Verlauf-Gesamtbeurteilung** — obds-to-fhir models response as SNOMED
   Gesamtbeurteilung `396432002` (no RECIST); DNPM-on-FHIR `Response` uses LOINC
   `21976-6` with {CR,PR,MR,SD,PD,NA,NYA}. What does `mii-pr-mtb-response-befund`
   expect (incl. MR/NYA)?
4. **Fusion gene orientation** — structuralVariants `geneA`/`geneB` should map to
   `five-prime-gene` / `three-prime-gene` (orientation), not two generic
   `gene-studied`. Confirm the MTB fusion profile component names. (codex #3)
5. **chromosome component** — `component:chromosome` vs `component:chromosome-identifier`
   in the MTB/MolGen variant profiles. (codex #4)
6. **AlphaID-SE → AlphaID** — DNPM source emits Alpha-ID-SE; MII Seltene uses system
   `bfarm/alpha-id`. Confirm the diagnosis slice accepts Alpha-ID-SE content under that
   system, and the ICD-10-GM + ORPHA + AlphaID "all-three-or-noMatchingCode" rule. (codex #15)
7. **EpisodeOfCare vs Encounter** — DNPM SE/MTB use a distinct `EpisodeOfCare` (the
   "Fall"); MII Fall is `Encounter`. Is there an MII EpisodeOfCare profile, or do we
   model the episode as Encounter? Plus the dual `molecularBoardDecisionDate`
   (indication board = first CarePlan; molecular board = latest). (codex #7)
8. **GMFCS** — no MII/DNPM FHIR canonical exists; need a local CodeSystem/profile and
   the repeating effective-dated modelling. (codex #8)
9. **GRZ sequencing Device / QC** — no MII Device profile in the crawl. Where do
   kit/sequencer/pipeline/caller/coverage-QC land — MolGen `genomic-study-analysis`,
   a Device, or out-of-scope (the canonical DNPM Datenmodell marks much of this
   optional/not-Datenkranz)? (codex #9)
10. **Biobank Specimen.type SNOMED slice (MIIUP-04)** — profile requires an SCT slice
    but KDK ships only BTO. SCT translation, BTO-as-additional-coding, or escalation? (codex #13)
11. **MTB recommendations** — Tumorkonferenz / Therapieempfehlung / Studieneinschluss:
    map to the concrete MTB profiles (`mii-pr-mtb-therapieempfehlung`,
    `-studieneinschluss-anfrage`, `-behandlungsepisode`) with their cardinalities,
    instead of generic CarePlan. (codex #10)
12. **Consent `category` 3rd coding** — mapper sets LOINC `57016-8` + MII `…24.2.184`;
    we add a fhir.de consent-status coding. Binding choice to confirm.
13. **`barcode = "na"` sentinel** — must not become a false `Specimen.accessionIdentifier`. (codex #17)
14. **Block-level cardinalities** — the table lacks the canonical DNPM block cardinality
    (required/optional/conditional for the MVH minimal dataset). Pending ingestion of
    the DNPM Datenmodell V2.1 PDF will fill this.
