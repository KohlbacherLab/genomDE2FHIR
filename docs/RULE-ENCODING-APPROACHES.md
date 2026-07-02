# Encoding semantic rules for JSON — approaches & best practice

Context: the genomde-dk-validator uses a **rules-as-data + primitive-catalog** engine (mzPeak-style)
to encode the BfArM QS criteria (cross-field, conditional, temporal). Survey of the alternatives,
and what's best for this project.

## The landscape

| Approach | What it is | Fit for QS-style rules | Standard / library |
|---|---|---|---|
| **JSON Schema conditionals** (`if`/`then`/`else`, `dependentRequired`, `dependentSchemas`) | Conditional presence/type within the schema | Good for "X required when Y present" (e.g. libraryType when sequencing done); weak for arithmetic/date/cross-field comparisons | ✅ standard, `jsonschema`/`Ajv` — no extra code |
| **JSONLogic** | Business rules as portable JSON expression trees, safe eval | Good for boolean/arithmetic/comparison over one object; array "for-all" quantifiers + locating the failing element are awkward; dates need custom ops | de-facto standard; `json-logic-py` (Python), cross-language |
| **FHIRPath invariants** | Constraints as FHIRPath expressions (the language FHIR itself uses; e.g. MII `mii-pat-1`) | Excellent — designed for exactly this (cross-element, conditional, `implies`, collections, severity) | ✅ HL7 standard; engines in Java/Python/JS |
| **Rego / OPA** | Policy-as-code language + runtime | Powerful for cross-field/collection policy | industry standard (heavy for a small lib) |
| **CUE** | Config language unifying schema+constraints+data | Cross-field constraints via unification | Go toolchain |
| **Schematron for JSON (Jsontron)** | Schematron's context/assert/report model ported to JSON | Conceptually closest: per-context assertion + human message | niche, low adoption |
| **SHACL (+SPARQL)** | Shapes constraint language for RDF/JSON-LD | Rich, but needs JSON-LD/RDF framing | W3C standard (semantic-web stack) |
| **Python rule engines** | rules-as-JSON evaluated in Python (`python-rule-engine`, `business-rules`, `py-rules-engine`, `json-rules-engine-simplified`) | Drop-in to what we hand-rolled | various small libs |

## Assessment for this project
- The current engine (data rules + code primitives) is a **recognized pattern** — essentially a small
  domain rule engine, same shape as the Python rule-engine libs and mzPeak. Fine for a controlled,
  well-tested rule set, and it keeps `source` citations + per-finding `file:line:col`.
- **Two standards are the strongest fits:**
  1. **FHIRPath** — best *long-term* fit because the pipeline is FHIR-bound: the MII profile side
     already validates with FHIRPath invariants, and the QS criteria (`date > birthDate`,
     `all dates before molecularBoardDecisionDate`, `gender='other' implies …`) map cleanly to
     FHIRPath. Authoring QS + MII conformance in **one** expression language is the alignment win.
  2. **JSONLogic** — best *portable/tool-agnostic* fit if you want the rule *conditions* to be a
     recognized standard (shareable, UI-editable, safe), keeping thin wrappers for array
     quantification and location reporting (JSONLogic's weak spots).
- **Fold the simple conditional rules into JSON Schema** where possible: `if`/`then` +
  `dependentRequired` are library-backed and need no custom code (e.g. rare→libraryType,
  "genomicDataCenterId required when sequencing performed").

## Recommendation
Keep the primitive engine for now (small, tested, cited). For v1.0+, either (a) migrate rule
*conditions* to **JSONLogic** for portability, or (b) — preferred given the FHIR target — express QS
criteria as **FHIRPath** and evaluate with a FHIRPath engine, unifying Datenkranz-QS with MII-profile
invariants. Push pure presence/type conditionals down into **JSON Schema `if/then`**.

Sources: [JsonLogic](https://jsonlogic.com/) · [json-logic-py](https://github.com/nadirizr/json-logic-py) ·
[FHIR invariants / FHIRPath](https://outburn.health/anatomy-of-fhir-invariants/) ·
[JSON Schema conditionals](https://json-schema.org/understanding-json-schema/reference/conditionals) ·
[Rego/OPA vs CUE vs JSONLogic](https://cuelang.org/docs/howto/use-encoding-json-validate-as-a-field-validator/) ·
[Jsontron (Schematron for JSON)](https://github.com/amer-ali/jsontron) ·
[SHACL for JSON/JSON-LD](https://github.com/mulesoft-labs/json-ld-schema) ·
[Python rule engines](https://github.com/santalvarez/python-rule-engine).
