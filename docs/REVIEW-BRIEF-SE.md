Final adversarial review of the RARE-DISEASE mapping after applying the canonical
DNPM SE Data Model. Read knowledge/dnpm-rd/se-datamodel-crosswalk.md +
se-implementierungsleitfaden.md, then mapping/mapping_kdk_rarediseases.csv.
Check each RD row against the authoritative SE model (value sets, cardinalities,
BfArM-Datenkranz field correspondence, FHIR targets vs crawled MII Seltene/MolGen IGs in knowledge/mii-kds/).
Output ONLY a terse ranked list: (1) RD rows that are WRONG vs the SE model (path -> current -> should-be -> why);
(2) MAPPED rows that should be DRAFT (unverified target); (3) the top RD open issues that remain.
Do not restate correct rows.
