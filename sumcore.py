# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Core of the SUM_n compressor-block search (stdlib only).

A *group* is (kind, weight). Kinds:
  "P": one wire b, value b.
  "D": two wires (u, v) = (p, p XOR q) for two same-weight bits p, q;
       value = u + (u XOR v) = p + q.
A *block* maps input groups (all at weight 0 here) to output groups so that
sum(value * 2**weight) is preserved for every input assignment. The outputs
are a relation, not a function: any valid code is allowed (for D, the value 1
has two codes), and output wires may be negated for free (negations are
absorbed by the gates that read them, as in the full binary basis B2).

Potentials (twice the real value, so they stay integers): P = 9 (4.5), D = 16 (8).
With these, the XOR that pairs two P bits into a D (cost 1) and Demenkov et
al.'s MDFA (P + 2D -> P@0 + D@1, cost 8) are both exactly tight, and they force
these values. A block whose size is strictly below phi(in) - phi(out) is
"profitable"; by LP duality, any profitable block lowers the best constant
in size(SUM_n) <= c*n + o(n) obtainable from these building blocks below 4.5.
"""
from itertools import product

PHI2 = {"P": 9, "D": 16}
WIRES = {"P": 1, "D": 2}
MAXVAL = {"P": 1, "D": 2}
KINDS = ("P", "D")


def group_value(kind, bits):
    if kind == "P":
        return bits[0]
    if kind == "D":
        u, v = bits[0], bits[1]
        return u + (u ^ v)
    raise ValueError(kind)


def wire_count(groups):
    return sum(WIRES[k] for k, _ in groups)


def value(groups, bits):
    total = 0
    i = 0
    for kind, w in groups:
        n = WIRES[kind]
        total += group_value(kind, bits[i:i + n]) << w
        i += n
    return total


def phi2(groups):
    return sum(PHI2[k] for k, _ in groups)


def s_max(inputs, outputs):
    """Largest gate count s with s < phi(in) - phi(out); -1 if none."""
    diff2 = phi2(inputs) - phi2(outputs)
    return (diff2 - 1) // 2


def max_value(groups):
    return sum(MAXVAL[k] << w for k, w in groups)


def achievable(groups):
    vals = {0}
    for kind, w in groups:
        vals = {a + (g << w) for a in vals for g in range(MAXVAL[kind] + 1)}
    return vals


def input_shapes(max_wires):
    out = []
    for d in range(0, max_wires // 2 + 1):
        for p in range(0, max_wires - 2 * d + 1):
            if p + d == 0:
                continue
            out.append(tuple([("P", 0)] * p + [("D", 0)] * d))
    return out


def output_shapes(inputs, max_out_wires=8):
    """All output shapes with phi(out) <= phi(in) - 1/2 that can hold every
    total 0..V of the inputs. Weights w with 2**w > V are never used."""
    V = max_value(inputs)
    budget2 = phi2(inputs) - 1
    weights = [w for w in range(0, 16) if (1 << w) <= V]
    slots = [(k, w) for w in weights for k in KINDS]
    need = set(range(V + 1))
    results = []

    def rec(idx, cur, phi, wires):
        if idx == len(slots):
            if cur and need <= achievable(cur):
                results.append(tuple(cur))
            return
        k, w = slots[idx]
        c = 0
        while phi + c * PHI2[k] <= budget2 and wires + c * WIRES[k] <= max_out_wires:
            rec(idx + 1, cur + [(k, w)] * c, phi + c * PHI2[k], wires + c * WIRES[k])
            c += 1

    rec(0, [], 0, 0)
    return results


def enumerate_shapes(max_wires, max_out_wires=8):
    shapes = []
    for ins in input_shapes(max_wires):
        for outs in output_shapes(ins, max_out_wires):
            sm = s_max(ins, outs)
            if sm >= 0:
                shapes.append((ins, outs, sm))
    return shapes


def shape_name(groups):
    return "+".join("%s@%d" % (k, w) for k, w in groups)


# ---------------------------------------------------------------- circuits
# circuit = {"n": n, "gates": [[j, k, [f00, f01, f10, f11]], ...],
#            "outs": [[src, pol], ...]}  src = -1 means constant 0.
# Gate g (node index n + position) computes f[2*val(j) + val(k)], j < k < g.

def evaluate(circ, bits):
    vals = list(bits)
    for j, k, f in circ["gates"]:
        vals.append(f[2 * vals[j] + vals[k]])
    res = []
    for src, pol in circ["outs"]:
        x = 0 if src < 0 else vals[src]
        res.append(x ^ pol)
    return res


def check(inputs, outputs, circ):
    n = wire_count(inputs)
    if circ["n"] != n or len(circ["outs"]) != wire_count(outputs):
        return False, -1
    for idx, (j, k, f) in enumerate(circ["gates"]):
        g = n + idx
        if not (0 <= j < k < g) or len(f) != 4:
            return False, -1
    for r in range(1 << n):
        bits = [(r >> i) & 1 for i in range(n)]
        y = evaluate(circ, bits)
        if value(outputs, y) != value(inputs, bits):
            return False, r
    return True, None


# ---------------------------------------------------------------- CNF
class Encoding:
    def __init__(self):
        self.nvars = 0
        self.clauses = []
        self.first = {}
        self.second = {}
        self.f = {}
        self.t = {}
        self.a = {}
        self.b = {}
        self.src = {}
        self.pol = {}
        self.y = {}

    def var(self):
        self.nvars += 1
        return self.nvars

    def add(self, clause):
        self.clauses.append(clause)

    def exactly_one(self, lits):
        self.add(list(lits))
        for i in range(len(lits)):
            for j in range(i + 1, len(lits)):
                self.add([-lits[i], -lits[j]])


FPQ = ((0, 1), (1, 0), (1, 1))


def encode(inputs, outputs, s, all_used=True):
    """CNF: is there a circuit of exactly s normal (f00 = 0), non-degenerate
    B2 gates, every gate read by a later gate or an output, whose outputs
    (any source, free negation) satisfy the block relation on every row?
    UNSAT for every size 0..S  <=>  no circuit of size <= S exists."""
    e = Encoding()
    n = wire_count(inputs)
    m = wire_count(outputs)
    rows = 1 << n
    e.n, e.s, e.m, e.rows = n, s, m, rows
    gates = list(range(n, n + s))

    def node_val_lit(node, r):
        """(constant, literal): constant is 0/1 for inputs, None for gates."""
        if node < n:
            return (r >> node) & 1, None
        return None, e.t[node, r]

    for g in gates:
        for r in range(rows):
            e.t[g, r] = e.var()
    for g in gates:
        preds = list(range(g))
        for j in preds:
            e.first[g, j] = e.var()
            e.second[g, j] = e.var()
        e.exactly_one([e.first[g, j] for j in preds])
        e.exactly_one([e.second[g, j] for j in preds])
        for j in preds:
            for k in preds:
                if k <= j:
                    e.add([-e.first[g, j], -e.second[g, k]])
        for pq in FPQ:
            e.f[g, pq] = e.var()
        f01, f10, f11 = e.f[g, (0, 1)], e.f[g, (1, 0)], e.f[g, (1, 1)]
        e.add([f01, f10, f11])            # not constant 0
        e.add([f01, -f10, -f11])          # not "= first input"
        e.add([-f01, f10, -f11])          # not "= second input"
        for r in range(rows):
            a = e.a[g, r] = e.var()
            b = e.b[g, r] = e.var()
            for sel, x in ((e.first, a), (e.second, b)):
                for j in preds:
                    c, lit = node_val_lit(j, r)
                    sv = sel[g, j]
                    if c is None:
                        e.add([-sv, -x, lit])
                        e.add([-sv, x, -lit])
                    elif c == 1:
                        e.add([-sv, x])
                    else:
                        e.add([-sv, -x])
            t = e.t[g, r]
            for p in (0, 1):
                for q in (0, 1):
                    base = [(-a if p else a), (-b if q else b)]
                    if p == 0 and q == 0:
                        e.add(base + [-t])
                    else:
                        fv = e.f[g, (p, q)]
                        e.add(base + [-t, fv])
                        e.add(base + [t, -fv])
    sources = [-1] + list(range(n + s))
    for o in range(m):
        for v in sources:
            e.src[o, v] = e.var()
        e.exactly_one([e.src[o, v] for v in sources])
        e.pol[o] = e.var()
        for r in range(rows):
            e.y[o, r] = e.var()
    for o in range(m):
        pol = e.pol[o]
        for r in range(rows):
            y = e.y[o, r]
            for v in sources:
                sv = e.src[o, v]
                if v < 0:
                    c, lit = 0, None
                else:
                    c, lit = node_val_lit(v, r)
                if lit is None:
                    if c == 0:      # y = pol
                        e.add([-sv, pol, -y])
                        e.add([-sv, -pol, y])
                    else:           # y = not pol
                        e.add([-sv, pol, y])
                        e.add([-sv, -pol, -y])
                else:               # y = lit xor pol
                    e.add([-sv, lit, pol, -y])
                    e.add([-sv, lit, -pol, y])
                    e.add([-sv, -lit, pol, y])
                    e.add([-sv, -lit, -pol, -y])
    for r in range(rows):
        bits = [(r >> i) & 1 for i in range(n)]
        vin = value(inputs, bits)
        for Y in product((0, 1), repeat=m):
            if value(outputs, list(Y)) != vin:
                e.add([(-e.y[o, r] if Y[o] else e.y[o, r]) for o in range(m)])
    if all_used:
        for g in gates:
            lits = []
            for h in gates:
                if h > g:
                    lits.append(e.first[h, g])
                    lits.append(e.second[h, g])
            for o in range(m):
                lits.append(e.src[o, g])
            e.add(lits)
    return e


def decode(e, model):
    pos = set(l for l in model if l > 0)
    gates = []
    for g in range(e.n, e.n + e.s):
        j = [jj for jj in range(g) if e.first[g, jj] in pos]
        k = [kk for kk in range(g) if e.second[g, kk] in pos]
        f = [0] + [1 if e.f[g, pq] in pos else 0 for pq in FPQ]
        gates.append([j[0], k[0], f])
    outs = []
    for o in range(e.m):
        srcs = [v for v in [-1] + list(range(e.n + e.s)) if e.src[o, v] in pos]
        outs.append([srcs[0], 1 if e.pol[o] in pos else 0])
    return {"n": e.n, "gates": gates, "outs": outs}


def assignment_from_circuit(e, circ):
    """Full variable assignment induced by a circuit (for testing the CNF)."""
    asg = {}
    n = e.n
    for (g, j), v in e.first.items():
        asg[v] = circ["gates"][g - n][0] == j
    for (g, j), v in e.second.items():
        asg[v] = circ["gates"][g - n][1] == j
    for (g, pq), v in e.f.items():
        asg[v] = circ["gates"][g - n][2][2 * pq[0] + pq[1]] == 1
    for r in range(e.rows):
        bits = [(r >> i) & 1 for i in range(n)]
        vals = list(bits)
        for j, k, f in circ["gates"]:
            vals.append(f[2 * vals[j] + vals[k]])
        for g in range(n, n + e.s):
            j, k, _ = circ["gates"][g - n]
            asg[e.t[g, r]] = vals[g] == 1
            asg[e.a[g, r]] = vals[j] == 1
            asg[e.b[g, r]] = vals[k] == 1
        for o in range(e.m):
            src, pol = circ["outs"][o]
            x = 0 if src < 0 else vals[src]
            asg[e.y[o, r]] = (x ^ pol) == 1
    for (o, v), var in e.src.items():
        asg[var] = circ["outs"][o][0] == v
    for o, var in e.pol.items():
        asg[var] = circ["outs"][o][1] == 1
    return asg


def unsatisfied(clauses, asg):
    bad = []
    for c in clauses:
        if not any((asg[abs(l)] if l > 0 else not asg[abs(l)]) for l in c):
            bad.append(c)
    return bad
