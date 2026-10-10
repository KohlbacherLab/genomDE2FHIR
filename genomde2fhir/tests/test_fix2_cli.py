"""Regression tests for the second fix round of the CLI findings R13 (sanitised output names), R31 (validator
install remedy, report wording) and R36 (undeclared fields judged by the report's dispositions).

Inputs are small variants of the tracked GRZ example written to tmp_path; everything runs offline."""
import importlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

from genomde2fhir import io as gio
from genomde2fhir.cli import _out_name, _pointer_path, _undeclared, main
from genomde2fhir.io import discover
from genomde2fhir.report import Report

cli = importlib.import_module("genomde2fhir.cli")
REPO = Path(__file__).resolve().parents[2]
GRZ = REPO / "examples/grz/grz-paired-rd-01.json"


def grz(**sub) -> dict:
    dk = json.loads(GRZ.read_text(encoding="utf-8"))
    dk.pop("_paired_with", None)
    dk["submission"].update(sub)
    return dk


def write(path: Path, dk) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dk, indent=1), encoding="utf-8")
    return path


def run(capsys, *argv) -> tuple[int, str]:
    rc = main([str(x) for x in argv])
    return rc, capsys.readouterr().err


# ---- R13: a '..' or hidden parent / name never gives a hidden bundle --------------------------------------------
def test_out_name_never_hidden():
    taken = set()
    names = [_out_name(n, taken) for n in ("w/case.json", "w/../case.json", ".cfg/case.json", "d/.case.json",
                                           ".arc.zip!case.json", "x.zip!../case.json")]
    assert names == ["case.bundle.json", "case-2.bundle.json", "cfg_case.bundle.json", "d_case.bundle.json",
                     "arc_case.bundle.json", "case-3.bundle.json"]
    assert _out_name("e/.json", set()) == "json.bundle.json" and _out_name("d/...", set()) == "input.bundle.json"


def test_dotdot_and_hidden_inputs_all_reach_validate(tmp_path, capsys):
    """The round-1 defect: `convert case.json ../case.json` wrote '.._case.bundle.json', which `validate out/` and
    out/*.bundle.json skip."""
    w = tmp_path / "w"
    files = [write(w / "case.json", grz(localCaseId="c1")), write(tmp_path / "case.json", grz(localCaseId="c2")),
             write(tmp_path / ".cfg/case.json", grz(localCaseId="c3")), write(w / ".case.json", grz(localCaseId="c4"))]
    with zipfile.ZipFile(tmp_path / ".arc.zip", "w") as z:
        z.writestr("case.json", json.dumps(grz(localCaseId="c5")))
    args = [files[0], f"{w}/../case.json", files[2], files[3], tmp_path / ".arc.zip"]
    rc, err = run(capsys, "convert", *args, "-o", tmp_path / "out", "--no-input-check")
    assert rc == 0
    names = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert len(names) == 5 and not [n for n in names if n.startswith(".")], names
    assert len(discover([tmp_path / "out"])) == 5            # validate out/ sees every bundle
    assert len({json.loads(p.read_text())["entry"][0]["fullUrl"] for p in (tmp_path / "out").iterdir()}) == 5


# ---- R31: the refusal names a remedy for pipx and for pip installs; report wording ----------------------------
def test_refusal_names_pipx_and_pip_remedies(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(gio, "DatenkranzValidator", None)
    gio._validator.cache_clear()
    try:
        f = write(tmp_path / "x.json", grz())
        rc, err = run(capsys, "convert", f, "-o", tmp_path / "out", "--report", tmp_path / "r.json")
        assert rc == 1 and "--no-input-check" in err
        assert f'pipx inject genomde2fhir "{gio.VALIDATOR_REQ}"' in err      # a pipx venv has no pip
        assert f'-m pip install "{gio.VALIDATOR_REQ}"' in err and sys.executable in err
        assert not (tmp_path / "out").exists() and not (tmp_path / "r.json").exists()
        ok, findings = gio.validate_input(grz(), "x.json")               # the library's skip note
        assert ok and "pipx inject genomde2fhir" in findings[0] and "genomde2fhir[input]" not in findings[0]
    finally:
        gio._validator.cache_clear()
    assert "every case" not in cli.__doc__ and "no input found" in cli.__doc__
    readme = (REPO / "genomde2fhir/README.md").read_text(encoding="utf-8")
    assert f'pipx inject genomde2fhir "{gio.VALIDATOR_REQ}"' in readme


# ---- R36: undeclared fields are 'not converted' only when no builder handled the path --------------------------
def test_pointer_path():
    assert _pointer_path("/case/diagnosisOd/germlineDiagnoses/0/date") == "case.diagnosisOd.germlineDiagnoses[].date"
    assert _pointer_path("/molecular/smallVariants/12/genes/0/system") == "molecular.smallVariants[].genes[].system"
    assert _pointer_path("/a~1b/c~0d") == "a/b.c~d"


def _rep(*pointers, status="converted", covered=(), preserved=(), dropped=()) -> Report:
    return Report(file="x", status=status, input_findings=["/x: schema note"] + [f"unknown field {p}" for p in pointers],
                  covered=set(covered), preserved=set(preserved), dropped=[(p, "v", "why") for p in dropped])


def test_undeclared_dispositions():
    r = _rep("/case/diagnosisOd/germlineDiagnoses/0/date", "/case/priorRd", "/case/note", "/plan/x/1/legacy",
             "/case/diagnosisOd/clinicallyImportantNote",
             covered={"case.diagnosisOd.germlineDiagnoses[].date", "case.priorRds[].diagnosticDate", "case.diagnosisOd"},
             preserved={"case.note.text"}, dropped={"plan.x[].legacy"})
    assert _undeclared(r) == [("/case/diagnosisOd/germlineDiagnoses/0/date", "converted"),
                              ("/case/priorRd", "not converted"),           # priorRds[] is another field
                              ("/case/note", "converted"),                 # a path below it is preserved
                              ("/plan/x/1/legacy", "dropped"),
                              ("/case/diagnosisOd/clinicallyImportantNote", "not converted")]   # parent covered only
    rejected = _rep("/case/a", status="rejected", covered={"case.a"})
    assert _undeclared(rejected) == [("/case/a", "not converted")]


def test_undeclared_warnings_follow_dispositions(tmp_path, capsys, monkeypatch):
    pytest.importorskip("genomde_dk_validator")
    real = cli.convert

    def convert(dk, name, *a, **kw):   # a builder that uses one of the two undeclared fields
        bundle, rep = real(dk, name, *a, **kw)
        rep.covered.add("submission.usedExtra")
        return bundle, rep
    monkeypatch.setattr(cli, "convert", convert)
    dk = grz()
    dk["submission"].update(usedExtra="u", lostExtra="l")
    f = write(tmp_path / "x.json", dk)
    rep = tmp_path / "rep.json"
    rc, err = run(capsys, "convert", f, "-o", tmp_path / "out", "--report", rep)
    assert rc == 0 and "2 input field(s) not declared in the schema, in 1 file(s): 1 converted, 1 not converted" in err
    w = {x["path"]: x["message"] for x in json.loads(rep.read_text())["files"][0]["warnings"]}
    assert w["/submission/usedExtra"] == "field not declared in the input schema: converted"
    assert w["/submission/lostExtra"] == "field not declared in the input schema: not converted"
    # --strict rejects every undeclared field (schema-strict); the error says what would have been converted
    rc, err = run(capsys, "convert", f, "-o", tmp_path / "out2", "--report", rep, "--strict")
    file = json.loads(rep.read_text())["files"][0]
    assert rc == 1 and file["status"] == "rejected" and not (tmp_path / "out2/x.bundle.json").exists()
    assert "1 converted, 1 dropped or not converted" in file["error"]
    assert {x["message"] for x in file["warnings"] if x["path"].startswith("/submission/")} == \
        {"field not declared in the input schema: not converted"}
    assert "1 file(s) rejected for them (--strict)" in err


def test_strict_suffix_only_for_files_rejected_for_undeclared_fields(tmp_path, capsys):
    pytest.importorskip("genomde_dk_validator")
    dk = grz()
    dk["submission"]["extraField"] = "x"
    del dk["donors"][0]["researchConsents"][0]["presentationDate"]     # schema-invalid as well
    f = write(tmp_path / "x.json", dk)
    rc, err = run(capsys, "convert", f, "--strict")
    assert rc == 1 and "1 not converted" in err and "rejected for them" not in err
