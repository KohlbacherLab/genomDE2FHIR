"""Regression tests for the cross-group handoffs applied at integration (R14 R33 R39 R42 R44 R63 R70 R27 R47).

Offline: matchbox and HAPI are fakes or a closed local port (127.0.0.1:1)."""
import importlib.util
import io
import json
import types
import urllib.request
from pathlib import Path

import pytest

from genomde2fhir import validate as gval
from genomde2fhir.bundle import dangling_references
from genomde2fhir.builders.common import scoped_id
from genomde2fhir.cli import main
from genomde2fhir.convert import convert_file
from genomde2fhir.identity import CaseKey
from genomde2fhir.io import Num, dumps, loads

REPO = Path(__file__).resolve().parents[2]
GRZ = REPO / "examples/grz/grz-paired-rd-01.json"
GRZ_QC = Path(__file__).parent / "fixtures/grz_labdata/grz-labdata-onco-edge.json"
FIXTURE = REPO / "genomde2fhir" / "tests" / "fixtures" / "onco_plan" / "plan_full.json"
KDS = "de.medizininformatikinitiative.kerndatensatz."


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RC = _load("run_corpus_integ", REPO / "scripts" / "run_corpus.py")


def grz(**sub) -> dict:
    dk = json.loads(GRZ.read_text(encoding="utf-8"))
    dk.pop("_paired_with", None)
    dk["submission"].update(sub)
    return dk


def write(path: Path, dk) -> Path:
    path.write_text(dk if isinstance(dk, str) else json.dumps(dk, indent=1), encoding="utf-8")
    return path


def run(capsys, *argv):
    rc = main([str(x) for x in argv])
    return rc, capsys.readouterr().err


class _Resp(io.BytesIO):
    status = 200


# ---- R44: convert --validate checks that matchbox holds the KDS packages of --profile-set -----------------------
@pytest.mark.parametrize("ps, held, validated", [
    ("2026", {KDS + "mtb": {"2027.0.0-ballot.1"}, KDS + "base": {"2027.0.0-ballot"}}, False),   # matchbox-2027
    ("2026", None, False),                                                                       # cannot tell
    ("2026", {KDS + "mtb": {"2026.0.1"}, KDS + "person": {"2025.0.1"}}, True),                   # 2026 stack
    ("2026", {KDS + "mtb": {"2026.0.1", "2027.0.0-ballot.1"}}, False),                           # mixed: ambiguous
    ("2027", {KDS + "mtb": {"2027.0.0-ballot.1"}}, True),
    ("2027", None, True),                                  # the documented matchbox-2027; no answer -> validate_bundle
    ("2027", {KDS + "mtb": {"2026.0.1"}}, False),
])
def test_validate_refuses_matchbox_of_other_profile_set(tmp_path, capsys, monkeypatch, ps, held, validated):
    calls = []
    monkeypatch.setattr(gval.Matchbox, "packages", lambda self, prefix=KDS: held)
    monkeypatch.setattr(gval, "validate_bundle",
                        lambda b, mb, bundle_level=True, source=None: calls.append(1) or {"verdict": "PASS", "resources": []})
    f = write(tmp_path / "x.json", grz())
    rep = tmp_path / "rep.json"
    rc, err = run(capsys, "convert", f, "--profile-set", ps, "--validate", "http://mb.test/fhir", "--no-input-check",
                  "--report", rep)
    v = json.loads(rep.read_text())["validation"][str(f)]["validation"]
    if validated:
        assert rc == 0 and calls == [1] and v["verdict"] == "PASS"
    else:
        assert rc == 3 and calls == [] and v["verdict"] == "ERROR" and "not validated" in err
        assert f"not {ps}" in v["error"] or "cannot tell" in v["error"]


def test_matchbox_packages_lists_kds_versions(monkeypatch):
    seen = {}
    body = {"resourceType": "Bundle", "entry": [
        {"resource": {"resourceType": "ImplementationGuide", "packageId": KDS + "mtb", "version": "2027.0.0-ballot.1"}},
        {"resource": {"resourceType": "ImplementationGuide", "packageId": KDS + "mtb", "version": "2026.0.1"}},
        {"resource": {"resourceType": "ImplementationGuide", "packageId": "hl7.fhir.r4.core", "version": "4.0.1"}}]}

    def fake(req, timeout=None):
        seen["url"] = req.full_url
        return _Resp(json.dumps(body).encode())
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    assert gval.Matchbox("http://mb.test/fhir/").packages() == {KDS + "mtb": {"2027.0.0-ballot.1", "2026.0.1"}}
    assert seen["url"].startswith("http://mb.test/fhir/ImplementationGuide?")
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: _Resp(b'{"resourceType": "OperationOutcome"}'))
    assert gval.Matchbox("http://mb.test/fhir").packages() is None              # not matchbox / cannot tell


# ---- R33: a not-ok ingest answer that is not 'unreachable' is a failure, not a 'server down' -----------------------
def test_ingest_http_error_is_failure_and_report_written(tmp_path, capsys, monkeypatch):
    class FakeHapi:
        def __init__(self, base):
            pass

        def transaction(self, b):
            return False, {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "diagnostics": "HTTP 422"}]}
    monkeypatch.setattr(gval, "Hapi", FakeHapi)
    rep = tmp_path / "rep.json"
    rc, err = run(capsys, "convert", write(tmp_path / "x.json", grz()), write(tmp_path / "y.json", grz(localCaseId="y")),
                  "--ingest", "http://fhir.test/fhir", "--no-input-check", "--report", rep)
    assert rc == 3 and "unreachable" not in err and "ingest ok=0 failed=2" in err
    assert all(v["ingest"] != "ok" and "skipped" not in v["ingest"]
               for v in json.loads(rep.read_text())["validation"].values())   # both were sent


# ---- R42: the stderr summary line names submission types, test submissions and TAN-fallback case keys -------------
def test_summary_line_lists_submission_types_and_test_count(tmp_path, capsys):
    rc, err = run(capsys, "convert", write(tmp_path / "a.json", grz(submissionType="test")),
                  write(tmp_path / "b.json", grz(localCaseId="b")), "--no-input-check")
    assert rc == 0
    line = err.splitlines()[0]
    assert "test=1" in line and "tan-fallback=0" in line and "types={" in line and "'test': 1" in line


# ---- R70: library convert_file and the HTTP client keep decimal spelling --------------------------------------------
def test_convert_file_keeps_decimal_precision(tmp_path):
    text = GRZ_QC.read_text(encoding="utf-8").replace('"count": 35.5', '"count": 58.50', 1)
    bundle, rep = convert_file(write(tmp_path / "grz.json", text), check_input=False)
    assert rep.status == "converted" and '"value": 58.50' in dumps(bundle)


def test_http_writes_and_reads_num_spelling(monkeypatch):
    seen = {}

    def fake(req, timeout=None):
        seen["data"] = req.data
        return _Resp(b'{"resourceType": "Bundle", "entry": [{"resource": {"valueQuantity": {"value": 58.50}}}]}')
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    st, out = gval.Matchbox("http://mb.test/fhir").transform({"count": Num("58.50"), "name": "Müller"}, "http://m")
    assert b'"count": 58.50' in seen["data"] and "Müller".encode() in seen["data"]
    v = out["entry"][0]["resource"]["valueQuantity"]["value"]
    assert st == 200 and isinstance(v, Num) and v.text == "58.50"


def test_canonical_sees_decimal_precision():
    def b(value):
        return {"entry": [{"fullUrl": "urn:uuid:1", "resource": {"resourceType": "Observation", "id": "1",
                                                                 "valueQuantity": {"value": value, "unit": "%"}}}]}
    assert RC.canonical(b(loads("58.50"))) != RC.canonical(b(loads("58.5")))    # FML 58.50 vs Python 58.5
    assert RC.canonical(b(loads("58.5"))) == RC.canonical(b(58.5))               # parsed vs computed float
    assert RC.canonical(b(loads("58.50"))) == RC.canonical(b(loads("58.50")))
    [s] = RC.canonical(b(loads("58.50")))
    assert json.loads(s)["valueQuantity"] == {"unit": "%", "value": 58.5}       # still valid JSON


# ---- R63: scoped_id escapes the submitter id and the source id ------------------------------------------------------
def test_scoped_id_escapes_components():
    ctx = types.SimpleNamespace(key=CaseKey("kdk", "LE|1", "case\\|x", True, "tan", "initial", "2025-01-01"))
    a = scoped_id(ctx, "http://sid", "v|1")
    assert a == {"system": "http://sid", "value": "LE\\|1|case\\|x|v\\|1"}
    # two different (submitter, source id) splits no longer give the same value
    other = types.SimpleNamespace(key=CaseKey("kdk", "LE", "1", True, "tan", "initial", "2025-01-01"))
    assert scoped_id(other, "http://sid", "case|x|v|1")["value"] != a["value"]
    assert scoped_id(ctx, "http://sid", "") is None


# ---- R39 hardening: '#id' references must resolve to a contained resource of the same entry -------------------------
def test_dangling_references_checks_contained():
    res = {"resourceType": "Consent", "id": "c", "contained": [{"resourceType": "Organization", "id": "org"}],
           "performer": [{"reference": "#org"}], "sourceReference": {"reference": "#qr"},
           "policyRule": {"text": "x"}, "extension": [{"valueReference": {"reference": "#"}}]}
    out = dangling_references({"entry": [{"fullUrl": "urn:uuid:c", "resource": res}]})
    assert out == ["Consent/c: #qr"]


# ---- R33 / run_corpus: an unreachable matchbox is counted as ERROR and the remaining bundles are not sent ------------
def test_run_corpus_stops_validating_after_unreachable(tmp_path, monkeypatch):
    calls = []

    def down(b, mb, source=None):
        calls.append(1)
        return {"verdict": "ERROR", "error": "no response", "unreachable": True, "resources": []}
    monkeypatch.setattr(RC, "validate_bundle", down)
    m = tmp_path / "manifest.json"
    second = write(tmp_path / "second.json", FIXTURE.read_text(encoding="utf-8"))
    m.write_text(json.dumps({"oncology": {"valid": [str(FIXTURE), str(second)], "invalid": []}}))
    rc = RC.main(["--branches", "oncology", "--no-ingest", "--manifest", str(m), "--out", str(tmp_path),
                  "--report", str(tmp_path / "r.md"), "--profile-set", "2026", "--matchbox-2026", "http://mb.invalid/fhir",
                  "--gate"])
    d = json.loads((tmp_path / "results.json").read_text())
    assert calls == [1] and d["branches"]["oncology"]["verdicts"] == {"ERROR": 2} and rc == 1
    report = (tmp_path / "r.md").read_text()
    assert "**ERROR**" in report and "candidate" in report
