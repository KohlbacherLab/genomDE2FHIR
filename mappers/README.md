# genomDE Datenkranz → MII KDS FHIR — mappers

Two implementations of the FHIR mapping table (`mapping/mapping_kdk_oncology.csv`),
both covering the **high-confidence MAPPED oncology spine** first and structured to
extend group-by-group. The mapping table is authoritative; both mappers implement it.

## (a) Python — `python/genomde_to_fhir.py`
Emits a FHIR R4 **transaction Bundle** from a Datenkranz oncology JSON, using the
`fhir.resources` library (R4B models = R4; construction is validated).

```bash
pip install -r python/requirements.txt
python3 python/genomde_to_fhir.py example-data/oncology/<file>.json -o bundle.json
python3 python/genomde_to_fhir.py --demo            # runs on the first example file
```

Covers: Patient (PatientPseudonymisiert), Coverage, Consent (mvConsent → provisions),
primary Condition (mii-pr-mtb-diagnose-primaertumor: ICD-10-GM + ICD-O-3 morphology
extension + topography bodySite), additional Conditions, ECOG Observation, prior
systemic therapy (Procedure + MedicationStatement), follow-up ECOG + vital status.
Cross-resource refs use `urn:uuid:` (deterministic uuid5). `meta.profile` set per row.

Extend: add a builder per resource group; the `cc()` helper turns a source coding
`{code,system,version,display}` into a CodeableConcept. TODO hooks marked inline for
TNM, grading, MTB molecular variants, biomarkers, care-plan recommendations (these are
the table's DRAFT/open-issue rows).

Validate the output against the MII profiles (needs the packages loaded):
```bash
# HL7 validator
java -jar validator_cli.jar bundle.json -version 4.0 \
  -ig de.medizininformatikinitiative.kerndatensatz.mtb#2026.0.0 \
  -ig de.medizininformatikinitiative.kerndatensatz.person -tx https://tx.fhir.org/r4
# or matchbox $validate (see fhir-validate skill)
```

## (b) FML / StructureMap — `fml/` (for HAPI / Matchbox `$transform`)
Server-side structural mapping: a source **LogicalModel** + a **StructureMap** that a
HAPI/Matchbox server runs to turn Datenkranz JSON into a Bundle.

- `fml/DatenkranzOncology.logical.json` — logical model declaring the source paths
  (required so the engine resolves them — fml-edit-safe **Q6**). Extend `element[]` as
  you extend the map.
- `fml/genomde-oncology-to-mii.map` — the StructureMap (FML). Covers Patient + primary
  Condition as the runnable, **matchbox-trap-safe** pattern (single-step sources via
  sub-groups, no `where !=`, bind-once, no literal-string sources).

Pre-flight + load + transform (Matchbox):
```bash
# 1. trap check (no Java needed)
bash ~/.claude/skills/fml-edit-safe/scripts/check-fml.sh fml/genomde-oncology-to-mii.map
# 2. load the logical model + the map
curl -sS -X POST -H "Content-Type: application/fhir+json" \
  --data-binary @fml/DatenkranzOncology.logical.json  $MATCHBOX/StructureDefinition
curl -sS -X POST -H "Content-Type: text/fhir-mapping" \
  --data-binary @fml/genomde-oncology-to-mii.map       $MATCHBOX/StructureMap
# 3. transform a Datenkranz file (must be tagged with the logical-model profile, or
#    posted as the logical resource) — see Matchbox docs / fhir-validate skill
curl -sS -X POST -H "Content-Type: application/fhir+json" --data-binary @datenkranz.json \
  "$MATCHBOX/StructureMap/\$transform?source=https://www.medizininformatik-initiative.de/fhir/StructureMap/GenomDeOncologyToMii"
```

> Status: the FML passes the fml-edit-safe static checker (PUSH-SAFE) but has **not** been
> round-tripped on a live Matchbox here. Before relying on it, push to Matchbox and confirm
> it returns a `Bundle` (not an `OperationOutcome`), and extend the logical model for any
> new source path (Q6). The prior pipeline's `maps/` (knowledge/genomde-mapping) is a
> reference for the full-coverage FML.

## Scope note
Both mappers do **oncology** first (richest, most MAPPED branch). Rare-disease and GRZ are
added the same way (new entry point / new groups + logical model), and molecular/recommendation
coverage tracks the open issues in `docs/OPEN-ISSUES.md`.
