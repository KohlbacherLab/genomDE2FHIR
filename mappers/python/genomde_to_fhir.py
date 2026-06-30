#!/usr/bin/env python3
"""genomDE Datenkranz (KDK oncology) -> MII KDS FHIR R4 transaction Bundle.

Driven by the mapping table (mapping/mapping_kdk_oncology.csv). Covers the
high-confidence MAPPED spine: Patient, Coverage, Consent, primary + additional
Conditions (ICD-10-GM + ICD-O-3 morphology + topography), ECOG, prior systemic
therapy (Procedure + MedicationStatement), vital status. Molecular (MTB variants),
TNM, care-plan recommendations etc. are scaffolded as TODO hooks — extend per the table.

Uses fhir.resources (R4B models = FHIR R4). Emits a transaction Bundle (urn:uuid refs).

Usage:
  python3 mappers/python/genomde_to_fhir.py <datenkranz_oncology.json> [-o bundle.json]
  python3 mappers/python/genomde_to_fhir.py --demo      # run on the first example file

ponytail: oncology core first — the part the table marks MAPPED. RD/GRZ are separate
entry points to add the same way; molecular/recommendations wait on the open issues.
"""
import sys, json, uuid, argparse, glob
from pathlib import Path

from fhir.resources.R4B.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.coverage import Coverage
from fhir.resources.R4B.consent import Consent, ConsentProvision
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.procedure import Procedure
from fhir.resources.R4B.medicationstatement import MedicationStatement

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "https://www.medizininformatik-initiative.de/fhir/{}"
P = {  # crawl-verified canonicals (see mapping table / terminology-locks)
 "patient": "core/modul-person/StructureDefinition/PatientPseudonymisiert",
 "vitalstatus": "core/modul-person/StructureDefinition/mii-pr-person-vitalstatus",
 "coverage": "http://fhir.de/StructureDefinition/coverage-de-basis",
 "consent": "core/modul-consent/StructureDefinition/mii-pr-consent-einwilligung",
 "primaertumor": "fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-diagnose-primaertumor".replace("fhir/", ""),
 "diagnose": "core/modul-diagnose/StructureDefinition/Diagnose",
 "ecog": "fhir/ext/modul-onko/StructureDefinition/mii-pr-onko-allgemeiner-leistungszustand-ecog".replace("fhir/", ""),
 "vortherapie": "fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemische-vortherapie".replace("fhir/", ""),
 "med_stmt": "fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemtherapie-medication-statement".replace("fhir/", ""),
}
HISTOLOGY_EXT = "https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-ex-onko-histology-morphology-behavior-icdo3"
GENDER_MAP = {"male": "male", "female": "female", "other": "other", "unknown": "unknown",
              "divers": "other", "unbestimmt": "unknown"}

def prof(key):  # full profile canonical
    v = P[key]
    return v if v.startswith("http") else PROFILE.format(v)

def uid(*parts):
    return "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "genomde:" + ":".join(str(p) for p in parts if p)))

def cc(src, default_system=None):
    """source coding dict {code,system,version,display} -> CodeableConcept dict."""
    if not src or not src.get("code"):
        return None
    coding = {"code": src["code"]}
    if src.get("system") or default_system:
        coding["system"] = src.get("system") or default_system
    if src.get("version"):
        coding["version"] = src["version"]
    if src.get("display"):
        coding["display"] = src["display"]
    return {"coding": [coding]}

class BundleBuilder:
    def __init__(self):
        self.entries = []
    def add(self, resource, full_url):
        rtype = resource.resource_type
        self.entries.append(BundleEntry(
            fullUrl=full_url, resource=resource,
            request=BundleEntryRequest(method="POST", url=rtype)))
    def bundle(self):
        return Bundle(type="transaction", entry=self.entries)

def map_oncology(dk):
    b = BundleBuilder()
    meta = dk.get("metaData", {})
    case = dk.get("case", {})
    diag = case.get("diagnosisOd", {})

    # --- Patient (PatientPseudonymisiert) ---
    pat_id = uid("patient", meta.get("tanC") or meta.get("localCaseId") or "anon")
    ident = []
    if meta.get("tanC"):
        ident.append({"system": "https://www.medizininformatik-initiative.de/fhir/sid/mvh-tan-c", "value": meta["tanC"]})
    if meta.get("localCaseId"):
        ident.append({"system": "urn:local:case-id", "value": meta["localCaseId"]})
    pat_kwargs = {"meta": {"profile": [prof("patient")]}, "identifier": ident or None}
    if meta.get("gender"):
        pat_kwargs["gender"] = GENDER_MAP.get(meta["gender"], "unknown")
    if meta.get("birthDate"):
        pat_kwargs["birthDate"] = meta["birthDate"]
    patient = Patient(**{k: v for k, v in pat_kwargs.items() if v is not None})
    b.add(patient, pat_id)
    subj = {"reference": pat_id}

    # --- Coverage (coverage-de-basis) ---
    if meta.get("coverageType"):
        cov = Coverage(status="active", beneficiary=subj,
                       meta={"profile": [prof("coverage")]},
                       type={"coding": [{"system": "http://fhir.de/CodeSystem/versicherungsart-de-basis",
                                          "code": meta["coverageType"]}]},
                       payor=[subj])
        b.add(cov, uid("coverage", pat_id))

    # --- Consent (mvConsent -> mii-pr-consent-einwilligung) ---
    mvc = meta.get("mvConsent")
    if mvc:
        provisions = []
        for sc in mvc.get("scope", []):
            provisions.append(ConsentProvision(
                type=sc.get("type", "permit"),
                code=[{"coding": [{"system": "https://www.medizininformatik-initiative.de/fhir/modul-consent/CodeSystem/mii-cs-consent-mvh-domain",
                                    "code": sc.get("domain")}]}] if sc.get("domain") else None))
        consent = Consent(
            status="active", scope={"coding": [{"system": "http://terminology.hl7.org/CodeSystem/consentscope", "code": "research"}]},
            category=[{"coding": [{"system": "http://loinc.org", "code": "57016-8"}]}],
            patient=subj, dateTime=mvc.get("presentationDate"),
            meta={"profile": [prof("consent")]},
            policy=[{"uri": mvc.get("version")}] if mvc.get("version") else None,
            provision={"type": "deny", "provision": provisions} if provisions else None)
        b.add(consent, uid("consent", pat_id))

    # --- Primary diagnosis (mii-pr-mtb-diagnose-primaertumor) ---
    md = diag.get("mainDiagnosis")
    if md and md.get("code"):
        ext = None
        histo = diag.get("histology")
        if histo and histo.get("code"):
            ext = [{"url": HISTOLOGY_EXT, "valueCodeableConcept": cc(histo)}]
        cond = Condition(
            subject=subj, recordedDate=md.get("date"),
            meta={"profile": [prof("primaertumor")]},
            clinicalStatus={"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            verificationStatus={"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
            code=cc(md), bodySite=[cc(diag["topography"])] if diag.get("topography", {}).get("code") else None,
            extension=ext)
        b.add(cond, uid("cond-primary", pat_id, md.get("code")))

    # --- Additional diagnoses (core Diagnose) ---
    for i, ad in enumerate(diag.get("additionalDiagnoses", []) or []):
        if ad.get("code"):
            b.add(Condition(subject=subj, recordedDate=ad.get("date"), code=cc(ad),
                            meta={"profile": [prof("diagnose")]},
                            clinicalStatus={"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]}),
                  uid("cond-add", pat_id, i, ad.get("code")))

    # --- ECOG (diagnosis + follow-ups) ---
    def ecog_obs(score, date, tag):
        return Observation(
            status="final", subject=subj, effectiveDateTime=date,
            meta={"profile": [prof("ecog")]},
            code={"coding": [{"system": "http://loinc.org", "code": "89262-0"},
                              {"system": "http://snomed.info/sct", "code": "423740007"}]},
            valueCodeableConcept={"coding": [{"system": "https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/CodeSystem/mii-cs-onko-ecog", "code": str(score)}]})
    if diag.get("ecogPerformanceStatusScore"):
        b.add(ecog_obs(diag["ecogPerformanceStatusScore"], None, "dx"), uid("ecog-dx", pat_id))

    # --- Prior systemic therapies: Procedure + MedicationStatement(s) ---
    for i, pp in enumerate(case.get("priorProcedures", []) or []):
        proc_url = uid("proc", pat_id, i)
        period = {}
        if pp.get("therapyStartDate"): period["start"] = pp["therapyStartDate"]
        if pp.get("therapyEndDate"): period["end"] = pp["therapyEndDate"]
        b.add(Procedure(status="completed", subject=subj,
                        meta={"profile": [prof("vortherapie")]},
                        code={"coding": [{"system": "http://snomed.info/sct", "code": "277132007", "display": "Therapeutic procedure"}]},
                        performedPeriod=period or None), proc_url)
        for j, sub in enumerate(pp.get("substances", []) or []):
            code = sub.get("code") or {}
            if code.get("code") or sub.get("name"):
                b.add(MedicationStatement(
                    status="completed", subject=subj,
                    meta={"profile": [prof("med_stmt")]},
                    partOf=[{"reference": proc_url}],
                    medicationCodeableConcept=cc(code) or {"text": sub.get("name")},
                    effectivePeriod=period or None), uid("med", pat_id, i, j))

    # --- Follow-up: ECOG + vital status ---
    for k, fu in enumerate(dk.get("followUp", {}).get("followUpOds", []) or []):
        if fu.get("ecogPerformanceStatusScore"):
            b.add(ecog_obs(fu["ecogPerformanceStatusScore"], fu.get("followUpDate"), f"fu{k}"), uid("ecog-fu", pat_id, k))
        if fu.get("vitalStatus"):
            b.add(Observation(status="final", subject=subj, effectiveDateTime=fu.get("followUpDate"),
                              meta={"profile": [prof("vitalstatus")]},
                              code={"coding": [{"system": "http://loinc.org", "code": "67162-8"}]},
                              valueCodeableConcept={"coding": [{"system": "https://www.medizininformatik-initiative.de/fhir/core/modul-person/CodeSystem/Vitalstatus", "code": fu["vitalStatus"]}]}),
                  uid("vital", pat_id, k))
    # TODO (per mapping table / open issues): TNM, grading, molecular MTB variants,
    # complexBiomarkers, carePlan/recommendations, studyInclusion, RNA-seq.
    return b.bundle()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?")
    ap.add_argument("-o", "--output")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    path = a.input
    if a.demo or not path:
        path = sorted(glob.glob(str(ROOT / "example-data/oncology/*.json")))[0]
        sys.stderr.write(f"[demo] {path}\n")
    dk = json.load(open(path))
    bundle = map_oncology(dk)
    out = json.dumps(json.loads(bundle.json(exclude_none=True)), indent=2, ensure_ascii=False)
    if a.output:
        Path(a.output).write_text(out)
        sys.stderr.write(f"wrote {a.output}\n")
    else:
        sys.stdout.write(out)
    types = {}
    for e in bundle.entry:
        types[e.resource.resource_type] = types.get(e.resource.resource_type, 0) + 1
    sys.stderr.write(f"Bundle: {len(bundle.entry)} resources {types}\n")

if __name__ == "__main__":
    main()
