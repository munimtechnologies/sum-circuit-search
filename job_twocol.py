# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Search 3: can a block that reads TWO adjacent columns beat 4.5n for SUM_n?

Every known block for counting bits (full adder, Stockmeyer, MDFA, MDFA') reads
groups of one weight only; columns meet only through carries. This job lists
every block whose inputs are P/D groups at weights 0 AND 1 (both present), with
at most 6 input wires, and every output shape over P/D (any weights, at most 8
wires) that can hold every input total and has s_max >= 0, where s_max is the
largest size strictly below phi(in) - phi(out) with phi_P = 4.5, phi_D = 8.
For each block it searches sizes 0, 1, ... upward (exact; every gate used;
relational outputs, free output negation) up to s_max. A circuit of size
<= s_max is a PROFITABLE block: the potentials 4.5 / 8 that make the 4.5n
construction tight no longer hold for it. If every block is decided with none
profitable, no circuit composed of these blocks and search 1's blocks beats
4.5n - O(log n) (telescoping over the potential).

Long shots: the two tight fused chains of two MDFAs across adjacent columns
(8 input wires) are tried at one gate below the known composite (SAT only,
fixed time; a timeout is NOT a proof).

python job_twocol.py --out-dir /out [--main-minutes 290 --longshot-minutes 50]"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import enccore as ec  # noqa: E402
import known_blocks as kb  # noqa: E402

LOCK = threading.Lock()
PHI = dict(ec.PHI2_BASE)          # doubled: P = 9, D = 16
P0, D0, P1, D1, P2, D2 = ("P", 0), ("D", 0), ("P", 1), ("D", 1), ("P", 2), ("D", 2)

# (name, inputs, outputs, size of the known tight composite)
LONG_SHOTS = [
    ("mdfa_then_mdfa", (P0, D0, D0, P1, D1), (P0, P1, D2), 16),
    ("mdfa_then_pair_mdfa", (P0, D0, D0, P1, P1, P1), (P0, P1, D2), 17),
]


def log(msg):
    with LOCK:
        print(msg, flush=True)


def twocol_inputs(max_wires=6):
    """P/D multisets with groups at weight 0 and at weight 1, <= max_wires wires."""
    out = []
    for p0 in range(max_wires + 1):
        for d0 in range(max_wires // 2 + 1):
            for p1 in range(max_wires + 1):
                for d1 in range(max_wires // 2 + 1):
                    w0, w1 = p0 + 2 * d0, p1 + 2 * d1
                    if w0 >= 1 and w1 >= 1 and w0 + w1 <= max_wires:
                        out.append(tuple([P0] * p0 + [D0] * d0 + [P1] * p1 + [D1] * d1))
    return out


def twocol_shapes(max_wires=6, max_out_wires=8):
    shapes = []
    for ins in twocol_inputs(max_wires):
        for outs in ec.output_shapes(ins, ("P", "D"), PHI, max_out_wires):
            shapes.append((ins, outs))
    return shapes


def shift_circuit(circ, at, by):
    """Insert `by` extra input wires at node index `at` (they are appended
    after the original inputs); gate and output references >= at move up."""
    def mv(x):
        return x + by if x >= at else x
    return {"n": circ["n"] + by,
            "gates": [[mv(j), mv(k), list(f)] for j, k, f in circ["gates"]],
            "outs": [[mv(s) if s >= 0 else s, p] for s, p in circ["outs"]]}


def mdfa_pass_circuit():
    """MDFA on wires 0..4 plus a plain weight-1 bit on wire 5, passed through:
    P@0 + D@0 + D@0 + P@1 -> P@0 + P@1 + D@1 with 8 gates."""
    c = shift_circuit(kb.MDFA["circuit"], 5, 1)
    p_out, d_a, d_b = c["outs"]
    c["outs"] = [p_out, [5, 0], d_a, d_b]
    return c


def new_state(ins, outs):
    return {"key": ec.shape_key(ins, outs), "ins": tuple(ins), "outs": tuple(outs),
            "t": -1, "m": None, "stuck": "", "error": "", "seconds": 0.0,
            "calls": 0, "circuit": None}


class Runner:
    def __init__(self, step_timeout, shape_budget, solvers, out_dir):
        self.step_timeout = step_timeout
        self.shape_budget = shape_budget
        self.solvers = solvers
        self.out_dir = out_dir

    def run_step(self, inputs, outputs, s, timeout):
        spec = json.dumps({"inputs": [list(g) for g in inputs],
                           "outputs": [list(g) for g in outputs],
                           "s": s, "solvers": self.solvers, "tables": {}})
        t0 = time.time()
        try:
            proc = subprocess.run([sys.executable, os.path.join(HERE, "solve_enc.py"), spec],
                                  capture_output=True, text=True, timeout=max(1, timeout))
        except subprocess.TimeoutExpired:
            return {"s": s, "timeout": True, "seconds": round(time.time() - t0, 1)}
        lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
        if proc.returncode != 0 or not lines:
            return {"s": s, "error": (proc.stderr or "")[-800:],
                    "seconds": round(time.time() - t0, 1)}
        res = json.loads(lines[-1])
        res["seconds"] = round(time.time() - t0, 1)
        if res.get("sat"):
            ok, _row = ec.check(inputs, outputs, res["circuit"])   # independent re-check
            res["verified_parent"] = bool(ok)
        return res

    def extend(self, st, s_hi, deadline):
        """Sizes st['t']+1 .. s_hi upward; the first SAT size is the exact minimum."""
        s = st["t"] + 1
        while s <= s_hi and st["m"] is None and not st["stuck"]:
            left_shape = self.shape_budget - st["seconds"]
            left_time = deadline - time.time()
            if left_shape < 5:
                st["stuck"] = "shape_budget"
                break
            if left_time < 5:
                break
            res = self.run_step(st["ins"], st["outs"], s,
                                min(self.step_timeout, left_shape, left_time))
            st["seconds"] = round(st["seconds"] + float(res.get("seconds", 0.0)), 1)
            st["calls"] += 1
            if res.get("timeout"):
                st["stuck"] = "timeout"
                break
            if "error" in res:
                st["stuck"] = "error"
                st["error"] = str(res.get("error"))[-300:]
                break
            if res.get("sat"):
                if res.get("verified") and res.get("verified_parent"):
                    st["m"] = s
                    st["circuit"] = res["circuit"]
                else:
                    st["stuck"] = "sat_unverified"
                    st["circuit"] = res.get("circuit")
                break
            st["t"] = s
            s += 1
        line = {"key": st["key"], "searched_to": s_hi, "no_circuit_up_to": st["t"],
                "min_size": st["m"], "stuck": st["stuck"], "seconds": st["seconds"]}
        with LOCK:
            with open(os.path.join(self.out_dir, "progress.jsonl"), "a") as fh:
                fh.write(json.dumps(line) + "\n")
        log("[shape] %s to=%d t=%d m=%s %s" % (st["key"], s_hi, st["t"], st["m"], st["stuck"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--max-wires", type=int, default=6)
    ap.add_argument("--max-out-wires", type=int, default=8)
    ap.add_argument("--main-minutes", type=float, default=290.0)
    ap.add_argument("--longshot-minutes", type=float, default=50.0)
    ap.add_argument("--step-timeout", type=float, default=600.0)
    ap.add_argument("--shape-budget", type=float, default=1500.0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--solvers", default="cadical195,glucose4")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    t_start = time.time()
    main_deadline = t_start + 60 * args.main_minutes
    runner = Runner(args.step_timeout, args.shape_budget, args.solvers.split(","), args.out_dir)

    # C1: known blocks found at their sizes; full-adder shape has nothing <= 4;
    # the MDFA + pass-through two-column block is found at size 8.
    sanity = []
    checks = [(nm, kb.ALL[nm]["inputs"], kb.ALL[nm]["outputs"], len(kb.ALL[nm]["circuit"]["gates"]))
              for nm in ("full_adder", "stockmeyer", "mdfa_prime", "mdfa", "pair_xor")]
    checks.append(("mdfa_pass", [P0, D0, D0, P1], [P0, P1, D1], 8))
    for name, ins, outs, size in checks:
        res = runner.run_step([tuple(g) for g in ins], [tuple(g) for g in outs], size,
                              args.step_timeout)
        ok = bool(res.get("sat") and res.get("verified") and res.get("verified_parent"))
        sanity.append({"name": name, "s": size, "found": ok, "seconds": res.get("seconds"),
                       "timeout": bool(res.get("timeout")),
                       "error": str(res.get("error", ""))[-300:]})
        log("[sanity] %s size %d found=%s (%ss)" % (name, size, ok, res.get("seconds")))
    fa = new_state(tuple(kb.FULL_ADDER["inputs"]), tuple(kb.FULL_ADDER["outputs"]))
    runner.extend(fa, 4, main_deadline)
    fa_lower_ok = fa["m"] is None and fa["t"] == 4

    # main search, cheapest first
    inputs = twocol_inputs(args.max_wires)
    recs = [(ec.s_max(i, o, PHI), new_state(i, o))
            for i, o in twocol_shapes(args.max_wires, args.max_out_wires)]
    recs.sort(key=lambda x: (x[0], ec.wire_count(x[1]["ins"]), x[1]["key"]))
    log("[shapes] inputs=%d shapes=%d" % (len(inputs), len(recs)))

    def work(item):
        sm, st = item
        if main_deadline - time.time() < 10:
            return
        runner.extend(st, sm, main_deadline)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, recs))

    def decided(sm, st):
        return st["m"] is not None or st["t"] >= sm

    profits = []
    for sm, st in recs:
        if st["m"] is not None and st["m"] <= sm:
            drop = (ec.phi2(st["ins"], PHI) - ec.phi2(st["outs"], PHI)) / 2.0
            profits.append({"key": st["key"], "min_size": st["m"], "s_max": sm,
                            "phi_drop": drop, "circuit": st["circuit"]})
            log("[PROFIT] %s size %d < %.1f" % (st["key"], st["m"], drop))

    # long shots (SAT only, fixed time each, run side by side)
    def shoot(item):
        name, ins, outs, tight = item
        res = runner.run_step(ins, outs, tight - 1, 60 * args.longshot_minutes)
        out = {"name": name, "key": ec.shape_key(ins, outs), "tight": tight,
               "tried_size": tight - 1, "sat": bool(res.get("sat")),
               "verified": bool(res.get("verified") and res.get("verified_parent")),
               "timeout": bool(res.get("timeout")), "seconds": res.get("seconds"),
               "error": str(res.get("error", ""))[-300:],
               "vars": res.get("vars"), "clauses": res.get("clauses"),
               "circuit": res.get("circuit")}
        log("[longshot] %s size %d sat=%s timeout=%s (%ss)" % (
            name, tight - 1, out["sat"], out["timeout"], out["seconds"]))
        return out

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        long_shots = list(ex.map(shoot, LONG_SHOTS))

    small = [(sm, st) for sm, st in recs if sm <= 6]
    by_s = {}
    for sm, st in recs:
        d = by_s.setdefault(str(sm), [0, 0])
        d[0] += 1
        d[1] += 1 if decided(sm, st) else 0
    stats = {
        "sanity_all_found": all(x["found"] for x in sanity),
        "full_adder_no_circuit_le_4": fa_lower_ok,
        "n_inputs": len(inputs),
        "n_shapes": len(recs),
        "n_decided": sum(1 for sm, st in recs if decided(sm, st)),
        "n_s_max_le_6": len(small),
        "n_s_max_le_6_decided": sum(1 for sm, st in small if decided(sm, st)),
        "by_s_max": by_s,
        "n_stuck": sum(1 for _sm, st in recs if st["stuck"]),
        "n_profitable": len(profits),
        "profits": [{k: p[k] for k in ("key", "min_size", "s_max", "phi_drop")} for p in profits],
        "long_shots": [{k: x[k] for k in ("name", "key", "tried_size", "sat", "verified", "timeout",
                                          "seconds")} for x in long_shots],
        "minutes": round((time.time() - t_start) / 60.0, 1),
    }
    shapes_out = [{"key": st["key"], "w": ec.wire_count(st["ins"]), "s_max": sm,
                   "min": st["m"], "none_le": st["t"], "dec": decided(sm, st),
                   "stuck": st["stuck"], "sec": st["seconds"]}
                  for sm, st in recs]
    out = {"version": "sum-circuit-search search 3 (two-column blocks) v1",
           "params": vars(args), "sanity": sanity,
           "full_adder_check": {k: fa[k] for k in ("t", "m", "stuck")},
           "stats_for_verdicts": stats, "profits": profits, "long_shots": long_shots,
           "shapes": shapes_out}
    with open(os.path.join(args.out_dir, "results.json"), "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    log("[stats] " + json.dumps({k: v for k, v in stats.items() if k != "profits"}))
    log("[profits] " + json.dumps(stats["profits"]))


if __name__ == "__main__":
    main()
