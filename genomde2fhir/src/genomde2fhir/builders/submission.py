"""KDK submission metadata and the indication-board decision (oncology and rare disease).

Indication board (metaData.decisionToInclude / .molecularBoardDecisionDate / .rejectionJustification): the
multidisciplinary case conference in the field of diagnostics decides on inclusion in the Modellvorhaben. No MII
profile carries this decision (mii-pr-onko-tumorkonferenz needs an oBDS conference type and therapy-type
activities; Seltene has no board profile) -> local CarePlan profile `mvgs-inclusion-decision`:
  created = molecularBoardDecisionDate; one activity `mvgs-cs-mv-administrative#mv-genome-sequencing`
  decisionToInclude true  -> CarePlan.status active,  activity.detail.status scheduled
  decisionToInclude false -> CarePlan.status revoked, activity.detail.status cancelled,
                             reasonCode = mvgs-cs-mv-rejection-reason#<rejectionJustification>
Registered as ctx.refs['indication_board']; the oncology Therapieplan points `basedOn` at it (onco.careplan).

Submission block (metaData.submission.*): transport metadata, no KDS element; handled like GRZ submission.* (mapping
table DRAFT: kept in core resources without an MII profile). submitterId, clinicalDataNodeId and genomicDataCenterId
each give one core Organization (submission_organization, shared with grz.donors: id parts (role, value), identifier
le-id / clinical-data-node / genomic-data-center, name '<label> <value>'; an absent or empty id gives none), the
author / custodian agents of the per-submission Provenance (convert._provenance); the FML maps build the same
Organizations (DkOrg* groups, no Provenance); submitterId also scopes every resource identity (docs/IDENTITY.md).
Date and type are preserved on every resource by meta.source (identity.CaseKey.source, convert._label_source; also
without the Provenance) and by the per-submission Provenance (convert._provenance: occurredDateTime / recorded,
activity = v3-DataOperation by type, one Provenance per submission); a test submission's type also by the HTEST label
(separate identity namespace). The disease type is dropped with a reason: the KDK branch (oncology / rare disease) and
its diagnosis resources already carry the disease. GRZ keeps it as the reasonCode of its sequencing genomic study;
KDK builds no submission-level genomic study (its only genomic studies are the oncology prior-diagnostic studies of
case.priorDiagnostics[], which describe earlier tests and point to the diagnosis by reasonReference).
"""
from ..systems import MVGS_SD, SID_GDC, SID_KDK, SID_LE
from ..terminology import local_coding
from .common import cc, identifier
from .consent import mark

PROFILE = MVGS_SD + "mvgs-inclusion-decision"
ADMIN_CS = "mvgs-cs-mv-administrative"
REJECTION_CS = "mvgs-cs-mv-rejection-reason"
# submission field (same name in KDK metaData.submission and GRZ submission) -> (role, identifier system, name label);
# ctx.refs['org_<role>'] are the agents of the submission Provenance (convert._provenance)
SUBMISSION_ORGS = {
    "submitterId": ("submitter", SID_LE, "Leistungserbringer (submitter)"),
    "clinicalDataNodeId": ("clinical-data-node", SID_KDK, "Klinischer Datenknoten"),
    "genomicDataCenterId": ("genomic-data-center", SID_GDC, "Genomrechenzentrum"),
}


def build(ctx):
    md = ctx.dk.get("metaData") or {}
    _submission(ctx, md.get("submission") or {})
    _indication_board(ctx, md)


def submission_organization(ctx, sub: dict, key: str, prefix: str) -> dict | None:
    """Core Organization (no MII profile) for one routing id of the submission block, both streams alike: id parts
    (role, value), identifier <system>|<value>, name '<label> <value>', ctx.refs['org_<role>']; the field is preserved
    (rep submission-organization). None when the field is absent or empty."""
    val = sub.get(key)
    if not val:
        return None
    role, system, label = SUBMISSION_ORGS[key]
    org = ctx.new("Organization", role, val)
    org.update(identifier=[identifier(system, val)], active=True, name=f"{label} {val}")
    ref = ctx.add(org, name=f"org_{role}")
    ctx.preserve(prefix + key, "submission-organization")
    return ref


def _submission(ctx, s):
    p = "metaData.submission."
    for key in SUBMISSION_ORGS:     # same Organizations as GRZ (grz.donors); date / type: convert._provenance
        submission_organization(ctx, s, key, p)
    if s.get("diseaseType"):
        ctx.drop(p + "diseaseType", s["diseaseType"], "submission routing (oncological/hereditary/rare); the KDK "
                 "branch and its diagnosis resources carry the disease")


def _indication_board(ctx, md):
    include, date, reason = md.get("decisionToInclude"), md.get("molecularBoardDecisionDate"), \
        md.get("rejectionJustification")
    if include is None and not date:
        if reason:
            ctx.drop("metaData.rejectionJustification", reason, "no board decision to attach it to")
        return
    if not date:
        # created is 1..1 and the schema requires the date; never invent one
        ctx.drop("metaData.decisionToInclude", include, "board decision without molecularBoardDecisionDate")
        if reason:
            ctx.drop("metaData.rejectionJustification", reason, "board decision without molecularBoardDecisionDate")
        return
    detail = {"code": cc(local_coding(ADMIN_CS, "mv-genome-sequencing"))}
    paths = ["metaData.molecularBoardDecisionDate"]
    if include is None:
        detail["status"] = "unknown"
        cp_status = "unknown"
        ctx.warn("metaData.decisionToInclude", "board decision date without decisionToInclude")
    else:
        detail["status"] = "scheduled" if include else "cancelled"
        cp_status = "active" if include else "revoked"
    if reason:
        rc = local_coding(REJECTION_CS, reason)
        if include:
            ctx.drop("metaData.rejectionJustification", reason, "rejection reason with decisionToInclude = true")
        elif not rc:
            ctx.drop("metaData.rejectionJustification", reason, "unknown rejectionJustification value")
        else:
            detail["reasonCode"] = [cc(rc)]
    cp = ctx.new("CarePlan", "indication-board", profile=PROFILE)
    cp.update(status=cp_status, intent="plan", category=[cc(local_coding(ADMIN_CS, "indication-board"))],
              subject=ctx.patient, created=date, activity=[{"detail": detail}])
    ref = ctx.add(cp, *paths, name="indication_board")
    ctx.rep("mvgs-inclusion-decision")
    if include is not None:
        mark(ctx, "metaData.decisionToInclude", "mvgs-inclusion-decision")
    if detail.get("reasonCode"):
        mark(ctx, "metaData.rejectionJustification", "mvgs-inclusion-decision")
    return ref
