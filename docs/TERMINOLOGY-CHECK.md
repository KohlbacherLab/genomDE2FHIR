# Terminology / coded-value check of the genomDE→MII mapping

Automated re-run of the NUM-OMICS review via `https://tx.fhir.org/r4` (LOINC+SNOMED $lookup/$expand). Checked **45** distinct coded values.

- INVALID (code does not exist): **0**
- MISMATCH (display unrelated to the mapped concept): **0**
- OK (exists, display consistent): **45**

## ❌ INVALID codes (do not exist)

| system | code | cited for |
|---|---|---|

## ⚠️ MISMATCH — official display unrelated to the mapped field

| code | official display | cited for (suspect) |
|---|---|---|

## 🔎 Answer-code roster (per field — eyeball for a rogue value)

Answer codes exist in LOINC (else marked INVALID above); their *display* is shown next to the field so a wrong-but-valid code stands out (e.g. an anatomy term among inheritance modes):

- **case.diagnosisRd.diagnosisGmfcs** — `LA15150-8`=Can stand on their own and only walks using a walking aid (such as a walker, rollator, crutches, canes, etc.); `LA15151-6`=Can walk on their own without using walking aids, but needs to hold the handrail when going up or down stairs; `LA16552-4`=Can walk on their own without using walking aids, and can go up or down stairs without needing to hold the handrail.; `LL1594-2`=PhenX13_50_motor function child 6-12Y
- **donors[].labData[].sequenceData.referenceGenome** — `LA14029-5`=GRCh37; `LA26806-2`=GRCh38
- **followUp.followUpRds[].gmfcs** — `LA15150-8`=Can stand on their own and only walks using a walking aid (such as a walker, rollator, crutches, canes, etc.); `LA15151-6`=Can walk on their own without using walking aids, but needs to hold the handrail when going up or down stairs; `LA16552-4`=Can walk on their own without using walking aids, and can go up or down stairs without needing to hold the handrail.; `LL1594-2`=PhenX13_50_motor function child 6-12Y
- **molecular.copyNumberVariants[].acmgClass** — `LA6668-3`=Pathogenic; `LA6675-8`=Benign; `LL4034-6`=ACMG_Clinical significance of genetic variation
- **molecular.copyNumberVariants[].cnvType** — `LA14033-7`=Copy number gain; `LA14034-5`=Copy number loss
- **molecular.copyNumberVariants[].modeOfInheritance** — `LA24640-7`=Autosomal dominant; `LA24641-5`=Autosomal recessive; `LA24789-2`=Mitochondrial; `LA24947-6`=X-linked; `LL3731-8`=[NEI] Inheritance pattern from family history
- **molecular.copyNumberVariants[].zygosity** — `LA6705-3`=Homozygous; `LL381-5`=MG_5_Genetic variant allelic state
- **molecular.smallVariants[].acmgClass** — `LA6668-3`=Pathogenic; `LA6675-8`=Benign; `LL4034-6`=ACMG_Clinical significance of genetic variation
- **molecular.smallVariants[].genomicSource** — `LA6683-2`=Germline; `LA6684-0`=Somatic
- **molecular.smallVariants[].modeOfInheritance** — `LA24640-7`=Autosomal dominant; `LA24641-5`=Autosomal recessive; `LA24789-2`=Mitochondrial; `LA24947-6`=X-linked; `LL3731-8`=[NEI] Inheritance pattern from family history
- **molecular.smallVariants[].zygosity** — `LA6705-3`=Homozygous; `LL381-5`=MG_5_Genetic variant allelic state
- **molecular.structuralVariants[].acmgClass** — `LA6668-3`=Pathogenic; `LA6675-8`=Benign; `LL4034-6`=ACMG_Clinical significance of genetic variation
- **molecular.structuralVariants[].modeOfInheritance** — `LA24640-7`=Autosomal dominant; `LA24641-5`=Autosomal recessive; `LA24789-2`=Mitochondrial; `LA24947-6`=X-linked; `LL3731-8`=[NEI] Inheritance pattern from family history
- **molecular.structuralVariants[].zygosity** — `LA6705-3`=Homozygous; `LL381-5`=MG_5_Genetic variant allelic state

## ✅ Verified consistent (45)

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
| `51958-7` | Transcript reference sequence [ID] |
| `53034-5` | Allelic state |
| `53037-8` | Genetic variation clinical significance [Imp] |
| `62374-4` | Human reference sequence assembly version |
| `62781-0` | PhenX - gross motor function - 4-6Y protocol 131202 |
| `62782-8` | PhenX - gross motor function - 6-12 years protocol 131203 |
| `67162-8` | Patient Disposition |
| `69547-8` | Genomic ref allele [ID] |
| `69551-0` | Genomic alt allele [ID] |
| `79742-3` | Inheritance pattern based on family history |
| `81254-5` | Genomic allele start-end |
| `81290-9` | Genomic DNA change (gHGVS) |
| `81291-7` | Variant ISCN |
| `82155-3` | Genomic structural variant copy number |
| `94076-7` | Mutations/Megabase [# Ratio] in Tumor |
| `LA14029-5` | GRCh37 |
| `LA14033-7` | Copy number gain |
| `LA14034-5` | Copy number loss |
| `LA15150-8` | Can stand on their own and only walks using a walking aid (such as a walker, rollator, crutches, canes, etc.) |
| `LA15151-6` | Can walk on their own without using walking aids, but needs to hold the handrail when going up or down stairs |
| `LA16552-4` | Can walk on their own without using walking aids, and can go up or down stairs without needing to hold the handrail. |
| `LA24640-7` | Autosomal dominant |
| `LA24641-5` | Autosomal recessive |
| `LA24789-2` | Mitochondrial |
| `LA24947-6` | X-linked |
| `LA26806-2` | GRCh38 |
| `LA6668-3` | Pathogenic |
| `LA6675-8` | Benign |
| `LA6683-2` | Germline |
| `LA6684-0` | Somatic |
| `LA6705-3` | Homozygous |
| `LL1594-2` | PhenX13_50_motor function child 6-12Y |
| `LL3731-8` | [NEI] Inheritance pattern from family history |
| `LL381-5` | MG_5_Genetic variant allelic state |
| `LL4034-6` | ACMG_Clinical significance of genetic variation |
| `396432002` | Status of regression of tumour |
| `399537006` | Clinical TNM stage grouping |
| `399588009` | Pathologic TNM stage grouping |

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
