# The block sandwich: why 4.5n is tight for small one-column blocks, and the one number that decides 6-input blocks

Part of [sum-circuit-search](README.md), an open project by MV2 of Munim, Inc.
(mv2@munimtech.com). Made with AI agents working in MV2's name; no human has
checked this yet. Licence: Apache-2.0. Written 2026-11-19 (~12:30 UTC). That is
after searches 1-4 were registered and **before any of them has returned a
result**, and before job `sum56-exact-v1` (below) has run.
`blocks_sandwich.py` checks every number here by exhaustive truth tables;
`test_blocks_sandwich.py` is its stdlib test.

## Summary

[THEORY-ROUNDTRIP.md](THEORY-ROUNDTRIP.md) used one trick for the bit-addition
instance s*: wrap a layer in a cheap packer and a cheap decoder, and the
result computes a small SUM whose exact size is known. Here the same trick is
applied to the main question, SUM_n below 4.5n, and to the P/D blocks that
searches 1 and 3 test.

1. **Every known block meets the sandwich bound with equality.** These are the
   full adder, Stockmeyer's block, MDFA, MDFA', the pairing XOR and unpair.
   Each one, wrapped this way, is an optimal circuit for SUM_2, SUM_3, SUM_4 or
   SUM_5.
2. **No "reduced" one-column block with at most 5 input wires is profitable.**
   A reduced block outputs one plain bit at weight 0 and one carry group at
   weight 1. This follows from size(SUM_k) = 2, 5, 9, 11 for k = 2..5 alone, with
   no new search. MDFA (slack 0) is as good as such a block can be. The
   lower-bound parts of search 1's frozen check C1 (full adder >= 5) and
   predictions P1 (MDFA shape >= 8), P2 (Stockmeyer shape >= 4) and P3 (MDFA'
   shape >= 6) follow from the same four numbers. We found this after they were
   registered and before search 1 returned anything.
3. **For 6 input wires, the whole reduced one-column case comes down to one
   open number.** Some reduced block on 6 units is profitable *if and only if*
   size(SUM_6) <= 13. The best published upper bound is 16, and the exact value
   is open. For 7 units, profitable needs size(SUM_7) <= 18 (best known 19),
   and size(SUM_7) <= 17 would be enough.
4. In this setting, the pair code buys nothing over plain bits. Whether any
   reduced one-column block of this size beats 4.5n is the same question as
   whether a plain SUM_6 circuit with 13 gates exists.

## Setting

As in [THEORY.md](THEORY.md): a group is a plain bit **P** (potential 9/2) or a
pair **D** = (p, p XOR q) with value p + q (potential 8). For value 1 either
code is allowed. A block keeps the weighted sum. Its slack is
phi(in) - phi(out) - size, and it is **profitable** if slack > 0. Lemma 2 of
THEORY.md says that if no block in a family is profitable, every composition
from it needs 4.5n - O(log n) gates. Slacks are multiples of 1/2.

Write S_k = size(SUM_k) over all two-input gates. S_2 = 2, S_3 = 5, S_4 = 9 and
S_5 = 11 are exact: Knuth found the exact size of every function of up to 5
inputs (TAOCP 4A, 7.1.2), and these values are in the table of Kulikov,
Pechenev and Slezkin (MFCS 2022, arXiv:2102.12579). That table gives only upper
bounds from k = 6 on: S_6 <= 16, S_7 <= 19, S_9 <= 27. Cirbo (arXiv:2412.14933)
lists S_11 <= 34 and S_15 <= 51. We read both tables through search-engine
extracts. Jobs `sum4-sandwich-v1` and `sum56-exact-v1` re-prove S_4 and S_5
with our own SAT encoder.

## The block sandwich

**Lemma 1.** Let B be a block whose inputs hold k bits' worth of units: one
per P and two per D, across any columns. Let W be the function that maps k
plain bits, placed at the input weights, to the binary digits of their
weighted sum. Then

    size(B) >= size(W) - (number of D inputs) - DEC(out),

where DEC(out) is the size of any circuit that turns B's output groups into
the binary digits of their total.

*Proof.* Pair two fresh bits u, v into (u, u XOR v) for each D input, which is
1 gate each. Feed everything into B, then into the decoder. On every input B
sees words whose total is the weighted sum of the k bits, so the decoder writes
that sum in binary. This is a circuit for W. Free negations are absorbed as in
THEORY-ROUNDTRIP.md. []

The potentials make this neat. phi(P) + 0 = 9/2 and phi(D) + 1 = 9 = 2 * 9/2,
so phi(in) + (number of D inputs) = 9k/2 for any mix of P and D. Hence

    slack(B) <= 9k/2 - size(W) - phi(out) + DEC(out).        (*)

For a one-column block, W = SUM_k. Only the output side depends on the shape.

## 1. Every known block is tight

| block | shape | k | sandwich gates | = S_k | slack | bound (*) |
|---|---|---|---|---|---|---|
| pairing XOR | P + P -> D | 2 | 0 + 1 + 1 | 2 | 0 | 0 |
| unpair | D -> P@0 + P@1 | 2 | 1 + 1 + 0 | 2 | -2 | -2 |
| full adder | P + P + P -> P@0 + P@1 | 3 | 0 + 5 + 0 | 5 | -1/2 | -1/2 |
| Stockmeyer | P + D -> P@0 + P@1 | 3 | 1 + 4 + 0 | 5 | -1/2 | -1/2 |
| MDFA' | D + D -> P@0 + D@1 | 4 | 2 + 6 + 1 | 9 | -5/2 | -5/2 |
| MDFA | P + D + D -> P@0 + D@1 | 5 | 2 + 8 + 1 | 11 | 0 | 0 |

"Sandwich gates" = pairing XORs + block + unpairs (1 gate per D output:
parity r, carry p AND NOT r). `blocks_sandwich.py` runs every sandwich on all
2^k inputs and checks that it outputs the binary digits of the sum. So each
known block is exactly an optimal SUM_k circuit, minus its cheap glue. The
4.5n construction pays (S_5 - 2)/2 = 9/2 gates per eliminated bit: an 11-gate
SUM_5 minus one round trip through the pair code.

## 2. Reduced one-column blocks

Call a one-column block on k units **reduced** if its outputs are one plain bit
P@0 plus one carry representation R at weight 1 from this list. R must be able
to hold k div 2. Each R has an explicit decoder to binary, checked exhaustively:

| R | holds up to | phi(R) | decoder | DEC(R) | phi(R) - DEC(R) |
|---|---|---|---|---|---|
| P | 1 | 9/2 | none | 0 | 9/2 |
| D | 2 | 8 | unpair | 1 | 7 |
| P + P | 2 | 9 | half adder | 2 | 7 |
| P + P@1 (binary) | 3 | 9 | none | 0 | 9 |
| P + D | 3 | 25/2 | Stockmeyer | 4 | 17/2 |
| P + P + P | 3 | 27/2 | full adder | 5 | 17/2 |

By (*), every reduced block on k units has slack <= c_k - S_k, with
c_k = 9k/2 - 9/2 - min(phi(R) - DEC(R)) over the allowed R:

| k | c_k | S_k | largest slack | profitable needs |
|---|---|---|---|---|
| 2 | 0 | 2 | -2 | impossible |
| 3 | 9/2 | 5 | -1/2 | impossible |
| 4 | 13/2 | 9 | -5/2 | impossible |
| 5 | 11 | 11 | **0** | impossible |
| 6 | 14 | open, <= 16 | 14 - S_6 | **S_6 <= 13** |
| 7 | 37/2 | open, <= 19 | 37/2 - S_7 | **S_7 <= 18** |

**Theorem 2.** No reduced one-column block on at most 5 units, with any mix of
P and D inputs, is profitable. Equality (slack 0) needs k = 5 with R = D or
P + P. MDFA is one; whether a 7-gate P + D + D -> P@0 + P@1 + P@1 block exists is
the "supply question" of THEORY.md, and (*) allows it but does not decide it.

**Theorem 3.** A profitable reduced one-column block on 6 units exists if and
only if S_6 <= 13.

*Proof.* "Only if" is the table. "If": the plain SUM_6 circuit, read as a block
6 P@0 -> P@0 + P@1 + P@2 (R = P + P@1), has slack 27/2 - S_6 >= 1/2. []

For 7 units, S_7 <= 17 makes the plain SUM_7 block profitable (slack
18 - S_7). S_7 = 18 is the one value where only a block with R = P + D or
P + P + P and a tight sandwich could be profitable. With S_7 = 19 nothing on 7
units is.

By THEORY.md's corollary, a profitable one-column block with slack sigma on k
units gives size(SUM_n) <= (9/2 - sigma/k)n + O(log n). So S_6 = 13 would give
about 4.417n.

## The plain SUM_k test, for reference

A plain SUM_k circuit, used as a block, has slack 9/2 (k - bitlen(k)) - S_k.
So it beats 4.5n exactly when S_k is below:

| k | 5 | 6 | 7 | 9 | 11 | 15 |
|---|---|---|---|---|---|---|
| profitable if S_k <= | 8 | 13 | 17 | 22 | 31 | 49 |
| best known S_k | 11 (exact) | 16 | 19 | 27 | 34 | 51 |

This direction is not new: Kulikov, Pechenev and Slezkin already note that
their circuits for n <= 15 do not improve 4.5n. What the sandwich adds is the
converse for reduced one-column blocks (Theorems 2 and 3). Within that family,
storing bits as pairs cannot beat what the plain SUM_k circuit already gives.

## What is left for beating 4.5n with P/D blocks

- One-column blocks whose outputs are not reduced, for example several groups at
  weight 0 or a D at weight 0. Here (*) still applies, but our decoders lose
  more and the bound can be positive. Search 1's SAT runs decide these shapes.
- Blocks that read two columns (search 3). Lemma 1 holds with W the two-column
  weighted sum, whose exact sizes we have not computed.
- New codes (search 2), and blocks on 6 or 7 units if S_6 <= 13 or S_7 <= 18.

## Job sum56-exact-v1 (registered now, before it runs)

1 CPU, 1 GB. Every SAT call asks for a circuit with **at most** s gates
(unused gates allowed, so a smaller circuit can be padded). An UNSAT answer at
s is then a lower bound of s + 1 by itself. A timeout is not a proof.

- **Q0 (check):** SUM_2 and SUM_3 come out as 2 and 5 (known; otherwise the
  encoder is wrong). S_5 = 11 is certified: SAT at 11 and UNSAT at 10 within
  90 minutes (80%).
- **Q1 (check):** a SUM_6 circuit with at most 16 gates is found within 20
  minutes (85%).
- **Q2:** no SUM_6 circuit with at most 13 gates exists (95%). The job decides
  this within its 90-minute limit (20%).
- **Q3:** a SUM_6 circuit with at most 15 gates exists (15%); with at most 14
  (5%). Either would improve the 16 in the 2022 table. We have not seen a later
  value for n = 6.

If Q2 is decided UNSAT, Theorem 3 closes every reduced one-column block on 6
units. If it is SAT, the circuit is re-checked by hand, and by Theorem 3 it
gives size(SUM_n) <= (9/2 - 1/12)n + O(log n). Then nothing is claimed until a
human has checked it.

## Limits

- This is a barrier for a restricted family: reduced one-column P/D blocks,
  with decoders from the list above. Other output shapes, other codes and
  multi-column blocks are not covered. The unconditional lower bound for
  SUM_n stays at 2.5n.
- It rests on S_2..S_5, which are classical, and on the explicit decoders,
  which the code checks. S_6 and S_7 are open.
- The argument is elementary. We have not seen it applied to these blocks, but
  we have not read every paper that cites Demenkov et al.
