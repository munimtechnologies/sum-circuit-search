# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""The block sandwich for SUM_n (stdlib only). See THEORY-BLOCKS.md.

A block B reads P groups (one plain bit) and D groups (a pair (p, p XOR q) with
value p + q) and writes P and D groups, keeping the weighted sum. Put a pairing
XOR in front of every D input (u, v -> (u, u XOR v)) and a decoder behind the
outputs that turns them into the binary digits of their total. The whole thing
computes SUM_k, k = (number of P inputs) + 2 (number of D inputs), so

    size(B) >= S_k - (number of D inputs) - DEC(outputs),     S_k = size(SUM_k).

With phi(P) = 9/2 and phi(D) = 8, phi(in) + (number of D inputs) = 9k/2 for any
mix of P and D, so

    slack(B) = phi(in) - phi(out) - size(B) <= 9k/2 - S_k - phi(out) + DEC(out).

This module checks every explicit decoder exhaustively, checks that each of the
six known blocks meets the bound with equality (the sandwich is a correct S_k-gate
SUM_k circuit), and tabulates the bound for "reduced" one-column blocks (outputs
= one plain bit at weight 0 plus one carry representation R at weight 1).
"""
import argparse
import itertools
import json
import os
import sys
from fractions import Fraction

import known_blocks as kb

PHI = {"P": Fraction(9, 2), "D": Fraction(8)}
UNITS = {"P": 1, "D": 2}
WIRES = {"P": 1, "D": 2}
HALF = Fraction(1, 2)

# Exact sizes of SUM_k over all two-input gates (Knuth, TAOCP 4A 7.1.2, for k <= 5;
# table of Kulikov, Pechenev and Slezkin, MFCS 2022, arXiv:2102.12579).
# S_4 is re-proved by job sum4-sandwich-v1 and S_5 by job sum56-exact-v1.
SUM_EXACT = {1: 0, 2: 2, 3: 5, 4: 9, 5: 11}
# Best known upper bounds only (same table; Cirbo, arXiv:2412.14933, for 11 and 15).
SUM_UPPER = {6: 16, 7: 19, 9: 27, 11: 34, 15: 51}

UNPAIR = {   # D -> P@0 + P@1: parity r, carry p AND NOT r. 1 gate.
    "inputs": [kb.D0], "outputs": [kb.P0, kb.P1],
    "circuit": {"n": 2, "gates": [[0, 1, kb.FIRST_AND_NOT_SECOND]], "outs": [[1, 0], [2, 0]]},
}

KNOWN = dict(kb.ALL)
KNOWN["unpair"] = UNPAIR

# Carry representations R (groups at relative weights) with an explicit decoder
# to binary (output j has relative weight 2^j) and the largest value R must hold.
HALF_ADDER = {"n": 2, "gates": [[0, 1, kb.XOR], [0, 1, kb.AND]], "outs": [[2, 0], [3, 0]]}
REPS = {
    "P": {"groups": [("P", 0)], "decoder": {"n": 1, "gates": [], "outs": [[0, 0]]}},
    "D": {"groups": [("D", 0)], "decoder": UNPAIR["circuit"]},
    "P+P": {"groups": [("P", 0), ("P", 0)], "decoder": HALF_ADDER},
    "P+P@1": {"groups": [("P", 0), ("P", 1)], "decoder": {"n": 2, "gates": [], "outs": [[0, 0], [1, 0]]}},
    "P+D": {"groups": [("P", 0), ("D", 0)], "decoder": kb.STOCKMEYER["circuit"]},
    "P+P+P": {"groups": [("P", 0), ("P", 0), ("P", 0)], "decoder": kb.FULL_ADDER["circuit"]},
}


def run(circ, vals):
    w = list(vals)
    if len(w) != circ["n"]:
        raise ValueError("expected %d inputs, got %d" % (circ["n"], len(w)))
    for a, b, tt in circ["gates"]:
        w.append(tt[2 * w[a] + w[b]])
    return [w[i] ^ neg for i, neg in circ["outs"]]


def group_value(kind, wires):
    if kind == "P":
        return wires[0]
    p, r = wires
    return p + (p ^ r)


def groups_value(groups, wires):
    """Total value of groups [(kind, weight)] read from a flat wire list."""
    total, i = 0, 0
    for kind, wt in groups:
        total += group_value(kind, wires[i:i + WIRES[kind]]) << wt
        i += WIRES[kind]
    return total


def n_wires(groups):
    return sum(WIRES[k] for k, _ in groups)


def max_value(groups):
    return sum(UNITS[k] << wt for k, wt in groups)


def phi(groups):
    return sum((PHI[k] for k, _ in groups), Fraction(0))


def decoder_ok(rep):
    """The decoder is correct on every wire word of R (both codes of a D value 1)."""
    groups, dec = rep["groups"], rep["decoder"]
    for wires in itertools.product((0, 1), repeat=n_wires(groups)):
        bits = run(dec, list(wires))
        if sum(b << j for j, b in enumerate(bits)) != groups_value(groups, wires):
            return False
    return True


def units_in(block):
    return sum(UNITS[k] for k, _ in block["inputs"])


def d_inputs(block):
    return sum(1 for k, _ in block["inputs"] if k == "D")


def block_slack(block):
    size = len(block["circuit"]["gates"])
    return phi(block["inputs"]) - phi(block["outputs"]) - size


def dec_outputs_size(block):
    """Gates of the decoder used behind this block: one unpair per D output."""
    return sum(1 for k, _ in block["outputs"] if k == "D")


def block_bound(block):
    """9k/2 - S_k - phi(out) + DEC(out), DEC = one gate per D output (the outputs
    of every known block are at distinct weights once each D is unpaired)."""
    k = units_in(block)
    return Fraction(9, 2) * k - SUM_EXACT[k] - phi(block["outputs"]) + dec_outputs_size(block)


def sandwich(block):
    """Pairing XORs + block + unpairs on k plain bits. Returns (the outputs are the
    binary digits of the sum on every input, number of gates)."""
    k = units_in(block)
    size = d_inputs(block) + len(block["circuit"]["gates"]) + dec_outputs_size(block)
    for bits in itertools.product((0, 1), repeat=k):
        wires, i = [], 0
        for kind, _ in block["inputs"]:
            if kind == "P":
                wires.append(bits[i])
                i += 1
            else:
                u, v = bits[i], bits[i + 1]
                wires += [u, u ^ v]
                i += 2
        out = run(block["circuit"], wires)
        weights, values, j = [], [], 0
        for kind, wt in block["outputs"]:
            if kind == "P":
                weights.append(wt)
                values.append(out[j])
                j += 1
            else:
                lo, hi = run(UNPAIR["circuit"], out[j:j + 2])
                weights += [wt, wt + 1]
                values += [lo, hi]
                j += 2
        if len(set(weights)) != len(weights):
            return False, size
        if sum(v << w for v, w in zip(values, weights)) != sum(bits):
            return False, size
    return True, size


def rep_cost(name):
    rep = REPS[name]
    return phi(rep["groups"]) - len(rep["decoder"]["gates"])   # phi(R) - DEC(R)


def reduced_constant(k):
    """c_k with: every reduced one-column block on k units has slack <= c_k - S_k.
    Reduced = outputs P@0 plus one listed R at weight 1 that can hold k // 2."""
    need = k // 2
    best = min(rep_cost(n) for n in REPS if max_value(REPS[n]["groups"]) >= need)
    return Fraction(9, 2) * k - PHI["P"] - best


def bit_length(k):
    return k.bit_length()


def plain_slack_constant(k):
    """The plain SUM_k circuit as a block (k P@0 in, its binary digits out) has
    slack 9/2 (k - bitlen(k)) - S_k."""
    return Fraction(9, 2) * (k - bit_length(k))


def largest_profitable(constant):
    """Largest integer S with constant - S >= 1/2 (slack is a multiple of 1/2)."""
    x = constant - HALF
    return x.numerator // x.denominator


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    ok = True
    res = {"decoders": {}, "known_blocks": {}, "reduced": {}, "plain": {}}
    for name, rep in REPS.items():
        good = decoder_ok(rep)
        res["decoders"][name] = {"correct": good, "gates": len(rep["decoder"]["gates"]),
                                 "phi_minus_dec": str(rep_cost(name)),
                                 "max_value": max_value(rep["groups"])}
        print("decoder %s: correct=%s, %d gates" % (name, good, len(rep["decoder"]["gates"])))
        ok = ok and good
    for name, block in sorted(KNOWN.items()):
        k = units_in(block)
        good, size = sandwich(block)
        sl, bd = block_slack(block), block_bound(block)
        tight = good and size == SUM_EXACT[k] and sl == bd
        res["known_blocks"][name] = {"units": k, "sandwich_correct": good, "sandwich_gates": size,
                                     "S_k": SUM_EXACT[k], "slack": str(sl), "bound": str(bd),
                                     "tight": tight}
        print("%s: k=%d, sandwich SUM_k correct=%s with %d gates (S_k=%d), slack %s, bound %s" % (
            name, k, good, size, SUM_EXACT[k], sl, bd))
        ok = ok and tight
    for k in range(2, 8):
        c = reduced_constant(k)
        row = {"constant": str(c), "profitable_needs_S_k_at_most": largest_profitable(c)}
        if k in SUM_EXACT:
            row["max_slack"] = str(c - SUM_EXACT[k])
        if k in SUM_UPPER:
            row["best_known_upper"] = SUM_UPPER[k]
        res["reduced"][str(k)] = row
        print("reduced blocks on %d units: slack <= %s - S_%d %s" % (k, c, k, row))
    for k in (5, 6, 7, 9, 11, 15):
        c = plain_slack_constant(k)
        known = SUM_EXACT.get(k, SUM_UPPER.get(k))
        res["plain"][str(k)] = {"constant": str(c), "profitable_if_S_k_at_most": largest_profitable(c),
                                "best_known": known, "slack_at_best_known": str(c - known)}
        print("plain SUM_%d block: slack = %s - S_%d (best known %d)" % (k, c, k, known))
    res["all_ok"] = ok
    with open(os.path.join(args.out_dir, "results-blocks.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print("BLOCKS_OK" if ok else "BLOCKS_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
