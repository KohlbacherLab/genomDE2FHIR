"""MV-GenomSeq participation consent (metaData.mvConsent / donors[].mvConsent) -> local profile mvgs-consent.

MII mii-pr-consent-einwilligung cannot carry the MV domains (provision.provision.code is required-bound to
mii-vs-consent-policy) -> docs/REPRESENTATIONS.md #35. The former mapping to the Broad-Consent OIDs
...24.5.3.{8,2,6} (IDAT/MDAT purposes) is semantically wrong and not used.

Representation (core Consent + mvgs-consent):
  status active, scope patient-privacy, category LOINC 57016-8, patient -> Patient
  dateTime          = presentationDate; absent -> earliest scope[].date (schema: "unless identical to the date
                      of signature")
  policyRule.text   = version (name/version of the declaration; no URI exists for it)
  provision.provision[] per scope[]: type = permit/deny, period.start = date, code = mvgs-cs-mv-consent-domain#domain
Rows: metaData.mvConsent.* (KDK), donors[].mvConsent.* (GRZ).
"""
from ..data_access import mapping_rows
from ..systems import LOINC, MVGS_SD
from ..terminology import local_coding
from .common import cc, coding

PROFILE = MVGS_SD + "mvgs-consent"
DOMAIN_CS = "mvgs-cs-mv-consent-domain"
CONSENT_SCOPE = "http://terminology.hl7.org/CodeSystem/consentscope"
PRIVACY_CATEGORY = cc(coding(LOINC, "57016-8", "Privacy policy acknowledgment Document"))


def mark(ctx, path: str, note: str):
    """Disposition for a value carried by a local mvgs-* resource: cover when the branch table maps the row
    (MAPPED), otherwise preserve (shared by the consent, research_consent and submission builders)."""
    if (mapping_rows(ctx.branch).get(path) or {}).get("status") == "MAPPED":
        ctx.cover(path)
        ctx.rep(note)
    else:
        ctx.preserve(path, note)


def build(ctx):
    md = ctx.dk.get("metaData") or {}
    ref = build_mv_consent(ctx, md.get("mvConsent"), ctx.patient, "metaData.mvConsent", ())
    if ref:
        ctx.refs["mv_consent"] = ref


def build_mv_consent(ctx, mvc: dict | None, patient_ref: dict, path_prefix: str, id_parts: tuple) -> dict | None:
    """Create the MV consent for one patient/donor; returns its reference or None.
    path_prefix is 'metaData.mvConsent' (KDK) or 'donors[].mvConsent' (GRZ); id_parts disambiguates donors."""
    if not mvc:
        return None
    p = path_prefix
    paths = []
    provisions = []
    for sc in mvc.get("scope") or []:
        domain, typ, date = sc.get("domain"), sc.get("type"), sc.get("date")
        code = local_coding(DOMAIN_CS, domain) if domain else None
        if not code:
            ctx.drop(f"{p}.scope[].domain", domain, "unknown MV consent domain (not in mvgs-cs-mv-consent-domain)")
            continue
        if typ not in ("permit", "deny"):
            ctx.drop(f"{p}.scope[].type", typ, f"scope entry ({domain}) without permit/deny type; provision not emitted")
            continue
        if not date:
            ctx.drop(f"{p}.scope[].date", date, f"scope entry ({domain}) without signature date; provision not emitted")
            continue
        provisions.append({"type": typ, "period": {"start": date}, "code": [cc(code)]})
        paths += [f"{p}.scope[].domain", f"{p}.scope[].type", f"{p}.scope[].date"]
    if not provisions:
        ctx.warn(p, "MV consent without a usable scope entry; no Consent emitted")
        for k in ("version", "presentationDate"):
            if mvc.get(k):
                ctx.drop(f"{p}.{k}", mvc[k], "MV consent without a usable scope entry; no Consent emitted")
        return None

    dates = sorted(x["period"]["start"] for x in provisions)
    if mvc.get("presentationDate"):
        date_time = mvc["presentationDate"]
        paths.append(f"{p}.presentationDate")
    else:
        date_time = dates[0]      # presentation date is only given when it differs from the signature date
    version = mvc.get("version")

    con = ctx.new("Consent", "mv-consent", *id_parts, profile=PROFILE)
    con.update(
        status="active",
        scope=cc(coding(CONSENT_SCOPE, "patient-privacy", "Privacy Consent")),
        category=[PRIVACY_CATEGORY],
        patient=patient_ref,
        dateTime=date_time,
        policyRule={"text": version} if version else None,
        provision={"provision": provisions},
    )
    if version:
        paths.append(f"{p}.version")
    else:   # schema-required; keep the resource valid against ppc-1 only if a version exists
        ctx.warn(f"{p}.version", "MV consent without version; policyRule missing")
    ctx.rep("mvgs-consent")
    return ctx.add(con, *paths)
