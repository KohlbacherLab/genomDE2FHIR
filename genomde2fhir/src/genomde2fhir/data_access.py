"""Package data: canonical index (profile existence per profile set), mapping rows, MV-GenomSeq terminology."""
import csv
import json
from functools import lru_cache
from importlib import resources

DATA = resources.files("genomde2fhir") / "data"
BRANCH_CSV = {"oncology": "mapping_kdk_oncology.csv", "rare-disease": "mapping_kdk_rarediseases.csv",
              "grz": "mapping_grz.csv"}


@lru_cache(maxsize=None)
def canonical_index() -> dict:
    """{url: {"type", "kind", "rtype", "sets": [...]}} for every StructureDefinition/ValueSet/CodeSystem
    in the 2026 and 2027 package stacks plus de.genomde.mvgs (built by scripts/build_canonical_index.py)."""
    p = DATA / "canonical-index.json"
    return json.loads(p.read_text()) if p.is_file() else {}


@lru_cache(maxsize=None)
def mapping_rows(branch: str) -> dict:
    """{path: row} from the bundled copy of the reviewed mapping table (git CSVs are the source)."""
    p = DATA / "mapping" / BRANCH_CSV[branch]
    if not p.is_file():
        return {}
    with p.open(newline="") as f:
        return {r["path"]: r for r in csv.DictReader(f)}


@lru_cache(maxsize=None)
def mvgs_resources() -> dict:
    """{canonical url: resource} for every CodeSystem/ValueSet/ConceptMap/NamingSystem/StructureDefinition
    shipped in de.genomde.mvgs (mirrored into data/mvgs/)."""
    out = {}
    d = DATA / "mvgs"
    if d.is_dir():
        for f in d.iterdir():
            if f.name.endswith(".json"):
                r = json.loads(f.read_text())
                if r.get("url"):
                    out[r["url"]] = r
    return out
