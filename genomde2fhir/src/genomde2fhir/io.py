"""Input discovery (files, directories, globs, zip archives), branch detection, the input gate and
precision-preserving JSON reading/writing."""
import glob
import json
import os
import re
import shlex
import subprocess
import sys
import uuid
import zipfile
from functools import lru_cache
from pathlib import Path, PurePosixPath

try:  # optional: schema validation + unknown-field detection (genomde-dk-validator)
    from genomde_dk_validator import DatenkranzValidator, classify as _dkv_classify
except ImportError:  # pragma: no cover - exercised only without the extra
    DatenkranzValidator = None
    _dkv_classify = None

BRANCHES = ("oncology", "rare-disease", "grz")
# genomde-dk-validator is not on PyPI (the 'input' extra cannot resolve from an index): install it from git
VALIDATOR_REQ = "genomde-dk-validator @ git+https://github.com/KohlbacherLab/genomde-dk-validator@v1.1.2"


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


def input_check_available() -> bool:
    """True when genomde-dk-validator is installed (the CLI refuses to convert without it unless --no-input-check)."""
    return DatenkranzValidator is not None


def validator_install_hint(executable: str | None = None, windows: bool | None = None) -> str:
    """The two ways to add genomde-dk-validator to the environment genomde2fhir runs in: a pipx venv has no pip
    ('pipx inject'); otherwise the pip of this interpreter (a pip on PATH may belong to another environment).
    The interpreter path is quoted for the shell it is pasted into: POSIX sh quoting, on Windows double quotes only
    when the path needs them (cmd.exe; PowerShell runs a quoted path only after '&', said on an extra line).
    executable / windows default to sys.executable / os.name == 'nt'."""
    exe = sys.executable if executable is None else executable
    win = os.name == "nt" if windows is None else windows
    req = f'"{VALIDATOR_REQ}"'
    quoted = subprocess.list2cmdline([exe]) if win else shlex.quote(exe)
    hint = (f"  installed with pipx: pipx inject genomde2fhir {req}\n"
            f"  installed with pip:  {quoted} -m pip install {req}")
    if win and quoted.startswith('"'):
        hint += "\n  (PowerShell: put '& ' in front of the quoted interpreter path)"
    return hint


def validate_input(dk, name: str, strict: bool = False):
    """Schema-validate one Datenkranz document. Returns (ok, findings) where findings are strings
    ('<path>: <message>' for schema errors, 'unknown field <path>' for fields the schema does not declare);
    strict=True also fails on unknown fields. (True, ['input validation skipped ...']) when
    genomde-dk-validator is not installed."""
    v = _validator()
    if v is None:
        return True, [f"input validation skipped: genomde-dk-validator not installed (pipx inject genomde2fhir "
                      f"\"{VALIDATOR_REQ}\", or pip install \"{VALIDATOR_REQ}\")"]
    res = v.validate(dk, name)
    findings = [f"{f.path}: {f.message}" for f in res.schema_errors] + \
               [f"unknown field {f.path}" for f in res.unknown_fields]
    return res.ok(strict=strict), findings


def discover(paths) -> list[tuple[str, object]]:
    """Expand paths to [(name, loader)]: a file as given, a directory recursively (*.json and *.zip, any case), a
    .zip archive (its *.json members) or a glob pattern. An existing path is used literally, never glob-expanded.
    Hidden files and directories (.name, __MACOSX) below a directory or inside an archive are skipped at any depth.
    Hits of each argument are sorted by name; a file reached twice (resolved path) is listed once. An argument that
    matches nothing, or an unreadable archive, yields a loader that raises, so the caller reports it per input."""
    out, seen = [], set()

    def add(key, name, loader):
        if key not in seen:
            seen.add(key)
            out.append((name, loader))

    def add_file(f: Path):
        if f.suffix.lower() != ".zip":
            add(f.resolve(), str(f), _file_loader(f))
            return
        try:
            with zipfile.ZipFile(f) as z:
                names = sorted(z.namelist())
        except (OSError, zipfile.BadZipFile) as ex:
            add(f.resolve(), str(f), _raiser(ex))
            return
        for n in names:
            if n.lower().endswith(".json") and not _hidden(PurePosixPath(n).parts):
                add((f.resolve(), n), f"{f}!{n}", _zip_loader(f, n))

    for p in map(str, paths):
        hits = [Path(p)] if Path(p).exists() else sorted(Path(x) for x in glob.glob(p, recursive=True))
        if not hits:
            add(("missing", p), p, _raiser(FileNotFoundError(f"no such file or directory: {p}")))
        for h in hits:
            if h.is_dir():
                for f in sorted(h.rglob("*")):
                    if f.suffix.lower() in (".json", ".zip") and not _hidden(f.relative_to(h).parts) and f.is_file():
                        add_file(f)
            else:
                add_file(h)
    return out


def _hidden(parts) -> bool:
    return any(part.startswith(".") or part == "__MACOSX" for part in parts)


def _raiser(ex: Exception):
    def load():
        raise ex
    return load


class Num(float):
    """A JSON number read from the input that remembers how it was written. It is a float for every builder (same
    arithmetic, comparisons, str() and ids as before), and dumps() writes it back verbatim, so 12.50 stays 12.50:
    FHIR decimals carry their precision, as in the FML output. (decimal.Decimal is not used: builder arithmetic
    such as round(x * 100, 6) would change, and json.dumps elsewhere cannot serialise it.)"""
    __slots__ = ("text",)

    def __new__(cls, text: str):
        o = super().__new__(cls, text)
        o.text = text
        return o

    def __reduce__(self):   # copy / deepcopy / pickle keep the spelling
        return Num, (self.text,)


def loads(s: str | bytes):
    """json.loads with input numbers as Num (written precision kept)."""
    return json.loads(s, parse_float=Num)


def dumps(obj, indent=1) -> str:
    """json.dumps(ensure_ascii=False) that writes Num values with their input spelling."""
    raw, tag = [], uuid.uuid4().hex   # random tag: cannot collide with a string in the data

    def walk(o):
        if isinstance(o, Num):
            raw.append(o.text)
            return f"{tag}{len(raw) - 1}"
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [walk(v) for v in o]
        return o
    s = json.dumps(walk(obj), ensure_ascii=False, indent=indent)
    return re.sub(f'"{tag}(\\d+)"', lambda m: raw[int(m.group(1))], s) if raw else s


def _file_loader(f: Path):
    return lambda: loads(f.read_text(encoding="utf-8"))


def _zip_loader(z: Path, n: str):
    def load():
        with zipfile.ZipFile(z) as zz:
            return loads(zz.read(n).decode("utf-8"))
    return load
