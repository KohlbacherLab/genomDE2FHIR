#!/usr/bin/env python3
"""Alignment correction pass: retarget the oncology branch to the MII MTB module
(DNPM/Molekulares Tumorboard) and apply obds-to-fhir + crawled-IG verified
canonicals. Runs AFTER enrich_from_research.py; this is the audit trail of the
"align to obds-to-fhir + MTB/Seltene IGs" decision.

Sources of truth (all crawled/verified):
- genomDE oncology == DNPM ~= oBDS -> MII MTB module (knowledge/mii-kds MTB IG,
  knowledge/obds-to-fhir/ALIGNMENT.md). [[feedback-prefer-obds-for-oncology]]
- HPO phenotypes -> mii-pr-seltene-hpo-assessment, term in Observation.code.
- RD molecular stays MolGen (rare-disease genetics, not tumour board).

Profiles below were grep-verified to exist in the crawled IGs.
"""
import csv
from pathlib import Path

MAP = Path(__file__).resolve().parent.parent / "mapping"
MTB = "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition"
ONKOEX = "https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition"
SELT = "https://www.medizininformatik-initiative.de/fhir/ext/modul-seltene/StructureDefinition/mii-pr-seltene-hpo-assessment"
A = "[[obds-to-fhir/ALIGNMENT]] [[ref-bzkf-obds-to-fhir]]"

# Each correction: (file_keys, match_kind, pathspec, updates)
#  file_keys subset of {onc, rd, grz}; match_kind 'prefix'|'exact'
#  updates: dict of column->value to overwrite; special key '_hpo_code' rewrites
#  element valueCodeableConcept -> code (HPO term goes in Observation.code).
C = []
def add(files, kind, path, **upd): C.append((set(files), kind, path, upd))

# ---- oncology molecular -> MTB module (profiles only; keep component elements) ----
add({"onc"}, "prefix", "molecular.smallVariants",      mii_profile=f"{MTB}/mii-pr-mtb-einfache-variante", notes=A)
add({"onc"}, "prefix", "molecular.copyNumberVariants", mii_profile=f"{MTB}/mii-pr-mtb-copy-number-variant", notes=A)
add({"onc"}, "prefix", "molecular.structuralVariants", mii_profile=f"{MTB}/mii-pr-mtb-dna-fusion", transform="MTB DNA/RNA fusion (mii-pr-mtb-rna-fusion if sequenceType=RNA); SO variant-type", notes=A)
add({"onc"}, "prefix", "molecular.expressionVariants", mii_profile=f"{MTB}/mii-pr-mtb-rna-seq", notes=A)
add({"onc"}, "exact",  "molecular.complexBiomarkers[].tmb",     mii_profile=f"{MTB}/mii-pr-mtb-mutationslast", notes=A)
add({"onc"}, "exact",  "molecular.complexBiomarkers[].hrdHigh", mii_profile=f"{MTB}/mii-pr-mtb-hrd-score", notes=A)
add({"onc"}, "exact",  "molecular.complexBiomarkers[].ploidy",  mii_profile=f"{MTB}/mii-pr-mtb-ploidie", notes=A)
add({"onc"}, "exact",  "molecular.complexBiomarkers[].lstHigh", mii_profile=f"{MTB}/mii-pr-mtb-molekularer-biomarker", notes=A)
add({"onc"}, "exact",  "molecular.complexBiomarkers[].taiHigh", mii_profile=f"{MTB}/mii-pr-mtb-molekularer-biomarker", notes=A)
add({"onc"}, "exact",  "molecular.complexBiomarkers[].identifier", mii_profile=f"{MTB}/mii-pr-mtb-molekularer-biomarker", notes=A)
add({"onc"}, "prefix", "molecular.sbsSignatures",      mii_profile=f"{MTB}/mii-pr-mtb-molekularer-biomarker", notes=A)

# ---- oncology clinical: primary diagnosis (MTB Primaertumor) ----
add({"onc"}, "prefix", "case.diagnosisOd.mainDiagnosis", mii_profile=f"{MTB}/mii-pr-mtb-diagnose-primaertumor", notes=A)
add({"onc"}, "prefix", "case.diagnosisOd.histology",
    mii_profile=f"{MTB}/mii-pr-mtb-diagnose-primaertumor",
    fhir_element=f"Condition.extension(mii-ex-onko-histology-morphology-behavior-icdo3)",
    transform="ICD-O-3 morphology as Condition extension (obds-to-fhir model); no standalone histology Observation; system http://terminology.hl7.org/CodeSystem/icd-o-3", notes=A)
add({"onc"}, "prefix", "case.diagnosisOd.topography",
    mii_profile=f"{MTB}/mii-pr-mtb-diagnose-primaertumor",
    fhir_element="Condition.bodySite (ICD-O-3 coding)",
    transform="ICD-O-3 topography -> Condition.bodySite; system http://terminology.hl7.org/CodeSystem/icd-o-3 (HL7 URI, NOT OID)", notes=A)
add({"onc"}, "prefix", "case.diagnosisOd.tnmClassifications",
    mii_profile=f"{ONKOEX}/mii-pr-onko-tnm-klassifikation",
    fhir_element="Observation.hasMember -> T/N/M category Observations",
    transform="TNM SNOMED grouping 399537006/.. + categories SNOMED + values UICC https://www.uicc.org/resources/tnm; hasMember (NOT component); c/p via mii-ex-onko-tnm-cp-praefix", notes=A)
add({"onc"}, "exact", "case.diagnosisOd.ecogPerformanceStatusScore",
    mii_profile=f"{ONKOEX}/mii-pr-onko-allgemeiner-leistungszustand-ecog",
    transform="ECOG LOINC 89262-0 (+SNOMED 423740007); value emits MII ECOG CS AND LOINC LA9622-7.. (obds-to-fhir)", notes=A)
# flags with no valid profile -> DRAFT
for p in ("case.diagnosisOd.diagnosticAssessment", "case.diagnosisOd.germlineDiagnosisConfirmed"):
    add({"onc"}, "exact", p, mii_profile="", status="DRAFT", transform="no MTB/Onko profile found; represent via Condition verification/clinicalStatus or note", notes=A)
add({"onc"}, "prefix", "case.diagnosisOd.additionalClassification", mii_profile="", status="DRAFT", transform="no exact Weitere-Klassifikationen canonical confirmed; base Observation", notes=A)

# ---- oncology systemic therapy -> MTB ----
add({"onc"}, "prefix", "case.priorProcedures", mii_profile=f"{MTB}/mii-pr-mtb-systemische-vortherapie",
    transform="prior systemic therapy; Stellung/Intention via mii-ex-onko-systemische-therapie-{stellungzurop,intention} (MII URLs, not fhir.de)", notes=A)
add({"onc"}, "prefix", "case.priorProcedures[].substances", mii_profile=f"{MTB}/mii-pr-mtb-systemtherapie-medication-statement", transform="ATC http://fhir.de/CodeSystem/bfarm/atc; one MedicationStatement per substance", notes=A)
add({"onc"}, "prefix", "plan.recommendedSystemicTherapies", mii_profile=f"{MTB}/mii-pr-mtb-therapieempfehlung", notes=A)
add({"onc"}, "prefix", "plan.recommendedStudies", mii_profile=f"{MTB}/mii-pr-mtb-studieneinschluss-anfrage", transform="study enrolment request; register NCT/EudraCT/DRKS", notes=A)
add({"onc"}, "prefix", "followUp.followUpOds[].therapies", mii_profile=f"{MTB}/mii-pr-mtb-systemische-therapie", notes=A)
add({"onc"}, "prefix", "followUp.followUpOds[].therapies[].substances", mii_profile=f"{MTB}/mii-pr-mtb-systemtherapie-medication-statement", notes=A)
add({"onc"}, "exact", "case.priorProcedures[].therapyResponse", mii_profile=f"{MTB}/mii-pr-mtb-response-befund", fhir_element="Observation.valueCodeableConcept", transform="response = Verlauf Gesamtbeurteilung SNOMED 396432002 (obds-to-fhir has no RECIST LOINC)", notes=A)
add({"onc"}, "exact", "followUp.followUpOds[].therapies[].therapyResponse", mii_profile=f"{MTB}/mii-pr-mtb-response-befund", fhir_element="Observation.valueCodeableConcept", transform="Gesamtbeurteilung SNOMED 396432002", notes=A)

# ---- HPO phenotypes -> Seltene HPO assessment; term in Observation.code ----
for files, p in [({"onc"}, "case.diagnosisOd.hpoTerms"), ({"onc"}, "followUp.followUpOds[].phenotypes"),
                 ({"rd"}, "case.diagnosisRd.phenotypes"), ({"rd"}, "followUp.followUpRds[].phenotypes")]:
    add(files, "prefix", p, mii_profile=SELT, _hpo_code=True,
        transform="HPO term in Observation.code (NOT value[x]); http://human-phenotype-ontology.org (LOCKED); change->component[status].interpretation newly-added/no-longer-observed", notes=A)

# ---- GRZ tumour cell content -> MTB ----
add({"grz"}, "prefix", "donors[].labData[].tumorCellCount", mii_profile=f"{MTB}/mii-pr-mtb-tumorzellgehalt", notes=A)

FILES = {"onc": "mapping_kdk_oncology.csv", "rd": "mapping_kdk_rarediseases.csv", "grz": "mapping_grz.csv"}

def norm(p): return p.replace("[]", "")

def main():
    counts = {}
    for key, fn in FILES.items():
        rows = list(csv.DictReader(open(MAP / fn)))
        fields = list(rows[0].keys())
        n = 0
        for r in rows:
            np = norm(r["path"])
            for files, kind, pathspec, upd in C:
                if key not in files:
                    continue
                ps = norm(pathspec)
                hit = (np == ps) if kind == "exact" else (np == ps or np.startswith(ps + ".") or np.startswith(ps + "["))
                if not hit:
                    continue
                for col, val in upd.items():
                    if col == "_hpo_code":
                        r["fhir_element"] = r["fhir_element"].replace("valueCodeableConcept", "code")
                    else:
                        r[col] = val
                n += 1
        with open(MAP / fn, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
        counts[fn] = n
    for fn, n in counts.items():
        print(f"{fn}: {n} rows corrected")

if __name__ == "__main__":
    main()
