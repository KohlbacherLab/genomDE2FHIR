# genomDE2FHIR

Mapping from **BfArM Modellvorhaben Genomsequenzierung (§64e SGB V)** submission data
(genomDE Datenkranz) into **MII Kerndatensatz (KDS)** FHIR R4 resources.

The project has three deliverables, all on the **MII KDS 2027.0.0 ballot** (plan: [`docs/PLAN-2027.md`](docs/PLAN-2027.md)):

| | Deliverable | Where |
|:--|:--|:--|
| (a) | `genomde2fhir` — pip package: one or many Datenkranz JSON files (KDK oncology, KDK rare disease, GRZ) → loadable FHIR R4 transaction Bundles | [`genomde2fhir/`](genomde2fhir/README.md) |
| (b) | FML StructureMaps for matchbox `$transform` → HAPI, at parity with (a) | [`mappers/`](mappers/README.md), `mappers/fml/`, `scripts/load_datenkranz.sh` |
| (c) | matchbox validation of the bundles (per resource + per bundle, classified verdicts) | `genomde2fhir validate`, `infra/matchbox-2027/`, `scripts/run_corpus.py` → [`docs/E2E-REPORT-2027.md`](docs/E2E-REPORT-2027.md) |

The **mapping table** (`mapping/*.csv`, leaf level, GRZ and KDK kept separate) is the central reference and
specification; both implementations follow it, and it is kept in step with them. Reference mapping: Thomas
Debertshäuser's annotated table of 2026-10-06 (`docs/REVIEW-TD-2026-10-06.md`, `docs/DISCUSS-TD-2026-10-09.md`).
Adversarial CLI review (`vibe`, `codex`, `kimi`) is used at critical steps.

## Source schemas

Vendored from the authoritative BfArM repos and **verified byte-identical** to upstream — see
[`schemas/PROVENANCE.md`](schemas/PROVENANCE.md) for exact tags + a refresh/verify command.

| Source | Local | Repo | Release tag | Schema content version | Roots |
|--------|-------|------|-------------|------------------------|-------|
| KDK | `schemas/kdk/` | BfArM-MVH/MVGenomseq_KDK | v2.3 + `main` `fe724ff` | **1.7.1** | `Oncology.json`, `RareDiseases.json` |
| GRZ | `schemas/grz/` | BfArM-MVH/MVGenomseq_GRZ | v1.3.1 | **1.2.3** (schema `version` 1.3.1) | `grz-schema.json` |

(The repos tag releases `v2.x`/`v1.3.x`; each schema's own CHANGELOG uses a content version —
1.7.1 / 1.2.3 — and the latest tag ships the latest content. KDK is pinned one untagged commit past v2.3:
`fe724ff` widens the embedded consent's `schemaVersion` enum to 2025.0.1–2026.0.1, as GRZ v1.3.1 does. KDK `develop`
has further unreleased changes, not vendored: `schemas/PROVENANCE.md`.)

Target: MII KDS profiles, FHIR R4 (4.0.1), **2027.0.0 ballot** (default profile set; the 2026 releases remain
selectable with `--profile-set 2026`). Package pins and the 2026 → 2027 change analysis: `docs/PLAN-2027.md` §2,
`docs/2027-BALLOT-DIFF.md`.

## The mapping table

Three CSVs under `mapping/` — the editable, version-controlled central reference:
`mapping_kdk_oncology.csv` (229 leaves), `mapping_kdk_rarediseases.csv` (132 leaves + 3 rows for non-schema
fields the converter reads), `mapping_grz.csv` (67).
Columns: source side (`path,type,required,array,enum,format,description`, auto-extracted) + target
side (`mii_module,mii_profile,fhir_element,transform,status,notes`, hand-filled).
`status` ∈ {TODO, MAPPED, DRAFT, NOMAP, REMOVED?}. Online-editable mirror: Google Sheet (round-trip
via `scripts/export_xlsx.py` / `sync_from_sheet.py`; git CSVs stay source of truth).

Regenerate the skeleton idempotently after a schema bump (hand-filled columns preserved):
```bash
bash scripts/regen-mapping.sh
```

## Quick start

```bash
pipx install ./genomde2fhir            # (a); PyPI publication pending
pipx inject genomde2fhir "genomde-dk-validator @ git+https://github.com/KohlbacherLab/genomde-dk-validator@v1.1.3"
genomde2fhir convert data/ -o out/ --report report.json
genomde2fhir validate out/*.bundle.json --matchbox http://localhost:8091/matchboxv3/fhir   # (c)

docker compose -f infra/matchbox-2027/docker-compose.yml up -d    # matchbox-2027 :8091 + HAPI-2027 :8092
python scripts/build_mvgs.py --install http://localhost:8091/matchboxv3/fhir --maps          # (b) package + maps
scripts/load_datenkranz.sh submission.json                         # (b) $transform -> HAPI
python scripts/run_corpus.py --sample 25 --fml                     # E2E: both paths, validation, ingest, parity
```

`convert` checks every input against the BfArM schemas with
[genomde-dk-validator](https://github.com/KohlbacherLab/genomde-dk-validator) (not on PyPI; the pipx environment
has no pip, hence `pipx inject`). Without it `convert` refuses to run (exit 1) unless `--no-input-check` is given.
`-v` prints per-file lines on stderr, which can contain
TANs or pseudonyms; `--strict` also rejects input fields the schema does not declare. That rejects all 42
rare-disease example files (`examples/rarediseases/`, the `mv_dummy_data` revision of 2026-08-09): they carry `molecular.*Variants[].genes[].system` and `localization[].system` / `.display`,
which the vendored KDK schema does not declare (nor does the upstream schema; RD `genes[].display` is undeclared too,
but converted). Without `--strict` they convert; the 42 oncology examples pass `--strict`
([`example-data/README.md`](example-data/README.md)).

The local package `de.genomde.mvgs` (`mvgs-ig/`) holds the logical models of the three Datenkranz branches and the
local profiles, extensions, CodeSystems and ConceptMaps used where the ballot has no conformant element
([`docs/REPRESENTATIONS.md`](docs/REPRESENTATIONS.md)). Resource identity and idempotent re-submission:
[`docs/IDENTITY.md`](docs/IDENTITY.md).

## Validators & harness

- **Datenkranz validator** — a standalone repo/package,
  [**genomde-dk-validator**](https://github.com/KohlbacherLab/genomde-dk-validator): validates a
  Datenkranz file (or tree) against the BfArM JSON Schemas offline (schemas vendored), with
  unknown-field detection and the BfArM Qualitätssicherung semantic rules (`--kdk-rules` /
  `--grz-rules`). (`scripts/validate_datenkranz.py` is now just a pointer to it.)
  ```bash
  pip install git+https://github.com/KohlbacherLab/genomde-dk-validator.git
  genomde-dk-validator example-data examples
  genomde-dk-validator --kdk-rules example-data/synthData-v1/nct
  ```
- **E2E harness (2027)** — `scripts/run_corpus.py`: converts the whole corpus (schema-invalid inputs must be
  rejected; manifest files not in the checkout are skipped and counted), validates a sample per branch with
  matchbox-2027, ingests into HAPI-2027 twice (the second transaction must answer 200 for every entry and leave the
  uncached resource counts unchanged), and with `--fml` runs the FML maps, validates and ingests their bundles and
  compares them graph-aware with the Python output → `docs/E2E-REPORT-2027.md`. `--gate` exits 1 on any failure
  (nightly CI). A matchbox whose KDS packages belong to the other profile set is refused: not validated, and
  `--gate` fails. `--profile-set 2026` writes `docs/E2E-REPORT-2026.md` and validates only with
  `--matchbox-2026 URL`; without it the run is reported as 'passed without validation'.
  (`scripts/e2e_harness.py` / `docs/E2E-REPORT.md` are the 2026 prototype run.)

<a name="validation-terminology"></a>
## Validation & terminology setup

`infra/matchbox-2027/`: matchbox 4.1.21 (`:8091`) with the 2027 ballot stack (onkologie/mtb/molgen
2027.0.0-ballot.1, seltene/consent/base/meta/… 2027.0.0-ballot, de.basisprofil 1.6.0, GR 3.0.0) plus
`de.genomde.mvgs`, and HAPI 8.4 (`:8092`) as ingest target. `scripts/build_matchbox_cache.py` patches the package
cache (matchbox's H2 store cannot hold StructureDefinitions with types longer than 100 characters).
Terminology: `tx.fhir.org` validates SNOMED, LOINC, UCUM, HGVS, NCIt and ICD-O-3 (edition 2000 only); it does not serve
the German BfArM terminologies (ICD-10-GM, OPS, ATC, Alpha-ID) or Orphanet/HPO/HGNC/SO/ClinGen. Such issues are
classified *unchecked* (verdict INCONCLUSIVE), never silently passed; details in
[`docs/TERMINOLOGY-CAPABILITY.md`](docs/TERMINOLOGY-CAPABILITY.md). The MII SU-TermServ Ontoserver needs a client
certificate (mTLS proxy scaffold: [`infra/mii-termserv-proxy/`](infra/mii-termserv-proxy/README.md)). The shared
2026 matchbox (`:8090`, sibling project) is untouched.

## Key documents (`docs/`)

- [`PLAN-2027.md`](docs/PLAN-2027.md) — implementation plan for (a)–(c) on the 2027 ballot, with status.
- [`2027-BALLOT-DIFF.md`](docs/2027-BALLOT-DIFF.md) — package changes 2026 → 2027 ballot.
- [`REPRESENTATIONS.md`](docs/REPRESENTATIONS.md), [`IDENTITY.md`](docs/IDENTITY.md) — representation register, identity scheme.
- [`E2E-REPORT-2027.md`](docs/E2E-REPORT-2027.md) — latest corpus run (verdicts, ingest, FML parity).
- [`BALLOT-COMMENTS-2027.md`](docs/BALLOT-COMMENTS-2027.md) — draft ballot comments (German).
- [`REVIEW-TD-2026-10-06.md`](docs/REVIEW-TD-2026-10-06.md), [`DISCUSS-TD-2026-10-09.md`](docs/DISCUSS-TD-2026-10-09.md) — reference mapping review and call agenda.
- [`TERMINOLOGY-CHECK.md`](docs/TERMINOLOGY-CHECK.md), [`TERMINOLOGY-CAPABILITY.md`](docs/TERMINOLOGY-CAPABILITY.md) — mapping-table code check; what the tx server can check.
- `REVIEW-*.md` — adversarial-review rounds; `OPEN-ISSUES.md`, `FIX-PLAN.md`, `E2E-REPORT.md` — 2026 prototype phase.

## Status (2026-10-10, after four review-fix rounds)

- Mapping table reconciled with the implementation: oncology 215 / rare disease 111 / GRZ 44 MAPPED rows; terminology
  gate INVALID 0 / MISMATCH 0; coverage over all corpora: 0 MAPPED rows without emission.
- (a) converts every schema-valid corpus file (oncology 668, rare disease 132, GRZ 459) and rejects every invalid one
  (1,025); bundles ingest into HAPI with 2xx twice (the idempotency check is now uncached). KDK and GRZ handle the
  submission block alike (same submitter / clinical-data-node / genomic-data-center Organizations and Provenance
  agents, `builders/submission.py`); the KDK examples are the `mv_dummy_data` revision of 2026-08-09
  ([`example-data/README.md`](example-data/README.md)).
- (b) all six maps transform every valid corpus file; graph-aware parity with (a) under the deep `canonical()` of
  `scripts/run_corpus.py`, re-measured after fix round 4: 0 differences over 1,259 manifest files (oncology 668, rare
  disease 132, GRZ 459) and the 84 `mv_dummy_data` examples, no duplicate fullUrl or conditional URL; HAPI ingest of
  a validated sample 2xx twice, the second ingest creating nothing.
- (c) sampled bundles: no converter content errors; remaining errors are invalid codes copied from the synthetic input
  (DATA-QUALITY), terminologies the tx server cannot check (INCONCLUSIVE) or listed ballot package defects (waived;
  reported as ballot comments). Re-checked after fix round 4 on a sample (8 files per branch plus 2 examples per KDK
  branch): 0 content errors on both paths, FML verdicts equal to Python; the full 25-per-branch corpus run
  (`docs/E2E-REPORT-2027.md`) is still to be repeated.
- Verdicts (`genomde2fhir validate`, `convert --validate`, the harness), by precedence: **ERROR** (validation could
  not run: server unreachable, HTTP error, no usable OperationOutcome, unknown profile; never PASS) > **FAIL** (a
  `content` issue: a conformance error in our output) > **DATA-QUALITY** (a `source` issue: an unknown code copied
  verbatim from the input) > **INCONCLUSIVE** (an `unchecked` issue: terminology the tx server cannot check, for a
  system the binding admits) > **PASS**. Reported but never failing: `waived` (listed ballot package defects),
  `cascade` (a reference failure explained by an own error of its target, counted there), `candidate` (errors
  against a profile the resource does not declare, raised while matchbox tried it as a reference target) and
  warnings. Details: `docs/PLAN-2027.md` §11, `docs/TERMINOLOGY-CAPABILITY.md`.
- Numbers per run: `docs/E2E-REPORT-2027.md`. Open items: `docs/PLAN-2027.md` §11.
