# sum-circuit-search: can bit counting be done with fewer than 4.5n gates?

An open, pre-registered computer search by MV2 of Munim, Inc. (mv2@munimtech.com).
Made with AI agents working in MV2's name; no human has checked these results yet.
Licence: Apache-2.0.

## The question

SUM_n takes n bits and outputs their sum in binary. Every symmetric Boolean
function of n bits (majority, threshold, MOD-m, ...) is SUM_n followed by o(n)
more gates, so SUM_n's circuit size bounds them all. Over the full binary basis
(all two-input gates), the best known bounds are

    2.5n - O(1)  <=  size(SUM_n)  <=  4.5n + o(n)

The lower bound is Stockmeyer's (1977). The upper bound is Demenkov, Kojevnikov,
Kulikov and Yaroslavtsev (IPL 110(7), 2010). Their key piece is the 8-gate "MDFA"
block, which stores pairs of same-weight bits (p, q) as (p, p XOR q). Nobody has
lowered the 4.5 since 2010. Sergeev's 2026 survey (arXiv:2603.24319) still lists
4.5n - Theta(log n) as the best bound. Goncharov, Kulikov and Levtsov
(arXiv:2509.13966, 2025) list "the smallest gamma with size <= gamma*n - O(m)" as
an open problem, known to satisfy gamma <= 4.5. They write that improving it
"would most probably require using new building blocks".

**What would be remarkable:** a block that lowers 4.5 would be the first
improvement in 16 years to the number of gates needed to count bits. It would
also be the first for every symmetric Boolean function at once.

## The method: an exact test for "new building blocks"

A *block* takes groups of bits from one column (weight w) and outputs groups at
weights w, w+1, w+2, keeping the weighted sum. A group is either a plain bit
**P**, or a pair **D** stored as (p, p XOR q) with value p + q. The block's
outputs form a relation, not a function: for a D group with value 1, either
code (0,1) or (1,1) is accepted. The MDFA uses this freedom.

Give each P bit a potential of 4.5 and each D pair a potential of 8. Two known
blocks then pay exactly their potential drop:
- the pairing XOR (P + P -> D, 1 gate, drop 9 - 8 = 1)
- the MDFA (P + D + D -> P@w + D@w+1, 8 gates, drop 20.5 - 12.5 = 8)

These two blocks force these exact potentials. The potentials give a simple bound.

**Lemma.** Suppose every block in a family has size >= phi(in) - phi(out). Then
every circuit built from that family, turning n plain bits into the binary sum,
has at least 4.5n - O(log n) gates. The proof telescopes: total potential starts
at 4.5n and ends at O(log n).

So a block can beat 4.5n only if it is **profitable**, meaning its size is
strictly less than phi(in) - phi(out). Conversely, a profitable block means the
LP over block compositions has value below 4.5. An explicit SUM_n construction
would then confirm the new constant. That step is done only if one is found.

*Correction added 2026-11-17, before any search result:* the "conversely"
sentence holds for blocks that read one column. A block that reads two columns
and needs extra plain bits at the higher weight beats 4.5n only under a stronger
condition (gain > 0). [THEORY.md](THEORY.md) has the proofs and an explicit
improvement for each case.

The job lists every shape: inputs are any mix of P and D in one column with at
most 6 wires; outputs are any P and D groups that can hold every possible total
and leave a positive potential drop. For each shape, s_max is the largest size
that would be profitable. The job asks a SAT solver (CaDiCaL 1.9.5 through
PySAT) whether a circuit of exactly s gates exists, for s = 0, 1, ..., s_max.
Gates are any non-degenerate two-input gate, normalised to output 0 on input 00,
with free output negation. Every gate must be used. A SAT answer is decoded and
re-checked on every input row, in two separate processes. UNSAT at every
s <= s_max proves the shape cannot beat 4.5n. Each size step has a 900 s limit,
each shape 2,400 s, and the whole run 330 minutes, on 2 CPUs. Shapes run
cheapest first (by s_max).

The CNF encoding is tested without a solver (test_sumcore.py). Every known block
(full adder, Stockmeyer's 4-gate block, MDFA, MDFA', pairing XOR), transcribed
gate by gate from Cirbo (github.com/spbsat/cirbo), must satisfy every clause.
Broken versions (swapped outputs, a degenerate gate, an unused gate, a wrongly
negated output) must violate at least one.

## Prior art (searched 2026-11-17)

- Demenkov et al. 2010: 4.5n + o(n); MDFA.
- Kulikov and Slezkin, MFCS 2022 (arXiv:2102.12579): SAT local improvement finds
  size(SUM_k) for k <= 15 (e.g. SUM_5 = 11, SUM_7 <= 19). Plugged into the
  Theorem 1 formula, size(SUM_k)/(k - ceil(log2(k+1))), the best constant they
  give is 4.75 (k = 7). Their paper says the circuits for n <= 15 "do not allow
  to improve" 4.5n.
- Goncharov, Kulikov and Levtsov 2025 (arXiv:2509.13966): 4.5n - 2m for
  general bit addition. As read through a text extraction of the PDF, the paper
  reports no SAT search over pair-encoded blocks; gamma <= 4.5 is left open.
- Sergeev 2026 survey (arXiv:2603.24319): 4.5n - Theta(log n) is still the best.
- We found no paper that tests encoded compressor blocks against these potentials.

## Pre-registered predictions (frozen 2026-11-17 ~09:55 UTC, before any run)

**C1 (check, not a prediction):** the solver finds all five known blocks at their
known sizes (5, 4, 8, 6, 1), and the full-adder shape (P+P+P -> P@0+P@1) has no
circuit of size <= 4. The full adder's minimum of 5 is known. If C1 fails, the
encoder is wrong and the run is void.

- **P1.** The MDFA shape (P + D + D -> P@0 + D@1) has no circuit of size <= 7,
  even with the freedom in output codes. MDFA's 8 gates are optimal.
- **P2.** Stockmeyer's shape (P + D -> P@0 + P@1) has no circuit of size <= 3.
- **P3.** MDFA' (D + D -> P@0 + D@1) has no circuit of size 4 or 5, so 6 is optimal.
- **P4.** No shape is profitable: n_profitable = 0.
- **P5.** At least 80% of shapes with s_max <= 8 are decided (barrier holds or
  profitable) within the time limits.
- **P6.** Every shape with at most 4 input wires is decided.

If P4 fails, the found block is re-verified by hand and turned into an explicit
SUM_n construction before anything is claimed. If P4 holds, the decided shapes
give a barrier: within this block family, new building blocks need more than 6
input wires, inputs from several columns, or new encodings beyond P and D. Those
are the next versions of this search.

## Files

- `sumcore.py`: semantics, potentials, shape enumeration, CNF encoder and decoder, circuit checker (stdlib only)
- `known_blocks.py`: the known blocks, gate by gate
- `solve_one.py`: solves one (shape, size) instance with PySAT
- `job.py`: the full search; writes `results.json` and `progress.jsonl`
- `test_sumcore.py`: stdlib unit tests

Run: `pip install -r requirements.txt && python -m unittest -v && python job.py --out-dir out`

## Search 2: new 3-bit encodings (added 2026-11-17, pre-registered before its run)

Search 2 asks whether new *encodings* help. There are exactly five XOR-linear
3-bit codes that are not built from P and D (for example (p, p^q, p^r)). For
each one, the job finds its potential from exact creation costs. It then tests
every block with up to 6 input wires that produces or consumes that code,
including the MDFA analogues E+E -> P@0 + E@1. Full method, the hand
classification and five frozen predictions are in [SEARCH2.md](SEARCH2.md).
Code: `enccore.py`, `solve_enc.py`, `job_enc.py`, `test_enccore.py`.

## Search 3: blocks that read two columns at once (added 2026-11-17, pre-registered before its run)

Every known block reads one column; columns meet only through carries. Search 3
tests every P/D block whose inputs come from two adjacent columns (both used,
at most 6 input wires), against the same potentials 4.5 and 8. The potentials do
not depend on the column, so the barrier lemma still applies. As long shots, it
also asks for one gate fewer than the two tight fused MDFA chains across adjacent
columns (8 input wires: 15 instead of 16 gates, 16 instead of 17). Method, a
hand-built check of both chains, and five frozen predictions are in
[SEARCH3.md](SEARCH3.md). Code: `job_twocol.py`, `test_twocol.py` (shares
`enccore.py`, `solve_enc.py` and `known_blocks.py`).

## Theory: what a cheaper block would buy (added 2026-11-17, before any result)

[THEORY.md](THEORY.md) proves three things:
1. An exact accounting identity: size = 4.5n - phi(final) - (sum of slacks).
2. The barrier: if no block is profitable, every composition needs at least
   4.5n - O(log n) gates.
3. A construction lemma with an explicit gain. A profitable one-column block
   with at most 6 input wires would give size(SUM_n) <= (4.5 - 1/12)n + O(log n)
   or better. A two-column block that needs delta extra plain bits at the higher
   weight helps only if its slack exceeds delta/2, because each such bit costs
   half a gate (full adder or Stockmeyer). So the second long shot at 16 gates
   would only break even. At 15 gates it would give 4.5 - 1/9.

Code: `lemma.py` (Lemma 3 as exact arithmetic) and `test_lemma.py`.

## Search 4: the hard instance s* of bit addition (added 2026-11-17, pre-registered before its run)

Goncharov, Kulikov and Levtsov's open problem 1 asks whether their bound
4.5n - 2m for every bit-addition function can be improved. They name the instance
that blocks it: s* = (0,0,0,0,1,1,2,2,...), that is X + Y + a + b, where their
circuit costs 7 gates per weight (3.5n). The carry is then 0, 1 or 2. Search 4
computes the exact minimum gates of one layer for every pair of 2-wire carry
codes (9 classes, found by hand and checked by code). The minimum mean cycle of
that 9 x 9 table is then the best rate of *any* layered circuit with 2-wire
carries. Below 7 means an explicit circuit for s* under 3.5n; exactly 7 means a
proved 3.5n - O(1) lower bound for that class of circuits. It also tries 3-wire
codes and fused 2-layer blocks. Method, proof sketch and five frozen predictions
are in [SEARCH4.md](SEARCH4.md). Code: `stagecore.py`, `solve_stage.py`,
`job_stage.py`, `test_stagecore.py` (standalone; stdlib apart from PySAT).

## Layered s* theory: pass-through layers and a conservation law (added 2026-11-17, before search 4's results)

[THEORY-SSTAR.md](THEORY-SSTAR.md) gives the full proof of the cut argument
behind search 4. It also shows that a layer may pass a carry wire straight
through. A full adder alone is then a complete 5-gate layer from the binary
carry code to two plain bits. Nine hand-built layers between the three main
codes (two plain bits, the pair code, binary) all cost exactly
7 + phi(out) - phi(in), where phi = 0, 1, 2 is the cost of packing two plain
bits into each code. Four of the nine are our own (simple) constructions. Every chain of them costs exactly
7 gates per weight. If that conservation law holds on the whole table, no
layered circuit with 2-wire carries beats 3.5n on s*.
[SEARCH4-ADDENDUM.md](SEARCH4-ADDENDUM.md) registers this as prediction H1
before any result. It also records that search 4's P5 is already known to fail.
`verify_layers.py` checks all nine layers and 363 chains exhaustively (stdlib
only).

## The round-trip barrier: the conservation law proved without SAT (added 2026-11-18, before search 4's results)

[THEORY-ROUNDTRIP.md](THEORY-ROUNDTRIP.md) proves the conservation law for
every layered s* circuit whose carry codes are cheap to enter and leave. Put a
circuit that packs two plain bits u, v into code A in front of any layer
A -> B, and a decoder for B behind it. The result computes the binary sum of
x, y, u, v, which needs 9 gates (size(SUM_4) = 9). So

    pack(A) + cost(A -> B) + dec(B) >= 9,

and a layered circuit with L layers has at least 9L minus the sum of
pack + dec over its inner cuts. For the three main codes, pack + dec = 2, so the
bound is 7L + 2. Our hand-built chains have exactly 7L + 2 gates, so they are
optimal among such circuits, with any number of carry wires. This proves H1
from one known fact (size(SUM_4) = 9), before search 4 reports. It also shows
where a sub-3.5n layered circuit would have to live: in codes with
pack + dec >= 3 (six of the nine 2-wire classes). `roundtrip.py` computes
pack and dec for all 60 two-wire carry tables by brute force and checks the
nine 9-gate SUM_4 "sandwiches" (stdlib; test `test_roundtrip.py`).
`job_sum4.py` (queued as job `sum4-sandwich-v1`) re-proves size(SUM_4) = 9
with the SAT encoder and tries the two-layer version, which would remove the
pack + dec condition at every other cut. *Correction:* arXiv:2102.12579 (cited
above as "Kulikov and Slezkin") has three authors: Kulikov, Pechenev and
Slezkin.

## The block sandwich for SUM_n (added 2026-11-19, before any search result)

[THEORY-BLOCKS.md](THEORY-BLOCKS.md) applies the same trick to the main
question. Put a pairing XOR in front of every D input of a block and a decoder
behind its outputs, and the result computes SUM_k. With the potentials 4.5 and
8 this gives slack(B) <= 9k/2 - size(SUM_k) - phi(out) + DEC(out) for any mix of
P and D inputs. Findings, none checked by a human yet:
- All six known blocks (pairing XOR, unpair, full adder, Stockmeyer, MDFA',
  MDFA) meet this bound with equality. Each one, wrapped this way, is an
  optimal SUM_2 to SUM_5 circuit.
- No "reduced" one-column block (one plain bit at weight 0 plus one carry
  group at weight 1) on at most 5 input wires is profitable. This follows from
  size(SUM_k) = 2, 5, 9, 11 alone. It also implies the lower-bound parts of
  search 1's C1 and P1-P3 (found after they were registered, before any
  result).
- On 6 input wires, a profitable reduced block exists if and only if
  size(SUM_6) <= 13. The exact value is open, and the best published upper
  bound is 16.

`blocks_sandwich.py` checks every number exhaustively (stdlib; test
`test_blocks_sandwich.py`). `job_sum56.py` (queued as job `sum56-exact-v1`)
re-proves size(SUM_5) = 11 and asks the SAT solver about SUM_6 at 16, 15, 14
and 13 gates. The predictions in THEORY-BLOCKS.md were frozen before it ran.
