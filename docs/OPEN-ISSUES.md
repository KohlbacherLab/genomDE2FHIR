# genomDE → MII KDS mapping — final open issues

Consolidated from adversarial review rounds 1–3 + **final round** (codex-final &
vibe-final, with the complete KG: mii-kds crawl 1416p, obds-to-fhir, dnpm-rd,
kohlbacherlab, bih-cei, dnpm-datenmodell, MolGen paper). Supersedes
[docs/SYNTHESIS.md](SYNTHESIS.md).

## Robustness snapshot (after final corrections)

| Branch | MAPPED | DRAFT | NOMAP | Total |
|--------|-------:|------:|------:|------:|
| KDK oncology | 166 | 53 | 10 | 229 |
| KDK rare diseases | 106 | 16 | 10 | 132 |
| GRZ | 27 | 20 | 20 | 67 |
| **Total** | **299** | **89** | **40** | **428** |

_RD updated after ingesting the canonical DNPM SE Data Model + SE Implementierungs-
leitfaden and promoting RD rows to crawl-verified Seltene profiles (`seltene@2026.0.0`):
`mii-pr-seltene-{genetic-diagnosis, therapieplan, therapieempfehlung, studieneinschluss-anfrage, studie, clinical-impression, hpo-assessment}`._

The final pass deliberately *lowered* MAPPED (318→293) to be honest: rows with
wrong/unverified targets were downgraded rather than left green.

## Resolved / informed since round 3

| # | Item | Outcome |
|---|------|---------|
| RECIST response | mCODE CancerDiseaseStatus + **LOINC 21976-6** (incl. MR/NYA) on `mii-pr-mtb-response-befund` | RESOLVED (bih-cei A2) |
| Fusion orientation | MTB DNA/RNA-fusion use `component:five-prime-gene`/`three-prime-gene` | RESOLVED → applied as DRAFT until rewired |
| chromosome component | `component:chromosome-identifier` (LOINC 48000-4) | RESOLVED → **fixed** |
| Block cardinalities (RD) | DNPM Datenmodell V2.1 + rd-validation give required/optional/conditional | RESOLVED (dnpm-rd, dnpm-datenmodell) |
| **RECIST response** (was open #3) | `Observation:Response`, LOINC **21976-6**, values **CR/PR/MR/SD/PD/NA**, method {RECIST,RANO} | RESOLVED — full DNPM Datenmodell ingested (`knowledge/dnpm-datenmodell/crosswalk.md`) |
| **MTB recommendation profiles** (was open #5) | Therapieplan=CarePlan + activity.reference→TherapyRecommendation(MedicationRequest)/ServiceRequest(GeneticCounselling/Rebiopsy/StudyInclusion); evidence ladder m1A–m3 | RESOLVED — crosswalk pp.113-150 |
| **Oncology block cardinalities** (was open #14) | MTB-Akte Bundle: NGS≥1 & CarePlan≥1 required for MVH; ECOG+Follow-up required for followup-type | RESOLVED — crosswalk pp.151-164 |
| NGS variant component codes | SimpleVariant/CNV/Fusion/RNASeq bwhc profiles + LOINC (dna-chg 48004-6, gene 48018-6, chromosome 48000-4, ref/alt 69547-8/69551-0, …) | RESOLVED — crosswalk pp.95-112 |
| Biobank `Specimen.type` SNOMED slice | SCT slice required; KDK ships BTO only → needs SCT translation (MIIUP-04) | CONFIRMED open |
| TNM enrichment | UICC value system + LOINC cT/cN/cM 21905-5/21906-3/21907-1; `Condition.stage` for AJCC overall | INFORMED (bih-cei A1) |
| RD phenotype status | SNOMED present/refuted `410605003`/`723511001` behind HPO assessment | INFORMED (bih-cei B1) |
| Therapy intent | `OnkoTherapyIntent` CS (adds **erhaltung/neoadjuvant/adjuvant**) ≈ mCODE procedure-intent | INFORMED (bih-cei A3) |

## Open issues (ranked — what's needed to close)

1. **MTB/MolGen canonical + element verification (P0).** Validate every
   `ext/modul-mtb` and `ext/modul-molgen` canonical *and element/component path*
   against the **pinned packages** (MolGen 2026.0.4, MTB module). Crawled-IG
   existence ≠ exact slice names. Blocks raising ~110 MTB + ~50 MolGen rows from
   medium→high.
2. **ECOG code conflict (P0).** obds-to-fhir/MII-Onko → LOINC **89262-0** + SNOMED
   `423740007`; DNPM/bwhc → **89247-1**. Table now unified to 89262-0 *pending*
   confirmation against the pinned MII Onko ECOG profile binding.
3. **AlphaID-SE vs AlphaID (P1).** DNPM RD source emits Alpha-ID-SE
   (`…/bfarm/alpha-id-se`); MII Seltene diagnosis slice uses `…/bfarm/alpha-id`
   (crawl-verified). Confirm the slice accepts Alpha-ID-SE *content* under the
   AlphaID system + enforce the ICD-10-GM ∧ ORPHA ∧ AlphaID "all-three-or-
   `noMatchingCodeExists`" rule.
4. **EpisodeOfCare vs Encounter (P1).** DNPM SE/MTB model the "Fall" as a distinct
   `EpisodeOfCare`; MII Fall is `Encounter` (`KontaktGesundheitseinrichtung`) only.
   Decide: model a base-FHIR EpisodeOfCare, or fold the episode into Encounter.
   Includes the dual `molecularBoardDecisionDate` (indication=first CarePlan;
   molecular=latest CarePlan).
5. **MTB / SE recommendation profiles (P1).** Replace generic `CarePlan`/
   `ServiceRequest`/`ResearchStudy`/`MedicationRequest` recommendation rows with the
   concrete profiles: `mii-pr-mtb-therapieplan` + activity slices,
   `mii-pr-mtb-therapieempfehlung`, `mii-pr-mtb-studieneinschluss-anfrage`;
   RD `mii-pr-seltene-therapieempfehlung` / `-studieneinschluss-anfrage`.
6. **GRZ sequencing Device/QC (P1).** No MII Device profile exists. 14 rows now
   DRAFT. Decide target: MolGen `genomic-study-analysis` metadata, a local Device
   profile, or out-of-Datenkranz (DNPM marks much of this optional).
7. **Fusion orientation rewire (P2).** structuralVariants `geneA`/`geneB` (8 rows,
   now DRAFT) → `five-prime-gene`/`three-prime-gene` per the MTB fusion profile.
8. **GMFCS (P2).** No MII/DNPM canonical (4 rows DRAFT). Define a local CodeSystem
   + repeating effective-dated Observation.
9. **Biobank `Specimen.type` SNOMED slice / MIIUP-04 (P2).** KDK BTO-only; needs SCT
   translation or BTO-as-additional-coding. Still MAPPED with caveat.
10. **`barcode = "na"` sentinel (P2).** Guard so it never becomes a false
    `Specimen.accessionIdentifier`. Transform-level fix.
11. **Consent `category` 3rd coding (P3).** Mapper emits LOINC `57016-8` + MII
    `…24.2.184`; we add a fhir.de consent-status coding — confirm the binding choice.
12. **Therapy-response date element (P3).** `…effectiveDateTime` on a few therapy
    rows sits on the wrong profile; attach to the RECIST/Verlauf Observation.
13. **Gap candidates (P3).** Complex biomarkers (TMB/MSI-h/HRD/mutational
    signatures) and line-of-therapy (`EpisodeOfCare`) — confirm whether the
    genomDE/DNPM source carries them before adding rows.
14. **Full KDK/GRZ block cardinality audit (P3).** RD cardinalities grounded;
    extend the canonical block-cardinality (MVH-pflicht) audit to KDK oncology + GRZ.

## Applied in the final pass

- **Fixed (kept MAPPED):** chromosome→`chromosome-identifier` (4); ECOG unified +
  conflict-noted (2); RD hospitalization rows relabeled `Encounter` (2).
- **Downgraded to DRAFT (honest):** fusion geneA/geneB (8), GMFCS (2), RD
  `diagnosticAssessment` placeholder (1), GRZ sequencing Device rows (14).

See `scripts/apply_final_review.py` for the exact audit trail.

## RD addendum — after SE Data Model ingest + Seltene-profile alignment (round: SE docs)

**Resolved / improved:**
- `diagnosticAssessment` → `Condition.verificationStatus` on `mii-pr-seltene-genetic-diagnosis` (was DRAFT placeholder).
- RD diagnosis/recommendation rows promoted from generic base FHIR to concrete Seltene
  profiles (genetic-diagnosis, therapieplan, therapieempfehlung, studieneinschluss-anfrage, studie).
- Value sets pinned from the SE model: diagnosticExtent (Family Control Level), CNV type
  {gain,loss}, Therapy Category/Type, Clinical Management Type (TNAMSE), HPO status history.
- **hospitalization fixed**: banded count/day codes → `Observation.valueCodeableConcept`
  (was wrongly `Encounter.period/length`); now DRAFT (no MII profile for the bands).

**RD open issues remaining (codex + vibe round on SE docs):**
1. **ClinicalDiagnosis vs GeneticDiagnosis split** — we target `mii-pr-seltene-genetic-diagnosis`
   for all RD diagnoses; should switch to `mii-pr-seltene-clinical-diagnosis` when not
   genetically confirmed. Needs a verification-status-driven profile selection rule.
2. **`furtherGeneticDiagnosticRecommended`** — this KDK enum value has NO
   `condition-ver-status` target in the SE model; needs a fallback (note/extension).
3. **AlphaID-SE vs AlphaID** (persistent) — SE source emits Alpha-ID-SE; MII Seltene IG
   uses system `bfarm/alpha-id`. Confirm the diagnosis slice accepts Alpha-ID-SE content.
4. **GMFCS** — still no MII/DNPM CodeSystem; DRAFT. Needs a local CS + repeating
   effective-dated Observation.
5. **`genomicStudyType` hardcoded `single`** upstream (DNPM //TODO) — unreliable source value.
6. **Board model** — indication-board vs therapy-board: the two `molecularBoardDecisionDate`
   values map to first vs latest `mii-pr-seltene-therapieplan`; board-type marking unmodeled.
7. **Therapieempfehlung sub-profiles** — split `-nicht-medikamentoes` / `-kombination` by
   Therapy Type (currently the base `-therapieempfehlung` with a note).
8. **MolGen variant component paths** (vibe) — localization / diagnosticSignificance /
   segregationAnalysis / publications: verify exact component slices against the pinned
   MolGen package (else DRAFT).

## Population-weighted priorities (vs SE/MTB example JSONs: 42 onc + 42 rd + 6 grz)

Coverage of *actually-populated* leaves: **oncology** MAPPED 98 / DRAFT 17 / NOMAP 8 /
MISSING-from-table 2; **rare-disease** MAPPED 91 / DRAFT 13 / NOMAP 8 / MISSING-from-table 21.

### #0 (NEW, biggest) — schema-version mismatch: example data ≠ mapping-table schema
The examples populate field names the table doesn't have, because the table was extracted
from `schemas/kdk` (1.7.1) but the examples follow a different KDK version. All 42/42:
- RD `case.priorRd.*` (singular object: zseContactDate, hospitalization{Periods,Duration},
  genomic{Test,Study}Type, diagnostic{Date,Result}) — table has `case.priorRds` (array).
- RD `plan.recommended{Therapies,Studies}[].variantReferences[]` — table has `…variants[]`.
- onc `case.priorDiagnostic.{type,date}` (singular) — table has `case.priorDiagnostics`.
- RD coding arrays `*.genes[].{system,display}` and `*.localization[].{system,display}` —
  table only emitted `.code`.
**Impact:** a mapper built on the current table would silently miss these 100%-populated
fields. **Action:** decide which KDK version production uses (per the BfArM-MVH repo / the
LMU/Tübingen contacts), re-extract leaves, then re-run the alignment passes.

### Population-ranked content issues (already tracked, now prioritized by frequency)
1. **Molecular variant DRAFT fields — 42/42 every RD case:** `*.localization`,
   `*.diagnosticSignificance`, `*.segregationAnalysis`, `*.publications` →
   MolGen component-path verification (open #P0). Highest-volume content gap.
2. **Recommendation DRAFT fields — 42/42 every onc case:** `recommendedSystemicTherapies`
   type/therapeuticStrategy/evidenceLevel/variants, `recommendedStudies`,
   `carePlanOd.otherRecommendations` → MTB recommendation canonical/element verification.
3. **GMFCS — 42/42 every RD case (DRAFT):** local CodeSystem needed.
4. **`germlineDiagnosisConfirmed`, `additionalClassification` — 42/42 onc (DRAFT).**
5. **GRZ sequencing Device/QC — 4/6 (DRAFT):** whole `sequenceData` QC block populated.
6. **`researchConsents[].scope` embedded MII Consent — 24-25/42:** treated as one verbatim
   passthrough leaf (~25 sub-fields); validate the passthrough round-trips.

### Lower priority (real but rarely/never populated in the examples)
AlphaID-SE-vs-AlphaID, EpisodeOfCare-vs-Encounter semantics, `barcode="na"` sentinel,
Consent 3rd category coding — correctness items, but not high-frequency in the corpus.

## Update — GMFCS resolved (LOINC 62782-8)
GMFCS (42/42 every RD case, previously DRAFT "no MII/DNPM CodeSystem") is now MAPPED:
`Observation.code` = LOINC **62782-8** (PhenX gross motor function 6-12y / GMFCS Family
Report), value from LOINC answer list **LL1594-2** (LA-codes). ConceptMap {I→LA16552-4,
II→LA15151-6, III→LA15150-8, IV→LA16556-5, V→LA16558-1} — by severity, not list order.
Residual caveat: 62782-8 is the **6-12y** age band; the source level is age-agnostic —
confirm the band (or that a single code is acceptable). No MII Seltene GMFCS profile, so
this is a base `Observation` with standard LOINC binding.

## Update — GRZ sequencing QC resolved (research: knowledge/research/fhir-sequencing-qc.md)
Adversarial research (cross-checked vs DNPM/bwhc, which omits raw QC) → sequencing act =
Procedure **`mii-pr-mtb-genomic-study-analysis`** (mtb@2026.0.0), with device-function CS
`mii-cs-mtb-genomicanalysis-devicefunction` (sequencing-device / library-prep), genome-build
ext (LOINC **62374-4**; GRCh37=LA14029-5, GRCh38=LA26806-2), method-type ext, and QC ext
`mii-ex-mtb-genomic-study-analysis-qc` (read-depth + sequencing-coverage, uncoded).
Promoted: sequencer/kit/libraryPrep devices, referenceGenome, libraryType/sequenceType/
Subtype, meanDepthOfCoverage, targetedRegionsAboveMinCoverage, callerUsed, pipeline.
**GRZ MAPPED 27→41, DRAFT 20→6.**

Still DRAFT — **no standard clinical-FHIR home** (HL7 Genomics Reporting metrics covers only
read-depth + coverage; DNPM/bwhc omits these): `percentBasesAboveQualityThreshold` (%≥Q30),
`minCoverage`, `nonCodingVariants`, `sequencingLayout`, `fragmentationMethod`. → local code /
DeviceMetric / omit. GRZ `sequenceData.files[]` stay NOMAP (raw genomic data; DocumentReference
is the option if ever ingested). researchConsents[].scope = verbatim MII Consent passthrough (resolved).

## Robustness snapshot — current
| Branch | MAPPED | DRAFT | NOMAP | Total |
|--------|-------:|------:|------:|------:|
| KDK oncology | 166 | 53 | 10 | 229 |
| KDK rare diseases | 108 | 14 | 10 | 132 |
| GRZ | 41 | 6 | 20 | 67 |
| **Total** | **315** | **73** | **40** | **428** |

---

## Stage-2 update — mappers, harness, validation (current)

**Built:** Python + FML oncology mappers (clinical spine); e2e harness
([FIX-PLAN](FIX-PLAN.md), [E2E-REPORT](E2E-REPORT.md)); BfArM JSON-Schema validator
(`scripts/validate_datenkranz.py`); schemas verified byte-identical to upstream
([schemas/PROVENANCE.md](../schemas/PROVENANCE.md)).

**Resolved this stage (Python, live-verified against matchbox + latest 2026 packages + tx.fhir.org):**
- Patient `gender=other` → `gender-amtlich-de` extension (mii-pat-1) — clean.
- ECOG out-of-VS scores (source `5`) dropped with warning — clean.
- Consent + Vitalstatus profile canonicals corrected (`modul-consent` no `core/`; `Vitalstatus`
  not `mii-pr-person-vitalstatus`); Vitalstatus codes L/T — clean.
- matchbox: heap 3g→12g (was OOMing), reloaded to latest 2026 packages, tx.fhir.org enabled.

**Open — oncology mapper content:**
1. **Coverage `coverageType='UNK'`** (89/1056 in synthData-v1) — not in `versicherungsart-de-basis`;
   map to unknown/data-absent or drop `Coverage.type`.
2. **Consent §64e modelling** — genomDE MV-consent domains (`mvSequencing`/`reIdentification`/
   `caseIdentification`) are NOT MII Broad-Consent policy codes, and the real MII Broad Consent
   arrives separately via `researchConsents` (passthrough). Needs a target-model decision, not a hack.
3. **Coverage-gap (dominant): molecular / plan / TNM / grading unmapped** — the new data populates
   these in ~98% of records (molecular), all silently dropped. Biggest missing surface.

**Open — infra/terminology:**
4. German terminologies (ICD-10-GM/ICD-O-3/OPS/ATC) can't validate on tx.fhir.org → wire the
   **MII SU-TermServ Ontoserver** via the mTLS proxy (`infra/mii-termserv-proxy/`; needs the cert).

**Open — FML (Path B), backlogged:** `reference(pat)` produces nothing in matchbox v4.0.12 → build
refs as `'Patient/'+tanC`; add transaction `fullUrl`+`request`; `Coverage.meta.profile`; backport all
Python P0 fixes; conformance extensions parity.

**Open — RD / GRZ FHIR mappers:** not built.

**Source-data defects found by the schema validator** ([SCHEMA-VALIDATION-FINDINGS](SCHEMA-VALIDATION-FINDINGS.md)):
synthData-v1 `nct` (476/500 invalid: TNM `version` missing, `priority` string-not-int, therapy
`reference` missing) and multi-donor `grz` (549/1000: `researchConsents.presentationDate` missing).
`dnpm`/`ukdd`/`nse` schema-clean. Raise with the data generators.
