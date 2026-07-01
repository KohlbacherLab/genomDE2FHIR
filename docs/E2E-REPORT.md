# genomDE → MII KDS — end-to-end conversion harness report
_generated 2026-07-01T10:52:25 · roots=['examples'] · paths=A · ingest=True · validate=True · limit=none_

> **Path A: FAIL**

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
| PatientPseudonymisiert | 44 | 0 | 0 | 0 | 0 |
| Vitalstatus | 44 | 0 | 0 | 0 | 0 |
| coverage-de-basis | 44 | 0 | 0 | 0 | 0 |
| mii-pr-consent-einwilligung | 0 | 0 | 44 | 0 | 0 |
| mii-pr-mtb-diagnose-primaertumor | 0 | 44 | 0 | 0 | 0 |
| mii-pr-mtb-systemische-vortherapie | 0 | 0 | 67 | 0 | 0 |
| mii-pr-mtb-systemtherapie-medication-statement | 0 | 67 | 0 | 0 | 0 |
| mii-pr-onko-allgemeiner-leistungszustand-ecog | 82 | 0 | 0 | 0 | 0 |

## Path B — FML `$transform` (matchbox)
_SKIPPED (paths=A)_

## Content-error samples (tx-server/env noise excluded; full list in results.json)
- `A` **mii-pr-consent-einwilligung**: Consent.provision.period: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-consent-einwilligun
- `A` **mii-pr-consent-einwilligung**: Consent.provision.provision.period.end: minimum required = 1, but only found 0 (from https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-conse
- `A` **mii-pr-consent-einwilligung**: Unknown code 'mvSequencing' in the CodeSystem 'urn:oid:2.16.840.1.113883.3.1937.777.24.5.3' version '1.0.5'
- `A` **mii-pr-consent-einwilligung**: None of the codings provided are in the value set 'MII Consent: Policy ValueSet' (https://www.medizininformatik-initiative.de/fhir/modul-consent/ValueSet/mii-vs-consent-policy|1.0.
- `A` **mii-pr-consent-einwilligung**: Unknown code 'reIdentification' in the CodeSystem 'urn:oid:2.16.840.1.113883.3.1937.777.24.5.3' version '1.0.5'
- `A` **mii-pr-consent-einwilligung**: Unknown code 'caseIdentification' in the CodeSystem 'urn:oid:2.16.840.1.113883.3.1937.777.24.5.3' version '1.0.5'
- `A` **mii-pr-mtb-systemische-vortherapie**: Profile https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemische-vortherapie|2026.0.1, Element matches more than one slice - sct, s

## Notes
- **Verdict:** FAIL = produce/ingest/content-conformance error; INCONCLUSIVE = only env/tx-server, missing-profile, or $validate transport issues (couldn't fully validate); PASS = all clean. This matchbox has no terminology server, so KDS-conformant mappers land at INCONCLUSIVE here and PASS against a tx.fhir.org-backed validator.
- **env-only** = the only $validate errors are terminology/snapshot limits (ICD-10-GM/ICD-O-3/ATC/SNOMED can't expand offline). Every issue (env + content) is kept with its classifier in `out/e2e/results.json`.
- Path B ingest failing *"not a transaction bundle"* is the known FML gap (entries lack `fullUrl`+`request`); `$validate` still runs on its resources. See docs/OPEN-ISSUES.md.
- **HAPI pollution:** repeated runs POST new resources each time (metrics are unaffected — they read the transaction *response*, not DB counts). For a clean store, `$expunge` or point `HAPI=` at a throwaway partition. ponytail: not auto-purged.
- RD/GRZ/legacy-variant branches have no mapper yet → classified, not run.
