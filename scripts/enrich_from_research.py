#!/usr/bin/env python3
"""Authoritative research-grounded enrichment of the mapping table, module by module.

This is the *real* build of the central mapping table: each leaf is mapped from
the prior pipeline's per-module MII audits + locked terminology (distilled in
knowledge/genomde-mapping/). It supersedes the earlier prefix-rule draft +
review-fix passes for the leaves it covers.

Keyed by EXACT leaf path. Applies to whichever of the three CSVs contain the
path. status MAPPED = research-grounded; NOMAP = intentionally no clinical KDS
target. notes carries the KG provenance.

Grow MODULES one step at a time (one module per commit). Re-runnable/idempotent.
Run after draft_targets.py + apply_review_fixes.py.
"""
import csv
from pathlib import Path

MAP = Path(__file__).resolve().parent.parent / "mapping"
CSVS = ["mapping_kdk_oncology.csv", "mapping_kdk_rarediseases.csv", "mapping_grz.csv"]

# --- profile canonicals (package-snapshot verified; see knowledge/genomde-mapping) ---
PAT   = "https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/PatientPseudonymisiert"
ENC   = "https://www.medizininformatik-initiative.de/fhir/core/modul-fall/StructureDefinition/KontaktGesundheitseinrichtung"
COVB  = "http://fhir.de/StructureDefinition/coverage-de-basis"
CONS  = "https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-consent-einwilligung"

# value = (module, profile, fhir_element, transform, status, notes)
M = "[[mii-person-fall]]"
MC = "[[mii-consent-med-proc]]"

MODULE_METADATA = {
    "metaData.birthDate": ("Person", PAT, "Patient.birthDate",
        "FHIR date; YYYY-MM is valid — do not pad", "MAPPED", M),
    "metaData.gender": ("Person", PAT, "Patient.gender (+ extension:other-amtlich)",
        "ConceptMap genomDE->administrative-gender; gender-amtlich-de ext (D/X) when gender=other", "MAPPED", M),
    "metaData.addressAGS": ("Person", PAT,
        "Patient.address:Strassenanschrift.city.extension:gemeindeschluessel",
        "AGS Gemeindeschluessel; ext http://fhir.de/StructureDefinition/destatis/ags mounts on address.CITY (P0: not address.extension); valueCoding system urn:oid:1.2.276.0.76.5.474", "MAPPED", M),
    "metaData.localCaseId": ("Person", PAT, "Patient.identifier:pid",
        "local case/patient id; type.coding=MR (v2-0203); also links the per-case Encounter", "MAPPED", M),
    "metaData.tanC": ("Person", PAT, "Patient.identifier:PseudonymisierterIdentifier",
        "tanC pseudonym; type.coding=PSEUDED (v3-ObservationValue) + assigner.identifier; KDK-stream pseudonym — never co-mingle with tanG", "MAPPED", M),
    "metaData.coverageType": ("Fall", COVB, "Coverage.type",
        "-> versicherungsart-de-basis VS; GKV upgrades meta.profile to coverage-de-gkv; SKT->KBV CS, UNK->v3-NullFlavor; guard the 8 valid codes", "MAPPED", M),
    "metaData.molecularBoardDecisionDate": ("Fall", ENC, "Encounter.period.start",
        "MTB decision date; seeds per-case Encounter (class=AMB, status=finished); also MedicationRequest.authoredOn", "MAPPED", M),
    # --- MV consent (mvConsent.scope[] -> Consent.provision.provision[]) ---
    "metaData.mvConsent.scope[].domain": ("Consent", CONS, "Consent.provision.provision.code",
        "domain->broad-consent code: mvSequencing=...24.5.3.8, caseIdentification=...5.3.2, reIdentification=...5.3.6; code.system urn:oid:2.16.840.1.113883.3.1937.777.24.5.3", "MAPPED", MC),
    "metaData.mvConsent.scope[].type": ("Consent", CONS, "Consent.provision.provision.type",
        "permit/deny per inner provision", "MAPPED", MC),
    "metaData.mvConsent.scope[].date": ("Consent", CONS, "Consent.provision.provision.period.start",
        "signature date of this consent scope", "MAPPED", MC),
    "metaData.mvConsent.presentationDate": ("Consent", CONS, "Consent.dateTime",
        "date the MV declaration was presented", "MAPPED", MC),
    "metaData.mvConsent.version": ("Consent", CONS, "Consent.policy.uri",
        "declaration version; policy.uri urn:oid:2.16.840.1.113883.3.1937.777.24.2.2079", "MAPPED", MC),
    # --- research (broad) consent: embedded scope is a full MII Consent ---
    "metaData.researchConsents[].scope": ("Consent", CONS, "(whole Consent resource)",
        "embedded MII Consent — lift VERBATIM as additional Bundle.entry Consent (~27 provisions); passthrough, not field-mapped", "MAPPED", MC),
    "metaData.researchConsents[].presentationDate": ("Consent", CONS, "Consent.dateTime",
        "delivery date of the research consent", "MAPPED", MC),
    "metaData.researchConsents[].noScopeJustification": ("", "", "",
        "justification when no scope present; provenance only, no clinical KDS element", "NOMAP", MC),
    "metaData.researchConsents[].schemaVersion": ("", "", "",
        "consent KDS package version (2025.0.1); metadata, not a mapped element", "NOMAP", MC),
}

MODULES = {
    "metaData (Person/Fall/Coverage/Consent)": MODULE_METADATA,
}

# --- prefix-rule modules (homogeneous coding-triple groups) ---
# (prefix, module, profile, base_element, coding_slice|None, transform, status, notes)
DIAG = "https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose"
ONKO = "https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition"  # + /<profile>
MOLG = "https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition"  # + /<profile>
D = "[[mii-diagnose-onkologie]]"
DL = "[[mii-diagnose-onkologie]] [[fml-codesystem-url-lock]]"

MODULE_DIAG_ONC = [
    # diagnoses -> MII Diagnose Condition (multi-coding on ONE Condition)
    ("case.diagnosisOd.mainDiagnosis", "Diagnose", DIAG, "Condition.code", "icd10-gm",
     "primary oncological diagnosis; ICD-10-GM +version 1..1; SCT/orphanet/alpha-id parallel codings on same Condition", "MAPPED", D),
    ("case.diagnosisOd.additionalDiagnoses", "Diagnose", DIAG, "Condition.code", "icd10-gm",
     "secondary diagnoses; one Condition each, multi-coded", "MAPPED", D),
    ("case.diagnosisOd.germlineDiagnoses", "Diagnose", DIAG, "Condition.code", "icd10-gm",
     "hereditary tumour syndrome (ICD-10-GM Z80*/Z85* + SCT); germline route", "MAPPED", D),
    ("case.diagnosisOd.germlineDiagnosisConfirmed", "Onkologie", ONKO + "/...", "Observation.valueBoolean",
     None, "HT-syndrome confirmed flag (Observation)", "MAPPED", D),
    # oBDS Observations (LOINC + value system locked)
    ("case.diagnosisOd.histology", "Onkologie", ONKO + "/mii-pr-onko-histologie", "Observation.valueCodeableConcept",
     None, "LOINC 59847-4; ICD-O-3 morphology value system urn:oid:2.16.840.1.113883.6.43.1 +version 1..1", "MAPPED", D),
    ("case.diagnosisOd.topography", "Onkologie", ONKO + "/mii-pr-onko-tumorausbreitung", "Observation.valueCodeableConcept",
     None, "LOINC 21861-0 (LOCKED, not 66112-0); ICD-O-3 topography system urn:oid:2.16.840.1.113883.6.43.1 (LOCKED, not .43.2)", "MAPPED", DL),
    ("case.diagnosisOd.grading", "Onkologie", ONKO + "/mii-pr-onko-grading", "Observation.valueCodeableConcept",
     None, "LOINC 33732-9; oBDS Grading OID urn:oid:2.16.840.1.113883.3.7.1.10 or SCT", "MAPPED", D),
    ("case.diagnosisOd.tnmClassifications", "Onkologie", ONKO + "/mii-pr-onko-tnm", "Observation.component.valueCodeableConcept",
     None, "TNM cluster: parent LOINC 21908-9 (UICC OID urn:oid:2.16.840.1.113883.15.16) hasMember T/N/M (c:21905-5/21906-3/21907-1, p:21899-0/21900-6/21901-4)", "MAPPED", D),
    ("case.diagnosisOd.ecogPerformanceStatusScore", "Onkologie", ONKO + "/mii-pr-onko-allgemeiner-leistungszustand-ecog",
     "Observation.valueCodeableConcept", None,
     "LOINC 89247-1; MII ECOG CS codes 0-4(+U) (LOCKED, not LOINC LA); binding mii-vs-onko-allgemeiner-leistungszustand-ecog", "MAPPED", DL),
    ("case.diagnosisOd.diagnosticAssessment", "Onkologie", ONKO + "/...", "Observation.valueCodeableConcept",
     None, "genetic diagnostic evaluation (HT only); verify onko profile", "MAPPED", D),
    ("case.diagnosisOd.additionalClassification", "Onkologie", ONKO + "/...", "Observation",
     None, "other staging classification (key/system, e.g. non-TNM); verify onko profile", "MAPPED", D),
    # phenotype + sequencing-type live under diagnosisOd but belong to MolGen
    ("case.diagnosisOd.hpoTerms", "MolGen", MOLG + "/...phaenotyp", "Observation.valueCodeableConcept",
     None, "HPO Observation; system http://human-phenotype-ontology.org (LOCKED); verify molgen phenotype profile", "MAPPED", DL),
    ("case.diagnosisOd.libraryType", "MolGen", "ServiceRequest", "ServiceRequest.code",
     None, "sequencing type panel/wes/wgs/none; not a diagnosis", "MAPPED", D),
]

PREFIX_MODULES = {
    "case.diagnosisOd (Diagnose/Onkologie)": MODULE_DIAG_ONC,
}

CC_PARTS = ("code", "system", "display", "version")

def norm(p):
    return p.replace("[]", "")

def refine_element(base, slice_, path):
    seg = norm(path).rsplit(".", 1)[-1]
    if base.startswith("Condition") and seg == "date":
        return "Condition.recordedDate"
    if seg == "text":
        if base.endswith("component.valueCodeableConcept"):
            return base[: -len(".valueCodeableConcept")] + ".valueString"
        if base.endswith(("CodeableConcept", ".code", ".bodySite")):
            return base + ".text"
        return base
    if seg in CC_PARTS and base.endswith(("CodeableConcept", ".code", ".bodySite")):
        cod = f".coding:{slice_}" if slice_ else ".coding"
        return base + cod + "." + seg
    return base

def match_prefix(path, rules):
    np = norm(path)
    best = None
    for r in rules:
        pref = r[0]
        if np == pref or np.startswith(pref + ".") or np.startswith(pref + "["):
            if best is None or len(pref) > len(best[0]):
                best = r
    return best

def apply():
    tables = {tf: list(csv.DictReader(open(MAP / tf))) for tf in CSVS}
    fields = {tf: list(rows[0].keys()) for tf, rows in tables.items() if rows}
    total = 0
    for mod_name, mod in MODULES.items():
        hit = 0
        for tf, rows in tables.items():
            for r in rows:
                if r["path"] in mod:
                    module, profile, elem, tr, st, notes = mod[r["path"]]
                    r["mii_module"], r["mii_profile"], r["fhir_element"] = module, profile, elem
                    r["transform"], r["status"], r["notes"] = tr, st, notes
                    hit += 1
        print(f"  module '{mod_name}': {hit} rows enriched")
        total += hit
    for mod_name, rules in PREFIX_MODULES.items():
        hit = 0
        for tf, rows in tables.items():
            for r in rows:
                m = match_prefix(r["path"], rules)
                if not m:
                    continue
                _, module, profile, base, slice_, tr, st, notes = m
                r["mii_module"], r["mii_profile"] = module, profile
                r["fhir_element"] = refine_element(base, slice_, r["path"]) if module else ""
                r["transform"], r["status"], r["notes"] = tr, st, notes
                hit += 1
        print(f"  prefix-module '{mod_name}': {hit} rows enriched")
        total += hit
    for tf, rows in tables.items():
        with open(MAP / tf, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields[tf])
            w.writeheader()
            w.writerows(rows)
    # report MAPPED coverage
    for tf, rows in tables.items():
        c = {}
        for r in rows:
            c[r["status"]] = c.get(r["status"], 0) + 1
        print(f"  {tf}: " + " ".join(f"{k}={v}" for k, v in sorted(c.items())))
    print(f"total enriched: {total}")

if __name__ == "__main__":
    apply()
