# genomDE → MII KDS — end-to-end conversion harness report
_generated 2026-07-02T10:17:09 · roots=['example-data/synthData-v1'] · paths=AB · ingest=True · validate=True · limit=150_

> **Path A: FAIL** · **Path B: FAIL**

## Pipeline
```
DK JSON ─┬─ (A) Python  genomde_to_fhir.py     ─┐
         └─ (B) FML     matchbox $transform     ─┴─► Bundle ─► [ingest → HAPI] + [KDS $validate → matchbox]
```
- **HAPI** `http://localhost:8080/fhir` — JPA store (no MII IGs → ingest = transaction/referential check, *not* KDS validation)
- **matchbox** `http://localhost:8090/matchboxv3/fhir` — `$transform` + KDS `$validate` (MII packages loaded)

## Discovery
2098 JSON across ['example-data/synthData-v1']. Only the **oncology** branch has mappers → 1056 eligible, 150 run this pass (--limit 150).

| branch | files | has mapper? |
|---|---|---|
| oncology | 1056 | yes |
| rare-disease | 42 | no |
| grz | 1000 | no |

## Path A — Python mapper — verdict **FAIL**
- emit Bundle: **150 ok / 0 fail**
- ingest → HAPI (transaction): **150 ok / 0 fail**

### KDS `$validate` (per resource × declared profile)
| profile | clean | env-only | content-err | val-err | no-profile |
|---|---|---|---|---|---|
| PatientPseudonymisiert | 150 | 0 | 0 | 0 | 0 |
| Vitalstatus | 84 | 0 | 0 | 0 | 0 |
| coverage-de-basis | 134 | 0 | 16 | 0 | 0 |
| mii-pr-consent-einwilligung | 0 | 0 | 150 | 0 | 0 |
| mii-pr-mtb-diagnose-primaertumor | 0 | 150 | 0 | 0 | 0 |
| mii-pr-mtb-systemische-vortherapie | 0 | 0 | 110 | 0 | 0 |
| mii-pr-mtb-systemtherapie-medication-statement | 45 | 65 | 0 | 0 | 0 |
| mii-pr-onko-allgemeiner-leistungszustand-ecog | 228 | 0 | 0 | 0 | 0 |

## Path B — FML `$transform` (matchbox) — verdict **FAIL**
- transform Bundle: **150 ok / 0 fail**
- ingest → HAPI (transaction): **0 ok / 150 fail**

### KDS `$validate` (per resource × declared profile)
| profile | clean | env-only | content-err | val-err | no-profile |
|---|---|---|---|---|---|
| (no profile: Coverage) | 0 | 0 | 0 | 0 | 150 |
| PatientPseudonymisiert | 145 | 0 | 5 | 0 | 0 |
| mii-pr-consent-einwilligung | 0 | 150 | 0 | 0 | 0 |
| mii-pr-mtb-diagnose-primaertumor | 0 | 0 | 150 | 0 | 0 |
| mii-pr-mtb-systemische-vortherapie | 0 | 0 | 110 | 0 | 0 |
| mii-pr-mtb-systemtherapie-medication-statement | 0 | 0 | 110 | 0 | 0 |
| mii-pr-onko-allgemeiner-leistungszustand-ecog | 0 | 0 | 234 | 0 | 0 |
| mii-pr-person-vitalstatus | 0 | 84 | 0 | 0 | 0 |

## A↔B parity
Cases where Path A and Path B emit different resource-type counts: **3 / 150**.
- `OncologySubmission_4A1F48C8F347F967E1CB72D1C1725BBAA8F23B5A627E3DC7A8FFF0A4092E9B63`: {'Observation': [1, 3]}
- `OncologySubmission_639605FE11AEC0DF38D509693AB7FF1A6135BC8BB4AB57A02839A434A37A26E2`: {'Observation': [1, 3]}
- `OncologySubmission_720D1596164CF6917C5DFDB447F88751E5B0B3457E48F6F3B9C95183EA2CF1E5`: {'Observation': [1, 3]}

## Content-error samples (tx-server/env noise excluded; full list in results.json)
- `A` **mii-pr-consent-einwilligung**: Consent.provision.period: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-consent-einwilligun
- `A` **mii-pr-consent-einwilligung**: Consent.provision.provision.period.end: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-conse
- `A` **mii-pr-consent-einwilligung**: Unknown code 'mvSequencing' in the CodeSystem 'urn:oid:2.16.840.1.113883.3.1937.777.24.5.3' version '1.0.5'
- `A` **mii-pr-consent-einwilligung**: None of the codings provided are in the value set 'MII Consent: Policy ValueSet' (https://www.medizininformatik-initiative.de/fhir/modul-consent/ValueSet/mii-vs-consent-policy|1.0.
- `A` **mii-pr-consent-einwilligung**: Unknown code 'reIdentification' in the CodeSystem 'urn:oid:2.16.840.1.113883.3.1937.777.24.5.3' version '1.0.5'
- `A` **mii-pr-consent-einwilligung**: Unknown code 'caseIdentification' in the CodeSystem 'urn:oid:2.16.840.1.113883.3.1937.777.24.5.3' version '1.0.5'
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
- `B` **PatientPseudonymisiert**: Constraint failed: mii-pat-1: 'Falls die Geschlechtsangabe 'other' gewählt wird, muss die amtliche Differenzierung per Extension angegeben werden' (defined in https://www.medizinin
- `A` **mii-pr-consent-einwilligung**: Consent.dateTime: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-consent-einwilligung|1.0.8)
- `A` **coverage-de-basis**: Unknown code 'UNK' in the CodeSystem 'http://fhir.de/CodeSystem/versicherungsart-de-basis' version '1.4.0'
- `A` **coverage-de-basis**: None of the codings provided are in the value set 'VersicherungsartDeBasis' (http://fhir.de/ValueSet/versicherungsart-de-basis|1.4.0), and a coding from this value set is required)
- `A` **coverage-de-basis**: Unknown code 'SKT' in the CodeSystem 'http://fhir.de/CodeSystem/versicherungsart-de-basis' version '1.4.0'

## Failures / gaps (deduped)
| path | kind | reason | count |
|---|---|---|---|
| B | ingest/structural | entry without fullUrl; entry without request.method | 150 |

## Notes
- **Verdict:** FAIL = produce/ingest/content-conformance error; INCONCLUSIVE = only env/tx-server, missing-profile, or $validate transport issues (couldn't fully validate); PASS = all clean. This matchbox has no terminology server, so KDS-conformant mappers land at INCONCLUSIVE here and PASS against a tx.fhir.org-backed validator.
- **env-only** = the only $validate errors are terminology/snapshot limits (ICD-10-GM/ICD-O-3/ATC/SNOMED can't expand offline). Every issue (env + content) is kept with its classifier in `out/e2e/results.json`.
- Path B ingest failing *"not a transaction bundle"* is the known FML gap (entries lack `fullUrl`+`request`); `$validate` still runs on its resources. See docs/OPEN-ISSUES.md.
- **HAPI pollution:** repeated runs POST new resources each time (metrics are unaffected — they read the transaction *response*, not DB counts). For a clean store, `$expunge` or point `HAPI=` at a throwaway partition. ponytail: not auto-purged.
- RD/GRZ/legacy-variant branches have no mapper yet → classified, not run.
