"""KDK rare-disease molecular block -> one MolGen molekulargenetischer-befundbericht (DiagnosticReport).

Results are the references collected by earlier builders in ctx.bag["rd_report_results"] (variante,
diagnostische-implikation, molekulare-konsequenz from rd.variants). Registers ctx.refs["rd_report"].
Emitted when the document has a molecular block or any result was collected. No report date: the KDK
molecular block carries none (the submission date is not the report date).
"""
from ...systems import LOINC, MOLGEN
from ..common import ext

BEFUNDBERICHT = MOLGEN + "StructureDefinition/molekulargenetischer-befundbericht"
GENOMIC_STUDY_EXT = "http://hl7.org/fhir/uv/genomics-reporting/StructureDefinition/genomic-study-reference"
V2_0074 = "http://terminology.hl7.org/CodeSystem/v2-0074"


def build(ctx):
    results = list(ctx.bag.get("rd_report_results") or [])
    if not results and not isinstance(ctx.dk.get("molecular"), dict):
        return
    seen, uniq = set(), []
    for r in results:
        if r["reference"] not in seen:
            seen.add(r["reference"])
            uniq.append(r)
    rep = ctx.new("DiagnosticReport", "rd-molecular-report", profile=BEFUNDBERICHT)
    study = ctx.refs.get("genomic_study")
    rep.update(
        extension=[ext(GENOMIC_STUDY_EXT, valueReference=study)] if study else [],
        status="final",
        category=[{"coding": [{"system": V2_0074, "code": "GE", "display": "Genetics"}]}],
        code={"coding": [{"system": LOINC, "code": "51969-4", "display": "Genetic analysis report"}]},
        subject=ctx.patient,
        result=uniq,
    )
    ctx.add(rep, name="rd_report")
