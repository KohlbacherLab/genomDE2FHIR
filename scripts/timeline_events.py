#!/usr/bin/env python3
"""Ereignisliste je Fall für den interaktiven Zeitstrahl (docs/timespans/events.json).

    python3 scripts/timeline_events.py [--limit N]

Je Fall: id, Zweig, Anker-Datum (Indikationsboard) und Ereignisse mit Tag relativ dazu, Spur (admin/klinisch),
optionalem Ende (Intervalle) und Beschriftung. Monatsgenaue Daten tragen approx=true.
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from timespans import d  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rel(ref, s):
    x = d(s)
    return None if not x else ((x[0] - ref).days, x[1])


def events(kdk):
    md = kdk["metaData"]; case = kdk["case"]; plan = kdk.get("plan", {}); fu = kdk.get("followUp", {})
    onco = "diagnosisOd" in case
    ref = d(md.get("molecularBoardDecisionDate"))
    if not ref:
        return None
    ref = ref[0]
    ev = []

    def add(name, start, track, end=None, detail=None, kind="point"):
        r = rel(ref, start)
        if not r:
            return
        e = {"n": name, "t": r[0], "track": track, "approx": r[1], "kind": kind}
        if end:
            re_ = rel(ref, end)
            if re_:
                e["end"] = re_[0]; e["kind"] = "bar"
        if detail:
            e["d"] = detail
        ev.append(e)

    for sc in md.get("mvConsent", {}).get("scope", []):
        add(f"Einwilligung {sc.get('domain')}", sc.get("date"), "admin", detail=sc.get("type"))
    add("Indikationsboard", md.get("molecularBoardDecisionDate"), "admin", detail="metaData.molecularBoardDecisionDate")
    cp = plan.get("carePlanOd") or plan.get("carePlanRd") or {}
    add("molekulares Board", cp.get("molecularBoardDecisionDate"), "admin", detail="plan.carePlan*.molecularBoardDecisionDate")
    add(f"Meldung ({md['submission'].get('type')})", md["submission"].get("date"), "admin")
    if onco:
        dx = case["diagnosisOd"]
        add("Hauptdiagnose", dx.get("mainDiagnosis", {}).get("date"), "clin",
            detail=(dx.get("mainDiagnosis", {}).get("code") or {}).get("display") if isinstance(dx.get("mainDiagnosis", {}).get("code"), dict) else None)
        for a in dx.get("additionalDiagnoses", []):
            add("weitere Diagnose", a.get("date"), "clin")
        for p in case.get("priorProcedures", []):
            add(f"Vortherapie {p.get('type', '')}".strip(), p.get("therapyStartDate"), "clin", p.get("therapyEndDate"),
                detail=p.get("therapyResponse"))
            add("Response (Vortherapie)", p.get("therapyResponseDate"), "clin", detail=p.get("therapyResponse"))
        for p in case.get("priorDiagnostics", []):
            add(f"Vorbefund {p.get('type', '')}".strip(), p.get("date"), "clin")
        for i, f in enumerate(fu.get("followUpOds", []), 1):
            add(f"Follow-up {i}", f.get("followUpDate"), "clin", detail=f"ECOG {f.get('ecogPerformanceStatusScore')}, {f.get('vitalStatus')}")
            for t in f.get("therapies", []):
                add("Therapie", t.get("therapyStartDate"), "clin", t.get("therapyEndDate"), detail=t.get("therapyResponse"))
                add("Response", t.get("therapyResponseDate"), "clin", detail=t.get("therapyResponse"))
            for a in f.get("additionalDiagnoses", []):
                add("weitere Diagnose", a.get("date"), "clin")
            for m in f.get("preventiveMeasures", []):
                add("präventive Maßnahme", m.get("preventiveMeasureDate"), "clin")
            add("letzter Kontakt", f.get("lastContactDate"), "clin")
            add("Tod", f.get("deathDate"), "clin")
    else:
        dx = case["diagnosisRd"]
        add("Symptombeginn", dx.get("symptomOnsetDate"), "clin")
        for p in case.get("priorRds", []):
            add("ZSE-Erstkontakt", p.get("zseContactDate"), "clin")
            add(f"frühere Genetik {p.get('genomicStudyType', '')}".strip(), p.get("diagnosticDate"), "clin", detail=p.get("diagnosticResult"))
        for i, f in enumerate(fu.get("followUpRds", []), 1):
            add(f"Follow-up {i}", f.get("followUpDate"), "clin",
                detail=("Diagnose gesichert" if f.get("diagnosisEstablished") else "Diagnose offen") + f", {f.get('vitalStatus')}")
            add("Tod", f.get("deathDate"), "clin")
    return {"branch": "oncology" if onco else "rare-disease", "ref": ref.isoformat(),
            "type": md["submission"].get("type"), "events": sorted(ev, key=lambda e: e["t"])}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs/timespans/events.json"))
    args = ap.parse_args()
    man = json.load(open(os.path.join(ROOT, "genomde2fhir/tests/corpus_manifest.json")))
    out, seen = [], set()
    for br in ("oncology", "rare-disease"):
        for p in man[br]["valid"]:
            f = os.path.join(ROOT, p)
            if not os.path.exists(f):
                continue
            raw = open(f, "rb").read(); h = hashlib.sha1(raw).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            e = events(json.loads(raw))
            if e:
                e["id"] = os.path.basename(p).replace(".json", "")[:40]
                out.append(e)
    if args.limit:
        out = out[:args.limit]
    json.dump(out, open(args.out, "w"), separators=(",", ":"))
    print(len(out), "Fälle,", sum(len(x["events"]) for x in out), "Ereignisse ->", os.path.relpath(args.out, ROOT))


if __name__ == "__main__":
    main()
