#!/usr/bin/env python3
"""Apply merged adversarial-review corrections (codex + vibe) to the mapping tables.

This script IS the audit trail of what review round 1 changed. Two passes:
  (A) generic  — coding-triple parts (.code/.system/.display/.version/.text) get
      pointed at the CodeableConcept's .coding.<part> / .text; diagnosis dates ->
      Condition.recordedDate; TNM parts -> component.valueCodeableConcept.
  (B) overrides — per-path judgment fixes (module/profile/element/transform).

Idempotent: re-running yields the same result. Run after draft_targets.py.
"""
import csv
from pathlib import Path

MAP = Path(__file__).resolve().parent.parent / "mapping"
CC_PARTS = ("code", "system", "display", "version")

def last(path):
    return path.replace("[]", "").rsplit(".", 1)[-1]

def cc_base(elem):
    """Strip an existing .coding.* / .text tail to get the CodeableConcept base."""
    for tail in (".coding.code", ".coding.system", ".coding.display", ".coding.version", ".text"):
        if elem.endswith(tail):
            return elem[: -len(tail)]
    return elem

def is_cc_target(elem):
    base = cc_base(elem)
    return base.endswith((".code", ".bodySite", "valueCodeableConcept", "Specimen.type", ".component"))

def generic_fix(path, row):
    seg = last(path)
    elem = row["fhir_element"]
    # TNM: component-based
    if "tnmClassifications" in path:
        if seg == "text":
            row["fhir_element"] = "Observation.component.valueString"
        elif seg in CC_PARTS:
            row["fhir_element"] = f"Observation.component.valueCodeableConcept.coding.{seg}"
        return
    # diagnosis dates
    if seg == "date" and any(k in path for k in ("Diagnos", "diagnoses")):
        row["fhir_element"] = "Condition.recordedDate"
        return
    # coding triples / text on a CodeableConcept target
    if elem and is_cc_target(elem):
        base = cc_base(elem)
        if seg in CC_PARTS:
            row["fhir_element"] = f"{base}.coding.{seg}"
        elif seg == "text":
            row["fhir_element"] = f"{base}.text"

# (prefix, module, profile, element, transform, status) — longest prefix wins.
# element="" keeps existing; status="" keeps existing.
OVERRIDES = {
    "mapping_kdk_oncology.csv": [
        ("case.diagnosisOd.libraryType", "MolGen", "ServiceRequest / DiagnosticReport (method)", "ServiceRequest.code", "sequencing type (panel/wes/wgs); not a diagnosis", "DRAFT"),
        ("metaData.molecularBoardDecisionDate", "Onkologie", "CarePlan", "CarePlan.created", "MTB decision date", "DRAFT"),
    ],
    "mapping_kdk_rarediseases.csv": [
        ("case.diagnosisRd.libraryType", "MolGen", "ServiceRequest / DiagnosticReport (method)", "ServiceRequest.code", "sequencing type; not a diagnosis", "DRAFT"),
        ("case.diagnosisRd.diagnosticExtent", "MolGen", "ServiceRequest (study design)", "ServiceRequest.code", "single/duo/trio genomic testing metadata", "DRAFT"),
        ("case.diagnosisRd.diagnosisGmfcs", "", "Observation", "Observation.valueCodeableConcept", "GMFCS functional score (base FHIR Observation)", "DRAFT"),
        ("case.priorRds", "Fall", "Encounter", "Encounter", "ZSE contact / hospitalization utilization data", "DRAFT"),
        ("plan.carePlanRd", "", "CarePlan", "CarePlan", "RD care plan — NOT MII Onkologie (base FHIR CarePlan)", "DRAFT"),
        ("plan.recommendedTherapies", "", "MedicationRequest / CarePlan", "CarePlan.activity", "RD therapy recommendation — not Onkologie", "DRAFT"),
        ("followUp.followUpRds", "", "Observation / Condition", "Observation", "RD follow-up — NOT MII Onkologie Verlauf", "DRAFT"),
        ("metaData.molecularBoardDecisionDate", "Onkologie", "CarePlan", "CarePlan.created", "MTB decision date", "DRAFT"),
    ],
    "mapping_grz.csv": [
        ("submission.coverageType", "Fall", "Coverage", "Coverage.type", "GKV/PKV etc -> Coverage.type (same as KDK)", "DRAFT"),
        ("submission.localCaseId", "Person", "Patient", "Patient.identifier", "index-patient case id (same as KDK metaData.localCaseId)", "DRAFT"),
        ("submission.tanG", "Person", "Patient", "Patient.identifier", "index-patient genomic pseudonym (VNg)", "DRAFT"),
        ("donors[].relation", "Person", "FamilyMemberHistory", "FamilyMemberHistory.relationship", "trio mother/father/sibling; index -> the Patient itself", "DRAFT"),
        ("donors[].labData[].tumorCellCount[].count", "Onkologie", "Observation (Tumorzellgehalt)", "Observation.valueQuantity.value", "tumour cell content %; UCUM %", "DRAFT"),
        ("donors[].labData[].tumorCellCount[].method", "Onkologie", "Observation (Tumorzellgehalt)", "Observation.method", "method CodeableConcept", "DRAFT"),
        ("donors[].labData[].tissueOntology.name", "Biobank", "Specimen", "Specimen.type.coding.system", "tissue ontology system (BTO/SNOMED)", "DRAFT"),
        ("donors[].labData[].tissueOntology.version", "Biobank", "Specimen", "Specimen.type.coding.version", "tissue ontology version", "DRAFT"),
        ("donors[].labData[].tissueTypeId", "Biobank", "Specimen", "Specimen.type.coding.code", "tissue code", "DRAFT"),
        ("donors[].labData[].tissueTypeName", "Biobank", "Specimen", "Specimen.type.coding.display", "tissue display", "DRAFT"),
        ("donors[].labData[].sequenceData.referenceGenome", "MolGen", "Observation (Variante)", "Observation.component(reference-sequence-assembly)", "GRCh37/38 genomic build for variant coords", "DRAFT"),
        # library / sequencer prep metadata -> sequencing Procedure/Device, not Specimen.type
        ("donors[].labData[].libraryType", "MolGen", "Procedure / Device (sequencing)", "Procedure.code / Device", "sequencing prep metadata", "DRAFT"),
        ("donors[].labData[].sequenceType", "MolGen", "Procedure / Device (sequencing)", "Procedure.code / Device", "DNA/RNA", "DRAFT"),
        ("donors[].labData[].sequenceSubtype", "MolGen", "Procedure / Device (sequencing)", "Procedure.code / Device", "germline/somatic", "DRAFT"),
        ("donors[].labData[].sequencingLayout", "MolGen", "Procedure / Device (sequencing)", "Procedure.code / Device", "single/paired-end", "DRAFT"),
        ("donors[].labData[].fragmentationMethod", "MolGen", "Procedure / Device (sequencing)", "Procedure.code / Device", "fragmentation", "DRAFT"),
        ("donors[].labData[].enrichmentKit", "MolGen", "Procedure / Device (sequencing)", "Device", "enrichment kit", "DRAFT"),
        ("donors[].labData[].libraryPrepKit", "MolGen", "Procedure / Device (sequencing)", "Device", "library prep kit", "DRAFT"),
        ("donors[].labData[].kitName", "MolGen", "Procedure / Device (sequencing)", "Device", "sequencing kit", "DRAFT"),
        ("donors[].labData[].kitManufacturer", "MolGen", "Procedure / Device (sequencing)", "Device.manufacturer", "kit manufacturer", "DRAFT"),
        ("donors[].labData[].sequencerManufacturer", "MolGen", "Procedure / Device (sequencing)", "Device.manufacturer", "sequencer manufacturer", "DRAFT"),
        ("donors[].labData[].sequencerModel", "MolGen", "Procedure / Device (sequencing)", "Device.deviceName", "sequencer model", "DRAFT"),
    ],
}

def match_override(path, rules):
    np = path.replace("[]", "")
    best = None
    for r in rules:
        pref = r[0].replace("[]", "")
        if np == pref or np.startswith(pref + ".") or np.startswith(pref + "["):
            if best is None or len(pref) > len(best[0].replace("[]", "")):
                best = r
    return best

def apply(tf):
    p = MAP / tf
    rows = list(csv.DictReader(open(p)))
    fields = list(rows[0].keys())
    changed = 0
    overrides = OVERRIDES.get(tf, [])
    for r in rows:
        before = dict(r)
        generic_fix(r["path"], r)
        m = match_override(r["path"], overrides)
        if m:
            _, mod, prof, elem, tr, st = m
            r["mii_module"] = mod
            r["mii_profile"] = prof
            if elem:
                r["fhir_element"] = elem
            r["transform"] = tr
            if st:
                r["status"] = st
        if r != before:
            changed += 1
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"{tf}: {changed} rows changed")

if __name__ == "__main__":
    for tf in OVERRIDES:
        apply(tf)
