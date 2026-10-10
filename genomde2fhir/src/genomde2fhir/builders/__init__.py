"""Builders: one module per Datenkranz block. Each exposes `build(ctx)`; branch pipelines list the order.

Shared reference names (ctx.refs, set by `ctx.add(..., name=)`):
  patient, coverage, mv_consent, indication_board (mvgs-inclusion-decision CarePlan);
  oncology: primary (primary-tumour Condition), tnm, sequencing_request, episode (MTB Behandlungsepisode),
    ngs_report, careplan, followup_death;
  rare disease: rd_diagnosis, rd_report, zse_episode, careplan;
  GRZ: genomic_study, lab, org_<role> (genomic data center / clinical data node).
Source-id lookups (ctx.ids, first occurrence wins for duplicated source ids):
  ("variant", id), ("therapy_recommendation", id), ("therapy_recommendation_group", id),
  ("therapy_recommendation_member", recommendation id, ATC code) (per-substance MedicationRequest of a
  recommendation: set by onco.careplan, read by onco.followup), ("study_recommendation", id),
  ("preventive_measure", id), ("prior_procedure", index), ("rd_phenotype", hpo code), ("donor", pseudonym),
  ("specimen", pseudonym, labDataName), ("genomic_study_analysis", pseudonym, labDataName).
Collections (ctx.bag): ngs_results, ngs_biomarker_sets (onco.molecular_biomarkers -> onco.molecular_report:
  (entry key, [refs]) per complexBiomarkers entry), rd_report_results, rd_prior_reports, episode_supporting,
  careplan_activities, research_consents; per-file warn-once state: hgvs-unqualified-warned,
  plan_split_variant_ids.

Order matters: later builders reference resources registered in `ctx.refs` / `ctx.ids` by earlier ones
(Patient first, then diagnoses, then molecular findings, then plans that cite them, then follow-ups).
"""
from importlib import import_module

PIPELINES = {
    "oncology": [
        "patient", "coverage", "consent", "research_consent", "submission",
        "onco.diagnosis", "onco.tnm", "onco.ecog", "onco.prior_procedures", "onco.prior_diagnostics",
        "onco.molecular_variants", "onco.molecular_cnv", "onco.molecular_fusions",
        "onco.molecular_biomarkers", "onco.molecular_expression", "onco.molecular_signatures",
        "onco.molecular_report",
        "onco.careplan", "onco.recommendations", "onco.followup",
    ],
    "rare-disease": [
        "patient", "coverage", "consent", "research_consent", "submission",
        "rd.diagnosis", "rd.prior", "rd.variants", "rd.report", "rd.careplan", "rd.followup",
    ],
    "grz": [
        "grz.donors", "grz.labdata",
    ],
}


def pipeline(branch: str):
    """Resolve builder modules for a branch; modules not implemented yet are skipped with a note."""
    out = []
    for name in PIPELINES[branch]:
        try:
            out.append((name, import_module(f".{name}", __name__).build))
        except ModuleNotFoundError as ex:
            if ex.name and ex.name.endswith(name.split(".")[-1]):
                out.append((name, None))
            else:
                raise
    return out
