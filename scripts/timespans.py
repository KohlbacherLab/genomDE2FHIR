#!/usr/bin/env python3
"""Zeitspannen aus einer Datenkranz-Meldung (KDK Onkologie oder Seltene Erkrankungen, optional gepaartes GRZ).

    python3 scripts/timespans.py KDK.json [--grz GRZ.json] [--json]

Gibt je Fall die Anker (T_*) und die Zeitspannen (D*) in Tagen aus; Monatsangaben (YYYY-MM) werden auf
den 15. gesetzt und als ungenau markiert. Fehlende Felder ergeben None, keine Exception.
"""
import argparse
import json
import sys
from datetime import date

SENTINEL = "1800-01"          # DNPM: symptomOnsetDate unbekannt


def d(s):
    """ISO-Datum oder YYYY-MM -> (date, monatsgenau?) oder None."""
    if not s or s == SENTINEL:
        return None
    if len(s) == 7:
        y, m = s.split("-")
        return date(int(y), int(m), 15), True
    return date.fromisoformat(s[:10]), False


def days(a, b):
    """b - a in Tagen; None, wenn ein Anker fehlt. Monatsgenaue Anker geben die Differenz als ±15 d markiert zurück."""
    if not a or not b:
        return None
    n = (b[0] - a[0]).days
    return {"days": n, "approx": a[1] or b[1]} if (a[1] or b[1]) else n


def first(lst, key):
    vals = [d(x.get(key)) for x in (lst or []) if x.get(key)]
    vals = [v for v in vals if v]
    return min(vals) if vals else None


def anchors(kdk, grz=None):
    md = kdk.get("metaData", {})
    case = kdk.get("case", {})
    plan = kdk.get("plan", {})
    onco = "diagnosisOd" in case
    a = {
        "branch": "oncology" if onco else "rare-disease",
        "T_submit": d(md.get("submission", {}).get("date")),
        "submission_type": md.get("submission", {}).get("type"),
        "T_birth": d(md.get("birthDate")),
        "T_consent": first(md.get("mvConsent", {}).get("scope"), "date"),          # metaData.mvConsent.scope[].date
        "T_board1": d(md.get("molecularBoardDecisionDate")),                      # metaData.molecularBoardDecisionDate
        "T_board2": d((plan.get("carePlanOd") or plan.get("carePlanRd") or {}).get("molecularBoardDecisionDate")),
    }
    if onco:
        a["T_dx"] = d(case["diagnosisOd"].get("mainDiagnosis", {}).get("date"))    # case.diagnosisOd.mainDiagnosis.date
        a["prior_therapy_starts"] = [d(p.get("therapyStartDate")) for p in case.get("priorProcedures", [])]
        a["prior_test_dates"] = [d(p.get("date")) for p in case.get("priorDiagnostics", [])]
    else:
        a["T_onset"] = d(case["diagnosisRd"].get("symptomOnsetDate"))             # case.diagnosisRd.symptomOnsetDate
        a["T_zse"] = first(case.get("priorRds"), "zseContactDate")                 # case.priorRds[].zseContactDate
        a["T_prior_test"] = first(case.get("priorRds"), "diagnosticDate")          # case.priorRds[].diagnosticDate
    if grz:
        a["T_grz_submit"] = d(grz.get("submission", {}).get("submissionDate"))    # GRZ submission.submissionDate
        idx = [x for x in grz.get("donors", []) if x.get("relation") == "index"] or grz.get("donors", [])
        a["T_sample"] = first([ld for dn in idx for ld in dn.get("labData", [])], "sampleDate")  # donors[].labData[].sampleDate
    return a


def spans(kdk, a):
    s = {
        "D1_consent_to_board1": days(a["T_consent"], a["T_board1"]),
        "D2_board1_to_submit": days(a["T_board1"], a["T_submit"]),
        "D3_consent_to_submit": days(a["T_consent"], a["T_submit"]),
        "A1_age_at_board1_years": None,
        "D6_board1_to_board2": days(a["T_board1"], a["T_board2"]),
        "D7_board2_to_submit": days(a["T_board2"], a["T_submit"]),
    }
    if a["T_birth"] and a["T_board1"]:
        s["A1_age_at_board1_years"] = round((a["T_board1"][0] - a["T_birth"][0]).days / 365.25, 1)
    if a.get("T_sample"):
        s["D9_board1_to_sample"] = days(a["T_board1"], a["T_sample"])
        s["D10_sample_to_board2"] = days(a["T_sample"], a["T_board2"])
        s["D11_sample_to_grz_submit"] = days(a["T_sample"], a["T_grz_submit"])
        s["D12_grz_minus_kdk_submit"] = days(a["T_submit"], a["T_grz_submit"])
    ref = a["T_board2"] or a["T_board1"]
    if a["branch"] == "oncology":
        s["D4_dx_to_board1"] = days(a["T_dx"], a["T_board1"])
        s["D8_dx_to_board2"] = days(a["T_dx"], a["T_board2"])
        s["D24_prior_therapy_to_dx"] = [days(t, a["T_dx"]) for t in a["prior_therapy_starts"]]
        s["D26_prior_test_to_board1"] = [days(t, a["T_board1"]) for t in a["prior_test_dates"]]
        fus = kdk.get("followUp", {}).get("followUpOds", [])
        key = "followUpOds"
    else:
        s["D5_onset_to_board1"] = days(a["T_onset"], a["T_board1"])
        s["D27_zse_to_board1"] = days(a["T_zse"], a["T_board1"])
        s["D28_onset_to_zse"] = days(a["T_onset"], a["T_zse"])
        s["D29_prior_test_to_board1"] = days(a["T_prior_test"], a["T_board1"])
        fus = kdk.get("followUp", {}).get("followUpRds", [])
        key = "followUpRds"
    # Follow-ups (followUp.<key>[].followUpDate), zeitlich sortiert
    fus = sorted(fus, key=lambda f: f.get("followUpDate", ""))
    fu_dates = [d(f.get("followUpDate")) for f in fus]
    s["D13_board_to_followup"] = [days(ref, t) for t in fu_dates]
    s["D14_followup_interval"] = [days(fu_dates[i - 1], fu_dates[i]) for i in range(1, len(fu_dates))]
    s["D15_observation_span"] = days(a["T_board1"], max(fu_dates)) if any(fu_dates) else None
    if a["branch"] == "oncology":
        ther = [(t, f) for f in fus for t in f.get("therapies", [])]
        s["D16_board2_to_therapy_start"] = [days(ref, d(t.get("therapyStartDate"))) for t, _ in ther]
        s["D17_therapy_duration"] = [days(d(t.get("therapyStartDate")), d(t.get("therapyEndDate"))) for t, _ in ther]
        s["D18_start_to_response"] = [days(d(t.get("therapyStartDate")), d(t.get("therapyResponseDate"))) for t, _ in ther]
        s["D19_board2_to_additional_dx"] = [days(ref, d(x.get("date"))) for f in fus for x in f.get("additionalDiagnoses", [])]
        s["D20_board1_to_death"] = days(a["T_board1"], first(fus, "deathDate"))
        s["D21_board1_to_last_contact"] = days(a["T_board1"], max((d(f["lastContactDate"]) for f in fus if f.get("lastContactDate")), default=None))
    else:
        est = [t for f, t in zip(fus, fu_dates) if f.get("diagnosisEstablished") is True]
        s["D13e_board_to_diagnosis_established"] = days(ref, est[0]) if est else None
        s["D20_board1_to_death"] = days(a["T_board1"], first(fus, "deathDate"))
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kdk")
    ap.add_argument("--grz")
    ap.add_argument("--json", action="store_true", help="JSON statt Text")
    args = ap.parse_args()
    kdk = json.load(open(args.kdk))
    grz = json.load(open(args.grz)) if args.grz else None
    a = anchors(kdk, grz)
    s = spans(kdk, a)
    if args.json:
        out = {"anchors": {k: (v[0].isoformat() if isinstance(v, tuple) else v) for k, v in a.items()
                           if not isinstance(v, list)}, "spans": s}
        json.dump(out, sys.stdout, indent=1, default=str)
        return
    print(f"{a['branch']}  submission {a['submission_type']}  {a['T_submit'][0] if a['T_submit'] else '-'}")
    for k, v in a.items():
        if isinstance(v, tuple):
            print(f"  {k:14s} {v[0]}{' (±15 d)' if v[1] else ''}")
    for k, v in s.items():
        if v not in (None, []):
            print(f"  {k:36s} {v}")


if __name__ == "__main__":
    main()
