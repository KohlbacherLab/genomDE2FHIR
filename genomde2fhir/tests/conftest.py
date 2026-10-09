"""Shared pytest helpers: corpus manifest, conversion, resource lookup."""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((Path(__file__).parent / "corpus_manifest.json").read_text())


def corpus(branch: str, kind: str = "valid") -> list[Path]:
    """Corpus files of the manifest that exist in this checkout (example-data/synthData-v1 is not in git;
    CI runs on examples/ and tests/fixtures/ only)."""
    return [p for p in (REPO / f for f in MANIFEST.get(branch, {}).get(kind, [])) if p.is_file()]


def load(path) -> dict:
    path = Path(path) if Path(path).is_absolute() else REPO / path
    if not path.is_file():   # synthetic corpus files are not distributed with the repository
        pytest.skip(f"{path.relative_to(REPO) if path.is_relative_to(REPO) else path} not in this checkout")
    return json.loads(path.read_text(encoding="utf-8"))


def resources(bundle: dict, rtype: str | None = None, profile: str | None = None) -> list[dict]:
    out = []
    for e in bundle["entry"]:
        r = e["resource"]
        if rtype and r["resourceType"] != rtype:
            continue
        if profile and not any(profile in p for p in r.get("meta", {}).get("profile", [])):
            continue
        out.append(r)
    return out


def first_with(branch: str, predicate, limit: int = 400):
    """First valid corpus file whose JSON satisfies predicate(dk)."""
    for f in corpus(branch)[:limit]:
        dk = load(f)
        if predicate(dk):
            return f, dk
    pytest.skip(f"no {branch} corpus file matches")


@pytest.fixture
def convert_dk():
    from genomde2fhir import convert

    def _run(dk, name="<test>", profile_set="2027", strict=False):
        bundle, rep = convert(dk, name, profile_set, strict=strict)
        assert rep.status == "converted", rep.error or rep.input_findings
        return bundle, rep
    return _run
