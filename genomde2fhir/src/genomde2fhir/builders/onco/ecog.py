"""KDK case.diagnosisOd.ecogPerformanceStatusScore -> mii-pr-onko-allgemeiner-leistungszustand-ecog (REPRESENTATIONS #1).

- 0-4     -> value.coding:obds (mii-cs-onko-allgemeiner-leistungszustand-ecog) + value.coding:loinc (LA9622-7 ... LA9626-8,
             the 2027 required VS mii-vs-onko-allgemeiner-leistungszustand-ecog-loinc; the 2026 slice is unbound, so the
             same codes are valid there; the 2026 ConceptMap's LA codes are wrong and not used)
- unknown -> obds code U (no LOINC answer; the dataAbsentReason route is invalid: value[x] and coding:obds are 1..1)
- 5 (dead) / notApplicable -> no representation in the MII CS (ballot candidate): no Observation, dropped with reason.
Observation.code carries SNOMED 423740007 (slice 1..1) + LOINC 89262-0; Observation.focus -> primary tumour (2027 MS).
The KDK diagnosis ECOG has no date, so effective[x] is omitted.

`ecog_observation()` is reused by onco.followup for followUps[].ecogPerformanceStatusScore (with its date).
"""
from ...systems import LOINC, ONKO, SNOMED
from ..common import cc, coding

PROFILE = ONKO + "StructureDefinition/mii-pr-onko-allgemeiner-leistungszustand-ecog"
CS_ECOG = ONKO + "CodeSystem/mii-cs-onko-allgemeiner-leistungszustand-ecog"
ECOG_CODE = cc(coding(SNOMED, "423740007", "ECOG performance status"),
               coding(LOINC, "89262-0", "ECOG Performance Status [Interpretation]"))
OBDS_DISPLAY = {"0": "Normale, uneingeschränkte Aktivität wie vor der Erkrankung (90 - 100 % nach Karnofsky)",
                "1": "Einschränkung bei körperlicher Anstrengung, aber gehfähig; leichte körperliche Arbeit bzw. Arbeit im "
                     "Sitzen (z. B. leichte Hausarbeit oder Büroarbeit) möglich (70 - 80 % nach Karnofsky)",
                "2": "Gehfähig, Selbstversorgung möglich, aber nicht arbeitsfähig; kann mehr als 50 % der Wachzeit "
                     "aufstehen (50 - 60 % nach Karnofsky)",
                "3": "Nur begrenzte Selbstversorgung möglich; ist 50 % oder mehr der Wachzeit an Bett oder Stuhl gebunden "
                     "(30  40 % nach Karnofsky)",
                "4": "Völlig pflegebedürftig, keinerlei Selbstversorgung möglich; völlig an Bett oder Stuhl gebunden "
                     "(10 - 20 % nach Karnofsky)",
                "U": "Unbekannt"}
LOINC_ANSWER = {"0": ("LA9622-7", "Fully active, able to carry on all pre-disease performance without restriction"),
                "1": ("LA9623-5", "Restricted in physically strenuous activity but ambulatory and able to carry out work "
                                  "of a light or sedentary nature, e.g., light house work, office work"),
                "2": ("LA9624-3", "Ambulatory and capable of all selfcare but unable to carry out any work activities. "
                                  "Up and about more than 50% of waking hours"),
                "3": ("LA9625-0", "Capable of only limited selfcare, confined to bed or chair more than 50% of waking hours"),
                "4": ("LA9626-8", "Completely disabled. Cannot carry on any selfcare. Totally confined to bed or chair")}
NOT_REPRESENTABLE = {"5": "ECOG 5 (dead) is not in mii-cs-onko-allgemeiner-leistungszustand-ecog (ballot, DISCUSS-TD #1)",
                     "notApplicable": "ECOG notApplicable has no code and value[x] is 1..1 (ballot, DISCUSS-TD #1)"}


def ecog_observation(ctx, score, path: str, *id_parts, effective: str | None = None) -> dict | None:
    """Add one ECOG Observation for a KDK score; returns its reference, or None when the score was dropped."""
    if score in (None, ""):
        return None
    s = "U" if str(score) == "unknown" else str(score)
    if s not in OBDS_DISPLAY:
        ctx.drop(path, score, NOT_REPRESENTABLE.get(str(score), "not an ECOG score"))
        ctx.warn(path, f"ECOG {score!r} not representable; no Observation")
        return None
    o = ctx.new("Observation", *id_parts, profile=PROFILE)
    o["status"] = "final"
    o["code"] = ECOG_CODE
    o["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        o["focus"] = [ctx.refs["primary"]]
    if effective:
        o["effectiveDateTime"] = effective
    loinc = LOINC_ANSWER.get(s)
    o["valueCodeableConcept"] = cc(coding(CS_ECOG, s, OBDS_DISPLAY[s]), coding(LOINC, *loinc) if loinc else None)
    return ctx.add(o, path)


def build(ctx):
    d = (ctx.dk.get("case") or {}).get("diagnosisOd") or {}
    ecog_observation(ctx, d.get("ecogPerformanceStatusScore"), "case.diagnosisOd.ecogPerformanceStatusScore",
                     "ecog", "diagnosis")
