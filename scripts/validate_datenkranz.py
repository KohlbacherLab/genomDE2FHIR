#!/usr/bin/env python3.11
"""
Validate genomDE Datenkranz JSON against the BfArM JSON Schemas (schemas/kdk + schemas/grz).

Branch is auto-detected and mapped to its root schema:
  case.diagnosisOd  -> schemas/kdk/Oncology.json
  case.diagnosisRd  -> schemas/kdk/RareDiseases.json
  donors+submission -> schemas/grz/grz-schema.json

The KDK root schemas $ref the other KDK files by absolute BfArM GitHub raw URL
(https://raw.githubusercontent.com/BfArM-MVH/MVGenomseq_KDK/main/KDK/...). We register every
local schema under that URL in a referencing Registry so validation runs fully offline against
the pinned local copies — no network, no version drift.

Requires jsonschema >= 4.18 (Draft 2020-12 + referencing) => run with python3.11:
  python3.11 scripts/validate_datenkranz.py [PATH ...]     # default: example-data
  python3.11 scripts/validate_datenkranz.py example-data/synthData-v1
Writes out/validation/schema-report.json (full per-file errors) + prints a summary.
"""
import argparse, collections, glob, json, os, sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry
    from referencing.jsonschema import DRAFT202012
except Exception as e:  # pragma: no cover
    sys.exit(f"needs jsonschema>=4.18 + referencing (run with python3.11): {e}")

ROOT = Path(__file__).resolve().parent.parent
KDK_DIR = ROOT / "schemas" / "kdk"
GRZ_SCHEMA = ROOT / "schemas" / "grz" / "grz-schema.json"
KDK_BASE = "https://raw.githubusercontent.com/BfArM-MVH/MVGenomseq_KDK/main/KDK/"


def build_registry() -> Registry:
    """Map each BfArM raw-GitHub schema URL -> the local file, so $refs resolve offline."""
    resources = []
    for f in KDK_DIR.rglob("*.json"):
        rel = f.relative_to(KDK_DIR).as_posix()          # e.g. OncologyCase.json | data-types/Coding.json
        url = KDK_BASE + rel
        resources.append((url, DRAFT202012.create_resource(json.loads(f.read_text()))))
    return Registry().with_resources(resources)


def classify(dk) -> str:
    if not isinstance(dk, dict):
        return "unknown"
    if "donors" in dk and "submission" in dk:
        return "grz"
    case = dk.get("case") or {}
    if "diagnosisOd" in case:
        return "oncology"
    if "diagnosisRd" in case:
        return "rare-disease"
    if "metadata" in dk and "metaData" not in dk:
        return "legacy-variant"
    return "unknown"


def make_validators(registry):
    roots = {
        "oncology": json.loads((KDK_DIR / "Oncology.json").read_text()),
        "rare-disease": json.loads((KDK_DIR / "RareDiseases.json").read_text()),
        "grz": json.loads(GRZ_SCHEMA.read_text()),
    }
    return {b: Draft202012Validator(s, registry=registry) for b, s in roots.items()}


def err_path(e):
    return "/" + "/".join(str(p) for p in e.absolute_path) if e.absolute_path else "(root)"


def validate_file(path, validators):
    try:
        dk = json.loads(Path(path).read_text())
    except Exception as e:
        return {"branch": "unreadable", "ok": False, "errors": [{"path": "(file)", "msg": f"unreadable: {e}"}]}
    branch = classify(dk)
    v = validators.get(branch)
    if v is None:
        return {"branch": branch, "ok": None, "errors": []}   # no schema for this branch
    errs = sorted(v.iter_errors(dk), key=lambda e: list(e.absolute_path))
    return {"branch": branch, "ok": not errs,
            "errors": [{"path": err_path(e), "msg": e.message[:200],
                        "validator": e.validator} for e in errs]}


def discover(paths):
    files = []
    for p in paths:
        p = ROOT / p if not os.path.isabs(p) else Path(p)
        if p.is_dir():
            files += [Path(x) for x in glob.glob(str(p / "**" / "*.json"), recursive=True)]
        elif p.is_file():
            files.append(p)
    return sorted(set(files))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=["example-data"])
    ap.add_argument("--show", type=int, default=15, help="top N error patterns to print per branch")
    a = ap.parse_args()
    paths = a.paths or ["example-data"]

    registry = build_registry()
    validators = make_validators(registry)
    files = discover(paths)
    if not files:
        sys.exit(f"no JSON files under {paths}")

    per_branch = collections.defaultdict(lambda: {"total": 0, "valid": 0, "invalid": 0, "noschema": 0})
    patterns = collections.defaultdict(collections.Counter)   # branch -> Counter of (path, validator, msg-head)
    cases = []
    for i, f in enumerate(files, 1):
        r = validate_file(f, validators)
        b = r["branch"]; s = per_branch[b]; s["total"] += 1
        if r["ok"] is None:
            s["noschema"] += 1
        elif r["ok"]:
            s["valid"] += 1
        else:
            s["invalid"] += 1
            for e in r["errors"]:
                patterns[b][(e["path"], e.get("validator"), e["msg"][:70])] += 1
        cases.append({"file": str(f.relative_to(ROOT)), **r})
        if i % 500 == 0:
            sys.stderr.write(f"  ...{i}/{len(files)}\n")

    out = ROOT / "out" / "validation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "schema-report.json").write_text(json.dumps(
        {"schemas": "schemas/kdk (KDK) + schemas/grz (GRZ)", "roots": paths,
         "summary": per_branch, "cases": cases}, indent=2, ensure_ascii=False))

    print(f"\n=== Datenkranz JSON-Schema validation ({len(files)} files) ===")
    print(f"{'branch':16} {'total':>6} {'valid':>6} {'invalid':>7} {'no-schema':>9}")
    for b in ("oncology", "rare-disease", "grz", "legacy-variant", "unknown", "unreadable"):
        if b in per_branch:
            s = per_branch[b]
            print(f"{b:16} {s['total']:>6} {s['valid']:>6} {s['invalid']:>7} {s['noschema']:>9}")
    for b, ctr in patterns.items():
        if not ctr:
            continue
        print(f"\n--- {b}: top error patterns (of {per_branch[b]['invalid']} invalid files) ---")
        for (path, val, msg), n in ctr.most_common(a.show):
            print(f"  {n:5}x [{val}] {path}: {msg}")
    print("\nfull per-file report: out/validation/schema-report.json")


if __name__ == "__main__":
    main()
