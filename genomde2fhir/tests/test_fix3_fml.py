"""Fix round 3, group fml: the FML maps mirror the round-3 Python changes and close the reopened FML residuals.

Offline (always run): the map text carries the round-3 rules (static checks) and the FML README / test docstrings
describe the inputs the tests use (R46 documentation residual).
With MB2027 (matchbox-2027 base URL; HAPI2027 defaults to http://localhost:8092/fhir), every scenario converts on both
paths with zero differences under canonical() of scripts/run_corpus.py, no duplicate fullUrl / conditional URL and no
duplicate JSON key in the raw $transform response, plus scenario checks:
  - R24 follow-up therapies matched by substance identity, then by the remaining attributes (followup._FollowUp.
    therapy_ids): further split, merge plus subset, same substances with other attributes, normalised names, '+' in a
    name, a split entry continuing the earlier single report, every array order;
  - R43 meta.source = 'urn:genomde2fhir:submission:' + the percent-encoded components (identity.source_component);
  - PLACEHOLDERS German placeholder study names / ids in both careplans;
  - R06 the GRZ lab Organization keyed by lab name (an addition from another lab keeps the earlier study's performer);
  - R26 rare-disease recommendation ids from the produced ids (rd.careplan._rid), variant duplicates in a namespace of
    their own (rd.variants: the index as an id part);
  - R30 a whitespace-only follow-up diagnosis code under ICD-10-GM (bfarm, dimdi, empty or no system) keeps the
    metachronous flag; Python's strip() whitespace; an empty item replaces no earlier one;
  - R39 sender-system references inside a kept contained resource are removed as in Python;
  - R53 no duplicate extension value, an all-'' typed extension value is left out as after Python's prune().
Inputs: tracked fixtures only, mutated inline."""
import collections
import copy
import itertools
import json
import re
import sys
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import test_fix2_fml as f2  # noqa: E402  (scenario builders, harness; imported as a module: its tests are not re-collected)

from genomde2fhir.convert import convert  # noqa: E402
from genomde2fhir.io import loads  # noqa: E402
from genomde2fhir.identity import SOURCE_PREFIX, source_component  # noqa: E402
from genomde2fhir.validate import Hapi  # noqa: E402

REPO = f2.REPO
FML = REPO / "mappers" / "fml"
FX = f2.FX
MB, HAPI = f2.MB, f2.HAPI
PLAN, FU, SV, CONSENT, RD, GRZ, GRZL = f2.PLAN, f2.FU, f2.SV, f2.CONSENT, f2.RD, f2.GRZ, f2.GRZL
RDV = FX / "rd_variants/rd-variants-edge-cases.json"
X, Y, Z, W = "L01EC02", "L01EE01", "L01XX86", "L01XX99"
A = dict(subs=[X], end="2026-02-01", reason="A", response="PD")     # stopped for toxicity
B = dict(subs=[Y], end="2026-03-01", reason="E", response="CR")     # regular completion
fu, therapy, followups, scope = f2.fu, f2.therapy, f2.followups, f2.scope
ICD = "http://fhir.de/CodeSystem/bfarm/icd-10-gm"
DIMDI = "http://fhir.de/CodeSystem/dimdi/icd-10-gm"
ALPHA = "http://fhir.de/CodeSystem/bfarm/alpha-id"
SNOMED = "http://snomed.info/sct"
SENDER = "urn:uuid:11111111-2222-4333-8444-555566667777"
DOMAIN_REFERENCE = "http://fhir.de/ConsentManagement/StructureDefinition/DomainReference"


# ---- scenario builders ----------------------------------------------------------------------------------------------
def fu12(fu1, fu2):
    return followups(fu("2026-01-10", *fu1), fu("2026-03-10", *fu2))


def diagnoses(*items, flag=True, k=0):
    """follow-up k of the follow-up fixture with these additionalDiagnoses and metachroneDiagnoses = flag"""
    def m(d):
        f = d["followUp"]["followUpOds"][k]
        f["metachroneDiagnoses"] = flag
        f["additionalDiagnoses"] = [dict(x) for x in items]
    return m


def dx(code, system=ICD, date="2025-05-15", **kw):
    out = {"code": code, "date": date, **kw}
    if system is not None:
        out["system"] = system
    return out


def both_fu(*muts):
    def m(d):
        for x in muts:
            x(d)
    return m


def local_case_id(value, stype=None, grz=False):
    def m(d):
        if grz:
            d["submission"]["localCaseId"] = value
            if stype:
                d["submission"]["submissionType"] = stype
        else:
            d["metaData"]["localCaseId"] = value
            if stype:
                d["metaData"]["submission"]["type"] = stype
    return m


def onco_studies(*names):
    def m(d):
        studies = d["plan"]["recommendedStudies"]
        for s, n in zip(studies, names):
            s["name"] = n
    return m


def onco_unknown_study(name, sid):
    def m(d):
        d["plan"]["recommendedStudies"].append({"identifier": "st-german-placeholder", "register": "yesButStudyIsUnknown",
                                                "id": sid, "name": name, "evidenceLevel": "m3"})
    return m


def rd_studies(named_name, unknown_name, unknown_id):
    def m(d):
        studies = d["plan"]["recommendedStudies"]
        named = next(s for s in studies if s.get("name") and s.get("register") not in (None, "yesButStudyIsUnknown") and s.get("id"))
        named["name"] = named_name
        unknown = copy.deepcopy(next(s for s in studies if s.get("register") == "yesButStudyIsUnknown"))
        unknown.update(identifier="rdpf-study-german-placeholder", name=unknown_name, id=unknown_id)
        studies.append(unknown)
    return m


def rd_suffixed(key, kind):
    """[.., x, copy of x, '<x>#<kind>-<i>']: the copy gets '#<kind>-<i>' (rd.careplan._rid), the next identifier is
    exactly that id part"""
    def m(d):
        lst = d["plan"][key]
        k = next(i for i, x in enumerate(lst) if x.get("identifier"))
        lst.append(copy.deepcopy(lst[k]))
        x = copy.deepcopy(lst[k])
        x["identifier"] = f"{lst[k]['identifier']}#{kind}-{len(lst) - 1}"
        lst.append(x)
    return m


def rd_variants(fn):
    def m(d):
        fn(d["molecular"]["smallVariants"])
    return m


def _var_colon(v):
    v.append(copy.deepcopy(v[0]))
    x = copy.deepcopy(v[0])
    x["identifier"] = f"{v[0]['identifier']}:{len(v) - 1}"
    v.append(x)


def _var_hash0(v):
    v[0].pop("identifier", None)
    v[1]["identifier"] = "#0"


def _var_empty(v):
    v[0]["identifier"] = ""
    v[1]["identifier"] = ""


def _var_triple(v):
    v[1]["identifier"] = v[0]["identifier"]
    v[2]["identifier"] = v[0]["identifier"]


def grz_sub(**kw):
    def m(d):
        d["submission"].update(kw)
    return m


def _rc_contained_sender(sc):
    """Scenario C (urn:uuid inside a kept contained Practitioner) + Scenario A (relative sender reference)"""
    sc["contained"] = [
        {"resourceType": "Practitioner", "id": "doctor", "name": [{"family": "Arzt", "given": ["Eva"]}],
         "identifier": [{"system": "urn:x", "value": "1", "assigner": {"reference": "Organization/o9"}}],
         "qualification": [{"code": {"text": "Facharzt"}, "issuer": {"reference": SENDER}},
                           {"code": {"text": "Zweitqualifikation"}, "issuer": {"reference": "Organization/o9", "display": "Kammer"}}]},
        {"resourceType": "Organization", "id": "org", "name": "Studienzentrale", "partOf": {"reference": SENDER},
         "endpoint": [{"reference": "Endpoint/e1"}], "contact": [{"name": {"family": "Kontakt"}}]},
        {"resourceType": "Organization", "id": "unused", "name": "nobody"}]
    sc["performer"] = [{"reference": "#doctor"}]
    sc["organization"] = [{"reference": "#org"}]


def _rc_contained_qr(sc):
    """QuestionnaireResponse / Provenance / PractitionerRole / RelatedPerson with sender references at depth"""
    sc["contained"] = [
        {"resourceType": "QuestionnaireResponse", "id": "qr", "status": "completed", "questionnaire": "#q",
         "subject": {"reference": "Patient/p1"}, "author": {"reference": "#role"}, "source": {"reference": SENDER, "display": "Pat"},
         "item": [{"linkId": "1", "answer": [{"valueReference": {"reference": SENDER}},
                                             {"valueString": "ja", "item": [{"linkId": "1.1", "answer": [{"valueReference": {"reference": "Patient/p1"}}]}]}]}]},
        {"resourceType": "Questionnaire", "id": "q", "status": "active"},
        {"resourceType": "PractitionerRole", "id": "role", "practitioner": {"reference": "Practitioner/x"},
         "organization": {"reference": "#"}, "location": [{"reference": SENDER}]},
        {"resourceType": "Provenance", "id": "signing", "target": [{"reference": "#"}], "recorded": "2025-01-01T00:00:00Z",
         "agent": [{"who": {"reference": SENDER}, "onBehalfOf": {"reference": "#role"}}],
         "entity": [{"role": "source", "what": {"reference": "DocumentReference/d1"}}]},
        {"resourceType": "RelatedPerson", "id": "rp", "patient": {"reference": SENDER}, "name": [{"family": "Mutter"}]}]
    sc["sourceReference"] = {"reference": "#qr"}
    sc["provision"]["actor"] = [{"role": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                                                      "code": "PRCP"}]}, "reference": {"reference": "#rp"}}]


def _rc_allempty_ext(sc):
    sc["extension"] += [{"url": "http://example.org/c", "valueCoding": {"system": "", "code": ""}},
                        {"url": "http://example.org/cc", "valueCodeableConcept": {"text": "", "coding": [{"display": ""}]}},
                        {"url": "http://example.org/i", "valueIdentifier": {"system": "", "value": ""}},
                        {"url": "http://example.org/p", "valuePeriod": {"start": ""}},
                        {"url": "http://example.org/r", "valueReference": {"display": ""}},
                        {"url": "http://example.org/partial", "valueCoding": {"system": "", "code": "c", "display": ""}}]
    status = sc["extension"][0]["extension"][1]
    status["valueCoding"] = {"system": "", "code": ""}
    sc["extension"][0]["extension"][0]["valueReference"]["display"] = "Studie X"


def _rc_domain_display(sc):
    sc["extension"][0]["extension"][0]["valueReference"]["display"] = "Studie X"


NASTY = "MTB#7 ü €\U0001F600\x01:|?/%\\"

# name -> (branch, input, mutation of the parsed input)
SCENARIOS = {
    # R24 follow-up therapies (reference outputs: tests/test_fix3_py_onco.py)
    "R24-further-split": ("oncology", PLAN, fu12([therapy([X, Y]), therapy([Z], end="2026-01-05", reason="A")],
                                                [therapy(**A), therapy(**B)])),
    "R24-further-split-reversed": ("oncology", PLAN, fu12([therapy([X, Y]), therapy([Z], end="2026-01-05", reason="A")],
                                                         [therapy(**B), therapy(**A)])),
    "R24-merge-plus-subset": ("oncology", PLAN, fu12([therapy(**A), therapy(**B)],
                                                    [therapy([X, Y], end="2026-04-01", reason="E"), therapy([X], end="2026-02-02", reason="A")])),
    "R24-merge-plus-subset-reversed": ("oncology", PLAN, fu12([therapy(**A), therapy(**B)],
                                                             [therapy([X], end="2026-02-02", reason="A"), therapy([X, Y], end="2026-04-01", reason="E")])),
    "R24-same-subs-conflict": ("oncology", PLAN, fu12([therapy(**A), therapy(**B)],
                                                     [therapy([Y], end="2026-04-01", reason="E"), therapy([Y], end="2026-04-02", reason="P")])),
    "R24-same-subs-identical": ("oncology", PLAN, fu12([therapy(**A), therapy(**B)],
                                                      [therapy([Y], end="2026-04-01", reason="E"), therapy([Y], end="2026-04-01", reason="E")])),
    "R24-names-normalised": ("oncology", PLAN, fu12([therapy([], names=["Alpha"]), therapy([], names=["Beta"])],
                                                   [therapy([], names=["  ALPHA "], end="2026-04-01", reason="E")])),
    "R24-split-continues-single": ("oncology", PLAN, fu12([therapy([X, Y])],
                                                         [therapy([X, Y], end="2026-03-01", reason="E"), therapy([Z], end="2026-01-05", reason="A")])),
    "R24-plus-in-name": ("oncology", PLAN, followups(fu("2026-01-10", therapy([], names=["A+B"], end="2026-02-01", reason="A"),
                                                        therapy([], names=["A", "B"])))),
    "R24-three-way-regroup": ("oncology", PLAN, fu12([therapy([X, Y]), therapy([Z])],
                                                    [therapy([X], end="2026-02-01", reason="A", response="PD"),
                                                     therapy([Y, Z], end="2026-03-01", reason="E", response="CR"),
                                                     therapy([Z], end="2026-03-05", reason="P")])),
    "R24-single-superset-after-split": ("oncology", PLAN, fu12([therapy(**A), therapy(**B)], [therapy([X, W], end="2026-04-01", reason="E")])),
    "R24-note-spellings": ("oncology", PLAN, fu12([therapy([], names=["Alpha", "beta"])], [therapy([], names=["ALPHA", "Beta  ", "Gamma"])])),
    "R24-split-backslash-name": ("oncology", PLAN, followups(fu("2026-01-10", therapy([], names=["a\\+b"], end="2026-02-01", reason="A"),
                                                                therapy([], names=["a\\", "b"])))),
    # R43 meta.source percent-encoding
    "R43-source-unicode-onco": ("oncology", SV, local_case_id(NASTY)),
    "R43-source-unicode-test": ("oncology", SV, local_case_id(NASTY, "test")),
    "R43-source-unicode-rd": ("rare-disease", RD, local_case_id("a:b|c#d eß")),
    "R43-source-unicode-grz": ("grz", GRZ, local_case_id("G#1|x €", "followup", grz=True)),
    # PLACEHOLDERS (German placeholder study names / ids)
    "PH-plan-full": ("oncology", PLAN, lambda d: None),
    "PH-onco-study-names": ("oncology", PLAN, onco_studies(" Unbekannt ", "k. A.", "Keine Angabe")),
    "PH-onco-unknown-study": ("oncology", PLAN, onco_unknown_study("keine Angabe", " K.A. ")),
    "PH-onco-unknown-real": ("oncology", PLAN, onco_unknown_study("Basket", "n.a.")),
    "PH-rd-studies": ("rare-disease", RD, rd_studies("n.a.", "keine Angabe", " Unbekannt ")),
    "PH-rd-unknown-name-equals-id": ("rare-disease", RD, rd_studies("K.A.", "Basket X", "Basket X")),
    # R06 GRZ Organizations by value
    "R06-grz-addition-other-lab": ("grz", GRZ, grz_sub(submissionType="addition", submissionDate="2026-06-01", labName="Other Lab",
                                                      genomicDataCenterId="GRZXXX9", clinicalDataNodeId="KDKXXX9")),
    # R26 rare-disease ids
    "R26-rd-therapy-suffix-id": ("rare-disease", RD, rd_suffixed("recommendedTherapies", "therapy")),
    "R26-rd-study-suffix-id": ("rare-disease", RD, rd_suffixed("recommendedStudies", "study")),
    "R26-rd-variant-colon-id": ("rare-disease", RDV, rd_variants(_var_colon)),
    "R26-rd-variant-hash0-id": ("rare-disease", RDV, rd_variants(_var_hash0)),
    "R26-rd-variant-empty-id": ("rare-disease", RDV, rd_variants(_var_empty)),
    "R26-rd-variant-triple": ("rare-disease", RDV, rd_variants(_var_triple)),
    # R30 follow-up diagnoses whose code is empty after normalisation
    "R30-icd-blank-only": ("oncology", FU, diagnoses(dx(" ", version="2025"))),
    "R30-icd-blank-plus-valid": ("oncology", FU, diagnoses(dx("C187", version="2025"), dx(" "))),
    "R30-dimdi-tab": ("oncology", FU, diagnoses(dx("\t", DIMDI))),
    "R30-empty-system-blank": ("oncology", FU, diagnoses(dx(" ", ""))),
    "R30-no-system-blank": ("oncology", FU, diagnoses(dx("   ", None))),
    "R30-icd-marks-only": ("oncology", FU, diagnoses(dx(" +† "))),
    "R30-nbsp-alpha": ("oncology", FU, diagnoses(dx(" ", ALPHA))),
    "R30-nbsp-icd": ("oncology", FU, diagnoses(dx(" ", ICD))),
    "R30-nbsp-icd-code": ("oncology", FU, diagnoses(dx(" c187 ", ICD, version="2025"))),
    "R30-flag-false-blank": ("oncology", FU, diagnoses(dx(" "), flag=False)),
    "R30-xsys-same-code": ("oncology", FU, diagnoses(dx("+", SNOMED), dx("+", ICD))),
    "R30-xsys-later-follow-up": ("oncology", FU, both_fu(diagnoses(dx("+", ALPHA)), diagnoses(dx("+", ICD), k=1))),
    # R39 sender-system references inside kept contained resources
    "R39-contained-sender-refs": ("oncology", CONSENT, scope(_rc_contained_sender)),
    "R39-contained-deep-refs": ("oncology", CONSENT, scope(_rc_contained_qr)),
    # R53 extension values
    "R53-allempty-typed-ext": ("oncology", CONSENT, scope(_rc_allempty_ext)),
    "R53-domain-display": ("oncology", CONSENT, scope(_rc_domain_display)),
}
RAW_CHECK = ["R53-allempty-typed-ext", "R53-domain-display", "R39-contained-sender-refs", "R39-contained-deep-refs"]


def scenario(name):
    branch, path, fn = SCENARIOS[name]
    dk = loads(Path(path).read_text(encoding="utf-8"))
    fn(dk)
    return branch, dk


# ---- offline: the map text --------------------------------------------------------------------------------------------
def _map(name):
    return (FML / name).read_text(encoding="utf-8")


PLACEHOLDER_RE = "'^(|n/a|na|unknown|-|unbekannt|k[.]a[.]|k[.] a[.]|keine angabe|n[.]a[.])$'"


def test_placeholders_regex_in_both_maps():
    for name, n in (("OncoPlanFollowUp.map", 15), ("DatenkranzRareDiseaseToMii.map", 6)):
        text = _map(name)
        assert "'^(|n/a|na|unknown|-)$'" not in text, name
        assert text.count(PLACEHOLDER_RE) == n, name
    # the regex is Python's PLACEHOLDER_NAMES, trimmed and lower-cased
    from genomde2fhir.builders.rd.careplan import PLACEHOLDER_NAMES
    rx = re.compile(PLACEHOLDER_RE.strip("'"))
    assert all(rx.match(p) for p in PLACEHOLDER_NAMES)
    for real in ("kxa.", "k.a", "keine  angabe", "studie x", "na."):
        assert not rx.match(real), real


def test_r43_meta_source_expression_in_every_main_map():
    for name in ("DatenkranzGrzToMii.map", "DatenkranzOncologyToMii.map", "DatenkranzRareDiseaseToMii.map"):
        line = next(x for x in _map(name).splitlines() if "msx.value = ('urn:genomde2fhir:submission:'" in x)
        assert line.count(".encode('hex').upper().replaceMatches('(..)', '$1 ').trim().split(' ')") == 4, name
        assert line.count("'^(2[1246-9A-E]|3[0-9B-E]|[4-6][0-9A-F]|7[0-9ABDE])$'") == 4, name
        assert "|test" not in line and ".replace('%', '%25')" not in line, name


def test_r43_kept_hex_pairs_are_python_safe_set():
    """the kept byte pairs of the recipe are exactly the bytes source_component keeps"""
    rx = re.compile(r"^(2[1246-9A-E]|3[0-9B-E]|[4-6][0-9A-F]|7[0-9ABDE])$")
    for b in range(256):
        pair = f"{b:02X}"
        kept = bool(rx.match(pair))
        assert kept == (b < 128 and source_component(chr(b)) == chr(b)), pair


def test_r24_reserve_group_mirrors_therapy_ids():
    text = _map("OncoPlanFollowUp.map")
    grp = text[text.index("group OncoPlanReserveFuTherapies("):text.index("group OncoPlanEmit(")]
    assert "ftt:" not in grp and "ftp:" not in grp                    # no 'taken' check, no part register
    assert "replaceMatches('^ | $', '').lower()" in grp                 # normalised names (round 4: str.split() whitespace)
    assert ".replace('+', '\\\\+')" in grp                              # suffix escaping
    assert "value < %sk" in grp                                         # earlier = reported by earlier follow-ups
    assert "therapyResponseSource" in grp                               # attribute variants
    assert "followup._FollowUp.therapy_ids" in text and "_FollowUp.therapy_id)" not in text
    assert "the later entry wins" not in text


def test_r06_lab_organization_keyed_by_name():
    text = _map("DatenkranzGrzToMii.map")
    assert "('org:lab:' & %v) as role" in text and "('org:lab') as role" not in text
    assert "('org:genomic-data-center:' & %v) as role" in text and "('org:clinical-data-node:' & %v) as role" in text


def test_r26_rd_ids_from_produced_ids():
    text = _map("DatenkranzRareDiseaseToMii.map")
    assert "%rids.parameter.where(value = %base)" in text
    assert "take(%i).where(identifier = %rt.identifier)" not in text and "take(%i).where(identifier = %rs.identifier)" not in text
    for kind in ("small", "cnv", "sv"):
        assert f"'variant-dup:{kind}:' & %base & ':' & %i.toString(), 'variant:{kind}:' & %base" in text


def test_r53_extension_value_written_once():
    grp = _map("DatenkranzCommon.map")
    grp = grp[grp.index("group DkRcExtension("):]
    grp = grp[:grp.index("\n}")]
    assert "v.hasValue()" not in grp and '"value-other"' not in grp
    assert "(v is Reference or v is CodeableConcept or v is Coding or v is Period or v is Identifier).not()" in grp


def test_r46_readme_and_docstrings_name_the_inputs():
    text = (FML / "README.md").read_text(encoding="utf-8")
    assert "3 oncology files (one each from ukdd, DNPM and NCT)" not in text
    assert "3 oncology files (NCT, DNPM, ukdd) plus 8 edge-case mutations of the NCT file" not in text
    assert "run 3 files each" not in text
    import test_fml_grz
    import test_fml_onco_molecular
    import test_fml_onco_spine
    import test_fml_rd
    assert "For 3 GRZ files" not in test_fml_grz.__doc__
    assert f"{len(test_fml_grz.FILES)} GRZ files" in " ".join(test_fml_grz.__doc__.split())
    for mod in (test_fml_onco_spine, test_fml_onco_molecular, test_fml_rd):
        for f in mod.FILES:
            assert Path(f).name in text, (mod.__name__, f)


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
    py, rep = convert(dk, name or "fix3", check_input=False)
    st, fml = mb.transform(dk, f2._RC.MAPS[branch])
    return py, rep, st, fml


def raw_transform(branch, dk):
    """the raw $transform response text (matchbox writes JSON; a duplicate key is lost by json.loads)"""
    url = f"{MB.rstrip('/')}/StructureMap/$transform?source=" + urllib.parse.quote(f2._RC.MAPS[branch])
    req = urllib.request.Request(url, data=json.dumps(dk).encode(), method="POST",
                                 headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read().decode("utf-8")


def duplicate_keys(text):
    dups = []

    def hook(pairs):
        keys = [k for k, _ in pairs]
        dups.extend(k for k, n in collections.Counter(keys).items() if n > 1)
        return dict(pairs)
    json.loads(text, object_pairs_hook=hook)
    return dups


@needs_mb
@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario_parity(mb, name):
    f2.assert_parity(*both(mb, name))


@needs_mb
@pytest.mark.parametrize("name", RAW_CHECK + ["R24-further-split", "R43-source-unicode-onco"])
def test_raw_response_has_no_duplicate_key(mb, name):
    branch, dk = scenario(name)
    assert duplicate_keys(raw_transform(branch, dk)) == []


@needs_mb
def test_r53_empty_in_datatypes_raw_has_no_duplicate_key(mb):
    """the round-2 regression scenario: valueReference / valueCoding were written twice (whole + typed copy)"""
    branch, dk = f2.scenario("R53-empty-in-datatypes")
    assert duplicate_keys(raw_transform(branch, dk)) == []


def _procs(b):
    """{coded substances: (status, end, outcome codes)} of the follow-up Procedures (several per set: a sorted list)"""
    out = collections.defaultdict(list)
    ms = collections.defaultdict(list)
    for e in b["entry"]:
        r = e["resource"]
        if r["resourceType"] == "MedicationStatement" and r.get("partOf"):
            ms[r["partOf"][0]["reference"]].append(r["medicationCodeableConcept"]["coding"][0]["code"])
    for e in b["entry"]:
        r = e["resource"]
        if r["resourceType"] == "Procedure" and r["meta"]["profile"][0].endswith("mii-pr-mtb-systemische-therapie"):
            out[tuple(sorted(ms[e["fullUrl"]]))].append((r["status"], (r.get("performedPeriod") or {}).get("end"),
                                                         [c["code"] for c in (r.get("outcome") or {}).get("coding", [])]))
    return {k: sorted(v) for k, v in out.items()}


@needs_mb
def test_r24_further_split_keeps_each_substance_state(mb):
    for name in ("R24-further-split", "R24-further-split-reversed"):
        _, _, st, fml = both(mb, name)
        assert _procs(fml) == {(X, Y): [("in-progress", None, [])], (Z,): [("stopped", "2026-01-05", ["A"])],
                               (X,): [("stopped", "2026-02-01", ["A"])], (Y,): [("completed", "2026-03-01", ["E"])]}, name


@needs_mb
def test_r24_merge_plus_subset_and_conflict(mb):
    for name in ("R24-merge-plus-subset", "R24-merge-plus-subset-reversed"):
        _, _, _, fml = both(mb, name)
        assert _procs(fml) == {(X,): [("stopped", "2026-02-02", ["A"])], (Y,): [("completed", "2026-03-01", ["E"])],
                               (X, Y): [("completed", "2026-04-01", ["E"])]}, name
    _, _, _, fml = both(mb, "R24-same-subs-conflict")
    assert _procs(fml)[(Y,)] == [("completed", "2026-03-01", ["E"]), ("completed", "2026-04-01", ["E"]),
                                 ("stopped", "2026-04-02", ["P"])]
    _, _, _, fml = both(mb, "R24-same-subs-identical")
    assert _procs(fml)[(Y,)] == [("completed", "2026-04-01", ["E"])]


@needs_mb
def test_r24_names_and_plus(mb):
    def notes(b):
        return sorted((r["status"], " ".join(n["text"] for n in r.get("note", [])))
                      for r in f2.resources(b, "Procedure", "mii-pr-mtb-systemische-therapie"))
    _, _, _, fml = both(mb, "R24-names-normalised")
    assert notes(fml) == [("completed", "Substanzen ohne ATC-Code: Alpha"), ("in-progress", "Substanzen ohne ATC-Code: Beta")]
    _, _, _, fml = both(mb, "R24-plus-in-name")
    assert notes(fml) == [("in-progress", "Substanzen ohne ATC-Code: A, B"), ("stopped", "Substanzen ohne ATC-Code: A+B")]
    _, _, _, fml = both(mb, "R24-note-spellings")
    assert notes(fml) == [("in-progress", "Substanzen ohne ATC-Code: Alpha, beta, Gamma")]


@needs_mb
@pytest.mark.parametrize("name", ["R24-three-way-regroup", "R24-further-split", "R24-merge-plus-subset", "R24-same-subs-conflict"])
def test_r24_every_array_order_matches_python(mb, name):
    branch, dk = scenario(name)
    fus = dk["followUp"]["followUpOds"]
    for orders in itertools.product(*(itertools.permutations(f["therapies"]) for f in fus)):
        d = copy.deepcopy(dk)
        for f, o in zip(d["followUp"]["followUpOds"], orders):
            f["therapies"] = copy.deepcopy(list(o))
        f2.assert_parity(*both(mb, branch=branch, dk=d))


@needs_mb
@pytest.mark.parametrize("name", [n for n in SCENARIOS if n.startswith("R43-")])
def test_r43_meta_source_equals_python(mb, name):
    py, _, _, fml = both(mb, name)
    want = {r.get("meta", {}).get("source") for r in f2.resources(py)}
    assert len(want) == 1 and None not in want, want
    src = next(iter(want))
    assert src.startswith(SOURCE_PREFIX) and src.isascii() and not re.search(r"[\s#|?]", src)
    assert {r.get("meta", {}).get("source") for r in f2.resources(fml)} == want


@needs_mb
def test_placeholder_study_not_noted_or_titled(mb):
    _, _, _, fml = both(mb, "PH-plan-full")
    notes = [n["text"] for r in f2.resources(fml, "ServiceRequest") for n in r.get("note", [])]
    assert not [n for n in notes if n.startswith("Empfohlene Studie (nicht identifiziert)")]   # 'unbekannt' / 'n/a'
    _, _, _, fml = both(mb, "PH-onco-study-names")
    titles = [r.get("title") for r in f2.resources(fml, "ResearchStudy")]
    assert not {" Unbekannt ", "k. A.", "Keine Angabe"} & set(titles)
    _, _, _, fml = both(mb, "PH-rd-unknown-name-equals-id")
    notes = [n["text"] for r in f2.resources(fml, "ServiceRequest") for n in r.get("note", [])]
    assert "Empfohlene Studie (nicht identifiziert): Basket X Basket X" in notes


def _key(r):
    return next(i["value"] for i in r["identifier"] if i["system"] == f2.KEY)


@needs_mb
def test_r06_lab_organization_per_lab_name(mb):
    def orgs(**kw):
        dk = loads(GRZ.read_text(encoding="utf-8"))
        dk["submission"].update(kw)
        _, _, st, fml = both(mb, branch="grz", dk=dk)
        assert st == 200
        return {o["name"]: _key(o) for o in f2.resources(fml, "Organization")}
    initial = orgs(submissionType="initial", submissionDate="2026-01-01")
    other = orgs(submissionType="addition", submissionDate="2026-06-01", labName="Other Lab")
    same = orgs(submissionType="addition", submissionDate="2026-07-01")
    assert initial["GRZ-Lab-Synth"] != other["Other Lab"]                     # an addition from another lab: its own Organization
    assert initial["GRZ-Lab-Synth"] == same["GRZ-Lab-Synth"]                  # the same lab: the same Organization
    for k in initial:
        if not k.startswith("GRZ-Lab"):
            assert initial[k] == other.get(k, initial[k]) or k not in other


@needs_mb
def test_r06_hapi_initial_study_keeps_its_lab(mb):
    """initial ('GRZ-Lab-Synth') then an addition from 'Other Lab' into HAPI: the initial study's performer keeps its name"""
    case = f"FIX3-R06-{uuid.uuid4().hex[:10]}"
    hapi = Hapi(HAPI)
    study_keys = {}
    for stype, date, lab in (("initial", "2026-01-01", "GRZ-Lab-Synth"), ("addition", "2026-06-01", "Other Lab")):
        dk = loads(GRZ.read_text(encoding="utf-8"))
        dk["submission"].update(localCaseId=case, submissionType=stype, submissionDate=date, labName=lab)
        _, _, st, fml = both(mb, branch="grz", dk=dk)
        assert st == 200
        [study] = [r for r in f2.resources(fml, "Procedure") if r["meta"]["profile"][0].endswith("-genomic-study")]
        study_keys[stype] = _key(study)
        ok, resp = hapi.transaction(fml)
        assert ok, json.dumps(resp)[:300]
    assert study_keys["initial"] != study_keys["addition"]
    for stype, lab in (("initial", "GRZ-Lab-Synth"), ("addition", "Other Lab")):
        q =f"{HAPI.rstrip('/')}/Procedure?identifier={urllib.parse.quote(f2.KEY + '|' + study_keys[stype])}&_include=Procedure:performer"
        with urllib.request.urlopen(urllib.request.Request(q, headers={"Accept": "application/fhir+json", "Cache-Control": "no-cache"}),
                                    timeout=120) as r:
            bundle = json.loads(r.read())
        names = [e["resource"].get("name") for e in bundle.get("entry", []) if e["resource"]["resourceType"] == "Organization"]
        assert names == [lab], (stype, names)


@needs_mb
@pytest.mark.parametrize("name", [n for n in SCENARIOS if n.startswith("R30-")])
def test_r30_flag_and_conditions_match_python(mb, name):
    py, _, st, fml = both(mb, name)
    assert st == 200

    def flags(b):
        return sorted((r.get("effectiveDateTime"), x["valueBoolean"]) for r in f2.resources(b, "Observation")
                      for x in r.get("extension", []) if x["url"].endswith("mvgs-ex-metachronous-tumor"))

    def conds(b):
        return sorted((c["code"]["coding"][0]["system"], c["code"]["coding"][0]["code"])
                      for c in f2.resources(b, "Condition", "mii-pr-onko-diagnose-primaertumor") if c.get("recordedDate", "").startswith("2025-05-1"))
    assert flags(fml) == flags(py) and conds(fml) == conds(py)


@needs_mb
def test_r30_blank_icd_code_keeps_the_flag(mb):
    for name in ("R30-icd-blank-only", "R30-icd-blank-plus-valid", "R30-dimdi-tab", "R30-empty-system-blank", "R30-no-system-blank"):
        _, _, _, fml = both(mb, name)
        verlauf = next(r for r in f2.resources(fml, "Observation", "mii-pr-onko-verlauf") if r.get("effectiveDateTime") == "2025-06-01")
        assert {"url": "https://genomde.de/fhir/StructureDefinition/mvgs-ex-metachronous-tumor", "valueBoolean": True} in verlauf.get("extension", []), name
    _, _, _, fml = both(mb, "R30-nbsp-icd-code")
    assert [c["code"]["coding"][0]["code"] for c in f2.resources(fml, "Condition", "mii-pr-onko-diagnose-primaertumor")
            if c.get("recordedDate") == "2025-05-15"] == ["C18.7"]
    _, _, _, fml = both(mb, "R30-xsys-same-code")
    assert [(c["code"]["coding"][0]["system"], c["code"]["coding"][0]["code"]) for c in f2.resources(fml, "Condition", "mii-pr-onko-diagnose-primaertumor")
            if c.get("recordedDate") == "2025-05-15"] == [(SNOMED, "+")]


@needs_mb
@pytest.mark.parametrize("name", [n for n in SCENARIOS if n.startswith("R26-")])
def test_r26_rd_keys_unique_and_python_converts(mb, name):
    py, rep, st, fml = both(mb, name)
    assert rep.status == "converted" and st == 200, (rep.error, json.dumps(fml)[:300])
    keys = [_key(e["resource"]) for e in fml["entry"] if e["resource"]["resourceType"] != "Patient"]
    assert len(keys) == len(set(keys))


def _research_consent(b):
    return [r for r in f2.resources(b, "Consent") if r.get("scope", {}).get("coding", [{}])[0].get("code") == "research"][0]


def _refs(o):
    if isinstance(o, dict):
        out = [o["reference"]] if isinstance(o.get("reference"), str) else []
        return out + [x for v in o.values() for x in _refs(v)]
    if isinstance(o, list):
        return [x for v in o for x in _refs(v)]
    return []


@needs_mb
def test_r39_sender_references_inside_contained_removed(mb):
    for name in ("R39-contained-sender-refs", "R39-contained-deep-refs"):
        py, _, _, fml = both(mb, name)
        c = _research_consent(fml)
        assert all(r.startswith("#") for r in _refs(c.get("contained", []))), (name, _refs(c.get("contained", [])))
        assert c.get("contained") == _research_consent(py).get("contained"), name
    c = _research_consent(both(mb, "R39-contained-sender-refs")[3])
    doctor = next(x for x in c["contained"] if x["id"] == "doctor")
    assert doctor["qualification"][0]["issuer"] == {"display": f"{SENDER} (sender system)"}
    assert doctor["qualification"][1]["issuer"] == {"display": "Kammer"}
    assert [x["id"] for x in c["contained"]] == ["doctor", "org"]


@needs_mb
def test_r39_contained_scenario_validates_without_urn_warning(mb):
    py, _, _, fml = both(mb, "R39-contained-sender-refs")
    c = _research_consent(fml)
    assert SENDER not in json.dumps({k: v for k, v in c.items() if k != "performer"}).replace(f"{SENDER} (sender system)", "")


@needs_mb
def test_r53_all_empty_typed_extension_values_left_out(mb):
    py, _, _, fml = both(mb, "R53-allempty-typed-ext")
    c = _research_consent(fml)
    assert '""' not in json.dumps(c)
    by_url = {x["url"]: x for x in c["extension"]}
    for u in ("c", "cc", "i", "p", "r"):
        assert by_url[f"http://example.org/{u}"] == {"url": f"http://example.org/{u}"}, u
    assert by_url["http://example.org/partial"] == {"url": "http://example.org/partial", "valueCoding": {"code": "c"}}
    key = lambda x: json.dumps(x, sort_keys=True)  # noqa: E731  (the DomainReference rule runs after the others)
    assert sorted(_research_consent(py)["extension"], key=key) == sorted(c["extension"], key=key)


@needs_mb
@pytest.mark.parametrize("name", ["R24-further-split", "R26-rd-variant-colon-id", "R06-grz-addition-other-lab", "R39-contained-sender-refs"])
def test_ingest_twice_without_silent_merge(mb, name):
    _, _, st, fml = both(mb, name)
    assert st == 200
    hapi = Hapi(HAPI)
    for run in (1, 2):
        ok, resp = hapi.transaction(fml)
        assert ok, json.dumps(resp)[:300]
        statuses = [str((e.get("response") or {}).get("status", "")) for e in resp.get("entry", [])]
        assert len(statuses) == len(fml["entry"])
        if run == 2:
            assert all(s.startswith("200") for s in statuses), collections.Counter(statuses)
