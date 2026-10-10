"""Regression tests for the validate group, fix round 2 (residuals of R01 R02 R04 R17 R19 R28 R33).

Offline: matchbox is replaced by fakes returning OperationOutcomes shaped like matchbox-2027's (texts and expressions
copied from live runs); the lookups (StructureDefinition / ValueSet search) use a throw-away server on 127.0.0.1.
"""
import http.server
import json
import threading
import urllib.parse

import pytest

from genomde2fhir import validate as v
from genomde2fhir.validate import Hapi, Matchbox, classify_issue, validate_bundle

from conftest import REPO
from test_fix_validate import (EMPF, ICDO3, NGS, PAT, PRIMAER, PT_ONKO, PT_PROF, UNCHECKED_PT, FakeMatchbox, at,
                                bundle, classes, cls_of, iss, ref, res)

MII = "https://www.medizininformatik-initiative.de/fhir/ext/"
VARIANTE = MII + "modul-mtb/StructureDefinition/mii-pr-mtb-einfache-variante"
MOLGEN_VARIANTE = MII + "modul-molgen/StructureDefinition/variante"
GRADING = MII + "modul-onko/StructureDefinition/mii-pr-onko-grading"
HGVS_VS = "http://hl7.org/fhir/uv/genomics-reporting/ValueSet/hgvs-vs"
MORPH_VS = MII + "modul-onko/ValueSet/mii-vs-onko-icdo3-morphologie"
HGNC = "http://www.genenames.org"
HGVS = "http://varnomen.hgvs.org"
SLICE_ID = "MedicationRequest.reasonReference:Primaertumor"


# ---- R01: the MTB-22 waiver in matchbox's real shapes, and only for that overlap --------------------------------

def _ngs_bundle():
    rep = res(2, "DiagnosticReport", NGS, subject=ref(1), result=[ref(3), ref(4)])
    return bundle(res(1, "Patient", PAT), rep, res(3, "Observation", None), res(4, "Observation", None))


def test_tumorzellgehalt_overflow_at_resource_root_is_waived():
    """matchbox-2027 reports slice cardinality at the resource itself: '.../*DiagnosticReport/<id>*/', no '.result'."""
    b = _ngs_bundle()
    tzg = iss(at(b, 1), "DiagnosticReport.result:Tumorzellgehalt: max allowed = 1, but found 34 "
                        f"(from {NGS}|2027.0.0-ballot.1)")
    out = validate_bundle(b, FakeMatchbox(bundle_issues=[tzg]))
    assert cls_of(out, "Tumorzellgehalt").startswith("waived:") and out["verdict"] == "PASS", classes(out)


@pytest.mark.parametrize("pair", ["EinfacheVariante, Tumorzellgehalt", "HRDScore, MolekularerBiomarker",
                                  "TumorMutionalBurden, MSI"])
def test_slice_overlap_at_result_is_waived(pair):
    b = _ngs_bundle()
    text = f"Profile {NGS}|2027.0.0-ballot.1, Element matches more than one slice - {pair}"
    out = validate_bundle(b, FakeMatchbox(bundle_issues=[iss(at(b, 1, "result[1]"), text)]))
    assert cls_of(out, "more than one slice").startswith("waived:") and out["verdict"] == "PASS"


@pytest.mark.parametrize("expr_path,text", [
    ("", "DiagnosticReport.result:TumorMutionalBurden: max allowed = 1, but found 2"),   # a real duplicate (R15)
    ("", "DiagnosticReport.result:HRDScore: max allowed = 1, but found 2"),
    ("result[1]", "DiagnosticReport.result:Tumorzellgehalt: max allowed = 1, but found 2"),   # not matchbox's shape
    ("subject", "DiagnosticReport.result:Tumorzellgehalt: max allowed = 1, but found 2"),
])
def test_other_slice_overflows_are_content(expr_path, text):
    b = _ngs_bundle()
    bi = [iss(at(b, 1, expr_path), f"{text} (from {NGS}|2027.0.0-ballot.1)")]
    out = validate_bundle(b, FakeMatchbox(bundle_issues=bi))
    assert out["verdict"] == "FAIL" and cls_of(out, "max allowed") == "content"


def test_waiver_needs_the_ngs_bericht_profile():
    rep = res(2, "DiagnosticReport", MII + "modul-patho/StructureDefinition/mii-pr-patho-report", subject=ref(1))
    b = bundle(res(1, "Patient", PAT), rep)
    tzg = iss(at(b, 1), "DiagnosticReport.result:Tumorzellgehalt: max allowed = 1, but found 2")
    assert validate_bundle(b, FakeMatchbox(bundle_issues=[tzg]))["verdict"] == "FAIL"


# ---- R02: a failing Bundle pass reports the failure, not matchbox's information issue ----------------------------

def test_bundle_pass_failure_names_the_real_error():
    b = bundle(res(1, "Patient", PAT))
    info = {"severity": "information", "code": "informational",
            "diagnostics": "Validation for profile http://hl7.org/fhir/StructureDefinition/Bundle|4.0.1"}
    npe = {"severity": "error", "code": "exception", "diagnostics": "NullPointerException in FHIRPath"}
    other = iss("Bundle.entry[0].resource", "Constraint failed: bdl-3")
    mb = FakeMatchbox()
    mb.validate = lambda r, p=None: {"resourceType": "OperationOutcome",
                                     "issue": [info, npe, other] if r["resourceType"] == "Bundle" else [info]}
    out = validate_bundle(b, mb)
    assert out["verdict"] == "ERROR" and out["error"] == "NullPointerException in FHIRPath"
    brow = out["resources"][-1]
    assert [(i["class"], i["severity"]) for i in brow["issues"]] == [("validator-error", "error"), ("unchecked", "error")]


# ---- R04 / R19: resolve() slices judged only by the references that can fill the slice ---------------------------

class SliceMatchbox(FakeMatchbox):
    """FakeMatchbox that also knows the slice's target profiles (slices=False: cannot tell) and the profile
    hierarchy, as Matchbox does."""

    def __init__(self, own=None, bundle_issues=None, slices=True):
        self.slices = slices
        super().__init__(own, bundle_issues, ancestors={
            PT_PROF: {PT_PROF, PT_ONKO, v.BASE_SD + "Condition"}, PT_ONKO: {PT_ONKO, v.BASE_SD + "Condition"},
            VARIANTE: {VARIANTE, MOLGEN_VARIANTE, v.BASE_SD + "Observation"},
            GRADING: {GRADING, v.BASE_SD + "Observation"}})

    def slice_targets(self, profile, element_id):
        return {PT_ONKO} if self.slices and (profile.split("|")[0], element_id) == (EMPF, SLICE_ID) else None


HGVS_ERR = iss("Observation.component[0].value.ofType(CodeableConcept).coding[0].code",
               "Unknown code 'c.218A>G' in the CodeSystem 'http://varnomen.hgvs.org' version '2.0'")


def _empf(reason, pt_issues=(), var_issues=(), var_profile=VARIANTE, var_focus=True, slices=True):
    """Patient, Primaertumor (2), Observation (3, focus -> Primaertumor), Therapieempfehlung (4) with reasonReference."""
    pt = res(2, "Condition", PT_PROF, subject=ref(1))
    var = res(3, "Observation", var_profile, subject=ref(1), **({"focus": [ref(2)]} if var_focus else {}))
    mr = res(4, "MedicationRequest", EMPF, subject=ref(1), reasonReference=[ref(n) for n in reason])
    b = bundle(res(1, "Patient", PAT), pt, var, mr)
    own = {pt["id"]: list(pt_issues), var["id"]: list(var_issues), mr["id"]: [iss("MedicationRequest", PRIMAER)]}
    return b, SliceMatchbox(own=own, bundle_issues=[iss(at(b, 3), PRIMAER)], slices=slices)


SRC = {"variant": {"cDNAChange": "c.218A>G"}}


@pytest.mark.parametrize("reason,var_profile,pt_issues,var_issues,var_focus", [
    ([3], VARIANTE, UNCHECKED_PT, [], True),        # variant only, its focus Primaertumor unchecked (was INCONCLUSIVE)
    ([3], VARIANTE, [], [HGVS_ERR], False),         # variant with a source error (was cascade / DATA-QUALITY)
    ([3], GRADING, UNCHECKED_PT, [], True),         # a Grading observation (was unchecked)
    ([3], None, UNCHECKED_PT, [], True),            # an Observation without profile: wrong resource type
])
def test_reference_slice_with_only_wrong_kind_of_targets_fails(reason, var_profile, pt_issues, var_issues, var_focus):
    b, mb = _empf(reason, pt_issues, var_issues, var_profile, var_focus)
    out = validate_bundle(b, mb, source=SRC)
    assert cls_of(out, "reasonReference:Primaertumor") == "content" and out["verdict"] == "FAIL", classes(out)


def test_reference_slice_ignores_unrelated_tainted_target():
    """[Primaertumor (unchecked), variant (source)]: judged by the Primaertumor only, not blamed on the variant."""
    b, mb = _empf([2, 3], UNCHECKED_PT, [HGVS_ERR], var_focus=False)
    out = validate_bundle(b, mb, source=SRC)
    assert cls_of(out, "reasonReference:Primaertumor") == "unchecked" and out["verdict"] == "DATA-QUALITY", classes(out)


@pytest.mark.parametrize("pt_issues,want,verdict", [
    (UNCHECKED_PT, "unchecked", "INCONCLUSIVE"),
    ([iss("Condition.code", "Condition.code: minimum required = 1, but only found 0")], "cascade", "FAIL"),
    ([], "content", "FAIL"),
])
def test_reference_slice_with_plausible_target_judged_by_it(pt_issues, want, verdict):
    b, mb = _empf([2], pt_issues)
    out = validate_bundle(b, mb)
    assert cls_of(out, "reasonReference:Primaertumor") == want and out["verdict"] == verdict, classes(out)


def test_reference_slice_without_slice_lookup_keeps_old_judgement():
    """matchbox cannot tell the slice's target profiles: all references of the element count, as before."""
    b, mb = _empf([3], UNCHECKED_PT, slices=False)
    assert cls_of(validate_bundle(b, mb), "reasonReference:Primaertumor") == "unchecked"


# ---- R17: composed HGVS is source only when every part is verbatim input -------------------------------------

def _unknown(code):
    return iss("Observation.component[0].value.ofType(CodeableConcept).coding[0].code",
               f"Unknown code '{code}' in the CodeSystem 'http://varnomen.hgvs.org' version '2.0'")


def _vs(code, system=HGVS):
    return iss("Observation.component[0].value.ofType(CodeableConcept)",
               "None of the codings provided are in the value set 'Human Genome Variation Society (HGVS) Nomenclature' "
               f"({HGVS_VS}|3.0.0), and a coding from this value set is required) (codes = {system}#{code})")


HGVS_SRC = v._source_values({"gene": {"code": "HGNC:6407", "display": "KRAS"}, "dnaChange": "c.34T>G",
                             "proteinChange": "p.Trp12Cys", "transcriptId": {"code": "NM_004985", "version": 5},
                             "other": {"transcript": "NM_000546.6"}})


@pytest.mark.parametrize("code,want", [
    ("NM_004985.5:c.34T>G", "source"),             # accession + version from transcriptId.code/.version
    ("NM_004985.5(KRAS):p.Trp12Cys", "source"),    # ClinVar style, gene symbol from gene.display
    ("NM_000546.6:c.34T>G", "source"),             # reference sequence as one input value
    ("NM_004985.6:c.34T>G", "content"),            # version not in the input
    ("NM_004985.5(NRAS):p.Trp12Cys", "content"),   # gene symbol not in the input
    ("NM_004985(KRAS).5:p.Trp12Cys", "content"),   # not the composed shape
    ("NM_004985.5:c.34T>GA", "content"),           # notation not a whole input value
    ("NM_999999.5:c.34T>G", "content"),
])
def test_composed_hgvs_rule(code, want):
    assert classify_issue(_unknown(code), "", HGVS_SRC) == want
    assert classify_issue(_vs(code), "", HGVS_SRC) == want


def test_composition_rule_is_hgvs_only():
    hpo = iss("Observation.value.ofType(CodeableConcept).coding[0].code",
              "Unknown code 'HP:0001250' in the CodeSystem 'http://human-phenotype-ontology.org' version 'x'")
    assert classify_issue(hpo, "", v._source_values({"a": "HP", "b": "0001250"})) == "content"


def test_converter_composed_hgvs_is_source(convert_dk):
    """The rule matches what the converter composes: an unversioned RefSeq + transcriptId.version, ClinVar-style p."""
    dk = json.loads((REPO / "examples/oncology" / ("OncologySubmission_044AFF6262356F2F8EC60039DC08AE36FBAA011DE29740CBC83E9FA"
                                                   "5643E4640.json")).read_text())
    dk["molecular"]["smallVariants"][0].update(
        gene={"code": "HGNC:6407", "display": "KRAS", "system": "https://www.genenames.org/"}, dnaChange="c.34T>G",
        proteinChange="p.Trp12Cys",
        transcriptId={"code": "NM_004985", "version": "5", "system": "https://www.ncbi.nlm.nih.gov/refseq"})
    b, _ = convert_dk(dk)
    codes = {cd["code"] for e in b["entry"] for c in e["resource"].get("component", [])
             for cd in (c.get("valueCodeableConcept") or {}).get("coding", [])
             if cd.get("system") == HGVS and "NM_004985" in cd["code"]}
    assert codes == {"NM_004985.5:c.34T>G", "NM_004985.5(KRAS):p.Trp12Cys"}
    sv = v._source_values(dk)
    assert all(classify_issue(_unknown(c), "", sv) == "source" for c in codes)
    assert classify_issue(_unknown("NM_004985.5(KRAS):p.Trp12Ser"), "", sv) == "content"


# ---- R28: a value-set error is unchecked only for an admissible coding the tx server cannot check ---------------

HGNC_SIB = iss("Observation.component[0].value.ofType(CodeableConcept).coding[0].system",
               f"A definition for CodeSystem '{HGNC}' could not be found, so the code cannot be validated", sev="warning")
ICDO3_SIB = iss("Observation.component[0].value.ofType(CodeableConcept).coding[0].system",
                f"A definition for CodeSystem '{ICDO3}' version '2019' could not be found, so the code cannot be "
                "validated. Valid versions: 2000", sev="warning")
TIMEOUT_SIB = iss("Observation.component[0].value.ofType(CodeableConcept).coding[0]",
                  "Error from https://tx.fhir.org/r4: Error: Error validating HGVS code: HGVS validation request timed out")
VS_SYSTEMS = {HGVS_VS: {HGVS}, MORPH_VS: {ICDO3}}.get


@pytest.mark.parametrize("err,sib,want", [
    (_vs("HGNC:1100", HGNC), HGNC_SIB, "content"),           # wrong system under the HGVS binding (live probe)
    (_vs("8140/3", ICDO3), ICDO3_SIB, "content"),            # ICD-O-3 2019 coding under the HGVS binding
    (_vs("NM_004985.5:c.34T>G"), TIMEOUT_SIB, "unchecked"),  # admissible HGVS coding, tx timed out
])
def test_value_set_error_needs_admissible_undecidable_coding(err, sib, want):
    assert classify_issue(err, "", frozenset(), [err, sib], VS_SYSTEMS) == want


def test_wrong_system_coding_is_never_source():
    """HGNC:1100 is an input value, but an HGNC coding under the HGVS binding is the converter's error (live probe)."""
    err = _vs("HGNC:1100", HGNC)
    sv = v._source_values({"gene": {"code": "HGNC:1100"}})
    assert classify_issue(err, "", sv, [err, HGNC_SIB], VS_SYSTEMS) == "content"
    assert classify_issue(_vs("c.34T>G"), "", v._source_values({"dnaChange": "c.34T>G"}), None, VS_SYSTEMS) == "source"


def test_icdo3_morphology_with_unknown_edition_stays_unchecked():
    vs_err, sib = UNCHECKED_PT
    assert classify_issue(vs_err, PT_PROF, frozenset(), UNCHECKED_PT, VS_SYSTEMS) == "unchecked"
    # a checkable coding next to a sibling about another system is decided: content
    other = iss(v._expr(vs_err), vs_err["diagnostics"].replace(f"{ICDO3}#8253/2", "http://snomed.info/sct#1234"))
    assert classify_issue(other, PT_PROF, frozenset(), [other, sib], VS_SYSTEMS) == "content"


def test_value_set_admissibility_unknown_gives_benefit_of_doubt():
    err = _vs("HGNC:1100", HGNC)
    assert classify_issue(err, "", frozenset(), [err, HGNC_SIB], lambda url: None) == "unchecked"


def test_wrong_system_coding_fails_the_bundle():
    obs = res(2, "Observation", VARIANTE, subject=ref(1))
    b = bundle(res(1, "Patient", PAT), obs)
    mb = FakeMatchbox(own={obs["id"]: [_vs("HGNC:1100", HGNC), HGNC_SIB]})
    mb.vs_systems = VS_SYSTEMS
    out = validate_bundle(b, mb, source={"gene": {"code": "HGNC:1100"}})
    assert out["verdict"] == "FAIL" and cls_of(out, "None of the codings") == "content"


# ---- R04 / R28: the matchbox lookups behind slice_targets / vs_systems ------------------------------------------

class _Router:
    """Answers GET <base>/<type>?url=<canonical> with a search Bundle of the resources registered for it."""

    def __init__(self, resources):
        found = {}

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                u = urllib.parse.urlparse(self.path)
                key = (u.path.rsplit("/", 1)[-1], urllib.parse.parse_qs(u.query).get("url", [""])[0])
                found.setdefault(key, 0)
                found[key] += 1
                body = json.dumps({"resourceType": "Bundle", "type": "searchset",
                                   "entry": [{"resource": r} for r in resources.get(key, [])]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass
        self.calls = found
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/fhir"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()


def test_matchbox_slice_targets_and_vs_systems():
    sd = {"resourceType": "StructureDefinition", "url": EMPF, "snapshot": {"element": [
        {"id": "MedicationRequest.reasonReference", "type": [{"code": "Reference", "targetProfile": [
            PT_ONKO, v.BASE_SD + "Condition", v.BASE_SD + "Observation"]}]},
        {"id": SLICE_ID, "type": [{"code": "Reference", "targetProfile": [PT_ONKO + "|2027.0.0-ballot.1"]}]},
        {"id": "MedicationRequest.subject", "type": [{"code": "Reference"}]}]}}
    outer = {"resourceType": "ValueSet", "url": "http://x/vs-outer", "compose": {"include": [
        {"system": "http://loinc.org"}, {"valueSet": ["http://x/vs-inner"]}]}}
    inner = {"resourceType": "ValueSet", "url": "http://x/vs-inner", "compose": {"include": [{"system": HGVS}]}}
    with _Router({("StructureDefinition", EMPF): [sd], ("ValueSet", "http://x/vs-outer"): [outer],
                  ("ValueSet", "http://x/vs-inner"): [inner]}) as srv:
        mb = Matchbox(srv.url)
        assert mb.slice_targets(EMPF + "|2027.0.0-ballot.1", SLICE_ID) == {PT_ONKO}
        assert mb.slice_targets(EMPF, "MedicationRequest.subject") is None   # no target profile: cannot tell
        assert mb.slice_targets(EMPF, "MedicationRequest.reasonReference:Nope") is None
        assert mb.slice_targets(MII + "unknown", SLICE_ID) is None
        assert mb.vs_systems("http://x/vs-outer|1.0") == {"http://loinc.org", HGVS}
        assert mb.vs_systems("http://x/vs-missing") is None
        mb.slice_targets(EMPF, SLICE_ID)
        mb.vs_systems("http://x/vs-outer")
    assert srv.calls[("StructureDefinition", EMPF)] == 1 and srv.calls[("ValueSet", "http://x/vs-outer")] == 1   # cached


# ---- R33: a URL without a scheme is an unreachable server, never an exception ------------------------------------

@pytest.mark.parametrize("url", ["matchbox.example.org/fhir", "matchbox/fhir", "fhir", "", "http://[::1/fhir"])
def test_bad_url_is_no_response(url):
    st, oo = v._http("GET", url)
    assert st == v.NO_RESPONSE and v.is_unreachable(oo)


def test_bad_url_gives_error_verdict_and_no_exception():
    out = validate_bundle(bundle(res(1, "Patient", PAT), res(2, "Patient", PAT)), Matchbox("matchbox/fhir"))
    assert out["verdict"] == "ERROR" and out.get("unreachable") and "unknown url type" in out["error"]
    ok, resp = Hapi("fhir").transaction(bundle(res(1, "Patient", PAT)))
    assert not ok and v.is_unreachable(resp) and Hapi("fhir").count("Patient") == -1
    assert Matchbox("fhir").packages() is None and Matchbox("fhir").ancestors(PT_PROF) is None


def test_cli_bad_url_exit_3_and_report(tmp_path, capsys):
    from genomde2fhir import cli
    f = tmp_path / "x.json"
    f.write_text((REPO / "examples/grz/grz-paired-rd-01.json").read_text())
    rep = tmp_path / "rep.json"
    rc = cli.main(["convert", str(f), "-o", str(tmp_path / "out"), "--validate", "matchbox/fhir", "--ingest", "hapi/fhir",
                   "--no-input-check", "--report", str(rep)])
    err = capsys.readouterr().err
    assert rc == 3 and "Traceback" not in err and rep.is_file()
    val = json.loads(rep.read_text())["validation"][str(f)]
    assert val["validation"]["verdict"] == "ERROR" and val["validation"]["unreachable"] is True
    rc = cli.main(["validate", str(next((tmp_path / "out").glob("*.json"))), "--matchbox", "localhost/fhir"])
    assert rc == 3
