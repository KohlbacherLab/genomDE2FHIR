"""Oncology complexBiomarkers / expressionVariants / sbsSignatures -> MTB biomarker Observations."""
import csv
from pathlib import Path

import pytest
from conftest import REPO, load, resources

from genomde2fhir.builders.onco import molecular_biomarkers, molecular_expression, molecular_signatures
from genomde2fhir.context import Ctx
from genomde2fhir.identity import case_key

FIXTURE = Path(__file__).parent / "fixtures" / "onco_biomarkers" / "synthetic_biomarkers.json"
CORPUS = [  # schema-valid corpus files: TMB-only (DNPM), all flags false + ploidy, mixed flags, SBS signatures
    "example-data/oncology/OncologySubmission_044AFF6262356F2F8EC60039DC08AE36FBAA011DE29740CBC83E9FA5643E4640.json",
    "example-data/synthData-v1/nct/case_013.json",
    "example-data/synthData-v1/nct/case_015.json",
    "example-data/synthData-v1/nct/case_036.json",
]
PREFIXES = ("molecular.complexBiomarkers[]", "molecular.expressionVariants[]", "molecular.sbsSignatures[]")
MTB = "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/"
V3 = "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"


def block_rows(status: str | None = None) -> list[str]:
    with open(REPO / "mapping" / "mapping_kdk_oncology.csv", newline="", encoding="utf-8") as f:
        return [r["path"] for r in csv.DictReader(f)
                if r["path"].startswith(PREFIXES) and (status is None or r["status"] == status)]


def by_identifier(bundle, profile, source_id):
    return [r for r in resources(bundle, "Observation", profile)
            if any(i["value"].endswith("|" + source_id) for i in r.get("identifier", []))]


def interp_code(r):
    return [c["code"] for i in r.get("interpretation", []) for c in i["coding"]]


@pytest.fixture(scope="module")
def fixture_2027():
    from genomde2fhir import convert
    bundle, rep = convert(load(FIXTURE), str(FIXTURE), "2027")
    assert rep.status == "converted"
    return bundle, rep


# ---- corpus -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("rel", CORPUS)
def test_corpus_complex_biomarkers(rel, convert_dk):
    path = REPO / rel
    if not path.exists():
        pytest.skip(f"missing {rel}")
    dk = load(path)
    bundle, rep = convert_dk(dk, rel)
    for cb in dk["molecular"]["complexBiomarkers"]:
        sid = cb["identifier"]
        if "tmb" in cb:
            (tmb,) = by_identifier(bundle, "mii-pr-mtb-mutationslast", sid)
            assert tmb["code"]["coding"][0]["code"] == "94076-7"
            assert tmb["valueQuantity"]["value"] == cb["tmb"]
            assert tmb["valueQuantity"]["code"] == "1/1000000{Base}"
            assert {c["coding"][0]["code"] for c in tmb["category"]} >= {"laboratory", "biomarker-category"}
        if "hrdHigh" in cb:
            (hrd,) = by_identifier(bundle, "mii-pr-mtb-hrd-score", sid)
            assert hrd["code"]["coding"][0]["code"] == "107286-7"
            assert "valueInteger" not in hrd                      # no numeric score in the source
            assert interp_code(hrd) == ["H" if cb["hrdHigh"] else "L"]
            comps = {c["code"]["coding"][0]["code"]: c["interpretation"][0]["coding"][0]["code"]
                     for c in hrd.get("component", [])}
            if "lstHigh" in cb:
                assert comps["C120466"] == ("H" if cb["lstHigh"] else "L")
            if "taiHigh" in cb:
                assert comps["C129774"] == ("H" if cb["taiHigh"] else "L")
        if "ploidy" in cb:
            (pl,) = by_identifier(bundle, "mii-pr-mtb-ploidie", sid)
            assert pl["code"]["coding"][0]["code"] == "C18303"
            assert pl["valueQuantity"] == {"value": cb["ploidy"]}
            assert "interpretation" not in pl
    assert "molecular.complexBiomarkers[].identifier" in rep.covered


def test_corpus_sbs_signatures(convert_dk):
    path = REPO / "example-data/synthData-v1/nct/case_036.json"
    if not path.exists():
        pytest.skip("missing case_036")
    dk = load(path)
    bundle, rep = convert_dk(dk)
    sig = dk["molecular"]["sbsSignatures"][0]
    obs = by_identifier(bundle, "mii-pr-mtb-molekularer-biomarker", sig["identifier"])
    assert len(obs) == len(sig["name"])
    for o in obs:
        assert o["code"]["coding"][0] == {"system": "https://genomde.de/fhir/CodeSystem/mvgs-cs-molecular-feature",
                                          "code": "sbs-signature", "display": "COSMIC single base substitution signature"}
        c = o["valueCodeableConcept"]["coding"][0]
        assert c["system"] == "https://cancer.sanger.ac.uk/cosmic" and c["version"] == sig["version"]
    assert {o["valueCodeableConcept"]["coding"][0]["code"] for o in obs} == set(sig["name"])
    assert "molecular.sbsSignatures[].name[]" in rep.preserved


# The schema-valid corpus has no expressionVariants. The NCT synthetic cases do, but write every KDK identifier as
# {system, value} instead of a string (rejected by the schema). Flattening those objects in memory gives realistic,
# schema-valid inputs for all four expressionType values.
NCT_EXPRESSION = {"case_001.json": "highExpression", "case_018.json": "noExpression",
                  "case_020.json": "normalExpression", "case_023.json": "lowExpression"}


def _flatten_ids(o):
    if isinstance(o, dict):
        if set(o) == {"system", "value"} and o["system"] == "https://genomics.example.org/ids":
            return o["value"]
        return {k: _flatten_ids(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_flatten_ids(x) for x in o]
    return o


@pytest.mark.parametrize("name,etype", NCT_EXPRESSION.items())
def test_corpus_expression_variants(name, etype, convert_dk):
    path = REPO / "example-data/synthData-v1/nct" / name
    if not path.exists():
        pytest.skip(f"missing {name}")
    dk = _flatten_ids(load(path))
    bundle, rep = convert_dk(dk, name)
    evs = dk["molecular"]["expressionVariants"]
    assert etype in {ev["expressionType"] for ev in evs}
    for ev in evs:
        (o,) = by_identifier(bundle, "mii-pr-mtb-rna-seq", ev["identifier"])
        assert o["code"]["coding"][0]["code"] == "69548-6"
        absent = ev["expressionType"] == "noExpression"
        assert o["valueCodeableConcept"]["coding"][0]["code"] == ("LA9634-2" if absent else "LA9633-4")
        assert interp_code(o) == {"highExpression": ["H"], "lowExpression": ["L"], "normalExpression": ["N"],
                                  "noExpression": []}[ev["expressionType"]]
        (gene,) = o["component"]
        assert gene["code"]["coding"][0]["code"] == "48018-6"
        assert gene["valueCodeableConcept"]["coding"][0] == {"system": "http://www.genenames.org",
                                                             "code": ev["gene"]["code"], "display": ev["gene"]["display"]}
        assert o["note"] == [{"text": f"Bewertungsgrundlage: {ev['reference']}"}]
    for p in ("identifier", "expressionType", "gene.code", "gene.display", "gene.system", "reference"):
        assert f"molecular.expressionVariants[].{p}" in rep.covered


# ---- synthetic fixture: enum values and edge cases ----------------------------------------------------------------
def test_fixture_expression_levels(fixture_2027):
    bundle, rep = fixture_2027
    expected = {"ev-high": ("LA9633-4", ["H"]), "ev-low": ("LA9633-4", ["L"]),
                "ev-normal": ("LA9633-4", ["N"]), "ev-none": ("LA9634-2", [])}
    for sid, (value, interp) in expected.items():
        (o,) = by_identifier(bundle, "mii-pr-mtb-rna-seq", sid)
        assert o["code"]["coding"][0]["code"] == "69548-6"
        assert o["valueCodeableConcept"]["coding"][0]["code"] == value
        assert interp_code(o) == interp
        assert o["note"][0]["text"].startswith("Bewertungsgrundlage: ")
        (gene,) = [c for c in o["component"] if c["code"]["coding"][0]["code"] == "48018-6"]
        assert gene["valueCodeableConcept"]["coding"][0]["system"] == "http://www.genenames.org"
        assert {c["coding"][0]["code"] for c in o["category"]} == {"laboratory", "GE"}
    (high,) = by_identifier(bundle, "mii-pr-mtb-rna-seq", "ev-high")
    gene = high["component"][0]["valueCodeableConcept"]["coding"][0]
    assert gene == {"system": "http://www.genenames.org", "code": "HGNC:3236", "version": "2024-10", "display": "EGFR"}


def test_fixture_complex_biomarker_edges(fixture_2027):
    bundle, rep = fixture_2027
    assert not by_identifier(bundle, "", "cb-only-id")
    assert ("molecular.complexBiomarkers[].identifier", "cb-only-id",
            "complex biomarker entry without tmb/ploidy/hrd/lst/tai values") in rep.dropped
    assert len(by_identifier(bundle, "", "cb-tmb-only")) == 1
    (hrd,) = by_identifier(bundle, "mii-pr-mtb-hrd-score", "cb-flags")
    assert interp_code(hrd) == ["H"]
    assert [c["code"]["coding"][0]["code"] for c in hrd["component"]] == ["C120466"]   # taiHigh absent


def test_fixture_sbs_normalisation(fixture_2027):
    bundle, rep = fixture_2027
    obs = by_identifier(bundle, "mii-pr-mtb-molekularer-biomarker", "sbs-edge")
    vals = [o["valueCodeableConcept"] for o in obs]
    codes = [v["coding"][0]["code"] for v in vals if "coding" in v]
    assert codes == ["SBS6", "SBS7a"]                                       # 'SBS 6' normalised, 'SBS6' deduplicated
    assert {v["coding"][0]["version"] for v in vals if "coding" in v} == {"COSMIC v3.4"}
    assert any(v.get("text") == "Signature X (COSMIC v3.4)" and "coding" not in v for v in vals)
    (nover,) = by_identifier(bundle, "mii-pr-mtb-molekularer-biomarker", "sbs-nover")
    assert nover["valueCodeableConcept"]["coding"] == [{"system": "https://cancer.sanger.ac.uk/cosmic", "code": "SBS40"}]
    assert any("Signature X" in m for _, m in rep.warnings)


@pytest.mark.parametrize("raw,norm", [("SBS 6", "SBS6"), ("sbs7A", "SBS7a"), ("SBS-40", "SBS40"), ("SBS10a", "SBS10a"),
                                      ("SBS017b", "SBS17b"), ("DBS2", None), ("Signature 3", None)])
def test_normalise(raw, norm):
    assert molecular_signatures.normalise(raw) == norm


def test_fixture_profile_set_2026():
    from genomde2fhir import convert
    bundle, rep = convert(load(FIXTURE), str(FIXTURE), "2026")
    assert rep.status == "converted"
    (hrd,) = by_identifier(bundle, "mii-pr-mtb-hrd-score", "cb-flags")
    assert "interpretation" not in hrd and "HRD high" in hrd["note"][0]["text"]
    assert hrd["component"][0]["interpretation"][0]["coding"][0]["code"] == "H"
    assert "molecular.complexBiomarkers[].hrdHigh" in rep.preserved


def test_registration():
    dk = load(FIXTURE)
    ctx = Ctx(dk, "oncology", case_key(dk, "oncology"))
    ctx.refs["patient"] = {"reference": "urn:uuid:patient"}
    for m in (molecular_biomarkers, molecular_expression, molecular_signatures):
        m.build(ctx)
    for sid in ("ev-high", "ev-none", "cb-flags", "cb-atfexm92", "sbs-edge", "sbs-0hbctc12"):
        assert ("variant", sid) in ctx.ids
    assert ("variant", "cb-only-id") not in ctx.ids
    observations = [e["fullUrl"] for e in ctx.bundle.entries.values() if e["resource"]["resourceType"] == "Observation"]
    assert sorted(r["reference"] for r in ctx.bag["ngs_results"]) == sorted(observations)
    # complexBiomarkers 'cb-atfexm92' answers with its first resource (TMB)
    first = ctx.bundle.entries[ctx.ids[("variant", "cb-atfexm92")]["reference"]]["resource"]
    assert first["meta"]["profile"][0] == MTB + "mii-pr-mtb-mutationslast"


# ---- coverage -----------------------------------------------------------------------------------------------------
KNOWN_UNCOVERABLE = {}   # every row of the block is reachable (name[] is preserved: local Observation.code)


def test_block_coverage(convert_dk):
    from genomde2fhir import convert
    seen = set()
    for f in [REPO / c for c in CORPUS] + [FIXTURE]:
        if f.exists():
            _, rep = convert(load(f), str(f), "2027")
            seen |= rep.covered | rep.preserved
    mapped = set(block_rows("MAPPED"))
    assert mapped, "no MAPPED rows found for the block"
    assert mapped - seen - set(KNOWN_UNCOVERABLE) == set()
    # DRAFT rows made mappable by REVIEW-TD A / REPRESENTATIONS #18, #20 are implemented as well
    assert set(block_rows()) - seen - set(KNOWN_UNCOVERABLE) == set()


def test_paths_are_table_paths(fixture_2027):
    _, rep = fixture_2027
    used = {p for p in rep.covered | rep.preserved | {d[0] for d in rep.dropped} | {w[0] for w in rep.warnings}
            if p.startswith(PREFIXES)}
    assert used and used <= set(block_rows())
