"""Consent block: MV consent (mvgs-consent), embedded Broad Consent (mii-pr-consent-einwilligung 2027),
research consent absence (mvgs-research-consent-absent), submission metadata and the indication-board decision
(mvgs-inclusion-decision). Paths: metaData.mvConsent.*, metaData.researchConsents[].*, metaData.submission.*,
metaData.decisionToInclude / .molecularBoardDecisionDate / .rejectionJustification (oncology and rare disease)."""
import copy
from pathlib import Path

import pytest
from conftest import corpus, first_with, load, resources

from genomde2fhir.builders import consent, patient, research_consent, submission
from genomde2fhir.bundle import structural_errors
from genomde2fhir.context import Ctx
from genomde2fhir.data_access import mapping_rows
from genomde2fhir.identity import case_key

FIX = Path(__file__).parent / "fixtures" / "consent"
MV = "https://genomde.de/fhir/StructureDefinition/mvgs-consent"
BROAD = "https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-consent-einwilligung"
ABSENT = "https://genomde.de/fhir/StructureDefinition/mvgs-research-consent-absent"
BOARD = "https://genomde.de/fhir/StructureDefinition/mvgs-inclusion-decision"
DOMAIN_CS = "https://genomde.de/fhir/CodeSystem/mvgs-cs-mv-consent-domain"
REJECT_CS = "https://genomde.de/fhir/CodeSystem/mvgs-cs-mv-rejection-reason"
ABSENCE_CS = "https://genomde.de/fhir/CodeSystem/mvgs-cs-research-consent-absence-reason"
VERSION_MODULES = "https://www.medizininformatik-initiative.de/fhir/modul-consent/CodeSystem/mii-cs-consent-version-modules"
PREFIXES = ("metaData.mvConsent.", "metaData.researchConsents[].", "metaData.submission.", "metaData.decisionToInclude",
            "metaData.molecularBoardDecisionDate", "metaData.rejectionJustification")


def block_rows(branch):
    return {p: r for p, r in mapping_rows(branch).items() if p.startswith(PREFIXES)}


def disposed(rep, branch, path):
    """MAPPED rows must be covered; rows the table leaves NOMAP are preserved by the local mvgs-* resource."""
    status = (mapping_rows(branch).get(path) or {}).get("status")
    return path in (rep.covered if status == "MAPPED" else rep.preserved)


def one(bundle, profile):
    rs = resources(bundle, profile=profile)
    assert len(rs) == 1, [r["id"] for r in rs]
    return rs[0]


def patient_ref(bundle):
    return "urn:uuid:" + resources(bundle, "Patient")[0]["id"]


def check_mv_consent(bundle, md):
    con = one(bundle, MV)
    mvc = md["mvConsent"]
    assert con["patient"]["reference"] == patient_ref(bundle)
    assert con["policyRule"]["text"] == mvc["version"]
    assert con["dateTime"] == (mvc.get("presentationDate") or min(s["date"] for s in mvc["scope"]))
    prov = con["provision"]["provision"]
    assert [(p["type"], p["period"]["start"], p["code"][0]["coding"][0]["code"]) for p in prov] == \
        [(s["type"], s["date"], s["domain"]) for s in mvc["scope"]]
    assert all(p["code"][0]["coding"][0]["system"] == DOMAIN_CS for p in prov)
    assert "type" not in con["provision"]          # root rule carries no type (FHIR R4 Consent.provision.type)
    return con


def check_broad(con, bundle, rc):
    assert con["meta"]["profile"] == [BROAD]     # test submissions also carry meta.security HTEST
    assert set(con["meta"]) <= {"profile", "security", "source"}   # meta.source: the submission (R43, IDENTITY.md)
    assert con["patient"] == {"reference": patient_ref(bundle)}
    assert con["dateTime"] == rc["presentationDate"]
    assert con["scope"]["coding"][0]["code"] == "research"
    codings = [c for cat in con["category"] for c in cat["coding"]]
    assert {"system": "http://loinc.org", "code": "57016-8"} in codings
    assert {"system": VERSION_MODULES, "code": "2.16.840.1.113883.3.1937.777.24.2.184"} in codings
    assert not any("consent_category" in c["system"] for c in codings)
    assert all(p["uri"].startswith("urn:oid:") for p in con["policy"])
    assert "text" not in con and "lastUpdated" not in con["meta"]
    refs = []

    def walk(o):
        if isinstance(o, dict):
            if "reference" in o:
                refs.append(o["reference"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(con)
    assert all(r.startswith("urn:uuid:") for r in refs), refs
    # nested provisions are carried over verbatim
    assert len(con["provision"]["provision"]) == len(rc["scope"]["provision"]["provision"])


# ---- (a) corpus files -------------------------------------------------------------------------------------
@pytest.mark.parametrize("branch", ["oncology", "rare-disease"])
def test_corpus_files(branch, convert_dk):
    files = [f for f in corpus(branch) if (load(f)["metaData"].get("researchConsents") or [{}])[0].get("scope")][:3]
    files += [f for f in corpus(branch) if not load(f)["metaData"].get("researchConsents")][:1]
    assert len(files) >= 3
    for f in files:
        dk = load(f)
        md = dk["metaData"]
        bundle, rep = convert_dk(dk, str(f))
        check_mv_consent(bundle, md)
        broad = resources(bundle, profile=BROAD)
        assert len(broad) == sum(1 for rc in md.get("researchConsents") or [] if rc.get("scope"))
        for con, rc in zip(broad, [rc for rc in md.get("researchConsents") or [] if rc.get("scope")]):
            check_broad(con, bundle, rc)
        cp = one(bundle, BOARD)
        assert cp["created"] == md["molecularBoardDecisionDate"]
        assert cp["subject"]["reference"] == patient_ref(bundle)
        assert cp["status"] == ("active" if md["decisionToInclude"] else "revoked")
        assert cp["activity"][0]["detail"]["status"] == ("scheduled" if md["decisionToInclude"] else "cancelled")
        assert "metaData.submission.submitterId" in rep.preserved
        assert not structural_errors({"entry": [{"resource": r} for r in
                                                [*broad, cp, *resources(bundle, profile=MV)]]})


def test_corpus_rejected_and_no_scope(convert_dk):
    f, dk = first_with("oncology", lambda d: d["metaData"].get("decisionToInclude") is False and any(
        rc.get("noScopeJustification") for rc in d["metaData"].get("researchConsents") or []))
    md = dk["metaData"]
    bundle, rep = convert_dk(dk, str(f))
    cp = one(bundle, BOARD)
    det = cp["activity"][0]["detail"]
    assert cp["status"] == "revoked" and det["status"] == "cancelled"
    assert det["reasonCode"][0]["coding"][0] == {**det["reasonCode"][0]["coding"][0], "system": REJECT_CS,
                                                 "code": md["rejectionJustification"]}
    obs = resources(bundle, profile=ABSENT)
    assert len(obs) == sum(1 for rc in md["researchConsents"] if rc.get("noScopeJustification"))
    assert obs[0]["valueCodeableConcept"]["coding"][0]["display"] == md["researchConsents"][0]["noScopeJustification"]
    assert disposed(rep, "oncology", "metaData.researchConsents[].noScopeJustification")
    assert disposed(rep, "oncology", "metaData.rejectionJustification")
    assert disposed(rep, "oncology", "metaData.decisionToInclude")


# ---- (b) synthetic fixtures -------------------------------------------------------------------------------
def test_fixture_onco_edge(convert_dk):
    dk = load(FIX / "onco_edge.json")
    md = dk["metaData"]
    bundle, rep = convert_dk(dk, "onco_edge")
    con = check_mv_consent(bundle, md)
    assert con["dateTime"] == "2026-03-21"            # no presentationDate -> earliest signature date
    assert [p["type"] for p in con["provision"]["provision"]] == ["permit", "deny", "permit"]
    assert "metaData.mvConsent.presentationDate" not in rep.covered

    broad = one(bundle, BROAD)
    check_broad(broad, bundle, md["researchConsents"][0])
    assert broad["performer"] == [{"display": "Pseudonym xyz"}]   # sender-system reference removed, display kept
    assert "extension" not in broad                                 # unresolvable DomainReference dropped
    msgs = " ".join(m for _, m in rep.warnings)
    assert "LOINC 57016-8; added" in msgs and "DomainReference" in msgs and "replaced by presentationDate" in msgs

    obs = resources(bundle, profile=ABSENT)
    got = {o["valueCodeableConcept"]["coding"][0]["code"]: o for o in obs}
    assert set(got) == {"unable-to-consent", "refused", "documents-not-returned", "other-patient-reason",
                        "technical-reason", "not-implemented"}
    assert all(o["valueCodeableConcept"]["coding"][0]["system"] == ABSENCE_CS for o in obs)
    assert sorted(o["effectiveDateTime"] for o in obs) == [f"2026-03-{d}" for d in range(10, 16)]
    assert len({o["id"] for o in obs}) == 6

    cp = one(bundle, BOARD)
    assert cp["activity"][0]["detail"]["reasonCode"][0]["coding"][0]["code"] == "probablyNoGeneticCause"
    drops = {p for p, _, _ in rep.dropped}
    assert {"metaData.submission.diseaseType", "metaData.researchConsents[].schemaVersion"} <= drops
    # BfArM routing ids are kept as conversion Provenance agents (convert._provenance)
    assert {"metaData.submission.genomicDataCenterId", "metaData.submission.clinicalDataNodeId"} <= rep.preserved
    prov = resources(bundle, "Provenance")[0]
    assert {"https://genomde.de/fhir/sid/genomic-data-center", "https://genomde.de/fhir/sid/clinical-data-node"} <= \
        {a["who"]["identifier"]["system"] for a in prov["agent"]}


@pytest.mark.parametrize("reason", ["targetedDiagnosticRecommended", "probablyPsychosomaticIllness",
                                    "probablyCommonDisease", "probablyNoGeneticCause", "otherReason"])
def test_rejection_reasons(reason, convert_dk):
    dk = load(FIX / "onco_edge.json")
    dk["metaData"]["rejectionJustification"] = reason
    bundle, _ = convert_dk(dk)
    det = one(bundle, BOARD)["activity"][0]["detail"]
    assert det["reasonCode"][0]["coding"][0]["code"] == reason and det["status"] == "cancelled"


def test_included_with_reason_is_dropped(convert_dk):
    dk = load(FIX / "onco_edge.json")
    dk["metaData"]["decisionToInclude"] = True
    bundle, rep = convert_dk(dk)
    cp = one(bundle, BOARD)
    assert cp["status"] == "active" and "reasonCode" not in cp["activity"][0]["detail"]
    assert ("metaData.rejectionJustification", "probablyNoGeneticCause",
            "rejection reason with decisionToInclude = true") in rep.dropped


def test_presentation_date_and_ids_stable(convert_dk):
    dk = load(FIX / "onco_edge.json")
    dk["metaData"]["mvConsent"]["presentationDate"] = "2026-03-01"
    b1, rep = convert_dk(copy.deepcopy(dk))
    b2, _ = convert_dk(dk)
    assert one(b1, MV)["dateTime"] == "2026-03-01"
    assert "metaData.mvConsent.presentationDate" in rep.covered
    assert [e["fullUrl"] for e in b1["entry"]] == [e["fullUrl"] for e in b2["entry"]]


def test_fixture_rd_rejected(convert_dk):
    dk = load(FIX / "rd_rejected.json")
    bundle, rep = convert_dk(dk, "rd_rejected")
    check_mv_consent(bundle, dk["metaData"])
    check_broad(one(bundle, BROAD), bundle, dk["metaData"]["researchConsents"][0])
    det = one(bundle, BOARD)["activity"][0]["detail"]
    assert det["reasonCode"][0]["coding"][0]["code"] == "probablyPsychosomaticIllness"
    for path in ("metaData.rejectionJustification", "metaData.decisionToInclude",
                 "metaData.researchConsents[].noScopeJustification"):
        assert disposed(rep, "rare-disease", path), path


def test_profile_set_2026(convert_dk):
    for f in (FIX / "onco_edge.json", FIX / "rd_rejected.json"):
        bundle, _ = convert_dk(load(f), str(f), profile_set="2026")
        assert resources(bundle, profile=BROAD) and resources(bundle, profile=MV) and resources(bundle, profile=BOARD)


def run_block(dk, branch="oncology"):
    """Run the block's builders directly (inputs that fail the BfArM schema are rejected by convert())."""
    ctx = Ctx(dk, branch, case_key(dk, branch), "2027", strict=True)
    for b in (patient, consent, research_consent, submission):
        b.build(ctx)
    return {"entry": list(ctx.bundle.entries.values())}, ctx.report


def test_sender_references_and_bad_scope_entries():
    dk = load(FIX / "onco_edge.json")
    md = dk["metaData"]
    emb = md["researchConsents"][0]["scope"]
    emb["sourceReference"] = {"reference": "DocumentReference/abc"}
    emb["provision"]["provision"][0]["actor"] = [{"role": {"text": "x"}, "reference": {"reference": "Organization/o1"}}]
    md["mvConsent"]["scope"] += [{"type": "maybe", "date": "2026-03-21", "domain": "mvSequencing"},
                                 {"type": "permit", "domain": "reIdentification"}]
    bundle, rep = run_block(dk)
    broad = one(bundle, BROAD)
    assert "sourceReference" not in broad                    # reference 1..1 in the profile: unresolvable -> removed
    assert broad["provision"]["provision"][0]["actor"][0]["reference"] == {"display": "Organization/o1 (sender system)"}
    assert len(one(bundle, MV)["provision"]["provision"]) == 3
    drops = {(p, v) for p, v, _ in rep.dropped}
    assert ("metaData.mvConsent.scope[].type", "maybe") in drops
    assert ("metaData.mvConsent.scope[].date", "None") in drops or ("metaData.mvConsent.scope[].date", None) in drops


def test_unusable_mv_consent_is_dropped():
    dk = load(FIX / "onco_edge.json")
    dk["metaData"]["mvConsent"] = {"version": "v1", "presentationDate": "2026-01-01",
                                   "scope": [{"type": "permit", "date": "2026-01-02", "domain": "bogus"}]}
    bundle, rep = run_block(dk)
    assert not resources(bundle, profile=MV)
    drops = {p for p, _, _ in rep.dropped}
    assert {"metaData.mvConsent.scope[].domain", "metaData.mvConsent.version",
            "metaData.mvConsent.presentationDate"} <= drops


# ---- strict path / canonical check and the GRZ API -----------------------------------------------------------
@pytest.mark.parametrize("fixture,branch", [("onco_edge.json", "oncology"), ("rd_rejected.json", "rare-disease")])
def test_strict_paths(fixture, branch):
    dk = load(FIX / fixture)
    ctx = Ctx(dk, branch, case_key(dk, branch), "2027", strict=True)
    for b in (patient, consent, research_consent, submission):
        b.build(ctx)
    assert ctx.refs["mv_consent"] and ctx.refs["indication_board"] and ctx.bag["research_consents"]


def test_grz_api():
    f, dk = first_with("grz", lambda d: any(x.get("mvConsent") for x in d.get("donors") or []))
    embedded = load(FIX / "onco_edge.json")["metaData"]["researchConsents"][0]
    ctx = Ctx(dk, "grz", case_key(dk, "grz"), "2027", strict=True)
    pref = {"reference": "urn:uuid:donor"}
    for donor in dk["donors"]:
        dp = donor["donorPseudonym"]
        if donor.get("mvConsent"):
            assert consent.build_mv_consent(ctx, donor["mvConsent"], pref, "donors[].mvConsent", (dp,))
        for i, rc in enumerate(donor.get("researchConsents") or []):   # GRZ corpus: scope = {} -> dropped
            assert research_consent.build_research_consent(ctx, rc, pref, "donors[].researchConsents[]",
                                                           (dp, i)) is None
        assert research_consent.build_research_consent(ctx, embedded, pref, "donors[].researchConsents[]", (dp, 99))
    assert {"donors[].mvConsent.scope[].domain", "donors[].mvConsent.version",
            "donors[].researchConsents[].scope", "donors[].researchConsents[].presentationDate"} <= ctx.report.covered
    assert "mv_consent" not in ctx.refs     # per-donor consents are returned, not registered
    rs = [e["resource"] for e in ctx.bundle.entries.values()]
    assert len({r["id"] for r in rs}) == len(rs)
    assert all(r["patient"] == pref for r in rs if r["resourceType"] == "Consent")


# ---- (c) coverage ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("branch,files", [
    ("oncology", ["onco_edge.json"]),
    ("rare-disease", ["rd_rejected.json"]),
])
def test_coverage(branch, files, convert_dk):
    inputs = [load(FIX / f) for f in files]
    dk = load(FIX / files[0])           # variant with presentationDate (absent in the edge fixtures)
    dk["metaData"]["mvConsent"]["presentationDate"] = "2026-03-01"
    inputs.append(dk)
    covered, preserved, dropped = set(), set(), set()
    for dk in inputs:
        _, rep = convert_dk(dk)
        covered |= rep.covered
        preserved |= rep.preserved
        dropped |= {p for p, _, _ in rep.dropped}
    rows = block_rows(branch)
    mapped = {p for p, r in rows.items() if r["status"] == "MAPPED"}
    assert mapped and mapped <= covered, mapped - covered
    assert set(rows) <= covered | preserved | dropped, set(rows) - covered - preserved - dropped
