"""KDK molecular.smallVariants[] -> mii-pr-mtb-einfache-variante (+ one MolGen molekulare-konsequenz per variant).

Rows: molecular.smallVariants[].identifier, .genomicSource, .gene.*, .transcriptId.*, .dnaChange, .proteinChange,
.chromosome, .startPosition, .endPosition, .ref, .alt, .variantTypes[].*, .localization, .loh.

Variant Observation (GR 3.0.0 slices as profiled by MTB 2027, REVIEW-TD A "Variant components"):
- value = LOINC LA9633-4 Present (2027 closes value[x] to valueCodeableConcept, LL1971-2)
- gene-studied (HGNC `http://www.genenames.org`, terminology lock / DISCUSS-TD #9)
- representative-transcript-ref-seq: Ensembl or RefSeq system by accession prefix (#10); the MTB required binding to
  `http://ensembl.org` names no ValueSet, so validators only warn
- representative-coding-hgvs / representative-protein-hgvs: varnomen coding qualified with the KDK transcript
  accession (c.: "NM_x.v:c.."; n.: "NR_x.v:n.."; p.: "NM_x.v(GENE):p.."), KDK string kept as text (F.6 open; interim);
  when the transcript is no accession, an unversioned RefSeq accession (HGVS needs the version; it is taken from
  transcriptId.version when given) or does not fit the description type (e.g. NR_ with c.), the KDK string is
  kept as given (reported as representation 'hgvs-unqualified', warned once per file and reason)
- chromosome-identifier: LOINC LL2938-0 answers (no answer for MT -> component omitted, dropped)
- exact-start-end: Range low/high; the KDK coordinates are "GRCh38 VCF-style" by schema definition, hence
  reference-sequence-assembly GRCh38 (LA26806-2) and coordinate-system 1-based (LA30102-0)
- ref-allele / alt-allele, genomic-source-class (LL378-1)
- coding-change-type: all KDK variantTypes as SO codings in the one CodeableConcept (#11)
- loh: unsliced component `mvgs-cs-molecular-feature#loh` valueBoolean (#19, preserved)
Localization (#26): mii-pr-molgen-molekulare-konsequenz, component:feature-consequence via
ConceptMap mvgs-cm-onco-localization-so, derivedFrom -> variant; source value kept as text.

Registers ctx.ids[('variant', <KDK identifier>)] and appends variant + consequence to ctx.bag['ngs_results'].
"""
import re

from ... import terminology
from ...systems import ENSEMBL, HGNC, HGVS, LOINC, MOLGEN, MTB, REFSEQ, SID_FINDING, SO, TBD_GR
from ..common import cc, coding, obs_category, scoped_id

P_VARIANT = MTB + "StructureDefinition/mii-pr-mtb-einfache-variante"
P_CONSEQUENCE = MOLGEN + "StructureDefinition/mii-pr-molgen-molekulare-konsequenz"
CM_LOCALIZATION = "mvgs-cm-onco-localization-so"
CS_FEATURE = "mvgs-cs-molecular-feature"

# Same system/value form as the other molecular builders (local until systems.py carries it; core request).

B = "molecular.smallVariants[]."
GE_CATEGORY = {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "GE"}]}

# LOINC LL2938-0 (required on chromosome-identifier); verified against tx.fhir.org. MT has no answer.
CHROMOSOME_LA = {
    "1": "LA21254-0", "2": "LA21255-7", "3": "LA21256-5", "4": "LA21257-3", "5": "LA21258-1", "6": "LA21259-9",
    "7": "LA21260-7", "8": "LA21261-5", "9": "LA21262-3", "10": "LA21263-1", "11": "LA21264-9", "12": "LA21265-6",
    "13": "LA21266-4", "14": "LA21267-2", "15": "LA21268-0", "16": "LA21269-8", "17": "LA21270-6",
    "18": "LA21271-4", "19": "LA21272-2", "20": "LA21273-0", "21": "LA21274-8", "22": "LA21275-5",
    "X": "LA21276-3", "Y": "LA21277-1",
}
GENOMIC_SOURCE_LA = {"somatic": ("LA6684-0", "Somatic"), "germline": ("LA6683-2", "Germline")}
QUALIFY_PREFIXES = {"c": ("NM_", "XM_", "ENST"), "n": ("NR_", "XR_", "ENST"), "p": ("NM_", "XM_")}
REFSEQ_PREFIXES = ("NM_", "NR_", "XM_", "XR_", "NG_", "NC_", "NT_", "NW_", "NP_", "XP_")


def loinc(code: str, display: str | None = None) -> dict:
    return {"coding": [coding(LOINC, code, display)]}


def component(code: dict, **value) -> dict:
    return {"code": code, **value}


def finding_identifier(ctx, value) -> dict | None:
    return scoped_id(ctx, SID_FINDING, value)


def hgnc_coding(ctx, gene: dict | None, path_prefix: str) -> tuple[dict | None, list]:
    """KDK gene Coding -> HGNC coding (system locked to http://www.genenames.org); returns (coding, covered paths)."""
    if not gene or not gene.get("code"):
        return None, []
    sys_ = gene.get("system") or ""
    code = str(gene["code"])
    if not sys_ or "genenames" in sys_ or code.upper().startswith("HGNC:"):
        system = HGNC
    else:
        system = sys_
        ctx.warn(path_prefix + "system", f"gene system {sys_!r} is not HGNC; passed through")
    paths = [path_prefix + "code"] + [path_prefix + k for k in ("display", "system", "version") if gene.get(k)]
    return coding(system, code, gene.get("display"), gene.get("version")), paths


def transcript_system(code: str, source_system: str | None) -> str | None:
    c = code.upper()
    if c.startswith(("ENST", "ENSG", "ENSP")):
        return ENSEMBL
    if c.startswith(REFSEQ_PREFIXES):
        return REFSEQ
    s = (source_system or "").lower()
    if "ensembl" in s:
        return ENSEMBL
    if "ncbi" in s or "refseq" in s:
        return REFSEQ
    return source_system


def transcript_accession(tr: dict) -> str | None:
    """Versioned RefSeq (NM_/NR_/XM_/XR_) or Ensembl (ENST) accession usable as HGVS reference, else None.
    A RefSeq accession without version (in the code or transcriptId.version) is no valid HGVS reference ('NM_000546:c.'
    is rejected by the HGVS check, 'NM_000546.6:c.' passes) -> None. An unversioned ENST is kept: the HGVS check on
    matchbox/tx.fhir.org accepts it (checked 2026-10-09), and the KDK schema example is one."""
    code = str(tr.get("code") or "")
    if not re.fullmatch(r"(N[MR]_|X[MR]_)\d+(\.\d+)?|ENST\d+(\.\d+)?", code):
        return None
    if "." not in code and tr.get("version") and str(tr["version"]).isdigit() and code.startswith(("N", "X")):
        code = f"{code}.{tr['version']}"
    if code.startswith(("N", "X")) and "." not in code:
        return None
    return code


def unqualified_reason(tr: dict, accession: str | None) -> tuple[str, str]:
    """(kind, text) why a bare c./p. string could not be qualified."""
    code = str(tr.get("code") or "")
    if not code:
        return "no-transcript", "no transcriptId"
    if not accession and re.fullmatch(r"(N[MR]_|X[MR]_)\d+", code):
        return "unversioned", f"RefSeq transcript {code!r} has no version (HGVS needs a versioned reference sequence)"
    if not accession:
        return "no-accession", f"transcript id {code!r} is not a RefSeq/Ensembl accession"
    return "mismatch", f"transcript {accession} does not fit the description type, or no gene symbol for p."


def warn_unqualified(ctx, path: str, tr: dict, accession: str | None):
    """Representation 'hgvs-unqualified' + one warning per file and reason (the variants of a file share the cause)."""
    ctx.rep("hgvs-unqualified")
    kind, reason = unqualified_reason(tr, accession)
    done = ctx.bag["hgvs-unqualified-warned"]
    if kind not in done:
        done.append(kind)
        ctx.warn(path, f"HGVS not qualified: {reason}; bare c./p. strings kept as delivered (fail the hgvs-vs check; "
                       f"further variants counted in representation 'hgvs-unqualified')")


def qualify_hgvs(raw: str, accession: str | None, gene_symbol: str | None = None) -> str:
    """'c.181C>A' + NM_002524.5 -> 'NM_002524.5:c.181C>A'; protein changes have no protein accession in the KDK, so
    they are given relative to the transcript with the gene symbol (ClinVar style 'NM_002524.5(NRAS):p.Gln61Lys')."""
    raw = raw.strip()
    if ":" in raw or not accession or not raw.startswith(("c.", "n.", "p.")):
        return raw
    # the prefix must fit the reference type: c./p. need a coding transcript, n. a non-coding one (an NR_ accession
    # with a c. description would be invalid HGVS, so the KDK string is then kept as given)
    if not accession.startswith(QUALIFY_PREFIXES[raw[0]]):
        return raw
    if raw.startswith("p."):
        if not gene_symbol:
            return raw
        return f"{accession}({gene_symbol}):{raw}"
    return f"{accession}:{raw}"


def so_system(system: str | None, code: str) -> str | None:
    if (system and "sequenceontology" in system) or str(code).upper().startswith("SO:"):
        return SO
    return system


def _unique(ctx, seen: set, source_id, index: int) -> str:
    if source_id in (None, "") or source_id in seen:
        if source_id not in (None, ""):
            ctx.warn(B + "identifier", f"duplicate identifier {source_id!r}; id made unique with array index {index}")
        return f"{source_id or ''}#{index}"
    seen.add(source_id)
    return source_id


def build(ctx):
    variants = (ctx.dk.get("molecular") or {}).get("smallVariants") or []
    seen: set = set()
    for i, sv in enumerate(variants):
        build_variant(ctx, sv, _unique(ctx, seen, sv.get("identifier"), i))


def build_variant(ctx, sv: dict, key: str):
    o = ctx.new("Observation", "small-variant", key, profile=P_VARIANT)
    o["identifier"] = [finding_identifier(ctx, sv.get("identifier"))]
    o["status"] = "final"
    o["category"] = obs_category("laboratory") + [GE_CATEGORY]
    o["code"] = loinc("69548-6", "Genetic variant assessment")
    o["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        o["focus"] = [ctx.refs["primary"]]
    o["valueCodeableConcept"] = loinc("LA9633-4", "Present")
    paths = [B + "identifier"] if sv.get("identifier") else []
    comps = []

    # gene-studied
    g, gp = hgnc_coding(ctx, sv.get("gene"), B + "gene.")
    if g:
        comps.append(component(loinc("48018-6", "Gene studied [ID]"), valueCodeableConcept=cc(g)))
        paths += gp

    # chromosome-identifier
    chrom = sv.get("chromosome")
    if chrom:
        la = CHROMOSOME_LA.get(str(chrom))
        if la:
            comps.append(component(loinc("48000-4"), valueCodeableConcept=loinc(la, f"Chromosome {chrom}")))
            paths.append(B + "chromosome")
        else:
            ctx.drop(B + "chromosome", chrom, "no LOINC LL2938-0 answer (required binding on chromosome-identifier)")

    # exact-start-end (+ assembly / coordinate system as defined by the KDK schema: GRCh38, VCF-style = 1-based)
    start, end = sv.get("startPosition"), sv.get("endPosition")
    if start is not None or end is not None:
        rng = {}
        if start is not None:
            rng["low"] = {"value": start}
            paths.append(B + "startPosition")
        if end is not None:
            if start is not None and end < start:
                ctx.drop(B + "endPosition", end, "endPosition < startPosition (data quality); Range.high omitted (rng-2)")
            else:
                rng["high"] = {"value": end}
                paths.append(B + "endPosition")
        comps.append(component(loinc("81254-5"), valueRange=rng))
        comps.append(component(loinc("62374-4"), valueCodeableConcept=loinc("LA26806-2", "GRCh38")))
        comps.append(component(loinc("92822-6"), valueCodeableConcept=loinc("LA30102-0", "1-based character counting")))

    # ref / alt allele
    if sv.get("ref"):
        comps.append(component(loinc("69547-8"), valueString=sv["ref"]))
        paths.append(B + "ref")
    if sv.get("alt"):
        comps.append(component(loinc("69551-0"), valueString=sv["alt"]))
        paths.append(B + "alt")

    # HGVS: qualified with the KDK transcript accession where it is one (hgvs-vs is validated semantically and
    # rejects bare c./p. strings); the KDK string is kept as CodeableConcept.text
    tr = sv.get("transcriptId") or {}
    acc = transcript_accession(tr)
    gene_symbol = (sv.get("gene") or {}).get("display")
    for field, loinc_code, kind in (("dnaChange", "48004-6", "c"), ("proteinChange", "48005-3", "p")):
        raw = sv.get(field)
        if not raw:
            continue
        expr = qualify_hgvs(raw, acc, gene_symbol if kind == "p" else None)
        if expr == raw and ":" not in raw:
            warn_unqualified(ctx, B + field, tr, acc)
        comps.append(component(loinc(loinc_code), valueCodeableConcept=cc(coding(HGVS, expr),
                                                                          text=raw if expr != raw else None)))
        paths.append(B + field)

    # transcript
    if tr.get("code"):
        system = transcript_system(str(tr["code"]), tr.get("system"))
        comps.append(component(loinc("51958-7"), valueCodeableConcept=cc(
            coding(system, tr["code"], tr.get("display"), tr.get("version")))))
        paths += [B + "transcriptId.code"] + [B + "transcriptId." + k for k in ("display", "system", "version")
                                              if tr.get(k)]
        if system == REFSEQ:
            ctx.rep("transcript-refseq-vs-mtb-ensembl-binding")

    # coding-change-type: all variant types as SO codings in one CodeableConcept
    vts = [vt for vt in sv.get("variantTypes") or [] if vt and vt.get("code")]
    for vt in sv.get("variantTypes") or []:
        if not (vt and vt.get("code")):
            ctx.drop(B + "variantTypes[].code", vt, "variant type without code")
    if vts:
        codings = [coding(so_system(vt.get("system"), vt["code"]), vt["code"], vt.get("display"), vt.get("version"))
                   for vt in vts]
        comps.append(component(loinc("48019-4"), valueCodeableConcept=cc(*codings)))
        vp = B + "variantTypes[]."
        paths += [vp + "code"] + [vp + k for k in ("display", "system", "version") if any(vt.get(k) for vt in vts)]
        if len(vts) > 1:
            ctx.rep("variant-types-multi-coding")

    # genomic source class
    gs = sv.get("genomicSource")
    if gs:
        la = GENOMIC_SOURCE_LA.get(gs)
        if la:
            comps.append(component(loinc("48002-0"), valueCodeableConcept=loinc(*la)))
            paths.append(B + "genomicSource")
        else:
            ctx.drop(B + "genomicSource", gs, "not in LL378-1 mapping")

    # LOH: open (unsliced) component with the local feature code (#19)
    if sv.get("loh") is not None:
        c = terminology.local_coding(CS_FEATURE, "loh")
        comps.append(component(cc(c), valueBoolean=bool(sv["loh"])))
        ctx.preserve(B + "loh", "loh-unsliced-component")

    o["component"] = comps
    ref = ctx.add(o, *paths)
    if sv.get("identifier") not in (None, "") and ("variant", sv["identifier"]) not in ctx.ids:
        ctx.ids[("variant", sv["identifier"])] = ref
    ctx.bag["ngs_results"].append(ref)

    if sv.get("localization"):
        build_consequence(ctx, sv["localization"], key, ref)


def build_consequence(ctx, localization: str, key: str, variant_ref: dict):
    """One molekulare-konsequenz per variant with the localization as feature-consequence (#26)."""
    so = terminology.translate(CM_LOCALIZATION, localization)
    if not so:
        ctx.drop(B + "localization", localization, f"not in {CM_LOCALIZATION}")
        return
    o = ctx.new("Observation", "small-variant", key, "consequence", profile=P_CONSEQUENCE)
    o["status"] = "final"
    o["category"] = obs_category("laboratory") + [GE_CATEGORY]
    o["code"] = {"coding": [coding(TBD_GR, "molecular-consequence", "Molecular Consequence")]}
    o["subject"] = ctx.patient
    o["derivedFrom"] = [variant_ref]
    o["component"] = [component({"coding": [coding(TBD_GR, "feature-consequence")]},
                                valueCodeableConcept=cc(*so, text=localization))]
    ref = ctx.add(o, B + "localization")
    if localization == "notInCodingAndNotInRegulatoryElements":
        ctx.rep("localization-so-wider")
    ctx.bag["ngs_results"].append(ref)
