"""Deterministic, sender-scoped resource identities (docs/IDENTITY.md).

Every resource id is uuid5(NAMESPACE, "<stream>|<submitterId>|<caseKey>|<ResourceType>|<local parts...>").
The same case re-submitted (correction, followup, addition) yields the same ids, so the
transaction `PUT Type/<id>` is idempotent and overwrites instead of duplicating.
"""
import uuid
from dataclasses import dataclass

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://genomde.de/fhir/genomde2fhir")


def rid(*parts) -> str:
    """uuid5 over the '|'-joined string parts; None parts are kept as '' so positions stay stable."""
    return str(uuid.uuid5(NAMESPACE, "|".join("" if p is None else str(p) for p in parts)))


@dataclass(frozen=True)
class CaseKey:
    stream: str            # 'kdk' or 'grz'
    submitter_id: str
    case_id: str           # localCaseId, falling back to the TAN when the KDK file has none
    case_id_is_local: bool
    tan: str
    submission_type: str
    submission_date: str

    def id(self, rtype: str, *parts) -> str:
        return rid(self.stream, self.submitter_id, self.case_id, rtype, *parts)


def case_key(dk: dict, branch: str) -> CaseKey:
    if branch == "grz":
        s = dk.get("submission") or {}
        local = s.get("localCaseId")
        return CaseKey("grz", s.get("submitterId") or "", local or s.get("tanG") or "", bool(local),
                       s.get("tanG") or "", s.get("submissionType") or "", s.get("submissionDate") or "")
    md = dk.get("metaData") or {}
    s = md.get("submission") or {}
    local = md.get("localCaseId")
    return CaseKey("kdk", s.get("submitterId") or "", local or md.get("tanC") or "", bool(local),
                   md.get("tanC") or "", s.get("type") or "", s.get("date") or "")
