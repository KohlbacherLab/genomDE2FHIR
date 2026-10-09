"""KDK molecular.structuralVariants[] -> MTB dna-fusion / rna-fusion Observations (+ molekulare-konsequenz).

Rows: molecular.structuralVariants[].identifier, .genomicSource, .geneA.*, .geneB.*, .structureType, .description,
.sequenceType, .localization.

- sequenceType selects the profile (DNA -> mii-pr-mtb-dna-fusion, RNA -> mii-pr-mtb-rna-fusion).
- geneA -> `component:five-prime-gene`, geneB -> `component:three-prime-gene` (HGNC coding; DISCUSS-TD #21).
- The profiles' 1..1 breakpoint components (DNA: chromosome + position; RNA: transcript, exon, position, strand)
  have no KDK source: emitted as code + dataAbsentReason `unknown` (REPRESENTATIONS #21).
- structureType -> `component:coding-change-type` SO code via `mvgs-cm-structure-type-so`, the KDK enum kept as a
  second coding from `mvgs-cs-structure-type` (REPRESENTATIONS #11).
- description (HGVS/ISCN text) -> `component:cytogenomic-nomenclature.valueCodeableConcept.text`.
- localization -> molekulare-konsequenz (see molecular_cnv.add_consequence).
"""
from ... import terminology
from ...systems import MTB
from ..common import cc, dar_cc
from .molecular_cnv import (add_consequence, comp, gene_coding, genomic_source_comp, loinc_cc, register,
                            unique_key, variant_skeleton)

DNA_PROFILE = MTB + "StructureDefinition/mii-pr-mtb-dna-fusion"
RNA_PROFILE = MTB + "StructureDefinition/mii-pr-mtb-rna-fusion"
BIOMARKER_CS = MTB + "CodeSystem/mii-cs-mtb-molekulare-biomarker"
STRUCTURE_TYPE_CS = "mvgs-cs-structure-type"
P = "molecular.structuralVariants[]."

# mandatory breakpoint slices without a KDK source (in profile order after the partner gene)
BREAKPOINTS = {
    "DNA": ["five-prime-chromosome", "three-prime-chromosome", "five-prime-position", "three-prime-position"],
    "RNA": ["five-prime-transcript-id", "five-prime-exon-id", "five-prime-position", "five-prime-strand",
            "three-prime-transcript-id", "three-prime-exon-id", "three-prime-position", "three-prime-strand"],
}


def biomarker(code: str) -> dict:
    return {"coding": [{"system": BIOMARKER_CS, "code": code}]}


def partner_gene(ctx, slice_name: str, gene: dict | None, path: str) -> dict:
    g = gene_coding(ctx, gene, path)
    if g:
        return comp(biomarker(slice_name), valueCodeableConcept=cc(g))
    return comp(biomarker(slice_name), dataAbsentReason=dar_cc("unknown"))


def build(ctx):
    seen: set = set()
    for i, v in enumerate((ctx.dk.get("molecular") or {}).get("structuralVariants") or []):
        build_sv(ctx, v, unique_key(ctx, seen, v.get("identifier"), i, P + "identifier"))


def build_sv(ctx, v: dict, key: str):
    seq = v.get("sequenceType")
    if seq not in BREAKPOINTS:
        # schema requires DNA|RNA; anything else cannot select a profile -> DNA fusion (genomic default), reported
        ctx.warn(P + "sequenceType", f"unknown sequenceType {seq!r}; DNA fusion profile used")
        seq = "DNA"
    else:
        ctx.cover(P + "sequenceType")
    obs = variant_skeleton(ctx, "sv", key, v.get("identifier"), RNA_PROFILE if seq == "RNA" else DNA_PROFILE)
    paths = [P + "identifier"] if v.get("identifier") else []

    comps = [partner_gene(ctx, "five-prime-gene", v.get("geneA"), P + "geneA"),
             partner_gene(ctx, "three-prime-gene", v.get("geneB"), P + "geneB")]
    comps += [comp(biomarker(s), dataAbsentReason=dar_cc("unknown")) for s in BREAKPOINTS[seq]]
    ctx.rep(f"fusion-breakpoints-data-absent-{seq.lower()}")

    gs = genomic_source_comp(ctx, v.get("genomicSource"), P + "genomicSource")
    if gs:
        comps.append(gs)

    st = v.get("structureType")
    if st:
        so = terminology.translate("mvgs-cm-structure-type-so", st)
        local = terminology.local_coding(STRUCTURE_TYPE_CS, st)
        if so or local:
            comps.append(comp(loinc_cc("48019-4"), valueCodeableConcept=cc(*so, local)))
            paths.append(P + "structureType")
        else:
            ctx.drop(P + "structureType", st, "unknown structural variant type")

    if v.get("description"):
        comps.append(comp(loinc_cc("81291-7"), valueCodeableConcept={"text": v["description"]}))
        paths.append(P + "description")

    obs["component"] = comps
    ref = ctx.add(obs, *paths)
    register(ctx, v.get("identifier") if key == v.get("identifier") else None, ref, P + "identifier")
    add_consequence(ctx, "sv", key, ref, v.get("localization"), P + "localization")
