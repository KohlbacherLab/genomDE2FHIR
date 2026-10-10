"""KDK molecular block -> mii-pr-mtb-ngs-bericht (DiagnosticReport) for the current submission.

No mapping row of its own: the container for every molecular finding. `result` lists ctx.bag['ngs_results'] in
pipeline order (simple variants + their consequences, CNVs, fusions, biomarkers, expression, signatures); the
profile's result slicing is open (discriminator resolve() profile), so each reference lands in its typed slice or
stays unsliced. The slices TumorMutionalBurden, MSI, Ploidie, HRDScore, BRCAness and Tumorzellgehalt are 0..1, and
every complexBiomarkers[] entry yields up to one TMB, HRD score and ploidy: with more than one such entry, each entry's
biomarkers go to a report of their own (id part 'complex-biomarker' + entry key) and the main report keeps the other
findings (omitted when none are left), so no report holds two results of a 0..1 slice and nothing is dropped.
(Tumorzellgehalt targets plain Observation, so every untyped result, e.g. molekulare-konsequenz, also matches it:
package defect, waived in validate.WAIVERS 'mtb-ngs-bericht-result-slice-overlap'; not addressed here.)
The KDK molecular block carries no report date, so `issued`/`effective[x]` stay empty (no invented timestamps).
Every report gets the genomic study link (mii-ex-mtb-ngs-bericht-genomic-study) when a builder registered
ctx.refs['genomic_study'] and is linked from the MTB Behandlungsepisode (ctx.refs['episode'], built by
onco.prior_procedures) via its own `investigation:NgsBericht` (0..*, code SNOMED 106221001, item 1..1 ->
mii-pr-mtb-ngs-bericht; the profile's designated link for the current NGS report, MS in 2026 and 2027).
Registers ctx.refs['ngs_report'] (the main report, else the first per-entry report). Prior findings stay in
`supportingInfo:Vorbefund` (onco.prior_diagnostics).
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
    sets = ctx.bag.get("ngs_biomarker_sets", [])
    if len(sets) > 1:   # several TMB / HRD / ploidy results would break the 0..1 result slices of one report
        moved = [r for _, refs in sets for r in refs]
        results = [r for r in results if r not in moved]
        ctx.warn("molecular.complexBiomarkers[].identifier",
                 f"{len(sets)} complexBiomarkers entries: mii-pr-mtb-ngs-bericht allows one TMB, HRD score and ploidy "
                 f"result each, so every entry's biomarkers are reported in a mii-pr-mtb-ngs-bericht of their own")
        ctx.rep("ngs-report-per-complex-biomarker-entry")
    else:
        sets = []
    refs = [_report(ctx, ("ngs-report",), results)] if results else []
    refs += [_report(ctx, ("ngs-report", "complex-biomarker", key), entry) for key, entry in sets]
    if refs:
        ctx.refs["ngs_report"] = refs[0]


def _report(ctx, id_parts: tuple, results: list) -> dict:
    dr = ctx.new("DiagnosticReport", *id_parts, profile=P_NGS)
    if ctx.refs.get("genomic_study"):
        dr["extension"] = [{"url": EX_GENOMIC_STUDY, "valueReference": ctx.refs["genomic_study"]}]
    dr["status"] = "final"
    dr["category"] = [{"coding": [coding("http://terminology.hl7.org/CodeSystem/v2-0074", "GE", "Genetics")]}]
    dr["code"] = {"coding": [coding(LOINC, "51969-4", "Genetic analysis report")]}
    dr["subject"] = ctx.patient
    dr["result"] = results
    ref = ctx.add(dr)
    link_episode(ctx, ref)
    return ref


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
