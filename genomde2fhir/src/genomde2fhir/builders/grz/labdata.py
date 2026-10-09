"""GRZ donors[].labData[] -> Specimen, genomic-study-analysis Procedure, Devices, Tumorzellgehalt Observations.

Rows: every `donors[].labData[].*` row of mapping_grz.csv.

Per labData element (id parts: 'donor', donorPseudonym, 'labdata', labDataName):
- Specimen (biobank SpecimenCore): identifier = labDataName, accessionIdentifier = barcode ('na' -> none),
  type.coding:sct from tissueTypeId via mvgs-cm-tissue-sct, mapped only when tissueTypeName agrees with the
  ontology label of the code (otherwise the root concept 123038009 'Specimen' and a warning); the original
  ontology coding (UBERON / BTO by CURIE prefix, version from tissueOntology) is kept as second coding.
  sampleDate -> collection.collectedDateTime; sampleConservation ffpe / cryo-frozen -> processing.procedure
  (SNOMED via mvgs-cm-grz-sample-conservation-sct, no temperatures); fresh-tissue -> Specimen.note (preserved).
- genomic-study-analysis Procedure: the profile family follows the submission's genomic study (grz.donors):
  diseaseType 'oncological' -> MTB mii-pr-mtb-genomic-study-analysis, 'rare' / 'hereditary' -> MolGen
  mii-pr-molgen-genomic-study-analysis. method-type from libraryType (mvgs-cm-grz-library-type-method-type)
  plus rnaseq-transcriptomics for sequenceType rna; exact libraryType (incl. long-read) in the GR title
  extension (display of mvgs-cs-grz-library-type; Procedure.code is 0..0); genome-build LOINC;
  genomic-source-class LOINC from sequenceSubtype; specimen extension -> Specimen; devices via GR
  genomic-study-analysis-device (REPRESENTATIONS #24): sequencer
  (sequencing-device), sequencing kit (sequencing-kit), library prep kit (library-preparation-kit), enrichment
  kit (gene-panel for panels in 2027, else library-preparation-kit; + mvgs enrichment-kit), pipeline and callers
  (software Devices, mvgs-cs-grz-device-function); 2027 panel kits matching an MII catalogue entry get
  Device.definition -> mii-pr-mtb-panel-devicedefinition. QC (REPRESENTATIONS #22): MTB extension:qc
  (read-depth, sequencing-coverage, sequencing-read-type, metrics-description), MolGen GR extension:metrics
  (read-depth, sequencing-coverage, metrics-description); minCoverage, Q-threshold percent, fragmentation,
  non-coding flag (and on MolGen the layout) as key=value text in metrics-description (preserved).
  Known ballot defect: the qc extension declares context Extension, so matchbox rejects it on Procedure
  (Extension_EXTP_Context_Wrong) in both 2026 and 2027 packages (REVIEW-TD B, MTB QC / defects).
  The analysis is appended to the genomic study (`genomic-study-analysis-ext`).
- tumorCellCount[] -> mii-pr-mtb-tumorzellgehalt (method pathology/bioinformatics -> histologic/bioinformatic;
  other -> method.text, preserved; unknown -> method data-absent-reason).
- sequenceData.files[] are NOMAP (raw data stays in the GRZ): dropped with a reason.

Shared names: reads ctx.ids[('donor', pseudonym)], ctx.refs['genomic_study'], ctx.refs['lab'] (grz.donors);
registers ctx.ids[('specimen', pseudonym, labDataName)] and ctx.ids[('genomic_study_analysis', pseudonym,
labDataName)].
"""
import re

from ...bundle import ref as uuid_ref
from ...systems import BIOBANK, GR, LOINC, MOLGEN, MTB, SID_BARCODE, SID_LAB_DATA, SNOMED, UCUM
from ...terminology import concept_map, local_coding, translate
from ..common import cc, coding, dar_ext, ext, identifier

P = "donors[].labData[]."

SPECIMEN_PROFILE = BIOBANK + "StructureDefinition/SpecimenCore"
ANALYSIS_PROFILE = {"mtb": MTB + "StructureDefinition/mii-pr-mtb-genomic-study-analysis",
                    "molgen": MOLGEN + "StructureDefinition/mii-pr-molgen-genomic-study-analysis"}
DEVICE_PROFILE = MTB + "StructureDefinition/genomic-study-device"
TZG_PROFILE = MTB + "StructureDefinition/mii-pr-mtb-tumorzellgehalt"

GR_SD = GR + "StructureDefinition/"
EXT_METHOD_TYPE = GR_SD + "genomic-study-analysis-method-type"
EXT_GENOME_BUILD = GR_SD + "genomic-study-analysis-genome-build"
EXT_SOURCE_CLASS = GR_SD + "genomic-study-analysis-genomic-source-class"
EXT_SPECIMEN = GR_SD + "genomic-study-analysis-specimen"
EXT_DEVICE = GR_SD + "genomic-study-analysis-device"
EXT_METRICS = GR_SD + "genomic-study-analysis-metrics"
EXT_TITLE = GR_SD + "genomic-study-analysis-title"
EXT_ANALYSIS = GR_SD + "genomic-study-analysis-ext"
EXT_QC = MTB + "StructureDefinition/mii-ex-mtb-genomic-study-analysis-qc"

MTB_CS = MTB + "CodeSystem/"
DEVICE_FUNCTION_CS = MTB_CS + "mii-cs-mtb-genomicanalysis-devicefunction"
METHOD_TYPE_CS = MTB_CS + "mii-cs-mtb-genomic-analysis-method-type"
TZG_METHOD_CS = MTB_CS + "mii-cs-mtb-bestimmungsmethode-tumorzellgehalt"
OBS_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category"

# local identifier systems for lab data (sender-scoped like the other genomDE identifiers; docs/IDENTITY.md)

# tissue ontologies (OBO PURLs; no HL7 THO entry exists for UBERON / BTO)
UBERON = "http://purl.obolibrary.org/obo/uberon.owl"
BTO = "http://purl.obolibrary.org/obo/bto.owl"
ICDO3 = "http://terminology.hl7.org/CodeSystem/icd-o-3"
CURIE_SYSTEMS = {"UBERON": UBERON, "BTO": BTO}
ONTOLOGY_NAMES = {"uberon": UBERON, "bto": BTO, "brenda": BTO, "brendatissueontology": BTO,
                  "snomedct": SNOMED, "snomed": SNOMED, "sct": SNOMED, "icdo3": ICDO3, "icdo": ICDO3}
SPECIMEN_ROOT = ("123038009", "Specimen")
LABEL_STOPWORDS = {"of", "the", "and"}

GENOME_BUILD = {"GRCh37": ("LA14029-5", "GRCh37"), "GRCh38": ("LA26806-2", "GRCh38")}
SOURCE_CLASS = {"germline": ("LA6683-2", "Germline"), "somatic": ("LA6684-0", "Somatic")}
TZG_METHOD = {"pathology": ("histologic", "Histologisch"), "bioinformatics": ("bioinformatic", "Bioinformatisch")}
LAYOUT_CS = "mvgs-cs-grz-sequencing-layout"
LIBRARY_CS = "mvgs-cs-grz-library-type"
FUNCTION_CS = "mvgs-cs-grz-device-function"
CATCH_ALL = {"other", "unknown", "none", "notApplicable"}
ABSENT_TEXT = {"", "na", "n/a", "none", "unknown"}
FILE_FIELDS = ("filePath", "fileType", "checksumType", "fileChecksum", "fileSizeInBytes", "readOrder", "readLength",
               "flowcellId", "laneId")

# MII MTB 2027 panel catalogue (mii-pr-mtb-panel-devicedefinition instances); normalised name fragments -> id
PANEL_CATALOGUE = [
    (("trusightoncology500", "tso500"), "mii-dd-mtb-panel-tso-500", "TruSight Oncology 500"),
    (("oncominefocusassayplus", "ofaplus"), "mii-dd-mtb-panel-ofa-plus", "Oncomine Focus Assay Plus"),
    (("oncominefocusassay",), "mii-dd-mtb-panel-ofa", "Oncomine Focus Assay"),
    (("sureselectcancercgpassay", "sureselectcgp"), "mii-dd-mtb-panel-cgp", "SureSelect Cancer CGP Assay"),
    (("fusionplexarcherlungv2", "archerlungv2"), "mii-dd-mtb-panel-archer-lung-v2", "FusionPlex Archer Lung V2"),
    (("dhs3501z",), "mii-dd-mtb-panel-dhs-3501z", "Qiagen DHS-3501Z"),
    (("mhivd600", "mh600"), "mii-dd-mtb-panel-mh600plus", "MH IVD 600+"),
]


def build(ctx):
    seen = set()
    for d in ctx.dk.get("donors") or []:
        pseudo = d.get("donorPseudonym")
        if not pseudo:
            continue
        for i, ld in enumerate(d.get("labData") or []):
            ldn = ld.get("labDataName") or f"#{i}"
            if (pseudo, ldn) in seen:
                ctx.warn(P + "labDataName", f"duplicate labDataName {ldn!r} for donor {pseudo!r}; index appended")
                ldn = f"{ldn}#{i}"
            seen.add((pseudo, ldn))
            _lab_data(ctx, pseudo, ldn, ld)


def _lab_data(ctx, pseudo: str, ldn: str, ld: dict):
    subject = _donor_ref(ctx, pseudo)
    if subject is None:
        return
    parts = ("donor", pseudo, "labdata", ldn)
    spec_ref = _specimen(ctx, parts, pseudo, ldn, ld, subject)
    ctx.ids[("specimen", pseudo, ldn)] = spec_ref
    for j, tcc in enumerate(ld.get("tumorCellCount") or []):
        _tumor_cell_count(ctx, parts, j, tcc, subject, spec_ref)
    an_ref = _analysis(ctx, parts, ld, subject, spec_ref)
    ctx.ids[("genomic_study_analysis", pseudo, ldn)] = an_ref
    _link_to_study(ctx, an_ref)
    _drop_files(ctx, (ld.get("sequenceData") or {}).get("files") or [])


def _donor_ref(ctx, pseudo: str) -> dict | None:
    r = ctx.ids.get(("donor", pseudo))
    if r:
        return r
    rid = ctx.id("Patient", "donor", pseudo)   # same id grz.donors builds
    if ctx.bundle.has(rid):
        return uuid_ref("Patient", rid)
    ctx.warn(P + "labDataName", f"no Patient for donor {pseudo!r}; its lab data are not converted")
    return None


# ---- Specimen ----------------------------------------------------------------------------------------------
def _specimen(ctx, parts, pseudo, ldn, ld, subject) -> dict:
    k = ctx.key
    spec = ctx.new("Specimen", *parts, profile=SPECIMEN_PROFILE)
    paths = [P + "labDataName"] if ld.get("labDataName") else []
    acc = None
    bc = ld.get("barcode")
    if bc and bc.strip().lower() not in ABSENT_TEXT:
        acc = identifier(SID_BARCODE, f"{ctx.key.submitter_id}|{bc}")
        paths.append(P + "barcode")
    elif bc:
        ctx.drop(P + "barcode", bc, "no barcode ('na')")
    spec.update(
        identifier=[identifier(SID_LAB_DATA, f"{k.submitter_id}|{pseudo}|{ld.get('labDataName') or ldn}")],
        accessionIdentifier=acc,
        status="available",        # the GRZ received data from this sample; SpecimenCore requires a status
        type=_specimen_type(ctx, ld, spec, paths),
        subject=subject,
    )
    if ld.get("sampleDate"):
        spec["collection"] = {"collectedDateTime": ld["sampleDate"]}
        paths.append(P + "sampleDate")
    else:  # collection.collected[x] is 1..1 in SpecimenCore; schema requires sampleDate, so this is defensive
        spec["collection"] = {"_collectedDateTime": {"extension": [dar_ext("unknown")]}}
    if spec.get("_bodySite"):
        spec["collection"]["bodySite"] = spec.pop("_bodySite")
    _conservation(ctx, ld.get("sampleConservation"), spec, paths)
    return ctx.add(spec, *paths)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _tokens(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower())) - LABEL_STOPWORDS


def _labels_agree(name: str, label: str) -> bool:
    a, b = _tokens(name), _tokens(label)
    return bool(a and b) and (a <= b or b <= a)


def _cm_element(map_name: str, system: str, code: str) -> dict | None:
    for g in concept_map(map_name).get("group", []):
        if g.get("source") != system:
            continue
        for el in g.get("element", []):
            if el.get("code") == code:
                return el
    return None


def _specimen_type(ctx, ld: dict, spec: dict, paths: list) -> dict | None:
    tid = (ld.get("tissueTypeId") or "").strip()
    tname = ld.get("tissueTypeName")
    onto = ld.get("tissueOntology") or {}
    claimed = ONTOLOGY_NAMES.get(_norm(onto.get("name")))
    prefix = tid.split(":", 1)[0].upper() if ":" in tid else None
    system = CURIE_SYSTEMS.get(prefix) if prefix else None
    if system is None and tid:
        if claimed == SNOMED and tid.isdigit():
            system = SNOMED
        elif claimed == ICDO3 and re.fullmatch(r"C\d{2}(\.\d)?", tid):
            system = ICDO3
        elif claimed in (UBERON, BTO):
            system = claimed           # bare code in the claimed ontology
    if claimed and system and claimed != system:
        ctx.warn(P + "tissueOntology.name", f"tissueOntology {onto.get('name')!r} does not match the code "
                                            f"{tid!r}; system taken from the code")
    if tname:
        paths.append(P + "tissueTypeName")
    if not tid:
        return cc(coding(SNOMED, *SPECIMEN_ROOT), text=tname)
    if system is None:
        ctx.warn(P + "tissueTypeId", f"unknown tissue ontology {onto.get('name')!r} for {tid!r}; kept as text")
        ctx.preserve(P + "tissueTypeId", "grz-tissue-text")
        if onto.get("name"):
            ctx.preserve(P + "tissueOntology.name", "grz-tissue-text")
        return cc(coding(SNOMED, *SPECIMEN_ROOT), text=f"{tname or ''} ({onto.get('name')} {tid})".strip())
    paths.append(P + "tissueTypeId")
    if onto.get("name") and claimed == system:
        paths.append(P + "tissueOntology.name")
    elif onto.get("name"):
        ctx.drop(P + "tissueOntology.name", onto["name"], "ontology name contradicts the code; system from the code")
    version = onto.get("version") if claimed == system else None
    if version and system == SNOMED and not version.startswith("http://snomed.info/sct/"):
        version = None   # SNOMED CT versions are edition URIs; a bare release label ('2024.03') is not one
        ctx.drop(P + "tissueOntology.version", onto["version"], "not a SNOMED CT edition/version URI")
    elif onto.get("version"):
        if version:
            paths.append(P + "tissueOntology.version")
        else:
            ctx.drop(P + "tissueOntology.version", onto["version"], "version of an ontology the code is not from")

    if system == SNOMED:
        return cc(coding(SNOMED, tid, tname, version), text=tname)
    if system == ICDO3:
        # topography = site, not a specimen type: collection.bodySite coding:icd-o-3; type stays the root concept
        spec["_bodySite"] = cc(coding(ICDO3, tid, tname, version))
        return cc(coding(SNOMED, *SPECIMEN_ROOT), text=tname)
    original = coding(system, tid, tname, version)
    el = _cm_element("mvgs-cm-tissue-sct", system, tid)
    sct = None
    if el is None:
        ctx.warn(P + "tissueTypeId", f"{tid} not in mvgs-cm-tissue-sct; Specimen.type uses the root concept")
    elif tname and not _labels_agree(tname, el.get("display", "")):
        ctx.warn(P + "tissueTypeName", f"tissueTypeName {tname!r} contradicts {tid} ({el.get('display')!r}); "
                                       "Specimen.type uses the root concept, original coding kept")
        # Coding.display must be the ontology's label for the code; the contradicting name stays in type.text
        original = coding(system, tid, el.get("display") or None, version)
    else:
        hits = translate("mvgs-cm-tissue-sct", tid, system)
        sct = hits[0] if hits else None
    if sct is None:
        ctx.rep("grz-specimen-type-root")
        sct = coding(SNOMED, *SPECIMEN_ROOT)
    return cc(sct, original, text=tname)


def _conservation(ctx, sc: str | None, spec: dict, paths: list):
    if not sc:
        return
    hits = translate("mvgs-cm-grz-sample-conservation-sct", sc)
    local = local_coding("mvgs-cs-grz-sample-conservation", sc)
    if hits:
        spec["processing"] = [{"procedure": cc({**hits[0], "system": SNOMED}, local)}]
        paths.append(P + "sampleConservation")
    elif sc == "fresh-tissue":
        spec["note"] = [{"text": "Sample conservation: fresh tissue (not fixed, not frozen)"}]
        ctx.preserve(P + "sampleConservation", "grz-fresh-tissue-note")
    else:
        ctx.drop(P + "sampleConservation", sc, "catch-all value; no processing step")


# ---- Tumorzellgehalt ------------------------------------------------------------------------------------------
def _tumor_cell_count(ctx, parts, j: int, tcc: dict, subject: dict, spec_ref: dict):
    if tcc.get("count") is None:
        return
    obs = ctx.new("Observation", *parts, "tumor-cell-count", j, profile=TZG_PROFILE)
    paths = [P + "tumorCellCount[].count"]
    m = tcc.get("method")
    if m in TZG_METHOD:
        method = cc(coding(TZG_METHOD_CS, *TZG_METHOD[m]))
        paths.append(P + "tumorCellCount[].method")
    elif m == "other":
        method = cc(text="other method (genomDE tumorCellCount.method 'other')")
        ctx.preserve(P + "tumorCellCount[].method", "grz-tumor-cell-count-method-text")
    else:                       # 'unknown' or missing: Observation.method is 1..1
        method = {"extension": [dar_ext("unknown")]}
        if m:
            ctx.drop(P + "tumorCellCount[].method", m, "unknown method; data-absent-reason")
    obs.update(
        status="final",
        category=[{"coding": [{"system": OBS_CATEGORY, "code": "laboratory", "display": "Laboratory"}]}],
        code=cc(coding(LOINC, "93356-4", "Cells with cytogenetic abnormality [#] in Blood or Tissue by Molecular "
                                         "genetics method")),
        subject=subject,
        specimen=spec_ref,
        valueQuantity={"value": tcc["count"], "unit": "percent", "system": UCUM, "code": "%"},
        method=method,
    )
    ctx.add(obs, *paths)


# ---- genomic-study-analysis ------------------------------------------------------------------------------------
def _family(ctx) -> str:
    st = ctx.refs.get("genomic_study")
    if st:
        res = ctx.bundle.entries.get(st["reference"], {}).get("resource", {})
        if any(MOLGEN in p for p in res.get("meta", {}).get("profile", [])):
            return "molgen"
        if any(MTB in p for p in res.get("meta", {}).get("profile", [])):
            return "mtb"
    return "mtb" if (ctx.dk.get("submission") or {}).get("diseaseType") == "oncological" else "molgen"


def _analysis(ctx, parts, ld: dict, subject: dict, spec_ref: dict) -> dict:
    fam = _family(ctx)
    an = ctx.new("Procedure", *parts, "genomic-study-analysis", profile=ANALYSIS_PROFILE[fam])
    paths, exts = [], []
    sd = ld.get("sequenceData") or {}

    lt = ld.get("libraryType")
    method_types = translate("mvgs-cm-grz-library-type-method-type", lt) if lt else []
    for c in method_types:
        exts.append(ext(EXT_METHOD_TYPE, valueCodeableConcept=cc(c)))
    if lt and lt not in CATCH_ALL:
        # Procedure.code is 0..0 on both analysis profiles: the exact library type (incl. the long-read
        # qualifier, which no method-type code carries) goes into the GR title extension
        lc = local_coding(LIBRARY_CS, lt) or {}
        exts.append(ext(EXT_TITLE, valueString=f"{lc.get('display', lt)} (GRZ libraryType {lt})"))
        if lt.endswith("_lr"):
            ctx.rep("grz-long-read-title")
        paths.append(P + "libraryType")
    elif lt:
        ctx.drop(P + "libraryType", lt, "catch-all value; no method type")
    st = ld.get("sequenceType")
    if st == "rna":
        exts.append(ext(EXT_METHOD_TYPE, valueCodeableConcept=cc(coding(METHOD_TYPE_CS, "rnaseq-transcriptomics",
                                                                        "RNA Sequencing (RNA-Seq)"))))
        paths.append(P + "sequenceType")
    elif st == "dna":
        if method_types:   # panel / WES / WGS method types denote DNA sequencing
            paths.append(P + "sequenceType")
        else:
            ctx.drop(P + "sequenceType", st, "DNA without a library method type has no method-type code")

    gb = sd.get("referenceGenome")
    if gb in GENOME_BUILD:
        exts.append(ext(EXT_GENOME_BUILD, valueCodeableConcept=cc(coding(LOINC, *GENOME_BUILD[gb]))))
        paths.append(P + "sequenceData.referenceGenome")
    elif gb:
        ctx.drop(P + "sequenceData.referenceGenome", gb, "no LOINC answer code")

    ss = ld.get("sequenceSubtype")
    if ss in SOURCE_CLASS:
        exts.append(ext(EXT_SOURCE_CLASS, valueCodeableConcept=cc(coding(LOINC, *SOURCE_CLASS[ss]))))
        paths.append(P + "sequenceSubtype")
    elif ss:
        ctx.drop(P + "sequenceSubtype", ss, "catch-all value; genomic-source-class omitted")

    exts.append(ext(EXT_SPECIMEN, valueReference=spec_ref))
    exts.extend(_devices(ctx, parts, ld, sd))
    q = _qc(ctx, fam, ld, sd)
    if q:
        exts.append(q)

    lab = ctx.refs.get("lab")
    an.update(
        extension=exts,
        status="completed",
        category=cc(coding(OBS_CATEGORY, "laboratory")),
        subject=subject,
        performer=[{"actor": lab}] if lab else None,
    )
    return ctx.add(an, *paths)


def _link_to_study(ctx, an_ref: dict):
    st = ctx.refs.get("genomic_study")
    entry = ctx.bundle.entries.get(st["reference"]) if st else None
    if not entry:
        ctx.warn(P + "labDataName", "no genomic study (grz.donors); analysis not linked to a study")
        return
    entry["resource"].setdefault("extension", []).append(ext(EXT_ANALYSIS, valueReference=an_ref))


# ---- devices ---------------------------------------------------------------------------------------------------
def _present(v) -> bool:
    return isinstance(v, str) and v.strip().lower() not in ABSENT_TEXT


def _devices(ctx, parts, ld: dict, sd: dict) -> list:
    out = []
    mtb_fn = lambda code, display: coding(DEVICE_FUNCTION_CS, code, display)   # noqa: E731
    specs = [
        ("sequencer", "sequencerModel", "sequencerManufacturer", cc(mtb_fn("sequencing-device", "Sequenziergerät"))),
        ("sequencing-kit", "kitName", "kitManufacturer", cc(mtb_fn("sequencing-kit", "Sequenzier-Kit"))),
        ("library-prep-kit", "libraryPrepKit", "libraryPrepKitManufacturer",
         cc(mtb_fn("library-preparation-kit", "Library-Preparation Kit"))),
    ]
    for role, nk, mk, fn in specs:
        r = _device(ctx, parts, role, ld, nk, mk, None)
        if r:
            out.append(_device_ext(r, fn))

    # enrichment kit: the manufacturer enum carries 'none' when no enrichment was done (WGS)
    em, ed = ld.get("enrichmentKitManufacturer"), ld.get("enrichmentKitDescription")
    if em == "none" and not _present(ed):
        ctx.drop(P + "enrichmentKitManufacturer", em, "no enrichment kit")
        if ed:
            ctx.drop(P + "enrichmentKitDescription", ed, "no enrichment kit")
    else:
        panel = (ld.get("libraryType") or "").startswith("panel")
        fn = (mtb_fn("gene-panel", "Genpanel") if panel and ctx.is_2027
              else mtb_fn("library-preparation-kit", "Library-Preparation Kit"))
        definition = _panel_definition(ed) if panel and ctx.is_2027 else None
        r = _device(ctx, parts, "enrichment-kit", ld, "enrichmentKitDescription", "enrichmentKitManufacturer",
                    None, definition=definition)
        if r:
            out.append(_device_ext(r, cc(fn, local_coding(FUNCTION_CS, "enrichment-kit"))))

    # software: pipeline and variant callers
    r = _device(ctx, parts, "pipeline", sd, "bioinformaticsPipelineName", None, "bioinformaticsPipelineVersion",
                path_prefix=P + "sequenceData.")
    if r:
        out.append(_device_ext(r, cc(local_coding(FUNCTION_CS, "bioinformatics-pipeline"))))
        ctx.rep("grz-software-device")
    for i, caller in enumerate(sd.get("callerUsed") or []):
        r = _device(ctx, parts, f"caller-{i}", caller, "name", None, "version",
                    path_prefix=P + "sequenceData.callerUsed[].")
        if r:
            out.append(_device_ext(r, cc(local_coding(FUNCTION_CS, "variant-caller"))))
            ctx.rep("grz-software-device")
    return out


def _device_ext(dev_ref: dict, function: dict) -> dict:
    return ext(EXT_DEVICE, extension=[ext("device", valueReference=dev_ref),
                                      ext("function", valueCodeableConcept=function)])


def _device(ctx, parts, role: str, src: dict, name_key: str, mfr_key: str | None, version_key: str | None,
            path_prefix: str = P, definition: dict | None = None) -> dict | None:
    name = src.get(name_key)
    mfr = src.get(mfr_key) if mfr_key else None
    version = src.get(version_key) if version_key else None
    paths = []
    if name is not None and not _present(name):
        ctx.drop(path_prefix + name_key, name, "no name ('na')")
        name = None
    if mfr is not None and (not _present(mfr) or mfr in CATCH_ALL):
        ctx.drop(path_prefix + mfr_key, mfr, "catch-all manufacturer value")
        mfr = None
    if not name and not mfr:
        return None
    dev = ctx.new("Device", *parts, "device", role, profile=DEVICE_PROFILE)
    if name:
        paths.append(path_prefix + name_key)
    if mfr:
        paths.append(path_prefix + mfr_key)
    if version:
        paths.append(path_prefix + version_key)
    dev.update(
        definition=definition,
        manufacturer=mfr,
        deviceName=[{"name": name, "type": "user-friendly-name"}] if name else None,
        version=[{"value": str(version)}] if version else None,
    )
    if definition:
        ctx.rep("mtb-panel-devicedefinition")
    return ctx.add(dev, *paths)


def _panel_definition(desc: str | None) -> dict | None:
    n = _norm(desc)
    if not n:
        return None
    for keys, did, display in PANEL_CATALOGUE:
        if any(k in n for k in keys):
            # logical reference by canonical: the catalogue DeviceDefinitions are package content, not bundle entries,
            # so a literal DeviceDefinition/<id> would only resolve on a server preloaded with the MTB examples
            return {"type": "DeviceDefinition", "display": display,
                    "identifier": {"system": "urn:ietf:rfc:3986", "value": f"{MTB}DeviceDefinition/{did}"}}
    return None


# ---- QC -------------------------------------------------------------------------------------------------------
def _num(v):
    return int(v) if isinstance(v, float) and v.is_integer() else v


def _qc(ctx, fam: str, ld: dict, sd: dict) -> dict | None:
    sub, text = [], []
    q = P + "sequenceData."
    if sd.get("meanDepthOfCoverage") is not None:
        sub.append(ext("read-depth", valueQuantity={"value": sd["meanDepthOfCoverage"], "unit": "x",
                                                    "system": UCUM, "code": "1"}))
        ctx.cover(q + "meanDepthOfCoverage")
    if sd.get("targetedRegionsAboveMinCoverage") is not None:
        pct = round(sd["targetedRegionsAboveMinCoverage"] * 100, 6)
        sub.append(ext("sequencing-coverage", valueQuantity={"value": _num(pct), "unit": "%", "system": UCUM,
                                                             "code": "%"}))
        ctx.cover(q + "targetedRegionsAboveMinCoverage")
    layout = ld.get("sequencingLayout")
    if layout and layout not in CATCH_ALL:
        if fam == "mtb":   # unbound MII slot: the local coding is conformant
            sub.append(ext("sequencing-read-type", valueCodeableConcept=cc(local_coding(LAYOUT_CS, layout))))
            ctx.cover(P + "sequencingLayout")
        else:              # GR metrics has no read-type slot
            text.append(f"sequencingLayout={layout}")
            ctx.preserve(P + "sequencingLayout", "grz-qc-metrics-description")
    elif layout:
        ctx.drop(P + "sequencingLayout", layout, "catch-all value")
    if sd.get("minCoverage") is not None:
        text.append(f"minCoverage={_num(sd['minCoverage'])}x")
        ctx.preserve(q + "minCoverage", "grz-qc-metrics-description")
    pq = sd.get("percentBasesAboveQualityThreshold") or {}
    if pq.get("percent") is not None:
        thr = f" (Q>={_num(pq['minimumQuality'])})" if pq.get("minimumQuality") is not None else ""
        text.append(f"percentBasesAboveQualityThreshold={_num(pq['percent'])}%{thr}")
        ctx.preserve(q + "percentBasesAboveQualityThreshold.percent", "grz-qc-metrics-description")
        if thr:
            ctx.preserve(q + "percentBasesAboveQualityThreshold.minimumQuality", "grz-qc-metrics-description")
    fm = ld.get("fragmentationMethod")
    if fm in ("sonication", "enzymatic", "none"):
        text.append(f"fragmentationMethod={fm}")
        ctx.preserve(P + "fragmentationMethod", "grz-qc-metrics-description")
    elif fm:
        ctx.drop(P + "fragmentationMethod", fm, "catch-all value")
    if isinstance(sd.get("nonCodingVariants"), bool):
        text.append(f"nonCodingVariants={str(sd['nonCodingVariants']).lower()}")
        ctx.preserve(q + "nonCodingVariants", "grz-qc-metrics-description")
    if text:
        sub.append(ext("metrics-description", valueString="; ".join(text)))
    if not sub:
        return None
    return ext(EXT_QC if fam == "mtb" else EXT_METRICS, extension=sub)


def _drop_files(ctx, files: list):
    if not files:
        return
    for f in FILE_FIELDS:
        n = sum(1 for x in files if x.get(f) not in (None, ""))
        if n:
            ctx.drop(P + "sequenceData.files[]." + f, f"{n} file(s)",
                     "NOMAP: raw sequencing files stay in the GRZ, not ingested into MII KDS")
