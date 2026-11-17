# Search 3: blocks that read two columns at once

Part of [sum-circuit-search](README.md), an open, pre-registered search by MV2 of
Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no
human has checked these results yet. Licence: Apache-2.0.

## Why a third search

Every building block used so far for counting bits reads groups of **one**
weight. That includes the full adder, Stockmeyer's 4-gate block, and the MDFA and
MDFA' of Demenkov, Kojevnikov, Kulikov and Yaroslavtsev (2010). In the 4.5n
construction, and in Goncharov, Kulikov and Levtsov's 4.5n - 2m circuits for
general bit addition (arXiv:2509.13966), columns meet only through carries: one
column's MDFA emits a carry pair D at weight w+1, and the next column's MDFA
consumes it. As we read that paper, none of its blocks takes inputs from two
weights. It also reports no SAT search for blocks. Search 1 covers one-column P/D
blocks, and search 2 covers new 3-bit codes. Search 3 asks whether a block that
**fuses work across two adjacent columns** can beat the potentials 4.5 (P) and
8 (D) that make the 4.5n construction tight.

## Method

Same potentials, CNF, relational outputs, free output negation and
every-gate-used rule as searches 1 and 2 (the code reuses `enccore.py`).

- **Inputs:** every multiset of P and D groups with at least one group at weight 0,
  at least one at weight 1, and at most 6 wires. There are 49 of them; the count
  is derived by hand in `test_twocol.py`.
- **Outputs:** every multiset of P and D groups (any weights, at most 8 wires)
  that can hold every possible input total and leaves a positive potential drop.
- **Test:** s_max is the largest size strictly below phi(in) - phi(out). The job
  asks the SAT solver for a circuit of exactly s gates for s = 0, 1, ..., s_max,
  cheapest shapes first. If it finds a circuit of size <= s_max, the block is
  **profitable**: it pays less than its potential drop, so the LP over block
  compositions falls below 4.5. If every shape is decided and none is
  profitable, then every circuit composed of these blocks (together with
  search 1's) needs at least 4.5n - O(log n) gates. The potentials do not depend
  on the column, so the telescoping lemma holds for multi-column blocks too.
- **Long shots (SAT only, not exhaustive).** Two 8-wire blocks are exactly the
  two tight fused chains of MDFAs across adjacent columns:
  - `mdfa_then_mdfa`: P@0 + D@0 + D@0 + P@1 + D@1 -> P@0 + P@1 + D@2. The chain
    MDFA (column 0), then MDFA on the carry and column 1, uses 16 gates, exactly
    its potential drop.
  - `mdfa_then_pair_mdfa`: P@0 + D@0 + D@0 + P@1 + P@1 + P@1 -> P@0 + P@1 + D@2.
    MDFA, then a pairing XOR, then MDFA, uses 17 gates, exactly its drop.

  `test_twocol.py` builds both composites gate by gate and checks them on all
  256 inputs. The job asks for one gate fewer (15 and 16), 50 minutes each. A
  circuit found there would be profitable. A timeout proves nothing.

Limits: 600 s per size step, 1,500 s per shape, 290 minutes for the main search
and 50 minutes for the long shots, on 2 CPUs. Each SAT answer is decoded and
re-checked on every input row in two separate processes.

## Pre-registered predictions (frozen 2026-11-17 ~14:30 UTC, before any run)

**C1 (check):** the encoder finds the five known blocks at their sizes (full
adder 5, Stockmeyer 4, MDFA' 6, MDFA 8, pairing XOR 1), and finds the
two-column block MDFA + pass-through (P@0 + D@0 + D@0 + P@1 -> P@0 + P@1 + D@1)
at 8. The full-adder shape has no circuit of size <= 4. If C1 fails, the run is
void.

**C2 (check):** n_inputs == 49.

- **P1 (main).** No two-column block with at most 6 input wires is profitable:
  n_profitable == 0.
- **P2.** The MDFA + pass-through shape is decided: it has no circuit of size
  <= 7, so an extra weight-1 bit does not make the MDFA cheaper.
- **P3.** At least 80% of shapes with s_max <= 6 are decided
  (n_s_max_le_6_decided / n_s_max_le_6 >= 0.8).
- **P4.** At least 60% of all listed shapes are decided (n_decided / n_shapes
  >= 0.6).
- **P5.** Neither long shot finds a circuit (sat == false for both).

If P1 or P5 fails, the circuit is re-verified by hand and then built into an
explicit SUM_n construction. Gates and the constant are counted for n up to
10^4 in a separate, pre-registered job before anything is claimed.

**What would be remarkable:** a profitable two-column block, or a 15-gate fused
MDFA chain, would be the first building block for counting bits that beats the
2010 potentials. It would point to the first improvement of 4.5n in 16 years,
for SUM_n and every symmetric Boolean function. If P1 holds, the barrier says
that fusing two adjacent columns does not help at up to 6 input wires. Any new
block then needs more wires, more columns or a new encoding.

## Note added 2026-11-17 ~17:00 UTC, before any result (the predictions above are unchanged)

The Method says a profitable block makes "the LP over block compositions" fall
below 4.5. [THEORY.md](THEORY.md) (Lemma 3) shows this needs one more condition
for two-column blocks. A block that consumes delta more plain weight-1 bits than
it emits must pay for them. The cheapest known source, a full adder or
Stockmeyer's block, costs half a gate each, so the block beats 4.5n by Lemma 3
only if slack > delta/2. When this search is graded, every profitable block is
listed with its delta and Lemma 3's gain/R (`lemma.py`). P1 is still graded on
n_profitable exactly as frozen. For the long shots:
- `mdfa_then_mdfa` has delta = 0, so a 15-gate circuit would give
  gamma <= 4.5 - 1/9.
- `mdfa_then_pair_mdfa` has delta = 2, so the 16-gate circuit this job asks for
  would break even under Lemma 3 (gain 0). It would beat 4.5n only together
  with a slack-0 source of plain weight-1 bits, and we know of none.

## Files

- `job_twocol.py`: the search; writes `results.json` (stats_for_verdicts,
  profits, long_shots, one row per shape) and `progress.jsonl`
- `test_twocol.py`: stdlib unit tests (hand count of inputs, a hand-enumerated
  shape case, the MDFA + pass-through circuit against the CNF, both 8-wire
  composites)
- `enccore.py`, `solve_enc.py`, `known_blocks.py`: shared with search 2

Run: `pip install -r requirements.txt && python -m unittest -v && python job_twocol.py --out-dir out`
