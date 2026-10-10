#!/usr/bin/env python3
"""End-to-end corpus run -> docs/E2E-REPORT-<profile set>.md + out/e2e-<profile set>/results.json

For every file of the corpus manifest (genomde2fhir/tests/corpus_manifest.json):
  convert (Python path) -> dispositions; schema-invalid inputs must be rejected (manifest files that are not in
    the checkout, e.g. the untracked example-data/synthData-v1/, are skipped and counted)
  validate a sample per branch with matchbox-2027 (per resource + bundle), classified content/unchecked/waived;
    --profile-set 2026 is validated only with --matchbox-2026 URL (a matchbox loaded with the 2026 packages); a
    matchbox that lists the KDS packages of the other profile set is refused (not validated; --gate fails)
  ingest the sample into HAPI-2027 twice (the second transaction must answer 200 for every entry and leave the
    uncached counts of every resource type in the Bundle unchanged)
  optional --fml (2027 only): matchbox $transform with the FML maps, ingest, and graph-aware parity against the
    Python bundle (canonical(): references resolved to the target's content at every depth, meta.profile compared)
  --gate: exit 1 on any failure (gate_failures()); used by the nightly workflow. A run without validation (2026
    without --matchbox-2026) passes on its other checks only and says so ('passed without validation')

Usage: python3 scripts/run_corpus.py [--sample 25] [--branches oncology,rare-disease,grz] [--fml] [--no-ingest]
                                     [--profile-set 2027|2026 [--matchbox-2026 URL]] [--gate]
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "genomde2fhir" / "src"))
from genomde2fhir import __version__  # noqa: E402
from genomde2fhir.cli import _profile_set_mismatch  # noqa: E402
from genomde2fhir.convert import convert  # noqa: E402
from genomde2fhir.data_access import mapping_rows  # noqa: E402
from genomde2fhir.io import dumps, loads  # noqa: E402
from genomde2fhir.validate import Hapi, Matchbox, validate_bundle  # noqa: E402

MB = os.environ.get("MB2027", "http://localhost:8091/matchboxv3/fhir")
HAPI = os.environ.get("HAPI2027", "http://localhost:8092/fhir")
MAPS = {"oncology": "https://genomde.de/fhir/StructureMap/DatenkranzOncologyToMii",
        "rare-disease": "https://genomde.de/fhir/StructureMap/DatenkranzRareDiseaseToMii",
        "grz": "https://genomde.de/fhir/StructureMap/DatenkranzGrzToMii"}


def spread(files, n):
    """n files spread evenly over the list (covers all sub-corpora)."""
    if len(files) <= n:
        return files
    step = len(files) / n
    return [files[int(i * step)] for i in range(n)]


def canonical(bundle, deep: bool = True):
    """Graph-aware canonical form; returns a multiset of canonical resource strings (Provenance left out).
    Dropped: ids, fullUrls, narrative, resource-key identifiers and meta except meta.profile (kept, sorted).
    A reference inside the Bundle becomes the target's content key '<Type>/<profile tail>#<hash>', the hash taken over
    the target's own canonical form with ITS references again replaced by content keys, computed bottom-up to a
    fixpoint: a resource is keyed once all its targets are (the exact recursive content hash, any depth). The n
    members of a reference cycle (e.g. Condition.stage.assessment <-> tumour-extent Observation.focus) start from
    their labels and are rehashed 2n times with the previous round's keys (colour refinement; targets outside the
    cycle keep their keys): refining two n-member cycles together stabilizes within 2n - 1 rounds, so two members get
    the same key only if their unfoldings are identical at every depth, and the rounds are bounded (cycles terminate).
    A reference to the wrong one of two same-profile resources therefore changes the result unless the two have the
    same content at every depth, including what they reference in turn, and a difference only changes the strings of
    the resources that reach it. Unresolved references keep their resource type only. deep=False labels references
    '<Type>/<profile tail>' only: for comparing partial outputs whose reference targets are deliberately incomplete
    (probe maps with placeholder resources). The profile tail is that of the alphabetically first meta.profile
    (meta.profile itself is compared sorted, so its order never matters).
    Decimals compare by their written spelling (io.Num from io.loads, as validate.py parses $transform output), so
    58.50 and 58.5 differ; the strings are io.dumps text of key-sorted objects (valid JSON)."""
    by_url = {e["fullUrl"]: e["resource"] for e in bundle.get("entry", [])}

    def label(r):
        prof = sorted(r.get("meta", {}).get("profile") or [""])[0].split("/")[-1]
        return f"{r['resourceType']}/{prof}"

    def norm(o, ref):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                if k == "id" or (k == "text" and "resourceType" in o):   # narrative only, not CodeableConcept.text
                    continue
                if k == "meta":
                    if "resourceType" in o and (v or {}).get("profile"):
                        out[k] = {"profile": sorted(v["profile"])}
                    continue
                if k == "reference" and isinstance(v, str):
                    out[k] = ref(v) if v in by_url else v.split("/")[0]
                elif k == "identifier" and isinstance(v, list):
                    ids = [i for i in v if "resource-key" not in i.get("system", "")]
                    if ids:            # the FML resource key may have been the only identifier
                        out[k] = norm(ids, ref)
                else:
                    out[k] = norm(v, ref)
            return dict(sorted(out.items()))
        if isinstance(o, list):
            return sorted((norm(x, ref) for x in o), key=text)
        return o

    def text(o):
        return dumps(o, indent=None)

    def content_key(u, keys):
        r = by_url[u]
        return f"{label(r)}#{hashlib.sha1(text(norm(r, keys.__getitem__)).encode()).hexdigest()[:16]}"

    def refine(cycle, keys):
        # deliberately simple: 2n rounds over n members (quadratic); the cycles of these Bundles have two members
        cur = {u: label(by_url[u]) for u in cycle}
        for _ in range(2 * len(cycle)):
            cur = {u: content_key(u, keys | cur) for u in cycle}
        return cur

    if not deep:
        ref = lambda v: label(by_url[v])   # noqa: E731
    else:
        targets = {}
        for u, r in by_url.items():
            targets[u] = seen = set()
            norm(r, lambda v, seen=seen: seen.add(v) or v)
        keys, todo = {}, set(by_url)

        def reachable(u):   # unkeyed resources reachable from u (u itself only over a cycle)
            seen, stack = set(), [v for v in targets[u] if v in todo]
            while stack:
                v = stack.pop()
                if v not in seen:
                    seen.add(v)
                    stack += [w for w in targets[v] if w in todo]
            return seen
        while todo:
            ready = {u for u in todo if targets[u] <= keys.keys()}
            if ready:
                keys.update({u: content_key(u, keys) for u in ready})
            else:           # every unkeyed resource is on or above a cycle: key the cycles that reach no other
                reach = {u: reachable(u) for u in todo}
                cycles = {frozenset(c) for c in reach.values() if all(reach[v] == c for v in c)}
                for c in cycles:
                    keys.update(refine(c, keys))
                ready = set().union(*cycles)
            todo -= ready
        ref = keys.__getitem__
    return collections.Counter(text(norm(e["resource"], ref))
                               for e in bundle.get("entry", []) if e["resource"]["resourceType"] != "Provenance")


def count_uncached(base: str, rtype: str) -> int:
    """Total of rtype on the server, -1 on failure (Hapi.count: Cache-Control no-cache, because HAPI answers
    _summary=count searches from its search cache for about a minute)."""
    return Hapi(base).count(rtype)


def second_ingest_idempotent(bundle: dict, resp: dict, before: dict, after: dict) -> bool:
    """The second transaction of the same Bundle created nothing: one response entry per request entry, every one
    '200' (no '201 Created'), and the uncached count of every resource type in the Bundle is unchanged (and was
    read: a failed count, -1, never passes)."""
    st = [str((e.get("response") or {}).get("status", "")) for e in (resp or {}).get("entry", [])]
    return len(st) == len(bundle.get("entry", [])) and all(s.startswith("200") for s in st) and before == after \
        and min(before.values(), default=0) >= 0


def ingest_twice(hapi: Hapi, bundle: dict) -> tuple[bool, bool]:
    """(both transactions ok, second one idempotent)."""
    ok1, _ = hapi.transaction(bundle)
    types = sorted({e["resource"]["resourceType"] for e in bundle.get("entry", [])})
    before = {t: count_uncached(hapi.base, t) for t in types}
    ok2, resp = hapi.transaction(bundle)
    after = {t: count_uncached(hapi.base, t) for t in types}
    return ok1 and ok2, second_ingest_idempotent(bundle, resp, before, after)


def present(files: list, missing: collections.Counter, kind: str) -> list:
    """Manifest files that exist in this checkout; most of the corpus (example-data/synthData-v1/) is not in git."""
    out = [f for f in files if (ROOT / f).is_file()]
    missing[kind] += len(files) - len(out)
    return out


def stack_mismatch(mb, ps: str) -> str | None:
    """cli._profile_set_mismatch for the configured server: why it cannot validate profile set ps (it lists the KDS
    packages of another profile set, e.g. matchbox-2027 passed as --matchbox-2026), or None. Unlike the CLI, a server
    that cannot tell (no answer to the package listing) is still used for 2026: the URL was given for that profile
    set explicitly, and an unreachable server yields ERROR verdicts, which fail the gate anyway."""
    return None if mb.packages() is None else _profile_set_mismatch(mb, ps)


BAD_VERDICTS = ("FAIL", "ERROR")


def gate_failures(res: dict) -> list[str]:
    """Reasons a --gate run fails (empty list = pass). A refused matchbox fails; a run that was not asked to validate
    (no matchbox for its profile set) is judged on the other checks only (main/write_report label it)."""
    out = [f"validation refused: {res['validation_refused']}"] if res.get("validation_refused") else []
    for b, d in res["branches"].items():
        par, ing = d.get("parity", {}), d.get("ingest", {})
        checks = [(d.get("error_count", len(d.get("errors", []))), "valid inputs not converted"),
                  (d["invalid_files"] - d["invalid_rejected"], "schema-invalid inputs not rejected"),
                  (int(d["sample"] == 0), "no bundle converted"),
                  (sum(d.get("verdicts", {}).get(v, 0) for v in BAD_VERDICTS), "Python bundles with FAIL/ERROR verdict"),
                  (sum(d.get("fml_verdicts", {}).get(v, 0) for v in BAD_VERDICTS), "FML bundles with FAIL/ERROR verdict"),
                  (par.get("transform-failed", 0), "FML $transform failures"),
                  (par.get("different", 0), "FML/Python parity differences"),
                  (ing.get("fail", 0) + par.get("fml-ingest-fail", 0), "HAPI ingest failures"),
                  (ing.get("duplicated", 0) + par.get("fml-duplicated", 0), "non-idempotent second ingests")]
        out += [f"{b}: {n} {what}" for n, what in checks if n > 0]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=25)
    ap.add_argument("--branches", default="oncology,rare-disease,grz")
    ap.add_argument("--fml", action="store_true")
    ap.add_argument("--no-ingest", action="store_true")
    ap.add_argument("--profile-set", default="2027", choices=("2026", "2027"))
    ap.add_argument("--matchbox-2026", metavar="URL",
                    help="matchbox loaded with the 2026 packages; without it profile-set 2026 output is not validated")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 on conversion errors, accepted invalid inputs, FAIL/ERROR verdicts, a refused matchbox "
                         "(KDS packages of the other profile set), transform failures, parity differences, ingest or "
                         "idempotency failures, or a branch with no converted bundle")
    ap.add_argument("--manifest", type=Path, default=ROOT / "genomde2fhir" / "tests" / "corpus_manifest.json")
    ap.add_argument("--out", type=Path, help="results.json directory (default out/e2e-<profile set>)")
    ap.add_argument("--report", type=Path, help="Markdown report (default docs/E2E-REPORT-<profile set>.md)")
    a = ap.parse_args(argv)
    manifest = json.loads(a.manifest.read_text())
    # matchbox-2027 holds the 2027 ballot packages only: validating 2026 output there would check it against the
    # 2027 profiles (unversioned meta.profile) and report PASS for bundles invalid against the 2026 packages
    mb_url = MB if a.profile_set == "2027" else a.matchbox_2026
    mb, hapi = (Matchbox(mb_url) if mb_url else None), (None if a.no_ingest else Hapi(HAPI))
    refused = stack_mismatch(mb, a.profile_set) if mb else None
    if refused:
        print(f"profile set {a.profile_set}: not validated: {refused}")
        mb = None
    elif not mb:
        print(f"profile set {a.profile_set}: not validated (pass --matchbox-2026 URL, a matchbox with the 2026 packages)")
    fml = a.fml and a.profile_set == "2027" and mb is not None   # the FML maps produce the 2027 profile set only
    if a.fml and not fml:
        print("--fml ignored: " + ("the FML maps produce the 2027 profile set" if a.profile_set != "2027" else
                                   "no usable matchbox-2027"))
    down = []   # matchbox did not answer: the remaining bundles are not sent (validate_bundle stops at the first)

    def validate(b, dk, name, what=""):
        """validate_bundle (never raises); an ERROR verdict is printed and counted, never hidden."""
        if down:
            return {"verdict": "ERROR", "error": f"skipped, matchbox unreachable: {down[0]}", "resources": []}
        v = validate_bundle(b, mb, source=dk)
        if v["verdict"] == "ERROR":
            print(f"  {what}validation error {name}: {v.get('error', '')[:300]}")
            if v.get("unreachable"):
                down.append(v.get("error") or "no response")
        return v
    out_dir = a.out or ROOT / "out" / f"e2e-{a.profile_set}"
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {"generated": datetime.datetime.now().isoformat(timespec="seconds"), "version": __version__,
           "profile_set": a.profile_set, "matchbox": mb_url, "validated": bool(mb),
           **({"validation_refused": refused} if refused else {}),
           "fml": "run" if fml else "not run" if not a.fml else
                  "not applicable (the FML maps produce the 2027 profile set)" if a.profile_set != "2027" else
                  "not run (matchbox refused)",
           "hapi": None if a.no_ingest else HAPI, "branches": {}}
    for branch in a.branches.split(","):
        t0 = time.time()
        missing = collections.Counter()
        valid = present(manifest[branch]["valid"], missing, "valid")
        invalid = present(manifest[branch]["invalid"], missing, "invalid")
        if sum(missing.values()):
            print(f"{branch}: skipped {missing['valid']} valid and {missing['invalid']} invalid manifest files "
                  f"not in this checkout")
        status, resources, covered, drops, reps, warns = (collections.Counter() for _ in range(6))
        errors, bundles = [], {}
        for f in valid:
            b, r = convert(loads((ROOT / f).read_text(encoding="utf-8")), f, a.profile_set)
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
            b, r = convert(loads((ROOT / f).read_text(encoding="utf-8")), f, a.profile_set)
            rejected_ok += (r.status == "rejected")
        mapped = {p for p, row in mapping_rows(branch).items() if row.get("status") == "MAPPED"}
        sample = spread(sorted(bundles), a.sample)
        verdicts, issues = collections.Counter(), collections.defaultdict(collections.Counter)
        ingest = collections.Counter()
        parity, fml_verdicts, fml_diff = collections.Counter(), collections.Counter(), collections.Counter()
        for f in sample:
            b = bundles[f]
            dk = loads((ROOT / f).read_text(encoding="utf-8"))
            if mb:
                v = validate(b, dk, f)
                verdicts[v["verdict"]] += 1
                for rr in v["resources"]:
                    prof = (rr["profile"] or rr["type"]).split("/")[-1]
                    for i in rr["issues"]:
                        if i["class"] != "info":
                            issues[(prof, i["class"])][f"{i['expression']} :: {i['text'][:200]}"] += 1
            if hapi:
                ok, idem = ingest_twice(hapi, b)
                ingest["ok" if ok else "fail"] += 1
                if ok:
                    ingest["idempotent" if idem else "duplicated"] += 1
            if fml:
                st, fb = mb.transform(dk, MAPS[branch])   # never raises: no response -> 599 + OperationOutcome
                if st >= 300 or fb.get("resourceType") != "Bundle":
                    print(f"  transform failed {f}: HTTP {st}")
                    parity["transform-failed"] += 1
                    continue
                ca, cb = canonical(b), canonical(fb)
                parity["equal" if ca == cb else "different"] += 1
                for side, diff in (("only-python", ca - cb), ("only-fml", cb - ca)):
                    for s, n in diff.items():
                        fml_diff[f"{side}: {json.loads(s).get('resourceType')}"] += n
                fml_verdicts[validate(fb, dk, f, "FML ")["verdict"]] += 1
                if hapi:
                    okf, idemf = ingest_twice(hapi, fb)
                    parity["fml-ingest-ok" if okf else "fml-ingest-fail"] += 1
                    if okf:
                        parity["fml-idempotent" if idemf else "fml-duplicated"] += 1
        res["branches"][branch] = {
            "valid_files": len(valid), "invalid_files": len(invalid), "invalid_rejected": rejected_ok,
            "missing_files": dict(missing), "conversion": dict(status), "error_count": len(errors),
            "errors": errors[:20], "resources": dict(resources),
            "mapped_rows": len(mapped), "mapped_rows_emitted": len(mapped & set(covered)),
            "mapped_rows_never_emitted": sorted(mapped - set(covered)),
            "dropped_by_path": dict(drops.most_common(30)), "representations": dict(reps),
            "pipeline_warnings": dict(warns), "sample": len(sample), "verdicts": dict(verdicts),
            "issues": {f"{p} [{c}]": dict(cnt.most_common(15)) for (p, c), cnt in sorted(issues.items())},
            "ingest": dict(ingest), "parity": dict(parity), "fml_verdicts": dict(fml_verdicts),
            "fml_differences": dict(fml_diff.most_common(20)), "seconds": round(time.time() - t0, 1)}
        print(f"{branch}: {dict(status)} rejected {rejected_ok}/{len(invalid)} "
              f"verdicts {dict(verdicts) if mb else 'not validated'} ingest {dict(ingest)} parity {dict(parity)}")
    if a.gate:
        res["gate"] = gate_failures(res)
    (out_dir / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    write_report(res, a.report or ROOT / "docs" / f"E2E-REPORT-{a.profile_set}.md")
    if a.gate:
        print("gate: " + (("passed" if mb else "passed without validation (conversion, rejection and ingest checks only)")
                          if not res["gate"] else "FAILED\n  " + "\n  ".join(res["gate"])))
        return 1 if res["gate"] else 0
    return 0


def write_report(res, path: Path):
    L = [f"# genomde2fhir E2E report — profile set {res['profile_set']}", "",
         f"_generated {res['generated']} · genomde2fhir {res['version']} · matchbox `{res['matchbox']}` · HAPI `{res['hapi']}`_", ""]
    validated = res.get("validated", True)
    if res.get("validation_refused"):
        L += [f"**Not validated**: {res['validation_refused']} (the bundles claim unversioned profiles, so that "
              "matchbox would check them against the profiles of its own packages).", ""]
    elif not validated:
        L += [f"**Not validated**: profile set {res['profile_set']} needs a matchbox loaded with its own packages "
              "(`--matchbox-2026 URL`); matchbox-2027 would check the bundles against the 2027 ballot profiles.", ""]
    if "gate" in res:
        L += ["Gate: " + (("passed" if validated else "passed without validation (conversion, rejection and ingest "
                                                       "checks only)")
                          if not res["gate"] else "**failed** — " + "; ".join(res["gate"])), ""]
    L += [
         "Verdicts per sampled bundle: **PASS** = no error; **INCONCLUSIVE** = only errors the terminology server cannot check "
         "(German/OBO systems, ICD-O-3 2014/2019, tx timeouts), including reference failures whose target has only such "
         "errors; **DATA-QUALITY** = an invalid code copied from the input file (e.g. HGVS without reference sequence, "
         "non-existent SNOMED codes in the synthetic data); **FAIL** = at least one content error of the converter's own "
         "output; **ERROR** = validation could not run (matchbox unreachable or timed out, an HTTP error or unusable "
         "response, a profile matchbox does not know: issue class `validator-error`), never a pass. "
         "Cascades = reference/profile-match failures whose target (or a resource the target references) has a content, "
         "source or waived error of its own, counted there; a reference failure no target error explains stays content. "
         "candidate = errors of a resource against a profile it does not declare (nor derive from), raised while "
         "matchbox tried it as a "
         "reference target (reported, the reference failure is classified itself); waived = listed ballot-package "
         "defects (`genomde2fhir/validate.py` WAIVERS).", ""]
    for b, d in res["branches"].items():
        sampled = d["sample"] if validated else f"0 ({d['sample']} sampled, not validated)"
        L += [f"## {b}", "",
              "| measure | value |", "|:--|:--|",
              f"| valid inputs converted | {d['conversion'].get('converted', 0)} / {d['valid_files']} |",
              f"| manifest files not in this checkout (skipped) | "
              f"{', '.join(f'{k} {v}' for k, v in d.get('missing_files', {}).items()) or '0'} |",
              f"| invalid inputs rejected | {d['invalid_rejected']} / {d['invalid_files']} |",
              f"| MAPPED rows emitted at least once | {d['mapped_rows_emitted']} / {d['mapped_rows']} |",
              f"| sampled bundles validated | {sampled} |",
              f"| verdicts | {', '.join(f'{k} {v}' for k, v in d['verdicts'].items()) if validated else 'not validated'} |",
              f"| HAPI ingest (twice) | {', '.join(f'{k} {v}' for k, v in d['ingest'].items()) or '—'} |",
              f"| FML parity, ingest (twice) | {', '.join(f'{k} {v}' for k, v in d['parity'].items()) or res.get('fml', 'not run')} |",
              f"| FML verdicts | {', '.join(f'{k} {v}' for k, v in d.get('fml_verdicts', {}).items()) or res.get('fml', 'not run')} |",
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
    path.write_text("\n".join(L) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    sys.exit(main())
