"""KDK rare-disease molecular block -> MolGen variant findings (DISCUSS-TD #26-#30, REVIEW-TD A).

Per source variant (smallVariants[], copyNumberVariants[], structuralVariants[]):
  * one MolGen `variante` Observation (MolGen has no CNV/SV profiles; GR 3.0.0 slices),
  * one MolGen `diagnostische-implikation` (derivedFrom:variant) when the variant carries an ACMG class,
    criteria, mode of inheritance, diagnostic significance or publications,
  * one `mii-pr-molgen-molekulare-konsequenz` (derivedFrom:variant) when it carries localizations.
Registers ctx.ids[("variant", identifier)] -> variante and appends variante, implication and consequence
references to ctx.bag["rd_report_results"] (consumed by rd.report).

Rows: molecular.{smallVariants,copyNumberVariants,structuralVariants}[].*
"""
import re

from ...systems import HGNC, HGVS, HPO, LOINC, MOLGEN, OBS_CATEGORY, SID_FINDING, SID_LE, SO, TBD_GR
from ...terminology import local_coding, translate
from ..common import cc, coding, ext, scoped_id

VARIANTE = MOLGEN + "StructureDefinition/variante"
IMPLIKATION = MOLGEN + "StructureDefinition/diagnostische-implikation"
KONSEQUENZ = MOLGEN + "StructureDefinition/mii-pr-molgen-molekulare-konsequenz"
RELATED_ARTIFACT_EXT = "http://hl7.org/fhir/StructureDefinition/workflow-relatedArtifact"

CLINVAR = "http://www.ncbi.nlm.nih.gov/clinvar"
CLINGEN_ACMG = "https://clinicalgenome.org/codesystem/acmg-criteria"
V2_0074 = "http://terminology.hl7.org/CodeSystem/v2-0074"
PUBMED = "https://pubmed.ncbi.nlm.nih.gov/"

CS_FINDING = "mvgs-cs-finding-category"
CS_SEGREGATION = "mvgs-cs-segregation"
CS_ACMG_STRENGTH = "mvgs-cs-rd-acmg-strength"
CM_LOCALIZATION = "mvgs-cm-rd-localization-so"

KINDS = (("smallVariants", "small"), ("copyNumberVariants", "cnv"), ("structuralVariants", "sv"))

# LOINC LL2938-0 (chromosome-identifier, required binding)
CHROMOSOME = {**{str(n): (c, f"Chromosome {n}") for n, c in enumerate((
    "LA21254-0 LA21255-7 LA21256-5 LA21257-3 LA21258-1 LA21259-9 LA21260-7 LA21261-5 LA21262-3 LA21263-1 LA21264-9 "
    "LA21265-6 LA21266-4 LA21267-2 LA21268-0 LA21269-8 LA21270-6 LA21271-4 LA21272-2 LA21273-0 LA21274-8 LA21275-5"
    ).split(), start=1)},
    "X": ("LA21276-3", "Chromosome X"), "Y": ("LA21277-1", "Chromosome Y")}
# MT has no LL2938-0 answer -> genomic-ref-seq with the mitochondrial reference sequence (rCRS, GRCh37 and GRCh38)
MT_REFSEQ = ("NC_012920.1", "Homo sapiens mitochondrion, complete genome")
REFSEQ = "http://www.ncbi.nlm.nih.gov/refseq"
# LOINC LL381-5 (allelic-state, extensible)
ZYGOSITY = {"heterozygous": ("LA6706-1", "Heterozygous"), "homozygous": ("LA6705-3", "Homozygous"),
            "hemi": ("LA6707-9", "Hemizygous"), "compHet": ("LA26217-2", "Compound heterozygous"),
            "homoplasmic": ("LA6704-6", "Homoplasmic"), "heteroplasmic": ("LA6703-8", "Heteroplasmic")}
# LOINC LL5489-1 (variant-inheritance, extensible); fromMotherAndFather -> local biparental; notPerformed -> omitted
SEGREGATION = {"deNovo": ("LA26807-0", "De novo"), "fromFather": ("LA26321-2", "Paternal"),
               "fromMother": ("LA26320-4", "Maternal")}
# LOINC LL4034-6 (clinical-significance, example binding; ACMG 5-tier)
ACMG_CLASS = {"1": ("LA6675-8", "Benign"), "2": ("LA26334-5", "Likely benign"),
              "3": ("LA26333-7", "Uncertain significance"), "4": ("LA26332-9", "Likely pathogenic"),
              "5": ("LA6668-3", "Pathogenic")}
# HPO, GR condition-inheritance-mode-vs (preferred); unclear -> text only (REPRESENTATIONS #29)
INHERITANCE = {"dominant": ("HP:0000006", "Autosomal dominant inheritance"),
               "recessive": ("HP:0000007", "Autosomal recessive inheritance"),
               "XLinked": ("HP:0001417", "X-linked inheritance"),
               "mitochondrial": ("HP:0001427", "Mitochondrial inheritance")}
# SO (GR dna-change-type-vs, extensible); REVIEW-TD A
CNV_TYPE = {"gain": ("SO:0001742", "copy_number_gain"), "loss": ("SO:0001743", "copy_number_loss")}

# plausible HGVS expression: optional reference sequence, one of c/g/m/n/r/p, no whitespace
HGVS_EXPR = re.compile(r"^(?:[A-Za-z][A-Za-z0-9_]*(?:\.[0-9]+)?(?:\([A-Za-z0-9_.]+\))?:)?([cgmnrp])\.\S+$")
HGVS_FIELDS = (("cdnaChange", "48004-6", "cn"), ("gdnaChange", "81290-9", "gm"), ("proteinChange", "48005-3", "p"))
# HGVS constructs the hgvs-vs terminology service (tx.fhir.org -> VariantValidator) rejects or times out on:
# alternatives '^', mosaic/chimeric '/', whole-chromosome 'pter'/'qter', uncertain breakpoints '(a_b)_(c_d)'.
# A coded slot with them fails the required binding, so they are kept in Observation.note like malformed ones.
HGVS_UNVALIDATABLE = re.compile(r"\^|/|pter|qter|\)_\(")
CLINVAR_ID = re.compile(r"^(?:[0-9]+|[VRS]CV[0-9]+(?:\.[0-9]+)?)$")


def _categories() -> list:
    return [{"coding": [{"system": OBS_CATEGORY, "code": "laboratory"}]},
            {"coding": [{"system": V2_0074, "code": "GE"}]}]


def _comp(system: str, code: str, **value) -> dict:
    return {"code": {"coding": [{"system": system, "code": code}]}, **value}


def _cc(system, code, display=None, text=None) -> dict:
    return cc(coding(system, code, display), text=text)


def build(ctx):
    mol = ctx.dk.get("molecular") or {}
    for key, kind in KINDS:
        for i, v in enumerate(mol.get(key) or []):
            if isinstance(v, dict):
                _variant(ctx, key, kind, i, v)


def _variant(ctx, key: str, kind: str, index: int, v: dict):
    P = f"molecular.{key}[]."
    vid = v.get("identifier")
    parts = ("rd-variant", kind, vid if vid else f"#{index}")
    if ctx.bundle.has(ctx.id("Observation", *parts)):
        ctx.warn(P + "identifier", f"duplicate variant identifier {vid!r}; position {index} kept as a separate finding")
        parts = parts + (index,)
    obs = ctx.new("Observation", *parts, profile=VARIANTE)
    obs.update(status="final", category=_categories(), code=_cc(LOINC, "69548-6", "Genetic variant assessment"),
               subject=ctx.patient,
               valueCodeableConcept=_cc(LOINC, "LA9633-4", "Present"))
    paths, comps, ids = [], [], []

    if vid:
        ids.append({"use": "usual", **scoped_id(ctx, SID_FINDING, vid),
                    "assigner": {"identifier": {"system": SID_LE, "value": ctx.key.submitter_id}}})
        paths.append(P + "identifier")
    xid = v.get("externalId")
    if xid:
        if CLINVAR_ID.match(str(xid)):
            ids.append({"use": "secondary", "system": CLINVAR, "value": str(xid)})
            comps.append(_comp(LOINC, "81252-9", valueCodeableConcept=_cc(CLINVAR, str(xid))))
        else:   # schema: "ClinVar variant ID"; values that are not ClinVar ids keep the value without a system
            ids.append({"use": "secondary", "value": str(xid), "type": {"text": "external variant id"}})
            ctx.warn(P + "externalId", f"not a ClinVar id: {xid!r}; kept as identifier without system")
        paths.append(P + "externalId")
    obs["identifier"] = ids

    # genes -> gene-studied (HGNC lock http://www.genenames.org; source system ignored)
    for g in v.get("genes") or []:
        code = (g or {}).get("code")
        if code:
            comps.append(_comp(LOINC, "48018-6", valueCodeableConcept=_cc(HGNC, code, g.get("display"))))
            paths.append(P + "genes[].code")

    chrom = v.get("chromosome")
    if chrom:
        if chrom in CHROMOSOME:
            comps.append(_comp(LOINC, "48000-4", valueCodeableConcept=_cc(LOINC, *CHROMOSOME[chrom])))
            paths.append(P + "chromosome")
        elif chrom == "MT":
            comps.append(_comp(LOINC, "48013-7", valueCodeableConcept=_cc(REFSEQ, *MT_REFSEQ)))
            paths.append(P + "chromosome")
            ctx.rep("chromosome-mt-genomic-ref-seq")
        else:
            ctx.drop(P + "chromosome", chrom, "not in LOINC LL2938-0")

    start, end = v.get("startPosition"), v.get("endPosition")
    if start is not None and end is not None and start > end:   # rng-2: low <= high
        ctx.drop(P + "startPosition", start, f"start > end ({end}); positions not emitted")
        ctx.drop(P + "endPosition", end, f"end < start ({start}); positions not emitted")
        start = end = None
    if start is not None or end is not None:
        # positions as given (KDK: GRCh38, VCF-style); coordinate system / assembly not asserted (inconsistent in the data)
        rng = {}
        if start is not None:
            rng["low"] = {"value": start}
            paths.append(P + "startPosition")
        if end is not None:
            rng["high"] = {"value": end}
            paths.append(P + "endPosition")
        comps.append(_comp(LOINC, "81254-5", valueRange=rng))

    if v.get("ref") not in (None, ""):
        comps.append(_comp(LOINC, "69547-8", valueString=v["ref"]))
        paths.append(P + "ref")
    if v.get("alt") not in (None, ""):
        comps.append(_comp(LOINC, "69551-0", valueString=v["alt"]))
        paths.append(P + "alt")

    notes = []
    for field, loinc, types in HGVS_FIELDS:
        s = (v.get(field) or "").strip()
        if not s:
            continue
        m = HGVS_EXPR.match(s)
        if m and m.group(1) in types and not HGVS_UNVALIDATABLE.search(s):
            comps.append(_comp(LOINC, loinc, valueCodeableConcept=_cc(HGVS, s)))
            paths.append(P + field)
        elif m and m.group(1) in types:   # well-formed, but not validatable against hgvs-vs (required binding)
            notes.append({"text": f"{field}: {s}"})
            ctx.preserve(P + field, "hgvs-not-validatable-note")
            ctx.warn(P + field, f"HGVS construct not validatable by the hgvs-vs terminology service: {s!r}; kept in Observation.note")
        else:   # hgvs-vs is a required binding: a malformed or mis-typed expression goes to the note
            notes.append({"text": f"{field}: {s}"})
            ctx.preserve(P + field, "hgvs-not-conformant-note")
            ctx.warn(P + field, f"not a {'/'.join(t + '.' for t in types)} HGVS expression: {s!r}; kept in Observation.note")

    if kind == "cnv" and v.get("type"):
        t = CNV_TYPE.get(v["type"])
        if t:
            comps.append(_comp(LOINC, "48019-4", valueCodeableConcept=_cc(SO, *t)))
            paths.append(P + "type")
        else:
            ctx.drop(P + "type", v["type"], "no SO copy-number term")

    if kind == "sv" and v.get("description"):
        comps.append(_comp(LOINC, "81291-7", valueCodeableConcept={"text": v["description"]}))
        paths.append(P + "description")

    z = v.get("zygosity")
    if z:
        if z in ZYGOSITY:
            comps.append(_comp(LOINC, "53034-5", valueCodeableConcept=_cc(LOINC, *ZYGOSITY[z])))
            paths.append(P + "zygosity")
        else:
            ctx.drop(P + "zygosity", z, "not in LOINC LL381-5")

    seg = v.get("segregationAnalysis")
    if seg:
        if seg in SEGREGATION:
            comps.append(_comp(LOINC, "94186-4", valueCodeableConcept=_cc(LOINC, *SEGREGATION[seg])))
            paths.append(P + "segregationAnalysis")
        elif seg == "fromMotherAndFather":
            comps.append(_comp(LOINC, "94186-4", valueCodeableConcept=cc(local_coding(CS_SEGREGATION, "biparental"))))
            ctx.preserve(P + "segregationAnalysis", "segregation-biparental-local-code")
        else:   # notPerformed: variant-inheritance value[x] is 1..1, dataAbsentReason alone is invalid (DISCUSS-TD #28)
            ctx.drop(P + "segregationAnalysis", seg, "no conformant representation (variant-inheritance value[x] 1..1)")

    obs["component"] = comps
    obs["note"] = notes
    ref = ctx.add(obs, *paths)
    if vid and ("variant", vid) not in ctx.ids:   # duplicate identifiers: the first finding is the link target
        ctx.ids[("variant", vid)] = ref
    ctx.bag["rd_report_results"].append(ref)

    _consequence(ctx, P, parts, v, ref)
    _implication(ctx, P, parts, v, ref)


def _consequence(ctx, P: str, parts: tuple, v: dict, vref: dict):
    """localization[] -> one molekulare-konsequenz with one feature-consequence per entry (DISCUSS-TD #26)."""
    comps, paths = [], []
    for loc in v.get("localization") or []:
        code = (loc or {}).get("code")
        if not code:
            continue
        so = translate(CM_LOCALIZATION, code)
        if not so:
            ctx.drop(P + "localization[].code", code, "not in mvgs-cm-rd-localization-so")
            continue
        comps.append(_comp(TBD_GR, "feature-consequence", valueCodeableConcept=cc(*so)))
        paths.append(P + "localization[].code")
    if not comps:
        return
    kon = ctx.new("Observation", "rd-consequence", *parts[1:], profile=KONSEQUENZ)
    kon.update(status="final", category=_categories(), code=_cc(TBD_GR, "molecular-consequence"),
               subject=ctx.patient, derivedFrom=[vref], component=comps)
    ctx.bag["rd_report_results"].append(ctx.add(kon, *paths))


def _implication(ctx, P: str, parts: tuple, v: dict, vref: dict):
    """ACMG class, mode of inheritance, finding category, ACMG criteria, publications -> diagnostische-implikation."""
    comps, paths = [], []

    acmg = v.get("acmgClass")
    if acmg:
        if acmg in ACMG_CLASS:
            comps.append(_comp(LOINC, "53037-8", valueCodeableConcept=_cc(LOINC, *ACMG_CLASS[acmg])))
            paths.append(P + "acmgClass")
        else:
            ctx.drop(P + "acmgClass", acmg, "not an ACMG class 1-5")

    moi = v.get("modeOfInheritance")
    if moi:
        if moi in INHERITANCE:
            comps.append(_comp(TBD_GR, "condition-inheritance", valueCodeableConcept=_cc(HPO, *INHERITANCE[moi])))
            paths.append(P + "modeOfInheritance")
        else:   # 'unclear': no HPO concept; text-only value under the preferred binding (REPRESENTATIONS #29)
            comps.append(_comp(TBD_GR, "condition-inheritance", valueCodeableConcept={"text": moi}))
            ctx.preserve(P + "modeOfInheritance", "mode-of-inheritance-text")

    sig = v.get("diagnosticSignificance")
    if sig:
        c = local_coding(CS_FINDING, sig)
        if c and sig != "finding-category":
            comps.append({"code": cc(local_coding(CS_FINDING, "finding-category")), "valueCodeableConcept": cc(c)})
            ctx.preserve(P + "diagnosticSignificance", "finding-category-local-component")
        else:
            ctx.drop(P + "diagnosticSignificance", sig, "not in mvgs-cs-finding-category")

    # ACMG criteria: component code = ClinGen criterion, value = strength (REPRESENTATIONS #30)
    for crit in v.get("acmgCriteria") or []:
        code = (crit or {}).get("value")
        if not code:
            continue
        comp = {"code": _cc(CLINGEN_ACMG, code)}
        mod = crit.get("modifier")
        if mod:
            strength = local_coding(CS_ACMG_STRENGTH, mod)
            if strength:
                comp["valueCodeableConcept"] = cc(strength)
                ctx.preserve(P + "acmgCriteria[].modifier", "acmg-criterion-strength-local-code")
            else:
                ctx.drop(P + "acmgCriteria[].modifier", mod, "not in mvgs-cs-rd-acmg-strength")
        comps.append(comp)
        ctx.preserve(P + "acmgCriteria[].value", "acmg-criterion-component")

    exts = []
    for pub in v.get("publications") or []:
        if pub in (None, ""):
            continue
        pub = str(pub).strip()
        pmid = pub.removeprefix("PMID:").strip()
        ra = {"type": "citation", "citation": pub}
        if pmid.isdigit():
            ra.update(label="PMID", citation=f"PMID:{pmid}", url=f"{PUBMED}{pmid}/")
        exts.append(ext(RELATED_ARTIFACT_EXT, valueRelatedArtifact=ra))
        paths.append(P + "publications[]")

    if not comps and not exts:
        return
    imp = ctx.new("Observation", "rd-implication", *parts[1:], profile=IMPLIKATION)
    imp.update(extension=exts, status="final", category=_categories(),
               code=_cc(TBD_GR, "diagnostic-implication"), subject=ctx.patient,
               derivedFrom=[vref], component=comps)
    ctx.bag["rd_report_results"].append(ctx.add(imp, *paths))
