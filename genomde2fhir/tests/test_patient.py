"""Patient: 8-digit AGS -> destatis/ags extension on address.city; other strings -> address.text (preserved)."""
import copy

from conftest import corpus, load, resources

AGS_EXT = "http://fhir.de/StructureDefinition/destatis/ags"


def test_ags(convert_dk):
    dk = load(corpus("oncology")[0])
    ok, bad = copy.deepcopy(dk), copy.deepcopy(dk)
    ok["metaData"]["addressAGS"], bad["metaData"]["addressAGS"] = "08416041", "08416"
    b, rep = convert_dk(ok, "ags_ok")
    [addr] = resources(b, "Patient")[0]["address"]
    assert addr["_city"]["extension"][0]["url"] == AGS_EXT and "type" not in addr
    assert addr["_city"]["extension"][0]["valueCoding"]["code"] == "08416041"
    assert "metaData.addressAGS" in rep.covered
    b, rep = convert_dk(bad, "ags_bad")
    assert resources(b, "Patient")[0]["address"] == [{"country": "DE", "text": "AGS 08416"}]
    assert "metaData.addressAGS" in rep.preserved
