# genomde2fhir

Convert genomDE / MV-GenomSeq (§ 64e SGB V) **Datenkranz** JSON — the BfArM KDK oncology, KDK rare-disease
and GRZ submissions — into **FHIR R4 transaction Bundles** that follow the MII Kerndatensatz profiles of the
**2027.0.0 ballot** and load into any FHIR R4 server.

```bash
pipx install genomde2fhir
pipx inject genomde2fhir "genomde-dk-validator @ git+https://github.com/KohlbacherLab/genomde-dk-validator@v1.1.2"   # input gate (required unless --no-input-check)
# or, in a virtualenv: pip install genomde2fhir "genomde-dk-validator @ git+https://github.com/KohlbacherLab/genomde-dk-validator@v1.1.2"

genomde2fhir convert submission.json -o out/                     # one <name>.bundle.json per input
genomde2fhir convert data/ --report report.json -o out/          # a directory (recursive), glob or .zip
genomde2fhir convert kdk.json grz.json --single-bundle case.json # several files into one Bundle (submission order)
genomde2fhir convert data/ -o out/ --validate http://localhost:8091/matchboxv3/fhir --ingest http://localhost:8092/fhir
genomde2fhir validate out/*.bundle.json --matchbox http://localhost:8091/matchboxv3/fhir
genomde2fhir coverage data/                                      # mapping-table rows not emitted
```

Exit codes of `convert`: `0` ok · `1` some inputs rejected (schema-invalid, unsupported, not JSON, or failed
`--strict`), no input found, or genomde-dk-validator missing · `2` conversion errors or missing paths · `3`
validation verdict FAIL or ERROR, ingest failures, an unreachable server, or a `--validate` matchbox whose MII KDS
packages do not match `--profile-set` (the report is still written; it is not written when `convert` stops before
reading any input: validator missing, no input found).
`validate`: `0` ok · `1` no input · `2` unreadable or non-Bundle files · `3` FAIL or ERROR verdicts.
`coverage`: `0` no gaps · `1` inputs rejected or unreadable (not counted) or no input · `2` converter errors or
missing paths · `4` mapping-table gaps remain (precedence 2 > 4 > 1; a builder crash on a schema-invalid input
counts as rejected, since coverage runs without the input gate).

- Without genomde-dk-validator `convert` refuses to run and prints how to add it (`pipx inject genomde2fhir ...` for a
  pipx install, whose environment has no pip; `pip install ...` with the interpreter that runs genomde2fhir);
  `--no-input-check` converts without the input gate.
- Inputs: files, directories (recursive; `*.json` and `*.zip` in any case), `.zip` archives and globs. An existing
  path is taken literally, a file reached twice is converted once, hidden files and directories (also inside
  archives) are skipped. One bad or missing file does not stop the batch.
- Input fields the schema does not declare are reported per field as a warning, judged by the report's
  dispositions: `converted` when a builder covered or preserved the path, `dropped` when it dropped it (reason under
  *dropped*), otherwise `not converted`; stderr counts them. Fields the converter maps although the schema does not
  declare them (legacy keys such as `case.priorRd`, `germlineDiagnoses[].date`, RD `genes[].display`) count as
  `converted`. `--strict` is schema-strict like `genomde-dk-validator --strict`: it rejects a file (exit 1, reason in
  the report) on unknown mapping paths or canonicals, structural errors or any undeclared input field, converted or
  not, with no exception; the other files are still converted. So `--strict` rejects all 42 rare-disease example
  files (`examples/rarediseases/`, the `mv_dummy_data` revision of 2026-08-09): they
  carry `molecular.*Variants[].genes[].system` / `.display` and `localization[].system` / `.display`, which neither the
  vendored nor the upstream KDK schema declares (`example-data/README.md`); the 42 oncology examples pass.
- `-o` writes `<name>.bundle.json`; when two inputs share a name the later one is written as
  `<parent>_<name>.bundle.json` (or `<name>-<n>`) and stderr says so. Leading dots are dropped, so no bundle is a
  hidden file, and a parent written as `..` is not used (the counter decides). With `--single-bundle FILE` a
  relative FILE goes into the `-o` directory; inputs are applied by submission date, then initial <
  followup/addition < correction, so a correction wins; `--ingest` posts in the same order. No file is written
  when nothing converts.
- stderr carries counts only: `genomde2fhir <version> [<profile set>]: N file(s) {status: n} resources=N
  types={submission type: n} test=N tan-fallback=N`, then lines for files not converted, undeclared fields, output
  name clashes and validation / ingest results. `-v` adds a line per file: file names and findings can contain
  pseudonyms or TANs.
- Decimals keep their written precision in the written bundles and report (`12.50` stays `12.50`).

## What it does

- **Input gate**: each file is classified (oncology / rare disease / GRZ) and schema-validated with
  `genomde-dk-validator`; invalid files are rejected with their findings, never silently repaired.
- **Mapping**: one builder per Datenkranz block implements the project's reviewed mapping table
  (`mapping/*.csv` in the repository) and the representation register (`docs/REPRESENTATIONS.md`).
  Where the MII ballot has no conformant element, values go to declared local resources of the
  `de.genomde.mvgs` package (e.g. the MV-GenomSeq consent domains) or are reported as dropped.
- **Idempotent bundles**: every resource has a deterministic id derived from the sender's case key
  (`docs/IDENTITY.md`); entries are `PUT Type/<id>`, so re-submitting a case updates instead of duplicating.
  Each submission adds its own Provenance (submission type as v3-DataOperation, sender and data-node agents,
  targets = every resource of the bundle); a GRZ follow-up or addition gets its own genomic study, while a
  correction rewrites the initial one. Every resource carries `meta.source =
  urn:genomde2fhir:submission:<submitterId>:<caseId>:<date>:<type>` (components percent-encoded), so resources a
  correction no longer sends stay identifiable: corrections never delete server resources. Test submissions
  (`type` / `submissionType` = `test`) are converted in a separate identity namespace and labelled
  `meta.security` v3-ActReason `HTEST`; the report carries `submission_type`, `test` and `case_key_fallback`.
- **Report**: per file the emitted mapping rows, values kept outside a conformant MII element
  (*preserved*), dropped values with reasons, warnings and resource counts (`--report`).
- **Structural check**: every resource is parsed with `fhir.resources`; profile conformance is checked by
  matchbox (`--validate`). Each issue is classified: content (a converter defect) -> FAIL, source (an invalid code
  copied from the input) -> DATA-QUALITY, unchecked (terminology the server cannot check) -> INCONCLUSIVE,
  validator-error (validation could not run: server unreachable, HTTP error, unusable response, unknown profile)
  -> ERROR, never PASS; reported only: cascade (a reference failure explained by an own error of the target,
  counted there), candidate (errors against a profile the resource does not declare, raised while matchbox tried
  it as a reference target), waived package defects and warnings. Verdict precedence ERROR > FAIL > DATA-QUALITY >
  INCONCLUSIVE > PASS.

Profile sets: `--profile-set 2027` (default, MII KDS 2027.0.0 ballot) and `2026` (current 2026 releases; the
builders differ only where the ballot changed an element, e.g. `occurredFollowing`, `basedOn:therapieempfehlung`,
the HRD interpretation; the 2026 output is not part of the E2E run). The ballot is not final; the default does
not change automatically when 2027.0.0 is published. `--validate` checks the MII KDS package versions the
matchbox holds: 2026 output is validated only on a matchbox that shows the 2026 KDS packages, never against the
2027 ballot (`--profile-set 2026 --validate <matchbox-2027>` gives verdict ERROR "not validated: ... holds KDS
packages of 2027 profile set, not 2026", exit 3). `scripts/run_corpus.py --profile-set 2026` needs
`--matchbox-2026`.

## Python API

```python
from pathlib import Path
from genomde2fhir import convert_file
from genomde2fhir.io import dumps
bundle, report = convert_file("submission.json", profile_set="2027")
print(report.status, report.resources, sorted(report.dropped))
if bundle is not None:   # None when the input is rejected
    Path("out.bundle.json").write_text(dumps(bundle), encoding="utf-8")   # keeps decimal spellings (58.50)
```

`convert_file` reads with `genomde2fhir.io.loads`, so input decimals keep their written precision; write the
bundle with `genomde2fhir.io.dumps` (`json.dumps` would write `58.50` as `58.5`). Unlike the CLI, the Python API
converts without genomde-dk-validator and only adds an `input validation skipped` note to
`report.input_findings`. With the validator, undeclared fields appear there as `unknown field <pointer>`; the
rejection of undeclared fields is a CLI `--strict` feature (`convert(..., strict=True)` raises on unknown mapping
paths or canonicals, builder errors and structural errors only).

## Validation server

`infra/matchbox-2027/` in the repository runs matchbox 4.1.21 with the 2027 ballot stack and a HAPI store
for ingest tests; `scripts/run_corpus.py` writes `docs/E2E-REPORT-2027.md`.

Licence: MIT. Source: https://github.com/KohlbacherLab/genomDE2FHIR (`genomde2fhir/`).
