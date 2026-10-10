"""Fix round 4, HARMONIZE: KDK and GRZ handle the submission block the same way.

submitterId, clinicalDataNodeId and genomicDataCenterId give the same core Organizations (id rule, identifier, name)
and the same Provenance.agent references in both streams (builders/submission.submission_organization); the mapping
rows of the shared submission fields carry the same status, fhir_element and transform in the KDK and GRZ tables.
diseaseType is the intended exception (KDK NOMAP / dropped, GRZ DRAFT / genomic study). Fixtures only, no server."""
import csv
import json
from pathlib import Path

import pytest
from conftest import REPO, resources

from genomde2fhir.convert import PROVENANCE_AGENT, convert
from genomde2fhir.identity import case_key
from genomde2fhir.systems import SID_GDC, SID_KDK, SID_LE

FIX = Path(__file__).parent / "fixtures"
ONCO = FIX / "onco_variants" / "synthetic_small_variants.json"
RD = FIX / "consent" / "rd_rejected.json"
GRZ = FIX / "grz_labdata" / "grz-labdata-rd-duo.json"
ROUTING = {"submitterId": ("submitter", SID_LE, "Leistungserbringer (submitter)", "author"),
           "clinicalDataNodeId": ("clinical-data-node", SID_KDK, "Klinischer Datenknoten", "custodian"),
           "genomicDataCenterId": ("genomic-data-center", SID_GDC, "Genomrechenzentrum", "custodian")}
VALUES = {"submitterId": "260840108", "clinicalDataNodeId": "KDKTUE009", "genomicDataCenterId": "GRZTUE009"}


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def kdk(path=ONCO, **sub) -> dict:
    dk = load(path)
    dk["metaData"]["submission"].update(VALUES, **sub)
    return dk


def grz(**sub) -> dict:
    dk = load(GRZ)
    dk["submission"].update(VALUES, **sub)
    return dk


def submission(dk) -> dict:
    return dk["metaData"]["submission"] if "metaData" in dk else dk["submission"]


def run(dk, **kw):
    bundle, rep = convert(dk, "<fix>", **kw)
    assert rep.status == "converted", rep.error or rep.input_findings
    return bundle, rep


def routing_orgs(bundle) -> dict:
    """{system: Organization} of the submission Organizations (the GRZ lab has no identifier)."""
    systems = {s for _, s, _, _ in ROUTING.values()}
    return {o["identifier"][0]["system"]: o for o in resources(bundle, "Organization")
            if o.get("identifier") and o["identifier"][0]["system"] in systems}


def body(org) -> dict:
    return {k: v for k, v in org.items() if k not in ("id", "meta")}


CASES = [pytest.param(lambda **s: kdk(ONCO, **s), "metaData.submission.", id="kdk-onco"),
         pytest.param(lambda **s: kdk(RD, **s), "metaData.submission.", id="kdk-rd"),
         pytest.param(grz, "submission.", id="grz")]


@pytest.mark.parametrize("make,prefix", CASES)
def test_routing_organizations_and_provenance_agents(make, prefix):
    dk = make()
    bundle, rep = run(dk)
    key = case_key(dk, rep.branch)
    orgs = routing_orgs(bundle)
    full = {e["resource"]["id"]: e["fullUrl"] for e in bundle["entry"]}
    [prov] = resources(bundle, "Provenance")
    agents = {a["who"]["identifier"]["system"]: a for a in prov["agent"] if "identifier" in a["who"]
              and a["who"]["identifier"]["system"] != PROVENANCE_AGENT}
    for field, (role, system, label, ptype) in ROUTING.items():
        val = VALUES[field]
        org = orgs[system]
        assert org["id"] == key.id("Organization", role, val)          # same id rule in both streams
        assert body(org) == {"resourceType": "Organization", "identifier": [{"system": system, "value": val}],
                             "active": True, "name": f"{label} {val}"}
        a = agents[system]
        assert a["type"]["coding"][0]["code"] == ptype
        assert a["who"]["reference"] == full[org["id"]]
        assert a["who"]["identifier"] == {"system": system, "value": val}
        assert prefix + field in rep.preserved
    assert rep.representations["submission-organization"] == 3


def test_kdk_and_grz_build_identical_organizations_for_the_same_values():
    (kb, _), (gb, _) = run(kdk()), run(grz())
    k, g = routing_orgs(kb), routing_orgs(gb)
    assert set(k) == set(g) == {s for _, s, _, _ in ROUTING.values()}
    for system in k:
        assert body(k[system]) == body(g[system])
        assert k[system]["id"] != g[system]["id"]      # the stream is part of every id (stream isolation)

    def agents(b):
        [prov] = resources(b, "Provenance")
        return [(a["type"]["coding"][0]["code"], a["who"]["display"], a["who"]["identifier"])
                for a in prov["agent"][1:]]
    assert agents(kb) == agents(gb)


@pytest.mark.parametrize("make,prefix", CASES)
def test_routing_ids_kept_without_the_provenance(make, prefix):
    bundle, rep = run(make(), provenance=False)
    assert not resources(bundle, "Provenance")
    assert len(routing_orgs(bundle)) == 3
    assert {prefix + f for f in ROUTING} <= rep.preserved


def test_kdk_without_genomic_data_center():
    dk = kdk()
    del dk["metaData"]["submission"]["genomicDataCenterId"]     # optional in KDK (no sequencing)
    bundle, rep = run(dk)
    assert SID_GDC not in routing_orgs(bundle)
    [prov] = resources(bundle, "Provenance")
    assert SID_GDC not in {a["who"].get("identifier", {}).get("system") for a in prov["agent"]}
    assert "metaData.submission.genomicDataCenterId" not in rep.preserved


@pytest.mark.parametrize("make,prefix", CASES[:2])
def test_kdk_disease_type_still_dropped(make, prefix):
    _, rep = run(make())
    assert any(p == prefix + "diseaseType" for p, _, _ in rep.dropped)


def test_grz_disease_type_still_on_the_genomic_study():
    bundle, rep = run(grz())
    assert "submission.diseaseType" in rep.preserved
    assert any(p.get("reasonCode") for p in resources(bundle, "Procedure"))


# ---- mapping table -------------------------------------------------------------------------------------------------
def rows(name, prefix) -> dict:
    with (REPO / "mapping" / name).open(encoding="utf-8", newline="") as f:
        return {r["path"][len(prefix):]: r for r in csv.DictReader(f) if r["path"].startswith(prefix)}


SHARED = {"submitterId": "submitterId", "clinicalDataNodeId": "clinicalDataNodeId",
          "genomicDataCenterId": "genomicDataCenterId", "date": "submissionDate", "type": "submissionType"}
KDK_TABLES = ("mapping_kdk_oncology.csv", "mapping_kdk_rarediseases.csv")


@pytest.mark.parametrize("table", KDK_TABLES)
def test_shared_submission_rows_match_grz(table):
    g, k = rows("mapping_grz.csv", "submission."), rows(table, "metaData.submission.")
    for kf, gf in SHARED.items():
        for col in ("status", "fhir_element", "transform"):
            assert k[kf][col] == g[gf][col], (table, kf, col)
        assert k[kf]["status"] == "DRAFT"
        assert "harmonized submission rows" in k[kf]["notes"] and "harmonized submission rows" in g[gf]["notes"]
    for f in ("date", "type"):
        assert "urn:genomde2fhir:submission:<submitterId>:<caseId>:<date>:<type>" in k[f]["transform"]
        assert "|<caseKey>|" not in k[f]["transform"]


@pytest.mark.parametrize("table", KDK_TABLES)
def test_disease_type_rows_differ_with_a_reason(table):
    g, k = rows("mapping_grz.csv", "submission.")["diseaseType"], rows(table, "metaData.submission.")["diseaseType"]
    assert (g["status"], k["status"]) == ("DRAFT", "NOMAP")
    for r in (g, k):
        assert "diseaseType differs on purpose" in r["notes"]
    assert "dropped" in k["transform"]


@pytest.mark.parametrize("table", ("mapping_grz.csv",) + KDK_TABLES)
def test_package_copy_and_crlf(table):
    src = (REPO / "mapping" / table).read_bytes()
    assert src == (REPO / "genomde2fhir/src/genomde2fhir/data/mapping" / table).read_bytes()
    assert src.count(b"\r\n") == src.count(b"\n")
