"""Regression tests for the CLI / input-discovery review findings (R12 R13 R31 R32 R34 R35 R36 R57-R61 R70).

Inputs are small variants of the tracked examples (examples/grz, examples/oncology, tests/fixtures), written to
tmp_path; matchbox and HAPI are replaced by fakes, so everything runs offline."""
import copy
import importlib
import json
import zipfile
from pathlib import Path

import pytest

from genomde2fhir import io as gio
from genomde2fhir import validate as gval
from genomde2fhir.cli import main
from genomde2fhir.io import discover, dumps, loads

REPO = Path(__file__).resolve().parents[2]
GRZ = REPO / "examples/grz/grz-paired-rd-01.json"
ONC = REPO / "examples/oncology/OncologySubmission_05728AC3075CC1AE436AE78E87976D52619F033020BB3147F575A22FF91A1AC1.json"
GRZ_QC = Path(__file__).parent / "fixtures/grz_labdata/grz-labdata-onco-edge.json"


def grz(**sub) -> dict:
    """The GRZ example without its bookkeeping field, submission fields overridden."""
    dk = json.loads(GRZ.read_text(encoding="utf-8"))
    dk.pop("_paired_with", None)
    dk["submission"].update(sub)
    return dk


def write(path: Path, dk) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dk if isinstance(dk, str) else json.dumps(dk, indent=1), encoding="utf-8")
    return path


def resources(bundle: dict, rtype: str) -> list[dict]:
    return [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == rtype]


def run(capsys, *argv) -> tuple[int, str]:
    rc = main([str(x) for x in argv])
    return rc, capsys.readouterr().err


# ---- R12: --single-bundle / --ingest apply submissions in submission order ------------------------------------
def _initial_and_correction(tmp_path, corr_date="2026-08-01", init_date="2026-04-21"):
    init = grz(submissionDate=init_date, submissionType="initial")
    corr = grz(submissionDate=corr_date, submissionType="correction")
    corr["donors"][0]["gender"] = "female"
    # file names sort the correction first: the old code merged it first, so the initial overwrote it
    write(tmp_path / "in/case-a-correction.json", corr)
    write(tmp_path / "in/case-b-initial.json", init)
    return tmp_path / "in"


def test_single_bundle_applies_correction_last(tmp_path, capsys):
    rc, _ = run(capsys, "convert", _initial_and_correction(tmp_path), "--single-bundle", tmp_path / "merged.json",
                "--no-input-check")
    assert rc == 0
    b = json.loads((tmp_path / "merged.json").read_text())
    assert [p["gender"] for p in resources(b, "Patient")] == ["female"]
    assert any("submission correction" in p["activity"]["text"] for p in resources(b, "Provenance"))


def test_single_bundle_same_date_orders_by_type(tmp_path, capsys):
    d = _initial_and_correction(tmp_path, corr_date="2026-04-21")
    rc, _ = run(capsys, "convert", d, "--single-bundle", tmp_path / "merged.json", "--no-input-check")
    assert rc == 0
    assert [p["gender"] for p in resources(json.loads((tmp_path / "merged.json").read_text()), "Patient")] == ["female"]


def test_ingest_posts_in_submission_order(tmp_path, capsys, monkeypatch):
    posted = []

    class FakeHapi:
        def __init__(self, base):
            pass

        def transaction(self, b):
            posted.append(resources(b, "Patient")[0]["gender"])
            return True, {}
    monkeypatch.setattr(gval, "Hapi", FakeHapi)
    rc, _ = run(capsys, "convert", _initial_and_correction(tmp_path), "--ingest", "http://fhir.test/fhir",
                "--no-input-check")
    assert rc == 0 and posted == ["male", "female"]


# ---- R13: -o output names never collide -----------------------------------------------------------------------
def test_output_names_do_not_collide(tmp_path, capsys):
    write(tmp_path / "a/case.json", grz(localCaseId="case-a"))
    write(tmp_path / "b/case.json", grz(localCaseId="case-b"))
    with zipfile.ZipFile(tmp_path / "z.zip", "w") as z:
        z.writestr("x/case.json", json.dumps(grz(localCaseId="case-c")))
    rc, err = run(capsys, "convert", tmp_path / "a/case.json", tmp_path / "b/case.json", tmp_path / "z.zip",
                  "-o", tmp_path / "out", "--no-input-check")
    assert rc == 0
    names = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert names == ["b_case.bundle.json", "case.bundle.json", "x_case.bundle.json"]
    cases = {json.loads(p.read_text())["entry"][0]["fullUrl"] for p in (tmp_path / "out").iterdir()}
    assert len(cases) == 3                                   # three different cases, none overwritten
    assert "2 output name clash(es)" in err and "case.json" not in err


# ---- R31: no genomde-dk-validator -> refuse unless --no-input-check -------------------------------------------
def test_convert_fails_closed_without_validator(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(gio, "DatenkranzValidator", None)
    gio._validator.cache_clear()
    try:
        f = write(tmp_path / "x.json", grz())
        rc, err = run(capsys, "convert", f, "-o", tmp_path / "out")
        assert rc == 1 and "genomde-dk-validator" in err and "--no-input-check" in err
        assert not (tmp_path / "out").exists()
        rc, _ = run(capsys, "convert", f, "-o", tmp_path / "out", "--no-input-check")
        assert rc == 0 and (tmp_path / "out/x.bundle.json").is_file()
    finally:
        gio._validator.cache_clear()


# ---- R32: --strict rejects the failing file, the batch continues, the report is written -----------------------
def test_strict_failure_rejects_file_and_continues(tmp_path, capsys, monkeypatch):
    conv = importlib.import_module("genomde2fhir.convert")   # the package attribute is the function
    bad = write(tmp_path / "in/1-bad.json", grz(localCaseId="case-bad"))
    good = write(tmp_path / "in/2-good.json", grz(localCaseId="case-good"))
    real = conv.structural_errors
    # a structural problem in the first file only: a warning normally, an exception under --strict
    monkeypatch.setattr(conv, "structural_errors",
                        lambda b: ["Patient/x: broken"] if "case-bad" in json.dumps(b) else real(b))
    monkeypatch.setattr(conv, "dangling_references", lambda b: [])
    rep = tmp_path / "rep.json"
    rc, _ = run(capsys, "convert", bad, good, "--strict", "--no-input-check", "-o", tmp_path / "out", "--report", rep)
    assert rc == 1
    files = {f["file"]: f for f in json.loads(rep.read_text())["files"]}
    assert files[str(bad)]["status"] == "rejected" and files[str(bad)]["error"].startswith("--strict: ValueError")
    assert files[str(good)]["status"] == "converted"
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["2-good.bundle.json"]


def test_strict_builder_crash_is_an_error_not_an_abort(tmp_path, capsys):
    dk = json.loads(ONC.read_text(encoding="utf-8"))
    dk["case"]["diagnosisOd"] = ["not an object"]           # crashes a builder (no input check)
    bad = write(tmp_path / "bad.json", dk)
    good = write(tmp_path / "good.json", grz())
    rep = tmp_path / "rep.json"
    rc, err = run(capsys, "convert", bad, good, "--strict", "--no-input-check", "--report", rep)
    assert rc == 2 and "Traceback" not in err
    st = {f["file"]: f["status"] for f in json.loads(rep.read_text())["files"]}
    assert st == {str(bad): "error", str(good): "converted"}


# ---- R34: convert --validate passes the input as source -------------------------------------------------------
def test_validate_gets_source(tmp_path, capsys, monkeypatch):
    seen = []

    def fake_validate(bundle, mb, bundle_level=True, source=None):
        seen.append(source)
        return {"verdict": "DATA-QUALITY", "resources": []}
    monkeypatch.setattr(gval, "validate_bundle", fake_validate)
    f = write(tmp_path / "x.json", grz())
    rc, _ = run(capsys, "convert", f, "--validate", "http://mb.test/fhir", "--no-input-check")
    assert rc == 0 and seen == [grz()]
    seen.clear()
    g = write(tmp_path / "y.json", grz(localCaseId="case-y"))
    rc, _ = run(capsys, "convert", f, g, "--single-bundle", tmp_path / "m.json", "--validate", "http://mb.test/fhir",
                "--no-input-check")
    assert rc == 0 and seen == [[grz(), grz(localCaseId="case-y")]]


def test_unreachable_server_exit_3_and_report(tmp_path, capsys):
    """Real validate.py path (no fake): nothing listens on 127.0.0.1:1, so matchbox and HAPI do not answer."""
    f = write(tmp_path / "x.json", grz())
    rep = tmp_path / "rep.json"
    rc, err = run(capsys, "convert", f, "--validate", "http://127.0.0.1:1/fhir", "--ingest", "http://127.0.0.1:1/fhir",
                  "--no-input-check", "--report", rep)
    assert rc == 3 and "matchbox unreachable" in err and "hapi unreachable" in err and "Traceback" not in err
    v = json.loads(rep.read_text())["validation"][str(f)]
    assert v["validation"]["verdict"] == "ERROR" and v["validation"]["unreachable"] is True
    assert v["ingest"] != "ok"


def test_unreachable_verdict_skips_remaining_bundles(tmp_path, capsys, monkeypatch):
    calls = []

    def fake_validate(bundle, mb, bundle_level=True, source=None):   # validate.py's ERROR verdict, no exception
        calls.append(1)
        return {"verdict": "ERROR", "error": "no response", "unreachable": True, "resources": []}
    monkeypatch.setattr(gval, "validate_bundle", fake_validate)
    rep = tmp_path / "rep.json"
    rc, err = run(capsys, "convert", write(tmp_path / "x.json", grz()), write(tmp_path / "y.json", grz(localCaseId="y")),
                  "--validate", "http://mb.test/fhir", "--no-input-check", "--report", rep)
    assert rc == 3 and calls == [1] and "matchbox unreachable" in err
    assert {v["validation"]["verdict"] for v in json.loads(rep.read_text())["validation"].values()} == {"ERROR"}


# ---- R35: no pseudonyms / TANs on stderr unless -v ------------------------------------------------------------
def test_no_identifiers_on_stderr_by_default(tmp_path, capsys):
    pytest.importorskip("genomde_dk_validator")
    tan = "835927c0b06f9bf162e75f2f874b62afcbecbd62b768267ddab3cd38f6d568bZ"
    f = write(tmp_path / f"GrzSubmission_{tan}.json", grz(tanG=tan))
    rc, err = run(capsys, "convert", f)
    assert rc == 1 and tan not in err and "1 file(s) not converted" in err
    rc, err = run(capsys, "convert", f, "-v")
    assert rc == 1 and tan in err


# ---- R36: undeclared input fields are reported, and rejected under --strict ----------------------------------
def test_undeclared_fields_reported_and_strict_rejects(tmp_path, capsys):
    pytest.importorskip("genomde_dk_validator")
    dk = grz()
    dk["submission"]["extraField"] = "x"
    f = write(tmp_path / "x.json", dk)
    rep = tmp_path / "rep.json"
    rc, err = run(capsys, "convert", f, "-o", tmp_path / "out", "--report", rep)
    assert rc == 0 and "1 input field(s) not declared" in err
    warnings = json.loads(rep.read_text())["files"][0]["warnings"]
    assert {"path": "/submission/extraField", "message": "field not declared in the input schema: not converted"} in warnings
    rc, err = run(capsys, "convert", f, "-o", tmp_path / "out2", "--report", rep, "--strict")
    assert rc == 1 and not (tmp_path / "out2").joinpath("x.bundle.json").exists()
    assert json.loads(rep.read_text())["files"][0]["status"] == "rejected"


# ---- R57 / R58: discovery ---------------------------------------------------------------------------------------
def test_literal_path_is_not_globbed_and_hits_are_deduplicated(tmp_path):
    lit = write(tmp_path / "d/case[1].json", grz(localCaseId="literal"))
    write(tmp_path / "d/case1.json", grz(localCaseId="other"))
    assert [n for n, _ in discover([lit])] == [str(lit)]
    assert len(discover([tmp_path / "d/case1.json"] * 3)) == 1
    hits = discover([str(tmp_path / "d") + "/**"])
    assert sorted(Path(n).name for n, _ in hits) == ["case1.json", "case[1].json"]


def test_directory_zip_case_and_hidden_members(tmp_path):
    d = tmp_path / "delivery"
    write(d / "CASE.JSON", grz())
    write(d / ".hidden/h.json", grz())
    with zipfile.ZipFile(d / "t.zip", "w") as z:
        for n in ("UPPER.JSON", "a/x.json", "a/._x.json", "a/.hidden/y.json", "__MACOSX/a/._x.json", "a/notes.txt"):
            z.writestr(n, json.dumps(grz()))
    names = [n.replace(str(d) + "/", "") for n, _ in discover([d])]
    assert names == ["CASE.JSON", "t.zip!UPPER.JSON", "t.zip!a/x.json"]


def test_empty_input_set_exits_1(tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    rc, err = run(capsys, "convert", tmp_path / "empty", "--no-input-check")
    assert rc == 1 and "no input files" in err


# ---- R59: coverage reports rejected / crashing inputs ---------------------------------------------------------
def test_coverage_reports_skipped_inputs(tmp_path, capsys):
    good = write(tmp_path / "good.json", grz())
    rc, err = run(capsys, "coverage", good, write(tmp_path / "nondk.json", {"foo": 1}))
    assert rc in (1, 4) and "not counted: 1 file(s) {'rejected': 1}" in err
    rc, err = run(capsys, "coverage", good, write(tmp_path / "bad.json", "{not json"))
    assert rc in (1, 4) and "Traceback" not in err and "not counted: 1 file(s)" in err


def test_coverage_builder_crash_on_valid_input_exits_2(tmp_path, capsys, monkeypatch):
    conv = importlib.import_module("genomde2fhir.convert")
    real = conv.pipeline

    def boom(ctx):
        raise RuntimeError("builder defect")
    monkeypatch.setattr(conv, "pipeline", lambda branch: list(real(branch)) + [("boom", boom)])
    rc, err = run(capsys, "coverage", write(tmp_path / "x.json", grz()))
    assert rc == 2 and "not counted: 1 file(s) {'error': 1}" in err and "Traceback" not in err


def test_coverage_crash_on_schema_invalid_input_is_rejected(tmp_path, capsys):
    pytest.importorskip("genomde_dk_validator")
    dk = json.loads(ONC.read_text(encoding="utf-8"))
    dk["case"]["diagnosisOd"] = ["not an object"]           # crashes a builder; coverage runs without the gate
    rc, err = run(capsys, "coverage", write(tmp_path / "good.json", grz()), write(tmp_path / "crash.json", dk))
    assert rc == 1 and "{'rejected': 1}" in err


def test_coverage_help_documents_exit_4(capsys):
    with pytest.raises(SystemExit):
        main(["coverage", "--help"])
    assert "4 gaps remain" in capsys.readouterr().out


# ---- R60: clean errors for missing paths, malformed JSON, non-Bundle files ------------------------------------
def test_validate_bad_inputs_clean_exit_2(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(gval, "validate_bundle", lambda *a, **k: pytest.fail("nothing to validate"))
    rep = tmp_path / "rep.json"
    rc, err = run(capsys, "validate", write(tmp_path / "bad.json", "{not json"), write(tmp_path / "dk.json", grz()),
                  tmp_path / "missing.json", "--matchbox", "http://mb.test/fhir", "--report", rep)
    assert rc == 2 and "Traceback" not in err
    res = json.loads(rep.read_text())
    assert {v["verdict"] for v in res.values()} == {"ERROR"} and len(res) == 3


def test_convert_missing_path_does_not_block_batch(tmp_path, capsys):
    good = write(tmp_path / "good.json", grz())
    rc, err = run(capsys, "convert", tmp_path / "missing.json", good, "-o", tmp_path / "out", "--no-input-check")
    assert rc == 2 and "Traceback" not in err and (tmp_path / "out/good.bundle.json").is_file()


# ---- R61: --single-bundle with no converted input writes nothing; relative FILE goes into -o -----------------
def test_single_bundle_all_rejected_writes_nothing(tmp_path, capsys):
    target = write(tmp_path / "case.json", '{"keep": true}')
    rc, err = run(capsys, "convert", write(tmp_path / "nondk.json", {"foo": 1}), "--single-bundle", target,
                  "--no-input-check")
    assert rc == 1 and json.loads(target.read_text()) == {"keep": True} and "not written" in err


def test_single_bundle_relative_path_inside_output_dir(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write(tmp_path / "x.json", grz())
    rc, _ = run(capsys, "convert", "x.json", "--single-bundle", "merged.json", "-o", "out", "--no-input-check")
    assert rc == 0 and (tmp_path / "out/merged.json").is_file() and not (tmp_path / "merged.json").exists()


# ---- R70: decimals keep their written precision -----------------------------------------------------------------
def test_decimal_precision_is_preserved(tmp_path, capsys):
    text = GRZ_QC.read_text(encoding="utf-8")
    text = text.replace('"count": 35.5', '"count": 58.50', 1).replace('"meanDepthOfCoverage": 100,',
                                                                       '"meanDepthOfCoverage": 100.10,', 1)
    text = text.replace('"minCoverage": 20,', '"minCoverage": 20.0,', 1)
    f = write(tmp_path / "grz.json", text)
    onc = write(tmp_path / "onc.json", ONC.read_text(encoding="utf-8").replace('"tmb" : 464806', '"tmb" : 12.50'))
    rep = tmp_path / "rep.json"
    rc, _ = run(capsys, "convert", f, onc, "-o", tmp_path / "out", "--no-input-check", "--report", rep)
    assert rc == 0
    g = (tmp_path / "out/grz.bundle.json").read_text()
    assert '"value": 58.50' in g and '"value": 100.10' in g
    assert "minCoverage=20x" in g                          # builder text formatting is unchanged (float semantics)
    assert '"value": 12.50' in (tmp_path / "out/onc.bundle.json").read_text()
    files = json.loads(rep.read_text())["files"]
    assert all(f["status"] == "converted" and not [w for w in f["warnings"] if w["path"] == "(structure)"]
               for f in files)                         # fhir.resources structural check passes


def test_num_round_trip():
    o = loads('{"a": 12.50, "b": [1e2, -0.0, 3], "c": "12.50"}')
    assert o["a"] == 12.5 and isinstance(o["a"], float)
    assert copy.deepcopy(o)["a"].text == "12.50"
    assert dumps(o, indent=None) == '{"a": 12.50, "b": [1e2, -0.0, 3], "c": "12.50"}'
