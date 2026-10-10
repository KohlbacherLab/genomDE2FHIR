"""KDK molecular.complexBiomarkers[] -> MTB biomarker Observations (one entry may yield up to three).

Rows: molecular.complexBiomarkers[].identifier, .tmb, .ploidy, .hrdHigh, .lstHigh, .taiHigh.

- tmb     -> mii-pr-mtb-mutationslast, valueQuantity (LOINC 94076-7, UCUM 1/1000000{Base} as in the MolGen example)
- ploidy  -> mii-pr-mtb-ploidie, valueQuantity (code.coding:NCIT C18303 fixed by the profile); no interpretation
- hrdHigh -> mii-pr-mtb-hrd-score (LOINC 107286-7); the source has no numeric score, so value[x] (integer) stays
             empty and the flag goes to Observation.interpretation H/L (2027: required mii-vs-mtb-interpretation-high-low;
             2026 binds an unshipped GR value set -> flag kept as note, preserved)
- lstHigh / taiHigh -> the hrd-score's own sub-score components LST (NCIt C120466) / TAI (NCIt C129774) with
             component.interpretation H/L (extensible observation-interpretation, valid in 2026 and 2027). This replaces the
             table's "molekularer-biomarker valueBoolean with a genomDE biomarker code" (no such code exists; the hrd-score
             component slicing is closed and already defines LST/TAI).

The module also holds the helpers shared by molecular_expression and molecular_signatures.
"""
from ...systems import LOINC, MTB, SID_FINDING, TBD_GR, UCUM, V3_INTERP
from ..common import cc, coding, obs_category, scoped_id

P_TMB = MTB + "StructureDefinition/mii-pr-mtb-mutationslast"
P_PLOIDY = MTB + "StructureDefinition/mii-pr-mtb-ploidie"
P_HRD = MTB + "StructureDefinition/mii-pr-mtb-hrd-score"

# NCIt as fixed by the MTB profiles (an NCPI page URL, reported as package defect DISCUSS-TD #23); must match the pattern
NCIT_MTB = "https://nih-ncpi.github.io/ncpi-fhir-ig/CodeSystem-ncit.html"
LST_CODE = {"system": NCIT_MTB, "code": "C120466", "display": "Large-Scale State Transition"}
TAI_CODE = {"system": NCIT_MTB, "code": "C129774", "display": "Telomeric Allelic Imbalance Region"}

# Source ids of molecular findings (KDK `identifier`, unique within a submission); value "<submitterId>|<caseKey>|<id>".
# Local until systems.py carries a shared constant (core request).

BASE = "molecular.complexBiomarkers[]."


# ---- shared helpers (molecular_expression, molecular_signatures) ------------------------------------------------
def finding_identifier(ctx, value) -> dict | None:
    return scoped_id(ctx, SID_FINDING, value)


GE_CATEGORY = {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "GE"}]}


def biomarker_categories() -> list:
    """labCategory + mbCategory (slices required by the MTB biomarker profiles) + geCategory."""
    return obs_category("laboratory") + [{"coding": [{"system": TBD_GR, "code": "biomarker-category"}]}, GE_CATEGORY]


def observation(ctx, profile: str, *id_parts, code: dict, categories: list | None = None) -> dict:
    o = ctx.new("Observation", *id_parts, profile=profile)
    o["status"] = "final"
    o["category"] = categories if categories is not None else biomarker_categories()
    o["code"] = code
    o["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        o["focus"] = [ctx.refs["primary"]]
    return o


def interp(flag: bool) -> dict:
    code, display = ("H", "High") if flag else ("L", "Low")
    return {"coding": [{"system": V3_INTERP, "code": code, "display": display}]}


def register(ctx, ref: dict, source_id, primary: bool = True):
    """Collect for the NGS report; the first resource of a source entry answers ('variant', id) look-ups."""
    ctx.bag["ngs_results"].append(ref)
    if primary and source_id not in (None, "") and ("variant", source_id) not in ctx.ids:
        ctx.ids[("variant", source_id)] = ref


def unique_key(seen: set, ctx, path: str, source_id, index: int):
    """Source identifier as id part; on a duplicate within the file fall back to identifier + index (warned)."""
    if source_id in (None, "") or source_id in seen:
        if source_id not in (None, ""):
            ctx.warn(path, f"duplicate identifier {source_id!r}; id made unique with the array index {index}")
        return f"{source_id or ''}#{index}"
    seen.add(source_id)
    return source_id


# ---- builder ----------------------------------------------------------------------------------------------------
def build(ctx):
    items = (ctx.dk.get("molecular") or {}).get("complexBiomarkers") or []
    seen: set = set()
    for i, cb in enumerate(items):
        sid = cb.get("identifier")
        key = unique_key(seen, ctx, BASE + "identifier", sid, i)
        ident = finding_identifier(ctx, sid)
        emitted = []

        tmb = cb.get("tmb")
        if tmb is not None:
            o = observation(ctx, P_TMB, "complex-biomarker", key, "tmb",
                            code=cc(coding(LOINC, "94076-7", "Mutations/Megabase [# Ratio] in Tumor")))
            o["identifier"] = [ident]
            o["valueQuantity"] = {"value": tmb, "unit": "Mutations/Megabase", "system": UCUM, "code": "1/1000000{Base}"}
            if tmb > 1000:  # data quality: TMB is reported in mutations per megabase, typically < 500
                ctx.warn(BASE + "tmb", f"implausible TMB {tmb} mut/Mb (identifier {sid!r}); emitted as delivered")
            emitted.append(ctx.add(o, BASE + "tmb"))

        hrd, lst, tai = cb.get("hrdHigh"), cb.get("lstHigh"), cb.get("taiHigh")
        if any(v is not None for v in (hrd, lst, tai)):
            o = observation(ctx, P_HRD, "complex-biomarker", key, "hrd",
                            code=cc(coding(LOINC, "107286-7", "Homologous recombination deficiency status analysis "
                                                             "[Presence] in Tissue by Molecular genetics method")))
            o["identifier"] = [ident]
            paths = []
            if hrd is not None:
                if ctx.is_2027:
                    o["interpretation"] = [interp(hrd)]
                    paths.append(BASE + "hrdHigh")
                else:  # 2026: interpretation bound to GR high-low-codes-vs, which GR 3.0.0 does not ship
                    o["note"] = [{"text": f"HRD {'high' if hrd else 'not high'} (genomDE hrdHigh={str(hrd).lower()})"}]
                    ctx.preserve(BASE + "hrdHigh", "hrd-flag-note-2026")
            comps = []
            for flag, code, path in ((lst, LST_CODE, "lstHigh"), (tai, TAI_CODE, "taiHigh")):
                if flag is None:
                    continue
                comps.append({"code": {"coding": [dict(code)]}, "interpretation": [interp(flag)]})
                paths.append(BASE + path)
            o["component"] = comps
            emitted.append(ctx.add(o, *paths))

        ploidy = cb.get("ploidy")
        if ploidy is not None:
            o = observation(ctx, P_PLOIDY, "complex-biomarker", key, "ploidy",
                            code=cc(dict(system=NCIT_MTB, code="C18303", display="DNA Ploidy Analysis")))
            o["identifier"] = [ident]
            o["valueQuantity"] = {"value": ploidy}
            emitted.append(ctx.add(o, BASE + "ploidy"))

        if emitted:
            ctx.cover(BASE + "identifier")
            for n, ref in enumerate(emitted):
                register(ctx, ref, sid, primary=n == 0)
            # TMB / HRD score / ploidy fill 0..1 result slices of the NGS report: molecular_report gives every entry
            # its own report when there are several
            ctx.bag["ngs_biomarker_sets"].append((key, emitted))
        else:
            ctx.drop(BASE + "identifier", sid, "complex biomarker entry without tmb/ploidy/hrd/lst/tai values")
