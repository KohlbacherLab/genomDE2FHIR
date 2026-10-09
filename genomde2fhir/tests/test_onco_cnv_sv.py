"""molecular.copyNumberVariants[] / molecular.structuralVariants[] -> MTB CNV / DNA- and RNA-fusion Observations."""
from pathlib import Path

import pytest
from conftest import corpus, load, resources

from genomde2fhir.data_access import mapping_rows

FIXTURE = Path(__file__).parent / "fixtures" / "onco_cnv_sv" / "cnv_sv_enums.json"
MTB = "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/"
BIOMARKER = MTB + "CodeSystem/mii-cs-mtb-molekulare-biomarker"
CNV = "mii-pr-mtb-copy-number-variant"
DNA = "mii-pr-mtb-dna-fusion"
RNA = "mii-pr-mtb-rna-fusion"
CONSEQUENCE = "mii-pr-molgen-molekulare-konsequenz"
SO = "http://www.sequenceontology.org"
LOINC = "http://loinc.org"
BWHC = "http://bwhc.de/mtb/genetics-copy-number-variant"
MVGS_CNV = "https://genomde.de/fhir/CodeSystem/mvgs-cs-cnv-type"
MVGS_ST = "https://genomde.de/fhir/CodeSystem/mvgs-cs-structure-type"
PREFIXES = ("molecular.copyNumberVariants[].", "molecular.structuralVariants[].")
# MAPPED or made mappable by REVIEW-TD A / REPRESENTATIONS (#21 partner genes, #26 localization, sequenceType)
EXTRA_MAPPABLE = {p + s for p in PREFIXES for s in ("localization", "sequenceType")} | {
    f"molecular.structuralVariants[].{g}.{k}" for g in ("geneA", "geneB") for k in ("code", "display", "system", "version")}


def comps(obs, system, code):
    return [c for c in obs.get("component", []) if any(
        cd.get("system") == system and cd.get("code") == code for cd in c["code"]["coding"])]


def one(obs, system, code):
    hit = comps(obs, system, code)
    assert len(hit) == 1, (code, obs["id"])
    return hit[0]


def codes(cc):
    return {(c.get("system"), c["code"]) for c in cc.get("coding", [])}


def by_identifier(bundle, profile):
    return {o["identifier"][0]["value"].split("|")[-1]: o for o in resources(bundle, "Observation", profile)}


@pytest.fixture(scope="module")
def fixture_result():
    from genomde2fhir import convert
    bundle, rep = convert(load(FIXTURE), str(FIXTURE), "2027")
    assert rep.status == "converted", rep.error
    return bundle, rep


def corpus_with(key, n=3):
    out = []
    for f in corpus("oncology"):
        dk = load(f)
        if (dk.get("molecular") or {}).get(key):
            out.append((f, dk))
        if len(out) >= n:
            break
    if not out:
        pytest.skip(f"no corpus file with molecular.{key}")
    return out


# ---- corpus -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("idx", range(3))
def test_corpus_cnv(convert_dk, idx):
    files = corpus_with("copyNumberVariants")
    if idx >= len(files):
        pytest.skip("fewer corpus files")
    f, dk = files[idx]
    bundle, rep = convert_dk(dk, str(f))
    src = dk["molecular"]["copyNumberVariants"]
    obs = resources(bundle, "Observation", CNV)
    assert len(obs) == len(src)
    first, o = src[0], by_identifier(bundle, CNV)[src[0]["identifier"]]
    assert o["code"]["coding"][0]["code"] == "69548-6" and o["valueCodeableConcept"]["coding"][0]["code"] == "LA9633-4"
    gene = one(o, LOINC, "48018-6")["valueCodeableConcept"]["coding"][0]
    assert gene == {k: v for k, v in {"system": "http://www.genenames.org", "code": first["gene"]["code"],
                                      "display": first["gene"]["display"],
                                      "version": first["gene"].get("version")}.items() if v}
    cnv_type = codes(one(o, BWHC, "type")["valueCodeableConcept"])
    assert (MVGS_CNV, first["cnvType"]) in cnv_type
    so = codes(one(o, LOINC, "48019-4")["valueCodeableConcept"])
    assert so == {(SO, "SO:0001742" if "ain" in first["cnvType"] else "SO:0001743")}
    assert one(o, LOINC, "48000-4")["valueCodeableConcept"]["coding"][0]["display"] == f"Chromosome {first['chromosome']}"
    # every CNV and its consequence are registered for the report
    ids = _ids_of(dk)
    assert all(("variant", s["identifier"]) in ids for s in src)
    assert len(resources(bundle, "Observation", CONSEQUENCE)) >= len(src)
    assert {"molecular.copyNumberVariants[].cnvType", "molecular.copyNumberVariants[].gene.code",
            "molecular.copyNumberVariants[].localization"} <= rep.covered


def _ids_of(dk):
    from genomde2fhir.builders.onco import molecular_cnv, molecular_fusions
    from genomde2fhir.context import Ctx
    from genomde2fhir.identity import case_key
    ctx = Ctx(dk, "oncology", case_key(dk, "oncology"))
    ctx.refs["patient"] = {"reference": "urn:uuid:p"}
    molecular_cnv.build(ctx)
    molecular_fusions.build(ctx)
    assert all(r in ctx.bag["ngs_results"] for r in ctx.ids.values())
    return ctx.ids


@pytest.mark.parametrize("idx", range(3))
def test_corpus_sv(convert_dk, idx):
    files = corpus_with("structuralVariants")
    if idx >= len(files):
        pytest.skip("fewer corpus files")
    f, dk = files[idx]
    bundle, rep = convert_dk(dk, str(f))
    for s in dk["molecular"]["structuralVariants"]:
        prof = RNA if s["sequenceType"] == "RNA" else DNA
        o = by_identifier(bundle, prof)[s["identifier"]]
        assert one(o, BIOMARKER, "five-prime-gene")["valueCodeableConcept"]["coding"][0]["code"] == s["geneA"]["code"]
        assert one(o, BIOMARKER, "three-prime-gene")["valueCodeableConcept"]["coding"][0]["code"] == s["geneB"]["code"]
        assert (MVGS_ST, s["structureType"]) in codes(one(o, LOINC, "48019-4")["valueCodeableConcept"])
        assert len(o["component"]) >= (10 if prof == RNA else 6)


def test_corpus_profile_set_2026(convert_dk):
    for f, dk in corpus_with("copyNumberVariants", 2):
        bundle, _ = convert_dk(dk, str(f), profile_set="2026")
        assert resources(bundle, "Observation", CNV)


# ---- synthetic fixture: enum values and edge cases ------------------------------------------------------

def test_fixture_cnv_types(fixture_result):
    bundle, rep = fixture_result
    obs = by_identifier(bundle, CNV)
    expect = {"completeLoss": ("loss", "SO:0001743"), "heterozygousLoss": ("loss", "SO:0001743"),
              "loss": ("loss", "SO:0001743"), "lowLevelGain": ("low-level-gain", "SO:0001742"),
              "highLevelGain": ("high-level-gain", "SO:0001742"), "gain": (None, "SO:0001742")}
    for t, (dnpm, so) in expect.items():
        o = obs[f"cnv-{t}"]
        ct = codes(one(o, BWHC, "type")["valueCodeableConcept"])
        assert (MVGS_CNV, t) in ct
        assert ((BWHC, dnpm) in ct) if dnpm else not any(s == BWHC for s, _ in ct)
        assert codes(one(o, LOINC, "48019-4")["valueCodeableConcept"]) == {(SO, so)}
    assert rep.representations["cnv-type-no-dnpm-code"] == 1


def test_fixture_cnv_positions_and_sources(fixture_result):
    bundle, rep = fixture_result
    obs = by_identifier(bundle, CNV)
    assert one(obs["cnv-completeLoss"], LOINC, "81254-5")["valueRange"] == {"low": {"value": 43044295},
                                                                            "high": {"value": 43125364}}
    assert one(obs["cnv-lowLevelGain"], LOINC, "81254-5")["valueRange"] == {"low": {"value": 55019017}}
    assert one(obs["cnv-highLevelGain"], LOINC, "81254-5")["valueRange"] == {"high": {"value": 69000000}}
    assert not comps(obs["cnv-loss"], LOINC, "81254-5")          # no coordinates in source
    assert not comps(obs["cnv-gain"], LOINC, "81254-5")          # start > end dropped
    assert {d[0] for d in rep.dropped if "copyNumberVariants" in d[0]} == {
        "molecular.copyNumberVariants[].startPosition", "molecular.copyNumberVariants[].endPosition"}
    assert codes(one(obs["cnv-heterozygousLoss"], LOINC, "48002-0")["valueCodeableConcept"]) == {(LOINC, "LA6683-2")}
    assert codes(one(obs["cnv-heterozygousLoss"], LOINC, "48000-4")["valueCodeableConcept"]) == {(LOINC, "LA21276-3")}
    assert codes(one(obs["cnv-loss"], LOINC, "48018-6")["valueCodeableConcept"]) == {
        ("http://www.genenames.org", "HGNC:3236")}                 # source without system -> HGNC lock
    assert one(obs["cnv-completeLoss"], LOINC, "48018-6")["valueCodeableConcept"]["coding"][0]["version"] == "2026-07-01"
    # duplicate identifier -> separate resource, id made unique, warned
    assert len(resources(bundle, "Observation", CNV)) == 7
    assert any("duplicate identifier" in m for _, m in rep.warnings)


def test_fixture_structure_types(fixture_result):
    bundle, rep = fixture_result
    dna, rna = by_identifier(bundle, DNA), by_identifier(bundle, RNA)
    assert set(rna) == {"sv-translocationWithCodingRegion", "sv-deletionOfGeneSegments"}
    expect = {"translocation": "SO:0000199", "translocationWithCodingRegion": "SO:0000199",
              "translocationWithNonCodingRegion": "SO:0000199", "inversion": "SO:1000036",
              "deletionOfGeneSegments": "SO:0000159", "duplicationOfGeneSegments": "SO:1000035"}
    for t, so in expect.items():
        o = {**dna, **rna}[f"sv-{t}"]
        assert codes(one(o, LOINC, "48019-4")["valueCodeableConcept"]) == {(SO, so), (MVGS_ST, t)}


def test_fixture_fusion_breakpoints(fixture_result):
    bundle, _ = fixture_result
    o = by_identifier(bundle, DNA)["sv-translocation"]
    for s in ("five-prime-chromosome", "three-prime-chromosome", "five-prime-position", "three-prime-position"):
        c = one(o, BIOMARKER, s)
        assert c["dataAbsentReason"]["coding"][0]["code"] == "unknown" and "valueCodeableConcept" not in c
    assert one(o, BIOMARKER, "five-prime-gene")["valueCodeableConcept"]["coding"][0] == {
        "system": "http://www.genenames.org", "code": "HGNC:1316", "display": "EML4", "version": "2026-07-01"}
    assert one(o, LOINC, "81291-7")["valueCodeableConcept"] == {"text": "t(2;2)(p23;p21)"}
    r = by_identifier(bundle, RNA)["sv-deletionOfGeneSegments"]
    for s in ("transcript-id", "exon-id", "position", "strand"):
        for side in ("five-prime-", "three-prime-"):
            assert one(r, BIOMARKER, side + s)["dataAbsentReason"]["coding"][0]["code"] == "unknown"
    assert codes(one(r, LOINC, "48002-0")["valueCodeableConcept"]) == {(LOINC, "LA6683-2")}   # germline


def test_fixture_localization(fixture_result):
    bundle, rep = fixture_result
    variants = {r["fullUrl"]: r["resource"] for r in bundle["entry"]}
    seen = {}
    for c in resources(bundle, "Observation", CONSEQUENCE):
        target = variants[c["derivedFrom"][0]["reference"]]
        if not any(p in target["meta"]["profile"][0] for p in (CNV, DNA, RNA)):
            continue
        fc = c["component"][0]["valueCodeableConcept"]
        seen[fc["text"]] = {cd["code"] for cd in fc["coding"]}
    assert seen == {"coding": {"SO:0001580"}, "inRegulatoryElements": {"SO:0001566"},
                    "notInCodingAndNotInRegulatoryElements": {"SO:0001537"}}


def test_fixture_registration(fixture_result):
    bundle, _ = fixture_result
    from genomde2fhir.builders.onco import molecular_cnv, molecular_fusions
    from genomde2fhir.context import Ctx
    from genomde2fhir.identity import case_key
    dk = load(FIXTURE)
    ctx = Ctx(dk, "oncology", case_key(dk, "oncology"))
    ctx.refs["patient"] = {"reference": "urn:uuid:p"}
    molecular_cnv.build(ctx)
    molecular_fusions.build(ctx)
    ids = {k[1] for k in ctx.ids if k[0] == "variant"}
    src = dk["molecular"]
    assert ids == {v["identifier"] for v in src["copyNumberVariants"] + src["structuralVariants"]}
    # 7 CNV + 6 SV variants + one consequence each
    assert len(ctx.bag["ngs_results"]) == 2 * (7 + 6)


# ---- coverage ----------------------------------------------------------------------------------------

KNOWN_UNCOVERABLE = {}   # every row of the block is exercised by the fixture


def test_coverage(fixture_result, convert_dk):
    covered = set(fixture_result[1].covered)
    for f, dk in corpus_with("copyNumberVariants", 2):
        covered |= convert_dk(dk, str(f))[1].covered
    rows = mapping_rows("oncology")
    block = {p for p in rows if p.startswith(PREFIXES)}
    mappable = {p for p in block if rows[p]["status"] == "MAPPED"} | (EXTRA_MAPPABLE & block)
    assert mappable - covered - set(KNOWN_UNCOVERABLE) == set()
