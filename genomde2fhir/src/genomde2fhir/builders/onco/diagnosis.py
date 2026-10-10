"""KDK case.diagnosisOd -> primary-tumour Condition plus the diagnosis-level satellites.

Rows (mapping_kdk_oncology.csv, case.diagnosisOd.*):
- mainDiagnosis.{code,system,version,display,date}, histology.*, topography.*
      -> mii-pr-mtb-diagnose-primaertumor (ctx.refs['primary']): ICD-10-GM coding (system normalised to bfarm),
         Feststellungsdatum (condition-assertedDate) + recordedDate = date, ICD-O-3 morphology extension and
         bodySite.coding:icd-o-3 (HL7 URI fixed by the profile, version 2014/2019 = the MII VS editions); each
         ICD-O-3 field is placed by the axis of its code (M/T codes swapped by the sender are accepted with a
         warning), anything else is kept as Condition.note (preserved), except the placeholder 'T' (root of the
         ICD-O-3 topography axis = topography not specified, outside mii-vs-onko-icdo3-topographie), which is
         dropped with that reason,
         category:onkologie SNOMED 55342001 (mandatory in 2027, harmless in 2026; REPRESENTATIONS #8).
         clinicalStatus / verificationStatus are not in the source and are not emitted.
- additionalDiagnoses[] -> one MII Diagnose Condition per item (ICD-10-GM / Orphanet / Alpha-ID by source system).
- germlineDiagnoses[] + germlineDiagnosisConfirmed -> one Diagnose Condition per item, verificationStatus
         confirmed|unconfirmed from the boolean, category SNOMED 782964007 (genetic disease, as on Seltene
         genetic-diagnosis); the schema has no date -> recordedDate carries data-absent-reason unless the item has one.
- grading -> mii-pr-onko-grading (all 13 KDK codes are in mii-cs-onko-grading); effective[x] 1..1 has no source
         (no grading date) -> data-absent-reason on the primitive, not the diagnosis date.
- hpoTerms[] -> mii-pr-seltene-hpo-assessment (HPO term in Observation.code).
- libraryType -> ServiceRequest MolGen anforderung-genetischer-test (sequencing indicated), code from
         mii-cs-mtb-genomic-analysis-method-type;
         `none` -> no request (dropped: no sequencing indicated). Registered as ctx.refs['sequencing_request'].
- additionalClassification[] -> mii-pr-onko-weitere-klassifikationen (code.text = system, value.text = key), except the
         DNPM tumour spread (system dnpm-dip/mtb/diagnosis/kds-tumor-spread, a key of TUMOR_SPREAD): the dedicated
         mii-pr-mtb-tumorausbreitung (code SNOMED 371508000, category ErstdiagnoseZeitpunkt 473302008 = state at
         diagnosis as the DNPM model defines the list; value coding:Tumorausbreitung, key as text; effective[x] 1..1 =
         mainDiagnosis.date, data-absent-reason without it), linked from the primary tumour as
         Condition.stage:ErstdiagnoseZeitpunkt (type NCIt C19251, 0..1: further items stay unlinked, warned).
- diagnosticAssessment -> Observation with mvgs-cs-genetic-diagnostic-assessment (REPRESENTATIONS #5, preserved).
TNM and ECOG are separate modules (onco.tnm, onco.ecog) that run after this one.
"""
import re

from ... import terminology
from ...systems import ALPHA_ID, COND_VER, DIAGNOSE, FHIR_EXT, HPO, ICD10GM, ICDO3, LOINC, MOLGEN, MTB, ONKO, ORPHA, SELTENE, SNOMED
from ..common import as_list, cc, coding, dar_cc, dar_ext, ext, icd10gm, obs_category

P_PRIMARY = MTB + "StructureDefinition/mii-pr-mtb-diagnose-primaertumor"
P_DIAGNOSE = DIAGNOSE + "StructureDefinition/Diagnose"
P_GRADING = ONKO + "StructureDefinition/mii-pr-onko-grading"
P_HPO = SELTENE + "StructureDefinition/mii-pr-seltene-hpo-assessment"
P_WEITERE = ONKO + "StructureDefinition/mii-pr-onko-weitere-klassifikationen"
P_REQUEST = MOLGEN + "StructureDefinition/anforderung-genetischer-test"
P_TUMOR_SPREAD = MTB + "StructureDefinition/mii-pr-mtb-tumorausbreitung"

EXT_ASSERTED = FHIR_EXT + "condition-assertedDate"
EXT_MORPHOLOGY = ONKO + "StructureDefinition/mii-ex-onko-histology-morphology-behavior-icdo3"
CS_GRADING = ONKO + "CodeSystem/mii-cs-onko-grading"
CS_METHOD_TYPE = MTB + "CodeSystem/mii-cs-mtb-genomic-analysis-method-type"
CS_ASSESSMENT = "mvgs-cs-genetic-diagnostic-assessment"

CAT_ONKOLOGIE = {"coding": [{"system": SNOMED, "code": "55342001", "display": "Neoplastic disease"}]}
CAT_GENETIC = {"coding": [{"system": SNOMED, "code": "782964007", "display": "Genetic disease"}]}
GRADING_CODE = {"coding": [{"system": LOINC, "code": "33732-9", "display": "Histology grade [Identifier] in Cancer specimen"}]}

# KDK system spellings -> canonical system URIs (BfArM moved the DIMDI namespace; Orphanet/Alpha-ID homepages)
SYSTEM_ALIASES = {
    "http://fhir.de/CodeSystem/dimdi/icd-10-gm": ICD10GM, ICD10GM: ICD10GM,
    "https://www.orpha.net/consor/cgi-bin/index.php": ORPHA, "https://www.orpha.net": ORPHA, ORPHA: ORPHA,
    "http://www.orpha.net/": ORPHA,
    "https://www.alpha-id.de": ALPHA_ID, "http://fhir.de/CodeSystem/dimdi/alpha-id": ALPHA_ID, ALPHA_ID: ALPHA_ID,
    "http://snomed.info/sct": SNOMED,
}
HPO_ALIASES = {"https://hpo.jax.org/app/", "https://hpo.jax.org", "http://purl.obolibrary.org/obo/hp.owl", HPO}
ICDO3_ALIASES = {ICDO3, "urn:oid:2.16.840.1.113883.6.43.1", "ICD-O3-M", "ICD-O3-T", "ICD-O-3", "icd-o-3"}
# ICD-O-3 editions of the MII value sets: 2014 = first revision (ICD-O-3.1), 2019 = second revision (ICD-O-3.2)
ICDO3_VERSIONS = {"2014": "2014", "2019": "2019", "zweite revision": "2019", "rev2": "2019", "3.2": "2019",
                  "icd-o-3.2": "2019", "erste revision": "2014", "rev1": "2014", "3.1": "2014", "icd-o-3.1": "2014"}

LIBRARY_TYPE = {  # KDK libraryType -> mii-cs-mtb-genomic-analysis-method-type
    "panel": ("gene-panel", "Genpanel", None),
    "wes": ("whole-exom-sequencing", "Whole Exom Sequencing (WES)", None),
    "wgs": ("whole-genom-sequencing", "Whole Genom Sequencing (WGS)", None),
    "wgs_lr": ("whole-genom-sequencing", "Whole Genom Sequencing (WGS)", "Whole genome sequencing, long read"),
}
TUMOR_SPREAD_SYSTEM = "dnpm-dip/mtb/diagnosis/kds-tumor-spread"
TUMOR_SPREAD_CODE = {"coding": [{"system": SNOMED, "code": "371508000", "display": "Tumor stage"}]}
CAT_AT_DIAGNOSIS = {"coding": [{"system": SNOMED, "code": "473302008", "display": "Aware of diagnosis"}]}
# Condition.stage:ErstdiagnoseZeitpunkt.type pattern (NCIt as fixed by the MTB profile, see molecular_biomarkers.NCIT_MTB)
STAGE_AT_DIAGNOSIS = {"coding": [{"system": "https://nih-ncpi.github.io/ncpi-fhir-ig/CodeSystem-ncit.html",
                                  "code": "C19251", "display": "Stage at Diagnosis"}]}
TUMOR_SPREAD = {  # DNPM kds-tumor-spread -> mii-vs-mtb-tumorausbreitung (SNOMED)
    "tumor-free": ("58899004", "No evidence of tumor"),
    "local": ("255127006", "Local tumor spread"),
    "metastasized": ("128462008", "Metastases"),
    "unknown": ("261665006", "Unknown"),
}

D = "case.diagnosisOd."


def norm_system(system: str | None) -> str | None:
    return SYSTEM_ALIASES.get(system, system) if system else system


def diagnosis_coding(ctx, item: dict, path: str) -> dict | None:
    """One KDK diagnosis Coding (ICD-10-GM / ORPHA / Alpha-ID / SNOMED) -> FHIR Coding of the MII Diagnose slices."""
    code = (item or {}).get("code")
    if not code:
        return None
    system = norm_system(item.get("system"))
    if system == ORPHA:
        code = re.sub(r"^ORPHA:?", "", str(code), flags=re.I)
    elif system == ICD10GM:
        c = icd10gm(code, item.get("display"), item.get("version"))
        if c and c["code"] != str(code).strip().upper():
            ctx.warn(path, f"ICD-10-GM code {code!r} normalised to {c['code']!r}"
                     + (" + Mehrfachkodierungs-Kennzeichen" if c.get("extension") else ""))
        return c
    elif system not in (ALPHA_ID, SNOMED):
        ctx.warn(path, f"unknown diagnosis code system {item.get('system')!r}; kept as given")
    return coding(system, code, item.get("display"), item.get("version"))


def icdo3_coding(ctx, item: dict, axis: str, path: str):
    """ICD-O-3 morphology ('M') or topography ('T') -> (coding | None, valid). Source OIDs/labels are replaced by the
    HL7 URI the profile fixes; the edition label is normalised to the MII VS versions 2014/2019."""
    code = str(item.get("code") or "").strip()
    if item.get("system") not in ICDO3_ALIASES:
        ctx.warn(path, f"unexpected ICD-O-3 system {item.get('system')!r}; treated as ICD-O-3")
    if axis == "M":
        m = re.fullmatch(r"M?(\d{4})/?(\d)", code)
        norm = f"{m[1]}/{m[2]}" if m else None
    else:
        m = re.fullmatch(r"C(\d{2})\.?(\d)?", code.upper())
        norm = (f"C{m[1]}.{m[2]}" if m[2] else f"C{m[1]}") if m else None
    if norm and norm != code:
        ctx.warn(path, f"ICD-O-3 code {code!r} normalised to {norm!r}")
    version = ICDO3_VERSIONS.get(str(item.get("version") or "").strip().lower())
    if item.get("version") and not version:
        ctx.warn(path, f"ICD-O-3 edition {item.get('version')!r} is neither 2014 nor 2019; coding.version omitted")
    if not norm:
        return None, False
    return coding(ICDO3, norm, item.get("display"), version), True


def _paths(prefix: str, item: dict, *keys) -> list:
    return [prefix + k for k in keys if item.get(k) not in (None, "")]


ICDO3_KEYS = ("code", "system", "version", "display")
AXIS_NAME = {"M": "morphology", "T": "topography"}


def icdo3_axis(code) -> str | None:
    """'M' for an ICD-O-3 morphology code (8140/3, M8140/3), 'T' for a topography code (C34.1, C341), else None."""
    c = str(code or "").strip()
    if re.fullmatch(r"M?\d{4}/?\d", c):
        return "M"
    if re.fullmatch(r"C\d{2}\.?\d?", c.upper()):
        return "T"
    return None


def icdo3_slots(ctx, d: dict) -> tuple[dict, list]:
    """histology (ICD-O-3 M) / topography (ICD-O-3 T) -> ({'M'|'T': coding}, notes).

    Each field is placed by the axis its code actually has: a morphology code delivered in `topography` (or a
    topography code in `histology`) fills the other slot when that slot is still free (accepted with a warning,
    REPRESENTATIONS: unambiguous wrong-field codes). Codes of neither axis, or a second code for an occupied slot,
    are kept as Condition.note (preserved); an exact duplicate of the occupied slot is dropped."""
    fields = [("histology", "M", d.get("histology") or {}), ("topography", "T", d.get("topography") or {})]
    slots, notes, done = {}, [], set()
    for field, want, item in fields:                       # pass 1: codes in their own field
        if item.get("code") and icdo3_axis(item["code"]) == want:
            slots[want] = icdo3_coding(ctx, item, want, D + field + ".code")[0]
            ctx.cover(*_paths(D + field + ".", item, *ICDO3_KEYS))
            done.add(field)
    for field, want, item in fields:                       # pass 2: wrong field or no ICD-O-3 code
        if not item.get("code") or field in done:
            continue
        p, code, got = D + field + ".", item["code"], icdo3_axis(item["code"])
        if str(code).strip().upper() == "T":   # topography-axis root ('Topographie'): no site information
            for k in ICDO3_KEYS:
                if item.get(k) not in (None, ""):
                    ctx.drop(p + k, item[k], "placeholder 'T' = ICD-O-3 topography-axis root (topography not "
                                             "specified); outside mii-vs-onko-icdo3-topographie (descendent-of T)")
            continue
        c = icdo3_coding(ctx, item, got, p + "code")[0] if got else None
        if got and got not in slots:
            slots[got] = c
            ctx.cover(*_paths(p, item, *ICDO3_KEYS))
            ctx.rep("icdo3-wrong-field-accepted")
            ctx.warn(p + "code", f"ICD-O-3 {AXIS_NAME[got]} code {code!r} delivered in {field}; used as {AXIS_NAME[got]}")
        elif got and slots[got]["code"] == c["code"]:
            for k in ICDO3_KEYS:
                if item.get(k) not in (None, ""):
                    ctx.drop(p + k, item[k], f"duplicate of the ICD-O-3 {AXIS_NAME[got]} code already mapped")
        else:
            what = f"a second ICD-O-3 {AXIS_NAME[got]} code" if got else "not an ICD-O-3 code"
            notes.append({"text": f"{field.capitalize()} (ICD-O-3 {want}, as delivered): {code} {item.get('display') or ''}".strip()})
            for k in ICDO3_KEYS:
                if item.get(k) not in (None, ""):
                    ctx.preserve(p + k, "icdo3-unmapped-as-note")
            ctx.warn(p + "code", f"{field} {code!r}: {what}; kept as Condition.note")
    return slots, notes


def build(ctx):
    d = (ctx.dk.get("case") or {}).get("diagnosisOd") or {}
    if not d:
        return
    primary(ctx, d)
    additional_diagnoses(ctx, d)
    germline_diagnoses(ctx, d)
    grading(ctx, d)
    hpo_terms(ctx, d)
    library_type(ctx, d)
    additional_classifications(ctx, d)
    diagnostic_assessment(ctx, d)


# ---- primary tumour --------------------------------------------------------------------------------------------
def primary(ctx, d: dict):
    md = d.get("mainDiagnosis") or {}
    if not md.get("code"):
        return
    cond = ctx.new("Condition", "primary", profile=P_PRIMARY)
    paths = _paths(D + "mainDiagnosis.", md, "code", "system", "version", "display", "date")
    exts = []
    if md.get("date"):
        exts.append(ext(EXT_ASSERTED, valueDateTime=md["date"]))
    else:  # Feststellungsdatum 1..1; the schema requires the date, so only reached with --no-check input
        exts.append({"url": EXT_ASSERTED, "_valueDateTime": {"extension": [dar_ext("unknown")]}})
    slots, notes = icdo3_slots(ctx, d)
    if slots.get("M"):
        exts.append(ext(EXT_MORPHOLOGY, valueCodeableConcept=cc(slots["M"])))
    cond["extension"] = exts
    cond["category"] = [CAT_ONKOLOGIE]
    icd = diagnosis_coding(ctx, md, D + "mainDiagnosis.code")
    if icd["system"] != ICD10GM:
        ctx.warn(D + "mainDiagnosis.system", f"main diagnosis not ICD-10-GM: {md.get('system')!r}")
    cond["code"] = cc(icd)
    if slots.get("T"):
        cond["bodySite"] = [cc(slots["T"])]
    cond["subject"] = ctx.patient
    if md.get("date"):
        cond["recordedDate"] = md["date"]
    if notes:
        cond["note"] = notes
    ctx.add(cond, *paths, name="primary")


# ---- secondary and germline diagnoses ----------------------------------------------------------------------------
def _diagnose(ctx, role: str, i: int, item: dict, path: str) -> dict | None:
    c = diagnosis_coding(ctx, item, path + "code")
    if not c:
        return None
    cond = ctx.new("Condition", role, i, profile=P_DIAGNOSE)
    cond["code"] = cc(c)
    cond["subject"] = ctx.patient
    if item.get("date"):
        cond["extension"] = [ext(EXT_ASSERTED, valueDateTime=item["date"])]
        cond["recordedDate"] = item["date"]
    else:
        cond["_recordedDate"] = {"extension": [dar_ext("unknown")]}
    return cond


def additional_diagnoses(ctx, d: dict):
    p = D + "additionalDiagnoses[]."
    for i, item in enumerate(as_list(d.get("additionalDiagnoses"))):
        cond = _diagnose(ctx, "additional-diagnosis", i, item, p)
        if cond:
            ctx.add(cond, *_paths(p, item, "code", "system", "version", "display", "date"))


def germline_diagnoses(ctx, d: dict):
    p = D + "germlineDiagnoses[]."
    confirmed = d.get("germlineDiagnosisConfirmed")
    items = [x for x in as_list(d.get("germlineDiagnoses")) if (x or {}).get("code")]
    if confirmed is not None and not items:
        ctx.drop(D + "germlineDiagnosisConfirmed", confirmed,
                 "no germlineDiagnoses[] to qualify (verificationStatus needs a Condition)")
    for i, item in enumerate(items):
        cond = _diagnose(ctx, "germline-diagnosis", i, item, p)
        cond["category"] = [CAT_GENETIC]
        paths = _paths(p, item, "code", "system", "version", "display")
        if confirmed is not None:
            vs = ("confirmed", "Confirmed") if confirmed else ("unconfirmed", "Unconfirmed")
            cond["verificationStatus"] = cc(coding(COND_VER, vs[0], vs[1]))
            paths.append(D + "germlineDiagnosisConfirmed")
        ctx.add(cond, *paths)
        ctx.cover_undeclared(*_paths(p, item, "date"))   # not in the KDK schema, converted by _diagnose


# ---- grading --------------------------------------------------------------------------------------------------------
def grading(ctx, d: dict):
    g = d.get("grading")
    if g in (None, ""):
        return
    o = ctx.new("Observation", "grading", profile=P_GRADING)
    o["status"] = "final"
    o["category"] = obs_category("laboratory")
    o["code"] = GRADING_CODE
    o["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        o["focus"] = [ctx.refs["primary"]]
    o["_effectiveDateTime"] = {"extension": [dar_ext("unknown")]}   # 1..1, no grading date in the KDK
    o["valueCodeableConcept"] = cc(coding(CS_GRADING, str(g)))
    ctx.add(o, D + "grading")


# ---- HPO terms ------------------------------------------------------------------------------------------------------
def hpo_terms(ctx, d: dict):
    p = D + "hpoTerms[]."
    for i, t in enumerate(as_list(d.get("hpoTerms"))):
        if not (t or {}).get("code"):
            continue
        if t.get("system") and t["system"] not in HPO_ALIASES:
            ctx.warn(p + "system", f"unexpected HPO system {t['system']!r}; HPO assumed")
        o = ctx.new("Observation", "hpo", i, profile=P_HPO)
        o["status"] = "final"
        o["code"] = cc(coding(HPO, t["code"], t.get("display"), t.get("version")), text=t.get("text"))
        o["subject"] = ctx.patient
        ctx.add(o, *_paths(p, t, "code", "system", "version", "display", "text"))


# ---- sequencing indication --------------------------------------------------------------------------------------------
def library_type(ctx, d: dict):
    lt = d.get("libraryType")
    if not lt:
        return
    if lt not in LIBRARY_TYPE:
        if lt == "none":
            ctx.drop(D + "libraryType", lt, "no sequencing indicated: no ServiceRequest")
        else:
            ctx.drop(D + "libraryType", lt, "unknown library type")
        return
    code, display, text = LIBRARY_TYPE[lt]
    sr = ctx.new("ServiceRequest", "sequencing", profile=P_REQUEST)
    sr["status"] = "unknown"          # the KDK states the indicated sequencing type, not the order state
    sr["intent"] = "order"
    sr["code"] = cc(coding(CS_METHOD_TYPE, code, display), text=text)
    sr["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        sr["reasonReference"] = [ctx.refs["primary"]]
    if text:
        ctx.rep("library-type-long-read-as-text")
    ctx.add(sr, D + "libraryType", name="sequencing_request")


# ---- additional classifications ------------------------------------------------------------------------------------------
def weitere_klassifikation(ctx, id_parts: tuple, system_text: str, value: dict | None) -> dict:
    """mii-pr-onko-weitere-klassifikationen with code.text = classification system, value = CodeableConcept
    (text = key / notation); without a value the optional value[x] gets dataAbsentReason. Also used by onco.tnm."""
    o = ctx.new("Observation", *id_parts, profile=P_WEITERE)
    o["status"] = "final"
    o["code"] = {"text": system_text}
    o["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        o["focus"] = [ctx.refs["primary"]]
    if value:
        o["valueCodeableConcept"] = value
    else:
        o["dataAbsentReason"] = dar_cc("unknown")
    return o


def additional_classifications(ctx, d: dict):
    p = D + "additionalClassification[]."
    for i, item in enumerate(as_list(d.get("additionalClassification"))):
        system, key = (item or {}).get("system"), (item or {}).get("key")
        if not system:
            if key:
                ctx.drop(p + "key", key, "classification without system (Observation.code.text 1..1)")
            continue
        if system == TUMOR_SPREAD_SYSTEM and key in TUMOR_SPREAD:
            tumor_spread(ctx, d, i, key)
            ctx.cover(p + "system", p + "key")
            continue
        value = cc(text=key) if key else None   # an unknown tumour-spread key has no mii-vs-mtb-tumorausbreitung code
        o = weitere_klassifikation(ctx, ("additional-classification", i), system, value)
        ctx.add(o, *_paths(p, item, "system", "key"))


def tumor_spread(ctx, d: dict, i: int, key: str):
    """DNPM kds-tumor-spread -> mii-pr-mtb-tumorausbreitung + Condition.stage:ErstdiagnoseZeitpunkt of the primary."""
    o = ctx.new("Observation", "additional-classification", i, profile=P_TUMOR_SPREAD)
    o["status"] = "final"
    o["category"] = [CAT_AT_DIAGNOSIS]
    o["code"] = TUMOR_SPREAD_CODE
    o["subject"] = ctx.patient
    primary_ref = ctx.refs.get("primary")
    if primary_ref:
        o["focus"] = [primary_ref]
    date = (d.get("mainDiagnosis") or {}).get("date")
    if date:   # the list is the state at diagnosis (category ErstdiagnoseZeitpunkt) -> date of the main diagnosis
        o["effectiveDateTime"] = date
    else:      # effective[x] 1..1; only reached with --no-check input (the schema requires the diagnosis date)
        o["_effectiveDateTime"] = {"extension": [dar_ext("unknown")]}
    sct, display = TUMOR_SPREAD[key]
    o["valueCodeableConcept"] = cc(coding(SNOMED, sct, display), text=key)
    ref = ctx.add(o)
    ctx.rep("tumor-spread-mtb-tumorausbreitung")
    cond = ctx.resource(primary_ref)
    if cond is None:
        return
    if any(st.get("type") == STAGE_AT_DIAGNOSIS for st in cond.get("stage", [])):   # slice 0..1
        ctx.warn(D + "additionalClassification[].key",
                 f"second tumour-spread item {key!r}: Condition.stage:ErstdiagnoseZeitpunkt is 0..1; "
                 f"Observation emitted without stage link")
        return
    cond.setdefault("stage", []).append({"type": STAGE_AT_DIAGNOSIS, "assessment": [ref]})


# ---- genetic diagnostic assessment (hereditary tumour cases) -------------------------------------------------------------
def diagnostic_assessment(ctx, d: dict):
    a = d.get("diagnosticAssessment")
    if not a:
        return
    value = terminology.local_coding(CS_ASSESSMENT, a)
    if not value:
        ctx.drop(D + "diagnosticAssessment", a, f"code not in {CS_ASSESSMENT}")
        return
    o = ctx.new("Observation", "genetic-diagnostic-assessment")
    o["status"] = "final"
    o["code"] = cc(terminology.local_coding(CS_ASSESSMENT, "genetic-diagnostic-assessment"))
    o["subject"] = ctx.patient
    if ctx.refs.get("primary"):
        o["focus"] = [ctx.refs["primary"]]
    o["valueCodeableConcept"] = cc(value)
    ctx.add(o)
    ctx.preserve(D + "diagnosticAssessment", "genetic-diagnostic-assessment-local-cs")
