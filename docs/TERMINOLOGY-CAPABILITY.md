# Terminology capability matrix (validation of genomde2fhir output)

_Probed 2026-10-09: one known code per system with `CodeSystem/$validate-code`; package contents from the
2027 ballot stack in `infra/matchbox-2027/package-cache`. ICD-O-3 and the BfArM systems re-probed on 2026-10-09
(fix round), together with the matchbox messages of the corpus validation run._

| Code system | Used for | tx.fhir.org | In the 2027 packages | matchbox-2027 verdict for a binding |
|:--|:--|:--|:--|:--|
| SNOMED CT (`http://snomed.info/sct`) | category 55342001, procedures, specimen types, GMFCS code | **validates** | — | checked |
| LOINC | observation codes, LA answers (ECOG, LL1971-2, LL4034-6, LL5489-1, LL1594-2) | **validates** | — | checked |
| UCUM | quantities | **validates** | — | checked |
| ICD-O-3 (`http://terminology.hl7.org/CodeSystem/icd-o-3`) | morphology, topography (required-bound in 2027) | edition **2000 only** (`Valid versions: 2000`); `$validate-code` in 2000 even accepts codes that do not exist (`XYZ`, `C99.9` → true, while `$lookup` of `C99.9` fails) | stub (`not-present`) | the MII value sets pin 2014 / 2019, so a 2014/2019 coding is **unchecked** (INCONCLUSIVE) whether the code is valid or not; a coding in edition 2000, or with a wrong edition, is checked for the edition only: `version '2019' in the ValueSet include is different to the one in the value ('2000')` (content), the signal of a wrong edition. An unknown code in edition 2000 is only a warning on matchbox-2027 (`Unknown Code ... version 2000 - note that the code system is labeled as a fragment`), so it never counts |
| HGVS (`http://varnomen.hgvs.org`) | c./g./p. notation | **validates** (syntax service) | — | checked |
| NCIt | ploidy C18303 | **validates** | — | checked |
| UICC TNM (`https://www.uicc.org/resources/tnm`) | TNM category values | no | **complete CodeSystem (138 codes) in onkologie 2027** | checked locally |
| ICD-10-GM (`http://fhir.de/CodeSystem/bfarm/icd-10-gm`) | diagnoses | no (`$validate-code`: definition not found) | stub (`not-present`, basisprofil) | unchecked binding (the value-set check is only a warning, `Unable to check whether the code is in the value set …`); unknown codes are reported (`Unknown code '…' in … icd-10-gm version '2025'/'2026'` in the corpus run): content, or source when the code is an input value |
| OPS, ATC, Alpha-ID (`http://fhir.de/CodeSystem/bfarm/*`) | procedures, substances, diagnoses | no (`$validate-code`: definition not found) | stub (`not-present`, basisprofil) | **unchecked** (INCONCLUSIVE) |
| Orphanet (`http://www.orpha.net`) | rare-disease diagnoses | no | no | **unchecked** |
| HPO (`http://human-phenotype-ontology.org`) | phenotypes, mode of inheritance | no | stub | **unchecked** |
| HGNC (`http://www.genenames.org`) | genes | no | stub | **unchecked** |
| Sequence Ontology (`http://www.sequenceontology.org`) | variant types, consequences | no | stub | **unchecked** |
| ClinGen ACMG criteria | ACMG evidence codes | no | no | **unchecked** |
| local `https://genomde.de/fhir/CodeSystem/mvgs-*` | genomDE enums without a standard code | no | **complete, in de.genomde.mvgs** | checked locally |

BfArM terminology server (`https://terminologieserver.bfarm.de/fhir`): **not reachable** from the
development host (DNS/connection failure; previously observed as authentication-gated). The MII SU-TermServ
Ontoserver serves all German systems but requires an mTLS client certificate (not yet requested) and its
policy forbids production ETL validation; it may be used for development probes with few, non-personal resources.

Consequences:
- `unchecked` issues make a bundle **INCONCLUSIVE**, never PASS; definitive "unknown code" messages are
  content errors, or source (verdict DATA-QUALITY) when the code is exactly the value of an input field
  (`genomde2fhir/validate.py`).
- Validation that could not run (matchbox unreachable, HTTP error, empty or non-OperationOutcome response, unknown
  profile) gives verdict **ERROR**, never PASS.
- A value-set error (`None of the codings provided are in the value set`) on a coding whose system the tx server
  cannot check is *unchecked* only when the value set admits that system (its `compose.include[].system`, read
  from matchbox `ValueSet?url=` and followed through included value sets). A coding of a system the value set does
  not include is no member whatever the system: content, never source.
- HGVS the converter composes (`<transcript>[(<gene>)]:<c./p. notation>`, REPRESENTATIONS #43) counts as source
  only when every part is verbatim an input value: the transcript code (or the accession and its version, each an
  input value), the gene symbol and the c./p. notation. Otherwise an unknown HGVS code is content.
- Known limitation (review finding R17): the source rule looks at the value only, so a raw KDK enum value that
  reaches a SNOMED or LOINC coding because a ConceptMap entry is missing (a converter defect) is also classed
  source (DATA-QUALITY), not content.
- ICD-O-3 is effectively not checked at the code level anywhere: the 2014/2019 codings the converter emits are
  unchecked, and tx.fhir.org's edition 2000 accepts any code string.
- Corpus-scale validation of the German systems needs a local terminology server with licensed content
  (MII validator's Blaze setup or a local Ontoserver); until then the E2E report counts them separately.
