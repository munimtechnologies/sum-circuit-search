# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""python solve_stage.py '<json>' -> one JSON line per size tried, upward,
stopping at the first size with a circuit.
json = {"rel": {...relation spec, see stagecore.relation_from_spec...},
        "s_lo": int, "s_hi": int, "solvers": [...]}"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stagecore as sc  # noqa: E402


def main():
    spec = json.loads(sys.argv[1])
    n, m, rows = sc.relation_from_spec(spec["rel"])
    from pysat.solvers import Solver
    names = spec.get("solvers", ["cadical195", "glucose4"])
    for s in range(int(spec["s_lo"]), int(spec["s_hi"]) + 1):
        t0 = time.time()
        e = sc.encode_relation(n, m, rows, s)
        solver, used, errors = None, None, []
        for name in names:
            try:
                solver = Solver(name=name, bootstrap_with=e.clauses)
                used = name
                break
            except Exception as exc:  # solver not in this build
                errors.append("%s: %s" % (name, exc))
                solver = None
        if solver is None:
            print(json.dumps({"s": s, "error": "no solver", "details": errors}), flush=True)
            return
        sat = solver.solve()
        out = {"s": s, "sat": bool(sat), "solver": used, "vars": e.nvars,
               "clauses": len(e.clauses), "seconds": round(time.time() - t0, 2)}
        if sat:
            circ = sc.decode(e, solver.get_model())
            out["circuit"] = circ
            out["verified"] = bool(sc.check_relation(n, m, rows, circ))
        solver.delete()
        print(json.dumps(out), flush=True)
        if sat:
            return


if __name__ == "__main__":
    main()
