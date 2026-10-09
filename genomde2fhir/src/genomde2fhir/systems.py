"""Code system, identifier system and canonical base constants shared by all builders.

Canonical URLs of profiles live next to the builder that uses them; `Ctx.new()` checks each one
against the generated canonical index for the active profile set (data/canonical-index.json).
"""

# --- canonical bases -------------------------------------------------------------------------
MII = "https://www.medizininformatik-initiative.de/fhir/"
MII_CORE = MII + "core/"
MII_EXT = MII + "ext/"
ONKO = MII_EXT + "modul-onko/"
MTB = MII_EXT + "modul-mtb/"
MOLGEN = MII_EXT + "modul-molgen/"
SELTENE = MII_EXT + "modul-seltene/"
BIOBANK = MII_EXT + "modul-biobank/"
STUDIE = MII + "modul-studie/"        # no ext/ segment (e.g. .../modul-studie/StructureDefinition/mii-pr-studie-studie)
CONSENT = MII + "modul-consent/"
PERSON = MII_CORE + "modul-person/"
DIAGNOSE = MII_CORE + "modul-diagnose/"
MEDIKATION = MII_CORE + "modul-medikation/"
GR = "http://hl7.org/fhir/uv/genomics-reporting/"
FHIR_EXT = "http://hl7.org/fhir/StructureDefinition/"

# local MV-GenomSeq conformance package (de.genomde.mvgs); change in one place if the namespace moves
MVGS = "https://genomde.de/fhir/"
MVGS_SD = MVGS + "StructureDefinition/"
MVGS_CS = MVGS + "CodeSystem/"
MVGS_VS = MVGS + "ValueSet/"
MVGS_CM = MVGS + "ConceptMap/"
MVGS_SID = MVGS + "sid/"

# --- terminologies ---------------------------------------------------------------------------
LOINC = "http://loinc.org"
SNOMED = "http://snomed.info/sct"
UCUM = "http://unitsofmeasure.org"
ICD10GM = "http://fhir.de/CodeSystem/bfarm/icd-10-gm"
OPS = "http://fhir.de/CodeSystem/bfarm/ops"
ATC = "http://fhir.de/CodeSystem/bfarm/atc"
ALPHA_ID = "http://fhir.de/CodeSystem/bfarm/alpha-id"
ICDO3 = "http://terminology.hl7.org/CodeSystem/icd-o-3"
ORPHA = "http://www.orpha.net"
HPO = "http://human-phenotype-ontology.org"
HGNC = "http://www.genenames.org"          # terminology lock (GR hgnc-vs); Onko 2027 marker-gene VS uses /geneId
SO = "http://www.sequenceontology.org"
HGVS = "http://varnomen.hgvs.org"
ENSEMBL = "http://www.ensembl.org"
REFSEQ = "http://www.ncbi.nlm.nih.gov/refseq"
NCIT = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl"
NCIT_MTB = "https://nih-ncpi.github.io/ncpi-fhir-ig/CodeSystem-ncit.html"  # fixed by MTB ploidie/hrd-score patterns (ballot defect)
ATC_WHO = "http://www.whocc.no/atc"
UICC = "https://www.uicc.org/resources/tnm"
COSMIC = "https://cancer.sanger.ac.uk/cosmic"
DAR = "http://terminology.hl7.org/CodeSystem/data-absent-reason"
OBS_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category"
COND_CLINICAL = "http://terminology.hl7.org/CodeSystem/condition-clinical"
COND_VER = "http://terminology.hl7.org/CodeSystem/condition-ver-status"
V2_0203 = "http://terminology.hl7.org/CodeSystem/v2-0203"
V2_0074 = "http://terminology.hl7.org/CodeSystem/v2-0074"
V3_OBSVALUE = "http://terminology.hl7.org/CodeSystem/v3-ObservationValue"
V3_INTERP = "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"
TBD_GR = GR + "CodeSystem/tbd-codes-cs"

# --- identifier systems (genomDE submission identities) --------------------------------------
SID_LE = MVGS_SID + "le-id"                 # submitterId (Leistungserbringer, §293 SGB V / BfArM)
SID_LOCAL_CASE = MVGS_SID + "local-case-id"  # value = "<submitterId>|<localCaseId>" (sender-scoped)
SID_TAN_C = MVGS_SID + "tan-c"              # VNk (KDK transaction number)
SID_TAN_G = MVGS_SID + "tan-g"              # VNg (GRZ transaction number)
SID_DONOR = MVGS_SID + "donor-pseudonym"    # value = "<submitterId>|<donorPseudonym>"
SID_GDC = MVGS_SID + "genomic-data-center"  # GRZXXXnnn
SID_KDK = MVGS_SID + "clinical-data-node"   # KDKXXXnnn
SID_FINDING = MVGS_SID + "molecular-finding-id"      # "<submitterId>|<caseKey>|<KDK id>" molecular findings (variants, CNV, fusions, biomarkers; both branches)
SID_KDK_OBJECT = MVGS_SID + "kdk-object-id"          # "<submitterId>|<caseKey>|<KDK id>" recommendations, preventive measures
                                                      # (both branches; also the target of logical references)
SID_LAB_DATA = MVGS_SID + "grz-lab-data-name"        # "<submitterId>|<donorPseudonym>|<labDataName>"
SID_BARCODE = MVGS_SID + "grz-sample-barcode"        # "<submitterId>|<sample barcode>"
