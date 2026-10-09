"""KDK molecular.copyNumberVariants[] -> MTB copy-number-variant Observations (+ MolGen molekulare-konsequenz).

Rows: molecular.copyNumberVariants[].identifier, .genomicSource, .cnvType, .gene.{code,display,system,version},
.chromosome, .startPosition, .endPosition, .localization.

- cnvType -> `component:cnv-type` with the DNPM/bwHC code where one exists (`mvgs-cm-cnv-type-dnpm`) plus the
  six-level `mvgs-cs-cnv-type` coding, and `component:coding-change-type` SO copy_number_gain/loss
  (`mvgs-cm-cnv-type-so`) (REPRESENTATIONS #17).
- localization -> one `mii-pr-molgen-molekulare-konsequenz` per variant, `component:feature-consequence`
  (SO, REPRESENTATIONS #26), derivedFrom -> variant.
- KDK carries no copy number, LOH or focality for CNVs: those MTB components are not emitted.

Also hosts the variant helpers shared with molecular_fusions (gene coding, chromosome, genomic source,
molecular consequence).
"""
from ... import terminology
from ...systems import HGNC, LOINC, MOLGEN, MTB, SID_FINDING, SO, TBD_GR
from ..common import cc, coding, obs_category, scoped_id

PROFILE = MTB + "StructureDefinition/mii-pr-mtb-copy-number-variant"
CONSEQUENCE_PROFILE = MOLGEN + "StructureDefinition/mii-pr-molgen-molekulare-konsequenz"
P = "molecular.copyNumberVariants[]."

# Same identifier system/value form as the other molecular builders ("<submitterId>|<caseId>|<KDK identifier>");
# local until systems.py carries it (core request).
CM_LOCALIZATION = "mvgs-cm-onco-localization-so"
GE_CATEGORY = {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "GE"}]}
GRCH38 = ("LA26806-2", "GRCh38")   # KDK: positions are "HG38-Position"
BWHC_CNV = "http://bwhc.de/mtb/genetics-copy-number-variant"
CNV_TYPE_CS = "mvgs-cs-cnv-type"

VARIANT_CODE = {"coding": [{"system": LOINC, "code": "69548-6", "display": "Genetic variant assessment"}]}
PRESENT = {"coding": [{"system": LOINC, "code": "LA9633-4", "display": "Present"}]}
GENOMIC_SOURCE = {"somatic": ("LA6684-0", "Somatic"), "germline": ("LA6683-2", "Germline")}
# LOINC answer list LL2938-0 (chromosome 1..22, X, Y): consecutive LA codes LA21254-0 .. LA21277-1
_CHR = [str(i) for i in range(1, 23)] + ["X", "Y"]
_CHR_LA = ["LA21254-0", "LA21255-7", "LA21256-5", "LA21257-3", "LA21258-1", "LA21259-9", "LA21260-7", "LA21261-5",
           "LA21262-3", "LA21263-1", "LA21264-9", "LA21265-6", "LA21266-4", "LA21267-2", "LA21268-0", "LA21269-8",
           "LA21270-6", "LA21271-4", "LA21272-2", "LA21273-0", "LA21274-8", "LA21275-5", "LA21276-3", "LA21277-1"]
CHROMOSOME = dict(zip(_CHR, _CHR_LA))

# Oncology localization -> SO (REVIEW-TD A "Localization"); read from mvgs-cm-onco-localization-so, this table is
# only the fallback while that ConceptMap is not installed.
LOCALIZATION_SO = {
    "coding": ("SO:0001580", "coding_sequence_variant"),
    "inRegulatoryElements": ("SO:0001566", "regulatory_region_variant"),
    # no single SO term for "neither coding nor regulatory": parent structural_variant (lossy; enum kept as text)
    "notInCodingAndNotInRegulatoryElements": ("SO:0001537", "structural_variant"),
}
LOSSY_LOCALIZATION = {"notInCodingAndNotInRegulatoryElements"}


def comp(code: dict, **value) -> dict:
    return {"code": code, **value}


def loinc_cc(code: str, display: str | None = None) -> dict:
    return {"coding": [coding(LOINC, code, display)]}


def gene_coding(ctx, gene: dict | None, path: str) -> dict | None:
    """KDK gene Coding -> HGNC coding (terminology lock http://www.genenames.org; code = HGNC ID, display = symbol).
    Covers <path>.code/.display/.system/.version for the fields present."""
    if not gene or not gene.get("code"):
        return None
    system = gene.get("system")
    if system and "genenames.org" not in system:
        ctx.warn(path + ".system", f"non-HGNC gene system kept as delivered: {system}")
    else:
        system = HGNC
        if not str(gene["code"]).startswith("HGNC:"):
            ctx.warn(path + ".code", f"gene code is not an HGNC ID: {gene['code']!r}")
    ctx.cover(*[f"{path}.{k}" for k in ("code", "display", "system", "version") if gene.get(k)])
    return coding(system, gene["code"], gene.get("display"), gene.get("version"))


def chromosome_cc(ctx, chrom: str | None, path: str) -> dict | None:
    la = CHROMOSOME.get(str(chrom)) if chrom else None
    if chrom and not la:
        ctx.drop(path, chrom, "chromosome not in LOINC LL2938-0")
        return None
    return loinc_cc(la, f"Chromosome {chrom}") if la else None


def genomic_source_comp(ctx, src: str | None, path: str) -> dict | None:
    if not src:
        return None
    hit = GENOMIC_SOURCE.get(src)
    if not hit:
        ctx.drop(path, src, "genomic source not in LOINC LL378-1")
        return None
    ctx.cover(path)
    return comp(loinc_cc("48002-0"), valueCodeableConcept=loinc_cc(*hit))


def finding_identifier(ctx, value) -> dict | None:
    return scoped_id(ctx, SID_FINDING, value)


def unique_key(ctx, seen: set, source_id, index: int, path: str) -> str:
    """Resource-id key: the KDK identifier, or identifier#index when missing/duplicated within the block."""
    if source_id in (None, "") or source_id in seen:
        if source_id not in (None, ""):
            ctx.warn(path, f"duplicate identifier {source_id!r}; id made unique with array index {index}")
        return f"{source_id or ''}#{index}"
    seen.add(source_id)
    return str(source_id)


def variant_skeleton(ctx, kind: str, key: str, source_id, profile: str) -> dict:
    """Common MTB variant header: status, lab+GE category, 69548-6, subject, focus -> primary tumour, Present."""
    obs = ctx.new("Observation", kind, key, profile=profile)
    obs.update(
        identifier=[finding_identifier(ctx, source_id)],
        status="final",
        category=obs_category("laboratory") + [GE_CATEGORY],
        code=VARIANT_CODE,
        subject=ctx.patient,
        focus=[ctx.refs["primary"]] if ctx.refs.get("primary") else None,
        valueCodeableConcept=PRESENT,
    )
    return obs


def localization_coding(loc: str) -> dict | None:
    try:
        hits = terminology.translate(CM_LOCALIZATION, loc)
    except KeyError:
        hits = []
    if hits:
        return hits[0]
    so = LOCALIZATION_SO.get(loc)
    return coding(SO, so[0], so[1]) if so else None


def add_consequence(ctx, kind: str, key: str, variant_ref: dict, loc: str | None, path: str):
    """KDK localization -> mii-pr-molgen-molekulare-konsequenz.component:feature-consequence (REPRESENTATIONS #26)."""
    if not loc:
        return
    c = localization_coding(loc)
    if not c:
        ctx.drop(path, loc, "localization not mappable to SO")
        return
    if loc in LOSSY_LOCALIZATION:
        ctx.rep("localization-so-wider")
    mc = ctx.new("Observation", kind, key, "consequence", profile=CONSEQUENCE_PROFILE)
    mc.update(
        status="final",
        category=obs_category("laboratory") + [GE_CATEGORY],
        code={"coding": [coding(TBD_GR, "molecular-consequence", "Molecular Consequence")]},
        subject=ctx.patient,
        derivedFrom=[variant_ref],
        component=[comp({"coding": [{"system": TBD_GR, "code": "feature-consequence"}]},
                        valueCodeableConcept=cc(c, text=loc))],
    )
    ref = ctx.add(mc, path)
    ctx.bag["ngs_results"].append(ref)


def register(ctx, source_id, ref: dict, path: str):
    """ctx.ids[('variant', <KDK identifier>)] (first one wins across variant blocks) + bag['ngs_results']."""
    if source_id not in (None, ""):
        if ("variant", source_id) in ctx.ids:
            ctx.warn(path, f"variant identifier {source_id!r} already used by another molecular finding; "
                           "references resolve to the first one")
        else:
            ctx.ids[("variant", source_id)] = ref
    ctx.bag["ngs_results"].append(ref)


def position_range(ctx, start, end, path_prefix: str) -> tuple[dict | None, list]:
    """start/end -> Range low/high; inconsistent coordinates (start > end, data quality) are dropped, not swapped."""
    if start is None and end is None:
        return None, []
    if start is not None and end is not None and start > end:
        for k, val in (("startPosition", start), ("endPosition", end)):
            ctx.drop(path_prefix + k, val, f"start {start} > end {end} (rng-2); coordinates not emitted")
        return None, []
    rng, paths = {}, []
    if start is not None:
        rng["low"] = {"value": start}
        paths.append(path_prefix + "startPosition")
    if end is not None:
        rng["high"] = {"value": end}
        paths.append(path_prefix + "endPosition")
    return rng, paths


def build(ctx):
    seen: set = set()
    for i, v in enumerate((ctx.dk.get("molecular") or {}).get("copyNumberVariants") or []):
        build_cnv(ctx, v, unique_key(ctx, seen, v.get("identifier"), i, P + "identifier"))


def build_cnv(ctx, v: dict, key: str):
    obs = variant_skeleton(ctx, "cnv", key, v.get("identifier"), PROFILE)
    comps, paths = [], ([P + "identifier"] if v.get("identifier") else [])

    g = gene_coding(ctx, v.get("gene"), P + "gene")
    if g:
        comps.append(comp(loinc_cc("48018-6"), valueCodeableConcept=cc(g)))

    ch = chromosome_cc(ctx, v.get("chromosome"), P + "chromosome")
    if ch:
        comps.append(comp(loinc_cc("48000-4"), valueCodeableConcept=ch))
        paths.append(P + "chromosome")

    rng, pos_paths = position_range(ctx, v.get("startPosition"), v.get("endPosition"), P)
    if rng:
        comps.append(comp(loinc_cc("81254-5"), valueRange=rng))
        comps.append(comp(loinc_cc("62374-4"), valueCodeableConcept=loinc_cc(*GRCH38)))
        paths += pos_paths

    gs = genomic_source_comp(ctx, v.get("genomicSource"), P + "genomicSource")
    if gs:
        comps.append(gs)

    t = v.get("cnvType")
    local = terminology.local_coding(CNV_TYPE_CS, t) if t else None
    if local:
        dnpm = terminology.translate("mvgs-cm-cnv-type-dnpm", t)
        so = terminology.translate("mvgs-cm-cnv-type-so", t)
        comps.append(comp({"coding": [{"system": BWHC_CNV, "code": "type"}]}, valueCodeableConcept=cc(*dnpm, local)))
        if so:
            comps.append(comp(loinc_cc("48019-4"), valueCodeableConcept=cc(*so)))
        if not dnpm:
            ctx.rep("cnv-type-no-dnpm-code")
        paths.append(P + "cnvType")
    elif t:
        ctx.drop(P + "cnvType", t, "not in mvgs-cs-cnv-type")

    obs["component"] = comps
    ref = ctx.add(obs, *paths)
    register(ctx, v.get("identifier") if key == v.get("identifier") else None, ref, P + "identifier")
    add_consequence(ctx, "cnv", key, ref, v.get("localization"), P + "localization")
