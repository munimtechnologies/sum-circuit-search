# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Search 4 core (stdlib only): layer-by-layer circuits for the bit adder BA^{s*}.

Goncharov, Kulikov and Levtsov (arXiv:2509.13966, open problem 1) single out
the significance vector s* = (0,0,0,0,1,1,2,2,...,k,k): four bits of weight 0
and two bits of every weight 1..k. Their circuit costs 3.5n + O(1) there, which
is exactly 4.5n - 2m; a smaller circuit for s* is needed before their bound
4.5n - 2m can be improved to 4.5n - beta*m with beta > 2.

The value s* encodes is X + Y + a + b, so the carry into each weight is 0, 1
or 2. A *layered* circuit carries it from one weight to the next on a few
wires. A *carry code* says how: k wires, word index sum(bit_i << i), and
table[index] in {0, 1, 2} or UNUSED (a word that never occurs). A *stage*
reads x_i, y_i (and, for a 2-layer stage, x_{i+1}, y_{i+1}) plus the carry
wires in code C_in, and writes s_i (s_{i+1}) plus the carry wires in C_out.

  Gates per layer of GKL's circuit: 1 (pair x_i, y_i) + 6 (MDFA') = 7.

Wires in a stage are numbered x_0, y_0, x_1, y_1, ..., then the carry wires;
outputs s_0, s_1, ..., then the carry wires.
"""
from fractions import Fraction
from itertools import permutations, product

UNUSED = 3

XOR = [0, 1, 1, 0]
OR = [0, 1, 1, 1]
AND = [0, 0, 0, 1]
FIRST_AND_NOT_SECOND = [0, 0, 1, 0]   # first and not second
SECOND_AND_NOT_FIRST = [0, 1, 0, 0]   # second and not first

DCODE = (2, (0, 2, 1, 1))   # Demenkov et al.'s pair code (p, p^q), value p + q
SUM2 = (2, (0, 1, 1, 2))    # two plain bits, value b0 + b1


# ------------------------------------------------------------ carry codes
def code_index(bits):
    idx = 0
    for i, b in enumerate(bits):
        idx |= (b & 1) << i
    return idx


def transform(table, k, perm, mask):
    """Relabel wires: new bit i = old bit perm[i] XOR bit i of mask."""
    out = [None] * (1 << k)
    for idx in range(1 << k):
        new = 0
        for i in range(k):
            new |= (((idx >> perm[i]) & 1) ^ ((mask >> i) & 1)) << i
        out[new] = table[idx]
    return tuple(out)


def orbit(table, k):
    return set(transform(table, k, perm, mask)
               for perm in permutations(range(k)) for mask in range(1 << k))


def carry_codes(k):
    """One canonical table (the smallest of its orbit) for every class of
    k-wire codes of a carry in {0, 1, 2}, under permuting and negating wires
    (both are free for a stage: B2 gates absorb input negation and outputs
    may be negated). Sorted. Returns (classes, total number of tables)."""
    seen = set()
    classes = []
    for table in product(range(4), repeat=1 << k):
        if table in seen or not {0, 1, 2} <= set(table):
            continue
        orb = orbit(table, k)
        seen |= orb
        classes.append(min(orb))
    return sorted(classes), len(seen)


def label(table):
    """2-wire classes: U<m> (one word unused; m = value of the word opposite
    it), A<v> (value v has two opposite words), J<v> (value v has two adjacent
    words). Other sizes: K<k>-<table>."""
    table = tuple(table)
    k = len(table).bit_length() - 1
    if k == 2:
        if UNUSED in table:
            u = table.index(UNUSED)
            return "U%d" % table[u ^ 3]
        for v in (0, 1, 2):
            pos = [i for i, t in enumerate(table) if t == v]
            if len(pos) == 2:
                return ("A%d" if pos[0] ^ pos[1] == 3 else "J%d") % v
    return "K%d-%s" % (k, "".join("x" if t == UNUSED else str(t) for t in table))


# ------------------------------------------------------------- relations
# A relation is (n, m, rows): rows = [(r, allowed)] where r is an input row
# (wire i = bit i of r) and allowed is the frozenset of output tuples that
# are correct on it. Rows that cannot occur (unused carry words) are absent.

def stage_relation(cin, cout, layers=1):
    kin, tin = cin
    kout, tout = cout
    n = 2 * layers + kin
    m = layers + kout
    outs = []
    for Y in product((0, 1), repeat=m):
        cv = tout[code_index(Y[layers:])]
        if cv == UNUSED:
            continue
        outs.append((Y, sum(Y[i] << i for i in range(layers)) + (cv << layers)))
    rows = []
    for r in range(1 << n):
        bits = [(r >> i) & 1 for i in range(n)]
        cv = tin[code_index(bits[2 * layers:])]
        if cv == UNUSED:
            continue
        vin = sum((bits[2 * i] + bits[2 * i + 1]) << i for i in range(layers)) + cv
        rows.append((r, frozenset(Y for Y, v in outs if v == vin)))
    return n, m, rows


def decode_relation(c):
    """Carry wires in code c -> two plain bits (weights 0 and 1)."""
    k, t = c
    outs = [(Y, Y[0] + 2 * Y[1]) for Y in product((0, 1), repeat=2)]
    rows = []
    for r in range(1 << k):
        cv = t[r]
        if cv == UNUSED:
            continue
        rows.append((r, frozenset(Y for Y, v in outs if v == cv)))
    return k, 2, rows


def sum_relation(n_in, m_out):
    """SUM: n_in plain bits -> their count in binary on m_out bits."""
    outs = [(Y, sum(Y[i] << i for i in range(m_out))) for Y in product((0, 1), repeat=m_out)]
    rows = []
    for r in range(1 << n_in):
        v = bin(r).count("1")
        rows.append((r, frozenset(Y for Y, vv in outs if vv == v)))
    return n_in, m_out, rows


def relation_from_spec(rel):
    kind = rel["kind"]
    if kind == "stage":
        cin = (int(rel["cin"][0]), tuple(rel["cin"][1]))
        cout = (int(rel["cout"][0]), tuple(rel["cout"][1]))
        return stage_relation(cin, cout, int(rel.get("layers", 1)))
    if kind == "decode":
        return decode_relation((int(rel["c"][0]), tuple(rel["c"][1])))
    if kind == "sum":
        return sum_relation(int(rel["n"]), int(rel["m"]))
    raise ValueError("unknown relation kind %r" % (kind,))


# -------------------------------------------------------------- circuits
# circuit = {"n": n, "gates": [[j, k, [f00, f01, f10, f11]], ...],
#            "outs": [[src, pol], ...]}; src = -1 is the constant 0.
# Gate g (node n + position) computes f[2*val(j) + val(k)], j < k < g.

def evaluate(circ, bits):
    vals = list(bits)
    for j, k, f in circ["gates"]:
        vals.append(f[2 * vals[j] + vals[k]])
    res = []
    for src, pol in circ["outs"]:
        x = 0 if src < 0 else vals[src]
        res.append(x ^ pol)
    return res


def check_relation(n, m, rows, circ):
    if circ["n"] != n or len(circ["outs"]) != m:
        return False
    for idx, (j, k, f) in enumerate(circ["gates"]):
        if not (0 <= j < k < n + idx) or len(f) != 4:
            return False
    for src, pol in circ["outs"]:
        if not (-1 <= src < n + len(circ["gates"])) or pol not in (0, 1):
            return False
    for r, allowed in rows:
        bits = [(r >> i) & 1 for i in range(n)]
        if tuple(evaluate(circ, bits)) not in allowed:
            return False
    return True


# ------------------------------------------------- explicit known circuits
# Full adder (Cirbo add_sum3): x1, x2, x3 -> sum, carry. 5 gates.
FULL_ADDER = {"n": 3, "gates": [
    [0, 1, XOR], [1, 2, XOR], [3, 4, OR], [2, 3, XOR], [5, 6, XOR],
], "outs": [[6, 0], [7, 0]]}

# GKL's layer: x, y, carry D = (p, p^q) -> s, carry D. Pair x, y (1 gate),
# then MDFA' (6 gates, Cirbo add_simplified_mdfa) on (x, x^y), (p, p^q).
STAGE_D = {"n": 4, "gates": [
    [0, 1, XOR],                    # 4: x ^ y
    [0, 4, OR],                     # 5: g2 = (x^y) | x
    [4, 5, XOR],                    # 6: g4 = g2 ^ (x^y)
    [2, 4, XOR],                    # 7: g5 = p ^ (x^y)
    [3, 4, XOR],                    # 8: g6 = (x^y) ^ (p^q) = s
    [3, 7, SECOND_AND_NOT_FIRST],   # 9: g7 = g5 & ~(p^q)
    [5, 9, XOR],                    # 10: g8 = g2 ^ g7
], "outs": [[8, 0], [6, 0], [10, 0]]}

# Same idea with the carry kept as two plain bits u, v (value u + v):
# full adder on x, y, u, then a half adder on (sum, v). 7 gates.
STAGE_SUM2 = {"n": 4, "gates": [
    [0, 1, XOR], [1, 2, XOR], [4, 5, OR], [2, 4, XOR], [6, 7, XOR],   # 4..8 full adder
    [3, 7, XOR],                    # 9: s = sum ^ v
    [3, 7, AND],                    # 10: second carry bit = sum & v
], "outs": [[9, 0], [8, 0], [10, 0]]}

# Layer 0 of s*: x0, y0, a, b (a, b read as a SUM2 carry) -> s0, carry D.
# Pair both, then MDFA'. 8 gates.
START_SUM2_D = {"n": 4, "gates": [
    [0, 1, XOR],                    # 4: x ^ y
    [2, 3, XOR],                    # 5: a ^ b
    [0, 4, OR],                     # 6: g2
    [4, 6, XOR],                    # 7: g4
    [2, 4, XOR],                    # 8: g5
    [4, 5, XOR],                    # 9: g6 = parity
    [5, 8, SECOND_AND_NOT_FIRST],   # 10: g7 = g5 & ~(a^b)
    [6, 10, XOR],                   # 11: g8
], "outs": [[9, 0], [7, 0], [11, 0]]}

# Carry D = (p, p^q) -> two plain bits: parity is wire 1, top bit p & ~(p^q).
DECODE_D = {"n": 2, "gates": [[0, 1, FIRST_AND_NOT_SECOND]], "outs": [[1, 0], [2, 0]]}


def stack(c1, c2):
    """Two 1-layer stages (4 inputs: x, y, two carry wires; outputs s and
    two carry wires; every output a gate or input with polarity 0) -> one
    2-layer stage with inputs x0, y0, x1, y1, carry wires."""
    for c in (c1, c2):
        if c["n"] != 4 or len(c["outs"]) != 3:
            raise ValueError("stack needs 1-layer stages with 2-wire carries")
        for src, pol in c["outs"]:
            if src < 0 or pol != 0:
                raise ValueError("stack needs plain outputs")
    gates = []

    def add(j, k, f):
        if j > k:
            j, k, f = k, j, [f[0], f[2], f[1], f[3]]
        gates.append([j, k, list(f)])

    m1 = [0, 1, 4, 5]
    base1 = 6

    def mv1(x):
        return m1[x] if x < 4 else base1 + (x - 4)
    for j, k, f in c1["gates"]:
        add(mv1(j), mv1(k), f)
    o1 = [mv1(s) for s, _p in c1["outs"]]
    m2 = [2, 3, o1[1], o1[2]]
    base2 = base1 + len(c1["gates"])

    def mv2(x):
        return m2[x] if x < 4 else base2 + (x - 4)
    for j, k, f in c2["gates"]:
        add(mv2(j), mv2(k), f)
    o2 = [mv2(s) for s, _p in c2["outs"]]
    return {"n": 6, "gates": gates, "outs": [[o1[0], 0], [o2[0], 0], [o2[1], 0], [o2[2], 0]]}


# ------------------------------------------------- s* circuits, end to end
def place(circ, input_lits, gates, n_in):
    """Append circ to a composite netlist. Literals are (node, pol); node -1
    is the constant 0. Composite gate p is node n_in + p. Returns the output
    literals of circ."""
    start = len(gates)
    n = circ["n"]

    def lit(x):
        if x < n:
            return input_lits[x]
        return (n_in + start + (x - n), 0)
    for j, k, f in circ["gates"]:
        gates.append([lit(j), lit(k), list(f)])
    outs = []
    for src, pol in circ["outs"]:
        if src < 0:
            outs.append((-1, pol))
        else:
            node, p = lit(src)
            outs.append((node, p ^ pol))
    return outs


def build_sstar(start, stages, end):
    """start: circuit for layer 0 (x0, y0, a, b -> s0, carry); stages: list of
    (circuit, layers) for the next layers; end: carry -> two plain bits.
    Inputs: x0, y0, a, b, x1, y1, x2, y2, ...; output j has weight j."""
    total = sum(l for _c, l in stages)
    n_in = 4 + 2 * total
    gates = []
    o = place(start, [(0, 0), (1, 0), (2, 0), (3, 0)], gates, n_in)
    outs = [o[0]]
    carry = o[1:]
    nxt = 4
    for circ, layers in stages:
        ins = [(nxt + i, 0) for i in range(2 * layers)] + list(carry)
        nxt += 2 * layers
        o = place(circ, ins, gates, n_in)
        outs.extend(o[:layers])
        carry = o[layers:]
    outs.extend(place(end, list(carry), gates, n_in))
    return {"n_in": n_in, "layers": total, "gates": gates, "outs": outs}


def eval_composite(comp, bits):
    vals = list(bits)

    def v(l):
        node, pol = l
        return (0 if node < 0 else vals[node]) ^ pol
    for a, b, f in comp["gates"]:
        vals.append(f[2 * v(a) + v(b)])
    return [v(l) for l in comp["outs"]]


def sstar_value(bits, layers):
    total = bits[0] + bits[1] + bits[2] + bits[3]
    for i in range(1, layers + 1):
        total += (bits[2 + 2 * i] + bits[3 + 2 * i]) << i
    return total


def verify_sstar(comp):
    """Exhaustive: the outputs are the binary digits of the s* sum."""
    n = comp["n_in"]
    for r in range(1 << n):
        bits = [(r >> i) & 1 for i in range(n)]
        y = eval_composite(comp, bits)
        if sum(b << j for j, b in enumerate(y)) != sstar_value(bits, comp["layers"]):
            return False
    return True


def composite_size(comp):
    """Gates, plus one NOT for every output that is a negated input or a
    constant (negating a gate's output is free in the full binary basis)."""
    extra = 0
    for node, pol in comp["outs"]:
        if node < 0 or (node < comp["n_in"] and pol == 1):
            extra += 1
    return len(comp["gates"]) + extra


# ------------------------------------------------------- cycle arithmetic
def min_mean_cycle(w):
    """Karp: smallest mean weight of a cycle; w[u][v] int or None (no edge).
    Returns a Fraction, or None when there is no cycle."""
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


def best_short_cycle(w, max_len=3):
    """(mean, [nodes]) of the cheapest cycle with at most max_len edges
    (shortest among equals), or None."""
    best = None
    for l in range(1, max_len + 1):
        for cyc in product(range(len(w)), repeat=l):
            cost = 0
            ok = True
            for i in range(l):
                c = w[cyc[i]][cyc[(i + 1) % l]]
                if c is None:
                    ok = False
                    break
                cost += c
            if not ok:
                continue
            mean = Fraction(cost, l)
            if best is None or mean < best[0]:
                best = (mean, list(cyc))
    return best


# -------------------------------------------------------------------- CNF
class CNF:
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


def encode_relation(n, m, rows, s, all_used=True):
    """CNF: is there a circuit of exactly s normal (f00 = 0), non-degenerate
    B2 gates, every gate read by a later gate or an output, whose outputs
    (any node or the constant 0, free negation) are allowed on every row?
    UNSAT for every size 0..S  <=>  no circuit of size <= S exists.
    Same clauses as sum-circuit-search's enccore.encode, on the listed rows."""
    e = CNF()
    e.n, e.m, e.s = n, m, s
    e.rows = [r for r, _a in rows]
    gates = list(range(n, n + s))

    def node_val_lit(node, r):
        if node < n:
            return (r >> node) & 1, None
        return None, e.t[node, r]

    for g in gates:
        for r in e.rows:
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
        for r in e.rows:
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
        for r in e.rows:
            e.y[o, r] = e.var()
    for o in range(m):
        pol = e.pol[o]
        for r in e.rows:
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
    all_y = list(product((0, 1), repeat=m))
    for r, allowed in rows:
        for Y in all_y:
            if Y not in allowed:
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
    for r in e.rows:
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
