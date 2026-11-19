# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""SAT runs for THEORY-BLOCKS.md (PySAT; uses stagecore.py from this repo).

1. Checks: SUM_2 = 2, SUM_3 = 5 (known; if either fails the encoder is wrong).
2. size(SUM_5) = 11: an 11-gate circuit exists and no 10-gate one does. Known
   (Knuth; Kulikov, Pechenev and Slezkin); the reduced-block barrier for 5
   units rests on it, so we re-prove it.
3. SUM_6 (6 inputs, 3 outputs). Best published upper bound 16; the exact value
   is open. THEORY-BLOCKS.md shows that a profitable reduced one-column block
   on 6 units exists if and only if size(SUM_6) <= 13. Sizes tried, in order:
   16 (check of the encoder at the known bound), 15, 14 (each SAT would improve
   the published upper bound) and 13 (SAT would beat 4.5n; UNSAT closes the
   6-unit reduced case). A timeout is not a proof.

Every call uses "at most s gates" semantics (unused gates allowed), so UNSAT
at s proves size >= s + 1 by itself. SAT answers are decoded and re-checked on
every row in the child process.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import stagecore as sc

SOLVERS = ("cadical195", "cadical153", "glucose4")
KINDS = {"sum2": (2, 2), "sum3": (3, 2), "sum5": (5, 3), "sum6": (6, 3)}


def solve_one(kind, s):
    from pysat.solvers import Solver
    n, m, rows = sc.sum_relation(*KINDS[kind])
    # all_used=False: unused gates are allowed, so a smaller circuit can be
    # padded with unused gates. One call then answers "is there a circuit with
    # AT MOST s gates?", and UNSAT at s is a lower bound size >= s + 1.
    e = sc.encode_relation(n, m, rows, s, all_used=False)
    last = None
    for name in SOLVERS:
        try:
            solver = Solver(name=name, bootstrap_with=e.clauses)
        except Exception as exc:     # solver not built into this PySAT
            last = exc
            continue
        with solver:
            sat = bool(solver.solve())
            out = {"kind": kind, "s": s, "sat": sat, "solver": name,
                   "vars": e.nvars, "clauses": len(e.clauses)}
            if sat:
                circ = sc.decode(e, solver.get_model())
                out["circuit"] = circ
                out["verified"] = sc.check_relation(n, m, rows, circ)
            return out
    raise RuntimeError("no PySAT solver available: %r" % (last,))


def run_child(kind, s, limit):
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", kind, str(s)],
                           capture_output=True, text=True, timeout=limit)
    except subprocess.TimeoutExpired:
        return {"kind": kind, "s": s, "status": "timeout", "limit": limit,
                "seconds": round(time.time() - t0, 1)}
    res = {"kind": kind, "s": s, "limit": limit, "seconds": round(time.time() - t0, 1)}
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


def status_of(runs, kind, s):
    for r in runs:
        if r["kind"] == kind and r["s"] == s:
            return r["status"]
    return "not_run"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", nargs=2, metavar=("KIND", "S"))
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--small-limit", type=int, default=600)
    ap.add_argument("--sum5-limit", type=int, default=5400)
    ap.add_argument("--sum6-limits", default="16:1200,15:3000,14:3000,13:5400")
    args = ap.parse_args(argv)
    if args.one:
        print(json.dumps(solve_one(args.one[0], int(args.one[1]))))
        return 0
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, "results-sum56.json")
    res = {"runs": [], "circuits": {}}

    def go(kind, s, limit):
        r = run_child(kind, s, limit)
        res["runs"].append({k: v for k, v in r.items() if k != "circuit"})
        if r.get("status") == "sat_verified":
            res["circuits"]["%s@%d" % (kind, s)] = r["circuit"]
        print(json.dumps({k: v for k, v in r.items() if k != "circuit"}), flush=True)
        with open(path, "w") as fh:
            json.dump(res, fh, indent=1)
        return r["status"]

    for s in (1, 2):
        go("sum2", s, args.small_limit)
    for s in (4, 5):
        go("sum3", s, args.small_limit)
    runs = res["runs"]
    res["checks_ok"] = (status_of(runs, "sum2", 1) == "unsat" and status_of(runs, "sum2", 2) == "sat_verified"
                        and status_of(runs, "sum3", 4) == "unsat" and status_of(runs, "sum3", 5) == "sat_verified")
    go("sum5", 11, args.small_limit)
    go("sum5", 10, args.sum5_limit)
    res["sum5_certified_11"] = bool(res["checks_ok"] and status_of(runs, "sum5", 11) == "sat_verified"
                                    and status_of(runs, "sum5", 10) == "unsat")
    for item in args.sum6_limits.split(","):
        s, limit = (int(x) for x in item.split(":"))
        go("sum6", s, limit)
    sat6 = [r["s"] for r in runs if r["kind"] == "sum6" and r["status"] == "sat_verified"]
    res["sum6_smallest_found"] = min(sat6) if sat6 else None
    res["sum6_13"] = status_of(runs, "sum6", 13)
    with open(path, "w") as fh:
        json.dump(res, fh, indent=1)
    print("CHECKS_OK" if res["checks_ok"] else "CHECKS_FAILED")
    print("SUM5_CERTIFIED_11" if res["sum5_certified_11"] else "SUM5_NOT_CERTIFIED")
    print("SUM6_SMALLEST_FOUND %s; SUM6_AT_13 %s" % (res["sum6_smallest_found"], res["sum6_13"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
