"""KDK case.priorProcedures[] -> MTB prior systemic therapy (Procedure) + one MedicationStatement per substance,
plus the MTB Behandlungsepisode (ClinicalImpression) that links prior therapies and prior findings.

Rows: case.priorProcedures[].treatmentType, .intention, .therapyStartDate, .therapyEndDate, .terminationReasonOBDS,
.substances[].code.{system,code,version,display}, .substances[].name, .therapyResponse, .therapyResponseDate.

- Procedure `mii-pr-mtb-systemische-vortherapie`: treatmentType -> extension:StellungZurOp (mii-cs-onko-therapie-stellungzurop,
  codes 1:1); intention -> extension:Intention (1..1; absent -> oBDS `X` "fehlende Angabe"); start/end -> performedPeriod
  (start 1..1 in 2027); terminationReasonOBDS -> Procedure.outcome (oBDS Ende-Grund, 1:1) and statusReason:Therapiestatusgrund
  (2027: system+code 1..1) via the inverse of mii-cm-mtb-therapiestatusgrund-obds. code: the Datenkranz has no therapy type
  (Therapieart), so only the generic SNOMED 18629005 required by sct-ops-1 is emitted, no `systemische_therapie_art` coding.
- MedicationStatement `mii-pr-mtb-systemtherapie-medication-statement` per substance, partOf -> the Procedure. ATC with the
  German system (BfArM; the WIdO edition URL is normalised) -> coding:atcClassDe, WHO ATC -> coding:atcClassEn; name -> text.
  A substance with only a name has no coding (medication coding 1..*) -> kept as Procedure.note (preserved).
- therapyResponse / -Date -> Observation (REPRESENTATIONS #14: local `mvgs-therapy-response`, not mii-pr-mtb-response-befund whose
  method 1..1 RECIST/RANO is unknown) with the MTB response code, partOf -> the Procedure.
- Behandlungsepisode `mii-pr-mtb-behandlungsepisode` (ctx.refs['episode']): effectivePeriod.start = molecularBoardDecisionDate,
  problem:PrimaertumorDiagnose, supportingInfo:Vortherapie -> each Procedure; prior findings (prior_diagnostics) and later
  builders append via `episode_add()`.
"""
import re

from ...systems import MTB, MVGS_SD, ONKO, SNOMED
from ..common import atc_system, cc, coding, period

P_VORTHERAPIE = MTB + "StructureDefinition/mii-pr-mtb-systemische-vortherapie"
P_MEDSTMT = MTB + "StructureDefinition/mii-pr-mtb-systemtherapie-medication-statement"
P_EPISODE = MTB + "StructureDefinition/mii-pr-mtb-behandlungsepisode"
P_RESPONSE = MVGS_SD + "mvgs-therapy-response"      # REPRESENTATIONS #14 (local profile on core Observation)

EXT_INTENTION = ONKO + "StructureDefinition/mii-ex-onko-systemische-therapie-intention"
EXT_STELLUNG = ONKO + "StructureDefinition/mii-ex-onko-systemische-therapie-stellungzurop"
CS_INTENTION = ONKO + "CodeSystem/mii-cs-onko-intention"
CS_STELLUNG = ONKO + "CodeSystem/mii-cs-onko-therapie-stellungzurop"
CS_ENDE_GRUND = ONKO + "CodeSystem/mii-cs-onko-therapie-ende-grund"
CS_STATUSGRUND = MTB + "CodeSystem/mii-cs-mtb-therapiestatusgrund"
CS_RESPONSE = MTB + "CodeSystem/mii-cs-mtb-response-befund-beurteilung"

INTENTION = {"K": "kurativ", "P": "palliativ", "S": "Sonstiges", "X": "fehlende Angabe"}
STELLUNG = {"O": "ohne Bezug zur operativen Therapie", "A": "adjuvant", "N": "neoadjuvant", "I": "intraoperativ",
            "S": "Sonstiges"}
ENDE_GRUND = {"E": "reguläres Ende", "R": "reguläres Ende mit Dosisreduktion", "W": "reguläres Ende mit Substanzwechsel",
              "A": "Abbruch wegen Nebenwirkungen", "P": "Abbruch wegen Progress", "S": "Abbruch aus sonstigen Gründen",
              "V": "Patient verweigert weitere Therapie", "T": "Patient verstorben", "U": "unbekannt"}
# inverse of mii-cm-mtb-therapiestatusgrund-obds (MTB -> oBDS); oBDS S has three MTB sources -> the generic `other`
STATUSGRUND = {"E": ("regular-completion", "Reguläres Ende"),
               "R": ("regular-completion-with-dosage-reduction", "Reguläres Ende mit Dosisreduktion"),
               "W": ("regular-completion-with-substance-change", "Reguläres Ende mit Substanzwechsel"),
               "A": ("toxicity", "Toxizität"), "P": ("progression", "Progression"), "S": ("other", "Weitere Gründe"),
               "V": ("patient-refusal", "Therapie durch Patient abgelehnt"), "T": ("patient-death", "Tod"),
               "U": ("unknown", "Unbekannt")}
STOPPED = {"A", "P", "S", "V", "T"}     # Abbruch -> event status `stopped`
RESPONSE = {"CR": "Complete Response", "PR": "Partial Response", "SD": "Stable Disease", "PD": "Progressive Disease"}
SCT_DRUG_THERAPY = coding(SNOMED, "18629005", "Administration of drug or medicament")
SCT_THERAPEUTIC = coding(SNOMED, "277132007", "Therapeutic procedure")
SCT_RESPONSE = coding(SNOMED, "396432002", "Status of regression of tumor")
ATC_L5 = re.compile(r"^[A-Z][0-9]{2}[A-Z]{2}[0-9]{2}$")

BASE = "case.priorProcedures[]."


# ---- Behandlungsepisode (shared with prior_diagnostics and later builders) -----------------------------------------
def ensure_episode(ctx) -> dict:
    """Create the MTB Behandlungsepisode once per case and register ctx.refs['episode']."""
    if "episode" in ctx.refs:
        return ctx.refs["episode"]
    md = ctx.dk.get("metaData") or {}
    ep = ctx.new("ClinicalImpression", "episode", profile=P_EPISODE)
    ep["status"] = "completed"
    ep["subject"] = ctx.patient
    # MTB episode = the model-project case, opened by the case conference that included the patient (schema: required)
    ep["effectivePeriod"] = period(md.get("molecularBoardDecisionDate") or ctx.key.submission_date)
    ep["description"] = "MV-GenomSeq Behandlungsepisode"
    if ctx.refs.get("primary"):
        ep["problem"] = [ctx.refs["primary"]]
    ep["supportingInfo"] = list(ctx.bag.get("episode_supporting", []))
    return ctx.add(ep, name="episode")


def episode_add(ctx, ref: dict):
    """Append a reference to the episode's supportingInfo (slices Vortherapie / Vorbefund / Therapieplan are by profile)."""
    ensure_episode(ctx)
    res = ctx.bundle.entries[ctx.refs["episode"]["reference"]]["resource"]
    si = res.setdefault("supportingInfo", [])
    if ref not in si:
        si.append(ref)


# ---- prior systemic therapies ---------------------------------------------------------------------------------------
def _status(pp: dict) -> str:
    reason = pp.get("terminationReasonOBDS")
    if reason in STOPPED:
        return "stopped"
    if reason or pp.get("therapyEndDate"):
        return "completed"
    return "unknown"


def _medication(ctx, sub: dict, path_base: str) -> tuple[dict | None, list]:
    """(CodeableConcept, covered paths) for one KDK substance."""
    c = sub.get("code") or {}
    paths = []
    coding_ = None
    if c.get("code"):
        system = atc_system(ctx, c.get("system"), path_base + "code.system")
        coding_ = coding(system, c["code"], c.get("display"), c.get("version"))
        paths += [path_base + "code.code", path_base + "code.system"]
        paths += [path_base + p for p in ("code.version", "code.display") if c.get(p.split(".")[1])]
        if not ATC_L5.match(c["code"]) and not sub.get("name"):
            ctx.warn(path_base + "name", f"ATC {c['code']} is not a substance (level 5) and no name is given")
    name = sub.get("name")
    if name:
        paths.append(path_base + "name")
    if not coding_:
        return None, paths
    return cc(coding_, text=name), paths


def build(ctx):
    case = ctx.dk.get("case") or {}
    pps = case.get("priorProcedures") or []
    ensure_episode(ctx)
    for i, pp in enumerate(pps):
        _procedure(ctx, i, pp)


def _procedure(ctx, i: int, pp: dict):
    paths = []
    proc = ctx.new("Procedure", "prior_procedure", i, profile=P_VORTHERAPIE)
    ext = []
    intention = pp.get("intention")
    if intention in INTENTION:
        paths.append(BASE + "intention")
    else:
        if intention:
            ctx.warn(BASE + "intention", f"unknown intention {intention!r}; coded as X (fehlende Angabe)")
        intention = "X"          # Intention is 1..1 in the profile; oBDS X = "fehlende Angabe" is the structural catch-all
        ctx.rep("prior-therapy-intention-missing-X")
    ext.append({"url": EXT_INTENTION, "valueCodeableConcept": cc(coding(CS_INTENTION, intention, INTENTION[intention]))})
    tt = pp.get("treatmentType")
    if tt in STELLUNG:
        ext.append({"url": EXT_STELLUNG, "valueCodeableConcept": cc(coding(CS_STELLUNG, tt, STELLUNG[tt]))})
        paths.append(BASE + "treatmentType")
    elif tt:
        ctx.drop(BASE + "treatmentType", tt, "not in mii-cs-onko-therapie-stellungzurop")
    proc["extension"] = ext
    status = _status(pp)
    proc["status"] = status
    reason = pp.get("terminationReasonOBDS")
    if reason in ENDE_GRUND:
        sg_code, sg_display = STATUSGRUND[reason]
        proc["statusReason"] = cc(coding(CS_STATUSGRUND, sg_code, sg_display), text=ENDE_GRUND[reason])
        proc["outcome"] = cc(coding(CS_ENDE_GRUND, reason, ENDE_GRUND[reason]))
        paths.append(BASE + "terminationReasonOBDS")
    elif reason:
        ctx.drop(BASE + "terminationReasonOBDS", reason, "not an oBDS Ende-Grund code")
    proc["category"] = cc(SCT_THERAPEUTIC)
    proc["code"] = cc(SCT_DRUG_THERAPY, text="Systemische Vortherapie")
    proc["subject"] = ctx.patient
    proc["performedPeriod"] = period(pp.get("therapyStartDate"), pp.get("therapyEndDate"))
    paths += [BASE + p for p in ("therapyStartDate", "therapyEndDate") if pp.get(p)]
    if not pp.get("therapyStartDate"):
        ctx.warn(BASE + "therapyStartDate", "missing (required); performedPeriod.start is 1..1 in 2027")
    if ctx.refs.get("primary"):
        proc["reasonReference"] = [ctx.refs["primary"]]

    # substances: name-only entries cannot fill medication.coding 1..* -> kept as a note on the Procedure
    meds, notes = [], []
    for j, sub in enumerate(pp.get("substances") or []):
        sbase = BASE + "substances[]."
        med, spaths = _medication(ctx, sub, sbase)
        if med:
            meds.append((j, med, spaths))
        elif sub.get("name"):
            notes.append(f"Substanz (ohne Code): {sub['name']}")
            ctx.preserve(sbase + "name", "prior-therapy-substance-name-only-note")
    if notes:
        proc["note"] = [{"text": n} for n in notes]
    ref = ctx.add(proc, *paths)
    ctx.ids[("prior_procedure", i)] = ref
    episode_add(ctx, ref)

    for j, med, spaths in meds:
        ms = ctx.new("MedicationStatement", "prior_procedure", i, "substance", j, profile=P_MEDSTMT)
        ms["partOf"] = [ref]
        ms["status"] = status          # completed / stopped / unknown are valid MedicationStatement codes too
        ms["medicationCodeableConcept"] = med
        ms["subject"] = ctx.patient
        ms["effectivePeriod"] = dict(proc["performedPeriod"] or {})
        if ctx.refs.get("primary"):
            ms["reasonReference"] = [ctx.refs["primary"]]
        ctx.add(ms, *spaths)

    _response(ctx, i, pp, ref)


def _response(ctx, i: int, pp: dict, proc_ref: dict):
    resp, date = pp.get("therapyResponse"), pp.get("therapyResponseDate")
    if not resp:
        if date:
            ctx.drop(BASE + "therapyResponseDate", date, "response date without a response value")
        return
    if resp not in RESPONSE:
        ctx.drop(BASE + "therapyResponse", resp, "not in mii-cs-mtb-response-befund-beurteilung")
        return
    obs = ctx.new("Observation", "prior_procedure", i, "response", profile=P_RESPONSE)
    obs["status"] = "final"
    obs["code"] = cc(SCT_RESPONSE)
    obs["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        obs["focus"] = [ctx.refs["primary"]]
    obs["partOf"] = [proc_ref]
    obs["effectiveDateTime"] = date
    obs["valueCodeableConcept"] = cc(coding(CS_RESPONSE, resp, RESPONSE[resp]))
    ctx.add(obs)
    # local profile (no MII element: mii-pr-mtb-response-befund needs method RECIST/RANO) -> preserved, as in followup
    ctx.preserve(BASE + "therapyResponse", "mvgs-therapy-response")
    if date:
        ctx.preserve(BASE + "therapyResponseDate", "mvgs-therapy-response")
