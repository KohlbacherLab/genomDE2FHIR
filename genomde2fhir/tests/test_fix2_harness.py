"""Regression tests for fix round 2, group harness_schema (R40, R44, SCHEMA). Offline.

R40: run_corpus.canonical() keys references by the target's content to a fixpoint (any depth, cycle-safe), so a
     reference swapped between two same-profile resources that differ only in what THEY reference is visible.
R44: run_corpus refuses a matchbox that lists the KDS packages of the other profile set (gate fails), an unvalidated
     run is labelled as such in the gate line and the report, and the report no longer counts unvalidated bundles
     as validated.
SCHEMA: schemas/kdk/Submission.json follows BfArM MVGenomseq_KDK main fe724ff (researchConsents[].schemaVersion
     2025.0.1 .. 2026.0.1); the logical models list the new versions and the consent migration accepts them.
"""
import copy
import importlib.util
import json
import random
from pathlib import Path

import pytest

from genomde2fhir.convert import convert
from genomde2fhir.io import loads

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "genomde2fhir" / "tests" / "fixtures" / "onco_plan" / "plan_full.json"
ONCO = REPO / "example-data" / "oncology"
CONSENT_EXAMPLE = ONCO / "OncologySubmission_2980C67615BFCCAC783BAB12CC54041D6D2EAE014112425D565A4F74E2860F05.json"
TWIN_THERAPIES = ONCO / "OncologySubmission_22134CADB80AE0F034B01A8473C469E591161A04C82418BF07893D9ABCC520B8.json"
NEW_CONSENT_VERSIONS = ["2025.0.1", "2025.0.2", "2025.0.3", "2025.0.4", "2026.0.0", "2026.0.1"]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RC = _load("run_corpus_fix2", REPO / "scripts" / "run_corpus.py")


# ---- R40: canonical() to a fixpoint ------------------------------------------------------------------------------
MTB = "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/"


def _res(rtype, profile, **body):
    return dict(resourceType=rtype, meta={"profile": [MTB + profile]}, **body)


def _bundle(*pairs):
    return {"resourceType": "Bundle", "type": "transaction",
            "entry": [{"fullUrl": u, "resource": dict(r, id=u.rsplit(":", 1)[-1])} for u, r in pairs]}


def _chain(response_target="urn:uuid:th-a"):
    """variant A/B differ in content; recommendations A/B differ ONLY in the variant they cite; therapies A/B differ
    ONLY in the recommendation that caused them; the response cites one therapy. A swap of the response's partOf is
    a difference two reference levels below the swapped target."""
    var = lambda gene: _res("Observation", "variante", status="final", valueString=gene)          # noqa: E731
    rec = lambda v: _res("MedicationRequest", "therapieempfehlung", status="active", intent="proposal",  # noqa: E731
                         reasonReference=[{"reference": v}])
    th = lambda r: _res("Procedure", "systemische-therapie", status="completed",                    # noqa: E731
                        extension=[{"url": "causedBy", "valueReference": {"reference": r}}])
    return _bundle(("urn:uuid:var-a", var("BRAF")), ("urn:uuid:var-b", var("KRAS")),
                   ("urn:uuid:rec-a", rec("urn:uuid:var-a")), ("urn:uuid:rec-b", rec("urn:uuid:var-b")),
                   ("urn:uuid:th-a", th("urn:uuid:rec-a")), ("urn:uuid:th-b", th("urn:uuid:rec-b")),
                   ("urn:uuid:resp", _res("Observation", "response", status="final",
                                          partOf=[{"reference": response_target}])))


def test_canonical_detects_swap_between_targets_differing_only_in_their_references():
    """R40 residual: the twin therapies have the same own content; only their causedBy recommendations differ, and
    those only in the variant they cite. The one-level hash of round 1 could not see this swap."""
    assert RC.canonical(_chain("urn:uuid:th-a")) != RC.canonical(_chain("urn:uuid:th-b"))
    # deep=False (probe maps) stays label-only by design
    assert RC.canonical(_chain("urn:uuid:th-a"), deep=False) == RC.canonical(_chain("urn:uuid:th-b"), deep=False)


def test_canonical_true_twins_stay_interchangeable():
    """Two therapies identical at every depth (same recommendation) are indistinguishable: swapping is no change."""
    b = _chain()
    b["entry"][5]["resource"]["extension"][0]["valueReference"]["reference"] = "urn:uuid:rec-a"
    swapped = copy.deepcopy(b)
    swapped["entry"][6]["resource"]["partOf"] = [{"reference": "urn:uuid:th-b"}]
    assert RC.canonical(b) == RC.canonical(swapped)


def _cycles(cite="urn:uuid:cond-a", extent_b="T2"):
    """Two primary-tumour Conditions, each in a reference cycle with its own tumour-extent Observation
    (Condition.stage.assessment <-> Observation.focus); the Conditions differ only in the Observation they cite."""
    cond = lambda o: _res("Condition", "diagnose-primaertumor",                                       # noqa: E731
                          stage=[{"assessment": [{"reference": o}]}])
    ext = lambda c, v: _res("Observation", "tumorausbreitung", status="final", valueString=v,             # noqa: E731
                            focus=[{"reference": c}])
    return _bundle(("urn:uuid:cond-a", cond("urn:uuid:ext-a")), ("urn:uuid:ext-a", ext("urn:uuid:cond-a", "T1")),
                   ("urn:uuid:cond-b", cond("urn:uuid:ext-b")), ("urn:uuid:ext-b", ext("urn:uuid:cond-b", extent_b)),
                   ("urn:uuid:self", _res("Observation", "self", status="final",
                                          hasMember=[{"reference": "urn:uuid:self"}])),
                   ("urn:uuid:plan", _res("CarePlan", "plan", status="active", addresses=[{"reference": cite}])))


def test_canonical_is_cycle_safe_and_sees_swaps_between_cycles():
    assert RC.canonical(_cycles("urn:uuid:cond-a")) != RC.canonical(_cycles("urn:uuid:cond-b"))
    # identical cycles at every depth: interchangeable
    assert RC.canonical(_cycles("urn:uuid:cond-a", "T1")) == RC.canonical(_cycles("urn:uuid:cond-b", "T1"))


def test_canonical_ignores_ids_entry_order_and_profile_order_with_cycles():
    b = _cycles()
    other = copy.deepcopy(b)
    ren = {e["fullUrl"]: f"urn:uuid:x{i}" for i, e in enumerate(other["entry"])}
    txt = json.dumps(other)
    for old, new in ren.items():
        txt = txt.replace(f'"{old}"', f'"{new}"')
    other = json.loads(txt)
    random.Random(7).shuffle(other["entry"])
    for e in other["entry"]:
        e["resource"]["id"] = "renamed"
        e["resource"]["meta"]["profile"].insert(0, "https://example.org/aaa-extra")
    for e in b["entry"]:
        e["resource"]["meta"]["profile"].append("https://example.org/aaa-extra")   # same set, other written order
    assert RC.canonical(b) == RC.canonical(other)


def test_canonical_difference_changes_only_resources_that_reach_it():
    """A content change of one tumour extent changes its own string and those of the resources reaching it (both
    cycle members, the CarePlan), never the other cycle's."""
    a, b = RC.canonical(_cycles(extent_b="T2")), RC.canonical(_cycles(extent_b="T3"))
    changed = {json.loads(s)["resourceType"] + "/" + json.loads(s)["meta"]["profile"][0].split("/")[-1]
               for s in (a - b)}
    assert changed == {"Condition/diagnose-primaertumor", "Observation/tumorausbreitung"}
    assert len(a - b) == 2 and len(b - a) == 2       # cond-b + ext-b; cond-a, ext-a, plan (cites cond-a), self same


def test_canonical_twin_therapy_swap_on_corpus_file():
    """The verifier's corpus case (twin systemische-therapie Procedures differing only in procedure-causedBy):
    rewiring the response and the medication statement from one therapy to its twin is now visible."""
    b, rep = convert(loads(TWIN_THERAPIES.read_text(encoding="utf-8")), TWIN_THERAPIES.name, "2027",
                     check_input=False)
    assert rep.status == "converted"
    prof = lambda r: (r.get("meta", {}).get("profile") or [""])[0].rsplit("/", 1)[-1]     # noqa: E731
    th = [e["fullUrl"] for e in b["entry"] if prof(e["resource"]) == "mii-pr-mtb-systemische-therapie"]
    assert len(th) == 2
    base = RC.canonical(b)
    hits = 0
    for i, e in enumerate(b["entry"]):
        if prof(e["resource"]) in ("mvgs-therapy-response", "mii-pr-mtb-systemtherapie-medication-statement") \
                and f'"{th[0]}"' in json.dumps(e["resource"]):
            m = copy.deepcopy(b)
            m["entry"][i]["resource"] = json.loads(json.dumps(e["resource"]).replace(f'"{th[0]}"', f'"{th[1]}"'))
            assert RC.canonical(m) != base, prof(e["resource"])
            hits += 1
    assert hits >= 2


# ---- R44: refused matchbox, labelled unvalidated runs ------------------------------------------------------------
KDS = "de.medizininformatikinitiative.kerndatensatz."


def _manifest(tmp_path):
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"oncology": {"valid": [str(FIXTURE)], "invalid": []}}))
    return m


def _run(tmp_path, *extra):
    return RC.main(["--branches", "oncology", "--no-ingest", "--manifest", str(_manifest(tmp_path)),
                    "--out", str(tmp_path), "--report", str(tmp_path / "report.md"), *extra])


def _boom(*a, **k):
    raise AssertionError("must not validate/transform on a refused matchbox")


@pytest.mark.parametrize("ps, held, extra", [
    ("2026", "2027.0.0-ballot.1", ["--matchbox-2026", "http://mb2027.invalid/fhir"]),   # matchbox-2027 given as 2026
    ("2027", "2026.0.4", ["--fml"]),                                                   # MB2027 points at a 2026 stack
])
def test_matchbox_of_other_profile_set_is_refused(tmp_path, monkeypatch, capsys, ps, held, extra):
    listing = {KDS + "molgen": {held}, KDS + "person": {"2025.0.1"}}     # 2025.x is shared by both stacks
    monkeypatch.setattr(RC.Matchbox, "packages", lambda self, prefix=KDS: listing)
    monkeypatch.setattr(RC, "validate_bundle", _boom)
    monkeypatch.setattr(RC.Matchbox, "transform", _boom)
    assert _run(tmp_path, "--profile-set", ps, "--gate", *extra) == 1
    res = json.loads((tmp_path / "results.json").read_text())
    assert res["validated"] is False and f"not {ps}" in res["validation_refused"]
    assert any(g.startswith("validation refused: ") for g in res["gate"])
    assert res["branches"]["oncology"]["verdicts"] == {} and res["branches"]["oncology"]["parity"] == {}
    if ps == "2027":
        assert res["fml"] == "not run (matchbox refused)"
    txt = (tmp_path / "report.md").read_text()
    assert f"**Not validated**: {res['validation_refused']}" in txt and "Gate: **failed**" in txt
    assert "| sampled bundles validated | 0 (1 sampled, not validated) |" in txt
    assert "not validated" in capsys.readouterr().out
    # without --gate the refused run still exits 0 (report and results say why)
    assert _run(tmp_path, "--profile-set", ps, *extra) == 0


def test_matchbox_without_package_listing_is_still_used_for_2026(tmp_path, monkeypatch):
    """No answer to the package listing: the explicit --matchbox-2026 URL is used (an unreachable one gives ERROR)."""
    used = []
    monkeypatch.setattr(RC.Matchbox, "packages", lambda self, prefix=KDS: None)
    monkeypatch.setattr(RC, "validate_bundle", lambda b, mb, source=None: used.append(mb.base) or
                        {"verdict": "PASS", "resources": []})
    assert _run(tmp_path, "--profile-set", "2026", "--matchbox-2026", "http://mb2026.invalid/fhir", "--gate") == 0
    res = json.loads((tmp_path / "results.json").read_text())
    assert used == ["http://mb2026.invalid/fhir"] and res["validated"] is True and "validation_refused" not in res
    txt = (tmp_path / "report.md").read_text()
    assert "| sampled bundles validated | 1 |" in txt and "Gate: passed\n" in txt


def test_matchbox_of_own_profile_set_is_used(tmp_path, monkeypatch):
    monkeypatch.setattr(RC.Matchbox, "packages", lambda self, prefix=KDS: {KDS + "molgen": {"2026.0.4"}})
    monkeypatch.setattr(RC, "validate_bundle", lambda b, mb, source=None: {"verdict": "PASS", "resources": []})
    assert _run(tmp_path, "--profile-set", "2026", "--matchbox-2026", "http://mb2026.invalid/fhir", "--gate") == 0
    assert json.loads((tmp_path / "results.json").read_text())["branches"]["oncology"]["verdicts"] == {"PASS": 1}


def test_unvalidated_gate_and_report_say_so(tmp_path, monkeypatch, capsys):
    """2026 without --matchbox-2026: the gate judges the other checks and says it ran without validation; the report
    does not count the sampled bundles as validated."""
    monkeypatch.setattr(RC, "validate_bundle", _boom)
    assert _run(tmp_path, "--profile-set", "2026", "--gate") == 0
    assert "gate: passed without validation" in capsys.readouterr().out
    txt = (tmp_path / "report.md").read_text()
    assert "Gate: passed without validation (conversion, rejection and ingest checks only)" in txt
    assert "| sampled bundles validated | 0 (1 sampled, not validated) |" in txt
    assert "| verdicts | not validated |" in txt


# ---- SCHEMA: BfArM KDK main fe724ff ------------------------------------------------------------------------------
KDK = REPO / "schemas" / "kdk"
KDK_BASE = "https://raw.githubusercontent.com/BfArM-MVH/MVGenomseq_KDK/main/KDK/"


def _kdk_validator(root="Oncology.json"):
    # jsonschema / referencing come only with genomde-dk-validator (no genomde2fhir dependency): skip without them
    # instead of failing the collection of the whole suite
    Draft202012Validator = pytest.importorskip("jsonschema").Draft202012Validator
    Registry = pytest.importorskip("referencing").Registry
    DRAFT202012 = pytest.importorskip("referencing.jsonschema").DRAFT202012
    store = {KDK_BASE + p.relative_to(KDK).as_posix(): json.loads(p.read_text(encoding="utf-8"))
             for p in KDK.rglob("*.json")}
    reg = Registry().with_resources([(u, DRAFT202012.create_resource(c)) for u, c in store.items()])
    return Draft202012Validator(store[KDK_BASE + root], registry=reg)


def _with_version(version):
    dk = json.loads(CONSENT_EXAMPLE.read_text(encoding="utf-8"))
    for rc in dk["metaData"]["researchConsents"]:
        rc["schemaVersion"] = version
    return dk


def test_vendored_submission_schema_lists_upstream_consent_versions():
    sub = json.loads((KDK / "Submission.json").read_text(encoding="utf-8"))
    enum = sub["properties"]["researchConsents"]["items"]["properties"]["schemaVersion"]["enum"]
    assert enum == NEW_CONSENT_VERSIONS
    prov = (REPO / "schemas" / "PROVENANCE.md").read_text(encoding="utf-8")
    assert "fe724ff09172a284cb1334c677db030643b99203" in prov


def test_vendored_kdk_schema_accepts_new_consent_versions():
    v = _kdk_validator()
    for version in NEW_CONSENT_VERSIONS:
        errs = [e for e in v.iter_errors(_with_version(version)) if "schemaVersion" in e.json_path]
        assert errs == [], version
    bad = [e for e in v.iter_errors(_with_version("2027.0.0")) if "schemaVersion" in e.json_path]
    assert bad and bad[0].validator == "enum"


@pytest.mark.parametrize("model", ["DatenkranzOncology", "DatenkranzRareDisease"])
def test_logical_models_list_new_consent_versions(model):
    sd = json.loads((REPO / "mvgs-ig" / "input" / f"StructureDefinition-{model}.json").read_text(encoding="utf-8"))
    path = f"{model}.metaData.researchConsents.schemaVersion"
    (el,) = [e for e in sd["differential"]["element"] if e["path"] == path]
    assert el["definition"].endswith("Allowed values: " + ", ".join(f"'{x}'" for x in NEW_CONSENT_VERSIONS) + ".")


def _consents(bundle):
    return [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Consent"
            and "mii-pr-consent-einwilligung" in json.dumps(e["resource"].get("meta"))]


@pytest.mark.parametrize("version", NEW_CONSENT_VERSIONS)
def test_research_consent_migration_accepts_new_versions(version):
    """The consent migration does not depend on schemaVersion: every listed version gives the same migrated Consent,
    and the version is reported as dropped (consumed by the migration). check_input=False: the input gate
    (genomde-dk-validator) vendors its own schema copy, which still lists 2025.0.1 only."""
    b, rep = convert(_with_version(version), CONSENT_EXAMPLE.name, "2027", check_input=False)
    ref, _ = convert(_with_version("2025.0.1"), CONSENT_EXAMPLE.name, "2027", check_input=False)
    assert rep.status == "converted"
    assert _consents(b) == _consents(ref) and len(_consents(b)) == 1
    assert ("metaData.researchConsents[].schemaVersion", version,
            "source package version of the embedded consent; consumed by the migration to the target profile") \
        in rep.dropped


def test_research_consent_migration_keeps_2026_style_category():
    """A consent 2026.x object already codes the Broad Consent category in mii-cs-consent-version-modules: it is kept
    once, nothing is added or duplicated."""
    dk = _with_version("2026.0.1")
    scope = dk["metaData"]["researchConsents"][0]["scope"]
    for cat in scope["category"]:
        for c in cat["coding"]:
            c["system"] = c["system"].replace("mii-cs-consent-consent_category", "mii-cs-consent-version-modules")
    b, rep = convert(dk, CONSENT_EXAMPLE.name, "2027", check_input=False)
    (con,) = _consents(b)
    codes = [(c["system"].rsplit("/", 1)[-1], c["code"]) for cat in con["category"] for c in cat["coding"]]
    assert codes.count(("mii-cs-consent-version-modules", "2.16.840.1.113883.3.1937.777.24.2.184")) == 1
    assert codes.count(("loinc.org", "57016-8")) == 1
    assert not [w for w in rep.warnings if "added" in w[1] and "researchConsents" in w[0]]
