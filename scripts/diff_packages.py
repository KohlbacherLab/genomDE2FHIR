#!/usr/bin/env python3
"""Diff two versions of a FHIR NPM package from ~/.fhir/packages: StructureDefinition snapshots
(min/max/types/targets/binding/pattern/fixed/slicing/mustSupport), ValueSet compose, CodeSystem
concepts, package dependencies.

Usage: python3 scripts/diff_packages.py <module> <from> <to> [--all]
   e.g. python3 scripts/diff_packages.py onkologie 2026.0.3 2027.0.0-ballot.1
<module> = kerndatensatz module name or a full package name. --all also lists cosmetic changes.
# ponytail: snapshot-only, element-id keyed; no rename detection — a renamed slice shows as removed+added.
"""
import json, sys
from pathlib import Path

CACHE = Path.home() / ".fhir" / "packages"
MII = "de.medizininformatikinitiative.kerndatensatz."
KEYS = ("min", "max", "mustSupport", "patternCodeableConcept", "patternCoding", "patternUri", "fixedUri", "fixedCode")


def load(pkg, version):
    d = CACHE / f"{pkg}#{version}" / "package"
    if not d.is_dir():
        sys.exit(f"missing {d} (download: curl -sL https://packages.simplifier.net/{pkg}/{version} | tar xz -C <dir>)")
    out = {"sd": {}, "vs": {}, "cs": {}, "deps": json.load(open(d / "package.json")).get("dependencies", {})}
    for f in d.glob("*.json"):
        try:
            r = json.load(open(f))
        except Exception:
            continue
        t = r.get("resourceType")
        if t == "StructureDefinition":
            out["sd"][r.get("id") or f.stem] = r
        elif t == "ValueSet":
            out["vs"][r.get("id") or f.stem] = r
        elif t == "CodeSystem":
            out["cs"][r.get("id") or f.stem] = r
    return out


def elem_sig(e):
    b = e.get("binding") or {}
    sl = e.get("slicing") or {}
    return {
        **{k: e.get(k) for k in KEYS if k in e},
        "type": sorted({t.get("code", "") + "|" + ",".join(t.get("targetProfile") or t.get("profile") or []) for t in e.get("type", [])}),
        "binding": (b.get("strength"), b.get("valueSet")),
        "slicing": sl.get("rules"),
        "constraints": sorted(c.get("key", "") for c in e.get("constraint", []) if c.get("key")),
    }


def diff_sd(a, b):
    ea = {e["id"]: elem_sig(e) for e in a.get("snapshot", {}).get("element", [])}
    eb = {e["id"]: elem_sig(e) for e in b.get("snapshot", {}).get("element", [])}
    out = []
    for k in sorted(set(ea) | set(eb)):
        if k not in ea:
            out.append((k, "added", "", json.dumps(eb[k], default=str)[:160]))
        elif k not in eb:
            out.append((k, "removed", json.dumps(ea[k], default=str)[:160], ""))
        elif ea[k] != eb[k]:
            for f in ea[k]:
                if ea[k].get(f) != eb[k].get(f):
                    out.append((k, f, json.dumps(ea[k].get(f), default=str), json.dumps(eb[k].get(f), default=str)))
    return out


def concepts(cs):
    acc = {}

    def walk(cc):
        for c in cc:
            acc[c["code"]] = c.get("display")
            walk(c.get("concept", []))

    walk(cs.get("concept", []))
    return acc


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    mod, v1, v2 = sys.argv[1:4]
    pkg = mod if "." in mod else MII + mod
    a, b = load(pkg, v1), load(pkg, v2)
    print(f"# {pkg}: {v1} -> {v2}")
    if a["deps"] != b["deps"]:
        print("deps:", {k: (a["deps"].get(k), b["deps"].get(k)) for k in sorted(set(a["deps"]) | set(b["deps"])) if a["deps"].get(k) != b["deps"].get(k)})
    for kind, label in (("sd", "StructureDefinition"), ("vs", "ValueSet"), ("cs", "CodeSystem")):
        add, rem = sorted(set(b[kind]) - set(a[kind])), sorted(set(a[kind]) - set(b[kind]))
        if add: print(f"{label} added: {add}")
        if rem: print(f"{label} removed: {rem}")
    for sid in sorted(set(a["sd"]) & set(b["sd"])):
        sa, sb = a["sd"][sid], b["sd"][sid]
        if sa.get("url") != sb.get("url"):
            print(f"\n## {sid}: URL CHANGED {sa.get('url')} -> {sb.get('url')}")
        rows = diff_sd(sa, sb)
        if rows:
            print(f"\n## {sid} ({len(rows)} element changes)")
            for k, f, x, y in rows:
                print(f"  {k} [{f}]: {x} -> {y}")
    for sid in sorted(set(a["vs"]) & set(b["vs"])):
        if a["vs"][sid].get("compose") != b["vs"][sid].get("compose"):
            print(f"\n## ValueSet {sid}: compose changed")
    for sid in sorted(set(a["cs"]) & set(b["cs"])):
        ca, cb = concepts(a["cs"][sid]), concepts(b["cs"][sid])
        if ca != cb:
            print(f"\n## CodeSystem {sid}: +{sorted(set(cb) - set(ca))} -{sorted(set(ca) - set(cb))} display-changed {[c for c in ca if c in cb and ca[c] != cb[c]]}")


if __name__ == "__main__":
    main()
