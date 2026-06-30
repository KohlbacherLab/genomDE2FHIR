Adversarially review the two genomDE-oncology->MII-KDS-FHIR mappers for CORRECTNESS.
Files: mappers/python/genomde_to_fhir.py, mappers/fml/genomde-oncology-to-mii.map,
mappers/fml/DatenkranzOncology.logical.json. Sample outputs: /tmp/sample_py_bundle.json,
/tmp/sample_fml_bundle.json. Source-of-truth mapping: mapping/mapping_kdk_oncology.csv
(only MAPPED rows are in scope). KG profile refs: knowledge/genomde-mapping/, knowledge/mii-kds/.

Check, ranked by impact, with concrete fixes:
1. CORRECTNESS vs the mapping table — do the mappers emit what mapping_kdk_oncology.csv (MAPPED rows) says? Any row mapped wrongly, missed, or with wrong element/system/code?
2. MII-PROFILE conformance gaps — required elements/slices the profiles demand that the output omits (e.g. Patient identifier slice, Condition.code ICD-10-GM slice + version, Consent provision OIDs, Observation category, ECOG value set, MedicationStatement medication slice). Cite the MII profile element.
3. FHIR R4 correctness — references, cardinalities, datatypes, status codes, meta.profile correctness.
4. Python vs FML divergence — places the two mappers disagree (one is right, one wrong).
5. Risks/over-claims — anything emitted as MAPPED that won't validate against the pinned MII MTB 2026 / person / consent / onko packages.
Output ONLY a terse ranked list: file:area -> issue -> fix. No restating correct code.
