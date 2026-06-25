# Adversarial review brief — mapping table draft

Review the three mapping tables in `mapping/` (`mapping_kdk_oncology.csv`,
`mapping_kdk_rarediseases.csv`, `mapping_grz.csv`). They map genomDE Datenkranz
leaves (BfArM MV Genomseq; KDK 1.7.1, GRZ 1.3.0) to **MII Kerndatensatz** FHIR R4
targets. Columns: source side (`path,type,required,array,enum,format,description`)
+ target side (`mii_module,mii_profile,fhir_element,transform,status`).

Status: every row is a first-pass DRAFT or NOMAP. Find what's **wrong**, not
what's fine.

## Find specifically

1. **Wrong module/profile** — leaf mapped to a MII module that doesn't hold that
   concept (e.g. sequencing/library metadata mapped to Diagnose/Condition;
   anything swept into a parent fallback rule that doesn't fit).
2. **Wrong `fhir_element`** — element path that doesn't exist on the target
   resource, or coding-triple parts (.code/.system/.display/.version) pointed at
   the wrong CodeableConcept.
3. **Bad NOMAP calls** — leaves marked NOMAP that DO have a MII KDS home
   (and vice-versa: DRAFT rows that genuinely have no KDS target).
4. **Oncology specifics** — TNM should be MII Onkologie TNM (component-based,
   c/p prefix, UICC version); histology/grading/topography use ICD-O-3; check
   Primärdiagnose vs additional/germline Condition split.
5. **Genomic (MolGen)** — small/CNV/structural variants → MII Molekulargenetischer
   Befund / HL7 Genomics Reporting. Flag where the profile is guessed ("VERIFY")
   and whether the chosen resource (Observation vs DiagnosticReport) is right.
6. **GRZ** — is the germline/somatic, referenceGenome, libraryType, tumorCellCount,
   tissueOntology handling right? Should `donors[].relation` (trio mother/father/
   index) drive FamilyMemberHistory / Patient.link rather than plain Patient?
7. **Terminology realism** — any invented or wrong CodeSystem assumptions.

## Output

A ranked list of concrete corrections: `path → current → should-be → why`.
Be terse. Highest-impact errors first.
