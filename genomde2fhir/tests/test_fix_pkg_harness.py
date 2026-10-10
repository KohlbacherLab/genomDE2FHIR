"""Regression tests for the package / E2E-harness review fixes (R27, R40, R41, R44, R47, R64, R71, R72, R73).

Offline except the two matchbox-backed checks at the end (skipped unless MB2027 is set).
"""
import copy
import importlib.util
import io
import json
import os
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "mvgs-ig" / "input"
MB = os.environ.get("MB2027")
MTB_CS = "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/CodeSystem/"
FIXTURE = REPO / "genomde2fhir" / "tests" / "fixtures" / "onco_plan" / "plan_full.json"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RC = _load("run_corpus_fix", REPO / "scripts" / "run_corpus.py")


def _pkg(name):
    return json.loads((PKG / f"{name}.json").read_text())


# ---- R40 / R47: canonical() -------------------------------------------------------------------------------------
P = "https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition/"


def _graph(target="urn:uuid:a", ids=("a", "b", "m", "c")):
    """Two variants of the same profile (different content), a recommendation citing one of them, and a consent
    that nothing references."""
    a, b, m, c = (f"urn:uuid:{i}" for i in ids)
    var = lambda gene: {"resourceType": "Observation", "meta": {"profile": [P + "mii-pr-molgen-variante"]},  # noqa: E731
                        "status": "final", "component": [{"code": {"text": "gene"}, "valueString": gene}]}
    return {"resourceType": "Bundle", "type": "transaction", "entry": [
        {"fullUrl": a, "resource": dict(var("BRAF"), id=ids[0])},
        {"fullUrl": b, "resource": dict(var("KRAS"), id=ids[1])},
        {"fullUrl": m, "resource": {"resourceType": "MedicationRequest", "id": ids[2], "status": "active",
                                    "reasonReference": [{"reference": target.replace("urn:uuid:a", a)}]}},
        {"fullUrl": c, "resource": {"resourceType": "Consent", "id": ids[3], "status": "active",
                                    "meta": {"profile": ["https://example.org/p2", "https://example.org/p1"]}}}]}


def test_canonical_detects_swapped_reference_target_of_same_profile():
    """R40: rewiring the recommendation to the other variant (same profile) must change the canonical form."""
    assert RC.canonical(_graph("urn:uuid:a")) != RC.canonical(_graph("urn:uuid:b"))


def test_canonical_is_independent_of_ids_and_fullurls():
    renamed = _graph("urn:uuid:a", ids=("x1", "x2", "x3", "x4"))
    renamed["entry"][2]["resource"]["reasonReference"] = [{"reference": "urn:uuid:x1"}]
    assert RC.canonical(_graph("urn:uuid:a")) == RC.canonical(renamed)


def test_canonical_compares_own_meta_profile():
    """R47: a resource nothing references (Consent) dropping or changing its meta.profile must be visible;
    the profile order and other meta elements are not."""
    base = _graph()
    dropped = copy.deepcopy(base)
    dropped["entry"][3]["resource"].pop("meta")
    changed = copy.deepcopy(base)
    changed["entry"][3]["resource"]["meta"]["profile"] = ["https://example.org/p1"]
    reordered = copy.deepcopy(base)
    reordered["entry"][3]["resource"]["meta"] = {"profile": ["https://example.org/p1", "https://example.org/p2"],
                                                 "lastUpdated": "2026-01-01T00:00:00Z", "versionId": "3"}
    assert RC.canonical(base) != RC.canonical(dropped)
    assert RC.canonical(base) != RC.canonical(changed)
    assert RC.canonical(base) == RC.canonical(reordered)


def test_canonical_shallow_mode_for_partial_outputs():
    """deep=False (probe maps with placeholder targets): references labelled by type/profile only, own profile kept."""
    assert RC.canonical(_graph("urn:uuid:a"), deep=False) == RC.canonical(_graph("urn:uuid:b"), deep=False)
    (s,) = [k for k in RC.canonical(_graph(), deep=False) if '"MedicationRequest"' in k]
    assert json.loads(s)["reasonReference"] == [{"reference": "Observation/mii-pr-molgen-variante"}]
    dropped = _graph()
    dropped["entry"][3]["resource"].pop("meta")
    assert RC.canonical(_graph(), deep=False) != RC.canonical(dropped, deep=False)


def test_canonical_unresolved_reference_keeps_type_only():
    g = _graph()
    g["entry"][2]["resource"]["reasonReference"] = [{"reference": "Observation/123"}]
    (s,) = [k for k in RC.canonical(g) if '"MedicationRequest"' in k]
    assert json.loads(s)["reasonReference"] == [{"reference": "Observation"}]


# ---- R27: idempotency of the second ingest -----------------------------------------------------------------------
def _resp(*statuses):
    return {"resourceType": "Bundle", "entry": [{"response": {"status": s}} for s in statuses]}


def test_second_ingest_idempotent_requires_200_for_every_entry():
    b = {"entry": [{"resource": {"resourceType": "Patient"}}, {"resource": {"resourceType": "Observation"}}]}
    same = {"Patient": 1, "Observation": 5}
    assert RC.second_ingest_idempotent(b, _resp("200 OK", "200 OK"), same, same)
    assert not RC.second_ingest_idempotent(b, _resp("200 OK", "201 Created"), same, same)
    assert not RC.second_ingest_idempotent(b, _resp("200 OK"), same, same)                    # entry missing
    assert not RC.second_ingest_idempotent(b, _resp("200 OK", "200 OK"), same, {"Patient": 1, "Observation": 6})


class _FakeHapi:
    """Second transaction duplicates everything (201 Created) while the (cached) counts stay the same."""
    base = "http://hapi.invalid/fhir"

    def __init__(self):
        self.calls = 0

    def transaction(self, bundle):
        self.calls += 1
        return True, _resp(*["201 Created"] * len(bundle["entry"]))


def test_ingest_twice_detects_duplicating_second_transaction(monkeypatch):
    """R27 failure scenario: identical counts no longer mask a second ingest that creates every resource."""
    monkeypatch.setattr(RC, "count_uncached", lambda base, rtype: 42)
    b = {"entry": [{"resource": {"resourceType": "Consent"}}, {"resource": {"resourceType": "Specimen"}}]}
    hapi = _FakeHapi()
    assert RC.ingest_twice(hapi, b) == (True, False)
    assert hapi.calls == 2


class _Resp(io.BytesIO):
    status = 200


def test_count_uncached_bypasses_hapi_search_cache(monkeypatch):
    """count_uncached is Hapi.count (Cache-Control: no-cache); a failed count is -1 and never passes as idempotent."""
    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["url"], seen["cc"] = req.full_url, req.get_header("Cache-control")
        return _Resp(b'{"resourceType": "Bundle", "total": 7}')
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert RC.count_uncached("http://hapi.invalid/fhir/", "Consent") == 7
    assert seen == {"url": "http://hapi.invalid/fhir/Consent?_summary=count", "cc": "no-cache"}
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: (_ for _ in ()).throw(OSError("refused")))
    assert RC.count_uncached("http://hapi.invalid/fhir/", "Consent") == -1
    b = {"entry": [{"resource": {"resourceType": "Consent"}}]}
    assert not RC.second_ingest_idempotent(b, _resp("200 OK"), {"Consent": -1}, {"Consent": -1})


# ---- R41: gate ---------------------------------------------------------------------------------------------------
def _branch(**kw):
    d = {"valid_files": 3, "invalid_files": 2, "invalid_rejected": 2, "error_count": 0, "errors": [], "sample": 3,
         "verdicts": {"PASS": 3}, "fml_verdicts": {"PASS": 3}, "ingest": {"ok": 3, "idempotent": 3},
         "parity": {"equal": 3, "fml-ingest-ok": 3, "fml-idempotent": 3}}
    d.update(kw)
    return {"branches": {"grz": d}}


@pytest.mark.parametrize("kw, reason", [
    ({"error_count": 1}, "valid inputs not converted"),
    ({"invalid_rejected": 1}, "schema-invalid inputs not rejected"),
    ({"sample": 0, "verdicts": {}}, "no bundle converted"),
    ({"verdicts": {"PASS": 2, "FAIL": 1}}, "Python bundles with FAIL/ERROR verdict"),
    ({"verdicts": {"PASS": 2, "ERROR": 1}}, "Python bundles with FAIL/ERROR verdict"),
    ({"fml_verdicts": {"FAIL": 1}}, "FML bundles with FAIL/ERROR verdict"),
    ({"parity": {"transform-failed": 3}}, "FML $transform failures"),
    ({"parity": {"equal": 2, "different": 1}}, "FML/Python parity differences"),
    ({"ingest": {"fail": 1}}, "HAPI ingest failures"),
    ({"parity": {"fml-ingest-fail": 1}}, "HAPI ingest failures"),
    ({"ingest": {"ok": 3, "duplicated": 1}}, "non-idempotent second ingests"),
    ({"parity": {"fml-duplicated": 1}}, "non-idempotent second ingests"),
])
def test_gate_fails(kw, reason):
    out = RC.gate_failures(_branch(**kw))
    assert out and all(o.startswith("grz: ") for o in out) and any(reason in o for o in out)


def test_gate_passes_clean_run():
    assert RC.gate_failures(_branch()) == []


def _manifest(tmp_path, valid, invalid):
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"oncology": {"valid": [str(p) for p in valid], "invalid": [str(p) for p in invalid]}}))
    return m


def _run(tmp_path, manifest, *extra):
    return RC.main(["--branches", "oncology", "--no-ingest", "--manifest", str(manifest), "--out", str(tmp_path),
                    "--report", str(tmp_path / "report.md"), *extra])


def test_main_gate_exit_code_on_accepted_invalid_and_conversion_error(tmp_path):
    """R41: a valid-list input that is rejected and an invalid-list input that converts fail the gate (exit 1);
    without --gate the run still exits 0. Profile set 2026 without --matchbox-2026: no server needed."""
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    m = _manifest(tmp_path, [FIXTURE, bad], [FIXTURE])
    assert _run(tmp_path, m, "--profile-set", "2026") == 0
    assert _run(tmp_path, m, "--profile-set", "2026", "--gate") == 1
    res = json.loads((tmp_path / "results.json").read_text())
    assert any("1 valid inputs not converted" in g for g in res["gate"])
    assert any("1 schema-invalid inputs not rejected" in g for g in res["gate"])
    assert "Gate: **failed**" in (tmp_path / "report.md").read_text()


def test_main_gate_passes(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    assert _run(tmp_path, _manifest(tmp_path, [FIXTURE], [bad]), "--profile-set", "2026", "--gate") == 0


# ---- R44: profile set 2026 is not validated against matchbox-2027 ------------------------------------------------
def test_profile_set_2026_not_validated_without_own_matchbox(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("2026 output must not be validated/transformed on matchbox-2027")
    monkeypatch.setattr(RC, "validate_bundle", boom)
    monkeypatch.setattr(RC.Matchbox, "transform", boom)
    reports = []
    monkeypatch.setattr(RC, "write_report", lambda res, path: reports.append(path))
    m = _manifest(tmp_path, [FIXTURE], [])
    assert RC.main(["--branches", "oncology", "--no-ingest", "--manifest", str(m), "--out", str(tmp_path),
                    "--profile-set", "2026", "--fml"]) == 0
    res = json.loads((tmp_path / "results.json").read_text())
    assert res["validated"] is False and res["matchbox"] is None
    assert res["branches"]["oncology"]["verdicts"] == {} and res["branches"]["oncology"]["parity"] == {}
    assert res["fml"].startswith("not applicable")
    assert reports == [REPO / "docs" / "E2E-REPORT-2026.md"]          # no longer overwrites the 2027 report


def test_profile_set_2026_validated_on_given_matchbox(tmp_path, monkeypatch):
    used = []
    monkeypatch.setattr(RC, "validate_bundle", lambda b, mb, source=None: used.append(mb.base) or
                        {"verdict": "PASS", "resources": []})
    m = _manifest(tmp_path, [FIXTURE], [])
    assert _run(tmp_path, m, "--profile-set", "2026", "--matchbox-2026", "http://mb2026.invalid/fhir/") == 0
    res = json.loads((tmp_path / "results.json").read_text())
    assert used == ["http://mb2026.invalid/fhir"] and res["validated"] is True
    assert res["branches"]["oncology"]["verdicts"] == {"PASS": 1}
    assert "Not validated" not in (tmp_path / "report.md").read_text()


def test_report_marks_2026_not_validated(tmp_path):
    m = _manifest(tmp_path, [FIXTURE], [])
    _run(tmp_path, m, "--profile-set", "2026")
    txt = (tmp_path / "report.md").read_text()
    assert "**Not validated**" in txt and "| verdicts | not validated |" in txt


# ---- R64: missing manifest files ---------------------------------------------------------------------------------
def test_missing_manifest_files_are_skipped_and_counted(tmp_path):
    gone = tmp_path / "example-data-not-in-checkout.json"
    m = _manifest(tmp_path, [FIXTURE, gone], [gone, gone])
    assert _run(tmp_path, m, "--profile-set", "2026", "--gate") == 0
    d = json.loads((tmp_path / "results.json").read_text())["branches"]["oncology"]
    assert d["missing_files"] == {"valid": 1, "invalid": 2}
    assert (d["valid_files"], d["invalid_files"], d["conversion"]) == (1, 0, {"converted": 1})


def test_nightly_workflow_uses_gate():
    wf = (REPO / ".github" / "workflows" / "genomde2fhir-validation.yml").read_text()
    assert "scripts/run_corpus.py" in wf and "--gate" in wf


# ---- R71: mvgs-ex-evidence-level enforces Evidenzgrad 1..1 + Zusatzverweis 0..* ----------------------------------
def test_evidence_level_extension_slices_coding_by_system():
    els = {e["id"]: e for e in _pkg("StructureDefinition-mvgs-ex-evidence-level")["differential"]["element"]}
    sl = els["Extension.value[x].coding"]["slicing"]
    assert sl["discriminator"] == [{"type": "value", "path": "system"}]
    assert (els["Extension.value[x].coding:Evidenzgrad"]["min"], els["Extension.value[x].coding:Evidenzgrad"]["max"]) == (1, "1")
    assert (els["Extension.value[x].coding:Zusatzverweis"]["min"], els["Extension.value[x].coding:Zusatzverweis"]["max"]) == (0, "*")
    assert els["Extension.value[x].coding:Evidenzgrad.system"]["patternUri"] == MTB_CS + "mii-cs-mtb-empfehlung-evidenzgrad"
    assert els["Extension.value[x].coding:Zusatzverweis.system"]["patternUri"] == \
        MTB_CS + "mii-cs-mtb-empfehlung-evidenzgrad-zusatzverweis"


# ---- R72: splicingRegion -> SO:0001630 is narrower, not equivalent -----------------------------------------------
def test_rd_localization_splicing_region_is_narrower():
    cm = _pkg("ConceptMap-mvgs-cm-rd-localization-so")
    (t,) = [t for g in cm["group"] for e in g["element"] if e["code"] == "splicingRegion" for t in e["target"]]
    assert t["code"] == "SO:0001630" and t["equivalence"] == "narrower"
    assert "SO:0001629" in t.get("comment", "")      # R4: the sense of 'narrower' SHALL be described


# ---- R73: package CodeSystems are valid ----------------------------------------------------------------------------
HL7_CONCEPT_PROPERTIES = {"inactive", "deprecated", "notSelectable", "parent", "child"}     # R4 concept-properties


def test_codesystem_properties_not_in_undefined_hl7_namespace():
    for f in sorted(PKG.glob("CodeSystem-*.json")):
        for p in json.loads(f.read_text()).get("property", []):
            uri = p.get("uri", "")
            if uri.startswith("http://hl7.org/fhir/concept-properties#"):
                assert uri.split("#")[1] in HL7_CONCEPT_PROPERTIES, f"{f.name}: {uri}"


def test_codesystem_valueset_is_an_all_codes_value_set():
    """CodeSystem.valueSet must be a value set of the entire code system (no concept list, no filter)."""
    vs = {json.loads(f.read_text())["url"]: json.loads(f.read_text()) for f in PKG.glob("ValueSet-*.json")}
    for f in sorted(PKG.glob("CodeSystem-*.json")):
        cs = json.loads(f.read_text())
        if "valueSet" not in cs:
            continue
        inc = vs[cs["valueSet"]]["compose"]["include"]
        assert [i for i in inc if i.get("system") == cs["url"]], f.name
        assert all(set(i) <= {"system", "version"} for i in inc if i.get("system") == cs["url"]), f.name
        assert "exclude" not in vs[cs["valueSet"]]["compose"], f.name


# ---- matchbox-backed (MB2027) ------------------------------------------------------------------------------------
needs_mb = pytest.mark.skipif(not MB, reason="MB2027 (matchbox-2027 base URL) not set")


@needs_mb
def test_package_conformance_resources_validate_on_matchbox():
    """R73: every de.genomde.mvgs conformance resource validates against its base resource definition."""
    from genomde2fhir.validate import Matchbox
    mb, bad = Matchbox(MB), {}
    for f in sorted(PKG.glob("*.json")):
        r = json.loads(f.read_text())
        oo = mb.validate(r, f"http://hl7.org/fhir/StructureDefinition/{r['resourceType']}")
        errs = [i.get("diagnostics", "") for i in oo.get("issue", []) if i.get("severity") in ("error", "fatal")]
        if errs:
            bad[f.name] = errs
    assert not bad, bad


@needs_mb
def test_evidence_level_extension_rejects_missing_or_double_grade_on_matchbox():
    """R71 on the installed package (python3 scripts/build_mvgs.py --install ... --only StructureDefinition)."""
    from genomde2fhir.validate import Matchbox
    url = "https://genomde.de/fhir/StructureDefinition/mvgs-ex-evidence-level"
    sr = {"resourceType": "ServiceRequest", "status": "draft", "intent": "proposal",
          "subject": {"reference": "Patient/p"}, "extension": [{"url": url, "valueCodeableConcept": {}}]}
    grade = {"system": MTB_CS + "mii-cs-mtb-empfehlung-evidenzgrad", "code": "m1A"}
    z = {"system": MTB_CS + "mii-cs-mtb-empfehlung-evidenzgrad-zusatzverweis", "code": "Z"}
    mb = Matchbox(MB)

    def errors(codings):
        s = copy.deepcopy(sr)
        s["extension"][0]["valueCodeableConcept"] = {"coding": codings}
        oo = mb.validate(s)
        return [i.get("diagnostics", "") for i in oo.get("issue", [])
                if i.get("severity") in ("error", "fatal") and "Evidenzgrad" in i.get("diagnostics", "")]
    assert errors([grade, z]) == []
    assert errors([z])
    assert errors([grade, dict(grade, code="m3")])
