"""Small, dependency-free helpers for building FHIR R4 dicts. Builders return plain dicts;
`Ctx.add()` prunes empty elements and `bundle.structural_errors()` parses them with fhir.resources."""
import re

from ..systems import ATC, DAR, FHIR_EXT, ICD10GM, OBS_CATEGORY


def coding(system: str | None, code, display: str | None = None, version: str | None = None) -> dict | None:
    if code in (None, ""):
        return None
    c = {"system": system, "code": str(code)}
    if version:
        c["version"] = str(version)
    if display:
        c["display"] = display
    return c



MEHRFACH = "http://fhir.de/StructureDefinition/icd-10-gm-mehrfachcodierungs-kennzeichen"
MEHRFACH_CS = "http://fhir.de/CodeSystem/icd-10-gm-mehrfachcodierungs-kennzeichen"


def icd10gm(code, display: str | None = None, version: str | None = None) -> dict | None:
    """ICD-10-GM Coding; a trailing multiple-coding mark (dagger/+, *, !) moves to the fhir.de extension
    (context Condition.code.coding), and a missing dot after the 3-character category is added."""
    code = str(code or "").strip().upper()
    mark = code[-1] if code and code[-1] in "†+*!" else None
    code = code.rstrip("†+*!")
    if re.fullmatch(r"[A-Z]\d{2}[0-9A-Z]{1,4}", code):
        code = code[:3] + "." + code[3:]
    c = coding(ICD10GM, code, display, version)
    if c and mark:
        c["extension"] = [{"url": MEHRFACH, "valueCoding": {"system": MEHRFACH_CS, "code": "†" if mark == "+" else mark}}]
    return c


ATC_WHO = "http://www.whocc.no/atc"
# the German ATC edition, formerly published by WIdO, now by BfArM under the fhir.de system (KDK files carry both URLs)
ATC_DE_ALIASES = {ATC, "https://www.wido.de/publikationen-produkte/analytik/arzneimittel-klassifikation/",
                  "https://www.wido.de/publikationen-produkte/analytik/arzneimittel-klassifikation"}


def atc_system(ctx, system: str | None, path: str) -> str:
    """KDK substance code system -> BfArM ATC (coding:atcClassDe) or WHO ATC (coding:atcClassEn); others pass through."""
    system = system or ATC
    if system in ATC_DE_ALIASES:
        if system != ATC:
            ctx.rep("atc-wido-system-normalised")
        return ATC
    if system.rstrip("/") == ATC_WHO:
        return ATC_WHO
    ctx.warn(path, f"substance code system {system!r} is not ATC; passed through")
    return system


def scoped_id(ctx, system: str, value) -> dict | None:
    """Sender-scoped identifier: value '<submitterId>|<caseKey>|<source id>' (docs/IDENTITY.md), components escaped
    (CaseKey.scoped); None if no value."""
    if value in (None, ""):
        return None
    return {"system": system, "value": ctx.key.scoped(value)}

def cc(*codings, text: str | None = None) -> dict | None:
    cs = [c for c in codings if c]
    if not cs and not text:
        return None
    out = {}
    if cs:
        out["coding"] = cs
    if text:
        out["text"] = text
    return out


def src_coding(src: dict | None, system: str | None = None, keep_version: bool = True) -> dict | None:
    """KDK Coding {system, version, code, display} -> FHIR Coding; `system` overrides the source system
    (profile-fixed systems), in which case the source version is dropped (it belongs to the source system)."""
    if not src or not src.get("code"):
        return None
    return coding(system or src.get("system"), src["code"], src.get("display"),
                  src.get("version") if keep_version and not system else None)


def src_cc(src: dict | None, system: str | None = None, keep_version: bool = True) -> dict | None:
    c = src_coding(src, system, keep_version)
    if not c:
        return None
    return cc(c, text=(src or {}).get("text"))


def period(start: str | None = None, end: str | None = None) -> dict | None:
    p = {}
    if start:
        p["start"] = start
    if end:
        p["end"] = end
    return p or None


def ext(url: str, **value) -> dict:
    """ext(url, valueCoding={...}) / ext(url, extension=[...])"""
    return {"url": url, **value}


def dar_ext(code: str = "unknown") -> dict:
    return {"url": FHIR_EXT + "data-absent-reason", "valueCode": code}


def dar_cc(code: str = "unknown") -> dict:
    """CodeableConcept carrying only a data-absent-reason coding (for elements with value[x] optional)."""
    return {"coding": [{"system": DAR, "code": code}]}


def obs_category(*codes: str) -> list:
    return [{"coding": [{"system": OBS_CATEGORY, "code": c}]} for c in codes]


def quantity(value, unit: str | None = None, ucum: str | None = None) -> dict | None:
    if value is None:
        return None
    q = {"value": value}
    if unit:
        q["unit"] = unit
    if ucum is not None:
        q["system"] = "http://unitsofmeasure.org"
        q["code"] = ucum
    return q


def identifier(system: str, value, type_system: str | None = None, type_code: str | None = None,
               assigner_system: str | None = None, assigner_value: str | None = None) -> dict | None:
    if value in (None, ""):
        return None
    i = {"system": system, "value": str(value)}
    if type_code:
        i["type"] = {"coding": [{"system": type_system, "code": type_code}]}
    if assigner_value:
        i["assigner"] = {"identifier": {"system": assigner_system, "value": assigner_value}}
    return i


def as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]
