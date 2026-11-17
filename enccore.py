# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Search 2 core: compressor blocks over general group encodings (stdlib only).

A group *encoding* is a k-wire code with a value table: the k wire bits
b_0..b_{k-1} form the index sum(b_i << i), and table[index] is the value the
group stands for. A *group* is (encoding name, weight). Built in:
  "P": 1 wire, table (0, 1)               -- a plain bit
  "D": 2 wires (p, p^q), table (0, 2, 1, 1) -- Demenkov et al.'s pair code
Search 2 adds every indecomposable XOR-linear 3-bit encoding: wires are
three independent GF(2) linear forms of bits (p, q, r) and the value is
p + q + r. Up to permuting and negating wires there are exactly seven such
encodings; two are P+P+P and P+D, and five are new (register_linear(3)).

Blocks, relational outputs, free output negation, normal gates and the CNF
are exactly as in sumcore.py (search 1); only the value function is general.
Potentials are doubled so they stay integers: P = 9 (4.5), D = 16 (8).
"""
from itertools import permutations, product

PHI2_BASE = {"P": 9, "D": 16}
ENC = {}


def register(name, k, table, label=""):
    table = tuple(int(v) for v in table)
    if len(table) != (1 << k):
        raise ValueError("table of %s must have %d entries" % (name, 1 << k))
    ENC[name] = {"k": int(k), "table": table, "label": label}


register("P", 1, (0, 1), "p")
register("D", 2, (0, 2, 1, 1), "p, p^q")


# ---------------------------------------------------------------- semantics
def code_index(bits):
    idx = 0
    for i, b in enumerate(bits):
        idx |= (b & 1) << i
    return idx


def group_value(name, bits):
    return ENC[name]["table"][code_index(bits)]


def wire_count(groups):
    return sum(ENC[n]["k"] for n, _ in groups)


def value(groups, bits):
    total = 0
    i = 0
    for name, w in groups:
        k = ENC[name]["k"]
        total += group_value(name, bits[i:i + k]) << w
        i += k
    return total


def maxval(name):
    return max(ENC[name]["table"])


def max_value(groups):
    return sum(maxval(n) << w for n, w in groups)


def achievable(groups):
    vals = {0}
    for name, w in groups:
        gv = set(ENC[name]["table"])
        vals = {a + (g << w) for a in vals for g in gv}
    return vals


def phi2(groups, phi):
    return sum(phi[n] for n, _ in groups)


def s_max(inputs, outputs, phi):
    """Largest gate count s with s < phi(in) - phi(out); -1 if none."""
    return (phi2(inputs, phi) - phi2(outputs, phi) - 1) // 2


def shape_name(groups):
    return "+".join("%s@%d" % (n, w) for n, w in groups)


def shape_key(inputs, outputs):
    return shape_name(inputs) + " -> " + shape_name(outputs)


# ---------------------------------------------------------- linear encodings
VARS = "pqrs"


def popcount(x):
    return bin(x).count("1")


def rank2(rows, k):
    rows = list(rows)
    r = 0
    for bit in range(k):
        piv = None
        for i in range(r, len(rows)):
            if (rows[i] >> bit) & 1:
                piv = i
                break
        if piv is None:
            continue
        rows[r], rows[piv] = rows[piv], rows[r]
        for i in range(len(rows)):
            if i != r and (rows[i] >> bit) & 1:
                rows[i] ^= rows[r]
        r += 1
    return r


def linear_table(rows):
    """Wire i = parity(rows[i] & x) for x = (p, q, r, ...) as bits 0, 1, 2, ...;
    value = popcount(x). rows must be linearly independent."""
    k = len(rows)
    table = [None] * (1 << k)
    for x in range(1 << k):
        idx = 0
        for i, row in enumerate(rows):
            idx |= (popcount(row & x) & 1) << i
        table[idx] = popcount(x)
    return tuple(table)


def transform(table, k, perm, mask):
    """Relabel wires: new bit i = old bit perm[i] XOR bit i of mask."""
    out = [None] * (1 << k)
    for idx in range(1 << k):
        new = 0
        for i in range(k):
            new |= (((idx >> perm[i]) & 1) ^ ((mask >> i) & 1)) << i
        out[new] = table[idx]
    return tuple(out)


def canonical(table, k):
    """Smallest table over all wire permutations and negations."""
    best = None
    for perm in permutations(range(k)):
        for mask in range(1 << k):
            t = transform(table, k, perm, mask)
            if best is None or t < best:
                best = t
    return best


def product_table(parts):
    """parts = [(k, table), ...] side by side -> (k_total, table of the sum)."""
    k = sum(kk for kk, _ in parts)
    out = []
    for idx in range(1 << k):
        v, shift = 0, 0
        for kk, t in parts:
            v += t[(idx >> shift) & ((1 << kk) - 1)]
            shift += kk
        out.append(v)
    return k, tuple(out)


def linear_classes(k):
    """canonical table -> first row tuple found, over all invertible k x k
    GF(2) matrices (rows as bit masks)."""
    classes = {}
    for rows in product(range(1, 1 << k), repeat=k):
        if rank2(rows, k) < k:
            continue
        c = canonical(linear_table(rows), k)
        if c not in classes:
            classes[c] = rows
    return classes


def decomposable_canonicals(k, indec):
    """Canonical tables of side-by-side products (>= 2 parts) of the
    indecomposable classes in indec (dict size -> [(canonical, rows)])."""
    res = set()

    def rec(remaining, min_part, parts):
        if remaining == 0:
            if len(parts) >= 2:
                kk, t = product_table(parts)
                res.add(canonical(t, kk))
            return
        for kk in range(min_part, remaining + 1):
            for c, _rows in indec.get(kk, []):
                rec(remaining - kk, kk, parts + [(kk, c)])

    rec(k, 1, [])
    return res


def indecomposable_linear_classes(k):
    """Sorted [(canonical table, rows)] of linear k-bit encodings that are not
    a side-by-side product of smaller ones."""
    indec = {}
    for kk in range(1, k + 1):
        cls = linear_classes(kk)
        dec = decomposable_canonicals(kk, indec)
        indec[kk] = sorted((c, rows) for c, rows in cls.items() if c not in dec)
    return indec[k]


def row_label(row, k):
    return "^".join(VARS[j] for j in range(k) if (row >> j) & 1)


def register_linear(k):
    """Register every indecomposable linear k-bit encoding as L<k>a, L<k>b, ...
    (sorted by canonical table). Returns the names."""
    names = []
    for i, (_canon, rows) in enumerate(indecomposable_linear_classes(k)):
        name = "L%d%s" % (k, "abcdefghijklmnopqrstuvwxyz"[i])
        register(name, k, linear_table(rows), ", ".join(row_label(r, k) for r in rows))
        names.append(name)
    return names


# ------------------------------------------------------------------ shapes
def pd_multisets(max_wires, min_wires=0):
    """Multisets of P/D groups at weight 0 with min_wires..max_wires wires
    (the empty multiset is included when min_wires == 0)."""
    out = []
    for d in range(0, max_wires // 2 + 1):
        for p in range(0, max_wires - 2 * d + 1):
            if p + 2 * d < min_wires:
                continue
            out.append(tuple([("P", 0)] * p + [("D", 0)] * d))
    return out


def output_shapes(inputs, kinds, phi, max_out_wires=8, count_name=None,
                  count_min=0, count_max=99):
    """Output shapes over `kinds` with phi(out) <= phi(in) - 1/2 that can hold
    every achievable input total; groups at weights w with 2**w <= max input
    value; the number of `count_name` groups must be in [count_min, count_max]."""
    V = max_value(inputs)
    need = achievable(inputs)
    budget2 = phi2(inputs, phi) - 1
    weights = [w for w in range(0, 16) if (1 << w) <= V]
    slots = [(kd, w) for w in weights for kd in kinds]
    results = []

    def rec(idx, cur, ph, wires):
        if idx == len(slots):
            if not cur:
                return
            if count_name is not None:
                c = sum(1 for g in cur if g[0] == count_name)
                if c < count_min or c > count_max:
                    return
            if need <= achievable(cur):
                results.append(tuple(cur))
            return
        kd, w = slots[idx]
        kw = ENC[kd]["k"]
        c = 0
        while ph + c * phi[kd] <= budget2 and wires + c * kw <= max_out_wires:
            rec(idx + 1, cur + [(kd, w)] * c, ph + c * phi[kd], wires + c * kw)
            c += 1

    rec(0, [], 0, 0)
    return results


def e_shapes(e, phi, max_wires=6, max_out_wires=8):
    """Shapes involving encoding e (besides P and D):
    producers: P/D inputs -> exactly one e group (+ P/D) out;
    consumers: c = 1 or 2 copies of e (+ P/D) in -> at most c copies of e out.
    Returns [(kind, inputs, outputs)] with s_max >= 0 under phi."""
    k = ENC[e]["k"]
    kinds = ("P", "D", e)
    shapes = []
    for ins in pd_multisets(max_wires, 1):
        for outs in output_shapes(ins, kinds, phi, max_out_wires, e, 1, 1):
            shapes.append(("producer", ins, outs))
    for c in (1, 2):
        rest = max_wires - c * k
        if rest < 0:
            continue
        for x in pd_multisets(rest, 0):
            ins = tuple([(e, 0)] * c) + x
            for outs in output_shapes(ins, kinds, phi, max_out_wires, e, 0, c):
                shapes.append(("consumer", ins, outs))
    return shapes


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
    UNSAT for every size 0..S  <=>  no circuit of size <= S exists.
    (Same clauses as sumcore.encode; only the value function is general.)"""
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
    out_codes = [(Y, value(outputs, list(Y))) for Y in product((0, 1), repeat=m)]
    for r in range(rows):
        bits = [(r >> i) & 1 for i in range(n)]
        vin = value(inputs, bits)
        for Y, vout in out_codes:
            if vout != vin:
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
