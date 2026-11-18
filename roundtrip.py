# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""The round-trip barrier for layered s* circuits (stdlib only).

See THEORY-ROUNDTRIP.md. In short: put a "pack" circuit (two plain bits u, v
-> a word of carry code A with value u + v) in front of a layer A -> B, and a
"decode" circuit (a word of code B -> its value in binary) behind it. The
result computes SUM_4(x, y, u, v) in binary, so

    pack(A) + cost(A -> B) + dec(B) >= size(SUM_4) = 9.

Summed along a layered circuit for s* with L layers and cut codes
C_0 = A1 (the bits a, b), C_1, ..., C_L, this gives

    size >= 9L - sum_{i=1}^{L-1} rt(C_i),    rt(C) = pack(C) + dec(C) >= 2.

This module computes pack and dec exactly for all 60 two-wire carry tables
(brute force over every circuit of at most 2 gates on 2 inputs; 2 always
suffice), the 9 x 9 lower-bound matrix 9 - pack(A) - dec(B), its minimum mean
cycles, and checks that the nine hand-built layers of verify_layers.py meet
the bound with equality (pack + layer + dec is a correct 9-gate SUM_4 circuit).
"""
import argparse
import itertools
import json
import os
import sys
from fractions import Fraction

import verify_layers as vl

SUM4_SIZE = 9   # size(SUM_4) over all two-input gates; certified by job_sum4.py

ROWS = range(4)                                  # row r: first input r & 1, second r >> 1
IN1 = sum((r & 1) << r for r in ROWS)            # 0b1010
IN2 = sum((r >> 1) << r for r in ROWS)           # 0b1100
ALL = 15

PACKERS = {   # (u, v) -> a word of the code with value u + v, in verify_layers format
    "A1": {"inputs": ["u", "v"], "gates": [], "outs": ["u", "v"]},
    "J1": {"inputs": ["u", "v"], "gates": [("r", "XOR", "u", "v")], "outs": ["u", "r"]},
    "U0": {"inputs": ["u", "v"], "gates": [("d", "XOR", "u", "v"), ("e", "AND", "u", "v")],
           "outs": ["d", "e"]},
}


def all_tables():
    """Every 2-wire carry table (table[w1 + 2*w2] in {0, 1, 2, None}) in
    which the values 0, 1 and 2 all occur. There are 60."""
    return [t for t in itertools.product((0, 1, 2, None), repeat=4) if {0, 1, 2} <= set(t)]


def apply_gate(f, a, b):
    """Column of gate f (bit 2*a + b of f is its output) on input columns a, b."""
    m = 0
    for r in ROWS:
        av = (a >> r) & 1
        bv = (b >> r) & 1
        m |= ((f >> (2 * av + bv)) & 1) << r
    return m


def achievable_pairs(max_gates=2):
    """{(col1, col2): fewest gates} over every circuit on two inputs with at
    most max_gates gates (all 16 two-input functions); each of the two
    outputs is any node or a constant, with either polarity."""
    best = {}

    def record(nodes, g):
        cols = {0, ALL}
        for m in nodes:
            cols.add(m)
            cols.add(m ^ ALL)
        for a in cols:
            for b in cols:
                if best.get((a, b), g + 1) > g:
                    best[(a, b)] = g

    def grow(nodes, g):
        record(nodes, g)
        if g == max_gates:
            return
        for j in range(len(nodes)):
            for k in range(j + 1, len(nodes)):
                for f in range(16):
                    grow(nodes + [apply_gate(f, nodes[j], nodes[k])], g + 1)

    grow([IN1, IN2], 0)
    return best


def _bits(m1, m2, r):
    return (m1 >> r) & 1, (m2 >> r) & 1


def pack_ok(table, m1, m2):
    for r in ROWS:
        u, v = r & 1, r >> 1
        w1, w2 = _bits(m1, m2, r)
        if table[w1 + 2 * w2] != u + v:
            return False
    return True


def dec_ok(table, m1, m2):
    for r in ROWS:                     # row r is the word with index r
        if table[r] is None:
            continue
        c0, c1 = _bits(m1, m2, r)
        if c0 + 2 * c1 != table[r]:
            return False
    return True


def min_cost(table, ok, best):
    found = [g for (m1, m2), g in best.items() if ok(table, m1, m2)]
    if not found:
        raise ValueError("no circuit with <= 2 gates for %r" % (table,))
    return min(found)


def table_costs(best=None):
    best = best or achievable_pairs()
    return {t: (min_cost(t, pack_ok, best), min_cost(t, dec_ok, best)) for t in all_tables()}


def class_costs(per_table=None):
    """{label: {"pack", "dec", "rt", "tables"}}; raises if a class is not uniform."""
    per_table = per_table or table_costs()
    out = {}
    for t, (p, d) in per_table.items():
        lab = vl.label(t)
        cur = out.setdefault(lab, {"pack": p, "dec": d, "rt": p + d, "tables": 0})
        if (cur["pack"], cur["dec"]) != (p, d):
            raise ValueError("class %s is not uniform" % lab)
        cur["tables"] += 1
    return out


def lb_matrix(classes):
    labs = sorted(classes)
    return labs, [[SUM4_SIZE - classes[a]["pack"] - classes[b]["dec"] for b in labs] for a in labs]


def min_mean_cycle(w):
    """Karp. w[u][v] is an int or None (no edge). Returns a Fraction or None."""
    N = len(w)
    D = [[None] * N for _ in range(N + 1)]
    for v in range(N):
        D[0][v] = 0
    for k in range(1, N + 1):
        for v in range(N):
            best = None
            for u in range(N):
                if D[k - 1][u] is not None and w[u][v] is not None:
                    c = D[k - 1][u] + w[u][v]
                    if best is None or c < best:
                        best = c
            D[k][v] = best
    mu = None
    for v in range(N):
        if D[N][v] is None:
            continue
        worst = None
        for k in range(N):
            if D[k][v] is None:
                continue
            val = Fraction(D[N][v] - D[k][v], N - k)
            if worst is None or val > worst:
                worst = val
        if worst is not None and (mu is None or worst < mu):
            mu = worst
    return mu


def restricted(labs, w, keep):
    return [[w[i][j] if (labs[i] in keep and labs[j] in keep) else None
             for j in range(len(labs))] for i in range(len(labs))]


def chain_lower_bound(codes, classes):
    """codes = [C_0, ..., C_L] (C_0 the code of a, b). Lower bound on the
    gates of any layered s* circuit with these cut codes, final decoder
    included: 9L - pack(C_0) - sum of rt over the internal cuts."""
    L = len(codes) - 1
    return SUM4_SIZE * L - classes[codes[0]]["pack"] - sum(classes[c]["rt"] for c in codes[1:L])


def sandwich(cin, cout):
    """pack(cin) + hand layer cin -> cout + decoder(cout) on (x, y, u, v).
    Returns (computes SUM_4 correctly on all 16 inputs, total gates)."""
    pk, layer, dec = PACKERS[cin], vl.LAYERS[(cin, cout)], vl.DECODERS[cout]
    size = len(pk["gates"]) + len(layer["gates"]) + len(dec["gates"])
    for x, y, u, v in itertools.product((0, 1), repeat=4):
        w1, w2 = vl.run(pk, [u, v])
        s, o1, o2 = vl.run(layer, [x, y, w1, w2])
        d0, d1 = vl.run(dec, [o1, o2])
        if s + 2 * d0 + 4 * d1 != x + y + u + v:
            return False, size
    return True, size


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--max-layers", type=int, default=4)
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    ok = True
    classes = class_costs()
    labs, w = lb_matrix(classes)
    rt2 = {c for c in labs if classes[c]["rt"] == 2}
    rt3 = {c for c in labs if classes[c]["rt"] <= 3}
    mmc = {
        "all_2wire_classes": str(min_mean_cycle(w)),
        "classes_rt_le_3": str(min_mean_cycle(restricted(labs, w, rt3))),
        "classes_rt_2": str(min_mean_cycle(restricted(labs, w, rt2))),
    }
    for c in labs:
        print("%s: pack %d, dec %d, round trip %d (%d tables)" % (
            c, classes[c]["pack"], classes[c]["dec"], classes[c]["rt"], classes[c]["tables"]))
    print("min mean cycle of 9 - pack(A) - dec(B):", mmc)
    sand = []
    for (cin, cout) in sorted(vl.LAYERS):
        good, size = sandwich(cin, cout)
        sand.append({"cin": cin, "cout": cout, "computes_sum4": good, "gates": size})
        print("sandwich %s -> %s: SUM_4 correct=%s, %d gates" % (cin, cout, good, size))
        ok = ok and good and size == SUM4_SIZE
    chains = {}
    for L in range(1, args.max_layers + 1):
        tight = 0
        total = 0
        for tail in itertools.product(sorted(vl.CODES), repeat=L):
            codes = ("A1",) + tail
            correct, size = vl.check_chain(codes)
            total += 1
            tight += correct and size == chain_lower_bound(codes, classes) == 7 * L + 2
        chains[str(L)] = {"chains": total, "meet_bound_exactly": tight}
        print("L=%d: %d/%d chains are correct and meet the bound 7L+2 exactly" % (L, tight, total))
        ok = ok and tight == total
    res = {"sum4_size_assumed": SUM4_SIZE, "classes": classes, "labels": labs, "lb_matrix": w,
           "min_mean_cycles": mmc, "round_trip_2_classes": sorted(rt2),
           "sandwiches": sand, "chains": chains, "all_ok": ok}
    with open(os.path.join(args.out_dir, "results-roundtrip.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print("ROUNDTRIP_OK" if ok else "ROUNDTRIP_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
