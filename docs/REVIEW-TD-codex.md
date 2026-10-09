**1. Findings, most severe first**

Package filenames below refer to the supplied version directories. These are static package/schema findings; I ran no validation tests and changed no files. Live tx.fhir.org/OLS rechecks were **UNCHECKED** because requests failed.

1. **BLOCKER — Headline 1, C, D: “55 notes hold identically” is false.**

   **Evidence:** `StructureDefinition-mii-pr-onko-diagnose-primaertumor.json:Condition.extension:occurredFollowing.value[x]:valueReference` permits only `fruehere-tumorerkrankung` in 2026; 2027 adds `diagnose-primaertumor`. The report’s follow-up primary tumour → initial primary tumour link therefore encounters a target-profile mismatch in 2026.

   Other material changes include MTB `rna-seq` and `einfache-variante:Observation.value[x].slicing.rules`, **open → closed** in the snapshots; RNA’s 2027 differential still says **open**. MTB `ploidie`, `hrd-score`, `mutationslast` and `brcaness:Observation.interpretation.binding` also switch to the new `mii-vs-mtb-interpretation-high-low`.

   **Consequence / bites:** real primary-to-primary references are affected; alternative value types depend on actual payloads and snapshot handling. Even before these MTB changes, **G2, G3, G4, G13 and G14** prevent a literal “55 identical.”

   **Corrected statement:** many corrections apply in 2026, but the migration includes additional reference constraints, value constraints and terminology repairs.

   The eight added Onko SDs are:

   | SD filename stem | Relevance |
   |---|---|
   | `mii-ex-onko-nebenwirkung-ctcae-version` | Adverse-event version; none of the named gaps. |
   | `mii-ex-onko-tnm-a-praefix` | TNM autopsy modifier. |
   | `mii-ex-onko-tnm-r-praefix` | TNM recurrence modifier. |
   | `mii-ex-onko-tnm-y-praefix` | TNM treatment modifier. |
   | `mii-ex-onko-transformation-von` | Tumour transformation, not a metachronous boolean. |
   | `mii-pr-onko-prostate-gleason-score-gesamt` | Total Gleason score. |
   | `mii-pr-onko-tnm-klassifikation-synthetisiert` | Aggregated TNM with provenance. |
   | `mii-pr-onko-tumormarker` | Tumour-marker observation; not a complete preventive-measure model. |

   None directly closes diagnosticAssessment, recommendation therapy type, follow-up ECOG or suitableInterventions flags.

2. **MAJOR — Tally and A/B: “BALLOT” conflates unavailable representation with missing standardization.**

   **Evidence, already in MTB 2026.0.1:**

   | Item | Existing carrier and constraint |
   |---|---|
   | G5 complexVariants | `…ngs-bericht.json:DiagnosticReport.conclusion`, `0..1 string`; `effective[x]` also permits dateTime. |
   | G26 LOH | `…einfache-variante.json:Observation.component`, **open** slicing. |
   | G37 study variants | `…studieneinschluss-anfrage.json:ServiceRequest.supportingInfo`, `0..* Reference(Resource)`, open slicing. |
   | G38 therapeuticStrategy | `…therapieempfehlung.json:MedicationRequest.category`, example binding; or `…therapieempfehlung-kombination.json:RequestGroup.code`, explicitly defined for therapy classification. |
   | G21 expression interpretation | `…rna-seq.json:Observation.interpretation`, extensible binding permitting H/L/N. |

   **Consequence / bites:** real mappings could be unnecessarily deferred. Missing MustSupport does not prohibit an element; it concerns implementation obligations. [FHIR R4 MustSupport](https://hl7.org/fhir/R4/profiling.html#mustsupport)

   **Corrected statement:** these are available representations, sometimes requiring local conventions and additional resource assembly. Ballots can improve interoperability, but **16 is not a demonstrated count of representation blockers**. A replacement tally needs explicit G1–G57 assignments, including mixed groups.

3. **MAJOR — A, MolGen canonicals: the blanket repair still leaves two resource/profile mismatches.**

   **Evidence:** [RD CSV:18](/Users/kohlbach/Claude/MII/genomDE2FHIR/mapping/mapping_kdk_rarediseases.csv:18) and line 19 map `diagnosticDate` and `diagnosticResult` to `DiagnosticReport.effectiveDateTime` and `.conclusion`, while naming the variant profile. Neither proposed replacement—`/variante` nor `/diagnostische-implikation`—profiles a DiagnosticReport.

   Both packages’ `StructureDefinition-mii-pr-molgen-molekulargenetischer-befundbericht.json:url` instead ends **`/molekulargenetischer-befundbericht`**.

   **Consequence / bites:** real prior-RD findings remain assigned to the wrong resource profile after applying A literally.

   **Corrected statement:** repair profile selection as well as canonical spelling; these two rows need the molecular genetic report profile.

4. **MAJOR — A/B: two extension recommendations ignore context constraints.**

   **Evidence:** in both MTB versions:

   - `StructureDefinition-mii-ex-mtb-genomic-study-analysis-qc.json:context` permits nesting within an **Extension**, while `…genomic-study-analysis.json:Procedure.extension:qc` places it on a Procedure.
   - `StructureDefinition-mii-ex-mtb-empfehlung-evidenzgraduierung.json:context` permits **RequestGroup, MedicationRequest and Observation**, excluding ServiceRequest.

   **Consequence / bites:** real QC payloads encounter the package’s context inconsistency; adding the proposed study-evidence slice alone still leaves evidence extensions outside their allowed context.

   **Corrected statement:** QC cannot be advertised as an unconditional “valid against pinned 2026” fix while this defect remains unresolved. The study-evidence ballot must request **context expansion and the profile slice**.

5. **MAJOR — A, inheritance: structurally legal fallbacks silently lose known information.**

   **Evidence:** MolGen `…diagnostische-implikation.json:Observation.component:mode-of-inheritance.value[x]` has a **preferred** binding. Thus `unclear` need not disappear, and LOINC answers are not validation-invalid merely because HPO is preferred.

   `…variante.json:Observation.component:variant-inheritance.value[x]` is extensible. `notPerformed → Unknown` loses whether testing happened; `fromMotherAndFather → Parental` broadens a known biparental result. LOINC defines Parental as maternal and/or paternal, intended when the specific result cannot be reported. [LOINC LL5489-1](https://loinc.org/LL5489-1)

   **Consequence / bites:** demonstrated in the repository’s RD fixture ending `…F6566.json`, lines 147, 181 and 297: biparental, notPerformed and unclear occur.

   **Corrected statement:** optional-component omission is permitted, but is a lossy policy choice. Preserve explicit distinctions with suitable code/text/extension; do not equate successful validation with faithful mapping.

6. **MAJOR — B/F TNM: the unmatched-code argument uses the wrong direction and an inaccurate aggregate.**

   **Evidence:** `ConceptMap-mii-cm-onko-tnm-uicc-sct-clinical.json:group.element` has **131 rows, 38 unmatched**; the pathological map has **131 rows, 39 unmatched**. There are **40 distinct unmatched codes**, with 37 shared. Pathological `N1mi` **does** map, to SNOMED `1352620005`.

   **Consequence / bites:** this can misdirect real SNOMED-input conversion. Missing targets for **UICC → SNOMED** do not establish missing UICC values for **SNOMED → UICC**.

   **Corrected statement:** audit inverse coverage and ambiguity against incoming SNOMED codes, including the yc/yp/rc/rp hierarchies included by the 2027 category ValueSets. The report has not established that coverage.

7. **MAJOR — B/E: diagnosticAssessment is confused with germlineDiagnoses.**

   **Evidence:** [OncologyCase.json:242](/Users/kohlbach/Claude/MII/genomDE2FHIR/schemas/kdk/OncologyCase.json:242) defines assessment states: no, suspected, further diagnostics recommended, confirmed and partial genetic diagnosis. `germlineDiagnoses` is a separate coded-diagnosis field. The LM’s cited `…Diagnose.Keimbahndiagnose` describes that latter concept.

   **Consequence / bites:** real assessment states would be discussed or mapped as diagnoses, and the ballot justification cites the wrong field. The same assessment enum also exists in RareDiseasesCase.

   **Corrected statement:** assess the diagnostic-evaluation enum independently; the LM’s “no direct match” for Keimbahndiagnose does not prove this gap.

8. **MINOR — A/C/D: source-value coverage remains incomplete.**

   **Evidence:**

   - [OncologyMolecular.json:343](/Users/kohlbach/Claude/MII/genomDE2FHIR/schemas/kdk/OncologyMolecular.json:343) includes **noExpression**; H/L/N covers only three of four expression states.
   - [OncologyCase.json:266](/Users/kohlbach/Claude/MII/genomDE2FHIR/schemas/kdk/OncologyCase.json:266) includes prior-diagnostic type **none**. D’s “only single-gene is missing” omits that branch; the GR method CS has no `none`.
   - `OncologyFollowUp.json:$defs.FollowUpOd` requires the metachronous boolean but does not require the accompanying diagnosis array when it is true.

   **Consequence / bites:** schema-valid inputs can lose absence states or cause an unjustified diagnostic resource to be manufactured. The metachronous edge case is schema-demonstrated, not fixture-demonstrated.

   **Corrected statement:** define noExpression and no-diagnostics explicitly. Replace the metachronous **⇔** rule with conditional derivation plus a way to preserve the boolean when linked diagnoses are unavailable; absence of a Condition does not itself encode false.

9. **MINOR — A/G: dedicated 2027 slices are mistaken for first-time representability.**

   **Evidence:** Onko 2026 `…allgemeiner-leistungszustand-ecog.json:Observation.value[x].coding:loinc` is already **0..***; 2027 adds a **required binding**, not required occurrence. `Observation.focus` already exists in 2026; 2027 narrows its target and marks it MS.

   Likewise 2026 TNM category `value[x]` is a UICC-bound CodeableConcept with unsliced `coding 0..*`: a suitable UICC coding can coexist with the original SNOMED coding.

   **Consequence / bites:** implementers could unnecessarily wait for 2027 or fabricate a LOINC value for unknown ECOG.

   **Corrected statement:** 2027 formalizes these representations. ECOG LOINC remains optional; TNM dual coding was already possible, although the 2027 SCT slices and constraints are new.

10. **MINOR — Headline 4/B: unmapped follow-up and plan blocks are not defects of this ConceptMap’s declared scope.**

    **Evidence:** `ConceptMap-mii-cm-onkologie-to-mvgenomseq.json:description` explicitly limits itself to **OncologyCase.json**, excludes OncologyPlan/OncologyFollowUp/OncologyMolecular and assigns those areas to MTB.

    **Consequence / bites:** process-level rather than direct data corruption: the ballot bundles genuine defects with a scope-expansion request.

    **Corrected statement:** the TNM destinations and terminology-system mix-up are defects; additional block coverage is a cross-module specification task.

11. **MINOR — G: readiness claims exceed the demonstrated package evidence.**

    **Evidence:** both MTB `package.json` files already depend on **GR 3.0.0**; it is not a new 2027 dependency. The `.1` versus MolGen `.rc3` mismatch is correctly mentioned, but loadability does not establish a validated dependency set.

    The mapping tables also leave assembly decisions beyond terminology checking: [GRZ CSV:2](/Users/kohlbach/Claude/MII/genomDE2FHIR/mapping/mapping_grz.csv:2) uses donor pseudonyms including `index`; specimen identifiers and donor relationships appear separately at lines 4, 10 and 52.

    **Consequence / bites:** real multi-donor and repeated-submission data require scoped identities and consistent references; row-level conformance cannot establish those properties.

    **Corrected statement:** distinguish package inspection from executed validation. The MVGS specification still needs per-stream Patient identity, Specimen→donor and report→result linkage, reference resolution, and Encounter/EpisodeOfCare assembly rules. Do not infer cross-stream identity from TAN-C/TAN-G.

12. **NIT — Headline counts and “fail today” wording need tightening.**

    **Evidence:** the seven named stale slices occur on **28 rows: oncology 15, RD 13, GRZ 0**. There are **57 invalid MolGen canonical entries**, correctly split 22/19/16, but **61 MolGen-labelled RD rows** including four ServiceRequest placeholders.

    **Consequence / bites:** reporting precision only; the canonical defects themselves affect real implementations.

    **Corrected statement:** “57 mapping rows contain invalid target canonicals,” not demonstrated runtime failure of 57 resources. `td_groups.json` does confirm **57 groups covering 133 rows**.

**2. Claims checked and found correct**

- MolGen’s 22 SD URLs are unchanged across the supplied versions; generic `variante` exists, separate MolGen CNV/SV profiles do not, and oncology/GRZ do not repeat the same canonical-URL bug.
- The four examined MolGen component slices are optional, their values mandatory; DAR-only is invalid, while omitting the whole component survives obs-6, obs-7 and ele-1.
- ECOG value and oBDS coding are mandatory; `U` means unknown, and the ECOG ConceptMap lacks 5.
- Fusion breakpoint values and their nested type slices are optional despite mandatory components; correctly coded DAR-only components have no identified structural blocker.
- G15’s `causedBy` reference to Therapieempfehlung exists in both MTB versions.
- G16 is correct: the schema defines therapyResponseSource as the source of response data, not RECIST/RANO.
- G12’s ValueSet includes the whole GR method CS; G50’s MTB binding is the same preferred HPO binding.
- G57 correctly distinguishes GR percentage coverage from mean read depth; neither directly represents minimum coverage.
- Consent `.2/.6/.8` exist and examples use them for IDAT/MDAT purposes; the supplied CS contains no MV-GenomSeq concept and does not establish equivalent mappings for the three source domains.
- TNM 2027 SCT slices are `0..1`, UICC slices `1..1`; source Coding.version is not TNM edition.
- The four TNM→ECOG destinations, `33732-9` labelled SNOMED, and empty Condition ConceptMap are real artefact defects.
- Seltene strategy CS/VS compositions are unchanged; its added ValueSets do not supply GMFCS or hospitalization bands.
- MTB’s three new DNPM logical models are not resource profiles; new panel artefacts do not close the cited expression/LOH/study-evidence gaps.
- HGNC `http://www.genenames.org` is supported by GR’s `hgnc-vs`; its description additionally requires the `HGNC:` prefix on gene IDs.

**3. Verdict**

Most canonical and component repairs predate 2027, but “only TNM/ECOG/category; 55 identical” is false.  
“31 corrections valid against 2026” is not established: the proposed repairs include unresolved context defects, wrong resource profiles and lossy transformations.  
“16 ballot items” mixes genuine constraints with already available representations and standardization requests, so the tally needs reclassification before it guides implementation or Friday’s discussion.
