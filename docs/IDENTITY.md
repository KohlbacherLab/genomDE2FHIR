# Identity, idempotency and linkage (genomde2fhir)

## Keys

| Stream | Case key | Stable across submissions? |
|:--|:--|:--|
| KDK (oncology, rare disease) | `metaData.submission.submitterId` + `metaData.localCaseId` | yes — the schema defines `localCaseId` as the sender's id for all submissions of a case |
| KDK without `localCaseId` (optional in the schema) | `submitterId` + `metaData.tanC` | no — TAN-C is per submission; follow-ups then create new resources (reported as a warning) |
| GRZ | `submission.submitterId` + `submission.localCaseId` (required) | yes |
| GRZ donor | case key + `donors[].donorPseudonym` | yes |

TAN-C (VNk) and TAN-G (VNg) are transaction numbers for reimbursement; they are recorded as identifiers
(type `PSEUDED`), never used to link resources across streams.

## Resource ids

`id = uuid5(NS, "<stream>|<submitterId>|<caseKey>|<ResourceType>|<local parts>")`
(`NS = uuid5(NAMESPACE_URL, "https://genomde.de/fhir/genomde2fhir")`, `genomde2fhir.identity.rid`).
Local parts are source identifiers where the schema has them (variant `id`, recommendation `id`, therapy
`id`, donor pseudonym, lab-data `labDataName`) and otherwise the semantic role plus the array index
(e.g. `("followup", 2, "ecog")`). Array positions are only used where the schema has no identifier, and never where a later submission may
carry a subset of the array:

- follow-ups (oncology, RD) are keyed by `followUpDate` (index only for two follow-ups with the same date), so a
  follow-up submission carrying only the newest entry does not overwrite older ones; follow-up therapies by
  `(therapies[].reference, therapyStartDate)` (a later follow-up updates the same Procedure/MedicationStatement);
  one `Tod` Observation per patient;
- prior procedures and prior diagnostics keep their array index (the schema has no identifier; a correction
  that reorders them rewrites them in place);
- duplicate source identifiers within one file (variants, CNVs, recommendations) get the array index appended
  to the id part and a warning; lookups (`ctx.ids`) resolve to the first occurrence;
- GRZ: genomic study `("submission", "genomic-study")` once per submission; Specimen, analysis and devices by
  `(donorPseudonym, labDataName)`; relatives by donor pseudonym.

## Bundle entries

Every entry: `fullUrl = urn:uuid:<id>`, `resource.id = <id>`, `request = PUT <Type>/<id>`; intra-bundle
references use the `urn:uuid:` form. Re-submitting a case (correction, follow-up, addition) overwrites
the same resources instead of duplicating them. Resources that disappear from a correction are not
deleted (FHIR transactions cannot express "delete what is no longer there" without listing it); the
conversion report lists the submission type so downstream processes can decide.

## Patients per stream

The KDK Patient carries demographics; a GRZ submission only knows pseudonym, gender and relation. To never
erase KDK demographics with a sparse GRZ update, the GRZ stream writes its own Patient per donor
(stream `grz`); the index donor's GRZ Patient carries the same `local-case-id` identifier as the KDK
Patient, so both are found by `Patient?identifier=https://genomde.de/fhir/sid/local-case-id|<submitterId>|<localCaseId>`.
Relatives are separate Patients (stream `grz`, keyed by donor pseudonym); the index Patient carries one MolGen `familienanamnese` per relative with the core `familymemberhistory-patient-record` extension pointing to the relative's Patient. `Patient.link` is not used (it asserts the same person).

## Identifier systems

| System | Value |
|:--|:--|
| `https://genomde.de/fhir/sid/local-case-id` | `<submitterId>|<localCaseId>` (assigner = LE id) |
| `https://genomde.de/fhir/sid/tan-c` | VNk |
| `https://genomde.de/fhir/sid/tan-g` | VNg |
| `https://genomde.de/fhir/sid/donor-pseudonym` | `<submitterId>|<donorPseudonym>` |
| `https://genomde.de/fhir/sid/le-id` | submitter (Leistungserbringer) id |
| `https://genomde.de/fhir/sid/genomic-data-center`, `.../clinical-data-node` | GRZ / KDK ids |
| `https://genomde.de/fhir/sid/molecular-finding-id` | `<submitterId>|<caseKey>|<KDK id>` — variants, CNVs, SVs, fusions, biomarkers (oncology and RD) |
| `https://genomde.de/fhir/sid/kdk-object-id` | `<submitterId>|<caseKey>|<KDK id>` — therapy/study recommendations and preventive measures (both branches); also the identifier of logical references to objects sent in an earlier submission (e.g. a follow-up therapy citing an earlier recommendation) |
| `https://genomde.de/fhir/sid/grz-lab-data-name` | `<submitterId>|<donorPseudonym>|<labDataName>` |
| `https://genomde.de/fhir/sid/grz-sample-barcode` | `<submitterId>|<sample barcode>` (`Specimen.accessionIdentifier`) |
| `https://genomde.de/fhir/sid/resource-key` | `<submitterId>:<caseKey>:<role>[:<local>]` — FML path only: conditional PUT key (FML cannot compute uuid5) |

Sender-scoped values are built by one helper (`builders/common.scoped_id`); the case key is the one of
section Keys, so a logical reference from a later submission of the same case finds the earlier object.
Study register ids use the MII NamingSystems (`modul-mtb/sid/nct`, `modul-studie/sid/drks`,
`modul-studie/sid/eudract`); register `other` keeps the id without a system.

The `https://genomde.de/fhir/` namespace is a placeholder owned by this project until the MV-GenomSeq
specification assigns official systems; it is defined once in `genomde2fhir/systems.py`.

## Multiple files

`genomde2fhir convert` writes one transaction Bundle per input. `--single-bundle FILE` merges all inputs
into one Bundle; entries with the same id are replaced in input order (later submissions win).
