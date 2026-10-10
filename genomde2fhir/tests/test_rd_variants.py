"""rd.variants + rd.report: KDK rare-disease molecular block -> MolGen variante / diagnostische-implikation /
molekulare-konsequenz + molekulargenetischer-befundbericht."""
import csv
from pathlib import Path

import pytest
from conftest import REPO, corpus, load, resources

from genomde2fhir.builders import patient
from genomde2fhir.builders.rd import report, variants
from genomde2fhir.context import Ctx
from genomde2fhir.identity import case_key

FIXTURE = Path(__file__).parent / "fixtures" / "rd_variants" / "rd-variants-edge-cases.json"
VARIANTE = "modul-molgen/StructureDefinition/variante"
IMPL = "modul-molgen/StructureDefinition/diagnostische-implikation"
KONS = "mii-pr-molgen-molekulare-konsequenz"
REPORT = "molekulargenetischer-befundbericht"
LOINC = "http://loinc.org"
KINDS = ("smallVariants", "copyNumberVariants", "structuralVariants")


def corpus_files(n=3):
    """n corpus files with distinct content (the corpus mirrors the same file in several directories)."""
    out, seen = [], set()
    for f in corpus("rare-disease"):
        dk = load(f)
        if f.name in seen or not any((dk.get("molecular") or {}).get(k) for k in KINDS):
            continue
        seen.add(f.name)
        out.append(f)
        if len(out) == n:
            break
    return out


def run_ctx(dk, profile_set="2027"):
    """Patient + rd.variants + rd.report only (strict: unknown mapping paths / canonicals raise)."""
    ctx = Ctx(dk, "rare-disease", case_key(dk, "rare-disease"), profile_set, strict=True)
    patient.build(ctx)
    variants.build(ctx)
    report.build(ctx)
    return ctx


def comp(obs, system, code):
    return [c for c in obs.get("component", []) if any(
        x.get("system") == system and x.get("code") == code for x in c["code"]["coding"])]


def value_code(c):
    return c["valueCodeableConcept"]["coding"][0]["code"]


def by_identifier(bundle, vid):
    for o in resources(bundle, "Observation", VARIANTE):
        if any(i.get("value", "").endswith("|" + vid) for i in o.get("identifier", [])):
            yield o


def derived(bundle, vref, profile):
    return [o for o in resources(bundle, "Observation", profile) if vref in [d["reference"] for d in o["derivedFrom"]]]


@pytest.fixture(scope="module")
def fixture_run():
    from genomde2fhir import convert
    dk = load(FIXTURE)
    bundle, rep = convert(dk, str(FIXTURE))
    assert rep.status == "converted", rep.error or rep.input_findings
    return dk, bundle, rep


# ---- (a) corpus ---------------------------------------------------------------------------------
@pytest.mark.parametrize("path", corpus_files(), ids=lambda p: p.name[:40])
def test_corpus_variants(path, convert_dk):
    dk = load(path)
    mol = dk["molecular"]
    bundle, rep = convert_dk(dk, path.name)
    var = resources(bundle, "Observation", VARIANTE)
    n = sum(len(mol.get(k) or []) for k in KINDS)
    assert len(var) == n
    urls = {e["resource"]["id"]: e["fullUrl"] for e in bundle["entry"]}
    for o in var:
        assert o["status"] == "final" and o["code"]["coding"][0]["code"] == "69548-6"
        assert {c["coding"][0]["code"] for c in o["category"]} == {"laboratory", "GE"}
        assert value_code({"valueCodeableConcept": o["valueCodeableConcept"]}) == "LA9633-4"
        for g in comp(o, LOINC, "48018-6"):
            assert g["valueCodeableConcept"]["coding"][0]["system"] == "http://www.genenames.org"
        assert len(comp(o, LOINC, "81254-5")) <= 1
    # every small variant has ref/alt and a chromosome (LL2938-0 or MT refseq)
    for sv in mol.get("smallVariants") or []:
        (o,) = by_identifier(bundle, sv["identifier"])
        assert comp(o, LOINC, "69547-8")[0]["valueString"] == sv["ref"]
        assert comp(o, LOINC, "69551-0")[0]["valueString"] == sv["alt"]
        assert comp(o, LOINC, "48000-4") or comp(o, LOINC, "48013-7")
        if sv.get("acmgClass"):
            (imp,) = derived(bundle, urls[o["id"]], IMPL)
            assert comp(imp, LOINC, "53037-8")
    # CNV type -> coding-change-type
    for cnv in mol.get("copyNumberVariants") or []:
        (o,) = by_identifier(bundle, cnv["identifier"])
        so = value_code(comp(o, LOINC, "48019-4")[0])
        assert so == {"gain": "SO:0001742", "loss": "SO:0001743"}[cnv["type"]]
    # one report with all variant, implication and consequence Observations
    reps = [r for r in resources(bundle, "DiagnosticReport", REPORT)
            if r["id"] == run_ctx(dk).id("DiagnosticReport", "rd-molecular-report")]
    assert len(reps) == 1
    results = {r["reference"] for r in reps[0]["result"]}
    mine = var + resources(bundle, "Observation", IMPL) + resources(bundle, "Observation", KONS)
    assert results == {urls[o["id"]] for o in mine}
    assert not [w for w in rep.warnings if w[0] in ("(structure)", "(reference)")]


def test_refs_ids_bag():
    path = corpus_files(1)[0]
    dk = load(path)
    ctx = run_ctx(dk)
    for k in KINDS:
        for v in dk["molecular"].get(k) or []:
            assert ("variant", v["identifier"]) in ctx.ids
            assert ctx.ids[("variant", v["identifier"])] in ctx.bag["rd_report_results"]
    assert "rd_report" in ctx.refs


def test_duplicate_identifier_links_first():
    ctx = run_ctx(load(FIXTURE))
    first = ctx.id("Observation", "rd-variant", "small", "SNV-6")
    assert ctx.ids[("variant", "SNV-6")]["reference"].endswith(first)
    assert ctx.id("Observation", "rd-variant", "small", "SNV-6") == run_ctx(load(FIXTURE)).id(
        "Observation", "rd-variant", "small", "SNV-6")   # deterministic ids


def test_hgvs_slots_carry_only_validatable_expressions():
    """Coded HGVS slots never carry constructs the hgvs-vs terminology service rejects or times out on."""
    n = 0
    for path in corpus_files(10) + [FIXTURE]:
        for o in resources(run_ctx(load(path)).bundle.bundle(), "Observation", VARIANTE):
            for c in o.get("component", []):
                for x in (c.get("valueCodeableConcept") or {}).get("coding", []):
                    if x.get("system") == "http://varnomen.hgvs.org":
                        assert not variants.HGVS_UNVALIDATABLE.search(x["code"]), x["code"]
                        n += 1
    assert n


def test_profile_set_2026(convert_dk):
    for path in corpus_files(2):
        bundle, _ = convert_dk(load(path), path.name, profile_set="2026")
        assert resources(bundle, "Observation", VARIANTE)
        run_ctx(load(path), "2026")


# ---- (b) synthetic fixture: enum values and edge cases --------------------------------------------
def test_fixture_zygosity_segregation(fixture_run):
    _, bundle, rep = fixture_run
    # compHet: LL381-5 has no compound-heterozygous answer -> Heterozygous + LA26217-2 as second coding
    zyg = {"SNV-1": ["LA6706-1"], "SNV-2": ["LA6703-8"], "SNV-3": ["LA6707-9"], "SNV-4": ["LA6705-3"],
           "SNV-5": ["LA6706-1", "LA26217-2"]}
    for vid, codes in zyg.items():
        (o,) = by_identifier(bundle, vid)
        assert [c["code"] for c in comp(o, LOINC, "53034-5")[0]["valueCodeableConcept"]["coding"]] == codes
    seg = {"SNV-1": "LA26807-0", "SNV-2": "LA26320-4", "SNV-3": "LA26321-2"}
    for vid, code in seg.items():
        (o,) = by_identifier(bundle, vid)
        assert value_code(comp(o, LOINC, "94186-4")[0]) == code
    (o,) = by_identifier(bundle, "SNV-4")   # fromMotherAndFather -> local biparental
    c = comp(o, LOINC, "94186-4")[0]["valueCodeableConcept"]["coding"][0]
    assert c["system"].endswith("mvgs-cs-segregation") and c["code"] == "biparental"
    (o,) = by_identifier(bundle, "SNV-5")   # notPerformed -> omitted + dropped
    assert not comp(o, LOINC, "94186-4")
    assert ("molecular.smallVariants[].segregationAnalysis", "notPerformed") in [(p, v) for p, v, _ in rep.dropped]


def test_fixture_chromosome_positions_hgvs(fixture_run):
    _, bundle, rep = fixture_run
    (o,) = by_identifier(bundle, "SNV-1")
    assert value_code(comp(o, LOINC, "48000-4")[0]) == "LA21270-6"     # chromosome 17
    assert comp(o, LOINC, "81254-5")[0]["valueRange"] == {"low": {"value": 7673802}, "high": {"value": 7673802}}
    assert value_code(comp(o, LOINC, "48004-6")[0]) == "NM_000546.6:c.818G>A"
    assert value_code(comp(o, LOINC, "81290-9")[0]) == "NC_000017.11:g.7673802C>T"
    assert value_code(comp(o, LOINC, "48005-3")[0]) == "NP_000537.3:p.Arg273His"
    assert {i.get("system") for i in o["identifier"]} >= {"http://www.ncbi.nlm.nih.gov/clinvar"}
    assert value_code(comp(o, LOINC, "81252-9")[0]) == "17677"
    (o,) = by_identifier(bundle, "SNV-2")   # MT -> genomic-ref-seq; m. in cdnaChange and malformed p. -> note
    assert not comp(o, LOINC, "48000-4")
    assert value_code(comp(o, LOINC, "48013-7")[0]) == "NC_012920.1"
    assert value_code(comp(o, LOINC, "81290-9")[0]) == "NC_012920.1:m.3243A>G"
    assert not comp(o, LOINC, "48004-6") and not comp(o, LOINC, "48005-3")
    notes = {n["text"] for n in o["note"]}
    assert notes == {"cdnaChange: NC_012920.1:m.3243A>G", "proteinChange: p.Trp24Ter (p.Trp24*)"}
    (o,) = by_identifier(bundle, "CNV-2")   # start > end -> no Range
    assert not comp(o, LOINC, "81254-5")
    assert value_code(comp(o, LOINC, "48019-4")[0]) == "SO:0001743"
    (o,) = by_identifier(bundle, "CNV-1")
    assert [value_code(c) for c in comp(o, LOINC, "48018-6")] == ["HGNC:3236", "HGNC:7029"]
    assert value_code(comp(o, LOINC, "48019-4")[0]) == "SO:0001742"
    (o,) = by_identifier(bundle, "SNV-3")   # well-formed HGVS the hgvs-vs service cannot validate -> note
    assert not comp(o, LOINC, "81290-9") and not comp(o, LOINC, "48005-3")
    assert {n["text"] for n in o["note"]} == {"gdnaChange: NC_000023.11:g.33344590_33344592=/dup",
                                             "proteinChange: NP_003997.1:p.(Gly56Ala^Ser^Cys)"}
    (o,) = by_identifier(bundle, "CNV-2")
    assert {n["text"] for n in o["note"]} == {"cdnaChange: NC_000022.11:g.1000_2000del",
                                             "gdnaChange: NC_000023.11:g.(31060227_31100351)_(33274278_33417151)dup"}
    assert rep.representations["hgvs-not-validatable-note"] == 3
    dup = list(by_identifier(bundle, "SNV-6"))  # duplicate identifier -> both kept
    assert len(dup) == 2 and len({o["id"] for o in dup}) == 2
    (o,) = by_identifier(bundle, "SV-1")
    assert comp(o, LOINC, "81291-7")[0]["valueCodeableConcept"] == {"text": "46,XX,t(1;3)(p31;q21)"}
    assert [i for i in o["identifier"] if i.get("use") == "secondary"][0] == {
        "use": "secondary", "value": "abc-not-clinvar", "type": {"text": "external variant id"}}


def test_fixture_implication(fixture_run):
    _, bundle, rep = fixture_run
    urls = {e["resource"]["id"]: e["fullUrl"] for e in bundle["entry"]}
    tbd = "http://hl7.org/fhir/uv/genomics-reporting/CodeSystem/tbd-codes-cs"
    acmg = {"SNV-1": "LA6668-3", "SNV-2": "LA26332-9", "SNV-3": "LA26333-7", "SNV-4": "LA26334-5",
            "SNV-5": "LA6675-8"}
    moi = {"SNV-1": "HP:0000006", "SNV-2": "HP:0001427", "SNV-3": "HP:0001417", "SNV-4": "HP:0000007"}
    cat = {"SNV-1": "primary", "SNV-2": "incidental", "SNV-3": "candidate"}
    for vid, code in acmg.items():
        (o,) = by_identifier(bundle, vid)
        (imp,) = derived(bundle, urls[o["id"]], IMPL)
        assert value_code(comp(imp, LOINC, "53037-8")[0]) == code
        m = comp(imp, tbd, "condition-inheritance")[0]["valueCodeableConcept"]
        assert (m["coding"][0]["code"] if vid in moi else m) == moi.get(vid, {"text": "unclear"})
        fc = [c for c in imp["component"] if c["code"]["coding"][0]["code"] == "finding-category"]
        assert [value_code(c) for c in fc] == ([cat[vid]] if vid in cat else [])
    (o,) = by_identifier(bundle, "SNV-1")
    (imp,) = derived(bundle, urls[o["id"]], IMPL)
    crit = {c["code"]["coding"][0]["code"]: c.get("valueCodeableConcept") for c in imp["component"]
            if c["code"]["coding"][0]["system"] == "https://clinicalgenome.org/codesystem/acmg-criteria"}
    assert set(crit) == {"PVS1", "PM2"} and crit["PM2"] is None
    assert crit["PVS1"]["coding"][0]["code"] == "pvs"
    ras = [e["valueRelatedArtifact"] for e in imp["extension"]]
    assert [r["citation"] for r in ras] == ["PMID:20301425", "PMID:12345678"]
    assert ras[0]["url"] == "https://pubmed.ncbi.nlm.nih.gov/20301425/" and ras[0]["type"] == "citation"
    (o,) = by_identifier(bundle, "CNV-1")   # DNPM 'bm' strength
    (imp,) = derived(bundle, urls[o["id"]], IMPL)
    assert {value_code(c) for c in imp["component"] if c["code"]["coding"][0]["code"] == "BP4"} == {"bm"}
    (o,) = by_identifier(bundle, "SNV-2")
    (imp,) = derived(bundle, urls[o["id"]], IMPL)
    assert [e["valueRelatedArtifact"] for e in imp["extension"]] == [{"type": "citation", "citation": "doi:10.1000/xyz"}]
    for vid in ("SNV-6", "SV-2"):          # nothing to imply / no localization -> no extra resources
        for o in by_identifier(bundle, vid):
            assert not derived(bundle, urls[o["id"]], IMPL) and not derived(bundle, urls[o["id"]], KONS)


def test_fixture_localization(fixture_run):
    _, bundle, _ = fixture_run
    urls = {e["resource"]["id"]: e["fullUrl"] for e in bundle["entry"]}
    want = {"SNV-1": ["SO:0001580", "SO:0001630"], "SNV-2": ["SO:0001566"], "SNV-3": ["SO:0001627"],
            "SNV-4": ["SO:0001628"], "SV-1": ["SO:0001627"]}
    for vid, codes in want.items():
        (o,) = by_identifier(bundle, vid)
        (k,) = derived(bundle, urls[o["id"]], KONS)
        assert [value_code(c) for c in k["component"]] == codes
        assert all(c["valueCodeableConcept"]["coding"][0]["system"] == "http://www.sequenceontology.org"
                   for c in k["component"])
        assert "valueCodeableConcept" not in k


# ---- (c) coverage --------------------------------------------------------------------------------
def test_block_coverage(fixture_run):
    rows = []
    with (REPO / "mapping" / "mapping_kdk_rarediseases.csv").open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["path"].startswith(tuple(f"molecular.{k}[]." for k in KINDS))]
    assert rows
    seen = set()
    for path in corpus_files() + [FIXTURE]:
        ctx = run_ctx(load(path))
        seen |= ctx.report.covered | ctx.report.preserved
    _, _, rep = fixture_run
    seen |= rep.covered | rep.preserved
    known_uncoverable = {}   # every row of the block is reachable with the corpus + fixture
    missing = [r["path"] for r in rows if r["path"] not in seen and r["path"] not in known_uncoverable]
    assert not missing, missing
    mapped = [r["path"] for r in rows if r["status"] == "MAPPED"]
    assert set(mapped) <= seen
