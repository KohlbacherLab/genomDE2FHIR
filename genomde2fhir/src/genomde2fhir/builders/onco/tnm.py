"""KDK case.diagnosisOd.tnmClassifications[] -> MII Onko TNM (REPRESENTATIONS #2, DISCUSS-TD #2, REVIEW-TD A "TNM").

Each KDK item is one T, N or M category (SNOMED CT qualifier value per schema; many senders put UICC strings such as
"T3" with system "UICC" instead):
- category Observation mii-pr-onko-tnm-{t,n,m}-kategorie: `value.coding:uicc` (1..1) from ConceptMap
  mvgs-cm-tnm-sct-uicc (group 1: inverse of the MII uicc->sct maps, c/p prefix as `product`; group 2: accepted UICC
  strings, warned when they sit in a SNOMED-labelled field); 2027 only: the KDK SNOMED code in `coding:snomed-ct` with the
  MII (FSN) display, which satisfies invariant tnm-sct-uicc-konsistenz ("<prefix><UICC> "); KDK text/display ->
  value.text. c/p/u prefix -> `code.extension:cpPraefix` and the cT/pT/T observable code; y/r/a -> 2027:
  modifierExtension mii-ex-onko-tnm-{y,r,a}-praefix; 2026 (no such extension): one mii-pr-onko-tnm-{y,r,a}-symbol
  Observation per prefix letter, member of the grouping (the 2026 grouping lists them as hasMember targets).
  The coding:uicc display is the display of the mii-cs-onko-tnm-uicc concept (N1mi -> 'N1(mi)', NX -> 'Nx').
  2026: UICC 9th-edition codes absent from the 2026 value sets (T1b3, M1c1, M1c2) take the weitere-klassifikationen
  text fallback (warned).
- `version`: for UICC strings it is the TNM edition -> Observation.method mii-cs-onko-tnm-version; only explicit edition
  numbers 1-9 are read ('8', '8th ed.', 'UICC 8', 'TNM8', '8. Auflage'); dates, years or SNOMED release labels are
  dropped (warned). For SNOMED items it is the SNOMED release, kept as coding:snomed-ct.version only when it is a SNOMED
  version URI (else dropped).
- grouping Observation mii-pr-onko-tnm-klassifikation with hasMember -> categories; code clinical 399537006 /
  pathological 399588009 when all prefixes agree, else 399390009; no stage value and no date (not in the KDK).
- items without a UICC equivalent (e.g. AJCC SNOMED codes, codes whose SNOMED concept is no UICC category) ->
  mii-pr-onko-weitere-klassifikationen with code.text "TNM", value = the KDK coding + notation (preserved).
"""
import re

from ... import terminology
from ...systems import LOINC, ONKO, SNOMED, UICC
from ..common import as_list, cc, coding, ext
from .diagnosis import weitere_klassifikation

P_GROUP = ONKO + "StructureDefinition/mii-pr-onko-tnm-klassifikation"
P_CATEGORY = {ax: ONKO + f"StructureDefinition/mii-pr-onko-tnm-{ax.lower()}-kategorie" for ax in "TNM"}
EXT_CP = ONKO + "StructureDefinition/mii-ex-onko-tnm-cp-praefix"
EXT_YRA = {p: ONKO + f"StructureDefinition/mii-ex-onko-tnm-{p}-praefix" for p in "yra"}
P_SYMBOL = {p: ONKO + f"StructureDefinition/mii-pr-onko-tnm-{p}-symbol" for p in "yra"}   # 2026 y/r/a representation
# code / value patterns of the 2026.0.3 symbol profiles (value displays = MII ConceptMaps uicc-sct)
SYMBOL_CODE = {
    "y": ("101658-3", "421755005", "Tumor staging descriptor y (tumor staging)"),
    "r": ("101659-1", "421188008", "Tumor staging descriptor r (tumor staging)"),
    "a": ("101660-9", "421426001", "Tumor staging descriptor a (tumor staging)"),
}
# mii-cs-onko-tnm-uicc concepts whose display differs from the code (identical in 2026.0.3 and 2027.0.0-ballot.1;
# every other T/N/M category code has display == code); checked against the package in test_fix_onco_mol
UICC_DISPLAY = {"NX": "Nx", "N1mi": "N1(mi)"}
# UICC 9th-edition codes of mvgs-cm-tnm-sct-uicc that onkologie 2026.0.3 lacks (CodeSystem and
# mii-vs-onko-tnm-{t,n,m}-kategorie-werte, required binding in 2026); 2027.0.0-ballot.1 has them
UICC_NOT_IN_2026 = {"T1b3", "M1c1", "M1c2"}
CS_TNM_VERSION = ONKO + "CodeSystem/mii-cs-onko-tnm-version"
CM = "mvgs-cm-tnm-sct-uicc"

# observable codes (mii-vs-onko-tnm-{t,n,m}-kategorie) by axis and c/p prefix
CATEGORY_CODE = {
    ("T", ""): ("78873005", "T category"), ("T", "c"): ("399504009", "cT category"), ("T", "p"): ("384625004", "pT category"),
    ("N", ""): ("277206009", "N category"), ("N", "c"): ("399534004", "cN category"), ("N", "p"): ("371494008", "pN category"),
    ("M", ""): ("277208005", "M category"), ("M", "c"): ("399387003", "cM category"), ("M", "p"): ("371497001", "pM category"),
}
GROUP_CODE = {"c": ("399537006", "Clinical TNM stage grouping"), "p": ("399588009", "Pathologic TNM stage grouping"),
              "": ("399390009", "TNM stage grouping")}
NOTATION = re.compile(r"^(?P<yra>[yra]*)(?P<cp>[cpu]?)(?P<cat>[TNM].*)$")
SCT_VERSION = re.compile(r"^http://snomed\.info/sct/\d+(/version/\d{8})?$")
P = "case.diagnosisOd.tnmClassifications[]."


def _maps():
    """(sct -> (uicc, cp, sct display), set of accepted UICC strings) from the local ConceptMap."""
    sct, uicc = {}, set()
    for g in terminology.concept_map(CM).get("group", []):
        for e in g.get("element", []):
            for t in e.get("target", []):
                if not t.get("code") or t.get("equivalence") == "unmatched":
                    continue
                if g.get("source") == SNOMED:
                    cp = next((pr.get("value") for pr in t.get("product", []) if pr.get("property") == EXT_CP), "")
                    sct[e["code"]] = (t["code"], cp, e.get("display"))
                else:
                    uicc.add(t["code"])
    return sct, uicc


EDITION = re.compile(r"(?:(?:UICC|TNM)[\s-]*)?([1-9])\s*(?:\.|st|nd|rd|th)?\s*(?:ed\.?|edition|aufl\.?|auflage)?",
                     re.I)


def _edition(version) -> str | None:
    """Explicit TNM edition number 1-9 (mii-cs-onko-tnm-version) or None: dates, years and release labels are no
    edition ('2017', '2025-03-01' used to yield '2')."""
    m = EDITION.fullmatch(str(version or "").strip())
    return m[1] if m else None


def uicc_coding(code: str) -> dict:
    return coding(UICC, code, UICC_DISPLAY.get(code, code))


def build(ctx):
    items = as_list(((ctx.dk.get("case") or {}).get("diagnosisOd") or {}).get("tnmClassifications"))
    if not items:
        return
    sct_map, uicc_codes = _maps()
    members, prefixes, editions, symbols = [], [], set(), []
    for i, it in enumerate(items):
        code, system = str((it or {}).get("code") or "").strip(), it.get("system")
        if not code:
            continue
        notation = (it.get("text") or it.get("display") or "").strip()
        m = NOTATION.match(notation)
        yra, cp = (m["yra"], m["cp"]) if m else ("", "")
        sct = None
        if system == SNOMED and code in sct_map:
            uicc, cp_map, sct_display = sct_map[code]
            if cp and cp != cp_map:
                ctx.warn(P + "text", f"prefix {cp!r} of {notation!r} contradicts SNOMED {code} ({cp_map}); SNOMED wins")
            cp = cp_map
            sct = (code, sct_display)
        elif code in uicc_codes:
            uicc = code
            if system == SNOMED:
                ctx.warn(P + "code", f"UICC string {code!r} in a SNOMED-labelled code field; accepted as UICC")
        else:
            _unmatched(ctx, i, it, notation)
            continue
        if not ctx.is_2027 and uicc in UICC_NOT_IN_2026:
            _unmatched(ctx, i, it, notation, f"UICC {uicc} (9th edition) is not in the 2026 TNM value sets "
                                             f"(required binding); kept as weitere-klassifikationen text", uicc=uicc)
            continue
        axis = uicc[0]
        o = ctx.new("Observation", "tnm", i, profile=P_CATEGORY[axis])
        paths = [P + "code", P + "system"]
        o["status"] = "final"
        o["code"] = cc(coding(SNOMED, *CATEGORY_CODE[(axis, cp if cp in "cp" else "")]))
        if cp:
            o["code"]["extension"] = [ext(EXT_CP, valueCodeableConcept=cc(coding(UICC, cp, cp)))]
        if yra:
            if ctx.is_2027:
                o["modifierExtension"] = [ext(EXT_YRA[p], valueCodeableConcept=cc(coding(UICC, p, p))) for p in yra]
            else:  # 2026: no prefix extension; the grouping gets mii-pr-onko-tnm-{y,r,a}-symbol members (below)
                symbols += [p for p in yra if p not in symbols]
        o["subject"] = ctx.patient
        if ctx.refs.get("primary"):
            o["focus"] = [ctx.refs["primary"]]
        value = [uicc_coding(uicc)]
        version = it.get("version")
        if sct and ctx.is_2027:
            v = version if version and SCT_VERSION.match(str(version)) else None
            value.append(coding(SNOMED, sct[0], sct[1], v))
            if v:
                paths.append(P + "version")
            elif version:
                ctx.drop(P + "version", version, "SNOMED release label is not a SNOMED version URI")
        elif sct and version:
            ctx.drop(P + "version", version, "SNOMED coding not emitted against the 2026 profiles (UICC only)")
        elif version:  # UICC string: the version is the TNM edition
            ed = _edition(version)
            if ed:
                o["method"] = cc(coding(CS_TNM_VERSION, ed, f"{ed}. Auflage"))
                editions.add(ed)
                paths.append(P + "version")
            else:
                ctx.drop(P + "version", version, "not an explicit TNM edition number (1-9)")
                ctx.warn(P + "version", f"TNM version {version!r} of {notation or code!r} is no edition number; "
                                        f"Observation.method omitted")
        o["valueCodeableConcept"] = cc(*value, text=notation or None)
        paths += [P + k for k in ("display", "text") if it.get(k)]
        members.append(ctx.add(o, *paths))
        prefixes.append(cp if cp in "cp" else "")
    if not members:
        return
    for p in symbols:
        members.append(_symbol(ctx, p))
    g = ctx.new("Observation", "tnm", "grouping", profile=P_GROUP)
    g["status"] = "final"
    kinds = set(prefixes)
    g["code"] = cc(coding(SNOMED, *GROUP_CODE[kinds.pop() if len(kinds) == 1 else ""]))
    g["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        g["focus"] = [ctx.refs["primary"]]
    if len(editions) == 1:
        ed = next(iter(editions))
        g["method"] = cc(coding(CS_TNM_VERSION, ed, f"{ed}. Auflage"))
    g["hasMember"] = members
    ctx.add(g, name="tnm")


def _symbol(ctx, p: str) -> dict:
    """2026: mii-pr-onko-tnm-{y,r,a}-symbol (code LOINC, value SNOMED fixed by the profile pattern)."""
    loinc, sct, display = SYMBOL_CODE[p]
    o = ctx.new("Observation", "tnm", "symbol", p, profile=P_SYMBOL[p])
    o["status"] = "final"
    o["code"] = cc(coding(LOINC, loinc))
    o["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        o["focus"] = [ctx.refs["primary"]]
    o["valueCodeableConcept"] = cc(coding(SNOMED, sct, display))
    ctx.rep("tnm-yra-symbol-2026")
    return ctx.add(o)   # the notation (text/display) is covered by the category Observation that carries it


def _unmatched(ctx, i: int, it: dict, notation: str, why: str | None = None, uicc: str | None = None):
    """weitere-klassifikationen for a TNM item without a category Observation. uicc: a recognised UICC string (also
    from a SNOMED-labelled field) the active profile set lacks -> value.text only, never a SNOMED coding, and the text
    always names the code."""
    code, system = it.get("code"), it.get("system")
    c = coding(SNOMED, code, None, it.get("version") if SCT_VERSION.match(str(it.get("version") or "")) else None) \
        if system == SNOMED and not uicc else None
    text = notation or str(code)
    if uicc and uicc not in text:
        text = f"{uicc} ({text})"
    o = weitere_klassifikation(ctx, ("tnm", i), "TNM", cc(c, text=text))
    ctx.add(o)
    if it.get("version") and not (c and c.get("version")):
        ctx.drop(P + "version", it.get("version"), "UICC code kept as text: no coding to carry its version" if uicc
                 else "edition of an unmatched TNM item (not a SNOMED version URI)")
    for k in ("code", "system", "display", "text") + (("version",) if c and c.get("version") else ()):
        if it.get(k):
            ctx.preserve(P + k, "tnm-unmatched-weitere-klassifikationen")
    ctx.warn(P + "code", f"TNM {system}|{code} ({notation}): "
                         + (why or f"no UICC equivalent in {CM}; kept as weitere-klassifikationen"))
