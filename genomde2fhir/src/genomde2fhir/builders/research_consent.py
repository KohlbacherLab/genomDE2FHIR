"""Embedded MII Broad Consent (metaData.researchConsents[] / donors[].researchConsents[]) -> mii-pr-consent-einwilligung.

The KDK carries the Broad Consent as an opaque 'MII Consent 2025.0.1' FHIR object (scope); it is migrated to the
2027 profile (docs/REPRESENTATIONS.md #35; the same element changes satisfy consent 2026.0.0):
  - id / meta / text of the source system are replaced (deterministic id, versionless meta.profile) and reported as
    dropped, like the source patient reference and every other element not carried over; contained resources are
    kept only when a carried-over element references them ('#id' as Reference.reference or as a canonical / uri
    value, transitively) or when they refer to the Consent itself ('#'; both satisfy dom-3), the others are dropped
  - patient -> our Patient (the source reference points into the sender's system)
  - category: the 2025 coding `mii-cs-consent-consent_category#...2.184` moves to `mii-cs-consent-version-modules`
    (slice category:mii); LOINC 57016-8 (slice category:consentCategory) is added if missing
  - policy.uri: bare OIDs -> `urn:oid:` form (as in the MII examples)
  - literal references into the sender's system (DomainReference -> ResearchStudy, performer, source, ...; also
    urn:uuid references, which name entries of the sender's Bundle) cannot resolve in our transaction; they are removed
    (display/identifier kept), a DomainReference without a usable domain is dropped as a whole (domain + status;
    warning and dropped entry)
  - dateTime = researchConsents[].presentationDate (mapping table row; the embedded dateTime is reported if it differs)
  - without policy (policy 1..* in mii-pr-consent-einwilligung) the Consent is emitted as a core Consent without that
    meta.profile (warning, preserved); without policy and policyRule a data-absent-reason policyRule keeps core ppc-1
Entries without scope (noScopeJustification) -> Observation `mvgs-research-consent-absent` (value = reason).
Rows: metaData.researchConsents[].* (KDK), donors[].researchConsents[].* (GRZ).
"""
import copy
import json
import re

from ..bundle import local_ref, prune
from ..systems import CONSENT, LOINC, MVGS_SD
from ..terminology import local_coding
from .common import cc, coding, dar_ext
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
# source elements the migration replaces -> (report value, reason); values that may carry personal data (narrative,
# patient display) are reported by element name only
REPLACED = {
    "id": (lambda v: f"id {v}", "source-system resource id; replaced by the deterministic id (docs/IDENTITY.md)"),
    "meta": (lambda v: "meta " + json.dumps(v, ensure_ascii=False)[:70],
             "source-system bookkeeping (versionId / lastUpdated / source / 2025 profile); replaced by the versionless "
             "target meta.profile"),
    "text": (lambda v: "text (narrative)", "source-system narrative; not regenerated"),
    "implicitRules": (lambda v: f"implicitRules {v}", "source-system rule set; not carried over"),
    "patient": (lambda v: "patient " + ", ".join(sorted(v)) if isinstance(v, dict) else "patient",
                "reference into the sender's patient registry (with its display); replaced by the converted Patient"),
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
    for k, (show, why) in REPLACED.items():
        if k in src:
            ctx.drop(f"{p}.scope", show(src[k]), why)
    for k in sorted(set(src) - set(KEEP) - set(REPLACED) - {"resourceType", "contained", "dateTime"}):
        ctx.drop(f"{p}.scope", k, "element of the embedded consent not carried over to mii-pr-consent-einwilligung")

    con["patient"] = patient_ref
    if rc.get("presentationDate"):
        if src.get("dateTime") and src["dateTime"] != rc["presentationDate"]:
            ctx.warn(f"{p}.presentationDate", f"embedded dateTime {src['dateTime']} replaced by presentationDate "
                                              f"{rc['presentationDate']}")
            ctx.drop(f"{p}.scope", f"dateTime {src['dateTime']}", "embedded dateTime replaced by "
                                                                  "researchConsents[].presentationDate")
        con["dateTime"] = rc["presentationDate"]
    elif src.get("dateTime"):
        con["dateTime"] = src["dateTime"]

    _fix_scope(ctx, con, p)
    _fix_category(ctx, con, p)
    _fix_policy(con)
    con["extension"] = _domain_references(ctx, con.get("extension") or [], p)
    _strip_external_refs(ctx, con, p, "Consent")
    _contained(ctx, con, src.get("contained"), p)
    con = prune(con)    # an element emptied by a removed reference must not count as present below
    src_ref = con.get("sourceReference")
    if src_ref is not None and not src_ref.get("reference"):
        # mii-pr-consent-einwilligung: source[x].reference 1..1 -> a Reference without a resolvable target is invalid
        ctx.warn(f"{p}.scope", f"Consent.sourceReference {src_ref!r} without a resolvable reference removed")
        con.pop("sourceReference")
    dates = [f"{p}.presentationDate"] if rc.get("presentationDate") else []
    if not con.get("policy"):
        # policy 1..* in mii-pr-consent-einwilligung: do not claim the profile; keep the content as a core Consent
        con.pop("meta", None)
        if not con.get("policyRule"):   # core ppc-1 (policy or policyRule); nothing to state -> data-absent-reason
            con["policyRule"] = {"extension": [dar_ext("unknown")]}
        ctx.warn(f"{p}.scope", "embedded consent without policy (policy 1..* in mii-pr-consent-einwilligung): "
                               "emitted as core Consent without that meta.profile")
        ctx.preserve(f"{p}.scope", "research-consent-core-no-policy")
        return ctx.add(con, *dates)
    ctx.rep("research-consent-migrated-2027")
    return ctx.add(con, f"{p}.scope", *dates)


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
            target = dom.get("valueReference", {}).get("reference")
            ctx.warn(f"{p}.scope", f"DomainReference to {target!r} (sender system, not in the bundle) dropped")
            ctx.drop(f"{p}.scope", f"DomainReference {target}", "domain is only a literal reference into the sender "
                                                                "system; extension dropped as a whole (domain + status)")
    return out


def _local_refs(o, key=None) -> set:
    """Ids of contained resources referenced as '#id' anywhere in o (bundle.local_ref: Reference.reference and
    canonical / uri values); '' stands for a reference to the container itself ('#')."""
    out = set()
    if isinstance(o, dict):
        for k, v in o.items():
            out |= _local_refs(v, k)
    elif isinstance(o, list):
        for v in o:
            out |= _local_refs(v, key)
    elif (cid := local_ref(key, o)) is not None:
        out.add(cid)
    return out


def _contained(ctx, con, contained, p):
    """Carry over the contained resources referenced ('#id') from the kept elements and those referring to the
    Consent ('#'), transitively; drop the others (dom-3: a contained resource must be referenced or refer to its
    container). References to a missing contained id are removed like sender-system references."""
    contained = [c for c in contained or [] if isinstance(c, dict)]
    pool = {c.get("id"): c for c in contained if c.get("id")}
    keep, todo = set(), _local_refs(con) | {cid for cid, c in pool.items() if "" in _local_refs(c)}
    while todo:
        cid = todo.pop()
        if cid in pool and cid not in keep:
            keep.add(cid)
            todo |= _local_refs(pool[cid])
    for c in contained:
        if c.get("id") not in keep:
            ctx.drop(f"{p}.scope", f"contained {c.get('resourceType')}/{c.get('id')}", "contained resource neither "
                     "referenced from the carried-over elements nor referring to the Consent")
    kept = [c for c in contained if c.get("id") in keep]
    for c in kept:
        _strip_external_refs(ctx, c, p, f"Consent.contained.{c.get('resourceType')}")
    if kept:
        con["contained"] = kept
    _unresolved_local_refs(ctx, con, keep, p, "Consent")


def _unresolved_local_refs(ctx, o, keep, p, where):
    """Remove '#id' references whose contained resource is not carried over: a Reference keeps its target as display
    text (like a sender-system reference), a canonical / uri value is removed (from its list, if repeated)."""
    def missing(k, v):
        cid = local_ref(k, v)
        return cid not in (None, "") and cid not in keep
    if isinstance(o, dict):
        r = o.get("reference")
        if missing("reference", r):
            ctx.warn(f"{p}.scope", f"{where}: reference {r!r} to a missing contained resource removed")
            o.pop("reference")
            if not (o.get("display") or o.get("identifier")):
                o["display"] = f"{r} (missing contained resource)"
        for k in list(o):
            v = o[k]
            if k != "reference" and (missing(k, v) or isinstance(v, list) and any(missing(k, x) for x in v)):
                for x in v if isinstance(v, list) else [v]:
                    if missing(k, x):
                        ctx.warn(f"{p}.scope", f"{where}.{k}: canonical/uri {x!r} to a missing contained resource "
                                               "removed")
                o[k] = [x for x in v if not missing(k, x)] if isinstance(v, list) else None
            else:
                _unresolved_local_refs(ctx, v, keep, p, f"{where}.{k}")
    elif isinstance(o, list):
        for v in o:
            _unresolved_local_refs(ctx, v, keep, p, where)


def _external(r) -> bool:
    """A literal reference out of the embedded consent: anything but '#id' (urn:uuid names the sender's Bundle)."""
    return isinstance(r, str) and not r.startswith("#")


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
