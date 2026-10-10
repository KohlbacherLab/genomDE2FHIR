#!/usr/bin/env python3
"""Generate FHIR logical models (the FML source types) from the BfArM Datenkranz JSON Schemas.

  schemas/kdk/Oncology.json      -> mvgs-ig/input/StructureDefinition-DatenkranzOncology.json
  schemas/kdk/RareDiseases.json  -> mvgs-ig/input/StructureDefinition-DatenkranzRareDisease.json
  schemas/grz/grz-schema.json    -> mvgs-ig/input/StructureDefinition-DatenkranzGrz.json

Usage: python3 scripts/schema_to_logical.py [--check]
  --check   do not write; exit 1 if an output file is stale

Mapping rules (StructureDefinition kind=logical, derivation=specialization, base Base, differential only):
  * element path = JSON property name, nested objects -> BackboneElement, arrays -> max '*'
  * string (incl. format date/date-time/uri) -> string (dates stay strings so FML copies them verbatim),
    integer -> integer, number -> decimal, boolean -> boolean; enums -> string, enum listed in definition
  * $ref (local '#/...' and absolute BfArM URLs -> files under schemas/kdk), allOf / oneOf / anyOf /
    if-then are merged; alternatives and conditional requirements are recorded in the definition
  * an object schema without properties (researchConsents[].scope = embedded MII Consent resource) becomes a
    BackboneElement without children, flagged as opaque in the definition
  * min = 1 only for unconditionally required properties (arrays additionally need minItems >= 1)
  * any JSON-Schema keyword not handled here raises SchemaError (fail loudly, never silently drop)
  * EXTRAS (one explicit list below): properties the schemas do not declare, or declare as an opaque object, but
    that genomde2fhir reads (pre-KDK-1.6.5 legacy keys, extra properties of the synthetic corpora, the embedded MII
    Broad Consent under researchConsents[].scope). matchbox drops every input property the model leaves undeclared
    (mappers/fml/README.md, quirk Q6), so the FML maps can only see them once they are declared. Every extra element
    is marked "EXTRA (legacy/non-schema property accepted by genomde2fhir)" in its definition.

After generating, check_model() walks the schema independently and asserts that every property path is
present in the model with a compatible type (and that every other element is a declared extra).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KDK = ROOT / "schemas" / "kdk"
GRZ = ROOT / "schemas" / "grz"
OUT = ROOT / "mvgs-ig" / "input"
BASE = "https://genomde.de/fhir/StructureDefinition/"
VERSION = "0.1.0"
KDK_URL_MARK = "/MVGenomseq_KDK/main/KDK/"

MODELS = {
    "DatenkranzOncology": (KDK / "Oncology.json",
                           "genomDE KDK Oncology Datenkranz (logical model)",
                           "BfArM MV-GenomSeq KDK oncology submission (schemas/kdk/Oncology.json)"),
    "DatenkranzRareDisease": (KDK / "RareDiseases.json",
                              "genomDE KDK Rare Disease Datenkranz (logical model)",
                              "BfArM MV-GenomSeq KDK rare-disease submission (schemas/kdk/RareDiseases.json)"),
    "DatenkranzGrz": (GRZ / "grz-schema.json",
                      "genomDE GRZ metadata Datenkranz (logical model)",
                      "BfArM MV-GenomSeq GRZ metadata submission (schemas/grz/grz-schema.json)"),
}

PRIMITIVE = {"string": "string", "integer": "integer", "number": "decimal", "boolean": "boolean"}
# keywords that only annotate / constrain values; rendered into the definition text where useful
ANNOTATION = {"$id", "$schema", "$comment", "$dynamicAnchor", "title", "description", "format", "pattern",
              "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength",
              "minItems", "maxItems", "default", "examples", "nullable", "$defs", "definitions"}
STRUCTURAL = {"type", "properties", "required", "items", "enum", "$ref", "allOf", "oneOf", "anyOf", "if", "then",
              "else"}
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class SchemaError(Exception):
    pass


# ---------------------------------------------------------------------------------------------- $ref resolution
class Resolver:
    def __init__(self):
        self.docs: dict[Path, dict] = {}

    def load(self, path: Path) -> dict:
        path = path.resolve()
        if path not in self.docs:
            self.docs[path] = json.loads(path.read_text(encoding="utf-8"))
        return self.docs[path]

    def resolve(self, ref: str, doc_path: Path) -> tuple[dict, Path]:
        url, _, frag = ref.partition("#")
        if url:
            if KDK_URL_MARK not in url:
                raise SchemaError(f"unsupported external $ref {ref!r} (only BfArM KDK URLs are mapped to files)")
            target = (KDK / url.split(KDK_URL_MARK, 1)[1]).resolve()
            if not target.exists():
                raise SchemaError(f"$ref {ref!r} -> {target} does not exist")
        else:
            target = doc_path
        node = self.load(target)
        if frag:
            if not frag.startswith("/"):
                raise SchemaError(f"unsupported $ref fragment (anchor) {ref!r}")
            for part in frag[1:].split("/"):
                part = part.replace("~1", "/").replace("~0", "~")
                if not isinstance(node, dict) or part not in node:
                    raise SchemaError(f"$ref {ref!r}: pointer segment {part!r} not found")
                node = node[part]
        return node, target


# --------------------------------------------------------------------------------------- schema normalisation
class Shape:
    """Merged view of one schema position (all $ref/allOf/oneOf/anyOf/then fragments folded together)."""

    def __init__(self):
        self.types: set[str] = set()
        self.props: dict[str, list[tuple[dict, Path]]] = {}
        self.required: set[str] = set()
        self.cond_required: list[str] = []      # human-readable conditional requirements
        self.items: list[tuple[dict, Path]] = []
        self.enum: list | None = None
        self.descriptions: list[str] = []
        self.facets: list[str] = []
        self.alternatives: list[str] = []
        self.min_items = 0
        self.nullable = False


def _fmt(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def fold(node: dict, doc: Path, res: Resolver, sh: Shape, where: str, conditional: bool = False) -> Shape:
    if not isinstance(node, dict):
        raise SchemaError(f"{where}: schema node is not an object: {node!r}")
    unknown = set(node) - ANNOTATION - STRUCTURAL
    if where.count(".") == 0:
        unknown -= {"version"}  # GRZ schema carries its own version as a root annotation
    if unknown:
        raise SchemaError(f"{where}: unsupported JSON-Schema keyword(s) {sorted(unknown)}")
    if "$ref" in node:
        target, tdoc = res.resolve(node["$ref"], doc)
        fold(target, tdoc, res, sh, where, conditional)
    t = node.get("type")
    if t is not None:
        if not isinstance(t, str):
            raise SchemaError(f"{where}: type lists are not supported ({t!r})")
        if t not in PRIMITIVE and t not in ("object", "array"):
            raise SchemaError(f"{where}: unsupported type {t!r}")
        sh.types.add(t)
    if node.get("description") and node["description"] not in sh.descriptions:
        sh.descriptions.append(node["description"].strip())
    for k in ("format", "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength",
              "maxLength", "maxItems", "default"):
        if k in node:
            f = f"{k}={_fmt(node[k])}"
            if f not in sh.facets:
                sh.facets.append(f)
    if node.get("nullable"):
        sh.nullable = True
    if "minItems" in node and not conditional:
        sh.min_items = max(sh.min_items, int(node["minItems"]))
    if "enum" in node:
        if not isinstance(node["enum"], list) or not node["enum"]:
            raise SchemaError(f"{where}: malformed enum")
        if any(not isinstance(v, (str, int, float, bool)) for v in node["enum"]):
            raise SchemaError(f"{where}: enum with non-primitive values")
        sh.enum = list(node["enum"]) if sh.enum is None else [v for v in sh.enum if v in node["enum"]]
    for name, sub in (node.get("properties") or {}).items():
        if not NAME_RE.match(name):
            raise SchemaError(f"{where}.{name}: property name is not a valid FHIR element name")
        sh.props.setdefault(name, []).append((sub, doc))
    if "properties" in node and not isinstance(node["properties"], dict):
        raise SchemaError(f"{where}: properties must be an object")
    if "required" in node:
        if conditional:
            sh.cond_required.append(f"requires {', '.join(node['required'])}")
        else:
            sh.required.update(node["required"])
    if "items" in node:
        if not isinstance(node["items"], dict):
            raise SchemaError(f"{where}: tuple-style items are not supported")
        sh.items.append((node["items"], doc))
    for sub in node.get("allOf", []):
        fold(sub, doc, res, sh, where, conditional)
    for kw in ("oneOf", "anyOf"):
        if kw in node:
            alts = []
            for i, sub in enumerate(node[kw]):
                before = len(sh.cond_required)
                fold(sub, doc, res, sh, f"{where}<{kw}[{i}]>", True)
                reqs = sh.cond_required[before:]
                del sh.cond_required[before:]
                alts.append(" and ".join(reqs) if reqs else (sub.get("$ref") or sub.get("title") or _fmt(sub)[:80]))
            sh.alternatives.append(f"{kw}: " + " | ".join(f"({a})" for a in alts))
    if "if" in node:
        if "then" not in node and "else" not in node:
            raise SchemaError(f"{where}: 'if' without then/else")
        cond = _fmt(node["if"])
        for kw in ("then", "else"):
            if kw in node:
                before = len(sh.cond_required)
                fold(node[kw], doc, res, sh, f"{where}<{kw}>", True)
                reqs = sh.cond_required[before:]
                del sh.cond_required[before:]
                sh.alternatives.append(f"{'if' if kw == 'then' else 'unless'} {cond}: {'; '.join(reqs) or 'see schema'}")
    elif "then" in node or "else" in node:
        raise SchemaError(f"{where}: then/else without if")
    return sh


def shape_of(fragments: list[tuple[dict, Path]], res: Resolver, where: str) -> Shape:
    sh = Shape()
    for node, doc in fragments:
        fold(node, doc, res, sh, where)
    return sh


def kind_of(sh: Shape, where: str) -> str:
    types = set(sh.types)
    if not types:  # untyped: infer from structure
        if sh.props:
            types = {"object"}
        elif sh.items:
            types = {"array"}
        elif sh.enum is not None and all(isinstance(v, str) for v in sh.enum):
            types = {"string"}
    if len(types) != 1:
        raise SchemaError(f"{where}: cannot determine a single type (types={sorted(types)})")
    t = types.pop()
    if t != "object" and sh.props:
        raise SchemaError(f"{where}: properties on non-object type {t!r}")
    if t != "array" and sh.items:
        raise SchemaError(f"{where}: items on non-array type {t!r}")
    return t


# ------------------------------------------------------------------------------------------------------- extras
EXTRA_NOTE = "legacy/non-schema property accepted by genomde2fhir"

# The embedded MII Broad Consent (researchConsents[].scope; the schema declares an object without properties):
# the FHIR R4 Consent elements that the migration in genomde2fhir builders/research_consent.py reads, as
# (path below scope, type code, max). Leaves use FHIR datatypes, so matchbox parses them like the Consent itself and
# FML can copy them whole. A type 'Resource' (or 'Consent') for scope itself parses a Consent too, but fails the
# whole $transform with 'Unable to find resourceType property' (HTTP 500) on the schema-valid `scope: {}` of every
# GRZ corpus file, so the elements are declared one by one. `contained` is declared as Resource: the migration keeps
# the contained resources the carried-over elements reference ('#id'); an item without resourceType (invalid FHIR)
# fails the $transform. Not declared (the migration discards it): text.
CONSENT_TOP = [
    ("resourceType", "string", "1"), ("id", "string", "1"), ("meta", "Meta", "1"), ("implicitRules", "string", "1"),
    ("language", "string", "1"), ("extension", "Extension", "*"), ("modifierExtension", "Extension", "*"),
    ("identifier", "Identifier", "*"), ("status", "string", "1"), ("scope", "CodeableConcept", "1"),
    ("category", "CodeableConcept", "*"), ("patient", "Reference", "1"), ("dateTime", "string", "1"),
    ("performer", "Reference", "*"), ("organization", "Reference", "*"), ("sourceAttachment", "Attachment", "1"),
    ("sourceReference", "Reference", "1"), ("policy", "BackboneElement", "*"), ("policy.authority", "string", "1"),
    ("policy.uri", "string", "1"), ("policyRule", "CodeableConcept", "1"), ("verification", "BackboneElement", "*"),
    ("verification.verified", "boolean", "1"), ("verification.verifiedWith", "Reference", "1"),
    ("verification.verificationDate", "string", "1"), ("contained", "Resource", "*"),
]
CONSENT_PROVISION = [
    ("type", "string", "1"), ("period", "Period", "1"), ("actor", "BackboneElement", "*"),
    ("actor.role", "CodeableConcept", "1"), ("actor.reference", "Reference", "1"), ("action", "CodeableConcept", "*"),
    ("securityLabel", "Coding", "*"), ("purpose", "Coding", "*"), ("class", "Coding", "*"),
    ("code", "CodeableConcept", "*"), ("dataPeriod", "Period", "1"), ("data", "BackboneElement", "*"),
    ("data.meaning", "string", "1"), ("data.reference", "Reference", "1"),
]
# Consent.provision is recursive; the logical model declares a fixed depth (deliberate simplification: the MII Broad
# Consent uses 2 levels, deeper levels stay invisible to FML).
CONSENT_PROVISION_DEPTH = 3
CONSENT_DISCARDED = {"id", "meta", "implicitRules", "patient"}   # read only to be replaced or dropped


def consent_elements() -> list[tuple[str, str, str]]:
    out = list(CONSENT_TOP)
    prefix = "provision"
    for level in range(CONSENT_PROVISION_DEPTH):
        out.append((prefix, "BackboneElement", "1" if level == 0 else "*"))
        out += [(f"{prefix}.{rel}", t, mx) for rel, t, mx in CONSENT_PROVISION]
        prefix += ".provision"
    return out


# THE list of extras: (model, element path below the root, kind, max, note). kind is
#   a type code       one element of that type;
#   'like:<path>'     a copy of the generated element tree at <path> (legacy key of a renamed schema key);
#   'Consent'         consent_elements() below an existing schema element (the embedded MII Broad Consent).
SCOPE_NOTE = "embedded MII Broad Consent (FHIR R4 Consent), migrated by research_consent.py"
GENE_DISPLAY_NOTE = "HGNC display of a gene (synthetic corpus; schema: code only), read by rd/variants.py"
EXTRAS = [
    ("DatenkranzOncology", "metaData.researchConsents.scope", "Consent", None, SCOPE_NOTE),
    ("DatenkranzOncology", "case.diagnosisOd.germlineDiagnoses.date", "string", "1",
     "date of a germline diagnosis (synthetic corpus; the schema items are Codings): Feststellungsdatum and "
     "recordedDate in onco/diagnosis.py"),
    ("DatenkranzOncology", "case.priorDiagnostic", "like:case.priorDiagnostics", "1",
     "pre-KDK-1.6.5 single-object key; onco/prior_diagnostics.py treats it as one more priorDiagnostics[] entry"),
    ("DatenkranzRareDisease", "metaData.researchConsents.scope", "Consent", None, SCOPE_NOTE),
    ("DatenkranzRareDisease", "case.priorRd", "like:case.priorRds", "*",
     "pre-KDK-1.6.5 key of priorRds (an object, or an array), read as priorRds[] by rd/prior.py"),
    ("DatenkranzRareDisease", "molecular.smallVariants.genes.display", "string", "1", GENE_DISPLAY_NOTE),
    ("DatenkranzRareDisease", "molecular.copyNumberVariants.genes.display", "string", "1", GENE_DISPLAY_NOTE),
    ("DatenkranzRareDisease", "molecular.structuralVariants.genes.display", "string", "1", GENE_DISPLAY_NOTE),
    ("DatenkranzRareDisease", "plan.recommendedTherapies.variantReferences", "like:plan.recommendedTherapies.variants",
     "*", "pre-KDK-1.6.5 key of variants, read as variants[] by rd/careplan.py"),
    ("DatenkranzRareDisease", "plan.recommendedStudies.variantReferences", "like:plan.recommendedStudies.variants",
     "*", "pre-KDK-1.6.5 key of variants, read as variants[] by rd/careplan.py"),
    ("DatenkranzGrz", "donors.researchConsents.scope", "Consent", None, SCOPE_NOTE),
]


def _extra_el(path: str, code: str, mx: str, definition: str) -> dict:
    return {"id": path, "path": path, "short": "EXTRA: " + definition.split(". ")[0][:110],
            "definition": f"EXTRA ({EXTRA_NOTE}): {definition}", "min": 0, "max": mx, "type": [{"code": code}]}


def _insert_subtree(els: list[dict], parent: str, new: list[dict]):
    """Insert `new` as the last children of `parent` (after its whole subtree), keeping the tree order."""
    idx = [e["path"] for e in els].index(parent)
    end = idx + 1
    while end < len(els) and els[end]["path"].startswith(parent + "."):
        end += 1
    els[end:end] = new


def add_extras(name: str, els: list[dict]) -> list[dict]:
    paths = {e["path"] for e in els}
    for model, rel, kind, mx, note in EXTRAS:
        if model != name:
            continue
        path = f"{name}.{rel}"
        if kind == "Consent":
            if path not in paths:
                raise SchemaError(f"extra {path}: the embedded Consent needs the schema element")
            scope = next(e for e in els if e["path"] == path)
            if any(p.startswith(path + ".") for p in paths):
                raise SchemaError(f"extra {path}: the schema already declares children")
            scope["definition"] = scope["definition"].split(" OPAQUE: ")[0] + (
                f" The schema declares this object without properties; its content, the {note}, is declared below as "
                f"EXTRA elements ({EXTRA_NOTE}).")
            new = []
            for sub, code, smx in consent_elements():
                why = ("read only to be replaced or dropped by the migration" if sub in CONSENT_DISCARDED
                       else "carried over or used by the migration")
                new.append(_extra_el(f"{path}.{sub}", code, smx, f"Consent.{sub} of the {note}; {why}."))
            _insert_subtree(els, path, new)
        else:
            parent = path.rsplit(".", 1)[0]
            if path in paths or parent not in paths:
                raise SchemaError(f"extra {path}: already declared, or parent {parent} missing")
            if kind.startswith("like:"):
                like = f"{name}.{kind[5:]}"
                tree = [e for e in els if e["path"] == like or e["path"].startswith(like + ".")]
                if not tree:
                    raise SchemaError(f"extra {path}: {like} not in the model")
                new = []
                for e in tree:
                    p2 = path + e["path"][len(like):]
                    d = (f"{note}; same structure as {kind[5:]}." if e["path"] == like else
                         f"as {e['path'][len(name) + 1:]} (under the legacy key {rel}): {e['definition']}")
                    n = _extra_el(p2, e["type"][0]["code"], mx if e["path"] == like else e["max"], d)
                    n["min"] = 0 if e["path"] == like else e["min"]
                    new.append(n)
            else:
                new = [_extra_el(path, kind, mx, note + ".")]
            _insert_subtree(els, parent, new)
        paths = {e["path"] for e in els}
    return els


def extra_paths(name: str, sd: dict) -> set[str]:
    """Element paths of the model that are declared extras (EXTRA marker in the definition)."""
    return {e["path"] for e in sd["differential"]["element"]
            if e.get("definition", "").startswith(f"EXTRA ({EXTRA_NOTE})")}


# ------------------------------------------------------------------------------------------- element emission
def definition(sh: Shape, extra: list[str] = ()) -> str:
    parts = [" ".join(sh.descriptions) or "(no description in the BfArM schema)"]
    if sh.enum is not None:
        parts.append("Allowed values: " + ", ".join(_fmt(v) if not isinstance(v, str) else f"'{v}'" for v in sh.enum)
                     + ".")
    if sh.facets:
        parts.append("Schema facets: " + "; ".join(sh.facets) + ".")
    if sh.nullable:
        parts.append("May be null (nullable).")
    if sh.alternatives:
        parts.append("Schema alternatives/conditions: " + " ; ".join(sh.alternatives) + ".")
    parts.extend(extra)
    return " ".join(parts)


def short(sh: Shape) -> str | None:
    d = " ".join(sh.descriptions)
    if not d:
        return None
    d = d.split(". ")[0].strip()
    return d if len(d) <= 120 else d[:117] + "..."


def emit(path: str, sh: Shape, res: Resolver, required: bool, out: list[dict]):
    t = kind_of(sh, path)
    is_array = t == "array"
    if is_array:
        if len(sh.items) == 0:
            raise SchemaError(f"{path}: array without items")
        item = shape_of(sh.items, res, path + "[]")
        item.descriptions = sh.descriptions + [d for d in item.descriptions if d not in sh.descriptions]
        item.facets = sh.facets + item.facets
        item.alternatives = sh.alternatives + item.alternatives
        item.nullable = item.nullable or sh.nullable
        mn = 1 if required and sh.min_items >= 1 else 0
        eff, t = item, kind_of(item, path + "[]")
        if t == "array":
            raise SchemaError(f"{path}: nested arrays are not supported")
        if sh.min_items:
            eff.facets = eff.facets + [f"minItems={sh.min_items}"]
    else:
        mn, eff = (1 if required else 0), sh
    el = {"id": path, "path": path}
    s = short(eff)
    if s:
        el["short"] = s
    extra = []
    if t == "object" and not eff.props:
        extra.append("OPAQUE: the schema declares this object without properties (an embedded JSON/FHIR object, "
                     "e.g. the MII Consent resource of researchConsents[].scope); it is modelled as an empty "
                     "BackboneElement - FML cannot navigate into it, the Python converter reads it as raw JSON.")
    if eff.cond_required:
        extra.append("Conditionally: " + "; ".join(eff.cond_required) + ".")
    el["definition"] = definition(eff, extra)
    el["min"] = mn
    el["max"] = "*" if is_array else "1"
    el["type"] = [{"code": "BackboneElement" if t == "object" else PRIMITIVE[t]}]
    out.append(el)
    if t == "object":
        for name, frags in eff.props.items():
            emit(f"{path}.{name}", shape_of(frags, res, f"{path}.{name}"), res, name in eff.required, out)


def build(name: str, spec: tuple[Path, str, str] | None = None) -> dict:
    """Logical model `name` from MODELS[name] or from spec = (schema file, title, source description)."""
    schema_path, title, source = spec or MODELS[name]
    res = Resolver()
    root_schema = res.load(schema_path)
    root = shape_of([(root_schema, schema_path.resolve())], res, name)
    if kind_of(root, name) != "object":
        raise SchemaError(f"{name}: schema root is not an object")
    url = BASE + name
    schema_ver = root_schema.get("version")
    desc = (f"Logical model of the {source}, generated by scripts/schema_to_logical.py; the source type of the "
            f"genomDE FML StructureMaps. Element names are the JSON property names, so a raw Datenkranz JSON "
            f"instance parses against it unchanged. Dates are kept as strings (copied verbatim), enumerations "
            f"are strings whose allowed values are listed in each element definition."
            + (f" Schema version {schema_ver}." if schema_ver else ""))
    els = [{"id": name, "path": name, "short": title, "definition": desc, "min": 1, "max": "1"}]
    for pname, frags in root.props.items():
        emit(f"{name}.{pname}", shape_of(frags, res, f"{name}.{pname}"), res, pname in root.required, els)
    if spec is None:
        add_extras(name, els)
    return {
        "resourceType": "StructureDefinition",
        "id": name,
        "url": url,
        "version": VERSION,
        "name": name,
        "title": title,
        "status": "draft",
        "experimental": False,
        "publisher": "KohlbacherLab (genomDE2FHIR)",
        "description": desc,
        "fhirVersion": "4.0.1",
        "kind": "logical",
        "abstract": False,
        "type": url,
        "baseDefinition": "http://hl7.org/fhir/StructureDefinition/Base",
        "derivation": "specialization",
        "differential": {"element": els},
    }


# ------------------------------------------------------------------------------------------- independent check
def schema_paths(name: str, schema_path: Path | None = None) -> dict[str, str]:
    """Walk the schema naively (no Shape merging) and return {property path: json type or ''}."""
    schema_path = schema_path or MODELS[name][0]
    res = Resolver()
    found: dict[str, set[str]] = {}

    def walk(node, doc, path, depth=0):
        if depth > 60:
            raise SchemaError(f"{path}: recursion too deep (cyclic $ref?)")
        if "$ref" in node:
            t, d = res.resolve(node["$ref"], doc)
            walk(t, d, path, depth + 1)
        if isinstance(node.get("type"), str):
            found.setdefault(path, set()).add(node["type"])
        for k in ("allOf", "oneOf", "anyOf"):
            for sub in node.get(k, []):
                walk(sub, doc, path, depth + 1)
        for k in ("then", "else"):
            if k in node:
                walk(node[k], doc, path, depth + 1)
        if "items" in node:
            walk(node["items"], doc, path, depth + 1)
        for pn, sub in (node.get("properties") or {}).items():
            found.setdefault(f"{path}.{pn}", set())
            walk(sub, doc, f"{path}.{pn}", depth + 1)

    walk(res.load(schema_path), schema_path.resolve(), name)
    return {p: "/".join(sorted(t - {"array"})) for p, t in found.items() if p != name}


COMPAT = {"string": "string", "integer": "integer", "number": "decimal", "boolean": "boolean", "object": "BackboneElement"}


def check_model(name: str, sd: dict, schema_path: Path | None = None) -> list[str]:
    els = {e["path"]: e for e in sd["differential"]["element"]}
    problems = []
    sp = schema_paths(name, schema_path)
    extras = extra_paths(name, sd)
    for p in els:
        if p != name and p not in sp and p not in extras:
            problems.append(f"element {p} has no schema property")
    for p in extras & set(sp):
        problems.append(f"extra {p} is a schema property")
    for p, jt in sp.items():
        e = els.get(p)
        if e is None:
            problems.append(f"missing element {p}")
            continue
        code = e["type"][0]["code"]
        if jt and COMPAT.get(jt) != code:
            problems.append(f"type mismatch {p}: schema {jt} vs model {code}")
    ids = [e["id"] for e in sd["differential"]["element"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate element ids")
    for e in sd["differential"]["element"][1:]:
        parent = e["path"].rsplit(".", 1)[0]
        if parent not in els or (parent != name and els[parent]["type"][0]["code"] != "BackboneElement"):
            problems.append(f"orphan element {e['path']}")
    return problems


FHIR_COMPLEX = {"Meta", "Extension", "Identifier", "CodeableConcept", "Coding", "Reference", "Period", "Attachment"}


def instance_problems(sd: dict, instance) -> list[str]:
    """Every key path of a JSON instance must exist in the model with a compatible primitive type."""
    els = {e["path"]: e for e in sd["differential"]["element"]}
    out = []

    def walk(v, path):
        e = els.get(path)
        if e is None:
            out.append(f"no element for {path}")
            return
        code = e.get("type", [{"code": "BackboneElement"}])[0]["code"] if path != sd["name"] else "BackboneElement"
        vals = v if isinstance(v, list) else [v]
        if isinstance(v, list) and e["max"] != "*":
            out.append(f"array value for single element {path}")
        for x in vals:
            if x is None:
                continue
            if isinstance(x, dict):
                if code in FHIR_COMPLEX:
                    continue                      # a FHIR datatype (extras): matchbox parses it with its own definition
                if code != "BackboneElement":
                    out.append(f"object value for {code} element {path}")
                elif any(c["path"].startswith(path + ".") for c in els.values()):
                    for k, sub in x.items():
                        walk(sub, f"{path}.{k}")
            elif isinstance(x, bool):
                if code != "boolean":
                    out.append(f"boolean value for {code} element {path}")
            elif isinstance(x, int):
                if code not in ("integer", "decimal"):
                    out.append(f"integer value for {code} element {path}")
            elif isinstance(x, float):
                if code != "decimal":
                    out.append(f"decimal value for {code} element {path}")
            elif isinstance(x, str):
                if code != "string":
                    out.append(f"string value for {code} element {path}")
            else:
                out.append(f"unsupported value at {path}")

    walk(instance, sd["name"])
    return out


def render(sd: dict) -> str:
    return json.dumps(sd, ensure_ascii=False, indent=1) + "\n"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    rc = 0
    for name in MODELS:
        sd = build(name)
        problems = check_model(name, sd)
        if problems:
            for p in problems:
                print(f"{name}: {p}", file=sys.stderr)
            raise SchemaError(f"{name}: {len(problems)} model check failure(s)")
        target = OUT / f"StructureDefinition-{name}.json"
        text = render(sd)
        n = len(sd["differential"]["element"])
        if check:
            if not target.exists() or target.read_text(encoding="utf-8") != text:
                print(f"stale: {target.relative_to(ROOT)}")
                rc = 1
        else:
            if not target.exists() or target.read_text(encoding="utf-8") != text:
                target.write_text(text, encoding="utf-8")
                print(f"wrote {target.relative_to(ROOT)} ({n} elements)")
            else:
                print(f"unchanged {target.relative_to(ROOT)} ({n} elements)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
