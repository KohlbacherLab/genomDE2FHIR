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
from fhir.resources.R4B.fhirprimitiveextension import FHIRPrimitiveExtension

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
ASSERTED_DATE_EXT = "http://hl7.org/fhir/StructureDefinition/condition-assertedDate"  # Feststellungsdatum (min 1)
INTENTION_EXT = "https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-ex-onko-systemische-therapie-intention"  # min 1
ICDO3 = "http://terminology.hl7.org/CodeSystem/icd-o-3"      # profile fixes histology/topography to this (not the source OID)
ECOG_CS = "https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/CodeSystem/mii-cs-onko-allgemeiner-leistungszustand-ecog"
ECOG_VALID = {"0", "1", "2", "3", "4", "U"}  # MII CS; source "5"(=death)/"notApplicable" are out-of-VS
# gender=other requires the amtliche Differenzierung (mii-pat-1); bound VS permits only D/X
GENDER_AMTLICH_EXT = "http://fhir.de/StructureDefinition/gender-amtlich-de"
GENDER_AMTLICH_CS = "http://fhir.de/CodeSystem/gender-amtlich-de"
GENDER_AMTLICH_MAP = {"other": ("D", "divers"), "divers": ("D", "divers"),
                      "unbestimmt": ("X", "unbestimmt")}
INTENTION_CS = "https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/CodeSystem/mii-cs-onko-intention"
VITALSTATUS_CS = "https://www.medizininformatik-initiative.de/fhir/core/modul-person/CodeSystem/Vitalstatus"
CONSENT_PROVISION_CS = "urn:oid:2.16.840.1.113883.3.1937.777.24.5.3"
CONSENT_POLICY_OID = "urn:oid:2.16.840.1.113883.3.1937.777.24.2.2079"
GENDER_MAP = {"male": "male", "female": "female", "other": "other", "unknown": "unknown",
              "divers": "other", "unbestimmt": "unknown"}

def prof(key):  # full profile canonical
    v = P[key]
    return v if v.startswith("http") else PROFILE.format(v)


def ecog_code(raw, where, tan):
    """Normalize source ECOG to the MII CS; warn+drop anything out of {0-4,U} (e.g. 5=death)."""
    s = str(raw).strip()
    if s.lower() in ("unknown", "unbekannt", "u"):
        s = "U"
    if s in ECOG_VALID:
        return s
    sys.stderr.write(f"[warn] ECOG '{raw}' not in MII CS {{0-4,U}} — dropped ({where}, tan={tan})\n")
    return None

def uid(*parts):
    return "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "genomde:" + ":".join(str(p) for p in parts if p)))

def cc(src, default_system=None, override_system=None):
    """source coding dict {code,system,version,display} -> CodeableConcept dict.
    override_system wins over the source system (for profile-fixed systems, e.g. ICD-O-3)."""
    if not src or not src.get("code"):
        return None
    coding = {"code": src["code"]}
    if override_system or src.get("system") or default_system:
        coding["system"] = override_system or src.get("system") or default_system
    if src.get("version") and not override_system:
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
    PSEUDED = {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationValue", "code": "PSEUDED"}]}
    MR = {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]}
    ident = []
    if meta.get("tanC"):
        ident.append({"type": PSEUDED, "system": "https://www.medizininformatik-initiative.de/fhir/sid/mvh-tan-c", "value": meta["tanC"]})
    if meta.get("localCaseId"):
        ident.append({"type": MR, "system": "urn:local:case-id", "value": meta["localCaseId"]})
    pat_kwargs = {"meta": {"profile": [prof("patient")]}, "identifier": ident or None}
    if meta.get("gender"):
        g = GENDER_MAP.get(meta["gender"], "unknown")
        pat_kwargs["gender"] = g
        if g == "other":  # mii-pat-1: amtliche Differenzierung required when gender=other
            code, disp = GENDER_AMTLICH_MAP.get(meta["gender"], ("D", "divers"))
            pat_kwargs["gender__ext"] = FHIRPrimitiveExtension(extension=[{
                "url": GENDER_AMTLICH_EXT,
                "valueCoding": {"system": GENDER_AMTLICH_CS, "code": code, "display": disp}}])
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
                period={"start": sc["date"]} if sc.get("date") else None,
                code=[{"coding": [{"system": CONSENT_PROVISION_CS, "code": sc.get("domain")}]}] if sc.get("domain") else None))
        consent = Consent(
            status="active", scope={"coding": [{"system": "http://terminology.hl7.org/CodeSystem/consentscope", "code": "research"}]},
            category=[{"coding": [{"system": "http://loinc.org", "code": "57016-8"}]},
                      {"coding": [{"system": "https://www.medizininformatik-initiative.de/fhir/modul-consent/CodeSystem/mii-cs-consent-consent_category", "code": "2.16.840.1.113883.3.1937.777.24.2.184"}]}],
            patient=subj, dateTime=mvc.get("presentationDate"),
            meta={"profile": [prof("consent")]},
            policy=[{"uri": CONSENT_POLICY_OID}],
            provision={"type": "deny", "provision": provisions} if provisions else None)
        b.add(consent, uid("consent", pat_id))

    # --- Primary diagnosis (mii-pr-mtb-diagnose-primaertumor) ---
    md = diag.get("mainDiagnosis")
    if md and md.get("code"):
        ext = []
        if md.get("date"):  # Feststellungsdatum (condition-assertedDate) — profile min=1
            ext.append({"url": ASSERTED_DATE_EXT, "valueDateTime": md["date"]})
        histo = diag.get("histology")
        if histo and histo.get("code"):  # ICD-O-3 morphology -> fixed system icd-o-3
            ext.append({"url": HISTOLOGY_EXT, "valueCodeableConcept": cc(histo, override_system=ICDO3)})
        cond = Condition(
            subject=subj, recordedDate=md.get("date"),
            meta={"profile": [prof("primaertumor")]},
            clinicalStatus={"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            verificationStatus={"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
            code=cc(md),  # ICD-10-GM (source system already http://fhir.de/CodeSystem/bfarm/icd-10-gm)
            bodySite=[cc(diag["topography"], override_system=ICDO3)] if diag.get("topography", {}).get("code") else None,
            extension=ext or None)
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
            category=[{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "survey"}]}],
            code={"coding": [{"system": "http://loinc.org", "code": "89262-0"},
                              {"system": "http://snomed.info/sct", "code": "423740007"}]},
            valueCodeableConcept={"coding": [{"system": ECOG_CS, "code": str(score)}]})
    if diag.get("ecogPerformanceStatusScore"):
        c = ecog_code(diag["ecogPerformanceStatusScore"], "dx", meta.get("tanC"))
        if c:
            b.add(ecog_obs(c, None, "dx"), uid("ecog-dx", pat_id))

    # --- Prior systemic therapies: Procedure + MedicationStatement(s) ---
    for i, pp in enumerate(case.get("priorProcedures", []) or []):
        proc_url = uid("proc", pat_id, i)
        period = {}
        if pp.get("therapyStartDate"): period["start"] = pp["therapyStartDate"]
        if pp.get("therapyEndDate"): period["end"] = pp["therapyEndDate"]
        intention_code = pp.get("intention") or "X"   # profile requires Intention (min 1)
        # code carries the SNOMED procedure code (sct slice + satisfies sct-ops-1). The
        # "Element matches more than one slice (sct, systemische_therapie_art)" error is a
        # terminology-server artifact: without SNOMED loaded the validator can't confirm the
        # code is in procedures-sct and not in systemische-therapie-art, so it can't assign the
        # slice. Resolves once matchbox has a tx server (see docs/FIX-PLAN.md P1-1). Do NOT move
        # SNOMED off code — that violates sct-ops-1 (a real, tx-independent error).
        b.add(Procedure(status="completed", subject=subj,
                        meta={"profile": [prof("vortherapie")]},
                        extension=[{"url": INTENTION_EXT,
                                    "valueCodeableConcept": {"coding": [{"system": INTENTION_CS, "code": intention_code}]}}],
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
            c = ecog_code(fu["ecogPerformanceStatusScore"], f"fu{k}", meta.get("tanC"))
            if c:
                b.add(ecog_obs(c, fu.get("followUpDate"), f"fu{k}"), uid("ecog-fu", pat_id, k))
        if fu.get("vitalStatus"):
            vmap = {"living": "lebend", "deceased": "verstorben", "alive": "lebend"}
            b.add(Observation(status="final", subject=subj, effectiveDateTime=fu.get("followUpDate"),
                              meta={"profile": [prof("vitalstatus")]},
                              category=[{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "survey"}]}],
                              code={"coding": [{"system": "http://loinc.org", "code": "67162-8"}]},
                              valueCodeableConcept={"coding": [{"system": VITALSTATUS_CS, "code": vmap.get(fu["vitalStatus"], fu["vitalStatus"])}]}),
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
