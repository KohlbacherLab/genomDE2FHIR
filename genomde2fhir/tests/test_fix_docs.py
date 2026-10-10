"""Regression tests for review findings of group docs (mapping table and docs describe the converter as it is).

F04 submission.date claimed as part of the resource identity     F14 RD tanC row promised an assigner
F13 follow-up ECOG notes: category / LOINC answer 2027 only        F15 compHet code said to be in LL381-5
F17 genes[].display used without a mapping row                    F01 tumour spread profile missing from the rows
R30 follow-up diagnoses: source system slices                     R28 capability matrix claimed ICD-O-3 is checked
plus the format contract of the CSVs (CRLF, header, package-data copy) and the terminology-gate wording rules.
"""
import copy
import csv
import re

import pytest
from conftest import REPO, load, resources

from genomde2fhir import convert
from genomde2fhir.builders.rd import variants

ONCO = REPO / "examples/oncology/OncologySubmission_044AFF6262356F2F8EC60039DC08AE36FBAA011DE29740CBC83E9FA5643E4640.json"
RD = REPO / "examples/rarediseases/RareDiseasesSubmission_485A17D06AAF5617E285789BF949526D04CB837D1724084F892A3181F68BFC49.json"
CSVS = ("mapping_kdk_oncology.csv", "mapping_kdk_rarediseases.csv", "mapping_grz.csv")
HEADER = ["path", "type", "required", "array", "enum", "format", "description", "mii_module", "mii_profile",
          "fhir_element", "transform", "status", "notes", "reference"]
PKG = REPO / "genomde2fhir" / "src" / "genomde2fhir" / "data" / "mapping"
SID_TAN_C = "https://genomde.de/fhir/sid/tan-c"
TUMORAUSBREITUNG = "mii-pr-mtb-tumorausbreitung"


def rows(name: str) -> dict:
    with (REPO / "mapping" / name).open(newline="", encoding="utf-8") as f:
        return {r["path"]: r for r in csv.DictReader(f)}


def run(dk, profile_set="2027"):
    bundle, rep = convert(dk, "<fix_docs>", profile_set, strict=True)
    assert rep.status == "converted", rep.error or rep.input_findings
    return bundle, rep


# ---- CSV format contract -----------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", CSVS)
def test_mapping_csv_format_and_package_copy(name):
    raw = (REPO / "mapping" / name).read_bytes()
    assert raw.count(b"\r\n") == raw.count(b"\n"), "CRLF line endings"
    with (REPO / "mapping" / name).open(newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        paths = [r["path"] for r in rd]
        assert rd.fieldnames == HEADER
    assert len(paths) == len(set(paths))
    assert (PKG / name).read_bytes() == raw, "run scripts/sync_package_data.py"


def test_no_six_digit_loinc_next_to_snomed():
    """scripts/check_terminology.py reads every 6-18 digit number of a row that mentions SNOMED as a SNOMED code, so a
    LOINC code with six digits before the hyphen (101658-3) in such a row is reported INVALID (gate failure)."""
    bad = []
    for name in CSVS:
        for p, r in rows(name).items():
            blob = " ".join(r[c] for c in ("transform", "fhir_element", "reference", "mii_profile"))
            if "SNOMED" in blob.upper() and re.search(r"\b\d{6,7}-\d\b", blob):
                bad.append(f"{name}:{p}")
    assert bad == []


# ---- F04: submission.date is part of the Provenance id only ------------------------------------------------------
def test_submission_date_changes_only_the_provenance_id():
    dk = load(ONCO)
    a, _ = run(dk)
    dk2 = copy.deepcopy(dk)
    dk2["metaData"]["submission"]["date"] = "2026-05-01"
    b, _ = run(dk2)
    ids = lambda bundle: {(e["resource"]["resourceType"], e["resource"]["id"]) for e in bundle["entry"]}  # noqa: E731
    diff = ids(a) ^ ids(b)
    assert diff and {t for t, _ in diff} == {"Provenance"}
    for name in ("mapping_kdk_oncology.csv", "mapping_kdk_rarediseases.csv"):
        t = rows(name)["metaData.submission.date"]["transform"]
        assert "not part of any other resource id" in t and "part of the resource identity" not in t


# ---- F14: RD tanC without assigner, as emitted ------------------------------------------------------------------
def test_rd_tanc_row_matches_converter():
    bundle, _ = run(load(RD))
    pat = next(p for p in resources(bundle, "Patient") if any(i.get("system") == SID_TAN_C for i in p["identifier"]))
    tan = next(i for i in pat["identifier"] if i["system"] == SID_TAN_C)
    assert "assigner" not in tan
    t = rows("mapping_kdk_rarediseases.csv")["metaData.tanC"]["transform"]
    assert "no assigner" in t and "assigner.identifier" not in t
    assert t == rows("mapping_kdk_oncology.csv")["metaData.tanC"]["transform"]


# ---- F13: follow-up ECOG: no category, coding:loinc in both profile sets -----------------------------------------
@pytest.mark.parametrize("profile_set", ["2026", "2027"])
def test_followup_ecog_notes_match_converter(profile_set):
    dk = load(ONCO)
    score = dk["followUp"]["followUpOds"][0]["ecogPerformanceStatusScore"]
    bundle, _ = run(dk, profile_set)
    ecog = [o for o in resources(bundle, "Observation", "mii-pr-onko-allgemeiner-leistungszustand-ecog")
            if any(c.get("code") == score for c in o["valueCodeableConcept"]["coding"])]
    assert ecog and all("category" not in o for o in ecog)
    assert all(any(c["system"] == "http://loinc.org" for c in o["valueCodeableConcept"]["coding"]) for o in ecog)
    notes = rows("mapping_kdk_oncology.csv")["followUp.followUpOds[].ecogPerformanceStatusScore"]["notes"]
    assert "category survey" not in notes and "LOINC answer coding 2027 only" not in notes


# ---- F15: compHet codes as emitted -------------------------------------------------------------------------------
def test_comphet_rows_match_converter_codes():
    het, comp = variants.ZYGOSITY["compHet"][0], variants.COMPOUND_HET["code"]
    assert (het, comp) == ("LA6706-1", "LA26217-2")
    for v in ("copyNumberVariants", "smallVariants", "structuralVariants"):
        t = rows("mapping_kdk_rarediseases.csv")[f"molecular.{v}[].zygosity"]["transform"]
        assert f"compHet={het} Heterozygous + second coding {comp}" in t and "compHet=LA26217-2," not in t


# ---- F17: genes[].display has a row and is covered ---------------------------------------------------------------
def test_genes_display_rows_covered():
    table = rows("mapping_kdk_rarediseases.csv")
    paths = [f"molecular.{v}[].genes[].display" for v in ("copyNumberVariants", "smallVariants", "structuralVariants")]
    assert all(table[p]["status"] == "MAPPED" for p in paths)
    dk = load(RD)
    present = [p for p in paths if any(g.get("display") for v in dk["molecular"].get(p.split(".")[1][:-2]) or []
                                       for g in v.get("genes") or [])]
    _, rep = run(dk)                 # strict: a covered path without a mapping row would raise
    assert present and set(present) <= rep.covered
    # fix round 3 (R36): display is used and covered; its unknown-field finding stays (CLI: 'converted', --strict
    # rejects it like every other undeclared field)


# ---- F01: tumour spread profile named by the rows and emitted ----------------------------------------------------
def test_tumor_spread_rows_name_the_emitted_profile():
    bundle, _ = run(load(ONCO))
    obs = resources(bundle, "Observation", TUMORAUSBREITUNG)
    assert len(obs) == 1
    emitted = obs[0]["meta"]["profile"][0].split("|")[0]
    for k in ("key", "system"):
        assert emitted in rows("mapping_kdk_oncology.csv")[f"case.diagnosisOd.additionalClassification[].{k}"]["mii_profile"]


# ---- R30: follow-up diagnoses keep their source system -----------------------------------------------------------
def test_followup_diagnosis_rows_name_all_source_slices():
    table = rows("mapping_kdk_oncology.csv")
    for k in ("code", "display", "system", "version"):
        fe = table[f"followUp.followUpOds[].additionalDiagnoses[].{k}"]["fhir_element"]
        assert all(s in fe for s in ("icd10-gm", "alpha-id", "orphanet", "sct"))
    assert "code always as ICD-10-GM" not in table["followUp.followUpOds[].additionalDiagnoses[].code"]["transform"]


# ---- reps cited by the docs exist in the converter ---------------------------------------------------------------
def test_cited_representation_ids_exist_in_code():
    src = "\n".join(p.read_text(encoding="utf-8") for p in (REPO / "genomde2fhir" / "src").rglob("*.py"))
    text = "\n".join(r["transform"] + " " + r["notes"] for n in CSVS for r in rows(n).values())
    text += (REPO / "docs" / "REPRESENTATIONS.md").read_text(encoding="utf-8")
    cited = set(re.findall(r"\brep `?([a-z0-9][a-z0-9-]+[a-z0-9])`?", text))
    assert cited and sorted(c for c in cited if f'"{c}"' not in src) == []


# ---- R28: capability matrix does not claim ICD-O-3 is checked ----------------------------------------------------
def test_capability_matrix_icdo3_row():
    doc = (REPO / "docs" / "TERMINOLOGY-CAPABILITY.md").read_text(encoding="utf-8")
    row = next(line for line in doc.splitlines() if line.startswith("| ICD-O-3"))
    cells = [c.strip() for c in row.strip("|").split("|")]
    assert "2000" in cells[2] and "validates" not in cells[2]
    assert cells[4] != "checked" and "unchecked" in cells[4]
    assert "ERROR" in doc
