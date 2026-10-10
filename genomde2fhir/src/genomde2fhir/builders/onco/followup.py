"""KDK oncology follow-up (followUp.followUpOds[]) -> Verlauf, ECOG, Vitalstatus, Tod, follow-up diagnoses,
HPO phenotypes, performed systemic therapies (Procedure + MedicationStatement), therapy responses and
preventive-measure results.

Representations (docs/REPRESENTATIONS.md, REVIEW-TD section A):
- followUpDate -> mii-pr-onko-verlauf.effectiveDateTime (focus primary tumour; no Gesamtbeurteilung is sent, value omitted)
- ECOG (#1): onco.ecog.ecog_observation (0-4 -> coding:obds + coding:loinc, unknown -> obds U, 5 / notApplicable dropped)
- vitalStatus -> MII Vitalstatus (L/T); deathDate -> Patient.deceasedDateTime + mii-pr-onko-tod (hasMember of Verlauf)
- metachroneDiagnoses (#4): 2027 additionalDiagnoses[] -> mii-pr-onko-diagnose-primaertumor with
  extension:occurredFollowing -> primary tumour; the flag itself via mvgs-ex-metachronous-tumor when not derivable;
  the code keeps its source system (onco.diagnosis.diagnosis_coding: ICD-10-GM normalised, Alpha-ID / Orphanet /
  SNOMED into their own slices; no system -> ICD-10-GM)
- therapies[] (#13): mii-pr-mtb-systemische-therapie, extension:causedBy -> therapy recommendation, outcome =
  oBDS Ende-Grund (+ MTB statusReason); one mii-pr-mtb-systemtherapie-medication-statement per substance
  (2027: basedOn:therapieempfehlung = the recommendation's MedicationRequest for the same substance). Unresolved
  reference: plan in this submission -> it is the therapy's own "new identifier" (KDK schema) ->
  Procedure.identifier, no causedBy; no plan -> logical causedBy by identifier; study recommendation ->
  Procedure.note (no conformant target)
- therapyResponse (#14): local profile mvgs-therapy-response (MTB response code, date, data source as note)
- preventiveMeasures[] (#5): result Observation (mvgs-cs-preventive-measure-result), basedOn -> preventive ServiceRequest

Ids are keyed by followUpDate (required, one follow-up per date) rather than array position so that a follow-up
submission that carries only the newest follow-up does not overwrite older ones (docs/IDENTITY.md). Follow-ups are
processed in followUpDate order (same date: array order), so the latest report sets a therapy's final state and the
death date whatever the array order; a repeated HPO code within one follow-up gets the array index appended and a
warning.

Therapy identity (therapies[], _FollowUp.therapy_ids). The ids of one follow-up's entries are decided together, from
their content and the therapies of the earlier follow-ups only, never from array position:
- (reference, therapyStartDate) identifies a therapy. Reported once per follow-up and never split: the plain id, so
  a later report updates it (latest state wins; MedicationStatements of substances reported only earlier take over
  the final state, _harmonize_medications).
- Reported in several entries by one follow-up, it is split into parts identified by their substance set: ATC code,
  else the name normalised (whitespace collapsed, lower case), sorted and joined by '+' (a '+' or '\\' inside a name
  escaped by '\\'). An entry whose set equals the set of the earlier single report continues that report's
  Procedure.
- Once split, every later entry is matched by substance identity first: equal set -> it continues that part (or the
  earlier single report). No equal set (a further split {X,Y} -> {X},{Y}, a merge {X},{Y} -> {X,Y}, a superset, a
  new substance) -> a Procedure of its own (the plain id for the follow-up's only entry of the therapy while that id
  is unused, as a submission without the splitting follow-up would give it; else the substance-keyed id), warned,
  and the earlier parts keep their state. One substance's end date, termination reason or response is therefore
  never carried over to another substance.
- Then by the remaining attributes (therapyEndDate, terminationReasonOBDS, therapyResponse, therapyResponseDate,
  therapyResponseSource): entries of one follow-up with equal substance sets and equal attributes are one report
  (warned); equal sets but different attributes are ambiguous -> each a part of its own keyed by its attributes
  (warned), and an earlier Procedure with that set keeps its state.
- A substance listed in entries with different sets in one follow-up is warned; each entry keeps its own part.
Limitation: a submission without the splitting follow-up cannot see the split, so a single report there gets the
plain id (an additional Procedure; the split parts keep their state).
"""
from collections import Counter

from ...systems import (FHIR_EXT, HPO, ICD10GM, LOINC, MTB, MVGS_SD, ONKO, PERSON, SELTENE, SID_KDK_OBJECT,
                        SNOMED)
from ...terminology import local_coding
from .diagnosis import diagnosis_coding
from .ecog import ecog_observation
from ..common import atc_system, cc, coding, obs_category, period, scoped_id

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
    # chronological order (the schema imposes none); stable, so equal dates keep array order. An undated follow-up
    # (schema-invalid) sorts first: a dated report wins over it.
    order = sorted(range(len(fus)), key=lambda k: fus[k].get("followUpDate") or "")
    death_dates = [fus[k]["deathDate"] for k in order if fus[k].get("deathDate")]
    if death_dates:
        if len(set(death_dates)) > 1:
            ctx.warn(P + "deathDate", f"conflicting death dates {sorted(set(death_dates))}; "
                                      "the one of the latest follow-up used")
        _tod(ctx, death_dates[-1])      # one Tod per patient; Verlauf.hasMember points to it
    seen = set()
    therapies = {}      # therapy id parts -> {"state": (status, start, end), "meds": [MedicationStatement id],
                        #   "names": [name-only substances of every report], "coded": names/displays reported coded,
                        #   "therapy": (reference, start), "subs": substance keys of every report}; a split part's
                        #   id has more than 3 parts
    for k in order:     # k = array index: id suffix of a second follow-up with the same date
        fu = fus[k]
        date = fu.get("followUpDate")
        key = date if date and date not in seen else f"{date}#{k}"
        seen.add(key)
        _FollowUp(ctx, fu, key, therapies).run()
        if fu.get("vitalStatus") == "deceased" or fu.get("deathDate"):
            _patient_deceased(ctx, fu.get("deathDate"))
    _harmonize_medications(ctx, therapies)


def _harmonize_medications(ctx, therapies: dict):
    """A therapy reported again by a later follow-up (same therapy id) replaces its Procedure; the
    MedicationStatements of substances reported only earlier take over the final status and period. Only an unsplit
    therapy has such substances: a split part is continued only by an entry with exactly its substances."""
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
        entries = self.fu.get("therapies") or []
        for t, tid in zip(entries, self.therapy_ids(entries)):   # ids first: from the earlier follow-ups only
            self.therapy(t, tid)
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
        # source system kept (Alpha-ID / Orphanet / SNOMED slices of the profile); only ICD-10-GM is normalised.
        # No system given: ICD-10-GM, the system the schema describes for metachronous tumours.
        code = diagnosis_coding(ctx, d if d.get("system") else {**d, "system": ICD10GM},
                                P + "additionalDiagnoses[].code")
        if not code or not str(code.get("code") or "").strip():
            # nothing left after normalisation ('ORPHA:', ' ', '+'): Condition.code is 1..1, no Condition
            for f in ("code", "date", "display", "system", "version"):
                if d.get(f):
                    ctx.drop(P + "additionalDiagnoses[]." + f, d[f], "empty code after normalisation: no Condition")
            return 0
        c = ctx.new("Condition", "followup-diagnosis", d.get("code"), d.get("date"), profile=PRIMAERTUMOR)
        exts = [{"url": ASSERTED_DATE, "valueDateTime": d["date"]}] if d.get("date") else []
        linked = 0
        if ctx.is_2027 and self.primary and flag is not False:
            # 2027 widens occurredFollowing to diagnose-primaertumor (temporal sequence, not dueTo = causal)
            exts.append({"url": OCCURRED_FOLLOWING, "valueReference": self.primary})
            linked = 1
        # no clinicalStatus: the KDK does not state it (as onco.diagnosis)
        c.update(extension=exts,
                 category=[cc(coding(SNOMED, "55342001", "Neoplastic disease"))],
                 code=cc(code), subject=ctx.patient, recordedDate=d.get("date"))
        paths = [P + "additionalDiagnoses[]." + f for f in ("code", "date", "display", "system", "version") if d.get(f)]
        ctx.add(c, *paths, replace=ctx.bundle.has(c["id"]))
        if not d.get("version"):
            label = "ICD-10-GM" if code["system"] == ICD10GM else code["system"]
            ctx.warn(P + "additionalDiagnoses[].version", f"{label} code {d['code']} without version")
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
        seen = set()
        for j, ph in enumerate(self.fu.get("phenotypes") or []):
            if not ph.get("code"):
                continue
            key = ph["code"]
            if key in seen:   # the same HPO term twice in one follow-up: both kept, the second id gets the index
                ctx.warn(P + "phenotypes[].code", f"HPO code {key!r} repeated in one follow-up; "
                                                  f"id made unique with array index {j}")
                key = f"{key}#{j}"
            seen.add(ph["code"])
            change = HPO_CHANGE.get(ph.get("change"))
            o = ctx.new("Observation", *self.id("phenotype", key), profile=HPO_ASSESSMENT)
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
    def therapy_ids(self, entries: list) -> list:
        """Procedure id parts of every therapies[] entry of this follow-up, decided together before any is built
        (rule: module docstring, 'Therapy identity'). Each id depends on the entries' content and on the therapies
        of the earlier follow-ups (self.therapies), never on array order."""
        ctx, wp = self.ctx, P + "therapies[].reference"
        groups = {}
        for i, t in enumerate(entries):
            groups.setdefault((t.get("reference"), t.get("therapyStartDate")), []).append(i)
        tids = [None] * len(entries)
        for key in sorted(groups, key=lambda k: (str(k[0]), str(k[1]))):
            idx, (reference, start) = groups[key], key
            base = ("followup-therapy", reference, start)
            earlier = {p: s["subs"] for p, s in self.therapies.items() if s["therapy"] == key}
            parts = {p: s for p, s in earlier.items() if len(p) > 3}     # split by an earlier follow-up
            if len(idx) == 1 and not parts:
                tids[idx[0]] = base         # unsplit therapy: the latest report updates it
                continue
            label, n = f"therapy {reference!r} started {start}", len(idx)
            if n > 1:
                ctx.warn(wp, f"{label} reported {'twice' if n == 2 else f'{n} times'} in one follow-up; kept apart "
                             f"by their substances")
            by_subs = {}                    # substance set -> entry indexes
            for i in idx:
                by_subs.setdefault(frozenset(_substance_keys(entries[i])), []).append(i)
            continued_base = False
            for subs in sorted(by_subs, key=_suffix):
                members, suffix = by_subs[subs], _suffix(subs)
                # 1. substance identity: the earlier single report or the part with exactly these substances; else a
                #    Procedure of its own: the plain id for a follow-up's only entry while unused (the id a submission
                #    without the splitting follow-up gives it), else the substance-keyed id
                part = (*base, suffix)
                if (base in earlier and earlier[base] == subs) or (n == 1 and part not in earlier
                                                                   and base not in earlier):
                    tid = base
                else:
                    tid = part
                # 2. remaining attributes: equal -> one report; different -> ambiguous, a part each
                variants = {_attributes(entries[i]) for i in members}
                if len(variants) > 1:
                    ctx.warn(wp, f"{label} reported {len(members)} times in one follow-up with the same substances "
                                 f"[{suffix}] but another end, termination reason or response: each kept as a "
                                 f"Procedure of its own" + ("; the earlier Procedure of these substances keeps its "
                                                            "state" if tid in earlier else ""))
                    for i in members:
                        tids[i] = (*base, suffix, *_attributes(entries[i]))
                    continue
                if len(members) > 1:
                    ctx.warn(wp, f"{label} reported {len(members)} times in one follow-up with the same substances "
                                 f"[{suffix}] and the same content: one Procedure")
                continued_base |= tid == base
                if parts and tid not in earlier:
                    overlap = sorted({_suffix(s) for s in parts.values() if s & subs})
                    ctx.warn(wp, f"{label} was split by an earlier follow-up; its substances match no single part "
                                 f"([{suffix}]{f', overlapping {overlap}' if overlap else ''}): kept as a Procedure "
                                 f"of its own, the earlier parts keep their state")
                for i in members:
                    tids[i] = tid
            if n > 1 and base in earlier and not continued_base:
                ctx.warn(wp, f"{label}: the single report of an earlier follow-up stays a Procedure of its own with "
                             f"its state")
            shared = sorted(k for k, c in Counter(k for subs in by_subs for k in subs).items() if c > 1)
            if shared:
                ctx.warn(wp, f"{label}: substance(s) {shared} listed in entries with different substances in one "
                             f"follow-up; each entry kept as a Procedure of its own")
        return tids

    def therapy(self, t: dict, tid: tuple):
        ctx = self.ctx
        tp = P + "therapies[]."
        reference, start, end = t.get("reference"), t.get("therapyStartDate"), t.get("therapyEndDate")
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
            # plan not in this submission: logical reference by the recommendation's KDK identifier, which exactly one
            # MedicationRequest carries: the only one, or a combination's first member (careplan._therapy), the same
            # target as causedBy within one submission
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
        # name-only substances of this and every earlier report of the therapy: the replacing Procedure keeps them
        # (as the MedicationStatements of substances reported only earlier are kept)
        state = self.therapies.setdefault(tid, {"meds": [], "names": [], "coded": set(), "therapy": (reference, start),
                                                "subs": set()})
        state["subs"] |= _substance_keys(t)
        for s in t.get("substances") or []:
            c = s.get("code") or {}
            if c.get("code"):
                state["coded"] |= {s.get("name"), c.get("display")} - {None}
            elif s.get("name") and _norm(s["name"]) not in map(_norm, state["names"]):
                state["names"].append(s["name"])     # one spelling per substance identity (the first reported)
        # a name reported coded by this or any earlier report has its own MedicationStatement (kept by
        # _harmonize_medications): not listed as uncoded
        names = [n for n in state["names"] if n not in state["coded"]]
        if names:
            text = "Substanzen ohne ATC-Code: " + ", ".join(names)
            note = {"text": f"{note['text']}; {text}" if note else text}
            ctx.preserve(tp + "substances[].name", "substance-name-note")
        proc.update(extension=exts, identifier=identifier, status=status, statusReason=status_reason, code=cc(DRUG_THERAPY),
                    subject=ctx.patient, performedPeriod=period(start, end),
                    reasonReference=[self.primary] if self.primary else None, outcome=outcome,
                    note=[note] if note else None)
        proc_ref = ctx.add(proc, *paths, replace=ctx.bundle.has(proc["id"]))
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
        basedon = None
        if rec and ctx.is_2027:
            ref = t.get("reference")
            own = ctx.ids.get(("therapy_recommendation_member", ref, code["code"]))
            if own:
                basedon = [own]       # the recommendation's MedicationRequest for this substance
            elif not ctx.ids.get(("therapy_recommendation_group", ref)):
                basedon = [rec]       # single-substance recommendation (e.g. substance changed): its only request
            # a substance outside a combination's members: no basedOn (the RequestGroup is no allowed target)
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


def _substance_keys(t: dict) -> set:
    """Substance identity of a therapies[] entry: ATC code, else the name with whitespace collapsed and in lower case
    (empty ones left out). What tells apart entries sharing reference + start."""
    keys = set()
    for s in t.get("substances") or []:
        if isinstance(s, dict):
            code = (s.get("code") or {}).get("code")
            keys.add(str(code) if code else _norm(s.get("name") or ""))
    return keys - {""}


def _norm(name) -> str:
    """A substance name for identity: whitespace collapsed, lower case."""
    return " ".join(str(name).split()).lower()


def _suffix(subs) -> str:
    """Id part of a split therapy: its substance keys, sorted, joined by '+' ('\\' and '+' inside a name escaped by
    '\\', so the name 'a+b' and the names 'a', 'b' give different parts)."""
    return "+".join(sorted(k.replace("\\", "\\\\").replace("+", "\\+") for k in subs))


def _attributes(t: dict) -> tuple:
    """The remaining attributes of a therapies[] entry (besides reference, start and substances)."""
    return tuple(str(t.get(f) or "") for f in ("therapyEndDate", "terminationReasonOBDS", "therapyResponse",
                                               "therapyResponseDate", "therapyResponseSource"))


def _plan_recommendations(ctx) -> bool:
    """True when this submission carries the MTB plan's systemic-therapy recommendations."""
    return bool((ctx.dk.get("plan") or {}).get("recommendedSystemicTherapies"))
