# Final adversarial review brief

The mapping tables are mapping/mapping_kdk_oncology.csv, mapping_kdk_rarediseases.csv,
mapping_grz.csv (columns: path,type,required,array,enum,format,description,
mii_module,mii_profile,fhir_element,transform,status; status in MAPPED/DRAFT/NOMAP).

Prior open issues already catalogued: docs/SYNTHESIS.md (14 open questions + robustness).
Full reference KG in knowledge/: obds-to-fhir/ (oncology align), dnpm-rd/ (RD align),
kohlbacherlab/ (DNPM-on-FHIR + consent), bih-cei/ (BreastCancer/Prostate/Therapieziele/
rarelink/ERKER REVIEW.md — NEWEST, postdates SYNTHESIS), papers/ (MolGen JAMIA), and
mii-kds/ (1416-page crawl of the MII IGs).

Output ONLY (terse, ranked, cite file:row + the KG note that grounds each point):
1. NEW correctness issues NOT already in docs/SYNTHESIS.md open questions.
2. For each SYNTHESIS open question, whether knowledge/bih-cei/REVIEW.md or the
   completed crawl now RESOLVES or INFORMS it (give the concrete code/canonical).
3. Any MAPPED row that should be downgraded to DRAFT (unverified canonical/element).
Do not restate things already correct or already in SYNTHESIS.
