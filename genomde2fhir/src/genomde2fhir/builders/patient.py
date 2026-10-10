"""KDK metaData -> Patient (MII PatientPseudonymisiert). Shared by the oncology and rare-disease branches.

Rows: metaData.gender, .birthDate, .addressAGS, .tanC, .localCaseId.
"""
from ..systems import PERSON, SID_LE, SID_LOCAL_CASE, SID_TAN_C, V2_0203, V3_OBSVALUE
from .common import ext, identifier

PROFILE = PERSON + "StructureDefinition/PatientPseudonymisiert"
GENDER_AMTLICH_EXT = "http://fhir.de/StructureDefinition/gender-amtlich-de"
GENDER_AMTLICH_CS = "http://fhir.de/CodeSystem/gender-amtlich-de"
AGS_EXT = "http://fhir.de/StructureDefinition/destatis/ags"
AGS_SYSTEM = "http://fhir.de/sid/destatis/ags"


def build(ctx):
    md = ctx.dk.get("metaData") or {}
    k = ctx.key
    pat = ctx.new("Patient", profile=PROFILE)
    ids = [identifier(SID_TAN_C, md.get("tanC"), V3_OBSVALUE, "PSEUDED")]
    if k.case_id_is_local:   # '<submitterId>|<caseKey>' (escaped; test submissions: '<localCaseId>|test')
        ids.append(identifier(SID_LOCAL_CASE, k.scoped(), V2_0203, "MR",
                              assigner_system=SID_LE, assigner_value=k.submitter_id))
    pat["identifier"] = ids
    paths = ["metaData.tanC"] + (["metaData.localCaseId"] if md.get("localCaseId") else [])

    g = md.get("gender")
    if g:
        pat["gender"] = g if g in ("male", "female", "other", "unknown") else "unknown"
        if pat["gender"] == "other":  # mii-pat-1: amtliche Differenzierung required (D = divers)
            pat["_gender"] = {"extension": [ext(GENDER_AMTLICH_EXT, valueCoding={
                "system": GENDER_AMTLICH_CS, "code": "D", "display": "divers"})]}
        paths.append("metaData.gender")
    if md.get("birthDate"):
        pat["birthDate"] = md["birthDate"]          # YYYY-MM is a valid FHIR date
        paths.append("metaData.birthDate")
    ags = md.get("addressAGS")
    if ags:
        if len(ags) == 8 and ags.isdigit():
            # Amtlicher Gemeindeschlüssel: basisprofil extension on Address.city (context), 8 digits (ags-extension-1).
            # No address.type: the PatientPseudonymisiert slice 'Strassenanschrift' (type 1..1) would demand postalCode.
            pat["address"] = [{"country": "DE", "_city": {"extension": [ext(AGS_EXT, valueCoding={
                "system": AGS_SYSTEM, "code": ags})]}}]
            paths.append("metaData.addressAGS")
        else:
            # schema allows any string; values that are not an 8-digit AGS (e.g. 5-digit codes in the synthetic data)
            # are kept as address text rather than as an invalid AGS coding
            pat["address"] = [{"country": "DE", "text": f"AGS {ags}"}]
            ctx.preserve("metaData.addressAGS", "ags-not-8-digits")
            ctx.warn("metaData.addressAGS", f"not an 8-digit AGS: {ags!r}; kept as address.text")
    ctx.add(pat, *paths, name="patient")
