"""Conversion context handed to every builder."""
from collections import defaultdict

from .bundle import BundleBuilder, prune
from .data_access import canonical_index, mapping_rows
from .identity import CaseKey
from .report import Report

PROFILE_SETS = ("2027", "2026")


class ProfileError(ValueError):
    pass


class Ctx:
    """State for converting one Datenkranz file.

    Builders read `ctx.dk`, create resources with `ctx.new(...)`, add them with `ctx.add(...)`,
    look up earlier resources in `ctx.refs`, and record dispositions with `ctx.cover/preserve/drop/warn`.
    Mapping paths are the `path` column of the mapping CSV for the branch (validated in strict mode).
    """

    def __init__(self, dk: dict, branch: str, key: CaseKey, profile_set: str = "2027",
                 report: Report | None = None, strict: bool = False):
        if profile_set not in PROFILE_SETS:
            raise ValueError(f"profile set must be one of {PROFILE_SETS}")
        self.dk, self.branch, self.key, self.ps, self.strict = dk, branch, key, profile_set, strict
        self.report = report or Report(file="")
        self.bundle = BundleBuilder()
        self.refs: dict = {}         # named references produced by earlier builders (e.g. 'patient', 'primary')
        self.ids: dict = {}          # (kind, source id) -> reference, e.g. ('variant', 'SV1') for recommendations
        self.bag = defaultdict(list)  # cross-builder collections, e.g. bag['ngs_results'] -> [reference, ...]
        self.finishers: list = []     # callables run after the whole pipeline (convert.py)
        self._rows = mapping_rows(branch)

    # ---- identities and resources ---------------------------------------------------------------
    def id(self, rtype: str, *parts) -> str:
        return self.key.id(rtype, *parts)

    def new(self, rtype: str, *id_parts, profile: str | list | None = None) -> dict:
        """Resource skeleton {resourceType, id, meta.profile}; profile canonical(s) are checked against
        the canonical index for the active profile set."""
        r = {"resourceType": rtype, "id": self.id(rtype, *id_parts)}
        profiles = [profile] if isinstance(profile, str) else (profile or [])
        for p in profiles:
            self.check_canonical(p)
        if profiles:
            r["meta"] = {"profile": profiles}
        return r

    def add(self, resource: dict, *paths, name: str | None = None, replace: bool = False) -> dict:
        """Prune empty elements, add as PUT, record covered mapping paths; returns the reference."""
        resource = prune(resource)
        new = not self.bundle.has(resource["id"])
        ref = self.bundle.put(resource, replace=replace)
        if new:
            self.report.resources[resource["resourceType"]] += 1
        self.cover(*paths)
        if name:
            self.refs[name] = ref
        return ref

    def check_canonical(self, url: str):
        idx = canonical_index()
        if not idx:
            return
        hit = idx.get(url.split("|")[0])
        if not hit or self.ps not in hit.get("sets", []) and "mvgs" not in hit.get("sets", []):
            msg = f"canonical not in profile set {self.ps}: {url}"
            if self.strict:
                raise ProfileError(msg)
            self.warn("(profile)", msg)

    # ---- dispositions ---------------------------------------------------------------------------
    def _check_path(self, path: str):
        if self.strict and self._rows and path not in self._rows:
            raise KeyError(f"mapping path not in {self.branch} table: {path}")

    def cover(self, *paths):
        for p in paths:
            self._check_path(p)
            self.report.covered.add(p)

    def cover_undeclared(self, *paths):
        """Covered paths of input fields the schema does not declare but a builder converts (legacy keys,
        germlineDiagnoses[].date): no mapping-table row is required (no strict check), so the CLI reports the
        validator's 'unknown field' finding as converted instead of 'not converted' (cli._undeclared)."""
        self.report.covered.update(paths)

    def preserve(self, path: str, note: str = ""):
        """Value kept, but not in a conformant MII element (local profile/extension, text fallback)."""
        self._check_path(path)
        self.report.preserved.add(path)
        if note:
            self.report.representations[note] += 1

    def drop(self, path: str, value, reason: str):
        self._check_path(path)
        self.report.dropped.append((path, value if isinstance(value, (str, int, float, bool)) else str(value)[:80], reason))

    def warn(self, path: str, msg: str):
        self.report.warnings.append((path, msg))

    def rep(self, name: str):
        self.report.representations[name] += 1

    def resource(self, ref: dict | None) -> dict | None:
        """The resource dict an earlier builder added (by its reference), to append to it; None if absent."""
        if not ref:
            return None
        e = self.bundle.entries.get(ref.get("reference", ""))
        return e["resource"] if e else None

    def on_finish(self, fn):
        """Register fn(ctx) to run after all builders (e.g. to link resources created later in the pipeline)."""
        self.finishers.append(fn)

    # ---- convenience ------------------------------------------------------------------------------
    @property
    def patient(self) -> dict:
        return self.refs["patient"]

    @property
    def is_2027(self) -> bool:
        return self.ps == "2027"
