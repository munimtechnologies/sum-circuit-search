# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Solve one instance: python solve_enc.py '<json>'  ->  one JSON line on stdout.
json = {"inputs": [[name, w], ...], "outputs": [...], "s": int,
        "solvers": [...], "tables": {name: [k, table], ...}}"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enccore as ec  # noqa: E402


def main():
    spec = json.loads(sys.argv[1])
    for name, (k, table) in spec.get("tables", {}).items():
        ec.register(name, k, table)
    inputs = [tuple(g) for g in spec["inputs"]]
    outputs = [tuple(g) for g in spec["outputs"]]
    s = int(spec["s"])
    t0 = time.time()
    e = ec.encode(inputs, outputs, s)
    build = time.time() - t0
    from pysat.solvers import Solver
    solver, used, errors = None, None, []
    for name in spec.get("solvers", ["cadical195", "glucose4"]):
        try:
            solver = Solver(name=name, bootstrap_with=e.clauses)
            used = name
            break
        except Exception as exc:  # solver not available in this build
            errors.append("%s: %s" % (name, exc))
            solver = None
    if solver is None:
        print(json.dumps({"s": s, "error": "no solver", "details": errors}))
        return
    t1 = time.time()
    sat = solver.solve()
    out = {"s": s, "sat": bool(sat), "solver": used, "vars": e.nvars,
           "clauses": len(e.clauses), "build_seconds": round(build, 2),
           "solve_seconds": round(time.time() - t1, 2)}
    if sat:
        circ = ec.decode(e, solver.get_model())
        ok, row = ec.check(inputs, outputs, circ)
        out["circuit"] = circ
        out["verified"] = bool(ok)
        out["bad_row"] = row
    solver.delete()
    print(json.dumps(out))


if __name__ == "__main__":
    main()
