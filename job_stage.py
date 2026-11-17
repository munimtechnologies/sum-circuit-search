# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Search 4: is there a layered circuit for BA^{s*} with fewer than 7 gates
per layer (i.e. below Goncharov-Kulikov-Levtsov's 3.5n)? See SEARCH4.md.

Part 1: exact minimum gates of one layer for every pair (C_in, C_out) of the
        9 classes of 2-wire carry codes (81 SAT ladders, sizes 0..cap), then
        the best rate of any layered circuit with 2-wire carries = the minimum
        mean cycle of that 9 x 9 matrix (Karp). The best short cycle is built
        into whole s* circuits and checked on every input.
Part 2: every class of 3-wire carry codes, one layer, same code in and out:
        is there a stage with <= 6 gates?
Part 3: 2-layer stages, same 2-wire code in and out: is there one with
        <= 13 gates (below two GKL layers)? SAT ladders with a time limit;
        a timeout is NOT a proof.

python job_stage.py --out-dir /out"""
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
import stagecore as sc  # noqa: E402

LOCK = threading.Lock()


def log(msg):
    with LOCK:
        print(msg, flush=True)


def rel_stage(cin, cout, layers=1):
    return {"kind": "stage", "cin": [cin[0], list(cin[1])],
            "cout": [cout[0], list(cout[1])], "layers": layers}


def rel_decode(c):
    return {"kind": "decode", "c": [c[0], list(c[1])]}


class Ladder:
    def __init__(self, solvers, out_dir):
        self.solvers = solvers
        self.out_dir = out_dir

    def run(self, rel, lo, hi, timeout, tag=""):
        """Sizes lo..hi upward until the first circuit. Result: min (or None),
        none_up_to (no circuit of any size lo..none_up_to), timeout, error."""
        res = {"tag": tag, "lo": lo, "hi": hi, "min": None, "none_up_to": lo - 1,
               "timeout": False, "error": "", "circuit": None, "seconds": 0.0}
        if hi < lo:
            return res
        if timeout < 2:
            res["timeout"] = True
            return res
        spec = json.dumps({"rel": rel, "s_lo": lo, "s_hi": hi, "solvers": self.solvers})
        t0 = time.time()
        proc = subprocess.Popen([sys.executable, os.path.join(HERE, "solve_stage.py"), spec],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            res["timeout"] = True
        res["seconds"] = round(time.time() - t0, 1)
        for line in (out or "").splitlines():
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if "error" in d:
                res["error"] = str(d.get("error"))
                break
            if d.get("sat"):
                n, m, rows = sc.relation_from_spec(rel)
                ok = bool(d.get("verified")) and sc.check_relation(n, m, rows, d["circuit"])
                if ok:
                    res["min"] = d["s"]
                    res["circuit"] = d["circuit"]
                else:
                    res["error"] = "sat_unverified"
                    res["circuit"] = d.get("circuit")
                break
            res["none_up_to"] = d["s"]
        if (not res["timeout"] and res["min"] is None and not res["error"]
                and res["none_up_to"] < hi):
            res["error"] = "incomplete: " + (err or "")[-300:]
        line = {k: res[k] for k in ("tag", "lo", "hi", "min", "none_up_to", "timeout",
                                    "error", "seconds")}
        with LOCK:
            with open(os.path.join(self.out_dir, "progress.jsonl"), "a") as fh:
                fh.write(json.dumps(line) + "\n")
        return res


def compose(start, unit_circs, layers, end):
    comp = sc.build_sstar(start, [(c, layers) for c in unit_circs], end)
    return {"stage_layers": comp["layers"], "n": comp["n_in"],
            "size": sc.composite_size(comp), "ok": bool(sc.verify_sstar(comp))}


def compose_cycle(start_by, edge, decode_by, cyc, units, layers=1):
    """Layer 0 by start_by[cyc[0]], then `units` stages along the cycle, then
    decode_by[last code]. Returns a dict, or None if a piece is missing."""
    l = len(cyc)
    circs = [edge.get((cyc[i % l], cyc[(i + 1) % l])) for i in range(units)]
    st = start_by.get(cyc[0])
    en = decode_by.get(cyc[units % l])
    if st is None or en is None or any(c is None for c in circs):
        return None
    return compose(st, circs, layers, en)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--p1-cap", type=int, default=10)
    ap.add_argument("--part2-minutes", type=float, default=90.0)
    ap.add_argument("--part3-minutes", type=float, default=150.0)
    ap.add_argument("--step-timeout", type=float, default=900.0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--solvers", default="cadical195,glucose4")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    t_start = time.time()
    lad = Ladder(args.solvers.split(","), args.out_dir)

    # ---------------------------------------------------------------- C1
    fa = lad.run({"kind": "sum", "n": 3, "m": 2}, 0, 6, args.step_timeout, "full_adder")
    explicit = []
    for name, rel, circ in [
            ("stage_D", rel_stage(sc.DCODE, sc.DCODE), sc.STAGE_D),
            ("stage_SUM2", rel_stage(sc.SUM2, sc.SUM2), sc.STAGE_SUM2),
            ("start_SUM2_D", rel_stage(sc.SUM2, sc.DCODE), sc.START_SUM2_D),
            ("decode_D", rel_decode(sc.DCODE), sc.DECODE_D),
            ("stage_D_twice", rel_stage(sc.DCODE, sc.DCODE, 2), sc.stack(sc.STAGE_D, sc.STAGE_D))]:
        n, m, rows = sc.relation_from_spec(rel)
        explicit.append({"name": name, "gates": len(circ["gates"]),
                         "ok": bool(sc.check_relation(n, m, rows, circ))})
    gkl = [compose(sc.START_SUM2_D, [sc.STAGE_D] * L, 1, sc.DECODE_D) for L in (1, 2, 3, 4)]
    log("[C1] full adder min %s; explicit %s; gkl %s" % (fa["min"], explicit, gkl))

    # ------------------------------------------------------------ part 1
    codes2, total2 = sc.carry_codes(2)
    labels2 = [sc.label(t) for t in codes2]
    C2 = [(2, t) for t in codes2]
    N2 = len(C2)
    log("[part1] %d classes of 2-wire codes (%d tables): %s" % (N2, total2, labels2))

    def p1(item):
        i, j = item
        r = lad.run(rel_stage(C2[i], C2[j]), 0, args.p1_cap, args.step_timeout,
                    "p1 %s->%s" % (labels2[i], labels2[j]))
        log("[p1] %s -> %s: min %s (none <= %s) %s" % (labels2[i], labels2[j], r["min"],
                                                     r["none_up_to"], r["error"]))
        return item, r

    def p1_start(j):
        return j, lad.run(rel_stage(sc.SUM2, C2[j]), 0, args.p1_cap + 2, args.step_timeout,
                          "start SUM2->%s" % labels2[j])

    def p1_decode(j):
        return j, lad.run(rel_decode(C2[j]), 0, 4, args.step_timeout, "decode %s" % labels2[j])

    pairs = [(i, j) for i in range(N2) for j in range(N2)]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        res1 = dict(ex.map(p1, pairs))
        starts2 = dict(ex.map(p1_start, range(N2)))
        decodes2 = dict(ex.map(p1_decode, range(N2)))
    W = [[res1[(i, j)]["min"] for j in range(N2)] for i in range(N2)]
    complete = all(W[i][j] is not None or res1[(i, j)]["none_up_to"] >= args.p1_cap
                   for i in range(N2) for j in range(N2))
    mu = sc.min_mean_cycle(W)
    # lower-bound matrix: the exact minimum where found, else (largest size
    # proved impossible) + 1; its min mean cycle is a proved lower bound
    W_lb = [[W[i][j] if W[i][j] is not None else res1[(i, j)]["none_up_to"] + 1
             for j in range(N2)] for i in range(N2)]
    mu_lb = sc.min_mean_cycle(W_lb)
    short = sc.best_short_cycle(W, 3)
    edge2 = {(i, j): res1[(i, j)]["circuit"] for i in range(N2) for j in range(N2)
             if res1[(i, j)]["circuit"] is not None}
    start_by2 = {j: r["circuit"] for j, r in starts2.items() if r["circuit"] is not None}
    decode_by2 = {j: r["circuit"] for j, r in decodes2.items() if r["circuit"] is not None}
    comps1 = []
    if short is not None:
        for units in (1, 2, 3, 4):
            comps1.append(compose_cycle(start_by2, edge2, decode_by2, short[1], units))
    entries = [W[i][j] for i in range(N2) for j in range(N2) if W[i][j] is not None]
    iD = labels2.index("J1")
    iS = labels2.index("A1")
    log("[part1] mu* = %s, best short cycle %s, compositions %s" % (
        mu, None if short is None else (str(short[0]), [labels2[c] for c in short[1]]), comps1))

    # ------------------------------------------------------------ part 2
    codes3, total3 = sc.carry_codes(3)
    C3 = [(3, t) for t in codes3]
    labels3 = [sc.label(t) for t in codes3]
    log("[part2] %d classes of 3-wire codes (%d tables)" % (len(C3), total3))
    p2_deadline = time.time() + 60 * args.part2_minutes

    def p2(i):
        left = p2_deadline - time.time()
        r = lad.run(rel_stage(C3[i], C3[i]), 0, 6, min(args.step_timeout, left),
                    "p2 %s" % labels3[i])
        if r["min"] is not None:
            log("[p2 FOUND] %s stage with %d gates" % (labels3[i], r["min"]))
        return i, r

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        res2 = dict(ex.map(p2, range(len(C3))))
    found2 = []
    for i, r in sorted(res2.items()):
        if r["min"] is None:
            continue
        st = lad.run(rel_stage(sc.SUM2, C3[i]), 0, 14, args.step_timeout, "p2 start")
        de = lad.run(rel_decode(C3[i]), 0, 6, args.step_timeout, "p2 decode")
        comps = []
        if st["circuit"] is not None and de["circuit"] is not None:
            comps = [compose(st["circuit"], [r["circuit"]] * u, 1, de["circuit"]) for u in (1, 2, 3)]
        found2.append({"code": labels3[i], "table": list(codes3[i]), "min": r["min"],
                       "circuit": r["circuit"], "compositions": comps})
    decided2 = sum(1 for r in res2.values() if r["min"] is not None or r["none_up_to"] >= 6)

    # ------------------------------------------------------------ part 3
    per_code = 60 * args.part3_minutes * args.workers / max(1, N2)

    def p3(i):
        bound = None
        for j in range(N2):
            if W[i][j] is not None and W[j][i] is not None:
                b = W[i][j] + W[j][i]
                bound = b if bound is None else min(bound, b)
        hi = 13 if bound is None else min(13, bound - 1)
        r = lad.run(rel_stage(C2[i], C2[i], 2), 0, hi, per_code, "p3 %s" % labels2[i])
        log("[p3] %s two layers: min %s, none <= %s (hi %d) timeout=%s %s" % (
            labels2[i], r["min"], r["none_up_to"], hi, r["timeout"], r["error"]))
        return i, (hi, r)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        res3 = dict(ex.map(p3, range(N2)))
    found3 = []
    for i, (hi, r) in sorted(res3.items()):
        if r["min"] is None:
            continue
        comps = []
        if i in start_by2 and i in decode_by2:
            comps = [compose(start_by2[i], [r["circuit"]] * u, 2, decode_by2[i]) for u in (1, 2)]
        found3.append({"code": labels2[i], "min": r["min"], "circuit": r["circuit"],
                       "compositions": comps})

    # ------------------------------------------------------------ verdicts
    def ok_comp(c):
        return c is not None and c["ok"]
    wow = []
    if short is not None and short[0] < 7 and comps1 and all(ok_comp(c) for c in comps1):
        wow.append("part1 layered rate %s gates per layer" % short[0])
    for f in found2:
        if f["min"] <= 6 and f["compositions"] and all(ok_comp(c) for c in f["compositions"]):
            wow.append("part2 3-wire code %s: %d gates per layer" % (f["code"], f["min"]))
    for f in found3:
        if f["min"] <= 13 and f["compositions"] and all(ok_comp(c) for c in f["compositions"]):
            wow.append("part3 code %s: %d gates per two layers" % (f["code"], f["min"]))
    stats = {
        "c1_full_adder_min": fa["min"],
        "c1_full_adder_min_is_5": fa["min"] == 5 and fa["none_up_to"] == 4,
        "c1_explicit_all_ok": all(x["ok"] for x in explicit),
        "c1_gkl_composites": gkl,
        "c1_gkl_ok": all(c["ok"] and c["size"] == 7 * c["stage_layers"] + 9 for c in gkl),
        "c1_cost_D_D_le_7": W[iD][iD] is not None and W[iD][iD] <= 7,
        "c1_cost_SUM2_SUM2_le_7": W[iS][iS] is not None and W[iS][iS] <= 7,
        "p1_matrix_complete": complete,
        "p1_mu_star": None if mu is None else str(mu),
        "p1_mu_star_lower_bound": None if mu_lb is None else str(mu_lb),
        "p1_mu_star_is_7": None if not complete else (mu == 7 and mu_lb == 7),
        "p1_best_short_cycle": None if short is None else
            {"mean": str(short[0]), "codes": [labels2[c] for c in short[1]]},
        "p1_compositions": comps1,
        "p2_cost_D_D": W[iD][iD],
        "p2_cost_SUM2_SUM2": W[iS][iS],
        "p3_classes": len(C3),
        "p3_tables": total3,
        "p3_decided": decided2,
        "p3_found_le_6": len(found2),
        "p4_per_code": {labels2[i]: {"hi": hi, "min": r["min"], "none_up_to": r["none_up_to"],
                                      "timeout": r["timeout"], "seconds": r["seconds"]}
                        for i, (hi, r) in sorted(res3.items())},
        "p4_found": len(found3),
        "p4_decided": sum(1 for _i, (hi, r) in res3.items()
                          if r["min"] is not None or r["none_up_to"] >= hi),
        "p5_min_entry": min(entries) if entries else None,
        "wow": wow,
        "minutes": round((time.time() - t_start) / 60.0, 1),
    }
    out = {
        "version": "sum-circuit-search search 4 (s* layered stages) v1",
        "params": vars(args),
        "c1": {"full_adder": {k: fa[k] for k in ("min", "none_up_to", "error")},
               "explicit": explicit, "gkl": gkl},
        "codes2": [{"label": labels2[i], "table": list(codes2[i])} for i in range(N2)],
        "matrix": [[{"min": res1[(i, j)]["min"], "none_up_to": res1[(i, j)]["none_up_to"],
                     "error": res1[(i, j)]["error"]} for j in range(N2)] for i in range(N2)],
        "matrix_circuits": {"%s->%s" % (labels2[i], labels2[j]): c for (i, j), c in edge2.items()},
        "starts": {labels2[j]: {"min": r["min"], "none_up_to": r["none_up_to"],
                                "circuit": r["circuit"]} for j, r in starts2.items()},
        "decodes": {labels2[j]: {"min": r["min"], "none_up_to": r["none_up_to"],
                                 "circuit": r["circuit"]} for j, r in decodes2.items()},
        "part2": {"found": found2,
                  "codes": [{"label": labels3[i], "min": r["min"], "none_up_to": r["none_up_to"],
                             "timeout": r["timeout"], "error": r["error"]}
                            for i, r in sorted(res2.items())]},
        "part3": {"found": found3},
        "stats_for_verdicts": stats,
    }
    with open(os.path.join(args.out_dir, "results.json"), "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    log("[stats] " + json.dumps(stats))


if __name__ == "__main__":
    main()
