#!/usr/bin/env python3
"""Fill/refresh the `reference` column of the FHIR mapping CSVs.

`reference` records WHAT each mapping suggestion is based on — the MII profile
name plus any authoritative source cited in the row (oBDS-to-FHIR, fhir.de
Basisprofil-DE, HL7 R4 core, DNPM-SE / MII Seltene, an MII invariant). It is
derived from mii_profile + transform + notes, so it is re-runnable: edit those
columns, then re-run this to refresh. Repo-managed (not pulled from the Sheet),
appended as the last column. Usage: python3 scripts/fill_reference.py
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSVS = ["mapping_kdk_oncology.csv", "mapping_kdk_rarediseases.csv", "mapping_grz.csv"]

# substring (lowercased) -> source label, first match order preserved
SOURCES = [
    (("obds-to-fhir", "bzkf", "systemtherapie-procedure", "primaerdiagnose"), "oBDS-to-FHIR (bzkf)"),
    (("mii-pat-1",), "MII inv. mii-pat-1"),
    (("basisprofil", "fhir.de/structuredefinition", "gender-amtlich", "de.basisprofil"), "fhir.de Basisprofil-DE"),
    (("hl7.org/fhir",), "HL7 FHIR R4 core"),
    (("dnpm", "seltene", "episodeofcare-cardinalities", " se:", "se-datamodel"), "DNPM-SE / MII Seltene"),
    (("mii-ex-onko",), "MII Onko extensions"),
]


def profile_name(mii_profile: str) -> str:
    m = re.search(r"StructureDefinition/([A-Za-z0-9-]+)", mii_profile or "")
    return m.group(1) if m else (mii_profile or "").strip()   # else a bare label (Observation, CarePlan, ...)


def reference(row: dict) -> str:
    text = ((row.get("transform") or "") + " | " + (row.get("notes") or "")).lower()
    src = [label for keys, label in SOURCES if any(k in text for k in keys)]
    parts = [p for p in (profile_name(row.get("mii_profile", "")), "; ".join(src)) if p]
    return " | ".join(parts)


def main():
    for name in CSVS:
        fn = ROOT / "mapping" / name
        with open(fn, newline="") as f:
            r = csv.DictReader(f)
            fields = list(r.fieldnames)
            rows = list(r)
        if "reference" not in fields:
            fields.append("reference")
        filled = 0
        for row in rows:
            row["reference"] = reference(row)
            filled += bool(row["reference"])
        with open(fn, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"{name}: reference filled {filled}/{len(rows)}")


if __name__ == "__main__":
    main()
