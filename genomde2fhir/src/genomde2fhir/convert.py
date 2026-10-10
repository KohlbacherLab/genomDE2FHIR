"""Convert one Datenkranz document (or file) into a transaction Bundle plus a disposition report."""
import traceback

from . import __version__
from .builders import pipeline
from .bundle import dangling_references, structural_errors
from .context import Ctx
from .identity import case_key
from .io import BRANCHES, classify, loads, validate_input
from .report import Report

PROVENANCE_AGENT = "https://github.com/KohlbacherLab/genomDE2FHIR"
PROV_PARTICIPANT = "http://terminology.hl7.org/CodeSystem/provenance-participant-type"
DATA_OPERATION = "http://terminology.hl7.org/CodeSystem/v3-DataOperation"
# submission type -> v3-DataOperation (both streams): a correction rewrites, a follow-up / addition extends the case;
# 'test' has no operation (the HTEST security label marks it)
DATA_OP = {"initial": "CREATE", "correction": "UPDATE", "followup": "APPEND", "addition": "APPEND"}
HTEST = {"system": "http://terminology.hl7.org/CodeSystem/v3-ActReason", "code": "HTEST", "display": "test health data"}


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
    key = case_key(dk, branch)
    report.submission_type, report.submission_date, report.test = key.submission_type, key.submission_date, key.test
    report.case_key_fallback = not key.case_id_is_local
    ctx = Ctx(dk, branch, key, profile_set, report, strict)
    _identity_warnings(ctx)
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
        if key.test:
            _label_test(ctx)
        _label_source(ctx)
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
    """convert() of a file, read with io.loads so input decimals keep their written precision (write the bundle
    with io.dumps)."""
    from pathlib import Path
    return convert(loads(Path(path).read_text(encoding="utf-8")), str(path), **kw)


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


def _identity_warnings(ctx):
    k, grz = ctx.key, ctx.branch == "grz"
    if not k.case_id_is_local:
        ctx.warn("submission.localCaseId" if grz else "metaData.localCaseId",
                 f"no localCaseId: case key = {'tanG' if grz else 'tanC'} (per submission); follow-up, addition and "
                 "correction submissions of this case will create new resources instead of updating these")
    if k.test:
        ctx.warn("submission.submissionType" if grz else "metaData.submission.type",
                 "test submission: converted in the separate test identity namespace (case key '<caseId>|test'), "
                 "every resource labelled meta.security v3-ActReason#HTEST")


def _label_test(ctx):
    """meta.security HTEST on every resource of a test submission (docs/IDENTITY.md)."""
    for e in ctx.bundle.entries.values():
        sec = e["resource"].setdefault("meta", {}).setdefault("security", [])
        if HTEST not in sec:
            sec.append(dict(HTEST))
    p = "submission.submissionType" if ctx.branch == "grz" else "metaData.submission.type"
    if p in ctx._rows:
        ctx.preserve(p, "meta-security-htest")


def _label_source(ctx):
    """meta.source = the submission (CaseKey.source) on every resource, the Provenance included (docs/IDENTITY.md):
    a resource that a later correction no longer sends keeps naming an earlier submission."""
    src = ctx.key.source
    for e in ctx.bundle.entries.values():
        e["resource"].setdefault("meta", {})["source"] = src
    prefix = "submission." if ctx.branch == "grz" else "metaData.submission."
    for key, value in (("submissionDate" if ctx.branch == "grz" else "date", ctx.key.submission_date),
                       ("submissionType" if ctx.branch == "grz" else "type", ctx.key.submission_type)):
        if value and (prefix + key) in ctx._rows:
            ctx.preserve(prefix + key, "meta-source")


def _provenance(ctx):
    """One Provenance per submission (id parts: submission date, type, TAN): converter version, profile set,
    submission type as v3-DataOperation, sender and routing agents (references to the submission Organizations, the
    same for KDK and GRZ); targets every resource of the bundle.
    Earlier submissions keep their own Provenance, so the targets of successive submissions can be compared."""
    targets = [{"reference": e["fullUrl"]} for e in ctx.bundle.entries.values()]
    if not targets:
        return
    k, grz = ctx.key, ctx.branch == "grz"
    from .systems import SID_GDC, SID_KDK, SID_LE
    sub = (ctx.dk.get("metaData") or {}).get("submission") or ctx.dk.get("submission") or {}
    prefix = "submission." if grz else "metaData.submission."
    routing = []   # BfArM routing ids: no KDS element; their Organizations (builders.submission.submission_organization,
    # built by grz.donors / submission for both streams) are the sender and data-node agents
    for path_key, system, role, label, org in (
            ("submitterId", SID_LE, "author", "Leistungserbringer", "org_submitter"),
            ("clinicalDataNodeId", SID_KDK, "custodian", "Klinischer Datenknoten", "org_clinical-data-node"),
            ("genomicDataCenterId", SID_GDC, "custodian", "Genomrechenzentrum", "org_genomic-data-center")):
        if sub.get(path_key):
            who = {"display": label, "identifier": {"system": system, "value": sub[path_key]}}
            if ctx.refs.get(org):
                who = {**ctx.refs[org], **who}
            routing.append({"type": {"coding": [{"system": PROV_PARTICIPANT, "code": role}]}, "who": who})
    date = k.submission_date if len(k.submission_date or "") == 10 else None
    prov = ctx.new("Provenance", "submission", k.submission_date, k.submission_type, k.tan)
    prov.update(
        target=targets,
        occurredDateTime=date,
        recorded=f"{date or '1900-01-01'}T00:00:00Z",
        activity={"coding": [{"system": DATA_OPERATION, "code": DATA_OP[k.submission_type]}]
                  if k.submission_type in DATA_OP else None,
                  "text": f"genomde2fhir {__version__} profile-set {ctx.ps} submission {k.submission_type or '?'}"},
        agent=[{"type": {"coding": [{"system": PROV_PARTICIPANT, "code": "assembler"}]},
                "who": {"display": f"genomde2fhir {__version__}", "identifier": {"system": PROVENANCE_AGENT, "value": __version__}}}] + routing,
    )
    ctx.add(prov)
    for key, value, note in (("submissionDate" if grz else "date", k.submission_date, "submission-provenance"),
                             ("submissionType" if grz else "type", k.submission_type, "submission-provenance")):
        if value and (prefix + key) in ctx._rows:
            ctx.preserve(prefix + key, note)
