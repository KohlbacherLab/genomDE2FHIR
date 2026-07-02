**Findings**

1. [kdk.rules.json](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules/kdk.rules.json:39) / [rules.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules.py:203): `kdk-7` is wrong for RD follow-ups. It anchors only on `followUp.followUpOds.0.followUpDate`, so `followUp.followUpRds[]` skips criterion 7 entirely. Fix with branch-aware anchor paths for OD and RD, and define how multiple follow-up entries are compared.

2. [kdk.rules.json](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules/kdk.rules.json:57) / [rules.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules.py:176): `kdk-9b` uses the first `mvConsent.scope[].date` only and does not filter `type=permit, domain=mvSequencing`. This creates both false negatives and false positives. The source citation says `mvConsent/scope[].date`, which misrepresents the code. Add a consent-scope selector and compare against the relevant permit scope date(s), not `next(...)`.

3. [kdk.rules.json](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules/kdk.rules.json:16) / [rules.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules.py:273): `kdk-2` only checks `submitterId in le_ids`; it does not check indication approval for `diseaseType`. The `source` claims the full criterion. Fix by accepting LE records/flags keyed by indication and checking `metaData.submission.diseaseType`.

4. [rules.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules.py:222): TNM category detection overclaims SNOMED support. Schema-valid SNOMED entries with full `display` like “American Joint Committee on Cancer cT1 …” and no optional `text` are flagged as missing T/N/M. Parse category from SNOMED display text or code/value-set mapping, not only string prefix.

5. [kdk.rules.json](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules/kdk.rules.json:42): `kdk-7` still over-excludes `/metaData/molecularBoardDecisionDate`. For `followup`, QS only excludes `researchConsents/presentationDate` and `submission/date`, so this is a false negative and the source citation misstates the actual exceptions. Remove the global exclusion or exclude only the active anchor.

6. [rules.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules.py:53): date granularity is too blunt for month-only fields. `followUp.followUpRds[].deathDate` is `YYYY-MM`, but `_date_tuple` floors it to day 1, so `2026-03` is treated as before consent `2026-03-24`. Use interval-aware comparison or document that uncertain month-only dates intentionally fail.

7. [kdk.rules.json](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules/kdk.rules.json:72): `kdk-10` behavior is defensible, but the source is not exact. QS names `diagnosisOd/libraryType`; the code checks both `case.diagnosisOd.libraryType` and actual RD `case.diagnosisRd.libraryType`. Keep the behavior, but cite the literal QS path and explicitly explain the RD schema correction.

**Rule Status**

`kdk-1`, `kdk-3`, `kdk-8`, `kdk-9a`, `kdk-11`, `kdk-12`, and `grz-1/2/3` are path-faithful to the real KDK/GRZ roots. `kdk-8` and `kdk-9a` do compare all consent-date pairs as requested. `kdk-6` is faithful if “fields of format date” is interpreted literally, but it does not cover RD month-pattern dates such as onset/death unless explicitly added.

Previously fixed checks: `resolve()` numeric indexes are fixed at [rules.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules.py:47). `kdk-7` no longer excludes the whole follow-up subtree, but it is not fully fixed because of the remaining `metaData.molecularBoardDecisionDate` exclusion and RD anchor miss.

Severity: actual criterion violations should remain `error`. External-resource skips as `info` are reasonable only when config is absent; `kdk-2` should not look “fully enforced” when only a flat LE-ID list is configured.

I could not run full `pytest`: the read-only sandbox has no usable temp directory for pytest capture. I did run targeted in-memory checks with `python3.11` to confirm the failures above.
