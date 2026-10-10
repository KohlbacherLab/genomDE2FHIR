"""Per-file conversion report: dispositions (implemented / preserved / dropped), warnings, counts."""
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class Report:
    file: str
    branch: str = ""
    profile_set: str = ""
    status: str = "pending"            # converted | rejected | error
    submission_type: str = ""          # initial | followup | addition | correction | test (docs/IDENTITY.md)
    submission_date: str = ""
    test: bool = False                 # test submission: separate identity namespace, meta.security HTEST
    case_key_fallback: bool = False    # no localCaseId: the case key is the per-submission TAN (warning)
    input_findings: list = field(default_factory=list)   # schema findings from genomde-dk-validator
    resources: Counter = field(default_factory=Counter)
    covered: set = field(default_factory=set)            # mapping paths emitted (implemented), plus undeclared
                                                         # input fields a builder converts (Ctx.cover_undeclared)
    preserved: set = field(default_factory=set)          # kept, but not in a conformant MII element
    dropped: list = field(default_factory=list)          # (path, value, reason)
    warnings: list = field(default_factory=list)         # (path, message)
    representations: Counter = field(default_factory=Counter)
    error: str = ""
    output: str = ""                   # CLI: the bundle file this input was written to (renamed on a clash, or the
                                       # --single-bundle file); empty when none was written

    def to_dict(self) -> dict:
        return {
            "file": self.file, "branch": self.branch, "profile_set": self.profile_set, "status": self.status,
            "submission_type": self.submission_type, "submission_date": self.submission_date, "test": self.test,
            "case_key_fallback": self.case_key_fallback,
            "input_findings": self.input_findings, "resources": dict(self.resources),
            "covered": sorted(self.covered), "preserved": sorted(self.preserved),
            "dropped": [{"path": p, "value": v, "reason": r} for p, v, r in self.dropped],
            "warnings": [{"path": p, "message": m} for p, m in self.warnings],
            "representations": dict(self.representations), "error": self.error, "output": self.output,
        }


def summarize(reports) -> dict:
    status = Counter(r.status for r in reports)
    branches = Counter(r.branch for r in reports)
    res, reps, drops = Counter(), Counter(), Counter()
    covered = set()
    for r in reports:
        res.update(r.resources)
        reps.update(r.representations)
        drops.update(p for p, _, _ in r.dropped)
        covered |= {(r.branch, p) for p in r.covered}
    return {"files": len(reports), "status": dict(status), "branches": dict(branches),
            "submission_types": dict(Counter(r.submission_type for r in reports if r.submission_type)),
            "test_submissions": sum(1 for r in reports if r.test),
            "case_key_tan_fallback": sum(1 for r in reports if r.case_key_fallback),
            "resources": dict(res), "representations": dict(reps),
            "dropped_by_path": dict(drops.most_common()), "covered_paths": len(covered)}
