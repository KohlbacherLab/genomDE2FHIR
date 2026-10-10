# FML maps: genomDE Datenkranz → MII KDS 2027 (deliverable b)

matchbox runs these StructureMaps (`$transform`) on a raw genomDE / MV-GenomSeq Datenkranz JSON file and returns a
FHIR R4 **transaction Bundle** for HAPI. The targets are the MII KDS 2027.0.0 ballot profiles. The reference
implementation is the Python converter (`genomde2fhir/src/genomde2fhir/builders/**`, `docs/REPRESENTATIONS.md`,
`docs/IDENTITY.md`). The maps emit the same resources, profiles, codings and links. Plan:
`docs/PLAN-2027.md` §4 and §6.

Everything under "Engine behaviour" was checked on **matchbox 4.1.21** (hapi-fhir 8.12.1, org.hl7.fhir.core 6.10.4)
and HAPI 8.4.0. Each behaviour has a probe map in `test/`.

## Files

| File | Canonical (`https://genomde.de/fhir/StructureMap/…`) | Role |
|:--|:--|:--|
| `DatenkranzCommon.map` | `DatenkranzCommon` | shared groups (`Dk*`): envelope, datatypes, references, KDK Patient, Coverage, MV consent, Broad Consent migration, indication board |
| `DatenkranzOncologyToMii.map` | `DatenkranzOncologyToMii` | oncology main map; imports Common, OncoMolecular, OncoPlanFollowUp |
| `OncoMolecular.map` | `OncoMolecular` | oncology molecular block (sub-map) |
| `OncoPlanFollowUp.map` | `OncoPlanFollowUp` | oncology plan and follow-up (sub-map) |
| `DatenkranzRareDiseaseToMii.map` | `DatenkranzRareDiseaseToMii` | rare-disease main map |
| `DatenkranzGrzToMii.map` | `DatenkranzGrzToMii` | GRZ main map |
| `test/*.map` | `Engine*`, `Common*`, `Datenkranz*Probe` | engine probes and Common probes (not production) |
| `test/expect-fail/*.map` | | probes that matchbox rejects at upload (Q2, Q5); not pushed by the loader |
| `legacy/` | | the superseded 2026 map and its hand-written logical model |

Source types are the generated logical models in `de.genomde.mvgs` (`mvgs-ig/input/StructureDefinition-Datenkranz{Oncology,RareDisease,Grz}.json`,
canonical `https://genomde.de/fhir/StructureDefinition/Datenkranz…`). Element paths are the JSON property names.
Besides the schema properties, the models declare the non-schema properties that the Python converter reads, as
marked extras ("EXTRA (legacy/non-schema property accepted by genomde2fhir)" in the definition; one list,
`EXTRAS` in `scripts/schema_to_logical.py`):

| Extra | Model | Declared as |
|:--|:--|:--|
| `metaData.researchConsents[].scope.*`, `donors[].researchConsents[].scope.*` | all three | the FHIR R4 Consent elements of the embedded MII Broad Consent (leaves are FHIR datatypes: `CodeableConcept`, `Reference`, `Extension`, `Period`, …; `provision` to depth 3; `contained` as `Resource`; `text` is not declared) |
| `case.priorDiagnostic` | oncology | a copy of the `priorDiagnostics` item, max 1 (pre-KDK-1.6.5 single object) |
| `case.diagnosisOd.germlineDiagnoses[].date` | oncology | string |
| `case.priorRd` | rare disease | a copy of the `priorRds` item, max `*` (an object or an array) |
| `plan.recommended{Therapies,Studies}[].variantReferences` | rare disease | as `variants` (string, max `*`) |
| `molecular.{smallVariants,copyNumberVariants,structuralVariants}[].genes[].display` | rare disease | string |

Header syntax:

```fml
/// url = 'https://genomde.de/fhir/StructureMap/DatenkranzOncologyToMii'
/// name = 'DatenkranzOncologyToMii'
/// title = 'genomDE oncology Datenkranz to MII KDS 2027'     // no single quotes inside the title
/// status = 'draft'

uses "https://genomde.de/fhir/StructureDefinition/DatenkranzOncology" alias Datenkranz as source
uses "http://hl7.org/fhir/StructureDefinition/Bundle" alias Bundle as target

imports "https://genomde.de/fhir/StructureMap/DatenkranzCommon"

group main(source src : Datenkranz, target bundle : Bundle) { ... }
```

## Loading and running

```bash
. genomde2fhir/.venv/bin/activate
python scripts/build_mvgs.py --install http://localhost:8091/matchboxv3/fhir --only none --maps   # maps only
python scripts/build_mvgs.py --install http://localhost:8091/matchboxv3/fhir --maps               # package resources + maps
python scripts/build_mvgs.py --install http://localhost:8091/matchboxv3/fhir --only none --maps --test-maps   # + probes
python scripts/schema_to_logical.py && \
python scripts/build_mvgs.py --install http://localhost:8091/matchboxv3/fhir --only StructureDefinition --maps   # logical models changed
```

`--maps` POSTs `mappers/fml/*.map` (and `test/*.map` with `--test-maps`) as `Content-Type: text/fhir-mapping`. Imported
maps are pushed first (a topological order over the `imports` lines, so DatenkranzCommon comes first). Every run
pushes all maps, because an importing map binds its imports when it is loaded (see below). Re-running is idempotent.
After a change of the logical models (`scripts/schema_to_logical.py`, including its `EXTRAS`) push the
StructureDefinitions and then all maps again.

Transform (wire contract, PLAN §6):

```bash
curl -X POST -H 'Content-Type: application/fhir+json' -H 'Accept: application/fhir+json' \
  --data-binary @case.json \
  'http://localhost:8091/matchboxv3/fhir/StructureMap/$transform?source=https://genomde.de/fhir/StructureMap/DatenkranzOncologyToMii'
```

The response is the Bundle (HTTP 200), or an OperationOutcome (HTTP 500 for engine errors, 422 for an unknown map).
POST the Bundle to HAPI (`POST http://localhost:8092/fhir`).

One command does both steps for one file. It picks the map from the file's branch, transforms the file and POSTs the
Bundle to HAPI:

```bash
scripts/load_datenkranz.sh <datenkranz.json> [matchbox-base] [hapi-base]   # OUT=<file> keeps the Bundle, DRY_RUN=1 skips HAPI
```

## Conventions (binding for all maps)

### Bundle and entries

- `Bundle.type = 'transaction'`. Each resource is exactly one entry.
- Entry envelope: `fullUrl = 'urn:uuid:' + uuid()`. Keep the uuid in a variable and build intra-bundle references
  as `'urn:uuid:' + <uuid>`. `request = PUT <Type>?identifier=https://genomde.de/fhir/sid/resource-key|<k>`. The
  resource carries the identifier `{system: https://genomde.de/fhir/sid/resource-key, value: <k>}`. No
  `resource.id` is set: HAPI resolves the conditional update and rewrites the urn:uuid references.
- Use `DkEntry` for this. Do not write the envelope by hand.
- **Resource key**: `k = encode('urlbase64')` of `<ck>:<role>`.
  - `ck` (case key) is `kdk:<submitterId>:<CK>` or `grz:<submitterId>:<CK>`. `CK` is the string Python uses as
    `CaseKey.case_id`: the localCaseId (else tanC / tanG) escaped (`\` -> `\\`, `|` -> `\|`), plus `|test` for a test
    submission (KDK `metaData.submission.type`, GRZ `submission.submissionType` = `test`), so a test submission never
    meets the real case. This mirrors `docs/IDENTITY.md` (stream | submitterId | caseKey). The stream prefix keeps the
    KDK Patient and the GRZ index-donor Patient apart: both are keyed by the same submitterId and localCaseId.
  - `DkEntry` labels every resource of a test submission (a `ck` ending in an unescaped `|test`) with
    `meta.security` v3-ActReason `HTEST` ("test health data").
  - On a Patient the resource-key identifier carries `type` v2-0203 `RI` ("Resource identifier"): `Consent.patient`
    of `mii-pr-consent-einwilligung` targets the ConsentManagement Patient, which requires `identifier.type` on every
    identifier (otherwise a content error the Python Patient does not have).
  - `role` is the semantic role, for example `patient`, `coverage`, `mv-consent` or `indication-board`. Where the
    schema has a local id, append it as `role:<local id>` (for example `variant:<id>` or `donor:<donorPseudonym>`).
    Otherwise append the array index (`followup:<i>:ecog`). The role is unique per resource type within a case.
  - The key is base64url-encoded for both the identifier value and the URL, because local ids may contain URL-unsafe
    characters. HAPI rejects a space or `&` (HAPI-1744). It decodes `%`, so the stored value no longer matches the URL
    (HAPI-0929). To read a key, base64url-decode it.
- Case key expressions (put them in `main` and pass `ck` down as a source parameter):

  ```fml
  // KDK (oncology, rare disease)
  src.metaData as md -> ('kdk:' & %md.submission.submitterId & ':' &
        iif(%md.localCaseId.exists() and %md.localCaseId != '', %md.localCaseId, %md.tanC).replace('\\', '\\\\').replace('|', '\\|')
        & iif(%md.submission.type = 'test', '|test', '')) as ck, uuid() as pid
     then Case(src, md, ck, pid, bundle) "metaData";
  // GRZ
  src.submission as sub -> ('grz:' & %sub.submitterId & ':' &
        iif(%sub.localCaseId.exists() and %sub.localCaseId != '', %sub.localCaseId, %sub.tanG).replace('\\', '\\\\').replace('|', '\\|')
        & iif(%sub.submissionType = 'test', '|test', '')) as ck
     then Grz(src, sub, ck, bundle) "submission";
  ```

  Identifier values use the same escaping on every component and `CK` as is: `local-case-id` `<submitterId>|<CK>`,
  `molecular-finding-id` / `kdk-object-id` `<submitterId>|<CK>|<esc(id)>`, GRZ `donor-pseudonym`
  `<submitterId>|<CK>|<esc(pseudonym)>` (case-scoped), `grz-lab-data-name` `<submitterId>|<CK>|<esc(pseudonym)>|<esc(labDataName,
  else #i)>`, `grz-sample-barcode` `<esc(submitterId)>|<esc(barcode)>` (+ `|test`). `esc(x)` =
  `x.replace('\\', '\\\\').replace('|', '\\|')` (FHIRPath `replace` is literal).

  Use `&`, not `+`. `+` with one empty operand makes the whole string empty.
- Patient: KDK maps call `DkKdkPatient(md, ck, pid, bundle)`, where `pid` is the Patient's entry uuid. Hand `pid` to
  every group that references the Patient (`-> res.subject as s then DkReference(pid, s)`). If a branch must add
  elements to the Patient, such as `deceasedDateTime` from the follow-up (`onco/followup.py`, `rd` follow-up), build
  the entry itself and add its own group:

  ```fml
  md -> bundle.entry as e, e.resource = create('Patient') as pat, ('patient') as role
     then DkEntry(ck, role, pid, e, pat), DkKdkPatientBody(md, pat), MyPatientFollowUp(src, pat) "patient";
  ```

  Target variables are not visible to later rules (Q4), so everything that writes to one resource must run inside
  the rule that created it, or in groups called from that rule. The Patient keeps its natural identifiers (tan-c,
  local-case-id, and on GRZ donor-pseudonym / tan-g) next to the resource key.
- No Provenance is emitted by the FML maps (the Python converter's Provenance is excluded from parity), but every
  resource carries `meta.source = urn:genomde2fhir:submission:<submitterId>:<caseId>:<date>:<type>`
  (`identity.CaseKey.source`; caseId = the raw localCaseId, else tanC / tanG; a test submission differs by its type
  `test`). Each component is percent-encoded like `identity.source_component`: printable ASCII 0x21-0x7E stays except
  `%` `:` `|` `#` `?` `/`, every other UTF-8 byte becomes `%XX` (upper case). FHIRPath recipe per component `x`:
  `x.encode('hex').upper().replaceMatches('(..)', '$1 ').trim().split(' ').select(iif($this.matches('^(2[1246-9A-E]|3[0-9B-E]|[4-6][0-9A-F]|7[0-9ABDE])$'), $this.decode('hex'), '%' & $this)).join('')`
  (byte pairs of the UTF-8 hex string; a kept pair is decoded back; also correct for characters outside the BMP).
  `main` computes it next to `ck` and attaches it to the `ck` string as an extension
  (`urn:genomde2fhir:meta-source`), so `DkEntry` writes it without a further group parameter and without changing any
  resource key; a `ck` read back from the oncology `ctx` Parameters gets it re-attached from `ctx` `metaSource`. The
  stale resources of a case after a correction are found by `meta.source` plus the resource-key identifier
  (`docs/IDENTITY.md`).

### Profiles, codes, terminology

- `meta.profile` holds exactly the canonicals the Python builders use, unversioned:
  `res.meta as m, m.profile = '<canonical>'`. Local MV-GenomSeq profiles are `https://genomde.de/fhir/StructureDefinition/mvgs-*`.
- ConceptMaps of `de.genomde.mvgs` (`mvgs-ig/input/ConceptMap-mvgs-cm-*.json`):
  - `translate(v, 'https://genomde.de/fhir/ConceptMap/<id>', 'coding')` returns system, code and display of the
    target.
  - `'code'` returns the code only, so set the system yourself.
  - An unmapped code yields nothing, so no element is written. This is how catch-all values are dropped.
- Local CodeSystems with no ConceptMap (for example consent domains, administrative codes or rejection reasons):
  - Write the codes with the display copied from the CodeSystem.
  - Guard them with `where (x = 'a' or x = 'b' ...)`, so an unknown value fires no rule. This matches the Python
    `local_coding()`, which returns None.
- Write codings element by element: `cc.coding as c, c.system = '…', c.code = '…', c.display = '…'`. Do **not** use
  `c(system, code, display)`, because it ignores the display argument.
- Never invent values. A catch-all value (`other`, `unknown`, an unmapped code) is handled exactly as in the Python
  builder. Most often no rule fires and the value is dropped.

### Names and parameters

- Group names are unique across all maps. Common uses `Dk*`. Use a prefix per map (`Onco*`, `OncoMol*`,
  `OncoPlan*`, `Rd*`, `Grz*`). A local group silently shadows an imported group of the same name.
- Group arguments are always variables (Q3). Bind literals first: `('patient') as role`. Do not write
  `'patient' as role`, which is parsed as a target context.
- A main map imports every map whose groups it calls *directly*. Imports are not transitive for direct calls.

## DatenkranzCommon groups

| Group | Parameters | Python counterpart |
|:--|:--|:--|
| `DkEntry` | `ck, role, fid, e, res` | `BundleBuilder.put` + resource-key identifier + conditional PUT |
| `DkReference` | `fid, ref : Reference` | `bundle.ref` (`urn:uuid:` reference) |
| `DkCoding` / `DkCodingSystem` | `src[, sys], c : Coding` | `common.src_coding` (with a system override the source version is dropped) |
| `DkCodeableConcept` / `DkCodeableConceptSystem` | `src[, sys], cc` | `common.src_cc` (no code → nothing, text only with a code) |
| `DkCodeCoding` | `code, sys, c` | `common.coding(system, code)` |
| `DkIdentifier` | `sys, val, id` | `common.identifier(system, value)` |
| `DkPeriod` / `DkPeriodStart` / `DkPeriodEnd` | `start, end, p` | `common.period` |
| `DkKdkPatient` (+ `DkKdkPatientBody`, `DkLocalCaseAssigner`) | `md, ck, pid, bundle` | `patient.py` |
| `DkCoverage` (+ `DkCoverageBody`) | `ct, ck, pid, bundle` | `coverage.py`, `grz/donors.py:_coverage` (SKT → KBV payor type, UNK → NullFlavor; payor = the Patient only for `SEL`, otherwise a data-absent-reason payor) |
| `DkMvConsent` (+ `DkMvConsentBody`) | `mvc, ck, role, pid, bundle` | `consent.build_mv_consent` (KDK role `mv-consent`, GRZ `mv-consent:<donorPseudonym>`) |
| `DkResearchConsent` (+ `DkResearchConsentBody`, `DkRc*`) | `rc, ck, role, pid, bundle` | `research_consent._migrate` (KDK role `research-consent:<i>`, GRZ `research-consent:<donorPseudonym>:<i>`) |
| `DkKdkIndicationBoard` (+ body, detail) | `md, ck, pid, bundle` | `submission._indication_board` |
| `DkOrgSubmitter` / `DkOrgGdc` / `DkOrgKdk` | `sub, org : Organization` | `submission.submission_organization` (GRZ `submission` and KDK `metaData.submission`, same field names: identifier `le-id` / `genomic-data-center` / `clinical-data-node`, name `<label> <value>`; roles `org:submitter`, `org:genomic-data-center:<value>`, `org:clinical-data-node:<value>`) |

`DkResearchConsent` migrates the embedded MII Broad Consent of one `researchConsents[]` entry to
`mii-pr-consent-einwilligung` when `scope` is a FHIR Consent with a status (otherwise Python emits nothing for it; an
entry without scope is the absence Observation of the branch maps). Without `policy` (1..* in the profile) the Consent
carries no `meta.profile` (a core Consent), and without `policy` and `policyRule` it gets a `policyRule` with a
data-absent-reason (core ppc-1); a policy whose only content is a `#<id>` uri / authority without a contained resource of
that id is no policy (that value is removed). `contained` (declared as `Resource`) keeps the resources that a `#<id>`
reference, canonical, uri or url in a carried-over element names (not `patient`, `meta`, `text` or a dropped
DomainReference), or a kept contained resource names, transitively, and those referring to the Consent (`#`, dom-3); a
`#<id>` Reference without such a contained resource becomes the display `#<id> (missing contained resource)`, and a
`#<id>` canonical / uri / url without one is removed: `Coding.system`, `Identifier.system`, `Attachment.url`,
QuestionnaireResponse `item.definition`, and extension / answer values of any primitive type but string and markdown
(`research_consent._unresolved_local_refs`; Python takes every string element outside `bundle.NOT_URI` as a possible
uri). A kept Practitioner, PractitionerRole,
Organization, RelatedPerson, QuestionnaireResponse or Provenance is copied element by element (`DkRcContained`): its
references go through `DkRcReference` like the Consent's own (a sender-system reference, a `urn:uuid:` included,
becomes the display `<reference> (sender system)` unless a display or identifier is left), its datatypes through the
typed groups, and a `questionnaire` / `policy` `#<id>` without a contained resource of that id is removed
(`research_consent._contained`). As in Python: `id`, `meta`, `text`,
`implicitRules` and the sender's `patient` are dropped; empty strings are not copied (also inside the copied
datatypes, by typed groups); `patient` = our Patient; `scope` = `consentscope#research`; the
2025 category system `mii-cs-consent-consent_category` becomes `mii-cs-consent-version-modules`, and LOINC 57016-8 and the
MII Broad Consent category are added when missing; a bare policy OID becomes `urn:oid:…`; `dateTime` =
`presentationDate`, else the embedded `dateTime`; references into the sender's system (anything but `#`; a `urn:uuid:`
names an entry of the sender's Bundle) are removed, keeping the target as display `<reference> (sender system)` when
nothing else identifies it; a DomainReference extension survives only when its domain keeps a display, identifier or `#`
reference; `sourceReference` only with a resolvable `#` reference.
Deliberate simplifications: references are stripped in `Reference` elements, extension values (any depth) and
`Identifier.assigner`, not inside other datatypes; extension values of complex types other than CodeableConcept,
Coding, Period, Identifier and Reference are copied whole (an empty string inside them stays); `provision` is declared
to depth 3 (the MII profile allows 2); a contained resource of another type than the six above is
copied whole (Python also strips its sender-system references and its `#<id>` canonical / uri values without a kept
target), and so are HumanName, ContactPoint, Address, `meta`, `text`, nested `contained` and the backbone elements
without references of the six; a contained item without `resourceType` (invalid FHIR) fails the `$transform`.

**Cost of the contained-keep condition.** The keep rule of `DkResearchConsentBody` is evaluated level by level
(`defineVariable` r0 = the `#` values of the carried-over elements, k0 = the contained resources they name or that refer
to `#`, r1 = the `#` values inside k0, k1, r2, k2, r3), so its cost per contained resource is linear in the consent
size. The round-4 form nested the levels and re-scanned the consent root for every candidate (n^4: 15 contained
resources 31 s, 20 contained 113 s per `$transform`); after the closing fix 120 contained resources take about 0.3 s
(`test_fix4_fml.py::test_r39_keep_condition_cost_is_not_polynomial_in_contained`, scenario `R39-many-contained`).

**Accepted simplifications (R39).** The round-3 probe of 36 embedded-consent scenarios (verify-fixes3/r39) found 13
FML differences. Fixed in round 4 (parity, `test_fix4_fml.py`): `ext-canon-missing`, `ext-uri-missing`,
`ext-url-missing`, `ext-canon-missing-plus-q`, `nested-ext-canon-missing`, `provision-ext-canon-missing`,
`coding-system-missing`, `identifier-system-missing`, `attachment-url-missing`, `transitive-via-unkept`,
`transitive-canon-via-unkept`, `patient-local`, `meta-profile-local` (plus `ext-code-missing`, `qr-definition-missing`,
`domainref-local-unkept`, `transitive-kept-chain`). What HAPI FML cannot mirror, accepted and documented here:
- `other-type-with-urn`, `other-type-whole`: a contained resource of a type other than Practitioner, PractitionerRole,
  Organization, RelatedPerson, QuestionnaireResponse and Provenance is copied whole, so its sender-system references
  (also `urn:uuid:`) stay; Python replaces them with the display `<reference> (sender system)`. FML has no generic
  element traversal that could rewrite a Reference in an arbitrary resource type.
- `prim-ext`, `top-prim-ext`: primitive extensions (`_gender`, `_birthDate`, `policy._uri`, ...) and element `id`s of
  the copied elements are dropped; Python copies them. The typed copy rules assign the primitive value only.
- A chain of contained resources is followed to depth 3 (a resource referenced from a kept one that is itself three
  references away from the Consent); Python follows it to any depth. A deeper resource is dropped by FML.
- A `#<id>` in a code- or id-typed extension value counts as a reference for Python (it keeps that contained
  resource), not for FML (only Reference, canonical, uri and url do).
- `language-missing`, `contenttype-missing`, `contenttype-local` (verifier probe after round 4): Python's
  `research_consent` treats a `#<id>` in *any* string element whose key is not in `bundle.NOT_URI` as a local
  reference, including code-typed elements such as `Consent.language` and `Attachment.contentType`. Without a
  contained resource of that id Python removes the value and FML keeps it (a `language` `#nothere` is then an
  FML-only content error, "Invalid displayLanguage"); with one, Python keeps that contained resource and FML drops it.
  FML only looks at Reference, canonical, uri and url (and the string-typed `policy.uri` / `authority`).
None of these occurs in the corpus or in a real MII Broad Consent / gICS export.

## Oncology map (`DatenkranzOncologyToMii`) and its sub-maps

`main` computes the case key and the entry uuids, builds `ctx` once and calls `OncoCase`, which emits (Python builder in
brackets): Patient, Coverage, MV consent, indication board, the migrated Broad Consents (Common groups),
`mvgs-research-consent-absent` (`research_consent._absent`), the primary tumour with ICD-O-3 slots, additional / germline diagnoses, grading, HPO,
sequencing request, weitere-klassifikationen, the diagnostic-assessment Observation, TNM, ECOG (`onco/diagnosis`, `tnm`,
`ecog`), the Behandlungsepisode with the prior therapies, their MedicationStatements and responses
(`onco/prior_procedures`), and the prior reports with study, analysis and variants (`onco/prior_diagnostics`; the
legacy single object `case.priorDiagnostic` is one more report).
`metaData.submission` has no resource (`submission._submission` only records dispositions).

### `ctx`: the per-case context handed to the sub-maps

`ctx` is a `Parameters` object made with `create('Parameters')` in `main`. It is never put into the Bundle. Every
parameter is a `valueString`:

| name | value |
|:--|:--|
| `ck` | case key `kdk:<submitterId>:<CK>` (first argument of `DkEntry`) |
| `patient` | entry uuid of the Patient (`'urn:uuid:' + value`) |
| `primary` | entry uuid of the primary-tumour Condition. **Only present when it is emitted** (`case.diagnosisOd.mainDiagnosis.code` non-empty) |
| `episode` | entry uuid of the MTB Behandlungsepisode (always emitted) |
| `indicationBoard` | entry uuid of the indication board CarePlan (`mvgs-inclusion-decision`, only with `metaData.molecularBoardDecisionDate`); the Therapieplan's `basedOn` |
| `tumorSpread` | entry uuid of the first DNPM tumour-spread Observation (`mii-pr-mtb-tumorausbreitung`); the primary tumour's `stage` assessment |
| `ngsReport` | entry uuid reserved for the current NGS report (`mii-pr-mtb-ngs-bericht`, `onco/molecular_report.py`) |
| `ngsReport:<i>` | entry uuid of the own NGS report of `complexBiomarkers[i]`, only when several items yield biomarkers |
| `submitterId`, `caseId` | escaped submitterId and `CK`, for identifier values `<submitterId>\|<caseId>\|<esc(KDK id)>` (`molecular-finding-id`, `kdk-object-id`) |

Read a value with `(%ctx.parameter.where(name = 'ck').value) as ck`. A computed variable that evaluates to nothing cannot
be passed to a group, so guard optional values: `x where (%ctx.parameter.where(name = 'primary').exists()) -> o.focus as f
then OncoRefPrimary(ctx, f)`. `OncoRefPatient(ctx, ref)` and `OncoRefPrimary(ctx, ref)` live in the main map; sub-maps
cannot call them (imports are not transitive), so they write their own two-line equivalents.

### Entry groups of the sub-maps (fixed signatures)

| Map | Group | Called from | Must do |
|:--|:--|:--|:--|
| `OncoMolecular` | `OncoMolecular(source mol, target bundle : Bundle, source ctx)` | `OncoCase`, once, when `molecular` exists | every molecular resource; the NGS report with entry uuid `ctx.ngsReport` |
| `OncoMolecular` | `OncoMolEpisodeLink(source mol, source ctx, target ep : ClinicalImpression)` | the rule that creates the episode | `ep.investigation` (SNOMED 106221001, item → `ctx.ngsReport`) exactly when `OncoMolecular` emits the report (same FHIRPath predicate in both groups, otherwise the reference dangles) |
| `OncoPlanFollowUp` | `OncoPlanFollowUp(source src, target bundle : Bundle, source ctx)` | `OncoCase`, once (`src` = Datenkranz root) | plan and follow-up resources; CarePlan.supportingInfo → `ctx.episode` |
| `OncoPlanFollowUp` | `OncoPlanPatient(source src, source ctx, target pat : Patient)` | the rule that creates the Patient | `deceasedDateTime` / `deceasedBoolean` from the follow-up (`onco/followup.py`) |

Writes into a resource of another stage go through these hook groups, because target variables are only reachable from
the rule that created them (Q4). The same pattern is used inside the main map: the episode rule creates the prior
therapies and prior reports (`ep.supportingInfo`), and the TNM grouping rule creates the categories (`hasMember`).
References between sub-maps (for example from a therapy recommendation to a variant) need a uuid that both sides know.
Either reserve it in `ctx`, or create the referencing resource from the rule that creates the target.

### Resource keys (roles) of the spine

`patient`, `coverage`, `mv-consent`, `indication-board`, `research-consent:<i>` (Common); the three submission Organizations
`org:submitter`, `org:clinical-data-node:<clinicalDataNodeId>` and `org:genomic-data-center:<genomicDataCenterId>`
(`DkOrgSubmitter` / `DkOrgKdk` / `DkOrgGdc`, built the same way as GRZ from `metaData.submission`, as
`submission.submission_organization` does; the rare-disease map adds them too); `research-consent-absent:<i>`, `primary`,
`additional-diagnosis:<i>`, `germline-diagnosis:<i>` (index among the items with a code), `grading`, `hpo:<i>`,
`sequencing`, `additional-classification:<i>` (also the `mii-pr-mtb-tumorausbreitung` of a DNPM tumour-spread item),
`genetic-diagnostic-assessment`, `tnm:<i>`, `tnm:grouping`,
`ecog:diagnosis`, `episode`, `prior_procedure:<i>`, `prior_procedure:<i>:substance:<j>`, `prior_procedure:<i>:response`,
`prior_diagnostic:<k>`, `prior_diagnostic:<k>:study`, `prior_diagnostic:<k>:analysis`, `prior_diagnostic:<k>:variant:<j>`
(`<k>` = index in `priorDiagnostics[]`; the legacy `case.priorDiagnostic` takes the next index, 0 without
`priorDiagnostics[]`, so its resources are those of the same test resent as `priorDiagnostics[0]`).

**Array positions.** The engine has no rule index, and value equality
(`%list.select(iif($this = %item, $index, {})).first()`) gives two identical items one key: their conditional PUTs
collide and HAPI keeps one of them silently (R26), and a TNM lookup by such a key returned two values (HTTP 500, R52).
Every position is therefore taken from a counter: the caller creates `create('Parameters') as cnt` and passes it as a
target; the iterating rule binds `(%cnt.parameter.count()) as i` and then appends `cnt.parameter as p, p.name = 'i'`,
so `i` is the item's position whatever its content. A filtered position (germline diagnoses, coded substances) counts
in the filtered rule; a full-array position counts all items and filters in the called group. 'An earlier item with
the same id' is `%list.take(%i).where(...)`. `test_fix_fml.py` fails on any value-equality position in the production
maps. A GRZ submission with two donors of one pseudonym fails the transform (`check`), as Python's
'duplicate resource' does.

### TNM and other lookups

Each `tnmClassifications[]` item is classified once into a second in-memory `Parameters` (`tp`, value
`kind|cp|uicc|yra|edition`). The classification uses:

- a lookup string `|<sct>=<cp><UICC>|` generated from `mvgs-cm-tnm-sct-uicc` group 1. `translate()` cannot return the
  `cp` product or the source display that the MII invariant needs.
- the list of accepted UICC strings (group 2).

Regenerate both when the ConceptMap changes. The UICC coding of SNOMED items still comes from `translate()`.
Fixed local displays (ECOG, oBDS, MTB status reasons, test types) are copied from the Python builders.

### Molecular block (`OncoMolecular`)

`OncoMolecular(mol, bundle, ctx)` creates the current NGS report (`mii-pr-mtb-ngs-bericht`, entry uuid `ctx.ngsReport`,
role `ngs-report`) and, from the same rule, every finding, so that each one is listed in `rep.result` (Q4). The result
slices TMB, HRD score and ploidy are 0..1, so with several `complexBiomarkers` items that yield biomarkers (`tmb`,
`ploidy`, `hrdHigh`, `lstHigh` or `taiHigh`) each such item gets a report of its own (role
`ngs-report:complex-biomarker:<k>`, uuid `ctx.ngsReport:<i>`, result = its `[tmb, hrd, ploidy]`;
`molecular_report.py`). The main report exists when the block yields another finding (any `smallVariants`,
`copyNumberVariants`, `structuralVariants` or `expressionVariants` item, an `sbsSignatures` item with a non-blank name)
or exactly one item yields biomarkers. `OncoMolEpisodeLink` uses the same predicates for one `investigation:NgsBericht`
per report.

| Source | Resource (role) | Python |
|:--|:--|:--|
| `smallVariants[]` | `mii-pr-mtb-einfache-variante` (`small-variant:<k>`) + `mii-pr-molgen-molekulare-konsequenz` (`small-variant:<k>:consequence`) | `molecular_variants` |
| `copyNumberVariants[]` | `mii-pr-mtb-copy-number-variant` (`cnv:<k>`) + consequence | `molecular_cnv` |
| `structuralVariants[]` | `mii-pr-mtb-rna-fusion` (`RNA`) / `mii-pr-mtb-dna-fusion` (anything else) (`sv:<k>`) + consequence | `molecular_fusions` |
| `complexBiomarkers[]` | `mii-pr-mtb-mutationslast` / `-hrd-score` / `-ploidie` (`complex-biomarker:<k>:tmb\|hrd\|ploidy`) | `molecular_biomarkers` |
| `expressionVariants[]` | `mii-pr-mtb-rna-seq` (`expression:<k>`) | `molecular_expression` |
| `sbsSignatures[]` | `mii-pr-mtb-molekularer-biomarker`, one per name (`sbs:<k>:<SBSn>` or `sbs:<k>:#<j>`) | `molecular_signatures` |

`<k>` is the KDK identifier, or `<identifier>#<index>` when it is missing or repeats an earlier item of the same array
(Python `unique_key`). Every finding (not the consequences) carries the identifier
`https://genomde.de/fhir/sid/molecular-finding-id` = `<submitterId>|<caseId>|<KDK identifier>`.

**Variant references for the plan map.** Python resolves recommendation variant ids with
`ctx.ids[('variant', <KDK id>)]` (first finding with that id wins). FML has no shared registry, but a target Bundle is
readable from FHIRPath (`%bundle.entry…`) in every group that has it as a target, and it already holds the entries of
the groups that ran before. `OncoCase` calls `OncoMolecular` before `OncoPlanFollowUp`, and the findings are created in
Python pipeline order, so the first entry with the molecular-finding-id is the one Python registers. The plan map imports
`OncoMolecular` and calls

```fml
rec.<variantIds> as vid where (%bundle.entry.where(resource.identifier.where(system = 'https://genomde.de/fhir/sid/molecular-finding-id'
      and value = (%ctx.parameter.where(name = 'submitterId').value & '|' & %ctx.parameter.where(name = 'caseId').value & '|' & %vid)).exists()).exists())
   -> x.reasonReference as r then OncoMolFindingRef(vid, ctx, bundle, r) "variant";
```

`OncoMolFindingRef(source vid, source ctx, target bundle : Bundle, target ref : Reference)` sets
`ref.reference = <fullUrl of that entry>`. An id without a finding fires no rule (Python drops it). The plan's own
`OncoPlanVariantRefs` / `OncoPlanVariantInfo` add the split-CNV rule of `careplan._variant_refs`: a cited id without an
exact finding resolves to every finding whose id is `<cited>_<suffix>` (first Observation per id), and a finding cited
twice is listed once. Conditional references (`Observation?identifier=…molecular-finding-id|…`) are not used: a
complex-biomarker id is shared by up to three Observations, so HAPI would find several matches.

### Plan and follow-up (`OncoPlanFollowUp`)

- **Recommendations.** An id already reserved (also a generated `<id>#<k>`) is a further recommendation: id part
  `<id>#<i>` (`careplan._rid` looks up the ids it produced); the reserve phase stores the id of every position in `reg`
  (`trid:<i>`, `srid:<i>`, `pmid:<i>`) and the emitting groups read it back. `reg` keeps the first occurrence under the
  plain id, so the follow-up's references resolve to it. A combination's member `j` (position among the coded
  substances) has role `therapy-recommendation:<tid>` for `j = 0` (the single-substance key) and
  `therapy-recommendation-member:<tid>:<j>` otherwise, uuid `reg tr:<tid>` / `trm:<tid>:<j>`; member 0 carries the
  identifiers `<id>` and `<id>:0`, member `j >= 1` `<id>:<j>`, the RequestGroup `<id>`. A follow-up
  MedicationStatement's `basedOn` is the first member with the same ATC code (`reg trmc:<tid>|<code>`; a
  single-substance recommendation: its request; a combination without that code: none, `trg:<tid>`); `causedBy`
  stays member 0. The rare-disease map does the same for its recommendations (`rd.careplan._rid`: a produced id part,
  also a generated `<id>#therapy-<k>` / `<id>#study-<k>`, gets `#therapy-<i>` / `#study-<i>`; a Parameters `rids` holds
  every produced one) and keys a further variant with an already produced base (`<identifier>`, else `#<index>`) as
  `variant-dup:<kind>:<base>:<index>` (`rd.variants`: the index is an id part of its own).
- **Studies.** Placeholder names / ids (`''`, `n/a`, `na`, `unknown`, `-`, `unbekannt`, `k.a.`, `k. a.`,
  `keine angabe`, `n.a.`; trimmed, any case: `careplan._real`, regex
  `'^(|n/a|na|unknown|-|unbekannt|k[.]a[.]|k[.] a[.]|keine angabe|n[.]a[.])$'` after stripping the whitespace Python's
  `str.strip()` removes (a regex: `trim()` keeps U+00A0 and the other Unicode spaces) and `.lower()`, `[.]` instead of
  an escaped dot) give no title, no ResearchStudy key and no note; the same rule in the rare-disease map.
  A recommendation whose ResearchStudy came from an earlier one notes a different real name and every substance
  the first one's focus lacks (`careplan._repeated_study`).
- **Follow-up order.** Python processes `followUpOds[]` in `followUpDate` order (same date: array order; undated
  first), and a later report replaces an object it reports again. FML has no sort over rules, so every such object
  (follow-up therapy Procedure, MedicationStatement, response, metachronous diagnosis, preventive-measure result,
  Tod / `deceasedDateTime`) is emitted from its *winner*: the follow-up with the greatest processing key
  `sk = '<followUpDate> <4-digit position>'` among those reporting it, computed with `select()` + `aggregate()`
  (`' '` sorts below every date character, so an undated follow-up is the earliest). Within one follow-up the last
  equal item wins (positions from counters). A repeated HPO code is a further Observation (`<code>#<j>`).
- **Follow-up therapies** (`followup._FollowUp.therapy_ids`). The reserve phase walks the follow-ups in processing
  order (slot `r` picks the follow-up of rank `r`) and keeps Python's `therapies` state in `reg`. With
  `K = <reference>|<start>`, the substance keys of an entry (ATC code as sent, else the name with every run of
  `str.split()` whitespace, U+00A0 and the other Unicode spaces included, collapsed to one space, stripped and
  lower-cased: `followup._norm`; `''` left out), its suffix (the keys with `\` and `+` escaped by `\`, sorted, joined by
  `+`), `part = K#<suffix>`, `n` = the entries of this follow-up with `K` and *earlier* = the keys reported by earlier
  follow-ups (an `ftw` value below the current processing key), the key of an entry is: `K` when `n = 1` and no
  earlier `K#…` part exists; else `K` when `K` is earlier and the keys of all its reports (`ftk:K`) equal the entry's;
  else `K` when `n = 1` and neither `part` nor `K` is earlier; else `part`. Another entry of this follow-up with `K` and
  the same keys but other attributes (end date, termination reason, response, response date, response source) makes it
  `part#<those five values joined by #>`, a Procedure of its own. Only identical content is one therapy (one key, the
  later entry writes it); one substance's end, termination reason or response is never carried over to another
  substance. `reg` records per key the processing key of every report (`ftw`; the last one writes the Procedure), per
  key and ATC code (`fts`; MedicationStatement) and per key and response date (`ftr`), and the names reported uncoded /
  coded (`ftn` / `ftc`): the Procedure note lists the uncoded names of all reports (one spelling per normalised name,
  the first reported) minus every name or display any report sent coded (compared as sent). Identical follow-ups emit
  each object once (R62).
- **Follow-up diagnoses** are coded by their system (`diagnosis_coding`; no system = ICD-10-GM); a code that is empty
  after normalisation (`ORPHA:`, blank, `+` alone) gives no Condition, replaces no earlier item with the same code and
  date, and leaves `metachroneDiagnoses = true` explicit (`mvgs-ex-metachronous-tumor`). Whitespace is what Python's
  `str.strip()` removes (a regex, since `trim()` keeps U+00A0 and the other Unicode spaces), and every emptiness test
  ends in `& ''`: on matchbox `upper()` of `''` is an empty collection, which made a blank ICD-10-GM code look neither
  empty nor non-empty.

### Known differences to the Python converter

None on the corpus (all 1259 valid manifest files and the 84 MV dummy submissions were equal on the raw input in the
round-4 parity run; the manifest has listed 1253 valid files since the 3 older RD example files were removed from both
example folders). Beyond it:
- The deliberate simplifications of `DkResearchConsent` (Common groups).
- String handling of the engine where Python differs: keys are sorted by UTF-16 code unit (Python: by code point;
  they differ only between characters outside the BMP and U+E000-U+FFFF). (Resolved in round 4: substance names are
  normalised with the whitespace class of Python's `str.split()` / `str.strip()`, U+00A0 and the other Unicode spaces
  included, and the placeholder test strips the same class instead of `trim()`.)
- (Resolved) An empty array of a renamed key (`priorRds: []`, `variants: []`) is read like an absent key on both paths
  (finding R54: matchbox parses `[]` as absent, Python treats it so). An integral decimal priority (`1.0`, `1e0`) is
  kept as that integer on both paths (R69).

## Parity with the Python converter

Measured on 2026-10-10 (after the fix stage of release 0.10.0: case key with test marker and escaping, positions from
counters, follow-up winners, tumour spread, per-item biomarker reports, …) with `genomde2fhir/tests/test_fml_integration.py`
against matchbox 4.1.21 and HAPI 8.4. The package and all production maps were loaded with
`build_mvgs.py --install … --maps`. The 84 MV dummy submissions of the prior pipeline (`example-data/{oncology,rarediseases}`
and the 2026-10 refresh of `mv_dummy_data`) are equal on the raw input too (42 + 42 files, 6 816 + 2 212 resources).

**Method.**
- Parity is graph-aware: `canonical()` from `scripts/run_corpus.py` compares the multiset of resources. References are
  replaced by `<type>/<profile tail>#<hash of the target's content>`, so a reference to the wrong resource of the same
  profile is a difference. Ids, `meta` except `meta.profile`, `text`, resource-key identifiers and Provenance are
  ignored; decimals compare by their written spelling.
- Each file is compared twice:
  - **raw**: what a site sends;
  - **declared shape**: legacy keys renamed to their schema names, as the Python builders treat them
    (`case.priorRd` → `priorRds`, `case.priorDiagnostic` → one more `priorDiagnostics` entry,
    `plan.*.variantReferences` → `variants`), and every property the logical model does not declare removed (FHIR
    datatype elements of the extras are kept whole).
  Both converters get the same declared-shape input. The Python converter runs it without the input gate.
- Content errors come from `validate_bundle` with the source file. The FML Bundle may have no content error that the
  Python Bundle of the same file does not have.

**Round 4 (2026-10-10, KDK submission Organizations in FML, Unicode-whitespace and R39 fixes):** package and maps pushed
with `build_mvgs.py --install … --maps`; raw parity with `canonical()` of `scripts/run_corpus.py` on every valid
manifest file, the replaced examples included: oncology 668 / 668 equal (38 795 resources), rare disease 132 / 132
(7 598), GRZ 459 / 459 (10 159); MV dummy refresh 42 + 42 equal (6 942 + 2 338). 0 differences, no duplicate fullUrl or
conditional URL. Validated sample (8 manifest files per branch, plus 2 MV dummy files per KDK branch): content errors
FML-only 0 (FML 0 / Python 0); HAPI double ingest of the FML Bundles 28 / 28 ok, the second POST creating nothing.
The table below is the earlier 0.10.0 fix-stage measurement.

| Branch | Valid files | Bundles | Declared shape equal | Raw equal | Equal resources (raw) | Content errors FML / Python (24-file sample) | HAPI double ingest |
|:--|--:|--:|--:|--:|--:|:--|:--|
| oncology | 668 | 668 | 668 | 668 | 36 810 | 0 / 0 | 6 / 6 ok |
| rare disease | 126 | 126 | 126 | 126 | 7 278 | 0 / 0 | 6 / 6 ok |
| GRZ | 459 | 459 | 459 | 459 | 10 159 | 0 / 0 | 6 / 6 ok |

- **Raw and declared shape:** 0 differences on all 1253 valid corpus files (raw, `canonical()` of
  `scripts/run_corpus.py`) and on the 24-file samples per branch (raw and declared shape, 2026-10-10), no duplicate
  fullUrl or conditional `request.url` in any FML Bundle. The samples include KDK files with an embedded Broad Consent,
  `case.priorDiagnostic`, `case.priorRd` and dated germline diagnoses; the GRZ corpus has only empty `scope` objects
  (`test_fml_grz.py::test_grz_research_consent_migrated` covers a GRZ Broad Consent). Beyond the corpus, the ~80
  mutation scenarios of `test_fix_fml.py` (duplicate items of every array, test submissions, follow-up order, …) are
  equal as well.
- **Content errors:** none on either side in the samples. An earlier run found one shared error on
  `ukdd/synth_json_447` (Therapieplan `supportingInfo` "Unable to find a profile match" for the Behandlungsepisode,
  caused by a variant whose HGVS check timed out at tx.fhir.org; not a cascade `validate_bundle` recognises).
- **HAPI double ingest:** both POSTs return 2xx with one response entry per request entry, and the second POST
  answers 200 for every entry and creates no resource. A fresh case (new `localCaseId`) answers 201 for every entry on
  the first POST.

**Non-schema input properties.** matchbox drops every property the logical model does not declare when it parses the
input (Q6). The properties the Python converter reads are therefore declared as extras of the logical models (table in
"Files"); before that they caused every raw difference (onco 644 files, RD 126). The undeclared properties left in the
corpus are read by neither converter: `histology.text`, `topography.text` (oncology), `genes[].system`,
`localization[].system|display` (rare disease), `$schema` and `_paired_with` (GRZ).

**Differences by convention (excluded from parity).**
- The FML maps set no resource id. Every resource carries the resource-key identifier and is written by a
  conditional `PUT <Type>?identifier=…resource-key|<base64url key>`. Python uses `PUT <Type>/<uuid5>`. A Python ingest
  and an FML ingest of the same case into one server therefore give two separate sets of resources.
- The FML maps emit no Provenance; both paths write the same `meta.source` on every resource (the submission marker),
  but `canonical()` drops `meta` except `meta.profile`.
- Both converters key resources by stream (`kdk` or `grz`), submitterId and case key (`docs/IDENTITY.md`). An
  oncology case and a rare-disease case with the same submitterId and localCaseId therefore share the Patient,
  Coverage, MV consent and indication board. This happens on both paths.

**`scripts/run_corpus.py --fml`** uses the same `canonical()` (references resolved to the target's content,
`meta.profile` compared) on the raw files, validates the FML Bundle and ingests it twice; the parity above holds there
as well (`--gate` fails on any difference).

## Engine behaviour (matchbox 4.1.21, verified)

| Topic | Result | Probe |
|:--|:--|:--|
| `imports` | Groups of an imported map can be called. A missing import is accepted at upload and fails at `$transform` with `Unable to find map(s) for …`. | `EngineImportMain` + `EngineImportLib` |
| import binding | An importing map binds the imported maps **when it is loaded**. After a library is updated, its importers keep the old version until they are pushed again. Push libraries first and push everything every time. | manual re-push sequence with `EngineImportLib` |
| transitive imports | A group of an imported map may call groups of *its* imports. The main map cannot call those directly (`No matches found for rule`). | `EngineImportTransitive`, `EngineImportTransitiveDirect` |
| name collision | A local group with the same name as an imported one wins silently. | `EngineImportCollision` |
| multi-source groups | Groups with several `source` parameters work. Target variables, including `uuid()` results, can be passed as source arguments. | `EngineImportMain`, `EngineVarsProbe` |
| uuid passing | `md -> uuid() as fid` creates a string variable without a context element. In FHIRPath it is `%fid`. | `EngineVarsProbe` |
| computed variables | `('literal') as v` and `(expr) as v` work. `'literal' as v` fails (`target context not known`). | `EngineVarsProbe` |
| several groups per rule | `then G1(...), G2(...)` works. | `EngineVarsProbe` |
| resource assignment | `e.resource = create('T') as r` works. Assigning a resource created earlier in the rule (`e.resource = r`) loses it. | `EngineVarsProbe` |
| concatenation | `+` and `&` both work in target expressions. `+` with an empty operand gives an empty result, `&` treats it as `''`. | `EngineFhirpathProbe` |
| FHIRPath in targets | `%var`, and also a bare variable name at the start of the expression, resolves rule and group variables. `%res.type().name` gives the resource type name, but `%res.resourceType` is empty. `iif`, `matches`, `replaceMatches`, `aggregate` work. `min()` is unknown (parse error), so use `aggregate(iif($total.empty() or $this < $total, $this, $total))`. | `EngineFhirpathProbe`, `EngineVarsProbe` |
| `encode('urlbase64')` | Works. It uses the RFC 4648 §5 alphabet (`-`, `_`) with `=` padding. `encode('base64')` uses `+` and `/`. | `EngineFhirpathProbe` |
| `translate()` | Works with the mvgs ConceptMaps, including maps whose group has no `source`. `'coding'` gives system, code and display. `'code'` gives the code only. An unmapped code gives nothing (no error). | `EngineTranslateProbe`, `EngineTranslateUnmappedProbe` |
| `c(system, code, display)` | The display argument is ignored. The display is looked up in the terminology, and for an unknown system there is none. Write codings element by element. | `EngineCodingProbe` |
| empty elements | Complex elements left empty (for example a `CodeableConcept` whose translate gave nothing) are dropped from the JSON. | `EngineTranslateUnmappedProbe` |
| replacing a map | `POST /StructureMap` (text/fhir-mapping) **upserts by map url**. The resource id is the map `name`, the answer is 201 every time, and there is never a duplicate. `PUT /StructureMap/<id>` (text/fhir-mapping) also replaces by url (200), and the id in the path is ignored. The loader uses POST. | `EngineReplaceProbe` (rewritten v1→v4 during the check) |
| HAPI conditional PUT | `PUT T?identifier=sys\|value` in a transaction with urn:uuid fullUrls and references: first POST 201, second POST 200 and **no new resources**. References are resolved. A `\|` inside the value is accepted, because HAPI splits at the first `\|`. Space or `&` → HAPI-1744, `%` → HAPI-0929, so keys are base64url. | Common probes + `genomde2fhir/tests/test_fml_common.py` |
| HAPI counts | `GET T?_summary=count` is served from HAPI's search cache, so it is stale for about a minute after a write. Send `Cache-Control: no-cache` when checking idempotency. | `test_fml_common.hapi_count` |
| `translate()` into a choice element | `x.value = create('CodeableConcept') as v, v.coding = translate(c, url, 'coding')` fails for every choice element (`Observation.value[x]`, `Extension.value[x]`, even when written as `valueCodeableConcept`) with `Unable to find type g for element coding`. The outputs `'system'`, `'code'` and `'display'` work: `v.coding as cd, cd.system = translate(c, url, 'system'), cd.code = translate(c, url, 'code'), cd.display = translate(c, url, 'display')`. | DatenkranzOncologyToMii (method type, TNM UICC coding) |
| indexer after a bare function in `where()` / `select()` | `%coll.where(split('\|')[0] = 'U')` matches **every** item (wrong result, no error). `$this.split('\|')[0]` or `(split('\|')[0])` is correct. Qualify functions with `$this.` inside iteration functions. | TNM grouping (`OncoTnmGroupBody`) |
| empty computed variable | `(expr) as v` that evaluates to nothing fails when `v` is passed to a group (`INPUT variable 'v' ... has no value`). A computed `''` is a value. | ctx `primary` |
| collection-valued computed variable | `(%list.select($index)) as i` fails (`returned 3 objects`). Computed variables do not iterate. Use `select(iif($this = %item, $index, {})).first()` for an index. `$index` and equality of logical-model elements work. | resource-key indices |
| in-memory context object | `create('Parameters') as ctx` in a rule and filled by a group (target) can be passed to further groups, also of imported maps, as a *source*. `%ctx.parameter.where(name = 'x').value` reads it, and it is never serialised. `then G1(..), G2(..)` runs in order: G2 sees what G1 wrote. | `ctx`, `tp` |
| empty group | A group without rules loads and runs (sub-map stubs). | `OncoPlanFollowUp.map` |
| target Bundle in FHIRPath | A group's target `bundle` is readable as `%bundle` in `where (…)` conditions and in target expressions, including entries created by earlier groups (`%bundle.entry.where(resource.identifier…).first().fullUrl`). Used as the cross-group look-up of findings by id. | `OncoMolFindingRef` |
| `translate()` of an `unmatched`-only element | Throws `Concept map … found no translation for <code>` (500), unlike a code that is not in the map at all (nothing, no error). Guard such codes (`mvgs-cm-cnv-type-dnpm` `gain`). | `OncoMolCnvType` |
| `toInteger().toString()` | Keeps the original text, leading zeros included (`'06'` stays `'06'`). Strip zeros by regex (`0*([0-9]+)`). | SBS normalisation (`OncoMolSignature`) |
| primitive sources into typed targets | An integer / decimal source assigns to `Quantity.value` and `Range.low.value`; a boolean or string source assigned to `component.value` gives `valueBoolean` / `valueString`. | `OncoMolSmallVariantBody`, `OncoMolTmbBody` |
| undeclared properties in FHIRPath | Properties missing from the logical model are dropped at parse time and are invisible to FHIRPath too: `children()` lists only declared elements. A BackboneElement without declared children keeps only its inherited `extension`. Hence the extras of `schema_to_logical.py`. | `researchConsents.scope` (before the extras) |
| FHIR datatypes in a logical model | A logical-model element typed `CodeableConcept`, `Coding`, `Reference`, `Extension`, `Identifier`, `Period`, `Attachment` or `Meta` is parsed with that datatype's definition: FHIRPath navigates into it, and `src.x as v -> tgt.x = v` copies it whole into the target (also into a choice: an `Attachment` into `Consent.source[x]` gives `sourceAttachment`). The inherited `extension` / `modifierExtension` of a declared logical BackboneElement are parsed too. A logical child named `resourceType` or `id` is an ordinary element. | `DkResearchConsent` via `CommonKdkOncologyProbe` (`test_fml_common.py`, `rc-*` cases) |
| resource-typed element in a logical model | Type `Resource` (or `Consent`) parses an embedded resource completely, but an object without `resourceType` (the schema-valid `scope: {}` of every GRZ corpus file) fails the whole `$transform` with `Unable to find resourceType property` (HTTP 500). Not used: the Consent elements are declared one by one. | throwaway probe model `EngineProbeResTyped` (2026-10-09, not kept in `test/`) |
| cardinality mismatches at parse time | A JSON object for a max `*` element is parsed as a one-item list; a JSON array for a max 1 element is dropped silently (no error). | `case.priorRd` (max `*`), `case.priorDiagnostic` (max 1) |
| type-restricted source, `is` | `x.value : Reference as v` fires only for a `valueReference`; `where ((v is Reference).not())` selects the other value types. | `DkRcExtension` |
| primitive with extension only | `r.recordedDate as rd, rd.extension as x, ...` and `o.effective = create('dateTime') as d, d.extension as x, ...` give `_recordedDate` / `_effectiveDateTime` with the data-absent-reason. | grading, germline diagnoses |
| string functions | `upper()`, `lower()`, `trim()`, `contains()`, `startsWith()`, `endsWith()`, `split()`, `join('\n')`, `substring()`, `in (a \| b)` work. `replaceMatches()` works with `$1` groups and `(?i)`. Anchored `matches('^...$')` works. `'\\s'` is a regex `\s`. `replace('\\', '\\\\')` is a literal replace (one backslash doubled). | DatenkranzOncologyToMii |
| counters | `(%cnt.parameter.count()) as i, cnt.parameter as p, p.name = 'i'` on a `Parameters` passed as a target gives each iteration its position, also for identical items. | `EngineCounterProbe`; resource-key positions (all maps) |
| `$index` | Works in `select()` and in `iif()` inside `select()`; inside `where()` it is always 0 (wrong result, no error). | probe 2026-10-09 |
| `sort()`, `defineVariable()` | `sort()` sorts strings; `defineVariable('x'[, expr])` binds a variable for the rest of the chain, visible in nested `select()`/`where()`, also with `$index` (`defineVariable('m', $index)`); re-defining in every iteration is fine. Use names that no FML variable of the rule has (the maps use `z…`). | follow-up winners, F12 note, `EngineSortProbe` |
| `distinct()` | Keeps the *last* occurrence order (`'b,a,c,a'` → `b,c,a`); for first-seen order use `take($index)` with `defineVariable`. | F12 note |
| indexer, `aggregate` | `%list[1]` works; `aggregate(iif($total.empty() or $this > $total, $this, $total))` is a string max. | follow-up winners |
| `check (expr)` | A source `check` that is false fails the `$transform` (HTTP 500, `Rule "...": Check condition failed`). | `EngineCheckProbe`; GRZ duplicate donor pseudonym, `unique-keys` in every main group |
| extension on a computed string | `(expr) as ck, ck.extension as x, x.url = 'u', x.value = (…)` keeps the extension on the variable through group calls (`%ck.extension…` reads it; `%ck & ':'`, `matches()` see only the value). Stored as a `Parameters` value it is lost. | `ck` meta.source marker (main groups, `DkEntry`) |
| `hasValue()`, `toString()`, `is` | `hasValue()` is false for a primitive `''` but **true** for complex values (CodeableConcept, Coding, Reference, Quantity); `toString()` is `''` for a primitive `''` and non-empty for a complex value (`valueCoding=Coding[1 children]`); `v is Reference` etc. are correct. A rule `x.value as v where (v.hasValue()) -> t.value = v` next to typed rules therefore writes a complex value twice (a duplicate JSON key; parsers keep one copy). | `DkRcExtension` (typed values excluded with `is`, a primitive only when `toString() != ''`) |
| number spelling | An `integer` element of a logical model keeps the input spelling (`1.0`, `10.00`, `1e0` parse; `toString()` gives the text). `toDecimal()` is unusable for them (`10.00` fails `truncate() = $this`, an exponent gives HTTP 500). | `OncoPlanPrio` (string arithmetic) |
| state in processing order | A rule that iterates `followUpOds` once per slot and picks the item of rank `r` (`where (<count of smaller sort keys> = %r)`) visits the items in sort order, so a `Parameters` passed as a target can hold state across them. | `OncoPlanReserveFu` (follow-up therapy keys) |
| list modes | `src.list first as x` / `not_first as x` work. | Broad Consent categories |

### fml-edit-safe quirks (written for 4.0.12) on 4.1.21

| Quirk | 4.1.21 | Probe |
|:--|:--|:--|
| Q1 bare `where x != 'v'` | **Fixed**: it parses and evaluates correctly. For consistency, still write `where (x != 'v')` or `(x = 'v').not()`. | `EngineQuirkQ1`, `EngineQuirkQ1bare` |
| Q2 method call on an as-bound variable without parentheses (`= t.substring(0,8)`) | **Still breaks**: upload fails with `Found "(" expecting ";"`. With parentheses (`= (t.substring(0, 8))` or `(%t…)`) it works. A method call inside a parenthesised `where (…)` condition is fine. | `EngineQuirkQ2`, `test/expect-fail/EngineQuirkQ2bare` |
| Q3 literal argument in a group call | **Still applies**: the literal is looked up as a variable name (`INPUT variable … has no value`). Bind it first with `('lit') as v`. | `EngineQuirkQ3` |
| Q4 target variable re-used in a later rule | **Still applies**: `target context not known`. Nested `then { … }` rules of the binding rule do see it. | `EngineQuirkQ4`, `EngineQuirkQ4b` |
| Q5 multi-step source path (`src.a.b.c as x`) | **Still applies**: upload fails with `Found "." expecting ";"`. Descend one step per rule. Multi-step paths *inside FHIRPath expressions* (`%md.submission.submitterId`) are fine. | `test/expect-fail/EngineQuirkQ5` |
| Q6 source path not declared in the logical model | **Silent**: the rule fires zero times (no NPE). Every path must be declared in the generated logical model. | `EngineQuirkQ6` |

The static checker (`~/.claude/skills/fml-edit-safe/scripts/check-fml.sh`) reports Q2 false positives for method calls
inside a parenthesised `where (…)` condition, for example `md.addressAGS as a where (a.matches('^[0-9]{8}$'))`.

## Tests

- `genomde2fhir/tests/test_fml_integration.py` (skipped unless `MB2027` is set) pushes all production maps and runs one
  file per branch. Each file must give:
  - a Bundle;
  - no content error that the Python output does not have;
  - exact parity on the declared shape;
  - exact parity on the raw file;
  - an idempotent double ingest into HAPI-2027.

  It also checks the load order of the maps.

  Wide run: `MB2027=… python genomde2fhir/tests/test_fml_integration.py --n 20 --ingest 5`. `--n -1` runs the whole
  corpus. `--no-validate` runs transform, parity and ingest only: all 1253 files take about 2 minutes.

- `genomde2fhir/tests/test_fml_onco_spine.py` (skipped unless `MB2027` is set) pushes all production maps. It runs
  3 oncology inputs (the fixtures `onco_diagnosis/diagnosis_full.json` and `onco_prior/prior_all_enums.json`, and the
  DNPM file `example-data/oncology/OncologySubmission_044AFF6262356F2F8EC60039DC08AE36FBAA011DE29740CBC83E9FA5643E4640.json`)
  and 13 edge-case mutations of the prior fixture. Each run checks:
  - a Bundle;
  - no content error that the Python output of the same file does not have (both sides classified with
    `source=dk`);
  - zero parity differences on the spine resources, selected by the same function from both Bundles (follow-up
    `deceased[x]` and molecular `investigation` normalised away on both sides);
  - a double ingest, where the second ingest gives only 200 and no new resources.

  Wide run: `MB2027=… python genomde2fhir/tests/test_fml_onco_spine.py --n 60 --ingest 6`.

- `genomde2fhir/tests/test_fml_onco_molecular.py` (skipped unless `MB2027` is set) pushes all production maps and runs
  3 oncology inputs (the fixtures `onco_biomarkers/synthetic_biomarkers.json` and `onco_cnv_sv/cnv_sv_enums.json`, and
  the DNPM file `example-data/oncology/OncologySubmission_B2A88F25BF17D1913417EFC81DE39E22CF2047AED143BEA183C33BBB000AFD68.json`)
  plus 8 edge-case mutations of the biomarkers fixture (expression variants, duplicate ids,
  HGVS / transcript forms, fusion profiles, biomarker combinations, SBS name forms, no findings, no primary). It requires
  a Bundle, no content error on the molecular resources that Python does not have, zero parity differences on the NGS
  report, its results and the episode's `investigation`, the same finding for every KDK id as Python's
  `ctx.ids[('variant', id)]`, and an idempotent double ingest. Wide run:
  `MB2027=… python genomde2fhir/tests/test_fml_onco_molecular.py --n 80 --ingest 12`.
- `genomde2fhir/tests/test_fml_common.py` is skipped unless `MB2027` is set. It pushes Common and its probes, then
  runs one file per branch plus 25 edge-case mutations through the probes (10 of them on the embedded Broad Consent:
  every carried-over element with sender references, category variants, embedded `dateTime`, not a Consent, no status,
  DomainReference without domain, provision depth 3, several entries). It requires:
  - a Bundle;
  - zero content errors (`validate_bundle`; `rc-provision-depth-3` has the one input error Python carries over too);
  - graph-aware parity with the Python converter on the resources Common emits (`canonical()` from
    `scripts/run_corpus.py`);
  - a double ingest into HAPI-2027, where the second ingest gives only 200 and no new resources.
- Wide run: `MB2027=http://localhost:8091/matchboxv3/fhir python genomde2fhir/tests/test_fml_common.py --n 25`.
- `genomde2fhir/tests/test_fml_rd.py` (skipped unless `MB2027` is set) runs 3 rare-disease files (raw;
  `example-data/rarediseases/RareDiseasesSubmission_06B1EE824EDF30E43FAA6FF4DCFC5E00FD9A772ACCE0E4AD0BC593F6834F6566.json`,
  `example-data/rarediseases/RareDiseasesSubmission_9CCF7812F458C024A5D35754087C22A48E935AC16BA0056C61CE3F8A9CE846F3.json`,
  `examples/rarediseases/RareDiseasesSubmission_4B8581EA6277B9C60B04DD2304B40ED1C57B886FAD33E28C3C6575A76CCE248F.json`)
  and `test_fml_grz.py` 4 GRZ files (`example-data/grz/grz-edge-correction-multi-donor.json`, the fixtures
  `grz_labdata/grz-labdata-onco-edge.json`, `grz_labdata/grz-labdata-rd-duo.json` and `grz_donors/all_relations.json`),
  each with whole-Bundle parity, content errors and a double ingest, plus edge-case mutations (RD: on the declared
  shape; GRZ: wide run, and `test_grz_research_consent_migrated` for an embedded Broad Consent per donor, which the GRZ
  corpus lacks).
- `genomde2fhir/tests/test_fix_fml.py`, `test_fix2_fml.py`, `test_fix3_fml.py` and `test_fix4_fml.py`: offline guards (no
  value-equality position in a production map; every FML test input is tracked in git; Python R69; the round-3 / round-4
  rules in the map text; the whitespace class against `str.isspace()`) and, with `MB2027`, ~210 mutation scenarios of in-repo fixtures (duplicate items of every array, test submissions,
  escaped case ids, follow-up order and winners, follow-up therapies split / merged / regrouped in every array order,
  combination members, placeholders, TNM editions, tumour spread, meta.source encoding, contained resources with
  sender references, KDK submission Organizations, Unicode-space names and placeholders, `#<id>` values without a
  contained resource, …) with zero differences under `canonical()`, no duplicate fullUrl / request.url, no duplicate
  JSON key in the raw `$transform` response, and a double ingest of the duplicate-item cases (one response per request
  entry, the second POST only 200).
- Every FML test reads only files git tracks (`example-data/{oncology,rarediseases,grz}`, `genomde2fhir/tests/fixtures`;
  never the untracked synthetic corpus); a missing input fails instead of skipping.
