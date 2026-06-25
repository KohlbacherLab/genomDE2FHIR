#!/usr/bin/env python3
"""Apply the FHIR sequencing-QC research to the GRZ sequencing block.

Source: knowledge/research/fhir-sequencing-qc.md (adversarial research, cross-checked
vs DNPM/bwhc which omits raw QC) + crawl-verified MII MTB canonicals.

Sequencing act -> Procedure `mii-pr-mtb-genomic-study-analysis` (mtb@2026.0.0) with:
 device (device-function CS mii-cs-mtb-genomicanalysis-devicefunction), genome-build
 (LOINC 62374-4), method-type, and QC extension mii-ex-mtb-genomic-study-analysis-qc.
Genuinely-homeless raw QC stays DRAFT (DNPM/bwhc omits it). [[research/fhir-sequencing-qc]]
"""
import csv
from pathlib import Path
MAP = Path(__file__).resolve().parent.parent / "mapping" / "mapping_grz.csv"
M = "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/"
GSA = M + "mii-pr-mtb-genomic-study-analysis"
R = "[[research/fhir-sequencing-qc]] mtb@2026.0.0"

def dev(func, el, desc):  # device via Procedure.device + device-function CS
    return dict(mii_module="MTB", mii_profile=GSA, fhir_element=f"Procedure.device(function={func}).{el}",
                status="MAPPED", transform=f"{desc}; device-function CS mii-cs-mtb-genomicanalysis-devicefunction", notes=R)

U = {
  # genome build
  "donors[].labData[].sequenceData.referenceGenome": dict(mii_module="MTB", mii_profile=GSA,
    fhir_element="Procedure.extension(genome-build)", status="MAPPED",
    transform="LOINC 62374-4 reference-assembly; GRCh37=LA14029-5, GRCh38=LA26806-2 (verified)", notes=R),
  # method type
  "donors[].labData[].libraryType": dict(mii_module="MTB", mii_profile=GSA,
    fhir_element="Procedure.extension(method-type)", status="MAPPED",
    transform="panel/wes/wgs -> method-type VS mii-vs-mtb-genomic-analysis-method-type", notes=R),
  "donors[].labData[].sequenceType": dict(mii_module="MTB", mii_profile=GSA,
    fhir_element="Procedure.extension(method-type)", status="MAPPED", transform="DNA/RNA -> method-type", notes=R),
  "donors[].labData[].sequenceSubtype": dict(mii_module="MTB", mii_profile=GSA,
    fhir_element="Procedure.extension(method-type)", status="MAPPED", transform="germline/somatic -> method-type", notes=R),
  # devices / kits / sequencer
  "donors[].labData[].sequencerModel": dev("sequencing-device", "deviceName", "sequencer model"),
  "donors[].labData[].sequencerManufacturer": dev("sequencing-device", "manufacturer", "sequencer manufacturer"),
  "donors[].labData[].kitName": dev("sequencing-device", "deviceName", "sequencing kit"),
  "donors[].labData[].kitManufacturer": dev("sequencing-device", "manufacturer", "kit manufacturer"),
  "donors[].labData[].libraryPrepKit": dev("library-prep", "deviceName", "library prep kit"),
  "donors[].labData[].libraryPrepKitManufacturer": dev("library-prep", "manufacturer", "library prep kit mfr"),
  "donors[].labData[].enrichmentKitDescription": dev("library-prep", "deviceName", "enrichment kit"),
  "donors[].labData[].enrichmentKitManufacturer": dev("library-prep", "manufacturer", "enrichment kit mfr"),
  # QC metrics that DO have a home (IG metrics / MTB QC ext)
  "donors[].labData[].sequenceData.meanDepthOfCoverage": dict(mii_module="MTB", mii_profile=GSA,
    fhir_element="Procedure.extension(mii-ex-mtb-genomic-study-analysis-qc / metrics:read-depth)", status="MAPPED",
    transform="read-depth as uncoded SimpleQuantity (no LOINC for mean depth - verified none exists)", notes=R),
  "donors[].labData[].sequenceData.targetedRegionsAboveMinCoverage": dict(mii_module="MTB", mii_profile=GSA,
    fhir_element="Procedure.extension(genomic-study-analysis-qc / metrics:sequencing-coverage %)", status="MAPPED",
    transform="sequencing-coverage as % (uncoded)", notes=R),
  # caller / pipeline -> software device or note
  "donors[].labData[].sequenceData.callerUsed[].name": dict(mii_module="MTB", mii_profile=GSA,
    fhir_element="Procedure.device(software Device).deviceName / Procedure.note", status="MAPPED", transform="variant caller software", notes=R),
  "donors[].labData[].sequenceData.callerUsed[].version": dict(mii_module="MTB", mii_profile=GSA,
    fhir_element="Procedure.device(software Device).version", status="MAPPED", transform="caller version", notes=R),
  "donors[].labData[].sequenceData.bioinformaticsPipelineName": dict(mii_module="MTB", mii_profile=GSA,
    fhir_element="Procedure.device(software Device).deviceName / Procedure.note", status="MAPPED", transform="pipeline software", notes=R),
  "donors[].labData[].sequenceData.bioinformaticsPipelineVersion": dict(mii_module="MTB", mii_profile=GSA,
    fhir_element="Procedure.device(software Device).version", status="MAPPED", transform="pipeline version", notes=R),
}
# genuinely no standard clinical-FHIR home -> DRAFT with explicit note
NO_HOME = ["donors[].labData[].sequenceData.percentBasesAboveQualityThreshold.percent",
           "donors[].labData[].sequenceData.percentBasesAboveQualityThreshold.minimumQuality",
           "donors[].labData[].sequenceData.minCoverage",
           "donors[].labData[].sequenceData.nonCodingVariants",
           "donors[].labData[].sequencingLayout",
           "donors[].labData[].fragmentationMethod"]
NOTE = "NO standard clinical-FHIR home (HL7 Genomics Reporting metrics has only read-depth+coverage; DNPM/bwhc OMITS these) -> local code / DeviceMetric / omit | " + R

def main():
    rows = list(csv.DictReader(open(MAP))); fields = list(rows[0].keys()); n = 0
    for r in rows:
        if r["path"] in U:
            for c, v in U[r["path"]].items(): r[c] = v
            n += 1
        elif r["path"] in NO_HOME:
            r["status"] = "DRAFT"; r["mii_module"] = ""; r["mii_profile"] = "(no standard home)"
            r["transform"] = NOTE; r["notes"] = R; n += 1
    with open(MAP, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"mapping_grz.csv: {n} sequencing rows updated")
if __name__ == "__main__":
    main()
