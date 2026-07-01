# genomDE → MII KDS — prioritized fix plan (e2e harness findings)

Deep adversarial research (4 parallel research agents against the **live** matchbox + oBDS
reference, plus self-driven infra analysis), then **each content fix re-verified against
matchbox** — which overturned one agent proposal (substance slice, see P0-3). Findings from
`docs/E2E-REPORT.md` / `out/e2e/results.json`.

Legend: **✓live** = validated against the running matchbox; **logic** = proven by data/spec;
**flag** = carries an implementation risk to check during the edit.

---

## P0 — Python content fixes (cheap, verified, clears ALL Path-A content errors)

Each is ~4–10 lines in `mappers/python/genomde_to_fhir.py`. Together they take Path A from
**FAIL → clean content** (residual errors become purely environmental → see P1).

### P0-1 · gender = "other" needs the amtliche-Differenzierung extension  ✓live (1 case)
`mii-pat-1` is an **error**-severity invariant: `gender='other'` requires the
`http://fhir.de/StructureDefinition/gender-amtlich-de` extension on `Patient.gender`.
Bound ValueSet `gender-other-de` permits only `D` (divers) / `X` (unbestimmt).
**Fix:** when gender resolves to `other`, attach a primitive extension via fhir.resources:
```python
from fhir.resources.R4B.fhirprimitiveextension import FHIRPrimitiveExtension
GENDER_AMTLICH_EXT = "http://fhir.de/StructureDefinition/gender-amtlich-de"
GENDER_AMTLICH_CS  = "http://fhir.de/CodeSystem/gender-amtlich-de"
GENDER_AMTLICH_MAP = {"other": ("D","divers"), "divers": ("D","divers"), "unbestimmt": ("X","unbestimmt")}
# replace the gender block (~line 104):
if meta.get("gender"):
    g = GENDER_MAP.get(meta["gender"], "unknown"); pat_kwargs["gender"] = g
    if g == "other":
        code, disp = GENDER_AMTLICH_MAP.get(meta["gender"], ("D","divers"))
        pat_kwargs["gender__ext"] = FHIRPrimitiveExtension(extension=[{
            "url": GENDER_AMTLICH_EXT,
            "valueCoding": {"system": GENDER_AMTLICH_CS, "code": code, "display": disp}}])
```
Verified live: **with** extension → 0 errors; **without** → reproduces `mii-pat-1`. Default `D`
for bare "other" is a policy choice (both D/X validate) — confirm with a genomDE steward.

### P0-2 · ECOG score 5 is out of value set — DROP it (do NOT map to deceased)  logic (6 cases)
MII CS `mii-cs-onko-allgemeiner-leistungszustand-ecog` defines only `0,1,2,3,4,U`. Source
carries `5` in 6 cases. **Adversarial catch:** 5 is a data-quality artifact, NOT "dead" — at
follow-up, ECOG=5 co-occurs with vitalStatus **living ×2 / deceased ×1**, and the 3
diagnosis-time cases have no vitalStatus at all. Routing 5→deceased would fabricate death.
oBDS precedent: `LeistungszustandMapper` emits only `0–4,U`; death is modeled separately.
**Fix:** guard emission (mirror at diagnosis + follow-up):
```python
ECOG_VALID = {"0","1","2","3","4","U"}   # map source "unknown" -> "U" first if desired
s = diag.get("ecogPerformanceStatusScore")
if s and str(s) in ECOG_VALID: b.add(ecog_obs(s, None, "dx"), uid("ecog-dx", pat_id))
```
Log dropped codes (don't discard silently — real submissions may legitimately send 5).
Vital status already has its own home (`mii-pr-person-vitalstatus`, `deathDate`→`deceasedDateTime`).

### P0-3 · systemische-vortherapie slice collision — SNOMED off `code`  ✓live (67 cases — largest)
`Procedure.code.coding` slices on `pattern $this`; the `systemische_therapie_art` slice has
**no pattern discriminator**, so a lone SNOMED coding matches both it and the `sct` slice →
"Element matches more than one slice". **The agent's first fix (add a 2nd coding) did NOT
clear it — re-verified live.** Working fix: put only the therapy-type coding on `code`, move
SNOMED to `category`:
```python
# replace code={...} (~line 190):
code={"coding": [{"system": "https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/CodeSystem/mii-cs-onko-therapie-typ",
                  "code": pp.get("therapyType") or "SO"}]},   # SO=Sonstiges (no source therapy-type field yet)
category={"coding": [{"system": "http://snomed.info/sct", "code": "18629005",
                      "display": "Administration of drug or medicament"}]},
```
Verified live: collision **cleared (0)**. Matches oBDS `SystemischeTherapieProcedureMapper`
(therapy-type on code, SNOMED on category, substances stay ATC on MedicationStatement).
`SO` is an honest placeholder until a therapy-type field is added to the Datenkranz mapping.

---

## P1 — Environment / infra: make validation AUTHORITATIVE (unblocks real PASS)

Without these, even a perfectly-conformant mapper caps at the harness verdict **INCONCLUSIVE**
(the report is honest about this). These are NOT mapper bugs.

### P1-1 · matchbox can't reach a terminology server  infra
Config (`matchbox-config/application.yaml`) sets `txServer: https://tx.fhir.org/r4`, but the
same file notes **container egress is blocked** → ICD-10-GM / ICD-O-3 / ATC / SNOMED value
sets can't expand. Every `env-only` $validate error is this.
**Fix (pick one):** allow the matchbox container egress to `tx.fhir.org`; OR run a local
terminology server and point `txServer` at it; OR run the KDS validation pass with the HL7
`validator_cli.jar -tx tx.fhir.org` against the emitted bundles (the harness already writes
them to `out/e2e/py/`). Effort: small (config/network) but external-dependency dependent.

### P1-2 · consent + vitalstatus loaded without snapshots  infra
Those two StructureDefinitions have `snapshot: false` on matchbox → "could not validate
profile" (Patient/diagnose have 115/253-element snapshots and validate fine). Also a
**version skew**: base MII modules load at `2025.0.1` while the targeted MTB/onko profiles are
`2026.0.x` (loaded ad-hoc).
**Fix:** reload the MII packages cleanly (with snapshots, pinned to one consistent version set)
via the matchbox package config instead of ad-hoc POSTs, and re-run. Consider persisting the
loaded set so runs are reproducible.

---

## P2 — FML (Path B) parity: bring the StructureMap up to the Python spine

Larger effort; Path B currently FAILs on every resource. Root cause found by inspecting the
live Path-B output: **`reference(pat)` silently produces nothing in matchbox v4.0.12** (a 7th
quirk beyond the documented Q1–Q6) — the map *writes* `subject = reference(pat)` everywhere but
it evaporates. Do these in order; each has a flagged risk to check during the edit.

1. **Subject references (dominant failure).** Replace every `reference(pat)` with the
   known-good literal-concat idiom: thread `metaData.tanC` as a source string `pk` into each
   resource group and write `s.reference = ('Patient/' + pk), s.type = 'Patient'`. Give the
   Patient a stable `id = tanC`. ✓ pattern is proven safe in the reference impl.
2. **Transaction Bundle.** Add per-entry `fullUrl = uuid()` (bare — already returns `urn:uuid:`;
   **flag:** avoid `'urn:uuid:'+uuid()` concat) and `entry.request.method/url`. Patient →
   `PUT Patient/<tanC>` so refs resolve on ingest; other resources → `POST`. Unblocks HAPI
   ingest (0/44 → 44/44).
3. **Conformance parity** (mirror Python): Condition `condition-assertedDate` (**flag:**
   `ext.value=<string>` may emit `valueString` not `valueDateTime` — may need a `dateTime`-typed
   leaf in the logical model); Procedure `mii-ex-onko-systemische-therapie-intention` (code `X`);
   ECOG — **fix the wrong system URL** `mii-cs-onko-ecog` → Python's
   `mii-cs-onko-allgemeiner-leistungszustand-ecog` and add the SNOMED `423740007` code slice via
   a single-`create` sub-group (**Q4 re-binding risk**); apply the SAME P0-3 substance fix here;
   `Coverage.meta.profile = http://fhir.de/StructureDefinition/coverage-de-basis`;
   MedicationStatement `partOf` + `effective` (thread the parent Procedure id + start date).
   **Note:** the FML `value[x].coding:obds` error is just the wrong-system-URL bug above — NOT a
   missing oBDS OID (Python passes this slice with the MII ECOG system; don't invent an OID).
4. **Logical model (Q6):** declare any new source paths used (e.g. a `dateTime`-typed date leaf;
   optional `priorProcedures.intention`).

Re-run `python3 scripts/e2e_harness.py` after each phase to watch the verdict move.

---

## Suggested order

1. **P0-1/2/3** now — cheap, verified, clears all Path-A content errors (biggest correctness win).
2. **P1-1/2** — flips the verdict from INCONCLUSIVE to a real PASS you can show MII/BfArM.
3. **P2** — the larger FML build-out, so both mappers reach parity (the "structural mapping in
   HAPI" deliverable becomes real). Each sub-step re-validated by the harness.

Environmental note: P0 fixes are independently matchbox-verified, so they're correct regardless
of P1; P1 just lets the harness *display* the resulting PASS.

---

## Implementation outcome (Path A, tx-enabled authoritative run)

Applied P0-1/P0-2 + P1, and re-validated against matchbox reloaded to **latest 2026 packages**
with **tx.fhir.org enabled**. Per-profile Path A result over all 44 oncology files:

| profile | verdict | note |
|---|---|---|
| PatientPseudonymisiert | **44 clean** | P0-1 gender-amtlich extension |
| Vitalstatus | **44 clean** | canonical fixed (`Vitalstatus`, not `mii-pr-person-vitalstatus`) + codes L/T |
| coverage-de-basis | **44 clean** | — |
| mii-pr-onko-…-ecog | **82 clean** | P0-2 dropped out-of-VS ECOG 5 (SNOMED slice now resolves via tx) |
| mii-pr-mtb-diagnose-primaertumor | env | ICD-O-3 + ICD-10-GM VS — **BfArM** terms, not on tx.fhir.org |
| mii-pr-mtb-systemtherapie-medication-statement | env | ATC VS — **BfArM** |
| mii-pr-mtb-systemische-vortherapie | env* | `procedures-sct` pins SNOMED edition `20250701` which tx.fhir.org can't resolve → the "matches more than one slice" is a tx-version artifact, **not** a content bug (P0-3 confirmed: SNOMED stays on `code`). *Harness over-reports as content. |
| mii-pr-consent-einwilligung | **CONTENT (real)** | see below |

### What P1 changed
- **P1-1 egress:** the container was never egress-blocked — it reaches tx.fhir.org + the registries.
  matchbox just wasn't *consuming* tx (the running instance predated the `txServer` config).
  Restart applied `matchbox.fhir.context.txServer: https://tx.fhir.org/r4` → SNOMED/LOINC now expand.
- **P1-2 packages:** matchbox reloaded pinned to latest — basisprofil 1.6.0, meta/consent 2026.0.0,
  medikation 2026.0.1, **onkologie 2026.0.3, +mtb 2026.0.1**; person/diagnose/prozedur/fall at their
  latest 2025.0.1. Fixed the consent/vitalstatus "could not validate profile" (it was a
  profile-canonical mismatch in the mapper, now corrected).
- **Bonus** (exposed once validation became authoritative): 2 wrong profile canonicals + the
  Vitalstatus value code — all fixed and now 44 clean.

### Terminology gap (new finding — needs a decision)
tx.fhir.org covers **SNOMED/LOINC** but **not** the German BfArM terminologies (ICD-10-GM, OPS,
ATC, ICD-O-3) — those live on `https://terminologieserver.bfarm.de/fhir`. matchbox takes a single
`txServer`, so it can't consult both at once. Options: (a) point `txServer` at the BfArM server
(loses SNOMED); (b) accept ICD/OPS/ATC/ICD-O-3 as env here and do the authoritative German-code
pass with `validator_cli.jar -tx …bfarm…` (Java now installed); (c) pre-load the specific VS
expansions. Until then, the `diagnose`/`medication`/`vortherapie` env rows can't be turned green.

### Remaining REAL content issue — consent (genuine modeling gap, not a simple bug)
The genomDE **Modellvorhaben** consent scope domains (`mvSequencing`, `reIdentification`,
`caseIdentification`, …) are **not** codes in the MII Broad-Consent policy CS
(`urn:oid:2.16.840.1.113883.3.1937.777.24.5.3`), and MII `mii-pr-consent-einwilligung` requires
`provision.period` (1..1) on the outer + inner provisions. genomDE MV consent ≠ MII Broad Consent —
this needs a deliberate mapping (a ConceptMap MV-domain→MII-policy-code + provision period wiring),
or a decision to model MV consent differently. Not hacked; flagged for design.

**Net:** every P0/P1-addressable Path-A profile is clean; the only non-environmental residual is
the consent modeling gap.
