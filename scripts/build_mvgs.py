#!/usr/bin/env python3
"""Package mvgs-ig/ (de.genomde.mvgs: logical models, local profiles/extensions, CodeSystems, ValueSets,
ConceptMaps, NamingSystems, StructureMaps) as an NPM FHIR package and optionally push it to matchbox.

  python3 scripts/build_mvgs.py                     -> dist/de.genomde.mvgs-<version>.tgz
  python3 scripts/build_mvgs.py --install URL       -> also PUT every resource to matchbox (onlyOneEngine)
  python3 scripts/build_mvgs.py --install URL --only CodeSystem,ConceptMap

  python3 scripts/build_mvgs.py --install URL --only none --maps             -> push the FML maps only
  python3 scripts/build_mvgs.py --install URL --only none --maps --test-maps -> also the engine probes in mappers/fml/test

FML maps (mappers/fml/*.map, with --test-maps also mappers/fml/test/*.map) are POSTed as text/fhir-mapping to
{URL}/StructureMap. matchbox 4.1.21 upserts a POSTed map by its url (resource id = map name), so re-running is
idempotent. A map binds the maps it `imports` when it is loaded, so maps are pushed imported-first (DatenkranzCommon
before everything else) and every run pushes all of them: after a library changes, its importers must be reloaded
(mappers/fml/README.md).
"""
import argparse
import io
import json
import re
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "mvgs-ig"
ORDER = ["CodeSystem", "ValueSet", "NamingSystem", "StructureDefinition", "ConceptMap", "StructureMap"]
# matchbox 4.1.21 has no NamingSystem resource provider (PUT -> HAPI-0302 unknown resource type)
NO_INSTALL = {"NamingSystem": "matchbox has no NamingSystem endpoint (HAPI-0302); in the package only"}


def resources():
    out = []
    for f in sorted((SRC / "input").glob("*.json")):
        r = json.loads(f.read_text())
        out.append((f.name, r))
    out.sort(key=lambda x: (ORDER.index(x[1]["resourceType"]) if x[1]["resourceType"] in ORDER else 99, x[0]))
    return out


def build() -> Path:
    pkg = json.loads((SRC / "package.json").read_text())
    res = resources()
    index = {"index-version": 1, "files": []}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        def add(name, data: bytes):
            ti = tarfile.TarInfo(f"package/{name}")
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
        for name, r in res:
            index["files"].append({k: v for k, v in {"filename": name, "resourceType": r["resourceType"], "id": r.get("id"),
                                   "url": r.get("url"), "version": r.get("version"), "kind": r.get("kind"),
                                   "type": r.get("type")}.items() if v})
            add(name, json.dumps(r, ensure_ascii=False, indent=1).encode())
        add("package.json", json.dumps(pkg, indent=1).encode())
        add(".index.json", json.dumps(index, indent=1).encode())
    out = ROOT / "dist" / f"{pkg['name']}-{pkg['version']}.tgz"
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(buf.getvalue())
    print(f"built {out.relative_to(ROOT)} ({len(res)} resources)")
    return out


def _send(method, url, data, ctype):
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": ctype, "Accept": "application/fhir+json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, r.read()[:300]
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read()[:600]


MAP_URL = re.compile(r"^///\s*url\s*=\s*'([^']+)'", re.M)
MAP_IMPORT = re.compile(r'^\s*imports\s+"([^"]+)"', re.M)


def map_files(test_maps: bool = False) -> list[Path]:
    """FML maps in load order: every map after the maps it imports (DatenkranzCommon first)."""
    d = ROOT / "mappers" / "fml"
    files = sorted(d.glob("*.map")) + (sorted((d / "test").glob("*.map")) if test_maps else [])
    by_url, deps = {}, {}
    for f in files:
        txt = f.read_text(encoding="utf-8")
        m = MAP_URL.search(txt)
        if not m:
            raise ValueError(f"{f}: no '/// url = ...' header")
        if m.group(1) in by_url:
            raise ValueError(f"{f}: duplicate map url {m.group(1)} (also {by_url[m.group(1)]})")
        by_url[m.group(1)] = f
        deps[f] = MAP_IMPORT.findall(txt)
    out, state = [], {}

    def visit(f, stack):
        if state.get(f) == "done":
            return
        if state.get(f) == "busy":
            raise ValueError(f"import cycle: {' -> '.join(x.name for x in stack + [f])}")
        state[f] = "busy"
        for u in deps[f]:
            if u in by_url:          # imports outside this directory must already be on the server
                visit(by_url[u], stack + [f])
        state[f] = "done"
        out.append(f)
    for f in files:
        visit(f, [])
    return out


def push_maps(base: str, test_maps: bool = False) -> int:
    """POST every map (imported-first); returns the number of failures."""
    base = base.rstrip("/")
    bad = 0
    for m in map_files(test_maps):
        st, body = _send("POST", f"{base}/StructureMap", m.read_bytes(), "text/fhir-mapping")
        if st >= 300:
            bad += 1
            print(f"  FAIL {st} {m.relative_to(ROOT)}: {body.decode(errors='replace')[:300]}")
    return bad


def install(base: str, only: set | None, maps: bool, test_maps: bool = False):
    base = base.rstrip("/")
    bad = 0
    for name, r in resources():
        if only and r["resourceType"] not in only:
            continue
        if r["resourceType"] in NO_INSTALL:   # still packaged; matchbox's store rejects the type
            print(f"  skip {name}: {NO_INSTALL[r['resourceType']]}")
            continue
        st, body = _send("PUT", f"{base}/{r['resourceType']}/{r['id']}", json.dumps(r).encode(), "application/fhir+json")
        if st >= 300:
            bad += 1
            print(f"  FAIL {st} {name}: {body.decode(errors='replace')[:300]}")
    if maps:
        bad += push_maps(base, test_maps)
    print(f"installed into {base}: {'ok' if not bad else f'{bad} failure(s)'}")
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", metavar="MATCHBOX_URL")
    ap.add_argument("--only", help="comma-separated resource types")
    ap.add_argument("--maps", action="store_true", help="also POST mappers/fml/*.map (imported maps first)")
    ap.add_argument("--test-maps", action="store_true", help="with --maps: also the probes in mappers/fml/test")
    a = ap.parse_args()
    build()
    if a.install:
        sys.exit(1 if install(a.install, set(a.only.split(",")) if a.only else None, a.maps, a.test_maps) else 0)
