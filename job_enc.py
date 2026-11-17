# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Search 2: can a new XOR-linear 3-bit group encoding beat 4.5n for SUM_n?

For each of the five indecomposable linear 3-bit encodings E:
 1. creation: exact minimum size of P+P+P -> E and P+D -> E; phi_E is set to
    the largest phi(in) - size (doubled units). This is the smallest phi_E
    that every creation block allows.
 2. passes: list every producer (P/D in -> one E + P/D out) and consumer
    (c = 1, 2 copies of E + P/D in -> at most c copies of E + P/D out) with
    <= 6 input wires whose s_max >= 0 at the current phi_E, and search sizes
    upward (exact minimum, every gate used) up to s_max.
    - a producer below s_max raises phi_E (it makes E worth more); repeat.
    - a consumer below s_max is a profitable block: chained after the
      producer that sets phi_E (tight, exact) it gives a P/D block below
      phi(in) - phi(out), so the best constant drops below 4.5.
    - if every listed shape is decided with no violation, phi_P = 4.5,
      phi_D = 8, phi_E satisfy every constraint of this family, so no
      circuit built from these blocks beats 4.5n - O(log n).
 3. headline: exact minimum sizes of the MDFA analogues E+E, E+P+D and
    E+P+P+P -> P@0 + E@1 (a few sizes past s_max) with the time left.

python job_enc.py --out-dir /out [--minutes 330]"""
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
BASE = dict(ec.PHI2_BASE)


def log(msg):
    with LOCK:
        print(msg, flush=True)


def new_state(e, kind, ins, outs):
    return {"key": ec.shape_key(ins, outs), "e": e, "kind": kind,
            "ins": tuple(ins), "outs": tuple(outs), "t": -1, "m": None,
            "stuck": "", "error": "", "seconds": 0.0, "calls": 0, "circuit": None}


def e_balance(st):
    """(# e groups in) - (# e groups out)."""
    e = st["e"]
    return (sum(1 for g in st["ins"] if g[0] == e) -
            sum(1 for g in st["outs"] if g[0] == e))


class Runner:
    def __init__(self, deadline, step_timeout, shape_budget, solvers, tables, out_dir):
        self.deadline = deadline
        self.step_timeout = step_timeout
        self.shape_budget = shape_budget
        self.solvers = solvers
        self.tables = tables
        self.out_dir = out_dir

    def remaining(self):
        return self.deadline - time.time()

    def run_step(self, inputs, outputs, s, timeout):
        spec = json.dumps({"inputs": [list(g) for g in inputs],
                           "outputs": [list(g) for g in outputs],
                           "s": s, "solvers": self.solvers, "tables": self.tables})
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
        """Try sizes st['t']+1 .. s_hi upward; stop at the first SAT (that size
        is the exact minimum, since every smaller size was UNSAT)."""
        s = st["t"] + 1
        while s <= s_hi and st["m"] is None and not st["stuck"]:
            left_shape = self.shape_budget - st["seconds"]
            left_time = min(deadline, self.deadline) - time.time()
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
        self.record(st, s_hi)

    def record(self, st, s_hi):
        line = {"e": st["e"], "kind": st["kind"], "key": st["key"], "searched_to": s_hi,
                "no_circuit_up_to": st["t"], "min_size": st["m"], "stuck": st["stuck"],
                "seconds": st["seconds"], "calls": st["calls"]}
        with LOCK:
            with open(os.path.join(self.out_dir, "progress.jsonl"), "a") as fh:
                fh.write(json.dumps(line) + "\n")
        log("[shape] %s %s %s  to=%d  t=%d  m=%s  %s" % (
            st["e"], st["kind"], st["key"], s_hi, st["t"], st["m"], st["stuck"]))


def run_encoding(e, runner, args, deadline):
    t0 = time.time()
    state = {}

    def get(kind, ins, outs):
        key = ec.shape_key(ins, outs)
        if key not in state:
            state[key] = new_state(e, kind, ins, outs)
        return state[key]

    # 1. creation: P/D groups holding exactly E's range 0..3 -> E
    V = ec.maxval(e)
    creation = []
    for ins in ec.pd_multisets(args.max_wires, 1):
        if ec.max_value(ins) != V:
            continue
        st = get("producer", ins, ((e, 0),))
        runner.extend(st, args.creation_cap, deadline)
        creation.append(st)
    if not creation:
        return {"name": e, "status": "no_creation_shape"}, state, None
    cands = []
    for st in creation:
        base_in = ec.phi2(st["ins"], BASE)
        if st["m"] is not None:
            cands.append((base_in - 2 * st["m"], True, st["key"]))
        else:   # proven lower bound t + 1 on the size
            cands.append((base_in - 2 * (st["t"] + 1), False, st["key"]))
    lo2 = max(c[0] for c in cands)
    tight = [c for c in cands if c[0] == lo2 and c[1]]
    lo_tight = bool(tight)
    lo_source = tight[0][2] if tight else [c for c in cands if c[0] == lo2][0][2]
    creation_out = [{"key": st["key"], "min_size": st["m"], "no_circuit_up_to": st["t"],
                     "stuck": st["stuck"], "circuit": st["circuit"]} for st in creation]
    phi_after_creation = lo2 / 2.0
    history = [{"pass": 0, "phi_e": lo2 / 2.0, "source": lo_source, "tight": lo_tight}]
    log("[creation] %s phi_E = %.1f from %s (tight=%s)" % (e, lo2 / 2.0, lo_source, lo_tight))

    # 2. fixpoint passes
    profits, profit_keys = [], set()
    recs = []
    converged = False
    passes_run = 0
    for p in range(1, args.max_passes + 1):
        passes_run = p
        phi = dict(BASE)
        phi[e] = lo2
        recs = []
        for kind, ins, outs in ec.e_shapes(e, phi, args.max_wires, args.max_out_wires):
            recs.append((ec.s_max(ins, outs, phi), get(kind, ins, outs)))
        todo = [(sm, st) for sm, st in recs
                if st["m"] is None and not st["stuck"] and st["t"] < sm]
        todo.sort(key=lambda x: (x[0], ec.wire_count(x[1]["ins"]), x[1]["key"]))
        log("[pass] %s pass %d phi_E=%.1f shapes=%d to_search=%d" % (
            e, p, lo2 / 2.0, len(recs), len(todo)))

        def work(item):
            sm, st = item
            if min(deadline, runner.deadline) - time.time() < 10:
                return
            runner.extend(st, sm, deadline)

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(work, todo))
        raises = []
        for sm, st in recs:
            if st["m"] is not None and st["m"] <= sm:
                if st["kind"] == "producer":
                    other = ec.phi2(st["outs"], phi) - lo2
                    raises.append((ec.phi2(st["ins"], phi) - other - 2 * st["m"], st["key"]))
                elif st["key"] not in profit_keys:
                    profit_keys.add(st["key"])
                    profits.append({"key": st["key"], "pass": p, "phi_e": lo2 / 2.0,
                                    "a": e_balance(st), "min_size": st["m"], "s_max": sm,
                                    "phi_drop": (ec.phi2(st["ins"], phi) - ec.phi2(st["outs"], phi)) / 2.0,
                                    "lo_source": lo_source, "lo_tight": lo_tight,
                                    "circuit": st["circuit"]})
                    log("[PROFIT] %s %s size %d < %.1f" % (
                        e, st["key"], st["m"], (ec.phi2(st["ins"], phi) - ec.phi2(st["outs"], phi)) / 2.0))
        if raises:
            best = max(raises)
            lo2, lo_source, lo_tight = best[0], best[1], True
            history.append({"pass": p, "phi_e": lo2 / 2.0, "source": lo_source, "tight": True})
            log("[raise] %s phi_E -> %.1f by %s" % (e, lo2 / 2.0, lo_source))
            continue
        converged = True
        break

    def decided(sm, st):
        return st["m"] is not None or st["t"] >= sm

    n = len(recs)
    n_dec = sum(1 for sm, st in recs if decided(sm, st))
    small = [(sm, st) for sm, st in recs if sm <= 6]
    if any(pr["lo_tight"] for pr in profits):
        status = "profitable"
    elif profits:
        status = "candidate_profit"
    elif converged and n_dec == n:
        status = "barrier_holds"
    else:
        status = "open"
    shapes_out = []
    for sm, st in sorted(recs, key=lambda x: (x[0], x[1]["key"])):
        shapes_out.append({"key": st["key"], "kind": st["kind"], "a": e_balance(st),
                           "in_wires": ec.wire_count(st["ins"]), "s_max": sm,
                           "min_size": st["m"], "no_circuit_up_to": st["t"],
                           "decided": decided(sm, st), "stuck": st["stuck"],
                           "seconds": st["seconds"],
                           "circuit": st["circuit"] if st["m"] is not None else None})
    out = {"name": e, "wires": ec.ENC[e]["label"], "table": list(ec.ENC[e]["table"]),
           "creation": creation_out, "phi_e_after_creation": phi_after_creation,
           "phi_history": history, "phi_e_final": lo2 / 2.0, "n_raises": len(history) - 1,
           "passes_run": passes_run, "converged": converged, "status": status,
           "n_shapes": n, "n_decided": n_dec,
           "n_by_kind": {k: sum(1 for _sm, st in recs if st["kind"] == k)
                         for k in ("producer", "consumer")},
           "n_s_max_le_6": len(small),
           "n_s_max_le_6_decided": sum(1 for sm, st in small if decided(sm, st)),
           "n_stuck": sum(1 for _sm, st in recs if st["stuck"]),
           "profits": profits, "minutes": round((time.time() - t0) / 60.0, 1),
           "shapes": shapes_out}
    log("[encoding] %s status=%s phi_E=%.1f shapes=%d decided=%d profits=%d" % (
        e, status, lo2 / 2.0, n, n_dec, len(profits)))
    return out, state, lo2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--max-wires", type=int, default=6)
    ap.add_argument("--max-out-wires", type=int, default=8)
    ap.add_argument("--minutes", type=float, default=330.0)
    ap.add_argument("--headline-minutes", type=float, default=30.0)
    ap.add_argument("--headline-extra", type=int, default=3)
    ap.add_argument("--step-timeout", type=float, default=600.0)
    ap.add_argument("--shape-budget", type=float, default=1500.0)
    ap.add_argument("--creation-cap", type=int, default=8)
    ap.add_argument("--max-passes", type=int, default=4)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--solvers", default="cadical195,glucose4")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    t_start = time.time()

    names = ec.register_linear(3)
    tables = {nm: [ec.ENC[nm]["k"], list(ec.ENC[nm]["table"])] for nm in names}
    encs = [{"name": nm, "wires": ec.ENC[nm]["label"], "table": list(ec.ENC[nm]["table"]),
             "canonical": list(ec.canonical(ec.ENC[nm]["table"], 3))} for nm in names]
    log("[encodings] " + json.dumps(encs))
    runner = Runner(t_start + 60 * args.minutes, args.step_timeout, args.shape_budget,
                    args.solvers.split(","), tables, args.out_dir)

    # C1: the generalized encoder must find every known block at its size,
    # and the full-adder shape must have no circuit of size <= 4.
    sanity = []
    for name in ("full_adder", "stockmeyer", "mdfa_prime", "mdfa", "pair_xor"):
        blk = kb.ALL[name]
        size = len(blk["circuit"]["gates"])
        res = runner.run_step([tuple(g) for g in blk["inputs"]],
                              [tuple(g) for g in blk["outputs"]], size, args.step_timeout)
        ok = bool(res.get("sat") and res.get("verified") and res.get("verified_parent"))
        sanity.append({"name": name, "s": size, "found": ok, "seconds": res.get("seconds"),
                       "timeout": bool(res.get("timeout")),
                       "error": str(res.get("error", ""))[-300:]})
        log("[sanity] %s size %d found=%s (%ss)" % (name, size, ok, res.get("seconds")))
    fa = new_state("-", "check", tuple(kb.FULL_ADDER["inputs"]), tuple(kb.FULL_ADDER["outputs"]))
    runner.extend(fa, 4, runner.deadline)
    fa_lower_ok = fa["m"] is None and fa["t"] == 4

    # per encoding, with a fair share of the time (minus the headline reserve)
    per_e, states, finals = [], {}, {}
    reserve = 60 * args.headline_minutes
    for i, e in enumerate(names):
        share = max(0.0, (runner.remaining() - reserve) / (len(names) - i))
        out, state, lo2 = run_encoding(e, runner, args, time.time() + share)
        per_e.append(out)
        states[e] = state
        finals[e] = lo2

    # headline: exact minimum sizes of the MDFA analogues -> P@0 + E@1
    headline = []
    for e in names:
        lo2 = finals.get(e)
        if lo2 is None:
            continue
        phi = dict(BASE)
        phi[e] = lo2
        outs = (("P", 0), (e, 1))
        for ins in (((e, 0), (e, 0)), ((e, 0), ("P", 0), ("D", 0)),
                    ((e, 0), ("P", 0), ("P", 0), ("P", 0))):
            key = ec.shape_key(ins, outs)
            st = states[e].get(key) or new_state(e, "consumer", ins, outs)
            sm = ec.s_max(ins, outs, phi)
            if runner.remaining() > 10:
                runner.extend(st, sm + args.headline_extra, runner.deadline)
            headline.append({"e": e, "key": key, "s_max": sm, "min_size": st["m"],
                             "no_circuit_up_to": st["t"], "stuck": st["stuck"],
                             "circuit": st["circuit"]})

    small_n = sum(r.get("n_s_max_le_6", 0) for r in per_e)
    small_dec = sum(r.get("n_s_max_le_6_decided", 0) for r in per_e)
    stats = {
        "sanity_all_found": all(x["found"] for x in sanity),
        "full_adder_no_circuit_le_4": fa_lower_ok,
        "n_encodings": len(names),
        "per_encoding": [{k: r.get(k) for k in (
            "name", "wires", "status", "phi_e_after_creation", "phi_e_final", "n_raises",
            "converged", "n_shapes", "n_decided", "n_s_max_le_6", "n_s_max_le_6_decided",
            "n_stuck", "minutes")} for r in per_e],
        "creation_sizes": {r["name"]: [(c["key"], c["min_size"]) for c in r.get("creation", [])]
                           for r in per_e},
        "n_profitable_encodings": sum(1 for r in per_e if r.get("status") == "profitable"),
        "n_candidate_encodings": sum(1 for r in per_e if r.get("status") == "candidate_profit"),
        "n_barrier_encodings": sum(1 for r in per_e if r.get("status") == "barrier_holds"),
        "profits": [dict(p, e=r["name"]) for r in per_e for p in r.get("profits", [])],
        "n_s_max_le_6": small_n,
        "n_s_max_le_6_decided": small_dec,
        "headline": [{k: h[k] for k in ("e", "key", "s_max", "min_size", "no_circuit_up_to",
                                         "stuck")} for h in headline],
        "minutes": round((time.time() - t_start) / 60.0, 1),
    }
    out = {"version": "sum-circuit-search search 2 (linear 3-bit encodings) v1",
           "params": vars(args), "encodings": encs, "sanity": sanity,
           "full_adder_check": {k: fa[k] for k in ("t", "m", "stuck")},
           "stats_for_verdicts": stats, "headline": headline, "encodings_detail": per_e}
    with open(os.path.join(args.out_dir, "results.json"), "w") as fh:
        json.dump(out, fh)
    log("[stats] " + json.dumps({k: v for k, v in stats.items() if k != "profits"}))
    log("[profits] " + json.dumps(stats["profits"]))


if __name__ == "__main__":
    main()
