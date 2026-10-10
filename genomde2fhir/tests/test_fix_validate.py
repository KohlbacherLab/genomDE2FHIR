"""Regression tests for the validate group (review findings R01 R02 R03 R04 R17 R18 R19 R20 R28 R33).

Offline: matchbox is replaced by a fake that returns OperationOutcomes shaped like matchbox-2027's (message texts and
expressions copied from real runs); the HTTP tests use a throw-away server on 127.0.0.1.
"""
import http.server
import json
import socket
import threading

import pytest

from genomde2fhir import validate as v
from genomde2fhir.validate import Hapi, Matchbox, classify_issue, validate_bundle

MII = "https://www.medizininformatik-initiative.de/fhir/ext/"
PT_PROF = MII + "modul-mtb/StructureDefinition/mii-pr-mtb-diagnose-primaertumor"
PT_ONKO = MII + "modul-onko/StructureDefinition/mii-pr-onko-diagnose-primaertumor"
TNM_K = MII + "modul-onko/StructureDefinition/mii-pr-onko-tnm-klassifikation"
TNM_T = MII + "modul-onko/StructureDefinition/mii-pr-onko-tnm-t-kategorie"
TNM_MSYM = MII + "modul-onko/StructureDefinition/mii-pr-onko-tnm-m-symbol"
EMPF = MII + "modul-mtb/StructureDefinition/mii-pr-mtb-therapieempfehlung"
NGS = MII + "modul-mtb/StructureDefinition/mii-pr-mtb-ngs-bericht"
VITAL = "https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/Vitalstatus"
PAT = "https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/PatientPseudonymisiert"
INFO = {"severity": "information", "code": "informational", "diagnostics": "Validation for profile ... passed"}
ICDO3 = "http://terminology.hl7.org/CodeSystem/icd-o-3"


def uid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


def res(n, rtype, profile=None, **kw):
    r = {"resourceType": rtype, "id": uid(n), **kw}
    if profile:
        r["meta"] = {"profile": [profile]}
    return r


def ref(n):
    return {"reference": f"urn:uuid:{uid(n)}"}


def bundle(*resources, **kw):
    return {"resourceType": "Bundle", "id": "b", "type": kw.get("type", "transaction"),
            "entry": [{"fullUrl": f"urn:uuid:{r['id']}", "resource": r,
                       "request": {"method": "PUT", "url": f"{r['resourceType']}/{r['id']}"}} for r in resources]}


def iss(expr, text, sev="error", mid=None):
    i = {"severity": sev, "code": "processing", "diagnostics": text, "expression": [expr] if expr else []}
    if mid:
        i["extension"] = [{"url": v.MESSAGE_ID_EXT, "valueCode": mid}]
    return i


def at(b, n, path=""):
    """Bundle-pass expression of entry n."""
    r = b["entry"][n]["resource"]
    return f"Bundle.entry[{n}].resource/*{r['resourceType']}/{r['id']}*/" + (f".{path}" if path else "")


class FakeMatchbox:
    """own: {resource id: [issues]} for the per-resource pass; bundle: [issues] of the whole-Bundle pass."""

    def __init__(self, own=None, bundle_issues=None, ancestors=None):
        self.own, self.bundle_issues, self.anc, self.calls = own or {}, bundle_issues or [], ancestors or {}, 0

    def validate(self, resource, profile=None):
        self.calls += 1
        issues = self.bundle_issues if resource["resourceType"] == "Bundle" else self.own.get(resource["id"], [])
        return {"resourceType": "OperationOutcome", "issue": [INFO] + issues}

    def ancestors(self, url):
        return self.anc.get(url)


def classes(result):
    return [(r["type"], i["class"], i["text"][:60]) for r in result["resources"] for i in r["issues"] if i["class"] != "info"]


def cls_of(result, needle):
    found = [i["class"] for r in result["resources"] for i in r["issues"] if needle in i["text"]]
    assert found, (needle, classes(result))
    return found[0]


# ---- R01 / R03: Bundle-only errors are content unless waived or a cascade with a real root ----------------------

BDL = [
    ("Bundle", "Constraint failed: bdl-3: 'entry.request mandatory for batch/transaction/history, otherwise prohibited'"),
    ("Bundle", "Constraint failed: bdl-7: 'FullUrl must be unique in a bundle, or else entries with the same fullUrl "
               "must have different meta.versionId (except in history bundles)'"),
    ("Bundle.type", "The value provided ('transactionx') was not found in the value set 'BundleType' "
                    "(http://hl7.org/fhir/ValueSet/bundle-type|4.0.1), and a code is required from this value set"),
    ("Bundle.entry[1].request.method", "The value provided ('BOGUS') was not found in the value set 'HTTPVerb'"),
]


@pytest.mark.parametrize("expr,text", BDL)
def test_bundle_rule_errors_fail(expr, text):
    b = bundle(res(1, "Patient", PAT), res(2, "Observation", VITAL, subject=ref(1)))
    out = validate_bundle(b, FakeMatchbox(bundle_issues=[iss(expr, text)]))
    assert out["verdict"] == "FAIL" and cls_of(out, text[:30]) == "content"


def test_bundle_rule_error_fails_even_with_unrelated_unchecked_taint():
    """R01 on oncology: an unchecked ICD-O-3 issue elsewhere must not turn a Bundle rule error into a cascade."""
    pt = res(2, "Condition", PT_PROF, subject=ref(1))
    b = bundle(res(1, "Patient", PAT), pt)
    unchecked = iss("Condition.bodySite[0].coding[0].system", f"A definition for CodeSystem '{ICDO3}' version '2019' "
                    "could not be found, so the code cannot be validated. Valid versions: 2000")
    out = validate_bundle(b, FakeMatchbox(own={pt["id"]: [unchecked]}, bundle_issues=[iss(*BDL[0])]))
    assert out["verdict"] == "FAIL"


def test_definitive_reference_errors_fail():
    """Invalid target type / multiple matches are content whatever the target's own errors (R01, R19)."""
    pt = res(2, "Condition", PT_PROF, subject=ref(1))
    vs = res(3, "Observation", VITAL, subject=ref(2))
    b = bundle(res(1, "Patient", PAT), pt, vs)
    unchecked = iss("Condition.extension[1].value.ofType(CodeableConcept)", "None of the codings provided are in the "
                    "value set 'MII VS Onkologie ICD-O-3 Morphologie' (...), and a coding from this value set is "
                    f"required) (codes = {ICDO3}#8140/3)")
    sib = iss("Condition.extension[1].value.ofType(CodeableConcept).coding[0].system", f"A definition for CodeSystem "
              f"'{ICDO3}' version '2019' could not be found, so the code cannot be validated. Valid versions: 2000",
              sev="warning")
    for text in ("Invalid Resource target type. Found Condition, but expected one of ([Group, Device, Patient, Location])",
                 f"Multiple matches in bundle for reference urn:uuid:{uid(2)}"):
        out = validate_bundle(b, FakeMatchbox(own={pt["id"]: [unchecked, sib]},
                                              bundle_issues=[iss(at(b, 2, "subject"), text)]))
        assert out["verdict"] == "FAIL" and cls_of(out, text[:20]) == "content", classes(out)


def test_slice_overflow_in_bundle_context_fails_but_documented_overlap_stays_waived():
    """R01: two TMB results in a max-1 resolve() slice; MTB-22 (Tumorzellgehalt overlap) stays waived. matchbox
    reports slice cardinality at the resource itself (expression without '.result')."""
    rep = res(2, "DiagnosticReport", NGS, subject=ref(1), result=[ref(3), ref(4)])
    b = bundle(res(1, "Patient", PAT), rep, res(3, "Observation", None), res(4, "Observation", None))
    tmb = iss(at(b, 1), f"DiagnosticReport.result:TumorMutionalBurden: max allowed = 1, but found 2 (from {NGS}|2027.0.0-ballot.1)")
    out = validate_bundle(b, FakeMatchbox(bundle_issues=[tmb]))
    assert out["verdict"] == "FAIL" and cls_of(out, "TumorMutionalBurden") == "content"
    tzg = iss(at(b, 1), f"DiagnosticReport.result:Tumorzellgehalt: max allowed = 1, but found 2 (from {NGS}|2027.0.0-ballot.1)")
    out = validate_bundle(b, FakeMatchbox(bundle_issues=[tzg]))
    assert out["verdict"] == "PASS" and cls_of(out, "Tumorzellgehalt").startswith("waived:")


# ---- R04 / R18: required non-reference slices are never dropped ------------------------------------------------

SURVEY = (f"Slice 'Observation.category:survey': a matching slice is required, but not found (from {VITAL}|2027.0.0-ballot). "
          "Note that other slices are allowed in addition to this required slice")


def _vital_bundle():
    pt = res(2, "Condition", PT_PROF, subject=ref(1))
    vs = res(3, "Observation", VITAL, subject=ref(1),
             category=[{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}])
    unchecked = iss("Condition.bodySite[0].coding[0].system", f"A definition for CodeSystem '{ICDO3}' version '2019' "
                    "could not be found, so the code cannot be validated. Valid versions: 2000")
    return bundle(res(1, "Patient", PAT), pt, vs), {pt["id"]: [unchecked], vs["id"]: [iss("Observation", SURVEY)]}


@pytest.mark.parametrize("bundle_level", [True, False])
def test_missing_coding_slice_fails_regardless_of_other_resources(bundle_level):
    b, own = _vital_bundle()
    bundle_issues = [iss(at(b, 2), SURVEY)]   # the Bundle pass reports it again
    out = validate_bundle(b, FakeMatchbox(own=own, bundle_issues=bundle_issues), bundle_level=bundle_level)
    assert out["verdict"] == "FAIL" and cls_of(out, "category:survey") == "content"


VITAL_SLICE = f"Slice 'Observation.value[x].coding:Vitalstatus': a matching slice is required, but not found (from {VITAL})"


def test_missing_value_coding_slice_fails_in_oncology_context():
    b, own = _vital_bundle()
    vs = b["entry"][2]["resource"]
    vs["valueCodeableConcept"] = {"coding": [{"system": "http://snomed.info/sct", "code": "438949009"}]}
    own[vs["id"]] = [iss("Observation.value.ofType(CodeableConcept)", VITAL_SLICE)]
    out = validate_bundle(b, FakeMatchbox(own=own, bundle_issues=[iss(at(b, 2, "value.ofType(CodeableConcept)"), VITAL_SLICE)]))
    assert out["verdict"] == "FAIL"
    out = validate_bundle(b, FakeMatchbox(own=own), bundle_level=False)
    assert out["verdict"] == "FAIL"


PRIMAER = (f"Slice 'MedicationRequest.reasonReference:Primaertumor': a matching slice is required, but not found "
           f"(from {EMPF}|2027.0.0-ballot.1). Note that other slices are allowed in addition to this required slice")


def _empf_bundle(pt_issues):
    pt = res(2, "Condition", PT_PROF, subject=ref(1))
    mr = res(3, "MedicationRequest", EMPF, subject=ref(1), reasonReference=[ref(2)])
    b = bundle(res(1, "Patient", PAT), pt, mr)
    return b, FakeMatchbox(own={pt["id"]: pt_issues, mr["id"]: [iss("MedicationRequest", PRIMAER)]},
                           bundle_issues=[iss(at(b, 2), PRIMAER)])


def test_reference_slice_judged_by_its_target():
    unchecked = [iss("Condition.bodySite[0].coding[0].system", f"A definition for CodeSystem '{ICDO3}' version '2019' "
                     "could not be found, so the code cannot be validated. Valid versions: 2000")]
    content = [iss("Condition.code", "Condition.code: minimum required = 1, but only found 0")]
    for pt_issues, want, verdict in ((unchecked, "unchecked", "INCONCLUSIVE"), ([], "content", "FAIL"),
                                     (content, "cascade", "FAIL")):
        b, mb = _empf_bundle(pt_issues)
        out = validate_bundle(b, mb)
        assert cls_of(out, "reasonReference:Primaertumor") == want and out["verdict"] == verdict, classes(out)


def test_reference_slice_without_bundle_context_is_kept_unchecked():
    b, mb = _empf_bundle([])
    out = validate_bundle(b, mb, bundle_level=False)
    assert cls_of(out, "reasonReference:Primaertumor") == "unchecked" and out["verdict"] == "INCONCLUSIVE"


def test_reference_slice_on_absent_element_is_own_content():
    pt = res(2, "Condition", PT_PROF, subject=ref(1))
    mr = res(3, "MedicationRequest", EMPF, subject=ref(1))   # no reasonReference at all
    b = bundle(res(1, "Patient", PAT), pt, mr)
    out = validate_bundle(b, FakeMatchbox(own={mr["id"]: [iss("MedicationRequest", PRIMAER)]}), bundle_level=False)
    assert out["verdict"] == "FAIL"


# ---- R19: taint only from own content/source/waived errors (followed through references) ------------------------

def _tnm(t_issues=(), pt_issues=(), t_refs_pt=True, t_profile=TNM_T, noise=True):
    pt = res(2, "Condition", PT_PROF, subject=ref(1))
    t = res(3, "Observation", t_profile, subject=ref(1), **({"focus": [ref(2)]} if t_refs_pt else {}))
    k = res(4, "Observation", TNM_K, subject=ref(1), hasMember=[ref(3)])
    b = bundle(res(1, "Patient", PAT), pt, t, k)
    choices = ", ".join(MII + f"modul-onko/StructureDefinition/mii-pr-onko-tnm-{x}"
                        for x in ("a-symbol", "m-kategorie", "m-symbol", "n-kategorie", "t-kategorie"))
    bi = [iss(at(b, 3, "hasMember[0]"), f"Unable to find a profile match for urn:uuid:{uid(3)} among choices: {choices}",
              mid="Reference_REF_CantMatchChoice")]
    if noise:   # matchbox's report of why T fails a candidate profile it does not declare
        bi += [iss(at(b, 2, "code"), f"The pattern [system http://loinc.org, code 42030-7, and display 'null'] defined in "
                                     f"the profile {TNM_MSYM}|2027.0.0-ballot.1 not found. Issues: [...]"),
               iss(at(b, 2, "value.ofType(CodeableConcept)"), "None of the codings provided are in the value set 'MII VS "
                   "Onkologie TNM m-Symbol' (...), and a coding from this value set is required) "
                   "(codes = https://www.uicc.org/resources/tnm#T3)")]
    return b, FakeMatchbox(own={pt["id"]: list(pt_issues), t["id"]: list(t_issues)}, bundle_issues=bi,
                           ancestors={MII + "modul-onko/StructureDefinition/mii-pr-onko-tod": {
                               MII + "modul-onko/StructureDefinition/mii-pr-onko-tod", v.BASE_SD + "Observation"}})


UNCHECKED_PT = [iss("Condition.extension[1].value.ofType(CodeableConcept)", "None of the codings provided are in the "
                    "value set 'MII VS Onkologie ICD-O-3 Morphologie' (...), and a coding from this value set is "
                    f"required) (codes = {ICDO3}#8253/2)"),
                iss("Condition.extension[1].value.ofType(CodeableConcept).coding[0].system", "A definition for "
                    f"CodeSystem '{ICDO3}' version '2019' could not be found, so the code cannot be validated. "
                    "Valid versions: 2000", sev="warning")]


def test_reference_failure_through_unchecked_chain_is_unchecked_not_cascade():
    """TNM-Klassifikation.hasMember -> T-Kategorie -> focus -> Primaertumor (ICD-O-3 2019 unchecked)."""
    b, mb = _tnm(pt_issues=UNCHECKED_PT)
    out = validate_bundle(b, mb)
    assert cls_of(out, "Unable to find a profile match") == "unchecked"
    assert cls_of(out, "The pattern") == "candidate" and cls_of(out, "TNM m-Symbol") == "candidate"
    assert out["verdict"] == "INCONCLUSIVE"


def test_reference_failure_to_clean_target_fails_although_noise_is_attached():
    """Candidate-profile noise at the target does not taint it (R19: onko-tod / Verlauf.hasMember)."""
    b, mb = _tnm(t_refs_pt=False, pt_issues=UNCHECKED_PT)
    out = validate_bundle(b, mb)
    assert cls_of(out, "Unable to find a profile match") == "content" and out["verdict"] == "FAIL"


def test_reference_failure_to_target_with_content_error_is_cascade_and_root_fails():
    b, mb = _tnm(t_issues=[iss("Observation.value.ofType(CodeableConcept)", "Observation.value[x]: minimum required = 1, but only found 0")])
    out = validate_bundle(b, mb)
    assert cls_of(out, "Unable to find a profile match") == "cascade" and out["verdict"] == "FAIL"


def test_reference_to_wrong_kind_of_target_fails_even_if_target_is_unchecked():
    """The target declares a profile that is not (and does not derive from) any allowed target profile."""
    b, mb = _tnm(pt_issues=UNCHECKED_PT, t_profile=MII + "modul-onko/StructureDefinition/mii-pr-onko-tod")
    out = validate_bundle(b, mb)
    assert cls_of(out, "Unable to find a profile match") == "content" and out["verdict"] == "FAIL"


def test_derived_target_profile_is_plausible():
    """mtb-diagnose-primaertumor derives from onko-diagnose-primaertumor (listed in the choices)."""
    pt = res(2, "Condition", PT_PROF, subject=ref(1))
    obs = res(3, "Observation", None, subject=ref(1), focus=[ref(2)])
    b = bundle(res(1, "Patient", PAT), pt, obs)
    mb = FakeMatchbox(own={pt["id"]: UNCHECKED_PT}, ancestors={PT_PROF: {PT_PROF, PT_ONKO, v.BASE_SD + "Condition"}},
                      bundle_issues=[iss(at(b, 2, "focus[0]"), f"Unable to find a profile match for urn:uuid:{uid(2)} "
                                                               f"among choices: {PT_ONKO}")])
    assert cls_of(validate_bundle(b, mb), "Unable to find a profile match") == "unchecked"


def test_mutual_reference_failures_without_root_fail():
    a = res(2, "Observation", TNM_T, subject=ref(1), hasMember=[ref(3)])
    c = res(3, "Observation", TNM_T, subject=ref(1), hasMember=[ref(2)])
    b = bundle(res(1, "Patient", PAT), a, c)
    bi = [iss(at(b, 1, "hasMember[0]"), f"Unable to find a profile match for urn:uuid:{uid(3)} among choices: {TNM_T}"),
          iss(at(b, 2, "hasMember[0]"), f"Unable to find a profile match for urn:uuid:{uid(2)} among choices: {TNM_T}")]
    out = validate_bundle(b, FakeMatchbox(bundle_issues=bi))
    assert out["verdict"] == "FAIL" and {i["class"] for r in out["resources"] for i in r["issues"]} >= {"content"}


def test_source_and_waived_roots_taint():
    hgvs = iss("Observation.component[0].value.ofType(CodeableConcept).coding[0].code",
               "Unknown code 'c.218A>G' in the CodeSystem 'http://varnomen.hgvs.org' version '2.0'")
    b, mb = _tnm(t_issues=[hgvs], noise=False)
    out = validate_bundle(b, mb, source={"variants": [{"cDNAChange": "c.218A>G"}]})
    assert cls_of(out, "c.218A>G") == "source" and cls_of(out, "Unable to find a profile match") == "cascade"
    assert out["verdict"] == "DATA-QUALITY"


# ---- R17: source only for verbatim external codes that are whole input values ---------------------------------

def _err(text, expr="Observation.value.ofType(CodeableConcept).coding[0].code"):
    return iss(expr, text)


SRC = {"vitalStatus": "living", "molecular": {"x": 1}, "variant": {"cDNAChange": "c.218A>G", "note": "see c.230G>A here",
                                                                    "transcript": {"code": "NM_000546.6"}},
       "snomed": 1229893007}


@pytest.mark.parametrize("text,want", [
    ("Unknown code 'living' in the CodeSystem 'https://www.medizininformatik-initiative.de/fhir/core/modul-person/"
     "CodeSystem/Vitalstatus' version '2027.0.0-ballot'", "content"),           # ConceptMap passthrough into an MII CS
    ("Unknown code 'molecular' in the CodeSystem 'http://snomed.info/sct' version 'x'", "content"),   # a JSON key only
    ("None of the codings provided are in the value set 'HGVS' (...), and a coding from this value set is required) "
     "(codes = https://varnomen.hgvs.org#c.218A>G)", "content"),                 # converter wrote a wrong system URI
    ("Unknown code 'c.230G>A' in the CodeSystem 'http://varnomen.hgvs.org' version '2.0'", "content"),   # substring only
    ("Unknown code 'c.218A>G' in the CodeSystem 'http://varnomen.hgvs.org' version '2.0'", "source"),
    ("None of the codings provided are in the value set 'HGVS' (...), and a coding from this value set is required) "
     "(codes = http://varnomen.hgvs.org#NM_000546.6:c.218A>G)", "source"),       # transcript + notation, both input values
    ("Unknown code 'NM_999999.1:c.218A>G' in the CodeSystem 'http://varnomen.hgvs.org' version '2.0'", "content"),
    ("Unknown code '1229893007' in the CodeSystem 'http://snomed.info/sct' version 'http://snomed.info/sct/900000000000207008/"
     "version/20250201' (International Edition)", "source"),                     # numeric input value
])
def test_source_rule(text, want):
    assert classify_issue(_err(text), "", v._source_values(SRC)) == want
    assert classify_issue(_err(text), "", json.dumps(SRC)) == want   # former signature: the input as JSON text


# ---- R20: dangling urn:uuid references ---------------------------------------------------------------------------

def test_dangling_reference_warning_is_content():
    vs = res(2, "Observation", VITAL, subject=ref(99))
    b = bundle(res(1, "Patient", PAT), vs)
    w = iss(at(b, 1, "subject"), f"URN reference is not locally contained within the bundle urn:uuid:{uid(99)}", sev="warning")
    out = validate_bundle(b, FakeMatchbox(bundle_issues=[w]))
    assert out["verdict"] == "FAIL" and cls_of(out, "not locally contained") == "content"
    assert sum(uid(99) in i["text"] for r in out["resources"] for i in r["issues"]) == 1   # no duplicate local finding


def test_dangling_reference_found_locally_when_matchbox_is_silent():
    vs = res(2, "Observation", VITAL, subject=ref(99))
    out = validate_bundle(bundle(res(1, "Patient", PAT), vs), FakeMatchbox())
    assert out["verdict"] == "FAIL" and cls_of(out, "dangling") == "content"


def test_bundle_pass_warnings_are_reported_as_info():
    b = bundle(res(1, "Patient", PAT))
    out = validate_bundle(b, FakeMatchbox(bundle_issues=[iss(at(b, 0, "identifier[0].system"), "No definition could be "
                                                             "found for URL value 'https://genomde.de/fhir/sid/tan-c'", sev="warning")]))
    assert out["verdict"] == "PASS" and cls_of(out, "No definition could be found") == "info"


# ---- R28: ICD-O-3 -------------------------------------------------------------------------------------------------

MORPH = "Condition.extension[1].value.ofType(CodeableConcept)"
MORPH_VS = ("None of the codings provided are in the value set 'MII VS Onkologie ICD-O-3 Morphologie' (https://www."
            "medizininformatik-initiative.de/fhir/ext/modul-onko/ValueSet/mii-vs-onko-icdo3-morphologie|2027.0.0-ballot.1), "
            f"and a coding from this value set is required) (codes = {ICDO3}#{{code}})")


def test_icdo3_unknown_edition_is_unchecked():
    vs_err = iss(MORPH, MORPH_VS.format(code="8253/2"))
    sib = iss(MORPH + ".coding[0].system", f"A definition for CodeSystem '{ICDO3}' version '2019' could not be found, "
              "so the code cannot be validated. Valid versions: 2000", sev="warning")
    assert classify_issue(vs_err, PT_PROF, frozenset({"8253/2"}), [vs_err, sib]) == "unchecked"
    assert classify_issue(dict(sib, severity="error"), PT_PROF) == "unchecked"


def test_icdo3_code_invalid_in_known_edition_is_content_or_source():
    bad = iss(MORPH + ".coding[0].code", f"Unknown code '9999/9' in the CodeSystem '{ICDO3}' version '2000'")
    assert classify_issue(bad, PT_PROF) == "content"
    assert classify_issue(bad, PT_PROF, frozenset({"9999/9"})) == "source"
    vs_err = iss(MORPH, MORPH_VS.format(code="8140/3"))   # edition 2000 (known to tx), not in the 2014/2019 value set
    assert classify_issue(vs_err, PT_PROF, frozenset(), [vs_err, bad]) == "content"
    unknown_edition = iss(MORPH + ".coding[0].system", f"A definition for CodeSystem '{ICDO3}' version '2021' could not be "
                          "found, so the code cannot be validated. Valid versions: 2000")
    assert classify_issue(unknown_edition, PT_PROF) == "content"


def test_message_id_reads_value_code():
    assert v.message_id({"extension": [{"url": v.MESSAGE_ID_EXT, "valueCode": "Reference_REF_CantMatchChoice"}]}) \
        == "Reference_REF_CantMatchChoice"


# ---- R02 / R33 / Hapi.count: HTTP --------------------------------------------------------------------------------

class _Server:
    """Answers every request with (status, body bytes, delay); records request headers."""

    def __init__(self, status=200, body=b"", delay=0.0):
        outer = self
        self.headers = []

        class H(http.server.BaseHTTPRequestHandler):
            def _answer(self):
                import time
                outer.headers.append(dict(self.headers))
                n = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(n)
                time.sleep(delay)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            do_GET = do_POST = do_PUT = _answer

            def log_message(self, *a):
                pass
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/fhir"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()


def _closed_port_url():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{port}/fhir"


SPRING_404 = json.dumps({"timestamp": "2026-10-09T18:59:14.139+00:00", "status": 404, "error": "Not Found",
                         "path": "/matchboxv3/Observation/$validate"}).encode()


@pytest.mark.parametrize("status,body", [
    (404, SPRING_404),                                                     # base URL without /fhir
    (200, b""),                                                            # empty body
    (200, b"<html>proxy error</html>"),                                    # not JSON
    (200, json.dumps({"resourceType": "OperationOutcome"}).encode()),      # no issues at all
    (500, json.dumps({"resourceType": "OperationOutcome", "issue": [{"severity": "fatal", "code": "exception",
                                                                      "diagnostics": "NPE"}]}).encode()),
    (200, json.dumps({"resourceType": "Bundle"}).encode()),                # not an OperationOutcome
])
def test_matchbox_failure_is_error_never_pass(status, body):
    with _Server(status, body) as srv:
        out = validate_bundle(bundle(res(1, "Patient", PAT)), Matchbox(srv.url))
    assert out["verdict"] == "ERROR" and out["error"], out


def test_unknown_profile_is_error():
    body = json.dumps({"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception",
           "diagnostics": "Engine configured, but validation for profile 'http://x/y' not found. ch.ahdis..."}]}).encode()
    with _Server(200, body) as srv:
        assert validate_bundle(bundle(res(1, "Patient", PAT)), Matchbox(srv.url))["verdict"] == "ERROR"


def test_unreachable_matchbox_is_error_and_stops_early():
    mb = Matchbox(_closed_port_url())
    calls = []
    real = mb.validate
    mb.validate = lambda r, p=None: calls.append(1) or real(r, p)
    out = validate_bundle(bundle(*[res(n, "Patient", PAT) for n in range(1, 6)]), mb)
    assert out["verdict"] == "ERROR" and out.get("unreachable") and "no response" in out["error"]
    assert len(calls) == 1


def test_timeout_is_no_response():
    with _Server(200, b"{}", delay=2.0) as srv:
        st, oo = v._http("GET", srv.url, timeout=0.3)
    assert st == v.NO_RESPONSE and v.is_unreachable(oo) and classify_issue(oo["issue"][0]) == "validator-error"


def test_hapi_unreachable_is_not_ok_and_does_not_raise():
    ok, resp = Hapi(_closed_port_url()).transaction(bundle(res(1, "Patient", PAT)))
    assert not ok and v.is_unreachable(resp)
    assert Hapi(_closed_port_url()).count("Patient") == -1


def test_hapi_count_sends_no_cache():
    with _Server(200, json.dumps({"resourceType": "Bundle", "total": 5}).encode()) as srv:
        assert Hapi(srv.url).count("Patient") == 5
    assert srv.headers[0].get("Cache-Control") == "no-cache"
