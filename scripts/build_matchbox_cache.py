#!/usr/bin/env python3
"""Build infra/matchbox-2027/package-cache from ~/.fhir/packages: the dependency closure of the 2027 stack
plus de.genomde.mvgs (dist/), in FHIR package-cache layout (<name>#<version>/package/...).

Workaround (matchbox 4.1.21 / HAPI JPA): the NPM package tables store StructureDefinition.type in a
VARCHAR(100) column; 13 MII logical models (kind=logical) have a canonical-URL type longer than that and
make the whole package install fail. They carry no instance constraints, so they are removed from the
cache copy (and from .index.json). The user's ~/.fhir/packages is never modified.

Usage: python3 scripts/build_matchbox_cache.py [--clean]
"""
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.path.expanduser("~/.fhir/packages"))
OUT = ROOT / "infra" / "matchbox-2027" / "package-cache"
MII = "de.medizininformatikinitiative.kerndatensatz."
ROOTS = [MII + "mtb#2027.0.0-ballot.1", MII + "onkologie#2027.0.0-ballot.1", MII + "molgen#2027.0.0-ballot.1",
         MII + "seltene#2027.0.0-ballot", MII + "consent#2027.0.0-ballot", MII + "base#2027.0.0-ballot",
         MII + "meta#2027.0.0-ballot", MII + "biobank#2027.0.0-ballot", MII + "medikation#2027.0.0-ballot",
         MII + "studie#2027.0.0-ballot", MII + "patho#2027.0.0-ballot", MII + "laborbefund#2027.0.0-ballot",
         "hl7.fhir.uv.genomics-reporting#3.0.0", "de.basisprofil.r4#1.6.0", "hl7.fhir.r4.core#4.0.1"]
MAX_TYPE = 100


def closure(roots):
    seen, missing, todo = [], [], list(roots)
    while todo:
        k = todo.pop()
        if k in seen or k in missing:
            continue
        p = CACHE / k / "package" / "package.json"
        if not p.exists():
            missing.append(k)
            continue
        seen.append(k)
        todo += [f"{n}#{v}" for n, v in json.loads(p.read_text()).get("dependencies", {}).items()]
    return seen, missing


def strip_long_types(pkg_dir: Path) -> list[str]:
    removed = []
    for f in pkg_dir.glob("*.json"):
        if f.name in ("package.json", ".index.json"):
            continue
        try:
            r = json.loads(f.read_text())
        except Exception:
            continue
        if r.get("resourceType") == "StructureDefinition" and len(r.get("type") or "") > MAX_TYPE:
            f.unlink()
            removed.append(f.name)
    idx = pkg_dir / ".index.json"
    if removed and idx.exists():
        j = json.loads(idx.read_text())
        j["files"] = [e for e in j.get("files", []) if e.get("filename") not in removed]
        idx.write_text(json.dumps(j, indent=1))
    return removed


def main():
    if "--clean" in sys.argv and OUT.exists():
        for d in OUT.iterdir():
            if d.is_dir():
                shutil.rmtree(d)
    OUT.mkdir(parents=True, exist_ok=True)
    keys, missing = closure(ROOTS)
    stripped = {}
    for k in keys:
        dst = OUT / k
        if not dst.exists():
            shutil.copytree(CACHE / k, dst)
        rm = strip_long_types(dst / "package")
        long_in_source = [f.name for f in (CACHE / k / "package").glob("StructureDefinition-*.json")
                          if len(json.loads(f.read_text()).get("type") or "") > MAX_TYPE]
        if rm or long_in_source:
            stripped[k] = rm or long_in_source
    for tgz in sorted((ROOT / "dist").glob("de.genomde.mvgs-*.tgz")) if (ROOT / "dist").exists() else []:
        ver = tgz.stem.split("-", 1)[1]
        dst = OUT / f"de.genomde.mvgs#{ver}"
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        with tarfile.open(tgz) as t:
            t.extractall(dst, filter="data")
    # matchbox 4.1.x installs from the registry, not from this cache: write patched tarballs for the stripped
    # packages; config/application.yaml lists them first with url: file:///config/packages/<name>-<version>.tgz
    tgz_dir = ROOT / "infra" / "matchbox-2027" / "config" / "packages"
    tgz_dir.mkdir(parents=True, exist_ok=True)
    for k in stripped:
        name, ver = k.split("#")
        with tarfile.open(tgz_dir / f"{name}-{ver}.tgz", "w:gz") as t:
            t.add(OUT / k / "package", arcname="package")
    for d in OUT.rglob("*"):
        try:
            d.chmod(0o777 if d.is_dir() else 0o666)
        except PermissionError:
            pass
    print(f"cache: {len(keys)} packages; not in ~/.fhir/packages (served by matchbox itself): {missing}")
    for k, rm in stripped.items():
        print(f"  stripped from {k}: {rm}")


if __name__ == "__main__":
    main()
