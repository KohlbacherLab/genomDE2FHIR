#!/usr/bin/env python3
"""Developer loop for builder work: pick schema-valid corpus files that contain a given source path,
convert them, validate the output with matchbox-2027 and group the content errors.

  python3 scripts/g2f_dev.py --branch oncology --path molecular.smallVariants --n 8
  python3 scripts/g2f_dev.py --branch grz --path donors --n 5 --profile-filter specimen
  python3 scripts/g2f_dev.py --files a.json b.json --no-validate

Prints: conversion status, warnings/drops for the selected path, and per profile the distinct content / source /
unchecked / waived / cascade / candidate / validator-error issues with counts (an ERROR verdict, i.e. validation could
not run, is printed per file). Exit 1 if any content or validator error remains for --profile-filter.
"""
import argparse
import collections
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "genomde2fhir" / "src"))
from genomde2fhir.cli import _out_name  # noqa: E402
from genomde2fhir.convert import convert  # noqa: E402
from genomde2fhir.io import dumps, loads  # noqa: E402
from genomde2fhir.validate import Matchbox, validate_bundle  # noqa: E402

MANIFEST = ROOT / "genomde2fhir" / "tests" / "corpus_manifest.json"
MB = os.environ.get("MB2027", "http://localhost:8091/matchboxv3/fhir")


def has_path(o, parts):
    if not parts:
        return o not in (None, "", [], {})
    if isinstance(o, list):
        return any(has_path(x, parts) for x in o)
    if isinstance(o, dict):
        k = parts[0].replace("[]", "")
        return k in o and has_path(o[k], parts[1:])
    return False


def pick(branch, path, n):
    files = json.loads(MANIFEST.read_text())[branch]["valid"]
    parts = [p for p in path.split(".") if p] if path else []
    out, seen_dirs = [], collections.Counter()
    for f in files:   # spread over corpora (dnpm/nct/ukdd/nse/grz/examples)
        d = str(Path(f).parent)
        if seen_dirs[d] >= max(1, n // 2):
            continue
        try:
            dk = loads((ROOT / f).read_text(encoding="utf-8"))
        except Exception:
            continue
        if has_path(dk, parts):
            out.append(f)
            seen_dirs[d] += 1
        if len(out) >= n:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", choices=["oncology", "rare-disease", "grz"])
    ap.add_argument("--path", default="")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--profile-set", default="2027")
    ap.add_argument("--no-validate", action="store_true")
    ap.add_argument("--profile-filter", default="", help="only report resources whose profile contains this")
    ap.add_argument("--out", default="/tmp/g2f-dev")
    a = ap.parse_args()
    files = a.files or pick(a.branch, a.path, a.n)
    if not files:
        sys.exit("no matching files")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    mb = None if a.no_validate else Matchbox(MB)
    issues = collections.defaultdict(collections.Counter)
    bad, taken = 0, set()   # output names as the CLI picks them: same-named inputs do not overwrite each other
    for f in files:
        dk = loads((ROOT / f if not Path(f).is_absolute() else Path(f)).read_text(encoding="utf-8"))
        bundle, rep = convert(dk, f, a.profile_set)
        rel = [w for w in rep.warnings if a.path in w[0] or w[0].startswith("(")]
        print(f"{rep.status:<9} {f}  resources={dict(rep.resources)}")
        if rep.error:
            print("   ERROR", rep.error[:1500])
        for p, m in rel[:12]:
            print(f"   warn {p}: {m[:220]}")
        for p, v, r in rep.dropped:
            if a.path in p:
                print(f"   drop {p}={v!r}: {r}")
        if bundle is None:
            continue
        (out / _out_name(f, taken)).write_text(dumps(bundle), encoding="utf-8")
        if mb:
            res = validate_bundle(bundle, mb, source=dk)   # never raises; ERROR = validation could not run
            if res["verdict"] == "ERROR":
                print(f"   validation ERROR: {res.get('error', '')[:300]}")
            for r in res["resources"]:
                prof = (r["profile"] or r["type"]).split("/")[-1]
                if a.profile_filter and a.profile_filter not in prof:
                    continue
                for i in r["issues"]:
                    if i["class"] == "info":
                        continue
                    issues[(prof, i["class"])][f"{i['expression']} :: {i['text'][:260]}"] += 1
                    bad += i["class"] in ("content", "validator-error")
    for (prof, cls), c in sorted(issues.items()):
        print(f"\n== {prof} [{cls}] {sum(c.values())}")
        for msg, n in c.most_common(25):
            print(f"   {n:>3}x {msg}")
    print(f"\ncontent errors: {bad}; bundles in {out}")
    sys.exit(1 if bad and a.profile_filter else 0)


if __name__ == "__main__":
    main()
