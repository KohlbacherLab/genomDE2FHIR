"""Fix round 4, group fml: the FML maps mirror the harmonized KDK submission Organizations and close the round-3 FML
residuals.

Offline (always run): the map text carries the round-4 rules (static checks), and mappers/fml/README.md lists the
KDK submission Organizations and the accepted R39 simplifications by scenario name.
With MB2027 (matchbox-2027 base URL; HAPI2027 defaults to http://localhost:8092/fhir), every scenario converts on both
paths with zero differences under canonical() of scripts/run_corpus.py and no duplicate fullUrl / conditional URL:
  - ORG the three submission Organizations of a KDK case (submitter, clinical-data-node, genomic-data-center; oncology
    and rare disease), built by the DkOrg* groups shared with GRZ; an empty routing id gives none; a second HAPI ingest
    of the FML Bundle creates nothing;
  - R24-mirror follow-up therapy names padded or split by U+00A0 / other Unicode spaces are one substance, as in
    Python's followup._norm (str.split());
  - PLACEHOLDERS a placeholder study name / id padded with U+00A0 or another Unicode space is a placeholder, as after
    Python's str.strip();
  - R39 a '#<id>' canonical / uri / url / system without a contained resource is removed, and a contained resource is
    kept only when a carried-over element (or a kept contained resource) references it.
Inputs: tracked fixtures only, mutated inline."""
import base64
import copy
import json
import sys
import uuid
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import test_fix2_fml as f2  # noqa: E402  (harness; imported as a module: its tests are not re-collected)
import test_fix3_fml as f3  # noqa: E402  (scenario builders)

from genomde2fhir.convert import convert  # noqa: E402
from genomde2fhir.io import loads  # noqa: E402
from genomde2fhir.validate import Hapi  # noqa: E402

REPO = f2.REPO
FML = REPO / "mappers" / "fml"
MB, HAPI = f2.MB, f2.HAPI
PLAN, CONSENT, RD = f2.PLAN, f2.CONSENT, f2.RD
X, Y = "L01EC02", "L01EE01"
fu, therapy, followups, scope = f2.fu, f2.therapy, f2.followups, f2.scope
NBSP, EMSP, NNBSP = " ", " ", " "
EXT = "http://example.org/x"
DOMAIN_REFERENCE = "http://fhir.de/ConsentManagement/StructureDefinition/DomainReference"
ORG_SYSTEMS = {"https://genomde.de/fhir/sid/le-id", "https://genomde.de/fhir/sid/clinical-data-node",
               "https://genomde.de/fhir/sid/genomic-data-center"}


# ---- scenario builders ----------------------------------------------------------------------------------------------
def submission(**kw):
    def m(d):
        sub = d["metaData"]["submission"]
        for k, v in kw.items():
            if v is None:
                sub.pop(k, None)
            else:
                sub[k] = v
    return m


def fu12(fu1, fu2):
    return followups(fu("2026-01-10", *fu1), fu("2026-03-10", *fu2))


def ext(**value):
    return [dict(url=EXT, **value)]


def _ext_code_missing(s):
    s["extension"] = ext(valueCode="#nothere") + [dict(url=EXT + "s", valueString="#nothere"),
                                                  dict(url=EXT + "m", valueMarkdown="#nothere"),
                                                  dict(url=EXT + "i", valueId="#nothere")]


def _ext_plus_q(s):
    s["contained"] = [{"resourceType": "Questionnaire", "id": "q", "status": "active"}]
    s["extension"] = [dict(url=EXT, valueCanonical="#q"), dict(url="http://example.org/y", valueCanonical="#nothere")]


def _coding_system(s):
    s["provision"]["provision"][0]["code"][0]["coding"][0]["system"] = "#nothere"
    s["category"][0]["coding"][0]["system"] = "#nothere2"


def _transitive_unkept(s):
    s["contained"] = [{"resourceType": "Practitioner", "id": "a", "qualification": [{"code": {"text": "c"}, "issuer": {"reference": "#x"}}]},
                      {"resourceType": "Organization", "id": "x", "name": "x"}]


def _transitive_canon_unkept(s):
    s["contained"] = [{"resourceType": "QuestionnaireResponse", "id": "qr", "status": "completed", "questionnaire": "#q"},
                      {"resourceType": "Questionnaire", "id": "q", "status": "active"}]


def _patient_local(s):
    s["patient"] = {"reference": "#pat"}
    s["contained"] = [{"resourceType": "Patient", "id": "pat"}]


def _meta_profile_local(s):
    s["meta"]["profile"].append("#sd")
    s["contained"] = [{"resourceType": "StructureDefinition", "id": "sd", "url": "http://x", "name": "X", "status": "active",
                       "kind": "resource", "abstract": False, "type": "Consent"}]


def _kept_chain(s):
    s["performer"] = [{"reference": "#a"}]
    s["contained"] = [{"resourceType": "Practitioner", "id": "a", "qualification": [{"code": {"text": "c"}, "issuer": {"reference": "#b"}}]},
                      {"resourceType": "Organization", "id": "b", "name": "B", "partOf": {"reference": "#c"}},
                      {"resourceType": "Organization", "id": "c", "name": "C"},
                      {"resourceType": "Organization", "id": "u", "name": "U", "partOf": {"reference": "#c"}}]


def _domainref_unkept(s):
    s["extension"] = [{"url": DOMAIN_REFERENCE, "extension": [
        {"url": "domain", "valueReference": {"reference": "ResearchStudy/rs"}},
        {"url": "status", "valueCoding": {"system": "http://hl7.org/fhir/publication-status", "code": "active",
                                          "extension": [{"url": EXT, "valueReference": {"reference": "#o"}}]}}]}]
    s["contained"] = [{"resourceType": "Organization", "id": "o", "name": "O"}]


def _qr_definition(s):
    s["sourceReference"] = {"reference": "#qr"}
    s["contained"] = [{"resourceType": "QuestionnaireResponse", "id": "qr", "status": "completed",
                       "item": [{"linkId": "1", "definition": "#gone", "answer": [{"valueUri": "#gone"}, {"valueString": "#gone"}]}]}]


def _chain(n):
    def m(s):
        s["performer"] = [{"reference": "#c0"}]
        s["contained"] = [{"resourceType": "Organization", "id": f"c{i}", "name": f"C{i}",
                           **({"partOf": {"reference": f"#c{i + 1}"}} if i < n - 1 else {})} for i in range(n)]
    return m


def _many(n):
    """a kept 4-chain c0..c3, a self-referencing Provenance with its agent, and n unreferenced Organizations in a cycle"""
    def m(s):
        _chain(4)(s)
        s["contained"] += [{"resourceType": "Provenance", "id": "p", "target": [{"reference": "#"}], "recorded": "2025-01-01T00:00:00Z",
                            "agent": [{"who": {"reference": "#ag"}}]}, {"resourceType": "Organization", "id": "ag", "name": "AG"}]
        s["contained"] += [{"resourceType": "Organization", "id": f"o{i}", "name": f"O{i}", "partOf": {"reference": f"#o{(i + 1) % n}"}}
                           for i in range(n)]
    return m


def _set(path, value):
    def m(s):
        o = s
        for p in path[:-1]:
            o = o[p]
        o[path[-1]] = value
    return m


SCENARIOS = {
    # ORG: KDK submission Organizations (submission.submission_organization)
    "ORG-onco": ("oncology", PLAN, lambda d: None),
    "ORG-rd": ("rare-disease", RD, lambda d: None),
    "ORG-onco-empty-ids": ("oncology", PLAN, submission(clinicalDataNodeId="", genomicDataCenterId=None)),
    "ORG-rd-no-submitter-org-ids": ("rare-disease", RD, submission(clinicalDataNodeId=None, genomicDataCenterId="")),
    "ORG-onco-initial": ("oncology", PLAN, submission(type="initial")),
    # R24-mirror: Unicode whitespace in substance names (followup._norm = ' '.join(name.split()).lower())
    "R24-nbsp-trailing": ("oncology", PLAN, fu12([therapy([], names=["Alpha"]), therapy([X])],
                                                [therapy([], names=["Alpha" + NBSP], end="2026-03-01", reason="E"), therapy([X])])),
    "R24-nbsp-inner": ("oncology", PLAN, fu12([therapy([], names=["Alpha Beta"]), therapy([X])],
                                             [therapy([], names=["Alpha" + NBSP + "Beta"], end="2026-03-01", reason="E"), therapy([X])])),
    "R24-unicode-spaces": ("oncology", PLAN, fu12([therapy([], names=[EMSP + "alpha" + NNBSP + NBSP + "BETA" + NBSP])],
                                                 [therapy([], names=["Alpha beta"], end="2026-03-01", reason="E"), therapy([Y])])),
    "R24-note-nbsp-spellings": ("oncology", PLAN, fu12([therapy([], names=["Alpha", NBSP + "alpha", "Beta"])],
                                                      [therapy([], names=["BETA" + NBSP, "Gamma"])])),
    # PLACEHOLDERS padded with Unicode spaces (careplan._real: value.strip().lower())
    "PH-onco-nbsp-names": ("oncology", PLAN, f3.onco_studies(NBSP + "Unbekannt" + NBSP, EMSP + "k. A.", "N/A" + NNBSP)),
    "PH-onco-unknown-nbsp": ("oncology", PLAN, f3.onco_unknown_study("keine Angabe" + NBSP, NBSP + "unknown")),
    "PH-rd-nbsp": ("rare-disease", RD, f3.rd_studies(NBSP + "n.a.", "-" + NBSP, EMSP + "Unbekannt")),
    # R39: '#<id>' without a contained resource; contained kept only from carried-over elements, transitively
    "R39-ext-canon-missing": ("oncology", CONSENT, scope(_set(["extension"], ext(valueCanonical="#nothere")))),
    "R39-ext-uri-missing": ("oncology", CONSENT, scope(_set(["extension"], ext(valueUri="#nothere")))),
    "R39-ext-url-missing": ("oncology", CONSENT, scope(_set(["extension"], ext(valueUrl="#nothere")))),
    "R39-ext-code-missing": ("oncology", CONSENT, scope(_ext_code_missing)),
    "R39-ext-canon-missing-plus-q": ("oncology", CONSENT, scope(_ext_plus_q)),
    "R39-nested-ext-canon-missing": ("oncology", CONSENT, scope(_set(["extension"], [dict(url=EXT, extension=[
        dict(url="a", valueCanonical="#nothere"), dict(url="b", valueString="s")])]))),
    "R39-provision-ext-canon-missing": ("oncology", CONSENT, scope(_set(["provision", "extension"], ext(valueCanonical="#nothere")))),
    "R39-coding-system-missing": ("oncology", CONSENT, scope(_coding_system)),
    "R39-identifier-system-missing": ("oncology", CONSENT, scope(_set(["identifier"], [{"system": "#nothere", "value": "v"}]))),
    "R39-attachment-url-missing": ("oncology", CONSENT, scope(_set(["sourceAttachment"], {"contentType": "application/pdf", "url": "#att"}))),
    "R39-transitive-via-unkept": ("oncology", CONSENT, scope(_transitive_unkept)),
    "R39-transitive-canon-via-unkept": ("oncology", CONSENT, scope(_transitive_canon_unkept)),
    "R39-patient-local": ("oncology", CONSENT, scope(_patient_local)),
    "R39-meta-profile-local": ("oncology", CONSENT, scope(_meta_profile_local)),
    "R39-transitive-kept-chain": ("oncology", CONSENT, scope(_kept_chain)),
    "R39-domainref-local-unkept": ("oncology", CONSENT, scope(_domainref_unkept)),
    "R39-qr-definition-missing": ("oncology", CONSENT, scope(_qr_definition)),
    # closing fix after round 4: the keep condition evaluated level by level (same result, linear cost per resource)
    "R39-chain4": ("oncology", CONSENT, scope(_chain(4))),
    "R39-many-contained": ("oncology", CONSENT, scope(_many(40))),
}
# accepted simplifications (mappers/fml/README.md 'Accepted simplifications (R39)'), by the round-3 probe's names
R39_ACCEPTED = ["other-type-with-urn", "other-type-whole", "prim-ext", "top-prim-ext",
                "language-missing", "contenttype-missing", "contenttype-local"]   # the last three: verifier probe after round 4
R39_FIXED = ["ext-canon-missing", "ext-uri-missing", "ext-url-missing", "ext-canon-missing-plus-q", "nested-ext-canon-missing",
             "provision-ext-canon-missing", "coding-system-missing", "identifier-system-missing", "attachment-url-missing",
             "transitive-via-unkept", "transitive-canon-via-unkept", "patient-local", "meta-profile-local"]


def scenario(name):
    branch, path, fn = SCENARIOS[name]
    dk = loads(Path(path).read_text(encoding="utf-8"))
    fn(dk)
    return branch, dk


# ---- offline: the map text and the README -----------------------------------------------------------------------------
def _map(name):
    return (FML / name).read_text(encoding="utf-8")


def test_org_groups_shared_in_common():
    common, grz = _map("DatenkranzCommon.map"), _map("DatenkranzGrzToMii.map")
    for g in ("DkOrgSubmitter", "DkOrgGdc", "DkOrgKdk"):
        assert f"group {g}(source sub, target org : Organization)" in common, g
    for g in ("GrzOrgSubmitter", "GrzOrgGdc", "GrzOrgKdk"):
        assert g not in grz, g
    assert "group GrzOrgLab(" in grz                                   # the lab stays GRZ-only
    assert "builders/submission.submission_organization, shared with KDK" in grz
    for name in ("DatenkranzGrzToMii.map", "DatenkranzOncologyToMii.map", "DatenkranzRareDiseaseToMii.map"):
        text = _map(name)
        assert "DkOrgSubmitter(sub, org) \"org-submitter\"" in text, name
        assert "DkOrgGdc(sub, org) \"org-gdc\"" in text and "DkOrgKdk(sub, org) \"org-kdk\"" in text, name
        assert "('org:genomic-data-center:' & %v) as role" in text and "('org:clinical-data-node:' & %v) as role" in text, name
        assert 'alias Organization as target' in text, name


def test_no_trim_in_placeholder_or_name_normalisation():
    for name in ("OncoPlanFollowUp.map", "DatenkranzRareDiseaseToMii.map"):
        text = _map(name)
        assert ".trim().lower().matches('^(|n/a" not in text, name
        assert ".trim().replaceMatches('\\\\s+'" not in text, name
        assert text.count("\\\\xA0\\\\u1680\\\\u2000-\\\\u200A") > 0, name
    assert _map("OncoPlanFollowUp.map").count("replaceMatches('^ | $', '')") == 6


def test_readme_lists_kdk_orgs_and_r39_scenarios():
    text = " ".join((FML / "README.md").read_text(encoding="utf-8").split())
    assert "`org:submitter`, `org:clinical-data-node:<clinicalDataNodeId>` and `org:genomic-data-center:<genomicDataCenterId>`" in text
    assert "`DkOrgSubmitter` / `DkOrgGdc` / `DkOrgKdk`" in text
    sec = text[text.index("**Accepted simplifications (R39).**"):]
    sec = sec[:sec.index("## Oncology map")]
    for n in R39_ACCEPTED + R39_FIXED:
        assert f"`{n}`" in sec, n
    assert "a contained resource counts as referenced when any `#<id>` below `scope` names it" not in text
    assert "a substance name is normalised with `trim()` and `\\s+`" not in text


def test_python_whitespace_class_matches_str_split():
    """the regex class in the maps is exactly the whitespace of Python's str.split() / str.strip() (BMP)"""
    import re
    cls = "[\\t\\n\\x0B\\f\\r\\x1C-\\x20\\x85\\xA0\\u1680\\u2000-\\u200A\\u2028\\u2029\\u202F\\u205F\\u3000]"
    assert cls.replace("\\", "\\\\") in _map("OncoPlanFollowUp.map")
    rx = re.compile(cls)
    for cp in range(0x10000):
        c = chr(cp)
        assert bool(rx.fullmatch(c)) == c.isspace() == (len(("a" + c + "a").split()) == 2), hex(cp)


# ---- matchbox -----------------------------------------------------------------------------------------------------------
needs_mb = pytest.mark.skipif(not MB, reason="MB2027 not set (matchbox-2027 base URL)")


@pytest.fixture(scope="module")
def mb():
    build = f2._load("build_mvgs", REPO / "scripts" / "build_mvgs.py")
    assert build.push_maps(MB) == 0, "pushing the production maps failed"
    return f2.Matchbox(MB)


def both(mb, name=None, branch=None, dk=None):
    if name:
        branch, dk = scenario(name)
    py, rep = convert(copy.deepcopy(dk), name or "fix4", check_input=False)
    st, fml = mb.transform(dk, f2._RC.MAPS[branch])
    return py, rep, st, fml


def orgs(b):
    return sorted((i["system"], i["value"], r["name"]) for r in f2.resources(b, "Organization")
                  for i in r.get("identifier", []) if i.get("system") in ORG_SYSTEMS)


def research(b):
    [con] = [r for r in f2.resources(b, "Consent") if r.get("scope", {}).get("coding", [{}])[0].get("code") == "research"]
    return con


@needs_mb
@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario_parity(mb, name):
    f2.assert_parity(*both(mb, name))


@needs_mb
def test_org_kdk_submission_organizations(mb):
    want = [("https://genomde.de/fhir/sid/clinical-data-node", "KDKTUE005", "Klinischer Datenknoten KDKTUE005"),
            ("https://genomde.de/fhir/sid/genomic-data-center", "GRZTUE002", "Genomrechenzentrum GRZTUE002"),
            ("https://genomde.de/fhir/sid/le-id", "260840108", "Leistungserbringer (submitter) 260840108")]
    py, _, _, fml = both(mb, "ORG-onco")
    assert orgs(fml) == orgs(py) == want
    py, _, _, fml = both(mb, "ORG-onco-empty-ids")
    assert orgs(fml) == orgs(py) == want[2:]
    py, _, _, fml = both(mb, "ORG-rd")
    assert orgs(fml) == orgs(py) and len(orgs(fml)) == 3
    # stream-scoped keys: the KDK Organizations' resource keys start with 'kdk:'
    for r in f2.resources(fml, "Organization"):
        key = next(i["value"] for i in r["identifier"] if i["system"] == f2.KEY)
        assert base64.urlsafe_b64decode(key + "=" * (-len(key) % 4)).decode().startswith("kdk:260840108:")


@needs_mb
def test_org_hapi_double_ingest_creates_nothing(mb):
    branch, dk = scenario("ORG-onco-initial")
    dk["metaData"]["localCaseId"] = f"FIX4-ORG-{uuid.uuid4().hex[:10]}"
    _, _, st, fml = both(mb, branch=branch, dk=dk)
    assert st == 200
    hapi = Hapi(HAPI)
    ok, first = hapi.transaction(fml)
    assert ok, json.dumps(first)[:300]
    ok, second = hapi.transaction(fml)
    assert ok, json.dumps(second)[:300]
    status = [e["response"]["status"] for e in second["entry"]]
    assert len(status) == len(fml["entry"]) and all(s.startswith("200") for s in status), status


@needs_mb
def test_r24_unicode_space_names_are_one_substance(mb):
    def notes(b):
        return sorted((r["status"], " ".join(n["text"] for n in r.get("note", [])))
                      for r in f2.resources(b, "Procedure", "mii-pr-mtb-systemische-therapie"))
    for name in ("R24-nbsp-trailing", "R24-nbsp-inner", "R24-unicode-spaces"):
        py, _, _, fml = both(mb, name)
        assert notes(fml) == notes(py), name
        assert [s for s, _ in notes(fml) if "ohne ATC" in _] in (["completed"], ["completed", "in-progress"]), (name, notes(fml))
        assert not [n for s, n in notes(fml) if s == "in-progress" and "ohne ATC" in n], (name, notes(fml))


@needs_mb
def test_placeholder_padded_with_unicode_space(mb):
    for name in ("PH-onco-nbsp-names", "PH-onco-unknown-nbsp", "PH-rd-nbsp"):
        py, _, _, fml = both(mb, name)
        titles = sorted(r.get("title", "") for r in f2.resources(fml, "ResearchStudy"))
        assert titles == sorted(r.get("title", "") for r in f2.resources(py, "ResearchStudy")), name
        for r in f2.resources(fml, "ResearchStudy"):
            assert r.get("title", "x").strip().lower() not in {"unbekannt", "k. a.", "n/a", "n.a."}, (name, r.get("title"))
        notes = [n["text"] for r in f2.resources(fml, "ServiceRequest") for n in r.get("note", [])
                 if "nicht identifiziert" in n["text"]]
        assert not [n for n in notes if "keine Angabe" in n or "unknown" in n.lower() or "Unbekannt" in n], (name, notes)


@needs_mb
def test_r39_missing_local_values_removed_and_contained_pruned(mb):
    _, _, _, fml = both(mb, "R39-ext-canon-missing-plus-q")
    con = research(fml)
    assert con["extension"] == [{"url": EXT, "valueCanonical": "#q"}, {"url": "http://example.org/y"}]
    assert [c["id"] for c in con["contained"]] == ["q"]
    _, _, _, fml = both(mb, "R39-ext-code-missing")
    assert research(fml)["extension"] == [{"url": EXT}, {"url": EXT + "s", "valueString": "#nothere"},
                                          {"url": EXT + "m", "valueMarkdown": "#nothere"}, {"url": EXT + "i"}]
    for name in ("R39-transitive-via-unkept", "R39-transitive-canon-via-unkept", "R39-patient-local", "R39-meta-profile-local",
                 "R39-domainref-local-unkept"):
        _, _, _, fml = both(mb, name)
        assert "contained" not in research(fml), name
    _, _, _, fml = both(mb, "R39-transitive-kept-chain")
    assert [c["id"] for c in research(fml)["contained"]] == ["a", "b", "c"]
    _, _, _, fml = both(mb, "R39-attachment-url-missing")
    assert research(fml)["sourceAttachment"] == {"contentType": "application/pdf"}


@needs_mb
def test_r39_keep_condition_cost_is_not_polynomial_in_contained(mb):
    """round 4's nested keep condition re-scanned the consent per candidate (n^4: 15 contained 31 s, 20 contained 113 s);
    level by level, 40 unreferenced contained resources transform in well under the HTTP timeout, with parity"""
    import time
    t = time.time()
    py, _, st, fml = both(mb, "R39-many-contained")
    assert st < 300 and time.time() - t < 20
    assert f2._RC.canonical(py) == f2._RC.canonical(fml)
    assert [c["id"] for c in research(fml)["contained"]] == ["c0", "c1", "c2", "c3", "p", "ag"]
