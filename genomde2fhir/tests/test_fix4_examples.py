"""Fix round 4, group examples: the KDK example files are the mv_dummy_data revision of 2026-08-09.

- examples/{oncology,rarediseases} and example-data/{oncology,rarediseases} hold the same files (42 + 42); the 3 older RD files the revision dropped
  (423C3C2F, 42A16CA6, F11F0DB1) are gone from both.
- The revision's shape: oncology case.priorDiagnostics[] (no priorDiagnostic), rare disease without case.priorRd and
  with plan.recommended*[].variants (no variantReferences); submission type 'test'.
- corpus_manifest.json lists every one of these files, under its branch, as valid (genomde-dk-validator, non-strict).
- The legacy keys stay covered by tests/fixtures/legacy_keys/, which carry them and convert them.
"""
import json
from pathlib import Path

import pytest

from conftest import MANIFEST, REPO

DIRS = {"oncology": "oncology", "rarediseases": "rare-disease"}
LEGACY = REPO / "genomde2fhir/tests/fixtures/legacy_keys"
NEW_RD = ("147F575A22FF91A1AC1C529F73FC8645B9E88CE7CFA007AA8E6342DDD0E3AE1E",
          "3249DE06C02EC05A8CB2596777BC698D343B8A284BFEB849D59600AB7665E7A4",
          "CD9961FC3FA26A7E27F7E7B1586ED5032BC32687525E781403B7D90A2850DFA1")
DROPPED_RD = ("423C3C2F", "42A16CA6", "F11F0DB1")    # older RD files the 2026-08-09 revision no longer contains


def _files(top: str, sub: str) -> list[Path]:
    return sorted((REPO / top / sub).glob("*.json"))


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _present(sub: str) -> list[Path]:
    files = _files("examples", sub)
    if not files:
        pytest.skip(f"examples/{sub} not in this checkout")
    return files


@pytest.mark.parametrize("sub,count", [("oncology", 42), ("rarediseases", 42)])
def test_examples_and_example_data_hold_the_same_files(sub, count):
    ex = _present(sub)
    assert len(ex) == count
    data = _files("example-data", sub)
    if not data:
        pytest.skip(f"example-data/{sub} not in this checkout")
    assert [p.name for p in ex] == [p.name for p in data]
    assert all(a.read_bytes() == b.read_bytes() for a, b in zip(ex, data))


def test_the_three_new_rare_disease_files_are_present():
    names = {p.name for p in _present("rarediseases")}
    assert {f"RareDiseasesSubmission_{h}.json" for h in NEW_RD} <= names


def test_the_three_dropped_rare_disease_files_are_gone():
    for top in ("examples", "example-data"):
        names = {p.name for p in _files(top, "rarediseases")}
        assert not {n for n in names if n.split("_")[1][:8] in DROPPED_RD}, top
    listed = {x for v in MANIFEST.values() for k in v.values() for x in k
              if x.startswith(("examples/rarediseases/", "example-data/rarediseases/"))}
    assert not {x for x in listed if x.rsplit("_", 1)[1][:8] in DROPPED_RD}


def test_oncology_files_carry_prior_diagnostics_array():
    for p in _present("oncology"):
        case = _load(p)["case"]
        assert "priorDiagnostic" not in case, p.name
        assert isinstance(case["priorDiagnostics"], list) and case["priorDiagnostics"], p.name
        assert _load(p)["metaData"]["submission"]["type"] == "test"


def test_rare_disease_revision_files_use_variants_and_drop_prior_rd():
    for p in _present("rarediseases"):
        dk = _load(p)
        assert dk["metaData"]["submission"]["date"] >= "2026-08-09", p.name
        assert "priorRd" not in dk["case"], p.name
        for rec in dk["plan"].get("recommendedTherapies", []) + dk["plan"].get("recommendedStudies", []):
            assert "variantReferences" not in rec and "variants" in rec, p.name
        assert dk["metaData"]["submission"]["type"] == "test"


def test_manifest_lists_every_example_file_as_valid_under_its_branch():
    listed = {b: set(v["valid"]) for b, v in MANIFEST.items()}
    invalid = {x for v in MANIFEST.values() for x in v["invalid"]}
    for top in ("examples", "example-data"):
        for sub, branch in DIRS.items():
            for p in _files(top, sub):
                rel = p.relative_to(REPO).as_posix()
                assert rel in listed[branch] and rel not in invalid, rel
            prefix = f"{top}/{sub}/"
            stale = [x for v in MANIFEST.values() for k in v.values() for x in k
                     if x.startswith(prefix) and not (REPO / x).is_file() and (REPO / top / sub).is_dir()]
            assert not stale, stale


def test_example_files_pass_the_input_gate():
    dkv = pytest.importorskip("genomde_dk_validator")
    v = dkv.DatenkranzValidator(check_unknown=True)
    for sub, branch in DIRS.items():
        for p in _present(sub):
            dk = _load(p)
            res = v.validate(dk, p.name)
            assert dkv.classify(dk) == branch and res.ok(), (p.name, [e.message for e in res.schema_errors][:3])
            if sub == "oncology":
                assert res.ok(strict=True), p.name     # this revision declares every oncology field
            else:
                # undeclared genes[].system|display, localization[].system|display remain in RD
                assert {u.path.rsplit("/", 1)[-1] for u in res.unknown_fields} <= {"system", "display"}, p.name


def test_legacy_fixtures_carry_the_legacy_keys_and_convert_them():
    from genomde2fhir import convert
    from genomde2fhir.cli import _undeclared

    onco = _load(LEGACY / "onco_legacy_prior_diagnostic.json")
    rd = _load(LEGACY / "rd_legacy_prior_rd_variant_references.json")
    assert isinstance(onco["case"]["priorDiagnostic"], dict) and "priorDiagnostics" not in onco["case"]
    assert isinstance(rd["case"]["priorRd"], dict)
    recs = rd["plan"]["recommendedTherapies"] + rd["plan"]["recommendedStudies"]
    assert recs and all("variantReferences" in r and "variants" not in r for r in recs)

    def judged(dk, *pointers):
        _, rep = convert(dk, "x", check_input=False)
        assert rep.status == "converted", rep.error
        rep.input_findings = [f"unknown field {p}" for p in pointers]
        return [d for _, d in _undeclared(rep)]

    assert judged(onco, "/case/priorDiagnostic") == ["converted"]
    assert judged(rd, "/case/priorRd", "/plan/recommendedTherapies/0/variantReferences",
                  "/plan/recommendedStudies/0/variantReferences") == ["converted"] * 3


def test_readme_documents_the_revision():
    text = (REPO / "example-data/README.md").read_text(encoding="utf-8")
    for needle in ("2026-08-09", "priorDiagnostics[]", "variantReferences", "priorRd", "`test`",
                   "genes[].system", "localization[].system", "tests/fixtures/"):
        assert needle in text, needle
