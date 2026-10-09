"""Lookups in the MV-GenomSeq ConceptMaps and CodeSystems (de.genomde.mvgs)."""
from .data_access import mvgs_resources
from .systems import MVGS_CM, MVGS_CS


def concept_map(name_or_url: str) -> dict:
    url = name_or_url if name_or_url.startswith("http") else MVGS_CM + name_or_url
    cm = mvgs_resources().get(url)
    if not cm:
        raise KeyError(f"ConceptMap not in de.genomde.mvgs: {url}")
    return cm


def translate(map_name: str, code: str, source_system: str | None = None) -> list[dict]:
    """Codings for `code` from a ConceptMap (all groups, or the group whose source matches).
    Returns [] when unmapped; equivalence 'unmatched' targets are skipped."""
    out = []
    if code is None:
        return out
    for g in concept_map(map_name).get("group", []):
        if source_system and g.get("source") and g["source"] != source_system:
            continue
        for el in g.get("element", []):
            if el.get("code") != str(code):
                continue
            for t in el.get("target", []):
                if t.get("equivalence") == "unmatched" or not t.get("code"):
                    continue
                c = {"system": g.get("target"), "code": t["code"]}
                if t.get("display"):
                    c["display"] = t["display"]
                out.append(c)
    return out


def code_system(name_or_url: str) -> dict:
    url = name_or_url if name_or_url.startswith("http") else MVGS_CS + name_or_url
    cs = mvgs_resources().get(url)
    if not cs:
        raise KeyError(f"CodeSystem not in de.genomde.mvgs: {url}")
    return cs


def local_coding(cs_name: str, code: str) -> dict | None:
    """Coding from a local MV-GenomSeq CodeSystem; None (and the caller warns) if the code is unknown."""
    cs = code_system(cs_name)

    def find(concepts):
        for c in concepts:
            if c["code"] == code:
                return c
            hit = find(c.get("concept", []))
            if hit:
                return hit
        return None
    c = find(cs.get("concept", []))
    if not c:
        return None
    out = {"system": cs["url"], "code": c["code"]}
    if c.get("display"):
        out["display"] = c["display"]
    return out
