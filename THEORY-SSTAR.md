# Layered circuits for s*: the cut argument, pass-through layers, and a conservation law

Part of [sum-circuit-search](README.md), an open project by MV2 of Munim, Inc.
(mv2@munimtech.com). Made with AI agents working in MV2's name; no human has
checked this yet. Licence: Apache-2.0. Written 2026-11-17 (~20:00 UTC), after
search 4 ([SEARCH4.md](SEARCH4.md)) was filed and **before any of its results
exist**. Every circuit below is checked exhaustively by `verify_layers.py`. That
check is queued as job `sstar-hand-layers-v1` and has not run yet.

## Setting

s* = (0,0,0,0,1,1,2,2,...,k,k) is the bit-addition instance that Goncharov,
Kulikov and Levtsov (arXiv:2509.13966, STACS 2026, open problem 1) single out.
It computes X + Y + a + b. Their circuit uses 7 gates per weight (3.5n). Any
circuit below 3.5n - O(1) would be the first step past their bound 4.5n - 2m
on that instance. A lower bound of 3.5n - O(1) would prove alpha = 2.

The carry C into each weight is 0, 1 or 2. A *layered* circuit has one layer
per weight. Layer i reads x_i, y_i and two carry wires, and writes s_i and two
carry wires. Layer 0 reads x_0, y_0 and the bits a, b, which we treat as a
carry in code A1. Three 2-wire codes matter below, written as
table[w1 + 2*w2]:

| code | words (w1,w2) -> C | meaning |
|---|---|---|
| A1 | 00->0, 10->1, 01->1, 11->2 | two plain bits, C = w1 + w2 |
| J1 | 00->0, 10->2, 01->1, 11->1 | Demenkov et al.'s pair code (p, p^q), C = p + q |
| U0 | 00->0, 10->1, 01->2, 11 unused | binary: w1 = C mod 2, w2 = [C = 2] |

## 1. The cut argument, in full

**Theorem L.** Let mu* be the minimum mean cycle of the 9 x 9 matrix
cost(C -> C'): the fewest gates in one layer from 2-wire code class C to class
C'. Then every layered circuit with 2-wire carries for s* with L layers has at
least mu* (L - 8) gates.

*Proof.*
1. *Each cut carries a code.* Suppose one word at cut i occurred both with
   carry c and with carry c' != c. Set every higher input to 0. All higher
   outputs are then a function of that word, but they must spell c in one case
   and c' in the other. So words determine carries.
2. *Every combination occurs.* Carries 0, 1 and 2 all occur at every cut:
   take all lower inputs 0, then a = 1, then everything below 1. They do not
   depend on x_i, y_i. So layer i must be correct on every (occurring word,
   x_i, y_i). At least 3 words occur, so the table is one of the 60 tables
   that fall into the 9 classes of SEARCH4.md.
3. *Only classes matter.* Permuting the carry wires is a relabelling.
   Negating one is absorbed: a two-input gate with a negated input is again a
   two-input gate. A negated output of a gate g is absorbed by flipping g's
   truth table and letting every reader of g absorb the flip. A carry wire
   passed straight through (section 2) just has its negation absorbed one
   layer later. So the layers' gates add up to at least the sum of
   cost(C_i -> C_{i+1}) along the circuit's sequence of classes.
4. *Walks.* That sequence is a walk of L edges in a 9-vertex graph. A walk
   splits into cycles, each of mean at least mu*, plus a simple path of at
   most 8 edges, whose weight is at least 0. The sum is at least mu* (L - 8).

The SAT encoding in `stagecore.encode_relation` lets an output be any node,
including an input wire, with free negation. So it covers pass-through layers,
and its exact entries are the costs this proof needs. Two caveats remain. A
timeout is not a proof: the proved bound uses (largest size ruled out) + 1 for
an undecided entry. And the theorem says nothing about circuits that are not
layered.

**Certificate form.** By LP duality, mu* >= 7 holds if and only if there are
numbers phi(C), one per class, with cost(C -> C') >= 7 + phi(C') - phi(C) for
all 81 pairs. Such a phi is a short certificate that a reader can check
against the published table by hand.

## 2. Pass-through layers

**Lemma P.** A layer can pass an input carry wire w straight through as an
output carry wire only if w = [C = 2] exactly. Among the 9 classes, that
happens only for U0, U1 and J2. The output code is then A1 or J1.

*Proof.* Given C = 0 or 1, the next carry C' ranges over {0, 1}. Given C = 2,
it ranges over {1, 2}. The other output wire must tell apart every C'
reachable for each value of w. So one value of w may only occur with C = 2 and
the other only with C in {0, 1}. In A0, A1, J0 and J1, value 2 has one word and
the other three words are used. A wire splits the 4 words 2 + 2, so it cannot
isolate one word. In U2 and A2, the value-2 word(s) cannot be cut off by one
wire. That leaves U0, U1 and J2. Given w, both values of the second wire occur
for both values of w, so 4 words are used and value 1 has two words. That is
class A1 or J1.

The simplest case: from U0 = (D, E), with C = D + 2E,

    x + y + D + 2E = s + 2 * (maj(x, y, D) + E),

so **a full adder on (x, y, D) with E passed through is a complete layer
U0 -> A1 (5 gates)**. Pass-through cannot happen in two layers in a row: after
a U0 -> A1 or U0 -> J1 layer, the code is A1 or J1, which do not allow it.

## 3. Nine hand-built layers and one pattern

Let phi(C) be the number of gates needed to pack two plain bits u, v into code
C: phi(A1) = 0, phi(J1) = 1 (one XOR gives (u, u^v)), phi(U0) = 2 (a half
adder gives (u^v, u&v)). Every one of the nine layers we could build has exactly
7 + phi(out) - phi(in) gates:

| layer | gates | construction |
|---|---|---|
| A1 -> A1 | 7 | full adder (x, y, u), half adder (sum, v) |
| A1 -> J1 | 8 | pair (u, v), then GKL's layer (pair x, y + MDFA') |
| A1 -> U0 | 9 | full adder, half adder, half adder on the two carries |
| J1 -> A1 | 6 | *ours:* e = p AND NOT r (that is [C = 2]); full adder (x, y, r); carry (maj, e) |
| J1 -> J1 | 7 | GKL's layer |
| J1 -> U0 | 8 | GKL's layer, then e' = p' AND NOT r' |
| U0 -> A1 | 5 | *ours:* full adder (x, y, D); E passes through |
| U0 -> J1 | 6 | *ours:* as U0 -> A1, plus maj XOR E; carry (E, maj^E) |
| U0 -> U0 | 7 | *ours:* p = x^y, g = x&y, s = p^D, t = p&D, E' = E&g, D' = g ^ (t ^ E) |

The U0 -> U0 layer is correct because g AND t = 0 (g = 1 forces p = 0) and E = 1
forces D = 0. Then D' = maj(x, y, D) XOR E and E' = E AND g. The decoders from
A1, J1 and U0 to two plain output bits cost 2, 1 and 0 = 2 - phi. So **every
chain of these layers, from (a, b) through L layers to the output, has exactly
7L + 2 gates**: the codes move work between layers but never save any.
`verify_layers.py` checks all 363 chains with 1 to 5 layers exhaustively.

**Conjecture (the conservation law).** For C, C' in {A1, J1, U0}, these nine
costs are exact: cost(C -> C') = 7 + phi(C') - phi(C). More strongly, phi
extends to all 9 classes with cost(C -> C') >= 7 + phi(C') - phi(C) everywhere.
That would make mu* = 7 with a 9-number certificate. In words: in a layered
circuit for s*, every weight costs 7 gates of real work, and carry codes only
decide when that work is paid.

Search 4's table will test the first statement directly. It is registered as
prediction H1 in [SEARCH4-ADDENDUM.md](SEARCH4-ADDENDUM.md), before any result.

## What this does and does not show

- Nothing here beats 3.5n, and nothing here is a lower bound yet. The
  hand-built layers are upper bounds; their optimality is what the SAT ladder
  in search 4 decides.
- Already known before the results: search 4's pre-registered P5 ("the smallest
  entry of the whole 9 x 9 matrix is 7") will fail, because U0 -> A1 costs at
  most 5. P5 was a guess about cheap transitions, so this does not touch P1
  (mu* = 7).
- If the conservation law holds on all 81 entries, the result is a clean
  partial answer to GKL's open problem 1. No circuit that passes carries
  weight by weight on two wires beats their 3.5n on s*. A better circuit would
  have to carry three or more wires across some cut, or mix weights.
- The unconditional lower bound for s* stays at about 2.5n. Set a = b = 0 to
  get two-number addition, which needs 5(k+1) - 3 gates (Red'kin 1981, as
  cited by GKL).
