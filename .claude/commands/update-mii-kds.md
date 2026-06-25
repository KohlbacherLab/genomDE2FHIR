---
description: Crawl/refresh the MII KDS specs (website IGs + Simplifier) into the Obsidian vault at knowledge/mii-kds/
allowed-tools: Bash(python3 scripts/update_mii_kds.py:*)
---

Refresh the MII Kerndatensatz knowledge vault by running the crawler. This
re-crawls the MII KDS website (basismodule + erweiterungsmodule overviews and the
linked IG sites under /Kerndatensatz/) and the Simplifier MII org listing, writing
Markdown notes + MOC indexes into `knowledge/mii-kds/`.

Run it:

```bash
python3 scripts/update_mii_kds.py $ARGUMENTS
```

Notes:
- Idempotent — overwrites existing notes and rewrites the MOC indexes.
- Flags: `--max-pages N` (default 1200), `--depth D` (default 4), `--delay S`
  (default 0.4s), `--only mii|simplifier`.
- If a run reports `truncated: true`, raise `--max-pages` and re-run.
- The vault content is gitignored (regenerable); only the script + this command
  are tracked. After a refresh, skim `knowledge/mii-kds/MII-KDS.md` for the run
  summary and any errors.
