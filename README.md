# genomDE2FHIR

Mapping from **BfArM Modellvorhaben Genomsequenzierung (§64e SGB V)** Phase-0
submission data (genomDE Datenkranz) into **MII Kerndatensatz (KDS)** FHIR R4
resources.

The project proceeds in two stages:

1. **Mapping table** (this stage) — a leaf-level table mapping every leaf of the
   genomDE Datenkranz to its MII KDS target. GRZ and KDK are kept separate. The
   table is the project's **central reference**; both mappers are implementations
   of it.
2. **Mappers** — generated from the table: a FHIR StructureMap / FML pipeline
   running in HAPI, and a Python mapping script.

Adversarial CLI review (`vibe`, `codex`) is used at critical steps.

## Source schemas (locked versions)

| Source | Schema | Version | Root(s) |
|--------|--------|---------|---------|
| KDK | `schemas/kdk/` (BfArM-MVH/MVGenomseq_KDK) | 1.7.1 | `Oncology.json`, `RareDiseases.json` |
| GRZ | `schemas/grz/grz-schema.json` (BfArM-MVH/MVGenomseq_GRZ) | 1.3.0 | `grz-schema.json` |

Target: MII KDS profiles, FHIR R4 (4.0.1), KDS package versions 2025.0.x.

## The mapping table

Three CSVs under `mapping/` — the editable, version-controlled central reference:

- `mapping_kdk_oncology.csv` (229 leaves)
- `mapping_kdk_rarediseases.csv` (132 leaves)
- `mapping_grz.csv` (67 leaves)

Columns: `path, type, required, array, enum, format, description` (source side,
auto-extracted) + `mii_module, mii_profile, fhir_element, transform, status,
notes` (target side, hand-filled). `status` ∈ {TODO, MAPPED, NOMAP, REMOVED?}.

## Regenerating the skeleton

```bash
bash scripts/regen-mapping.sh
```

Re-extracts leaves from the schemas and refreshes the tables **idempotently** —
hand-filled target columns are preserved (keyed by `path`), new leaves added as
TODO, and leaves dropped by a schema change flagged `REMOVED?` (not deleted).
Run this after any schema bump, then reconcile flagged rows.

- `scripts/extract_leaves.py` — JSON-Schema → leaf CSV
- `scripts/build_mapping_table.py` — leaf CSV → mapping table (idempotent merge)
