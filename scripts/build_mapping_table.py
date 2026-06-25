#!/usr/bin/env python3
"""Build/refresh a mapping table from a leaf-skeleton CSV.

The mapping table is the project's central reference. This merge is idempotent:
re-run the leaf extractor whenever the schema changes, then run this to refresh
the table WITHOUT losing hand-filled target columns. Rows are keyed by `path`.

- New leaves (in skeleton, not in table)  -> added with empty target columns, status=TODO
- Dropped leaves (in table, not skeleton) -> kept, status=REMOVED? (flagged, not deleted)
- Source columns (type/required/array/enum/format/description) always refreshed from skeleton.

Usage: build_mapping_table.py <leaves.csv> <mapping.csv>
"""
import csv, sys, os

SOURCE_COLS = ["path", "type", "required", "array", "enum", "format", "description"]
TARGET_COLS = ["mii_module", "mii_profile", "fhir_element", "transform", "status", "notes"]
ALL = SOURCE_COLS + TARGET_COLS

def read_csv(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {r["path"]: r for r in csv.DictReader(f)}

def main():
    leaves_path, table_path = sys.argv[1], sys.argv[2]
    leaves = read_csv(leaves_path)
    table = read_csv(table_path)

    out = []
    for path, leaf in leaves.items():
        row = {c: leaf.get(c, "") for c in SOURCE_COLS}
        prev = table.get(path, {})
        for c in TARGET_COLS:
            row[c] = prev.get(c, "")
        if not row["status"]:
            row["status"] = "TODO"
        elif row["status"] == "REMOVED?":   # leaf came back
            row["status"] = "TODO"
        out.append(row)

    # keep dropped leaves, flagged
    for path, prev in table.items():
        if path not in leaves:
            row = {c: prev.get(c, "") for c in ALL}
            row["status"] = "REMOVED?"
            out.append(row)

    out.sort(key=lambda r: r["path"])
    with open(table_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALL)
        w.writeheader()
        w.writerows(out)

    todo = sum(1 for r in out if r["status"] == "TODO")
    sys.stderr.write(f"{table_path}: {len(out)} rows ({todo} TODO)\n")

if __name__ == "__main__":
    main()
