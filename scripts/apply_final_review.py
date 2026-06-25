#!/usr/bin/env python3
"""Final adversarial review corrections (codex-final + vibe-final convergence).

FIX  = correct element/label, keep MAPPED (target is right, detail was wrong).
DRAFT = downgrade: target is invalid/wrong/unverified (honest robustness).
Note-only items stay MAPPED with a caveat and live in docs/OPEN-ISSUES.md.

Audit trail of the final review pass. [[docs/OPEN-ISSUES]]
"""
import csv
from pathlib import Path
MAP = Path(__file__).resolve().parent.parent / "mapping"
RF = "[[docs/OPEN-ISSUES]] final-review"
FIX, DRAFT = [], []
def fix(f, path, **u): FIX.append((f, path, u))
def draft(f, path, note): DRAFT.append((f, path, note))

# --- FIX: chromosome -> chromosome-identifier (LOINC 48000-4) ---
for f in ("onc", "rd"):
    for v in ("smallVariants", "copyNumberVariants"):
        fix(f, f"molecular.{v}[].chromosome",
            fhir_element="Observation.component:chromosome-identifier.valueCodeableConcept",
            transform="LOINC 48000-4 chromosome-identifier (NOT generic component:chromosome)", notes=RF)
# --- FIX: unify ECOG code + note the cross-source conflict ---
for p in ("case.diagnosisOd.ecogPerformanceStatusScore", "followUp.followUpOds[].ecogPerformanceStatusScore"):
    fix("onc", p, transform="MII Onko ECOG: LOINC 89262-0 + SNOMED 423740007, value MII ECOG CS 0-4 (DNPM/bwhc source uses 89247-1) — verify pinned MII Onko package", notes=RF)
# --- FIX: hospitalization rows are Encounter, not EpisodeOfCare ---
for p in ("case.priorRds[].hospitalizationPeriods", "case.priorRds[].hospitalizationDuration"):
    fix("rd", p, mii_profile="Encounter", notes=RF + " (Encounter within the EpisodeOfCare/Fall)")

# --- DRAFT: fusion geneA/geneB lose 5'/3' orientation ---
for g in ("geneA", "geneB"):
    for part in ("code", "system", "display", "version"):
        draft("onc", f"molecular.structuralVariants[].{g}.{part}",
              "fusion: map to component:five-prime-gene / three-prime-gene (orientation); generic gene-studied loses 5'/3'")
# --- DRAFT: GMFCS (no verified MII/DNPM canonical) ---
draft("rd", "case.diagnosisRd.diagnosisGmfcs", "no MII/DNPM GMFCS canonical; needs local CodeSystem + effective-dated Observation")
draft("rd", "followUp.followUpRds[].gmfcs", "no MII/DNPM GMFCS canonical; needs local CodeSystem + effective-dated Observation")
# --- DRAFT: RD diagnosticAssessment placeholder profile ---
draft("rd", "case.diagnosisRd.diagnosticAssessment", "placeholder profile; no verified Onko/SE assessment profile in crawl")
# --- DRAFT: GRZ sequencing Device rows (no MII Device profile exists) ---
for p in ["enrichmentKitDescription","enrichmentKitManufacturer","fragmentationMethod","kitManufacturer",
          "kitName","libraryPrepKit","libraryPrepKitManufacturer","sequencerManufacturer","sequencerModel","sequencingLayout"]:
    draft("grz", f"donors[].labData[].{p}", "no verified MII Device profile; candidate MolGen genomic-study-analysis or out-of-Datenkranz")
for p in ["bioinformaticsPipelineName","bioinformaticsPipelineVersion","callerUsed[].name","callerUsed[].version"]:
    draft("grz", f"donors[].labData[].sequenceData.{p}", "no verified MII Device(software) profile; candidate MolGen analysis metadata or out-of-Datenkranz")

FILES = {"onc": "mapping_kdk_oncology.csv", "rd": "mapping_kdk_rarediseases.csv", "grz": "mapping_grz.csv"}
def norm(p): return p.replace("[]", "")
def main():
    for key, fn in FILES.items():
        rows = list(csv.DictReader(open(MAP / fn))); fields = list(rows[0].keys()); nf = nd = 0
        fixmap = {norm(p): u for f, p, u in FIX if f == key}
        draftmap = {norm(p): note for f, p, note in DRAFT if f == key}
        for r in rows:
            np = norm(r["path"])
            if np in fixmap:
                for c, v in fixmap[np].items(): r[c] = v
                nf += 1
            if np in draftmap:
                r["status"] = "DRAFT"; r["notes"] = draftmap[np] + " | " + RF; nd += 1
        with open(MAP / fn, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
        print(f"{fn}: {nf} fixed, {nd} -> DRAFT")
if __name__ == "__main__":
    main()
