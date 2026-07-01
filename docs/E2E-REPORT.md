# genomDE → MII KDS — end-to-end conversion harness report
_generated 2026-07-01T09:42:37 · roots=['examples'] · paths=AB · ingest=True · validate=True · limit=none_

> **Path A: FAIL** · **Path B: FAIL**

## Pipeline
```
DK JSON ─┬─ (A) Python  genomde_to_fhir.py     ─┐
         └─ (B) FML     matchbox $transform     ─┴─► Bundle ─► [ingest → HAPI] + [KDS $validate → matchbox]
```
- **HAPI** `http://localhost:8080/fhir` — JPA store (no MII IGs → ingest = transaction/referential check, *not* KDS validation)
- **matchbox** `http://localhost:8090/matchboxv3/fhir` — `$transform` + KDS `$validate` (MII packages loaded)

## Discovery
174 JSON across ['examples']. Only the **oncology** branch has mappers → 44 eligible, 44 run this pass.

| branch | files | has mapper? |
|---|---|---|
| oncology | 44 | yes |
| rare-disease | 42 | no |
| legacy-variant | 84 | no |
| grz | 4 | no |

## Path A — Python mapper — verdict **FAIL**
- emit Bundle: **44 ok / 0 fail**
- ingest → HAPI (transaction): **44 ok / 0 fail**

### KDS `$validate` (per resource × declared profile)
| profile | clean | env-only | content-err | val-err | no-profile |
|---|---|---|---|---|---|
| PatientPseudonymisiert | 43 | 0 | 1 | 0 | 0 |
| coverage-de-basis | 44 | 0 | 0 | 0 | 0 |
| mii-pr-consent-einwilligung | 0 | 44 | 0 | 0 | 0 |
| mii-pr-mtb-diagnose-primaertumor | 0 | 44 | 0 | 0 | 0 |
| mii-pr-mtb-systemische-vortherapie | 0 | 0 | 67 | 0 | 0 |
| mii-pr-mtb-systemtherapie-medication-statement | 0 | 67 | 0 | 0 | 0 |
| mii-pr-onko-allgemeiner-leistungszustand-ecog | 82 | 0 | 6 | 0 | 0 |
| mii-pr-person-vitalstatus | 0 | 44 | 0 | 0 | 0 |

## Path B — FML `$transform` (matchbox) — verdict **FAIL**
- transform Bundle: **44 ok / 0 fail**
- ingest → HAPI (transaction): **0 ok / 44 fail**

### KDS `$validate` (per resource × declared profile)
| profile | clean | env-only | content-err | val-err | no-profile |
|---|---|---|---|---|---|
| (no profile: Coverage) | 0 | 0 | 0 | 0 | 44 |
| PatientPseudonymisiert | 43 | 0 | 1 | 0 | 0 |
| mii-pr-consent-einwilligung | 0 | 44 | 0 | 0 | 0 |
| mii-pr-mtb-diagnose-primaertumor | 0 | 0 | 44 | 0 | 0 |
| mii-pr-mtb-systemische-vortherapie | 0 | 0 | 67 | 0 | 0 |
| mii-pr-mtb-systemtherapie-medication-statement | 0 | 0 | 67 | 0 | 0 |
| mii-pr-onko-allgemeiner-leistungszustand-ecog | 0 | 0 | 88 | 0 | 0 |
| mii-pr-person-vitalstatus | 0 | 44 | 0 | 0 | 0 |

## A↔B parity
Cases where Path A and Path B emit different resource-type counts: **0 / 44**.

## Content-error samples (tx-server/env noise excluded; full list in results.json)
- `A` **mii-pr-mtb-systemische-vortherapie**: Profile https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemische-vortherapie|2026.0.1, Element matches more than one slice - sct, s
- `B` **mii-pr-mtb-diagnose-primaertumor**: Condition.extension: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-diagnose-primaertumo
- `B` **mii-pr-mtb-diagnose-primaertumor**: Slice 'Condition.extension:Feststellungsdatum' for extension 'http://hl7.org/fhir/StructureDefinition/condition-assertedDate': a matching slice is required, but not found (from htt
- `B` **mii-pr-mtb-diagnose-primaertumor**: Condition.subject: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-diagnose-primaertumor|
- `B` **mii-pr-onko-allgemeiner-leistungszustand-ecog**: Observation.subject: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-pr-onko-allgemeiner-leistu
- `B` **mii-pr-onko-allgemeiner-leistungszustand-ecog**: Slice 'Observation.code.coding:snomed': a matching slice is required, but not found (from https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-pr
- `B` **mii-pr-onko-allgemeiner-leistungszustand-ecog**: Slice 'Observation.value[x].coding:obds': a matching slice is required, but not found (from https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-
- `B` **mii-pr-mtb-systemische-vortherapie**: Procedure.extension: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemische-vorthera
- `B` **mii-pr-mtb-systemische-vortherapie**: Slice 'Procedure.extension:Intention' for extension 'https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-ex-onko-systemische-therapie-intention'
- `B` **mii-pr-mtb-systemische-vortherapie**: Procedure.subject: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemische-vortherapi
- `B` **mii-pr-mtb-systemische-vortherapie**: Profile https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemische-vortherapie|2026.0.1, Element matches more than one slice - sct, s
- `B` **mii-pr-mtb-systemtherapie-medication-statement**: MedicationStatement.partOf: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemtherapi
- `B` **mii-pr-mtb-systemtherapie-medication-statement**: MedicationStatement.subject: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemtherap
- `B` **mii-pr-mtb-systemtherapie-medication-statement**: MedicationStatement.effective[x]: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemt
- `A` **PatientPseudonymisiert**: Constraint failed: mii-pat-1: 'Falls die Geschlechtsangabe 'other' gewählt wird, muss die amtliche Differenzierung per Extension angegeben werden' (defined in https://www.medizinin
- `A` **mii-pr-onko-allgemeiner-leistungszustand-ecog**: Unknown code '5' in the CodeSystem 'https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/CodeSystem/mii-cs-onko-allgemeiner-leistungszustand-ecog' version '2026.0.3'
- `A` **mii-pr-onko-allgemeiner-leistungszustand-ecog**: The Coding provided (https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/CodeSystem/mii-cs-onko-allgemeiner-leistungszustand-ecog#5) was not found in the value set 'MII
- `B` **PatientPseudonymisiert**: Constraint failed: mii-pat-1: 'Falls die Geschlechtsangabe 'other' gewählt wird, muss die amtliche Differenzierung per Extension angegeben werden' (defined in https://www.medizinin

## Failures / gaps (deduped)
| path | kind | reason | count |
|---|---|---|---|
| B | ingest/structural | entry without fullUrl; entry without request.method | 44 |

## Notes
- **Verdict:** FAIL = produce/ingest/content-conformance error; INCONCLUSIVE = only env/tx-server, missing-profile, or $validate transport issues (couldn't fully validate); PASS = all clean. This matchbox has no terminology server, so KDS-conformant mappers land at INCONCLUSIVE here and PASS against a tx.fhir.org-backed validator.
- **env-only** = the only $validate errors are terminology/snapshot limits (ICD-10-GM/ICD-O-3/ATC/SNOMED can't expand offline). Every issue (env + content) is kept with its classifier in `out/e2e/results.json`.
- Path B ingest failing *"not a transaction bundle"* is the known FML gap (entries lack `fullUrl`+`request`); `$validate` still runs on its resources. See docs/OPEN-ISSUES.md.
- **HAPI pollution:** repeated runs POST new resources each time (metrics are unaffected — they read the transaction *response*, not DB counts). For a clean store, `$expunge` or point `HAPI=` at a throwaway partition. ponytail: not auto-purged.
- RD/GRZ/legacy-variant branches have no mapper yet → classified, not run.
