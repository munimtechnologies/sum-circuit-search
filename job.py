# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Search every single-column P/D compressor shape for a "profitable" block:
a circuit whose size is strictly below phi(in) - phi(out) (phi_P = 4.5,
phi_D = 8). Sizes are tried upward from 0 (every gate must be used), so
UNSAT at every size 0..s_max proves no circuit of size <= s_max exists.

python job.py --out-dir /out [--max-wires 6] [--minutes 330]"""
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
import known_blocks as kb  # noqa: E402
import sumcore as sc  # noqa: E402

LOCK = threading.Lock()


def log(msg):
    with LOCK:
        print(msg, flush=True)


def run_step(inputs, outputs, s, timeout, solvers):
    spec = json.dumps({"inputs": [list(g) for g in inputs],
                       "outputs": [list(g) for g in outputs],
                       "s": s, "solvers": solvers})
    t0 = time.time()
    try:
        proc = subprocess.run([sys.executable, os.path.join(HERE, "solve_one.py"), spec],
                              capture_output=True, text=True, timeout=max(1, timeout))
    except subprocess.TimeoutExpired:
        return {"s": s, "timeout": True, "seconds": round(time.time() - t0, 1)}
    lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
    if proc.returncode != 0 or not lines:
        return {"s": s, "error": (proc.stderr or "")[-800:], "seconds": round(time.time() - t0, 1)}
    res = json.loads(lines[-1])
    res["seconds"] = round(time.time() - t0, 1)
    if res.get("sat"):
        ok, row = sc.check(inputs, outputs, res["circuit"])   # independent re-check
        res["verified_parent"] = bool(ok)
    return res


class Runner:
    def __init__(self, deadline, step_timeout, shape_budget, solvers):
        self.deadline = deadline
        self.step_timeout = step_timeout
        self.shape_budget = shape_budget
        self.solvers = solvers

    def remaining(self):
        return self.deadline - time.time()

    def search(self, inputs, outputs, s_lo, s_hi):
        """Try sizes s_lo..s_hi in order; stop at first SAT, timeout or error."""
        steps = []
        start = time.time()
        status, found, circuit = "unsat_all", None, None
        for s in range(s_lo, s_hi + 1):
            left = min(self.remaining(), self.shape_budget - (time.time() - start))
            if left < 5:
                status = "out_of_time"
                break
            res = run_step(inputs, outputs, s, min(self.step_timeout, left), self.solvers)
            short = {k: res.get(k) for k in ("s", "sat", "timeout", "seconds", "solver",
                                             "vars", "clauses") if k in res}
            if "error" in res:
                short["error"] = res["error"][-300:]
            steps.append(short)
            if res.get("timeout"):
                status = "timeout"
                break
            if "error" in res:
                status = "error"
                break
            if res.get("sat"):
                if res.get("verified") and res.get("verified_parent"):
                    status, found, circuit = "sat", s, res["circuit"]
                else:
                    status = "sat_unverified"
                    circuit = res.get("circuit")
                break
        proven = s_lo - 1
        for st in steps:
            if st.get("sat") is False and not st.get("timeout") and "error" not in st:
                proven = st["s"]
            else:
                break
        return {"status": status, "found_size": found, "circuit": circuit,
                "no_circuit_up_to": proven, "steps": steps}


def shape_record(ins, outs, sm, res):
    if res is None:
        status = "not_run"
    elif res["status"] == "sat":
        status = "profitable"
    elif res["status"] == "unsat_all":
        status = "barrier_holds"
    elif res["status"] in ("timeout", "out_of_time"):
        status = "open"
    else:
        status = res["status"]
    rec = {"inputs": sc.shape_name(ins), "outputs": sc.shape_name(outs),
           "in_wires": sc.wire_count(ins), "out_wires": sc.wire_count(outs),
           "phi_diff": (sc.phi2(ins) - sc.phi2(outs)) / 2.0, "s_max": sm,
           "status": status}
    if res is not None:
        rec.update({"no_circuit_up_to": res["no_circuit_up_to"],
                    "found_size": res["found_size"], "circuit": res["circuit"],
                    "steps": res["steps"]})
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--max-wires", type=int, default=6)
    ap.add_argument("--minutes", type=float, default=330.0)
    ap.add_argument("--step-timeout", type=float, default=900.0)
    ap.add_argument("--shape-budget", type=float, default=2400.0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--solvers", default="cadical195,glucose4")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    t_start = time.time()
    runner = Runner(t_start + 60 * args.minutes, args.step_timeout, args.shape_budget,
                    args.solvers.split(","))

    # 1. completeness checks: the encoder must find every known block at its size
    sanity = []
    for name in ("full_adder", "stockmeyer", "mdfa_prime", "mdfa", "pair_xor"):
        blk = kb.ALL[name]
        size = len(blk["circuit"]["gates"])
        res = run_step(blk["inputs"], blk["outputs"], size, args.step_timeout, runner.solvers)
        ok = bool(res.get("sat") and res.get("verified") and res.get("verified_parent"))
        sanity.append({"name": name, "s": size, "found": ok, "seconds": res.get("seconds"),
                       "solver": res.get("solver"), "timeout": bool(res.get("timeout")),
                       "error": res.get("error", "")[-300:] if "error" in res else ""})
        log("[sanity] %s size %d found=%s (%ss)" % (name, size, ok, res.get("seconds")))

    # 2. every shape, cheapest first
    shapes = sc.enumerate_shapes(args.max_wires)
    shapes.sort(key=lambda x: (x[2], sc.wire_count(x[0]), sc.shape_name(x[0]), sc.shape_name(x[1])))
    log("[shapes] %d shapes with <= %d input wires" % (len(shapes), args.max_wires))
    results = [None] * len(shapes)

    def work(i):
        ins, outs, sm = shapes[i]
        if runner.remaining() < 30:
            return
        res = runner.search(ins, outs, 0, sm)
        results[i] = res
        with LOCK:
            with open(os.path.join(args.out_dir, "progress.jsonl"), "a") as fh:
                fh.write(json.dumps(shape_record(ins, outs, sm, res)) + "\n")
        log("[shape] %s -> %s  s_max=%d  %s  no_circuit_up_to=%d%s" % (
            sc.shape_name(ins), sc.shape_name(outs), sm, res["status"], res["no_circuit_up_to"],
            ("  FOUND size %d" % res["found_size"]) if res["found_size"] is not None else ""))

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, range(len(shapes))))

    # 3. exact minimum of MDFA' (its s_max, 3, is below its size, 6; the
    #    shape loop already covers the full adder, Stockmeyer and MDFA)
    extend = []
    for name in ("mdfa_prime",):
        blk = kb.ALL[name]
        size = len(blk["circuit"]["gates"])
        sm = sc.s_max(blk["inputs"], blk["outputs"])
        if runner.remaining() < 60:
            extend.append({"name": name, "status": "not_run"})
            continue
        res = runner.search(blk["inputs"], blk["outputs"], sm + 1, size - 1)
        extend.append({"name": name, "known_size": size, "searched": [sm + 1, size - 1],
                       "status": res["status"], "found_size": res["found_size"],
                       "circuit": res["circuit"], "no_circuit_up_to": res["no_circuit_up_to"],
                       "steps": res["steps"]})
        log("[extend] %s sizes %d..%d: %s no_circuit_up_to=%d" % (
            name, sm + 1, size - 1, res["status"], res["no_circuit_up_to"]))

    records = [shape_record(ins, outs, sm, results[i]) for i, (ins, outs, sm) in enumerate(shapes)]

    def find(ins, outs):
        for r in records:
            if r["inputs"] == ins and r["outputs"] == outs:
                return r
        return None

    def count(pred):
        return sum(1 for r in records if pred(r))

    small = [r for r in records if r["s_max"] <= 8]
    stats = {
        "n_shapes": len(records),
        "by_status": {st: count(lambda r, st=st: r["status"] == st)
                      for st in sorted(set(r["status"] for r in records))},
        "n_profitable": count(lambda r: r["status"] == "profitable"),
        "profitable": [{k: r[k] for k in ("inputs", "outputs", "s_max", "found_size", "circuit")}
                       for r in records if r["status"] == "profitable"],
        "sanity_all_found": all(x["found"] for x in sanity),
        "full_adder_shape": find("P@0+P@0+P@0", "P@0+P@1"),
        "mdfa_shape": find("P@0+D@0+D@0", "P@0+D@1"),
        "n_s_max_le_8": len(small),
        "n_s_max_le_8_decided": sum(1 for r in small if r["status"] in ("barrier_holds", "profitable")),
        "by_in_wires": {str(w): {"n": count(lambda r, w=w: r["in_wires"] == w),
                                 "decided": count(lambda r, w=w: r["in_wires"] == w and
                                                  r["status"] in ("barrier_holds", "profitable")),
                                 "profitable": count(lambda r, w=w: r["in_wires"] == w and
                                                     r["status"] == "profitable")}
                        for w in range(1, args.max_wires + 1)},
        "minutes": round((time.time() - t_start) / 60.0, 1),
    }
    for key in ("full_adder_shape", "mdfa_shape"):
        r = stats[key]
        if r is not None:
            stats[key] = {k: r.get(k) for k in ("status", "s_max", "no_circuit_up_to", "found_size")}
    out = {"version": "sum-circuit-search v1",
           "params": vars(args), "sanity": sanity, "extend": extend,
           "stats_for_verdicts": stats, "shapes": records}
    with open(os.path.join(args.out_dir, "results.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    log("[stats] " + json.dumps({k: v for k, v in stats.items() if k != "profitable"}))
    log("[profitable] " + json.dumps(stats["profitable"]))


if __name__ == "__main__":
    main()
