---
description: Sync the mapping table between the canonical CSVs and the shared Google Sheet
allowed-tools: Bash(python3 scripts/sync_from_sheet.py:*), Bash(python3 scripts/export_xlsx.py:*), Bash(python3 scripts/render_table.py:*), Bash(git diff:*)
---

Sync the central mapping table with the online Google Sheet
(https://docs.google.com/spreadsheets/d/1vqPsLLaV6pMCDFXAReqczompNTnTPEqN).

Default (pull edits from the Sheet → canonical CSVs, target columns only):

```bash
python3 scripts/sync_from_sheet.py $ARGUMENTS
```

- The Sheet is the working copy; the `mapping/*.csv` in git are the source of truth.
- Pulls via the **XLSX export** (`export?format=xlsx`), NOT CSV — CSV silently drops
  cell comments; XLSX preserves them. [[feedback-pull-sheet-as-xlsx]]
- Pull updates ONLY the mapping columns (mii_module, mii_profile, fhir_element,
  transform, status), matched by `path`. Schema-derived columns A–G belong to
  `scripts/regen-mapping.sh`; the `notes` column is repo-managed (CLIN-REVIEW
  annotations come from `scripts/ingest_sheet_comments.py`) — neither is pulled.
- Reviewer feedback flows via the sheet's native cell COMMENTS → pull them with
  `python3 scripts/ingest_sheet_comments.py` (also XLSX-based).
- Add `--dry-run` to preview. After a real pull, review `git diff mapping/` and commit.
- To push the current CSVs back out for editing, regenerate the workbook with
  `python3 scripts/export_xlsx.py` (→ mapping/mapping-table.xlsx) and re-upload to Drive,
  or `python3 scripts/render_table.py` for the read-only HTML view.

Requires the Sheet to stay link-shared ("anyone with the link can view").
