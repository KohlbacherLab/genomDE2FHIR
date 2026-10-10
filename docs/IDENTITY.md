# Identity, idempotency and linkage (genomde2fhir)

## Keys

| Stream | Case key | Stable across submissions? |
|:--|:--|:--|
| KDK (oncology, rare disease) | `metaData.submission.submitterId` + `metaData.localCaseId` | yes — the schema defines `localCaseId` as the sender's id for all submissions of a case |
| KDK without `localCaseId` (optional in the schema) | `submitterId` + `metaData.tanC` | no — TAN-C is per submission; follow-ups then create new resources (warning on `metaData.localCaseId`, report `case_key_fallback`, summary `case_key_tan_fallback`) |
| GRZ | `submission.submitterId` + `submission.localCaseId` (required; without it `tanG`, warned and counted the same way) | yes |
| GRZ donor | case key + `donors[].donorPseudonym` | yes |
| Test submission (KDK `metaData.submission.type`, GRZ `submission.submissionType` = `test`) | as above, case key `<caseId>|test` | yes, but in its own namespace: never equal to a real submission of the case |

### Test submissions

`test` ("technical testing of submissions") is converted, but it can never touch real data:

- the case key gets the marker `|test` (`<localCaseId>|test`, or `<TAN>|test`). Components are escaped (below),
  so the unescaped separator cannot occur in a real case key: every resource id and every case-scoped identifier
  value (`local-case-id`, `donor-pseudonym`, `molecular-finding-id`, `kdk-object-id`, `grz-lab-data-name`) differs
  from the one of a real submission of the same case (a real `localCaseId` `X|test` is escaped to `X\|test`);
  the sample barcode (`<submitterId>|<barcode>|test`) gets the marker too. Identifiers of external entities
  (LE / GRZ / KDK Organizations) and the per-submission TANs are not namespaced;
- every resource carries `meta.security` = `http://terminology.hl7.org/CodeSystem/v3-ActReason#HTEST` ("test health
  data"), so servers and queries can exclude it (`_security:not=...|HTEST`);
- the report has `test: true` and a warning on the submission type; the summary counts `test_submissions`.

TAN-C (VNk) and TAN-G (VNg) are transaction numbers for reimbursement; they are recorded as identifiers
(type `PSEUDED`), never used to link resources across streams.

## Resource ids

`id = uuid5(NS, "<stream>|<submitterId>|<caseKey>|<ResourceType>|<local parts>")`
(`NS = uuid5(NAMESPACE_URL, "https://genomde.de/fhir/genomde2fhir")`, `genomde2fhir.identity.CaseKey.id`).
Every component is escaped before joining: `\` -> `\\`, `|` -> `\|` (`identity.esc`), so two different part tuples
never give the same string (e.g. `localCaseId` `a|b` cannot meet case `a` with a local part `b`). Plain components
are unchanged, so ids of inputs without `|` or `\` are the same as in earlier releases. The case key is the escaped
case id plus `|test` for test submissions (section Keys).
Local parts are source identifiers where the schema has them (variant `id`, recommendation `id`, therapy
`id`, donor pseudonym, lab-data `labDataName`) and otherwise the semantic role plus the array index
(e.g. `("followup", 2, "ecog")`). Array positions are only used where the schema has no identifier, and never where a later submission may
carry a subset of the array:

- follow-ups (oncology, RD) are keyed by `followUpDate` (index only for two follow-ups with the same date:
  `<date>#<index>`), so a follow-up submission carrying only the newest entry does not overwrite older ones.
  Oncology follow-ups are processed in `followUpDate` order (same date: array order), so the latest report sets a
  therapy's final state and the death date whatever the array order. RD HPO follow-up assessments by `(followUpDate key, phenotype
  index)`. Follow-up therapies by `(therapies[].reference, therapyStartDate)`: a later follow-up updates the same
  Procedure / MedicationStatements. Entries of one follow-up sharing reference and start are different therapies,
  told apart by their substances (ATC code, else name; id part `"+"`-joined sorted substance keys, never the array
  position). The ids of one follow-up's entries are decided together (`onco.followup._FollowUp.therapy_ids`; rule
  in the module docstring, "Therapy identity"): a later entry continues a part (or the earlier single report) only
  when its substance set is *equal* to that part's set; a further split, a merge, a superset or a new substance
  becomes a Procedure of its own (the plain id while it is unused and the entry is the follow-up's only one of that
  therapy, else the substance-keyed id), warned, and the earlier parts keep their state, so one substance's end,
  termination reason or response is never carried over to another. Entries of one follow-up with equal sets and
  equal end/termination/response are one report (warned); equal sets but different attributes are each a part of
  their own keyed by those attributes (warned). One `Tod` Observation per patient;
- prior procedures and prior diagnostics keep their array index (the schema has no identifier; a correction
  that reorders them rewrites them in place). The legacy single object `case.priorDiagnostic` takes the next
  index after `priorDiagnostics[]` (0 without it); RD reads the legacy `case.priorRd` only when `priorRds[]` is
  absent or empty, indexed from 0;
- one NGS report `("ngs-report",)` per oncology submission, plus one per complex-biomarker entry
  `("ngs-report", "complex-biomarker", <entry key>)`; TNM y/r/a symbols `("tnm", "symbol", <y|r|a>)`;
- duplicate source identifiers within one file (variants, CNVs, recommendations and preventive measures in both
  branches; an HPO code repeated within one follow-up) get the array index appended to the id part and a warning;
  lookups (`ctx.ids`) resolve to the first occurrence. Therapies repeated within one follow-up are told apart by
  their substances (above), never by position;
- oncology combination recommendations: the first coded substance's MedicationRequest keeps the recommendation's
  id part, further members add their member index `(id, j)`, so a correction that adds or removes a partner
  rewrites the same resources; the `-kombination` RequestGroup has its own id (another resource type);
- GRZ: genomic study `("submission", "genomic-study")` for the initial submission and its corrections,
  `("submission", "genomic-study", submissionDate)` for a follow-up or addition (section Per-submission resources):
  a correction rewrites the initial study, a follow-up / addition gets its own study whose analyses are that
  submission's `labData`, and the earlier study keeps its links. Specimen, analysis and devices by
  `(donorPseudonym, labDataName)`; relatives by donor pseudonym;
- Provenance `("submission", submissionDate, submissionType, TAN)`, one per submission and stream (KDK and GRZ alike,
  `convert._provenance`): targets every resource of the bundle; `occurredDateTime` / `recorded` = submission date;
  `activity` = v3-DataOperation by submission type (`initial` CREATE, `correction` UPDATE, `followup` / `addition`
  APPEND; `test` no operation code, only the text and the HTEST label); agents: converter (assembler), sender
  (author, `le-id`), clinical data node and genomic data center (custodian), each a reference to the submission
  Organization plus its identifier, KDK and GRZ alike (fix round 4: `builders/submission.submission_organization`
  builds the three core Organizations of `submitterId` / `clinicalDataNodeId` / `genomicDataCenterId` in both
  streams, id parts `(role, value)`, identifier `le-id` / `clinical-data-node` / `genomic-data-center`, name
  `<label> <value>`; an absent or empty id gives none). Earlier submissions keep their Provenance, corrections
  included (audit trail).

### Per-submission resources

A resource that exists once per submission but must be overwritten by a correction is keyed by
`CaseKey.submission_parts()`, the one rule for every such resource (today the GRZ genomic study):

- `initial`, `correction` (and `test`, in its own namespace): no submission part. The initial submission and all
  its corrections share one resource, and a correction rewrites it in place. The schema does not say which
  submission a correction corrects; it is taken to correct the initial one, so a correction of a follow-up or
  addition also rewrites the initial submission's resource (the follow-up's own resource stays as it was);
- `followup`, `addition`: the submission date. Each gets its own resource and earlier ones keep theirs; the same
  submission re-sent rewrites its own. Two follow-ups / additions of one case on the same date share one.

The Provenance is the exception: one per submission, corrections included, so the audit trail keeps every
submission (key above).

## Bundle entries

Every entry: `fullUrl = urn:uuid:<id>`, `resource.id = <id>`, `request = PUT <Type>/<id>`; intra-bundle
references use the `urn:uuid:` form. Re-submitting a case (correction, follow-up, addition) overwrites
the same resources instead of duplicating them; the exceptions are the per-submission resources above (a
follow-up / addition adds its own GRZ genomic study, every submission its own Provenance).

### Submission marker (`meta.source`)

Every resource of a bundle, the Provenance included, carries

    meta.source = urn:genomde2fhir:submission:<submitterId>:<caseId>:<submissionDate>:<submissionType>

(`CaseKey.source`, set by `convert._label_source`; the FML maps write the same value in `DkEntry`).
`<caseId>` is the `localCaseId` as sent (the TAN when there is none), not identity-escaped and without the
`|test` marker: a test submission differs by its type `test`. Each component is percent-encoded on its own
(`identity.source_component`): printable ASCII stays as it is except `%` `:` `|` `#` `?` `/`, and every other
character (blank and other whitespace, control characters, non-ASCII) is written as its UTF-8 bytes, `%` plus two
uppercase hex digits each (`%25` `%3A` `%7C` `%23` `%3F` `%2F` `%20`, `ü` -> `%C3%BC`, NBSP -> `%C2%A0`). So the
value is a FHIR `uri`, `:` separates exactly four components, and different submissions never give the same value.
A HAPI server that stores `meta.source` keeps the whole value (HAPI cuts it at the first `#`, which can no longer
occur), so an exact `_source` search can find it; percent-encode the value once more in the query string as for
any URL parameter (`%` -> `%25`), e.g. `_source=urn:genomde2fhir:submission:260840108:CASE%25207:2026-01-02:correction`
for `localCaseId` `CASE 7` (not exercised here: the local HAPI-2027 store does not store `meta.source`, below). The value names the case and the submission whose content the resource carries; it does not name the
stream (KDK and GRZ resources of a case are told apart by their own Patients). The report lists
`submission_date` / `submission_type` as preserved (`meta-source`).

**Known limitation: corrections that remove items.** Resources that disappear from a correction (a withdrawn
recommendation, a removed variant, relative or sample) are not deleted and stay active on the server: a FHIR
transaction cannot express "delete what is no longer there" without listing it, and the converter sees one
submission at a time (no server-side state, no DELETE entries). They stay identifiable:

- **meta.source (both paths).** After a correction, a resource of the case whose `meta.source` still names an
  earlier `initial` or `correction` submission was not rewritten by the correction. Unless the correction bundle
  contains it (same id; FML: same `resource-key` identifier), it is stale (the earlier submissions' Provenances
  are in this set by design: they are the audit trail). The bundle check is needed because servers
  do not always keep `meta.source` as sent. HAPI 8.4 stores it only when `hapi.fhir.store_meta_source_information` is
  not `NONE` (the local HAPI-2027 test store has it off and discards `meta.source`). It also treats a re-sent resource
  whose content is unchanged as "no changes detected": that resource keeps the earlier `meta.source` (and its
  `versionId` / `lastUpdated`). Search each earlier submission's value with `_source` (above), or read
  `meta.source` from the fetched resources of the case: the Patient compartments of the case's Patients (the
  index Patient and, for GRZ, each relative's own Patient) do not reach the GRZ sequencing Devices, which reference
  no Patient; reach those through the analysis Procedures or the Provenance targets.
  The rule misses a resource whose content a follow-up or addition rewrote (its `meta.source` then names that
  submission) when a later correction drops it; the Provenance procedure below finds it.
- **Provenance targets (Python path).** Every submission's Provenance survives and lists all resources that
  submission emitted. The stale resources of a case are therefore

      targets(Provenance of an earlier submission) - targets(Provenance of the correction)

  (e.g. `Provenance?target=Patient/<id>` for the case, ordered by `recorded`; corrections on the same day as the
  earlier submission are told apart by `activity` UPDATE). The FML maps emit no Provenance.

A downstream process then decides whether to delete the stale resources or set `entered-in-error`. The conversion
report gives `submission_type`, `submission_date`, `test` and `case_key_fallback` per file (summary:
`submission_types`, `test_submissions`, `case_key_tan_fallback`).

## Patients per stream

The KDK Patient carries demographics; a GRZ submission only knows pseudonym, gender and relation. To never
erase KDK demographics with a sparse GRZ update, the GRZ stream writes its own Patient per donor
(stream `grz`); the index donor's GRZ Patient carries the same `local-case-id` identifier as the KDK
Patient, so both are found by `Patient?identifier=https://genomde.de/fhir/sid/local-case-id|<submitterId>|<localCaseId>`.
Relatives are separate Patients (stream `grz`, keyed by donor pseudonym); the index Patient carries one MolGen `familienanamnese` per relative with the core `familymemberhistory-patient-record` extension pointing to the relative's Patient. `Patient.link` is not used (it asserts the same person).

## Identifier systems

| System | Value |
|:--|:--|
| `https://genomde.de/fhir/sid/local-case-id` | `<submitterId>|<caseKey>`, i.e. `<submitterId>|<localCaseId>` (test submissions `...|test`; assigner = LE id) |
| `https://genomde.de/fhir/sid/tan-c` | VNk |
| `https://genomde.de/fhir/sid/tan-g` | VNg |
| `https://genomde.de/fhir/sid/donor-pseudonym` | `<submitterId>|<caseKey>|<donorPseudonym>` (case-scoped: the schema's literal `index` pseudonym recurs in every case) |
| `https://genomde.de/fhir/sid/le-id` | submitter (Leistungserbringer) id |
| `https://genomde.de/fhir/sid/genomic-data-center`, `.../clinical-data-node` | GRZ / KDK ids |
| `https://genomde.de/fhir/sid/molecular-finding-id` | `<submitterId>|<caseKey>|<KDK id>` — variants, CNVs, SVs, fusions, biomarkers (oncology and RD) |
| `https://genomde.de/fhir/sid/kdk-object-id` | `<submitterId>|<caseKey>|<KDK id>` — therapy/study recommendations and preventive measures (both branches); also the identifier of logical references to objects sent in an earlier submission (e.g. a follow-up therapy citing an earlier recommendation). Oncology combinations: every member MedicationRequest also carries `<submitterId>|<caseKey>|<KDK id>:<member index>` (the first member both values), the `-kombination` RequestGroup `<KDK id>` |
| `https://genomde.de/fhir/sid/grz-lab-data-name` | `<submitterId>|<caseKey>|<donorPseudonym>|<labDataName>` (case-scoped) |
| `https://genomde.de/fhir/sid/grz-sample-barcode` | `<submitterId>|<sample barcode>` (`Specimen.accessionIdentifier`; test submissions `...|test`) |
| `https://genomde.de/fhir/sid/resource-key` | base64url(`<stream>:<submitterId>:<caseKey>:<role>[:<local>]`), stream `kdk` / `grz`, case key with `|test` for test submissions — FML path only: conditional PUT key (FML cannot compute uuid5); on a Patient the identifier has type v2-0203 `RI` |

Case-scoped values are built by one helper (`CaseKey.scoped`, used by `builders/common.scoped_id`; sender-scoped
values without a case by `CaseKey.sender_scoped`); every component is escaped like in resource ids, and the case
key is the one of section Keys, so a logical reference from a later submission of the same case finds the earlier
object. In FHIR token searches a literal `|` inside a value must itself be escaped (`\|`).
Study register ids use the MII NamingSystems (`modul-mtb/sid/nct`, `modul-studie/sid/drks`,
`modul-studie/sid/eudract`); register `other` keeps the id without a system.

The `https://genomde.de/fhir/` namespace is a placeholder owned by this project until the MV-GenomSeq
specification assigns official systems; it is defined once in `genomde2fhir/systems.py`.

## Multiple files

`genomde2fhir convert` writes one transaction Bundle per input. `--single-bundle FILE` merges all inputs
into one Bundle in submission order: submission date, then type (`initial` < `followup` / `addition` <
`correction`; other types such as `test` rank with `followup`), then file path. An entry with the same id is
replaced, so the later submission wins; `--ingest` posts the bundles in the same order. Every submission keeps its
own Provenance (its id includes date, type and TAN).
