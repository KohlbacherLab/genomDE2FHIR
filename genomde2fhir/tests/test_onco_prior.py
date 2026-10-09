"""Oncology prior systemic therapies (case.priorProcedures[]) and prior genetic findings (case.priorDiagnostics[])."""
from pathlib import Path

import pytest
from conftest import first_with, load, resources

from genomde2fhir.data_access import mapping_rows

FIXTURE = Path(__file__).parent / "fixtures" / "onco_prior" / "prior_all_enums.json"

MTB = "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/"
ONKO = "https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/"
GR = "http://hl7.org/fhir/uv/genomics-reporting/"
P_VORTHERAPIE = MTB + "StructureDefinition/mii-pr-mtb-systemische-vortherapie"
P_MEDSTMT = MTB + "StructureDefinition/mii-pr-mtb-systemtherapie-medication-statement"
P_EPISODE = MTB + "StructureDefinition/mii-pr-mtb-behandlungsepisode"
P_REPORT = MTB + "StructureDefinition/mii-pr-mtb-ngs-bericht"
P_VARIANT = MTB + "StructureDefinition/mii-pr-mtb-einfache-variante"
P_STUDY = MTB + "StructureDefinition/mii-pr-mtb-genomic-study"
P_ANALYSIS = MTB + "StructureDefinition/mii-pr-mtb-genomic-study-analysis"
P_RESPONSE = "https://genomde.de/fhir/StructureDefinition/mvgs-therapy-response"
EXT_INTENTION = ONKO + "StructureDefinition/mii-ex-onko-systemische-therapie-intention"
EXT_STELLUNG = ONKO + "StructureDefinition/mii-ex-onko-systemische-therapie-stellungzurop"
EXT_METHOD = GR + "StructureDefinition/genomic-study-analysis-method-type"
EXT_STUDY = MTB + "StructureDefinition/mii-ex-mtb-ngs-bericht-genomic-study"
ATC = "http://fhir.de/CodeSystem/bfarm/atc"

BLOCK = ("case.priorProcedures[].", "case.priorDiagnostics[].")
# REPRESENTATIONS #14: prior therapy response goes to the local profile mvgs-therapy-response -> preserved, not covered
LOCAL = {"case.priorProcedures[].therapyResponse", "case.priorProcedures[].therapyResponseDate"}


def by_profile(bundle, profile):
    return [r for r in resources(bundle) if profile in r.get("meta", {}).get("profile", [])]


def ext(r, url):
    return [e for e in r.get("extension", []) if e["url"] == url]


def comp(obs, loinc):
    return [c for c in obs.get("component", []) if c["code"]["coding"][0]["code"] == loinc]


def index(bundle):
    return {e["fullUrl"]: e["resource"] for e in bundle["entry"]}


# ---- corpus --------------------------------------------------------------------------------------------------------
def test_corpus_prior_procedures(convert_dk):
    f, dk = first_with("oncology", lambda d: any(p.get("terminationReasonOBDS") and p.get("substances")
                                                for p in (d.get("case") or {}).get("priorProcedures") or []))
    bundle, rep = convert_dk(dk, str(f))
    pps = dk["case"]["priorProcedures"]
    procs = by_profile(bundle, P_VORTHERAPIE)
    assert len(procs) == len(pps)
    for p in procs:
        assert p["performedPeriod"]["start"]
        assert len(ext(p, EXT_INTENTION)) == 1
        assert p["code"]["coding"][0]["system"] == "http://snomed.info/sct"
    with_reason = [p for p in procs if "statusReason" in p]
    assert with_reason and all(p["statusReason"]["coding"][0]["system"] == MTB + "CodeSystem/mii-cs-mtb-therapiestatusgrund"
                               for p in with_reason)
    proc_refs = {"urn:uuid:" + p["id"] for p in procs}
    meds = [m for m in by_profile(bundle, P_MEDSTMT) if m["partOf"][0]["reference"] in proc_refs]
    assert len(meds) == sum(len(p.get("substances") or []) for p in pps)
    assert all(c["system"] in (ATC, "http://www.whocc.no/atc") for m in meds for c in m["medicationCodeableConcept"]["coding"])
    ep = by_profile(bundle, P_EPISODE)
    assert len(ep) == 1 and proc_refs <= {s["reference"] for s in ep[0]["supportingInfo"]}
    assert "case.priorProcedures[].treatmentType" in rep.covered


def test_corpus_prior_response(convert_dk):
    f, dk = first_with("oncology", lambda d: any(p.get("therapyResponse")
                                                for p in (d.get("case") or {}).get("priorProcedures") or []))
    bundle, rep = convert_dk(dk, str(f))
    procs = {"urn:uuid:" + p["id"] for p in by_profile(bundle, P_VORTHERAPIE)}
    obs = [o for o in by_profile(bundle, P_RESPONSE) if o["partOf"][0]["reference"] in procs]
    want = [p["therapyResponse"] for p in dk["case"]["priorProcedures"] if p.get("therapyResponse")]
    assert sorted(o["valueCodeableConcept"]["coding"][0]["code"] for o in obs) == sorted(want)
    assert "case.priorProcedures[].therapyResponse" in rep.preserved


def test_corpus_prior_variants(convert_dk):
    f, dk = first_with("oncology", lambda d: any(pd.get("simpleVariants")
                                                for pd in (d.get("case") or {}).get("priorDiagnostics") or []))
    bundle, rep = convert_dk(dk, str(f))
    reports = by_profile(bundle, P_REPORT)
    prior = [r for r in reports if ext(r, EXT_STUDY) or r.get("conclusion")]
    assert prior
    variants = by_profile(bundle, P_VARIANT)
    res = index(bundle)
    prior_variants = [res[x["reference"]] for r in prior for x in r.get("result", [])]
    assert prior_variants and all(v in variants for v in prior_variants)
    v = prior_variants[0]
    assert v["valueCodeableConcept"]["coding"][0]["code"] == "LA9633-4"
    gene = comp(v, "48018-6")[0]["valueCodeableConcept"]["coding"][0]
    assert gene["system"] == "http://www.genenames.org" and gene["code"].startswith("HGNC:")
    assert comp(v, "48004-6")
    ep = by_profile(bundle, P_EPISODE)[0]
    assert {"urn:uuid:" + r["id"] for r in prior} <= {s["reference"] for s in ep["supportingInfo"]}
    assert "case.priorDiagnostics[].simpleVariants[].dnaChange" in rep.covered


def test_corpus_legacy_prior_diagnostic(convert_dk):
    f, dk = first_with("oncology", lambda d: isinstance((d.get("case") or {}).get("priorDiagnostic"), dict)
                       and (d["case"]["priorDiagnostic"].get("type") not in (None, "none")))
    bundle, rep = convert_dk(dk, str(f))
    assert any(p == "case.priorDiagnostic" for p, _ in rep.warnings)
    studies = by_profile(bundle, P_STUDY)
    assert any(s["code"]["coding"][0]["code"] == dk["case"]["priorDiagnostic"]["type"] for s in studies)


# ---- synthetic fixture: every enum value and edge case ------------------------------------------------------------
@pytest.fixture(scope="module")
def fixture_out():
    from genomde2fhir import convert
    dk = load(FIXTURE)
    bundle, rep = convert(dk, str(FIXTURE), "2027", strict=True)
    assert rep.status == "converted"
    return dk, bundle, rep


def test_fixture_procedures(fixture_out):
    dk, bundle, rep = fixture_out
    procs = sorted(by_profile(bundle, P_VORTHERAPIE), key=lambda p: p["performedPeriod"]["start"])
    assert len(procs) == 10
    stell = {ext(p, EXT_STELLUNG)[0]["valueCodeableConcept"]["coding"][0]["code"] for p in procs}
    assert stell == {"O", "A", "N", "I", "S"}
    intent = [ext(p, EXT_INTENTION)[0]["valueCodeableConcept"]["coding"][0]["code"] for p in procs]
    assert set(intent) == {"K", "P", "S", "X"} and intent.count("X") == 4   # 2x source X + 2x missing -> X
    outcomes = {p["outcome"]["coding"][0]["code"]: p for p in procs if "outcome" in p}
    assert set(outcomes) == {"E", "R", "W", "A", "P", "S", "V", "T", "U"}
    sg = {k: p["statusReason"]["coding"][0]["code"] for k, p in outcomes.items()}
    assert sg == {"E": "regular-completion", "R": "regular-completion-with-dosage-reduction",
                  "W": "regular-completion-with-substance-change", "A": "toxicity", "P": "progression", "S": "other",
                  "V": "patient-refusal", "T": "patient-death", "U": "unknown"}
    assert {k for k, p in outcomes.items() if p["status"] == "stopped"} == {"A", "P", "S", "V", "T"}
    assert [p["status"] for p in procs if "outcome" not in p] == ["unknown"]
    # name-only substance -> note on the Procedure, no MedicationStatement
    assert any("Studienmedikation ohne Code" in n["text"] for p in procs for n in p.get("note", []))


def test_fixture_medication_statements(fixture_out):
    dk, bundle, rep = fixture_out
    procs = {"urn:uuid:" + p["id"] for p in by_profile(bundle, P_VORTHERAPIE)}
    meds = [m for m in by_profile(bundle, P_MEDSTMT) if m["partOf"][0]["reference"] in procs]
    codings = [c for m in meds for c in m["medicationCodeableConcept"]["coding"]]
    assert len(meds) == 9                                    # 10 substances, one name-only
    assert {c["system"] for c in codings} == {ATC, "http://www.whocc.no/atc"}   # WIdO URL normalised
    assert all(c.get("version") == "2025" for c in codings)
    named = [m for m in meds if m["medicationCodeableConcept"].get("text") == "Prüfsubstanz XY-123"]
    assert named and named[0]["medicationCodeableConcept"]["coding"][0]["code"] == "L01X"
    assert all(m["effectivePeriod"]["start"] for m in meds)


def test_fixture_responses(fixture_out):
    dk, bundle, rep = fixture_out
    obs = by_profile(bundle, P_RESPONSE)
    assert sorted(o["valueCodeableConcept"]["coding"][0]["code"] for o in obs if "partOf" in o
                  and any(p["id"] in o["partOf"][0]["reference"] for p in by_profile(bundle, P_VORTHERAPIE))) == \
        ["CR", "PD", "PR", "SD"]
    assert ("case.priorProcedures[].therapyResponseDate", "2022-02-02",
            "response date without a response value") in rep.dropped


def test_fixture_prior_diagnostics(fixture_out):
    dk, bundle, rep = fixture_out
    res = index(bundle)
    reports = [r for r in by_profile(bundle, P_REPORT) if r.get("effectiveDateTime") in ("2020-05-15", "2019-03-15")]
    assert len(reports) == 9            # 8 typed tests + 'none' with findings; 'none' without findings -> nothing
    method = {}
    for r in reports:
        if not ext(r, EXT_STUDY):
            assert r["conclusion"] == "Befund ohne Testangabe: KRAS G12C"
            continue
        study = res[ext(r, EXT_STUDY)[0]["valueReference"]["reference"]]
        ttype = study["code"]["coding"][0]["code"]
        an = res[study["extension"][0]["valueReference"]["reference"]]
        m = ext(an, EXT_METHOD)
        method[ttype] = m[0]["valueCodeableConcept"]["coding"][0]["code"] if m else None
    assert method == {"exome": "whole-exom-sequencing", "genomeLongRead": "whole-genom-sequencing",
                      "genomeShortRead": "whole-genom-sequencing", "panel": "gene-panel", "single": None,
                      "array": "microarray", "karyotyping": "karyotyping", "other": "other"}
    assert any(r.get("conclusion") == "EML4::ALK Fusion (Variante 1)\nMET Amplifikation" for r in reports)
    assert ("case.priorDiagnostics[].type", "none", "no prior genetic test performed: no study or report emitted") \
        in rep.dropped


def test_fixture_variants(fixture_out):
    dk, bundle, rep = fixture_out
    res = index(bundle)
    rep_exome = [r for r in by_profile(bundle, P_REPORT) if len(r.get("result", [])) == 2
                 and all(res[x["reference"]]["id"] for x in r["result"])]
    braf, tp53 = (res[x["reference"]] for x in rep_exome[0]["result"])
    assert comp(braf, "48018-6")[0]["valueCodeableConcept"]["coding"][0] == {
        "system": "http://www.genenames.org", "code": "HGNC:1097", "version": "2025-01", "display": "BRAF"}
    assert comp(braf, "48004-6")[0]["valueCodeableConcept"]["coding"][0]["code"] == "ENST00000646891.2:c.1799T>A"
    # Ensembl transcript: c. qualified, p. left bare (no ClinVar-style protein form for ENST; as molecular_variants)
    assert comp(braf, "48005-3")[0]["valueCodeableConcept"]["coding"][0]["code"] == "p.Val600Glu"
    assert comp(braf, "48004-6")[0]["valueCodeableConcept"]["text"] == "c.1799T>A"
    tx = comp(braf, "51958-7")[0]["valueCodeableConcept"]["coding"][0]
    assert tx["system"] == "http://www.ensembl.org" and tx["version"] == "113"
    so = comp(braf, "48019-4")[0]["valueCodeableConcept"]["coding"]
    assert [c["code"] for c in so] == ["SO:0001583", "SO:0001483"]
    assert {c["system"] for c in so} == {"http://www.sequenceontology.org"}
    assert comp(tp53, "51958-7")[0]["valueCodeableConcept"]["coding"][0]["system"] == "http://www.ncbi.nlm.nih.gov/refseq"
    assert comp(tp53, "48004-6")[0]["valueCodeableConcept"]["coding"][0]["code"] == "NM_000546.6:c.524G>A"
    assert comp(tp53, "48005-3")[0]["valueCodeableConcept"] == {
        "coding": [{"system": "http://varnomen.hgvs.org", "code": "NM_000546.6(TP53):p.Arg175His"}], "text": "p.Arg175His"}


def test_fixture_episode(fixture_out):
    dk, bundle, rep = fixture_out
    ep = by_profile(bundle, P_EPISODE)
    assert len(ep) == 1
    ep = ep[0]
    assert ep["effectivePeriod"]["start"] == dk["metaData"]["molecularBoardDecisionDate"]
    si = {s["reference"] for s in ep["supportingInfo"]}
    assert {"urn:uuid:" + p["id"] for p in by_profile(bundle, P_VORTHERAPIE)} <= si
    assert {"urn:uuid:" + r["id"] for r in by_profile(bundle, P_REPORT) if "result" in r or "conclusion" in r
            or ext(r, EXT_STUDY)} & si


def test_profile_set_2026_no_crash():
    from genomde2fhir import convert
    bundle, rep = convert(load(FIXTURE), str(FIXTURE), "2026", strict=True)
    assert rep.status == "converted" and by_profile(bundle, P_VORTHERAPIE)


# ---- coverage of the block ---------------------------------------------------------------------------------------
def test_block_coverage(fixture_out, convert_dk):
    _, _, rep = fixture_out
    covered, preserved = set(rep.covered), set(rep.preserved)
    for pred in (lambda d: any(pd.get("simpleVariants") for pd in (d.get("case") or {}).get("priorDiagnostics") or []),
                 lambda d: any(p.get("therapyResponse") for p in (d.get("case") or {}).get("priorProcedures") or [])):
        f, dk = first_with("oncology", pred)
        _, r = convert_dk(dk, str(f))
        covered |= r.covered
        preserved |= r.preserved
    rows = {p: r for p, r in mapping_rows("oncology").items() if p.startswith(BLOCK)}
    assert rows, "mapping rows of the block missing"
    missing = [p for p in rows if p not in covered | preserved]
    assert not missing, f"block paths neither covered nor preserved: {missing}"
    mapped_not_covered = [p for p, r in rows.items() if r["status"] == "MAPPED" and p not in covered and p not in LOCAL]
    assert not mapped_not_covered, mapped_not_covered
    assert LOCAL <= preserved
