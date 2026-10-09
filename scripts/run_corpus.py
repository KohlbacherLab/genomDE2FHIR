#!/usr/bin/env python3
"""End-to-end corpus run for the 2027 profile set -> docs/E2E-REPORT-2027.md + out/e2e-2027/results.json

For every file of the corpus manifest (genomde2fhir/tests/corpus_manifest.json):
  convert (Python path) -> dispositions; schema-invalid inputs must be rejected
  validate a sample per branch with matchbox-2027 (per resource + bundle), classified content/unchecked/waived
  ingest the sample into HAPI-2027 twice (second ingest must not create new resources)
  optional --fml: matchbox $transform with the FML maps, ingest, and graph-aware parity against the Python bundle

Usage: python3 scripts/run_corpus.py [--sample 25] [--branches oncology,rare-disease,grz] [--fml] [--no-ingest]
"""
import argparse
import collections
import datetime
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "genomde2fhir" / "src"))
from genomde2fhir import __version__  # noqa: E402
from genomde2fhir.convert import convert  # noqa: E402
from genomde2fhir.data_access import mapping_rows  # noqa: E402
from genomde2fhir.validate import Hapi, Matchbox, validate_bundle  # noqa: E402

MB = os.environ.get("MB2027", "http://localhost:8091/matchboxv3/fhir")
HAPI = os.environ.get("HAPI2027", "http://localhost:8092/fhir")
OUT = ROOT / "out" / "e2e-2027"
MAPS = {"oncology": "https://genomde.de/fhir/StructureMap/DatenkranzOncologyToMii",
        "rare-disease": "https://genomde.de/fhir/StructureMap/DatenkranzRareDiseaseToMii",
        "grz": "https://genomde.de/fhir/StructureMap/DatenkranzGrzToMii"}


def spread(files, n):
    """n files spread evenly over the list (covers all sub-corpora)."""
    if len(files) <= n:
        return files
    step = len(files) / n
    return [files[int(i * step)] for i in range(n)]


def canonical(bundle):
    """Graph-aware canonical form: references replaced by '<Type>/<profile tail>', ids/fullUrls/meta dropped;
    returns a multiset of canonical resource strings."""
    by_url = {e["fullUrl"]: e["resource"] for e in bundle.get("entry", [])}

    def label(r):
        prof = (r.get("meta", {}).get("profile") or [""])[0].split("/")[-1]
        return f"{r['resourceType']}/{prof}"

    def norm(o):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                if k in ("id", "meta") or (k == "text" and "resourceType" in o):   # narrative only, not CodeableConcept.text
                    continue
                if k == "reference" and isinstance(v, str):
                    tgt = by_url.get(v)
                    out[k] = label(tgt) if tgt else v.split("/")[0]
                elif k == "identifier" and isinstance(v, list):
                    ids = [i for i in v if "resource-key" not in i.get("system", "")]
                    if ids:            # the FML resource key may have been the only identifier
                        out[k] = norm(ids)
                else:
                    out[k] = norm(v)
            return out
        if isinstance(o, list):
            return sorted((norm(x) for x in o), key=lambda x: json.dumps(x, sort_keys=True))
        return o
    return collections.Counter(json.dumps(norm(e["resource"]), sort_keys=True)
                               for e in bundle.get("entry", []) if e["resource"]["resourceType"] != "Provenance")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=25)
    ap.add_argument("--branches", default="oncology,rare-disease,grz")
    ap.add_argument("--fml", action="store_true")
    ap.add_argument("--no-ingest", action="store_true")
    ap.add_argument("--profile-set", default="2027")
    a = ap.parse_args()
    manifest = json.loads((ROOT / "genomde2fhir" / "tests" / "corpus_manifest.json").read_text())
    mb, hapi = Matchbox(MB), (None if a.no_ingest else Hapi(HAPI))
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"generated": datetime.datetime.now().isoformat(timespec="seconds"), "version": __version__,
           "profile_set": a.profile_set, "matchbox": MB, "hapi": None if a.no_ingest else HAPI, "branches": {}}
    for branch in a.branches.split(","):
        t0 = time.time()
        valid, invalid = manifest[branch]["valid"], manifest[branch]["invalid"]
        status, resources, covered, drops, reps, warns = (collections.Counter() for _ in range(6))
        errors, bundles = [], {}
        for f in valid:
            b, r = convert(json.loads((ROOT / f).read_text()), f, a.profile_set)
            status[r.status] += 1
            if b is None:
                errors.append((f, r.status, (r.error or "; ".join(r.input_findings))[:400]))
                continue
            resources.update(r.resources)
            covered.update(r.covered)
            drops.update(p for p, _, _ in r.dropped)
            reps.update(r.representations)
            warns.update(m.split(":")[0][:80] for p, m in r.warnings if p.startswith("("))
            bundles[f] = b
        rejected_ok = 0
        for f in invalid:
            b, r = convert(json.loads((ROOT / f).read_text()), f, a.profile_set)
            rejected_ok += (r.status == "rejected")
        mapped = {p for p, row in mapping_rows(branch).items() if row.get("status") == "MAPPED"}
        sample = spread(sorted(bundles), a.sample)
        verdicts, issues = collections.Counter(), collections.defaultdict(collections.Counter)
        ingest = collections.Counter()
        parity, fml_verdicts, fml_diff = collections.Counter(), collections.Counter(), collections.Counter()
        for f in sample:
            b = bundles[f]
            v = validate_bundle(b, mb, source=json.loads((ROOT / f).read_text()))
            verdicts[v["verdict"]] += 1
            for rr in v["resources"]:
                prof = (rr["profile"] or rr["type"]).split("/")[-1]
                for i in rr["issues"]:
                    if i["class"] != "info":
                        issues[(prof, i["class"])][f"{i['expression']} :: {i['text'][:200]}"] += 1
            if hapi:
                ok1, _ = hapi.transaction(b)
                before = {t: hapi.count(t) for t in ("Patient", "Observation", "Condition")}
                ok2, _ = hapi.transaction(b)
                after = {t: hapi.count(t) for t in ("Patient", "Observation", "Condition")}
                ingest["ok" if ok1 and ok2 else "fail"] += 1
                ingest["idempotent" if before == after else "duplicated"] += 1
            if a.fml:
                dk = json.loads((ROOT / f).read_text())
                st, fb = mb.transform(dk, MAPS[branch])
                if st >= 300 or fb.get("resourceType") != "Bundle":
                    parity["transform-failed"] += 1
                    continue
                ca, cb = canonical(b), canonical(fb)
                parity["equal" if ca == cb else "different"] += 1
                for side, diff in (("only-python", ca - cb), ("only-fml", cb - ca)):
                    for s, n in diff.items():
                        fml_diff[f"{side}: {json.loads(s).get('resourceType')}"] += n
                fml_verdicts[validate_bundle(fb, mb, source=dk)["verdict"]] += 1
                if hapi:
                    okf, _ = hapi.transaction(fb)
                    before = {t: hapi.count(t) for t in ("Patient", "Observation", "Condition")}
                    okf2, _ = hapi.transaction(fb)
                    after = {t: hapi.count(t) for t in ("Patient", "Observation", "Condition")}
                    parity["fml-ingest-ok" if okf and okf2 else "fml-ingest-fail"] += 1
                    parity["fml-idempotent" if before == after else "fml-duplicated"] += 1
        res["branches"][branch] = {
            "valid_files": len(valid), "invalid_files": len(invalid), "invalid_rejected": rejected_ok,
            "conversion": dict(status), "errors": errors[:20], "resources": dict(resources),
            "mapped_rows": len(mapped), "mapped_rows_emitted": len(mapped & set(covered)),
            "mapped_rows_never_emitted": sorted(mapped - set(covered)),
            "dropped_by_path": dict(drops.most_common(30)), "representations": dict(reps),
            "pipeline_warnings": dict(warns), "sample": len(sample), "verdicts": dict(verdicts),
            "issues": {f"{p} [{c}]": dict(cnt.most_common(15)) for (p, c), cnt in sorted(issues.items())},
            "ingest": dict(ingest), "parity": dict(parity), "fml_verdicts": dict(fml_verdicts),
            "fml_differences": dict(fml_diff.most_common(20)), "seconds": round(time.time() - t0, 1)}
        print(f"{branch}: {dict(status)} rejected {rejected_ok}/{len(invalid)} verdicts {dict(verdicts)} ingest {dict(ingest)} parity {dict(parity)}")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    write_report(res)


def write_report(res):
    L = [f"# genomde2fhir E2E report — profile set {res['profile_set']}", "",
         f"_generated {res['generated']} · genomde2fhir {res['version']} · matchbox `{res['matchbox']}` · HAPI `{res['hapi']}`_", "",
         "Verdicts per sampled bundle: **PASS** = no error; **INCONCLUSIVE** = only errors the terminology server cannot check "
         "(German/OBO systems, ICD-O-3 2014/2019); **DATA-QUALITY** = an invalid code copied from the input file (e.g. HGVS "
         "without reference sequence, non-existent SNOMED codes in the synthetic data); **FAIL** = at least one content error "
         "of the converter's own output. Cascades (reference failures caused by an error of the referenced resource) are "
         "counted at their root; waived = listed ballot-package defects (`genomde2fhir/validate.py` WAIVERS).", ""]
    for b, d in res["branches"].items():
        L += [f"## {b}", "",
              "| measure | value |", "|:--|:--|",
              f"| valid inputs converted | {d['conversion'].get('converted', 0)} / {d['valid_files']} |",
              f"| invalid inputs rejected | {d['invalid_rejected']} / {d['invalid_files']} |",
              f"| MAPPED rows emitted at least once | {d['mapped_rows_emitted']} / {d['mapped_rows']} |",
              f"| sampled bundles validated | {d['sample']} |",
              f"| verdicts | {', '.join(f'{k} {v}' for k, v in d['verdicts'].items())} |",
              f"| HAPI ingest (twice) | {', '.join(f'{k} {v}' for k, v in d['ingest'].items()) or '—'} |",
              f"| FML parity, ingest (twice) | {', '.join(f'{k} {v}' for k, v in d['parity'].items()) or 'not run'} |",
              f"| FML verdicts | {', '.join(f'{k} {v}' for k, v in d.get('fml_verdicts', {}).items()) or 'not run'} |",
              f"| resources | {sum(d['resources'].values())} ({', '.join(f'{k} {v}' for k, v in sorted(d['resources'].items()))}) |", ""]
        if d.get("fml_differences"):
            L += ["FML vs Python resources that differ (canonical form, resource count): " +
                  ", ".join(f"{k} {v}" for k, v in d["fml_differences"].items()), ""]
        if d["errors"]:
            L += ["Conversion errors:", ""] + [f"- `{f}`: {s} — {m[:200]}" for f, s, m in d["errors"]] + [""]
        if d["mapped_rows_never_emitted"]:
            L += ["MAPPED rows never emitted on this corpus (no source data, or a builder gap):", "",
                  ", ".join(f"`{p}`" for p in d["mapped_rows_never_emitted"]), ""]
        if d["issues"]:
            L += ["Validation issues (sample):", ""]
            for k, msgs in d["issues"].items():
                L += [f"- **{k}** — " + "; ".join(f"{n}× {m}" for m, n in list(msgs.items())[:6])]
            L += [""]
        if d["dropped_by_path"]:
            L += ["Dropped values (path: count): " + ", ".join(f"`{p}` {n}" for p, n in d["dropped_by_path"].items()), ""]
    (ROOT / "docs" / "E2E-REPORT-2027.md").write_text("\n".join(L) + "\n")
    print("wrote docs/E2E-REPORT-2027.md")


if __name__ == "__main__":
    main()
