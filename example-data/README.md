# Example data — synthetic genomDE Datenkranz submissions

Synthetic (dummy, no PHI) KDK/GRZ submissions for testing the mapping pipeline.
Copied from `genomDE FHIR Mapper/SynthData/mv_dummy_data` (the prior pipeline's
test corpus).

| Dir | Files | Schema root | Notes |
|-----|------:|-------------|-------|
| `oncology/` | 42 | KDK `Oncology.json` | `OncologySubmission_*` — KDK-conformant (camelCase `metaData`) |
| `rarediseases/` | 42 | KDK `RareDiseases.json` | `RareDiseasesSubmission_*` — KDK-conformant |
| `grz/` | 6 | GRZ `grz-schema.json` | 4 paired donor submissions + 2 coverage fixtures |

84 KDK cases (42 + 42) = the project's bulk-transform corpus. All verified to
carry the KDK top-level keys `metaData / case / molecular / plan / followUp`.

## Not copied (deliberately)

The source also held `onco/` (`OncoSubmission_*`) and `rare-diseases/`
(`RDSubmission_*`) variants that use lowercase `metadata` — an older,
non-KDK-conformant naming. Excluded to avoid mixing schema variants; the
conformant `metaData` sets above are what the mapping table was built from
(KDK schema 1.7.1).

GRZ files declare `_paired_with` linking each donor submission to its KDK case
(reflects the GRZ↔KDK stream pairing via the tanG/tanC pseudonyms).
