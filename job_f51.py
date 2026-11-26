# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Does F(5,1) need 12 gates?  If it does, counting 6 bits needs 14.

See THEORY-SUM6-ADDENDUM.md. F(k, c) is the 3-bit binary value of
c + (number of ones among k bits); F(k, 0) = SUM_k.

Lemma 0' (one gate-elimination step, with the constant 1 instead of 0):
size(SUM_6) >= size(F(5,1)) + 2. So "no circuit of at most 11 gates for
F(5,1)" proves size(SUM_6) >= 14 (best published lower bound: 13 by the same
step with the constant 0; best published upper bound: 16).

Steps (PySAT + stagecore.py + sum6rules.py, both downloaded from the repo):
1. F(4,1) and F(4,2) at most 8 gates. By duality they have the same size.
   Both UNSAT licenses the rules R1, R2 (c = 0, 1) and the symmetry rule for
   an 11-gate F(5,1) circuit, and gives size(F(5,1)) >= 11 by Lemma 0'.
2. Soundness check: SUM_5 at exactly 11 gates with the same rules (licensed by
   size(SUM_4) = 9 and size(F(4,1)) >= 9) must be SAT: 11-gate SUM_5 circuits
   exist.
3. F(5,1) at exactly 11 gates with the rules (only if 1 and 2 passed).
4. F(5,1) at most 11 gates with no rules at all (skipped if 3 found a circuit).
"""
import argparse
import json
import os
import subprocess
import sys
import time

SOLVERS = ("cadical195", "cadical153", "glucose4")

XOR = [0, 1, 1, 0]
AND = [0, 0, 0, 1]
OR = [0, 1, 1, 1]

# A 9-gate circuit for F(4,1) = 1 + x0 + x1 + x2 + x3 (inputs are nodes 0-3,
# gate i is node 4 + i; a gate [j, k, f] computes f[2 * v(j) + v(k)]; an output
# [node, neg] is v(node) XOR neg).  Full adder (1, x0, x1) costs 2 gates, a full
# adder on the weight-1 bits 5, a half adder on the weight-2 bits 2.
F41_NINE = {"n": 4, "gates": [
    [0, 1, XOR],    # 4: x0 ^ x1; the weight-1 bit of 1 + x0 + x1 is NOT this
    [0, 1, OR],     # 5: x0 | x1, its weight-2 bit
    [2, 4, XOR],    # 6
    [3, 6, XOR],    # 7: parity of x0..x3
    [3, 4, XOR],    # 8
    [6, 8, OR],     # 9
    [4, 9, XOR],    # 10: carry of the full adder on the weight-1 bits
    [5, 10, XOR],   # 11: bit 1
    [5, 10, AND],   # 12: bit 2
], "outs": [[7, 1], [11, 0], [12, 0]]}


def evaluate(circ, bits):
    val = list(bits)
    for a, b, f in circ["gates"]:
        val.append(f[2 * val[a] + val[b]])
    return [val[node] ^ neg for node, neg in circ["outs"]]


def offset_value(k, c, r):
    """c + (number of ones in the k-bit row r)."""
    return bin(r & ((1 << k) - 1)).count("1") + c


def computes_offset(circ, k, c):
    for r in range(1 << k):
        bits = [(r >> i) & 1 for i in range(k)]
        out = evaluate(circ, bits)
        if sum(b << i for i, b in enumerate(out)) != offset_value(k, c, r):
            return False
    return True


def dual_offset(k, c, m=3):
    """F(k, c)(NOT x) = NOT F(k, c')(x) on m output bits, for this c'."""
    return (1 << m) - 1 - k - c


def verdict(st):
    plain, pruned = st.get("f51_plain"), st.get("f51_pruned")
    if "sat_BAD" in (plain, pruned, st.get("check5")):
        return "BUG_UNVERIFIED_CIRCUIT"
    if pruned == "sat_verified" and plain == "unsat":
        return "SOLVER_CONFLICT"
    if plain == "sat_verified" and pruned == "unsat":
        return "RULES_CONFLICT"
    if plain == "sat_verified" or pruned == "sat_verified":
        return "F51_LE_11"
    if plain == "unsat":
        return "F51_GE_12_SO_SUM6_GE_14"
    if pruned == "unsat" and st.get("licence") and st.get("check5") == "sat_verified":
        return "F51_GE_12_SO_SUM6_GE_14_WITH_RULES"
    return "UNDECIDED"


def relation(kind):
    import stagecore as sc
    import sum6rules as sr
    if kind.startswith("sum"):
        return sc.sum_relation(int(kind[3:]), 3)
    if kind.startswith("f"):
        return sr.offset_relation(int(kind[1]), int(kind[2]), 3)
    raise ValueError(kind)


def solve_one(kind, s, mode):
    import stagecore as sc
    import sum6rules as sr
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
    ap.add_argument("--small-limit", type=int, default=900)
    ap.add_argument("--check-limit", type=int, default=1200)
    ap.add_argument("--pruned-limit", type=int, default=10800)
    ap.add_argument("--plain-limit", type=int, default=8400)
    args = ap.parse_args(argv)
    if args.one:
        print(json.dumps(solve_one(args.one[0], int(args.one[1]), args.one[2])))
        return 0
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, "results-f51.json")
    res = {"f41_nine_gate_circuit_ok": computes_offset(F41_NINE, 4, 1),
           "runs": [], "circuits": {}}
    try:
        import stagecore as sc
        n, m, rows = relation("f41")
        res["f41_nine_gate_circuit_stagecore_ok"] = bool(sc.check_relation(n, m, rows, F41_NINE))
    except Exception as exc:   # report, never hide
        res["f41_nine_gate_circuit_stagecore_ok"] = "error: %r" % (exc,)

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
    st["f41_8"] = go("f41", 8, "atmost", args.small_limit)
    st["f42_8"] = go("f42", 8, "atmost", args.small_limit)
    st["licence"] = st["f41_8"] == "unsat" and st["f42_8"] == "unsat"
    st["check5"] = (go("sum5", 11, "pruned01", args.check_limit)
                    if st["licence"] else "not_run")
    st["f51_pruned"] = (go("f51", 11, "pruned01", args.pruned_limit)
                        if st["licence"] and st["check5"] == "sat_verified" else "not_run")
    st["f51_plain"] = (go("f51", 11, "atmost", args.plain_limit)
                       if st["f51_pruned"] != "sat_verified" else "not_run")
    res.update(st)
    res["duality_f41_f42_agree"] = st["f41_8"] == st["f42_8"]
    res["verdict"] = verdict(st)
    save()
    print("VERDICT %s" % res["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
