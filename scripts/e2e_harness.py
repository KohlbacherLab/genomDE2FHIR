#!/usr/bin/env python3
"""
End-to-end conversion harness: genomDE Datenkranz (DK) JSON -> MII KDS FHIR.

Two paths per DK file, both terminating at the same checks:
  A. Python mapper   mappers/python/genomde_to_fhir.py            -> Bundle
  B. FML $transform  matchbox StructureMap (GenomDeOncologyToMii) -> Bundle
For each produced Bundle:
  (1) INGEST  -> POST as transaction to HAPI (/fhir); requires a transaction-response
                 Bundle with every entry 2xx and no error OperationOutcome.
  (2) VALIDATE-> per resource, per declared meta.profile, matchbox $validate (KDS/IG).

A per-path verdict (PASS / FAIL / INCONCLUSIVE) is computed and printed.

Outputs: out/e2e/{py,fml}/<case>.json + out/e2e/results.json (full diagnostics) + docs/E2E-REPORT.md

Servers (override via env):
  HAPI = http://localhost:8080/fhir            (JPA store; no MII IGs => ingest != KDS validation)
  MB   = http://localhost:8090/matchboxv3/fhir (MII packages loaded => $transform + $validate)

Only the oncology branch has mappers today. RD / GRZ / legacy-schema-variant files are
classified and reported as unsupported (counted, not run). See docs/OPEN-ISSUES.md.

Usage:
  python3 scripts/e2e_harness.py                     # all examples/, both paths, ingest+validate
  python3 scripts/e2e_harness.py --roots examples example-data
  python3 scripts/e2e_harness.py --limit 5 --paths A # smoke, Python only
  python3 scripts/e2e_harness.py --no-ingest         # transform+validate only
"""
import argparse, collections, datetime, glob, json, os, subprocess, sys
import urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HAPI = os.environ.get("HAPI", "http://localhost:8080/fhir")
MB   = os.environ.get("MB",   "http://localhost:8090/matchboxv3/fhir")
SM   = "https://www.medizininformatik-initiative.de/fhir/StructureMap/GenomDeOncologyToMii"
PY   = os.environ.get("PYTHON", "python3")     # interpreter that has fhir.resources installed
SUBPROC_TIMEOUT = int(os.environ.get("SUBPROC_TIMEOUT", "120"))
HTTP_TIMEOUT    = int(os.environ.get("HTTP_TIMEOUT", "90"))
OUT  = ROOT / "out" / "e2e"

# $validate diagnostics that reflect a missing terminology server / snapshot engine on THIS
# matchbox, not a mapper content bug. Heuristic ONLY — every issue (env or content) is kept in
# results.json with its classifier so a human (or a tx.fhir.org-backed rerun) can re-judge.
# ponytail: substring heuristic; authoritative env/content split needs a tx-server-backed validator.
ENV_MARKERS = [
    "unable to validate code", "unable to expand", "cannot validate code",
    "no terminology", "terminology service", "tx-server", "test-server",
    "unknown codesystem", "not been loaded", "unable to check", "no valueset",
    "error expanding valueset", "unable to find valueset",
    "a definition for codesystem", "the code cannot be validated",
    "could not be found, so the code",
    "could not validate profile", "engine configured, but validation for profile",
]


def is_env(diag: str) -> bool:
    d = (diag or "").lower()
    return any(m in d for m in ENV_MARKERS)


def is_oo(body) -> bool:
    return isinstance(body, dict) and body.get("resourceType") == "OperationOutcome"


def classify(dk: dict) -> str:
    """Branch of a Datenkranz payload. Only 'oncology' has mappers today."""
    if isinstance(dk, dict) and "donors" in dk and "submission" in dk:
        return "grz"
    if "metadata" in dk and "metaData" not in dk:      # legacy lowercase schema variant
        return "legacy-variant"
    case = dk.get("case") or {}
    if "diagnosisOd" in case:
        return "oncology"
    if "diagnosisRd" in case:
        return "rare-disease"
    return "unknown"


def get(url: str, timeout: int = 15):
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.status, json.load(r)
    except Exception as e:
        return None, {"_error": f"{type(e).__name__}: {e}"}


def post(url: str, obj, timeout: int = HTTP_TIMEOUT):
    """POST FHIR JSON; return (status_or_None, parsed_body_dict). None status = transport failure."""
    req = urllib.request.Request(
        url, data=json.dumps(obj).encode(), method="POST",
        headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {"resourceType": "OperationOutcome",
                            "_raw": e.read()[:800].decode("utf8", "replace")}
    except Exception as e:
        return None, {"_error": f"{type(e).__name__}: {e}"}


def first_error(oo: dict) -> str:
    if not isinstance(oo, dict):
        return str(oo)[:300]
    if "_error" in oo:
        return oo["_error"]
    if "_raw" in oo:
        return oo["_raw"][:300]
    for i in oo.get("issue", []):
        if i.get("severity") in ("error", "fatal"):
            return (i.get("diagnostics") or i.get("details", {}).get("text") or "")[:400]
    return ""


# ---- preflight -------------------------------------------------------------

def preflight(need_ingest: bool, need_validate: bool, need_b: bool):
    """Abort early on a broken environment so we never publish a green report from a down server."""
    problems = []
    if need_ingest:
        code, _ = get(f"{HAPI}/metadata")
        if code != 200:
            problems.append(f"HAPI {HAPI} not reachable (metadata={code})")
    if need_validate or need_b:
        code, _ = get(f"{MB}/metadata")
        if code != 200:
            problems.append(f"matchbox {MB} not reachable (metadata={code})")
    if need_b:
        code, body = get(f"{MB}/StructureMap?url={urllib.parse.quote(SM)}&_summary=count")
        total = body.get("total") if isinstance(body, dict) else None
        if code != 200 or not total:
            problems.append(f"StructureMap {SM} not loaded on matchbox (total={total})")
    if problems:
        sys.stderr.write("PREFLIGHT FAILED:\n  " + "\n  ".join(problems) + "\n")
        sys.exit(2)
    sys.stderr.write("preflight ok\n")


# ---- paths -----------------------------------------------------------------

def path_a(f: Path):
    outp = OUT / "py" / (f.stem + ".json")
    outp.parent.mkdir(parents=True, exist_ok=True)
    try:
        p = subprocess.run([PY, str(ROOT / "mappers/python/genomde_to_fhir.py"), str(f),
                            "-o", str(outp)], capture_output=True, text=True, timeout=SUBPROC_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "err": f"mapper timeout > {SUBPROC_TIMEOUT}s", "kind": "timeout"}
    if p.returncode != 0:
        return {"ok": False, "err": (p.stderr.strip() or "nonzero exit")[-400:], "kind": "emit"}
    try:
        bundle = json.load(open(outp))
    except Exception as e:
        return {"ok": False, "err": f"unreadable output: {e}", "kind": "emit"}
    return {"ok": True, "bundle": bundle, "n": len(bundle.get("entry", []))}


def path_b(f: Path):
    dk = json.load(open(f))
    code, body = post(f"{MB}/StructureMap/$transform?source={urllib.parse.quote(SM, safe=':/')}", dk)
    if code == 200 and isinstance(body, dict) and body.get("resourceType") == "Bundle":
        outp = OUT / "fml" / (f.stem + ".json")
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(body, indent=2, ensure_ascii=False))
        return {"ok": True, "bundle": body, "n": len(body.get("entry", []))}
    rt = body.get("resourceType") if isinstance(body, dict) else None
    return {"ok": False, "code": code, "err": first_error(body) or f"resourceType={rt}",
            "kind": "transport" if code is None else "transform"}


# ---- checks shared by both paths ------------------------------------------

def structural(bundle: dict):
    """Local transaction-bundle sanity (runs even with --no-ingest)."""
    issues = []
    if bundle.get("resourceType") != "Bundle":
        return ["not a Bundle"]
    entries = bundle.get("entry") or []
    if not entries:
        issues.append("empty bundle (0 entries)")
    if bundle.get("type") != "transaction":
        issues.append(f"type={bundle.get('type')!r} (expected transaction)")
    urls = [e.get("fullUrl") for e in entries]
    if any(not u for u in urls):
        issues.append("entry without fullUrl")
    if len(set(u for u in urls if u)) != len([u for u in urls if u]):
        issues.append("duplicate fullUrl")
    if any(not (e.get("request") or {}).get("method") for e in entries):
        issues.append("entry without request.method")
    if any(not e.get("resource") for e in entries):
        issues.append("entry without resource")
    return issues


def ingest(bundle: dict):
    struct = structural(bundle)
    if struct:
        return {"ok": False, "code": None, "note": "; ".join(struct), "kind": "structural"}
    code, body = post(HAPI, bundle)
    if code is None:
        return {"ok": False, "code": None, "note": first_error(body), "kind": "transport"}
    if code not in (200, 201) or not isinstance(body, dict) or body.get("resourceType") != "Bundle" \
            or not str(body.get("type", "")).endswith("response"):
        return {"ok": False, "code": code, "note": first_error(body), "kind": "ingest"}
    resp = body.get("entry", [])
    ok2xx = sum(1 for e in resp if str(e.get("response", {}).get("status", "")).startswith("2"))
    bad = [e.get("response", {}).get("status") for e in resp
           if not str(e.get("response", {}).get("status", "")).startswith("2")]
    oo_err = any(is_oo(e.get("response", {}).get("outcome")) and first_error(e["response"]["outcome"])
                 for e in resp)
    ok = ok2xx == len(resp) and not bad and not oo_err
    return {"ok": ok, "code": code, "created": ok2xx, "n": len(resp),
            "note": (f"non-2xx entries: {bad}" if bad else "entry OperationOutcome error" if oo_err else ""),
            "kind": "ingest" if not ok else None}


def validate(bundle: dict, file: str, path: str, issue_log: list):
    """Per-resource, per-declared-profile $validate. Buckets: clean/env/content/valerror/noprofile."""
    out = {}
    for e in bundle.get("entry", []):
        r = e.get("resource", {})
        rtype = r.get("resourceType")
        profiles = r.get("meta", {}).get("profile") or []
        if not profiles:
            tag = f"(no profile: {rtype})"
            out.setdefault(tag, _rec())["noprofile"] += 1
            issue_log.append({"file": file, "path": path, "resourceType": rtype,
                              "profile": None, "bucket": "noprofile", "severity": "error",
                              "diagnostics": "resource declares no meta.profile — cannot KDS-validate"})
            continue
        for prof in profiles:
            tag = prof.split("/")[-1]
            rec = out.setdefault(tag, _rec())
            code, oo = post(f"{MB}/$validate?profile=" + urllib.parse.quote(prof), r)
            if code != 200 or not is_oo(oo):
                rec["valerror"] += 1
                issue_log.append({"file": file, "path": path, "resourceType": rtype, "profile": prof,
                                  "bucket": "valerror", "severity": "error",
                                  "diagnostics": first_error(oo) or f"$validate transport code={code}"})
                continue
            errs = [i for i in oo.get("issue", []) if i.get("severity") in ("error", "fatal")]
            content = [i for i in errs if not is_env(i.get("diagnostics", ""))]
            for i in errs:
                bucket = "content" if i in content else "env"
                issue_log.append({"file": file, "path": path, "resourceType": rtype, "profile": prof,
                                  "bucket": bucket, "severity": i.get("severity"),
                                  "expression": i.get("expression"),
                                  "diagnostics": i.get("diagnostics", "")})
            if content:
                rec["content"] += 1
                for i in content:
                    d = (i.get("diagnostics") or "")[:180]
                    if d and d not in rec["samples"]["content"]:
                        rec["samples"]["content"].append(d)
            elif errs:
                rec["env"] += 1
                for i in errs:
                    d = (i.get("diagnostics") or "")[:180]
                    if d and d not in rec["samples"]["env"]:
                        rec["samples"]["env"].append(d)
            else:
                rec["clean"] += 1
    return out


def _rec():
    return {"clean": 0, "env": 0, "content": 0, "valerror": 0, "noprofile": 0,
            "samples": {"content": [], "env": []}}


def merge_val(agg: dict, one: dict):
    for tag, rec in one.items():
        a = agg.setdefault(tag, _rec())
        for k in ("clean", "env", "content", "valerror", "noprofile"):
            a[k] += rec[k]
        for kind in ("content", "env"):
            for s in rec["samples"][kind]:
                if s not in a["samples"][kind]:
                    a["samples"][kind].append(s)


def val_totals(val: dict):
    t = {"clean": 0, "env": 0, "content": 0, "valerror": 0, "noprofile": 0}
    for r in val.values():
        for k in t:
            t[k] += r[k]
    return t


# ---- driver ----------------------------------------------------------------

def run(roots, limit, do_paths, do_ingest, do_validate):
    preflight(do_ingest, do_validate, "B" in do_paths)
    files = sorted({Path(p) for root in roots
                    for p in glob.glob(str(ROOT / root / "**" / "*.json"), recursive=True)})
    branches = collections.Counter()
    supported = []
    for f in files:
        try:
            dk = json.load(open(f))
        except Exception:
            branches["unreadable"] += 1
            continue
        b = classify(dk)
        branches[b] += 1
        if b == "oncology":
            supported.append(f)
    eligible = len(supported)
    if limit:
        supported = supported[:limit]

    res = {"env": {"HAPI": HAPI, "MB": MB, "SM": SM,
                   "generated": datetime.datetime.now().isoformat(timespec="seconds"),
                   "roots": roots, "paths": do_paths, "ingest": do_ingest, "validate": do_validate,
                   "limit": limit},
           "discovery": {"total_files": len(files), "branches": dict(branches),
                         "eligible_oncology": eligible, "run": len(supported)},
           "cases": [], "agg": {}, "issues": []}
    A = res["agg"]["A"] = _pathagg()
    B = res["agg"]["B"] = _pathagg()
    IL = res["issues"]

    for i, f in enumerate(supported, 1):
        rel = str(f.relative_to(ROOT))
        case = {"file": rel, "name": f.stem}
        sys.stderr.write(f"[{i}/{len(supported)}] {f.name}\n")
        for pk, agg in (("A", A), ("B", B)):
            if pk not in do_paths:
                continue
            r = path_a(f) if pk == "A" else path_b(f)
            c = case[pk] = {"produced": r["ok"], "n": r.get("n"), "err": r.get("err")}
            agg["produce_ok" if r["ok"] else "produce_fail"] += 1
            if not r["ok"]:
                continue
            bundle = r["bundle"]
            case[pk]["types"] = _types(bundle)
            if do_ingest:
                ing = ingest(bundle)
                c["ingest"] = ing
                agg["ingest_ok" if ing["ok"] else "ingest_fail"] += 1
            if do_validate:
                v = validate(bundle, rel, pk, IL)
                merge_val(agg["val"], v)
                c["val"] = {t: {k: rr[k] for k in ("clean", "env", "content", "valerror", "noprofile")}
                            for t, rr in v.items()}
        res["cases"].append(case)

    # verdicts + parity
    for pk in do_paths:
        res["agg"][pk]["verdict"] = _verdict(res["agg"][pk], do_ingest, do_validate)
    res["parity"] = _parity(res["cases"], do_paths)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    write_report(res)
    return res


def _pathagg():
    return {"produce_ok": 0, "produce_fail": 0, "ingest_ok": 0, "ingest_fail": 0, "val": {}}


def _types(bundle):
    c = collections.Counter(e.get("resource", {}).get("resourceType") for e in bundle.get("entry", []))
    return dict(c)


def _verdict(agg, do_ingest, do_validate):
    t = val_totals(agg["val"])
    if agg["produce_fail"] or (do_ingest and agg["ingest_fail"]) or (do_validate and t["content"]):
        return "FAIL"
    if do_validate and (t["valerror"] or t["env"] or t["noprofile"]):
        return "INCONCLUSIVE"   # couldn't fully validate (offline tx / snapshot / missing profile)
    return "PASS"


def _parity(cases, do_paths):
    if not ("A" in do_paths and "B" in do_paths):
        return None
    mismatch = 0
    diffs = []
    for c in cases:
        ta, tb = c.get("A", {}).get("types"), c.get("B", {}).get("types")
        if ta is None or tb is None:
            continue
        keys = set(ta) | set(tb)
        d = {k: [ta.get(k, 0), tb.get(k, 0)] for k in sorted(keys) if ta.get(k, 0) != tb.get(k, 0)}
        if d:
            mismatch += 1
            if len(diffs) < 5:
                diffs.append({"case": c["name"], "diff_A_vs_B": d})
    return {"cases_with_type_mismatch": mismatch, "samples": diffs}


# ---- report ----------------------------------------------------------------

def _val_table(val: dict) -> str:
    if not val:
        return "_no resources validated_\n"
    lines = ["| profile | clean | env-only | content-err | val-err | no-profile |",
             "|---|---|---|---|---|---|"]
    for tag, r in sorted(val.items()):
        lines.append(f"| {tag} | {r['clean']} | {r['env']} | {r['content']} | {r['valerror']} | {r['noprofile']} |")
    return "\n".join(lines) + "\n"


def write_report(res: dict):
    e, d = res["env"], res["discovery"]
    L = []
    L.append("# genomDE → MII KDS — end-to-end conversion harness report\n")
    L.append(f"_generated {e['generated']} · roots={e['roots']} · paths={e['paths']} · "
             f"ingest={e['ingest']} · validate={e['validate']} · limit={e['limit'] or 'none'}_\n")
    # verdict banner
    vs = " · ".join(f"**Path {pk}: {res['agg'][pk].get('verdict','—')}**" for pk in e["paths"])
    L.append(f"\n> {vs}\n")
    L.append("\n## Pipeline\n```\n"
             "DK JSON ─┬─ (A) Python  genomde_to_fhir.py     ─┐\n"
             "         └─ (B) FML     matchbox $transform     ─┴─► Bundle ─► [ingest → HAPI] + [KDS $validate → matchbox]\n```\n")
    L.append(f"- **HAPI** `{e['HAPI']}` — JPA store (no MII IGs → ingest = transaction/referential check, *not* KDS validation)\n"
             f"- **matchbox** `{e['MB']}` — `$transform` + KDS `$validate` (MII packages loaded)\n")
    L.append("\n## Discovery\n")
    lim = f" (--limit {e['limit']})" if e["limit"] else ""
    L.append(f"{d['total_files']} JSON across {e['roots']}. Only the **oncology** branch has mappers → "
             f"{d['eligible_oncology']} eligible, {d['run']} run this pass{lim}.\n\n")
    L.append("| branch | files | has mapper? |\n|---|---|---|\n")
    order = ["oncology", "rare-disease", "legacy-variant", "grz", "unknown", "unreadable"]
    for k in order + [x for x in d["branches"] if x not in order]:
        if k in d["branches"]:
            L.append(f"| {k} | {d['branches'][k]} | {'yes' if k=='oncology' else 'no'} |\n")

    for pk, name in (("A", "Python mapper"), ("B", "FML `$transform` (matchbox)")):
        if pk not in e["paths"]:
            L.append(f"\n## Path {pk} — {name}\n_SKIPPED (paths={e['paths']})_\n")
            continue
        agg = res["agg"][pk]
        verb = "emit" if pk == "A" else "transform"
        L.append(f"\n## Path {pk} — {name} — verdict **{agg.get('verdict','—')}**\n")
        L.append(f"- {verb} Bundle: **{agg['produce_ok']} ok / {agg['produce_fail']} fail**\n")
        if e["ingest"]:
            L.append(f"- ingest → HAPI (transaction): **{agg['ingest_ok']} ok / {agg['ingest_fail']} fail**\n")
        if e["validate"]:
            L.append("\n### KDS `$validate` (per resource × declared profile)\n")
            L.append(_val_table(agg["val"]))

    if res.get("parity"):
        p = res["parity"]
        L.append(f"\n## A↔B parity\nCases where Path A and Path B emit different resource-type counts: "
                 f"**{p['cases_with_type_mismatch']} / {d['run']}**.\n")
        for s in p["samples"]:
            L.append(f"- `{s['case']}`: {s['diff_A_vs_B']}\n")

    # content-error samples (from full issue log, dedup)
    seen, csamp = set(), []
    for it in res["issues"]:
        if it["bucket"] != "content":
            continue
        key = (it["path"], it["profile"], it["diagnostics"][:80])
        if key in seen:
            continue
        seen.add(key)
        csamp.append(f"- `{it['path']}` **{(it['profile'] or '').split('/')[-1]}**: {it['diagnostics'][:180]}")
    if csamp:
        L.append("\n## Content-error samples (tx-server/env noise excluded; full list in results.json)\n")
        L.append("\n".join(csamp[:30]) + "\n")

    # failures, deduped by (path, kind, note)
    fc = collections.Counter()
    for c in res["cases"]:
        for pk in ("A", "B"):
            cc = c.get(pk)
            if not cc:
                continue
            if cc.get("produced") is False:
                fc[(pk, "produce", (cc.get("err") or "")[:90])] += 1
            ing = cc.get("ingest")
            if isinstance(ing, dict) and not ing.get("ok"):
                fc[(pk, f"ingest/{ing.get('kind')}", (ing.get("note") or "")[:90])] += 1
    if fc:
        L.append("\n## Failures / gaps (deduped)\n| path | kind | reason | count |\n|---|---|---|---|\n")
        for (pk, kind, note), n in fc.most_common():
            L.append(f"| {pk} | {kind} | {note} | {n} |\n")

    L.append("\n## Notes\n")
    L.append("- **Verdict:** FAIL = produce/ingest/content-conformance error; INCONCLUSIVE = only "
             "env/tx-server, missing-profile, or $validate transport issues (couldn't fully validate); "
             "PASS = all clean. This matchbox has no terminology server, so KDS-conformant mappers land "
             "at INCONCLUSIVE here and PASS against a tx.fhir.org-backed validator.\n")
    L.append("- **env-only** = the only $validate errors are terminology/snapshot limits (ICD-10-GM/"
             "ICD-O-3/ATC/SNOMED can't expand offline). Every issue (env + content) is kept with its "
             "classifier in `out/e2e/results.json`.\n")
    L.append("- Path B ingest failing *\"not a transaction bundle\"* is the known FML gap (entries lack "
             "`fullUrl`+`request`); `$validate` still runs on its resources. See docs/OPEN-ISSUES.md.\n")
    L.append("- **HAPI pollution:** repeated runs POST new resources each time (metrics are unaffected — "
             "they read the transaction *response*, not DB counts). For a clean store, `$expunge` or point "
             "`HAPI=` at a throwaway partition. ponytail: not auto-purged.\n")
    L.append("- RD/GRZ/legacy-variant branches have no mapper yet → classified, not run.\n")
    (ROOT / "docs" / "E2E-REPORT.md").write_text("".join(L))
    sys.stderr.write("\nwrote docs/E2E-REPORT.md + out/e2e/results.json\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", default=["examples"])
    ap.add_argument("--limit", type=int, default=0, help="cap oncology files run (0=all)")
    ap.add_argument("--paths", default="AB", help="which paths: A, B, or AB")
    ap.add_argument("--no-ingest", action="store_true")
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args()
    res = run(a.roots, a.limit, a.paths.upper(), not a.no_ingest, not a.no_validate)
    print(f"\n=== e2e: {res['discovery']['run']} oncology files "
          f"(of {res['discovery']['eligible_oncology']} eligible) ===")
    for pk in a.paths.upper():
        agg = res["agg"][pk]
        t = val_totals(agg["val"])
        print(f"Path {pk}: {agg.get('verdict')}  produce {agg['produce_ok']}/{agg['produce_ok']+agg['produce_fail']}"
              f"  ingest {agg['ingest_ok']}/{agg['ingest_ok']+agg['ingest_fail']}"
              f"  validate[clean {t['clean']} / env {t['env']} / content {t['content']} / valerr {t['valerror']}]")
    print("report: docs/E2E-REPORT.md")


if __name__ == "__main__":
    main()
