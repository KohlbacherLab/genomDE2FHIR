"""Fix round 3 regression tests (group py_onco: onco.followup), R24 residual.

Follow-up therapies sharing reference + start that an earlier follow-up split by substances: a later follow-up's
entries are matched by substance identity (ATC code, else normalised name) first, then by the remaining attributes,
never by array position, and one substance's end date / termination reason / response is never carried over to
another substance (the 'further split' repro of the round-2 verdict and the n > 1 'no single part' gap).
Small synthetic inputs built from the tracked onco_plan fixture (th-inlabel = combination L01EC02 + L01EE01)."""
import itertools
from pathlib import Path

import pytest
from conftest import load, resources

from genomde2fhir.builders.onco import followup as followup_module

PLAN = Path(__file__).parent / "fixtures" / "onco_plan" / "plan_full.json"
X, Y, Z, W = "L01EC02", "L01EE01", "L01XX86", "L01XX99"


def atc(code):
    return {"code": {"code": code, "system": "http://fhir.de/CodeSystem/bfarm/atc", "version": "2025"}}


def fu(date, *therapies):
    return {"followUpDate": date, "metachroneDiagnoses": False, "ecogPerformanceStatusScore": "1",
            "vitalStatus": "living", "therapies": list(therapies)}


def therapy(subs=(), end=None, reason=None, response=None, names=(), ref="th-inlabel", start="2025-11-11"):
    t = {"reference": ref, "therapyStartDate": start, "substances": [atc(s) for s in subs] + [{"name": n} for n in names]}
    if end:
        t["therapyEndDate"] = end
    if reason:
        t["terminationReasonOBDS"] = reason
    if response:
        t.update(therapyResponse=response, therapyResponseDate="2026-01-15")
    return t


A = dict(subs=[X], end="2026-02-01", reason="A", response="PD")     # stopped for toxicity
B = dict(subs=[Y], end="2026-03-01", reason="E", response="CR")     # regular completion


def codes(c):
    return [x["code"] for x in (c or {}).get("coding", [])]


def warned(rep, text):
    return [m for _, m in rep.warnings if text in m]


def run(convert_dk, fus, name="fix3"):
    dk = load(PLAN)
    dk["followUp"]["followUpOds"] = fus
    return convert_dk(dk, name)


def therapy_resources(bundle):
    """{fullUrl: resource} of the follow-up Procedures and everything partOf them (MedicationStatements, responses)."""
    procs = {f"urn:uuid:{p['id']}": p for p in resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")}
    out = dict(procs)
    for e in bundle["entry"]:
        if any(r.get("reference") in procs for r in e["resource"].get("partOf", [])):
            out[e["fullUrl"]] = e["resource"]
    return out


def procedures(bundle):
    """[(coded substances, status, end, outcome, MedicationStatement states, responses)] per follow-up Procedure."""
    res = therapy_resources(bundle)
    out = []
    for url, p in res.items():
        if p["resourceType"] != "Procedure":
            continue
        kids = [r for r in res.values() if any(x["reference"] == url for x in r.get("partOf", []))]
        ms = tuple(sorted((codes(m["medicationCodeableConcept"])[0], m["status"], m["effectivePeriod"].get("end"))
                          for m in kids if m["resourceType"] == "MedicationStatement"))
        out.append((tuple(c for c, _, _ in ms), p["status"], p["performedPeriod"].get("end"), codes(p.get("outcome")),
                    ms, tuple(sorted(codes(o["valueCodeableConcept"])[0]
                                     for o in kids if o["resourceType"] == "Observation"))))
    return out


def state(bundle):
    """{coded substances of the Procedure: (status, end, outcome, MedicationStatement states, responses)}; one
    Procedure per substance set."""
    out = {}
    for subs, *rest in procedures(bundle):
        assert subs not in out, f"two Procedures for {subs}"
        out[subs] = tuple(rest)
    return out


def assert_no_transfer(bundle, fus):
    """Every split part's state (end, termination reason, response) and every MedicationStatement's state come from an
    entry reporting exactly that Procedure's coded substances: nothing is carried over to another substance."""
    entries = [t for f in fus for t in f["therapies"]]
    for subs, status, end, outcome, ms, responses in procedures(bundle):
        same = [t for t in entries if tuple(sorted(s["code"]["code"] for s in t["substances"] if "code" in s)) == subs]
        assert same, f"no entry reports exactly {subs}"
        assert (end, outcome) in [(t.get("therapyEndDate"), [t["terminationReasonOBDS"]] if t.get(
            "terminationReasonOBDS") else []) for t in same], (subs, end, outcome)
        assert all(m_end == end for _, _, m_end in ms), (subs, ms)
        assert all(m_status == {"stopped": "stopped", "completed": "completed"}.get(status, "active")
                   for _, m_status, _ in ms), (subs, status, ms)
        assert set(responses) <= {t.get("therapyResponse") for t in same}, (subs, responses)


def permutations(fus):
    """Every combination of the follow-ups' therapies[] orders."""
    for orders in itertools.product(*(itertools.permutations(f["therapies"]) for f in fus)):
        yield [dict(f, therapies=list(o)) for f, o in zip(fus, orders)]


# ---- the 'further split' repro of the round-2 verdict ---------------------------------------------------------------
FURTHER_SPLIT = [fu("2026-01-10", therapy([X, Y]), therapy([Z], end="2026-01-05", reason="A")),
                 fu("2026-03-10", therapy(**A), therapy(**B))]


@pytest.mark.parametrize("reverse", [False, True])
def test_further_split_keeps_each_substance_state(convert_dk, reverse):
    fus = [FURTHER_SPLIT[0], dict(FURTHER_SPLIT[1], therapies=FURTHER_SPLIT[1]["therapies"][::-1 if reverse else 1])]
    bundle, rep = run(convert_dk, fus)
    assert state(bundle) == {
        (X, Y): ("in-progress", None, [], ((X, "active", None), (Y, "active", None)), ()),   # earlier part kept
        (Z,): ("stopped", "2026-01-05", ["A"], ((Z, "stopped", "2026-01-05"),), ()),
        (X,): ("stopped", "2026-02-01", ["A"], ((X, "stopped", "2026-02-01"),), ("PD",)),
        (Y,): ("completed", "2026-03-01", ["E"], ((Y, "completed", "2026-03-01"),), ("CR",))}
    # was: L01EE01 (or, reversed, L01EC02) shown stopped 02-01 / PD inside the {X,Y} part next to its own report
    assert len(warned(rep, "was split by an earlier follow-up; its substances match no single part")) == 2
    assert warned(rep, f"([{X}], overlapping ['{X}+{Y}'])") and warned(rep, f"([{Y}], overlapping ['{X}+{Y}'])")
    assert_no_transfer(bundle, fus)


def test_further_split_ids_independent_of_array_order(convert_dk):
    fus = FURTHER_SPLIT
    rev = [dict(f, therapies=f["therapies"][::-1]) for f in fus]
    b1, r1 = run(convert_dk, fus, "as-given")
    b2, r2 = run(convert_dk, rev, "reversed")
    assert therapy_resources(b1) == therapy_resources(b2)           # same ids, same content
    assert sorted(m for _, m in r1.warnings) == sorted(m for _, m in r2.warnings)


# ---- order independence and no transfer over every array order --------------------------------------------------
SCENARIOS = {
    "further-split": FURTHER_SPLIT,
    "merge-plus-subset": [fu("2026-01-10", therapy(**A), therapy(**B)),
                          fu("2026-03-10", therapy([X, Y], end="2026-04-01", reason="E"),
                             therapy([X], end="2026-02-02", reason="A"))],
    "superset-pair": [fu("2026-01-10", therapy(**A), therapy(**B)),
                      fu("2026-03-10", therapy([X, W], end="2026-04-01", reason="E", response="SD"),
                         therapy([Y], response="PR"))],
    "same-substances-conflict": [fu("2026-01-10", therapy(**A), therapy(**B)),
                                 fu("2026-03-10", therapy([Y], end="2026-04-01", reason="E"),
                                    therapy([Y], end="2026-04-02", reason="P"))],
    "three-way-regroup": [fu("2026-01-10", therapy([X, Y]), therapy([Z])),
                          fu("2026-03-10", therapy([X], end="2026-02-01", reason="A", response="PD"),
                             therapy([Y, Z], end="2026-03-01", reason="E", response="CR"),
                             therapy([Z], end="2026-03-05", reason="P"))],
    "split-continues-single": [fu("2026-01-10", therapy([X, Y])),
                               fu("2026-03-10", therapy([X, Y], end="2026-03-01", reason="E"),
                                  therapy([Z], end="2026-01-05", reason="A"))],
}


@pytest.mark.parametrize("name", SCENARIOS)
def test_every_array_order_gives_the_same_bundle_without_transfer(convert_dk, name):
    first = None
    for fus in permutations(SCENARIOS[name]):
        bundle, rep = run(convert_dk, fus, name)
        got = (therapy_resources(bundle), sorted(m for _, m in rep.warnings))
        assert first is None or got == first
        first = got
        assert_no_transfer(bundle, fus)


# ---- the n > 1 'no single part' gap ---------------------------------------------------------------------------------
@pytest.mark.parametrize("reverse", [False, True])
def test_merge_and_subset_in_one_follow_up(convert_dk, reverse):
    fus = SCENARIOS["merge-plus-subset"]
    if reverse:
        fus = [fus[0], dict(fus[1], therapies=fus[1]["therapies"][::-1])]
    bundle, rep = run(convert_dk, fus)
    assert state(bundle) == {
        (X,): ("stopped", "2026-02-02", ["A"], ((X, "stopped", "2026-02-02"),), ("PD",)),    # its own update
        (Y,): ("completed", "2026-03-01", ["E"], ((Y, "completed", "2026-03-01"),), ("CR",)),  # untouched
        (X, Y): ("completed", "2026-04-01", ["E"], ((X, "completed", "2026-04-01"), (Y, "completed", "2026-04-01")),
                 ())}
    # was: no warning (as given) / silently merged into the L01EE01 part (reversed)
    assert warned(rep, f"its substances match no single part ([{X}+{Y}], overlapping ['{X}', '{Y}'])")
    assert warned(rep, f"substance(s) ['{X}'] listed in entries with different substances in one follow-up")


def test_single_unmatched_entry_keeps_the_id_a_submission_without_the_split_gives(convert_dk):
    later = fu("2026-03-10", therapy([X, Y], end="2026-04-01", reason="E"))
    bundle, rep = run(convert_dk, [fu("2026-01-10", therapy(**A), therapy(**B)), later], "with-split")
    alone, _ = run(convert_dk, [later], "without-split")
    [plain] = resources(alone, "Procedure", "mii-pr-mtb-systemische-therapie")
    merged = next(p for p in resources(bundle, "Procedure") if p["id"] == plain["id"])
    assert (merged["status"], merged["performedPeriod"]["end"]) == ("completed", "2026-04-01")
    assert len(state(bundle)) == 3 and warned(rep, "its substances match no single part")


def test_single_superset_entry_after_split_is_its_own_part(convert_dk):
    fus = [fu("2026-01-10", therapy(**A), therapy(**B)), fu("2026-03-10", therapy([X, W], end="2026-04-01", reason="E"))]
    bundle, rep = run(convert_dk, fus)
    st = state(bundle)
    assert st[(X,)] == ("stopped", "2026-02-01", ["A"], ((X, "stopped", "2026-02-01"),), ("PD",))   # not overwritten
    assert st[(X, W)][:3] == ("completed", "2026-04-01", ["E"]) and len(st) == 3
    assert warned(rep, f"its substances match no single part ([{X}+{W}], overlapping ['{X}'])")


# ---- then by the remaining attributes ---------------------------------------------------------------------------------
def test_same_substances_with_other_attributes_are_ambiguous(convert_dk):
    bundle, rep = run(convert_dk, SCENARIOS["same-substances-conflict"])
    procs = [p for p in procedures(bundle) if p[0] == (Y,)]
    assert sorted(tuple(p[1:4]) for p in procs) == [("completed", "2026-03-01", ["E"]),        # earlier part keeps its state
                                            ("completed", "2026-04-01", ["E"]),
                                            ("stopped", "2026-04-02", ["P"])]
    assert warned(rep, f"reported 2 times in one follow-up with the same substances [{Y}] but another end, "
                       f"termination reason or response: each kept as a Procedure of its own; the earlier Procedure "
                       f"of these substances keeps its state")


def test_identical_entries_continue_the_part_once(convert_dk):
    fus = [fu("2026-01-10", therapy(**A), therapy(**B)),
           fu("2026-03-10", therapy([Y], end="2026-04-01", reason="E"), therapy([Y], end="2026-04-01", reason="E"))]
    bundle, rep = run(convert_dk, fus)
    assert state(bundle)[(Y,)][:3] == ("completed", "2026-04-01", ["E"]) and len(state(bundle)) == 2
    assert warned(rep, f"with the same substances [{Y}] and the same content: one Procedure")
    assert not warned(rep, "match no single part")


# ---- substance identity: normalised names, escaping, the earlier single report -----------------------------------------
def test_name_only_substances_matched_by_normalised_name(convert_dk):
    fus = [fu("2026-01-10", therapy(names=["Alpha"]), therapy(names=["Beta"])),
           fu("2026-03-10", therapy(names=["  ALPHA "], end="2026-04-01", reason="E"))]
    bundle, rep = run(convert_dk, fus)
    procs = resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")
    notes = sorted((p["status"], p["note"][0]["text"]) for p in procs)
    assert notes == [("completed", "Substanzen ohne ATC-Code: Alpha"), ("in-progress", "Substanzen ohne ATC-Code: Beta")]
    assert not warned(rep, "match no single part")


def test_plus_in_a_name_does_not_merge_with_two_names(convert_dk):
    fus = [fu("2026-01-10", therapy(names=["A+B"], end="2026-02-01", reason="A"), therapy(names=["A", "B"]))]
    bundle, _ = run(convert_dk, fus)
    procs = resources(bundle, "Procedure", "mii-pr-mtb-systemische-therapie")
    assert sorted((p["status"], p["note"][0]["text"]) for p in procs) == [
        ("in-progress", "Substanzen ohne ATC-Code: A, B"), ("stopped", "Substanzen ohne ATC-Code: A+B")]


def test_split_entry_with_the_single_reports_substances_continues_it(convert_dk):
    fus = SCENARIOS["split-continues-single"]
    single, _ = run(convert_dk, fus[:1], "single")
    bundle, rep = run(convert_dk, fus)
    assert state(bundle) == {
        (X, Y): ("completed", "2026-03-01", ["E"], ((X, "completed", "2026-03-01"), (Y, "completed", "2026-03-01")), ()),
        (Z,): ("stopped", "2026-01-05", ["A"], ((Z, "stopped", "2026-01-05"),), ())}
    # the single report's Procedure (plain therapy id) is the one continued, not left in-progress beside a new part
    [plain] = resources(single, "Procedure", "mii-pr-mtb-systemische-therapie")
    assert next(p for p in resources(bundle, "Procedure") if p["id"] == plain["id"])["status"] == "completed"
    assert not warned(rep, "the single report of an earlier follow-up stays a Procedure of its own")


def test_module_docstring_states_the_matching_rule():
    doc = " ".join(followup_module.__doc__.split())
    for phrase in ("Therapy identity", "never from array position", "matched by substance identity first",
                   "Then by the remaining attributes", "never carried over to another substance"):
        assert phrase in doc
