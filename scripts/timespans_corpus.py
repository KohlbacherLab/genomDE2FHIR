#!/usr/bin/env python3
"""Zeitspannen-Verteilungen über das Korpus (genomde2fhir/tests/corpus_manifest.json, gültige KDK-Dateien).

    uv run --with matplotlib python3 scripts/timespans_corpus.py [--out docs/timespans] [--manifest ...]

Schreibt <out>/summary.md (Tabellen je Zweig), <out>/spans.json (alle Werte) und PNGs:
  cohort_<branch>.png   Verteilung je Zeitspanne (Boxplot + Punkte)
  timeline_<branch>.png Zeitstrahl eines Einzelfalls (Median-nächster Fall nach D6)
"""
import argparse
import hashlib
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(__file__))
from timespans import anchors, spans  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ponytail: hand-paired GRZ files only; the schemas share no TAN key, so D9-D12 exist just for these
PAIRED = ("grz-paired-onco-01.json", "grz-paired-rd-01.json", "grz-paired-hereditary-01.json")


def flat(v):
    """Span value -> list of day numbers (dicts with approx and lists unpacked)."""
    if v is None:
        return []
    if isinstance(v, list):
        return [x for e in v for x in flat(e)]
    if isinstance(v, dict):
        return [v["days"]]
    return [v]


def quant(xs):
    xs = sorted(xs)
    if not xs:
        return None
    q = st.quantiles(xs, n=4) if len(xs) > 1 else [xs[0]] * 3
    return {"n": len(xs), "min": xs[0], "q1": q[0], "median": st.median(xs), "q3": q[2], "max": xs[-1]}


def run(manifest, out):
    man = json.load(open(manifest))
    per_branch = {"oncology": {}, "rare-disease": {}}
    cases = {"oncology": [], "rare-disease": []}
    grz_files = {os.path.basename(p): p for p in man["grz"]["valid"]}
    seen = set()   # the manifest lists the mv_dummy_data files up to three times (examples/, example-data/, synthData-v1/)
    for br in per_branch:
        for p in man[br]["valid"]:
            f = os.path.join(ROOT, p)
            if not os.path.exists(f):
                continue
            raw = open(f, "rb").read()
            h = hashlib.sha1(raw).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            kdk = json.loads(raw)
            grz = None
            for name in PAIRED:   # GRZ `_paired_with` is a string naming the KDK file
                if name in grz_files:
                    g = json.load(open(os.path.join(ROOT, grz_files[name])))
                    if os.path.basename(p) in str(g.get("_paired_with", "")):
                        grz = g
            a = anchors(kdk, grz)
            s = spans(kdk, a)
            cases[br].append({"file": p, "anchors": {k: (v[0].isoformat() if isinstance(v, tuple) else v)
                                                      for k, v in a.items() if not isinstance(v, list)}, "spans": s})
            for k, v in s.items():
                per_branch[br].setdefault(k, []).extend(flat(v))
    os.makedirs(out, exist_ok=True)
    json.dump(cases, open(os.path.join(out, "spans.json"), "w"), indent=0, default=str)
    lines = ["# Zeitspannen im Korpus\n", f"Manifest `{os.path.relpath(manifest, ROOT)}`; Werte in Tagen; "
             "Monatsangaben auf den 15. gesetzt. Nur gültige KDK-Dateien; GRZ-Spannen (D9–D12) nur für die "
             "handgepaarten Beispiele.\n"]
    for br, d in per_branch.items():
        lines += [f"\n## {br} ({len(cases[br])} Fälle)\n", "| Spanne | n | min | Q1 | Median | Q3 | max |", "|:--|--:|--:|--:|--:|--:|--:|"]
        for k in sorted(d, key=lambda x: (x.split('_')[0].rstrip('e'), x)):
            q = quant(d[k])
            if q:
                lines.append(f"| {k} | {q['n']} | {q['min']:.0f} | {q['q1']:.0f} | {q['median']:.0f} | {q['q3']:.0f} | {q['max']:.0f} |")
    open(os.path.join(out, "summary.md"), "w").write("\n".join(lines) + "\n")
    plot(per_branch, cases, out)
    print("\n".join(lines))


def plot(per_branch, cases, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib fehlt: keine Grafiken", file=sys.stderr)
        return
    for br, d in per_branch.items():
        keys = [k for k in d if d[k] and k.startswith("D") and len(d[k]) >= 5]
        keys.sort(key=lambda k: st.median(d[k]))
        fig, ax = plt.subplots(figsize=(9, 0.35 * len(keys) + 1.5))
        ax.boxplot([d[k] for k in keys], vert=False, showfliers=False, widths=0.6)
        for i, k in enumerate(keys, 1):
            xs = d[k]
            ax.plot(xs, [i + (hash(str(j)) % 7 - 3) * 0.04 for j in range(len(xs))], ".", ms=2, alpha=0.3, color="tab:blue")
        ax.set_yticks(range(1, len(keys) + 1))
        ax.set_yticklabels([f"{k} (n={len(d[k])})" for k in keys], fontsize=7)
        ax.axvline(0, color="grey", lw=0.5)
        ax.set_xlabel("Tage")
        ax.set_title(f"Zeitspannen {br}, {len(cases[br])} Fälle")
        fig.tight_layout()
        fig.savefig(os.path.join(out, f"cohort_{br}.png"), dpi=130)
        plt.close(fig)
        # Einzelfall: der Fall, dessen D6 dem Median am nächsten liegt
        with_d6 = [c for c in cases[br] if isinstance(c["spans"].get("D6_board1_to_board2"), int)]
        if not with_d6:
            continue
        med = st.median([c["spans"]["D6_board1_to_board2"] for c in with_d6])
        c = min(with_d6, key=lambda c: abs(c["spans"]["D6_board1_to_board2"] - med))
        timeline(c, br, os.path.join(out, f"timeline_{br}.png"), plt)


def timeline(c, br, path, plt):
    from datetime import date
    a = c["anchors"]
    ev = [("Einwilligung", a.get("T_consent")), ("Indikationsboard", a.get("T_board1")),
          ("molekulares Board", a.get("T_board2")), ("Meldung", a.get("T_submit"))]
    ev.insert(0, ("Diagnose", a.get("T_dx")) if br == "oncology" else ("Symptombeginn", a.get("T_onset")))
    if a.get("T_sample"):
        ev.insert(2, ("Probe (GRZ)", a["T_sample"]))
    ref = date.fromisoformat(a["T_board1"])
    ev = [(n, (date.fromisoformat(t) - ref).days) for n, t in ev if t]
    fu = [x for x in (c["spans"].get("D13_board_to_followup") or []) if isinstance(x, int)]
    d6 = c["spans"].get("D6_board1_to_board2") or 0
    ev += [(f"Follow-up {i + 1}", d6 + x) for i, x in enumerate(fu)]
    for i, x in enumerate(c["spans"].get("D16_board2_to_therapy_start") or []):
        if isinstance(x, int):
            ev.append((f"Therapie {i + 1}", d6 + x))
    fig, ax = plt.subplots(figsize=(10, 2.6))
    xs = [x for _, x in ev]
    ax.hlines(0, min(xs), max(xs), color="grey", lw=1)
    for i, (n, x) in enumerate(sorted(ev, key=lambda e: e[1])):
        ax.plot(x, 0, "o", color="tab:red" if "Board" in n or "board" in n else "tab:blue")
        ax.annotate(f"{n}\n{x:+d} d", (x, 0), xytext=(0, 14 if i % 2 else -26), textcoords="offset points",
                    ha="center", fontsize=7)
    ax.set_yticks([])
    ax.set_xlabel("Tage relativ zum Indikationsboard")
    ax.set_title(f"Zeitstrahl {br}: {os.path.basename(c['file'])[:40]}…", fontsize=9)
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=os.path.join(ROOT, "genomde2fhir/tests/corpus_manifest.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "docs/timespans"))
    args = ap.parse_args()
    run(args.manifest, args.out)
