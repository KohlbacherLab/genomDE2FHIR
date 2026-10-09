"""KDK rare-disease case.diagnosisRd -> Seltene diagnosis Condition, HPO assessments, GMFCS, genetic-test request.

Rows: case.diagnosisRd.diagnoses[].{code,display,system,version}, .noMatchingCodeExists, .diagnosticAssessment,
.symptomOnsetDate, .molecularBoardDecisionDate, .phenotypes[].{code,display,system,version,text},
.diagnosisGmfcs, .libraryType, .diagnosticExtent (rare-disease table).

Resources
- Condition (registered as ctx.refs['rd_diagnosis']). Profile by `diagnosticAssessment`:
  confirmed / partial / suspected genetic diagnosis -> `mii-pr-seltene-genetic-diagnosis` (category 782964007),
  noGeneticDiagnosis / furtherGeneticDiagnosticRecommended -> `mii-pr-seltene-clinical-diagnosis`
  (category encounter-diagnosis, as in the Seltene examples). verificationStatus per table: confirmed -> confirmed,
  partial -> differential, suspected -> provisional, no / further -> unconfirmed; the KDK literal's display goes to
  verificationStatus.text (keeps "partial" readable). furtherGeneticDiagnosticRecommended additionally yields a
  ServiceRequest (below). No clinicalStatus: the KDK does not state it.
  code.coding from diagnoses[]: ICD-10-GM (slice icd10-gm, version 1..1), ORPHA (`https://www.orpha.net` ->
  `http://www.orpha.net`, prefix `ORPHA:` stripped), Alpha-ID-SE (BfArM page URL -> `http://fhir.de/CodeSystem/bfarm/alpha-id`).
  onsetDateTime = symptomOnsetDate (YYYY-MM; 2027 closed onset to dateTime/Age, onsetPeriod removed);
  recordedDate (1..1) = molecularBoardDecisionDate.
  evidence: one entry `geneticEvidence` (SCT 106221001) -> the RD Befundbericht (built later by rd.report under the
  deterministic id ("rd-molecular-report"), present whenever the document has a `molecular` block), and one entry
  per phenotype (code = HPO term, detail = its HPO assessment), as in the Seltene examples (genetic-diagnosis needs
  evidence.detail 1..*). A second ICD-10-GM / ORPHA / Alpha-ID code is dropped (code.coding slices are 0..1).
  noMatchingCodeExists = true: no DAR code expresses "no matching code" (DAR has no such concept, the extension is
  required-bound) -> Condition.note + preserved; false needs no element.
- Observation `mii-pr-seltene-hpo-assessment` per phenotype: code = HPO (`https://hpo.jax.org` normalised to
  `http://human-phenotype-ontology.org`, version kept), code.text = phenotypes[].text, component:status = LOINC
  LA9633-4 Present (the KDK lists the patient's phenotypes). No effective date: the KDK gives none.
  Registered as ctx.ids[('rd_phenotype', code)].
- GMFCS (DISCUSS-TD #32, REPRESENTATIONS #32, HDB-975): generic Observation (category survey), code SCT 707621005,
  value LOINC LL1594-2 answer (I LA16552-4 ... V LA16558-1), effective = board date; preserved (no MII profile).
- libraryType + diagnosticExtent: MolGen `anforderung-genetischer-test` (intent order) for the MV sequencing the
  board decided: code = MTB method type (wes/wgs/wgs_lr/panel; long read kept in code.text), diagnosticExtent ->
  `mvgs-ex-genomic-study-design` (singleGenome/duoGenome/trioGenome -> single/duo/trio, DISCUSS-TD #31);
  libraryType `none` ("no sequencing indicated") -> doNotPerform = true. reasonReference -> diagnosis.
- furtherGeneticDiagnosticRecommended -> second `anforderung-genetischer-test` (intent proposal), added to
  ctx.bag['careplan_activities'] for the Seltene Therapieplan.
"""
from ...systems import (ALPHA_ID, COND_VER, HPO, ICD10GM, LOINC, MOLGEN, MTB, MVGS_CS, MVGS_SD, ORPHA, SELTENE,
                        SNOMED)
from ..common import cc, coding, ext, icd10gm, obs_category

P_GENETIC = SELTENE + "StructureDefinition/mii-pr-seltene-genetic-diagnosis"
P_CLINICAL = SELTENE + "StructureDefinition/mii-pr-seltene-clinical-diagnosis"
P_HPO = SELTENE + "StructureDefinition/mii-pr-seltene-hpo-assessment"
P_REQUEST = MOLGEN + "StructureDefinition/anforderung-genetischer-test"
EX_STUDY_DESIGN = MVGS_SD + "mvgs-ex-genomic-study-design"
CS_STUDY_DESIGN = MVGS_CS + "mvgs-cs-genomic-study-design"
CS_MTB_METHOD = MTB + "CodeSystem/mii-cs-mtb-genomic-analysis-method-type"
COND_CATEGORY = "http://terminology.hl7.org/CodeSystem/condition-category"
RD_REPORT_ID = "rd-molecular-report"      # id part used by builders/rd/report.py

PFX = "case.diagnosisRd."

# diagnosticAssessment -> (profile, verificationStatus, display of the KDK value)
ASSESSMENT = {
    "confirmedGeneticDiagnosis": (P_GENETIC, "confirmed", "Confirmed genetic diagnosis"),
    "partialGeneticDiagnosis": (P_GENETIC, "differential", "Partial genetic diagnosis"),
    "suspectedGeneticDiagnosis": (P_GENETIC, "provisional", "Suspected genetic diagnosis"),
    "noGeneticDiagnosis": (P_CLINICAL, "unconfirmed", "No genetic diagnosis"),
    "furtherGeneticDiagnosticRecommended": (P_CLINICAL, "unconfirmed", "Further genetic diagnostics recommended"),
}

# source system (lower-cased, trailing slash stripped) -> FHIR system
DX_SYSTEMS = {
    "http://fhir.de/codesystem/bfarm/icd-10-gm": ICD10GM,
    "https://www.orpha.net": ORPHA,
    "http://www.orpha.net": ORPHA,
    "https://www.bfarm.de/de/kodiersysteme/terminologien/alpha-id-se": ALPHA_ID,
    "http://fhir.de/codesystem/bfarm/alpha-id": ALPHA_ID,
}
HPO_SYSTEMS = {"https://hpo.jax.org", "http://hpo.jax.org", "http://human-phenotype-ontology.org",
               "https://human-phenotype-ontology.org", "http://www.human-phenotype-ontology.org"}

GMFCS_CODE = coding(SNOMED, "707621005", "Gross motor function classification system for cerebral palsy")
GMFCS_LEVELS = {"I": "LA16552-4", "II": "LA15151-6", "III": "LA15150-8", "IV": "LA16556-5", "V": "LA16558-1"}

LIBRARY = {   # libraryType -> (MTB method-type code, display, text)
    "wes": ("whole-exom-sequencing", "Whole Exom Sequencing (WES)", "Whole exome sequencing"),
    "wgs": ("whole-genom-sequencing", "Whole Genom Sequencing (WGS)", "Whole genome sequencing (short read)"),
    "wgs_lr": ("whole-genom-sequencing", "Whole Genom Sequencing (WGS)", "Whole genome sequencing (long read)"),
    "panel": ("gene-panel", "Genpanel", "Gene panel sequencing"),
}
EXTENT = {"singleGenome": "single", "duoGenome": "duo", "trioGenome": "trio"}
STUDY_DESIGN_DISPLAY = {"single": "Single (index only)", "duo": "Duo", "trio": "Trio"}


def study_design_ext(code: str) -> dict:
    return ext(EX_STUDY_DESIGN, valueCoding=coding(CS_STUDY_DESIGN, code, STUDY_DESIGN_DISPLAY.get(code)))


def board_date(ctx) -> str | None:
    return ((ctx.dk.get("case") or {}).get("diagnosisRd") or {}).get("molecularBoardDecisionDate")


def _dx_coding(ctx, dx: dict) -> dict | None:
    code, system = dx.get("code"), (dx.get("system") or "")
    if not code:
        return None
    target = DX_SYSTEMS.get(system.lower().rstrip("/"))
    if target == ORPHA and str(code).upper().startswith("ORPHA:"):
        code = str(code)[6:]
    if not target:
        ctx.warn(PFX + "diagnoses[].system", f"unexpected diagnosis code system {system!r}; coding kept as delivered")
        target = system or None
    if target == ICD10GM:
        return icd10gm(code, dx.get("display"), dx.get("version"))
    return coding(target, code, dx.get("display"), dx.get("version"))


def _phenotypes(ctx, d: dict) -> list[tuple[dict, dict]]:
    """HPO assessments; returns (reference, HPO coding) per distinct phenotype."""
    refs, seen = [], set()
    for ph in d.get("phenotypes") or []:
        code = ph.get("code")
        if not code:
            continue
        if code in seen:
            ctx.warn(PFX + "phenotypes[].code", f"phenotype {code} listed twice; emitted once")
            continue
        seen.add(code)
        system = ph.get("system")
        paths = [PFX + "phenotypes[].code"]
        if system and system.rstrip("/") not in HPO_SYSTEMS:
            ctx.warn(PFX + "phenotypes[].system", f"phenotype system {system!r} is not HPO; HPO assumed")
        if system:
            paths.append(PFX + "phenotypes[].system")
        if not str(code).startswith("HP:"):
            ctx.warn(PFX + "phenotypes[].code", f"not an HPO id: {code!r}")
        paths += [PFX + f"phenotypes[].{k}" for k in ("display", "version", "text") if ph.get(k)]
        hpo = coding(HPO, code, ph.get("display"), ph.get("version"))
        o = ctx.new("Observation", "rd_phenotype", code, profile=P_HPO)
        o.update(
            status="final",
            code=cc(dict(hpo), text=ph.get("text")),
            subject=dict(ctx.patient),
            component=[{"code": {"coding": [coding(SNOMED, "260411009", "Presence findings")]},
                        "valueCodeableConcept": {"coding": [coding(LOINC, "LA9633-4", "Present")]}}],
        )
        ref = ctx.add(o, *paths)
        ctx.ids[("rd_phenotype", code)] = ref
        refs.append((ref, hpo))
    return refs


def _gmfcs(ctx, d: dict, date: str | None):
    level = d.get("diagnosisGmfcs")
    if not level:
        return
    la = GMFCS_LEVELS.get(level)
    if not la:
        ctx.drop(PFX + "diagnosisGmfcs", level, "not a GMFCS level I-V")
        return
    o = ctx.new("Observation", "rd_gmfcs", "diagnosis")
    o.update(
        status="final",
        category=obs_category("survey"),
        code=cc(dict(GMFCS_CODE)),
        subject=dict(ctx.patient),
        effectiveDateTime=date,
        valueCodeableConcept=cc(coding(LOINC, la), text=f"GMFCS level {level}"),
    )
    ctx.add(o)
    ctx.preserve(PFX + "diagnosisGmfcs", "gmfcs-generic-observation")


def _sequencing_request(ctx, d: dict, date: str | None, diagnosis: dict):
    lib, extent = d.get("libraryType"), d.get("diagnosticExtent")
    if not lib and not extent:
        return
    sr = ctx.new("ServiceRequest", "rd_sequencing_request", profile=P_REQUEST)
    paths = []
    if lib == "none":
        sr["doNotPerform"] = True
        sr["code"] = {"text": "Genome sequencing (Modellvorhaben Genomsequenzierung): not indicated"}
        paths.append(PFX + "libraryType")
    elif lib in LIBRARY:
        c, disp, text = LIBRARY[lib]
        sr["code"] = cc(coding(CS_MTB_METHOD, c, disp), text=text)
        paths.append(PFX + "libraryType")
    elif lib:
        ctx.drop(PFX + "libraryType", lib, "unknown library type")
    if extent in EXTENT:
        sr["extension"] = [study_design_ext(EXTENT[extent])]
        ctx.preserve(PFX + "diagnosticExtent", "genomic-study-design-extension")
    elif extent:
        ctx.drop(PFX + "diagnosticExtent", extent, "unknown diagnostic extent")
    sr.update(status="active", intent="order", subject=dict(ctx.patient), authoredOn=date,
              reasonReference=[dict(diagnosis)])
    ctx.add(sr, *paths)


def _further_diagnostics(ctx, date: str | None, diagnosis: dict):
    sr = ctx.new("ServiceRequest", "rd_further_genetic_diagnostics", profile=P_REQUEST)
    sr.update(status="active", intent="proposal", subject=dict(ctx.patient), authoredOn=date,
              code={"text": "Further genetic diagnostics recommended"},
              reasonReference=[dict(diagnosis)])
    ctx.bag["careplan_activities"].append(ctx.add(sr))


def build(ctx):
    d = (ctx.dk.get("case") or {}).get("diagnosisRd")
    if not isinstance(d, dict):
        return
    date = d.get("molecularBoardDecisionDate")
    paths = []
    if date:
        paths.append(PFX + "molecularBoardDecisionDate")
    else:
        date = ctx.key.submission_date or None
        ctx.warn(PFX + "molecularBoardDecisionDate", "missing: Condition.recordedDate falls back to the submission date")

    phenotype_refs = _phenotypes(ctx, d)

    assessment = d.get("diagnosticAssessment")
    profile, ver, ver_text = ASSESSMENT.get(assessment, (P_CLINICAL, None, None))
    if assessment and assessment not in ASSESSMENT:
        ctx.drop(PFX + "diagnosticAssessment", assessment, "unknown assessment")
    has_report = isinstance(ctx.dk.get("molecular"), dict)
    if profile == P_GENETIC and not (phenotype_refs or has_report):
        ctx.warn(PFX + "diagnosticAssessment", "genetic diagnosis without phenotypes or molecular report: "
                 "evidence 1..* cannot be filled, emitted as clinical diagnosis")
        profile = P_CLINICAL

    cond = ctx.new("Condition", "rd_diagnosis", profile=profile)
    codings, sliced = [], set()
    for dx in d.get("diagnoses") or []:
        c = _dx_coding(ctx, dx)
        if not c:
            continue
        if c["system"] in (ICD10GM, ORPHA, ALPHA_ID):
            if c["system"] in sliced:   # code.coding slices icd10-gm / orphanet / alpha-id are 0..1
                ctx.drop(PFX + "diagnoses[].code", c["code"], f"second {c['system']} code: Seltene slice max 1")
                continue
            sliced.add(c["system"])
        codings.append(c)
    if codings:
        paths += [PFX + "diagnoses[].code", PFX + "diagnoses[].system"]
        dx_list = d.get("diagnoses") or []
        paths += [PFX + f"diagnoses[].{k}" for k in ("display", "version") if any(x.get(k) for x in dx_list)]
    else:
        ctx.warn(PFX + "diagnoses[]", "no diagnosis code: Condition.code carries text only")
    systems = {c["system"] for c in codings}
    if codings and not {ICD10GM, ORPHA, ALPHA_ID} <= systems and not d.get("noMatchingCodeExists"):
        ctx.warn(PFX + "diagnoses[]", "ICD-10-GM, ORPHA and Alpha-ID-SE are all required unless noMatchingCodeExists")

    notes = []
    nm = d.get("noMatchingCodeExists")
    if nm is True:
        notes.append({"text": "No matching code exists for this diagnosis in all of ICD-10-GM, ORPHA and Alpha-ID-SE "
                              "(KDK noMatchingCodeExists = true)."})
        ctx.preserve(PFX + "noMatchingCodeExists", "no-matching-code-note")
    elif nm is False:
        paths.append(PFX + "noMatchingCodeExists")   # all codes matched: the codings themselves say it

    if profile == P_GENETIC:
        category = [{"coding": [coding(SNOMED, "782964007", "Genetic disease")]}]
    else:
        category = [{"coding": [coding(COND_CATEGORY, "encounter-diagnosis", "Encounter Diagnosis")]}]
    evidence = []
    if has_report and profile == P_GENETIC:
        evidence.append({"code": [{"coding": [coding(SNOMED, "106221001", "Genetic finding")]}],
                         "detail": [{"reference": "urn:uuid:" + ctx.id("DiagnosticReport", RD_REPORT_ID)}]})
    for ref, hpo in phenotype_refs:   # one entry per phenotype, code = HPO term (as in the Seltene examples)
        # no coding.version here: the clinical-diagnosis evidence binding includes HPO unversioned and the validator
        # rejects a versioned coding; the version stays on the HPO assessment the entry points to
        term = {k: v for k, v in hpo.items() if k != "version"}
        evidence.append({"code": [{"coding": [term]}], "detail": [dict(ref)]})

    cond.update(
        verificationStatus=cc(coding(COND_VER, ver), text=ver_text) if ver else None,
        category=category,
        code=cc(*codings, text=None if codings else "Rare disease (no code delivered)"),
        subject=dict(ctx.patient),
        onsetDateTime=d.get("symptomOnsetDate"),
        recordedDate=date,
        evidence=evidence,
        note=notes,
    )
    if ver:
        paths.append(PFX + "diagnosticAssessment")
    if d.get("symptomOnsetDate"):
        paths.append(PFX + "symptomOnsetDate")
    diagnosis = ctx.add(cond, *paths, name="rd_diagnosis")

    if assessment == "furtherGeneticDiagnosticRecommended":
        _further_diagnostics(ctx, date, diagnosis)
    _gmfcs(ctx, d, date)
    _sequencing_request(ctx, d, date, diagnosis)
