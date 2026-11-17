# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Exhaustive check of the hand-built layers in THEORY-SSTAR.md (stdlib only).

s* = X + Y + a + b. Layer i reads x_i, y_i and a carry C in {0, 1, 2} on two
wires, and writes s_i = (x + y + C) mod 2 and the next carry (x + y + C) // 2
on two wires. A 2-wire carry code is a table: table[w1 + 2*w2] = carry value,
None for a word that never occurs.

Checks:
1. every layer is correct on every row it can see, and its codes have the
   class labels stated (same labelling as stagecore.label);
2. its gate count equals 7 + phi(out) - phi(in), phi = A1 0, J1 1, U0 2;
3. every chain of layers (start code A1 = the bits a, b) with 1..5 layers,
   followed by a decoder, is a correct circuit for s* on every input, and has
   exactly 7L + 2 gates.
"""
import argparse
import itertools
import json
import os
import sys

CODES = {
    "A1": (0, 1, 1, 2),        # two plain bits, value w1 + w2
    "J1": (0, 2, 1, 1),        # pair code (p, p^q), value p + q
    "U0": (0, 1, 2, None),     # binary: w1 = C mod 2, w2 = [C == 2]
}
PHI = {"A1": 0, "J1": 1, "U0": 2}

OPS = {
    "XOR": lambda a, b: a ^ b,
    "AND": lambda a, b: a & b,
    "OR": lambda a, b: a | b,
    "ANDN": lambda a, b: a & (1 - b),   # a and not b
}

# Full adder on (x, y, c): p = x^y, s = p^c, maj = ((x^c) & p) ^ x. 5 gates.
def fa(c, pre=""):
    return [
        (pre + "p", "XOR", "x", "y"),
        (pre + "s", "XOR", pre + "p", c),
        (pre + "h", "XOR", "x", c),
        (pre + "k", "AND", pre + "h", pre + "p"),
        (pre + "m", "XOR", pre + "k", "x"),
    ]

# GKL's layer (stagecore.STAGE_D): pair x, y, then MDFA'. Carry (P, R) in J1.
def gkl(P, R):
    return [
        ("q", "XOR", "x", "y"),
        ("g2", "OR", "x", "q"),
        ("g4", "XOR", "q", "g2"),
        ("g5", "XOR", P, "q"),
        ("s", "XOR", R, "q"),
        ("g7", "ANDN", "g5", R),
        ("g8", "XOR", "g2", "g7"),
    ]

LAYERS = {
    # binary carry (D, E): new 7-gate layer
    ("U0", "U0"): {"inputs": ["x", "y", "D", "E"], "gates": [
        ("p", "XOR", "x", "y"),
        ("g", "AND", "x", "y"),
        ("s", "XOR", "p", "D"),
        ("t", "AND", "p", "D"),
        ("e2", "AND", "E", "g"),
        ("u", "XOR", "t", "E"),
        ("d2", "XOR", "g", "u"),
    ], "outs": ["s", "d2", "e2"]},
    # full adder on (x, y, D); E passes through: C' = maj + E
    ("U0", "A1"): {"inputs": ["x", "y", "D", "E"], "gates": fa("D"),
                   "outs": ["s", "m", "E"]},
    ("U0", "J1"): {"inputs": ["x", "y", "D", "E"],
                   "gates": fa("D") + [("w", "XOR", "m", "E")],
                   "outs": ["s", "E", "w"]},
    # pair code (P, R): e = P & ~R is [C == 2]; full adder on (x, y, R)
    ("J1", "A1"): {"inputs": ["x", "y", "P", "R"],
                   "gates": [("e", "ANDN", "P", "R")] + fa("R"),
                   "outs": ["s", "m", "e"]},
    ("J1", "J1"): {"inputs": ["x", "y", "P", "R"], "gates": gkl("P", "R"),
                   "outs": ["s", "g4", "g8"]},
    ("J1", "U0"): {"inputs": ["x", "y", "P", "R"],
                   "gates": gkl("P", "R") + [("e", "ANDN", "g4", "g8")],
                   "outs": ["s", "g8", "e"]},
    # two plain bits (u, v)
    ("A1", "A1"): {"inputs": ["x", "y", "u", "v"],
                   "gates": fa("u", "f") + [("s", "XOR", "fs", "v"), ("c2", "AND", "fs", "v")],
                   "outs": ["s", "fm", "c2"]},
    ("A1", "J1"): {"inputs": ["x", "y", "u", "v"],
                   "gates": [("r", "XOR", "u", "v")] + gkl("u", "r"),
                   "outs": ["s", "g4", "g8"]},
    ("A1", "U0"): {"inputs": ["x", "y", "u", "v"],
                   "gates": fa("u", "f") + [("s", "XOR", "fs", "v"), ("c2", "AND", "fs", "v"),
                                            ("d", "XOR", "fm", "c2"), ("e", "AND", "fm", "c2")],
                   "outs": ["s", "d", "e"]},
}

DECODERS = {   # carry -> (bit of weight 1, bit of weight 2), relative
    "A1": {"inputs": ["w1", "w2"], "gates": [("d0", "XOR", "w1", "w2"), ("d1", "AND", "w1", "w2")],
           "outs": ["d0", "d1"]},
    "J1": {"inputs": ["w1", "w2"], "gates": [("d1", "ANDN", "w1", "w2")], "outs": ["w2", "d1"]},
    "U0": {"inputs": ["w1", "w2"], "gates": [], "outs": ["w1", "w2"]},
}


def label(t):
    t = tuple(t)
    if None in t:
        u = t.index(None)
        return "U%d" % t[u ^ 3]
    for v in (0, 1, 2):
        pos = [i for i, x in enumerate(t) if x == v]
        if len(pos) == 2:
            return ("A%d" if pos[0] ^ pos[1] == 3 else "J%d") % v
    return "?"


def run(circ, vals):
    env = dict(zip(circ["inputs"], vals))
    for name, op, a, b in circ["gates"]:
        if name in env:
            raise ValueError("gate name reused: %s" % name)
        env[name] = OPS[op](env[a], env[b])
    return [env[o] for o in circ["outs"]]


def check_layer(cin, cout, circ):
    tin, tout = CODES[cin], CODES[cout]
    for x, y, w1, w2 in itertools.product((0, 1), repeat=4):
        c = tin[w1 + 2 * w2]
        if c is None:
            continue
        s, o1, o2 = run(circ, [x, y, w1, w2])
        c2 = tout[o1 + 2 * o2]
        if c2 is None or s != (x + y + c) % 2 or c2 != (x + y + c) // 2:
            return False
    return True


def check_decoder(code, circ):
    t = CODES[code]
    for w1, w2 in itertools.product((0, 1), repeat=2):
        c = t[w1 + 2 * w2]
        if c is None:
            continue
        lo, hi = run(circ, [w1, w2])
        if lo + 2 * hi != c:
            return False
    return True


def check_chain(codes):
    """codes[0] = 'A1' (the bits a, b); layer i maps codes[i] -> codes[i+1]."""
    L = len(codes) - 1
    layers = [LAYERS[(codes[i], codes[i + 1])] for i in range(L)]
    dec = DECODERS[codes[-1]]
    size = sum(len(c["gates"]) for c in layers) + len(dec["gates"])
    n = 2 + 2 * L
    for bits in itertools.product((0, 1), repeat=n):
        carry = [bits[0], bits[1]]
        value = bits[0] + bits[1]
        outs = []
        for i in range(L):
            x, y = bits[2 + 2 * i], bits[3 + 2 * i]
            value += (x + y) << i
            s, w1, w2 = run(layers[i], [x, y] + carry)
            outs.append(s)
            carry = [w1, w2]
        outs += run(dec, carry)
        if sum(o << j for j, o in enumerate(outs)) != value:
            return False, size
    return True, size


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--max-layers", type=int, default=5)
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    ok_all = True
    res = {"labels": {k: label(v) for k, v in CODES.items()}, "layers": [], "decoders": {}, "chains": {}}
    for k, v in CODES.items():
        if label(v) != k:
            ok_all = False
    for (cin, cout), circ in sorted(LAYERS.items()):
        ok = check_layer(cin, cout, circ)
        g = len(circ["gates"])
        pred = 7 + PHI[cout] - PHI[cin]
        res["layers"].append({"cin": cin, "cout": cout, "gates": g, "correct": ok,
                              "phi_formula": pred, "matches_phi": g == pred})
        print("layer %s -> %s: %d gates, correct=%s, 7+phi(out)-phi(in)=%d" % (cin, cout, g, ok, pred))
        ok_all = ok_all and ok and g == pred
    for code, circ in sorted(DECODERS.items()):
        ok = check_decoder(code, circ)
        res["decoders"][code] = {"gates": len(circ["gates"]), "correct": ok,
                                 "is_2_minus_phi": len(circ["gates"]) == 2 - PHI[code]}
        ok_all = ok_all and ok
    for L in range(1, args.max_layers + 1):
        n_ok = 0
        sizes = set()
        total = 0
        for tail in itertools.product(sorted(CODES), repeat=L):
            ok, size = check_chain(("A1",) + tail)
            total += 1
            n_ok += ok
            sizes.add(size)
        res["chains"][str(L)] = {"chains": total, "correct": n_ok, "sizes": sorted(sizes),
                                 "all_size_7L_plus_2": sizes == {7 * L + 2}}
        print("L=%d: %d/%d chains correct, sizes %s" % (L, n_ok, total, sorted(sizes)))
        ok_all = ok_all and n_ok == total and sizes == {7 * L + 2}
    res["all_ok"] = ok_all
    with open(os.path.join(args.out_dir, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print("ALL_OK" if ok_all else "FAILED")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
