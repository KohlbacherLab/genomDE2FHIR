"""KDK molecular block -> one mii-pr-mtb-ngs-bericht (DiagnosticReport) for the current submission.

No mapping row of its own: the container for every molecular finding. `result` lists ctx.bag['ngs_results'] in
pipeline order (simple variants + their consequences, CNVs, fusions, biomarkers, expression, signatures); the
profile's result slicing is open (discriminator resolve() profile), so each reference lands in its typed slice or
stays unsliced. The KDK molecular block carries no report date, so `issued`/`effective[x]` stay empty (no
invented timestamps). Genomic study link (mii-ex-mtb-ngs-bericht-genomic-study) when a builder registered
ctx.refs['genomic_study']. Registers ctx.refs['ngs_report'] and links the report from the MTB Behandlungsepisode
(ctx.refs['episode'], built by onco.prior_procedures) via `investigation:NgsBericht` (code SNOMED 106221001, item 1..1 ->
mii-pr-mtb-ngs-bericht; the profile's designated link for the current NGS report, MS in 2026 and 2027). Prior findings
stay in `supportingInfo:Vorbefund` (onco.prior_diagnostics).
"""
from ...systems import LOINC, MTB, SNOMED
from ..common import coding

P_NGS = MTB + "StructureDefinition/mii-pr-mtb-ngs-bericht"
EX_GENOMIC_STUDY = MTB + "StructureDefinition/mii-ex-mtb-ngs-bericht-genomic-study"


def build(ctx):
    results = []
    for r in ctx.bag.get("ngs_results", []):
        if r not in results:
            results.append(r)
    if not results:
        return
    dr = ctx.new("DiagnosticReport", "ngs-report", profile=P_NGS)
    if ctx.refs.get("genomic_study"):
        dr["extension"] = [{"url": EX_GENOMIC_STUDY, "valueReference": ctx.refs["genomic_study"]}]
    dr["status"] = "final"
    dr["category"] = [{"coding": [coding("http://terminology.hl7.org/CodeSystem/v2-0074", "GE", "Genetics")]}]
    dr["code"] = {"coding": [coding(LOINC, "51969-4", "Genetic analysis report")]}
    dr["subject"] = ctx.patient
    dr["result"] = results
    ref = ctx.add(dr, name="ngs_report")
    link_episode(ctx, ref)


def link_episode(ctx, ref: dict):
    """Append investigation:NgsBericht -> ref to the Behandlungsepisode (same in-place pattern as
    prior_procedures.episode_add, which only covers supportingInfo)."""
    ep_ref = ctx.refs.get("episode")
    if not ep_ref or ep_ref["reference"] not in ctx.bundle.entries:
        return
    ep = ctx.bundle.entries[ep_ref["reference"]]["resource"]
    inv = {"code": {"coding": [coding(SNOMED, "106221001", "Genetic finding")]}, "item": [ref]}
    investigations = ep.setdefault("investigation", [])
    if inv not in investigations:
        investigations.append(inv)
