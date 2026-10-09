# genomDE Datenkranz → MII KDS FHIR — mappers

Two implementations turn a genomDE / MV-GenomSeq Datenkranz JSON file (BfArM KDK oncology, KDK rare disease, GRZ)
into a FHIR R4 **transaction Bundle** for the **MII KDS 2027.0.0 ballot** profiles. The mapping table
(`mapping/*.csv`) is authoritative, and both implementations follow it. Plan: `docs/PLAN-2027.md`.

| | Implementation | Where | Status |
|:--|:--|:--|:--|
| (a) | Python package `genomde2fhir`, the **reference implementation** | `genomde2fhir/` (`builders/**`, `docs/REPRESENTATIONS.md`, `docs/IDENTITY.md`) | all three branches |
| (b) | FML StructureMaps that matchbox runs with `$transform` | `mappers/fml/` (details: [`fml/README.md`](fml/README.md)) | all three branches, parity with (a) |
| | superseded 2026 prototypes | `python/genomde_to_fhir.py` (oncology spine), `fml/legacy/` | kept for reference only |

## (a) Python: `genomde2fhir`

```bash
. genomde2fhir/.venv/bin/activate
genomde2fhir convert submission.json -o out/ [--validate <matchbox> --ingest <hapi>]
```

See `genomde2fhir/README.md`.

## (b) FML: `mappers/fml/`

| Map (`https://genomde.de/fhir/StructureMap/…`) | Role |
|:--|:--|
| `DatenkranzCommon` | shared `Dk*` groups: entry envelope and resource key, datatypes, KDK Patient, Coverage, MV consent, migration of the embedded MII Broad Consent, indication board |
| `DatenkranzOncologyToMii` | oncology main map (imports Common, `OncoMolecular`, `OncoPlanFollowUp`) |
| `OncoMolecular` | oncology molecular block: NGS report, variants, CNV, fusions, biomarkers, expression, signatures |
| `OncoPlanFollowUp` | oncology therapy plan, recommendations, studies, follow-up, `Patient.deceased[x]` |
| `DatenkranzRareDiseaseToMii` | rare-disease main map (imports Common) |
| `DatenkranzGrzToMii` | GRZ main map (imports Common): donors, family history, organisations, lab data, devices, study |

Sources are the logical models `https://genomde.de/fhir/StructureDefinition/Datenkranz{Oncology,RareDisease,Grz}`,
generated from the BfArM schemas by `scripts/schema_to_logical.py`. matchbox drops every input property a model does
not declare, so the models also declare, as marked extras, the non-schema properties the Python converter reads: the
embedded MII Broad Consent under `researchConsents[].scope`, the pre-1.6.5 keys `case.priorDiagnostic`,
`case.priorRd` and `plan.*.variantReferences`, `germlineDiagnoses[].date` and the RD `genes[].display`. They ship in the local package `de.genomde.mvgs`
(`mvgs-ig/`) together with the profiles, CodeSystems and ConceptMaps that the maps use.

Every resource is one entry with a `urn:uuid` fullUrl and a conditional `PUT <Type>?identifier=https://genomde.de/fhir/sid/resource-key|<key>`.
The key is the base64url form of `<stream>:<submitterId>:<caseKey>:<role>`. Loading the same case again therefore
updates the existing resources and creates no new ones. Unlike the Python path, the FML maps emit no Provenance and set
no resource ids. A Python ingest and an FML ingest of the same case into one server give two separate sets of
resources.

### Loading recipe

On the first start of a matchbox, and after every map or package change, load the package resources and the maps.
Imported maps go first, and every map is pushed each time:

```bash
. genomde2fhir/.venv/bin/activate
python scripts/build_mvgs.py --install http://localhost:8091/matchboxv3/fhir --maps
```

Then load one Datenkranz file into HAPI with one command:

```bash
scripts/load_datenkranz.sh <datenkranz.json> [matchbox-base] [hapi-base]
# defaults: http://localhost:8091/matchboxv3/fhir  http://localhost:8092/fhir
# OUT=bundle.json keeps the Bundle; DRY_RUN=1 transforms only and prints the Bundle
```

The script does three things:

1. It picks the main map from the file's branch, using the same rules as `genomde2fhir.io.classify`.
2. It POSTs the raw file to `{matchbox}/StructureMap/$transform?source=<map url>` with `Content-Type: application/fhir+json`.
3. It POSTs the returned transaction Bundle to HAPI and prints the counts of the response statuses, for example
   `48x 201` on the first load and `48x 200` on a repeated load.

It exits 1 if the transform or the transaction fails, and 2 for an input that is not a Datenkranz file. It needs
`curl` and `jq`. Unlike `genomde2fhir convert`, the script does not schema-validate its input. Check files with
`genomde-dk-validator` (or `genomde2fhir convert`) first.

### Tests

These tests are skipped unless `MB2027` is set to the matchbox-2027 base URL. `HAPI2027` defaults to
`http://localhost:8092/fhir`.

- `genomde2fhir/tests/test_fml_integration.py` pushes all production maps. It runs one file per branch and checks:
  - a Bundle comes back;
  - there is no content error that the Python output of the same file does not have;
  - graph-aware parity with the Python converter is exact on the *declared shape* of the file, which is the input
    restricted to what the logical model declares (see `fml/README.md`, "Parity with the Python converter");
  - parity is exact on the raw file;
  - a double ingest into HAPI succeeds, and the second ingest gives only 200 and no new resources.

  Wide run: `MB2027=… python genomde2fhir/tests/test_fml_integration.py --n 20 --ingest 5`, where `--n -1` means the
  whole corpus and `--no-validate` gives a fast run of transform, parity and ingest only.
- Per-stage tests cover more edge cases: `test_fml_common.py`, `test_fml_onco_spine.py`,
  `test_fml_onco_molecular.py`, `test_fml_onco_plan_followup.py`, `test_fml_rd.py` and `test_fml_grz.py`.
- Corpus report: `python scripts/run_corpus.py --sample 20 --fml` writes `docs/E2E-REPORT-2027.md`. Its "FML parity"
  row compares the raw files with its own canonical form (see `fml/README.md`, "Parity with the Python converter").
