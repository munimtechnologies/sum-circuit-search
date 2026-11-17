# Theory: when does a cheaper block beat 4.5n?

Part of [sum-circuit-search](README.md), an open search by MV2 of Munim, Inc.
(mv2@munimtech.com). Made with AI agents working in MV2's name. No human has
checked these proofs yet. Licence: Apache-2.0. Written 2026-11-17 (~16:30-17:30
UTC), before any of the three searches had returned a result.

The searches ask a SAT solver whether small building blocks can be cheaper than
their *potential drop*. This note proves what such a block would buy, and what it
would not. It also corrects one sentence in the README.

## Setting

A **group** is a plain bit **P** (value b) or a pair **D** stored as
(p, p XOR q) with value p + q. A group at weight w counts value * 2^w. A **block**
is a circuit of two-input gates from input groups to output groups. On every
input it keeps the weighted sum, and a D output may use either code for value 1.
Potentials: phi(P) = 9/2 and phi(D) = 8 at every weight. For a block B,

    drop(B)  = phi(inputs) - phi(outputs)
    slack(B) = drop(B) - size(B)

The known blocks (gate by gate in `known_blocks.py`) have these slacks:

| block | shape | size | drop | slack |
|---|---|---|---|---|
| pairing XOR | P + P -> D | 1 | 1 | 0 |
| MDFA (Demenkov et al. 2010) | P + D + D -> P@0 + D@1 | 8 | 8 | 0 |
| full adder | P + P + P -> P@0 + P@1 | 5 | 9/2 | -1/2 |
| Stockmeyer | P + D -> P@0 + P@1 | 4 | 7/2 | -1/2 |
| MDFA' | D + D -> P@0 + D@1 | 6 | 7/2 | -5/2 |
| unpair | D -> P@0 + P@1 | 1 | -1 | -2 |

(The last one: the parity of a D is its second wire, and the carry is
p AND NOT(p XOR q), which is one gate.) A block is **profitable** if slack > 0.
A **composition** for SUM_n starts from n groups P@0. It applies blocks to live
groups, each group being consumed at most once. It ends when the live groups are
plain bits at distinct weights; these are the binary digits of the sum.

## Lemma 1 (exact accounting)

For every composition C of blocks B_1, ..., B_k computing SUM_n,

    size(C) = 9n/2 - phi(final groups) - (slack(B_1) + ... + slack(B_k)).

*Proof.* size(C) = sum of size(B_i) = sum of (drop(B_i) - slack(B_i)). Every
group other than the n inputs and the final outputs is produced by exactly one
block and consumed by exactly one, so the drops telescope to
phi(start) - phi(final) = 9n/2 - phi(final). QED.

The final groups are at most floor(log2 n) + 1 plain bits, so
phi(final) <= (9/2)(log2 n + 1).

## Lemma 2 (barrier)

If every block in a family has slack <= 0, every composition from that family
has size >= 9n/2 - (9/2)(log2 n + 1). This is Lemma 1 with all slacks <= 0. The
potentials do not depend on the weight, so this holds for blocks that read any
number of columns.

## Lemma 3 (construction)

Lemma 2 says a profitable block is *needed* to beat 4.5n. The README said a
profitable block is also *enough*. That is true for blocks that read one column,
but not in general. Plain bits above column 0 are scarce: in the 4.5n
construction, column w >= 1 holds only D carries and a single chain bit. The
cheapest known way to make one extra plain weight-1 bit is a full adder on three
column-0 bits (slack -1/2). The precise statement:

**Lemma 3.** Let B have base column b (its lowest input weight), with every input
at weight b or b+1. Let p0 and d0 be its P and D inputs at b, d1 its D inputs at
b+1, k1 its P inputs at b+1, and k1' its P outputs at b+1. Put

    delta = max(0, k1 - k1')
    R     = 4*d1 + 2*delta + p0 + 2*d0
    gain  = slack(B) - delta/2

If gain > 0, then size(SUM_n) <= (9/2 - gain/R) n + O(log n).

*Proof.* Shift so that b = 0. Choose m = floor((n - c)/R) copies of B, for a
constant c that covers the start-up bits below. Build the circuit in stages; each
stage reads only earlier stages, so the result is acyclic.

1. *Carries for B.* Take 4*d1*m + 1 input bits, pair them (pairing XOR, slack 0),
   and run an MDFA chain over the pairs: one bit starts the chain, and each MDFA
   eats two D@0 and emits one D@1 (slack 0). This makes d1*m groups D@1. The
   chain's last P@0 goes back to the pool of live column-0 bits.
2. *Plain weight-1 bits for B.* Make delta*m + k1 bits P@1 with full adders on
   fresh input bits. Each full adder eats three P@0, emits one P@1 and returns
   one P@0 to the pool (slack -1/2 each).
3. *The copies.* Run the m copies of B one after another. Copy j takes its P@0
   inputs from the pool, its D@0 inputs by pairing pool bits (slack 0), its D@1
   inputs from stage 1, and its P@1 inputs first from earlier copies' P@1
   outputs, then from stage 2. Copy 1 needs k1 bits from stage 2. Every later
   copy needs at most delta more, so stage 2 has enough.
4. *Rest of column 0.* All live column-0 groups (unused input bits, the pool,
   and every weight-0 output of the earlier stages) are handled as in stage 5
   with w = 0: pair the plain bits, then run an MDFA chain
   (slack 0 each), with O(1) clean-up at the end.
5. *Columns w = 1, 2, ...* Pair the plain bits at weight w (slack 0), leaving at
   most one. Start an MDFA chain with that bit, or with one MDFA' if there is
   none (slack -5/2). Chain MDFAs (slack 0) until at most one D is left, then
   finish with one Stockmeyer block if a D is left (slack -1/2), or with unpair
   if a lone D has no chain bit (slack -2). Each column ends with one plain
   output bit and sends at most O(1) extra groups up. These steps lose only
   O(1) slack per column, and there are O(log n) columns.

Stages 1-3 use at most m*R + c of the n input bits: 4*d1 per copy in stage 1,
2*delta per copy net in stage 2, and p0 + 2*d0 per copy in stage 3. The pool is
refilled by returned bits, so this count is generous. By Lemma 1 the total slack
is at least m*slack(B) - (delta*m + k1)/2 - O(log n), and so

    size(SUM_n) <= 9n/2 - m*gain + O(log n) = (9/2 - gain/R) n + O(log n). QED.

The bound is a guarantee, not the best rate. B is used only at column 0, at a
limited density. A 7-gate MDFA, for example, gives gain/R = 1/5 here, whereas
using it in every column would give 4.0n.

**Corollary (one column).** If B reads one column (k1 = d1 = 0, so delta = 0),
any profitable B gives size(SUM_n) <= (9/2 - slack(B)/(p0 + 2*d0)) n + O(log n).
For blocks with at most 6 input wires the improvement is at least 1/12.

## What this means for the three searches (stated before any result)

- **Search 1 (one column).** Any profitable block it finds would beat 4.5n by
  the corollary.
- **Search 3 (two columns).** A profitable block with delta = 0 beats 4.5n. One
  with delta >= 1 does so only if slack(B) > delta/2. Its slack is at least 1/2,
  so the doubtful cases are delta = 1 with slack 1/2, and delta = 2 with slack
  1/2 or 1, and so on. When search 3 is graded, each profitable block is
  reported with its delta and Lemma 3's gain/R from `lemma.py`, next to the
  frozen predictions (which stay as written).
- **Long shot 1** (P@0 + D@0 + D@0 + P@1 + D@1 -> P@0 + P@1 + D@2) has delta = 0.
  A 15-gate circuit would give gamma <= 9/2 - 1/9, about 4.389.
- **Long shot 2** (P@0 + D@0 + D@0 + 3 P@1 -> P@0 + P@1 + D@2) has delta = 2.
  The 16-gate circuit the job asks for would have gain 1 - 1 = 0, so by itself it
  would NOT beat 4.5n under Lemma 3. Only 15 gates (gain 1, about 4.389) would.
  A 16-gate hit would still be worth reporting, because it would also beat 4.5n
  if a slack-0 source of plain weight-1 bits exists.
- **Open supply question.** Is there any block with slack 0 that emits a plain
  bit at weight 1 (for example P + D + D -> P@0 + P@1 + P@1 in 7 gates, or
  P + P + P + D -> P@0 + P@1 + P@1 in 8)? Every one we know has slack <= -1/2
  per such bit. If one exists, delta drops out of Lemma 3. A small SAT search at
  size = drop for each such shape would settle it for up to 6 input wires. It
  will be run if search 3 turns up a block where it matters.

## Correction to the README

The README says: "Conversely, a profitable block means the LP over block
compositions has value below 4.5." That holds for blocks that read one column
(the corollary above). For blocks that read two columns, the precise condition
is Lemma 3's gain > 0. The README now links here.

## Files

- `lemma.py`: Lemma 3 as exact arithmetic (stdlib `fractions`)
- `test_lemma.py`: tests with every expected value worked out by hand
