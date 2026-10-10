"""Round-4 integration guards: no conversion scratch output in the checkout; the suite runs without git-ignored
generated files (mapping/_leaves_*.csv) and without example-data/synthData-v1."""
import fnmatch
import shutil
import subprocess

import pytest

from conftest import REPO

SCRATCH = ("*.bundle.json", "in.json", "out_*.json")


def _git_files(*args):
    if not shutil.which("git") or not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", *args], capture_output=True, check=True)
    return [p for p in out.stdout.decode("utf-8").split("\0") if p]


def test_no_scratch_output_in_checkout():
    files = _git_files("--cached", "--others", "--exclude-standard")
    stray = [p for p in files if not p.startswith("example-data/synthData-v1/")
             and any(fnmatch.fnmatch(p.rsplit("/", 1)[-1], g) for g in SCRATCH)]
    assert not stray, stray


def test_synthetic_corpus_not_tracked():
    assert not _git_files("--cached", "example-data/synthData-v1")


def test_leaves_check_tolerates_missing_generated_files(tmp_path, monkeypatch):
    import test_fix4_docs as docs
    for name in docs.CSVS:
        shutil.copy(docs.MAP / name, tmp_path / name)
    monkeypatch.setattr(docs, "MAP", tmp_path)
    docs.test_mapping_csvs_keep_crlf_and_source_columns()     # no _leaves_*.csv in tmp_path: must not raise
