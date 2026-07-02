# synthData-v1 — both-path mapping findings

Ran both mappers over the new `example-data/synthData-v1` (2098 files) via the e2e harness,
matchbox reloaded to latest-2026 + tx.fhir.org. Coverage pass = all 1056 oncology files;
KDS `$validate` findings = representative sample of 150 (tx round-trips make full-corpus validation slow).

## Discovery (2098 files)
| branch | files | mapper? |
|---|---|---|
| oncology (`metaData`/`diagnosisOd`; cohorts dnpm 42, nct 500, ukdd 514) | **1056** | yes (both paths) |
| grz (sequencing) | 1000 | no |
| rare-disease (nse) | 42 | no |

## Coverage — both mappers process ALL 1056 oncology files
| | produce | HAPI ingest |
|---|---|---|
| **A (Python)** | **1056 / 1056** | **1056 / 1056** |
| **B (FML `$transform`)** | **1056 / 1056** | 0 / 1056 (known: FML output isn't a transaction bundle) |

Resources emitted (both): Patient 1056, Coverage 1056, Consent 1056, Condition 2598,
Observation (A 1322 / B 1448), Procedure 817, MedicationStatement 817.

## Headline finding — the new data is full-model; the mappers cover only the clinical spine
The synthData-v1 oncology records populate sections the old examples didn't, and **neither mapper maps them** (silently dropped):
- **molecular** — 1034/1056 (smallVariants, copyNumberVariants, complexBiomarkers, expressionVariants) → **no** MolGen/MTB variant resources emitted.
- **plan** — 1037/1056 (carePlanOd, recommendedStudies, recommendedSystemicTherapies, preventiveMeasures) → **no** CarePlan/recommendation resources.
- **tnmClassifications** + **grading** (917) → **no** TNM/grading Observations.
- New dx fields ignored: germlineDiagnoses, hpoTerms, diagnosticAssessment, additionalClassification, libraryType.

So both paths emit a conformant-ish clinical spine but drop the genomic + care-plan payload — the largest gap for this dataset.

## KDS validation (Path A, sample n=150, tx-enabled)
| profile | clean | env | content |
|---|---|---|---|
| PatientPseudonymisiert | 150 | 0 | 0 |
| Vitalstatus | 84 | 0 | 0 |
| mii-pr-onko-…-ecog | 228 | 0 | 0 |
| coverage-de-basis | 134 | 0 | **16** |
| mii-pr-mtb-systemtherapie-medication-statement | 45 | 65 | 0 |
| mii-pr-mtb-diagnose-primaertumor | 0 | 150 | 0 |
| mii-pr-mtb-systemische-vortherapie | 0 | 0 | 110* |
| mii-pr-consent-einwilligung | 0 | 0 | 150 |

- **NEW real bug — Coverage `coverageType='UNK'`** (16/sample; **89/1056 corpus**): `UNK` is not in
  `versicherungsart-de-basis`. New data also uses BEI/SKT/GPV/PPV/SOZ/SEL/BG (all valid); only `UNK`
  fails. Fix: map `UNK` → drop `Coverage.type` (or `data-absent-reason`/`unknown`), don't pass through.
- **consent** (150): the known §64e-vs-MII-Broad-Consent modeling gap (mvSequencing/reIdentification/
  caseIdentification not MII policy codes; provision.period missing) — confirmed on the new data too.
- **env** (need the MII Ontoserver): diagnose (ICD-O-3/ICD-10-GM), medication (ATC). *vortherapie 110
  "matches more than one slice" is the SNOMED-edition-pin artifact on `procedures-sct` (env, not content).

Patient / Vitalstatus / ECOG are **clean on the new data** — the P0 fixes (gender-amtlich, ECOG-5 drop) hold at scale.

## Path B (FML) — systematically behind, and lacks the P0 fixes
Every diagnose/vortherapie/medication/ECOG resource fails on missing `subject` + missing extensions/slices
(`Feststellungsdatum`, `Intention`, `snomed`/`obds`), and Coverage has **no `meta.profile`** (150 no-profile).
Plus Path B lacks the Python P0 fixes: **5 Patient content errors** (gender=other without the amtlich
extension) and it emits **126 more ECOG Observations than Path A** (it doesn't drop out-of-VS ECOG 5).
A↔B resource-count mismatch: **123/150 cases** — mostly this ECOG divergence.

## Net
- Both mappers robustly **ingest the whole new oncology cohort** (Path A end-to-end into HAPI).
- Clinical-spine conformance holds (Patient/Vitalstatus/ECOG clean); the German-terminology rows are
  environmental until the MII Ontoserver cert is wired (see `infra/mii-termserv-proxy/`).
- Two actionable mapper items the new data surfaced: **(1) Coverage `UNK` handling**, **(2)** the long-known
  **molecular/plan/TNM/grading coverage gap** is now the dominant limitation (98% of records carry molecular).
- Path B (FML) parity + P0-fix backport remain backlogged.
