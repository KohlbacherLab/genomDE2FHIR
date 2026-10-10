"""GRZ donors[] (without labData) and submission.* -> Patients, family history, consents, Coverage, genomic study and
lab / submitter / GRZ / KDK Organizations (the submission Provenance is built by convert._provenance, one per
submission for both streams, with these Organizations as agents).

Rows: donors[].donorPseudonym, .gender, .relation, .mvConsent.*, .researchConsents[].* (via the consent builders),
submission.tanG, .localCaseId, .coverageType (MAPPED) and the transport rows submission.submitterId,
.genomicDataCenterId, .clinicalDataNodeId, .submissionDate, .submissionType, .diseaseType, .genomicStudyType,
.genomicStudySubtype, .labName (DRAFT in the table: kept in core resources without an MII profile, i.e. the
Organizations, the submission Provenance / meta.source and the genomic study, recorded as preserved). The submitter /
GRZ / KDK Organizations are built by submission.submission_organization, identically for KDK metaData.submission.*.

Identity (docs/IDENTITY.md): one GRZ-stream Patient per donor, id parts ('donor', donorPseudonym), identifier
donor-pseudonym '<submitterId>|<caseKey>|<donorPseudonym>' (case-scoped: the schema's literal 'index' pseudonym
recurs in every case); the index donor additionally carries tan-g and the sender-scoped local-case-id (same value
as the KDK Patient, so both streams meet on that identifier without sharing a resource). The genomic study is keyed
by CaseKey.submission_parts (id parts 'submission', 'genomic-study' [, submissionDate]): the initial submission and
its corrections share one study, which a correction rewrites in place; a follow-up / addition gets its own study
listing its own labData analyses, and the earlier study keeps its links. Relatives are linked to the index Patient by an
MII MolGen Familienanamnese (FamilyMemberHistory) pointing at the relative's own Patient through the core
extension familymemberhistory-patient-record; relation 'other' (and a second 'index') has no relationship concept
and is dropped. coverageType: versicherungsart-de-basis codes, SKT -> KBV_CS_FOR_Payor_Type_KBV, UNK ->
v3-NullFlavor (both systems are part of the required VersicherungsartDeBasisVS).

Shared names: ctx.refs['patient'] (index donor), ctx.refs['coverage'], ctx.refs['mv_consent'] (index donor),
ctx.refs['genomic_study']; ctx.ids[('donor', pseudonym)] for every donor (grz.labdata needs it);
ctx.refs['lab'] (sequencing lab Organization).
"""
from ...systems import (FHIR_EXT, MOLGEN, MTB, MVGS_SD, PERSON, SID_DONOR, SID_LE, SID_LOCAL_CASE, SID_TAN_G, SNOMED,
                        V2_0203, V3_OBSVALUE)
from ...terminology import local_coding
from ..coverage import add_coverage
from ..common import cc, coding, ext, identifier
from ..consent import build_mv_consent
from ..research_consent import build_research_consent
from ..submission import submission_organization
from ..patient import GENDER_AMTLICH_CS, GENDER_AMTLICH_EXT

PATIENT_PROFILE = PERSON + "StructureDefinition/PatientPseudonymisiert"
FMH_PROFILE = MOLGEN + "StructureDefinition/familienanamnese"
STUDY_PROFILE = {"oncological": MTB + "StructureDefinition/mii-pr-mtb-genomic-study"}
STUDY_PROFILE_DEFAULT = MOLGEN + "StructureDefinition/mii-pr-molgen-genomic-study"
STUDY_DESIGN_EXT = MVGS_SD + "mvgs-ex-genomic-study-design"
FMH_PATIENT_RECORD = FHIR_EXT + "familymemberhistory-patient-record"

ROLECODE = "http://terminology.hl7.org/CodeSystem/v3-RoleCode"
ADMIN_GENDER = "http://hl7.org/fhir/administrative-gender"
OBS_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category"

# relation -> (SNOMED descendant of 125677006 'Relative' [mii-vs-molgen-family-member-snomed], v3-RoleCode)
RELATION = {
    "mother": (("72705000", "Mother (person)"), ("MTH", "mother")),
    "father": (("66839005", "Father (person)"), ("FTH", "father")),
    "brother": (("70924004", "Brother (person)"), ("BRO", "brother")),
    "sister": (("27733009", "Sister (person)"), ("SIS", "sister")),
    "child": (("67822003", "Child (person)"), ("CHILD", "child")),
}
GENDERS = ("male", "female", "other", "unknown")
SUBTYPE_CS = "mvgs-cs-grz-study-subtype"
DISEASE_CS = "mvgs-cs-grz-disease-type"


def build(ctx):
    sub = ctx.dk.get("submission") or {}
    donors = [d for d in ctx.dk.get("donors") or [] if d.get("donorPseudonym")]
    if not donors:
        ctx.warn("donors[]", "no donor with a donorPseudonym; no Patient created")
        return
    index = next((d for d in donors if d.get("relation") == "index"), None)
    has_index = index is not None
    if not has_index:
        # schema allows it; tanG/localCaseId/coverage still need a patient, but no relationship can be asserted
        index = donors[0]
        ctx.warn("donors[].relation", f"no donor with relation 'index'; donor {index['donorPseudonym']!r} "
                                      "carries the index identifiers, relationships are not represented")
    submitter = _organization(ctx, sub, "submission.submitterId")

    # Patients first: the index Patient must be registered before family history and consents reference it
    pats = {}
    for d in donors:
        pats[id(d)] = _patient(ctx, d, sub, d is index, submitter)
    ctx.refs["patient"] = pats[id(index)]

    index_mv = None
    for d in donors:
        if not has_index:
            ctx.drop("donors[].relation", d.get("relation"), "no index donor to relate to")
        elif d is not index:
            _family_history(ctx, d, pats[id(d)])
        pseudo = d["donorPseudonym"]
        mvc = d.get("mvConsent")
        mv = build_mv_consent(ctx, mvc, pats[id(d)], "donors[].mvConsent", (pseudo,))
        if mvc and not mv:   # the consent builder warned (no usable scope); its other values go with it
            for k in ("version", "presentationDate"):
                if mvc.get(k):
                    ctx.drop(f"donors[].mvConsent.{k}", mvc[k], "no MV Consent emitted (no usable scope entry)")
        if d is index:
            index_mv = mv
        for i, rc in enumerate(d.get("researchConsents") or []):
            build_research_consent(ctx, rc, pats[id(d)], "donors[].researchConsents[]", (pseudo, i))
    if index_mv:   # set after the loop: the consent builder may register its own name per donor
        ctx.refs["mv_consent"] = index_mv

    _coverage(ctx, sub)
    _genomic_study(ctx, sub)
    _routing_organizations(ctx, sub)


# ---- Patients ------------------------------------------------------------------------------------------
def _patient(ctx, d: dict, sub: dict, is_index: bool, submitter: dict | None) -> dict:
    k = ctx.key
    pseudo = d["donorPseudonym"]
    pat = ctx.new("Patient", "donor", pseudo, profile=PATIENT_PROFILE)
    ids = [identifier(SID_DONOR, k.scoped(pseudo), V3_OBSVALUE, "PSEUDED")]
    paths = ["donors[].donorPseudonym"]
    if is_index:
        if d.get("relation") == "index":     # the index role is the Patient carrying tan-g / local-case-id
            paths.append("donors[].relation")
        if sub.get("tanG"):
            ids.append(identifier(SID_TAN_G, sub["tanG"], V3_OBSVALUE, "PSEUDED"))
            paths.append("submission.tanG")
        if sub.get("localCaseId"):
            ids.append(identifier(SID_LOCAL_CASE, k.scoped(), V2_0203, "MR",
                                  assigner_system=SID_LE, assigner_value=k.submitter_id))
            paths.append("submission.localCaseId")
    pat["identifier"] = ids
    g = d.get("gender")
    if g:
        pat["gender"] = g if g in GENDERS else "unknown"
        if pat["gender"] == "other":  # mii-pat-1: amtliche Differenzierung required (genomDE other = divers)
            pat["_gender"] = {"extension": [ext(GENDER_AMTLICH_EXT, valueCoding={
                "system": GENDER_AMTLICH_CS, "code": "D", "display": "divers"})]}
        paths.append("donors[].gender")
    if submitter:
        pat["managingOrganization"] = submitter
    ref = ctx.add(pat, *paths)
    ctx.ids[("donor", pseudo)] = ref
    return ref


def _family_history(ctx, d: dict, relative_ref: dict):
    rel = d.get("relation")
    if rel == "index":
        ctx.drop("donors[].relation", rel, "more than one donor with relation 'index'; only the first is the index "
                                           "Patient, this donor's Patient is kept without a relationship")
        return
    if rel not in RELATION:
        # 'other' (or an unknown value): no relationship concept; the donor's own Patient is still created
        ctx.drop("donors[].relation", rel, "no family relationship concept for this value; donor Patient kept "
                                           "without a link to the index patient")
        return
    (sct, sct_display), (role, role_display) = RELATION[rel]
    fmh = ctx.new("FamilyMemberHistory", "donor", d["donorPseudonym"], profile=FMH_PROFILE)
    fmh.update(
        extension=[ext(FMH_PATIENT_RECORD, valueReference=relative_ref)],
        status="partial",            # only the relationship (and sex) is known from the GRZ submission
        patient=ctx.patient,
        relationship=cc(coding(SNOMED, sct, sct_display), coding(ROLECODE, role, role_display)),
    )
    if d.get("gender") in GENDERS:
        fmh["sex"] = cc(coding(ADMIN_GENDER, d["gender"]))
    ctx.add(fmh, "donors[].relation")


# ---- Coverage -------------------------------------------------------------------------------------------
def _coverage(ctx, sub: dict):
    if sub.get("coverageType"):
        add_coverage(ctx, sub["coverageType"], "submission.coverageType")


# ---- Organizations ---------------------------------------------------------------------------------------
def _organization(ctx, sub: dict, path: str) -> dict | None:
    """Submission Organization, built exactly as for KDK (submission.submission_organization)."""
    return submission_organization(ctx, sub, path.split(".")[-1], "submission.")


def _lab(ctx, sub: dict) -> dict | None:
    name = sub.get("labName")
    if not name:
        return None
    org = ctx.new("Organization", "lab", name)
    org.update(active=True, name=name)
    return ctx.add(org, "submission.labName", name="lab")


# ---- genomic study (submission-level) ---------------------------------------------------------------------
def _genomic_study(ctx, sub: dict):
    disease = sub.get("diseaseType")
    profile = STUDY_PROFILE.get(disease, STUDY_PROFILE_DEFAULT)
    # initial + corrections: one study (a correction rewrites it); follow-up / addition: own study (docs/IDENTITY.md)
    st = ctx.new("Procedure", "submission", "genomic-study", *ctx.key.submission_parts(), profile=profile)
    exts = []
    design = sub.get("genomicStudyType")
    if design:
        c = local_coding("mvgs-cs-genomic-study-design", design)
        if c:
            exts.append(ext(STUDY_DESIGN_EXT, valueCoding=c))
            ctx.preserve("submission.genomicStudyType", "mvgs-ex-genomic-study-design")
        else:
            ctx.drop("submission.genomicStudyType", design, "not in mvgs-cs-genomic-study-design")
    subtype = sub.get("genomicStudySubtype")
    code = None
    if subtype:
        c = local_coding(SUBTYPE_CS, subtype)
        if c:
            code = cc(c)
            ctx.preserve("submission.genomicStudySubtype", SUBTYPE_CS)
        else:
            ctx.drop("submission.genomicStudySubtype", subtype, f"not in {SUBTYPE_CS}")
    reason = None
    if disease:
        c = local_coding(DISEASE_CS, disease)
        if c:
            reason = [cc(c)]
            ctx.preserve("submission.diseaseType", DISEASE_CS)
        else:
            ctx.drop("submission.diseaseType", disease, f"not in {DISEASE_CS}")
    lab = _lab(ctx, sub)
    st.update(
        extension=exts,
        status="completed",          # the GRZ submission reports the finished sequencing
        category=cc(coding(OBS_CATEGORY, "laboratory")),
        code=code,
        subject=ctx.patient,
        performer=[{"actor": lab}] if lab else None,
        reasonCode=reason,
    )
    ctx.add(st, name="genomic_study")


# ---- routing Organizations (agents of the submission Provenance, convert._provenance; same for KDK) -------------
def _routing_organizations(ctx, sub: dict):
    _organization(ctx, sub, "submission.genomicDataCenterId")
    _organization(ctx, sub, "submission.clinicalDataNodeId")
