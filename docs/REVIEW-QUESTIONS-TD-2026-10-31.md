# Adversarial review of the TD issues table and question document (2026-10-31)

**Objects:** `docs/ISSUES-TD-2026-10-09.md` (issues table) and `docs/QUESTIONS-TD-2026-10-27.md` (questions to
Thomas Debertshäuser), at HEAD `090455a`. **Reviewers:** Codex (gpt-6-astra), Kimi (K3.1 Pro), Opus 5.5 (independent
subagent), each with the same brief (package claims against `~/.fhir/packages`, staleness, coverage against TD's
workbook, cross-document consistency, priorities, questions to drop). Raw reviews are not committed.
**Result:** `docs/QUESTIONS-TD-2026-10-31.md` (+ `.docx`), corrections to five drafts in `docs/BALLOT-COMMENTS-2027.md`.

Every finding below was re-checked against the package snapshots or the code before it was applied.

## Confirmed and applied

| # | Finding | Found by | Evidence | Change |
|:-|:--|:--|:--|:--|
| 1 | MTB-1 (therapy-plan sub-slices vs parent targets) and MTB-22 (`ngs-bericht.result:Tumorzellgehalt` → core Observation, max 1) are in neither the questions nor section I, yet break validation of every MTB plan with non-drug recommendations and almost every NGS report | Codex, Kimi, Opus | mtb 2027 snapshots | new Q26 |
| 2 | Q19 calls `mii-pr-mtb-molecular-pathology-report` new in 2027; it exists in mtb 2026.0.1 and is a pathology report (LOINC 60568-3, IHC/ISH slices), not an NGS container | Codex, Opus | mtb 2026.0.1 package | Q19 premise and 19a rewritten |
| 3 | Q13 cites `mii-pr-onko-therapieempfehlung-kombination`; the Onko profile is `-kombinationstherapie` (MTB: `-kombination`) | Codex, Opus | file names | fixed |
| 4 | MTB-14 / ISSUES B11 deny that in-label/off-label can be carried; `mii-ex-mtb-leitlinie-dokumentation` has context `Element` and the recommendation's extension slicing is open | Codex, Kimi | extension `context` | MTB-14 problem text; Q14 merged |
| 5 | `mii-pr-mtb-genomic-study-analysis` slices GR `metrics` (context Procedure, valid); read-depth, sequencing-coverage and metrics-description have a conformant carrier, but we put everything into the broken `qc` | Opus | mtb 2027 snapshot | Q21 background, new Q22d, MTB-3 proposal; **code follow-up** |
| 6 | ONKO-5 / Q5 evidence "38/39 of 131 unmapped" overstates: for T/N/M only Tis(pu), Tis(pd), N1mi, MX (clinical) and Tis(pu), Tis(pd), T3e, M0, MX (pathological) are unmapped; the rest are prefixes, symbols and L/V/Pn/S | Opus | ConceptMaps | Q5, ONKO-5 |
| 7 | Q24 / MTB-16: no LOINC yes/no at `copy-number-neutral-loh` (value unbound); `hrd-score.component:LOH` uses NCIt C18016 | Opus | mtb 2027 snapshots | Q24, MTB-16 |
| 8 | Q15 / MOLGEN-6 present `https://clinicalgenome.org/codesystem/acmg-criteria` as ClinGen's; we minted it. No "acmg" in MolGen, MTB or GR 3.0.0 | Codex, Opus | grep over packages | Q15 states it; MOLGEN-6 asks for an MII-named CodeSystem; **code follow-up** |
| 9 | Q18b offered `observation-secondaryFinding` without a value; its `value[x]` is 1..1. MolGen already slices it on `diagnostische-implikation`. Source meaning of `incidental` is BfArM/DNPM's | Kimi, Opus, Codex | core extension SD | Q18 split; MOLGEN-4 note |
| 10 | Q25b offered several signatures as codings of one CodeableConcept; codings are alternatives of one concept | Kimi | FHIR CodeableConcept | 25b dropped, rationale in "Unser Stand" |
| 11 | Variant-type multi-coding in `coding-change-type` (implemented, MTB-9) has the same CodeableConcept problem | Kimi (high), Opus, Codex | GR 0..1 | new Q27 |
| 12 | Q20: the local code sits on `mii-pr-mtb-genomic-study.Procedure.code`; analysis `Procedure.code` is 0..0. GR `sequence-analysis-of-the-entire-coding-region` is a candidate for `single`; MTB-10's "gezielte Analyse" code already exists | Codex, Kimi, Opus | snapshots, GR CS | Q20, MTB-10 |
| 13 | Q22 lists `other` as emitted; `labdata.py` drops it as catch-all | Codex, Opus | code | fixed |
| 14 | Section I: preventive measure result is an Observation with `basedOn`, not `Procedure.basedOn` | Codex, Opus | `followup.py` | fixed |
| 15 | Section I: "identical in 2026" overstated; carriers existed, bindings/cardinalities changed | Codex, Opus | — | fixed |
| 16 | Dropped from §8 of ISSUES without a trace: HGNC URI (MII 2027 Onko VS, all MTB panel VSs and examples use `/geneId`; GR `hgnc-vs` uses `www.genenames.org`), MV-GenomSeq LM/CM ownership, identity rules, ICD-O-3 validation server, panel catalogue, fusions/intragenic SVs, localization in the MTB report, follow-up ECOG linkage (2027 `verlauf.hasMember` excludes ECOG), study-recommendation variants, MTB-23, PLAN §11 item 5 conventions, SE-3 | all three | snapshots, PLAN §11 | Q3b table row, Q6c, Q12c, new Q27–Q35, section I rows |
| 17 | Package-answered questions posed as permission questions: 5c (`method` is 0..1), 10a (schema says data source), 10c (extensible → add oBDS), 14b, 17b | Codex, Kimi, Opus | snapshots, schema | turned into statements |
| 18 | Q9a: DNPM defines the tumour-spread list "zum Diagnosezeitpunkt" (REPRESENTATIONS #47); date is not a question for MII | Kimi, Opus | DNPM model | 9a narrowed |
| 19 | "Bezug" numbers in Appendix A are `DISCUSS-TD-2026-10-09.md` numbers; "Vier unserer Entwürfe" listed five; Appendix A omitted cited drafts and had a stray heading | Codex, Opus | — | fixed; Appendix A now holds all 40 cited drafts |
| 20 | Deadline question was moot on the deadline day | Opus | — | rephrased (late filing) |
| 21 | MTB transcript component is defined as "Ensemble Transcript ID ('ENST...')" | Opus | mtb snapshot | Q3a reframed (allow RefSeq?) |
| 22 | `mii-pr-mtb-follow-up-clinicalimpression` (supportingInfo:UmgesetzteTherapien) is unused by us | Opus | mtb snapshot, grep | new Q35 |

## Disagreements between reviewers

| Point | Codex | Kimi | Opus | Verdict |
|:--|:--|:--|:--|:--|
| Q16a(b) "Unknown + dataAbsentReason" | structurally passes, semantically wrong | illegal (obs-6) | legal | `obs-6` is declared on the `Observation` root only, so the component passes structurally (Kimi wrong); a DAR next to a value contradicts its meaning (Codex). Option removed. |
| Consent policy concepts in 2026.0.0 | — | 101 (wrong count in Q1) | — | Both 2026.0.0 and 2027 contain 124 concepts (29 top-level); only the 2026 file's `count` element says 101. Q1 unchanged. |
| Q10c `coding:oBDS` | — | drop: not required | add oBDS: extensible binding requires it | Opus: the Onko ValueSet has direct equivalents (V/T/K/P), so extensible expects them. Stated in Q10. |
| Variant-type multi-coding | medium, convention | high, semantically wrong and implemented | medium, needs MII blessing | Real semantic issue, but MII must choose the convention → Q27. Implementation unchanged until answered. |
| Q7a (`occurredFollowing` vs `dueTo`) | drop, package decides | — | — | Kept: TD's note proposed `dueTo`, so his agreement is the point. |

## Not applied

- ISSUES §6 C3 (ICD-O-3 required binding "new in 2027"): correct finding (already required in onko 2026.0.3,
  moved in 2027), recorded here; ISSUES stays a dated historical document. Q32 states it correctly.
- Opus' proposed Appendix E (row-by-row disposition of all 205 notes): the intro now states the coverage without
  the unreproducible 140/65 split; a full appendix is left for a later round.

## Code follow-ups (not in this change)

1. GRZ QC on the MTB path: emit read-depth, sequencing-coverage, metrics-description in GR `metrics`, keep only the
   read type in `qc` (finding 5; Q22d asks TD first).
2. ACMG criteria URI in our own namespace unless MII names one (finding 8; REPRESENTATIONS #30, builder, FML, IG).
3. Variant types (finding 11) and the follow-up container (finding 22) wait for TD's answers.
4. REPRESENTATIONS #10 / CSV O 169–172 say RefSeq "fails" the required transcript binding; MTB-2 and the builder
   say validators only warn. Align on "warning only".
