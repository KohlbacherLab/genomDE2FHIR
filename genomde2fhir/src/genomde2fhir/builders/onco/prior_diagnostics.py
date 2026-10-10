"""KDK case.priorDiagnostics[] -> one MTB NGS report per prior genetic test (REPRESENTATIONS #12, REVIEW-TD A, DISCUSS-TD #12).

Rows: case.priorDiagnostics[].type, .date, .complexVariants[], .simpleVariants[].{gene,transcript,variantTypes[]}.*,
.simpleVariants[].dnaChange, .proteinChange.

Per prior test:
- DiagnosticReport `mii-pr-mtb-ngs-bericht` (code LOINC 51969-4, category GE): date -> effectiveDateTime (only `issued`, an instant,
  is MS; the source date is day-precision); complexVariants[] (free text) -> conclusion (one line each);
  result:EinfacheVariante -> the simple variants; linked from the Behandlungsepisode supportingInfo:Vorbefund
  (ctx.refs['episode'], created by prior_procedures) and to its genomic study via mii-ex-mtb-ngs-bericht-genomic-study.
- Procedure `mii-pr-mtb-genomic-study` (code = the Datenkranz test type from mvgs-cs-genomic-test-type, example binding, keeps
  short/long read and single-gene tests) with extension:genomic-study-analysis -> Procedure `mii-pr-mtb-genomic-study-analysis`
  carrying extension:method-type from mvgs-cm-genomic-test-type-method-type (exome/genome*/panel -> MII codes,
  array/karyotyping/other -> GR codes). `single` has no method concept (method-type omitted, value preserved in the study code);
  `none` -> no study and no report (dropped) unless findings are attached.
- Observation `mii-pr-mtb-einfache-variante` per simple variant: value LA9633-4 Present (LL1971-2, value[x] closed in 2027);
  components gene-studied (HGNC `http://www.genenames.org`, terminology lock), representative-coding-hgvs (dnaChange),
  representative-protein-hgvs (proteinChange), both qualified with the versioned transcript accession as for the current
  findings (molecular_variants helpers; a bare `c.`/`p.` without reference sequence stays unqualified and fails the
  hgvs-vs check = source data quality), representative-transcript-ref-seq (Ensembl/RefSeq system by prefix,
  REPRESENTATIONS #10), coding-change-type (all SO variantTypes as codings of one CodeableConcept, REPRESENTATIONS #11).

The legacy single-object key `case.priorDiagnostic` (pre-1.6.5 synthetic data, same fields) is treated as one more entry
with the next array index as id part (0 without priorDiagnostics[], like rd.prior), so its resource ids equal those of
the same test resent as priorDiagnostics[0] (docs/IDENTITY.md: prior diagnostics keep their array index).
"""
from ...systems import GR, HGVS, LOINC, MTB, REFSEQ, SO
from ... import terminology
from ..common import cc, coding
from .molecular_variants import (hgnc_coding, qualify_hgvs, so_system, transcript_accession, transcript_system,
                                 warn_unqualified)
from .prior_procedures import episode_add, ensure_episode

P_REPORT = MTB + "StructureDefinition/mii-pr-mtb-ngs-bericht"
P_VARIANT = MTB + "StructureDefinition/mii-pr-mtb-einfache-variante"
P_STUDY = MTB + "StructureDefinition/mii-pr-mtb-genomic-study"
P_ANALYSIS = MTB + "StructureDefinition/mii-pr-mtb-genomic-study-analysis"
EXT_REPORT_STUDY = MTB + "StructureDefinition/mii-ex-mtb-ngs-bericht-genomic-study"
EXT_STUDY_ANALYSIS = GR + "StructureDefinition/genomic-study-analysis-ext"
EXT_METHOD_TYPE = GR + "StructureDefinition/genomic-study-analysis-method-type"
CS_TEST_TYPE = "mvgs-cs-genomic-test-type"
CM_METHOD_TYPE = "mvgs-cm-genomic-test-type-method-type"

V2_0074 = "http://terminology.hl7.org/CodeSystem/v2-0074"
GE_CATEGORY = cc(coding(V2_0074, "GE", "Genetics"))
REPORT_CODE = cc(coding(LOINC, "51969-4", "Genetic analysis report"))
VARIANT_CODE = cc(coding(LOINC, "69548-6", "Genetic variant assessment"))
PRESENT = cc(coding(LOINC, "LA9633-4", "Present"))
LAB_CATEGORY = cc(coding("http://terminology.hl7.org/CodeSystem/observation-category", "laboratory"))

BASE = "case.priorDiagnostics[]."
SV = BASE + "simpleVariants[]."


def _component(loinc: str, display: str, value: dict | None) -> dict | None:
    if not value:
        return None
    return {"code": cc(coding(LOINC, loinc, display)), "valueCodeableConcept": value}


def _variant(ctx, key, j: int, v: dict, date: str | None) -> dict:
    """Same representation as the current-finding variants (molecular_variants helpers): HGNC lock, transcript system
    by accession prefix, HGVS qualified with a versioned transcript accession (c.: 'NM_x.v:c..', p.: ClinVar style
    'NM_x.v(GENE):p..'; the KDK string is kept as CodeableConcept.text), all SO variant types in one CodeableConcept."""
    paths = []
    obs = ctx.new("Observation", "prior_diagnostic", key, "variant", j, profile=P_VARIANT)
    obs["status"] = "final"
    obs["category"] = [LAB_CATEGORY, GE_CATEGORY]
    obs["code"] = VARIANT_CODE
    obs["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        obs["focus"] = [ctx.refs["primary"]]
    obs["effectiveDateTime"] = date
    obs["valueCodeableConcept"] = PRESENT
    comps = []

    g = v.get("gene") or {}
    gc, gp = hgnc_coding(ctx, g, SV + "gene.")
    if gc:
        if g.get("system") and gc["system"] != g["system"]:
            ctx.rep("hgnc-system-normalised")
        comps.append(_component("48018-6", "Gene studied [ID]", cc(gc)))
        paths += gp
    elif g.get("display"):
        comps.append(_component("48018-6", "Gene studied [ID]", cc(text=g["display"])))
        paths.append(SV + "gene.display")

    t = v.get("transcript") or {}
    acc = transcript_accession(t)
    for field, loinc, display, kind in (("dnaChange", "48004-6", "DNA change (c.HGVS)", "c"),
                                        ("proteinChange", "48005-3", "Amino acid change (pHGVS)", "p")):
        raw = (v.get(field) or "").strip()
        if not raw:
            continue
        expr = qualify_hgvs(raw, acc, g.get("display") if kind == "p" else None)
        if expr == raw and ":" not in raw:   # no usable reference sequence in the source (residual hgvs-vs error)
            warn_unqualified(ctx, SV + field, t, acc)
        comps.append(_component(loinc, display, cc(coding(HGVS, expr), text=raw if expr != raw else None)))
        paths.append(SV + field)

    if t.get("code"):
        system = transcript_system(str(t["code"]), t.get("system"))
        if system == REFSEQ:
            ctx.rep("transcript-refseq-vs-mtb-ensembl-binding")   # MTB binds required to http://ensembl.org (DISCUSS-TD #10)
        if not system:
            ctx.warn(SV + "transcript.system", f"transcript {t['code']!r} without a recognisable system")
        comps.append(_component("51958-7", "Transcript reference sequence [ID]",
                                cc(coding(system, t["code"], t.get("display"), t.get("version")))))
        paths += [SV + "transcript." + k for k in ("code", "display", "system", "version") if t.get(k)]

    vts = [vt for vt in v.get("variantTypes") or [] if vt and vt.get("code")]
    if vts:
        comps.append(_component("48019-4", "DNA change type", cc(*[
            coding(so_system(vt.get("system"), vt["code"]) or SO, vt["code"], vt.get("display"), vt.get("version"))
            for vt in vts])))
        paths += [SV + "variantTypes[]." + k for k in ("code", "display", "system", "version")
                  if any(vt.get(k) for vt in vts)]
        if len(vts) > 1:
            ctx.rep("variant-types-multi-coding")
    obs["component"] = comps
    return ctx.add(obs, *paths)


def _study(ctx, key, ptype: str, date: str | None) -> dict:
    """genomic-study-analysis (method-type) + genomic-study (Datenkranz test type); returns the study reference."""
    method = terminology.translate(CM_METHOD_TYPE, ptype)
    an = ctx.new("Procedure", "prior_diagnostic", key, "analysis", profile=P_ANALYSIS)
    if method:
        an["extension"] = [{"url": EXT_METHOD_TYPE, "valueCodeableConcept": cc(*method)}]
    an["status"] = "completed"
    an["category"] = LAB_CATEGORY
    an["subject"] = ctx.patient
    an["performedDateTime"] = date
    an_ref = ctx.add(an)

    st = ctx.new("Procedure", "prior_diagnostic", key, "study", profile=P_STUDY)
    st["extension"] = [{"url": EXT_STUDY_ANALYSIS, "valueReference": an_ref}]
    st["status"] = "completed"
    st["category"] = LAB_CATEGORY
    local = terminology.local_coding(CS_TEST_TYPE, ptype)
    st["code"] = cc(local, text="Vorbefund: genetische Untersuchung")
    st["subject"] = ctx.patient
    st["performedDateTime"] = date
    if ctx.refs.get("primary"):
        st["reasonReference"] = [ctx.refs["primary"]]
    if method:
        ref = ctx.add(st, BASE + "type")
        if ptype.startswith("genome"):
            ctx.rep("prior-test-read-length-in-study-code")
    else:
        ref = ctx.add(st)
        ctx.preserve(BASE + "type", "prior-test-type-local-code-only")
        ctx.warn(BASE + "type", f"{ptype!r} has no method-type concept; kept as mvgs-cs-genomic-test-type study code")
    return ref


def build(ctx):
    case = ctx.dk.get("case") or {}
    items = [(i, pd) for i, pd in enumerate(case.get("priorDiagnostics") or [])]
    legacy = case.get("priorDiagnostic")
    if isinstance(legacy, dict) and legacy:
        ctx.warn("case.priorDiagnostic", "legacy single-object key (pre-KDK 1.6.5) treated as a priorDiagnostics entry")
        items.append((len(items), legacy))
    if not items:
        return
    ensure_episode(ctx)
    valid_types = {c["code"] for c in terminology.code_system(CS_TEST_TYPE)["concept"]}
    for key, pd in items:
        if _report(ctx, key, pd, valid_types) and pd is legacy:
            ctx.cover_undeclared("case.priorDiagnostic")   # converted as a priorDiagnostics entry


def _report(ctx, key, pd: dict, valid_types: set):
    """The NGS report of one prior test; returns its reference, None when nothing is emitted (type 'none')."""
    ptype, date = pd.get("type"), pd.get("date")
    svs = pd.get("simpleVariants") or []
    cvs = [c for c in pd.get("complexVariants") or [] if c]
    if ptype == "none" and not svs and not cvs:
        ctx.drop(BASE + "type", "none", "no prior genetic test performed: no study or report emitted")
        if date:
            ctx.drop(BASE + "date", date, "date of a prior test of type 'none'")
        return

    paths = []
    rep = ctx.new("DiagnosticReport", "prior_diagnostic", key, profile=P_REPORT)
    if ptype in valid_types and ptype != "none":
        rep["extension"] = [{"url": EXT_REPORT_STUDY, "valueReference": _study(ctx, key, ptype, date)}]
    elif ptype == "none":
        ctx.drop(BASE + "type", "none", "type 'none' with findings: report without genomic study")
    elif ptype:
        ctx.drop(BASE + "type", ptype, "not a Datenkranz prior test type")
    rep["status"] = "final"
    rep["category"] = [GE_CATEGORY]
    rep["code"] = REPORT_CODE
    rep["subject"] = ctx.patient
    if date:
        rep["effectiveDateTime"] = date
        paths.append(BASE + "date")
    rep["result"] = [_variant(ctx, key, j, v, date) for j, v in enumerate(svs)]
    if cvs:
        rep["conclusion"] = "\n".join(cvs)
        paths.append(BASE + "complexVariants[]")
        ctx.rep("prior-complex-variants-conclusion")
    ref = ctx.add(rep, *paths)
    episode_add(ctx, ref)
    return ref
