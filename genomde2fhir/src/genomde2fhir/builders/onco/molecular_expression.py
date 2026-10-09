"""KDK molecular.expressionVariants[] -> mii-pr-mtb-rna-seq (REPRESENTATIONS #18, REVIEW-TD A/E).

Rows: molecular.expressionVariants[].identifier, .gene.{code,display,system,version}, .expressionType, .reference.

- expressionType -> valueCodeableConcept LL1971-2 (noExpression -> Absent LA9634-2, else Present LA9633-4) plus
  Observation.interpretation H / L / N (high / low / normal; extensible base binding). Together lossless.
- gene -> component:gene-studied (48018-6), HGNC system lock http://www.genenames.org
- reference (free-text assessment basis, e.g. a reference cohort) -> Observation.note (REVIEW-TD E; no rna-seq slot)
The Observation is registered as ('variant', identifier): recommendations cite expression variants by identifier.
"""
from ...systems import HGNC, LOINC, MTB, V3_INTERP
from ..common import cc, coding, obs_category
from .molecular_biomarkers import GE_CATEGORY, finding_identifier, observation, register, unique_key

PROFILE = MTB + "StructureDefinition/mii-pr-mtb-rna-seq"
BASE = "molecular.expressionVariants[]."

PRESENT = coding(LOINC, "LA9633-4", "Present")
ABSENT = coding(LOINC, "LA9634-2", "Absent")
LEVEL = {  # expressionType -> (LL1971-2 value, v3 interpretation)
    "noExpression": (ABSENT, None),
    "normalExpression": (PRESENT, ("N", "Normal")),
    "highExpression": (PRESENT, ("H", "High")),
    "lowExpression": (PRESENT, ("L", "Low")),
}


def gene_coding(ctx, gene: dict | None, path_base: str) -> tuple[dict | None, list]:
    """KDK gene Coding -> HGNC coding (system lock); returns (coding, covered paths)."""
    if not gene or not gene.get("code"):
        return None, []
    paths = [path_base + "code"]
    src_sys = gene.get("system")
    system = HGNC
    if src_sys:
        if "genenames.org" in src_sys:
            paths.append(path_base + "system")
        else:  # not HGNC: keep the delivered system rather than relabel the code
            system = src_sys
            ctx.preserve(path_base + "system", "gene-system-not-hgnc")
            ctx.warn(path_base + "system", f"gene system {src_sys!r} is not HGNC; kept as delivered")
    c = coding(system, gene["code"], gene.get("display"), gene.get("version"))
    if gene.get("display"):
        paths.append(path_base + "display")
    if gene.get("version"):
        paths.append(path_base + "version")
    return c, paths


def build(ctx):
    items = (ctx.dk.get("molecular") or {}).get("expressionVariants") or []
    seen: set = set()
    for i, ev in enumerate(items):
        sid = ev.get("identifier")
        key = unique_key(seen, ctx, BASE + "identifier", sid, i)
        o = observation(ctx, PROFILE, "expression", key, code=cc(coding(LOINC, "69548-6", "Genetic variant assessment")),
                        categories=obs_category("laboratory") + [GE_CATEGORY])
        o["identifier"] = [finding_identifier(ctx, sid)]
        paths = [BASE + "identifier"] if sid else []

        et = ev.get("expressionType")
        if et in LEVEL:
            value, interpretation = LEVEL[et]
            o["valueCodeableConcept"] = cc(dict(value))
            if interpretation:
                o["interpretation"] = [{"coding": [{"system": V3_INTERP, "code": interpretation[0],
                                                    "display": interpretation[1]}]}]
            paths.append(BASE + "expressionType")
        elif et:
            ctx.drop(BASE + "expressionType", et, "unknown expressionType")

        gc, gpaths = gene_coding(ctx, ev.get("gene"), BASE + "gene.")
        if gc:
            o["component"] = [{"code": cc(coding(LOINC, "48018-6", "Gene studied [ID]")), "valueCodeableConcept": cc(gc)}]
            paths += gpaths

        if ev.get("reference"):
            o["note"] = [{"text": f"Bewertungsgrundlage: {ev['reference']}"}]
            paths.append(BASE + "reference")

        register(ctx, ctx.add(o, *paths), sid)
