# Example data — synthetic genomDE Datenkranz submissions

Synthetic (dummy, no PHI) KDK/GRZ submissions for testing the mapping pipeline.
The KDK files come from the upstream `mv_dummy_data` test corpus (originally copied
from `genomDE FHIR Mapper/SynthData/mv_dummy_data`, the prior pipeline's test corpus).
`examples/oncology/` and `examples/rarediseases/` hold the same files as the two KDK
directories here. Both copies are tracked in git and both are listed in
`genomde2fhir/tests/corpus_manifest.json`, so tests and CI use either; only
`synthData-v1/` is untracked. `examples/grz/` holds only the 4 paired donor submissions
(the 2 coverage fixtures are in `example-data/grz/` alone).

| Dir | Files | Schema root | Notes |
|-----|------:|-------------|-------|
| `oncology/` | 42 | KDK `Oncology.json` | `OncologySubmission_*` — KDK-conformant (camelCase `metaData`) |
| `rarediseases/` | 42 | KDK `RareDiseases.json` | `RareDiseasesSubmission_*` — KDK-conformant |
| `grz/` | 6 | GRZ `grz-schema.json` | 4 paired donor submissions + 2 coverage fixtures |

84 KDK cases (42 + 42) = the project's bulk-transform corpus. All carry the KDK
top-level keys `metaData / case / molecular / plan / followUp`, and all are valid
for genomde-dk-validator (schema; non-strict) — see `genomde2fhir/tests/corpus_manifest.json`.

## Revision of 2026-08-09 (`mv_dummy_data`)

On 2026-10-10 the KDK files were replaced with the `mv_dummy_data` revision of
2026-08-09 (42 oncology + 42 rare-disease files; submission dates 2026-09-08).
Every file whose name matched got the new content; the 3 rare-disease files new in
that revision were added (`RareDiseasesSubmission_147F575A…`, `_3249DE06…`, `_CD9961FC…`).
The 3 older rare-disease files that the revision no longer contains
(`_423C3C2F…`, `_42A16CA6…`, `_F11F0DB1…`, submission date 2026-04-21) were removed
from both `rarediseases/` copies (they remain in git history) — hence 42 rare-disease
files, all from the revision. `grz/` was not touched.

What changed against the earlier copies:

- Oncology: `case.priorDiagnostic` (one object) became `case.priorDiagnostics[]` (an array
  of `{date, type}`), as in the current KDK schema.
- Rare diseases: `plan.recommendedTherapies[].variantReferences[]` and
  `plan.recommendedStudies[].variantReferences[]` became `…variants[]`.
- Rare diseases: `case.priorRd` (diagnostic date/result, genomic study/test type,
  hospitalisation, ZSE contact) was removed.
- Unchanged: `metaData.submission.type` is `test` in all files (old and new).
- Unchanged, still present in the rare-disease files: fields the KDK schema does not
  declare — `molecular.*Variants[].genes[].system` / `.display` and
  `molecular.*Variants[].localization[].system` / `.display`. genomde-dk-validator
  reports them as unknown fields, so these files pass only non-strict; the oncology files
  of this revision have no undeclared fields.

The legacy keys (`priorDiagnostic`, `priorRd`, `variantReferences`) no longer occur in
the example files. Tests that need the legacy keys use small synthetic fixtures under
`genomde2fhir/tests/fixtures/legacy_keys/` (derived from the 2026-08-09 files, keys renamed back).

## Not copied (deliberately)

The source also held `onco/` (`OncoSubmission_*`) and `rare-diseases/`
(`RDSubmission_*`) variants that use lowercase `metadata` — an older,
non-KDK-conformant naming. Excluded to avoid mixing schema variants; the
conformant `metaData` sets above are what the mapping table was built from
(KDK schema 1.7.1).

GRZ files declare `_paired_with` linking each donor submission to its KDK case
(reflects the GRZ↔KDK stream pairing via the tanG/tanC pseudonyms).
