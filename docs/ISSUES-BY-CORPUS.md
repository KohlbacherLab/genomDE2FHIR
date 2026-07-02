# Issues by corpus

Every example-data / examples directory, with its issues on three axes:
- **S — schema validity** (source JSON vs authoritative BfArM schema; `scripts/validate_datenkranz.py`).
- **M — mapper coverage** (sections the mappers silently drop).
- **C — KDS conformance / terminology** (mapper output vs MII profiles; `scripts/e2e_harness.py`).

M and C are content-driven and apply to any oncology/RD corpus that populates the relevant sections;
they are noted per corpus by what that corpus actually contains. GRZ has no FHIR mapper yet.

## Summary

| corpus | branch | n | schema valid/invalid | headline issue |
|---|---|---|---|---|
| example-data/synthData-v1/dnpm | onc | 42 | 42 / 0 | ✅ schema-clean; M+C apply |
| example-data/synthData-v1/ukdd | onc | 514 | 514 / 0 | ✅ schema-clean; **UNK 55, gender-other 130** |
| example-data/synthData-v1/nct | onc | 500 | **24 / 476** | ❌ `identifier`/`variants`/`reference` sent as objects, schema wants string |
| example-data/synthData-v1/nse | RD | 42 | 42 / 0 | ✅ schema-clean; M+C apply |
| example-data/synthData-v1/grz | grz | 1000 | **451 / 549** | ❌ multi-donor `researchConsents.presentationDate` missing; no FHIR mapper |
| example-data/oncology | onc | 42 | 42 / 0 | ✅ schema-clean; M+C apply |
| example-data/rarediseases | RD | 42 | 42 / 0 | ✅ schema-clean; M+C apply |
| example-data/grz | mix | 6 | 6 / 0 | ✅ schema-clean; no FHIR mapper (grz) |
| examples/oncology | onc | 42 | 42 / 0 | ✅ (SynthData copy) |
| examples/rarediseases | RD | 42 | 42 / 0 | ✅ (SynthData copy) |
| examples/synthetic-coverage-fixtures | onc | 2 | 2 / 0 | ✅ |
| examples/grz | grz | 4 | 4 / 0 | ✅ no FHIR mapper |
| examples/onco | onc | 42 | **0 / 42** | ⚠️ legacy lowercase `metadata` dummies (pre-schema) |
| examples/rare-diseases | RD | 42 | **0 / 42** | ⚠️ legacy lowercase `metadata` dummies (pre-schema) |

## Cross-cutting issues (apply to every oncology / RD corpus)

- **M1 — molecular unmapped** (smallVariants/CNV/complexBiomarkers/expression/SBS/structural): no
  MolGen/MTB variant resources emitted. Populated in ~98% of oncology records.
- **M2 — plan/recommendations unmapped** (carePlanOd, recommendedStudies/Therapies, preventiveMeasures).
- **M3 — TNM + grading unmapped**.
- **C1 — consent §64e modelling** (all onc+RD): `mvSequencing`/`reIdentification`/`caseIdentification`
  are not MII Broad-Consent policy codes; provision periods missing. Real MII consent arrives separately
  via `researchConsents` (passthrough).
- **C2 — German terminology environmental** (all onc+RD): ICD-10-GM / ICD-O-3 / ATC can't validate on
  tx.fhir.org; needs the MII SU-TermServ Ontoserver (`infra/mii-termserv-proxy/`).
- **C3 — vortherapie SNOMED** (`procedures-sct` pins a SNOMED edition tx.fhir.org can't resolve) →
  "matches more than one slice"; environmental, clears with a proper tx.

## Per-corpus detail

### example-data/synthData-v1/nct (500) — ❌ schema-invalid (476)
- **S:** `type` errors — `identifier` is an **object `{system,value}`** but KDK `Identifier` is a
  **string**. Affects molecular `identifier` (smallVariants 368, complexBiomarkers 347, CNV 209,
  sbsSignatures 205, structural 126, expression 102), plan `identifier` (recommendedSystemicTherapies
  431, recommendedStudies 152, preventiveMeasures 72), `plan…variants[]` (351/102),
  `followUp…therapies[].reference` (98). 3 files also fail `/molecular` type.
- **Also:** coverageType=`UNK` (34), gender=`other` (24). M1–M3, C1–C3 apply.

### example-data/synthData-v1/ukdd (514) — ✅ schema-clean; heaviest mapper load
- **C — Coverage `UNK`** (55): not in `versicherungsart-de-basis`.
- **gender=`other`** (130): Python adds gender-amtlich ext (clean); **FML fails** (no P0 fix).
- **out-of-VS ECOG** (120): Python drops with warning; **FML emits invalid**.
- M1–M3, C1–C3 apply.

### example-data/synthData-v1/grz (1000) — ❌ schema-invalid (549); no FHIR mapper
- **S:** `donors[].researchConsents[].presentationDate` required but missing — donor 0 (433),
  donor 1 (174), donor 2 (96). Single-donor files validate. No GRZ→FHIR mapper exists.

### example-data/synthData-v1/dnpm (42), nse (42); example-data/oncology (42), rarediseases (42) — ✅ schema-clean
- Reference cohorts, schema-valid. gender-other (1 each), out-of-VS ECOG (dnpm/oncology 3 each).
  M1–M3, C1–C3 apply (molecular/plan/TNM dropped; consent + German-terminology as above).

### examples/onco (42), examples/rare-diseases (42) — ⚠️ legacy artifact
- **S:** use lowercase `metadata` (schema requires `metaData`) → also cascade `tnmClassifications.version`,
  `phenotypes.version`, `molecular…identifier`, `followUpRds`, `carePlanRd`, `therapies.reference`.
  These are old dummy files predating the current schema; superseded by `examples/oncology` +
  `examples/rarediseases` (metaData, valid). Safe to delete.

### examples/oncology, rarediseases, synthetic-coverage-fixtures, grz; example-data/grz — ✅ clean
- Schema-valid. Oncology/RD ones carry the usual M/C cross-cutting items; grz has no mapper.
