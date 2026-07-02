# genomDE2FHIR

Mapping from **BfArM Modellvorhaben Genomsequenzierung (§64e SGB V)** submission data
(genomDE Datenkranz) into **MII Kerndatensatz (KDS)** FHIR R4 resources.

The project proceeds in two stages:

1. **Mapping table** — a leaf-level table mapping every leaf of the genomDE Datenkranz to its
   MII KDS target (GRZ and KDK kept separate). The table is the project's **central reference**;
   both mappers are implementations of it.
2. **Mappers** (in progress) — a Python mapping script and a FHIR StructureMap / FML pipeline for
   HAPI/matchbox, both generated from the table, plus an end-to-end test + validation harness.

Adversarial CLI review (`vibe`, `codex`) is used at critical steps.

## Source schemas

Vendored from the authoritative BfArM repos and **verified byte-identical** to upstream — see
[`schemas/PROVENANCE.md`](schemas/PROVENANCE.md) for exact tags + a refresh/verify command.

| Source | Local | Repo | Release tag | Schema content version | Roots |
|--------|-------|------|-------------|------------------------|-------|
| KDK | `schemas/kdk/` | BfArM-MVH/MVGenomseq_KDK | v2.3 | **1.7.1** | `Oncology.json`, `RareDiseases.json` |
| GRZ | `schemas/grz/` | BfArM-MVH/MVGenomseq_GRZ | v1.3.0 | **1.2.3** | `grz-schema.json` |

(The repos tag releases `v2.x`/`v1.3.0`; each schema's own CHANGELOG uses a content version —
1.7.1 / 1.2.3 — and the latest tag ships the latest content.)

Target: MII KDS profiles, FHIR R4 (4.0.1). Validation runs against latest KDS packages (2026 where
published — onkologie 2026.0.3, mtb 2026.0.1, consent/meta 2026.0.0, medikation 2026.0.1,
molgen 2026.0.4, basisprofil 1.6.0; person/diagnose/prozedur/fall at 2025.0.1). See
[`ref-matchbox-tx-setup`](#validation-terminology).

## The mapping table

Three CSVs under `mapping/` — the editable, version-controlled central reference:
`mapping_kdk_oncology.csv` (229 leaves), `mapping_kdk_rarediseases.csv` (132), `mapping_grz.csv` (67).
Columns: source side (`path,type,required,array,enum,format,description`, auto-extracted) + target
side (`mii_module,mii_profile,fhir_element,transform,status,notes`, hand-filled).
`status` ∈ {TODO, MAPPED, DRAFT, NOMAP, REMOVED?}. Online-editable mirror: Google Sheet (round-trip
via `scripts/export_xlsx.py` / `sync_from_sheet.py`; git CSVs stay source of truth).

Regenerate the skeleton idempotently after a schema bump (hand-filled columns preserved):
```bash
bash scripts/regen-mapping.sh
```

## Mappers (oncology branch)

Both implement the table's MAPPED clinical spine — Patient, Coverage, Consent, primary + additional
Condition, ECOG, prior systemic therapy (Procedure + MedicationStatement), vital status.
Molecular / plan / TNM / grading are not mapped yet (tracked in OPEN-ISSUES).

- **Python** — `mappers/python/genomde_to_fhir.py` (`fhir.resources`): DK oncology JSON → transaction
  Bundle. Emits + HAPI-ingests all synthetic oncology cases; Patient/Vitalstatus/Coverage/ECOG
  validate clean against MII profiles.
- **FML** — `mappers/fml/genomde-oncology-to-mii.map` (+ `DatenkranzOncology.logical.json`): the same
  spine for matchbox/HAPI `$transform`. Behind the Python mapper (subject refs, transaction entries,
  conformance parity — backlogged; see OPEN-ISSUES / FIX-PLAN).

## Validators & harness

- **Schema validator** — `scripts/validate_datenkranz.py`: validates a Datenkranz file (or tree)
  against the BfArM JSON Schemas, offline (resolves the schemas' GitHub `$ref`s to the local files).
  Needs jsonschema ≥4.18 → run with `python3.11`.
  ```bash
  python3.11 scripts/validate_datenkranz.py example-data examples
  ```
- **e2e conversion harness** — `scripts/e2e_harness.py`: runs each DK file through **both** mappers →
  ingests into HAPI → validates each resource against its MII `meta.profile` via matchbox `$validate`;
  emits a per-path PASS/FAIL/INCONCLUSIVE verdict + `docs/E2E-REPORT.md`.
  ```bash
  python3 scripts/e2e_harness.py --roots example-data/synthData-v1
  ```

<a name="validation-terminology"></a>
## Validation & terminology setup

Validation uses a local **matchbox** (`:8090`, from the sibling `genomDE FHIR Mapper` project;
config there) with the MII packages loaded and `txServer: tx.fhir.org` (SNOMED/LOINC). tx.fhir.org
does **not** serve the German BfArM terminologies (ICD-10-GM/ICD-O-3/OPS/ATC) — those need the
**MII SU-TermServ Ontoserver** (mutual-TLS, German-institution-only). A ready-to-activate mTLS proxy
scaffold is in [`infra/mii-termserv-proxy/`](infra/mii-termserv-proxy/README.md) (needs a SU-TermServ
client cert). HAPI (`:8080`) is the ingest/store target.

## Key documents (`docs/`)

- [`OPEN-ISSUES.md`](docs/OPEN-ISSUES.md) — consolidated open issues + robustness snapshot.
- [`FIX-PLAN.md`](docs/FIX-PLAN.md) — prioritized fixes + implementation outcome (P0 content fixes,
  P1 terminology/infra, P2 FML parity).
- [`E2E-REPORT.md`](docs/E2E-REPORT.md) — latest both-path harness run.
- [`SYNTHDATA-V1-FINDINGS.md`](docs/SYNTHDATA-V1-FINDINGS.md) — both-path mapping of the new
  `example-data/synthData-v1` (2098 files).
- [`SCHEMA-VALIDATION-FINDINGS.md`](docs/SCHEMA-VALIDATION-FINDINGS.md) — JSON-Schema validation of
  all example data (surfaces source-data defects pre-mapping).
- [`OMOP-MAPPING-SUMMARY.md`](docs/OMOP-MAPPING-SUMMARY.md) — the separate genomDE→OMOP mapping table.
- `REVIEW-*.md` — adversarial-review rounds.

## Status

Mapping table complete (central reference). Oncology mappers cover the clinical spine end-to-end
(Python ingests + validates clean on the spine; FML behind). Schema validator + e2e harness in place.
Known gaps: molecular/plan/TNM/grading unmapped; consent §64e-vs-MII-Broad-Consent modeling; German
terminology pending the SU-TermServ cert; RD/GRZ FHIR mappers not built. Details in `docs/OPEN-ISSUES.md`.
