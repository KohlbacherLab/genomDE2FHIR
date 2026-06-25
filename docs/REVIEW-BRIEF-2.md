# Adversarial review brief — round 2 (research-grounded table)

The three mapping tables in `mapping/` have now been authoritatively built module
by module from the prior pipeline's MII audits + locked terminology (distilled in
`knowledge/genomde-mapping/`). 316/428 leaves are MAPPED.

You have TWO grounding sources to check against:
1. `knowledge/genomde-mapping/` — the prior pipeline's per-module audits + the
   CodeSystem-URL lock note (`fml-codesystem-url-lock.md`).
2. `knowledge/mii-kds/mii-website/` — freshly crawled MII KDS IG pages (Person,
   Diagnose, Onkologie, **Molekulargenetischer Befundbericht**, Biobank, Consent,
   Seltene Erkrankungen, …). Use these to verify profile canonicals + element paths.

Find what's WRONG, not what's right. Specifically:

1. **Profile canonical errors** — `mii_profile` URLs that don't exist in the crawled
   IGs (esp. the `…/...` placeholders and the `ext/modul-onko` / `ext/modul-molgen`
   profile IDs I guessed: mii-pr-onko-histologie/-grading/-tnm/-tumorausbreitung/
   -allgemeiner-leistungszustand-ecog, mii-pr-molgen-variante/-strukturvariante/
   -kopienzahlvariante, the molgen phenotype profile). Give the correct canonical
   from the crawled IG where you can find it.
2. **Wrong `fhir_element`** — element/component paths that don't exist on the target
   profile; wrong LOINC component slice names in genomics-reporting.
3. **Terminology** — any CodeSystem/LOINC/OID that contradicts the locked values in
   `fml-codesystem-url-lock.md` or the crawled IGs.
4. **Wrong module/NOMAP calls** — leaves mapped to the wrong MII module, or
   MAPPED/NOMAP/DRAFT mis-classified.
5. **MolGen specifics** — variant component slices (gene-studied 48018-6, dna-change
   48004-6, etc.), DiagnosticReport vs Observation placement, ACMG handling.

Output ONLY a terse ranked list: `file:path -> current -> should-be -> why`.
Highest-impact errors first. Cite the crawled IG page when you correct a canonical.
