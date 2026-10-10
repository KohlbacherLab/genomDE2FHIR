# Datenkranz JSON Schema provenance

These are the **authoritative BfArM MVGenomseq schemas**, vendored locally so
`scripts/validate_datenkranz.py` runs offline against pinned copies.

| dir | source repo | release tag | schema content version | verified |
|---|---|---|---|---|
| `kdk/` | https://github.com/BfArM-MVH/MVGenomseq_KDK (`KDK/`) | **v2.3** + untagged `main` commit [`fe724ff`](https://github.com/BfArM-MVH/MVGenomseq_KDK/commit/fe724ff09172a284cb1334c677db030643b99203) (2026-08-05) | **1.7.1** (2025-09-05; `fe724ff` adds no CHANGELOG entry) | 2026-10-10 — all 14 files and `CHANGELOG.md` byte-identical to `fe724ff` (= `main`) |
| `grz/` | https://github.com/BfArM-MVH/MVGenomseq_GRZ (`GRZ/`) | **v1.3.1** ([`0c60bb6`](https://github.com/BfArM-MVH/MVGenomseq_GRZ/commit/0c60bb6), 2026-08-05; = `main` = `develop`) | schema `version` **1.3.1**; CHANGELOG still ends at 1.2.3 (2025-09-05) | 2026-10-10 — `grz-schema.json` and `CHANGELOG.md` byte-identical to v1.3.1 |

**KDK past v2.3.** `fe724ff` ("fix: Update research consent schema version", analog to GRZ v1.3.1) changes only
`KDK/Submission.json`: the enum of `researchConsents[].schemaVersion` (version of the embedded
`de.medizininformatikinitiative.kerndatensatz.consent` object) grows from `2025.0.1` to `2025.0.1`, `2025.0.2`,
`2025.0.3`, `2025.0.4`, `2026.0.0`, `2026.0.1`. Upstream tagged no KDK release and bumped no content version for it;
the other 13 files are unchanged since v2.3. Vendored 2026-10-10; `scripts/schema_to_logical.py` regenerated the KDK
logical models (definition text of `metaData.researchConsents.schemaVersion` only). genomde2fhir drops `schemaVersion`
(consumed by the consent migration to the target profile, which handles 2025 and 2026 consent objects alike), so the
new versions need no converter change.

**GRZ v1.3.1** (vendored 2026-10-10) is the counterpart: `grz-schema.json` `version` 1.3.0 → 1.3.1 and the same
enum for `donors[].researchConsents[].schemaVersion`; nothing else changed. Regenerated: the GRZ logical model
(definition text of that element) and the enum column of `mapping/mapping_grz.csv`.

**Not vendored: KDK `develop`** (`d30dd5d`, 7 commits past `main`, untagged): CHANGELOG 1.7.2 (RareDiseases `$id`
typo, RD `deathDate` regex) plus an [Unreleased] block — `Submission.confirmationId` (new), `tanC` pattern
harmonised, `addressAGS` pattern, `OncologyCase.variantTypes` required (`minItems` 1), OncologyPlan field renamed to
`interventionIsRiskReducing`, OncologyFollowUp `additionalDiagnoses[].system` required. Those need mapping-table,
converter and FML changes; vendor them once BfArM releases them to `main`.
genomde-dk-validator (the input gate) vendors its own copies and needs the same KDK and GRZ update.

Note the two-track versioning: the repos use release **tags** (`v2.x`, `v1.3.1`) while each schema's
own **CHANGELOG** uses semantic content versions (KDK 1.7.1, GRZ 1.2.3 — though GRZ v1.3.0/v1.3.1 also set the schema's own `version` field to the tag). The latest tag ships the
latest content version (KDK `main` is one untagged commit past v2.3, see above); both are pinned here.

The KDK root schemas `$ref` sibling files by absolute URL
(`https://raw.githubusercontent.com/BfArM-MVH/MVGenomseq_KDK/main/KDK/...`); the validator maps
those to these local files via a `referencing` Registry, so no network fetch happens at validation time.

## Refresh / re-verify against upstream
```bash
# KDK (14 files under KDK/)
for f in $(cd schemas/kdk && find . -name '*.json' | sed 's#^\./##'); do
  curl -sf "https://raw.githubusercontent.com/BfArM-MVH/MVGenomseq_KDK/fe724ff09172a284cb1334c677db030643b99203/KDK/$f" -o "schemas/kdk/$f"
done
# GRZ
curl -sf "https://raw.githubusercontent.com/BfArM-MVH/MVGenomseq_GRZ/v1.3.1/GRZ/grz-schema.json" -o schemas/grz/grz-schema.json
git diff --stat schemas/   # empty => still current; else review the upstream change
```
Bump the tags / commit above when BfArM publishes a change (`gh api repos/BfArM-MVH/MVGenomseq_KDK/compare/<pin>...main`
lists the changed files), then regenerate the logical models (`python3 scripts/schema_to_logical.py`, then
`python3 scripts/sync_package_data.py --no-index`) and update genomde-dk-validator's vendored copies.
