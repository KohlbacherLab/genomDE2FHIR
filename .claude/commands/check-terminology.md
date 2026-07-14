# check-terminology

Deep terminology / coded-value audit of the genomDE→MII mapping — automates the manual
"NUM-OMICS" review that caught wrong LOINC codes (e.g. `94195-5`=CPT2 cited for an HRD field).

> **Mandatory review gate.** This check is a required part of *every* adversarial review of the
> mapping table — run it alongside the clinical/structural pass and resolve all INVALID/MISMATCH
> findings + confirm catch-all-enum coverage before the review is complete. Structural FHIR
> validation cannot catch a valid-but-wrong code; only this terminology-server check can.

```bash
python3 scripts/check_terminology.py            # -> docs/TERMINOLOGY-CHECK.md
python3 scripts/check_terminology.py --tx URL   # use another FHIR terminology server
```

What it does, for every coded value the mapping cites (`transform`/`fhir_element`/`reference`):

1. **Existence** — asks a FHIR terminology server (`tx.fhir.org`, LOINC+SNOMED) `$lookup`
   whether each LOINC code / answer code (`LA…`) / answer list (`LL…`) / SNOMED code EXISTS.
   Missing → **INVALID** (e.g. `93573-4`, `LA26059-4`).
2. **Concept match** — compares the code's official display against the field it maps
   (camel-split field name + description + a genomics synonym map). No overlap → **MISMATCH**
   (e.g. `81303-0`="HGVS version" cited for `ploidy`). Applies to `Observation.code`-level
   codes only; answer values go to a per-field **roster** so a rogue value stands out
   (this is how `LA24788-4`="Mastoid" among inheritance modes was found).
3. **DK enum coverage** — every schema enum value; the catch-all values
   (`unknown/other/none/notAvailable/yesButStudyIsUnknown`) have no clinical code → must be
   mapped **structurally**: `dataAbsentReason`/nullFlavor (absence), `.text`/local CS (`other`),
   a real negative code or `dataAbsentReason` (`none`).

Codes documented as rejected in a cell ("was X", "X is WRONG", "confirm …") are skipped — the
checker only audits the *active* mapping. Notes:
- tx.fhir.org resolves **LOINC + SNOMED only**. ICD-10-GM, ICD-O-3, OPS, ATC, Orphanet,
  Alpha-ID, HPO, HGNC, SO, UICC, NCIt are listed as **not-checked-here** — verify against a
  German/OBO server (BfArM TermServ, EBI OLS) separately.
- Results cache in `scripts/.tx_cache.json` (gitignored); re-runs are offline for seen codes.
- After a mapping edit, re-run and commit the refreshed `docs/TERMINOLOGY-CHECK.md`.
