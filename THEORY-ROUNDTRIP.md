# The round-trip barrier: a SAT-free proof of the 7-gates-per-weight law for layered s* circuits

Part of [sum-circuit-search](README.md), an open project by MV2 of Munim, Inc.
(mv2@munimtech.com). Made with AI agents working in MV2's name; no human has
checked this yet. Licence: Apache-2.0. Written 2026-11-18 (~17:30 UTC). That is
after prediction H1 was registered ([SEARCH4-ADDENDUM.md](SEARCH4-ADDENDUM.md),
2026-11-17 ~20:00 UTC) and **before any result of search 4 exists**.
`roundtrip.py` checks every number below; `test_roundtrip.py` is its stdlib
test. Job `sum4-sandwich-v1` runs both and re-proves the one outside fact the
proof uses (size(SUM_4) = 9) with a SAT solver. It has not run yet.

## Setting

As in [THEORY-SSTAR.md](THEORY-SSTAR.md): s* = X + Y + a + b is the instance
that Goncharov, Kulikov and Levtsov (arXiv:2509.13966, STACS 2026) single out in
their open problem 1. Their circuit uses 7 gates per weight. A *layered* circuit
has one layer per weight. Layer i reads x_i, y_i and the carry wires at cut i,
and writes s_i and the carry wires at cut i+1. The first layer reads x_0, y_0
and the plain bits a, b (code A1). A final decoder turns the last carry into two
output bits. By the cut argument (THEORY-SSTAR.md, section 1), the words at each
cut form a *carry code* C_i: a table from words to carries in {0, 1, 2}.

For a code C (any number of wires), define

- **pack(C)**: the fewest gates that turn two plain bits u, v into a word of C
  with value u + v;
- **dec(C)**: the fewest gates that turn a word of C into its value in binary
  (two bits c0 + 2 c1);
- **rt(C) = pack(C) + dec(C)**, the round-trip cost.

Packing and then decoding computes (u XOR v, u AND v), which needs 2 gates.
So rt(C) >= 2 for every code.

## The sandwich lemma

**Lemma 1.** For every layer that maps code A to code B,

    pack(A) + cost(A -> B) + dec(B) >= size(SUM_4) = 9.

*Proof.* Feed u, v into a minimum pack circuit for A. Feed its word and x, y
into the layer, and feed the layer's carry word into a minimum decoder for B.
On every input, the layer sees a word of A with value u + v, so it outputs
s = (x + y + u + v) mod 2 and a word of B with value (x + y + u + v) div 2,
which the decoder writes in binary. The three outputs are therefore the binary
digits of x + y + u + v. That is SUM_4, so the combined circuit has at least
size(SUM_4) gates. Negated wires cost nothing: a negated input of a gate is
absorbed into its truth table, and no output of SUM_4 is a negated input. []

size(SUM_4) = 9 is listed in the table of small exact SUM sizes of Kulikov,
Pechenev and Slezkin (SAT-based circuit local improvement, MFCS 2022,
arXiv:2102.12579). We read this through a search-engine extract of that paper;
we could not open the PDF text ourselves. Knuth computed the exact circuit size
of every 4-input function (TAOCP 4A, section 7.1.2). Because the whole result
rests on this number, job `sum4-sandwich-v1` proves it again: the repository's
SAT encoder must find no circuit with 0 to 8 gates and a checked 9-gate one.
(*Correction:* the README calls arXiv:2102.12579 "Kulikov and Slezkin"; the
arXiv page lists three authors, Kulikov, Pechenev and Slezkin.)

## The round-trip theorem

**Theorem 2.** Every layered circuit for s* with L layers and cut codes
C_0 = A1, C_1, ..., C_L, final decoder included, has at least

    9L - (rt(C_1) + rt(C_2) + ... + rt(C_{L-1}))

gates. This holds for any number of carry wires at every cut.

*Proof.* Layer i costs at least 9 - pack(C_i) - dec(C_{i+1}) by Lemma 1, and
the decoder at least dec(C_L). Add these up. pack(A1) = 0, each inner cut
contributes pack(C_i) + dec(C_i) = rt(C_i), and dec(C_L) cancels. []

**Corollary 3 (the conservation law, proved for round-trip-2 codes).** If every
inner cut carries a code with rt = 2, the circuit has at least 7L + 2 gates.
Our chains of hand-built layers have exactly 7L + 2 gates (verify_layers.py),
so **7L + 2 is the exact optimum among such circuits**. With n = 2L + 2 inputs
this is 3.5n - 5, GKL's rate. In the potential form of THEORY-SSTAR.md,
phi(C) = pack(C) and cost(A -> B) >= 7 + phi(B) - phi(A).

For the nine pairs among {A1, J1, U0}, Lemma 1 gives exactly
7 + phi(out) - phi(in). Our hand layers meet it, so **H1 now follows from
Lemma 1 plus size(SUM_4) = 9**. That proof came after H1 was registered and
before search 4 reported anything. Search 4 still tests H1 independently. If
it ever finds one of those nine entries below the formula, then either
size(SUM_4) < 9 or something is broken, and we will say which.

## All nine 2-wire classes

Computed by brute force over every circuit with at most 2 gates on 2 inputs
(2 always suffice). Each class gives the same values on all its tables, and
the code checks this.

| class | meaning | pack | dec | rt |
|---|---|---|---|---|
| A1 | two plain bits | 0 | 2 | 2 |
| J1 | pair code (p, p^q) | 1 | 1 | 2 |
| U0 | binary (C mod 2, [C = 2]) | 2 | 0 | 2 |
| U1, U2, J2 | | 2 | 1 | 3 |
| A0, A2, J0 | | 2 | 2 | 4 |

So for layered circuits with **2-wire** carries:

- using only A1, J1 and U0: at least 7 gates per weight, matched exactly
  (Corollary 3);
- never using A0, A2 or J0: at least 6 per weight (minimum mean cycle of
  9 - pack - dec on the six classes with rt <= 3);
- in general: at least 5 per weight. This is no better than the known 2.5n
  (Red'kin's adder bound), so the classes with rt >= 3 are where any sub-3.5n
  layered circuit must live.

More precisely, a layered circuit with at most (7 - e)L gates needs
(rt(C_1) - 2) + ... + (rt(C_{L-1}) - 2) >= eL + 2. Its codes must waste
packing or unpacking work at a linear number of cuts, and still come out ahead.
Search 4's table decides whether that can happen with 2 wires.

Codes with more wires are covered whenever rt = 2. For example, the 3-wire code
(u, v, u XOR v) has pack 1 and dec 1, so no layered circuit that uses it
everywhere beats 7 per weight.

## Next: the two-layer sandwich (long shot, registered before running)

Let F2 be the 2-layer block of s*: u + v + x_0 + y_0 + 2(x_1 + y_1) in
binary (6 inputs, 4 outputs). Layers A1 -> J1 -> U0 give a 16-gate circuit. If
size(F2) = 16, the same sandwich gives
cost(A -> B) + cost(B -> C) >= 16 - pack(A) - dec(C) **whatever code B sits in
between**. That removes the round-trip condition at every other cut. The job
tries sizes 0, 1, 2, ... of F2 with 15 minutes each and stops at the first
size it cannot decide. Predictions, frozen now:

- **R0 (check):** SUM_2 = 2 and SUM_3 = 5 are reproduced, and size(SUM_4) = 9
  is certified (no circuit with 0 to 8 gates). Known; if it fails, the encoder
  is wrong.
- **R1.** F2 is decided UNSAT for every size up to at least 12 (55%).
- **R2.** The job proves size(F2) = 16, meaning UNSAT up to 15 (15%).
- **R3.** F2 has no circuit with 15 gates or fewer (80%). The job may leave
  this undecided.

## What this does and does not show

- It is a lower bound for a restricted class: layered circuits whose cut codes
  have round-trip cost 2. Circuits that mix weights, and codes with rt >= 3,
  are not covered. The unconditional lower bound for s* stays at about 2.5n.
- It needs no SAT search beyond the single fact size(SUM_4) = 9.
- The argument is elementary. We have not seen it applied to GKL's problem,
  but we have not checked every paper that cites them.
- It explains the "conservation law" that THEORY-SSTAR.md observed: every
  layer pays for a full SUM_4 except what the codes on its two sides save it.
  A cheap code on one side has to be paid for on the other.
