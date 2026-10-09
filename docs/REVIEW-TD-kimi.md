• I'll attack this systematically by dispatching parallel read-only verification agents against the package evidence, then synthesize.

• All 10 agents returned. A few cross-checks remain where agents disagreed or left gaps — I'll verify those directly.

• All verification is done — 10 read-only agents plus direct spot-checks where they disagreed. No files were touched. Here is the review.

  # Adversarial review: docs/REVIEW-TD-2026-10-06.md

  ## 1. Findings (most severe first)

  No BLOCKER found — the report's core conclusions survived every check I ran. The following are MAJOR/MINOR/NIT.

  **MAJOR — Localization row (section A): the proposed SO codes are all outside the bound ValueSet.**
  Report: localization → `molekulare-konsequenz.component:feature-consequence` "(SO, extensible)" with SO:0001580/0001630/0001566/0001627/0001628, filed under "fix now (valid against 2026)".
  Evidence: `ValueSet-molecular-consequence-vs.json` (GR 3.0.0) compose = `concept is-a SO:0001537`; OLS: **SO:0001537 = structural_variant**. The proposed codes (coding_region_variant, splice_site/regulatory/intron/intergenic variants) are sequence-variant descendants, not structural variants — every one falls outside the VS. Extensible binding means this validates with at most a warning, so "validates" is technically true, but the row is presented as a clean correction while in fact 8 of 8 proposed codes rely on the extensibility escape hatch — exactly what TD could push back on.
  Bites on real data: yes (warning on every localized variant), but non-blocking. Corrected statement: feature-consequence is the right slot, but the bound VS covers only structural variants; the SO localization codes are out-of-VS extensions — this strengthens routing the terminology to HDB-976/MVGS rather than presenting it as settled.

  **MINOR — TNM unmapped counts are wrong (section B, TNM ask).**
  Report: "38 UICC codes incl. L/V/Pn/S, MX, N1mi have no SNOMED map".
  Evidence: `ConceptMap-mii-cm-onko-tnm-uicc-sct-clinical.json`: 131 source concepts, **38 unmatched**; `...-pathological.json`: 131 source, **39 unmatched**. N1mi **is** mapped in the pathological map; the pathological map instead leaves **M0 and T3e** unmapped. L/V/Pn/S are standalone categories, not prefixes. Both ConceptMaps exist identically in onkologie-2026.0.3 (so this is not a 2027 gap at all — which actually helps the ballot case). Corrected: "38 (clinical) / 39 (pathological) of 131 UICC codes unmapped, incl. MX, M0 (path.), T3e (path.), L/V/Pn/S categories."

  **MINOR — "only MTB has [CNV/SV profiles]" is half wrong (headline + section A, MolGen canonicals row).**
  Evidence: MTB (2026.0.1 and 2027) has `mii-pr-mtb-copy-number-variant` but **no structural-variant profile**; SVs are covered only by `mii-pr-mtb-dna-fusion`/`rna-fusion` (agent check, full SD listing). Corrected: "MolGen has no CNV/SV profiles; MTB has a CNV profile only."

  **MINOR — Fusion SO:0001565 example is misattributed (section A, Fusions; question F7).**
  Report: structureType→coding-change-type "conflicts with MII's own example (SO:0001565 gene_fusion in the single 0..1 slot)".
  Evidence: no MTB fusion example contains coding-change-type at all (2027 `Observation-MII-EXA-MTB-{DNA,RNA}-Fusion-1.json`; grep for 0001565 across both MTB packages: zero hits). The SO:0001565 example is a **MolGen variante** example — `molgen-2026.0.4` and `molgen-2027.0.0-ballot.rc3` `examples/Observation-mii-exa-molgen-variante-fgfr2-fusion.json`, component 48019-4 = SO:0001565. The substantive conflict (single 0..1 slot, MII's own usage) is real and the Friday question stands, but it's a MolGen-variante example, not a fusion-profile example. Side note: that example's meta.profile uses the correct short canonical `…/StructureDefinition/variante` — corroborating the report's canonical-bug claim.

  **MINOR — TNM "keep coding:uicc 1..1" misdescribes 2026 (section A, TNM row).**
  Evidence: `StructureDefinition-mii-pr-onko-tnm-t-kategorie.json`: in 2026.0.3 `value.coding` is unsliced 0..* with the required UICC binding on `value[x]` itself; the `coding:uicc` **1..1 slice is new in 2027**, alongside `coding:snomed-ct` 0..1 (both slices required-bound). Net effect on the mapping argument is unchanged, but the report's framing ("2027 keeps uicc 1..1") understates that 2027 *introduced* the hard UICC requirement — which is precisely what the ballot ask (B, "allow coding:uicc 0..1") wants rolled back.

  **MINOR — NCIt URI claim wrong for hrd-score (section B, QC/defects).**
  Report: "NCIt system URI in ploidie/hrd-score is an NCPI page URL".
  Evidence: true only for `mii-pr-mtb-ploidie` (`Observation.code.coding:NCIT` pattern system `https://nih-ncpi.github.io/ncpi-fhir-ig/CodeSystem-ncit.html`, C18303 — verified). `mii-pr-mtb-hrd-score` uses **LOINC 107286-7**, no NCIt anywhere. Corrected: drop hrd-score from that ballot line.

  **MINOR — COSMIC "NamingSystem" does not exist (section A, MTB molecular).**
  Report: "SBS signatures → COSMIC NamingSystem `https://cancer.sanger.ac.uk/cosmic` (already in an MII example)".
  Evidence: the URI appears only as a raw coding system string in one example (`Observation-MII-EXA-MTB-RNA-Fusion-1.json`, code COSF1171, both MTB versions). **No NamingSystem resource** for COSMIC exists in any package (MTB ships only nct/drks/eudract NamingSystems). Section C correctly lists COSMIC under "local NamingSystems to create", so this is an internal inconsistency/over-claim in section A. Theoretical today; matters when someone goes looking for the NamingSystem.

  **MINOR — rna-seq details (section B, CNV/expression/LOH/SBS).**
  Report: "value closed to LL1971-2, components numeric and without fixed codes". Evidence: `Observation.interpretation` is **extensible** → base HL7 observation-interpretation (H/L/N validate today, both versions — the interim mapping is solid); the LL1971-2 required binding is on the `valueCodeableConcept` slice only, and value[x] type-slicing is open. Component `tissue-corrected-expression` is **boolean**, not numeric (that's TD's G21 error, but the report's ballot text repeats the "numeric" framing). Also unmentioned: 2027 adds `mii-vs-mtb-interpretation-high-low`, newly bound on ploidie/hrd-score/mutationslast/brcaness — a 2026→2027 change the "identical in 2026" headline glosses over (no current row affected → theoretical).

  **NIT — RequestGroup.code binding (section A, Onko row).** Bound **preferred** → `mii-vs-onko-therapieempfehlung-typ` (which includes the CS), not "CS mii-cs-onko-therapie-typ" directly. Advisory either way; mapping validates.

  **NIT — stale-slice count.** Actual: **28** rows with a stale slice name in `fhir_element` (RD 13, oncology 15), plus 5 prose-only mentions — not "~25". Substance correct; GR 3.0.0 slice names and all seven LOINC codes verified exact.

  **NIT — ECOG LOINC range.** The 2027 VS `mii-vs-onko-allgemeiner-leistungszustand-ecog-loinc` contains LA9622-7…**LA9627-6** ("Dead" is in the VS), not only …LA9626-8 as section A writes; the CM still lacks a row for `5`, and `coding:obds` 1..1 still blocks a LOINC-only answer — the ballot ask is correctly formulated, the parenthetical is not. Also unmentioned: the 2026 CM's LOINC targets had wrong check digits (LA9622-2 etc.), fixed in 2027.

  **NIT — MolGen canonical bullet overgeneralizes.** Four MolGen profiles have id-style urls (`mii-pr-molgen-genomic-study`, `-genomic-study-analysis`, `-molekulare-konsequenz`, `-molekularer-biomarker`, both molgen versions). A blanket "file id ≠ url" fix rule would break the molekulare-konsequenz rows the report itself adds in section A. The 57 counted rows are unaffected.

  **NIT — workflow-relatedArtifact.** Present 0..* on diagnostische-implikation (both versions), but `type=citation` is exemplified, not profile-constrained. Report's parenthetical is fine as guidance, wrong if read as a constraint.

  **Missing open points the report omits** (item 10): (a) mtb-2027 **dropped the consent dependency** that 2026.0.1 had; (b) **onkologie-2027 also pins molgen 2027.0.0-ballot.1**, so the rc3/ballot.1 skew hits both modules, and the 2027 switch additionally pulls the whole base-module ballot stack (meta/base/biobank/medikation 2027.0.0-ballot, basisprofil 1.6.0) — section G understates the migration surface; (c) seltene-2027 **removes** extensions (`inheritance-pattern`, `genetic-basis`, `age-of-onset`, `empfehlung-evidenzgraduierung`, …) — I checked: no RD CSV row references them, so theoretical, but "2027 maps better" is not uniformly true for Seltene; (d) Bundle/Patient/Specimen linkage, Encounter vs EpisodeOfCare, identifier systems/NamingSystems for genomDE IDs, and HGNC system URI policy (fusion gene slices are unbound; the MolGen example uses `http://www.genenames.org/geneId`) are all genuinely open and absent from section F.

  ## 2. Checked and correct (one line each)

  - RD canonical bug counts 22/19/16 = 57 rows, and the bug is **RD-only** — every mii_profile in the oncology and GRZ CSVs matches a real StructureDefinition.url (incl. consent's `mii-pr-consent-einwilligung`).
  - GR 3.0.0 variant slices and LOINC codes exactly as reported (ref-allele 69547-8, alt-allele 69551-0, repr-coding-hgvs 48004-6, repr-protein-hgvs 48005-3, genomic-hgvs 81290-9, repr-transcript-ref-seq 51958-7, coding-change-type 48019-4); molgen variante uses the same slices.
  - 57 groups / 133 annotated rows in td_groups.json; tally sums to 57.
  - ECOG: value[x] 1..1 and coding:obds 1..1 required in both versions; coding:loinc 0..* required-bound new in 2027; focus new in 2027; CS has `U`, no `5`; CM lacks `5`.
  - dataAbsentReason: invalid where value[x] 1..1 (ECOG, molgen variant-inheritance/coding-change-type, diagnostische-implikation mode-of-inheritance/clinical-significance); all four component slices are 0..1 so "omit the component" is legal; obs-6 explicitly permits DAR-only where value[x] is 0..1 — fusion breakpoint remedy valid.
  - Fusion breakpoint components 1..1 with value[x] 0..1 (dna: chromosome/position; rna: gene/transcript/exon/position/strand); gene slices unbound (HGNC binding only on gene-studied) — the report's HGNC-binding ballot ask is well-founded.
  - MTB mechanics: einfache-variante component slicing open (loh addable); transcript binding required→`http://ensembl.org` as bare URI in both MTB versions (MolGen: example, unbound — so "make it like MolGen" is right); studieneinschluss-anfrage supportingInfo targets any Resource (variant workaround valid) and has no Evidenzgraduierung slice (extension context also excludes ServiceRequest — an extra ballot detail); category example-bound; reasonReference:Primaertumor 1..1 mandatory, StuetzendeMolekulareAlteration 0..*; ngs-bericht conclusion/effective[x] not MS, only issued MS; qc extension context broken (Extension instead of Procedure), sub-extensions unbound; biomarker allele-A/B displays swapped.
  - therapieempfehlung-kombination RequestGroup.code → therapy-typ terminology exists in onkologie 2026.0.3 and 2027 (16 codes) — therapeuticStrategy mapping validates.
  - Section D push-backs all confirmed: causedBy→therapieempfehlung since 2026.0.1 (G15); therapyResponseSource = free string "Source of therapy response data" (G16, `OncologyFollowUp.json:244`); GR sequencing-coverage = "% of studied regions sequenced", read-depth = average depth, metrics-description exists, no minCoverage slot (G57); method-type VS includes the whole GR CS incl. karyotyping/microarray/CGH/snp-detection/other (G12 — TD wrong); MTB diagnostische-implikation mode-of-inheritance = same HPO preferred VS as MolGen (G50 — TD wrong); metachroneDiagnoses is boolean (G14); consent OIDs .2/.6/.8 exist in every version with IDAT/MDAT meanings and are used in MII's own examples as Broad-Consent provisions — "semantically wrong" judgement sound, provision.provision.code required-bound (G17).
  - TNM: grouping profile model unchanged (hasMember, same 11 targets); type VS was already SNOMED-required in 2026, 2027 only adds 399703000; method = TNM-Auflage (required → mii-cs-onko-tnm-version "1.–9. Auflage"), so KDK `version` (SNOMED edition per Coding.json) → method would indeed be wrong; y/r/a modifierExtensions and cpPraefix verified.
  - Consent period.end: min=1 in 2025.0.1, relaxed from 2026.0.0 — pipeline claim exact; no MV-GenomSeq concepts in any consent version.
  - Seltene: 29 vs 19 VS, new ones are ICF/NBS/consanguinity — nothing for GMFCS/hospitalisation/strategy; strategy CS unchanged and 1:1 to the enum; MedicationRequest/ServiceRequest category slices exist in both versions; `other` genuinely unreachable for medication strategies.
  - Dependencies: mtb-2027 pins molgen 2027.0.0-ballot.1 (we hold rc3) + hl7.fhir.uv.genomics-reporting 3.0.0 + crmi 2.0.0 + xver-r5.r4 — verified verbatim.
  - MVGS artefacts: all four TNM CM rows target `diagnosisOD.ECOGPerformanceStatusScore` (with mis-cased/nonexistent target paths); TNMSchluessel maps to LOINC 33732-9 (grading!) labelled snomed; the Condition ConceptMap has zero mappings plus wrong canonicals; follow-up/plan blocks unmapped; LM exists in 2026.0.3 too (with the same defect), CMs are 2027-only. "Defective" is fair.
  - Misc: LL5489-1 contains all five LA codes (tx.fhir.org); derivedFrom:variant slice exists on diagnostische-implikation (base derivedFrom is even 1..*); cnv-type bwhc CS dangling (patternCoding only, value[x] unbound); hgvs-vs includes all of varnomen unfiltered; complexVariants is string[], tnmClassifications are SNOMED codings, recommendation-type and evidenceLevelDetails (Z(FDA)) enums as reported; no single/duo/trio concept in any package.

  ## 3. Verdict on the headline

  The headline stands: I found no fourth 2027-enabled item — TNM, the ECOG LOINC slice/focus, and the diagnosis category 55342001 are the only material 2026→2027 changes touching TD's notes, and every other gap (preventive measures, Keimbahndiagnose, metachrone, therapy type, GMFCS, consent domains) is equally absent in both package generations. The CORRECTION claims I spot-checked do validate against the pinned 2026 packages, with one systematic weakness: the localization mapping only "validates" via an extensible-binding escape hatch (all eight SO codes are outside the structural-variant-scoped VS), and several section-A details (TNM uicc history, COSMIC NamingSystem, hrd-score NCIt, fusion example attribution, 38-of-39 framing) are wrong in the particulars without changing the conclusions. Net: safe to act on sections A–D as written, but fix the ~10 factual nicks above before Friday, because TD is exactly the person who will notice them.

