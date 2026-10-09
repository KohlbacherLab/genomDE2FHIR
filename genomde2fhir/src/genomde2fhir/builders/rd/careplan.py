"""KDK rare-disease plan -> Seltene Therapieplan (CarePlan) with its recommendations.

Rows: plan.carePlanRd.*, plan.recommendedTherapies[].*, plan.recommendedStudies[].* (rare-disease table).

Resources
- CarePlan `mii-pr-seltene-therapieplan`: created = molecularBoardDecisionDate, addresses -> rd_diagnosis,
  supportingInfo -> rd_report + prior-findings reports (rd.prior). Recommendation flags (*Recommended = true) and clinicalManagementDescriptions[]
  become `activity.detail` entries coded with `mvgs-cs-rd-plan-recommendation` (no MII code exists). A flag that
  is false yields no activity: the five flags are mandatory in the KDK, so an absent flag activity in a genomDE
  plan means "not recommended". Recommendations are linked as `activity.reference` (slices
  MedikamentoesTherapie / NichtMedikamentoesTherapie / Studieneinschlussempfehlung); references other builders
  put into `ctx.bag['careplan_activities']` are appended.
- Therapy recommendations (DISCUSS-TD #34, REVIEW-TD A "Seltene strategy"): split by the Seltene strategy VS.
  systemicMedication / targetedMedication / preventionMedication / genetic (= gene-therapy) / combination ->
  MedicationRequest `mii-pr-seltene-therapieempfehlung`; prophylactic / earlyDetection / nutrition / other ->
  ServiceRequest `mii-pr-seltene-therapieempfehlung-nicht-medikamentoes`. `category:MVGenomSeqTherapieStrategie`
  and `category:MVGenomSeqTherapieTyp` (KDK `type` causal/symptomatic) carry exactly one coding each with the CS
  canonical (2027 discriminator = coding.system). The KDK names no substance: `medication[x]` (1..1) is a
  CodeableConcept carrying only data-absent-reason. strategyOther / strategyCombination -> `note`. No
  Evidenzgraduierung (extension removed in 2027; the KDK has no RD evidence level anyway).
- Study recommendations: ServiceRequest `mii-pr-seltene-studieneinschluss-anfrage` (fixed category/code),
  `supportingInfo:Studie` -> ResearchStudy `mii-pr-studie-studie` (identifier system by register: MII NamingSystems
  NCT / DRKS / EudraCT; register `other` -> identifier without system, register in `identifier.type.text`,
  preserved), variants -> `reasonReference` (the Seltene profile allows Observation there). No ResearchStudy
  without a study id or a real name. `yesButStudyIsUnknown` -> request without `supportingInfo:Studie`; a
  non-placeholder name/id goes to the request's `note` (preserved). Placeholders ('N/A', 'unknown') are dropped.
- Repeated KDK recommendation identifiers get the role index appended (no duplicate resource ids).
- Variants (`variants[]`; the synthetic corpus spells it `variantReferences`) resolve via ctx.ids[("variant", id)].

Registers ctx.refs['careplan'], ctx.ids[('therapy_recommendation', identifier)],
ctx.ids[('study_recommendation', identifier)].
"""
from ...systems import MII, MVGS_CS, SELTENE, SID_KDK_OBJECT, SNOMED
from ..common import cc, coding, dar_ext, scoped_id

P_CAREPLAN = SELTENE + "StructureDefinition/mii-pr-seltene-therapieplan"
P_MED = SELTENE + "StructureDefinition/mii-pr-seltene-therapieempfehlung"
P_NONMED = SELTENE + "StructureDefinition/mii-pr-seltene-therapieempfehlung-nicht-medikamentoes"
P_STUDY_REQ = SELTENE + "StructureDefinition/mii-pr-seltene-studieneinschluss-anfrage"
# modul-studie lives under /fhir/modul-studie/ (not /fhir/ext/): systems.STUDIE is wrong, see core_requests
P_STUDY = MII + "modul-studie/StructureDefinition/mii-pr-studie-studie"

CS_STRATEGY = SELTENE + "CodeSystem/mii-cs-seltene-therapieempfehlung-strategie"
CS_TYPE = SELTENE + "CodeSystem/mii-cs-seltene-therapieempfehlung-typ"
CS_PLAN_REC = MVGS_CS + "mvgs-cs-rd-plan-recommendation"

# KDK strategy -> (CS code, display, medication?)  (VS ...-strategie-medikamentoes / -nicht-medikamentoes)
STRATEGY = {
    "systemicMedication": ("systemic-medication", "Systemische Medikation", True),
    "targetedMedication": ("targeted-medication", "Zielgerichtete Medikation", True),
    "preventionMedication": ("prevention-medication", "Präventive Medikation", True),
    "genetic": ("gene-therapy", "Gentherapie", True),
    "combination": ("combination", "Kombinationstherapie", True),
    "prophylactic": ("prophylactic", "Prophylaxe", False),
    "earlyDetection": ("early-detection", "Früherkennung", False),
    "nutrition": ("nutrition", "Ernährungstherapie", False),
    "other": ("other", "Sonstige", False),
}
THERAPY_TYPE = {"causal": "Kausal", "symptomatic": "Symptomatisch"}

# register -> identifier system (MII NamingSystems mii-ns-mtb-nct, mii-ns-studie-drks, mii-ns-studie-eudract)
REGISTER_SYSTEM = {
    "NCT": "https://www.medizininformatik-initiative.de/fhir/modul-mtb/sid/nct",
    "DRKS": "https://www.medizininformatik-initiative.de/fhir/modul-studie/sid/drks",
    "Eudra-CT/CTIS": "https://www.medizininformatik-initiative.de/fhir/modul-studie/sid/eudract",
}
STUDY_CATEGORY = {"coding": [{"system": SNOMED, "code": "110465008", "display": "Clinical trial (procedure)"}]}
STUDY_CODE = {"coding": [{"system": SNOMED, "code": "702475000", "display": "Referral to clinical trial (procedure)"}]}
PLACEHOLDER_NAMES = {"", "n/a", "na", "unknown", "-"}

FLAGS = [  # (KDK flag, local code, display)
    ("studyRecommended", "study-inclusion", "Study inclusion recommended"),
    ("counsellingRecommended", "genetic-counselling", "Human genetic counselling recommended"),
    ("reEvaluationRecommended", "re-evaluation", "Re-evaluation recommended"),
    ("therapyRecommended", "therapy", "Therapy recommended"),
]
CLIN_MGMT = {
    "diseaseSpecificAmbulatoryCare": "Disease-specific ambulatory care",
    "universityAmbulatoryCare": "University ambulatory care",
    "localCrd": "Local centre for rare diseases",
    "otherCrd": "Other centre for rare diseases",
    "otherAmbulatoryCare": "Other ambulatory care",
    "gp": "General practitioner",
    "specialist": "Specialist",
}
PFX = "plan.carePlanRd."


def _variant_refs(ctx, rec: dict, path: str) -> list:
    """Resolve recommendation variants against ctx.ids[('variant', id)]; unresolved ids are dropped."""
    ids = rec.get("variants")
    if ids is None and rec.get("variantReferences") is not None:
        ids = rec["variantReferences"]
        ctx.warn(path, "non-schema key 'variantReferences' read as 'variants'")
    out, seen = [], set()
    for vid in ids or []:
        ref = ctx.ids.get(("variant", vid))
        if ref is None:
            ctx.drop(path, vid, "variant id not found among the converted variants")
        elif vid not in seen:
            seen.add(vid)
            out.append(dict(ref))
    if out:
        ctx.cover(path)
    return out


def _diagnosis_refs(ctx) -> list:
    r = ctx.refs.get("rd_diagnosis")
    return [dict(r)] if r else []


def _recommendation_identifier(ctx, value) -> list:
    i = scoped_id(ctx, SID_KDK_OBJECT, value)   # same system as oncology recommendations
    return [i] if i else []


def _therapy(ctx, i: int, rt: dict, board_date) -> dict | None:
    base = "plan.recommendedTherapies[]."
    strategy = rt.get("strategy")
    if strategy not in STRATEGY:
        ctx.drop(base + "strategy", strategy, "unknown therapy strategy")
        return None
    code, display, is_med = STRATEGY[strategy]
    rid = _rid(ctx, "therapy_recommendation", rt.get("identifier"), f"therapy-{i}", base + "identifier")
    cats = [cc(coding(CS_STRATEGY, code, display))]
    paths = [base + "strategy"]
    if rt.get("type") in THERAPY_TYPE:
        cats.append(cc(coding(CS_TYPE, rt["type"], THERAPY_TYPE[rt["type"]])))
        paths.append(base + "type")
    elif rt.get("type"):
        ctx.drop(base + "type", rt["type"], "unknown therapy type")
    notes = []
    if rt.get("strategyOther"):
        notes.append({"text": f"Sonstige Strategie: {rt['strategyOther']}"})
        paths.append(base + "strategyOther")
        if strategy != "other":
            ctx.warn(base + "strategyOther", f"strategyOther given for strategy {strategy!r}")
    if rt.get("strategyCombination"):
        notes.append({"text": f"Kombinationstherapie: {rt['strategyCombination']}"})
        paths.append(base + "strategyCombination")
        if strategy != "combination":
            ctx.warn(base + "strategyCombination", f"strategyCombination given for strategy {strategy!r}")
    reasons = _variant_refs(ctx, rt, base + "variants[]") + _diagnosis_refs(ctx)
    if rt.get("identifier"):
        paths.append(base + "identifier")

    if is_med:
        r = ctx.new("MedicationRequest", "therapy_recommendation", rid, profile=P_MED)
        r.update(
            identifier=_recommendation_identifier(ctx, rt.get("identifier")),
            status="active", intent="proposal", category=cats,
            # 1..1, but the KDK names no substance: CodeableConcept with data-absent-reason only
            medicationCodeableConcept={"extension": [dar_ext("unknown")]},
            subject=dict(ctx.patient), authoredOn=board_date,
            reasonReference=reasons, note=notes,
        )
    else:
        r = ctx.new("ServiceRequest", "therapy_recommendation", rid, profile=P_NONMED)
        r.update(
            identifier=_recommendation_identifier(ctx, rt.get("identifier")),
            status="active", intent="proposal", category=cats,
            # code 1..1 (example binding) with code.text 1..1: the recommended (non-medication) therapy is the
            # strategy itself; text = strategyOther when given, else the strategy display
            code=cc(coding(CS_STRATEGY, code, display), text=rt.get("strategyOther") or display),
            subject=dict(ctx.patient), authoredOn=board_date,
            reasonReference=reasons, note=notes,
        )
    ref = ctx.add(r, *paths)
    ctx.ids[("therapy_recommendation", rid)] = ref
    return ref


def _rid(ctx, kind: str, identifier, fallback: str, path: str) -> str:
    """Recommendation id part: the KDK identifier, else role + index; a repeated identifier gets the index
    appended (deterministic) instead of colliding with the first resource."""
    rid = identifier or fallback
    if (kind, rid) in ctx.ids:
        ctx.warn(path, f"duplicate recommendation identifier {rid!r}; second resource gets suffix '#{fallback}'")
        rid = f"{rid}#{fallback}"
    return rid


def _real(value) -> str | None:
    """Source string unless it is a placeholder ('N/A', 'unknown', ...)."""
    return value if isinstance(value, str) and value.strip().lower() not in PLACEHOLDER_NAMES else None


def _study(ctx, i: int, rs: dict, board_date) -> dict | None:
    base = "plan.recommendedStudies[]."
    rid = _rid(ctx, "study_recommendation", rs.get("identifier"), f"study-{i}", base + "identifier")
    register, sid, name = rs.get("register"), rs.get("id"), rs.get("name")
    title = _real(name)
    if name and not title:
        ctx.drop(base + "name", name, "placeholder study name")
    paths = [base + "identifier"] if rs.get("identifier") else []
    notes, study_ref = [], None

    if register == "yesButStudyIsUnknown":
        # a study inclusion is recommended, but no concrete study: request without supportingInfo:Studie
        paths.append(base + "register")
        ctx.rep("study-unknown-no-researchstudy")
        real_id = _real(sid)
        if sid and not real_id:
            ctx.drop(base + "id", sid, "placeholder study id (register yesButStudyIsUnknown)")
        if title or real_id:
            notes.append("Empfohlene Studie (nicht identifiziert): " + " ".join(x for x in (title, real_id) if x))
            for k, v in (("name", title), ("id", real_id)):
                if v:
                    ctx.preserve(base + k, "study-unknown-note")
    else:
        ident, study_paths = None, []
        if sid:
            system = REGISTER_SYSTEM.get(register)
            if system:
                ident = {"system": system, "value": sid}
                study_paths += [base + "id", base + "register"]
            else:   # 'other' or no register: identifier without a register system, register named in type.text
                ident = {"type": {"text": f"Studienregister: {register or 'unbekannt'}"}, "value": sid}
                study_paths.append(base + "id")
                if register:
                    ctx.preserve(base + "register", "study-register-other")
        elif register:
            ctx.drop(base + "register", register, "register without study id")
        if title:
            study_paths.append(base + "name")
        if ident or title:
            study = ctx.new("ResearchStudy", "study", register or "", sid or title, profile=P_STUDY)
            study.update(
                identifier=[ident] if ident else [],
                title=title,
                # status 1..1, required binding without an 'unknown' code (data-absent-reason fails it): a study
                # the board recommends for inclusion is taken to be open for accrual (same rule as onco.careplan)
                status="active",
            )
            if ctx.bundle.has(study["id"]):   # same study recommended twice: one ResearchStudy
                study_ref = {"reference": f"urn:uuid:{study['id']}"}
                ctx.cover(*study_paths)
            else:
                study_ref = ctx.add(study, *study_paths)

    req = ctx.new("ServiceRequest", "study_recommendation", rid, profile=P_STUDY_REQ)
    req.update(
        identifier=_recommendation_identifier(ctx, rs.get("identifier")),
        status="active", intent="proposal",
        category=[STUDY_CATEGORY], code=STUDY_CODE,
        subject=dict(ctx.patient), authoredOn=board_date,
        reasonReference=_variant_refs(ctx, rs, base + "variants[]") + _diagnosis_refs(ctx),
        supportingInfo=[study_ref] if study_ref else [],
        note=[{"text": n} for n in notes],
    )
    ref = ctx.add(req, *paths)
    ctx.ids[("study_recommendation", rid)] = ref
    return ref


def _flag_activity(code: str, display: str, description: str | None = None) -> dict:
    return {"detail": {"kind": "ServiceRequest", "code": cc(coding(CS_PLAN_REC, code, display)),
                       "status": "not-started", "description": description}}


def build(ctx):
    plan = ctx.dk.get("plan") or {}
    cp = plan.get("carePlanRd") or {}
    therapies = plan.get("recommendedTherapies") or []
    studies = plan.get("recommendedStudies") or []
    if not (cp or therapies or studies):
        return
    board_date = cp.get("molecularBoardDecisionDate")

    activities, paths = [], []
    for flag, code, display in FLAGS:
        v = cp.get(flag)
        if v is True:
            activities.append(_flag_activity(code, display))
        if isinstance(v, bool):
            paths.append(PFX + flag)    # false: no activity (closed set of mandatory flags)

    mgmt = cp.get("clinicalManagementRecommended")
    descs = [d for d in cp.get("clinicalManagementDescriptions") or [] if d]
    if isinstance(mgmt, bool):
        paths.append(PFX + "clinicalManagementRecommended")
    if descs:
        if mgmt is False:
            ctx.warn(PFX + "clinicalManagementDescriptions[]", "settings given although clinicalManagementRecommended is false")
        for d in descs:
            if d in CLIN_MGMT:
                activities.append(_flag_activity(d, CLIN_MGMT[d], CLIN_MGMT[d]))
                paths.append(PFX + "clinicalManagementDescriptions[]")
            else:
                ctx.drop(PFX + "clinicalManagementDescriptions[]", d, "unknown clinical management setting")
    elif mgmt is True:
        activities.append(_flag_activity("clinical-management", "Clinical management recommended"))

    for i, rt in enumerate(therapies):
        ref = _therapy(ctx, i, rt, board_date)
        if ref:
            activities.append({"reference": dict(ref)})
    for i, rs in enumerate(studies):
        ref = _study(ctx, i, rs, board_date)
        if ref:
            activities.append({"reference": dict(ref)})
    for extra in ctx.bag.get("careplan_activities", []):
        if isinstance(extra.get("reference"), str):      # a plain Reference
            activities.append({"reference": dict(extra)})
        else:                                             # a ready CarePlan.activity
            activities.append(extra)

    if not cp:
        ctx.warn("plan.carePlanRd", "recommendations without carePlanRd: CarePlan without created date")
    if board_date:
        paths.append(PFX + "molecularBoardDecisionDate")
    careplan = ctx.new("CarePlan", "therapieplan", profile=P_CAREPLAN)
    careplan.update(
        status="active", intent="proposal",
        subject=dict(ctx.patient), created=board_date,
        addresses=_diagnosis_refs(ctx),
        supportingInfo=([dict(ctx.refs["rd_report"])] if ctx.refs.get("rd_report") else [])
        + [dict(r) for r in ctx.bag.get("rd_prior_reports", [])],
        activity=activities,
    )
    ctx.add(careplan, *paths, name="careplan")
