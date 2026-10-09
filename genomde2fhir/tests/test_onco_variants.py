"""Oncology molecular.smallVariants[] -> mii-pr-mtb-einfache-variante + MolGen molekulare-konsequenz, and the
mii-pr-mtb-ngs-bericht container for the molecular block."""
import csv
from pathlib import Path

import pytest
from conftest import REPO, load, resources

from genomde2fhir.builders import patient
from genomde2fhir.builders.onco import molecular_report, molecular_variants
from genomde2fhir.context import Ctx
from genomde2fhir.identity import case_key

FIXTURE = Path(__file__).parent / "fixtures" / "onco_variants" / "synthetic_small_variants.json"
CORPUS = [  # schema-valid corpus files: realistic RefSeq variants (NCT) and synthetic UUID transcripts (DNPM)
    "example-data/synthData-v1/nct/case_013.json",
    "example-data/synthData-v1/nct/case_015.json",
    "example-data/synthData-v1/nct/case_036.json",
    "example-data/oncology/OncologySubmission_044AFF6262356F2F8EC60039DC08AE36FBAA011DE29740CBC83E9FA5643E4640.json",
]
PREFIX = "molecular.smallVariants[]"
P_VAR = "mii-pr-mtb-einfache-variante"
P_CONS = "mii-pr-molgen-molekulare-konsequenz"
P_NGS = "mii-pr-mtb-ngs-bericht"
HGNC, HGVS, SO = "http://www.genenames.org", "http://varnomen.hgvs.org", "http://www.sequenceontology.org"
REFSEQ, ENSEMBL = "http://www.ncbi.nlm.nih.gov/refseq", "http://www.ensembl.org"
LOC_SO = {"coding": "SO:0001580", "inRegulatoryElements": "SO:0001566",
          "notInCodingAndNotInRegulatoryElements": "SO:0001537"}


def block_rows(*statuses) -> list[str]:
    with open(REPO / "mapping" / "mapping_kdk_oncology.csv", newline="", encoding="utf-8") as f:
        return [r["path"] for r in csv.DictReader(f) if r["path"].startswith(PREFIX) and r["status"] in statuses]


def comp(obs, code):
    return [c for c in obs.get("component", []) if any(x["code"] == code for x in c["code"]["coding"])]


def one(obs, code):
    (c,) = comp(obs, code)
    return c


def variant_by_id(bundle, source_id):
    out = [r for r in resources(bundle, "Observation", P_VAR)
           if any(i["value"].endswith("|" + source_id) for i in r.get("identifier", []))]
    return out


def full_url(bundle, res):
    return next(e["fullUrl"] for e in bundle["entry"] if e["resource"] is res)


def ngs_report(bundle, dk):
    rid = case_key(dk, "oncology").id("DiagnosticReport", "ngs-report")
    (dr,) = [r for r in resources(bundle, "DiagnosticReport", P_NGS) if r["id"] == rid]
    return dr


def consequence_of(bundle, var):
    url = full_url(bundle, var)
    return [r for r in resources(bundle, "Observation", P_CONS)
            if any(d["reference"] == url for d in r.get("derivedFrom", []))]


@pytest.fixture(scope="module")
def fixture_2027():
    from genomde2fhir import convert
    bundle, rep = convert(load(FIXTURE), str(FIXTURE), "2027")
    assert rep.status == "converted", rep.error or rep.input_findings
    return bundle, rep


# ---- corpus -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("rel", CORPUS)
def test_corpus_small_variants(rel, convert_dk):
    path = REPO / rel
    if not path.exists():
        pytest.skip(f"missing {rel}")
    dk = load(path)
    bundle, rep = convert_dk(dk, rel)
    svs = dk["molecular"]["smallVariants"]
    assert len(resources(bundle, "Observation", P_VAR)) >= len(svs)
    for sv in svs:
        (var,) = variant_by_id(bundle, sv["identifier"])
        assert var["status"] == "final"
        assert var["code"]["coding"][0]["code"] == "69548-6"
        assert var["valueCodeableConcept"]["coding"][0]["code"] == "LA9633-4"
        assert {c["coding"][0]["code"] for c in var["category"]} == {"laboratory", "GE"}
        g = one(var, "48018-6")["valueCodeableConcept"]["coding"][0]
        assert (g["system"], g["code"], g.get("display")) == (HGNC, sv["gene"]["code"], sv["gene"].get("display"))
        rng = one(var, "81254-5")["valueRange"]
        assert rng["low"]["value"] == sv["startPosition"]
        if sv["endPosition"] >= sv["startPosition"]:
            assert rng["high"]["value"] == sv["endPosition"]
        else:
            assert "high" not in rng
        assert one(var, "62374-4")["valueCodeableConcept"]["coding"][0]["code"] == "LA26806-2"
        assert one(var, "69547-8")["valueString"] == sv["ref"]
        assert one(var, "69551-0")["valueString"] == sv["alt"]
        gs = one(var, "48002-0")["valueCodeableConcept"]["coding"][0]["code"]
        assert gs == {"somatic": "LA6684-0", "germline": "LA6683-2"}[sv["genomicSource"]]
        chrom = one(var, "48000-4")["valueCodeableConcept"]["coding"][0]
        assert chrom["display"] == f"Chromosome {sv['chromosome']}"
        tr = one(var, "51958-7")["valueCodeableConcept"]["coding"][0]
        assert tr["code"] == sv["transcriptId"]["code"]
        assert tr["system"] in (REFSEQ, ENSEMBL)
        dna = one(var, "48004-6")["valueCodeableConcept"]
        assert dna["coding"][0]["system"] == HGVS
        if sv["transcriptId"]["code"].startswith("NM_"):          # qualified with the RefSeq accession
            assert dna["coding"][0]["code"] == f"{sv['transcriptId']['code']}:{sv['dnaChange']}"
            assert dna["text"] == sv["dnaChange"]
            prot = one(var, "48005-3")["valueCodeableConcept"]
            assert prot["coding"][0]["code"] == \
                f"{sv['transcriptId']['code']}({sv['gene']['display']}):{sv['proteinChange']}"
        loh = [c for c in var["component"] if c["code"]["coding"][0]["code"] == "loh"]
        assert [c["valueBoolean"] for c in loh] == ([sv["loh"]] if "loh" in sv else [])
        (cons,) = consequence_of(bundle, var)
        fc = cons["component"][0]
        assert fc["code"]["coding"][0]["code"] == "feature-consequence"
        assert fc["valueCodeableConcept"]["coding"][0] == {**fc["valueCodeableConcept"]["coding"][0], "system": SO,
                                                            "code": LOC_SO[sv["localization"]]}
        assert fc["valueCodeableConcept"]["text"] == sv["localization"]
    # one NGS report with every variant and its consequence as result (prior findings have their own reports)
    dr = ngs_report(bundle, dk)
    assert dr["code"]["coding"][0]["code"] == "51969-4"
    # linked from the Behandlungsepisode via investigation:NgsBericht (SNOMED 106221001)
    (ep,) = resources(bundle, "ClinicalImpression", "mii-pr-mtb-behandlungsepisode")
    ngs_inv = [i for i in ep.get("investigation", []) if i["code"]["coding"][0]["code"] == "106221001"]
    assert [i["item"] for i in ngs_inv] == [[{"reference": full_url(bundle, dr)}]]
    results = {r["reference"] for r in dr["result"]}
    for sv in svs:
        (var,) = variant_by_id(bundle, sv["identifier"])
        assert {full_url(bundle, var), full_url(bundle, consequence_of(bundle, var)[0])} <= results
    assert {PREFIX + ".dnaChange", PREFIX + ".localization", PREFIX + ".gene.code"} <= rep.covered


@pytest.mark.parametrize("rel", CORPUS[:2])
def test_corpus_profile_set_2026(rel, convert_dk):
    dk = load(REPO / rel)
    bundle, _ = convert_dk(dk, rel, profile_set="2026")
    assert len(resources(bundle, "Observation", P_VAR)) >= len(dk["molecular"]["smallVariants"])
    assert resources(bundle, "DiagnosticReport", P_NGS)


# ---- synthetic fixture: enum values and edge cases -----------------------------------------------------------------
def test_fixture_enums_and_edges(fixture_2027):
    bundle, rep = fixture_2027
    vs = {sid: variant_by_id(bundle, sid) for sid in ("sv-1", "sv-2", "sv-3")}
    assert len(vs["sv-3"]) == 2                     # duplicate KDK identifier -> two resources, unique ids
    assert any("duplicate identifier 'sv-3'" in m for _, m in rep.warnings)
    v1, v2 = vs["sv-1"][0], vs["sv-2"][0]
    v3 = next(v for v in vs["sv-3"] if one(v, "48018-6")["valueCodeableConcept"]["coding"][0]["code"] == "HGNC:11998")
    v4 = next(v for v in vs["sv-3"] if v is not v3)

    # gene: version kept, missing system -> HGNC lock
    g1 = one(v1, "48018-6")["valueCodeableConcept"]["coding"][0]
    assert g1 == {"system": HGNC, "code": "HGNC:7989", "display": "NRAS", "version": "2025-06"}
    assert one(v2, "48018-6")["valueCodeableConcept"]["coding"][0]["system"] == HGNC

    # transcript: RefSeq w/o version in code + separate version; Ensembl by prefix ('Ensembl' string system);
    # unknown local system passed through; HGVS qualified accordingly
    t1 = one(v1, "51958-7")["valueCodeableConcept"]["coding"][0]
    assert t1 == {"system": REFSEQ, "code": "NM_002524", "version": "5", "display": "NRAS transcript"}
    assert one(v1, "48004-6")["valueCodeableConcept"]["coding"][0]["code"] == "NM_002524.5:c.181C>A"
    assert one(v1, "48005-3")["valueCodeableConcept"]["coding"][0]["code"] == "NM_002524.5(NRAS):p.Gln61Lys"
    assert one(v2, "51958-7")["valueCodeableConcept"]["coding"][0]["system"] == ENSEMBL
    assert one(v2, "48004-6")["valueCodeableConcept"]["coding"][0]["code"] == "ENST00000357654.9:c.68_72del"
    assert not comp(v2, "48005-3")
    assert one(v3, "51958-7")["valueCodeableConcept"]["coding"][0]["system"] == "https://example.org/local-transcripts"
    dna3 = one(v3, "48004-6")["valueCodeableConcept"]
    assert dna3 == {"coding": [{"system": HGVS, "code": "c.215C>G"}]}       # no accession: as given
    assert rep.representations["hgvs-unqualified"] >= 2
    # already qualified source expression kept; protein qualified with the RefSeq transcript
    assert one(v4, "48004-6")["valueCodeableConcept"]["coding"][0]["code"] == "NM_005228.5:c.2573T>G"
    assert one(v4, "48005-3")["valueCodeableConcept"]["coding"][0]["code"] == "NM_005228.5(EGFR):p.Leu858Arg"

    # chromosome: X / Y coded, MT dropped (no LL2938-0 answer)
    assert one(v2, "48000-4")["valueCodeableConcept"]["coding"][0]["code"] == "LA21276-3"
    assert one(v4, "48000-4")["valueCodeableConcept"]["coding"][0]["code"] == "LA21277-1"
    assert not comp(v3, "48000-4")
    drops = {(p, str(v)) for p, v, _ in rep.dropped}
    assert (PREFIX + ".chromosome", "MT") in drops
    # start > end: Range.high omitted and dropped (rng-2)
    assert one(v3, "81254-5")["valueRange"] == {"low": {"value": 500}}
    assert (PREFIX + ".endPosition", "400") in drops
    assert one(v1, "92822-6")["valueCodeableConcept"]["coding"][0]["code"] == "LA30102-0"

    # genomic source both values
    assert one(v1, "48002-0")["valueCodeableConcept"]["coding"][0]["code"] == "LA6684-0"
    assert one(v2, "48002-0")["valueCodeableConcept"]["coding"][0]["code"] == "LA6683-2"

    # variant types: one coding-change-type with all SO codings, system normalised, version kept
    assert [c["code"] for c in one(v1, "48019-4")["valueCodeableConcept"]["coding"]] == ["SO:0001483"]
    cct = one(v2, "48019-4")["valueCodeableConcept"]["coding"]
    assert [(c["system"], c["code"], c["version"]) for c in cct] == [
        (SO, "SO:0000159", "2024-11-18"), (SO, "SO:0001589", "2024-11-18")]
    assert not comp(v3, "48019-4")

    # LOH true / false / absent (local code, preserved)
    def loh(v):
        return [c["valueBoolean"] for c in v["component"]
                if c["code"]["coding"][0] == {**c["code"]["coding"][0], "code": "loh",
                                              "system": "https://genomde.de/fhir/CodeSystem/mvgs-cs-molecular-feature"}]
    assert (loh(v1), loh(v2), loh(v3)) == ([True], [False], [])
    assert PREFIX + ".loh" in rep.preserved

    # localization: all three enum values; the lossy one keeps the source value as text
    for v, loc in ((v1, "coding"), (v2, "inRegulatoryElements"), (v3, "notInCodingAndNotInRegulatoryElements")):
        (cons,) = consequence_of(bundle, v)
        assert cons["code"]["coding"][0]["code"] == "molecular-consequence"
        assert cons["subject"] == v["subject"]
        val = cons["component"][0]["valueCodeableConcept"]
        assert (val["coding"][0]["code"], val["text"]) == (LOC_SO[loc], loc)
    assert rep.representations["localization-so-wider"] == 1


def test_fixture_report(fixture_2027):
    bundle, _ = fixture_2027
    dr = ngs_report(bundle, load(FIXTURE))
    assert dr["status"] == "final"
    assert dr["category"][0]["coding"][0]["code"] == "GE"
    assert "issued" not in dr and "effectiveDateTime" not in dr     # no source date: nothing invented
    refs = [r["reference"] for r in dr["result"]]
    assert len(refs) == len(set(refs))
    for sid in ("sv-1", "sv-2", "sv-3"):
        for var in variant_by_id(bundle, sid):
            assert {full_url(bundle, var), full_url(bundle, consequence_of(bundle, var)[0])} <= set(refs)


def test_qualify_hgvs_reference_types():
    q = molecular_variants.qualify_hgvs
    assert q("c.181C>A", "NM_002524.5") == "NM_002524.5:c.181C>A"
    assert q("c.181C>A", "NR_024540.1") == "c.181C>A"                 # c. on a non-coding RefSeq: kept as given
    assert q("n.100A>G", "NR_024540.1") == "NR_024540.1:n.100A>G"
    assert q("p.Gln61Lys", "NR_024540.1", "NRAS") == "p.Gln61Lys"
    assert q("p.Gln61Lys", "NM_002524.5") == "p.Gln61Lys"              # no gene symbol: no protein qualification
    assert q("p.Gln61Lys", "ENST00000369535.5", "NRAS") == "p.Gln61Lys"  # no Ensembl protein accession in the KDK
    assert q("NM_002524.5:c.181C>A", "NM_002524.5") == "NM_002524.5:c.181C>A"
    assert molecular_variants.transcript_accession({"code": "NM_002524", "version": "5"}) == "NM_002524.5"
    assert molecular_variants.transcript_accession({"code": "3f2c9e0a-uuid"}) is None


# ---- builder contract: ids / bag / refs ---------------------------------------------------------------------------
def make_ctx(dk, ps="2027"):
    ctx = Ctx(dk, "oncology", case_key(dk, "oncology"), ps)
    patient.build(ctx)
    return ctx


def test_registrations_and_genomic_study_link():
    dk = load(FIXTURE)
    ctx = make_ctx(dk)
    molecular_variants.build(ctx)
    assert set(k for k in ctx.ids if k[0] == "variant") == {("variant", "sv-1"), ("variant", "sv-2"), ("variant", "sv-3")}
    assert len(ctx.bag["ngs_results"]) == 8           # 4 variants + 4 consequences
    ctx.refs["genomic_study"] = {"reference": "urn:uuid:00000000-0000-0000-0000-000000000001"}
    molecular_report.build(ctx)
    rep = ctx.refs["ngs_report"]
    dr = ctx.bundle.entries[rep["reference"]]["resource"]
    assert dr["extension"] == [{"url": molecular_report.EX_GENOMIC_STUDY, "valueReference": ctx.refs["genomic_study"]}]
    assert dr["result"] == ctx.bag["ngs_results"]


def test_no_report_without_results():
    dk = load(FIXTURE)
    dk = {**dk, "molecular": {}}
    ctx = make_ctx(dk)
    molecular_variants.build(ctx)
    molecular_report.build(ctx)
    assert "ngs_report" not in ctx.refs


# ---- coverage of the block -----------------------------------------------------------------------------------------
KNOWN_UNCOVERABLE: dict[str, str] = {}


def test_block_coverage(fixture_2027, convert_dk):
    covered, preserved = set(fixture_2027[1].covered), set(fixture_2027[1].preserved)
    for rel in CORPUS:
        if (REPO / rel).exists():
            _, rep = convert_dk(load(REPO / rel), rel)
            covered |= rep.covered
            preserved |= rep.preserved
    mapped = set(block_rows("MAPPED"))
    assert mapped, "no MAPPED smallVariants rows found"
    # loh is MAPPED in the table but lands in a local (unsliced) component -> preserved (REPRESENTATIONS #19)
    missing = mapped - covered - preserved - set(KNOWN_UNCOVERABLE)
    assert not missing, f"MAPPED rows not covered: {sorted(missing)}"
    # DRAFT rows made mappable by REPRESENTATIONS #19 / #26
    assert PREFIX + ".localization" in covered
    assert PREFIX + ".loh" in preserved
    assert set(block_rows("DRAFT")) <= covered | preserved
