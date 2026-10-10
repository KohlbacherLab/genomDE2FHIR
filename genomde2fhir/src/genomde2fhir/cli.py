"""genomde2fhir command line.

  genomde2fhir convert INPUT... [-o OUTDIR] [--single-bundle FILE] [--profile-set 2027|2026]
                       [--report report.json] [--strict] [--no-input-check] [-v]
                       [--validate MATCHBOX_URL] [--ingest HAPI_URL]
  genomde2fhir validate BUNDLE... --matchbox URL [--report results.json] [-v]
  genomde2fhir coverage INPUT... [-v]       (MAPPED rows: emitted / preserved-dropped / no data / gaps)

Exit codes (convert): 0 ok · 1 some inputs rejected, no input found, or genomde-dk-validator missing ·
2 conversion errors or missing paths · 3 validation verdict FAIL or ERROR (ERROR: validation could not run), ingest
failures, server unreachable, or a matchbox whose KDS packages do not match --profile-set. --report is written
whenever inputs were read (not when convert stops before: genomde-dk-validator missing, no input found).
validate: 0 ok · 1 no input · 2 unreadable or non-Bundle files · 3 FAIL/ERROR verdicts.
coverage: 0 no gaps · 1 inputs rejected/unreadable or no input · 2 converter errors or missing paths · 4 gaps remain.
stderr carries counts only; -v adds per-file lines (file names and findings may contain pseudonyms or TANs).
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

from . import __version__, io
from .bundle import BundleBuilder
from .context import PROFILE_SETS
from .convert import convert
from .data_access import mapping_rows
from .identity import case_key
from .io import classify, discover, dumps
from .report import Report, summarize

# --single-bundle / --ingest order: submission date, then type, then path (later submissions win)
TYPE_ORDER = {"initial": 0, "followup": 1, "addition": 1, "correction": 2}   # other types ('test') rank 1


def _log(msg):
    sys.stderr.write(msg + "\n")


def _order_key(name: str, dk: dict, branch: str):
    k = case_key(dk, branch)
    return str(k.submission_date or ""), TYPE_ORDER.get(str(k.submission_type or ""), 1), name


def _split(name: str) -> tuple[str, Path]:
    """'archive.zip!dir/case.json' -> ('archive.zip', Path('dir/case.json')); a plain path -> ('', Path(path))."""
    outer, _, inner = name.rpartition("!")
    return (outer, Path(inner)) if outer.lower().endswith(".zip") else ("", Path(name))


def _visible(part: str) -> str:
    """A name part without leading dots: no bundle may be a hidden file, which `validate out/` and the shell glob
    out/*.bundle.json skip ('..' and '.' become '')."""
    return part.lstrip(".")


def _default_name(name: str) -> str:
    return (_visible(_split(name)[1].stem) or "input") + ".bundle.json"


def _out_name(name: str, taken: set) -> str:
    """<stem>.bundle.json; on a clash with an earlier input of this run <parent>_<stem>, then <stem>-<n>
    (compared case-insensitively: macOS/Windows file systems). Leading dots are dropped; a parent that is '..', '.'
    or empty gives no <parent>_ candidate (the counter decides)."""
    outer, p = _split(name)
    stem = _visible(p.stem) or "input"
    parent = _visible(p.parent.name or (Path(outer).stem if outer else ""))
    cands = [stem] + ([f"{parent}_{stem}"] if parent else [])
    n = 2
    while all(c.lower() in taken for c in cands):
        cands.append(f"{stem}-{n}")
        n += 1
    pick = next(c for c in cands if c.lower() not in taken)
    taken.add(pick.lower())
    return pick + ".bundle.json"


def _convert_one(dk, name: str, a):
    """convert() for the CLI: a failure never aborts the batch. Under --strict a failure that only --strict causes
    (unknown path/canonical, structural error) rejects the file; a builder crash is an 'error' as without --strict."""
    check = not a.no_input_check
    try:
        return convert(dk, name, a.profile_set, strict=a.strict, check_input=check)
    except Exception as ex:
        err = f"{type(ex).__name__}: {ex}"
    if a.strict:
        try:
            bundle, rep = convert(dk, name, a.profile_set, strict=False, check_input=check)
        except Exception:
            rep = None
        if rep is not None:
            if rep.status == "converted":
                rep.status, rep.error = "rejected", f"--strict: {err}"
                rep.resources.clear()
            return None, rep
    return None, Report(file=name, branch=classify(dk), profile_set=a.profile_set, status="error", error=err)


def _pointer_path(pointer: str) -> str:
    """JSON pointer of a validator finding -> mapping-table path: '/case/x/0/date' -> 'case.x[].date'."""
    parts = []
    for seg in pointer.strip("/").split("/"):
        seg = seg.replace("~1", "/").replace("~0", "~")
        if seg.isdigit() and parts:
            parts[-1] += "[]"
        else:
            parts.append(seg)
    return ".".join(parts)


def _undeclared(rep: Report) -> list[tuple[str, str]]:
    """(pointer, disposition) for each 'unknown field' finding of genomde-dk-validator, judged by the report's
    dispositions: 'converted' when a builder covered or preserved that path (or a path below it), 'dropped' when it
    only dropped it, otherwise 'not converted'. Nothing is converted in a file that is not converted."""
    def at(paths, p):
        return any(x == p or x.startswith((p + ".", p + "[]")) for x in paths)
    used = rep.covered | rep.preserved
    dropped = {d[0] for d in rep.dropped}
    out = []
    for f in rep.input_findings:
        if not f.startswith("unknown field "):
            continue
        ptr = f[len("unknown field "):]
        p = _pointer_path(ptr)
        if rep.status != "converted":
            out.append((ptr, "not converted"))
        else:
            out.append((ptr, "converted" if at(used, p) else "dropped" if at(dropped, p) else "not converted"))
    return out


UNDECLARED_MSG = {"converted": "field not declared in the input schema: converted",
                  "dropped": "field not declared in the input schema: dropped (reason under dropped)",
                  "not converted": "field not declared in the input schema: not converted"}


def _reason(r: Report) -> str:
    return (r.error.splitlines()[0] if r.error else (r.input_findings or [""])[0])[:200]


def _profile_set_mismatch(mb, ps: str) -> str | None:
    """Why matchbox cannot validate output of profile set ps, or None. The bundles claim unversioned KDS profiles,
    so the server must hold the KDS packages of that profile set only (2025.x versions, shared by both stacks, are
    ignored). 2027 is validated when the server cannot tell (the documented matchbox-2027); 2026 only on a server
    that shows its 2026 packages, never against the 2027 ballot profiles."""
    pk = mb.packages()
    if pk is None:
        return None if ps == "2027" else f"cannot tell whether {mb.base} holds the 2026 KDS packages"
    years = {v[:4] for vs in pk.values() for v in vs if v[:4] in PROFILE_SETS}
    if years != {ps}:
        return f"{mb.base} holds KDS packages of {'/'.join(sorted(years)) or 'no'} profile set, not {ps}"
    return None


def cmd_convert(a) -> int:
    if not a.no_input_check and not io.input_check_available():
        _log("genomde2fhir: input validation needs genomde-dk-validator, which is not installed in the environment "
             "genomde2fhir runs in. Add it:\n" + io.validator_install_hint() +
             "\nNothing converted. Pass --no-input-check to convert without the input gate.")
        return 1
    files = discover(a.inputs)
    if not files:
        _log("genomde2fhir: no input files found (*.json, *.zip)")
        return 1
    out = Path(a.output) if a.output else None
    single = Path(a.single_bundle) if a.single_bundle else None
    if single and out and not single.is_absolute():
        single = out / single
    if out:
        out.mkdir(parents=True, exist_ok=True)
    keep = bool(single or a.validate or a.ingest)
    reports, done, taken, renamed, n_unknown, strict_undeclared = [], [], set(), [], {}, 0
    for name, load in files:
        try:
            dk = load()
        except FileNotFoundError as ex:
            reports.append(Report(file=name, profile_set=a.profile_set, status="error", error=str(ex)))
            continue
        except Exception as ex:   # malformed JSON, undecodable file, unreadable archive
            reports.append(Report(file=name, profile_set=a.profile_set, status="rejected",
                                  input_findings=[f"not JSON: {type(ex).__name__}: {ex}"]))
            continue
        bundle, rep = _convert_one(dk, name, a)
        undeclared = _undeclared(rep)
        if undeclared and a.strict and bundle is not None:
            # --strict is schema-strict (as genomde-dk-validator --strict): every undeclared field rejects the file,
            # also one the converter maps; the error says how many would have been converted
            used = sum(d == "converted" for _, d in undeclared)
            bundle, rep.status = None, "rejected"
            rep.error = (f"--strict: {len(undeclared)} field(s) not declared in the input schema (without --strict: "
                         f"{used} converted, {len(undeclared) - used} dropped or not converted)")
            rep.resources.clear()
            strict_undeclared += 1
            undeclared = _undeclared(rep)
        rep.warnings.extend((u, UNDECLARED_MSG[d]) for u, d in undeclared)
        if undeclared:
            n_unknown[name] = Counter(d for _, d in undeclared)
        reports.append(rep)
        if bundle is None:
            continue
        if out and not single:
            fn = _out_name(name, taken)
            if fn != _default_name(name):
                renamed.append((name, fn))
            (out / fn).write_text(dumps(bundle), encoding="utf-8")
            rep.output = str(out / fn)
        elif single:
            rep.output = str(single)   # written below: every converted input is merged into it
        if keep:
            done.append((_order_key(name, dk, rep.branch), name, bundle, dk if a.validate else None))
    done.sort(key=lambda d: d[0])
    if single:
        if done:
            merged = BundleBuilder()
            for _, _, b, _ in done:   # later submissions (date, type) win
                tmp = BundleBuilder()
                tmp.entries = {e["fullUrl"]: e for e in b["entry"]}
                merged.merge(tmp)
            single.parent.mkdir(parents=True, exist_ok=True)
            single.write_text(dumps(merged.bundle()), encoding="utf-8")
            bundles = [(str(single), merged.bundle(), [d[3] for d in done])]
        else:
            bundles = []
            _log(f"genomde2fhir: no input converted, {single} not written")
    else:
        bundles = [(name, b, dk) for _, name, b, dk in done]

    rc = 0
    val_results = {}
    if a.validate or a.ingest:
        from . import validate as V   # validate.py never raises for network trouble: ERROR verdict / not-ok ingest
        mb = V.Matchbox(a.validate) if a.validate else None
        hapi = V.Hapi(a.ingest) if a.ingest else None
        wrong_stack = _profile_set_mismatch(mb, a.profile_set) if mb else None
        if wrong_stack:
            _log(f"genomde2fhir: not validated: {wrong_stack}")
        down = {}   # server -> reason; after the first unanswered call the remaining bundles are skipped
        for name, b, src in bundles:
            entry = {}
            if mb:
                if wrong_stack:
                    res = {"verdict": "ERROR", "error": f"not validated: {wrong_stack}"}
                elif "matchbox" in down:
                    res = {"verdict": "ERROR", "error": f"skipped, matchbox unreachable: {down['matchbox']}"}
                else:
                    res = V.validate_bundle(b, mb, source=src)
                    if res.get("unreachable"):
                        down["matchbox"] = res.get("error") or "no response"
                entry["validation"] = res
                if res["verdict"] in ("FAIL", "ERROR"):   # ERROR also for HTTP errors / bad responses
                    rc = 3
            if hapi:
                if "hapi" in down:
                    ok, entry["ingest"] = False, f"skipped, server unreachable: {down['hapi']}"
                else:
                    ok, resp = hapi.transaction(b)
                    entry["ingest"] = "ok" if ok else dumps(resp, indent=None)[:1000]
                    if not ok and V.is_unreachable(resp):
                        down["hapi"] = V.issue_text(resp["issue"][0]) or "no response"
                if not ok:
                    rc = 3
            val_results[name] = entry
        for server, reason in down.items():
            _log(f"genomde2fhir: {server} unreachable ({reason}); see the report")
    summ = summarize(reports)
    if a.report:
        Path(a.report).write_text(dumps({"summary": summ, "files": [r.to_dict() for r in reports],
                                         "validation": val_results}), encoding="utf-8")
    _log(f"genomde2fhir {__version__} [{a.profile_set}]: {summ['files']} file(s) {summ['status']} "
         f"resources={sum(summ['resources'].values())} types={summ['submission_types']} "
         f"test={summ['test_submissions']} tan-fallback={summ['case_key_tan_fallback']}")
    failed = [r for r in reports if r.status != "converted"]
    if failed and not a.verbose:
        _log(f"  {len(failed)} file(s) not converted; reasons in --report FILE or with -v")
    if n_unknown:
        tot = sum(n_unknown.values(), Counter())
        _log(f"  {sum(tot.values())} input field(s) not declared in the schema, in {len(n_unknown)} file(s): "
             + ", ".join(f"{tot[d]} {d}" for d in UNDECLARED_MSG if tot[d])
             + (f"; {strict_undeclared} file(s) rejected for them (--strict)" if strict_undeclared else ""))
    if renamed:
        _log(f"  {len(renamed)} output name clash(es): written under another name" + ("" if a.verbose else " (-v lists them)"))
    if val_results:
        verdicts = {}
        for e in val_results.values():
            if "validation" in e:
                verdicts[e["validation"]["verdict"]] = verdicts.get(e["validation"]["verdict"], 0) + 1
        ingested = [e["ingest"] == "ok" for e in val_results.values() if "ingest" in e]
        _log("  " + " ".join(([f"validation {verdicts}"] if verdicts else []) +
                             ([f"ingest ok={sum(ingested)} failed={len(ingested) - sum(ingested)}"] if ingested else [])))
    if a.verbose:
        for r in failed:
            _log(f"  {r.status}: {r.file} :: {_reason(r)}")
        for f, n in n_unknown.items():
            _log(f"  undeclared fields: {f} :: " + ", ".join(f"{n[d]} {d}" for d in UNDECLARED_MSG if n[d]))
        for name, fn in renamed:
            _log(f"  output name: {name} -> {fn}")
        for name, e in val_results.items():
            if "validation" in e:
                _log(f"  {e['validation']['verdict']:<12} {name}")
            if e.get("ingest", "ok") != "ok":
                _log(f"  ingest failed: {name} :: {e['ingest'][:200]}")
    if any(r.status == "rejected" for r in reports):
        rc = max(rc, 1)
    if any(r.status == "error" for r in reports) and rc != 3:
        rc = 2
    return rc


def cmd_validate(a) -> int:
    from . import validate as V
    files = discover(a.bundles)
    if not files:
        _log("genomde2fhir: no input files found (*.json, *.zip)")
        return 1
    mb, results, rc, down = V.Matchbox(a.matchbox), {}, 0, None
    for name, load in files:
        try:
            b = load()
            if not (isinstance(b, dict) and b.get("resourceType") == "Bundle"):
                raise ValueError("not a FHIR Bundle")
        except Exception as ex:   # missing path, malformed JSON, not a Bundle
            results[name] = {"verdict": "ERROR", "error": f"{type(ex).__name__}: {ex}"}
            rc = max(rc, 2)
            continue
        if down:
            res = {"verdict": "ERROR", "error": f"skipped, matchbox unreachable: {down}"}
        else:
            res = V.validate_bundle(b, mb)   # never raises: ERROR verdict, 'unreachable' when matchbox did not answer
            if res.get("unreachable"):
                down = res.get("error") or "no response"
        results[name] = res
        if res["verdict"] in ("FAIL", "ERROR"):
            rc = 3
    if a.report:
        Path(a.report).write_text(dumps(results), encoding="utf-8")
    counts = {}
    for res in results.values():
        counts[res["verdict"]] = counts.get(res["verdict"], 0) + 1
    _log(f"genomde2fhir {__version__} validate: {len(results)} file(s) {counts}")
    if down:
        _log(f"  matchbox unreachable ({down})")
    if a.verbose:
        for name, res in results.items():
            _log(f"  {res['verdict']:<12} {name}" + (f" :: {res['error'][:200]}" if res.get("error") else ""))
    return rc


def _present(o, parts) -> bool:
    if not parts:
        return o not in (None, "", [], {})
    if isinstance(o, list):
        return any(_present(x, parts) for x in o)
    if isinstance(o, dict):
        k = parts[0].replace("[]", "")
        return k in o and _present(o[k], parts[1:])
    return False


def cmd_coverage(a) -> int:
    """Per branch: MAPPED rows emitted (implemented), handled (preserved/dropped with a reason), never present in
    the inputs, and present-but-unhandled (a builder gap). Inputs that are rejected, unreadable or crash a builder
    are not counted and are reported; a crash counts as a converter error only on a schema-valid input.
    Exit 2 converter errors/missing paths > 4 gaps > 1 rejected/no input > 0."""
    stats, skipped = {}, []   # skipped: (name, status, reason)
    files = discover(a.inputs)
    if not files:
        _log("genomde2fhir: no input files found (*.json, *.zip)")
        return 1
    for name, load in files:
        try:
            dk = load()
        except FileNotFoundError as ex:
            skipped.append((name, "error", str(ex)))
            continue
        except Exception as ex:
            skipped.append((name, "rejected", f"not JSON: {type(ex).__name__}: {ex}"))
            continue
        try:
            bundle, rep = convert(dk, name, a.profile_set, check_input=False)
        except Exception as ex:   # outside convert()'s own builder guard
            bundle, rep = None, Report(file=name, status="error", error=f"{type(ex).__name__}: {ex}")
        if bundle is None:
            if rep.status == "error" and io.input_check_available() and not io.validate_input(dk, name)[0]:
                # coverage runs without the input gate: a crash on a schema-invalid input is no converter defect
                skipped.append((name, "rejected", "schema-invalid; " + _reason(rep)))
            else:
                skipped.append((name, rep.status, _reason(rep)))
            continue
        s = stats.setdefault(rep.branch, {"covered": set(), "handled": set(), "present": set(), "files": 0})
        s["files"] += 1
        s["covered"] |= rep.covered
        s["handled"] |= rep.preserved | {p for p, _, _ in rep.dropped}
        for p, row in mapping_rows(rep.branch).items():
            if row.get("status") == "MAPPED" and _present(dk, [x for x in p.split(".") if x]):
                s["present"].add(p)
    gaps_total = 0
    for branch, s in sorted(stats.items()):
        mapped = {p for p, r in mapping_rows(branch).items() if r.get("status") == "MAPPED"}
        emitted = mapped & s["covered"]
        handled = (mapped & s["handled"]) - emitted
        absent = mapped - s["present"] - emitted - handled
        gaps = sorted(mapped - emitted - handled - absent)
        gaps_total += len(gaps)
        _log(f"{branch} ({s['files']} files): MAPPED {len(mapped)} | emitted {len(emitted)} | preserved/dropped {len(handled)} "
             f"| no data in inputs {len(absent)} | GAPS {len(gaps)}")
        if a.verbose:
            for p in sorted(handled):
                _log(f"   handled: {p}")
            for p in sorted(absent):
                _log(f"   no data: {p}")
        for p in gaps:
            _log(f"   GAP: {p}")
    if skipped:
        by = {}
        for _, status, _ in skipped:
            by[status] = by.get(status, 0) + 1
        _log(f"not counted: {len(skipped)} file(s) {by}" + ("" if a.verbose else " (-v lists them)"))
        if a.verbose:
            for name, status, reason in skipped:
                _log(f"   {status}: {name} :: {reason[:200]}")
    if any(st == "error" for _, st, _ in skipped):
        return 2
    if gaps_total:
        return 4
    return 1 if skipped else 0




def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="genomde2fhir", description=__doc__.split("\n")[0])
    ap.add_argument("--version", action="version", version=f"genomde2fhir {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="Datenkranz JSON -> FHIR transaction Bundle(s)",
                       epilog="exit: 0 ok, 1 inputs rejected / no input / genomde-dk-validator missing, "
                              "2 conversion errors or missing paths, 3 validation FAIL/ERROR, ingest failures, server "
                              "unreachable, or a --validate matchbox whose KDS packages do not match --profile-set")
    c.add_argument("inputs", nargs="+")
    c.add_argument("-o", "--output", help="directory for one <name>.bundle.json per input (a clashing name gets "
                                          "the parent directory or a counter; leading dots are dropped); with "
                                          "--single-bundle the directory a relative FILE is written to")
    c.add_argument("--single-bundle", metavar="FILE",
                   help="write all inputs into one transaction Bundle, applied in submission order (date, then "
                        "initial < followup/addition < correction); not written when no input converts")
    c.add_argument("--profile-set", choices=["2027", "2026"], default="2027")
    c.add_argument("--report", metavar="FILE", help="JSON report (dispositions, warnings, validation)")
    c.add_argument("--strict", action="store_true",
                   help="reject a file on unknown mapping paths/canonicals, structural errors or any input field "
                        "the schema does not declare, converted or not (the batch continues; exit 1)")
    c.add_argument("--no-input-check", action="store_true",
                   help="skip schema validation of the input (required to convert without genomde-dk-validator)")
    c.add_argument("--validate", metavar="MATCHBOX_URL",
                   help="validate the bundles with matchbox; it must hold the KDS packages of --profile-set only "
                        "(checked: 2026 output is never validated against the 2027 ballot packages)")
    c.add_argument("--ingest", metavar="HAPI_URL",
                   help="POST the bundles as transactions to a FHIR server, in submission order")
    c.add_argument("-v", "--verbose", action="store_true",
                   help="per-file lines on stderr (file names and findings may contain pseudonyms or TANs)")
    c.set_defaults(fn=cmd_convert)
    v = sub.add_parser("validate", help="validate Bundle files with matchbox",
                       epilog="exit: 0 ok, 1 no input, 2 unreadable or non-Bundle files, 3 FAIL/ERROR verdicts")
    v.add_argument("bundles", nargs="+")
    v.add_argument("--matchbox", required=True)
    v.add_argument("--report", metavar="FILE")
    v.add_argument("-v", "--verbose", action="store_true", help="one verdict line per file (file names may hold TANs)")
    v.set_defaults(fn=cmd_validate)
    g = sub.add_parser("coverage", help="MAPPED mapping-table rows not emitted for the given inputs",
                       epilog="exit: 0 no gaps, 1 inputs rejected/unreadable (not counted) or no input, "
                              "2 converter errors or missing paths, 4 gaps remain (2 > 4 > 1)")
    g.add_argument("inputs", nargs="+")
    g.add_argument("--profile-set", choices=["2027", "2026"], default="2027")
    g.add_argument("-v", "--verbose", action="store_true", help="list handled and no-data rows and skipped files too")
    g.set_defaults(fn=cmd_coverage)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
