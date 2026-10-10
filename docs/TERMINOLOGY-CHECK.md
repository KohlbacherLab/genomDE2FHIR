# Terminology / coded-value check of the genomDE→MII mapping

Automated re-run of the NUM-OMICS review via `https://tx.fhir.org/r4` (LOINC+SNOMED $lookup/$expand). Checked **67** distinct coded values.

- INVALID (code does not exist): **0**
- MISMATCH (display unrelated to the mapped concept): **0**
- OK (exists, display consistent): **67**

## ❌ INVALID codes (do not exist)

| system | code | cited for |
|---|---|---|

## ⚠️ MISMATCH — official display unrelated to the mapped field

| code | official display | cited for (suspect) |
|---|---|---|

## 🔎 Answer-code roster (per field — eyeball for a rogue value)

Answer codes exist in LOINC (else marked INVALID above); their *display* is shown next to the field so a wrong-but-valid code stands out (e.g. an anatomy term among inheritance modes):

- **case.diagnosisOd.ecogPerformanceStatusScore** — `LA9622-7`=Fully active, able to carry on all pre-disease performance without restriction; `LA9626-8`=Completely disabled. Cannot carry on any selfcare. Totally confined to bed or chair
- **case.diagnosisRd.diagnosisGmfcs** — `LA15150-8`=Can stand on their own and only walks using a walking aid (such as a walker, rollator, crutches, canes, etc.); `LA15151-6`=Can walk on their own without using walking aids, but needs to hold the handrail when going up or down stairs; `LA16552-4`=Can walk on their own without using walking aids, and can go up or down stairs without needing to hold the handrail.; `LA16556-5`=Can sit on their own but does not stand or walk without significant support and adult supervision.; `LA16558-1`=Has difficulty sitting on their own and controlling their head and body posture in most positions; `LL1594-2`=PhenX13_50_motor function child 6-12Y
- **case.diagnosisRd.phenotypes[].code** — `LA9633-4`=Present
- **case.diagnosisRd.phenotypes[].display** — `LA9633-4`=Present
- **case.diagnosisRd.phenotypes[].system** — `LA9633-4`=Present
- **case.diagnosisRd.phenotypes[].text** — `LA9633-4`=Present
- **case.diagnosisRd.phenotypes[].version** — `LA9633-4`=Present
- **donors[].labData[].sequenceData.referenceGenome** — `LA14029-5`=GRCh37; `LA26806-2`=GRCh38
- **donors[].labData[].sequenceSubtype** — `LA6683-2`=Germline; `LA6684-0`=Somatic; `LL378-1`=MG_2_Genetic variant source
- **followUp.followUpOds[].ecogPerformanceStatusScore** — `LA9622-7`=Fully active, able to carry on all pre-disease performance without restriction; `LA9626-8`=Completely disabled. Cannot carry on any selfcare. Totally confined to bed or chair
- **followUp.followUpOds[].phenotypes[].change** — `LA9633-4`=Present; `LA9634-2`=Absent
- **followUp.followUpRds[].gmfcs** — `LA15150-8`=Can stand on their own and only walks using a walking aid (such as a walker, rollator, crutches, canes, etc.); `LA15151-6`=Can walk on their own without using walking aids, but needs to hold the handrail when going up or down stairs; `LA16552-4`=Can walk on their own without using walking aids, and can go up or down stairs without needing to hold the handrail.; `LA16556-5`=Can sit on their own but does not stand or walk without significant support and adult supervision.; `LA16558-1`=Has difficulty sitting on their own and controlling their head and body posture in most positions; `LL1594-2`=PhenX13_50_motor function child 6-12Y
- **followUp.followUpRds[].phenotypes[].change** — `LA9633-4`=Present; `LA9634-2`=Absent
- **followUp.followUpRds[].phenotypes[].code** — `LA9633-4`=Present; `LA9634-2`=Absent
- **followUp.followUpRds[].phenotypes[].display** — `LA9633-4`=Present; `LA9634-2`=Absent
- **followUp.followUpRds[].phenotypes[].system** — `LA9633-4`=Present; `LA9634-2`=Absent
- **followUp.followUpRds[].phenotypes[].text** — `LA9633-4`=Present; `LA9634-2`=Absent
- **followUp.followUpRds[].phenotypes[].version** — `LA9633-4`=Present; `LA9634-2`=Absent
- **molecular.copyNumberVariants[].acmgClass** — `LA26332-9`=Likely pathogenic; `LA26333-7`=Uncertain significance; `LA26334-5`=Likely benign; `LA6668-3`=Pathogenic; `LA6675-8`=Benign; `LL4034-6`=ACMG_Clinical significance of genetic variation
- **molecular.copyNumberVariants[].chromosome** — `LL2938-0`=List of human chromosomes
- **molecular.copyNumberVariants[].endPosition** — `LA26806-2`=GRCh38
- **molecular.copyNumberVariants[].genomicSource** — `LA6683-2`=Germline; `LA6684-0`=Somatic; `LL378-1`=MG_2_Genetic variant source
- **molecular.copyNumberVariants[].modeOfInheritance** — `LA24789-2`=Mitochondrial; `LA24947-6`=X-linked; `LL3731-8`=[NEI] Inheritance pattern from family history
- **molecular.copyNumberVariants[].segregationAnalysis** — `LA26320-4`=Maternal; `LA26321-2`=Paternal; `LA26807-0`=De novo; `LL5489-1`=Origin of Genetic Variance
- **molecular.copyNumberVariants[].startPosition** — `LA26806-2`=GRCh38
- **molecular.copyNumberVariants[].zygosity** — `LA26217-2`=Compound heterozygous; `LA6703-8`=Heteroplasmic; `LA6704-6`=Homoplasmic; `LA6705-3`=Homozygous; `LA6706-1`=Heterozygous; `LA6707-9`=Hemizygous; `LL381-5`=MG_5_Genetic variant allelic state; `LL3999-1`=Complex variant types
- **molecular.expressionVariants[].expressionType** — `LA9633-4`=Present; `LA9634-2`=Absent; `LL1971-2`=Variant Assess
- **molecular.smallVariants[].acmgClass** — `LA26332-9`=Likely pathogenic; `LA26333-7`=Uncertain significance; `LA26334-5`=Likely benign; `LA6668-3`=Pathogenic; `LA6675-8`=Benign; `LL4034-6`=ACMG_Clinical significance of genetic variation
- **molecular.smallVariants[].chromosome** — `LL2938-0`=List of human chromosomes
- **molecular.smallVariants[].endPosition** — `LA26806-2`=GRCh38; `LA30102-0`=1-based character counting
- **molecular.smallVariants[].genomicSource** — `LA6683-2`=Germline; `LA6684-0`=Somatic; `LL378-1`=MG_2_Genetic variant source
- **molecular.smallVariants[].modeOfInheritance** — `LA24789-2`=Mitochondrial; `LA24947-6`=X-linked; `LL3731-8`=[NEI] Inheritance pattern from family history
- **molecular.smallVariants[].segregationAnalysis** — `LA26320-4`=Maternal; `LA26321-2`=Paternal; `LA26807-0`=De novo; `LL5489-1`=Origin of Genetic Variance
- **molecular.smallVariants[].startPosition** — `LA26806-2`=GRCh38; `LA30102-0`=1-based character counting
- **molecular.smallVariants[].zygosity** — `LA26217-2`=Compound heterozygous; `LA6703-8`=Heteroplasmic; `LA6704-6`=Homoplasmic; `LA6705-3`=Homozygous; `LA6706-1`=Heterozygous; `LA6707-9`=Hemizygous; `LL381-5`=MG_5_Genetic variant allelic state; `LL3999-1`=Complex variant types
- **molecular.structuralVariants[].acmgClass** — `LA26332-9`=Likely pathogenic; `LA26333-7`=Uncertain significance; `LA26334-5`=Likely benign; `LA6668-3`=Pathogenic; `LA6675-8`=Benign; `LL4034-6`=ACMG_Clinical significance of genetic variation
- **molecular.structuralVariants[].genomicSource** — `LA6683-2`=Germline; `LA6684-0`=Somatic; `LL378-1`=MG_2_Genetic variant source
- **molecular.structuralVariants[].modeOfInheritance** — `LA24789-2`=Mitochondrial; `LA24947-6`=X-linked; `LL3731-8`=[NEI] Inheritance pattern from family history
- **molecular.structuralVariants[].segregationAnalysis** — `LA26320-4`=Maternal; `LA26321-2`=Paternal; `LA26807-0`=De novo; `LL5489-1`=Origin of Genetic Variance
- **molecular.structuralVariants[].zygosity** — `LA26217-2`=Compound heterozygous; `LA6703-8`=Heteroplasmic; `LA6704-6`=Homoplasmic; `LA6705-3`=Homozygous; `LA6706-1`=Heterozygous; `LA6707-9`=Hemizygous; `LL381-5`=MG_5_Genetic variant allelic state; `LL3999-1`=Complex variant types

## ✅ Verified consistent (67)

<details><summary>expand</summary>

| code | display |
|---|---|
| `107286-7` | Homologous recombination deficiency status analysis [Presence] in Tissue by Molecular genetics method |
| `33732-9` | Histology grade [Identifier] in Cancer specimen |
| `48000-4` | Chromosome [Identifier] in Blood or Tissue by Molecular genetics method |
| `48002-0` | Genomic source class [Type] |
| `48004-6` | DNA change (c.HGVS) |
| `48005-3` | Amino acid change (pHGVS) |
| `48018-6` | Gene studied [ID] |
| `48019-4` | DNA change type |
| `51958-7` | Transcript reference sequence [ID] |
| `53034-5` | Allelic state |
| `53037-8` | Genetic variation clinical significance [Imp] |
| `62374-4` | Human reference sequence assembly version |
| `67162-8` | Patient Disposition |
| `69547-8` | Genomic ref allele [ID] |
| `69551-0` | Genomic alt allele [ID] |
| `81252-9` | Discrete genetic variant |
| `81254-5` | Genomic allele start-end |
| `81290-9` | Genomic DNA change (gHGVS) |
| `81291-7` | Variant ISCN |
| `82155-3` | Genomic structural variant copy number |
| `89262-0` | ECOG Performance Status [Interpretation] |
| `94076-7` | Mutations/Megabase [# Ratio] in Tumor |
| `LA14029-5` | GRCh37 |
| `LA15150-8` | Can stand on their own and only walks using a walking aid (such as a walker, rollator, crutches, canes, etc.) |
| `LA15151-6` | Can walk on their own without using walking aids, but needs to hold the handrail when going up or down stairs |
| `LA16552-4` | Can walk on their own without using walking aids, and can go up or down stairs without needing to hold the handrail. |
| `LA16556-5` | Can sit on their own but does not stand or walk without significant support and adult supervision. |
| `LA16558-1` | Has difficulty sitting on their own and controlling their head and body posture in most positions |
| `LA24789-2` | Mitochondrial |
| `LA24947-6` | X-linked |
| `LA26217-2` | Compound heterozygous |
| `LA26320-4` | Maternal |
| `LA26321-2` | Paternal |
| `LA26332-9` | Likely pathogenic |
| `LA26333-7` | Uncertain significance |
| `LA26334-5` | Likely benign |
| `LA26806-2` | GRCh38 |
| `LA26807-0` | De novo |
| `LA30102-0` | 1-based character counting |
| `LA6668-3` | Pathogenic |
| `LA6675-8` | Benign |
| `LA6683-2` | Germline |
| `LA6684-0` | Somatic |
| `LA6703-8` | Heteroplasmic |
| `LA6704-6` | Homoplasmic |
| `LA6705-3` | Homozygous |
| `LA6706-1` | Heterozygous |
| `LA6707-9` | Hemizygous |
| `LA9622-7` | Fully active, able to carry on all pre-disease performance without restriction |
| `LA9626-8` | Completely disabled. Cannot carry on any selfcare. Totally confined to bed or chair |
| `LA9633-4` | Present |
| `LA9634-2` | Absent |
| `LL1594-2` | PhenX13_50_motor function child 6-12Y |
| `LL1971-2` | Variant Assess |
| `LL2938-0` | List of human chromosomes |
| `LL3731-8` | [NEI] Inheritance pattern from family history |
| `LL378-1` | MG_2_Genetic variant source |
| `LL381-5` | MG_5_Genetic variant allelic state |
| `LL3999-1` | Complex variant types |
| `LL4034-6` | ACMG_Clinical significance of genetic variation |
| `LL5489-1` | Origin of Genetic Variance |
| `396432002` | Status of regression of tumour |
| `399390009` | TNM stage grouping |
| `399537006` | Clinical TNM stage grouping |
| `399588009` | Pathologic TNM stage grouping |
| `423740007` | ECOG performance status |
| `707621005` | Gross motor function classification system for cerebral palsy |

</details>

## DK enum values with no clinical code → need STRUCTURAL mapping

Catch-all values (`unknown/other/none/notAvailable/…`) have no equivalent target concept; map them structurally, not to an invented code:

| policy | genomDE value | FHIR target |
|---|---|---|
| absence-of-value | `unknown`, `notAvailable` | `dataAbsentReason` = unknown / asked-unknown (Observation) or nullFlavor `UNK`; omit `value[x]` |
| free / uncoded | `other` | `.text` only, or a genomDE local CodeSystem concept; never force a wrong standard code |
| genuine negative | `none` | a real code where one exists (e.g. SNOMED 'none'/260413007) else dataAbsentReason |
| partial admin | `yesButStudyIsUnknown` | keep the boolean/flag; reference resource absent → `.display` note |

Fields carrying such values (23):

| field | catch-all value(s) |
|---|---|
| `diagnosticResult` | other |
| `ecogPerformanceStatusScore` | unknown |
| `ecogPerformanceStatusScore` | unknown |
| `enrichmentKitManufacturer` | other, unknown, none |
| `fragmentationMethod` | none, other, unknown |
| `gender` | other, unknown |
| `gender` | other, unknown |
| `genomicTestType` | other, none |
| `hospitalizationDuration` | none, unknown |
| `hospitalizationPeriods` | none, unknown |
| `libraryType` | other, unknown |
| `libraryType` | none |
| `libraryType` | none |
| `method` | other, unknown |
| `register` | other, yesButStudyIsUnknown |
| `register` | other, yesButStudyIsUnknown |
| `relation` | other |
| `sampleConservation` | other, unknown |
| `sequenceSubtype` | other, unknown |
| `sequencingLayout` | other |
| `strategy` | other |
| `type` | other, none |
| `type` | unknown |

## Not checked here (not on tx.fhir.org)

LOINC + SNOMED are verified above. These systems need a German/OBO terminology server (BfArM TermServ, OLS) — verify separately: **ICD-10-GM, ICD-O-3, OPS, ATC, Orpha, ORPHA, Alpha-ID, AlphaID, HPO, HGNC, SO:, UICC, NCIt**.
