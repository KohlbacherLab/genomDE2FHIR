"""Regression tests for fix round 3, group py_misc (residuals R31, R36, R43, SCHEMA, PLACEHOLDERS). Offline.

R31: the pip remedy of the validator refusal is quoted for the shell it is pasted into: POSIX sh quoting, on Windows
     double quotes only when needed (no shlex.quote, whose single quotes neither cmd.exe nor PowerShell accept).
R36: RD molecular.*[].genes[].display (not declared in the KDK schema) keeps the validator's 'unknown field' finding
     and is covered as a converted undeclared field, so --strict rejects it like every other undeclared field.
R43: meta.source = 'urn:genomde2fhir:submission:' + ':'-joined components (submitterId, case id, date, type), each
     percent-encoded for '%', ':', '|', '#', '?', '/', whitespace, control characters and non-ASCII: HAPI (which cuts
     meta.source at '#') keeps the whole value; the FHIRPath recipe the FML maps use gives the same string.
SCHEMA: tests/test_fix2_harness.py collects without jsonschema / referencing (they come only with the validator).
PLACEHOLDERS: German placeholder study names / ids ('unbekannt', 'k.a.', 'k. a.', 'keine angabe', 'n.a.'; trimmed,
     any case) are dropped in both careplans like 'N/A'.
"""
import copy
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

from conftest import resources

from genomde2fhir import cli
from genomde2fhir import io as gio
from genomde2fhir.builders import patient
from genomde2fhir.builders.onco import careplan as onco_careplan
from genomde2fhir.builders.rd import careplan as rd_careplan
from genomde2fhir.context import Ctx
from genomde2fhir.convert import convert
from genomde2fhir.identity import SOURCE_PREFIX, case_key, source_component

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parents[1]
FIX = TESTS / "fixtures"
ONCO = FIX / "onco_variants" / "synthetic_small_variants.json"
GRZ = FIX / "grz_labdata" / "grz-labdata-rd-duo.json"
RD_VARIANTS = FIX / "rd_variants" / "rd-variants-edge-cases.json"
ONCO_PLAN = FIX / "onco_plan" / "plan_full.json"
RD_PLAN = FIX / "rd_plan_followup" / "rd_plan_followup_all_enums.json"


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---- R31: install hint quoting --------------------------------------------------------------------------------------
def _pip_line(hint: str) -> str:
    return next(line for line in hint.splitlines() if "installed with pip:" in line).split("installed with pip:", 1)[1].strip()


def test_r31_windows_hint_uses_no_single_quotes():
    exe = r"C:\Users\me\AppData\Local\pipx\venvs\genomde2fhir\Scripts\python.exe"
    hint = gio.validator_install_hint(exe, windows=True)
    line = _pip_line(hint)
    assert "'" not in line and line == f'{exe} -m pip install "{gio.VALIDATOR_REQ}"'
    assert "PowerShell" not in hint                       # an unquoted path runs as is in cmd.exe and PowerShell
    assert f'pipx inject genomde2fhir "{gio.VALIDATOR_REQ}"' in hint


def test_r31_windows_hint_double_quotes_a_path_with_blanks():
    exe = r"C:\Users\John Doe\venv\Scripts\python.exe"
    hint = gio.validator_install_hint(exe, windows=True)
    line = _pip_line(hint)
    assert line == f'"{exe}" -m pip install "{gio.VALIDATOR_REQ}"' and "'" not in line
    assert "PowerShell: put '& ' in front" in hint        # PowerShell runs a quoted path only after the call operator


def test_r31_posix_hint_is_shell_quoted():
    exe = "/opt/venv sp/bin/python"
    line = _pip_line(gio.validator_install_hint(exe, windows=False))
    assert line.startswith("'/opt/venv sp/bin/python' -m pip install")
    assert shlex.split(line) == [exe, "-m", "pip", "install", gio.VALIDATOR_REQ]
    plain = _pip_line(gio.validator_install_hint("/usr/bin/python3", windows=False))
    assert plain == f'/usr/bin/python3 -m pip install "{gio.VALIDATOR_REQ}"'


def test_r31_default_hint_uses_this_interpreter():
    line = _pip_line(gio.validator_install_hint())
    assert sys.executable in line or shlex.quote(sys.executable) in line or \
        subprocess.list2cmdline([sys.executable]) in line


# ---- R36: genes[].display under --strict -----------------------------------------------------------------------------
def _remove(dk: dict, pointer: str):
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.strip("/").split("/")]
    node = dk
    for p in parts[:-1]:
        node = node[int(p)] if isinstance(node, list) else node[p]
    if isinstance(node, list):
        node.pop(int(parts[-1]))
    else:
        node.pop(parts[-1])


def _display_only_input(tmp_path) -> tuple[Path, int]:
    """The RD variants fixture with every undeclared field removed except genes[].display."""
    if not gio.input_check_available():
        pytest.skip("genomde-dk-validator not installed")
    dk = load(RD_VARIANTS)
    _, findings = gio.validate_input(dk, "x")
    unknown = [f[len("unknown field "):] for f in findings if f.startswith("unknown field ")]
    for ptr in sorted((p for p in unknown if not re.search(r"/genes/\d+/display$", p)), reverse=True):
        _remove(dk, ptr)
    ok, findings = gio.validate_input(dk, "x")
    displays = [f for f in findings if f.startswith("unknown field ")]
    assert ok and displays and all(re.search(r"/genes/\d+/display$", f) for f in displays)
    assert gio.validate_input(dk, "x", strict=True)[0] is False      # genomde-dk-validator --strict rejects it
    f = tmp_path / "rd_display_only.json"
    f.write_text(json.dumps(dk), encoding="utf-8")
    return f, len(displays)


def test_r36_display_keeps_its_finding_and_is_covered():
    if not gio.input_check_available():
        pytest.skip("genomde-dk-validator not installed")
    bundle, rep = convert(load(RD_VARIANTS), "rd")
    assert rep.status == "converted"
    shown = [f for f in rep.input_findings if re.search(r"^unknown field .*/genes/\d+/display$", f)]
    assert shown
    judged = dict(cli._undeclared(rep))
    assert all(judged[f[len("unknown field "):]] == "converted" for f in shown)
    assert "molecular.smallVariants[].genes[].display" in rep.covered


def test_r36_strict_rejects_a_file_whose_only_undeclared_field_is_genes_display(tmp_path, capsys):
    src, n = _display_only_input(tmp_path)
    rep_file = tmp_path / "rep.json"
    assert cli.main(["convert", str(src), "-o", str(tmp_path / "out"), "--report", str(rep_file)]) == 0
    err = capsys.readouterr().err
    assert f"{n} input field(s) not declared in the schema, in 1 file(s): {n} converted" in err
    files = json.loads(rep_file.read_text())["files"]
    assert files[0]["status"] == "converted"

    rep_file2 = tmp_path / "rep2.json"
    assert cli.main(["convert", str(src), "-o", str(tmp_path / "out2"), "--strict", "--report", str(rep_file2)]) == 1
    err = capsys.readouterr().err
    assert "1 file(s) rejected for them (--strict)" in err
    f2 = json.loads(rep_file2.read_text())["files"][0]
    assert f2["status"] == "rejected"
    assert f2["error"] == (f"--strict: {n} field(s) not declared in the input schema (without --strict: {n} converted, "
                           f"0 dropped or not converted)")
    assert not list((tmp_path / "out2").glob("*.bundle.json"))


# ---- R43: meta.source encoding ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("raw, enc", [
    ("%", "%25"), (":", "%3A"), ("|", "%7C"), ("#", "%23"), ("?", "%3F"), ("/", "%2F"),
    (" ", "%20"), ("\t", "%09"), ("\n", "%0A"), ("\x01", "%01"), ("\x7f", "%7F"),
    ("ü", "%C3%BC"), ("\u00a0", "%C2%A0"), ("€", "%E2%82%AC"), ("\U0001F600", "%F0%9F%98%80"),
    ("A-z_0.9~\\!$&'()*+,;=@[]^`{}\"<>", "A-z_0.9~\\!$&'()*+,;=@[]^`{}\"<>"),   # other printable ASCII stays
    (None, ""), ("", ""),
])
def test_r43_source_component_encoding(raw, enc):
    assert source_component(raw) == enc


def fhirpath_recipe(value: str) -> str:
    """Python model of the FHIRPath expression the FML maps use for one component (fml_changes of fix round 3):
    value.encode('hex').upper().replaceMatches('(..)', '$1 ').trim().split(' ')
         .select(iif($this.matches('^(2[1246-9A-E]|3[0-9B-E]|[4-6][0-9A-F]|7[0-9ABDE])$'), $this.decode('hex'),
                     '%' & $this)).join('')"""
    pairs = [value.encode("utf-8").hex().upper()[i:i + 2] for i in range(0, 2 * len(value.encode("utf-8")), 2)]
    keep = re.compile(r"^(2[1246-9A-E]|3[0-9B-E]|[4-6][0-9A-F]|7[0-9ABDE])$")
    return "".join(bytes.fromhex(p).decode("ascii") if keep.match(p) else "%" + p for p in pairs)


def test_r43_fhirpath_recipe_equals_python_for_every_ascii_char_and_samples():
    for c in map(chr, range(128)):
        assert fhirpath_recipe(c) == source_component(c), repr(c)
    for s in ("MTB#2026-7", "CASE 7/a|b%\\", "x\u00a0y", "Müller:ß?", "\U0001F600z", "", "  "):
        assert fhirpath_recipe(s) == source_component(s), repr(s)


def _kdk(local, stype="initial", date="2026-01-02", sub="260840108", tan="TANC1"):
    md = {"submission": {"submitterId": sub, "type": stype, "date": date}, "tanC": tan}
    if local is not None:
        md["localCaseId"] = local
    return {"metaData": md}


def _components(src: str) -> list[str]:
    assert src.startswith(SOURCE_PREFIX)
    return [unquote(p) for p in src[len(SOURCE_PREFIX):].split(":")]


@pytest.mark.parametrize("local", ["MTB#2026-7", "a:b|c", "CASE 7/a|b%\\", "x\u00a0y?z", "a%3Ab", "plain"])
def test_r43_four_components_round_trip(local):
    k = case_key(_kdk(local, "correction"), "oncology")
    src = k.source
    assert not re.search(r"[\s#|?]", src) and src.isascii()
    assert _components(src) == ["260840108", local, "2026-01-02", "correction"]


def test_r43_hash_in_local_case_id_survives_the_hapi_cut():
    """HAPI 8.4 stores meta.source cut at the first '#': the initial and the correction of 'MTB#2026-7' must still be
    stored as different values (the round-2 marker collapsed both to '...|MTB')."""
    init = case_key(_kdk("MTB#2026-7"), "oncology").source
    corr = case_key(_kdk("MTB#2026-7", "correction", "2026-03-01"), "oncology").source
    stored = {s.split("#", 1)[0] for s in (init, corr)}
    assert len(stored) == 2 and stored == {init, corr}
    assert init.endswith(":MTB%232026-7:2026-01-02:initial")


def test_r43_test_submission_and_tan_fallback():
    real, test = (case_key(_kdk("C1", t), "oncology") for t in ("initial", "test"))
    assert _components(test.source) == ["260840108", "C1", "2026-01-02", "test"]   # raw case id, no '|test'
    assert real.source != test.source and real.id("Patient") != test.id("Patient")
    tan = case_key(_kdk(None), "oncology")
    assert _components(tan.source)[1] == "TANC1"
    escaped = case_key(_kdk("a\\|b", "test"), "oncology")
    assert escaped.case_id == "a\\\\\\|b|test" and escaped.raw_case_id == "a\\|b"


def test_r43_injective_where_round_2_was_ambiguous():
    values = {case_key(_kdk(local), "oncology").source for local in ("a:b", "a%3Ab", "a%253Ab", "a|b", "a\\|b", "a b")}
    assert len(values) == 6


def test_r43_bundles_carry_the_new_marker_grz_and_kdk():
    dk = load(ONCO)
    dk["metaData"]["localCaseId"] = "MTB#7 ü"
    b, rep = convert(dk, "onc", check_input=False)
    assert rep.status == "converted"
    md = dk["metaData"]
    want = SOURCE_PREFIX + ":".join(source_component(x) for x in (
        md["submission"]["submitterId"], "MTB#7 ü", md["submission"]["date"], md["submission"]["type"]))
    assert {e["resource"]["meta"]["source"] for e in b["entry"]} == {want}
    g = load(GRZ)
    g["submission"].update(localCaseId="G#1|x", submissionType="followup", submissionDate="2026-05-01")
    b, rep = convert(g, "grz", check_input=False)
    assert rep.status == "converted"
    srcs = {e["resource"]["meta"]["source"] for e in b["entry"]}
    assert srcs == {SOURCE_PREFIX + f"{source_component(g['submission']['submitterId'])}:G%231%7Cx:2026-05-01:followup"}
    assert any(e["resource"]["resourceType"] == "Provenance" for e in b["entry"])


def test_r43_identity_doc_states_the_encoding():
    text = (REPO / "docs" / "IDENTITY.md").read_text(encoding="utf-8")
    assert "urn:genomde2fhir:submission:<submitterId>:<caseId>:<submissionDate>:<submissionType>" in text
    for token in ("`%25`", "`%3A`", "`%7C`", "`%23`", "`%3F`", "`%2F`", "`%20`", "%C3%BC"):
        assert token in text, token
    assert "<submitterId>|<caseKey>|<submissionDate>|<submissionType>" not in text


# ---- SCHEMA: test_fix2_harness collects without jsonschema / referencing -------------------------------------------
BLOCKER = '''
import sys
BLOCKED = ("jsonschema", "referencing", "genomde_dk_validator")
class Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ModuleNotFoundError(f"No module named {name!r} (blocked for the test)", name=name)
        return None
sys.meta_path.insert(0, Block())
for m in list(sys.modules):
    if m.split(".")[0] in BLOCKED:
        del sys.modules[m]
import pytest
sys.exit(pytest.main(sys.argv[1:]))
'''


def test_schema_harness_collects_without_jsonschema(tmp_path):
    runner = tmp_path / "run_blocked.py"
    runner.write_text(BLOCKER, encoding="utf-8")
    r = subprocess.run([sys.executable, str(runner), "-q", "-p", "no:cacheprovider", "-p", "no:randomly",
                        "test_fix2_harness.py", "-k", "vendored_kdk_schema_accepts or vendored_submission_schema"],
                       cwd=TESTS, capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "1 passed, 1 skipped" in out and "error" not in out.lower().replace("errors=", "")


# ---- PLACEHOLDERS: German placeholders in both careplans ---------------------------------------------------------------
GERMAN = ["unbekannt", " Unbekannt ", "k.a.", "K.A.", "k. a.", "K. A.", "keine angabe", "Keine Angabe ", "n.a.", "N.A."]


@pytest.mark.parametrize("value", GERMAN + ["N/A", "unknown", "-", "", "na"])
def test_placeholders_are_dropped_by_both_helpers(value):
    assert rd_careplan._real(value) is None and onco_careplan._real(value) is None


@pytest.mark.parametrize("value", ["KA", "k.a", "Studie unbekannter Phase", "NAVIGATOR", "keine"])
def test_real_names_are_kept(value):
    assert rd_careplan._real(value) == value and onco_careplan._real(value) == value


@pytest.mark.parametrize("value", ["Unbekannt", "k. A.", "Keine Angabe"])
def test_onco_placeholder_study_name_dropped(value):
    dk = load(ONCO_PLAN)
    dk["plan"]["recommendedStudies"] = [dict(dk["plan"]["recommendedStudies"][1], name=value)]    # DRKS study
    ctx = Ctx(dk, "oncology", case_key(dk, "oncology"), "2027")
    patient.build(ctx)
    ctx.refs["primary"] = {"reference": "urn:uuid:primary"}
    onco_careplan.build(ctx)
    studies = resources(ctx.bundle.bundle(), "ResearchStudy")
    assert len(studies) == 1 and "title" not in studies[0]
    assert ("plan.recommendedStudies[].name", value, "placeholder study name") in ctx.report.dropped


@pytest.mark.parametrize("value", ["n.a.", "K.A."])
def test_rd_placeholder_study_name_and_id_dropped(value):
    dk = load(RD_PLAN)
    studies = dk["plan"]["recommendedStudies"]
    named = next(s for s in studies if s.get("name") and s.get("register") not in (None, "yesButStudyIsUnknown")
                 and s.get("id"))
    unknown = copy.deepcopy(next(s for s in studies if s.get("register") == "yesButStudyIsUnknown"))
    named["name"] = value
    unknown.update(identifier="rdpf-study-german-placeholder", name="keine Angabe", id=" Unbekannt ")
    studies.append(unknown)
    bundle, rep = convert(dk, "rd", check_input=False)
    assert rep.status == "converted"
    assert ("plan.recommendedStudies[].name", value, "placeholder study name") in rep.dropped
    assert ("plan.recommendedStudies[].name", "keine Angabe", "placeholder study name") in rep.dropped
    assert ("plan.recommendedStudies[].id", " Unbekannt ", "placeholder study id (register yesButStudyIsUnknown)") \
        in rep.dropped
    assert not any(s.get("title") == value for s in resources(bundle, "ResearchStudy"))
    req = next(r for r in resources(bundle, "ServiceRequest", "studieneinschluss-anfrage")
               if any(i["value"].endswith("rdpf-study-german-placeholder") for i in r.get("identifier", [])))
    assert "note" not in req and "supportingInfo" not in req
