"""Deterministic, sender-scoped resource identities (docs/IDENTITY.md).

Every resource id is uuid5(NAMESPACE, "<stream>|<submitterId>|<caseKey>|<ResourceType>|<local parts...>").
The same case re-submitted (correction, followup, addition) yields the same ids, so the
transaction `PUT Type/<id>` is idempotent and overwrites instead of duplicating (exceptions: the per-submission
resources of CaseKey.submission_parts and the Provenance, one per submission).

Components are escaped ('\\' -> '\\\\', '|' -> '\\|'), so no two different part tuples give the same string.
Test submissions (type 'test') get the case key '<caseId>|test': the unescaped separator cannot occur in an
escaped real case id, so no id or case-scoped identifier value of a test submission equals a real one.
"""
import re
import uuid
from dataclasses import dataclass
from urllib.parse import quote

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://genomde.de/fhir/genomde2fhir")
TEST_MARKER = "test"
EXTENDING = ("followup", "addition")      # submission types that extend a case instead of replacing its content
SOURCE_PREFIX = "urn:genomde2fhir:submission:"


# meta.source component: printable ASCII (0x21-0x7E) stays as it is, except the separator ':' and the characters
# servers or URL handling treat specially ('%', '|', '#', '?', '/'); everything else (blank and other whitespace,
# control characters, non-ASCII) is percent-encoded as UTF-8 bytes, '%' + two uppercase hex digits per byte
SOURCE_ENCODED = re.compile(r"[^\x21-\x7e]|[%:|#?/]")


def source_component(part) -> str:
    """One meta.source component, percent-encoded (SOURCE_ENCODED; None -> ''). The separator ':' is itself in
    SOURCE_ENCODED, so no encoded component contains a literal ':' and the joined value splits back into the same
    components. '%' is encoded too, so the encoding is reversible: a literal '%3A' in the input becomes '%253A' and
    cannot collide with an encoded ':'. Together: different component tuples give different values."""
    return SOURCE_ENCODED.sub(lambda m: quote(m.group(), safe=""), "" if part is None else str(part))


def esc(part) -> str:
    """One id / identifier-value component: None -> '', the escape char and the separator '|' escaped."""
    return "" if part is None else str(part).replace("\\", "\\\\").replace("|", "\\|")


def join(*parts) -> str:
    """'|'-joined escaped components; None parts are kept as '' so positions stay stable."""
    return "|".join(esc(p) for p in parts)


def rid(*parts) -> str:
    """uuid5 over the joined, escaped parts."""
    return str(uuid.uuid5(NAMESPACE, join(*parts)))


@dataclass(frozen=True)
class CaseKey:
    stream: str            # 'kdk' or 'grz'
    submitter_id: str
    case_id: str           # caseKey component as it appears in ids and identifier values: the escaped localCaseId
                           # (the TAN when the file has none), '|test' appended for test submissions
    case_id_is_local: bool
    tan: str
    submission_type: str
    submission_date: str

    @property
    def test(self) -> bool:
        return self.submission_type == TEST_MARKER

    def id(self, rtype: str, *parts) -> str:
        return str(uuid.uuid5(NAMESPACE, "|".join((join(self.stream, self.submitter_id), self.case_id,
                                                   join(rtype, *parts)))))

    def scoped(self, *parts) -> str:
        """Case-scoped identifier value '<submitterId>|<caseKey>[|<part>...]' (docs/IDENTITY.md)."""
        return "|".join((esc(self.submitter_id), self.case_id) + ((join(*parts),) if parts else ()))

    def sender_scoped(self, *parts) -> str:
        """Sender-scoped identifier value '<submitterId>|<part>...' for ids that are not per case (sample
        barcode); test submissions get '|test' appended, like the case key."""
        return join(self.submitter_id, *parts) + ("|" + TEST_MARKER if self.test else "")

    def submission_parts(self) -> tuple:
        """Id parts of a resource that exists once per submission but must be overwritten by a correction
        (docs/IDENTITY.md): none for initial / correction / test, so a correction rewrites the resource in place (the
        schema does not say which submission a correction corrects; it is taken to correct the initial one), the
        submission date for a follow-up / addition, which gets its own resource."""
        return (self.submission_date,) if self.submission_type in EXTENDING else ()

    @property
    def raw_case_id(self) -> str:
        """The case id as sent (localCaseId, else the TAN): case_id without the test marker and the escaping."""
        cid = self.case_id[:-len("|" + TEST_MARKER)] if self.test else self.case_id
        return re.sub(r"\\(.)", r"\1", cid, flags=re.S)

    @property
    def source(self) -> str:
        """meta.source of every resource (docs/IDENTITY.md): 'urn:genomde2fhir:submission:' + the ':'-joined
        components submitterId, case id (localCaseId, else the TAN; raw, not identity-escaped), submission date and
        submission type, each percent-encoded by source_component. A test submission differs by its type 'test'."""
        return SOURCE_PREFIX + ":".join(source_component(p) for p in (
            self.submitter_id, self.raw_case_id, self.submission_date, self.submission_type))


def _case(case_id: str, submission_type: str) -> str:
    return esc(case_id) + ("|" + TEST_MARKER if submission_type == TEST_MARKER else "")


def case_key(dk: dict, branch: str) -> CaseKey:
    if branch == "grz":
        s = dk.get("submission") or {}
        local, stype = s.get("localCaseId"), s.get("submissionType") or ""
        return CaseKey("grz", s.get("submitterId") or "", _case(local or s.get("tanG") or "", stype), bool(local),
                       s.get("tanG") or "", stype, s.get("submissionDate") or "")
    md = dk.get("metaData") or {}
    s = md.get("submission") or {}
    local, stype = md.get("localCaseId"), s.get("type") or ""
    return CaseKey("kdk", s.get("submitterId") or "", _case(local or md.get("tanC") or "", stype), bool(local),
                   md.get("tanC") or "", stype, s.get("date") or "")
