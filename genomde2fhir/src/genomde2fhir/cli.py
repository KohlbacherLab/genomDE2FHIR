"""genomde2fhir command line.

  genomde2fhir convert INPUT... [-o OUTDIR] [--single-bundle FILE] [--profile-set 2027|2026]
                       [--report report.json] [--strict] [--no-input-check]
                       [--validate MATCHBOX_URL] [--ingest HAPI_URL]
  genomde2fhir validate BUNDLE... --matchbox URL [--report results.json]
  genomde2fhir coverage INPUT... [-v]       (MAPPED rows: emitted / preserved-dropped / no data / gaps)

Exit codes: 0 ok · 1 some inputs rejected · 2 conversion errors · 3 validation/ingest failures.
"""
import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .bundle import BundleBuilder
from .convert import convert
from .data_access import mapping_rows
from .io import discover
from .report import summarize


def _log(msg):
    sys.stderr.write(msg + "\n")


def cmd_convert(a) -> int:
    files = discover(a.inputs)
    out = Path(a.output) if a.output else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    merged = BundleBuilder() if a.single_bundle else None
    reports, bundles = [], []
    for name, load in files:
        try:
            dk = load()
        except Exception as ex:
            from .report import Report
            r = Report(file=name, status="rejected", input_findings=[f"not JSON: {ex}"])
            reports.append(r)
            continue
        bundle, rep = convert(dk, name, a.profile_set, strict=a.strict, check_input=not a.no_input_check)
        reports.append(rep)
        if bundle is None:
            continue
        if merged is not None:
            tmp = BundleBuilder()
            tmp.entries = {e["fullUrl"]: e for e in bundle["entry"]}
            merged.merge(tmp)
        else:
            bundles.append((name, bundle))
            if out:
                (out / (Path(name.split("!")[-1]).stem + ".bundle.json")).write_text(
                    json.dumps(bundle, ensure_ascii=False, indent=1))
    if merged is not None:
        bundles = [(a.single_bundle, merged.bundle())]
        Path(a.single_bundle).write_text(json.dumps(bundles[0][1], ensure_ascii=False, indent=1))

    rc = 0
    val_results = {}
    if a.validate or a.ingest:
        from .validate import Hapi, Matchbox, validate_bundle
        mb = Matchbox(a.validate) if a.validate else None
        hapi = Hapi(a.ingest) if a.ingest else None
        for name, b in bundles:
            entry = {}
            if mb:
                entry["validation"] = validate_bundle(b, mb)
                if entry["validation"]["verdict"] == "FAIL":
                    rc = 3
            if hapi:
                ok, resp = hapi.transaction(b)
                entry["ingest"] = "ok" if ok else json.dumps(resp)[:1000]
                if not ok:
                    rc = 3
            val_results[name] = entry
    summ = summarize(reports)
    if a.report:
        Path(a.report).write_text(json.dumps({"summary": summ, "files": [r.to_dict() for r in reports],
                                              "validation": val_results}, ensure_ascii=False, indent=1))
    _log(f"genomde2fhir {__version__} [{a.profile_set}]: {summ['files']} file(s) {summ['status']} "
         f"resources={sum(summ['resources'].values())}")
    for r in reports:
        if r.status != "converted":
            first = (r.input_findings or [r.error.splitlines()[0] if r.error else ""])[0]
            _log(f"  {r.status}: {r.file} :: {first[:200]}")
    if any(r.status == "error" for r in reports):
        rc = max(rc, 2) if rc != 3 else rc
    elif any(r.status == "rejected" for r in reports) and rc == 0:
        rc = 1
    return rc


def cmd_validate(a) -> int:
    from .validate import Matchbox, validate_bundle
    mb, results, rc = Matchbox(a.matchbox), {}, 0
    for name, load in discover(a.bundles):
        res = validate_bundle(load(), mb)
        results[name] = res
        _log(f"{res['verdict']:<12} {name}")
        rc = 3 if res["verdict"] == "FAIL" else rc
    if a.report:
        Path(a.report).write_text(json.dumps(results, ensure_ascii=False, indent=1))
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
    the inputs, and present-but-unhandled (a builder gap). Exit 4 if any gap remains."""
    stats = {}
    for name, load in discover(a.inputs):
        dk = load()
        bundle, rep = convert(dk, name, a.profile_set, check_input=False)
        if bundle is None:
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
    return 0 if gaps_total == 0 else 4


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="genomde2fhir", description=__doc__.split("\n")[0])
    ap.add_argument("--version", action="version", version=f"genomde2fhir {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="Datenkranz JSON -> FHIR transaction Bundle(s)")
    c.add_argument("inputs", nargs="+")
    c.add_argument("-o", "--output", help="directory for one <name>.bundle.json per input")
    c.add_argument("--single-bundle", metavar="FILE", help="write all inputs into one transaction Bundle")
    c.add_argument("--profile-set", choices=["2027", "2026"], default="2027")
    c.add_argument("--report", metavar="FILE", help="JSON report (dispositions, warnings, validation)")
    c.add_argument("--strict", action="store_true", help="fail on unknown paths/canonicals and structural errors")
    c.add_argument("--no-input-check", action="store_true", help="skip schema validation of the input")
    c.add_argument("--validate", metavar="MATCHBOX_URL", help="validate the bundles with matchbox")
    c.add_argument("--ingest", metavar="HAPI_URL", help="POST the bundles as transactions to a FHIR server")
    c.set_defaults(fn=cmd_convert)
    v = sub.add_parser("validate", help="validate Bundle files with matchbox")
    v.add_argument("bundles", nargs="+")
    v.add_argument("--matchbox", required=True)
    v.add_argument("--report", metavar="FILE")
    v.set_defaults(fn=cmd_validate)
    g = sub.add_parser("coverage", help="MAPPED mapping-table rows not emitted for the given inputs")
    g.add_argument("inputs", nargs="+")
    g.add_argument("--profile-set", choices=["2027", "2026"], default="2027")
    g.add_argument("-v", "--verbose", action="store_true", help="list handled and no-data rows too")
    g.set_defaults(fn=cmd_coverage)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
