# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Is size(SUM_6) >= 14?  SAT runs for THEORY-SUM6.md (PySAT + stagecore.py).

Size(SUM_6) >= size(SUM_5) + 2 = 13 by one gate-elimination step, so a
circuit of at most 13 gates for SUM_6 has exactly 13, all used. THEORY-SUM6.md
proves rules every such circuit obeys (sum6rules.py): R1 fan-out <= 2 for
every input; R2 a gate made constant by x = c is no output, its x has
fan-out 1 and it has one reader. R2 at c = 0 rests on size(SUM_5) = 11, at
c = 1 on size(F(5,1)) >= 11, where F(k,c) = bits of c + (count of k bits).

1. Table: SUM_4 at 8, F(4,1) and F(4,2) at 8 and 9, SUM_5 at 10, F(5,1) at
   10 and 11 ("at most s" semantics: UNSAT at s proves size >= s + 1).
2. Soundness check: the same rules, derived the same way from size(SUM_4) = 9
   (and F(4,1) >= 9 for c = 1), must still allow an 11-gate SUM_5 circuit,
   which exists. UNSAT here means a bug or a wrong lemma; then step 3 is
   skipped.
3. SUM_6 at exactly 13 gates with the rules. UNSAT proves size(SUM_6) >= 14;
   SAT would be a 13-gate circuit (best published: 16). A timeout is no proof.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import stagecore as sc
import sum6rules as sr

SOLVERS = ("cadical195", "cadical153", "glucose4")


def relation(kind):
    if kind.startswith("sum"):
        return sc.sum_relation(int(kind[3:]), 3)
    if kind.startswith("f"):
        return sr.offset_relation(int(kind[1]), int(kind[2]), 3)
    raise ValueError(kind)


def solve_one(kind, s, mode):
    from pysat.solvers import Solver
    n, m, rows = relation(kind)
    if mode == "atmost":
        e = sc.encode_relation(n, m, rows, s, all_used=False)
        extra = []
    else:
        e = sc.encode_relation(n, m, rows, s, all_used=True)
        consts = (0, 1) if mode == "pruned01" else (0,)
        extra = sr.rule_clauses(e, 2, consts, symmetric=True)
    clauses = e.clauses + extra
    last = None
    for name in SOLVERS:
        try:
            solver = Solver(name=name, bootstrap_with=clauses)
        except Exception as exc:     # solver not built into this PySAT
            last = exc
            continue
        with solver:
            sat = bool(solver.solve())
            out = {"kind": kind, "s": s, "mode": mode, "sat": sat, "solver": name,
                   "vars": e.nvars, "clauses": len(clauses), "rule_clauses": len(extra)}
            if sat:
                circ = sc.decode(e, solver.get_model())
                out["circuit"] = circ
                ok = sc.check_relation(n, m, rows, circ)
                if extra:
                    asg = sc.assignment_from_circuit(e, circ)
                    ok = ok and not sr.violated(extra, asg)
                out["verified"] = bool(ok)
            return out
    raise RuntimeError("no PySAT solver available: %r" % (last,))


def run_child(kind, s, mode, limit):
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", kind, str(s), mode],
                           capture_output=True, text=True, timeout=limit)
    except subprocess.TimeoutExpired:
        return {"kind": kind, "s": s, "mode": mode, "status": "timeout", "limit": limit,
                "seconds": round(time.time() - t0, 1)}
    res = {"kind": kind, "s": s, "mode": mode, "limit": limit,
           "seconds": round(time.time() - t0, 1)}
    lines = [l for l in p.stdout.splitlines() if l.startswith("{")]
    if p.returncode != 0 or not lines:
        res["status"] = "error"
        res["stderr"] = p.stderr[-2000:]
        return res
    res.update(json.loads(lines[-1]))
    if res["sat"]:
        res["status"] = "sat_verified" if res.get("verified") else "sat_BAD"
    else:
        res["status"] = "unsat"
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", nargs=3, metavar=("KIND", "S", "MODE"))
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--small-limit", type=int, default=600)
    ap.add_argument("--mid-limit", type=int, default=3600)
    ap.add_argument("--check-limit", type=int, default=1200)
    ap.add_argument("--big-limit", type=int, default=10800)
    args = ap.parse_args(argv)
    if args.one:
        print(json.dumps(solve_one(args.one[0], int(args.one[1]), args.one[2])))
        return 0
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, "results-sum6lb.json")
    res = {"runs": [], "circuits": {}}

    def save():
        with open(path, "w") as fh:
            json.dump(res, fh, indent=1)

    def go(kind, s, mode, limit):
        r = run_child(kind, s, mode, limit)
        res["runs"].append({k: v for k, v in r.items() if k != "circuit"})
        if r.get("status") == "sat_verified":
            res["circuits"]["%s@%d/%s" % (kind, s, mode)] = r["circuit"]
        print(json.dumps({k: v for k, v in r.items() if k != "circuit"}), flush=True)
        save()
        return r["status"]

    st = {}
    # 1. table of small exact sizes (at most s gates)
    for kind, s, limit in (("sum4", 8, args.small_limit),
                           ("f41", 8, args.small_limit), ("f41", 9, args.small_limit),
                           ("f42", 8, args.small_limit), ("f42", 9, args.small_limit),
                           ("sum5", 10, args.mid_limit),
                           ("f51", 10, args.mid_limit), ("f51", 11, args.small_limit)):
        st[kind, s] = go(kind, s, "atmost", limit)
    res["sum4_ge_9"] = st["sum4", 8] == "unsat"
    res["f41_ge_9"] = st["f41", 8] == "unsat"
    res["sum5_ge_11"] = st["sum5", 10] == "unsat"
    res["f51_ge_11"] = st["f51", 10] == "unsat"

    # 2. soundness check on SUM_5 at exactly 11 = size(SUM_4) + 2 gates
    c0 = go("sum5", 11, "pruned0", args.check_limit)
    c01 = go("sum5", 11, "pruned01", args.check_limit) if res["f41_ge_9"] else "not_run"
    res["check5_pruned0"] = c0
    res["check5_pruned01"] = c01
    res["check5_ok"] = c0 == "sat_verified" and c01 in ("sat_verified", "not_run")

    # 3. SUM_6 at exactly 13 gates with the rules
    mode6 = "pruned01" if res["f51_ge_11"] else "pruned0"
    res["sum6_mode"] = mode6
    res["sum6_13"] = go("sum6", 13, mode6, args.big_limit) if res["check5_ok"] else "skipped"
    if res["sum6_13"] == "unsat":
        verdict = "SUM6_GE_14" if res["sum5_ge_11"] else "SUM6_GE_14_GIVEN_PUBLISHED_SUM5"
    elif res["sum6_13"] == "sat_verified":
        verdict = "SUM6_13_GATE_CIRCUIT_FOUND"
    else:
        verdict = "UNDECIDED_" + str(res["sum6_13"]).upper()
    res["verdict"] = verdict
    save()
    print("CHECK5_OK" if res["check5_ok"] else "CHECK5_FAILED")
    print("VERDICT %s" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
