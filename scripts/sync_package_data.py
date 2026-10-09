#!/usr/bin/env python3
"""Refresh genomde2fhir/src/genomde2fhir/data from the repo sources of truth:

  data/mapping/*.csv          <- mapping/mapping_{kdk_oncology,kdk_rarediseases,grz}.csv
  data/mvgs/*.json            <- mvgs-ig/input/*.json (de.genomde.mvgs conformance resources)
  data/canonical-index.json   <- every StructureDefinition/ValueSet/CodeSystem url in the 2026 and the
                                 2027 package closures (~/.fhir/packages) plus de.genomde.mvgs

Usage: python3 scripts/sync_package_data.py [--check] [--no-index]
  --check: exit 1 if data/ is stale; --no-index: skip the canonical index (CI has no FHIR package cache)
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "genomde2fhir" / "src" / "genomde2fhir" / "data"
CACHE = Path(os.path.expanduser("~/.fhir/packages"))
MII = "de.medizininformatikinitiative.kerndatensatz."
STACKS = {
    "2027": [MII + "mtb#2027.0.0-ballot.1", MII + "onkologie#2027.0.0-ballot.1", MII + "molgen#2027.0.0-ballot.1",
             MII + "seltene#2027.0.0-ballot", MII + "consent#2027.0.0-ballot", MII + "base#2027.0.0-ballot",
             MII + "biobank#2027.0.0-ballot", MII + "studie#2027.0.0-ballot", MII + "medikation#2027.0.0-ballot",
             MII + "laborbefund#2027.0.0-ballot", "hl7.fhir.uv.genomics-reporting#3.0.0", "de.basisprofil.r4#1.6.0",
             "hl7.fhir.r4.core#4.0.1"],
    "2026": [MII + "mtb#2026.0.1", MII + "onkologie#2026.0.3", MII + "molgen#2026.0.4", MII + "seltene#2026.0.1",
             MII + "consent#2026.0.0", MII + "person#2025.0.1", MII + "diagnose#2025.0.1", MII + "prozedur#2025.0.1",
             MII + "fall#2025.0.1", MII + "biobank#2026.0.1", MII + "studie#2026.0.2", MII + "medikation#2026.0.1",
             "hl7.fhir.uv.genomics-reporting#3.0.0", "de.basisprofil.r4#1.6.0", "hl7.fhir.r4.core#4.0.1"],
}
KINDS = ("StructureDefinition", "ValueSet", "CodeSystem", "NamingSystem", "ConceptMap")
CSVS = ["mapping_kdk_oncology.csv", "mapping_kdk_rarediseases.csv", "mapping_grz.csv"]


def closure(roots):
    seen, todo = [], list(roots)
    while todo:
        k = todo.pop()
        if k in seen:
            continue
        p = CACHE / k / "package" / "package.json"
        if not p.exists():
            continue
        seen.append(k)
        todo += [f"{n}#{v}" for n, v in json.loads(p.read_text()).get("dependencies", {}).items()]
    return seen


def index_package(d: Path, tag: str, idx: dict):
    for f in d.glob("*.json"):
        if f.name in ("package.json", ".index.json"):
            continue
        try:
            r = json.loads(f.read_text())
        except Exception:
            continue
        if r.get("resourceType") not in KINDS or not r.get("url"):
            continue
        e = idx.setdefault(r["url"], {"resourceType": r["resourceType"], "type": r.get("type"),
                                      "kind": r.get("kind"), "id": r.get("id"), "sets": []})
        if tag not in e["sets"]:
            e["sets"].append(tag)


def build_index() -> dict:
    idx = {}
    for tag, roots in STACKS.items():
        for k in closure(roots):
            index_package(CACHE / k / "package", tag, idx)
    index_package(ROOT / "mvgs-ig" / "input", "mvgs", idx)
    return dict(sorted(idx.items()))


def main():
    check = "--check" in sys.argv
    want = {}
    for c in CSVS:
        want[DATA / "mapping" / c] = (ROOT / "mapping" / c).read_bytes()
    for f in sorted((ROOT / "mvgs-ig" / "input").glob("*.json")):
        want[DATA / "mvgs" / f.name] = f.read_bytes()
    if "--no-index" not in sys.argv:
        want[DATA / "canonical-index.json"] = json.dumps(build_index(), indent=0, sort_keys=True).encode()
    stale = [p for p, b in want.items() if not p.exists() or p.read_bytes() != b]
    extra = [p for p in (DATA / "mvgs").glob("*.json") if p not in want] if (DATA / "mvgs").exists() else []
    if check:
        for p in stale + extra:
            print("stale:", p.relative_to(ROOT))
        sys.exit(1 if stale or extra else 0)
    for p in extra:
        p.unlink()
    for p, b in want.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        if p in stale:
            p.write_bytes(b)
    n_idx = len(json.loads(want[DATA / "canonical-index.json"])) if DATA / "canonical-index.json" in want else "skipped"
    print(f"package data: {len(stale)} file(s) updated, {len(extra)} removed; index {n_idx} canonicals")


if __name__ == "__main__":
    main()
