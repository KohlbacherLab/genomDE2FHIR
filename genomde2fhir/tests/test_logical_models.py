"""Logical models of the BfArM Datenkranz JSON Schemas (scripts/schema_to_logical.py) - the FML source types."""
import csv
import importlib.util
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from conftest import REPO, corpus, load

spec = importlib.util.spec_from_file_location("schema_to_logical", REPO / "scripts" / "schema_to_logical.py")
s2l = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s2l)

FIX = Path(__file__).parent / "fixtures" / "logical_models"
MB = "http://localhost:8091/matchboxv3/fhir"
BRANCH = {"oncology": "DatenkranzOncology", "rare-disease": "DatenkranzRareDisease", "grz": "DatenkranzGrz"}
CSV = {"DatenkranzOncology": "mapping_kdk_oncology.csv", "DatenkranzRareDisease": "mapping_kdk_rarediseases.csv",
       "DatenkranzGrz": "mapping_grz.csv"}

# Keys that occur in schema-valid corpus files but are declared neither by the BfArM schemas (the schemas do not set
# additionalProperties=false) nor as an extra (s2l.EXTRAS: the non-schema keys genomde2fhir reads, e.g. the legacy
# case.priorRd / case.priorDiagnostic / plan.*.variantReferences, genes[].display, germlineDiagnoses[].date and the
# embedded Broad Consent under researchConsents[].scope). Neither converter reads these; matchbox ignores them.
UNDECLARED = {
    "DatenkranzOncology": {
        "case.diagnosisOd.histology.text",            # free text next to the ICD-O-3 M coding
        "case.diagnosisOd.topography.text",
    },
    "DatenkranzRareDisease": {
        f"molecular.{v}.{k}" for v in ("smallVariants", "copyNumberVariants", "structuralVariants")
        for k in ("genes.system", "localization.display", "localization.system")  # schema: {code} only
    },
    "DatenkranzGrz": {"$schema", "_paired_with"},     # JSON-Schema pointer / corpus pairing annotation
}


def model(name):
    return load(REPO / "mvgs-ig" / "input" / f"StructureDefinition-{name}.json")


def elements(sd):
    return {e["path"]: e for e in sd["differential"]["element"]}


def test_generated_files_are_current():
    assert s2l.main(["--check"]) == 0, "run python scripts/schema_to_logical.py"


@pytest.mark.parametrize("name", list(BRANCH.values()))
def test_header_and_every_schema_property_present(name):
    sd = model(name)
    assert sd["url"] == sd["type"] == f"https://genomde.de/fhir/StructureDefinition/{name}"
    assert (sd["id"], sd["version"], sd["kind"], sd["derivation"]) == (name, "0.1.0", "logical", "specialization")
    assert sd["baseDefinition"] == "http://hl7.org/fhir/StructureDefinition/Base"
    assert "snapshot" not in sd
    assert s2l.check_model(name, sd) == []
    # bijection: every schema property path <-> exactly one element; the rest are the declared extras
    extras = s2l.extra_paths(name, sd)
    assert set(s2l.schema_paths(name)) == set(elements(sd)) - {name} - extras
    assert {f"{name}.{rel}" for m, rel, kind, _, _ in s2l.EXTRAS if m == name and kind != "Consent"} <= extras
    assert all(e["min"] == 0 for e in elements(sd).values() if e["path"] in extras
               and e["path"].rsplit(".", 1)[0] not in extras)        # an extra is never required


@pytest.mark.parametrize("name", list(BRANCH.values()))
def test_every_mapping_table_path_is_an_element(name):
    els = elements(model(name))
    rows = list(csv.DictReader((REPO / "mapping" / CSV[name]).open(encoding="utf-8")))
    missing = [r["path"] for r in rows if f"{name}.{r['path'].replace('[]', '')}" not in els]
    assert rows and missing == []


def test_type_rules_on_real_schemas():
    onc, rd, grz = (elements(model(n)) for n in BRANCH.values())
    t = lambda els, p: els[p]["type"][0]["code"]  # noqa: E731
    # dates stay strings, enums are strings with the values in the definition
    assert t(onc, "DatenkranzOncology.metaData.molecularBoardDecisionDate") == "string"
    gender = onc["DatenkranzOncology.metaData.gender"]
    assert t(onc, "DatenkranzOncology.metaData.gender") == "string" and "'unknown'" in gender["definition"]
    # integer / decimal / boolean
    assert t(onc, "DatenkranzOncology.molecular.smallVariants.startPosition") == "integer"
    assert t(grz, "DatenkranzGrz.donors.labData.tumorCellCount.count") == "decimal"
    assert t(onc, "DatenkranzOncology.metaData.decisionToInclude") == "boolean"
    # arrays, required -> min 1, allOf-merged Coding + date
    assert onc["DatenkranzOncology.molecular.smallVariants"]["max"] == "*"
    assert onc["DatenkranzOncology.metaData.tanC"]["min"] == 1
    assert onc["DatenkranzOncology.metaData.localCaseId"]["min"] == 0
    for leaf in ("code", "system", "version", "display", "date"):
        assert f"DatenkranzOncology.case.diagnosisOd.mainDiagnosis.{leaf}" in onc
    # oneOf is recorded; the MII Consent object (opaque in the schema) gets the Consent elements as extras, with
    # FHIR datatypes at the leaves and a fixed provision depth
    rc = onc["DatenkranzOncology.metaData.researchConsents"]
    assert "oneOf" in rc["definition"] and rc["min"] == 0
    for els, scope in ((onc, "DatenkranzOncology.metaData.researchConsents.scope"),
                       (rd, "DatenkranzRareDisease.metaData.researchConsents.scope"),
                       (grz, "DatenkranzGrz.donors.researchConsents.scope")):
        assert t(els, scope) == "BackboneElement" and "OPAQUE" not in els[scope]["definition"]
        assert "EXTRA" in els[scope]["definition"] and not els[scope]["definition"].startswith("EXTRA")
        assert (t(els, scope + ".resourceType"), t(els, scope + ".status"), t(els, scope + ".category"),
                t(els, scope + ".extension"), t(els, scope + ".policy.uri"), t(els, scope + ".provision.period"),
                t(els, scope + ".provision.provision.code")) == (
                    "string", "string", "CodeableConcept", "Extension", "string", "Period", "CodeableConcept")
        assert els[scope + ".category"]["max"] == "*" and els[scope + ".provision"]["max"] == "1"
        assert els[scope + ".provision.provision"]["max"] == "*"
        assert scope + ".provision.provision.provision.provision" not in els
        assert scope + ".text" not in els and scope + ".contained" not in els
    # legacy keys: a copy of the schema key's tree
    assert t(onc, "DatenkranzOncology.case.priorDiagnostic") == "BackboneElement"
    assert onc["DatenkranzOncology.case.priorDiagnostic"]["max"] == "1"
    assert "DatenkranzOncology.case.priorDiagnostic.simpleVariants.gene.code" in onc
    assert rd["DatenkranzRareDisease.case.priorRd"]["max"] == "*"
    assert t(rd, "DatenkranzRareDisease.plan.recommendedTherapies.variantReferences") == "string"
    assert t(rd, "DatenkranzRareDisease.molecular.smallVariants.genes.display") == "string"
    assert t(onc, "DatenkranzOncology.case.diagnosisOd.germlineDiagnoses.date") == "string"
    # nullable / if-then annotations
    assert "nullable" in onc["DatenkranzOncology.followUp.followUpOds.deathDate"]["definition"]
    assert "requires name" in onc["DatenkranzOncology.case.priorProcedures.substances"]["definition"]
    # property named like the inherited Element.id
    assert "DatenkranzRareDisease.plan.recommendedStudies.id" in rd


@pytest.mark.parametrize("branch", list(BRANCH))
def test_corpus_instances_fit_the_model(branch):
    name = BRANCH[branch]
    sd = s2l.build(name)
    files = corpus(branch)
    assert len(files) >= 3
    allowed = {f"no element for {name}.{p}" for p in UNDECLARED[name]}
    seen = set()
    for f in files:
        probs = set(s2l.instance_problems(sd, load(f)))
        assert probs <= allowed, (f, sorted(probs - allowed)[:5])
        seen |= probs
    assert seen <= allowed


def test_synthetic_fixture_constructs():
    spec_ = (FIX / "edge-schema.json", "Edge", "synthetic edge schema")
    sd = s2l.build("Edge", spec_)
    assert s2l.check_model("Edge", sd, FIX / "edge-schema.json") == []
    els = elements(sd)
    code = lambda p: els[f"Edge.{p}"]["type"][0]["code"]  # noqa: E731
    assert code("meta.date") == "string" and "format=\"date\"" in els["Edge.meta.date"]["definition"]
    assert code("meta.kind") == "string" and "'alpha', 'beta', 'unknown'" in els["Edge.meta.kind"]["definition"]
    assert code("meta.untypedEnum") == "string"
    assert (code("meta.count"), code("meta.ratio"), code("meta.flag")) == ("integer", "decimal", "boolean")
    assert "nullable" in els["Edge.meta.endDate"]["definition"]
    assert code("meta.opaque") == "BackboneElement" and "OPAQUE" in els["Edge.meta.opaque"]["definition"]
    assert (els["Edge.items"]["min"], els["Edge.items"]["max"]) == (1, "*")          # required + minItems 1
    assert (els["Edge.optionalList"]["min"], els["Edge.optionalList"]["max"]) == (0, "*")  # required, no minItems
    assert code("optionalList") == "string"
    assert els["Edge.items.scope"]["min"] == 0 and els["Edge.items.justification"]["min"] == 0  # oneOf branches
    assert "oneOf" in els["Edge.items"]["definition"]
    assert {f"Edge.coded.{k}" for k in ("system", "version", "code", "display", "date")} <= set(els)
    assert els["Edge.coded.code"]["min"] == 1 and els["Edge.coded.system"]["min"] == 0
    assert els["Edge.items.substances.name"]["min"] == 0
    assert "requires name" in els["Edge.items.substances"]["definition"]
    assert code("items.substances.code.code") == "string"
    assert s2l.instance_problems(sd, load(FIX / "edge-instance.json")) == []
    assert s2l.instance_problems(sd, {"meta": {"count": "3", "bogus": 1}}) == [
        "string value for integer element Edge.meta.count", "no element for Edge.meta.bogus"]


@pytest.mark.parametrize("bad, msg", [
    ({"type": "object", "properties": {"a": {"type": ["string", "null"]}}}, "type lists"),
    ({"type": "object", "additionalProperties": False, "properties": {}}, "unsupported JSON-Schema keyword"),
    ({"type": "object", "properties": {"a": {"type": "array", "items": [{"type": "string"}]}}}, "tuple-style"),
    ({"type": "object", "properties": {"a": {"$ref": "https://example.org/x.json"}}}, "external $ref"),
    ({"type": "object", "properties": {"a": {"type": "array", "items": {"type": "array", "items": {}}}}},
     "nested arrays"),
    ({"type": "object", "properties": {"$schema": {"type": "string"}}}, "valid FHIR element name"),
    ({"type": "object", "properties": {"a": {"not": {"type": "string"}}}}, "unsupported JSON-Schema keyword"),
    ({"type": "object", "properties": {"a": {"description": "untyped"}}}, "single type"),
    ({"type": "object", "properties": {"a": {"type": "null"}}}, "unsupported type"),
])
def test_unsupported_constructs_fail_loudly(tmp_path, bad, msg):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(s2l.SchemaError, match=re.escape(msg)):
        s2l.build("Bad", (p, "Bad", "bad"))


# ------------------------------------------------------------------------------------ matchbox $transform probe
def _http(method, url, data, ctype):
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": ctype, "Accept": "application/fhir+json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as ex:
        return ex.code, json.loads(ex.read() or b"{}")


@pytest.fixture(scope="module")
def matchbox():
    try:
        urllib.request.urlopen(f"{MB}/StructureDefinition/DatenkranzGrz", timeout=5).read()
    except Exception:
        pytest.skip("matchbox-2027 not reachable or logical models not installed (build_mvgs.py --install)")
    return MB


@pytest.mark.parametrize("branch", list(BRANCH))
def test_matchbox_transform_with_probe_map(matchbox, branch):
    name = BRANCH[branch]
    st, sm = _http("POST", f"{matchbox}/StructureMap",
                   (REPO / "mappers" / "fml" / "test" / f"{name}Probe.map").read_bytes(), "text/fhir-mapping")
    assert st < 300 and sm["resourceType"] == "StructureMap", sm
    for f in corpus(branch)[:3]:
        dk = load(f)
        st, out = _http("POST", f"{matchbox}/StructureMap/$transform?source=" + urllib.parse.quote(sm["url"], safe=""),
                        f.read_bytes(), "application/fhir+json")
        assert st == 200 and out["resourceType"] == "Patient", (f, out)
        values = {i["system"].rsplit("/", 1)[1]: i["value"] for i in out["identifier"]}
        if branch == "grz":
            assert values["probe-tang"] == dk["submission"]["tanG"]
        else:
            assert values["probe-tanc"] == dk["metaData"]["tanC"]
            assert out["birthDate"] == dk["metaData"]["birthDate"]
