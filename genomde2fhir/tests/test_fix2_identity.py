"""Regression tests for the identity findings reopened after fix round 1 (R06 R43 R39).

R06: the initial GRZ submission and its corrections share one genomic study (a correction rewrites it in place);
     a follow-up / addition gets its own study keyed by submission date.
R43: every resource carries meta.source = the submission, so resources a correction left behind stay identifiable.
R39: contained resources referenced by canonical / uri '#id' values (and those referring to the Consent with '#')
     are kept; the dangling-reference check sees canonical / uri '#id' values.

Small synthetic variants of the committed fixtures; no corpus, no server."""
import copy
import json
import re
from pathlib import Path

from conftest import resources

from genomde2fhir import convert
from genomde2fhir.builders import patient, research_consent
from genomde2fhir.bundle import dangling_references, structural_errors
from genomde2fhir.context import Ctx
from genomde2fhir.identity import case_key, source_component

FIX = Path(__file__).parent / "fixtures"
ONCO = FIX / "onco_variants" / "synthetic_small_variants.json"     # KDK oncology, localCaseId, smallVariants
RD = FIX / "rd_variants" / "rd-variants-edge-cases.json"            # KDK rare disease
CONSENT = FIX / "consent" / "onco_edge.json"                        # KDK oncology with an embedded Broad Consent
GRZ = FIX / "grz_labdata" / "grz-labdata-rd-duo.json"               # GRZ initial, index + mother with labData
EXT_ANALYSIS = "http://hl7.org/fhir/uv/genomics-reporting/StructureDefinition/genomic-study-analysis-ext"
SCOPE = "metaData.researchConsents[].scope"


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run(dk, name="<fix2>", **kw):
    bundle, rep = convert(dk, name, **kw)
    assert rep.status == "converted", rep.error or rep.input_findings
    return bundle, rep


def grz(stype: str, **sub) -> dict:
    dk = load(GRZ)
    dk["submission"]["submissionType"] = stype
    dk["submission"].update(sub)
    return dk


def kdk(stype: str, date: str | None = None, path=ONCO, **md) -> dict:
    dk = load(path)
    dk["metaData"]["submission"]["type"] = stype
    if date:
        dk["metaData"]["submission"]["date"] = date
    dk["metaData"].update(md)
    return dk


def study(bundle) -> dict:
    [st] = [r for r in resources(bundle, "Procedure")
            if any(p.endswith("-genomic-study") for p in r.get("meta", {}).get("profile", []))]
    return st


def analyses(st) -> set:
    return {e["valueReference"]["reference"] for e in st.get("extension", []) if e["url"] == EXT_ANALYSIS}


def provenance_id(bundle) -> str:
    [prov] = resources(bundle, "Provenance")
    return prov["id"]


# ---- R06: initial + corrections share one genomic study, follow-up / addition get their own ---------------------------
def test_r06_correction_rewrites_the_initial_genomic_study():
    init, _ = run(grz("initial"))
    corr, _ = run(grz("correction", submissionDate="2026-05-10", labName="Corrected Lab GmbH"))
    s1, s2 = study(init), study(corr)
    assert s1["id"] == s2["id"], "a correction leaves the uncorrected study of the initial submission behind"
    [lab] = [o for o in resources(corr, "Organization") if o.get("name") == "Corrected Lab GmbH"]
    assert s2["performer"] == [{"actor": {"reference": "urn:uuid:" + lab["id"]}}]
    assert analyses(s2) == analyses(s1) and len(analyses(s2)) == 2     # same labData -> same analysis ids
    # same id as v0.10.0 (per-case key): studies already on a server are rewritten, not duplicated
    assert s1["id"] == case_key(grz("initial"), "grz").id("Procedure", "submission", "genomic-study")
    # the audit trail still has one Provenance per submission
    assert provenance_id(init) != provenance_id(corr)


def test_r06_followup_and_addition_get_their_own_study_by_date():
    s_init = study(run(grz("initial"))[0])
    ids = set()
    for stype, date in (("addition", "2026-06-01"), ("followup", "2026-07-01"), ("addition", "2026-08-01")):
        dk = grz(stype, submissionDate=date)
        dk["donors"] = dk["donors"][:1]
        dk["donors"][0]["labData"][0]["labDataName"] = f"index-{stype}-{date}"
        st = study(run(dk)[0])
        assert st["id"] == case_key(dk, "grz").id("Procedure", "submission", "genomic-study", date)
        assert len(analyses(st)) == 1 and not analyses(st) & analyses(s_init)
        ids.add(st["id"])
        again = study(run(copy.deepcopy(dk))[0])      # the same submission re-sent rewrites its own study
        assert again["id"] == st["id"]
    assert len(ids) == 3 and s_init["id"] not in ids


def test_r06_submission_parts_rule():
    def parts(stype, date="2026-01-02"):
        return case_key(grz(stype, submissionDate=date), "grz").submission_parts()
    assert parts("initial") == parts("correction") == parts("test") == ()
    assert parts("followup") == parts("addition") == ("2026-01-02",)
    # a correction is taken to correct the initial submission, also after a follow-up (documented limitation)
    corr = study(run(grz("correction", submissionDate="2026-09-09"))[0])
    assert corr["id"] == study(run(grz("initial"))[0])["id"]


# ---- R43: meta.source names the submission on every resource ------------------------------------------------------------
def expected_source(sub: str, case: str, date: str, stype: str) -> str:
    # fix round 3 (R43 '#'): ':'-joined raw components, each percent-encoded (identity.source_component)
    return "urn:genomde2fhir:submission:" + ":".join(source_component(p) for p in (sub, case, date, stype))


def sources(bundle) -> set:
    return {r.get("meta", {}).get("source") for r in resources(bundle)}


def test_r43_every_resource_carries_the_submission_as_meta_source():
    for dk in (kdk("initial"), kdk("followup", path=RD), grz("addition", submissionDate="2026-06-01")):
        s = dk.get("submission") or dk["metaData"]["submission"]
        local = (dk.get("submission", {}).get("localCaseId") or dk.get("metaData", {}).get("localCaseId")
                 or dk.get("metaData", {}).get("tanC"))           # the RD fixture has no localCaseId: TAN-C fallback
        stype = s.get("type") or s.get("submissionType")
        date = s.get("date") or s.get("submissionDate")
        bundle, rep = run(dk)
        assert sources(bundle) == {expected_source(s["submitterId"], local, date, stype)}
        assert resources(bundle, "Provenance")        # the Provenance carries it too
        assert not structural_errors(bundle)
        branch_prefix = "submission." if "submission" in dk else "metaData.submission."
        assert any(p.startswith(branch_prefix) and p.endswith(("ate", "ype")) for p in rep.preserved)
        assert rep.representations["meta-source"] >= 1
    # also without the Provenance, and in the test namespace
    b, _ = run(kdk("test"), provenance=False)
    md = load(ONCO)["metaData"]
    assert sources(b) == {expected_source(md["submission"]["submitterId"], md["localCaseId"],
                                          md["submission"]["date"], "test")}   # the type 'test' tells it apart


def test_r43_meta_source_is_escaped_and_stays_a_uri():
    b, _ = run(kdk("initial", localCaseId="CASE 7/a|b%\\"))
    [src] = sources(b)
    sub, date = load(ONCO)["metaData"]["submission"]["submitterId"], load(ONCO)["metaData"]["submission"]["date"]
    assert src == f"urn:genomde2fhir:submission:{sub}:CASE%207%2Fa%7Cb%25\\:{date}:initial"
    assert not re.search(r"\s", src)                    # FHIR uri: no whitespace
    # percent-encoding keeps different case ids apart
    b2, _ = run(kdk("initial", localCaseId="CASE%207/a|b%25\\"))
    assert sources(b2) != {src}


def ingest(server: dict, bundle: dict, keep_source_if_unchanged: bool):
    """Toy server: PUT by fullUrl. keep_source_if_unchanged mimics HAPI 8.4 ('no changes detected' when only
    meta.source differs: the earlier meta.source stays)."""
    def body(r):
        r = copy.deepcopy(r)
        r.get("meta", {}).pop("source", None)
        return r
    for e in bundle["entry"]:
        old = server.get(e["fullUrl"])
        if keep_source_if_unchanged and old is not None and body(old) == body(e["resource"]):
            continue
        server[e["fullUrl"]] = copy.deepcopy(e["resource"])


def stale_by_source(server: dict, correction: dict, earlier: set) -> set:
    """IDENTITY.md 'Known limitation': resources still naming an earlier initial / correction submission that the
    correction bundle does not contain."""
    in_corr = {e["fullUrl"] for e in correction["entry"]}
    return {u for u, r in server.items() if r["meta"]["source"] in earlier and u not in in_corr}


def test_r43_stale_resources_of_a_kdk_correction_are_found_by_meta_source():
    init_dk, corr_dk = kdk("initial"), kdk("correction", "2026-07-01")
    corr_dk["molecular"]["smallVariants"].pop(0)                  # the correction withdraws a variant
    init, corr = run(init_dk)[0], run(corr_dk)[0]
    removed = {e["fullUrl"] for e in init["entry"]} - {e["fullUrl"] for e in corr["entry"]}
    removed -= {"urn:uuid:" + provenance_id(init)}               # the initial's Provenance is the audit trail
    assert removed and sources(corr) == {next(iter(sources(corr)))}
    for keep in (False, True):
        server = {}
        ingest(server, init, keep)
        ingest(server, corr, keep)
        earlier = sources(init)
        assert stale_by_source(server, corr, earlier) - {"urn:uuid:" + provenance_id(init)} == removed
        # every resource the correction rewrote with new content names the correction
        changed = {u for u, r in server.items() if r["meta"]["source"] in sources(corr)}
        assert changed and not changed & removed


def test_r43_grz_correction_removing_a_donor_leaves_identifiable_resources_only():
    init_dk = grz("initial")
    corr_dk = grz("correction", submissionDate="2026-08-15")
    corr_dk["donors"] = [d for d in corr_dk["donors"] if d["relation"] != "mother"]
    corr_dk["submission"]["genomicStudyType"] = "single"
    init, corr = run(init_dk)[0], run(corr_dk)[0]
    server = {}
    ingest(server, init, True)
    ingest(server, corr, True)
    stale = stale_by_source(server, corr, sources(init)) - {"urn:uuid:" + provenance_id(init)}
    types = sorted(server[u]["resourceType"] for u in stale)
    # the mother's Patient, family history, consents, specimen, analysis and devices; not the genomic study (R06)
    assert {"Patient", "FamilyMemberHistory", "Specimen", "Procedure"} <= set(types)
    assert "urn:uuid:" + study(init)["id"] not in stale
    assert all(server[u]["meta"]["source"] in sources(init) for u in stale)


# ---- R39: canonical / uri '#id' references to contained resources -------------------------------------------------------
def consent(mutate, strict=True):
    dk = load(CONSENT)
    mutate(dk["metaData"]["researchConsents"][0]["scope"])
    ctx = Ctx(dk, "oncology", case_key(dk, "oncology"), "2027", strict=strict)
    patient.build(ctx)
    research_consent.build(ctx)
    bundle = {"entry": list(ctx.bundle.entries.values())}
    [con] = resources(bundle, "Consent")
    return con, ctx.report, bundle


QR = {"resourceType": "QuestionnaireResponse", "id": "qr", "status": "completed", "questionnaire": "#q"}
Q = {"resourceType": "Questionnaire", "id": "q", "status": "active"}


def test_r39_contained_questionnaire_referenced_by_canonical_is_kept():
    def mutate(sc):
        sc["contained"] = [copy.deepcopy(QR), copy.deepcopy(Q)]
        sc["sourceReference"] = {"reference": "#qr"}
    con, rep, bundle = consent(mutate)
    assert [c["id"] for c in con["contained"]] == ["qr", "q"]
    assert con["contained"][0]["questionnaire"] == "#q" and con["sourceReference"] == {"reference": "#qr"}
    assert not any(v.startswith("contained ") for _, v, _ in rep.dropped)
    assert not dangling_references(bundle) and not structural_errors(bundle)


def test_r39_canonical_to_a_missing_contained_resource_is_removed():
    def mutate(sc):
        q2 = dict(Q, id="q2", derivedFrom=["#q0", "#gone"])
        sc["contained"] = [dict(QR, questionnaire="#missing"), q2, {"resourceType": "Questionnaire", "id": "q0",
                                                                   "status": "draft"}]
        sc["sourceReference"] = {"reference": "#qr"}
        sc["policy"] = sc.get("policy", []) + [{"uri": "#q2"}]
    con, rep, bundle = consent(mutate)
    by_id = {c["id"]: c for c in con["contained"]}
    assert set(by_id) == {"qr", "q2", "q0"}                       # q2 via the policy uri, q0 via q2.derivedFrom
    assert "questionnaire" not in by_id["qr"] and by_id["q2"]["derivedFrom"] == ["#q0"]
    warned = " ".join(m for _, m in rep.warnings)
    assert "'#missing'" in warned and "'#gone'" in warned
    assert not dangling_references(bundle) and not structural_errors(bundle)


def test_r39_contained_resource_referring_to_the_consent_is_kept():
    prov = {"resourceType": "Provenance", "id": "signing", "target": [{"reference": "#"}],
            "recorded": "2025-01-01T00:00:00Z", "agent": [{"who": {"display": "Studienzentrale"}}]}

    def mutate(sc):
        sc["contained"] = [prov, {"resourceType": "Organization", "id": "unused", "name": "nobody"}]
    con, rep, bundle = consent(mutate)
    assert [c["id"] for c in con["contained"]] == ["signing"]      # dom-3: refers to its container
    assert (SCOPE, "contained Organization/unused",
            "contained resource neither referenced from the carried-over elements nor referring to the Consent") \
        in rep.dropped
    assert not dangling_references(bundle) and not structural_errors(bundle)


def test_r39_sender_urn_uuid_references_do_not_dangle_in_strict_mode():
    dk = load(CONSENT)
    sc = dk["metaData"]["researchConsents"][0]["scope"]
    sender = "urn:uuid:0b6f3e3e-1111-4222-8333-444455556666"
    sc["contained"] = [{"resourceType": "Practitioner", "id": "doctor", "name": [{"family": "Example"}],
                        "qualification": [{"code": {"text": "x"}, "issuer": {"reference": sender}}]}]
    sc["performer"] = [{"reference": "#doctor"}, {"reference": sender}]
    bundle, rep = convert(dk, "<fix2>", strict=True)       # strict raises on dangling references
    [con] = [r for r in resources(bundle, "Consent") if r.get("contained")]
    assert con["performer"] == [{"reference": "#doctor"}, {"display": f"{sender} (sender system)"}]
    assert con["contained"][0]["qualification"][0]["issuer"] == {"display": f"{sender} (sender system)"}


def test_r39_dangling_check_sees_canonical_and_uri_local_references():
    res = {"resourceType": "Consent", "id": "c1", "contained": [{"resourceType": "Questionnaire", "id": "a"}],
           "policy": [{"uri": "#a"}, {"uri": "#b"}], "sourceReference": {"reference": "#"},
           "extension": [{"url": "x", "valueCanonical": "#c"}],
           "provision": {"actor": [{"reference": {"display": "#b"}}], "code": [{"coding": [{"code": "#b"}]}]},
           "verification": [{"verified": True, "verifiedWith": {"reference": "#zz"}}]}
    bundle = {"entry": [{"fullUrl": "urn:uuid:c1", "resource": res}]}
    assert sorted(dangling_references(bundle)) == ["Consent/c1: #b", "Consent/c1: #c", "Consent/c1: #zz"]
