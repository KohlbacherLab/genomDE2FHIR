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
