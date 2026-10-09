"""KDK molecular.sbsSignatures[] -> mii-pr-mtb-molekularer-biomarker, one Observation per signature name
(REPRESENTATIONS #20, DISCUSS-TD #20).

Rows: molecular.sbsSignatures[].identifier, .name[], .version.

- code   = mvgs-cs-molecular-feature#sbs-signature (extensible binding mii-vs-mtb-molekulare-biomarker has no concept)
- value  = COSMIC coding, system https://cancer.sanger.ac.uk/cosmic (NamingSystem mvgs-ns-cosmic), code normalised
           ('SBS 6' -> 'SBS6'), catalogue version (sbsSignatures[].version, e.g. 'COSMIC v3.3') in coding.version
           (not Observation.method, which is the analysis method)
Names that do not look like SBS catalogue ids stay as valueCodeableConcept.text (warned).
"""
import re

from ...systems import COSMIC, MTB
from ...terminology import local_coding
from ..common import cc
from .molecular_biomarkers import finding_identifier, observation, register, unique_key

PROFILE = MTB + "StructureDefinition/mii-pr-mtb-molekularer-biomarker"
BASE = "molecular.sbsSignatures[]."
SBS_RE = re.compile(r"^SBS\s*[-_]?\s*(\d+)\s*([a-z]?)$", re.IGNORECASE)


def normalise(name: str) -> str | None:
    m = SBS_RE.match(name.strip())
    return f"SBS{int(m.group(1))}{m.group(2).lower()}" if m else None


def build(ctx):
    items = (ctx.dk.get("molecular") or {}).get("sbsSignatures") or []
    if not items:
        return
    code = local_coding("mvgs-cs-molecular-feature", "sbs-signature")
    seen: set = set()
    for i, sig in enumerate(items):
        sid = sig.get("identifier")
        key = unique_key(seen, ctx, BASE + "identifier", sid, i)
        version = sig.get("version")
        names = [n for n in (sig.get("name") or []) if isinstance(n, str) and n.strip()]
        if not names:
            ctx.drop(BASE + "identifier", sid, "SBS signature entry without names")
            continue
        done = set()
        for j, name in enumerate(names):
            norm = normalise(name)
            if norm and norm in done:
                ctx.warn(BASE + "name[]", f"signature {name!r} listed twice in {sid!r}; emitted once")
                continue
            done.add(norm)
            o = observation(ctx, PROFILE, "sbs", key, norm or f"#{j}", code=cc(dict(code)))
            o["identifier"] = [finding_identifier(ctx, sid)]
            paths = [BASE + "identifier"]  # name[] is preserved (local Observation.code)
            if norm:
                c = {"system": COSMIC, "code": norm}
                if version:
                    c["version"] = version
                    paths.append(BASE + "version")
                o["valueCodeableConcept"] = {"coding": [c], "text": name} if norm != name else {"coding": [c]}
                ctx.rep("sbs-cosmic-coding")
            else:
                o["valueCodeableConcept"] = {"text": name + (f" ({version})" if version else "")}
                ctx.warn(BASE + "name[]", f"not an SBS catalogue id: {name!r}; kept as text")
                if version:
                    paths.append(BASE + "version")
            ctx.preserve(BASE + "name[]", "sbs-signature-local-code")
            register(ctx, ctx.add(o, *paths), sid, primary=len(done) == 1)
