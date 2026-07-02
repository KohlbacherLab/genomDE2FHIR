I reviewed statically. I could not run tests here because the local interpreter lacks `jsonschema`/`setuptools`, and this sandbox cannot install dependencies.

**High Priority**

- [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:193): schema validation does not enable `format` checks, so `format: "date"` fields can pass as arbitrary strings. This also makes rule date handling unreliable. Fix by passing a `FormatChecker` or adding a strict in-package date validator; add the needed dependency extra if relying on `jsonschema[format]`.

- [rules.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules.py:322): rule primitive exceptions are downgraded to warnings, and [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:176) only fails `error`/`fatal`. A broken requested rule can therefore return `ok=True`. Fix: unknown primitives and primitive exceptions should be `fatal` or `error` when rules are explicitly enabled.

- [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:120): `_effective()` returns immediately on `$ref`, ignoring legal Draft 2020-12 sibling keywords. Fix by dereferencing and merging the referenced schema with sibling `properties`, `items`, and combinators.

- [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:126): combinator merging is first-wins for duplicate property names. In `anyOf`/`oneOf`, nested properties from later branches can be lost, causing false unknown-field reports. Fix by merging effective subschemas per property or by selecting/evaluating valid branches with jsonschema.

- [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:84): `_deref()` implements only absolute URLs and JSON Pointer fragments. It does not use URI resolution for relative refs, does not support anchors, and treats a resolved `null` as missing. Fix with `urllib.parse.urljoin`, explicit dict-key existence checks, and fail-fast diagnostics for unresolved refs.

- [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:52): `_build_store()` relies on `Traversable.rglob()`/`relative_to()`, which are not part of the portable `importlib.resources` Traversable API. It may work from an unpacked wheel, but it is not robust. Fix with an `iterdir()` recursive helper over Traversables.

- [pyproject.toml](/Users/kohlbach/Claude/MII/genomde-dk-validator/pyproject.toml:21): code imports `referencing` directly but only declares `jsonschema`. Add `referencing` as a direct dependency. Also pin/marker dependencies for Python 3.9: current PyPI shows `jsonschema 4.26.0` and `referencing 0.37.0` require Python `>=3.10`, while `jsonschema 4.25.1` still supports `>=3.9`.

**Medium Priority**

- [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:208): sorting errors by `list(e.absolute_path)` can raise `TypeError` if paths compare mixed `int` and `str` elements. Sort by escaped JSON pointer string instead.

- [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:72): `classify()` does not require `case` to be a dict; a string/list can produce bad branch decisions. Also mixed GRZ/KDK or OD/RD signatures silently pick one branch. Fix with strict shape checks and an `"ambiguous"` branch.

- [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:111): `$ref` cycles are handled by a magic depth cutoff, then silently return no properties. Fix with a visited set and an explicit “unresolvable/cyclic schema” diagnostic.

- [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:136): unknown-field paths are not JSON Pointer escaped. Keys containing `/` or `~` produce ambiguous paths. Escape path tokens everywhere paths are emitted.

- [validator.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/validator.py:139): unknown detection only runs when `props` is non-empty and ignores `patternProperties` / `additionalProperties` schemas. Map-like objects or schemas with declared dynamic keys will be misreported. Return effective `patternProperties` and `additionalProperties` from `_effective()`.

- [rules.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules.py:34): `resolve()` cannot address keys containing dots/brackets and has no escaping. `[]` and numeric indexes mostly work, but `a[0]` and `a.0` collapse to the same grammar. Prefer JSON Pointer for rule paths or add quoted/bracket key syntax.

- [rules.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules.py:57): `_date_tuple()` is not end-anchored and accepts invalid dates like `2026-99-99x`. Fix with full regex anchoring plus `datetime.date` validation.

- [rules.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/rules.py:89): `date_fields()` inherits `_effective()`’s branch/first-wins issues and silently stops after depth 60. Deep valid payloads can skip semantic date checks. Use explicit traversal limits that emit a fatal finding.

- [cli.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/cli.py:57): `--rules-config` accepts any JSON type. A list/string config later causes primitive `.get()` failures that are downgraded to warnings. Require a JSON object and validate expected key types before validation.

- [cli.py](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/cli.py:14): discovery dedupes raw strings, not resolved files, and glob matches can include directories. Use `Path.resolve()`, filter `is_file()`, and preserve deterministic order.

**Packaging / 3.9**

- The source syntax itself is okay for Python 3.9 because `validator.py`, `rules.py`, and `cli.py` all have `from __future__ import annotations`.
- [pyproject.toml](/Users/kohlbach/Claude/MII/genomde-dk-validator/pyproject.toml:40) probably includes `rules/*.json` and schema data, but I would still add an explicit `schemas/kdk/data-types/*.json` pattern and a wheel smoke test that imports the package and validates both fixtures from an installed wheel.
- [schemas/kdk/RareDiseases.json](/Users/kohlbach/Claude/MII/genomde-dk-validator/src/genomde_dk_validator/schemas/kdk/RareDiseases.json:2) has `$id: "hhttps://..."`. Fix the vendored typo or register both declared and expected URIs with a startup assertion.
