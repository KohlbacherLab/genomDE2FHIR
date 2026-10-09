"""grz.labdata: Specimen, genomic-study-analysis, Devices, QC and Tumorzellgehalt per donors[].labData[]."""
import csv
import json
from pathlib import Path

import pytest
from conftest import corpus, load, resources

from genomde2fhir.systems import SNOMED

FIX = Path(__file__).parent / "fixtures" / "grz_labdata"
REPO = Path(__file__).resolve().parents[2]
CSV = Path(__file__).resolve().parents[1] / "src" / "genomde2fhir" / "data" / "mapping" / "mapping_grz.csv"
PREFIX = "donors[].labData[]."

MTB_AN = "modul-mtb/StructureDefinition/mii-pr-mtb-genomic-study-analysis"
MOLGEN_AN = "modul-molgen/StructureDefinition/mii-pr-molgen-genomic-study-analysis"
SPECIMEN = "modul-biobank/StructureDefinition/SpecimenCore"
DEVICE = "modul-mtb/StructureDefinition/genomic-study-device"
TZG = "mii-pr-mtb-tumorzellgehalt"
GR = "http://hl7.org/fhir/uv/genomics-reporting/StructureDefinition/"
MTB = "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/"
QC = MTB + "StructureDefinition/mii-ex-mtb-genomic-study-analysis-qc"


def block_rows() -> dict:
    rows = csv.DictReader(CSV.open(encoding="utf-8"))
    return {r["path"]: r["status"] for r in rows if r["path"].startswith(PREFIX)}


def by_profile(bundle, rtype, suffix):
    return [r for r in resources(bundle, rtype) if any(p.endswith(suffix) for p in r.get("meta", {}).get("profile", []))]


def exts(r, url):
    return [e for e in r.get("extension", []) if e["url"] == url]


def sub(e, url):
    return next((s for s in e.get("extension", []) if s["url"] == url), None)


def index(bundle):
    return {e["fullUrl"]: e["resource"] for e in bundle["entry"]}


def devices_of(bundle, an):
    idx = index(bundle)
    out = []
    for e in exts(an, GR + "genomic-study-analysis-device"):
        dev = idx[sub(e, "device")["valueReference"]["reference"]]
        fn = [c["code"] for c in sub(e, "function")["valueCodeableConcept"]["coding"]]
        out.append((dev, fn))
    return out


def analysis_for(bundle, spec):
    for an in resources(bundle, "Procedure"):
        for e in exts(an, GR + "genomic-study-analysis-specimen"):
            if e["valueReference"]["reference"] == f"urn:uuid:{spec['id']}":
                return an
    raise AssertionError(f"no analysis for Specimen/{spec['id']}")


def spec_named(bundle, name):
    return next(s for s in resources(bundle, "Specimen") if s["identifier"][0]["value"].endswith("|" + name))


# ---- corpus files ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name,family", [("grz-paired-onco-01.json", MTB_AN), ("grz-paired-rd-01.json", MOLGEN_AN),
                                         ("grz-paired-hereditary-01.json", MOLGEN_AN)])
def test_paired_examples(convert_dk, name, family):
    f = REPO / "example-data" / "grz" / name
    dk = load(f)
    bundle, rep = convert_dk(dk, str(f))
    ld = dk["donors"][0]["labData"][0]
    pat = resources(bundle, "Patient")[0]
    [spec] = by_profile(bundle, "Specimen", SPECIMEN)
    assert spec["subject"]["reference"] == f"urn:uuid:{pat['id']}"
    assert spec["collection"]["collectedDateTime"] == ld["sampleDate"]
    assert spec["accessionIdentifier"]["value"].endswith("|" + ld["barcode"])   # "<submitterId>|<barcode>"
    codes = {c["system"]: c["code"] for c in spec["type"]["coding"]}
    assert codes[SNOMED] == "119297000"                      # blood (BTO:0000089 / UBERON:0000178)
    assert ld["tissueTypeId"] in codes.values()
    [an] = by_profile(bundle, "Procedure", family)
    assert an["status"] == "completed" and an["subject"] == spec["subject"]
    build = exts(an, GR + "genomic-study-analysis-genome-build")[0]["valueCodeableConcept"]["coding"][0]
    assert build["code"] == {"GRCh37": "LA14029-5", "GRCh38": "LA26806-2"}[ld["sequenceData"]["referenceGenome"]]
    # study -> analysis link
    study = [r for r in resources(bundle, "Procedure") if r is not an and exts(r, GR + "genomic-study-analysis-ext")]
    assert study and exts(study[0], GR + "genomic-study-analysis-ext")[0]["valueReference"]["reference"] == \
        f"urn:uuid:{an['id']}"
    # devices: sequencer, sequencing kit, library prep kit, enrichment kit, pipeline, callers
    devs = devices_of(bundle, an)
    fns = [fn[0] for _, fn in devs]
    assert fns.count("sequencing-device") == 1 and "sequencing-kit" in fns and "library-preparation-kit" in fns
    seq = next(d for d, fn in devs if fn[0] == "sequencing-device")
    assert seq["deviceName"][0]["name"] == ld["sequencerModel"] and seq["manufacturer"] == ld["sequencerManufacturer"]
    assert all(any(p.endswith(DEVICE) for p in d["meta"]["profile"]) for d, _ in devs)
    pipe = next(d for d, fn in devs if "bioinformatics-pipeline" in fn)
    assert pipe["version"][0]["value"] == ld["sequenceData"]["bioinformaticsPipelineVersion"]
    assert len([1 for _, fn in devs if "variant-caller" in fn]) == len(ld["sequenceData"]["callerUsed"])
    # QC / metrics
    q = exts(an, QC if family == MTB_AN else GR + "genomic-study-analysis-metrics")[0]
    assert sub(q, "read-depth")["valueQuantity"]["value"] == ld["sequenceData"]["meanDepthOfCoverage"]
    assert sub(q, "sequencing-coverage")["valueQuantity"]["code"] == "%"
    assert "minCoverage=" in sub(q, "metrics-description")["valueString"]
    # tumour cell content
    tzg = by_profile(bundle, "Observation", TZG)
    assert len(tzg) == len(ld.get("tumorCellCount") or [])
    for o in tzg:
        assert o["specimen"]["reference"] == f"urn:uuid:{spec['id']}" and o["valueQuantity"]["code"] == "%"
    assert not [w for w in rep.warnings if w[0].startswith("(")]


def test_multi_donor_edge(convert_dk):
    f = REPO / "example-data" / "grz" / "grz-edge-correction-multi-donor.json"
    dk = load(f)
    bundle, _ = convert_dk(dk, str(f))
    n_lab = sum(len(d.get("labData") or []) for d in dk["donors"])
    specs = by_profile(bundle, "Specimen", SPECIMEN)
    assert len(specs) == n_lab == len(resources(bundle, "Procedure")) - 1      # + one genomic study
    assert len({s["subject"]["reference"] for s in specs}) == len(dk["donors"])


def test_corpus_sample_converts(convert_dk):
    files = [f for f in corpus("grz") if "synthData" in str(f)][:25]
    assert len(files) >= 3
    for f in files:
        dk = load(f)
        bundle, rep = convert_dk(dk, str(f))
        n_lab = sum(len(d.get("labData") or []) for d in dk["donors"])
        assert len(by_profile(bundle, "Specimen", SPECIMEN)) == n_lab
        fam = MTB_AN if dk["submission"]["diseaseType"] == "oncological" else MOLGEN_AN
        assert len(by_profile(bundle, "Procedure", fam)) == n_lab
        assert not [w for w in rep.warnings if w[0].startswith("(")], rep.warnings


def test_deterministic_ids(convert_dk):
    f = REPO / "example-data" / "grz" / "grz-paired-onco-01.json"
    b1, _ = convert_dk(load(f))
    b2, _ = convert_dk(load(f))
    assert [e["fullUrl"] for e in b1["entry"]] == [e["fullUrl"] for e in b2["entry"]]


# ---- synthetic fixtures ------------------------------------------------------------------------------------
def test_fixture_oncology_edges(convert_dk):
    dk = load(FIX / "grz-labdata-onco-edge.json")
    bundle, rep = convert_dk(dk)
    drops = {(p, v) for p, v, _ in rep.dropped}

    # tumor-rna: panel + RNA, FFPE, SNOMED tissue code, catalogue panel, tumour cell counts
    s = spec_named(bundle, "tumor-rna")
    assert s["type"]["coding"] == [{"system": SNOMED, "code": "119376003", "display": "Tissue specimen"}]
    assert (PREFIX + "tissueOntology.version", "2024.03") in drops          # not a SNOMED edition URI
    assert s["processing"][0]["procedure"]["coding"][0]["code"] == "787376009"
    an = analysis_for(bundle, s)
    mt = [e["valueCodeableConcept"]["coding"][0]["code"] for e in exts(an, GR + "genomic-study-analysis-method-type")]
    assert mt == ["gene-panel", "rnaseq-transcriptomics"]
    assert exts(an, GR + "genomic-study-analysis-genomic-source-class")[0]["valueCodeableConcept"]["coding"][0][
        "code"] == "LA6684-0"
    enrich = [(d, fn) for d, fn in devices_of(bundle, an) if "enrichment-kit" in fn]
    assert enrich and enrich[0][1][0] == "gene-panel"
    assert enrich[0][0]["definition"]["identifier"]["value"].endswith("/DeviceDefinition/mii-dd-mtb-panel-tso-500")
    q = exts(an, QC)[0]
    assert sub(q, "sequencing-read-type")["valueCodeableConcept"]["coding"][0]["code"] == "paired-end"
    desc = sub(q, "metrics-description")["valueString"]
    assert "fragmentationMethod=enzymatic" in desc and "nonCodingVariants=true" in desc and "(Q>=30)" in desc
    assert len([1 for _, fn in devices_of(bundle, an) if "variant-caller" in fn]) == 2
    tzg = [o for o in by_profile(bundle, "Observation", TZG) if o["specimen"]["reference"] == f"urn:uuid:{s['id']}"]
    methods = [o["method"] for o in tzg]
    assert methods[0]["coding"][0]["code"] == "histologic" and methods[1]["coding"][0]["code"] == "bioinformatic"
    assert "text" in methods[2] and methods[3]["extension"][0]["valueCode"] == "unknown"
    assert [o["valueQuantity"]["value"] for o in tzg] == [40, 35.5, 30, 20]

    # normal-lr: long-read WXS, cryo, ICD-O-3 topography -> bodySite, catch-alls dropped
    s = spec_named(bundle, "normal-lr")
    assert s["collection"]["bodySite"]["coding"][0] == {"system": "http://terminology.hl7.org/CodeSystem/icd-o-3",
                                                        "code": "C34.1", "version": "2019",
                                                        "display": "Oberlappen der Lunge"}
    assert s["type"]["coding"][0]["code"] == "123038009" and "accessionIdentifier" not in s
    assert s["processing"][0]["procedure"]["coding"][0]["code"] == "27872000"
    an = analysis_for(bundle, s)
    assert "long-read" in exts(an, GR + "genomic-study-analysis-title")[0]["valueString"]
    assert not exts(an, GR + "genomic-study-analysis-genomic-source-class")
    assert not sub(exts(an, QC)[0], "sequencing-read-type")
    enrich = [d for d, fn in devices_of(bundle, an) if "enrichment-kit" in fn]
    assert not enrich                     # manufacturer 'other' and description 'na' -> nothing left
    for p, v in [("sequenceSubtype", "other"), ("sequencingLayout", "other"), ("fragmentationMethod", "unknown"),
                 ("barcode", "na"), ("enrichmentKitManufacturer", "other")]:
        assert (PREFIX + p, v) in drops

    # saliva-wgs: code/name contradiction -> root concept + original coding, warning; no enrichment kit
    s = spec_named(bundle, "saliva-wgs")
    assert [c["code"] for c in s["type"]["coding"]] == ["123038009", "UBERON:0002046"]
    assert s["type"]["coding"][1]["display"] == "thyroid gland" and s["type"]["text"] == "saliva"
    assert any("contradicts" in m for _, m in rep.warnings)
    assert "processing" not in s and (PREFIX + "sampleConservation", "other") in drops
    an = analysis_for(bundle, s)
    assert not [1 for _, fn in devices_of(bundle, an) if "enrichment-kit" in fn]
    assert (PREFIX + "enrichmentKitManufacturer", "none") in drops

    # misc: libraryType other, unknown ontology -> text, enrichment manufacturer unknown -> name only
    s = spec_named(bundle, "misc")
    assert "MyLocalTissues" in s["type"]["text"]
    an = analysis_for(bundle, s)
    assert not exts(an, GR + "genomic-study-analysis-method-type")
    enrich = [d for d, fn in devices_of(bundle, an) if "enrichment-kit" in fn]
    assert enrich[0]["deviceName"][0]["name"] == "Some custom capture" and "manufacturer" not in enrich[0]
    assert (PREFIX + "libraryType", "other") in drops


def test_fixture_oncology_2026(convert_dk):
    bundle, rep = convert_dk(load(FIX / "grz-labdata-onco-edge.json"), profile_set="2026")
    an = analysis_for(bundle, spec_named(bundle, "tumor-rna"))
    enrich = [(d, fn) for d, fn in devices_of(bundle, an) if "enrichment-kit" in fn]
    assert enrich[0][1][0] == "library-preparation-kit" and "definition" not in enrich[0][0]
    assert not [w for w in rep.warnings if w[0] == "(profile)"]


def test_fixture_rare_duo(convert_dk):
    dk = load(FIX / "grz-labdata-rd-duo.json")
    bundle, rep = convert_dk(dk)
    ans = by_profile(bundle, "Procedure", MOLGEN_AN)
    assert len(ans) == 2 and not by_profile(bundle, "Procedure", MTB_AN)
    pats = {p["id"] for p in resources(bundle, "Patient")}
    assert {a["subject"]["reference"].split(":")[-1] for a in ans} == pats
    mother = spec_named(bundle, "mother-wgs")
    assert {c["system"] for c in mother["type"]["coding"]} == {SNOMED, "http://purl.obolibrary.org/obo/bto.owl"}
    assert mother["note"][0]["text"].startswith("Sample conservation: fresh tissue")
    for an in ans:
        assert not exts(an, QC)
        m = exts(an, GR + "genomic-study-analysis-metrics")[0]
        assert "sequencingLayout=" in sub(m, "metrics-description")["valueString"]
    # both analyses hang off the one genomic study
    study = [r for r in resources(bundle, "Procedure") if exts(r, GR + "genomic-study-analysis-ext")]
    assert len(study) == 1 and len(exts(study[0], GR + "genomic-study-analysis-ext")) == 2
    assert not [w for w in rep.warnings if w[0].startswith("(")]


# ---- coverage ----------------------------------------------------------------------------------------------
KNOWN_UNCOVERABLE = {}   # path -> reason; every MAPPED labData row is reachable with the inputs below


def test_mapped_rows_covered(convert_dk):
    rows = block_rows()
    covered, preserved = set(), set()
    inputs = [load(FIX / "grz-labdata-onco-edge.json"), load(FIX / "grz-labdata-rd-duo.json")]
    inputs += [load(f) for f in corpus("grz")[:40]]
    for dk in inputs:
        _, rep = convert_dk(dk)
        covered |= rep.covered
        preserved |= rep.preserved
    mapped = {p for p, s in rows.items() if s == "MAPPED"}
    missing = mapped - covered - set(KNOWN_UNCOVERABLE)
    assert not missing, sorted(missing)
    draft = {p for p, s in rows.items() if s == "DRAFT"}
    assert draft <= preserved | covered, sorted(draft - preserved - covered)
    assert not (covered | preserved) - set(rows) - {p for p in covered | preserved if not p.startswith(PREFIX)}


def test_fixtures_schema_valid():
    from genomde2fhir.io import classify, validate_input
    for f in FIX.glob("*.json"):
        dk = json.loads(f.read_text())
        assert classify(dk) == "grz"
        ok, findings = validate_input(dk, f.name)
        assert ok, findings
