# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""THEORY.md, Lemma 3, as arithmetic (stdlib only, exact fractions).

A group is (kind, weight) with kind "P" (one plain bit) or "D" (a pair stored as
(p, p XOR q), value p + q). Potentials: P = 9/2, D = 8. For a block B with
inputs `ins`, outputs `outs` and `size` gates:

  slack(B) = phi(ins) - phi(outs) - size            (> 0 means "profitable")

Lemma 3 (THEORY.md): let the base column b be the lowest input weight, and let
every input sit at weight b or b + 1. Count
  p0 = P inputs at b, d0 = D inputs at b, d1 = D inputs at b + 1,
  k1 = P inputs at b + 1, k1_out = P outputs at b + 1,
  delta = max(0, k1 - k1_out)          (plain weight-(b+1) bits B must be fed),
  R = 4*d1 + 2*delta + p0 + 2*d0       (plain input bits used per copy of B).
If gain = slack(B) - delta/2 > 0, then
  size(SUM_n) <= (9/2 - gain/R) * n + O(log n).
The delta/2 is the cost of making each missing plain weight-1 bit with a full
adder (slack -1/2). epsilon() returns gain/R, or 0 when gain <= 0 (the lemma
then says nothing). It is a guaranteed improvement, not the best rate.
"""
from fractions import Fraction

PHI = {"P": Fraction(9, 2), "D": Fraction(8)}


def phi(groups):
    total = Fraction(0)
    for kind, _w in groups:
        total += PHI[kind]
    return total


def slack(ins, outs, size):
    return phi(ins) - phi(outs) - size


def counts(ins, outs):
    if not ins:
        raise ValueError("a block needs inputs")
    b = min(w for _k, w in ins)
    for kind, w in ins:
        if kind not in PHI:
            raise ValueError("unknown kind %r" % (kind,))
        if w > b + 1:
            raise ValueError("Lemma 3 covers inputs at the base column and the next one only")
    return {
        "base": b,
        "p0": sum(1 for k, w in ins if k == "P" and w == b),
        "d0": sum(1 for k, w in ins if k == "D" and w == b),
        "k1": sum(1 for k, w in ins if k == "P" and w == b + 1),
        "d1": sum(1 for k, w in ins if k == "D" and w == b + 1),
        "k1_out": sum(1 for k, w in outs if k == "P" and w == b + 1),
    }


def delta(ins, outs):
    c = counts(ins, outs)
    return max(0, c["k1"] - c["k1_out"])


def rate_denominator(ins, outs):
    c = counts(ins, outs)
    return 4 * c["d1"] + 2 * delta(ins, outs) + c["p0"] + 2 * c["d0"]


def gain(ins, outs, size):
    return slack(ins, outs, size) - Fraction(delta(ins, outs), 2)


def epsilon(ins, outs, size):
    g = gain(ins, outs, size)
    if g <= 0:
        return Fraction(0)
    return g / rate_denominator(ins, outs)


def gamma_bound(ins, outs, size):
    """Upper bound on the constant gamma in size(SUM_n) <= gamma*n + O(log n)."""
    return Fraction(9, 2) - epsilon(ins, outs, size)
