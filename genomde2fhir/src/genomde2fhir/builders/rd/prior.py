"""KDK rare-disease case.priorRds[] -> prior genetic diagnostics, hospitalisation bands, ZSE contact.

Rows: case.priorRds[].genomicTestType, .genomicStudyType, .diagnosticDate, .diagnosticResult,
.hospitalizationDuration, .hospitalizationPeriods, .zseContactDate (rare-disease table).
The synthetic/DNPM corpus delivers the pre-1.6.5 singular object `case.priorRd`; it is read as a one-element
`priorRds` (warning), since the content is identical. An empty array counts as an absent key, for either key
(`priorRds: []` plus `priorRd` -> the legacy key is read), as in the FML: matchbox parses [] as a missing key.

Per entry i
- ServiceRequest MolGen `anforderung-genetischer-test` (status completed, intent order) for the prior test:
  code = `mvgs-cs-genomic-test-type#<KDK literal>` (keeps read length and single-gene tests) plus the standard
  method type from `mvgs-cm-genomic-test-type-method-type` (MTB WES/WGS/panel codes, GR microarray/karyotyping/other;
  `single` has none) - same codes as the oncology prior findings (REPRESENTATIONS #12);
  genomicStudyType -> `mvgs-ex-genomic-study-design` (DISCUSS-TD #31; upstream DNPM export hard-codes `single`).
  genomicTestType `none` (no prior test): no request and no report; result/date/study type dropped.
- DiagnosticReport MolGen `molekulargenetischer-befundbericht` (REVIEW-TD A: diagnosticDate / diagnosticResult belong
  here, not on `variante`): basedOn -> request, effectiveDateTime = diagnosticDate, conclusion = diagnosticResult
  label (`other` -> no conclusion, dropped). Collected in ctx.bag['rd_prior_reports'].
- Observations (DISCUSS-TD #33, REPRESENTATIONS #33, HDB-975 pending): hospitalizationDuration /
  hospitalizationPeriods -> generic Observation (category survey), code and value from the local band CodeSystems
  `mvgs-cs-hospitalization-duration` / `-periods` (codes = KDK literals); `unknown` -> dataAbsentReason unknown.
  effective = board date (molecularBoardDecisionDate) when present. Preserved (no MII profile).
- zseContactDate (first contact with a Zentrum fuer Seltene Erkrankungen, YYYY-MM) -> one EpisodeOfCare
  (status active) with period.start = earliest date over all entries; registered as ctx.refs['zse_episode'].
"""
from ...systems import LOINC, MOLGEN
from ...terminology import local_coding, translate
from ..common import cc, coding, dar_cc, obs_category
from .diagnosis import P_REQUEST, board_date, study_design_ext

MOLGEN_REPORT = MOLGEN + "StructureDefinition/molekulargenetischer-befundbericht"
V2_0074 = "http://terminology.hl7.org/CodeSystem/v2-0074"
CS_TEST_TYPE = "mvgs-cs-genomic-test-type"
CM_TEST_TYPE = "mvgs-cm-genomic-test-type-method-type"
STUDY_TYPES = ("single", "duo", "trio")

PFX = "case.priorRds[]."

RESULT = {
    "phenotypeNotCompletelyClarified": "Phenotype not completely clarified by the prior diagnostics",
    "structuralVariantWithUnclearBreakpoint": "Structural variant with unclear breakpoint",
    "unclearVariantInGeneticDisease": "Variant of unclear significance in a gene associated with a genetic disease",
    "noPathogenicVariantDetected": "No pathogenic variant detected",
}
HOSP = {   # field -> (CodeSystem name, band codes)
    "hospitalizationDuration": ("mvgs-cs-hospitalization-duration",
                                ("none", "upToFive", "upToFifteen", "upToFifty", "moreThanFifty")),
    "hospitalizationPeriods": ("mvgs-cs-hospitalization-periods",
                               ("none", "upToFive", "upToTen", "upToFifteen", "moreThanFifteen")),
}
OBS_CODE = {"hospitalizationDuration": "hospitalization-duration", "hospitalizationPeriods": "hospitalization-periods"}


def entries(ctx) -> list[dict]:
    case = ctx.dk.get("case") or {}
    items = case.get("priorRds")
    if items in (None, []) and case.get("priorRd") not in (None, []):   # [] = absent (module docstring, FML parity)
        legacy = case["priorRd"]
        items = legacy if isinstance(legacy, list) else [legacy]
        ctx.warn("case.priorRds[]", "legacy key case.priorRd (KDK < 1.6.5) read as priorRds")
        if any(isinstance(p, dict) for p in items):
            ctx.cover_undeclared("case.priorRd")   # only when read: next to a non-empty priorRds it stays unread
    return [p for p in (items or []) if isinstance(p, dict)]


def _test_code(ctx, test_type: str) -> dict | None:
    local = local_coding(CS_TEST_TYPE, test_type)
    if not local:
        return None
    return cc(local, *translate(CM_TEST_TYPE, test_type))


def _request(ctx, i: int, pr: dict) -> dict | None:
    tt = pr.get("genomicTestType")
    if tt == "none":
        ctx.drop(PFX + "genomicTestType", tt, "no prior genetic test: no request/report emitted")
        for k in ("genomicStudyType", "diagnosticResult", "diagnosticDate"):
            if pr.get(k):
                ctx.drop(PFX + k, pr[k], "genomicTestType none: no prior test to attach it to")
        return None
    sr = ctx.new("ServiceRequest", "prior_rd", i, "test", profile=P_REQUEST)
    code = _test_code(ctx, tt) if tt else None
    if code and len(code["coding"]) > 1:   # standard method-type from the ConceptMap (REPRESENTATIONS #12)
        ctx.cover(PFX + "genomicTestType")
    elif code:                             # 'single': local code only
        ctx.preserve(PFX + "genomicTestType", "genomic-test-type-local-code")
    elif tt:
        ctx.drop(PFX + "genomicTestType", tt, "unknown genomic test type")
    st = pr.get("genomicStudyType")
    if st in STUDY_TYPES:
        sr["extension"] = [study_design_ext(st)]
        ctx.preserve(PFX + "genomicStudyType", "genomic-study-design-extension")
    elif st:
        ctx.drop(PFX + "genomicStudyType", st, "unknown genomic study type")
    sr.update(status="completed", intent="order", code=code, subject=dict(ctx.patient))
    if ctx.refs.get("rd_diagnosis"):
        sr["reasonReference"] = [dict(ctx.refs["rd_diagnosis"])]
    return ctx.add(sr)


def _report(ctx, i: int, pr: dict, request: dict):
    rep = ctx.new("DiagnosticReport", "prior_rd", i, "report", profile=MOLGEN_REPORT)
    paths = []
    res = pr.get("diagnosticResult")
    if res in RESULT:
        rep["conclusion"] = RESULT[res]
        paths.append(PFX + "diagnosticResult")
    elif res == "other":
        ctx.drop(PFX + "diagnosticResult", res, "catch-all 'other': no conclusion text")
    elif res:
        ctx.drop(PFX + "diagnosticResult", res, "unknown diagnostic result")
    if pr.get("diagnosticDate"):
        paths.append(PFX + "diagnosticDate")
    rep.update(
        basedOn=[dict(request)],
        status="final",
        category=[{"coding": [coding(V2_0074, "GE", "Genetics")]}],
        code={"coding": [coding(LOINC, "51969-4", "Genetic analysis report")]},
        subject=dict(ctx.patient),
        effectiveDateTime=pr.get("diagnosticDate"),
    )
    ctx.bag["rd_prior_reports"].append(ctx.add(rep, *paths))


def _hospitalization(ctx, i: int, pr: dict, field: str, date: str | None):
    val = pr.get(field)
    if not val:
        return
    cs, bands = HOSP[field]
    o = ctx.new("Observation", "prior_rd", i, OBS_CODE[field])
    o.update(status="final", category=obs_category("survey"),
             code=cc(local_coding(cs, OBS_CODE[field])), subject=dict(ctx.patient), effectiveDateTime=date)
    if val in bands:
        o["valueCodeableConcept"] = cc(local_coding(cs, val))
    elif val == "unknown":
        o["dataAbsentReason"] = dar_cc("unknown")
    else:
        ctx.drop(PFX + field, val, "unknown band")
        return
    ctx.add(o)
    ctx.preserve(PFX + field, "hospitalization-band-local-code")


def _zse_episode(ctx, items: list[dict]):
    dates = sorted({p["zseContactDate"] for p in items if p.get("zseContactDate")})
    if not dates:
        return
    if len(dates) > 1:
        ctx.warn(PFX + "zseContactDate", f"different ZSE contact dates {dates}; earliest used as episode start")
    ep = ctx.new("EpisodeOfCare", "zse_episode")
    ep.update(status="active",
              type=[{"text": "Care at a centre for rare diseases (Zentrum fuer Seltene Erkrankungen, ZSE)"}],
              patient=dict(ctx.patient), period={"start": dates[0]})
    ctx.add(ep, PFX + "zseContactDate", name="zse_episode")


def build(ctx):
    items = entries(ctx)
    if not items:
        return
    date = board_date(ctx)
    for i, pr in enumerate(items):
        request = _request(ctx, i, pr)
        if request:
            _report(ctx, i, pr, request)
        for field in HOSP:
            _hospitalization(ctx, i, pr, field, date)
    _zse_episode(ctx, items)
