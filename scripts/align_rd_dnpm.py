#!/usr/bin/env python3
"""RD alignment correction pass: apply DNPM rd-model + bfarm-schema-dto-model
findings (knowledge/dnpm-rd/ALIGNMENT.md) to the rare-diseases table, plus the
cross-cutting molecularBoardDecisionDate / EpisodeOfCare fix to BOTH branches.

Runs after enrich_from_research.py + align_obds_corrections.py. Audit trail of the
"align to DNPM RD (SE) model" decision. [[ref-dnpm-rd-model]]

IG-verified deviations from the agent's proposal:
- AlphaID: keep target system http://fhir.de/CodeSystem/bfarm/alpha-id (crawled
  Seltene IG uses this URL even though content is Alpha-ID-SE). Do NOT flip to
  alpha-id-se. ORPHA stays http://www.orpha.net.
"""
import csv
from pathlib import Path

MAP = Path(__file__).resolve().parent.parent / "mapping"
DIAG = "https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose"
VAR  = "https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition/mii-pr-molgen-variante"
CNVP = "https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition/mii-pr-molgen-kopienzahlvariante"
SVP  = "https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition/mii-pr-molgen-strukturvariante"
R = "[[dnpm-rd/ALIGNMENT]] [[ref-dnpm-rd-model]]"

C = []
def add(files, kind, path, **upd): C.append((set(files), kind, path, upd))

# --- cross-cutting: molecularBoardDecisionDate = CarePlan.created (indication board) ---
add({"onc"}, "exact", "metaData.molecularBoardDecisionDate", mii_module="Onkologie", mii_profile="CarePlan",
    fhir_element="CarePlan.created", status="MAPPED",
    transform="Indikationsboard decision = date of FIRST CarePlan (NOT a standalone field; was Encounter)", notes=R)
add({"rd"}, "exact", "case.diagnosisRd.molecularBoardDecisionDate", mii_module="", mii_profile="CarePlan",
    fhir_element="CarePlan.created", status="MAPPED",
    transform="indication board = indicationCarePlan.issuedOn (~first careplan)", notes=R)
add({"rd"}, "exact", "plan.carePlanRd.molecularBoardDecisionDate", mii_module="", mii_profile="CarePlan",
    fhir_element="CarePlan.created", status="MAPPED",
    transform="molecular board = LATEST careplan (plan.* emitted from latest careplan only)", notes=R)

# --- EpisodeOfCare = Fall (RD) ---
add({"rd"}, "exact", "case.priorRds[].zseContactDate", mii_module="Fall", mii_profile="EpisodeOfCare",
    fhir_element="EpisodeOfCare.period.start", status="MAPPED",
    transform="first ZSE contact = the Fall (EpisodeOfCare); the board is an Encounter within the episode", notes=R)
add({"rd"}, "exact", "case.priorRds[].hospitalizationPeriods", mii_module="Fall", mii_profile="EpisodeOfCare",
    fhir_element="Encounter.period (within episode)", status="MAPPED", transform="hospitalization periods", notes=R)
add({"rd"}, "exact", "case.priorRds[].hospitalizationDuration", mii_module="Fall", mii_profile="EpisodeOfCare",
    fhir_element="Encounter.length", status="MAPPED", transform="hospitalization length", notes=R)

# --- RD diagnoses: all-three-or-flag rule ---
add({"rd"}, "prefix", "case.diagnosisRd.diagnoses", mii_module="Diagnose", mii_profile=DIAG,
    transform="ONE multi-coded Condition; ALL THREE required: ICD-10-GM AND ORPHA (http://www.orpha.net) AND AlphaID (target system http://fhir.de/CodeSystem/bfarm/alpha-id; source=Alpha-ID-SE) OR set noMatchingCodeExists", notes=R)
add({"rd"}, "exact", "case.diagnosisRd.noMatchingCodeExists", mii_module="Diagnose", mii_profile=DIAG,
    fhir_element="Condition.code.extension(data-absent-reason)", status="MAPPED",
    transform="set when not all three code systems are available (DNPM rule)", notes=R)
add({"rd"}, "exact", "case.diagnosisRd.diagnosticExtent", mii_module="MolGen", mii_profile="ServiceRequest",
    fhir_element="ServiceRequest.code", status="MAPPED",
    transform="familyControlLevel single/duo/trio; required IFF sequencing performed, forbidden otherwise", notes=R)

# --- GMFCS: repeating, effective-dated; no DNPM canonical ---
for p in ("case.diagnosisRd.diagnosisGmfcs", "followUp.followUpRds[].gmfcs"):
    add({"rd"}, "exact", p, mii_module="", mii_profile="Observation", fhir_element="Observation.valueCodeableConcept",
        status="MAPPED", transform="GMFCS; repeating effective-dated Observation; DNPM has no FHIR canonical (literal 'Gross-Motor-Function-Classification-System') -> declare a local CS", notes=R)

# --- ACMG (all three RD variant types) ---
for v, prof in [("smallVariants", VAR), ("copyNumberVariants", CNVP), ("structuralVariants", SVP)]:
    add({"rd"}, "exact", f"molecular.{v}[].acmgCriteria[].value", mii_module="MolGen", mii_profile=prof,
        fhir_element="Observation.derivedFrom->Observation(acmg-criterion)", status="MAPPED",
        transform="source URI https://www.acmg.net/criteria/type -> translate to ClinGen https://clinicalgenome.org/codesystem/acmg-criteria (codes PVS1..BP7 identical)", notes=R)
    add({"rd"}, "exact", f"molecular.{v}[].acmgCriteria[].modifier", mii_module="MolGen", mii_profile=prof,
        fhir_element="Observation(acmg-criterion).component(strength)", status="MAPPED",
        transform="ACMG strength modifier; VS includes 'bm' (medium benign) — DNPM extra tier beyond classic ACMG", notes=R)

# --- priorRds + carePlanRd promotions ---
add({"rd"}, "exact", "case.priorRds[].diagnosticResult", mii_module="MolGen", mii_profile=VAR,
    fhir_element="DiagnosticReport.conclusion", status="MAPPED", transform="prior diagnostic result", notes=R)
add({"rd"}, "exact", "case.priorRds[].genomicStudyType", mii_module="MolGen", mii_profile="ServiceRequest",
    fhir_element="ServiceRequest.code", status="MAPPED",
    transform="CAVEAT: hardcoded 'single' upstream (DNPM //TODO) — unreliable", notes=R)
add({"rd"}, "exact", "plan.carePlanRd.clinicalManagementDescriptions[]", mii_module="", mii_profile="CarePlan",
    fhir_element="CarePlan.activity.detail.description", status="MAPPED", transform="clinical management description", notes=R)

# --- HPO change semantics (onc + rd) ---
for files, p in [({"onc"}, "followUp.followUpOds[].phenotypes[].change"), ({"rd"}, "followUp.followUpRds[].phenotypes[].change")]:
    add(files, "exact", p, status="MAPPED", fhir_element="Observation.component[status].interpretation",
        transform="status history: source 'abated'->noLongerObserved; 'newlyAdded' is derived (not in 4-value source enum)", notes=R)

FILES = {"onc": "mapping_kdk_oncology.csv", "rd": "mapping_kdk_rarediseases.csv", "grz": "mapping_grz.csv"}
def norm(p): return p.replace("[]", "")

def main():
    for key, fn in FILES.items():
        rows = list(csv.DictReader(open(MAP / fn)))
        fields = list(rows[0].keys()); n = 0
        for r in rows:
            np = norm(r["path"])
            for files, kind, ps, upd in C:
                if key not in files: continue
                p = norm(ps)
                hit = (np == p) if kind == "exact" else (np == p or np.startswith(p + ".") or np.startswith(p + "["))
                if not hit: continue
                for col, val in upd.items(): r[col] = val
                n += 1
        with open(MAP / fn, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
        print(f"{fn}: {n} rows corrected")

if __name__ == "__main__":
    main()
