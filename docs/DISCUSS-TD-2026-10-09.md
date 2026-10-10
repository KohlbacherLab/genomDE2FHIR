---
title: "MV-GenomSeq → MII KDS mapping: points to discuss"
date: "9 October 2026"
geometry: margin=2cm
fontsize: 10pt
colorlinks: true
header-includes:
  - \usepackage{xurl}
  - \renewcommand{\texttt}[1]{{\urlstyle{tt}\nolinkurl{#1}}}
---

*Reference: Thomas' annotated mapping table `DRAFT-Mapping-Table-genomDE-DK-2026-10-06-TD-final.xlsx`. Row numbers are Excel rows in his tabs:
**O** = KDK oncology, **R** = KDK rare diseases, **G** = GRZ, **OI** = Open Issues. Corrections we simply apply on our side are left out.
Every statement about a profile was checked against the real packages (2026 pins and the 2027.0.0 ballot) and cross-reviewed.
Kinds: **contradiction** = the packages say something different from the note; **decision** = needs a ballot comment or an agreed interim;
**2027** = changes in the ballot to confirm; **open** = rows without a note.*

## Index

| # | Module | Issue | Rows | Kind |
|:-|:--|:---------|:----|:---|
| 1 | Onkologie | ECOG value 5 and notApplicable are not representable | O 10, 76 | decision |
| 2 | Onkologie | TNM: KDK delivers SNOMED, the UICC coding is mandatory | O 32–36 | decision |
| 3 | Onkologie | Therapy type (therapeuticStrategy) has no element on the recommendation | O 228; OI 55 | decision |
| 4 | Onkologie | Metachrone diagnoses: boolean flag, occurredFollowing target changes in 2027 | O 79; OI 22 | contradiction, 2027 |
| 5 | Onkologie | Hereditary-case elements without any MII element | O 9, 87–88, 197–198; OI 4, 23–24, 47–48 | open, no note |
| 6 | Onkologie | Unannotated rows with a likely target: other recommendations, expression reference cohort | O 150, 194; OI 31, 46 | open, no note |
| 7 | Onkologie | MII's own MV-GenomSeq artefacts in the Onko package are defective | — | decision |
| 8 | Onkologie | 2027 diagnosis profiles: mandatory category and required ICD-O-3 topography binding | O 17–20, 27–31, 37–40 | 2027 change to confirm |
| 9 | Onkologie | HGNC system URI differs between modules in 2027 | — | 2027 change to confirm |
| 10 | MTB | Transcript ID bound required to http://ensembl.org | O 49–52, 169–172; OI 13–16 | decision |
| 11 | MTB | coding-change-type is 0..1 while KDK variantTypes is an array; fusion slot already used for gene_fusion | O 53–56, 173–176, 190; OI 17–20 | decision; updated 2026-10-10 |
| 12 | MTB | Prior findings: container, free-text carrier, method type | O 41–48, 57; OI 5–12, 21 | contradiction, decision; updated 2026-10-10 |
| 13 | MTB | Link between a performed therapy and its recommendation | O 90; OI 25 | contradiction, decision |
| 14 | MTB | therapyResponseSource is a data source; Observation.method is mandatory | O 100; OI 26 | contradiction, decision |
| 15 | MTB | Study recommendations: evidence grading, Z(FDA), supporting variants | O 206–207, 211, 218–220; OI 49–54 | decision; updated 2026-10-10 |
| 16 | MTB | Recommendation type (inLabel/offLabel/compassionateUse/secPreventive/unknown) has no element | O 229; OI 56 | decision |
| 17 | MTB | CNV type: undefined code system, genomDE 6 levels | O 134 | decision |
| 18 | MTB | Expression level (noExpression/normal/high/low) not codable | O 144; OI 30 | decision, 2027; updated 2026-10-10 |
| 19 | MTB | LOH per variant has no concept on the simple variant | O 165; OI 35 | decision |
| 20 | MTB | COSMIC SBS signatures have no concept | O 151–153; OI 32–33 | decision |
| 21 | MTB | Fusions: mandatory breakpoint components, unbound partner genes, intragenic SVs | O 178–185, 189; OI 36–43, 45 | decision |
| 22 | MTB | Sequencing QC extension: broken context, unclear semantics, no slot for minCoverage | G 7, 30–33, 40; OI 76–81 | contradiction, decision |
| 23 | MTB | Package defects: allele A/B displays swapped, NCIt system URI, ploidie interpretation, rna-seq slice codes | O 130; OI 28 | decision |
| 24 | MTB | Panel DeviceDefinition catalogue (2027) as home for GRZ kit names | G 5–6, 8–9, 11–12, 16–19, 38–39 | 2027 change to confirm |
| 25 | MTB | Notes labelled 2027 describe elements identical in the 2026 packages | O 2–3, 41–48, 53–56, 130, 134, 144, 151–153, 165, 178–185, 189–190; OI 2–3, 5–12, 17–20, 28, 30, 32–33, 35–43, 45 | contradiction |
| 26 | MolGen | Variant localization (HDB-976) | O 142, 164, 188; R 72, 92, 110; OI 29, 34, 44, 65, 69, 73 | in Thomas' ballot comment |
| 27 | MolGen | Finding category primary/incidental/candidate (HDB-976) | R 66, 86, 105; OI 64, 68, 72 | in Thomas' ballot comment; updated 2026-10-10 |
| 28 | MolGen | Segregation analysis: biparental and notPerformed (HDB-976 c) | R 76, 97, 114; OI 67, 71, 75 | in Thomas' ballot comment |
| 29 | MolGen | Mode of inheritance: LOINC answer codes vs HPO | R 73, 93, 111 | contradiction; updated 2026-10-10 |
| 30 | MolGen | ACMG evidence criteria have no component | R 62–63, 81–82, 101–102 | decision |
| 31 | MolGen | Study design single/duo/trio has no concept | R 20; OI 59 | open, no note |
| 32 | Seltene | GMFCS (HDB-975) | R 6, 29; OI 58, 62 | in Thomas' ballot comment |
| 33 | Seltene | Hospitalisation duration and periods bands (HDB-975) | R 22–23; OI 60–61 | in Thomas' ballot comment |
| 34 | Seltene | Therapy strategy 'other' unreachable for medication; medication/non-medication split | R 129 | decision |
| 35 | Consent | MV-GenomSeq consent domains cannot be expressed | O 112; R 46; G 49; OI 27, 63, 82 | contradiction, decision; updated 2026-10-10 |

## Onkologie

### 1. ECOG value 5 and notApplicable are not representable

*Rows:* O 10, 76 · *Kind:* decision

**Thomas' note.** Thomas (2026-10-06): the LOINC slice is present in Onko 2027 (`value.coding:loinc`, bound to `mii-vs-onko-allgemeiner-leistungszustand-ecog-loinc`); the CS still knows only 0-4 and U, so 5/notApplicable are a ballot candidate for Onkologie. His earlier note: "We can add that to the Onko Module if necessary", plus a planned optional LOINC annotation.

**What the packages say.** `mii-pr-onko-allgemeiner-leistungszustand-ecog` (2026.0.3 and 2027): Observation.value\[x\] 1..1, value\[x\].coding:obds 1..1 required-bound to `mii-vs-onko-allgemeiner-leistungszustand-ecog`; CS `mii-cs-onko-allgemeiner-leistungszustand-ecog` has 0, 1, 2, 3, 4, U in both versions; obs-6 forbids dataAbsentReason next to a value. value\[x\].coding:loinc 0..* MS exists since 2026.0.3 unbound; 2027 adds a required binding to the new VS (LA9622-7, LA9623-5, LA9624-3, LA9625-0, LA9626-8, LA9627-6 Dead). ConceptMap `mii-cm-onko-allgemeiner-leistungszustand-ecog-loinc`: 2026 carries wrong LOINC answer codes (LA9622-2 etc.), 2027 corrects them; U unmatched and no row for 5 in either. 2027 adds `Observation.focus` MS targeting `mii-pr-onko-diagnose-primaertumor`. `Observation.code` slices (SNOMED 423740007 1..1, LOINC 89262-0) unchanged. LM `OnkologieFollowup.ECOG` is unmapped in 2026 and 2027.

**Impact on genomDE data.** KDK `ecogPerformanceStatusScore` (case and follow-up) allows 0-5, unknown, notApplicable. 0-4 map to obds codes; unknown must become U (our dataAbsentReason route is invalid in both versions). 5 and notApplicable have no valid form, so the mapper drops them with a warning. LOINC annotation is reliable only against 2027.

**Options.**

- Ballot Onko: add `5` (Tod) and an explicit NA concept to the CS plus a ConceptMap row 5 -> LA9627-6 (the 2027 VS already has the target).
- Ballot alternative: relax value\[x\] or `coding:obds` to 0..1 so dataAbsentReason=not-applicable or a LOINC-only LA9627-6 coding validates.
- Interim: drop 5/notApplicable with a warning; or encode 5 as obds U plus loinc LA9627-6 (profile-valid, semantically contradictory).
- Follow-up ECOG: discriminate from the diagnosis ECOG only by `effectiveDateTime` (2027 also `focus`); no follow-up category exists.

**Our proposal.** Map 0-4 to `coding:obds` (plus `coding:loinc` from 2027 on), unknown to U, and drop 5/notApplicable with a warning until the ballot adds `5` and NA to the CS. We prefer extending the CS over relaxing cardinality, so oBDS alignment stays intact.

**To decide with Thomas.** Extend `mii-cs-onko-allgemeiner-leistungszustand-ecog` (5, NA) or relax value\[x\]/`coding:obds` to 0..1? Is obds U plus LOINC LA9627-6 an acceptable interim for ECOG 5? How is a follow-up ECOG marked, given 2027 `mii-pr-onko-verlauf.hasMember` no longer admits it?

### 2. TNM: KDK delivers SNOMED, the UICC coding is mandatory

*Rows:* O 32–36 · *Kind:* decision

**Thomas' note.** Thomas: TNM overhaul in 2027 to align with SNOMED, aim for the new version. `mii-pr-onko-tnm-klassifikation` binds the type to SNOMED (399537006 clinical, 399588009 pathologic, 399703000 integrated), UICC stage as value, T/N/M/L/V/Pn/S categories via hasMember with UICC+SNOMED value slices (e.g. `mii-vs-onko-tnm-t-kategorie-werte-sct`); update profile and VS names to 2027; model stays hasMember, not component.

**What the packages say.** Grouping profile `mii-pr-onko-tnm-klassifikation` is unchanged 2026 -> 2027 (`code` required `mii-vs-onko-tnm-klassifikation-typ`, which gains 399703000 in 2027; value\[x\] required `mii-vs-onko-tnm-uicc-stadium`; `method` required `mii-vs-onko-tnm-version`, but only example-bound on n/m-kategorie). Category profiles `mii-pr-onko-tnm-{t,n,m}-kategorie`: 2026 value\[x\] required-bound to the UICC VS with unsliced `coding` 0..*; 2027 introduces value\[x\].coding:uicc 1..1 and `coding:snomed-ct` 0..1 (VS `mii-vs-onko-tnm-{t,n,m}-kategorie-werte-sct`); L/V/Pn/S keep a single UICC binding. ConceptMaps `mii-cm-onko-tnm-uicc-sct-clinical/-pathological` run UICC -> SNOMED, 131 entries, 38 clinical / 39 pathological unmatched (e.g. MX, L/V/Pn/S). Canonical URLs unchanged. c/p prefix `code.extension:cpPraefix` exists in 2026; y/r/a `modifierExtension` and `component:multipleTumoren` are 2027 only (symbol profiles retired); 2027 invariant tnm-sct-uicc-konsistenz requires the SNOMED display to contain the prefixed UICC code plus trailing space.

**Impact on genomDE data.** KDK tnmClassifications\[\] (minItems 3) delivers SNOMED Codings (code, system, version, display, optional text cT1a). Both versions require a UICC coding, so the mapper must reverse-map SNOMED -> UICC; items without a match cannot validate. `version` is the SNOMED edition, not the TNM-Auflage, so our `Observation.method` mapping was wrong.

**Options.**

- Inverse ConceptMap (SNOMED -> UICC) maintained in the MVGS spec; unmatched items -> warning, Observation dropped (hard gap).
- Ballot Onko: `coding:uicc` 0..1 when `coding:snomed-ct` is present; ship an SCT -> UICC ConceptMap; loosen the display invariant.
- 2026 interim: UICC coding from the inverse map, SNOMED as additional unsliced coding. 2027: KDK code/system/version into `coding:snomed-ct`, display only via the SNOMED term that satisfies the invariant, KDK text into value\[x\].text, c/p into `cpPraefix`.
- Grouping Observation: `code` 399537006/399588009 from prefixes else 399390009 (399703000 only for the synthetisiert profile); omit `method` and stage `value` (not in KDK).

**Our proposal.** Target the 2027 category profiles: KDK Coding into `coding:snomed-ct`, `coding:uicc` derived through an inverted MII ConceptMap kept in the MVGS spec, and file a ballot asking for `coding:uicc` 0..1 when SNOMED is present.

**To decide with Thomas.** Is the inverse ConceptMap the sanctioned route, and who audits SNOMED -> UICC coverage? Can `coding:uicc` become 0..1 with `snomed-ct` present? Confirm `method` may be omitted and `version` goes to `coding:snomed-ct.version`; should y/r/a parsed from text populate the modifierExtensions?

### 3. Therapy type (therapeuticStrategy) has no element on the recommendation

*Rows:* O 228; OI 55 · *Kind:* decision

**Thomas' note.** Thomas: values = oBDS-Therapieart. Target terminology exists in Onko 2027: CS `mii-cs-onko-therapie-typ` / VS `mii-vs-onko-systemische-therapie-art` (CH, HO, IM, ZS, SZ, CI, CZ, CIZ, IZ, SO, ...), bound to `Procedure.code` of the performed systemic therapy. No element on `mii-pr-mtb-therapieempfehlung` (MedicationRequest), category only example -> ballot candidate MTB: bind category or an extension to this VS.

**What the packages say.** CS `mii-cs-onko-therapie-typ` (CH, HO, IM, ZS, SZ, CI, CZ, CIZ, IZ, WW, AS, WS, OP, ST, KW, SO) and VS `mii-vs-onko-systemische-therapie-art` (same minus OP, ST, KW) are identical in 2026.0.3 and 2027, so not new; the KDK enum (CH, HO, IM, ZS, CI, CZ, CIZ, IZ, SZ, SO) is a strict subset. `mii-pr-onko-systemische-therapie`: `Procedure.code.coding:systemische_therapie_art` 0..1 required. `mii-pr-mtb-therapieempfehlung` (mtb 2026.0.1 and 2027): `MedicationRequest.category` 0..* example-bound to the base medicationrequest-category VS; extensions only Prioritaet, Evidenzgraduierung, Publikation; base `mii-pr-onko-therapieempfehlung-medikation` has no therapy-type element either. `mii-pr-mtb-therapieempfehlung-kombination` (RequestGroup): `RequestGroup.code` 0..1 MS preferred-bound to `mii-vs-onko-therapieempfehlung-typ` (whole CS), `action` 1..*, `action.resource` 1..1 -> therapieempfehlung. `mii-pr-mtb-therapieplan` `activity:obds.detail.code` 1..1 required, but `activity:obds.reference` is 0..0.

**Impact on genomDE data.** Every KDK recommendedSystemicTherapies\[\].therapeuticStrategy has a code in the MII CS, but no profiled slot on the MedicationRequest recommendation. It validates today only via `RequestGroup.code` (one wrapper per recommendation, preferred binding, broader VS) or an unprofiled example-bound `MedicationRequest.category` coding; `activity:obds` cannot point at one MedicationRequest.

**Options.**

- Interim A: wrap each recommendation in `mii-pr-mtb-therapieempfehlung-kombination`, `RequestGroup.code` = strategy (valid in 2026 and 2027).
- Interim B: `MedicationRequest.category.coding` with system `mii-cs-onko-therapie-typ` (valid because example-bound; mirrors Seltene `category:MVGenomSeqTherapieStrategie`).
- Ballot MTB (and Onko base profile): add a `MedicationRequest.category` slice required-bound to `mii-vs-onko-systemische-therapie-art` or `mii-vs-onko-therapieempfehlung-typ`.

**Our proposal.** Use interim B now (category coding, no wrapper) and file the MTB/Onko ballot for a bound category slice; we lean to `mii-vs-onko-therapieempfehlung-typ` for consistency with `RequestGroup.code` and `activity:obds`, unless MTB prefers the narrower systemic VS Thomas named.

**To decide with Thomas.** Does MTB accept the example-bound category coding as interim, or prefer the RequestGroup wrapper? Which VS should the ballot bind: `mii-vs-onko-systemische-therapie-art` or `mii-vs-onko-therapieempfehlung-typ`? Should `mii-pr-onko-therapieempfehlung-medikation` get the same slice?

### 4. Metachrone diagnoses: boolean flag, occurredFollowing target changes in 2027

*Rows:* O 79; OI 22 · *Kind:* contradiction, 2027

**Thomas' note.** Thomas: confirmed, a further Condition per `mii-pr-mtb-diagnose-primaertumor` or `mii-pr-onko-diagnose-primaertumor`; new in 2027: mandatory category SNOMED 55342001 and extension dueTo for the relation to the first diagnosis.

**What the packages say.** KDK OncologyFollowUp.followUpOds\[\].metachroneDiagnoses is a boolean (renamed from metachroneTumorObserved); the diagnoses live in additionalDiagnoses\[\]. 2027 `mii-pr-onko-diagnose-primaertumor`: `Condition.category:onkologie` 1..1 pattern SNOMED 55342001 (2026.0.3 has no category constraint); new `extension:dueTo` (condition-dueTo 0..*, short "Verursacht durch (therapieassoziierte Sekundärmalignome)", targets therapies and tumour Conditions); `extension:occurredFollowing` exists since 2026.0.3 targeting only `mii-pr-onko-fruehere-tumorerkrankung`, 2027 widens it to `mii-pr-onko-diagnose-primaertumor` (short "zeitliche Abfolge"); 2027 also adds `Condition.identifier` (Tumor-ID) MS, `extension:transformationVon`, ICD-O-3 morphology 0..*. All inherited by `mii-pr-mtb-diagnose-primaertumor`. LM `OnkologieFollowup.MetachroneTumore` / `MetachroneDiagnose` unmapped in 2026 and 2027; the 2027 Condition ConceptMap to MVGS is an empty shell (no group).

**Impact on genomDE data.** Our row and Thomas's confirmation treat the boolean as a diagnosis object; it is not. additionalDiagnoses\[\] already map to `Condition.code` ICD-10-GM; the flag has no MII element. From 2027 follow-up Conditions need category 55342001 and may link via `occurredFollowing`; true without diagnoses or explicit false is lost.

**Options.**

- Derived rule (MVGS spec, 2027 only): true iff a follow-up Condition carries `extension:occurredFollowing` -> Erstdiagnose; `dueTo` only when therapy-associated (never derivable from KDK).
- Preserve the bare boolean when no diagnosis accompanies it: MVGS extension or note.
- Ballot Onko: an element 'metachroner Tumor ja/nein' (e.g. on `mii-pr-onko-verlauf`) and LM mappings for MetachroneTumore/MetachroneDiagnose.
- Reprofile follow-up `additionalDiagnoses` as `mii-pr-onko-diagnose-primaertumor` (Feststellungsdatum 1..1, category 55342001) instead of core Diagnose.

**Our proposal.** Split the row: additionalDiagnoses\[\] -> `mii-pr-onko-diagnose-primaertumor` (2027: category 55342001, `occurredFollowing` -> Erstdiagnose), and `metachroneDiagnoses` -> a derived MVGS rule with an MVGS extension preserving an unsupported true/false.

**To decide with Thomas.** Agree that `occurredFollowing` (temporal), not `dueTo` (causal), is the link for metachronous tumours? Should the flag get an Onko element or stay derived? Should follow-up diagnoses be profiled as `diagnose-primaertumor` rather than core Diagnose?

### 5. Hereditary-case elements without any MII element

*Rows:* O 9, 87–88, 197–198; OI 4, 23–24, 47–48 · *Kind:* open, no note

**Thomas' note.** Thomas wrote nothing on these rows.

**What the packages say.** No CS, VS or profile in Onko 2027 or MTB 2027 for three KDK blocks (2026 not separately checked). (a) `case.diagnosisOd.diagnosticAssessment` (noGeneticDiagnosis, suspectedGeneticDiagnosis, furtherGeneticDiagnosticRecommended, confirmedGeneticDiagnosis, partialGeneticDiagnosis): LM `mii-lm-mvgenomseq-onkologie` marks `Diagnose.DiagnostischeVoruntersuchungen` and `Keimbahndiagnose` as no direct match ("Keimbahndiagnose existiert als Konzept nicht"); Seltene `mii-pr-seltene-genetic-diagnosis` (Condition, category 782964007, `evidence` 1..*, `verificationStatus`) is how our RD row is mapped. (b) preventiveMeasures\[\].preventiveMeasureResult (noFindings, malignoma, unclear) and `.reference`: LM blocks `OnkologiePlan.PraeventiveUntersuchungen` and `OnkologieFollowup.PraeventiveMassnahmen` have no mapping; only generic `CarePlan.activity.outcomeCodeableConcept`, `Procedure.outcome`, `Procedure.basedOn`. (c) suitableInterventions\[\] therapeutic/risk-reducing flags: `mii-pr-onko-therapieempfehlung-operation` (ServiceRequest) has no intention element; `mii-ex-onko-operation-intention` (K, P, D, R, S, X) targets performed operations, no prophylactic code. 2027 ships unused `praedispositionsgene-hgnc` / `praedispositionssyndrome-orpha` value sets (purpose unverified).

**Impact on genomDE data.** Hereditary-tumour KDK data (assessment of genetic diagnostics, recommended preventive measures with result and back-reference, therapeutic versus risk-reducing intent of interventions) has no MII target today; without an interim the mapper drops it entirely from oncology bundles.

**Options.**

- diagnosticAssessment: reuse Seltene `mii-pr-seltene-genetic-diagnosis` with `verificationStatus` (no -> refuted/unconfirmed, suspected -> provisional, partial -> differential, confirmed -> confirmed); furtherGeneticDiagnosticRecommended -> `mii-pr-mtb-humangenetische-beratung-auftrag`.
- Preventive measures: ServiceRequest (intent proposal) in `CarePlan.activity.reference`; result via `Procedure.outcome` (MVGS CS) with `Procedure.basedOn` as link, or `CarePlan.activity.outcomeCodeableConcept`.
- Flags: `ServiceRequest.reasonCode` or an MVGS extension on `mii-pr-onko-therapieempfehlung-operation`.
- Ballot Onko: Keimbahndiagnose Condition profile, preventive-measure profiles with result VS, extend `mii-ex-onko-operation-intention` (risikoreduzierend) and slice it on the recommendation.

**Our proposal.** Implement the Seltene reuse and the ServiceRequest/Procedure interim now (status DRAFT) and file one Onko ballot comment covering all three hereditary gaps, asking also what the 2027 predisposition value sets are meant for.

**To decide with Thomas.** Is reusing the Seltene genetic-diagnosis Condition inside an MTB bundle acceptable, or does Onko want its own Keimbahndiagnose? Does Onko plan preventive-measure profiles? May `mii-ex-onko-operation-intention` be extended and reused on recommendations? Purpose of the 2027 predisposition value sets?

### 6. Unannotated rows with a likely target: other recommendations, expression reference cohort

*Rows:* O 150, 194; OI 31, 46 · *Kind:* open, no note

**Thomas' note.** Thomas wrote nothing on these rows.

**What the packages say.** plan.carePlanOd.otherRecommendations\[\] (KDK enum WW, AS, WS, OP, ST, KW, SO): `mii-pr-onko-tumorkonferenz` (2026.0.3 and 2027) has `CarePlan.activity:obds.detail.code` 1..1 required-bound to `mii-vs-onko-therapieempfehlung-typ` (whole CS `mii-cs-onko-therapie-typ`, coding.system pattern), inherited by `mii-pr-mtb-therapieplan`; the KDK enum is an exact subset; `activity:obds.reference` is 0..0. molecular.expressionVariants\[\].reference (free-text Bewertungsgrundlage, e.g. comparison cohort of 400 patients): `mii-pr-mtb-rna-seq` 2027 components are transcript-id, transcripts-per-million (Ratio), tissue-corrected-expression (boolean), raw-counts, library-size, cohort-ranking (Quantity), all numeric or boolean; LM `OnkologieMolekular.ExpressionsVariante.Bewertungsgrundlage` is unmapped; base `Observation.note` and `Observation.method.text` remain available. No 2026 vs 2027 difference for the obds slice.

**Impact on genomDE data.** Both rows are unmapped today although conformant targets exist: otherRecommendations can go into a required-bound coded slice right now; the expression reference cohort can only travel as free text (note or method.text), which loses structure but no content.

**Options.**

- otherRecommendations -> `mii-pr-mtb-therapieplan` `CarePlan.activity:obds.detail.code.coding` (system `mii-cs-onko-therapie-typ`, code 1:1), `detail.status not-started; MAPPED now.
- expressionVariants\[\].reference -> rna-seq Observation.note.text` (prefix 'Bewertungsgrundlage: '), alternatively `Observation.method.text`; a numeric rank additionally into `component:cohort-ranking`.
- Optional MTB ballot: a string component 'reference-cohort' on `mii-pr-mtb-rna-seq`.

**Our proposal.** Set both rows to MAPPED with the targets above and document the rna-seq free-text carrier in the MVGS IG; raise an MTB component only if the MTB team wants the cohort structured.

**To decide with Thomas.** Is `activity:obds` intended for board recommendations in MTB too, or should MTB recommendations always be `activity:extended` with referenced resources? For the cohort text, `Observation.note` or `Observation.method.text`?

### 7. MII's own MV-GenomSeq artefacts in the Onko package are defective

*Rows:* — · *Kind:* decision

**Thomas' note.** Thomas wrote nothing on these artefacts; his email names an MV-GenomSeq specification as the home for what the modules cannot hold, which is exactly what these artefacts are meant to be.

**What the packages say.** The Onko package ships `StructureDefinition-mii-lm-mvgenomseq-onkologie` (2026.0.3 and 2027, 130 elements) and, new in 2027, `ConceptMap-mii-cm-onkologie-to-mvgenomseq` (scope OncologyCase.json only) plus `ConceptMap-mii-cm-mii-to-mvgenomseq-condition-diagnose-primaertumor` (empty, no group, wrong canonicals). Defects we verified: all four TNM rows (TNM-Klassifikation, T, N, M) target `diagnosisOD.ECOGPerformanceStatusScore`; LM `TNMSchluessel` maps to Observation code 33732-9 (a LOINC grading code) labelled system snomed, same text already in 2026.0.3; the ECOG mapping is marked equivalent although 5/notApplicable are not representable; LM blocks `OnkologieFollowup.*` (ECOG, MetachroneTumore, MetachroneDiagnose, PraeventiveMassnahmen), `OnkologiePlan.PraeventiveUntersuchungen`, `EmpfehlungOperationTherapeutisch/-Risikoreduzierend`, `EmpfehlungTyp`, `EmpfohleneStudie.Evidenzgrad`, `ExpressionsVariante.Bewertungsgrundlage have map=\[\]; DiagnostischeVoruntersuchungen` and `Keimbahndiagnose` say no direct match; no ConceptMap target for `followUpOds.ecogPerformanceStatusScore`.

**Impact on genomDE data.** An implementer following MII's own artefacts would write TNM into the ECOG field and a LOINC grading code as SNOMED, and finds no guidance for follow-up, plan and hereditary blocks. Our verified table is currently the only complete crosswalk for genomDE oncology.

**Options.**

- Ballot Onko: fix the TNM and TNMSchluessel rows, fill or remove the empty Condition ConceptMap, map or explicitly hand off the unmapped LM blocks.
- Offer our mapping table as the source to regenerate the LM mapping elements and the ConceptMaps.
- Extend the ConceptMap scope beyond OncologyCase (FollowUp, Plan, Molecular) or declare MTB ownership for those blocks.
- Leave the artefacts as they are and keep the crosswalk only in our MVGS IG.

**Our proposal.** File one Onko ballot comment listing the concrete defects and offer our table as the maintained source for `mii-lm-mvgenomseq-onkologie` and `mii-cm-onkologie-to-mvgenomseq`.

**To decide with Thomas.** Who owns these artefacts and will fix them for 2027 final? Can our table feed them, and in which form (ConceptMap, LM mapping element, CSV)? Should the ConceptMap scope cover FollowUp, Plan and Molecular, or is that MTB's job?

### 8. 2027 diagnosis profiles: mandatory category and required ICD-O-3 topography binding

*Rows:* O 17–20, 27–31, 37–40 · *Kind:* 2027 change to confirm

**Thomas' note.** Thomas wrote nothing on this. We found it by diffing the 2026 and 2027 packages; it is outside his notes, and HDB-975/976 concern Seltene and MolGen, not Onkologie.

**What the packages say.** onkologie-2027.0.0-ballot.1 `mii-pr-onko-diagnose-primaertumor`, inherited by mtb-2027 `mii-pr-mtb-diagnose-primaertumor`: `Condition.category` 1..* with slice `category:onkologie` 1..1 patternCodeableConcept SNOMED 55342001 (2026.0.3: no category constraint); `Condition.bodySite.coding:icd-o-3` binding required to `mii-vs-onko-icdo3-topographie` (2026: no binding); `extension:morphology-behavior-icdo3` max 1 becomes *; `mii-pr-onko-fruehere-tumorerkrankung` category min 2 (slices `oncology` and `onkologie`). Seltene diagnosis profiles unchanged. ICD-O-3 is a licensed German terminology that tx.fhir.org does not serve, so our matchbox setup cannot validate the binding. Whether `bodySite` itself becomes mandatory and the cardinality of `coding:icd-o-3` were not re-verified (unverified).

**Impact on genomDE data.** Against the 2026 pins none of these constraints apply to our Condition rows. At the 2027 pin every primary-tumour Condition without `category:onkologie` fails, and any `coding:icd-o-3` not from the topography value set fails; whether KDK always supplies an ICD-O-3 topography code is unverified.

**Options.**

- Add the constant `category:onkologie` (SNOMED 55342001) to all primary-tumour Conditions now; harmless under 2026, required under 2027
- Emit `bodySite.coding:icd-o-3` only when KDK carries an ICD-O-3 topography code; otherwise omit `bodySite` (only if it stays optional, unverified)
- Load an ICD-O-3 CodeSystem into the local matchbox for validation
- Ballot: ask for extensible instead of required, or for documented validation guidance

**Our proposal.** Apply the constant category now and make the ICD-O-3 topography coding conditional; file a ballot comment asking MII to state how implementers validate a licensed terminology and whether required is intended.

**To decide with Thomas.** Is ICD-O-3 topography meant to be effectively mandatory on every 2027 diagnosis, which terminology server should implementers validate against, and would he support extensible instead of required?

### 9. HGNC system URI differs between modules in 2027

*Rows:* — · *Kind:* 2027 change to confirm

**Thomas' note.** Thomas wrote nothing on this. Found by our package diff; it is question F.14 in our review (which HGNC system URI for MV-GenomSeq).

**What the packages say.** onkologie-2027 `mii-pr-onko-genetische-variante`: the `gene-studied` value binding switches to `mii-vs-onko-marker-gene-hgnc`, system `http://www.genenames.org/geneId`, an enumerated list of 40 genes (binding strength unverified). 2026.0.3 bound it to GR `hgnc-vs` (system `http://www.genenames.org`, plus `/genegroup`). MTB `mii-pr-mtb-einfache-variante` and MolGen `variante` keep `hgnc-vs` with `http://www.genenames.org` in 2026 and 2027. MII's own MolGen example `cnv-4` already uses `/geneId`. Our terminology lock is `http://www.genenames.org`.

**Impact on genomDE data.** No current row breaks: our oncology variant rows target MTB and MolGen profiles, not `onko-genetische-variante`. But MII now carries two HGNC system URIs across modules, and a closed 40-gene enumeration could not hold genomDE's open gene list if a row ever moved to the Onko profile.

**Options.**

- Keep the lock `http://www.genenames.org` (GR `hgnc-vs`) and never target `onko-genetische-variante`
- Emit both HGNC codings (GR URI and `/geneId`) on gene-studied values
- Switch the lock to `/geneId` (would diverge from GR `hgnc-vs` as used by MTB/MolGen)
- Ballot: ask Onko to reuse `hgnc-vs`, or MII to document one canonical HGNC URI

**Our proposal.** Keep the GR URI and the MTB/MolGen profiles; file a short ballot comment asking Onko to align its HGNC system with GR `hgnc-vs` or to document the two URIs explicitly.

**To decide with Thomas.** Which HGNC system URI does MII want for MV-GenomSeq data, is the Onko 40-gene list meant as a closed required binding, and will Onko align with GR `hgnc-vs`?

## MTB

### 10. Transcript ID bound required to http://ensembl.org

*Rows:* O 49–52, 169–172; OI 13–16 · *Kind:* decision

**Thomas' note.** Thomas: Vorbefund container is `mii-pr-mtb-ngs-bericht`, linked from `mii-pr-mtb-behandlungsepisode.supportingInfo:Vorbefund`; variant = `mii-pr-mtb-einfache-variante`; transcript.* goes to `component:representative-transcript-ref-seq.valueCodeableConcept.coding` (LOINC 51958-7); MTB binds the value required to http://ensembl.org, so RefSeq NM_ transcripts must be translated or raised as a ballot item. He also corrected our stale slice name `transcript-ref-seq`.

**What the packages say.** `mii-pr-mtb-einfache-variante`, identical in 2026.0.1 and 2027.0.0-ballot.1: `Observation.component:representative-transcript-ref-seq` 0..1 MS, code LOINC 51958-7, value\[x\] 1..1 CodeableConcept, binding required to `http://ensembl.org`. No ValueSet with that URL exists in any package; the IG's own validation-oo.json reports it as a warning only (ValueSet not found); the definition says Ensemble Transcript ID (ENST...). Yet the packaged example `MII-EXA-MTB-Einfache-Variante` uses NM_133433.4 with system `https://www.ncbi.nlm.nih.gov/refseq/`. MolGen `variante` and Onko `genetische-variante` bind example (NCBI or LRG); MolGen examples use `http://www.ncbi.nlm.nih.gov/refseq`. DNPM allows Ensembl (`https://www.ensembl.org`) and RefSeq; KDK transcript.system is a free URI string, and the KDK changelog example system is the bare string 'Ensembl'.

**Impact on genomDE data.** KDK transcripts with RefSeq NM_ ids contradict the profile text, and no Ensembl system URI is defined anywhere in MII. Validators currently only warn because the ValueSet is unresolvable, so data passes by accident. The KDK string 'Ensembl' must be normalised to a URI by the mapper.

**Options.**

- Ballot: change the binding to example/extensible as in MolGen, or publish a real ValueSet covering Ensembl, RefSeq and LRG with fixed system URIs
- Interim: pass the coding through, RefSeq to `http://www.ncbi.nlm.nih.gov/refseq`, Ensembl to `http://www.ensembl.org` (URI to confirm), accept the warning as a documented deviation
- Omit the component for non-Ensembl transcripts and carry the transcript in the HGVS prefix (lossy)
- Reference a plain MolGen `variante` (example binding) from `result, whose slicing is open

**Our proposal.** File the ballot comment citing the self-contradiction between profile and example, and pass transcript codings through unchanged in the meantime with the deviation documented.

**To decide with Thomas.** Is the required http://ensembl.org binding intentional? Will MTB align with MolGen (example) or define a ValueSet, and which system URIs should Ensembl and RefSeq transcripts carry?

### 11. coding-change-type is 0..1 while KDK variantTypes is an array; fusion slot already used for gene_fusion

*Rows:* O 53–56, 173–176, 190; OI 17–20 · *Kind:* decision

**Thomas' note.** Thomas: variantTypes\[\].* goes to component:coding-change-type.valueCodeableConcept.coding` (LOINC 48019-4, extensible SO dna-change-type-vs); genomDE delivers a Coding, take it 1:1, SO preferred. He corrected our non-existent `component:variant-type`, and for structureType proposed coding-change-type (translocation/inversion/deletion/duplication) or `component:variation-code` (81252-9).

**What the packages say.** `component:coding-change-type` 0..1 MS, code LOINC 48019-4, value\[x\] 1..1 CodeableConcept, binding extensible `dna-change-type-vs` (GR 3.0.0, intensional: SO is-a SO:0002072, system `http://www.sequenceontology.org`); identical in `einfache-variante`, `dna-fusion`, `rna-fusion`, MolGen `variante`, 2026 and 2027. Max 1 is inherited from GR `variant`, so MolGen cannot widen it. GR ConceptMap `dna-change-type-map` confirms deletion SO:0000159, duplication SO:1000035, inversion SO:1000036 as members; translocation SO:0000199 is unverified. `component:variation-code` (81252-9, 0..*, unbound) is a variant identifier (ClinVar/COSMIC), not a type. MII example `fgfr2-fusion` puts SO:0001565 gene_fusion into coding-change-type; MTB DNA-fusion examples leave it empty. MII examples use `http://sequenceontology.org` 50 times, the www form 19 times.

**Impact on genomDE data.** KDK `variantTypes` can carry several SO codings per variant; only one component is allowed, so a second type has no slot. On fusions the single slot is contested between the KDK structural mechanism and MII's gene_fusion precedent. Consequence terms would belong to `molekulare-konsequenz, which MTB does not profile.

**Options.**

- Convention: several SO codings in the single CodeableConcept.coding\[\] (legal, lossless); document it
- One Observation per variant type (duplicates the variant)
- Fusions: gene_fusion plus the structural SO code as codings in the same CodeableConcept, genomDE enum kept as a further coding
- Fusions: structural mechanism in a genomDE extension instead
- Ballot MolGen to document the multi-coding convention (it cannot raise 0..1 itself; HL7 CG owns it)

**Our proposal.** Adopt the multi-coding convention with system http://www.sequenceontology.org`; on fusions emit gene_fusion plus the structural SO code in one CodeableConcept and ask MolGen to document this.

**To decide with Thomas.** Are several SO codings in one CodeableConcept acceptable? On fusions, gene_fusion or structural mechanism in coding-change-type? Is translocation inside dna-change-type-vs, and which SO system URI?

**Update 2026-10-10 (mapping table now differs; text above kept as discussed).** Translocation is now verified: in the Sequence Ontology (OLS) SO:0000199 translocation lies under structural_alteration SO:0001785, sequence_alteration SO:0001059 and sequence_comparison SO:0002072, so it is a member of `dna-change-type-vs` (SO is-a SO:0002072). gene_fusion SO:0001565 is not: its ancestors are feature_fusion, structural_variant SO:0001537 and sequence_variant SO:0001060 (molecular consequence), so the MII `fgfr2-fusion` example puts a code outside the value set into coding-change-type. The gene_fusion part of our proposal is withdrawn. On fusions the converter emits only the structural mechanism from `mvgs-cm-structure-type-so` (translocation SO:0000199, inversion SO:1000036, deletion SO:0000159, duplication SO:1000035) plus the KDK enum as a second coding (O 190), which is Thomas' first option. The multi-coding convention for `variantTypes` (O 53–56, 173–176) stands. Open for Thomas: only the SO system URI.

### 12. Prior findings: container, free-text carrier, method type

*Rows:* O 41–48, 57; OI 5–12, 21 · *Kind:* contradiction, decision

**Thomas' note.** Thomas: Vorbefund container `mii-pr-mtb-ngs-bericht` via `behandlungsepisode.supportingInfo:Vorbefund`; complexVariants to result:CopyNumberVariant / DNAFusion / RNAFusion (check KDK field structure); date to `DiagnosticReport.effectiveDateTime` (confirmed); type not on `DiagnosticReport.code` but on the linked `mii-pr-mtb-genomic-study-analysis.extension:method-type`, VS of six codes; exome to whole-exom-sequencing, genome* to whole-genom-sequencing (read length lost), panel to gene-panel; no concept for single/array/karyotyping/other/none, ballot candidate.

**What the packages say.** All identical in 2026.0.1 and 2027. `mii-pr-mtb-ngs-bericht` derives from base DiagnosticReport; `supportingInfo:Vorbefund` 0..* MS targets base DiagnosticReport or Observation. KDK `complexVariants is string\[\] (DNPM LM priorDiagnosticReports.results` also strings); the typed `result` slices need structured components (fusion partners 1..1) a string cannot fill; carriers: `DiagnosticReport.conclusion` 0..1 (not MS) or an unprofiled Observation.valueString via the open `result` slicing. effective\[x\] 0..1 not MS; only `issued` (instant) is MS. Extension `mii-ex-mtb-ngs-bericht-genomic-study` is sliced into no profile, no example. `method-type` binding required `mii-vs-mtb-genomic-analysis-method-type` = MII CS (six codes, spelled whole-genom-/whole-exom-) plus the entire GR `genomic-study-method-type-cs` (81 codes: karyotyping, microarray, comparative-genomic-hybridization, snp-detection, other; no single-gene, no short/long-read). qc sub-extension `sequencing-read-type` is unbound, undefined, unexampled. The DNPM LM shipped in MTB 2027 maps `priorDiagnosticReports` to the molecular-pathology-report.

**Impact on genomDE data.** Free-text complexVariants fit only `conclusion` (not MS) or an unprofiled valueString Observation; day-precision dates cannot fill `issued`; type requires an unprofiled link; karyotyping/array/other are codable with GR codes, `single` has no precise code, short vs long read collapses; `none` yields no resource.

**Options.**

- complexVariants: `conclusion` joined by newline, or one unprofiled Observation.valueString per entry
- date: `effectiveDateTime`, leave `issued` empty; ballot effective\[x\] MS
- type: MII codes for exome/genome/panel, GR codes for karyotyping/array/other, a Sanger code or targeted-variant-analysis for single (to pick); short/long read via qc `sequencing-read-type` as local convention
- Ballot: slice the genomic-study extension into `ngs-bericht`, add single-gene and read-length concepts, fix spellings

**Our proposal.** Map as in the options with uniform `conclusion for free text and GR codes for the missing types; file one MTB ballot comment covering carrier, effective\[x\], the unprofiled link and the missing concepts.

**To decide with Thomas.** Confirm ngs-bericht` (not molecular-pathology-report) as container, via `supportingInfo:Vorbefund` or `investigation:NgsBericht`; accept conclusion/valueString; which GR codes for single and array; is `sequencing-read-type` meant for short/long read; will he slice the genomic-study extension?

**Update 2026-10-10.** A profiled free-text carrier does exist: `component:conclusion-string` (GR `tbd-codes-cs#conclusion-string`, valueString, 0..1 MS) on `mii-pr-mtb-einfache-variante` and the other variant profiles, inherited from GR / MolGen `variante`. It needs a variant Observation, though. The converter keeps `DiagnosticReport.conclusion` for `complexVariants[]` (O 41), and BALLOT-COMMENTS MTB-10 now says this.

### 13. Link between a performed therapy and its recommendation

*Rows:* O 90; OI 25 · *Kind:* contradiction, decision

**Thomas' note.** Thomas: gap, `mii-pr-mtb-systemische-therapie.basedOn` targets only CarePlan (Therapieplan), not the single Therapieempfehlung (MedicationRequest); linkage only via CarePlan.activity.reference; a direct reference would be an MTB ballot candidate.

**What the packages say.** `Procedure.basedOn` 0..1 Reference(CarePlan); 2027 adds slice `basedOn:tumorkonferenz` 0..1 to `mii-pr-mtb-therapieplan` (2026: unsliced, targets therapieplan or CarePlan). But `Procedure.extension:causedBy` 0..1 MS (procedure-causedBy) with value Reference(MII MedicationRequest, `mii-pr-mtb-therapieempfehlung`, hl7 MedicationRequest) exists in 2026.0.1 and 2027: a direct link, documented in the LM mapping `mii-lm-mtb.FollowUp.SystemischeTherapie.TherapieEmpfehlung` to Procedure.extension\[causedBy\] and in the packaged example. `therapieplan.activity:extended.reference` 1..1 points to Onko therapieempfehlung profiles. No target exists for `mii-pr-mtb-studieneinschluss-anfrage` (ServiceRequest) or `therapieempfehlung-kombination` (RequestGroup). 2027 `systemtherapie-medication-statement` adds `basedOn:therapieempfehlung` to `mii-pr-onko-therapieempfehlung-medikation`, while its `basedOn:tumorkonferenz` targets `mii-pr-onko-tumorkonferenz`, not `mii-pr-mtb-therapieplan`.

**Impact on genomDE data.** Our row (basedOn) is wrong in both versions. KDK followUp.therapies\[\].reference resolving to a MedicationRequest maps to `causedBy` and is fixable now. A reference to a study recommendation (MII LM: Referenz auf Studien-/Therapieempfehlung) has no conformant link.

**Options.**

- `causedBy` to `mii-pr-mtb-therapieempfehlung`; `basedOn:tumorkonferenz` to `mii-pr-mtb-therapieplan`
- Ballot: add `studieneinschluss-anfrage` (and the kombination RequestGroup) to `causedBy` or `basedOn`
- Accept CarePlan-only for study-based therapies (lossy)
- Emit the MedicationStatement companion with `basedOn:therapieempfehlung` (2027)

**Our proposal.** Retarget the row to `causedBy` now and keep `basedOn:tumorkonferenz` for the board decision; ballot the missing ServiceRequest/RequestGroup targets and the MedicationStatement tumorkonferenz inconsistency.

**To decide with Thomas.** Confirm `procedure-causedBy` is the intended link (his note overlooked it); how should a therapy started on a Studieneinschluss-Anfrage be linked; is the MedicationStatement `basedOn:tumorkonferenz` target intentional?

### 14. therapyResponseSource is a data source; Observation.method is mandatory

*Rows:* O 100; OI 26 · *Kind:* contradiction, decision

**Thomas' note.** Thomas: target `mii-pr-mtb-response-befund` (Observation, derived from `mii-pr-onko-verlauf`), `method` bound to `mii-vs-mtb-response-befund-beurteilungsmethode` = RECIST, RANO; value bound to `mii-vs-onko-verlauf-gesamtbeurteilung`; enum reconciliation with genomDE values needed.

**What the packages say.** `mii-pr-mtb-response-befund`, identical 2026.0.1 and 2027: base `mii-pr-onko-verlauf`; code SNOMED 396432002; `partOf` 0..* MS to `mii-pr-mtb-systemische-therapie`; `focus` 1..1 primary tumour; `Observation.method` 1..1 MS, binding required to `mii-vs-mtb-response-befund-beurteilungsmethode` (RECIST, RANO only); value\[x\]:valueCodeableConcept extensible to `mii-vs-onko-verlauf-gesamtbeurteilung`, its `coding` sliced into `coding:oBDS` (code required `mii-vs-onko-verlauf-gesamtbeurteilung`: V,T,K,P,D,B,R,Y,U,X) and `coding:MTB` (code required `mii-vs-mtb-response-befund-beurteilung`: CR, PR, MR, SD, PD, NA, NYA; slice cardinalities unverified); `derivedFrom` 0..* unconstrained; `note` 0..*. KDK `therapyResponseSource` is a free string 'Source of therapy response data'; MII's own LM `DatenquelleTherapieansprechen` 1..1 string (Arztbrief, Entlassungsbericht, Tumordokumentation) has mapping none. KDK `therapyResponse` enum PD, SD, PR, CR maps 1:1 to the MTB slice.

**Impact on genomDE data.** Our row paired a Procedure profile with an Observation element. therapyResponseSource is provenance, not the assessment method; mapping it to `method` is a semantic error. genomDE transmits no method, so the mandatory `method` cannot be filled conformantly and every response Observation fails validation.

**Options.**

- Data source to `Observation.note.text`, or `derivedFrom` (DocumentReference) when a document resource exists, or Provenance
- method: ballot 0..1, or add other/unknown to `mii-cs-mtb-response-befund-beurteilungsmethode`; interim omit (non-conformant, documented)
- value: `coding:MTB` 1:1 from PD/SD/PR/CR plus `coding:oBDS` (P,K,T,V) via map
- Fix sibling rows: therapyResponseDate to `effectiveDateTime`, prior-procedure response date off the Vortherapie profile

**Our proposal.** Move the row to `mii-pr-mtb-response-befund` with `note.text` as carrier and fix the sibling rows; file a ballot comment on `method` 1..1 and on a documented home for the data source.

**To decide with Thomas.** Agree therapyResponseSource is Datenquelle, not Beurteilungsmethode? Where should the data source live? Relax `method` to 0..1 or add unknown/other? Must `coding:oBDS` accompany `coding:MTB`?

### 15. Study recommendations: evidence grading, Z(FDA), supporting variants

*Rows:* O 206–207, 211, 218–220; OI 49–54 · *Kind:* decision

**Thomas' note.** Three notes. (1) Confirms `mii-ex-mtb-empfehlung-evidenzgraduierung` is sliced on `mii-pr-mtb-therapieempfehlung` (`extension:Evidenzgraduierung`); CS `mii-cs-mtb-empfehlung-evidenzgrad` = m1A, m1B, m1C, m2A, m2B, m2C, m3, m4, undefined; the Zusatzverweis CS exists; proposes MAPPED. (2) Gap: `studieneinschluss-anfrage.reasonReference` targets only Condition, not variant Observations; workaround `supportingInfo`; ballot candidate to extend it. (3) Confirms `extension:Prioritaet` = `mii-ex-mtb-empfehlung-prioritaet` (decimal or positiveInt); proposes MAPPED.

**What the packages say.** `mii-ex-mtb-empfehlung-evidenzgraduierung`: context RequestGroup, MedicationRequest, Observation (no ServiceRequest); value 1..1 CodeableConcept; `coding:Evidenzgrad` 1..1 (patternUri to `mii-cs-mtb-empfehlung-evidenzgrad`, nine codes covering the KDK enum 1:1); `coding:Zusatzverweis` 0..* (CS codes is, iv, Z, R; Z(FDA) appears only in Z's definition text). Sliced on `therapieempfehlung` (`extension:Evidenzgraduierung` 0..1 MS), `-kombination` and `therapeutische-implikation` only. `mii-pr-mtb-studieneinschluss-anfrage` (ServiceRequest): extension slices statusReason, Prioritaet, Publikation; `reasonReference` 0..* MS Reference(mii-pr-mtb-diagnose-primaertumor, Condition); `supportingInfo` 0..* MS Reference(Resource), open slicing, named slice `Studie`. `therapieempfehlung.reasonReference` 1..* allows Observation via slice `StuetzendeMolekulareAlteration`. `mii-ex-mtb-empfehlung-prioritaet`: context MedicationRequest, RequestGroup, ServiceRequest; value 1..1 decimal or positiveInt. All identical in 2026.0.1 and 2027.0.0-ballot.1. Our rows cite `ResearchStudy.extension` and `CarePlan.activity.detail`, wrong resource types for these ServiceRequest profiles.

**Impact on genomDE data.** Therapy evidence grades map today; study evidence grades have no conformant slot (context excludes ServiceRequest) and are lost. KDK `Z(FDA)` collapses to code `Z`. Study-supporting variants only fit an unnamed `supportingInfo` reference whose meaning is not machine-readable. Priority rows point at wrong elements, so the rank misses the profiled extension.

**Options.**

- Therapy rows: `MedicationRequest.extension:Evidenzgraduierung.valueCodeableConcept.coding:Evidenzgrad.code` and `coding:Zusatzverweis.code`; interim for Z(FDA): code `Z` plus display/text "Z (FDA)".
- Study evidence: ballot for ServiceRequest context plus an `extension:Evidenzgraduierung` slice on `studieneinschluss-anfrage`; interim MVGS extension, or carry it on the `therapeutische-implikation` Observation when a variant-level implication exists.
- Study variants: `ServiceRequest.supportingInfo` to the variant Observation now (open slicing); ballot for `reasonReference:StuetzendeMolekulareAlteration` mirroring the Therapieempfehlung.
- Priority: `extension:Prioritaet.valuePositiveInt` on ServiceRequest and MedicationRequest (not `MedicationRequest.priority`, a different concept).

**Our proposal.** Split the rows: therapy evidenceLevel and both priority rows to MAPPED with the exact slice paths now; study evidenceLevel rows GAP (ballot) with an interim MVGS extension, study variants via `supportingInfo` interim. File one MTB ballot comment: add ServiceRequest to the Evidenzgraduierung context and slice it on `studieneinschluss-anfrage`, add a distinct Zusatzverweis concept for Z(FDA), extend `reasonReference` with a StuetzendeMolekulareAlteration slice.

**To decide with Thomas.** Does he support (or will he file) the three ballot asks? Is `supportingInfo` acceptable as interim for study variants? Is `valuePositiveInt` the intended slice for an integer rank? Is the LM `EmpfohleneStudie.Evidenzgrad` meant to land in MTB or in the MVGS spec?

**Update 2026-10-10 (mapping table now differs; text above kept as discussed).** The rows are split as proposed and no longer cite `ResearchStudy.extension` / `CarePlan.activity.detail`. Therapy `evidenceLevel` / `evidenceLevelDetails[]` map to `MedicationRequest.extension:Evidenzgraduierung` (Z(FDA) as `Z` plus text; O 219–220). Both priority rows map to `extension:Prioritaet.valuePositiveInt` (O 211, 222). Study variants go to `ServiceRequest.supportingInfo` (O 218). Study `evidenceLevel` / `evidenceLevelDetails[]` (O 206–207) are not GAP: they are MAPPED to a local extension `mvgs-ex-evidence-level` that carries the MII MTB evidence code systems, because the MII extension has no ServiceRequest context. The three ballot asks are unchanged.

### 16. Recommendation type (inLabel/offLabel/compassionateUse/secPreventive/unknown) has no element

*Rows:* O 229; OI 56 · *Kind:* decision

**Thomas' note.** MTB 2027: `mii-cs-mtb-zulassungsstatus` = in-label, off-label, leitlinie; bound only in `mii-ex-mtb-leitlinie-dokumentation`, not on the Therapieempfehlung. compassionateUse, secPreventive, unknown are missing; ballot candidate MTB (Therapieempfehlung).

**What the packages say.** `mii-cs-mtb-zulassungsstatus` concepts in-label, off-label, leitlinie; `mii-vs-mtb-zulassungsstatus` includes the whole CS; identical in 2026.0.1 and 2027.0.0-ballot.1. The VS is referenced only by `mii-ex-mtb-leitlinie-dokumentation` (`extension:Zulassungsstatus.valueCodeableConcept.coding.code` 1..1, binding required; sibling sub-extension Therapielinie unsignedInt). That extension is sliced on `mii-pr-mtb-systemische-vortherapie` (`Procedure.extension:Leitlinie`) and `mii-pr-mtb-behandlungsepisode` (`supportingInfo:Vortherapie.extension:LeitlinieDokumentation`), i.e. prior therapies only; `mii-lm-mtb` places Zulassungsstatus at Behandlungsepisode.Vortherapie. `mii-pr-mtb-therapieempfehlung` extension slices in both versions: Prioritaet, Evidenzgraduierung, Publikation. KDK enum (RecommendedSystemicTherapy.type): inLabel, offLabel, compassionateUse, unknown, secPreventive; 2 of 5 map (with code-form change), 3 have no code, `leitlinie` has no KDK counterpart. MII's own `mii-lm-mvgenomseq-onkologie` Therapieempfehlung.EmpfehlungTyp lists exactly the five KDK values but has no profile mapping.

**Impact on genomDE data.** The KDK recommendation type cannot be placed on `mii-pr-mtb-therapieempfehlung` today, not even the two mappable values (inLabel, offLabel), whose codes exist only for prior therapies. The regulatory status of MTB recommendations is lost in the MII representation.

**Options.**

- Interim: MVGS-spec extension on MedicationRequest with a genomDE CS (inLabel, offLabel, compassionateUse, secPreventive, unknown).
- Ballot (a): slice `mii-ex-mtb-leitlinie-dokumentation` (`extension:Leitlinie`) onto `mii-pr-mtb-therapieempfehlung` and add compassionate-use, secondary-preventive, unknown to `mii-cs-mtb-zulassungsstatus`.
- Ballot (b): dedicated Empfehlungstyp extension as in the LM EmpfehlungTyp.
- Partial projection inLabel to in-label, offLabel to off-label, only if MII allows the Leitlinie extension on the recommendation.

**Our proposal.** Keep the coded five-value type, status GAP (ballot) with the MVGS extension as interim representation. Ballot MTB: slice a Zulassungsstatus/Empfehlungstyp extension on `mii-pr-mtb-therapieempfehlung` and add the three missing concepts.

**To decide with Thomas.** Does he prefer extending `mii-cs-mtb-zulassungsstatus` plus slicing the Leitlinie extension on the Therapieempfehlung, or a dedicated Empfehlungstyp extension per the LM? Should `leitlinie` be treated as in-label for MV GenomSeq, or is recommendation type MVGS-specific?

### 17. CNV type: undefined code system, genomDE 6 levels

*Rows:* O 134 · *Kind:* decision

**Thomas' note.** Component check: `component:variant-type` does not exist; in the MTB CNV profile the slice is `component:cnv-type` (code bwhc.de/mtb/genetics-copy-number-variant#type, valueCodeableConcept); additionally `coding-change-type` (48019-4, SO copy_number_gain/loss) is possible.

**What the packages say.** `mii-pr-mtb-copy-number-variant` slices: gene-studied, chromosome-identifier, exact-start-end, copy-number (82155-3), relative-copy-number, cna, cnb, reported-focality, cnv-type, copy-number-neutral-loh plus inherited MolGen slices; no `variant-type` in 2026.0.1 or 2027.0.0-ballot.1, so our row is wrong in both. `component:cnv-type` 0..* MS, code patternCodeableConcept system `http://bwhc.de/mtb/genetics-copy-number-variant` code `type`; value\[x\]:valueCodeableConcept 0..1 MS with no binding; no CodeSystem resource for that URI in the package. MTB examples use value system bwhc.de, code `high-level-gain` = DNPM CNVType (low-level-gain, high-level-gain, loss). `component:coding-change-type` 0..1 MS, code LOINC 48019-4, value 1..1 CodeableConcept extensible `dna-change-type-vs` (copy_number_gain SO:0001742, copy_number_loss SO:0001743 per review). Component slicing is open (value:code). KDK cnvType: completeLoss, heterozygousLoss, loss, lowLevelGain, highLevelGain, gain.

**Impact on genomDE data.** Our row targets a non-existent slice, so CNV type lands in a component no profile recognises. Three of six KDK levels (completeLoss, heterozygousLoss, gain) have no DNPM or MII code. Because `cnv-type` is unbound, validation would not catch wrong or home-made codes.

**Options.**

- `cnv-type.valueCodeableConcept` with DNPM codes (loss, low-level-gain, high-level-gain, system bwhc.de as in the MTB examples) where they exist, genomDE CS coding for all six levels alongside.
- genomDE CS only for all six levels (ordinal preserved, no DNPM interoperability).
- Additionally `coding-change-type` 48019-4 = SO copy_number_gain / copy_number_loss as binary derived value; optional `copy-number` 82155-3 when numeric.
- Ballot: MII CodeSystem/ValueSet for CNV type replacing the undefined bwhc.de URI, including the six genomDE levels.

**Our proposal.** Correct the row to `Observation.component:cnv-type.valueCodeableConcept` (DNPM codes plus genomDE CS coding) and add the derived `coding-change-type` SO coding; keep MAPPED with the note that the value is unbound and the bwhc.de CS undefined. Ballot MTB for a defined CS/VS with the six levels.

**To decide with Thomas.** Does `bwhc.de/mtb/genetics-copy-number-variant#type` have a defined value set beyond the three DNPM values? Will MII replace it with an MII CodeSystem/ValueSet in 2027 final, and can the six genomDE levels be included?

### 18. Expression level (noExpression/normal/high/low) not codable

*Rows:* O 144; OI 30 · *Kind:* decision, 2027

**Thomas' note.** `mii-pr-mtb-rna-seq` fixes code 69548-6, value required to LL1971-2 (present/absent); components only numeric (tpm, raw-counts, tissue-corrected-expression). No place for noExpression/normal/high/low; ballot candidate MTB.

**What the packages say.** `Observation.code` pattern LOINC 69548-6 (inherited from MolGen variante, both versions). value\[x\] 0..1 MS, slice `valueCodeableConcept` 0..1 binding required `http://loinc.org/vs/LL1971-2`; slicing open in the 2026 snapshots, closed in 2027 (inherited from molgen 2027 rc3) while the mtb-2027 differential still declares open. Components transcript-id (CodeableConcept), transcripts-per-million (Ratio), tissue-corrected-expression (boolean, not numeric), raw-counts, library-size, cohort-ranking (Quantity): none has a fixed code although slicing discriminates on value:code, and `mii-cs-mtb-molekulare-biomarker` has no codes for them (2026 and 2027). No expression-level concept in MTB (only `mii-vs-mtb-mmr-expression`, IHC). `Observation.interpretation` 0..* extensible base observation-interpretation (H, L, N valid). 2027 adds `mii-vs-mtb-interpretation-high-low` (H, L), required on ploidie, hrd-score, mutationslast, brcaness only; 2026 bound those to GR high-low-codes-vs, which GR 3.0.0 no longer ships. LM ExpressionsVariante.Expression exists without profile.

**Impact on genomDE data.** The four-level expressionType cannot be a coded result; only present/absent plus `interpretation` H/L/N is conformant, so noExpression becomes Absent and the exact level survives only in an unsliced component. The free-text reference fits `note` only. The six numeric component slices are not discriminable (no fixed codes).

**Options.**

- Interim (valid 2026 and 2027): `valueCodeableConcept` LL1971-2 (noExpression to Absent, else Present; LA codes unverified) plus `Observation.interpretation` H/L/N, plus an unsliced genomDE component with the exact level; reference to `note`.
- Ballot (a): bound component `expression-level` and a `reference-cohort` string component on `mii-pr-mtb-rna-seq`.
- Ballot (b): bind `interpretation` on rna-seq to `mii-vs-mtb-interpretation-high-low` extended by N and a not-detected concept.
- Second ballot item: fixed codes for the six rna-seq component slices.
- MVGS-spec fallback if MTB declines (DNPM ngs-report 2027 LM has no RNASeq results).

**Our proposal.** Status BALLOT-PENDING with the interim mapping (LL1971-2 value plus `interpretation` H/L/N plus genomDE component). File two MTB ballot items: a coded expression level with reference cohort, and fixed codes for the six undiscriminable component slices.

**To decide with Thomas.** Does MTB prefer a bound `expression-level` component or binding `interpretation` (high-low plus N, not-detected)? Is the closed value\[x\] slicing in 2027 intended (differential says open)? Will the six component slices get codes? Is H/L/N acceptable interim?

**Update 2026-10-10 (mapping table now differs; text above kept as discussed).** O 144 is MAPPED, not BALLOT-PENDING. The value is LL1971-2 (noExpression to Absent LA9634-2, normal/high/low to Present LA9633-4) and the level goes to `Observation.interpretation` H / L / N. Together these are lossless, so there is no extra genomDE component. The `reference` field goes to `Observation.note` ('Bewertungsgrundlage: …', O 150). The ballot items are unchanged.

### 19. LOH per variant has no concept on the simple variant

*Rows:* O 165; OI 35 · *Kind:* decision

**Thomas' note.** `copy-number-neutral-loh` exists in MTB 2027 only on the CNV profile, not on `mii-pr-mtb-einfache-variante`. Ballot proposal MTB: concept `loh` in the biomarker CS plus a component on the simple variant. Interim: separate biomarker Observation with `derivedFrom` to the variant.

**What the packages say.** `mii-pr-mtb-copy-number-variant.component:copy-number-neutral-loh` 0..* MS, code pattern `mii-cs-mtb-molekulare-biomarker#copy-number-neutral-loh`, valueCodeableConcept 0..1 MS (example LOINC LA33-6 Yes); identical in 2026.0.1. `mii-pr-mtb-einfache-variante` 2027 slice list (conclusion-string through gene-fusion, detection-limit) has no loh or heterozygosity slice; zero differences 2026 to 2027 apart from meta. Its `Observation.component` slicing is open (discriminator value:code), so an unsliced component validates. `mii-pr-mtb-hrd-score.component:LOH` uses NCIt C18016 Loss of Heterozygosity with valueInteger (HRD sub-score, different semantics; its NCIt system is an NCPI page URL per review). `mii-pr-mtb-molekularer-biomarker`: `code` binding extensible, `derivedFrom` 0..* MS Reference(Observation), value open. MII LM `mii-lm-mvgenomseq-onkologie` EinfacheVariante.LossOfHeterozygosity (Ja/Nein) exists without profile. KDK smallVariants\[\].loh is boolean.

**Impact on genomDE data.** The per-variant boolean has no profiled slot, so today it is either dropped or emitted in a form only we understand. Both interim forms validate, but neither is semantically machine-readable to MII consumers: an unsliced component uses a non-MII code, a separate biomarker Observation detaches the flag from the variant.

**Options.**

- On-variant unsliced component (open slicing) with code NCIt C18016 or genomDE `loh` and valueBoolean: stays 1:1 with KDK, valid today.
- Thomas' interim: separate `mii-pr-mtb-molekularer-biomarker` Observation, code `copy-number-neutral-loh` or `loh`, value boolean or Yes/No, `derivedFrom` the variant.
- Ballot: concept `loh` in `mii-cs-mtb-molekulare-biomarker` plus `component:loh` slice on `einfache-variante`; alternatively reuse NCIt C18016 as in hrd-score.
- Ballot add-on: harmonise CNV `copy-number-neutral-loh` (CodeableConcept Yes/No) with a boolean.

**Our proposal.** Map `loh` to an unsliced component on `mii-pr-mtb-einfache-variante` (NCIt C18016 plus genomDE coding, valueBoolean) as interim, status MAPPED (ballot pending), with Thomas' biomarker Observation as documented alternative. Ballot MTB for a `loh` concept and component slice.

**To decide with Thomas.** Does he accept the on-variant open component instead of a separate biomarker Observation? Which code: NCIt C18016 (already in hrd-score) or a new `loh` concept with LOINC Yes/No like copy-number-neutral-loh? Boolean or CodeableConcept value?

### 20. COSMIC SBS signatures have no concept

*Rows:* O 151–153; OI 32–33 · *Kind:* decision

**Thomas' note.** Terminology check: no codes in SNOMED, LOINC, NCIt or OLS ontologies; COSMIC is the only reference (SBS1 to SBS112), in HL7 THO only as v2-0396 entry for variants, no URI. Planned strategy: NamingSystem for the COSMIC catalogue plus empty ValueSet, catalogue version in `Coding.version` (= sbsSignatures.version), normalise KDK free text 'SBS 6' to 'SBS6'; no CS mirror (COSMIC licence). Ballot: as genomDE example in the MTB biomarker comment.

**What the packages say.** No SBS or signature concept in `mii-cs-mtb-molekulare-biomarker` (20 component codes, identical 2026 and 2027) or any MTB ValueSet; only `mii-cs-mtb-panel-capability#signature-detection` (a capability, not a result). HL7 THO 7.4.0 `v2-0396` has COSMIC-Smpl and COSMIC-Strc only; no NamingSystem mentions COSMIC. The MTB 2027 example `Observation-MII-EXA-MTB-RNA-Fusion-1` already uses system `https://cancer.sanger.ac.uk/cosmic` (code COSF1171) in `component:variation-code` 81252-9, and `mii-lm-mtb` NGSBericht.RNAFusion.COSMICID exists. `mii-pr-mtb-molekularer-biomarker` (2026 = 2027): `code` 1..1 extensible `mii-vs-mtb-molekulare-biomarker`, value\[x\] 0..1 open, `identifier` 0..*, `method` binding example (analysis method), `derivedFrom` 0..* MS. LM `mii-lm-mvgenomseq-onkologie` has SBSSignature and SBS elements without profile. KDK: name\[\] strings such as 'SBS 6', `version` string; synthetic data always 'COSMIC v3.3', names 'SBS1' to 'SBS10a'. Absence of SBS codes in SNOMED/LOINC/NCIt is Thomas' finding (unverified here).

**Impact on genomDE data.** Signatures can be emitted today as biomarker Observations whose `code` is a genomDE extension code (extensible binding permits it) and whose value is a COSMIC coding under a URI no NamingSystem defines. The current `version` row routes the catalogue version to `Observation.method`, which is the analysis method and therefore wrong.

**Options.**

- One `mii-pr-mtb-molekularer-biomarker` Observation per signature: `valueCodeableConcept.coding` with system `https://cancer.sanger.ac.uk/cosmic, code normalised 'SBS6', version from sbsSignatures\[\].version; Observation.code` genomDE `sbs-signature` under the extensible binding; `identifier` shared or suffixed per name.
- One Observation with multiple codings instead of one per signature.
- NamingSystem owner: genomDE/MVGS IG (we create it) versus MII; URI as in the MTB example versus an MII URI.
- Ballot: biomarker concept `sbs-signature` or `mutational-signature` (SBS/DBS/ID) in `mii-cs-mtb-molekulare-biomarker` so `code` validates without extension.

**Our proposal.** Adopt Thomas' NamingSystem strategy with the URI `https://cancer.sanger.ac.uk/cosmic` already used in MII's own example; one Observation per signature, `version` row moved from `Observation.method` to `coding.version`, status MAPPED. Ballot MTB for a mutational-signature biomarker concept with the genomDE example.

**To decide with Thomas.** Confirm URI `https://cancer.sanger.ac.uk/cosmic` and who owns the NamingSystem (MII or MVGS IG)? One Observation per signature or one with multiple codings? Will MTB add a mutational-signature concept to `mii-cs-mtb-molekulare-biomarker`?

### 21. Fusions: mandatory breakpoint components, unbound partner genes, intragenic SVs

*Rows:* O 178–185, 189; OI 36–43, 45 · *Kind:* decision

**Thomas' note.** Three confirmations: `mii-pr-mtb-dna-fusion` / `-rna-fusion` have `component:five-prime-gene` (plus -chromosome/-position), geneA maps to five-prime-gene, MAPPED proposed; likewise geneB to `three-prime-gene`, MAPPED proposed; `sequenceType` is a control field without own element: DNA selects dna-fusion, RNA selects rna-fusion, both present in 2027 with the same five-/three-prime components, MAPPED (profile choice).

**What the packages say.** dna-fusion: `component` 6..*; five-/three-prime-gene 1..1 MS (code pattern `mii-cs-mtb-molekulare-biomarker#five-prime-gene` / `#three-prime-gene`), -chromosome 1..1 MS, -position 1..1 MS (valueRange). rna-fusion: `component` 10..*; five-/three-prime-gene, -transcript-id, -exon-id, -position, -strand each 1..1. Every slice's value\[x\] is 0..1 and `dataAbsentReason` 0..1; only ele-1 constrains the component, so code plus dataAbsentReason satisfies the minimums. No partner-gene value slice is bound to hgnc-vs (only inherited `gene-studied`, 1..1 extensible); dna-fusion five-prime-gene.value\[x\] lacks the valueCodeableConcept slice that three-prime-gene has. Inherited alternative: `component:gene-fusion` 0..1 MS, LOINC 95123-6, value 1..1 extensible hgnc-vs, 'GENESYMBOL1::GENESYMBOL2'. Components differ between profiles (chromosome versus transcript/exon/strand). MII examples use HGNC system `http://www.genenames.org/geneId` (DNA example: no system); our lock is `http://www.genenames.org`. dnpm-lm-ngs-report (same 2027 package) has fusionPartner5prime/3prime 0..1. Profiles identical 2026.0.1 and 2027.0.0-ballot.1; our fhir_element still says `component:gene-studied`.

**Impact on genomDE data.** KDK structuralVariants carry identifier, genomicSource, geneA, geneB, structureType, description, sequenceType, localization only (synthetic data confirms no breakpoint fields). Every fusion must be padded with 4 (DNA) or 8 (RNA) dataAbsentReason-only components to validate. Partner-gene HGNC is convention only. MTB has no generic SV profile for intragenic deletions, duplications, inversions.

**Options.**

- geneA/geneB to `component:five-prime-gene` / `three-prime-gene.valueCodeableConcept.coding.{code,display,system,version}`, profile chosen by sequenceType (`meta.profile`), mandatory breakpoint slices emitted as code plus dataAbsentReason=unknown.
- Fallback: inherited `component:gene-fusion` (95123-6, 'A::B') on a variant profile, no breakpoint padding.
- Ballot MTB: relax breakpoint components to 0..1 MS (consistent with dnpm-lm-ngs-report), add valueCodeableConcept slice on dna five-prime-gene and valueRange on three-prime-position, bind all four partner-gene values to hgnc-vs, give the DNA example a system.
- Intragenic SVs: geneB repeats geneA, or `einfache-variante` with `coding-change-type` (which MII's MolGen example fills with SO:0001565 gene_fusion); needs IG clarification.

**Our proposal.** Correct the nine rows to five-/three-prime-gene with profile selection by sequenceType and documented dataAbsentReason padding, status MAPPED with validation caveat. Ballot MTB to relax the 1..1 breakpoint components, fix the partner-gene slice and binding inconsistencies, and clarify the profile for non-fusion structural variants.

**To decide with Thomas.** Is code plus dataAbsentReason on all unfillable 1..1 breakpoint slices acceptable, or will he relax them to 0..1 in 2027 final? Which HGNC system URI for MV GenomSeq: `http://www.genenames.org` or `/geneId`? Which profile carries intragenic structureType values?

### 22. Sequencing QC extension: broken context, unclear semantics, no slot for minCoverage

*Rows:* G 7, 30–33, 40; OI 76–81 · *Kind:* contradiction, decision

**Thomas' note.** Thomas (G57): MTB 2027 has `mii-ex-mtb-genomic-study-analysis-qc` on `mii-pr-mtb-genomic-study-analysis` (Procedure) with sub-extensions read-depth, read-length, sequencing-coverage (for minCoverage), sequencing-read-type (for sequencingLayout), gap-statistics, metrics-description (free text for the rest). fragmentationMethod, nonCodingVariants and percentBasesAboveQualityThreshold have no field: metrics-description or MTB ballot candidate. MolGen: GR extension genomic-study-analysis-metrics analogously.

**What the packages say.** `Procedure.extension:qc` 0..1 to `mii-ex-mtb-genomic-study-analysis-qc` exists identically in mtb 2026.0.1 and 2027.0.0-ballot.1, so it is not new. Sub-extensions, each 0..1: `read-depth`, `read-length`, `sequencing-coverage`, `gap-statistics` (valueQuantity), `metrics-description` (valueString), `sequencing-read-type` (valueCodeableConcept, no binding). 2027 types the values; slicing stays open; no sub-extension has a definition text. Context is declared as type extension, expression Extension, not Procedure (both versions). The names mirror GR 3.0.0 `genomic-study-analysis-metrics`, where read-depth is the average read depth and sequencing-coverage the percentage of studied regions sequenced, so minCoverage has no slot and the minCoverage mapping is refuted. MolGen `mii-pr-molgen-genomic-study-analysis` carries `Procedure.extension:metrics` 0..1 MS to the GR extension (read-depth, sequencing-coverage, metrics-description only); the MTB profile inherits it next to its own `:qc`.

**Impact on genomDE data.** GRZ rows 29 and 35 (meanDepthOfCoverage, targetedRegionsAboveMinCoverage) already emit `extension:qc`, while the six rows here still say no standard home with a DeviceMetric draft. Strict validators may reject the extension on Procedure. minCoverage, Q30 percent, fragmentation and nonCodingVariants are not represented today.

**Options.**

- Interim (valid against the 2026 pins): sequencingLayout to `extension:qc.extension:sequencing-read-type.valueCodeableConcept` with a genomDE-local coding; minCoverage, percentBasesAboveQualityThreshold, fragmentationMethod, nonCodingVariants as structured key=value text in `metrics-description`.
- MTB ballot: fix the context to Procedure, add definitions, bind sequencing-read-type, add min-coverage, percent-bases-above-quality (threshold plus percent), fragmentation-method, non-coding-variants.
- Disease-agnostic alternative: MolGen `extension:metrics` (GR) for the RD path; it lacks read-type, so metrics-description there.
- Keep our DeviceMetric-linked Observation draft as fallback only.

**Our proposal.** Apply the interim now, file the MTB ballot comment, and never map minCoverage to sequencing-coverage (it would collide with row 35).

**To decide with Thomas.** Agree that sequencing-coverage means percent of regions covered (GR semantics)? Which of `:qc` versus inherited `:metrics` does MTB expect? Will the context be fixed in 2027? Which CodeSystem for sequencing-read-type? May the MTB qc extension be used on the MolGen path?

### 23. Package defects: allele A/B displays swapped, NCIt system URI, ploidie interpretation, rna-seq slice codes

*Rows:* O 130; OI 28 · *Kind:* decision

**Thomas' note.** Thomas only on ploidy (G18): confirms that `mii-pr-mtb-ploidie` fixes code.coding:NCIT C18303 (DNA Ploidy Analysis), valueQuantity allowed, proposes status MAPPED. He wrote nothing on the allele displays, the NCIt system URI or the rna-seq slice codes; these are our package findings.

**What the packages say.** `mii-cs-mtb-molekulare-biomarker` (2026 = 2027): `copy-number-allele-a` displays Copy Number of Allele B and vice versa. `mii-pr-mtb-ploidie`: `Observation.code.coding:NCIT` 1..1 patternCoding system `https://nih-ncpi.github.io/ncpi-fhir-ig/CodeSystem-ncit.html` code C18303, an IG page URL rather than the canonical NCIt URI; value\[x\]:valueQuantity 0..1 MS, no unit fixed; the shipped example has value 2.4 without unit. `mii-pr-mtb-hrd-score` code is LOINC 107286-7; its `component:LOH` uses NCIt C18016 with the same page URL as system. ploidie `Observation.interpretation`: 2026 required binding to GR `high-low-codes-vs`, which GR 3.0.0 does not ship; 2027 rebinds to `mii-vs-mtb-interpretation-high-low` (H/L), the only 2026 to 2027 difference. `mii-pr-mtb-rna-seq`: six component slices (transcript-id, transcripts-per-million, tissue-corrected-expression, raw-counts, library-size, cohort-ranking) discriminate on value:code but none has a fixed or pattern code (2026 and 2027).

**Impact on genomDE data.** CNV allele counts (cna, cnb) risk swapped displays; ploidy must carry the non-canonical NCIt URI to validate and must omit `interpretation` against 2026; the rna-seq component slices are not discriminable, so slice-based validation of TPM or raw counts is unreliable.

**Options.**

- Allele displays: emit codes without display until fixed; ballot to swap the displays.
- NCIt URI: keep the profile URI as fixed so instances validate; ballot for the canonical `http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl` and UCUM code 1 on the ploidy quantity.
- Ploidy interpretation: omit at the 2026 pin, add H/L from `mii-vs-mtb-interpretation-high-low` at the 2027 pin.
- rna-seq: ballot for pattern codes on the six slices; interim rely on the required-bound LL1971-2 `valueCodeableConcept` only.

**Our proposal.** Set ploidy MAPPED as Thomas proposes (valueQuantity with UCUM 1, profile URI as fixed, no interpretation at 2026) and bundle the three defects into one MTB ballot comment.

**To decide with Thomas.** Will MTB keep the NCPI page URL as NCIt system in 2027 final or switch to the canonical URI? Does he confirm the allele display swap and the missing rna-seq slice codes as defects, and who files the comment?

### 24. Panel DeviceDefinition catalogue (2027) as home for GRZ kit names

*Rows:* G 5–6, 8–9, 11–12, 16–19, 38–39 · *Kind:* 2027 change to confirm

**Thomas' note.** Thomas wrote nothing on the GRZ kit, sequencer, pipeline and caller rows (G 5 to 6, 8 to 9, 11 to 12, 16 to 19, 38 to 39). The issue comes from our 2026 versus 2027 package diff, not from his notes.

**What the packages say.** New in mtb 2027.0.0-ballot.1: `mii-pr-mtb-panel-devicedefinition` (DeviceDefinition with `manufacturer`, `deviceName`, `version`, `type`, `capability`, `extension:geneList`), twelve DeviceDefinition catalogue entries (TSO-500, OFA, CGP, WGS and others) and `mii-cs-mtb-panel-capability` with its ValueSet; a concrete device points at a catalogue entry via `Device.definition`. MTB has had the Device profile `genomic-study-device` since 2026. `Procedure.device` does not exist in R4: `mii-pr-mtb-genomic-study-analysis` carries devices through `Procedure.extension:device` (GR `genomic-study-analysis-device` with `extension:device` to Device and `extension:function`); `focalDevice` and `usedReference` are 0..0. Our twelve MAPPED rows cite `Procedure.device(function=...)`; the function CodeSystem they name was not re-verified here.

**Impact on genomDE data.** Twelve GRZ rows (kit, sequencer, pipeline and caller names, manufacturers and versions) are MAPPED to a non-existent element, so today's output cannot validate; GRZ kit strings have no catalogue matching rule.

**Options.**

- Fix now: `Procedure.extension:device.extension:device` to a `genomic-study-device` Device carrying name, manufacturer and version; `extension:function` from the function CodeSystem (to be re-verified).
- 2027 pin: additionally `Device.definition` to `mii-pr-mtb-panel-devicedefinition` when a GRZ kitName matches one of the twelve catalogue entries; free-text Device otherwise.
- Pipelines and callers: software Device under the same extension (function to be agreed) or `Procedure.note`.
- Ask MII to extend the catalogue with the kits used in MV-GenomSeq.

**Our proposal.** Correct the twelve rows to the GR device extension now and prepare the optional `Device.definition` link for the 2027 pin, with catalogue matching defined as an MVGS-IG rule.

**To decide with Thomas.** Is the panel DeviceDefinition catalogue the intended home for GRZ kit names, who maintains the entries, and how should kits without a catalogue match and software (pipelines, callers) be represented under `genomic-study-analysis-device`?

### 25. Notes labelled 2027 describe elements identical in the 2026 packages

*Rows:* O 2–3, 41–48, 53–56, 130, 134, 144, 151–153, 165, 178–185, 189–190; OI 2–3, 5–12, 17–20, 28, 30, 32–33, 35–43, 45 · *Kind:* contradiction

**Thomas' note.** In sixteen note groups (G1, G5 to G9, G11, G18, G19, G21, G22, G26, G31 to G34) Thomas writes Check gegen MII 2027.0.0-ballot, Vorbefunde MTB 2027 or Komponenten-Check and cites `mii-pr-mtb-ngs-bericht` as Vorbefund container, `mii-pr-mtb-einfache-variante` components, CNV `cnv-type`, dna- and rna-fusion five- and three-prime-gene, ploidie, rna-seq, SBS signatures via the biomarker profile, copy-number-neutral-loh and `mii-pr-onko-weitere-klassifikationen`, which he himself marks bereits 2026.0.3.

**What the packages say.** Verified by package diff: every cited artefact has an element-identical differential in mtb 2026.0.1 versus 2027.0.0-ballot.1 and molgen 2026.0.4 versus 2027.0.0-ballot.rc3; `mii-pr-onko-weitere-klassifikationen` exists since onkologie 2026.0.3 (2027 only adds the oBDS figo hierarchy to the CS). Only two 2026 to 2027 changes touch these groups: `Observation.interpretation` on ploidie (also hrd-score, mutationslast, brcaness) rebinds from GR `high-low-codes-vs` to `mii-vs-mtb-interpretation-high-low`, and value\[x\] slicing turns closed on the `rna-seq` and `einfache-variante` snapshots (open in 2026). Remaining diffs are metadata (root element, 4.0.1 suffixes, canonical pins). Our stale slice names are wrong in both versions: `transcript-ref-seq` and `variant-type` do not exist, and `gene-studied` is the wrong slice for fusion partners (five- and three-prime-gene).

**Impact on genomDE data.** Our validation stack runs the 2026 pins, so all of these mappings are implementable now. The risk runs the other way: treating them as 2027 work delays fixing rows that are invalid today, such as `component:variant-type` or the MolGen Befundbericht used as Vorbefund container.

**Options.**

- Apply all sixteen groups as corrections against the 2026 pins now; flag only the interpretation ValueSet and the closed value\[x\] slicing as 2027 deltas.
- Wait for 2027 final before touching these rows (not recommended).
- Add a since-version column to the mapping table so future notes separate existing from new.

**Our proposal.** Treat these notes as corrections valid today, apply them against the pinned 2026 packages, and track only the two real 2027 deltas separately.

**To decide with Thomas.** Confirm that nothing else in these profiles is scheduled to change before 2027 final, and that the interpretation ValueSet and closed value\[x\] slicing are the only 2027-relevant deltas, so we implement now.

## MolGen

### 26. Variant localization (HDB-976)

*Rows:* O 142, 164, 188; R 72, 92, 110; OI 29, 34, 44, 65, 69, 73 · *Kind:* in Thomas' ballot comment

**Thomas' note.** Thomas (G20, G25, G49): target `mii-pr-molgen-molekulare-konsequenz.component:feature-consequence` (SO, extensible), one consequence Observation per variant via derivedFrom; RD codingRegion SO:0001580, splicingRegion SO:0001630, regulatoryRegion SO:0001566, intronic SO:0001627, intergenic SO:0001628; onco coding SO:0001580, inRegulatoryElements SO:0001566, notInCodingAndNotInRegulatoryElements has no single term (lossy ConceptMap in the MVGS IG). `component:transcript-ref-seq` does not exist. HDB-976 (filed 2026-10-06) proposes profile Variantenlokalisation plus ValueSet; MTB has no equivalent. No LOINC or SNOMED code.

**What the packages say.** `mii-pr-molgen-molekulare-konsequenz` (molgen 2026.0.4 = 2027 rc3, base GR molecular-consequence): `Observation.derivedFrom` 1..* MS, `derivedFrom:variant` 0..* to `.../modul-molgen/StructureDefinition/variante`; `component:feature-consequence` 0..* (not MS), value\[x\] 1..1 CodeableConcept, binding extensible GR `molecular-consequence-vs` (SO is-a SO:0001537); all five SO codes are descendants (OLS). MTB `einfache-variante`, `copy-number-variant`, `dna-fusion`, `rna-fusion` derive from that `variante` canonical, so the reference validates. `mii-pr-mtb-ngs-bericht.result` slicing is open without a consequence slice; `molekulargenetischer-befundbericht` has `result:molecular-consequence` 0..*. MTB and Onko 2027 ship no consequence or localization artefact; `einfache-variante` only has `representative-transcript-ref-seq` (LOINC 51958-7), a transcript identifier. mtb 2027 ships DNPM logical models whose `localization` elements have no FHIR mapping entry. SO system URL: GR and MTB `http://www.sequenceontology.org`, MolGen examples `http://sequenceontology.org`. HDB-976 content is unverified offline.

**Impact on genomDE data.** Six rows (onc 3, RD 3) cite a non-existent component; the RD rows also cite non-existent canonicals (`mii-pr-molgen-kopienzahlvariante`, `-strukturvariante`, `mii-pr-molgen-variante`). Localization is not emitted validly today, and the onco value notInCodingAndNotInRegulatoryElements loses information in any mapping.

**Options.**

- Interim now: one `molekulare-konsequenz` per variant, one `feature-consequence` per localization entry, two ConceptMaps in the MVGS IG; onco third value to parent SO:0001537, text-only CodeableConcept, or an MVGS-own code (extensible binding).
- MTB ballot: `result` slice for molekulare-konsequenz in `ngs-bericht` or an IG reference to the MolGen profile, citing the unmapped DNPM logical-model `localization`.
- Wait for the HDB-976 Variantenlokalisation profile (shape unknown).
- Fix the RD canonicals to `.../StructureDefinition/variante` regardless of the ballot outcome.

**Our proposal.** Implement the feature-consequence interim now (valid against molgen 2026.0.4) with the ConceptMaps in the MVGS IG, support HDB-976, and add the MTB result-slice request to the ballot.

**To decide with Thomas.** Is Variantenlokalisation a new profile or a constraint on molekulare-konsequenz, and does its ValueSet cover both enums? Which fallback for notInCodingAndNotInRegulatoryElements? Which SO system URL is authoritative? Should MTB get a result slice, and who files?

### 27. Finding category primary/incidental/candidate (HDB-976)

*Rows:* R 66, 86, 105; OI 64, 68, 72 · *Kind:* in Thomas' ballot comment

**Thomas' note.** Thomas (G47): planned strategy is a component Befundkategorie on `mii-pr-molgen-diagnostische-implikation` (component slicing open, own code in the MVGS IG as interim); the `observation-secondaryFinding` extension covers only incidental (ACMG-SF guideline codes). HDB-976 (filed 2026-10-06) proposes a module-own CodeSystem with primary-finding, secondary-finding, candidate. `Observation.note` is an emergency solution only.

**What the packages say.** `diagnostische-implikation` (canonical `.../modul-molgen/StructureDefinition/diagnostische-implikation`) and `variante`: `Observation.component` slicing rules open, discriminator value:code (verified on the 2027 rc3 files; the 2026.0.4 to 2027 diff shows no change to these profiles), so an MVGS-IG-defined component code is technically valid today. `Observation.extension:secondary-finding` 0..1 to `http://hl7.org/fhir/StructureDefinition/observation-secondaryFinding` (R4 core, both versions): value CodeableConcept, binding extensible to the `secondary-finding` ValueSet whose CodeSystem holds acmg-version1 and acmg-version2; the semantics is which SF guideline was applied, not primary versus incidental versus candidate. `Observation.note` 0..* Annotation on both profiles. MolGen 2026 and 2027 ship no CodeSystem at all (four ValueSets only), so nothing of HDB-976 is in the ballot package; its content is unverifiable offline.

**Impact on genomDE data.** Three RD rows (diagnosticSignificance on small, copy-number and structural variants: primary, incidental, candidate) fall back to free text in `Observation.note`, so the category is lost for any coded query. Like the other RD MolGen rows, they need the real canonical `.../diagnostische-implikation`.

**Options.**

- Interim: unsliced component on `diagnostische-implikation` with an MVGS-IG CodeSystem (primary, incidental, candidate), later switched to the HDB-976 MolGen CodeSystem without structural change.
- For incidental additionally populate `extension:secondary-finding`, but only when the ACMG SF guideline version is known.
- Keep `Observation.note` (lossy, not recommended).
- Place the component on `variante` instead of the implication.

**Our proposal.** Implement the interim MVGS component on `diagnostische-implikation` now, support HDB-976, and swap the component code to the MolGen CodeSystem once it is accepted.

**To decide with Thomas.** Exact canonical and code strings proposed in HDB-976, and does the component sit on `diagnostische-implikation` or `variante`? Should incidental also set `extension:secondary-finding`? Who maintains the interim MVGS CodeSystem?

**Update 2026-10-10 (mapping table now differs; text above kept as discussed).** The interim is implemented, and the impact paragraph above no longer applies. `diagnosticSignificance` on small, copy-number and structural variants (R 66, 87, 107 in our table) is an open component on `diagnostische-implikation`, code `mvgs-cs-finding-category#finding-category`, value primary / incidental / candidate, not `Observation.note`. The status stays DRAFT until HDB-976 lands. These rows cite the real `.../diagnostische-implikation` canonical.

### 28. Segregation analysis: biparental and notPerformed (HDB-976 c)

*Rows:* R 76, 97, 114; OI 67, 71, 75 · *Kind:* in Thomas' ballot comment

**Thomas' note.** Thomas (G53): target `mii-pr-molgen-variante.component:variant-inheritance` (LOINC 94186-4, extensible LL5489-1): deNovo LA26807-0, fromFather LA26321-2 Paternal, fromMother LA26320-4 Maternal, fromMotherAndFather no exact code (LA30680-5 Parental is unspecific; own code biparental allowed because extensible), notPerformed to dataAbsentReason not-performed. HDB-976 point c: define the concept biparental in the module. Not `variant-inheritance-basis` (82309-6 is the basis for allelic phase).

**What the packages say.** `variante` (molgen 2026.0.4 = 2027 rc3): `Observation.component:variant-inheritance` 0..1, code LOINC 94186-4, value\[x\] 1..1 CodeableConcept, binding extensible `http://loinc.org/vs/LL5489-1`, `dataAbsentReason` 0..1, slice short Maternal, Paternal, Unknown. Because value\[x\] is 1..1, a component carrying only `dataAbsentReason` is invalid; the 1..1 is inherited from the GR variant profile and cannot be loosened by MolGen. LL5489-1 is not shipped in any package, so membership of the LA codes in it is unverified; the four LA codes Thomas cites exist on tx.fhir.org per the review, LA4489-6 Unknown is inferred from the slice short (unverified), and no biparental concept is known. Separate slice `component:variant-inheritance-basis` 0..1 LOINC 82309-6 (extensible LL4050-2) is not the result code. No MolGen example uses 94186-4. The profile canonical is `.../StructureDefinition/variante`; our CNV and SV rows cite non-existent canonicals.

**Impact on genomDE data.** Three RD rows (segregationAnalysis on small, copy-number and structural variants) emit free text in `Observation.note`; notPerformed cannot be expressed as dataAbsentReason alone; fromMotherAndFather has no exact code; the CNV and SV rows point at invalid canonicals.

**Options.**

- notPerformed: omit the component (loses not performed), or value LA4489-6 Unknown plus `dataAbsentReason` not-performed (conformant, still lossy).
- fromMotherAndFather: LA30680-5 Parental (broadens the meaning) or an own extensible code biparental (MVGS interim, HDB-976 c).
- Ballot: value\[x\] 1..1 is GR-inherited, so ask GR and MolGen jointly or document the pattern instead.
- Keep `Observation.note` (not recommended).

**Our proposal.** Map to `component:variant-inheritance` now with the three LA codes, use an MVGS interim biparental code until HDB-976 c lands, and omit the component for notPerformed unless Thomas prefers Unknown plus dataAbsentReason.

**To decide with Thomas.** Which notPerformed pattern does Thomas prefer (omit, or Unknown plus dataAbsentReason)? Which canonical and code for biparental until HDB-976 c? Does fromMotherAndFather mean one allele from each parent or inheritance from both for a homozygous variant?

### 29. Mode of inheritance: LOINC answer codes vs HPO

*Rows:* R 73, 93, 111 · *Kind:* contradiction

**Thomas' note.** TD correction: `mii-pr-molgen-variante` has no `component:mode-of-inheritance` (79742-3). In MolGen it sits on `mii-pr-molgen-diagnostische-implikation.component:mode-of-inheritance` (GR tbd code, preferred binding to `condition-inheritance-mode-vs` = HPO: HP:0000006 AD, HP:0000007 AR, HP:0001417 X-linked, HP:0001427 mitochondrial). He adds that the LOINC LA codes in our note apply only to the MTB counterpart.

**What the packages say.** Confirmed: `variante` (2026.0.4 identical to 2027) has no mode-of-inheritance slice; LOINC 79742-3 / LL3731-8 occur in no MII package nor GR 3.0.0. `diagnostische-implikation.component:mode-of-inheritance` is 0..1, code `tbd-codes-cs#condition-inheritance` (not condition-inheritance-mode), value\[x\] 1..1 CodeableConcept, binding preferred `condition-inheritance-mode-vs` (system http://human-phenotype-ontology.org, 17 concepts incl. HP:0001419 XLR, HP:0001423 XLD, HP:0003745 sporadic, HP:0025352 typically de novo; no unknown concept). MII example diagnostische-implikation-2 uses HP:0000006. Refuted: `mii-pr-mtb-diagnostische-implikation` (2026.0.1 and 2027) carries the identical HPO-preferred binding; the LA codes are not MTB codes, merely tolerated under preferred. Nothing changed 2026 vs 2027. Distinct from `component:variant-inheritance` (94186-4, parental origin), the segregationAnalysis target.

**Impact on genomDE data.** Our three RD rows (small/CNV/SV modeOfInheritance) name the wrong profile and emit LOINC LA codes: valid under preferred, but off the MII/GR examples. KDK `unclear` has no HPO code; value\[x\] 1..1 rules out dataAbsentReason. One implication per variant via `derivedFrom` (1..*) is needed.

**Options.**

- Switch to HPO on `diagnostische-implikation.component:mode-of-inheritance` (dominant HP:0000006, recessive HP:0000007, XLinked HP:0001417, mitochondrial HP:0001427), `derivedFrom` the variante Observation; `unclear` omits the component (lossy).
- Same, but `unclear` as valueCodeableConcept data-absent-reason#unknown or an own code (preferred binding allows it).
- Same, `unclear` into `Observation.note`.
- Keep the LOINC LA codes (validate, but diverge from MII examples).
- Ballot MolGen to relax value\[x\] to 0..1 with an invariant.

**Our proposal.** Switch the three rows to HPO on diagnostische-implikation (one implication per variant, derivedFrom the variant) and keep `unclear` as a coded value under the preferred binding rather than omitting it; drop any LOINC LA mode-of-inheritance codes from the oncology tab too, since MTB has the same binding.

**To decide with Thomas.** Which MTB counterpart did TD mean, given MTB uses the same HPO binding? For `unclear` with value\[x\] 1..1: omit, coded placeholder under preferred binding, or ballot 0..1? Drop LA codes in the oncology tab as well?

**Update 2026-10-10 (mapping table now differs; text above kept as discussed).** The switch is implemented. The three `modeOfInheritance` rows (R 74, 95, 114 in our table) map to `diagnostische-implikation.component:mode-of-inheritance` with HPO (dominant HP:0000006, recessive HP:0000007, XLinked HP:0001417, mitochondrial HP:0001427) and emit no LOINC LA codes. Our `unclear` proposal (a coded placeholder) was not adopted. `unclear` gives `valueCodeableConcept.text` only, without a coding and without dataAbsentReason. The oncology table has no mode-of-inheritance row.

### 30. ACMG evidence criteria have no component

*Rows:* R 62–63, 81–82, 101–102 · *Kind:* decision

**Thomas' note.** TD's note on these rows only corrects the profile names: `mii-pr-molgen-kopienzahlvariante` and `-strukturvariante` do not exist (neither 2026.0.4 nor 2027); MolGen has only `mii-pr-molgen-variante`, generic for SNV/CNV/SV as in the GR IG. He wrote nothing about the ACMG criteria themselves.

**What the packages say.** CNV/SV correction confirmed; the only variant canonical is `.../StructureDefinition/variante`. Our target `Observation(acmg-criterion).component(strength)` is refuted: grep acmg over molgen 2026.0.4, molgen 2027, seltene 2026.0.1/2027, mtb 2027 and GR 3.0.0 finds no SD, VS, CS, component slice or extension, only narrative text in molgen-2027 examples. Component slice sets of `variante` and `diagnostische-implikation` and the VS/CS inventory are unchanged in 2027. Our reference DNPM-SE / MII Seltene is wrong: Seltene offers only `Condition.evidence` (SNOMED 106221001 plus detail to variante/implikation), a diagnosis-to-variant link, not a criteria carrier. GR-inherited `component:evidence-level` (LOINC 93044-6, example binding, PharmGKB/ClinVar star levels) exists but means something else. GR 3.0.0 absence not re-checked by the skeptic (unverified); nothing contradicts it.

**Impact on genomDE data.** Six RD rows (value plus modifier for small/CNV/SV acmgCriteria) marked MAPPED point at a pseudo-profile. KDK acmgCriteria\[\].value is mandatory, so every classified variant in genomDE RD data loses its justification (PVS1..BP7 plus strength) today. Status must drop to GAP/DRAFT.

**Options.**

- Ballot MolGen: slice `diagnostische-implikation.component:acmg-criterion` 0..*, valueCodeableConcept bound extensible/example to ClinGen https://clinicalgenome.org/codesystem/acmg-criteria (PVS1..BP7), strength modifier (pvs/ps/pm/pp/ba/bs/bp, DNPM also bm) as component extension or second coding.
- Interim MVGS-local Observation profile (code ClinGen criterion, component strength, derivedFrom variant) referenced from the implikation.
- Reuse `component:evidence-level` 93044-6 (example-bound); skeptic advises against, different semantics.
- Free text in `Observation.note` (lossy).

**Our proposal.** Retarget the six rows to `diagnostische-implikation` next to `component:clinical-significance` (53037-8) as a not-yet-profiled component, status DRAFT, and file a MolGen ballot comment for an `acmg-criterion` slice with extensible ClinGen binding plus strength modifier (to admit DNPM `bm`).

**To decide with Thomas.** Does HDB-976 already request ACMG criteria plus strength (incl. DNPM `bm`), or do we file separately? ClinGen acmg-criteria or a module-own CS? Interim MVGS Observation profile acceptable, or would MolGen tolerate codings on `component:evidence-level`?

### 31. Study design single/duo/trio has no concept

*Rows:* R 20; OI 59 · *Kind:* open, no note

**Thomas' note.** TD wrote nothing on this row; it is one of the rows he did not comment on (section E of our review, still open).

**What the packages say.** Checked against the 2027 ballot packages: no singleton/duo/trio concept in molgen-2027 or seltene-2027 (grep trio/duo/familienanalyse/singleton hits only an unrelated NBS value set). `mii-pr-molgen-anforderung-genetischer-test` (ServiceRequest) has `subject` Patient or Group and `supportingInfo:familienanamnese`, but no design code. `mii-pr-molgen-genomic-study` / `-genomic-study-analysis` extensions (method-type, focus, title, ...) carry no design concept; GR 3.0.0 `genomic-study-method-type-cs` has no singleton/duo/trio codes. 2026 packages not separately checked for this item (unverified; no such concept is known there). Upstream caveat: the DNPM rd-model export hard-codes `single`.

**Impact on genomDE data.** R 20 (case.priorRds\[\].genomicStudyType) currently targets `ServiceRequest.code`, which has no code for the design, so the value is lost. In addition the DNPM export delivers a constant `single`, so real genomDE data carry an unreliable value anyway.

**Options.**

- Interim MVGS extension `mvgs-ex-genomic-study-design` (valueCodeableConcept single/duo/trio, local CS) on `anforderung-genetischer-test` or `genomic-study-analysis`.
- Model it structurally: `ServiceRequest.subject` to a Group (index plus parents) for duo/trio, Patient for singleton.
- Ballot MolGen for an extension `genomic-study-design` (CS singleton, duo, trio, other) on genomic-study(-analysis) or the Anforderung.
- Leave unmapped until DNPM delivers a real value.

**Our proposal.** Interim MVGS extension on `anforderung-genetischer-test` with a local CS (single/duo/trio), status MAPPED interim, plus a MolGen ballot comment for an official study-design extension; flag the DNPM `single` hard-coding upstream.

**To decide with Thomas.** Where would MolGen host a study-design concept: extension on genomic-study-analysis, on the Anforderung, or Group-based subject? Fold it into HDB-976 or file separately? Is the DNPM hard-coded `single` still present in the current rd-model?

## Seltene

### 32. GMFCS (HDB-975)

*Rows:* R 6, 29; OI 58, 62 · *Kind:* in Thomas' ballot comment

**Thomas' note.** TD: ballot comment HDB-975 (Modul Seltene) filed 2026-10-06. No target profile in Seltene 2027 (ICF assessment is nearest but not equivalent); he proposes an Observation profile GMFCS with an age-independent code (SNOMED 707621005 assessment scale) and levels from LL1594-2 or a module-own CS.

**What the packages say.** Confirmed: grep gmfcs over all nine packages gives 0 hits; `mii-lm-seltene` (2027) has no GMFCS element, only `Seltene.funktionsfaehigkeit` (icfCode, beurteilungsmerkmal, erhebungsdatum); the 2026.0.1 LM has no funktionsfaehigkeit at all. `mii-pr-seltene-icf-assessment` is new in 2027: `Observation.code.coding` required binding `mii-vs-seltene-icf` (system http://hl7.org/fhir/sid/icf), Observation.value\[x\] max 0, component slices (extentOfImpairment, capacity, performance, ...) bound to BfArM icf-q-* qualifier ValueSets, so a GMFCS level I-V fits neither code nor value. HDB-975 and its wording are unverifiable offline. SNOMED 707621005, LOINC 62782-8 / 62781-0 and LL1594-2 (I LA16552-4, II LA15151-6, III LA15150-8, IV LA16556-5, V LA16558-1) appear in no MII package; the codes TD cites exist on tx.fhir.org per our terminology check.

**Impact on genomDE data.** Two rows (`case.diagnosisRd.diagnosisGmfcs`, followUp.followUpRds\[\].gmfcs) stay DRAFT on a generic Observation. Our interim code LOINC 62782-8 is scoped to ages 6-12, so for other patients the code is semantically wrong; nothing validates against a Seltene profile today.

**Options.**

- Keep generic Observation (category survey), switch code to SNOMED 707621005 now, valueCodeableConcept LL1594-2 LA codes, LOINC 62782-8 only as additional coding for ages 6-12; `effective` = diagnosis date resp. follow-up date.
- Keep LOINC 62782-8 until HDB-975 resolves (age-band issue persists).
- Pre-adopt the expected canonical (e.g. mii-pr-seltene-gmfcs) in the table so the switch is trivial.
- Module-own CS for the levels if MII prefers that over LL1594-2.

**Our proposal.** Support HDB-975; switch now to SNOMED 707621005 plus LL1594-2 on a generic survey Observation, add HDB-975 to the reference column, and retarget to the Seltene profile once released.

**To decide with Thomas.** Please share HDB-975 wording: will `Observation.code` be SNOMED 707621005 or LOINC, and values LL1594-2 or a module CS? Expected in 2027 final or 2028? Pre-adopt a canonical now? Diagnosis vs follow-up GMFCS only via `effective`/encounter?

### 33. Hospitalisation duration and periods bands (HDB-975)

*Rows:* R 22–23; OI 60–61 · *Kind:* in Thomas' ballot comment

**Thomas' note.** TD: ballot comment HDB-975 (Modul Seltene) filed 2026-10-06. No target profile and no concept in the LM `mii-lm-seltene`; he proposes Observation profile(s) with valueCodeableConcept and a module-own CS for the bands. Until then: generic Observation.

**What the packages say.** Confirmed: the `mii-lm-seltene` 2027 differential (anamneseUndDiagnostik, koerperlicheUntersuchung, persoenlicheInfosIndexpatient, familienanamnese, perinatal, funktionsfaehigkeit, registerteilnahme, therapieForschung) has no hospitalisation element; grep hospitali/stationär in seltene 2026.0.1 and 2027 finds only descriptive text in `mii-pr-seltene-therapie-durchgefuehrt` and example Encounters. No Seltene Observation profile with a free valueCodeableConcept exists (`hpo-assessment` is HPO-bound, `icf-assessment` forbids value\[x\]). KDK `PriorRd.hospitalizationDuration` enum none/upToFive/upToFifteen/upToFifty/moreThanFifty/unknown (estimated inpatient pre-therapy in days); `hospitalizationPeriods` enum none/upToFive/upToTen/upToFifteen/moreThanFifteen/unknown (inpatient treatments in the last five years): two different enums. HDB-975 unverifiable offline; same ticket as GMFCS, so presumably bundled.

**Impact on genomDE data.** Two rows (R 22–23) stay DRAFT on a generic Observation with two genomDE-local CodeSystems: representable, but validating against no MII profile and using codes MII does not know. A single shared CS would conflate the two enums.

**Options.**

- Keep generic Observation (category survey), `code` = genomDE-local code (hospitalization-duration-5y-days resp. inpatient-treatments-5y-count), valueCodeableConcept from TWO local CSs with codes = KDK literals, `effective` = case date.
- Encode bands as valueRange/valueQuantity (loses none/unknown, invents boundaries).
- Wait for the HDB-975 profiles with module CS; leave rows unmapped.
- MVGS-IG owns the two band CSs and MII adopts them.

**Our proposal.** Keep the interim generic Observation with two local band CodeSystems (literals = KDK enum), add HDB-975 to the reference column, and retarget once Seltene ships the profile(s) and CS.

**To decide with Thomas.** Does HDB-975 cover both items with two separate ValueSets mirroring the KDK literals 1:1? Will `Observation.code` be a module CS code or SNOMED/LOINC? 2027 final or later; if later, should the MVGS IG define the interim CS for MII to adopt?

### 34. Therapy strategy 'other' unreachable for medication; medication/non-medication split

*Rows:* R 129 · *Kind:* decision

**Thomas' note.** TD confirms Seltene 2027: CS `mii-cs-seltene-therapieempfehlung-strategie` = systemic-medication, targeted-medication, prevention-medication, gene-therapy, prophylactic, early-detection, combination, nutrition, other (1:1 to the KDK enum); ValueSets split medicinal vs non-medicinal.

**What the packages say.** CS confirmed, 9 codes, identical in 2026.0.1 (not a 2027 change). KDK enum systemicMedication, targetedMedication, preventionMedication, genetic, prophylactic, earlyDetection, combination, nutrition, other: 1:1, with genetic = gene-therapy (DNPM display Gentherapie). VS `...-strategie-medikamentoes` = systemic-medication, targeted-medication, prevention-medication, gene-therapy, combination, required on `mii-pr-seltene-therapieempfehlung` `MedicationRequest.category:MVGenomSeqTherapieStrategie` (0..1, coding 1..1); VS `...-nicht-medikamentoes` = prophylactic, early-detection, nutrition, other, required on `mii-pr-seltene-therapieempfehlung-nicht-medikamentoes` `ServiceRequest.category:MVGenomSeqTherapieStrategie` (0..1). 2027 fixes coding.system via patternUri. Refuted: our row targeted `category:MVGenomSeqTherapieTyp`, whose CS `mii-cs-seltene-therapieempfehlung-typ` is causal/symptomatic (KDK `type`), and called genetic non-medication. `mii-pr-seltene-therapieempfehlung-kombination` (RequestGroup) has no strategy slice. 2027 removed `mii-ex-seltene-empfehlung-evidenzgraduierung`.

**Impact on genomDE data.** R 129 maps to the wrong slice and misclassifies `genetic`. After the fix a KDK recommendation with strategy `other` that is a medication cannot carry its strategy (required binding; slice 0..1, so omission validates but loses it); `combination` placement is ambiguous.

**Options.**

- Split by VS: five medication strategies to the MedicationRequest slice; prophylactic/earlyDetection/nutrition/other to the ServiceRequest slice; medicinal `other` omits the category (lossy) or is modelled as ServiceRequest.
- Ballot Seltene: add `other` to the medikamentoes VS, or bind both slices to the full `mii-vs-seltene-therapieempfehlung-strategie`.
- `combination`: category on member MedicationRequests vs on the RequestGroup (no slice today; needs ballot).
- Add a separate row for KDK `type` (causal/symptomatic) to `category:MVGenomSeqTherapieTyp`.

**Our proposal.** Correct R 129 to the strategy slice split by VS membership (status MAPPED, CS unchanged 2026/2027), add a row for KDK type to `category:MVGenomSeqTherapieTyp`, and file an optional Seltene ballot note adding `other` to the medicinal VS.

**To decide with Thomas.** How should a medicinal `other` strategy be represented? `combination` on the RequestGroup or on member MedicationRequests? Where do KDK strategyOther/strategyCombination free text and the evidence level go after 2027 dropped the Evidenzgraduierung extension?

## Consent

### 35. MV-GenomSeq consent domains cannot be expressed

*Rows:* O 112; R 46; G 49; OI 27, 63, 82 · *Kind:* contradiction, decision

**Thomas' note.** TD: the Policy CodeSystem is unchanged in 2027 (29 concepts); the OIDs ...24.5.3.8/.2/.6 exist in no version; MV-GenomSeq domains are still missing, hence a ballot candidate for Modul Consent, with an open question on how codes get registered.

**What the packages say.** `MiiConsentPolicyCodeSystem` urn:oid:2.16.840.1.113883.3.1937.777.24.5.3 v1.1.0 (consent 2027.0.0-ballot.rc1, dated 2025-12-11, before the 2026.0.0 release): 29 top-level concepts (TD's count), declared count 101, 124 concepts listed; unchanged vs 2026 (byte identity unprovable, no 2026 package on disk; cached 1.0.5 from 2025.0.1 has 66). Refuted: ...24.5.3.2 IDAT erheben, .6 MDAT erheben, .8 MDAT wissenschaftlich nutzen exist in 1.0.5 and 1.1.0 (children of .1) and are used in the package's own Broad-Consent examples; they are IDAT/MDAT purposes, not MV domains. Confirmed: no concept for mvSequencing/reIdentification/caseIdentification (grep genom/modellvorhaben/mvgs: 0 hits); `Profile_MII_Consent_Einwilligung` 1.1.0 `Consent.provision.provision.code` 1..*, required binding `mii-vs-consent-policy` (only that OID system), so any unregistered code fails. `provision.period.end` no longer mandatory since 2026.0.0.

**Impact on genomDE data.** Three rows (KDK onc/RD metaData.mvConsent.scope\[\].domain, GRZ donors\[\].mvConsent.scope\[\].domain) marked MAPPED are semantically wrong, and the mapper emits literal enum strings under the OID system: every genomDE MV consent fails the required binding today. Status to DRAFT.

**Options.**

- Separate Consent for the MV Teilnahmeerklaerung: `policy.uri` = MV URI (TBD), `provision.type permit/deny from scope\[\].type, provision.period.start from scope\[\].date, provision.provision.code` from a genomDE-local placeholder CS until registration (non-conformant to mii-pr-consent-einwilligung meanwhile).
- Ballot Consent: register three MV-GenomSeq policy codes (own top-level group) under the ...24.5.3 arc plus a version-modules entry.
- Separate MVGS CodeSystem/OID shipped by the MVGS IG.
- Keep the .2/.6/.8 mapping (rejected: wrong semantics).

**Our proposal.** Drop the .2/.6/.8 mapping, build a separate MV Consent with a placeholder MVGS policy CS (status DRAFT), and file a Consent ballot comment requesting registration of the three MV-GenomSeq policies under the existing OID arc.

**To decide with Thomas.** Registration path: new codes under ...24.5.3 (own top-level group) or a separate CS/OID, and who files (AG Consent/TMF), by when? Which `policy.uri` identifies the MV Teilnahmeerklaerung? Must the MV Consent satisfy mii-pr-consent-einwilligung meanwhile? Note: .2/.6/.8 do exist.

**Update 2026-10-10 (mapping table now differs; text above kept as discussed).** The .2/.6/.8 mapping is dropped. The three `scope[].domain` rows (O 112, R 46, G 49) are MAPPED, not DRAFT, to the local code system `mvgs-cs-mv-consent-domain` (mvSequencing / reIdentification / caseIdentification, 1:1) in the local Consent profile `mvgs-consent`. The declaration name and version go to `Consent.policyRule.text`, since no policy URI exists. The status DRAFT in this section was our proposal, not Thomas': his note asks for a Consent ballot candidate and how codes get registered. The registration questions are unchanged (ballot CONSENT-1).

## Cross-cutting questions

1. Who files the ballot comments, we or you? Can we see the HDB-975/976 texts to align ours?
2. HGVS strings: KDK gives bare `c.` / `g.` / `p.V600E`; must they be prefixed with transcript / NC_ accession and normalised, given that GR `hgvs-vs` accepts any varnomen coding?
   *Update 2026-10-10:* the premise is wrong. tx.fhir.org checks varnomen codings and rejects bare strings without a reference sequence (`c.181C>A`, `p.Gln61Lys`), so `hgvs-vs` does not accept just any varnomen coding. The converter qualifies them with the versioned transcript where the input allows it and otherwise reports them as source data quality (REPRESENTATIONS #43). The question to Thomas is now only whether qualification and normalisation are the sender's job.
3. Which terminology server should implementers validate German terminologies against (ICD-O-3 topography becomes a required binding in 2027; tx.fhir.org cannot)?
4. Should our mapping table feed `mii-lm-mvgenomseq-onkologie` and `mii-cm-onkologie-to-mvgenomseq`?
5. Identity and linkage rules for MV-GenomSeq bundles: one Patient per donor, Specimen to donor, report to result, Encounter versus EpisodeOfCare.
6. Package switch: when will 2027.0.0 be final, and will `molgen` be pinned to a later ballot than `2027.0.0-ballot.1` (newest ballot is `rc3`)?
