# Terminology capability matrix (validation of genomde2fhir output)

_Probed 2026-10-09: one known code per system with `CodeSystem/$validate-code`; package contents from the
2027 ballot stack in `infra/matchbox-2027/package-cache`._

| Code system | Used for | tx.fhir.org | In the 2027 packages | matchbox-2027 verdict for a binding |
|:--|:--|:--|:--|:--|
| SNOMED CT (`http://snomed.info/sct`) | category 55342001, procedures, specimen types, GMFCS code | **validates** | — | checked |
| LOINC | observation codes, LA answers (ECOG, LL1971-2, LL4034-6, LL5489-1, LL1594-2) | **validates** | — | checked |
| UCUM | quantities | **validates** | — | checked |
| ICD-O-3 (`http://terminology.hl7.org/CodeSystem/icd-o-3`) | morphology, topography (required-bound in 2027) | **validates** | stub (`not-present`) | checked |
| HGVS (`http://varnomen.hgvs.org`) | c./g./p. notation | **validates** (syntax service) | — | checked |
| NCIt | ploidy C18303 | **validates** | — | checked |
| UICC TNM (`https://www.uicc.org/resources/tnm`) | TNM category values | no | **complete CodeSystem (138 codes) in onkologie 2027** | checked locally |
| ICD-10-GM, OPS, ATC, Alpha-ID (`http://fhir.de/CodeSystem/bfarm/*`) | diagnoses, procedures, substances | no | stub (`not-present`, basisprofil) | **unchecked** (INCONCLUSIVE) |
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
  always content errors (`genomde2fhir/validate.py`).
- Corpus-scale validation of the German systems needs a local terminology server with licensed content
  (MII validator's Blaze setup or a local Ontoserver); until then the E2E report counts them separately.
