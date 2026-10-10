"""Transaction Bundle assembly: urn:uuid fullUrls, idempotent PUT requests, structural checks."""
import re

from fhir.resources.R4B import get_fhir_model_class

LOCAL_ID = re.compile(r"#[A-Za-z0-9\-.]{0,64}")   # '#<id>' of a contained resource; '#' alone is the container
# string elements that hold prose or codes, never a uri: a '#<id>' value there is not a local reference
NOT_URI = frozenset({"display", "text", "div", "name", "title", "description", "comment", "valueString",
                     "valueMarkdown", "code", "value", "version", "unit", "id"})


def local_ref(key, value) -> str | None:
    """The contained id that the element `key` with string `value` points to ('' = the container itself), else None:
    a Reference.reference '#...', or a canonical / uri / url value '#<id>' (R4 dom-3 counts those too). Without element
    types every other string element outside NOT_URI is taken as a possible canonical / uri (deliberate
    simplification: a stray '#<id>' string elsewhere keeps or loses a contained resource like a reference would)."""
    if not isinstance(value, str) or not value.startswith("#"):
        return None
    if key == "reference" or key not in NOT_URI and LOCAL_ID.fullmatch(value):
        return value[1:]
    return None


def ref(rtype: str, rid: str, display: str | None = None) -> dict:
    r = {"reference": f"urn:uuid:{rid}"}
    if display:
        r["display"] = display
    return r


class BundleBuilder:
    def __init__(self):
        self.entries: dict[str, dict] = {}

    def put(self, resource: dict, replace: bool = False) -> dict:
        """Add a resource (must carry resourceType + id) as `PUT Type/id`; returns a reference to it."""
        rtype, rid = resource["resourceType"], resource["id"]
        full = f"urn:uuid:{rid}"
        if full in self.entries and not replace:
            raise ValueError(f"duplicate resource {rtype}/{rid}")
        self.entries[full] = {"fullUrl": full, "resource": resource,
                              "request": {"method": "PUT", "url": f"{rtype}/{rid}"}}
        return {"reference": full}

    def has(self, rid: str) -> bool:
        return f"urn:uuid:{rid}" in self.entries

    def merge(self, other: "BundleBuilder"):
        """Merge another builder; later entries win (used to put several files in one Bundle)."""
        self.entries.update(other.entries)

    def bundle(self) -> dict:
        return {"resourceType": "Bundle", "type": "transaction", "entry": list(self.entries.values())}


def prune(o):
    """Drop None, empty strings, empty lists and empty dicts recursively (FHIR forbids empty elements)."""
    if isinstance(o, dict):
        out = {k: prune(v) for k, v in o.items()}
        return {k: v for k, v in out.items() if v not in (None, "", [], {})}
    if isinstance(o, list):
        out = [prune(v) for v in o]
        return [v for v in out if v not in (None, "", [], {})]
    return o


def structural_errors(bundle: dict) -> list[str]:
    """Parse every resource with the fhir.resources R4B models (identical to R4 for the types we emit).
    Catches misspelt elements, wrong datatypes and cardinality>1 on single elements; profile
    conformance is matchbox's job."""
    errs = []
    for e in bundle.get("entry", []):
        r = e["resource"]
        try:
            get_fhir_model_class(r["resourceType"]).model_validate(r)
        except Exception as ex:  # pydantic ValidationError or KeyError
            errs.append(f"{r.get('resourceType')}/{r.get('id')}: {str(ex).splitlines()[0][:300]} :: {str(ex)[:600]}")
    return errs


def dangling_references(bundle: dict) -> list[str]:
    """Intra-bundle urn:uuid references that point to no entry, and '#id' references (Reference.reference, canonical /
    uri values; local_ref) that point to no contained resource of the same entry ('#' alone is the container itself)."""
    have = {e["fullUrl"] for e in bundle.get("entry", [])}
    out = []

    def walk(o, where, local, key=None):
        if isinstance(o, dict):
            r = o.get("reference")
            if isinstance(r, str) and r.startswith("urn:uuid:") and r not in have:
                out.append(f"{where}: {r}")
            for k, v in o.items():
                walk(v, where, local, k)
        elif isinstance(o, list):
            for v in o:
                walk(v, where, local, key)
        elif local_ref(key, o) not in (None, "", *local):
            out.append(f"{where}: {o}")
    for e in bundle.get("entry", []):
        res = e["resource"]
        local = {c.get("id") for c in res.get("contained", []) if isinstance(c, dict)}
        walk(res, f"{res['resourceType']}/{res['id']}", local)
    return out
