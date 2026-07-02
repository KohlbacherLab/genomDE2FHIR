# BfArM Qualitätssicherung — semantic rules + corpus findings

The validator ([genomde-dk-validator](https://github.com/KohlbacherLab/genomde-dk-validator)) now
enforces the BfArM QS criteria as JSON-defined semantic rules (mechanics adopted from
mzPeakValidator: rules-as-data + primitive catalog). Sources ingested:
`knowledge/bfarm-qs/{Qs-KDK.pdf (v01.2), Qs-GRZ.pdf (v01.4), Anlage-Kodiersysteme-KDK.pdf}`.

Rules are **off by default**, opt-in via `--kdk-rules` / `--grz-rules`, with a branch **sanity check**
(rule set must match the detected KDK/GRZ branch) and `--rules-config` for external inputs
(LE-ID list, own node/centre id).

## Rule → criterion mapping (implemented)
**KDK** (12 Kriterien): 1 age∈[0,130]; 3 index consent (permit+mvSequencing); 5 TNM one T/N/M;
6 no date < birthDate; 7 dates before board decision (by submission.type); 8 presentation ≤ signature;
9 decision/actions after consent; 10 rare→libraryType∈{wgs,wgs_lr,none}; 12 noScopeJustification enum.
2 (LE-ID list) + 11 (own node id) need `--rules-config` (skip otherwise); 4 (terminology) handled by
the schema/matchbox tooling.
**GRZ** (Tabelle 1): rare→labData.libraryType∈{wgs,wgs_lr}; centre-id (config); noScopeJustification enum.
GRZ Detailprüfung QC thresholds (depth/read-length/%Q30-Q20/coverage) + raw-data checks (checksums,
read counts) run on FASTQ/BAM — out of scope for a JSON validator (use GRZ_QC_Workflow).

## Corpus results

### KDK rules over the KDK corpus (synthData-v1: dnpm, nct, ukdd, nse = 1098 files; post-review)
**334 rule-clean · 764 with ≥1 rule violation**

| rule | files | what it means |
|---|---:|---|
| kdk-7-dates-before-decision | 559 | a date (often prior-therapy start/end) falls after `molecularBoardDecisionDate` for an `initial` submission |
| kdk-12-noscope-justification | 309 | `researchConsents.noScopeJustification` uses one of the two now-forbidden technical/organizational values |
| kdk-9b-consented-actions-after-consent | 60 | a consent-gated date (follow-up/therapy) precedes the MV consent signature |
| kdk-10-rare-librarytype | 23 | rare-disease case with libraryType outside {wgs,wgs_lr,none} |
| kdk-6-no-date-before-birth | 1 | a date earlier than the patient's birthDate |

### GRZ rules over the GRZ corpus (1006 files)
**835 rule-clean · 171 with ≥1 rule violation**

| rule | files | what it means |
|---|---:|---|
| grz-1-rare-librarytype | 169 | rare-disease submission with `labData.libraryType` = panel/WES (excluded; must be wgs/wgs_lr) |
| grz-sanity | 2 | the two oncology coverage fixtures misfiled under `example-data/grz/` — correctly rejected as not-GRZ |

## Adversarial review notes (what's real vs. rule limitation)
- **Real data issues** the rules surface: forbidden `noScopeJustification` values (kdk-12, 309),
  rare-disease with panel/WES (grz-1 169 / kdk-10 46), and pervasive temporal incoherence in the
  synthetic dates (kdk-7/9b) — synthData-v1 dates are not generated to satisfy the QS ordering.
- **kdk-5 TNM** was initially buggy (counted only `T3`/`N0` prefixes → 382 false positives on nct's
  SNOMED-coded TNM); fixed to read the category from the `display` notation (`cT1a1`/`cN1`/`pM1`) —
  nct now 0/500. Residual limit: a SNOMED TNM entry with no `display` can't be categorized.
- **Anchor selection (v0.1 limitation):** kdk-7 (followup) and kdk-9b use the *first* follow-up /
  consent-scope date when several exist; multi-scope consents with differing dates may be judged
  against the wrong anchor. Documented in the rule `doc` fields.
- **Config-gated rules** (kdk-2/11, grz-2) correctly *skip with info* absent `--rules-config`, so a
  bare run never mis-passes them as satisfied.

## Adversarial review of the rule set (codex — docs/REVIEW-RULES-codex.md)
**Fixed:** (P0) `resolve()` didn't support numeric path indices → kdk-7's follow-up anchor never
resolved (dead check) — now supported; (P0) kdk-7 over-excluded every `/molecularBoardDecisionDate$`
(incl. plan + rare board dates) vs the QS text (only `researchConsents.presentationDate` +
`submission.date`) — now excludes just the metaData self-anchor (kdk-7 472→559 after the fix).
**Logged v0.1 follow-ups:** filter the mvConsent anchor to `type=permit,domain=mvSequencing` for
kdk-9a/9b; split kdk-9b/kdk-10 into branch-aware OD/RD rules (rare libraryType really lives under
`diagnosisRd`); enable a jsonschema `FormatChecker` + strict `date.fromisoformat` parsing;
interval-aware comparison for month-only fields; criterion-2 indication-admission (not just LE-ID
membership); criterion-4 terminology stays with the schema/matchbox tooling.

Full rule definitions + per-criterion path mapping: the `about`/`doc` blocks in
`genomde-dk-validator/src/genomde_dk_validator/rules/{kdk,grz}.rules.json`.
