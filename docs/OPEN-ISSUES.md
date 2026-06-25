# genomDE → MII KDS mapping — final open issues

Consolidated from adversarial review rounds 1–3 + **final round** (codex-final &
vibe-final, with the complete KG: mii-kds crawl 1416p, obds-to-fhir, dnpm-rd,
kohlbacherlab, bih-cei, dnpm-datenmodell, MolGen paper). Supersedes
[docs/SYNTHESIS.md](SYNTHESIS.md).

## Robustness snapshot (after final corrections)

| Branch | MAPPED | DRAFT | NOMAP | Total |
|--------|-------:|------:|------:|------:|
| KDK oncology | 166 | 53 | 10 | 229 |
| KDK rare diseases | 100 | 22 | 10 | 132 |
| GRZ | 27 | 20 | 20 | 67 |
| **Total** | **293** | **95** | **40** | **428** |

The final pass deliberately *lowered* MAPPED (318→293) to be honest: rows with
wrong/unverified targets were downgraded rather than left green.

## Resolved / informed since round 3

| # | Item | Outcome |
|---|------|---------|
| RECIST response | mCODE CancerDiseaseStatus + **LOINC 21976-6** (incl. MR/NYA) on `mii-pr-mtb-response-befund` | RESOLVED (bih-cei A2) |
| Fusion orientation | MTB DNA/RNA-fusion use `component:five-prime-gene`/`three-prime-gene` | RESOLVED → applied as DRAFT until rewired |
| chromosome component | `component:chromosome-identifier` (LOINC 48000-4) | RESOLVED → **fixed** |
| Block cardinalities (RD) | DNPM Datenmodell V2.1 + rd-validation give required/optional/conditional | RESOLVED (dnpm-rd, dnpm-datenmodell) |
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
