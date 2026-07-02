# Datenkranz JSON-Schema validation — findings

> The validator has since moved to its own package,
> [**genomde-dk-validator**](https://github.com/KohlbacherLab/genomde-dk-validator) (schemas vendored,
> + unknown-field detection + BfArM QS rules). The findings below still hold. Reproduce with:
> ```bash
> pip install git+https://github.com/KohlbacherLab/genomde-dk-validator.git
> genomde-dk-validator example-data examples
> ```

Validates Datenkranz JSON against the **BfArM JSON Schemas** (`schemas/kdk/` = KDK Oncology +
RareDiseases, `schemas/grz/` = GRZ). Branch auto-detected → root schema
(`Oncology.json` / `RareDiseases.json` / `grz-schema.json`). The KDK schemas `$ref` each other by
absolute BfArM GitHub raw URL; the validator maps those to the local files via a `referencing`
Registry, so it runs **fully offline** against the pinned local schema copies.

## Result (2362 files)
| branch | total | valid | invalid |
|---|---|---|---|
| oncology | 1186 | 668 | 518 |
| rare-disease | 168 | 126 | 42 |
| grz | 1008 | 459 | 549 |

## By cohort (the invalids are concentrated, not uniform)
| cohort | branch | valid / invalid | verdict |
|---|---|---|---|
| synthData-v1/dnpm | oncology | 42 / 0 | ✅ clean |
| synthData-v1/ukdd | oncology | 514 / 0 | ✅ clean |
| synthData-v1/nse | rare-disease | 42 / 0 | ✅ clean |
| **synthData-v1/nct** | oncology | **24 / 476** | ❌ schema-invalid |
| **synthData-v1/grz** | grz | **451 / 549** | ❌ schema-invalid |
| example-data/oncology, rarediseases, grz | mixed | all valid | ✅ clean |
| examples/oncology, rarediseases, synthetic-coverage-fixtures, grz | mixed | all valid | ✅ clean |
| **examples/onco, examples/rare-diseases** | — | **0 / 84** | ⚠️ legacy artifact |

## What's actually wrong (real, in the new data)

### synthData-v1/nct (476/500 invalid)
- `case.diagnosisOd.tnmClassifications[].version` — **required, missing** (42+ files).
- `plan.recommendedStudies[].priority` / `recommendedSystemicTherapies[].priority` — sent as a
  **string** (`"2"`) but schema requires **integer**. (Same field also breaks the FHIR mapping.)
- `followUp.followUpOds[].therapies[].reference` — **required, missing**.

### synthData-v1/grz (549/1000 invalid)
- `donors[].researchConsents[].presentationDate` — **required, missing** (on multi-donor
  submissions; donor index 0/1/2). Single-donor GRZ files validate.

### examples/onco + examples/rare-diseases (84) — not a new-data problem
Old dummy files use the lowercase key `metadata`; the schema requires `metaData`. These predate
the current schema (the newer `examples/oncology` + `examples/rarediseases` use `metaData` and
validate). Safe to ignore or delete.

## Takeaways
- The validator is a fast, offline, pre-mapping gate: it catches source-data defects **before**
  FHIR conversion (e.g., the `priority`-as-string and missing-TNM-`version` issues that otherwise
  surface deep in mapping/validation).
- **The new `nct` and multi-donor `grz` cohorts have genuine schema violations** — worth raising
  with whoever generated synthData-v1; the `dnpm`/`ukdd`/`nse` cohorts are schema-clean.
- Full per-file errors: `out/validation/schema-report.json`.
