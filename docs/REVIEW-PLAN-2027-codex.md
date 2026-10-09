## 1. Findings, most severe first

Reviewed HEAD `0d53fc4` and the supplied document copies, which match the current `docs/` files. All checks were read-only; no services were started. Corpus counts below exclude hidden checkpoint directories.

1. **BLOCKER — §§3–5, 10–11: the consent default cannot satisfy the promised MII conformance.**  
   Adding an MVGS CodeSystem does not extend a required MII ValueSet. In `consent#2027.0.0-ballot`, `mii-pr-consent-einwilligung / Consent.provision.provision.code` is `1..*`, required-bound to `mii-vs-consent-policy`; the proposed MV domains are absent. The supporting document explicitly calls the local-CS interim **non-conformant**, whereas A3 promises clean validation. Evidence: [PLAN:71](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:71), [DISCUSS:788](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/DISCUSS-TD-2026-10-09.md:788).  
   **Bites:** ordinary MV consents in all three branches. **Fix:** declare a separate MVGS Consent profile derived from core Consent, preserve domain/type/date there, and stop claiming the MII consent profile until upstream terminology supports it. Distinguish this local representation explicitly in acceptance.

2. **BLOCKER — A1, B2/B5, §11: strict input validation and successful transformation of every corpus file are contradictory.**  
   Running the existing validator offline gives **580 valid / 476 invalid oncology**, **42 valid RD**, and **451 valid / 549 invalid GRZ** files: **1,025 invalid inputs**. Oncology commonly contains object identifiers where strings are required; GRZ omits required consent presentation dates. These defects were already documented. Evidence: [PLAN:132](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:132), [ISSUES-BY-CORPUS:15](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/ISSUES-BY-CORPUS.md:15).  
   **Bites:** immediately. **Fix:** establish an exact corpus manifest; require successful conversion of valid inputs and correct rejection of invalid inputs. Any compatibility normalization needs a separate, explicit contract and tests.

3. **MAJOR — §4: deterministic `fullUrl` does not provide idempotency, and submission/path is the wrong general identity key.**  
   POST creates new persisted resources even when the submitted UUID is unchanged. Thus repeat submissions duplicate most resources under the proposed “POST otherwise” rule. Array positions also change when items are reordered; submission identity changes across follow-ups. No universal `submissionId` field exists in these schemas. Evidence: [PLAN:79](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:79), [Submission.json:182](/Users/kohlbach/Claude/MII/genomDE2FHIR/schemas/kdk/Submission.json:182), [FHIR transaction rules](https://hl7.org/fhir/R4/http.html#transaction).  
   **Bites:** repeat ingest, corrections and longitudinal linkage. **Fix:** define sender-scoped patient, donor, specimen and clinical-entity keys first; use stable PUTs or conditional updates consistently. Specify correction/removal semantics, KDK–GRZ linkage authority, and how sparse GRZ Patient updates avoid erasing clinical demographics. Test repeat ingest, reordered arrays, corrections and identical local IDs from different submitters.

4. **MAJOR — §§3, 5, 11: another required target field has no source.**  
   `mtb#2027.0.0-ballot.1 / mii-pr-mtb-response-befund / Observation.method` is `1..1`, required-bound to RECIST/RANO. Datenkranz supplies response and its **data source**, not the assessment method. “All open decisions are not blockers” therefore overstates feasibility. Evidence: [PLAN:71](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:71), [DISCUSS:340](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/DISCUSS-TD-2026-10-09.md:340).  
   **Bites:** ordinary CR/PR/SD/PD follow-ups. **Fix:** use an appropriate Onko/core response representation with a local profile until the method is known or upstream constraints change. Preserve the data source in note/DocumentReference/Provenance; do not invent RECIST.

5. **MAJOR — §7, A8: the classifier can turn genuine invalid output into apparent success.**  
   The existing harness classifies any diagnostic containing `bfarm/icd-10-gm`, `bfarm/atc` or `codesystem/icd-o-3` as environmental—including authoritative invalid-code and required-binding failures. Reproducing its verdicts preserves this defect. Equating “known gaps” with all open decisions compounds it. Evidence: [harness:47](/Users/kohlbach/Claude/MII/genomDE2FHIR/scripts/e2e_harness.py:47), [PLAN:142](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:142).  
   **Bites:** especially once terminology becomes available. **Fix:** distinguish unavailable validation from rejected content using message IDs, expressions, profile/version and verified server capability. Waive only precisely identified package defects; retain their failures separately. Unchecked required bindings remain INCONCLUSIVE, invalid codings FAIL. Add deliberately invalid-code sentinels.

6. **MAJOR — C1, §9: matchbox 4.0.12 needs qualification beyond package loading and one smoke profile.**  
   There are relevant documented fixes after 4.0.12: **4.0.16** removed automatic IG installation because it mishandled ballots; **4.0.19** fixed FML `translate()/cc()/c()` assignments to polymorphic elements; **4.1.2** integrated the new xver extension configuration. The prior GRZ map was authored for **4.0.20**, not 4.0.12. Evidence: [PLAN:149](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:149), [official changelog](https://ahdis.github.io/matchbox/changelog/).  
   **Bites:** concrete affected FML operations and reproducibility; this does **not** prove the entire stack cannot load. **Fix:** qualify a newer, explicitly pinned candidate first, using fresh volumes and fixtures for translated choices, extensions, reference validation and ballot resolution.

7. **MAJOR — §§2, 7: two cached package versions and CRMI installation do not establish effective validation versions.**  
   `onlyOneEngine=true` merges the development context instead of preserving the default per-IG dependency engines. Meanwhile MTB’s manifest selects SNOMED International **20250701**, while Onko/Biobank select **20260701**; some ValueSets also pin versions directly. Installing CRMI definitions does not prove matchbox applies those manifests. Evidence: [PLAN:140](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:140), package `Parameters-mii-param-*-manifest.json`, [matchbox configuration](https://ahdis.github.io/matchbox/validation/), [CRMI manifest rules](https://hl7.org/fhir/uv/crmi/STU2/en/version-manifest.html).  
   **Bites:** actual version-dependent membership and canonical resolution; 4.0.12 behavior remains untested. **Fix:** record resolved artifact business versions and effective terminology requests; test positive/negative examples for every used profile. Preserve per-IG contexts or explicitly qualify a harmonized graph.

8. **MAJOR — C2/C4/C5: central Ontoserver access is not a complete batch-validation strategy.**  
   The MII validator’s documentation restricts the central service to development with few resources and no personal data, and forbids production ETL validation. A certificate also does not establish availability of every historical terminology edition. Evidence: [PLAN:141](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:141), [official MII usage restriction](https://github.com/medizininformatik-initiative/mii-fhir-validator#alternative-mii-ontoserver-setup), [content-upload process](https://mii-termserv.de/en/services/requesting-content-uploads/).  
   **Bites:** sustained corpus/nightly runs and DIZ deployment; small synthetic development probes remain defensible. **Fix:** verify access, permitted workload and a terminology capability matrix immediately. Arrange agreed synthetic CI usage or local batch terminology infrastructure. Define actual routing between terminology servers rather than assuming two configured URLs provide federation.

9. **MAJOR — §§4, 10: the TNM fallback would discard most observed TNM even among valid inputs.**  
   Comparing source SCT codes with the target codes of both shipped UICC→SCT maps found **46 of 57 TNM codings in schema-valid oncology inputs unmatched**. Example: valid `nct/case_037.json`, SCT `1229892002`, `cM1`. Merely marking the row implemented would conceal this loss. Evidence: [PLAN:78](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:78), [DISCUSS:87](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/DISCUSS-TD-2026-10-09.md:87), `onkologie#2027.0.0-ballot.1 / mii-cm-onko-tnm-uicc-sct-*`.  
   **Bites:** demonstrated on valid planned fixtures. **Fix:** budget an edition-aware, reviewed SCT→UICC mapping before TNM implementation. Preserve unmatched source TNM in an explicit fallback or report partial/rejected conversion; dropped values must not count as preserved mapping coverage.

10. **MAJOR — §§2.1, 4–5: GRZ specimen conformance has unresolved prerequisites missing from the work breakdown.**  
    Full Biobank `Specimen` still requires `Specimen.type.coding:sct 1..*` and `processing.extension:temperaturbedingungen 1..1` for emitted processing entries. Looser unsliced coding rules remove neither requirement. Valid GRZ inputs contain non-SNOMED tissue codes and conservation without measured temperatures. Evidence: [DIFF:527](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/2027-BALLOT-DIFF.md:527), `biobank#2027.0.0-ballot / mii-pr-biobank-specimen`.  
    **Bites:** routine GRZ conversion. **Fix:** choose Specimen versus SpecimenCore explicitly, supply vetted ontology→specimen SCT mappings, and preserve original codes. Validate an honest unknown-temperature representation or use the appropriate Core profile; never invent temperatures. Also test ontology/code agreement—schema-valid fixtures can label UBERON codes as ICD-O-3.

11. **MAJOR — §§4–6: the shared source-model generator combines unnecessary Python machinery with unresolved FML requirements.**  
    The existing validator already resolves the schemas offline. New generated dataclasses add another decoder without demonstrated benefit. Conversely, schema generation cannot infer embedded `researchConsents.scope`: it is an opaque object documented as **2025 MII Consent**, with no declared children. Its migration and reference rebasing are unspecified. Evidence: [PLAN:76](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:76), [Submission.json:143](/Users/kohlbach/Claude/MII/genomDE2FHIR/schemas/kdk/Submission.json:143), [GRZ schema:251](/Users/kohlbach/Claude/MII/genomDE2FHIR/schemas/grz/grz-schema.json:251).  
    **Bites:** consent loss/dangling references and underestimated generator work. **Fix:** Python consumes validated dictionaries. Generate only bounded FML source declarations, explicitly handle `$ref`/composition and embedded FHIR, and fail on unsupported constructs. Define consent migration rather than promising verbatim passthrough under a new profile.

12. **MAJOR — §§6, 8: the HAPI loading contract is decided after maps are required to satisfy it.**  
    B2/B4/B5 require ingest, but B3 is deferred to P6. A provider calling `StructureMapUtilities` still needs worker contexts, logical parsing, terminology services and error handling; “thin interceptor” understates that implementation. Evidence: [PLAN:124](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:124), [PLAN:165](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:165), [standard `$transform`](https://hl7.org/fhir/R4/structuremap-operation-transform.html).  
    **Bites:** the first end-to-end delivery. **Fix:** choose the recommended sidecar now. Freeze a tested recipe for map/model installation, raw logical JSON or Binary input, `source=` selection, content types, transaction envelope and POST to HAPI. Demonstrate transform→validate→ingest→repeat-ingest before expanding maps. Use conditional **updates** for corrections; conditional creates ignore changed existing content.

13. **MAJOR — §§3–6: profile-set and policy parity exists only on the Python side.**  
    `policies.py` cannot change a stored StructureMap selected by `source=`; B2 explicitly targets 2027. Standard FML `uuid()` is random, so it also does not implement the stipulated Python UUID5 identity contract. “Differences explained by a policy” is weaker than same-configuration parity. Evidence: [PLAN:45](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:45), [PLAN:125](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:125), [FML transforms](https://hl7.org/fhir/R4/mapping-language.html).  
    **Bites:** policy changes, 2026 execution and parity testing. **Fix:** publish a support matrix and immutable map variants for supported configurations; agree representations before each block. Share constants, ConceptMaps, identity rules and semantic fixtures. Keep implementations independent; use graph-aware comparison with consistent reference rewriting where IDs legitimately differ.

14. **MAJOR — §§0, 3, 5, 11: CSV row coverage is not a sufficient executable specification or correctness oracle.**  
    Current `transform` cells contain prose and alternatives; slice notation is not an executable JSON path. Canonical existence proves neither element validity nor source preservation. Both converters can agree while dropping the same data, and demoting troublesome rows to DRAFT can improve the percentage without improving delivery. Evidence: [mapping schema:16](/Users/kohlbach/Claude/MII/genomDE2FHIR/scripts/build_mapping_table.py:16), [GRZ mapping:43](/Users/kohlbach/Claude/MII/genomDE2FHIR/mapping/mapping_grz.csv:43), [PLAN:193](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:193).  
    **Bites:** false 100% coverage. **Fix:** retain CSVs as the reviewed mapping specification, with stable branch/path IDs, release-specific dispositions and provenance. Associate each implemented row with observable assertions and enum/boundary fixtures. Report implemented, preserved, dropped and unresolved separately; validate required target-resource closure and cross-resource links.

15. **MAJOR — §8: nine weeks assumes staffing and defers prerequisites until integration.**  
    The arithmetic is correct; the dependency model is not. A7 policies/terminology and B3 loading decisions determine earlier builders/maps. C3 promises PASS before terminology capability is established. Three branch tracks, each with Python and FML, have no owners or effort allocation. Evidence: [PLAN:159](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:159).  
    **Bites:** predictable rework and unreliable phase gates. **Fix:** move contracts, terminology capability, engine qualification and reporting into the initial vertical slice. Run ballot comments and accepted CSV corrections concurrently; XLSX/sheet publication need not block feasibility work. Estimate again after measuring one molecular block and one multi-donor GRZ case.

16. **MINOR — §2.1/10: several implementation instructions need correction.**

    - **Onko onsetPeriod:** its named slice disappears, but `Condition.onset[x]` still allows Period with open slicing; Seltene’s closed slicing is different. [DIFF:181](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/2027-BALLOT-DIFF.md:181).
    - **QC:** metrics-description is string and sequencing-read-type CodeableConcept; only the four numerical subextensions are Quantity. [PLAN:66](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/PLAN-2027.md:66).
    - **Profile versions:** `canonical|version` is valid; stale **artifact** versions are the problem. Consent’s 2026 package version differs from its SD business version.
    - **Therapy strategy:** RequestGroup is valid, but [DISCUSS:118](/Users/kohlbach/Claude/MII/genomDE2FHIR/docs/DISCUSS-TD-2026-10-09.md:118) proposes MedicationRequest.category without a wrapper.

    **Bites:** QC can fail directly; the others cause unnecessary data loss, ambiguity or resources. **Fix:** correct the checklist and make deliberate policy deviations explicit.

17. **MINOR — §§5, 7–8: output-library, CI and deployment contracts remain unfinished.**  
    `fhir.resources.R4B` is not an exact R4 model set or an MII validator; the library’s current default is R5. Two thousand files provide no measured performance justification for choosing it. The 12 GB heap also requires an explicit CI runner budget. Existing proxy TLS verification is disabled, and current warning logs expose TANs. Evidence: [mapper:22](/Users/kohlbach/Claude/MII/genomDE2FHIR/mappers/python/genomde_to_fhir.py:22), [library documentation](https://github.com/nazrulworld/fhir.resources), [proxy:20](/Users/kohlbach/Claude/MII/genomDE2FHIR/infra/mii-termserv-proxy/nginx.conf:20), [mapper:75](/Users/kohlbach/Claude/MII/genomDE2FHIR/mappers/python/genomde_to_fhir.py:75).  
    **Bites:** release/deployment; library performance itself is unmeasured. **Fix:** prefer dictionaries plus pinned R4 validation unless typed models earn their complexity. Specify runner/readiness/cache limits, verified TLS, secret handling and redacted logs. Package mapping/terminology assets, define exit codes and partial-output behavior, and record converter/mapping/profile-lock provenance.

## 2. Claims checked and found right

- The coupled ballot switch, MolGen `.1` selection and exact GR 3.0.0 dependency are correct.
- A separate 2027 instance protects the shared 2026 validator.
- A matchbox sidecar followed by transaction POST to HAPI is a defensible minimal loading path.
- FML can emit `fullUrl` and `request`; resource-emitting groups need envelopes.
- Bundle validation alongside isolated-resource validation is necessary and correctly included.
- Mandatory tumour category, ECOG unknown→U, and honest rejection of ECOG 5/NA are correctly identified.
- Porting target patterns instead of DNPM source groups is appropriate.
- Skipping MedDRA implementation while no AdverseEvent output is planned is appropriate.

## 3. Revised work-plan skeleton

The simpler architecture is **validated dictionaries → small Python builders**, bounded logical models for FML, a dependency lock plus curated target constants, shared ConceptMaps and semantic fixtures. A small local conformance package is justified; a general schema compiler, exhaustive runtime registry and 35 user-selectable policy switches are not established necessities.

| Phase | Duration | Required outcome |
|---|---:|---|
| Ballot triage, concurrently | By 2026-10-27 | Submit evidence-backed comments; fold accepted corrections into CSVs incrementally. |
| Feasibility and contracts | 3–5 days | Fresh-volume engine qualification; terminology capability/access; identity/update rules; input rejection contract; explicit local representations. |
| Complete vertical slices | 1–2 weeks | One representative case per branch through Python/FML, Bundle validation, HAPI ingest and repeat ingest; reports and semantic fixtures working. |
| Expand branch coverage | 5–8 weeks with named parallel owners | Oncology, RD and GRZ implemented block-by-block; terminology and preservation gaps resolved with each block. |
| Integration and release | 1–2 weeks | Valid/rejection corpus reports, negative Bundle tests, clean installation, packaged assets, attribution/licences, DIZ instructions and operational documentation. |
| Final-2027 migration gate | Separate, after publication | Re-diff, update implementations, rerun qualification and regression suites before changing defaults. |

Use **roughly 9–14 weeks as a provisional multi-owner budget**, then replace it with measured estimates; the current nine-week commitment is unsupported for one implementer.

Keep the pinned ballot as the explicit experimental target and retain the existing 2026 baseline with a stated support matrix. Do not promise complete dual-version coverage or automatically switch defaults on publication. Isolate the snapshot-only MolGen closure, CarePlan ServiceRequest conflict, questionable storage cardinality and TNM display invariant for likely repair; there is no evidence that mandatory category, ECOG or consent changes will be reverted.

Also make re-diff reproducible: the referenced `scripts/diff_packages.py` is absent from this HEAD.

## 4. Verdict

The three deliverables are feasible, but this plan cannot meet its stated acceptance criteria with the proposed consent default and corpus requirements. Its main failures are unresolved semantics, identity and validation guarantees placed behind extensive implementation work. Keep the ballot pivot and sidecar architecture, simplify the shared machinery, and require an early complete vertical slice before committing to scope or dates.
