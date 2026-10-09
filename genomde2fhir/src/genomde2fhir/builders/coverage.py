"""KDK metaData.coverageType -> Coverage (coverage-de-basis). Row: metaData.coverageType. Shared with grz.donors."""
from .common import cc, coding, dar_ext

PROFILE = "http://fhir.de/StructureDefinition/coverage-de-basis"
VERSICHERUNGSART = "http://fhir.de/CodeSystem/versicherungsart-de-basis"
# codes not in versicherungsart-de-basis, but in the required VersicherungsartDeBasisVS (mapping rows; same as grz.donors)
OTHER_SYSTEM = {"SKT": ("https://fhir.kbv.de/CodeSystem/KBV_CS_FOR_Payor_Type_KBV", "Sonstige Kostenträger"),
                "UNK": ("http://terminology.hl7.org/CodeSystem/v3-NullFlavor", "unknown")}


def add_coverage(ctx, ct: str, path: str):
    """Coverage for one coverage type. The payor is the patient only for self-pay (SEL); the insurer itself is not
    submitted, so other types carry a data-absent-reason payor instead of asserting the patient pays."""
    system, display = OTHER_SYSTEM.get(ct, (VERSICHERUNGSART, None))
    cov = ctx.new("Coverage", profile=PROFILE)
    payor = dict(ctx.patient) if ct == "SEL" else {"extension": [dar_ext("unknown")]}
    cov.update(status="active", type=cc(coding(system, ct, display)), beneficiary=ctx.patient, payor=[payor])
    return ctx.add(cov, path, name="coverage")


def build(ctx):
    ct = (ctx.dk.get("metaData") or {}).get("coverageType")
    if ct:
        add_coverage(ctx, ct, "metaData.coverageType")
