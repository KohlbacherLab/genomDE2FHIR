"""Transaction Bundle assembly: urn:uuid fullUrls, idempotent PUT requests, structural checks."""
from fhir.resources.R4B import get_fhir_model_class


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
    """Intra-bundle urn:uuid references that point to no entry."""
    have = {e["fullUrl"] for e in bundle.get("entry", [])}
    out = []

    def walk(o, where):
        if isinstance(o, dict):
            r = o.get("reference")
            if isinstance(r, str) and r.startswith("urn:uuid:") and r not in have:
                out.append(f"{where}: {r}")
            for k, v in o.items():
                walk(v, where)
        elif isinstance(o, list):
            for v in o:
                walk(v, where)
    for e in bundle.get("entry", []):
        walk(e["resource"], f"{e['resource']['resourceType']}/{e['resource']['id']}")
    return out
