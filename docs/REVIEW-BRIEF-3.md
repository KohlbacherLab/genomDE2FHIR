# Adversarial review brief — round 3 (full current state)

The three mapping tables in `mapping/` are now research-grounded and aligned to:
- oncology → MII **MTB module** (DNPM/oBDS) — see knowledge/obds-to-fhir/, knowledge/kohlbacherlab/
- RD → DNPM **SE model** (MolGen + Seltene) — see knowledge/dnpm-rd/
- shared → Person/Fall/Consent/Biobank — see knowledge/genomde-mapping/
Locked terminology in knowledge/genomde-mapping/fml-codesystem-url-lock.md; MolGen paper in knowledge/papers/.

Grounding to check against: knowledge/mii-kds/mii-website/ (crawled MII IGs: MTB,
Onkologie, MolGen, Seltene, Diagnose, Person, Fall, Biobank, Consent).

This is a FULL adversarial review. For EACH of the three CSVs, find what is WRONG or
UNROBUST. Report ranked, terse: `file:path -> current -> issue -> fix`.

Check:
1. **Profile canonical validity** — every mii_profile URL: does it exist in the crawled
   IG? Flag invented/placeholder/wrong-module canonicals.
2. **Element/component path validity** — fhir_element paths that don't exist on the
   target profile; wrong LOINC/SNOMED component slice; wrong value[x] type.
3. **Terminology** — CodeSystem/LOINC/OID/SNOMED that contradict the crawled IGs or the
   locks (esp. ECOG 89247-1 vs 89262-0; topography HL7-URI vs OID; TNM SNOMED vs LOINC;
   HGNC; ORPHA; AlphaID).
4. **Module assignment** — leaves on the wrong MII module (MTB vs MolGen vs Onko vs
   Diagnose vs Seltene), or wrong MAPPED/DRAFT/NOMAP status.
5. **Robustness** — MAPPED rows that are actually shaky (guessed component, ambiguous
   cardinality, no verified canonical) and should be DRAFT; DRAFT rows that are actually
   solid and could be MAPPED.
6. **Coverage gaps** — source leaves that should map but don't; MII required elements
   with no source.

Also classify each branch's overall mapping robustness (high/medium/low) per module.
Output a ranked issue list + a short per-module robustness verdict.
