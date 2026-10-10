"""Regression tests for the onco_mol review fixes (R15/R38, R23, R48, R49, R55, R67, R68, F01, F08, F19, C1).

Each test reproduces the original failure scenario on a small synthetic input (existing fixtures, modified inline).
Checks against the MII packages run only when ~/.fhir/packages holds them (skipped in CI).
"""
import copy
import json
from pathlib import Path

import pytest
from conftest import REPO, load, resources

from genomde2fhir import convert
from genomde2fhir.builders.onco import molecular_variants, tnm
from genomde2fhir.identity import case_key
from genomde2fhir.systems import SNOMED, UICC

FIX = Path(__file__).parent / "fixtures"
BIOMARKERS = FIX / "onco_biomarkers" / "synthetic_biomarkers.json"
DIAG_DROPS = FIX / "onco_diagnosis" / "diagnosis_drops.json"
DIAG_FULL = FIX / "onco_diagnosis" / "diagnosis_full.json"
VARIANTS = FIX / "onco_variants" / "synthetic_small_variants.json"
PRIOR = FIX / "onco_prior" / "prior_all_enums.json"
PKG = Path.home() / ".fhir" / "packages"
ONKO_2026 = PKG / "de.medizininformatikinitiative.kerndatensatz.onkologie#2026.0.3" / "package"
ONKO_2027 = PKG / "de.medizininformatikinitiative.kerndatensatz.onkologie#2027.0.0-ballot.1" / "package"
MTB = "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/"
MAX1 = ("mii-pr-mtb-mutationslast", "mii-pr-mtb-mikrosatelliteninstabilitaet", "mii-pr-mtb-ploidie",
        "mii-pr-mtb-hrd-score", "mii-pr-mtb-brcaness")
SCT_V = "http://snomed.info/sct/900000000000207008/version/20240401"


def run(dk, ps="2027", **kw):
    b, rep = convert(dk, "<fix>", ps, **kw)
    assert rep.status == "converted", rep.error or rep.input_findings
    return b, rep


def by_url(b):
    return {e["fullUrl"]: e["resource"] for e in b["entry"]}


def profile(r):
    return (r.get("meta", {}).get("profile") or [""])[0].rsplit("/", 1)[-1]


def of_profile(b, name):
    return [r for r in resources(b) if profile(r) == name]


def ref(r):
    return {"reference": f"urn:uuid:{r['id']}"}


def cs_concepts(path: Path) -> dict:
    out = {}

    def walk(cs):
        for c in cs:
            out[c["code"]] = c.get("display")
            walk(c.get("concept", []))
    walk(json.loads(path.read_text())["concept"])
    return out


def need(path: Path):
    if not path.exists():
        pytest.skip(f"{path} not in the FHIR package cache")


# ---- R15 / R38: 0..1 result slices of mii-pr-mtb-ngs-bericht ------------------------------------------------------
def current_only(path):
    """Fixture without prior findings (they have NGS reports of their own)."""
    dk = load(path)
    dk["case"].pop("priorDiagnostics", None)
    return dk


def test_r15_several_complex_biomarkers_one_report_each():
    dk = current_only(BIOMARKERS)
    b, rep = run(dk)
    idx = by_url(b)
    reports = of_profile(b, "mii-pr-mtb-ngs-bericht")
    for dr in reports:   # no report holds two results of a 0..1 slice
        profs = [profile(idx[x["reference"]]) for x in dr.get("result", [])]
        for p in MAX1:
            assert profs.count(p) <= 1, (dr["id"], p, profs)
    # no data loss: every TMB / HRD / ploidy Observation is a result of exactly one report
    bio = [r for r in resources(b, "Observation") if profile(r) in MAX1]
    cited = [x["reference"] for dr in reports for x in dr.get("result", [])]
    assert len(bio) == 5 and all(cited.count(f"urn:uuid:{o['id']}") == 1 for o in bio)
    key = case_key(dk, "oncology")
    per_entry = {key.id("DiagnosticReport", "ngs-report", "complex-biomarker", sid)
                 for sid in ("cb-atfexm92", "cb-tmb-only", "cb-flags")}
    assert per_entry <= {r["id"] for r in reports}
    # every current report is linked from the Behandlungsepisode via its own investigation:NgsBericht
    (ep,) = of_profile(b, "mii-pr-mtb-behandlungsepisode")
    linked = [i["item"][0] for i in ep["investigation"] if i["code"]["coding"][0]["code"] == "106221001"]
    main = key.id("DiagnosticReport", "ngs-report")
    assert sorted(x["reference"] for x in linked) == sorted(f"urn:uuid:{i}" for i in per_entry | {main})
    assert any("complexBiomarkers entries" in m for _, m in rep.warnings)
    assert rep.representations["ngs-report-per-complex-biomarker-entry"] == 1


def test_r15_single_entry_keeps_one_report():
    dk = current_only(BIOMARKERS)
    dk["molecular"]["complexBiomarkers"] = [dk["molecular"]["complexBiomarkers"][0]]
    b, rep = run(dk)
    (dr,) = of_profile(b, "mii-pr-mtb-ngs-bericht")
    assert dr["id"] == case_key(dk, "oncology").id("DiagnosticReport", "ngs-report")
    assert not any("complexBiomarkers entries" in m for _, m in rep.warnings)


def test_r15_biomarkers_only_no_empty_main_report():
    dk = current_only(BIOMARKERS)
    dk["molecular"] = {"complexBiomarkers": [{"identifier": "a", "tmb": 3.1}, {"identifier": "b", "tmb": 7.0}]}
    b, _ = run(dk)
    reports = of_profile(b, "mii-pr-mtb-ngs-bericht")
    assert len(reports) == 2 and all(len(r["result"]) == 1 for r in reports)


# ---- R23: TNM edition --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("version,ed", [
    ("8", "8"), ("8th", "8"), ("8th ed.", "8"), ("UICC 8", "8"), ("TNM8", "8"), ("8. Auflage", "8"), ("9", "9"),
    ("2025-03-01", None), ("2017", None), ("10. Auflage", None), ("0", None), ("20240401", None), (None, None)])
def test_r23_edition_only_explicit_numbers(version, ed):
    assert tnm._edition(version) == ed


def test_r23_snomed_release_label_is_no_edition():
    dk = load(DIAG_DROPS)
    dk["case"]["diagnosisOd"]["tnmClassifications"] = [
        {"code": c, "system": SNOMED, "version": "2025-03-01", "display": c} for c in ("T3", "N1", "M0")]
    b, rep = run(dk)
    obs = [r for r in resources(b, "Observation") if profile(r).startswith("mii-pr-onko-tnm-")]
    assert len(obs) == 4 and not any("method" in o for o in obs)   # used to be '2. Auflage'
    assert ("case.diagnosisOd.tnmClassifications[].version", "2025-03-01",
            "not an explicit TNM edition number (1-9)") in rep.dropped
    assert any(p.endswith(".version") and "no edition number" in m for p, m in rep.warnings)


# ---- R48: ConceptMap target displays -----------------------------------------------------------------------------
CM_SRC = REPO / "mvgs-ig" / "input" / "ConceptMap-mvgs-cm-tnm-sct-uicc.json"


def _cm_targets():
    cm = json.loads(CM_SRC.read_text())
    return [(e["code"], t["code"], t.get("display")) for g in cm["group"] for e in g["element"]
            for t in e.get("target", []) if t.get("code")]


def test_r48_cm_target_displays_fixed():
    targets = {(s, c): d for s, c, d in _cm_targets()}
    for sct in ("1352969009", "1352569002"):
        assert targets[(sct, "T2c")] == "T2c"
    for sct in ("1352994005", "1352531007"):
        assert targets[(sct, "T3d")] == "T3d"
    assert not [d for d in targets.values() if d in ("T2c2", "Td3")]


def test_r48_cm_target_displays_match_codesystem():
    need(ONKO_2027)
    cs = cs_concepts(ONKO_2027 / "CodeSystem-mii-cs-onko-tnm-uicc.json")
    assert [(s, c, d) for s, c, d in _cm_targets() if d != cs.get(c)] == []


# ---- R49: UICC display from the CodeSystem ----------------------------------------------------------------------
@pytest.mark.parametrize("ps", ["2027", "2026"])
def test_r49_uicc_display_n1mi_nx(ps):
    dk = load(DIAG_DROPS)
    dk["case"]["diagnosisOd"]["tnmClassifications"] = [
        {"code": "1352620005", "system": SNOMED, "version": SCT_V, "display": "pN1mi", "text": "pN1mi"},
        {"code": "N1mi", "system": "UICC", "version": "8", "display": "N1mi"},
        {"code": "NX", "system": "UICC", "version": "8", "display": "NX"},
        {"code": "1352969009", "system": SNOMED, "version": SCT_V, "display": "cT2c", "text": "cT2c"},
    ]
    b, _ = run(dk, ps)
    got = [c for o in resources(b, "Observation") if profile(o).endswith("-kategorie")
           for c in o["valueCodeableConcept"]["coding"] if c["system"] == UICC]
    assert [(c["code"], c["display"]) for c in got] == [("N1mi", "N1(mi)"), ("N1mi", "N1(mi)"), ("NX", "Nx"),
                                                         ("T2c", "T2c")]


def test_r49_display_table_matches_codesystem():
    for pkg in (ONKO_2026, ONKO_2027):
        need(pkg)
        cs = cs_concepts(pkg / "CodeSystem-mii-cs-onko-tnm-uicc.json")
        targets = {c for _, c, _ in _cm_targets()}
        assert {c: cs[c] for c in targets if c in cs and cs[c] != c} == tnm.UICC_DISPLAY


# ---- R67: 9th-edition codes under 2026 ----------------------------------------------------------------------------
def _uicc_items(*codes):
    return [{"code": c, "system": "UICC", "version": "9th ed.", "display": c} for c in codes]


def test_r67_ninth_edition_codes_text_fallback_2026():
    dk = load(DIAG_DROPS)
    dk["case"]["diagnosisOd"]["tnmClassifications"] = _uicc_items("T1b3", "N0", "M1c1")
    b, rep = run(dk, "2026")
    cats = [o for o in resources(b, "Observation") if profile(o).endswith("-kategorie")]
    assert [o["valueCodeableConcept"]["coding"][0]["code"] for o in cats] == ["N0"]
    wk = [o for o in of_profile(b, "mii-pr-onko-weitere-klassifikationen") if o["code"]["text"] == "TNM"]
    assert sorted(o["valueCodeableConcept"]["text"] for o in wk) == ["M1c1", "T1b3"]
    assert all("coding" not in o["valueCodeableConcept"] for o in wk)
    assert sum("not in the 2026 TNM value sets" in m for _, m in rep.warnings) == 2
    b27, _ = run(dk, "2027")
    assert len([o for o in resources(b27, "Observation") if profile(o).endswith("-kategorie")]) == 3


def test_r67_set_matches_2026_value_sets():
    need(ONKO_2026)
    need(ONKO_2027)
    vs = set()
    for ax in "tnm":
        doc = json.loads((ONKO_2026 / f"ValueSet-mii-vs-onko-tnm-{ax}-kategorie-werte.json").read_text())
        vs |= {c["code"] for inc in doc["compose"]["include"] for c in inc.get("concept", [])}
    targets = {c for _, c, _ in _cm_targets()}
    assert targets - vs == tnm.UICC_NOT_IN_2026


# ---- R68: y/r/a prefixes under 2026 -------------------------------------------------------------------------------
def test_r68_yra_symbol_observations_2026():
    dk = load(DIAG_DROPS)
    dk["case"]["diagnosisOd"]["tnmClassifications"] = [
        {"code": "T2", "system": "UICC", "version": "8", "display": "ypT2", "text": "ypT2"},
        {"code": "N0", "system": "UICC", "version": "8", "display": "rN0", "text": "rN0"},
        {"code": "M0", "system": "UICC", "version": "8", "display": "yM0", "text": "yM0"},
    ]
    b, rep = run(dk, "2026")
    (group,) = of_profile(b, "mii-pr-onko-tnm-klassifikation")
    members = [by_url(b)[m["reference"]] for m in group["hasMember"]]
    syms = {profile(m): m for m in members if profile(m).endswith("-symbol")}
    assert set(syms) == {"mii-pr-onko-tnm-y-symbol", "mii-pr-onko-tnm-r-symbol"}     # one per letter
    y = syms["mii-pr-onko-tnm-y-symbol"]
    assert y["code"]["coding"][0]["code"] == "101658-3"
    assert y["valueCodeableConcept"]["coding"][0]["code"] == "421755005"
    assert syms["mii-pr-onko-tnm-r-symbol"]["valueCodeableConcept"]["coding"][0]["code"] == "421188008"
    assert not any("no y/r/a element" in m for _, m in rep.warnings)
    assert not any("modifierExtension" in m for m in members)
    b27, _ = run(dk, "2027")
    assert not [r for r in resources(b27) if profile(r).endswith("-symbol")]
    t27 = [o for o in resources(b27, "Observation") if profile(o) == "mii-pr-onko-tnm-t-kategorie"][0]
    assert t27["modifierExtension"][0]["url"].endswith("mii-ex-onko-tnm-y-praefix")


# ---- F01: DNPM tumour spread -> mii-pr-mtb-tumorausbreitung ---------------------------------------------------------
def _with_spread(*items):
    dk = load(DIAG_FULL)
    dk["case"]["diagnosisOd"]["additionalClassification"] = list(items)
    return dk


SPREAD = "dnpm-dip/mtb/diagnosis/kds-tumor-spread"


@pytest.mark.parametrize("ps", ["2027", "2026"])
def test_f01_tumor_spread_dedicated_profile(ps):
    dk = _with_spread({"system": SPREAD, "key": "local"}, {"system": "FIGO", "key": "IIB"})
    b, rep = run(dk, ps)
    (ts,) = of_profile(b, "mii-pr-mtb-tumorausbreitung")
    assert ts["code"]["coding"][0]["code"] == "371508000"
    assert ts["category"][0]["coding"][0]["code"] == "473302008"
    assert ts["valueCodeableConcept"] == {"coding": [{"system": SNOMED, "code": "255127006",
                                                      "display": "Local tumor spread"}], "text": "local"}
    assert ts["effectiveDateTime"] == dk["case"]["diagnosisOd"]["mainDiagnosis"]["date"]
    (cond,) = of_profile(b, "mii-pr-mtb-diagnose-primaertumor")
    assert cond["stage"] == [{"type": {"coding": [{"system": "https://nih-ncpi.github.io/ncpi-fhir-ig/CodeSystem-ncit.html",
                                                   "code": "C19251", "display": "Stage at Diagnosis"}]},
                              "assessment": [ref(ts)]}]
    assert ts["focus"] == [ref(cond)]
    wk = of_profile(b, "mii-pr-onko-weitere-klassifikationen")
    assert [o["code"]["text"] for o in wk if o["code"]["text"] != "TNM"] == ["FIGO"]   # other systems unchanged
    assert {"case.diagnosisOd.additionalClassification[].system",
            "case.diagnosisOd.additionalClassification[].key"} <= rep.covered


def test_f01_unknown_key_and_second_item():
    dk = _with_spread({"system": SPREAD, "key": "regional"}, {"system": SPREAD, "key": "metastasized"},
                      {"system": SPREAD, "key": "tumor-free"})
    b, rep = run(dk)
    ts = of_profile(b, "mii-pr-mtb-tumorausbreitung")
    assert [o["valueCodeableConcept"]["text"] for o in ts] == ["metastasized", "tumor-free"]
    wk = [o for o in of_profile(b, "mii-pr-onko-weitere-klassifikationen") if o["code"]["text"] == SPREAD]
    assert [o["valueCodeableConcept"] for o in wk] == [{"text": "regional"}]     # no tumorausbreitung code
    (cond,) = of_profile(b, "mii-pr-mtb-diagnose-primaertumor")
    assert [s["assessment"] for s in cond["stage"]] == [[ref(ts[0])]]                # stage slice 0..1
    assert any("second tumour-spread item" in m for _, m in rep.warnings)


def test_f01_no_diagnosis_date_data_absent_reason():
    dk = _with_spread({"system": SPREAD, "key": "unknown"})
    del dk["case"]["diagnosisOd"]["mainDiagnosis"]["date"]
    b, _ = run(dk, check_input=False)
    (ts,) = of_profile(b, "mii-pr-mtb-tumorausbreitung")
    assert "effectiveDateTime" not in ts
    assert ts["_effectiveDateTime"]["extension"][0]["valueCode"] == "unknown"


# ---- F08: placeholder topography 'T' ------------------------------------------------------------------------------
def test_f08_placeholder_topography_dropped():
    dk = load(DIAG_DROPS)
    dk["case"]["diagnosisOd"]["histology"] = {"code": "8140/3", "system": "urn:oid:2.16.840.1.113883.6.43.1",
                                             "version": "Zweite Revision"}
    b, rep = run(dk)
    (cond,) = of_profile(b, "mii-pr-mtb-diagnose-primaertumor")
    assert "bodySite" not in cond and "note" not in cond
    dropped = {p: why for p, _, why in rep.dropped}
    for k in ("code", "system", "version", "display"):
        p = f"case.diagnosisOd.topography.{k}"
        assert "topography-axis root" in dropped[p] and p not in rep.preserved | rep.covered


# ---- F19: legacy case.priorDiagnostic keeps index 0 ---------------------------------------------------------------
def _prior_ids(b):
    return sorted(r["id"] for r in resources(b) if profile(r) in (
        "mii-pr-mtb-ngs-bericht", "mii-pr-mtb-genomic-study", "mii-pr-mtb-genomic-study-analysis",
        "mii-pr-mtb-einfache-variante"))


def test_f19_legacy_prior_diagnostic_same_ids_as_array():
    new = load(PRIOR)
    new["case"]["priorDiagnostics"] = new["case"]["priorDiagnostics"][:1]
    old = copy.deepcopy(new)
    old["case"]["priorDiagnostic"] = old["case"].pop("priorDiagnostics")[0]
    b_new, _ = run(new)
    b_old, rep_old = run(old, check_input=False)          # legacy key is not in the current schema
    assert _prior_ids(b_old) == _prior_ids(b_new) != []
    assert any(p == "case.priorDiagnostic" for p, _ in rep_old.warnings)


def test_f19_legacy_next_to_array_does_not_collide():
    dk = load(PRIOR)
    dk["case"]["priorDiagnostics"] = dk["case"]["priorDiagnostics"][:1]
    dk["case"]["priorDiagnostic"] = copy.deepcopy(dk["case"]["priorDiagnostics"][0])
    b, _ = run(dk, check_input=False)
    assert len(of_profile(b, "mii-pr-mtb-ngs-bericht")) == 2


# ---- R55 / C1: HGVS qualification -----------------------------------------------------------------------------------
@pytest.mark.parametrize("tr,acc", [
    ({"code": "NM_000546"}, None),                       # unversioned RefSeq: no valid HGVS reference
    ({"code": "NM_000546", "version": "6"}, "NM_000546.6"),
    ({"code": "NM_000546.6"}, "NM_000546.6"),
    ({"code": "ENST00000269305"}, "ENST00000269305"),   # Ensembl unchanged (accepted by the HGVS check)
    ({"code": "2b3c587b-8abc-4c72-8e2f-2809624f9204"}, None)])
def test_r55_transcript_accession(tr, acc):
    assert molecular_variants.transcript_accession(tr) == acc


def _variant_values(b, loinc):
    return [c["valueCodeableConcept"] for o in of_profile(b, "mii-pr-mtb-einfache-variante")
            for c in o["component"] if c["code"]["coding"][0]["code"] == loinc]


def test_r55_unversioned_refseq_not_qualified():
    dk = current_only(VARIANTS)
    sv = dk["molecular"]["smallVariants"] = dk["molecular"]["smallVariants"][:1]
    sv[0]["transcriptId"] = {"code": "NM_000546", "system": "https://www.ncbi.nlm.nih.gov/refseq/"}
    b, rep = run(dk)
    assert _variant_values(b, "48004-6") == [{"coding": [{"system": "http://varnomen.hgvs.org", "code": sv[0]["dnaChange"]}]}]
    assert rep.representations["hgvs-unqualified"] == 2
    assert [m for _, m in rep.warnings if "HGVS not qualified" in m and "has no version" in m]


def test_c1_non_accession_transcripts_warn_once():
    dk = current_only(VARIANTS)
    for i, sv in enumerate(dk["molecular"]["smallVariants"]):
        sv["transcriptId"] = {"code": f"2b3c587b-8abc-4c72-8e2f-28096242920{i}", "system": "https://example.org/tx"}
    b, rep = run(dk)
    n = len([sv for sv in dk["molecular"]["smallVariants"] for f in ("dnaChange", "proteinChange")
             if sv.get(f) and ":" not in sv[f]])                  # strings already qualified by the sender stay as is
    assert n > 2 and rep.representations["hgvs-unqualified"] == n
    warned = [m for _, m in rep.warnings if "HGVS not qualified" in m]
    assert len(warned) == 1 and "not a RefSeq/Ensembl accession" in warned[0]


def test_c1_prior_diagnostics_use_the_same_warning():
    dk = load(PRIOR)
    for pd in dk["case"]["priorDiagnostics"]:
        for sv in pd.get("simpleVariants") or []:
            sv["transcript"] = {"code": "TX-1", "system": "local"}
    b, rep = run(dk)
    warned = [(p, m) for p, m in rep.warnings if "HGVS not qualified" in m]
    assert len(warned) == 1 and warned[0][0].startswith("case.priorDiagnostics[].simpleVariants[].")
