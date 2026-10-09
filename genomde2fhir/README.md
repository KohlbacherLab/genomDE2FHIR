# genomde2fhir

Convert genomDE / MV-GenomSeq (§ 64e SGB V) **Datenkranz** JSON — the BfArM KDK oncology, KDK rare-disease
and GRZ submissions — into **FHIR R4 transaction Bundles** that follow the MII Kerndatensatz profiles of the
**2027.0.0 ballot** and load into any FHIR R4 server.

```bash
pipx install genomde2fhir                      # or: pip install genomde2fhir
pip install "genomde-dk-validator @ git+https://github.com/KohlbacherLab/genomde-dk-validator@v1.1.2"   # input validation (recommended)

genomde2fhir convert submission.json -o out/                     # one <name>.bundle.json per input
genomde2fhir convert data/ --report report.json -o out/          # a directory (recursive), glob or .zip
genomde2fhir convert kdk.json grz.json --single-bundle case.json # several files into one Bundle
genomde2fhir convert data/ -o out/ --validate http://localhost:8091/matchboxv3/fhir --ingest http://localhost:8092/fhir
genomde2fhir validate out/*.bundle.json --matchbox http://localhost:8091/matchboxv3/fhir
genomde2fhir coverage data/                                      # mapping-table rows not emitted
```

Exit codes: `0` ok · `1` some inputs rejected (schema-invalid or unsupported) · `2` conversion errors · `3` validation or ingest failures.

## What it does

- **Input gate**: each file is classified (oncology / rare disease / GRZ) and schema-validated with
  `genomde-dk-validator`; invalid files are rejected with their findings, never silently repaired.
- **Mapping**: one builder per Datenkranz block implements the project's reviewed mapping table
  (`mapping/*.csv` in the repository) and the representation register (`docs/REPRESENTATIONS.md`).
  Where the MII ballot has no conformant element, values go to declared local resources of the
  `de.genomde.mvgs` package (e.g. the MV-GenomSeq consent domains) or are reported as dropped.
- **Idempotent bundles**: every resource has a deterministic id derived from the sender's case key
  (`docs/IDENTITY.md`); entries are `PUT Type/<id>`, so re-submitting a case updates instead of duplicating.
- **Report**: per file the emitted mapping rows, values kept outside a conformant MII element
  (*preserved*), dropped values with reasons, warnings and resource counts (`--report`).
- **Structural check**: every resource is parsed with `fhir.resources`; profile conformance is checked by
  matchbox (`--validate`); each issue is classified as content (a converter defect), source (an invalid code
  copied from the input), unchecked (terminology the server cannot check), cascade or waived package defect.

Profile sets: `--profile-set 2027` (default, MII KDS 2027.0.0 ballot) and `2026` (current 2026 releases; the
builders differ only where the ballot changed an element, e.g. `occurredFollowing`, `basedOn:therapieempfehlung`,
the HRD interpretation; the 2026 output is not part of the E2E run). The ballot is not final; the default does
not change automatically when 2027.0.0 is published.

## Python API

```python
from genomde2fhir import convert_file
bundle, report = convert_file("submission.json", profile_set="2027")
print(report.status, report.resources, sorted(report.dropped))
```

## Validation server

`infra/matchbox-2027/` in the repository runs matchbox 4.1.21 with the 2027 ballot stack and a HAPI store
for ingest tests; `scripts/run_corpus.py` writes `docs/E2E-REPORT-2027.md`.

Licence: MIT. Source: https://github.com/KohlbacherLab/genomDE2FHIR (`genomde2fhir/`).
