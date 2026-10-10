"""Fix round 2, group docs: the mapping table and the docs describe the converter as it is after round 2.

Each test pins one documented rule to the converter (or to the constant it uses), so a later code change that the
docs do not follow, or a doc edit that drifts from the code, fails here:
R06/R43 GRZ genomic study keying and meta.source      R39 contained resources of the embedded Broad Consent
R11 combination identifiers (plain <id> on the first member)   R30 empty follow-up diagnosis code
F20 study substances without a ResearchStudy           R67 2026 9th-edition TNM codes in a SNOMED-labelled field
RD-BASEDON Seltene Therapieplan -> indication board    R54 empty arrays of renamed keys
consent schemaVersion enum (KDK fe724ff)               docs: README / PLAN / register / capability matrix / MTB-22
"""
import copy
import csv
import json
import re

import pytest
from conftest import REPO, load, resources

from genomde2fhir import convert, io, validate
from genomde2fhir.identity import SOURCE_PREFIX

ONCO = REPO / "examples/oncology/OncologySubmission_044AFF6262356F2F8EC60039DC08AE36FBAA011DE29740CBC83E9FA5643E4640.json"
RD = REPO / "examples/rarediseases/RareDiseasesSubmission_485A17D06AAF5617E285789BF949526D04CB837D1724084F892A3181F68BFC49.json"
GRZ = REPO / "examples/grz/grz-paired-onco-01.json"
SID_KDK_OBJECT = "https://genomde.de/fhir/sid/kdk-object-id"
SNOMED = "http://snomed.info/sct"
FU = "followUp.followUpOds[]."


def rows(name: str) -> dict:
    with (REPO / "mapping" / name).open(newline="", encoding="utf-8") as f:
        return {r["path"]: r for r in csv.DictReader(f)}


def doc(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def register_row(n: int) -> str:
    return next(line for line in doc("docs/REPRESENTATIONS.md").splitlines() if line.startswith(f"| {n} |"))


def run(dk, profile_set="2027", **kw):
    bundle, rep = convert(dk, "<fix2_docs>", profile_set, strict=True, **kw)
    assert rep.status == "converted", rep.error or rep.input_findings
    return bundle, rep


# ---- R06 / R43: GRZ genomic study keying, meta.source -------------------------------------------------------------
def _study_id(bundle):
    studies = [r for r in resources(bundle, "Procedure")
               if any(p.split("|")[0].endswith("-genomic-study") for p in r["meta"]["profile"])]
    assert len(studies) == 1
    return studies[0]["id"]


def test_grz_genomic_study_rows_match_keying():
    dk = load(GRZ)
    initial = _study_id(run(dk)[0])
    later = copy.deepcopy(dk)
    later["submission"]["submissionDate"] = "2026-06-01"
    keys = {}
    for stype in ("correction", "followup", "addition"):
        later["submission"]["submissionType"] = stype
        keys[stype] = _study_id(run(later)[0])
    assert keys["correction"] == initial                  # a correction rewrites the initial submission's study
    assert keys["followup"] == keys["addition"] != initial  # followup / addition: own study by submission date
    grz = rows("mapping_grz.csv")
    date = grz["submission.submissionDate"]
    assert "genomic study id for followup/addition only" in date["fhir_element"]
    assert "initial submission and its corrections share one genomic study" in date["transform"]
    assert "with tanG also the key" not in date["transform"] and "meta.source" in date["transform"]
    assert "selects the genomic study key" in grz["submission.submissionType"]["transform"]
    assert "one genomic study per submission" not in grz["submission.genomicStudyType"]["transform"]
    assert "one Procedure per submission" not in register_row(41)


def test_kdk_submission_rows_meta_source_always_preserved():
    """metaData.submission.date / type are preserved through meta.source even without the Provenance."""
    bundle, rep = run(load(ONCO), provenance=False)
    assert not resources(bundle, "Provenance")
    assert all(e["resource"]["meta"]["source"].startswith(SOURCE_PREFIX) for e in bundle["entry"])
    assert {"metaData.submission.date", "metaData.submission.type"} <= rep.preserved
    assert rep.representations["meta-source"]
    for name in ("mapping_kdk_oncology.csv", "mapping_kdk_rarediseases.csv"):
        for p in ("metaData.submission.date", "metaData.submission.type"):
            t = rows(name)[p]["transform"]
            assert "only when the Provenance is emitted" not in t
            assert SOURCE_PREFIX in t and "rep meta-source" in t
    assert SOURCE_PREFIX in register_row(54)


# ---- R39: contained resources of the embedded Broad Consent -------------------------------------------------------
def test_consent_scope_rows_describe_contained_rule():
    for name, path in (("mapping_kdk_oncology.csv", "metaData.researchConsents[].scope"),
                       ("mapping_kdk_rarediseases.csv", "metaData.researchConsents[].scope"),
                       ("mapping_grz.csv", "donors[].researchConsents[].scope")):
        t = rows(name)[path]["transform"]
        assert "kept only when" not in t
        assert all(s in t for s in ("canonical/uri value", "refer to the Consent (#)", "urn:uuid references"))
    assert "canonical/uri" in register_row(35) and "`urn:uuid`" in register_row(35)


# ---- R11: combination identifiers ---------------------------------------------------------------------------------
def test_combination_identifier_row_matches_converter():
    dk = load(ONCO)
    rec = dk["plan"]["recommendedSystemicTherapies"][0]
    rec["substances"] = [
        {"code": {"code": "L01FX07", "display": "Blinatumomab", "system": "http://fhir.de/CodeSystem/bfarm/atc",
                  "version": "2025"}},
        {"code": {"code": "L01XE01", "display": "Imatinib", "system": "http://fhir.de/CodeSystem/bfarm/atc",
                  "version": "2025"}}]
    bundle, _ = run(dk)
    rid = rec["identifier"]

    def values(r):
        return [i["value"].rsplit("|", 1)[-1] for i in r.get("identifier", []) if i.get("system") == SID_KDK_OBJECT
                and i["value"].rsplit("|", 1)[-1].split(":")[0] == rid]
    mrs = sorted(values(r) for r in resources(bundle, "MedicationRequest") if values(r))
    assert mrs == [[rid, f"{rid}:0"], [f"{rid}:1"]]       # first member: plain <id> (logical causedBy target) + <id>:0
    assert [values(r) for r in resources(bundle, "RequestGroup") if values(r)] == [[rid]]
    t = rows("mapping_kdk_oncology.csv")["plan.recommendedSystemicTherapies[].identifier"]["transform"]
    assert "the first member carries both <id> and <id>:0" in t and "each member MedicationRequest" not in t
    assert "first-member MedicationRequest" in rows("mapping_kdk_oncology.csv")[FU + "therapies[].reference"]["transform"]


def test_followup_therapy_rows_follow_round2():
    table = rows("mapping_kdk_oncology.csv")
    start = table[FU + "therapies[].therapyStartDate"]["transform"]
    assert "(array index)" not in start and "keyed by their substance set" in start
    assert "any report of the therapy sent with a code" in table[FU + "therapies[].substances[].name"]["transform"]
    assert "keyed by their substance set" in register_row(13)


# ---- R30: empty follow-up diagnosis code --------------------------------------------------------------------------
REASON_EMPTY = "empty code after normalisation: no Condition"


def test_additional_diagnosis_rows_match_drop_reason():
    dk = load(ONCO)
    fu = dk["followUp"]["followUpOds"][0]
    fu["metachroneDiagnoses"] = True
    fu["additionalDiagnoses"] = [{"code": "ORPHA:", "system": "https://www.orpha.net", "version": "4.7",
                                  "date": "2025-05-15"}]
    _, rep = run(dk)
    dropped = {(p, r) for p, _, r in rep.dropped}
    assert (FU + "additionalDiagnoses[].code", REASON_EMPTY) in dropped
    for k in ("code", "date", "display", "system", "version"):
        assert REASON_EMPTY in rows("mapping_kdk_oncology.csv")[FU + f"additionalDiagnoses[].{k}"]["transform"]


# ---- F20: substances of a study recommendation without a ResearchStudy --------------------------------------------
def test_study_substance_rows_match_note():
    dk = load(ONCO)
    study = dk["plan"]["recommendedStudies"][0]
    study.update(register="yesButStudyIsUnknown", name="N/A", id="",
                 substances=[{"name": "Pembrolizumab", "code": {"code": "L01FF02", "display": "Pembrolizumab",
                                                                "system": "http://fhir.de/CodeSystem/bfarm/atc",
                                                                "version": "2025"}}])
    bundle, rep = run(dk)
    assert not resources(bundle, "ResearchStudy") or all(
        "Pembrolizumab" not in json.dumps(r) for r in resources(bundle, "ResearchStudy"))
    notes = [n["text"] for r in resources(bundle, "ServiceRequest", "studieneinschluss-anfrage")
             for n in r.get("note", [])]
    assert any("Studiensubstanz laut dieser Empfehlung: Pembrolizumab (L01FF02)" in n for n in notes)
    assert rep.representations["study-substance-note"]
    for k in ("code.code", "code.display", "code.system", "code.version", "name"):
        t = rows("mapping_kdk_oncology.csv")[f"plan.recommendedStudies[].substances[].{k}"]["transform"]
        assert "rep study-substance-note" in t
    assert "study-substance-note" in register_row(15)


# ---- R67: 2026 9th-edition TNM codes, also from a SNOMED-labelled field ------------------------------------------
def test_tnm_row_ninth_edition_text_fallback_2026():
    dk = load(ONCO)
    tnm = dk["case"]["diagnosisOd"]["tnmClassifications"]      # the schema wants T, N and M (minItems 3)
    tnm[2] = {"code": "M1c1", "display": "M1c", "system": SNOMED, "version": "8"}
    bundle, rep = run(dk, "2026")
    wk = [o for o in resources(bundle, "Observation", "weitere-klassifikationen")
          if (o.get("code") or {}).get("text") == "TNM"]
    assert len(wk) == 1
    assert wk[0]["valueCodeableConcept"] == {"text": "M1c1 (M1c)"}           # names the code, never a SNOMED coding
    reason = "UICC code kept as text: no coding to carry its version"
    assert ("case.diagnosisOd.tnmClassifications[].version", reason) in {(p, r) for p, _, r in rep.dropped}
    table = rows("mapping_kdk_oncology.csv")
    assert "SNOMED-labelled field (never a SNOMED coding)" in table["case.diagnosisOd.tnmClassifications[].code"]["transform"]
    assert reason in table["case.diagnosisOd.tnmClassifications[].version"]["transform"]
    assert "tnm-yra-symbol-2026" in register_row(2) and "never a SNOMED coding" in register_row(2)


# ---- RD-BASEDON / R54 ---------------------------------------------------------------------------------------------
def test_rd_therapieplan_based_on_indication_board():
    bundle, _ = run(load(RD))
    board = resources(bundle, "CarePlan", "mvgs-inclusion-decision")
    plan = resources(bundle, "CarePlan", "mii-pr-seltene-therapieplan")
    assert len(board) == 1 and len(plan) == 1
    url = next(e["fullUrl"] for e in bundle["entry"] if e["resource"] is board[0])
    assert plan[0]["basedOn"] == [{"reference": url}]
    row = rows("mapping_kdk_rarediseases.csv")["plan.carePlanRd.molecularBoardDecisionDate"]
    assert "basedOn -> indication-board CarePlan" in row["transform"] and "REPRESENTATIONS #36" in row["notes"]
    assert "mii-pr-seltene-therapieplan.basedOn" in register_row(36) and "does not link it yet" not in register_row(36)


def test_rd_empty_array_rule_noted():
    table = rows("mapping_kdk_rarediseases.csv")
    prior = [p for p in table if p.startswith("case.priorRds[].")]
    assert prior and all("case.priorRd is then read" in table[p]["notes"] for p in prior)
    for p in ("plan.recommendedTherapies[].variants[]", "plan.recommendedStudies[].variants[]"):
        assert "variantReferences is then read" in table[p]["notes"]


# ---- consent schemaVersion enum follows the vendored schemas ------------------------------------------------------
def _schema_version_enum(schema_file):
    found = []

    def walk(o):
        if isinstance(o, dict):
            sv = (o.get("properties") or {}).get("schemaVersion")
            if isinstance(sv, dict) and "kerndatensatz.consent" in sv.get("description", ""):
                found.append(sv["enum"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(json.loads((REPO / schema_file).read_text(encoding="utf-8")))
    assert found
    return ", ".join(found[0])


@pytest.mark.parametrize("schema_file, tables, path", [
    ("schemas/kdk/Submission.json", ("kdk_oncology", "kdk_rarediseases"), "metaData.researchConsents[].schemaVersion"),
    ("schemas/grz/grz-schema.json", ("grz",), "donors[].researchConsents[].schemaVersion"),
])
def test_consent_schema_version_enum_follows_schema(schema_file, tables, path):
    enum = _schema_version_enum(schema_file)
    for b in tables:
        assert rows(f"mapping_{b}.csv")[path]["enum"] == enum
        assert rows(f"mapping_omop_{b}.csv")[path]["enum"] == enum
    if len(tables) == 2:
        assert enum.endswith("2026.0.1")
        assert "2025.0.1 to 2026.0.1" in rows("mapping_kdk_oncology.csv")[path]["transform"]


# ---- docs ---------------------------------------------------------------------------------------------------------
def test_quick_start_installs_the_input_gate():
    readme = doc("README.md")
    block = readme[readme.index("## Quick start"):readme.index("## Validators")]
    assert block.index("pipx inject genomde2fhir") < block.index("genomde2fhir convert")
    assert io.VALIDATOR_REQ in block and "--no-input-check" in block      # same requirement as the CLI hint
    plan = doc("docs/PLAN-2027.md")
    row_a = next(line for line in plan.splitlines() if line.startswith("| **(a)**"))
    assert "pipx inject genomde2fhir" in row_a


def test_status_counts_match_tables():
    mapped = {b: sum(r["status"] == "MAPPED" for r in rows(f"mapping_{b}.csv").values())
              for b in ("kdk_oncology", "kdk_rarediseases", "grz")}
    status = doc("README.md").split("## Status", 1)[1]
    assert (f"oncology {mapped['kdk_oncology']} / rare disease {mapped['kdk_rarediseases']} / "
            f"GRZ {mapped['grz']} MAPPED") in status
    assert "**ERROR**" in status and "`candidate`" in status
    top = max(int(m) for m in re.findall(r"^\| (\d+) \|", doc("docs/REPRESENTATIONS.md"), re.M))
    assert f"Representation register grew to {top} entries" in doc("docs/PLAN-2027.md")


def test_capability_matrix_matches_matchbox_messages_and_rules():
    text = doc("docs/TERMINOLOGY-CAPABILITY.md")
    row = next(line for line in text.splitlines() if line.startswith("| ICD-O-3"))
    assert "is different to the one in the value" in row and "never counts" in row
    assert "An `Unknown code` message in edition 2000 is content" not in row
    consequences = text.split("Consequences:", 1)[1]
    assert "ValueSet?url=" in consequences and "content, never source" in consequences
    assert "HGVS the converter composes" in consequences
    plan = doc("docs/PLAN-2027.md")
    assert "ValueSet?url=" in plan and "type.targetProfile" in plan


def test_mtb22_comment_names_matchbox_shapes_of_the_waiver():
    text = doc("docs/BALLOT-COMMENTS-2027.md")
    mtb22 = text[text.index("#### MTB-22"):text.index("#### MTB-23")]
    assert "TumorMutionalBurden, MSI" in mtb22 and "EinfacheVariante" in mtb22 and "ohne `.result`" in mtb22
    waivers = [w for w in validate.WAIVERS if w["id"] == "mtb-ngs-bericht-result-slice-overlap"]
    assert any(w["expression"] == r"^DiagnosticReport$" for w in waivers)              # overflow at the report
    assert any("more than one slice" in w["text"] for w in waivers)                    # overlaps at result[n]
