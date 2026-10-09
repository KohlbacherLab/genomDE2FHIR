"""Convert one Datenkranz document (or file) into a transaction Bundle plus a disposition report."""
import traceback

from . import __version__
from .builders import pipeline
from .bundle import dangling_references, structural_errors
from .context import Ctx
from .identity import case_key
from .io import BRANCHES, classify, validate_input
from .report import Report

PROVENANCE_AGENT = "https://github.com/KohlbacherLab/genomDE2FHIR"


def convert(dk: dict, name: str = "<data>", profile_set: str = "2027", strict: bool = False,
            check_input: bool = True, provenance: bool = True):
    """Returns (bundle | None, Report). Rejected inputs (schema-invalid, unknown branch) give no bundle.
    In strict mode builder exceptions, unknown mapping paths, unknown canonicals and structural errors raise."""
    report = Report(file=name, profile_set=profile_set)
    branch = classify(dk)
    report.branch = branch
    if branch not in BRANCHES:
        report.status = "rejected"
        report.input_findings = [f"unsupported document type: {branch}"]
        return None, report
    if check_input:
        ok, findings = validate_input(dk, name)
        report.input_findings = findings
        if not ok:
            report.status = "rejected"
            return None, report
    ctx = Ctx(dk, branch, case_key(dk, branch), profile_set, report, strict)
    try:
        for step, fn in pipeline(branch):
            if fn is None:
                ctx.warn("(pipeline)", f"builder not implemented: {step}")
                continue
            fn(ctx)
        for fn in ctx.finishers:
            fn(ctx)
        _link_episode(ctx)
        if provenance:
            _provenance(ctx)
    except Exception as ex:
        if strict:
            raise
        report.status = "error"
        report.error = f"{type(ex).__name__}: {ex}\n{traceback.format_exc(limit=4)}"
        return None, report
    bundle = ctx.bundle.bundle()
    problems = [("(structure)", e) for e in structural_errors(bundle)] + \
               [("(reference)", e) for e in dangling_references(bundle)]
    if problems and strict:
        raise ValueError("; ".join(m for _, m in problems[:5]))
    report.warnings.extend(problems)
    report.status = "converted"
    return bundle, report


def convert_file(path, **kw):
    import json
    from pathlib import Path
    return convert(json.loads(Path(path).read_text(encoding="utf-8")), str(path), **kw)


def _link_episode(ctx):
    """Append references collected in bag['episode_supporting'] by builders that ran after the Behandlungsepisode."""
    ep = ctx.resource(ctx.refs.get("episode"))
    if ep is None:
        return
    have = {si.get("reference") for si in ep.get("supportingInfo", [])}
    for r in ctx.bag.get("episode_supporting", []):
        if r.get("reference") not in have:
            ep.setdefault("supportingInfo", []).append(dict(r))
            have.add(r.get("reference"))


def _provenance(ctx):
    """One Provenance per bundle: converter version, profile set, submission identity."""
    targets = [{"reference": e["fullUrl"]} for e in ctx.bundle.entries.values()]
    if not targets:
        return
    k = ctx.key
    from .systems import SID_GDC, SID_KDK, SID_LE
    sub = (ctx.dk.get("metaData") or {}).get("submission") or ctx.dk.get("submission") or {}
    routing = []   # BfArM routing ids have no KDS element; kept as Provenance agents (sender, data nodes)
    for path_key, system, role, label in (("submitterId", SID_LE, "author", "Leistungserbringer"),
                                          ("clinicalDataNodeId", SID_KDK, "custodian", "Klinischer Datenknoten"),
                                          ("genomicDataCenterId", SID_GDC, "custodian", "Genomrechenzentrum")):
        if sub.get(path_key):
            routing.append({"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type", "code": role}]},
                            "who": {"display": label, "identifier": {"system": system, "value": sub[path_key]}}})
            prefix = "metaData.submission." if ctx.branch != "grz" else "submission."
            if path_key != "submitterId" and ctx.branch != "grz" and (prefix + path_key) in ctx._rows:
                ctx.preserve(prefix + path_key, "provenance-agent")
    prov = ctx.new("Provenance", "conversion")
    prov.update(
        target=targets,
        recorded=(k.submission_date or "1900-01-01") + "T00:00:00Z" if len(k.submission_date or "") == 10 else "1900-01-01T00:00:00Z",
        activity={"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-DataOperation", "code": "CREATE"}],
                  "text": f"genomde2fhir {__version__} profile-set {ctx.ps} submission {k.submission_type or '?'}"},
        agent=[{"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                                     "code": "assembler"}]},
                "who": {"display": f"genomde2fhir {__version__}", "identifier": {"system": PROVENANCE_AGENT, "value": __version__}}}] + routing,
    )
    ctx.add(prov)
