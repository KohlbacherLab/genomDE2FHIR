"""KDK submission metadata and the indication-board decision (oncology and rare disease).

Indication board (metaData.decisionToInclude / .molecularBoardDecisionDate / .rejectionJustification): the
multidisciplinary case conference in the field of diagnostics decides on inclusion in the Modellvorhaben. No MII
profile carries this decision (mii-pr-onko-tumorkonferenz needs an oBDS conference type and therapy-type
activities; Seltene has no board profile) -> local CarePlan profile `mvgs-inclusion-decision`:
  created = molecularBoardDecisionDate; one activity `mvgs-cs-mv-administrative#mv-genome-sequencing`
  decisionToInclude true  -> CarePlan.status active,  activity.detail.status scheduled
  decisionToInclude false -> CarePlan.status revoked, activity.detail.status cancelled,
                             reasonCode = mvgs-cs-mv-rejection-reason#<rejectionJustification>
Registered as ctx.refs['indication_board'] so plan builders can point `basedOn` at it.

Submission block (metaData.submission.*): transport metadata, no KDS element (mapping table NOMAP). submitterId,
date and type are used for resource identity (docs/IDENTITY.md) and the conversion Provenance; the routing ids and
the disease type are dropped with a reason.
"""
from ..systems import MVGS_SD
from ..terminology import local_coding
from .common import cc
from .consent import mark

PROFILE = MVGS_SD + "mvgs-inclusion-decision"
ADMIN_CS = "mvgs-cs-mv-administrative"
REJECTION_CS = "mvgs-cs-mv-rejection-reason"


def build(ctx):
    md = ctx.dk.get("metaData") or {}
    _submission(ctx, md.get("submission") or {})
    _indication_board(ctx, md)


def _submission(ctx, s):
    p = "metaData.submission."
    for k, how in (("submitterId", "identity: resource ids, local-case-id assigner (docs/IDENTITY.md)"),
                   ("date", "conversion Provenance.recorded"), ("type", "conversion Provenance.activity.text")):
        if s.get(k):
            ctx.preserve(p + k, how)
    # clinicalDataNodeId / genomicDataCenterId: preserved as conversion Provenance agents (convert._provenance)
    for k, why in (("diseaseType", "submission routing (oncological/hereditary/rare); the branch and the diagnosis "
                                   "resources carry the disease"),):
        if s.get(k):
            ctx.drop(p + k, s[k], why)


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
