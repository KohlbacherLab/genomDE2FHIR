# Mappers — build, adversarial review & live test report

Stage-2 mappers for the oncology branch, built + tested against the **local matchbox
v4.0.12** (FHIR R4) with the real MII packages loaded.

## What was built
- **(a) Python** `mappers/python/genomde_to_fhir.py` — `fhir.resources`-based; Datenkranz
  oncology JSON → transaction Bundle (Patient, Coverage, Consent, primary+additional
  Condition, ECOG, prior Procedure+MedicationStatement, follow-up ECOG+vital status).
- **(b) FML** `mappers/fml/genomde-oncology-to-mii.map` + `DatenkranzOncology.logical.json`
  — StructureMap for matchbox/HAPI `$transform`, same spine.

## Test environment
matchbox `:8090` (`/matchboxv3/fhir`). Loaded packages: de.basisprofil.r4 1.6.0,
kerndatensatz.person 2025.0.1, consent 2026.0.0, diagnose 2025.0.1, **onkologie 2026.0.3,
mtb 2026.0.1**. No external terminology server attached (matters — see caveats).

## Results
| Test | Result |
|------|--------|
| Python — emit Bundle (all 42 oncology examples) | **42 / 42** |
| FML `$transform` on matchbox (all 42) | **42 / 42** (Bundle, not OperationOutcome) |
| FML compile / load (check-fml + matchbox) | **PUSH-SAFE**, HTTP 201 |
| Python output — MII `$validate` (per resource vs `meta.profile`) | see below |

### Per-profile `$validate` (Python output)
| Profile | Verdict |
|---------|---------|
| PatientPseudonymisiert | **conformant (0 errors)** |
| coverage-de-basis | **conformant (0 errors)** |
| mii-pr-onko-allgemeiner-leistungszustand-ecog | **conformant (0 errors)** |
| mii-pr-mtb-diagnose-primaertumor | 2 left — **environmental** (ICD-O-3 CodeSystem + ICD-10-GM VS can't expand without a tx-server) |
| mii-pr-mtb-systemische-vortherapie | content fixed (Intention added); residual = SNOMED/OPS VS expansion (tx-server) |
| mii-pr-mtb-systemtherapie-medication-statement | residual = ATC VS expansion (tx-server) |
| mii-pr-consent-einwilligung / mii-pr-person-vitalstatus | matchbox "could not validate profile" (snapshot/engine) — not a content error |

### Conformance fixes applied (driven by the live `$validate`)
ICD-O-3 system → `http://terminology.hl7.org/CodeSystem/icd-o-3` (+ drop bogus source
version); Condition **Feststellungsdatum** (`condition-assertedDate`, min 1); Patient
identifier **PSEUDED**/**MR** type slices; Consent **policy OID** `…24.2.2079` + provision
**OID system** `…24.5.3` + period + 2nd category; ECOG **mii-cs-onko-…-ecog** + SNOMED
423740007 + survey category; Procedure **Intention** extension (`mii-cs-onko-intention`
K/P/S/X — matches source); vital-status survey category + value map.
→ Patient/Coverage/ECOG went to 0 errors; Condition 5→2, Procedure 10→4 (rest env-only).

## Adversarial review (codex + vibe) — captured in docs/REVIEW-MAP-{codex,vibe}.md
Confirmed + actioned: the conformance fixes above. Still open (next iteration):
1. **FML structural** — entries lack `fullUrl` + `request.method/url` → output isn't a valid
   transaction Bundle yet (Python does this correctly). Add per-entry `fullUrl=uuid()` + request.
2. **FML conformance parity** — apply the same system/extension fixes (icd-o-3, asserted-date,
   Intention, PSEUDED, consent OIDs) the Python mapper got.
3. **Coverage breadth** — both mappers do the MAPPED *spine*; molecular MTB variants/CNV/fusion/
   RNA-seq/biomarkers, TNM, grading, care-plan recommendations are TODO (track the open issues).
4. **researchConsents[].scope** verbatim passthrough; localCaseId identifier in FML.

## Caveats
- **No terminology server** on this matchbox → large value sets (ICD-10-GM, ICD-O-3, ATC,
  SNOMED) can't expand, so those `$validate` errors are environmental, not mapper bugs; they
  resolve against a validator configured with `tx.fhir.org` (or a local TS).
- Consent/person "could not validate profile" is a matchbox snapshot/engine limitation here.
- The MII packages were loaded ad-hoc into the running matchbox for testing (not persisted).

## Repro
```bash
bash scripts/test-mappers.sh           # 42/42 both mappers
bash scripts/validate-bundles.sh py 5  # MII $validate sweep (needs packages loaded)
```
