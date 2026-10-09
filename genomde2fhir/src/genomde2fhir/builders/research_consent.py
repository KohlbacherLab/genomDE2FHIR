"""Embedded MII Broad Consent (metaData.researchConsents[] / donors[].researchConsents[]) -> mii-pr-consent-einwilligung.

The KDK carries the Broad Consent as an opaque 'MII Consent 2025.0.1' FHIR object (scope); it is migrated to the
2027 profile (docs/REPRESENTATIONS.md #35; the same element changes satisfy consent 2026.0.0):
  - id / meta / text / contained of the source system are replaced: deterministic id, versionless meta.profile
  - patient -> our Patient (the source reference points into the sender's system)
  - category: the 2025 coding `mii-cs-consent-consent_category#...2.184` moves to `mii-cs-consent-version-modules`
    (slice category:mii); LOINC 57016-8 (slice category:consentCategory) is added if missing
  - policy.uri: bare OIDs -> `urn:oid:` form (as in the MII examples)
  - literal references into the sender's system (DomainReference -> ResearchStudy, performer, source, ...) cannot
    resolve in our transaction; they are removed (display/identifier kept), a DomainReference without a usable
    domain is dropped as a whole
  - dateTime = researchConsents[].presentationDate (mapping table row; the embedded dateTime is reported if it differs)
Entries without scope (noScopeJustification) -> Observation `mvgs-research-consent-absent` (value = reason).
Rows: metaData.researchConsents[].* (KDK), donors[].researchConsents[].* (GRZ).
"""
import copy
import re

from ..systems import CONSENT, LOINC, MVGS_SD
from ..terminology import local_coding
from .common import cc, coding
from .consent import mark

PROFILE = CONSENT + "StructureDefinition/mii-pr-consent-einwilligung"
ABSENT_PROFILE = MVGS_SD + "mvgs-research-consent-absent"
CS_2025_CATEGORY = CONSENT + "CodeSystem/mii-cs-consent-consent_category"
CS_VERSION_MODULES = CONSENT + "CodeSystem/mii-cs-consent-version-modules"
MII_BROAD_CONSENT = "2.16.840.1.113883.3.1937.777.24.2.184"
CONSENT_SCOPE = "http://terminology.hl7.org/CodeSystem/consentscope"
DOMAIN_REFERENCE = "http://fhir.de/ConsentManagement/StructureDefinition/DomainReference"
OID = re.compile(r"^[0-2](\.(0|[1-9][0-9]*))+$")
# elements of the source Consent that are carried over (everything else is source-system bookkeeping)
KEEP = ("identifier", "language", "extension", "modifierExtension", "status", "scope", "category", "performer",
        "organization", "sourceAttachment", "sourceReference", "policy", "policyRule", "verification", "provision")
# researchConsents[].noScopeJustification (BfArM enum) -> mvgs-cs-research-consent-absence-reason
ABSENCE_REASON = {
    "patient unable to consent": "unable-to-consent",
    "patient refuses to sign consent": "refused",
    "patient did not return consent documents": "documents-not-returned",
    "other patient-related reason": "other-patient-reason",
    "consent information cannot be submitted by LE due to technical reason": "technical-reason",
    "consent is not implemented at LE due to organizational issues": "not-implemented",
}


def build(ctx):
    md = ctx.dk.get("metaData") or {}
    for i, rc in enumerate(md.get("researchConsents") or []):
        ref = build_research_consent(ctx, rc, ctx.patient, "metaData.researchConsents[]", (i,))
        if ref:
            ctx.bag["research_consents"].append(ref)


def build_research_consent(ctx, rc: dict, patient_ref: dict, path_prefix: str, id_parts: tuple) -> dict | None:
    """Create one research consent for a patient/donor; returns its reference or None."""
    if not rc:
        return None
    p = path_prefix
    if rc.get("schemaVersion"):
        ctx.drop(f"{p}.schemaVersion", rc["schemaVersion"],
                 "source package version of the embedded consent; consumed by the migration to the target profile")
    scope = rc.get("scope")
    if isinstance(scope, dict) and scope:
        return _migrate(ctx, rc, scope, patient_ref, p, id_parts)
    if scope is not None:
        ctx.drop(f"{p}.scope", str(scope)[:80], "empty or non-object research consent scope")
    if rc.get("noScopeJustification"):
        return _absent(ctx, rc, patient_ref, p, id_parts)
    _drop_date(ctx, rc, p, "research consent entry without content")
    return None


def _drop_date(ctx, rc, p, why):
    if rc.get("presentationDate"):
        ctx.drop(f"{p}.presentationDate", rc["presentationDate"], why)


def _absent(ctx, rc, patient_ref, p, id_parts):
    nsj = rc["noScopeJustification"]
    code = ABSENCE_REASON.get(nsj)
    value = local_coding("mvgs-cs-research-consent-absence-reason", code) if code else None
    if not value:
        ctx.drop(f"{p}.noScopeJustification", nsj, "unknown noScopeJustification value")
        _drop_date(ctx, rc, p, "research consent entry with an unknown noScopeJustification")
        return None
    obs = ctx.new("Observation", "research-consent-absent", *id_parts, profile=ABSENT_PROFILE)
    obs.update(status="final", code=cc(local_coding("mvgs-cs-mv-administrative", "research-consent-absent")),
               subject=patient_ref, effectiveDateTime=rc.get("presentationDate"), valueCodeableConcept=cc(value))
    mark(ctx, f"{p}.noScopeJustification", "mvgs-research-consent-absent")
    return ctx.add(obs, *([f"{p}.presentationDate"] if rc.get("presentationDate") else []))


def _migrate(ctx, rc, scope, patient_ref, p, id_parts):
    src = copy.deepcopy(scope)
    if src.get("resourceType") != "Consent":
        ctx.drop(f"{p}.scope", src.get("resourceType"), "embedded research consent is not a FHIR Consent")
        _drop_date(ctx, rc, p, "embedded research consent not emitted")
        return None
    if src.get("status") is None:
        ctx.drop(f"{p}.scope", src.get("id"), "embedded consent without status (required); not emitted")
        _drop_date(ctx, rc, p, "embedded research consent not emitted")
        return None
    con = ctx.new("Consent", "research-consent", *id_parts, profile=PROFILE)
    for k in KEEP:
        if k in src:
            con[k] = src[k]
    dropped_keys = sorted(set(src) - set(KEEP) - {"resourceType", "id", "meta", "text", "contained", "patient",
                                                   "dateTime", "implicitRules"})
    if dropped_keys:
        ctx.warn(f"{p}.scope", f"embedded consent elements not carried over: {', '.join(dropped_keys)}")

    con["patient"] = patient_ref
    if rc.get("presentationDate"):
        if src.get("dateTime") and src["dateTime"] != rc["presentationDate"]:
            ctx.warn(f"{p}.presentationDate", f"embedded dateTime {src['dateTime']} replaced by presentationDate "
                                              f"{rc['presentationDate']}")
        con["dateTime"] = rc["presentationDate"]
    elif src.get("dateTime"):
        con["dateTime"] = src["dateTime"]

    _fix_scope(ctx, con, p)
    _fix_category(ctx, con, p)
    _fix_policy(con)
    con["extension"] = _domain_references(ctx, con.get("extension") or [], p)
    _strip_external_refs(ctx, con, p, "Consent")
    src_ref = con.get("sourceReference")
    if src_ref is not None and not src_ref.get("reference"):
        # mii-pr-consent-einwilligung: source[x].reference 1..1 -> a Reference without a resolvable target is invalid
        ctx.warn(f"{p}.scope", f"Consent.sourceReference {src_ref!r} without a resolvable reference removed")
        con.pop("sourceReference")
    if not con.get("policy") and not con.get("policyRule"):
        ctx.warn(f"{p}.scope", "embedded consent without policy (policy 1..* in mii-pr-consent-einwilligung)")
    ctx.rep("research-consent-migrated-2027")
    return ctx.add(con, f"{p}.scope", *([f"{p}.presentationDate"] if rc.get("presentationDate") else []))


def _fix_scope(ctx, con, p):
    codings = (con.get("scope") or {}).get("coding") or []
    if not any(c.get("system") == CONSENT_SCOPE and c.get("code") == "research" for c in codings):
        ctx.warn(f"{p}.scope", f"embedded consent scope {codings!r} set to consentscope#research (Broad Consent)")
    con["scope"] = cc(coding(CONSENT_SCOPE, "research"))


def _fix_category(ctx, con, p):
    cats = []
    for cat in con.get("category") or []:
        cat = dict(cat)
        cat["coding"] = [dict(c, system=CS_VERSION_MODULES) if c.get("system") == CS_2025_CATEGORY else c
                         for c in cat.get("coding") or []]
        cats.append(cat)

    def has(system, code):
        return any(c.get("system") == system and c.get("code") == code for cat in cats for c in cat.get("coding", []))
    if not has(LOINC, "57016-8"):
        ctx.warn(f"{p}.scope", "embedded consent without category LOINC 57016-8; added")
        cats.insert(0, cc(coding(LOINC, "57016-8")))
    if not has(CS_VERSION_MODULES, MII_BROAD_CONSENT):
        ctx.warn(f"{p}.scope", "embedded consent without category MII Broad Consent (...24.2.184); added")
        cats.insert(1, cc(coding(CS_VERSION_MODULES, MII_BROAD_CONSENT)))
    con["category"] = cats


def _fix_policy(con):
    for pol in con.get("policy") or []:
        for k in ("uri", "authority"):
            if isinstance(pol.get(k), str) and OID.match(pol[k]):
                pol[k] = "urn:oid:" + pol[k]


def _domain_references(ctx, exts, p):
    """Keep DomainReference extensions only when their domain can be expressed without a dangling reference."""
    out = []
    for e in exts:
        if e.get("url") != DOMAIN_REFERENCE:
            out.append(e)
            continue
        dom = next((x for x in e.get("extension", []) if x.get("url") == "domain"), {})
        ref = dict(dom.get("valueReference") or {})
        if _external(ref.get("reference")):
            ref.pop("reference")
        if ref.get("reference") or ref.get("identifier") or ref.get("display"):
            dom["valueReference"] = ref
            out.append(e)
        else:
            ctx.warn(f"{p}.scope", f"DomainReference to {dom.get('valueReference', {}).get('reference')!r} (sender "
                                   "system, not in the bundle) dropped")
    return out


def _external(r) -> bool:
    return isinstance(r, str) and not r.startswith(("urn:uuid:", "#"))


def _strip_external_refs(ctx, o, p, where):
    """Remove literal references into the sender's system (they cannot resolve in our transaction)."""
    if isinstance(o, dict):
        if _external(o.get("reference")) and where != "Consent.patient":
            ctx.warn(f"{p}.scope", f"{where}: reference {o['reference']!r} into the sender system removed")
            target = o.pop("reference")
            if not (o.get("display") or o.get("identifier")) and where != "Consent.sourceReference":
                # keep the target as text: removing e.g. provision.actor.reference (1..1) would otherwise drop the
                # Reference and widen the provision to everyone
                o["display"] = f"{target} (sender system)"
        for k, v in o.items():
            _strip_external_refs(ctx, v, p, f"{where}.{k}")
    elif isinstance(o, list):
        for v in o:
            _strip_external_refs(ctx, v, p, where)
