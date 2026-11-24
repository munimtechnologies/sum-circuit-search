# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Sound pruning rules for a circuit of exactly S_{n-1} + 2 gates for SUM_n.

See THEORY-SUM6.md. The rules talk about the variables of stagecore's CNF
(e.first[g, j], e.second[g, j], e.f[g, pq], e.src[o, v]); gate g reads node j
as its first input when e.first[g, j] is true, and computes
f[2 * val(first) + val(second)] with f00 = 0.

R1 (fan-out): every input is read by at most `max_out` gates.
R2 (constant gate): if gate g reads input x and becomes constant when x = c,
    then g is not an output, no other gate reads x, and at most one gate
    reads g.
S  (symmetry): the first gate reads inputs 0 and 1 (valid for symmetric
    functions only: relabel the two inputs the first gate reads).
"""
from itertools import combinations, product


def offset_relation(k, c, m):
    """F(k, c): k plain bits -> (c + their count) in binary on m bits."""
    outs = [(Y, sum(Y[i] << i for i in range(m))) for Y in product((0, 1), repeat=m)]
    rows = []
    for r in range(1 << k):
        v = bin(r).count("1") + c
        rows.append((r, frozenset(Y for Y, vv in outs if vv == v)))
    return k, m, rows


def reads(e, h, x):
    """The two literals 'gate h reads node x' (as first or as second input)."""
    return [e.first[h, x], e.second[h, x]]


def const_cases(e, g, x, c):
    """Literal lists; each conjunction says: gate g reads input x and is
    constant once x = c.  Gate value is f[2p + q] with f00 = 0."""
    f01, f10, f11 = e.f[g, (0, 1)], e.f[g, (1, 0)], e.f[g, (1, 1)]
    A, B = e.first[g, x], e.second[g, x]
    if c == 0:
        # x first: f(0, q) = (0, f01); x second: f(p, 0) = (0, f10)
        return [[A, -f01], [B, -f10]]
    # x first: f(1, q) = (f10, f11); x second: f(p, 1) = (f01, f11)
    return [[A, f10, f11], [A, -f10, -f11], [B, f01, f11], [B, -f01, -f11]]


def outdeg_clauses(e, x, k):
    """At most k gates read input x (gates never read one node twice)."""
    lits = []
    for h in range(e.n, e.n + e.s):
        lits.extend(reads(e, h, x))
    return [[-l for l in sub] for sub in combinations(lits, k + 1)]


def const_clauses(e, g, x, c):
    gates = range(e.n, e.n + e.s)
    out = []
    for case in const_cases(e, g, x, c):
        neg = [-l for l in case]
        for o in range(e.m):
            out.append(neg + [-e.src[o, g]])
        for h in gates:
            if h != g:
                for l in reads(e, h, x):
                    out.append(neg + [-l])
        later = [h for h in gates if h > g]
        for h1, h2 in combinations(later, 2):
            for l1 in reads(e, h1, g):
                for l2 in reads(e, h2, g):
                    out.append(neg + [-l1, -l2])
    return out


def symmetry_clauses(e):
    """The first gate reads inputs 0 and 1."""
    return [[e.first[e.n, 0]], [e.second[e.n, 1]]]


def rule_clauses(e, max_out=2, consts=(0,), symmetric=True):
    cl = []
    for x in range(e.n):
        cl.extend(outdeg_clauses(e, x, max_out))
    for g in range(e.n, e.n + e.s):
        for x in range(e.n):
            for c in consts:
                cl.extend(const_clauses(e, g, x, c))
    if symmetric:
        cl.extend(symmetry_clauses(e))
    return cl


def violated(clauses, asg):
    """Clauses not satisfied by a {var: bool} assignment."""
    return [c for c in clauses
            if not any((asg[abs(l)] if l > 0 else not asg[abs(l)]) for l in c)]
