"""grz.donors: one Patient per donor, family history, Coverage, genomic study, submission Organizations/Provenance."""
import csv
from pathlib import Path

import pytest
from conftest import corpus, first_with, load, resources

from genomde2fhir.builders.consent import build_mv_consent
from genomde2fhir.builders.research_consent import build_research_consent
from genomde2fhir.systems import SID_DONOR, SID_LOCAL_CASE, SID_TAN_G, SNOMED

FIX = Path(__file__).parent / "fixtures" / "grz_donors"
CSV = Path(__file__).resolve().parents[1] / "src" / "genomde2fhir" / "data" / "mapping" / "mapping_grz.csv"
FMH = "modul-molgen/StructureDefinition/familienanamnese"
PAT = "PatientPseudonymisiert"


def block_rows():
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    return {r["path"]: r["status"] for r in rows
            if (r["path"].startswith("donors[].") and not r["path"].startswith("donors[].labData"))
            or r["path"].startswith("submission.")}


def study_of(bundle, name: str = "genomic-study") -> list[dict]:
    """Genomic study Procedures by exact profile name (the substring would also match '-genomic-study-analysis')."""
    return [r for r in resources(bundle, "Procedure")
            if any(p.rsplit("/", 1)[-1].endswith(name) for p in r.get("meta", {}).get("profile", []))]


def ident(r, system):
    return next((i["value"] for i in r.get("identifier", []) if i["system"] == system), None)


def implemented(builder, src: dict, prefix: str, parts: tuple) -> bool:
    """The consent builders are written by another work package; a builder that returns None without touching
    ctx is still the stub, and its donors[].mvConsent.* / researchConsents[].* rows are delegated, not asserted."""
    class Probe:  # any attribute access means the builder does real work
        def __getattr__(self, item):
            raise RuntimeError(item)
    try:
        return builder(Probe(), src, {"reference": "urn:uuid:x"}, prefix, parts) is not None
    except Exception:
        return True


MV_SAMPLE = {"version": "v1", "presentationDate": "2024-01-01",
             "scope": [{"type": "permit", "date": "2024-01-01", "domain": "mvSequencing"}]}
RC_SAMPLE = {"schemaVersion": "2025.0.1", "presentationDate": "2024-01-01", "scope": {"resourceType": "Consent"}}


# ---- corpus files ------------------------------------------------------------------------------------------
def test_single_donor_index(convert_dk):
    f, dk = first_with("grz", lambda d: len(d["donors"]) == 1 and d["donors"][0]["relation"] == "index")
    bundle, rep = convert_dk(dk, str(f))
    pats = resources(bundle, "Patient", PAT)
    assert len(pats) == 1
    p, s = pats[0], dk["submission"]
    assert ident(p, SID_TAN_G) == s["tanG"]
    assert ident(p, SID_LOCAL_CASE) == f"{s['submitterId']}|{s['localCaseId']}"
    assert ident(p, SID_DONOR) == f"{s['submitterId']}|{dk['donors'][0]['donorPseudonym']}"
    assert p["gender"] == dk["donors"][0]["gender"]
    assert not resources(bundle, "FamilyMemberHistory")
    study = study_of(bundle)
    assert len(study) == 1 and study[0]["subject"]["reference"] == f"urn:uuid:{p['id']}"
    design = study[0]["extension"][0]["valueCoding"]
    assert design["code"] == s["genomicStudyType"]
    assert {"donors[].donorPseudonym", "donors[].gender", "donors[].relation", "submission.tanG",
            "submission.localCaseId"} <= rep.covered


def test_trio_family_history(convert_dk):
    f, dk = first_with("grz", lambda d: {x["relation"] for x in d["donors"]} == {"index", "mother", "father"})
    bundle, rep = convert_dk(dk, str(f))
    pats = {p["id"]: p for p in resources(bundle, "Patient", PAT)}
    assert len(pats) == 3
    index = next(p for p in pats.values() if ident(p, SID_TAN_G))
    fmhs = resources(bundle, "FamilyMemberHistory", FMH)
    assert len(fmhs) == 2
    codes = set()
    for h in fmhs:
        assert h["patient"]["reference"] == f"urn:uuid:{index['id']}"
        rel_pat = h["extension"][0]["valueReference"]["reference"].removeprefix("urn:uuid:")
        assert rel_pat in pats and rel_pat != index["id"]
        assert not ident(pats[rel_pat], SID_TAN_G) and not ident(pats[rel_pat], SID_LOCAL_CASE)
        codes |= {c["code"] for c in h["relationship"]["coding"] if c["system"] == SNOMED}
    assert codes == {"72705000", "66839005"}


@pytest.mark.parametrize("disease,profile", [("oncological", "mii-pr-mtb-genomic-study"),
                                             ("rare", "mii-pr-molgen-genomic-study"),
                                             ("hereditary", "mii-pr-molgen-genomic-study")])
def test_study_profile_by_disease(convert_dk, disease, profile):
    f, dk = first_with("grz", lambda d: d["submission"]["diseaseType"] == disease)
    bundle, rep = convert_dk(dk, str(f))
    study = study_of(bundle, profile)
    assert len(study) == 1
    assert study[0]["reasonCode"][0]["coding"][0]["code"] == disease
    lab = resources(bundle, "Organization")
    assert any(o.get("name") == dk["submission"]["labName"] for o in lab)
    assert "submission.labName" in rep.covered


def test_coverage_and_provenance(convert_dk):
    f, dk = first_with("grz", lambda d: d["submission"]["coverageType"] == "GKV")
    bundle, rep = convert_dk(dk, str(f))
    cov = resources(bundle, "Coverage", "coverage-de-basis")
    assert len(cov) == 1 and cov[0]["type"]["coding"][0]["code"] == "GKV"
    prov = [p for p in resources(bundle, "Provenance") if p.get("occurredDateTime")]
    assert len(prov) == 1 and prov[0]["occurredDateTime"] == dk["submission"]["submissionDate"]
    assert len(prov[0]["agent"]) == 3


def test_ids_registered_for_labdata():
    from genomde2fhir.builders.grz import donors
    from genomde2fhir.context import Ctx
    from genomde2fhir.identity import case_key
    dk = load(FIX / "all_relations.json")
    ctx = Ctx(dk, "grz", case_key(dk, "grz"), strict=True)
    donors.build(ctx)
    for d in dk["donors"]:
        assert ("donor", d["donorPseudonym"]) in ctx.ids
    assert ctx.refs["patient"] == ctx.ids[("donor", dk["submission"]["tanG"])]
    assert {"coverage", "genomic_study", "lab", "mv_consent"} <= set(ctx.refs)
    index = dk["submission"]["tanG"]
    mv = next(r for r in ctx.bundle.bundle()["entry"] if r["fullUrl"] == ctx.refs["mv_consent"]["reference"])
    assert mv["resource"]["patient"] == ctx.ids[("donor", index)]


def test_profile_set_2026(convert_dk):
    for f in corpus("grz")[:2]:
        convert_dk(load(f), str(f), profile_set="2026")


# ---- synthetic fixtures -------------------------------------------------------------------------------------
def test_fixture_all_relations(convert_dk):
    dk = load(FIX / "all_relations.json")
    bundle, rep = convert_dk(dk, "all_relations", strict=True)
    pats = resources(bundle, "Patient", PAT)
    assert len(pats) == 7
    index = next(p for p in pats if ident(p, SID_TAN_G))
    assert index["gender"] == "other" and index["_gender"]["extension"][0]["valueCoding"]["code"] == "D"
    fmhs = resources(bundle, "FamilyMemberHistory", FMH)
    roles = sorted(c["code"] for h in fmhs for c in h["relationship"]["coding"] if "RoleCode" in c["system"])
    assert roles == ["BRO", "CHILD", "FTH", "MTH", "SIS"]
    assert {h["sex"]["coding"][0]["code"] for h in fmhs} == {"female", "male", "unknown"}
    assert [d[1] for d in rep.dropped if d[0] == "donors[].relation"] == ["other"]
    study = study_of(bundle, "mii-pr-mtb-genomic-study")[0]
    assert study["code"]["coding"][0]["code"] == "tumor+germline"
    assert study["extension"][0]["valueCoding"]["code"] == "trio"
    prov = [p for p in resources(bundle, "Provenance") if p.get("occurredDateTime")][0]
    assert "coding" not in prov["activity"] and "test" in prov["activity"]["text"]


def test_fixture_no_index_unk_coverage(convert_dk):
    dk = load(FIX / "no_index_unk_coverage.json")
    bundle, rep = convert_dk(dk, "no_index", strict=True)
    cov = resources(bundle, "Coverage", "coverage-de-basis")   # UNK: v3-NullFlavor, part of VersicherungsartDeBasisVS
    assert [c["system"] + "#" + c["code"] for c in cov[0]["type"]["coding"]] == [
        "http://terminology.hl7.org/CodeSystem/v3-NullFlavor#UNK"]
    assert "submission.coverageType" in rep.covered
    assert not resources(bundle, "FamilyMemberHistory")
    assert len([d for d in rep.dropped if d[0] == "donors[].relation"]) == 2
    pats = resources(bundle, "Patient", PAT)
    assert sum(1 for p in pats if ident(p, SID_TAN_G)) == 1
    assert any("no donor with relation 'index'" in m for _, m in rep.warnings)
    prov = [p for p in resources(bundle, "Provenance") if p.get("occurredDateTime")][0]
    assert prov["activity"]["coding"][0]["code"] == "UPDATE"


def test_fixture_duplicate_index_skt(convert_dk):
    dk = load(FIX / "duplicate_index_skt.json")
    bundle, rep = convert_dk(dk, "dup_index", strict=True)
    pats = resources(bundle, "Patient", PAT)
    assert len(pats) == 2 and sum(1 for p in pats if ident(p, SID_TAN_G)) == 1
    assert not resources(bundle, "FamilyMemberHistory")        # a second 'index' is no relationship
    assert [d[1] for d in rep.dropped if d[0] == "donors[].relation"] == ["index"]
    cov = resources(bundle, "Coverage", "coverage-de-basis")[0]
    assert cov["type"]["coding"][0]["system"] == "https://fhir.kbv.de/CodeSystem/KBV_CS_FOR_Payor_Type_KBV"
    assert cov["type"]["coding"][0]["code"] == "SKT"
    assert study_of(bundle, "mii-pr-molgen-genomic-study")[0]["reasonCode"][0]["coding"][0]["code"] == "rare"
    prov = [p for p in resources(bundle, "Provenance") if p.get("occurredDateTime")][0]
    assert prov["activity"]["coding"][0]["code"] == "APPEND"
    assert len(resources(bundle, "Consent", "mvgs-consent")) == 2 and "donors[].mvConsent.version" in rep.covered


def test_ids_deterministic(convert_dk):
    dk = load(FIX / "all_relations.json")
    a, _ = convert_dk(dk)
    b, _ = convert_dk(load(FIX / "all_relations.json"))
    assert [e["fullUrl"] for e in a["entry"]] == [e["fullUrl"] for e in b["entry"]]


# ---- coverage of the block ----------------------------------------------------------------------------------
def test_block_coverage(convert_dk):
    inputs = [load(FIX / f) for f in ("all_relations.json", "no_index_unk_coverage.json", "duplicate_index_skt.json")]
    inputs += [load(f) for f in corpus("grz")[:6]]
    seen = set()
    for dk in inputs:
        _, rep = convert_dk(dk)
        seen |= rep.covered | rep.preserved | {p for p, _, _ in rep.dropped}
    rows = block_rows()
    mapped = {p for p, s in rows.items() if s == "MAPPED"}
    known_uncoverable = {}
    for builder, sample, prefix in ((build_mv_consent, MV_SAMPLE, "donors[].mvConsent"),
                                    (build_research_consent, RC_SAMPLE, "donors[].researchConsents[]")):
        if not implemented(builder, sample, prefix, ("p", 0)):
            known_uncoverable |= {p: f"delegated to {builder.__module__} (stub)" for p in mapped
                                  if p.startswith(prefix)}
    missing = mapped - seen - set(known_uncoverable)
    assert not missing, missing
    # NOMAP transport rows are kept as Organizations / Provenance / genomic study (preserved)
    nomap_kept = {"submission.submitterId", "submission.genomicDataCenterId", "submission.clinicalDataNodeId",
                  "submission.submissionDate", "submission.submissionType", "submission.diseaseType",
                  "submission.genomicStudyType", "submission.genomicStudySubtype", "submission.labName"}
    assert nomap_kept <= seen
