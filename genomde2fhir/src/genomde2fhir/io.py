"""Input discovery (files, directories, globs, zip archives), branch detection and the input gate."""
import glob
import json
import zipfile
from functools import lru_cache
from pathlib import Path

try:  # optional: schema validation + unknown-field detection (genomde-dk-validator)
    from genomde_dk_validator import DatenkranzValidator, classify as _dkv_classify
except ImportError:  # pragma: no cover - exercised only without the extra
    DatenkranzValidator = None
    _dkv_classify = None

BRANCHES = ("oncology", "rare-disease", "grz")


def classify(dk) -> str:
    """'oncology' | 'rare-disease' | 'grz' | 'legacy-variant' | 'unknown' (same rules as genomde-dk-validator)."""
    if _dkv_classify:
        return _dkv_classify(dk)
    if not isinstance(dk, dict):
        return "unknown"
    if "donors" in dk and "submission" in dk:
        return "grz"
    case = dk.get("case") if isinstance(dk.get("case"), dict) else {}
    if "diagnosisOd" in case:
        return "oncology"
    if "diagnosisRd" in case:
        return "rare-disease"
    return "legacy-variant" if "metadata" in dk and "metaData" not in dk else "unknown"


@lru_cache(maxsize=1)
def _validator():
    return DatenkranzValidator(check_unknown=True) if DatenkranzValidator else None


def validate_input(dk, name: str):
    """Schema-validate one Datenkranz document. Returns (ok, findings) where findings are strings;
    (True, ['input validation skipped ...']) when genomde-dk-validator is not installed."""
    v = _validator()
    if v is None:
        return True, ["input validation skipped: genomde-dk-validator not installed (pip install 'genomde2fhir[input]')"]
    res = v.validate(dk, name)
    findings = [f"{f.path}: {f.message}" for f in res.schema_errors] + \
               [f"unknown field {f.path}" for f in res.unknown_fields]
    return res.ok(strict=False), findings


def discover(paths) -> list[tuple[str, object]]:
    """Expand paths (file, directory recursively, glob, .zip) to [(name, loader)], sorted by name.
    Hidden directories (e.g. .ipynb_checkpoints) are skipped."""
    out = []
    for p in paths:
        hits = [Path(x) for x in glob.glob(str(p), recursive=True)] or [Path(p)]
        for h in hits:
            if h.is_dir():
                for f in sorted(h.rglob("*.json")):
                    if not any(part.startswith(".") for part in f.relative_to(h).parts):
                        out.append((str(f), _file_loader(f)))
            elif h.suffix == ".zip":
                with zipfile.ZipFile(h) as z:
                    for n in sorted(z.namelist()):
                        if n.endswith(".json") and not n.startswith(("__MACOSX", ".")):
                            out.append((f"{h}!{n}", _zip_loader(h, n)))
            elif h.is_file():
                out.append((str(h), _file_loader(h)))
            else:
                raise FileNotFoundError(str(p))
    return out


def _file_loader(f: Path):
    return lambda: json.loads(f.read_text(encoding="utf-8"))


def _zip_loader(z: Path, n: str):
    def load():
        with zipfile.ZipFile(z) as zz:
            return json.loads(zz.read(n).decode("utf-8"))
    return load
