#!/usr/bin/env python3
"""Build/refresh the SECOND mapping table: genomDE Datenkranz -> OMOP CDM.

Same source leaves as the FHIR table (so the two targets stay row-aligned by `path`),
but with OMOP target columns. Idempotent merge like build_mapping_table.py: re-run the
leaf extractor, then this, to refresh without losing hand-filled OMOP columns.

Usage: build_omop_table.py <leaves.csv> <omop_mapping.csv>
"""
import csv, sys, os
SOURCE = ["path", "type", "required", "array", "enum", "format", "description"]
# OMOP targets: table + field, the vocabulary/standard-concept approach, transform, status
OMOP = ["omop_table", "omop_field", "omop_vocab", "omop_transform", "status", "notes"]
ALL = SOURCE + OMOP

def read(p):
    return {r["path"]: r for r in csv.DictReader(open(p))} if os.path.exists(p) else {}

def main():
    leaves, table = sys.argv[1], sys.argv[2]
    lv, prev = read(leaves), read(table)
    out = []
    for path, leaf in lv.items():
        row = {c: leaf.get(c, "") for c in SOURCE}
        p = prev.get(path, {})
        for c in OMOP:
            row[c] = p.get(c, "")
        row["status"] = row["status"] or "TODO"
        out.append(row)
    for path, p in prev.items():
        if path not in lv:
            row = {c: p.get(c, "") for c in ALL}; row["status"] = "REMOVED?"; out.append(row)
    out.sort(key=lambda r: r["path"])
    with open(table, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALL); w.writeheader(); w.writerows(out)
    todo = sum(1 for r in out if r["status"] == "TODO")
    sys.stderr.write(f"{table}: {len(out)} rows ({todo} TODO)\n")

if __name__ == "__main__":
    main()
