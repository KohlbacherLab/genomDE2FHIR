"""KDK oncology follow-up (followUp.followUpOds[]) -> Verlauf, ECOG, Vitalstatus, Tod, follow-up diagnoses,
HPO phenotypes, performed systemic therapies (Procedure + MedicationStatement), therapy responses and
preventive-measure results.

Representations (docs/REPRESENTATIONS.md, REVIEW-TD section A):
- followUpDate -> mii-pr-onko-verlauf.effectiveDateTime (focus primary tumour; no Gesamtbeurteilung is sent, value omitted)
- ECOG (#1): onco.ecog.ecog_observation (0-4 -> coding:obds + coding:loinc, unknown -> obds U, 5 / notApplicable dropped)
- vitalStatus -> MII Vitalstatus (L/T); deathDate -> Patient.deceasedDateTime + mii-pr-onko-tod (hasMember of Verlauf)
- metachroneDiagnoses (#4): 2027 additionalDiagnoses[] -> mii-pr-onko-diagnose-primaertumor with
  extension:occurredFollowing -> primary tumour; the flag itself via mvgs-ex-metachronous-tumor when not derivable
- therapies[] (#13): mii-pr-mtb-systemische-therapie, extension:causedBy -> therapy recommendation, outcome =
  oBDS Ende-Grund (+ MTB statusReason); one mii-pr-mtb-systemtherapie-medication-statement per substance
  (2027: basedOn:therapieempfehlung). Unresolved reference: plan in this submission -> it is the therapy's own
  "new identifier" (KDK schema) -> Procedure.identifier, no causedBy; no plan -> logical causedBy by identifier;
  study recommendation -> Procedure.note (no conformant target)
- therapyResponse (#14): local profile mvgs-therapy-response (MTB response code, date, data source as note)
- preventiveMeasures[] (#5): result Observation (mvgs-cs-preventive-measure-result), basedOn -> preventive ServiceRequest

Ids are keyed by followUpDate (required, one follow-up per date) rather than array position so that a follow-up
submission that carries only the newest follow-up does not overwrite older ones (docs/IDENTITY.md).
"""
from ...systems import (FHIR_EXT, HPO, ICD10GM, LOINC, MTB, MVGS_SD, ONKO, PERSON, SELTENE, SID_KDK_OBJECT,
                        SNOMED)
from ...terminology import local_coding
from .ecog import ecog_observation
from ..common import atc_system, cc, coding, icd10gm, obs_category, period, scoped_id

P = "followUp.followUpOds[]."

# --- profiles ------------------------------------------------------------------------------------
VERLAUF = ONKO + "StructureDefinition/mii-pr-onko-verlauf"
TOD = ONKO + "StructureDefinition/mii-pr-onko-tod"
PRIMAERTUMOR = ONKO + "StructureDefinition/mii-pr-onko-diagnose-primaertumor"
VITALSTATUS = PERSON + "StructureDefinition/Vitalstatus"
HPO_ASSESSMENT = SELTENE + "StructureDefinition/mii-pr-seltene-hpo-assessment"
SYST_THERAPIE = MTB + "StructureDefinition/mii-pr-mtb-systemische-therapie"
MED_STATEMENT = MTB + "StructureDefinition/mii-pr-mtb-systemtherapie-medication-statement"
THERAPY_RESPONSE = MVGS_SD + "mvgs-therapy-response"
METACHRONOUS_EXT = MVGS_SD + "mvgs-ex-metachronous-tumor"

# --- code systems --------------------------------------------------------------------------------
VITALSTATUS_CS = PERSON + "CodeSystem/Vitalstatus"
VITAL_CODE = {"living": ("L", "Patient lebt"), "deceased": ("T", "Patient verstorben")}
INTENTION_EXT = ONKO + "StructureDefinition/mii-ex-onko-systemische-therapie-intention"
INTENTION_CS = ONKO + "CodeSystem/mii-cs-onko-intention"
ENDE_GRUND_CS = ONKO + "CodeSystem/mii-cs-onko-therapie-ende-grund"
STATUSGRUND_CS = MTB + "CodeSystem/mii-cs-mtb-therapiestatusgrund"
RESPONSE_CS = MTB + "CodeSystem/mii-cs-mtb-response-befund-beurteilung"
HPO_CHANGE_CS = SELTENE + "CodeSystem/mii-cs-seltene-hpo-change-status"
PM_RESULT_CS = "mvgs-cs-preventive-measure-result"
CAUSED_BY = FHIR_EXT + "procedure-causedBy"
OCCURRED_FOLLOWING = FHIR_EXT + "condition-occurredFollowing"
ASSERTED_DATE = FHIR_EXT + "condition-assertedDate"
# identifier the plan builder puts on recommendations / preventive ServiceRequests (careplan.SID_KDK_OBJECT);
# used for logical references when the plan is not part of this submission (follow-up submissions)

# oBDS SYST Ende-Grund -> MTB Therapiestatusgrund (1:1 by definition of both code systems)
ENDE_TO_STATUSGRUND = {"E": "regular-completion", "R": "regular-completion-with-dosage-reduction",
                       "W": "regular-completion-with-substance-change", "A": "toxicity", "P": "progression",
                       "S": "other", "V": "patient-refusal", "T": "patient-death", "U": "unknown"}
ABORTED = {"A", "P", "S", "V", "T"}            # Abbruch -> Procedure.status stopped
_MS_STATUS = {"completed": "completed", "stopped": "stopped"}   # Procedure status -> MedicationStatement status
HPO_CHANGE = {"newlyAdded": "newly-added", "improved": "improved", "degraded": "degraded",
              "noLongerObserved": "no-longer-observed", "unchanged": "unchanged"}
PRESENT, ABSENT = ("LA9633-4", "Present"), ("LA9634-2", "Absent")
# generic SNOMED procedure for a drug therapy: KDK sends no therapy type (systemische_therapie_art) for follow-ups
DRUG_THERAPY = coding(SNOMED, "18629005", "Administration of drug or medicament (procedure)")


def build(ctx):
    fus = (ctx.dk.get("followUp") or {}).get("followUpOds") or []
    if not fus:
        return
    death_dates = [fu["deathDate"] for fu in fus if fu.get("deathDate")]
    if death_dates:
        if len(set(death_dates)) > 1:
            ctx.warn(P + "deathDate", f"conflicting death dates {sorted(set(death_dates))}; last one used")
        _tod(ctx, death_dates[-1])      # one Tod per patient; Verlauf.hasMember points to it
    seen = set()
    therapies = {}      # therapy id parts -> {"state": (status, start, end), "meds": [MedicationStatement id]}
    for k, fu in enumerate(fus):
        date = fu.get("followUpDate")
        key = date if date and date not in seen else f"{date}#{k}"
        seen.add(key)
        _FollowUp(ctx, fu, key, therapies).run()
        if fu.get("vitalStatus") == "deceased" or fu.get("deathDate"):
            _patient_deceased(ctx, fu.get("deathDate"))
    _harmonize_medications(ctx, therapies)


def _harmonize_medications(ctx, therapies: dict):
    """A therapy reported again by a later follow-up (same reference + start date) replaces its Procedure; the
    MedicationStatements of substances reported only earlier take over the final status and period."""
    for t in therapies.values():
        status, start, end = t["state"]
        for mid in t["meds"]:
            ms = ctx.bundle.entries[f"urn:uuid:{mid}"]["resource"]
            ms["status"] = _MS_STATUS.get(status, "active")
            ms["effectivePeriod"] = period(start, end)


def _patient_deceased(ctx, death_date):
    """deathDate -> Patient.deceasedDateTime (mapping row); deceased without a date -> deceasedBoolean."""
    entry = ctx.bundle.entries.get((ctx.refs.get("patient") or {}).get("reference"))
    if not entry:
        return
    pat = entry["resource"]
    if death_date:
        pat.pop("deceasedBoolean", None)
        pat["deceasedDateTime"] = death_date
        ctx.cover(P + "deathDate")
    elif "deceasedDateTime" not in pat:
        pat["deceasedBoolean"] = True


def _tod(ctx, death_date):
    """mii-pr-onko-tod: date of death only (cause of death and tumour relation are not sent)."""
    o = ctx.new("Observation", "followup", "death", profile=TOD)
    o.update(status="final", code=cc(coding(SNOMED, "184305005")), subject=ctx.patient,
             focus=[ctx.refs["primary"]] if ctx.refs.get("primary") else None,
             effectiveDateTime=death_date)
    ctx.add(o, P + "deathDate", name="followup_death")


class _FollowUp:
    def __init__(self, ctx, fu: dict, key: str, therapies: dict):
        self.ctx, self.fu, self.key, self.therapies = ctx, fu, key, therapies
        self.date = fu.get("followUpDate")
        self.primary = ctx.refs.get("primary")
        self.flag_ext = None          # mvgs-ex-metachronous-tumor, placed on Verlauf (or Vitalstatus without primary)

    def id(self, *parts):
        return ("followup", self.key, *parts)

    def run(self):
        self.diagnoses()
        self.ecog()
        self.phenotypes()
        for t in self.fu.get("therapies") or []:
            self.therapy(t)
        for i, pm in enumerate(self.fu.get("preventiveMeasures") or []):
            self.preventive(pm, i)
        self.vitalstatus()
        self.verlauf()

    # ---- Verlauf ---------------------------------------------------------------------------------
    def verlauf(self):
        ctx = self.ctx
        if not self.primary:
            # focus 1..1 -> primary tumour: without it no conformant Verlauf; the date stays on ECOG/Vitalstatus
            # (and the metachronous flag moved to the Vitalstatus Observation)
            ctx.warn(P + "followUpDate", "no primary tumour Condition; mii-pr-onko-verlauf not emitted")
            return
        o = ctx.new("Observation", *self.id("verlauf"), profile=VERLAUF)
        o.update(extension=[self.flag_ext] if self.flag_ext else None, status="final",
                 code=cc(coding(SNOMED, "396432002", "Status of regression of tumor (observable entity)")),
                 subject=ctx.patient, focus=[self.primary], effectiveDateTime=self.date,
                 hasMember=[ctx.refs["followup_death"]]
                 if self.fu.get("deathDate") and ctx.refs.get("followup_death") else None)
        ctx.add(o, P + "followUpDate")

    # ---- metachronous diagnoses ------------------------------------------------------------------
    def diagnoses(self):
        ctx, fu = self.ctx, self.fu
        flag = fu.get("metachroneDiagnoses")
        diags = [d for d in fu.get("additionalDiagnoses") or [] if d.get("code")]
        linked = 0
        for d in diags:
            linked += self.diagnosis(d, flag)
        if flag is None:
            return
        if flag is True and linked and linked == len(diags):
            ctx.cover(P + "metachroneDiagnoses")      # derived: follow-up Conditions with occurredFollowing
            return
        if flag is False and diags:
            ctx.warn(P + "metachroneDiagnoses", "additionalDiagnoses given but metachroneDiagnoses=false")
        self.flag_ext = {"url": METACHRONOUS_EXT, "valueBoolean": bool(flag)}
        ctx.preserve(P + "metachroneDiagnoses", "mvgs-ex-metachronous-tumor")

    def diagnosis(self, d: dict, flag) -> int:
        """additionalDiagnoses[] -> mii-pr-onko-diagnose-primaertumor; returns 1 if linked via occurredFollowing."""
        ctx = self.ctx
        c = ctx.new("Condition", "followup-diagnosis", d.get("code"), d.get("date"), profile=PRIMAERTUMOR)
        icd = icd10gm(d["code"], d.get("display"), d.get("version"))
        exts = [{"url": ASSERTED_DATE, "valueDateTime": d["date"]}] if d.get("date") else []
        linked = 0
        if ctx.is_2027 and self.primary and flag is not False:
            # 2027 widens occurredFollowing to diagnose-primaertumor (temporal sequence, not dueTo = causal)
            exts.append({"url": OCCURRED_FOLLOWING, "valueReference": self.primary})
            linked = 1
        if d.get("system") and d["system"] != ICD10GM:
            ctx.warn(P + "additionalDiagnoses[].system", f"unexpected system {d['system']!r}; coded as ICD-10-GM")
        # no clinicalStatus: the KDK does not state it (as onco.diagnosis)
        c.update(extension=exts,
                 category=[cc(coding(SNOMED, "55342001", "Neoplastic disease"))],
                 code=cc(icd), subject=ctx.patient, recordedDate=d.get("date"))
        paths = [P + "additionalDiagnoses[]." + f for f in ("code", "date", "display", "system", "version") if d.get(f)]
        ctx.add(c, *paths, replace=ctx.bundle.has(c["id"]))
        if not d.get("version"):
            ctx.warn(P + "additionalDiagnoses[].version", f"ICD-10-GM code {d['code']} without version")
        return linked

    # ---- ECOG ------------------------------------------------------------------------------------
    def ecog(self):
        """Same Observation as the diagnosis ECOG (onco.ecog.ecog_observation), dated by followUpDate."""
        if ecog_observation(self.ctx, self.fu.get("ecogPerformanceStatusScore"), P + "ecogPerformanceStatusScore",
                            *self.id("ecog"), effective=self.date):
            self.ctx.cover(P + "followUpDate")

    # ---- vital status ----------------------------------------------------------------------------
    def vitalstatus(self):
        ctx, fu = self.ctx, self.fu
        vs = fu.get("vitalStatus")
        if vs not in VITAL_CODE:
            return
        code, display = VITAL_CODE[vs]
        last = fu.get("lastContactDate")
        o = ctx.new("Observation", *self.id("vitalstatus"), profile=VITALSTATUS)
        paths = [P + "vitalStatus", P + "followUpDate"]
        effective = self.date
        note = None
        if last and vs == "living":
            # the status 'living' holds as of the last contact (Vitalstatus.effective = when it was established)
            effective = last
            paths = [P + "vitalStatus", P + "lastContactDate"]
        elif last:
            note = [{"text": f"Letzter Kontakt mit dem Patienten (lastContactDate): {last}"}]
            ctx.preserve(P + "lastContactDate", "lastContactDate-note")
        o.update(status="final", category=obs_category("survey"), code=cc(coding(LOINC, "67162-8")),
                 subject=ctx.patient, effectiveDateTime=effective,
                 valueCodeableConcept=cc(coding(VITALSTATUS_CS, code, display)), note=note)
        if not self.primary and self.flag_ext:
            o["extension"] = [self.flag_ext]
        ctx.add(o, *paths)
        if vs == "living" and fu.get("deathDate"):
            ctx.warn(P + "deathDate", "deathDate given with vitalStatus=living")

    # ---- phenotypes ------------------------------------------------------------------------------
    def phenotypes(self):
        ctx = self.ctx
        for ph in self.fu.get("phenotypes") or []:
            if not ph.get("code"):
                continue
            change = HPO_CHANGE.get(ph.get("change"))
            o = ctx.new("Observation", *self.id("phenotype", ph["code"]), profile=HPO_ASSESSMENT)
            comp = None
            if change:
                present = ABSENT if change == "no-longer-observed" else PRESENT
                comp = [{"code": cc(coding(SNOMED, "260411009", "Presence findings")),
                         "valueCodeableConcept": cc(coding(LOINC, *present)),
                         "interpretation": [cc(coding(HPO_CHANGE_CS, change))]}]
            o.update(status="final", code=cc(coding(HPO, ph["code"], ph.get("display"), ph.get("version")),
                                             text=ph.get("text")),
                     subject=ctx.patient, effectiveDateTime=self.date, component=comp)
            paths = [P + "phenotypes[]." + f for f in ("code", "display", "system", "text", "version") if ph.get(f)]
            if change:
                paths.append(P + "phenotypes[].change")
            ctx.add(o, *paths)

    # ---- performed systemic therapies ------------------------------------------------------------
    def therapy(self, t: dict):
        ctx = self.ctx
        tp = P + "therapies[]."
        reference, start, end = t.get("reference"), t.get("therapyStartDate"), t.get("therapyEndDate")
        tid = ("followup-therapy", reference, start)
        reason = t.get("terminationReasonOBDS")
        if reason in ABORTED:
            status = "stopped"
        elif end or reason:
            status = "completed"
        else:
            status = "in-progress"
        rec = ctx.ids.get(("therapy_recommendation", reference)) if reference else None
        exts = [{"url": INTENTION_EXT,   # Intention 1..1; KDK follow-ups carry none -> oBDS X 'fehlende Angabe'
                 "valueCodeableConcept": cc(coding(INTENTION_CS, "X"))}]
        paths = [tp + "therapyStartDate"] + ([tp + "therapyEndDate"] if end else [])
        note = identifier = None
        study = ctx.ids.get(("study_recommendation", reference)) if reference and not rec else None
        if rec:
            exts.append({"url": CAUSED_BY, "valueReference": rec})
            paths.append(tp + "reference")
        elif study:
            # causedBy admits only MedicationRequest; a study-based therapy has no conformant link (#13 ballot)
            note = {"text": f"Bezug: Studienempfehlung {reference}"}
            ctx.preserve(tp + "reference", "therapy-study-reference-note")
            ctx.warn(tp + "reference", f"study recommendation {reference}: no conformant causedBy target")
        elif reference and _plan_recommendations(ctx):
            # the plan of this submission does not recommend it: per KDK schema the reference is then a new
            # identifier of the therapy itself ("new identifier for future reference") -> no causedBy
            identifier = [scoped_id(ctx, SID_KDK_OBJECT, reference)]
            ctx.preserve(tp + "reference", "therapy-own-identifier")
            ctx.warn(tp + "reference", f"{reference} is no recommendation of this plan; kept as Procedure.identifier")
        elif reference:
            # plan not in this submission: logical reference by the recommendation's KDK identifier
            exts.append({"url": CAUSED_BY, "valueReference": {
                "type": "MedicationRequest", "identifier": scoped_id(ctx, SID_KDK_OBJECT, reference)}})
            paths.append(tp + "reference")
            ctx.rep("therapy-recommendation-logical-reference")
        proc = ctx.new("Procedure", *tid, profile=SYST_THERAPIE)
        outcome = status_reason = None
        if reason:
            outcome = cc(coding(ENDE_GRUND_CS, reason))
            status_reason = cc(coding(STATUSGRUND_CS, ENDE_TO_STATUSGRUND.get(reason)))
            paths.append(tp + "terminationReasonOBDS")
        names = []
        for s in t.get("substances") or []:
            if not (s.get("code") or {}).get("code") and s.get("name"):
                names.append(s["name"])
        if names:
            text = "Substanzen ohne ATC-Code: " + ", ".join(names)
            note = {"text": f"{note['text']}; {text}" if note else text}
            ctx.preserve(tp + "substances[].name", "substance-name-note")
        proc.update(extension=exts, identifier=identifier, status=status, statusReason=status_reason, code=cc(DRUG_THERAPY),
                    subject=ctx.patient, performedPeriod=period(start, end),
                    reasonReference=[self.primary] if self.primary else None, outcome=outcome,
                    note=[note] if note else None)
        proc_ref = ctx.add(proc, *paths, replace=ctx.bundle.has(proc["id"]))
        state = self.therapies.setdefault(tid, {"meds": []})
        state["state"] = (status, start, end)
        for s in t.get("substances") or []:
            mid = self.medication(t, s, tid, proc_ref, rec, status)
            if mid and mid not in state["meds"]:
                state["meds"].append(mid)
        if t.get("therapyResponse"):
            self.response(t, tid, proc_ref)
        else:
            for f in ("therapyResponseDate", "therapyResponseSource"):
                if t.get(f):
                    ctx.drop(tp + f, t[f], "therapy response date/source without a response")

    def medication(self, t, s, tid, proc_ref, rec, proc_status):
        ctx = self.ctx
        sp = P + "therapies[].substances[]."
        code = s.get("code") or {}
        if not code.get("code"):
            return None                 # name-only substance: kept as Procedure.note (coding 1..* required)
        system = atc_system(ctx, code.get("system"), sp + "code.system")
        ms = ctx.new("MedicationStatement", *tid, "substance", code["code"], profile=MED_STATEMENT)
        basedon = [rec] if rec and ctx.is_2027 else None
        ms.update(basedOn=basedon,
                  partOf=[proc_ref],
                  status=_MS_STATUS.get(proc_status, "active"),
                  medicationCodeableConcept=cc(coding(system, code["code"], code.get("display"), code.get("version")),
                                               text=s.get("name")),
                  subject=ctx.patient,
                  effectivePeriod=period(t.get("therapyStartDate"), t.get("therapyEndDate")))
        paths = [sp + "code." + f for f in ("code", "display", "system", "version") if code.get(f)]
        if s.get("name"):
            paths.append(sp + "name")
        if basedon:
            paths.append(P + "therapies[].reference")
        ctx.add(ms, *paths, replace=ctx.bundle.has(ms["id"]))
        return ms["id"]

    def response(self, t, tid, proc_ref):
        """#14: local profile mvgs-therapy-response (mii-pr-mtb-response-befund needs method RECIST/RANO)."""
        ctx = self.ctx
        tp = P + "therapies[]."
        rdate = t.get("therapyResponseDate")
        o = ctx.new("Observation", *tid, "response", rdate or self.date, profile=THERAPY_RESPONSE)
        src = t.get("therapyResponseSource")
        o.update(status="final", partOf=[proc_ref], code=cc(coding(SNOMED, "396432002")),
                 subject=ctx.patient, focus=[self.primary] if self.primary else None,
                 effectiveDateTime=rdate or self.date,
                 valueCodeableConcept=cc(coding(RESPONSE_CS, t["therapyResponse"])),
                 note=[{"text": f"Datenquelle: {src}"}] if src else None)
        ctx.add(o, replace=ctx.bundle.has(o["id"]))
        ctx.preserve(tp + "therapyResponse", "mvgs-therapy-response")
        if rdate:
            ctx.preserve(tp + "therapyResponseDate", "mvgs-therapy-response")
        if src:
            ctx.preserve(tp + "therapyResponseSource", "mvgs-therapy-response")

    # ---- preventive measures ---------------------------------------------------------------------
    def preventive(self, pm: dict, i: int):
        """#5: result Observation; basedOn -> preventive ServiceRequest of the plan (ctx.ids preventive_measure)."""
        ctx = self.ctx
        pp = P + "preventiveMeasures[]."
        reference, result = pm.get("reference"), pm.get("preventiveMeasureResult")
        value = local_coding(PM_RESULT_CS, result) if result else None
        if not value:
            ctx.drop(pp + "preventiveMeasureResult", result, "no result code")
            return
        o = ctx.new("Observation", "preventive-measure-result", reference or self.key, pm.get("preventiveMeasureDate") or i)
        sr = ctx.ids.get(("preventive_measure", reference)) if reference else None
        if reference and not sr:      # plan not in this submission: logical reference by KDK identifier
            sr = {"type": "ServiceRequest", "identifier": scoped_id(ctx, SID_KDK_OBJECT, reference)}
        o.update(basedOn=[sr] if sr else None,
                 status="final",
                 code=cc(local_coding(PM_RESULT_CS, "preventive-measure-result")),
                 subject=ctx.patient, effectiveDateTime=pm.get("preventiveMeasureDate"),
                 method=cc(text=pm.get("type")), valueCodeableConcept=cc(value))
        ctx.add(o, replace=ctx.bundle.has(o["id"]))
        for f in ("preventiveMeasureDate", "preventiveMeasureResult", "reference", "type"):
            if pm.get(f):
                ctx.preserve(pp + f, "mvgs-preventive-measure-result")


def _plan_recommendations(ctx) -> bool:
    """True when this submission carries the MTB plan's systemic-therapy recommendations."""
    return bool((ctx.dk.get("plan") or {}).get("recommendedSystemicTherapies"))
