"""KDK rare-disease follow-ups (followUp.followUpRds[]) -> follow-up resources per visit.

Per follow-up k (effective = followUpDate):
- ClinicalImpression `mii-pr-seltene-clinical-impression`: summary = diseaseProgression, problem -> rd_diagnosis;
  diagnosisEstablished = true -> finding.itemReference -> rd_diagnosis (the assessment's finding is the
  established diagnosis); otherwise (false, or no diagnosis Condition) the flag is kept as `note`. The latest
  follow-up's flag is also reconciled with the diagnosis Condition's verificationStatus (row: "established iff
  verificationStatus != unconfirmed; do NOT overwrite provisional/partial/confirmed"): an unconfirmed (or absent)
  status is raised to confirmed when the flag is true; any other disagreement is only reported.
- phenotypes[] -> `mii-pr-seltene-hpo-assessment` per phenotype: HPO code (system normalised to the HPO lock),
  component:status Present (Absent for noLongerObserved) with interpretation from
  `mii-cs-seltene-hpo-change-status`.
- gmfcs -> generic survey Observation, code SNOMED 707621005, value LOINC LL1594-2 answers (DISCUSS-TD #32,
  HDB-975 pending; same coding as the diagnosis GMFCS) -> preserved.
- vitalStatus -> `Vitalstatus` Observation (LOINC 67162-8, MII Vitalstatus CS L/T).
- deathDate -> Patient.deceasedDateTime (YYYY-MM is a valid dateTime); deceased without date -> deceasedBoolean.
  A deathDate before symptom onset, the MV consent or a board decision is kept, with a data-quality warning.

Ids are keyed by followUpDate (required; index appended only for a repeated date), not by array position, so a
follow-up submission carrying only the newest follow-up does not overwrite older ones (docs/IDENTITY.md, as
onco.followup); phenotype assessments keep their index within the follow-up.
"""
from ...systems import COND_VER, HPO, LOINC, PERSON, SELTENE, SNOMED
from ..common import cc, coding, obs_category

P_IMPRESSION = SELTENE + "StructureDefinition/mii-pr-seltene-clinical-impression"
P_HPO = SELTENE + "StructureDefinition/mii-pr-seltene-hpo-assessment"
P_VITAL = PERSON + "StructureDefinition/Vitalstatus"
CS_VITAL = PERSON + "CodeSystem/Vitalstatus"
CS_HPO_CHANGE = SELTENE + "CodeSystem/mii-cs-seltene-hpo-change-status"

VITAL = {"living": ("L", "Patient lebt"), "deceased": ("T", "Patient verstorben")}
HPO_CHANGE = {  # KDK change -> (change-status code, display, present?)
    "newlyAdded": ("newly-added", "Neu hinzugefügt", True),
    "improved": ("improved", "Verbessert", True),
    "degraded": ("degraded", "Verschlechtert", True),
    "noLongerObserved": ("no-longer-observed", "Nicht mehr beobachtet", False),
    "unchanged": ("unchanged", "Unverändert", True),
}
PRESENCE_CODE = {"coding": [{"system": SNOMED, "code": "260411009", "display": "Presence findings"}]}
PRESENT = {"coding": [{"system": LOINC, "code": "LA9633-4", "display": "Present"}]}
ABSENT = {"coding": [{"system": LOINC, "code": "LA9634-2", "display": "Absent"}]}
HPO_ALIASES = {None, "", HPO, "https://hpo.jax.org", "http://hpo.jax.org", "https://hpo.jax.org/",
               "http://purl.obolibrary.org/obo/hp.owl", "http://www.human-phenotype-ontology.org"}

# DISCUSS-TD #32: SNOMED 707621005 (age-independent) + LOINC answer list LL1594-2 (verified on tx.fhir.org);
# identical to the diagnosis GMFCS of rd.diagnosis (code, value coding, text)
GMFCS_CODE = {"coding": [{"system": SNOMED, "code": "707621005",
                          "display": "Gross motor function classification system for cerebral palsy"}]}
GMFCS_LEVEL = {"I": "LA16552-4", "II": "LA15151-6", "III": "LA15150-8", "IV": "LA16556-5", "V": "LA16558-1"}
PFX = "followUp.followUpRds[]."


def _hpo(ctx, k: str, j: int, ph: dict, date):
    p = PFX + "phenotypes[]."
    system = ph.get("system")
    if system in HPO_ALIASES or str(ph.get("code", "")).startswith("HP:"):
        if system not in (None, HPO):
            ctx.rep("hpo-system-normalised")
        system = HPO
    else:
        ctx.warn(p + "system", f"non-HPO phenotype system kept: {system!r}")
    paths = [p + "code"] + [p + f for f in ("system", "display", "version", "text") if ph.get(f)]
    change = ph.get("change")
    comp = {"code": PRESENCE_CODE}
    if change in HPO_CHANGE:
        code, display, present = HPO_CHANGE[change]
        comp["valueCodeableConcept"] = PRESENT if present else ABSENT
        comp["interpretation"] = [cc(coding(CS_HPO_CHANGE, code, display))]
        paths.append(p + "change")
    elif change:
        ctx.drop(p + "change", change, "unknown phenotype change")
    obs = ctx.new("Observation", "followup", k, "hpo", j, profile=P_HPO)
    obs.update(
        status="final",
        code=cc(coding(system, ph.get("code"), ph.get("display"), ph.get("version")), text=ph.get("text")),
        subject=dict(ctx.patient), effectiveDateTime=date, component=[comp],
        # the status change refers to the baseline assessment of the same phenotype (rd.diagnosis)
        derivedFrom=[dict(base)] if (base := ctx.ids.get(("rd_phenotype", ph.get("code")))) else [],
    )
    ctx.add(obs, *paths)


def _gmfcs(ctx, k: str, level, date):
    if level not in GMFCS_LEVEL:
        ctx.drop(PFX + "gmfcs", level, "unknown GMFCS level")
        return
    obs = ctx.new("Observation", "followup", k, "gmfcs")
    obs.update(
        status="final", category=obs_category("survey"), code=GMFCS_CODE,
        subject=dict(ctx.patient), effectiveDateTime=date,
        valueCodeableConcept=cc(coding(LOINC, GMFCS_LEVEL[level]), text=f"GMFCS level {level}"),
    )
    ctx.add(obs)
    ctx.preserve(PFX + "gmfcs", "gmfcs-generic-observation")


def _vital(ctx, k: str, status, date):
    if status not in VITAL:
        ctx.drop(PFX + "vitalStatus", status, "unknown vital status")
        return
    code, display = VITAL[status]
    obs = ctx.new("Observation", "followup", k, "vitalstatus", profile=P_VITAL)
    obs.update(
        status="final", category=obs_category("survey"),
        code={"coding": [{"system": LOINC, "code": "67162-8"}]},
        subject=dict(ctx.patient), effectiveDateTime=date,
        valueCodeableConcept={"coding": [{"system": CS_VITAL, "code": code, "display": display}]},
    )
    ctx.add(obs, PFX + "vitalStatus")


def _resource(ctx, ref):
    e = ctx.bundle.entries.get((ref or {}).get("reference"))
    return e["resource"] if e else None


def _reconcile_diagnosis(ctx, established: bool):
    """Latest follow-up flag vs the diagnosis Condition (row DERIVED rule)."""
    path = PFX + "diagnosisEstablished"
    cond = _resource(ctx, ctx.refs.get("rd_diagnosis"))
    if cond is None:
        return
    codes = [c.get("code") for c in (cond.get("verificationStatus") or {}).get("coding", [])]
    current = codes[0] if codes else None
    if established and current in (None, "unconfirmed"):
        cond["verificationStatus"] = {"coding": [{"system": COND_VER, "code": "confirmed"}],
                                      "text": "Diagnosis established (latest follow-up)"}
        ctx.warn(path, f"diagnosis verificationStatus {current or '(none)'} -> confirmed (latest follow-up: established)")
    elif not established and current in ("confirmed", "provisional", "differential"):
        ctx.warn(path, f"latest follow-up says not established, diagnosis is {current}; not overwritten")
    elif not established and current is None:
        cond["verificationStatus"] = {"coding": [{"system": COND_VER, "code": "unconfirmed"}]}


def _impression(ctx, k: str, fu: dict, date):
    dx = ctx.refs.get("rd_diagnosis")
    est = fu.get("diagnosisEstablished")
    paths, finding, notes = [], [], []
    if isinstance(est, bool):
        # true + diagnosis Condition -> finding (the established diagnosis); otherwise the flag as a note, so a
        # 'false' of an earlier follow-up (only the latest one is reconciled with the Condition) is not lost
        paths.append(PFX + "diagnosisEstablished")
        if est and dx:
            finding = [{"itemReference": dict(dx), "basis": "Diagnose gesichert (Follow-up)"}]
        else:
            notes = [{"text": "Diagnose gesichert (Follow-up)" if est else "Diagnose nicht gesichert (Follow-up)"}]
    if fu.get("diseaseProgression"):
        paths.append(PFX + "diseaseProgression")
    if not paths:
        return
    ci = ctx.new("ClinicalImpression", "followup", k, "impression", profile=P_IMPRESSION)
    ci.update(
        status="completed",
        description="MV-GenomSeq Follow-up",
        subject=dict(ctx.patient), effectiveDateTime=date, date=date,
        problem=[dict(dx)] if dx else [],
        summary=fu.get("diseaseProgression"),
        finding=finding,
        note=notes,
    )
    ctx.add(ci, *paths)


def _check_death_date(ctx, death: str):
    """Data-quality check: a death before symptom onset, the MV consent or a board decision contradicts the case
    (e.g. a generator deriving deathDate from birthDate). The value is kept; only a warning is issued."""
    dk = ctx.dk
    meta, dx = dk.get("metaData") or {}, (dk.get("case") or {}).get("diagnosisRd") or {}
    consent = meta.get("mvConsent") or {}
    later = [("case.diagnosisRd.symptomOnsetDate", dx.get("symptomOnsetDate")),
             ("metaData.mvConsent.presentationDate", consent.get("presentationDate")),
             *(("metaData.mvConsent.scope[].date", s.get("date")) for s in consent.get("scope") or []
               if isinstance(s, dict)),
             ("metaData.molecularBoardDecisionDate", meta.get("molecularBoardDecisionDate")),
             ("case.diagnosisRd.molecularBoardDecisionDate", dx.get("molecularBoardDecisionDate")),
             ("plan.carePlanRd.molecularBoardDecisionDate",
              ((dk.get("plan") or {}).get("carePlanRd") or {}).get("molecularBoardDecisionDate"))]
    # de-duplicated: consent scopes usually share one date
    for path, d in dict.fromkeys((p, d) for p, d in later if isinstance(d, str) and d):
        n = min(len(d), len(death))      # compare at the coarser precision (YYYY-MM vs YYYY-MM-DD)
        if death[:n] < d[:n]:
            ctx.warn(PFX + "deathDate", f"data quality: deathDate {death} is before {path} {d}; value kept")


def build(ctx):
    fus = (ctx.dk.get("followUp") or {}).get("followUpRds") or []
    if not fus:
        return
    latest = None
    death_date, deceased = None, False
    seen = set()
    for i, fu in enumerate(fus):
        date = fu.get("followUpDate")
        if date:
            ctx.cover(PFX + "followUpDate")
        if latest is None or (date or "") >= (fus[latest].get("followUpDate") or ""):
            latest = i
        key = date if date and date not in seen else f"{date}#{i}"   # id key (docs/IDENTITY.md)
        if date in seen:
            ctx.warn(PFX + "followUpDate", f"two follow-ups dated {date}; the later one keyed by its index")
        seen.add(date)
        _impression(ctx, key, fu, date)
        for j, ph in enumerate(fu.get("phenotypes") or []):
            if ph.get("code"):
                _hpo(ctx, key, j, ph, date)
            else:
                ctx.drop(PFX + "phenotypes[].code", ph, "phenotype without code")
        if fu.get("gmfcs"):
            _gmfcs(ctx, key, fu["gmfcs"], date)
        if fu.get("vitalStatus"):
            _vital(ctx, key, fu["vitalStatus"], date)
            deceased = deceased or fu["vitalStatus"] == "deceased"
        if fu.get("deathDate"):
            if fu.get("vitalStatus") != "deceased":
                ctx.warn(PFX + "deathDate", f"deathDate with vitalStatus {fu.get('vitalStatus')!r}")
            death_date = max(death_date or "", fu["deathDate"])

    if isinstance(fus[latest].get("diagnosisEstablished"), bool):
        _reconcile_diagnosis(ctx, fus[latest]["diagnosisEstablished"])
    if death_date:
        _check_death_date(ctx, death_date)

    pat = _resource(ctx, ctx.refs.get("patient"))
    if pat is not None and (death_date or deceased):
        pat.pop("deceasedBoolean", None)
        pat.pop("deceasedDateTime", None)
        if death_date:
            pat["deceasedDateTime"] = death_date
            ctx.cover(PFX + "deathDate")
        else:
            pat["deceasedBoolean"] = True
