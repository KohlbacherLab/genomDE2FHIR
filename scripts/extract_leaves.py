#!/usr/bin/env python3
"""Extract leaf paths from a genomDE Datenkranz JSON Schema (KDK roots or GRZ).

Walks the schema, resolving $ref (remote BfArM URLs -> local files, and internal
JSON-pointer refs), and emits one row per scalar/enum leaf:
  path, type, required, array, enum, format, description

ponytail: deliberately a flattener, not a full JSON-Schema validator. Handles the
constructs these two schemas actually use (properties, items, $ref, allOf,
anyOf/oneOf, enum). Add more keywords only if a schema starts using them.
"""
import json, sys, csv, os, re
from pathlib import Path

KDK_DIR = Path(__file__).resolve().parent.parent / "schemas" / "kdk"
URL_PREFIX = "https://raw.githubusercontent.com/BfArM-MVH/MVGenomseq_KDK/main/KDK/"

_cache = {}
def load_doc(path):
    path = str(path)
    if path not in _cache:
        with open(path) as f:
            _cache[path] = json.load(f)
    return _cache[path]

def resolve_ref(ref, cur_doc, cur_path):
    """Return (schema, doc, path) the ref points at."""
    ref = ref.strip()
    if ref.startswith("http"):
        rel = ref[len(URL_PREFIX):] if ref.startswith(URL_PREFIX) else os.path.basename(ref)
        p = KDK_DIR / rel
        doc = load_doc(p)
        return doc, doc, str(p)
    if ref.startswith("#"):
        node = cur_doc
        for part in ref[1:].split("/"):
            if part == "":
                continue
            part = part.replace("~1", "/").replace("~0", "~")
            node = node[part]
        return node, cur_doc, cur_path
    raise ValueError(f"unhandled $ref: {ref}")

def merge_allof(schema, doc, path, seen):
    """Flatten allOf into a single schema dict (shallow, enough here)."""
    out = {k: v for k, v in schema.items() if k != "allOf"}
    out.setdefault("properties", {})
    req = list(out.get("required", []))
    for sub in schema.get("allOf", []):
        sub, d, pth = deref(sub, doc, path, seen)
        for k, v in sub.get("properties", {}).items():
            out["properties"].setdefault(k, v)
        req += sub.get("required", [])
        if "type" not in out and "type" in sub:
            out["type"] = sub["type"]
    out["required"] = req
    return out

def deref(schema, doc, path, seen):
    """Follow a $ref one hop if present. Returns (schema, doc, path)."""
    if isinstance(schema, dict) and "$ref" in schema:
        return resolve_ref(schema["$ref"], doc, path)
    return schema, doc, path

def first_type(schema):
    t = schema.get("type")
    if isinstance(t, list):
        t = "|".join(x for x in t if x != "null") or "null"
    return t

def walk(schema, doc, path, prefix, required, rows, seen):
    schema, doc, path = deref(schema, doc, path, seen)
    if not isinstance(schema, dict):
        return

    # combinators that don't add a level: descend into the first object-y branch
    for comb in ("oneOf", "anyOf"):
        if comb in schema and "properties" not in schema:
            # treat union members as alternative shapes under same path
            for i, sub in enumerate(schema[comb]):
                walk(sub, doc, path, prefix, required, rows, seen)
            return
    if "allOf" in schema:
        schema = merge_allof(schema, doc, path, seen)

    t = first_type(schema)

    if t == "array" or "items" in schema:
        items = schema.get("items", {})
        walk(items, doc, path, prefix + "[]", required, rows, seen)
        return

    props = schema.get("properties")
    if props:
        req = set(schema.get("required", []))
        for name, sub in props.items():
            child_prefix = f"{prefix}.{name}" if prefix else name
            # cycle guard on ref targets
            ref = sub.get("$ref") if isinstance(sub, dict) else None
            key = (ref, child_prefix)
            if ref and key in seen:
                rows.append([child_prefix, "(recursive)", name in req, False, "", "", ""])
                continue
            walk(sub, doc, path,
                 child_prefix, name in req, rows,
                 seen | ({key} if ref else set()))
        return

    # leaf
    enum = schema.get("enum")
    rows.append([
        prefix,
        t or ("enum" if enum else "object?"),
        "yes" if required else "no",
        "yes" if prefix.endswith("[]") or "[]" in prefix else "no",
        ", ".join(map(str, enum)) if enum else "",
        schema.get("format", ""),
        (schema.get("description", "") or "").replace("\n", " ").strip(),
    ])

def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    doc = load_doc(src)
    rows = []
    walk(doc, doc, src, "", True, rows, set())
    rows.sort(key=lambda r: r[0])
    header = ["path", "type", "required", "array", "enum", "format", "description"]
    w = csv.writer(open(out, "w", newline="") if out else sys.stdout)
    w.writerow(header)
    w.writerows(rows)
    sys.stderr.write(f"{src}: {len(rows)} leaves\n")

if __name__ == "__main__":
    main()
