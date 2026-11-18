# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""SAT certificates for THEORY-ROUNDTRIP.md (PySAT; uses stagecore.py).

1. Checks: size(SUM_2) = 2 and size(SUM_3) = 5 (known; if either fails the
   encoder is wrong and the run is void).
2. The one outside fact the round-trip barrier needs: size(SUM_4) = 9, i.e.
   a 9-gate circuit exists and no circuit with 0..8 gates does.
3. Long shot: F2, the 2-layer s* block (plain bits u, v, x0, y0, x1, y1 ->
   u + v + x0 + y0 + 2(x1 + y1) in binary, 4 outputs). It has a 16-gate
   circuit (A1 -> J1 -> U0 layers). Sizes 0, 1, ... are tried in order until
   one is not decided in time. If F2 has no circuit below 16, then any two
   consecutive layers of a layered s* circuit cost >= 16 - pack - dec,
   whatever code sits between them.

Every size is solved in a child process with a time limit (a timeout is
not a proof). SAT answers are decoded and re-checked on every row.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import stagecore as sc

SOLVERS = ("cadical195", "cadical153", "glucose4")


def relation(kind):
    if kind == "sum2":
        return sc.sum_relation(2, 2)
    if kind == "sum3":
        return sc.sum_relation(3, 2)
    if kind == "sum4":
        return sc.sum_relation(4, 3)
    if kind == "f2":
        a1 = (2, (0, 1, 1, 2))
        binary = (2, (0, 1, 2, sc.UNUSED))
        return sc.stage_relation(a1, binary, layers=2)
    raise ValueError(kind)


def solve_one(kind, s):
    from pysat.solvers import Solver
    n, m, rows = relation(kind)
    e = sc.encode_relation(n, m, rows, s)
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
        return {"kind": kind, "s": s, "status": "timeout", "seconds": round(time.time() - t0, 1)}
    res = {"kind": kind, "s": s, "seconds": round(time.time() - t0, 1)}
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


def ladder(kind, sizes, limit, log, stop_on_timeout):
    out = []
    for s in sizes:
        r = run_child(kind, s, limit)
        out.append(r)
        log(r)
        if stop_on_timeout and r["status"] in ("timeout", "error"):
            break
    return out


def no_circuit_up_to(results):
    """Largest S such that sizes 0..S are all UNSAT (-1 if size 0 is not)."""
    status = {r["s"]: r["status"] for r in results}
    S = -1
    while status.get(S + 1) == "unsat":
        S += 1
    return S


def smallest_sat(results):
    sats = [r["s"] for r in results if r["status"] == "sat_verified"]
    return min(sats) if sats else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", nargs=2, metavar=("KIND", "S"))
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--sum4-limit", type=int, default=7200)
    ap.add_argument("--small-limit", type=int, default=600)
    ap.add_argument("--f2-limit", type=int, default=1200)
    args = ap.parse_args(argv)
    if args.one:
        print(json.dumps(solve_one(args.one[0], int(args.one[1]))))
        return 0
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, "results-sum4.json")
    res = {"runs": []}

    def log(r):
        res["runs"].append({k: v for k, v in r.items() if k != "circuit"})
        if r.get("status") == "sat_verified":
            res.setdefault("circuits", {})["%s@%d" % (r["kind"], r["s"])] = r["circuit"]
        print(json.dumps({k: v for k, v in r.items() if k != "circuit"}), flush=True)
        with open(path, "w") as fh:
            json.dump(res, fh, indent=1)

    r2 = ladder("sum2", range(0, 3), args.small_limit, log, False)
    r3 = ladder("sum3", range(0, 6), args.small_limit, log, False)
    checks_ok = (no_circuit_up_to(r2) == 1 and smallest_sat(r2) == 2 and
                 no_circuit_up_to(r3) == 4 and smallest_sat(r3) == 5)
    res["checks_ok"] = checks_ok
    r4 = ladder("sum4", [9], args.small_limit, log, False)
    r4 += ladder("sum4", range(0, 8), args.small_limit, log, False)
    r4 += ladder("sum4", [8], args.sum4_limit, log, False)
    res["sum4_no_circuit_up_to"] = no_circuit_up_to(r4)
    res["sum4_has_9"] = smallest_sat(r4) == 9
    res["sum4_certified_9"] = bool(checks_ok and res["sum4_has_9"] and res["sum4_no_circuit_up_to"] == 8)
    rf = ladder("f2", [16], args.f2_limit, log, False)
    rf += ladder("f2", range(0, 16), args.f2_limit, log, True)
    res["f2_has_16"] = any(r["status"] == "sat_verified" and r["s"] == 16 for r in rf)
    res["f2_no_circuit_up_to"] = no_circuit_up_to(rf)
    res["f2_smallest_found"] = smallest_sat(rf)
    with open(path, "w") as fh:
        json.dump(res, fh, indent=1)
    print("CHECKS_OK" if checks_ok else "CHECKS_FAILED")
    print("SUM4_CERTIFIED_9" if res["sum4_certified_9"] else "SUM4_NOT_CERTIFIED")
    print("F2_NO_CIRCUIT_UP_TO %d (16-gate circuit verified: %s)" % (
        res["f2_no_circuit_up_to"], res["f2_has_16"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
