"""KDK OncologyPlan -> MTB Therapieplan (CarePlan) and the recommendations it references.

Rows: plan.carePlanOd.*, plan.recommendedSystemicTherapies[].*, plan.recommendedStudies[].*,
plan.preventiveMeasures[].*  (docs/REVIEW-TD-2026-10-06.md A "MTB plan"; docs/REPRESENTATIONS.md #3, #5, #15, #16).

  carePlanOd                    -> CarePlan mii-pr-mtb-therapieplan (created = molecularBoardDecisionDate)
    otherRecommendations[]      -> activity:obds.detail.code (mii-cs-onko-therapie-typ, 1:1)
    interventionRecommended     -> suitableInterventions[] as mii-pr-onko-therapieempfehlung-operation
                                   (flags: mvgs-ex-intervention-purpose); without any: activity:obds 'OP'
    counsellingRecommended      -> mii-pr-mtb-humangenetische-beratung-auftrag (activity reference)
    reEvaluationRecommended     -> mii-pr-mtb-histologie-evaluation-auftrag (DNPM histology re-evaluation request)
    studyRecommended            -> presence of studieneinschluss-anfrage activities (one unspecific request
                                   when the flag is true but no study is listed)
  recommendedSystemicTherapies  -> mii-pr-mtb-therapieempfehlung (MedicationRequest, one per substance;
                                   several substances are grouped by mii-pr-mtb-therapieempfehlung-kombination)
  recommendedStudies            -> mii-pr-mtb-studieneinschluss-anfrage (ServiceRequest) + mii-pr-mtb-studie
  preventiveMeasures            -> ServiceRequest (intent plan), code.text = type
  indication board (submission) -> Therapieplan.basedOn (ctx.refs['indication_board'], CarePlan 0..* in both sets)

Boolean flags are encoded by presence of the activity (false -> no activity), hence covered either way.
`recommendations.build` is a no-op: everything is built here because the CarePlan references it.

Identity (docs/IDENTITY.md): a repeated recommendation / measure identifier gets the array index appended to its
id part and a warning (ctx.ids keeps the first). A combination's first MedicationRequest keeps the recommendation's
id, further members add their index, so the ids do not depend on the number of substances. The recommendation
identifier is carried by the first (or only) MedicationRequest, the target of follow-up causedBy references, and by
the RequestGroup; combination members additionally carry '<identifier>:<member index>'.
"""
import re

from ...bundle import prune
from ...systems import MII, MTB, MVGS_SD, ONKO, SID_KDK_OBJECT, SNOMED
from ...terminology import local_coding
from ..common import as_list, atc_system, cc, coding, ext, scoped_id
from ..rd.careplan import PLACEHOLDER_NAMES   # same placeholder rule as rare disease (study names)

P = "plan."
CP = P + "carePlanOd."
TH = P + "recommendedSystemicTherapies[]."
ST = P + "recommendedStudies[]."
PM = P + "preventiveMeasures[]."
SI = CP + "suitableInterventions[]."

PR_PLAN = MTB + "StructureDefinition/mii-pr-mtb-therapieplan"
PR_THERAPY = MTB + "StructureDefinition/mii-pr-mtb-therapieempfehlung"
PR_COMBI = MTB + "StructureDefinition/mii-pr-mtb-therapieempfehlung-kombination"
PR_STUDY_REQ = MTB + "StructureDefinition/mii-pr-mtb-studieneinschluss-anfrage"
PR_STUDY = MTB + "StructureDefinition/mii-pr-mtb-studie"
PR_COUNSEL = MTB + "StructureDefinition/mii-pr-mtb-humangenetische-beratung-auftrag"
PR_REEVAL = MTB + "StructureDefinition/mii-pr-mtb-histologie-evaluation-auftrag"
PR_OPERATION = ONKO + "StructureDefinition/mii-pr-onko-therapieempfehlung-operation"

EX_PRIO = MTB + "StructureDefinition/mii-ex-mtb-empfehlung-prioritaet"
EX_EVIDENCE = MTB + "StructureDefinition/mii-ex-mtb-empfehlung-evidenzgraduierung"
CS_EVIDENCE = MTB + "CodeSystem/mii-cs-mtb-empfehlung-evidenzgrad"
CS_EVIDENCE_ADD = MTB + "CodeSystem/mii-cs-mtb-empfehlung-evidenzgrad-zusatzverweis"
CS_PLAN_TYPE = ONKO + "CodeSystem/mii-cs-onko-therapieplanung-typ"
CS_THERAPY_TYPE = ONKO + "CodeSystem/mii-cs-onko-therapie-typ"

EX_USE_TYPE = MVGS_SD + "mvgs-ex-recommendation-use-type"
EX_STUDY_EVIDENCE = MVGS_SD + "mvgs-ex-evidence-level"
EX_PURPOSE = MVGS_SD + "mvgs-ex-intervention-purpose"
CS_USE_TYPE = "mvgs-cs-recommendation-use-type"

# KDK object identifiers (recommendation / measure UUIDs); no shared constant in systems.py yet (core request)

# MTB register NamingSystems (mii-pr-mtb-studie identifier slices NCT / DRKS / EudraCT)
REGISTER_SYSTEM = {
    "NCT": MII + "modul-mtb/sid/nct",
    "DRKS": MII + "modul-studie/sid/drks",
    "Eudra-CT/CTIS": MII + "modul-studie/sid/eudract",
}

# mii-cs-onko-therapie-typ displays (Onko 2026.0.3 = 2027.0.0-ballot.1)
THERAPY_TYPE = {
    "CH": "Chemotherapie", "HO": "Hormontherapie", "IM": "Immun-/Antikörpertherapie",
    "ZS": "zielgerichtete Substanzen", "SZ": "Stammzelltransplantation (inklusive Knochenmarktransplantation)",
    "CI": "Chemo- + Immun-/Antikörpertherapie", "CZ": "Chemotherapie + zielgerichtete Substanzen",
    "CIZ": "Chemo- + Immun-/Antikörpertherapie + zielgerichtete Substanzen",
    "IZ": "Immun-/Antikörpertherapie + zielgerichtete Substanzen", "WW": "Watchful Waiting",
    "AS": "Active Surveillance", "WS": "Wait and see", "OP": "Operation", "ST": "Strahlentherapie",
    "KW": "keine weitere tumorspezifische Therapie empfohlen", "SO": "Sonstiges",
}
EVIDENCE_LEVELS = {"m1A", "m1B", "m1C", "m2A", "m2B", "m2C", "m3", "m4", "undefined"}
EVIDENCE_ADD = {"is", "iv", "Z", "R"}

STUDY_CATEGORY = cc(coding(SNOMED, "110465008", "Clinical trial (procedure)"))
STUDY_CODE = cc(coding(SNOMED, "702475000", "Referral to clinical trial (procedure)"))
COUNSEL_CODE = cc(coding(SNOMED, "788339009", "Genetic consultation (procedure)"))
REEVAL_CODE = cc(coding(SNOMED, "183825009", "Refer for histology (procedure)"))
PREVENTIVE_CATEGORY = cc(coding(SNOMED, "169443000", "Preventive procedure (procedure)"))


def build(ctx):
    plan = ctx.dk.get("plan") or {}
    cp = plan.get("carePlanOd")
    if not cp:
        return
    date = cp.get("molecularBoardDecisionDate")
    if not date:
        ctx.warn(CP + "molecularBoardDecisionDate", "no board date: CarePlan.created / authoredOn missing")
    base = {"subject": ctx.patient, "authoredOn": date}
    activities = []

    # systemic therapy recommendations
    for i, t in enumerate(as_list(plan.get("recommendedSystemicTherapies"))):
        ref = _therapy(ctx, t, i, base)
        if ref:
            activities.append({"reference": ref})

    # study recommendations
    studies = as_list(plan.get("recommendedStudies"))
    for i, s in enumerate(studies):
        activities.append({"reference": _study(ctx, s, i, base)})
    flag = cp.get("studyRecommended")
    if flag is not None:
        if flag and not studies:
            # recommendation to take part in a study without a named study: an unspecific inclusion request
            sr = _request(ctx, PR_STUDY_REQ, ("study_recommendation", "unspecified"), base,
                          category=[STUDY_CATEGORY], code=STUDY_CODE)
            activities.append({"reference": ctx.add(sr)})
            ctx.rep("study-recommended-without-study")
        elif not flag and studies:
            ctx.warn(CP + "studyRecommended", "false although recommendedStudies[] is not empty; studies emitted")
        ctx.cover(CP + "studyRecommended")

    # human genetic counselling / diagnostic re-evaluation
    if cp.get("counsellingRecommended"):
        activities.append({"reference": ctx.add(_request(ctx, PR_COUNSEL, ("counselling",), base, code=COUNSEL_CODE))})
    if cp.get("reEvaluationRecommended"):
        # DNPM Therapieplan "Histologie-Reevaluations-Auftrag" is the source of KDK reEvaluationRecommended
        activities.append({"reference": ctx.add(_request(ctx, PR_REEVAL, ("reevaluation",), base, code=REEVAL_CODE))})
        ctx.rep("reevaluation-as-histology-reevaluation-request")
    for k in ("counsellingRecommended", "reEvaluationRecommended"):
        if cp.get(k) is not None:
            ctx.cover(CP + k)

    # interventions (operations) and other therapeutic recommendations (oBDS therapy type)
    obds = []
    for code in as_list(cp.get("otherRecommendations")):
        if code in THERAPY_TYPE and code not in obds:
            obds.append(code)
        elif code not in THERAPY_TYPE:
            ctx.drop(CP + "otherRecommendations[]", code, "not in mii-cs-onko-therapie-typ")
    if obds:
        ctx.cover(CP + "otherRecommendations[]")
    interventions = as_list(cp.get("suitableInterventions"))
    for i, si in enumerate(interventions):
        activities.append({"reference": _intervention(ctx, si, i, base)})
    if cp.get("interventionRecommended") is not None:
        if cp["interventionRecommended"] and not interventions and "OP" not in obds:
            obds.append("OP")   # "Recommendation for an operation" without a specified intervention
        elif not cp["interventionRecommended"]:
            if interventions:
                ctx.warn(CP + "interventionRecommended", "false although suitableInterventions[] is not empty")
            if "OP" in obds:   # the OP activity from otherRecommendations[] reads back as interventionRecommended=true
                ctx.warn(CP + "interventionRecommended", "false although otherRecommendations[] contains OP; "
                         "the OP activity is emitted")
        ctx.cover(CP + "interventionRecommended")
    for code in obds:
        activities.append({"detail": {"code": cc(coding(CS_THERAPY_TYPE, code, THERAPY_TYPE[code])),
                                      "status": "not-started"}})

    # preventive measures (hereditary cases): ServiceRequest, intent plan (REPRESENTATIONS #5)
    for i, m in enumerate(as_list(plan.get("preventiveMeasures"))):
        activities.append({"reference": _preventive(ctx, m, i, base)})

    for extra in ctx.bag.get("careplan_activities", []):   # plain References or ready CarePlan.activity
        activities.append({"reference": extra} if isinstance(extra.get("reference"), str) else extra)

    plan_res = ctx.new("CarePlan", "mtb-therapieplan", profile=PR_PLAN)
    plan_res.update({
        "status": "active",
        "intent": "plan",
        # category 1..1 with coding 1..* required-bound to mii-vs-onko-therapieplanung-typ (praeth/postop/postth/ther);
        # the Datenkranz has no board type, so a code must be chosen by convention: 'praeth' as in MII's MTB example
        # (mii-exa-mtb-kim-musterperson-therapieplan). Reported as a representation, not a source fact.
        "category": [cc(coding(CS_PLAN_TYPE, "praeth"), text="Molekulares Tumorboard")],
        "subject": ctx.patient,
        "created": date,
        # the MV indication board decision (submission.py, REPRESENTATIONS #36); CarePlan.basedOn is open (0..*)
        "basedOn": [ctx.refs["indication_board"]] if ctx.refs.get("indication_board") else [],
        "addresses": [ctx.refs["primary"]] if ctx.refs.get("primary") else [],
        "supportingInfo": [ctx.refs["episode"]] if ctx.refs.get("episode") else [],
        "activity": activities,
    })
    ctx.rep("careplan-category-praeth-convention")
    ctx.add(plan_res, *([CP + "molecularBoardDecisionDate"] if date else []), name="careplan")


# ---- helpers ---------------------------------------------------------------------------------------
def _identifier(ctx, value):
    i = scoped_id(ctx, SID_KDK_OBJECT, value)
    return [i] if i else []


def _rid(ctx, kind: str, identifier, i: int, path: str) -> str:
    """Id part of a recommendation / measure: the KDK identifier, else 'index-<i>'. A repeated identifier gets the
    array index appended and a warning (docs/IDENTITY.md, as rd.careplan._rid) instead of a duplicate resource."""
    rid = identifier or f"index-{i}"
    if (kind, rid) in ctx.ids:
        ctx.warn(path, f"duplicate identifier {rid!r}; id made unique with array index {i}")
        rid = f"{rid}#{i}"
    return rid


def _real(value) -> str | None:
    """Source string unless it is a placeholder (rd.careplan.PLACEHOLDER_NAMES, trimmed, any case: 'N/A', 'unknown',
    '-', 'unbekannt', 'k. A.', 'keine Angabe', ...)."""
    return value if isinstance(value, str) and value.strip().lower() not in PLACEHOLDER_NAMES else None


def _request(ctx, profile, id_parts, base, **fields):
    """ServiceRequest skeleton (status active, intent proposal) with subject + authoredOn."""
    sr = ctx.new("ServiceRequest", *id_parts, profile=profile)
    sr.update({"status": "active", "intent": "proposal", **fields, **base})
    return sr


def _primary(ctx, path):
    p = ctx.refs.get("primary")
    if not p:
        ctx.warn(path, "no primary-tumour Condition (ctx.refs['primary']); reasonReference:Primaertumor missing")
    return p


def _variant_refs(ctx, ids, path):
    """References for KDK variant identifiers (registered by the molecular builders). Exact identifier first; else
    a cited id resolves to every finding whose identifier is '<cited>_<suffix>' (a CNV split into one entry per
    gene, '<id>_<GENE>'), with one warning per cited id."""
    out = []
    for vid in as_list(ids):
        r = ctx.ids.get(("variant", vid))
        found = [r] if r else _split_variant_refs(ctx, vid, path)
        if not found:
            ctx.drop(path, vid, "cited variant id not present in this submission")
        out += [x for x in found if x not in out]
    return out


def _split_variant_refs(ctx, vid, path) -> list:
    if vid in (None, ""):
        return []
    prefix = f"{vid}_"
    hits = [(k[1], r) for k, r in ctx.ids.items() if k[0] == "variant" and isinstance(k[1], str)
            and k[1].startswith(prefix)]
    warned = ctx.bag["plan_split_variant_ids"]   # one warning per cited id (therapies and studies may share it)
    if hits and vid not in warned:
        warned.append(vid)
        ctx.warn(path, f"variant id {vid!r} not found; resolved to the {len(hits)} finding(s) "
                       f"'{prefix}<suffix>' ({', '.join(k[len(prefix):] for k, _ in hits)})")
    return [r for _, r in hits]


def _priority(ctx, value, path):
    if value is None:
        return None
    # the schema's integer may be written as an integral decimal (1.0, 1e0; JSON Schema counts it as an integer): kept as
    # that integer, as the FML map does (OncoPlanPrio); positiveInt range 1..2147483647
    n = value if isinstance(value, int) and not isinstance(value, bool) else \
        int(value) if isinstance(value, float) and value.is_integer() else None
    if n is not None and 0 < n <= 2147483647:
        ctx.cover(path)
        return ext(EX_PRIO, valuePositiveInt=n)
    ctx.drop(path, value, "priority is not a positive integer (mii-ex-mtb-empfehlung-prioritaet)")
    return None


def _evidence_cc(ctx, level, details, path):
    """CodeableConcept with coding:Evidenzgrad (+ coding:Zusatzverweis); Z(FDA) -> Z + text."""
    if level not in EVIDENCE_LEVELS:
        if level is not None:
            ctx.drop(path + "evidenceLevel", level, "not in mii-cs-mtb-empfehlung-evidenzgrad")
        return None
    codings = [coding(CS_EVIDENCE, level)]
    text = None
    for d in as_list(details):
        if d == "Z(FDA)":
            if "Z" not in [c["code"] for c in codings[1:]]:
                codings.append(coding(CS_EVIDENCE_ADD, "Z"))
            text = "Zusatzverweis Z(FDA)"
            ctx.preserve(path + "evidenceLevelDetails[]", "evidence-z-fda-as-z-plus-text")
        elif d in EVIDENCE_ADD:
            if d not in [c["code"] for c in codings[1:]]:
                codings.append(coding(CS_EVIDENCE_ADD, d))
        else:
            ctx.drop(path + "evidenceLevelDetails[]", d, "not in mii-cs-mtb-empfehlung-evidenzgrad-zusatzverweis")
    return cc(*codings, text=text)


def _medication(ctx, sub, path):
    """Substance -> CodeableConcept (ATC BfArM -> coding:atcClassDe, WHO -> coding:atcClassEn); paths covered."""
    concept, paths = _medication_cc(ctx, sub, path)
    ctx.cover(*paths)
    return concept


def _medication_cc(ctx, sub, path) -> tuple:
    """(CodeableConcept, mapping paths it carries) for one substance, nothing covered yet."""
    c = sub.get("code") or {}
    name = sub.get("name")
    paths = []
    cod = None
    if c.get("code"):
        cod = coding(atc_system(ctx, c.get("system"), path + "code.system"), c["code"], c.get("display"), c.get("version"))
        paths += [path + "code.code", path + "code.system"] + \
                 [path + "code." + k for k in ("display", "version") if c.get(k)]
    if name:
        paths.append(path + "name")
    return cc(cod, text=name or c.get("display")), paths


# ---- systemic therapy recommendations ------------------------------------------------------------
def _therapy(ctx, t, i, base):
    path = TH
    tid = _rid(ctx, "therapy_recommendation", t.get("identifier"), i, path + "identifier")
    subs = [s for s in as_list(t.get("substances")) if s and ((s.get("code") or {}).get("code") or s.get("name"))]
    if not subs:   # medication[x] is 1..1: without a coded or named substance there is no Therapieempfehlung
        ctx.drop(path + "identifier", tid, "therapy recommendation without substance: no MedicationRequest")
        return None
    # medicationCodeableConcept.coding is 1..*: name-only substances become a note (as in prior/follow-up therapies)
    named = [s["name"] for s in subs if not (s.get("code") or {}).get("code")]
    subs = [s for s in subs if (s.get("code") or {}).get("code")]
    if not subs:
        ctx.drop(path + "substances[].name", "; ".join(named), "no coded substance: Therapieempfehlung needs "
                 "medicationCodeableConcept.coding (1..*)")
        return None
    if named:
        ctx.preserve(path + "substances[].name", "substance-name-only-note")
    exts = []
    prio = _priority(ctx, t.get("priority"), path + "priority")
    if prio:
        exts.append(prio)
    ev = _evidence_cc(ctx, t.get("evidenceLevel"), t.get("evidenceLevelDetails"), path)
    if ev:
        exts.append(ext(EX_EVIDENCE, valueCodeableConcept=ev))
        ctx.cover(path + "evidenceLevel")
        if len(ev.get("coding", [])) > 1:
            ctx.cover(path + "evidenceLevelDetails[]")
    use = t.get("type")
    if use and use != "unknown":
        c = local_coding(CS_USE_TYPE, use)
        if c:
            exts.append(ext(EX_USE_TYPE, valueCoding=c))
            ctx.preserve(path + "type", "recommendation-use-type-mvgs-extension")
        else:
            ctx.drop(path + "type", use, "not in mvgs-cs-recommendation-use-type")
    elif use == "unknown":
        ctx.drop(path + "type", use, "use type unknown: mvgs-ex-recommendation-use-type omitted")

    strategy = t.get("therapeuticStrategy")
    category = []
    if strategy in THERAPY_TYPE:
        category = [cc(coding(CS_THERAPY_TYPE, strategy, THERAPY_TYPE[strategy]))]
    elif strategy:
        ctx.drop(path + "therapeuticStrategy", strategy, "not in mii-cs-onko-therapie-typ")

    reasons = []
    prim = _primary(ctx, path + "identifier")
    if prim:
        reasons.append(prim)
    variants = _variant_refs(ctx, t.get("variants"), path + "variants[]")
    if variants:
        ctx.cover(path + "variants[]")
    reasons += variants

    common = {"status": "active", "intent": "proposal", **base, "reasonReference": reasons}
    if named:
        common["note"] = [{"text": "Substanz ohne Code: " + n} for n in named]
    refs = []
    combo = len(subs) > 1
    for j, s in enumerate(subs):
        # the first substance keeps the recommendation's id whatever the substance count, further members add their
        # index: a correction that adds or removes a combination partner rewrites the same MedicationRequests
        mr = ctx.new("MedicationRequest", "therapy_recommendation", tid, *((j,) if j else ()), profile=PR_THERAPY)
        # identifier: the plain recommendation id stays on exactly one MedicationRequest, the first member (as its
        # resource id), so a follow-up's logical causedBy {type MedicationRequest, identifier <id>} (plan not in the
        # submission) resolves to it whether the recommendation is single or a combination, and before and after a
        # correction adds a partner (#13: causedBy -> the first member). Combination members additionally carry
        # '<id>:<member index>' (the first: both), one per member; the RequestGroup carries <id> (another type).
        ident = t.get("identifier")
        members = (([ident] if j == 0 else []) + ([f"{ident}:{j}"] if combo else [])) if ident else []
        mr.update({"extension": exts, "identifier": [i for m in members for i in _identifier(ctx, m)],
                   "medicationCodeableConcept": _medication(ctx, s, path + "substances[]."),
                   "category": category, **common})
        refs.append(ctx.add(mr))
        # per-substance target of follow-up MedicationStatement.basedOn (first member with that code wins)
        ctx.ids.setdefault(("therapy_recommendation_member", tid, s["code"]["code"]), refs[-1])
    if t.get("identifier"):
        ctx.cover(path + "identifier")
    ctx.ids[("therapy_recommendation", tid)] = refs[0]
    if len(subs) == 1:
        if category:
            ctx.preserve(path + "therapeuticStrategy", "therapy-type-medicationrequest-category")
        return refs[0]
    # combination: RequestGroup carries the therapy type in its (preferred-bound) code
    rg = ctx.new("RequestGroup", "therapy_recommendation", tid, profile=PR_COMBI)
    rg.update({"extension": exts, "identifier": _identifier(ctx, t.get("identifier")), "status": "active",
               "intent": "proposal", "code": category[0] if category else None, "subject": ctx.patient,
               "authoredOn": base.get("authoredOn"), "reasonReference": [prim] if prim else [],
               "action": [{"resource": r} for r in refs]})
    ctx.ids[("therapy_recommendation_group", tid)] = ref = ctx.add(rg)
    if category:
        ctx.cover(path + "therapeuticStrategy")
    return ref


# ---- study recommendations ------------------------------------------------------------------------
def _study(ctx, s, i, base):
    path = ST
    sid = _rid(ctx, "study_recommendation", s.get("identifier"), i, path + "identifier")
    exts = []
    prio = _priority(ctx, s.get("priority"), path + "priority")
    if prio:
        exts.append(prio)
    ev = _evidence_cc(ctx, s.get("evidenceLevel"), s.get("evidenceLevelDetails"), path)
    if ev:
        # mii-ex-mtb-empfehlung-evidenzgraduierung has no ServiceRequest context (ballot): local extension
        exts.append(ext(EX_STUDY_EVIDENCE, valueCodeableConcept=ev))
        ctx.preserve(path + "evidenceLevel", "study-evidence-mvgs-extension")
        if len(ev.get("coding", [])) > 1:
            ctx.preserve(path + "evidenceLevelDetails[]", "study-evidence-mvgs-extension")

    supporting, notes = [], []
    study_ref = _research_study(ctx, s, path, notes)
    if study_ref:
        supporting.append(study_ref)
    variants = _variant_refs(ctx, s.get("variants"), path + "variants[]")
    if variants:
        # no reasonReference slice for Observations on the request (ballot): open supportingInfo
        ctx.preserve(path + "variants[]", "study-variants-supportinginfo")
    supporting += variants

    prim = _primary(ctx, path + "identifier")
    sr = _request(ctx, PR_STUDY_REQ, ("study_recommendation", sid), base, category=[STUDY_CATEGORY],
                  code=STUDY_CODE)
    sr.update({"extension": exts, "identifier": _identifier(ctx, s.get("identifier")),
               "reasonReference": [prim] if prim else [], "supportingInfo": supporting,
               "note": [{"text": n} for n in notes]})
    ref = ctx.add(sr, *([path + "identifier"] if s.get("identifier") else []))
    ctx.ids[("study_recommendation", sid)] = ref
    return ref


def _research_study(ctx, s, path, notes):
    register, number, name = s.get("register"), s.get("id"), s.get("name")
    title = _real(name)   # placeholder names (PLACEHOLDER_NAMES: 'N/A', 'unbekannt', ...) are dropped, as in rare disease
    if name and not title:
        ctx.drop(path + "name", name, "placeholder study name")
    if register == "yesButStudyIsUnknown":
        # a study is recommended but not identified: inclusion request without ResearchStudy
        ctx.cover(path + "register")
        ctx.rep("study-unknown-no-researchstudy")
        real_id = _real(number)
        if number and not real_id:
            ctx.drop(path + "id", number, "placeholder study id (register yesButStudyIsUnknown)")
        if title or real_id:
            notes.append("Empfohlene Studie (nicht identifiziert): " + " ".join(x for x in (title, real_id) if x))
            for k, v in (("name", title), ("id", real_id)):
                if v:
                    ctx.preserve(path + k, "study-unknown-note")
        _substance_notes(ctx, s, path, notes)
        return None
    ident = None
    if number:
        if register in REGISTER_SYSTEM:
            ident = {"system": REGISTER_SYSTEM[register], "value": number}
            if register == "Eudra-CT/CTIS" and re.match(r"^\d{4}-5\d{5}-\d{2}-\d{2}$", number):
                ctx.rep("ctis-number-in-eudract-system")
            ctx.cover(path + "register", path + "id")
        else:   # 'other' or unknown register: identifier without a register system
            ident = {"type": {"text": f"Studienregister: {register or 'unbekannt'}"}, "value": number}
            ctx.cover(path + "id")
            ctx.preserve(path + "register", "study-register-other")
    elif register:
        ctx.drop(path + "register", register, "register without study id")
    if not ident and not title:
        _substance_notes(ctx, s, path, notes)
        return None
    rs = ctx.new("ResearchStudy", "study", register or "", number or title, profile=PR_STUDY)
    focus = [_medication_cc(ctx, sub, path + "substances[].") for sub in as_list(s.get("substances")) if sub]
    existing = ctx.resource({"reference": f"urn:uuid:{rs['id']}"})
    if existing:   # same study recommended twice: one ResearchStudy; what differs stays on this request
        _repeated_study(ctx, existing, title, focus, path, notes)
        return {"reference": f"urn:uuid:{rs['id']}"}
    rs.update({
        "identifier": [ident] if ident else [],
        "title": title,
        # required; an MTB inclusion recommendation implies a study open for inclusion
        "status": "active",
        "focus": [c for c, _ in focus],
    })
    for _, paths in focus:
        ctx.cover(*paths)
    if title:
        ctx.cover(path + "name")
    return ctx.add(rs)


def _repeated_study(ctx, existing, title, focus, path, notes):
    """A further recommendation of a study already in the bundle: a name or substance the ResearchStudy does not
    carry becomes a note of this recommendation's own inclusion request (preserved), never silently covered."""
    how = "repeated-study-recommendation-note"
    if title and title != existing.get("title"):
        notes.append(f"Studienname laut dieser Empfehlung: {title}")
        ctx.preserve(path + "name", how)
    elif title:
        ctx.cover(path + "name")
    for concept, paths in focus:
        if not concept:
            continue
        if prune(concept) in existing.get("focus", []):
            ctx.cover(*paths)
            continue
        _substance_note(ctx, concept, paths, notes, how)


def _substance_notes(ctx, s, path, notes):
    """Substances of a study recommendation that gets no ResearchStudy (no identifiable study, so no focus to carry
    them): a note of the inclusion request (preserved) instead of a silent loss."""
    for sub in as_list(s.get("substances")):
        concept, paths = _medication_cc(ctx, sub, path + "substances[].") if sub else (None, [])
        if concept:
            _substance_note(ctx, concept, paths, notes, "study-substance-note")


def _substance_note(ctx, concept, paths, notes, how):
    code = ((concept.get("coding") or [{}])[0]).get("code")
    label = " ".join(x for x in (concept.get("text"), f"({code})" if code else None) if x)
    notes.append(f"Studiensubstanz laut dieser Empfehlung: {label}")
    for k, p in enumerate(paths):
        ctx.preserve(p, how if k == 0 else "")


# ---- interventions and preventive measures -------------------------------------------------------
def _intervention(ctx, si, i, base):
    path = SI
    t = si.get("type") or {}
    c = t.get("code") or {}
    code = cc(coding(c.get("system"), c.get("code"), c.get("display"), c.get("version")), text=t.get("name"))
    ctx.cover(*[path + "type.code." + k for k in ("code", "system", "display", "version") if c.get(k)],
              *([path + "type.name"] if t.get("name") else []))
    flag_src = (("therapeutic", "interventionIsTherapeutic"), ("riskReducing", "interventionsIsRiskReducing"))
    flags = [ext(key, valueBoolean=bool(si[src])) for key, src in flag_src if si.get(src) is not None]
    for _, src in flag_src:   # mvgs-ex-intervention-purpose needs both sub-extensions (1..1 each)
        if si.get(src) is None:
            continue
        if len(flags) == 2:
            ctx.preserve(path + src, "intervention-purpose-mvgs-extension")
        else:
            ctx.drop(path + src, si[src], "other intervention flag missing: mvgs-ex-intervention-purpose needs both")
    prim = _primary(ctx, path + "type.name")
    sr = _request(ctx, PR_OPERATION, ("intervention", i), base, code=code,
                  reasonReference=[prim] if prim else [])
    if len(flags) == 2:
        sr["extension"] = [ext(EX_PURPOSE, extension=flags)]
    return ctx.add(sr)


def _preventive(ctx, m, i, base):
    mid = _rid(ctx, "preventive_measure", m.get("identifier"), i, PM + "identifier")
    sr = ctx.new("ServiceRequest", "preventive_measure", mid)
    sr.update({"identifier": _identifier(ctx, m.get("identifier")), "status": "active", "intent": "plan",
               "category": [PREVENTIVE_CATEGORY], "code": cc(text=m.get("type")), **base})
    ref = ctx.add(sr)
    for k in ("identifier", "type"):   # no MII profile for preventive measures (REPRESENTATIONS #5)
        if m.get(k):
            ctx.preserve(PM + k, "preventive-measure-servicerequest")
    ctx.ids[("preventive_measure", mid)] = ref
    return ref
