"""Fix round 4, group docs: the documentation and the mapping-table notes describe the current behaviour.

- R43: meta.source is 'urn:genomde2fhir:submission:<submitterId>:<caseId>:<date>:<type>' (':'-joined, percent-encoded
  components) in every doc and mapping row; the old '|'-joined form is gone; the package copy of the CSVs is in sync.
- DOCS (round 3 residual): the IDENTITY.md bullet on follow-up therapies states the equal-substance-set rule of
  onco.followup._FollowUp.therapy_ids (no "part sharing most substances").
- TD-question skeptics: dated updates in DISCUSS-TD (#11 #12 #15 #18 #27 #29 #35, cross-cutting Q2); CSV notes no longer
  credit Thomas with our conclusions (consent 'DRAFT', TNM 'SNOMED edition'); the proteinChange rows do not let an
  Ensembl transcript qualify a p. expression; one RefSeq wording for prior and current transcripts; the 'preferred
  codings' of additionalClassification corrected; BALLOT MTB-9 (translocation verified, gene_fusion proposal withdrawn)
  and MTB-10 (conclusion-string exists).
- Mapping rows describe the legacy case.priorDiagnostic and the undeclared germlineDiagnoses[].date conversion.
- R17 limitation in validate.py and TERMINOLOGY-CAPABILITY.md; --strict rejection of the rare-disease examples in both
  READMEs (checked against the CLI when genomde-dk-validator is installed); PLAN-2027 section 11 after round 4.
Offline; no server."""
import csv
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO

from genomde2fhir import validate
from genomde2fhir.builders import submission
from genomde2fhir.builders.onco import molecular_variants
from genomde2fhir.identity import case_key

DOCS = REPO / "docs"
MAP = REPO / "mapping"
PKG = REPO / "genomde2fhir/src/genomde2fhir/data/mapping"
CSVS = ("mapping_kdk_oncology.csv", "mapping_kdk_rarediseases.csv", "mapping_grz.csv")
NEW_FORM = "urn:genomde2fhir:submission:<submitterId>:<caseId>:<date>:<type>"
OLD_FORM = re.compile(r"urn:genomde2fhir:submission:<submitterId>\\?\|")


def text(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def rows(name: str) -> dict:
    with open(MAP / name, newline="", encoding="utf-8") as fh:
        return {r["path"]: r for r in csv.DictReader(fh)}


# ---- R43: meta.source format ------------------------------------------------------------------------------------------
DOC_FILES = sorted(p for p in DOCS.glob("*.md") if not p.name.startswith("QUESTIONS-TD")) + [
    REPO / "README.md", REPO / "genomde2fhir/README.md"]


@pytest.mark.parametrize("path", DOC_FILES + [MAP / n for n in CSVS], ids=lambda p: p.name)
def test_no_old_meta_source_form(path):
    assert not OLD_FORM.search(path.read_text(encoding="utf-8")), f"{path.name}: old '|'-joined meta.source form"


def test_representations_and_plan_show_current_form():
    rep = text("docs/REPRESENTATIONS.md")
    line = next(x for x in rep.splitlines() if x.startswith("| 54 |"))
    assert NEW_FORM in line and "identity.source_component" in line
    assert NEW_FORM in text("docs/PLAN-2027.md")


def test_mapping_rows_show_current_form_and_package_copy_in_sync():
    for name, paths in (("mapping_kdk_oncology.csv", ("metaData.submission.date", "metaData.submission.type")),
                        ("mapping_kdk_rarediseases.csv", ("metaData.submission.date", "metaData.submission.type")),
                        ("mapping_grz.csv", ("submission.submissionDate", "submission.submissionType"))):
        r = rows(name)
        for p in paths:
            assert NEW_FORM in r[p]["transform"], (name, p)
        assert (MAP / name).read_bytes() == (PKG / name).read_bytes(), f"package copy of {name} is stale"


def test_documented_form_matches_code():
    dk = {"metaData": {"submission": {"submitterId": "260840108", "date": "2026-01-02", "type": "correction"},
                       "localCaseId": "CASE 7", "tanC": "T" * 64}}
    src = case_key(dk, "oncology").source
    assert src == "urn:genomde2fhir:submission:260840108:CASE%207:2026-01-02:correction"
    assert src.count(":") == len(NEW_FORM.split(":")) - 1


# ---- DOCS: follow-up therapy bullet -------------------------------------------------------------------------------
def test_identity_followup_bullet_states_round3_rule():
    idt = text("docs/IDENTITY.md")
    assert "sharing most substances" not in idt
    assert "_FollowUp.therapy_id`" not in idt          # the old function name
    bullet = idt[idt.index("Follow-up therapies by"):idt.index("One `Tod` Observation")]
    assert "_FollowUp.therapy_ids" in bullet and "*equal*" in bullet
    assert "Procedure of its own" in bullet and "keep their state" in bullet


# ---- DISCUSS-TD dated updates ------------------------------------------------------------------------------------------
DISCUSS = DOCS / "DISCUSS-TD-2026-10-09.md"


def _section(doc: str, n: int) -> str:
    start = doc.index(f"\n### {n}. ")
    nxt = re.search(r"\n#{2,3} ", doc[start + 5:])
    return doc[start:start + 5 + nxt.start()] if nxt else doc[start:]


@pytest.mark.parametrize("n", [11, 12, 15, 18, 27, 29, 35])
def test_discuss_sections_carry_dated_update(n):
    sec = _section(DISCUSS.read_text(encoding="utf-8"), n)
    assert "**Update 2026-10-10" in sec


def test_discuss_update_contents():
    doc = DISCUSS.read_text(encoding="utf-8")
    s11 = _section(doc, 11)
    assert "SO:0000199" in s11.split("**Update 2026-10-10")[1] and "withdrawn" in s11
    assert "is MAPPED, not BALLOT-PENDING" in _section(doc, 18)
    assert "MAPPED, not DRAFT" in _section(doc, 35) and "not Thomas'" in _section(doc, 35)
    assert "mvgs-ex-evidence-level" in _section(doc, 15).split("**Update")[1]
    assert "conclusion-string" in _section(doc, 12).split("**Update 2026-10-10")[1]
    for n in (11, 12, 15, 18, 27, 29, 35):
        assert re.search(rf"^\| {n} \|.*updated 2026-10-10 \|$", doc, re.M), n
    updated = {int(m) for m in re.findall(r"^### (\d+)\. ", doc, re.M)
               if "**Update 2026-10-10" in _section(doc, int(m))}
    marked = {int(m) for m in re.findall(r"^\| (\d+) \|.*updated 2026-10-10 \|$", doc, re.M)}
    assert updated == marked, (updated, marked)
    q2 = doc[doc.index("2. HGVS strings"):doc.index("3. Which terminology server")]
    assert "rejects bare strings" in q2


# ---- CSV attribution and HGVS rows -------------------------------------------------------------------------------------
def test_td_attribution_corrected():
    onc, rd, grz = rows(CSVS[0]), rows(CSVS[1]), rows(CSVS[2])
    tnm = onc["case.diagnosisOd.tnmClassifications[].version"]["notes"]
    assert "TD 2026-10-06: version is the SNOMED edition" not in tnm and "ours, not TD" in tnm
    consent = [onc["metaData.mvConsent.scope[].domain"]["notes"], rd["metaData.mvConsent.scope[].domain"]["notes"],
               grz["donors[].mvConsent.scope[].domain"]["notes"]]
    assert "TD: DRAFT" not in consent[1] and "MII status DRAFT" not in consent[2]
    assert "Broad-Consent policy OIDs exist but" not in consent[0]
    for n in consent:
        assert "ballot candidate Consent" in n and "TD attribution corrected" in n


def test_ensembl_never_qualifies_protein_hgvs():
    onc = rows(CSVS[0])
    for p in ("case.priorDiagnostics[].simpleVariants[].proteinChange", "molecular.smallVariants[].proteinChange"):
        assert "an Ensembl ENST transcript does not" in onc[p]["transform"], p
    # the documented rule is the code's rule
    assert not molecular_variants.QUALIFY_PREFIXES["p"][0].startswith("ENST")
    assert all(not x.startswith("ENS") for x in molecular_variants.QUALIFY_PREFIXES["p"])
    assert molecular_variants.qualify_hgvs("p.Gln61Lys", "ENST00000369535.5", "NRAS") == "p.Gln61Lys"
    assert molecular_variants.qualify_hgvs("p.Gln61Lys", "NM_002524.5", "NRAS") == "NM_002524.5(NRAS):p.Gln61Lys"


def test_refseq_wording_harmonised():
    onc = rows(CSVS[0])
    phrase = ("NM_ -> RefSeq http://www.ncbi.nlm.nih.gov/refseq (fails the MTB required binding to "
              "http://ensembl.org, reported)")
    for k in ("code", "display", "system", "version"):
        assert phrase in onc[f"case.priorDiagnostics[].simpleVariants[].transcript.{k}"]["transform"], k
        assert phrase in onc[f"molecular.smallVariants[].transcriptId.{k}"]["transform"], k


def test_legacy_prior_diagnostic_and_germline_date_described():
    onc = rows(CSVS[0])
    prior = [r for p, r in onc.items() if p.startswith("case.priorDiagnostics[]")]
    assert prior and all("legacy single-object key case.priorDiagnostic" in r["notes"] for r in prior)
    for k in ("code", "display", "system", "version"):
        tr = onc[f"case.diagnosisOd.germlineDiagnoses[].{k}"]["transform"]
        assert "undeclared item date" in tr and "condition-assertedDate" in tr and "Ctx.cover_undeclared" in tr


def test_mapping_csvs_keep_crlf_and_source_columns():
    for name in CSVS:
        raw = (MAP / name).read_bytes()
        assert raw.count(b"\n") == raw.count(b"\r\n"), name
        out = io.StringIO(newline="")
        data = list(csv.reader(io.StringIO(raw.decode("utf-8"), newline="")))
        csv.writer(out, lineterminator="\r\n").writerows(data)
        assert out.getvalue().encode("utf-8") == raw, f"{name}: not in the canonical CSV form"
        leaves = MAP / ("_leaves_" + name.removeprefix("mapping_"))
        if not leaves.is_file():     # mapping/_leaves_*.csv is git-ignored (scripts/extract_leaves.py output)
            continue
        with open(leaves, newline="", encoding="utf-8") as fh:
            src = {r["path"]: r for r in csv.DictReader(fh)}
        cols = list(next(iter(src.values())).keys())
        for p, r in rows(name).items():
            if p in src:
                assert [r[c] for c in cols] == [src[p][c] for c in cols], (name, p)


def test_review_and_issues_preferred_codings_corrected():
    for rel in ("docs/REVIEW-TD-2026-10-06.md", "docs/ISSUES-TD-2026-10-09.md"):
        t = text(rel)
        i = t.index("(+ preferred codings)")
        assert "no preferred codings are implemented" in t[i:i + 300], rel


def test_ballot_mtb9_mtb10():
    b = text("docs/BALLOT-COMMENTS-2027.md")
    mtb9 = b[b.index("#### MTB-9 "):b.index("#### MTB-10 ")]
    mtb10 = b[b.index("#### MTB-10 "):b.index("#### MTB-11 ")]
    assert "nicht verifiziert" not in mtb9 and "SO:0002072" in mtb9 and "zurückgezogen" in mtb9
    assert "gene_fusion plus den Strukturcode" not in mtb9
    assert "conclusion-string" in mtb10 and "Passend sind nur" not in mtb10


# ---- R17, --strict, submission, PLAN -----------------------------------------------------------------------------------
def test_r17_limitation_documented():
    assert "Limitation (R17)" in validate.__doc__ and "missing ConceptMap entry" in validate.__doc__
    assert "R17" in text("docs/TERMINOLOGY-CAPABILITY.md")


def test_readmes_document_strict_rejection_of_rd_examples():
    for rel in ("README.md", "genomde2fhir/README.md"):
        t = " ".join(text(rel).split())
        assert "42 rare-disease example" in t and "45 rare-disease" not in t and "localization[].system" in t, rel


@pytest.mark.skipif(shutil.which("genomde2fhir") is None and not (Path(sys.executable).parent / "genomde2fhir").exists(),
                    reason="genomde2fhir console script not installed")
def test_strict_cli_matches_readme(tmp_path):
    pytest.importorskip("genomde_dk_validator")
    exe = shutil.which("genomde2fhir") or str(Path(sys.executable).parent / "genomde2fhir")
    rd = sorted((REPO / "examples/rarediseases").glob("*.json"))
    onc = sorted((REPO / "examples/oncology").glob("*.json"))
    assert len(rd) == 42 and len(onc) == 42
    rep = tmp_path / "rep.json"
    subprocess.run([exe, "convert", str(rd[0]), str(onc[0]), "--strict", "-o", str(tmp_path / "out"),
                    "--report", str(rep)], capture_output=True, check=False, timeout=600)
    files = {Path(f["file"]).parent.name: f for f in json.loads(rep.read_text())["files"]}
    assert files["rarediseases"]["status"] == "rejected"
    found = " ".join(files["rarediseases"]["input_findings"])
    assert "/genes/0/system" in found and "/localization/0/display" in found
    assert files["oncology"]["status"] == "converted"


def test_submission_docstring_and_identity_describe_harmonised_orgs():
    assert "an absent or empty id gives none" in submission.__doc__ and "DkOrg" in submission.__doc__
    idt = text("docs/IDENTITY.md")
    assert "KDK and GRZ alike (fix round 4: `builders/submission.submission_organization`" in idt


def test_plan_section_11_after_round_4():
    plan = text("docs/PLAN-2027.md")
    sec = plan[plan.index("## 11. Implementation status"):plan.index("## Review log")]
    assert "after four review-fix rounds" in sec and "96 findings" in sec
    assert "round-2 verification pending" not in sec
    for item in ("R36-minor", "R39, accepted", "R17, accepted", "R68", "0 differences", "38 795", "132/132", "402 passed",
                 "739 passed"):
        assert item in sec, item
    assert "example-data/README.md" in sec and "example-data/README.md" in text("README.md")


# ---- closing fixes after round 4 ---------------------------------------------------------------------------------------
def test_source_component_docstring_gives_the_actual_reason():
    from genomde2fhir.identity import source_component
    doc = " ".join(source_component.__doc__.split())
    assert "':' is itself in SOURCE_ENCODED" in doc and "reversible" in doc


def test_refseq_representation_key_is_unified():
    keys = set()
    for rel in ("builders/onco/molecular_variants.py", "builders/onco/prior_diagnostics.py"):
        keys |= set(re.findall(r'ctx\.rep\("(transcript-refseq[^"]*)"\)', text(f"genomde2fhir/src/genomde2fhir/{rel}")))
    assert keys == {"transcript-refseq-vs-mtb-ensembl-binding"}
