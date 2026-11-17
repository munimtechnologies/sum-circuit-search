# Search 4: a cheaper circuit for the hard vector s* of bit addition?

Part of [sum-circuit-search](README.md), an open search by MV2 of Munim, Inc.
(mv2@munimtech.com). Made with AI agents working in MV2's name; no human has
checked this yet. Licence: Apache-2.0. Pre-registered 2026-11-17 (~19:20 UTC),
before the job has run.

## The question

Goncharov, Kulikov and Levtsov (arXiv:2509.13966, STACS 2026) prove that every
bit-addition function BA^s (n input bits with weights 2^{s_i}, output the sum
in binary on m bits) has a circuit of size 4.5n - 2m over the full binary
basis. Their open problem 1 asks for the largest alpha with
size(BA^s) <= 4.5n - alpha*m for every s; they know 2 <= alpha <= 2.5.

They name the instance that blocks progress:

    s* = (0, 0, 0, 0, 1, 1, 2, 2, ..., k, k)

four bits of weight 1 and two bits of every weight 2^1 .. 2^k, so n = 2k + 4
and m is about n/2. Their circuit pairs the two bits of each weight (1 gate)
and applies one MDFA' block (6 gates): 7 gates per weight, 3.5n + O(1) in all,
which is exactly 4.5n - 2m. In their words, a smaller circuit for this s* is
needed before 2m can be improved, and a lower bound of 3.5n - O(1) for s*
would prove alpha = 2.

**What would be remarkable:** any circuit for s* below 3.5n would be the first
step past their bound on the instance they single out. A proof that a natural,
large class of circuits cannot go below 3.5n would be real evidence that
alpha = 2.

## The model: layered circuits

s* adds X + Y + a + b, where X and Y are (k+1)-bit numbers and a, b are bits.
The carry into each weight is therefore 0, 1 or 2 (it is 2 only when every
lower bit is 1). A *layered* circuit handles one weight at a time. Layer i
reads x_i, y_i and the carry wires, and writes the output bit s_i and the
carry wires for weight i+1. Nothing else crosses the cut between two layers.
GKL's circuit is layered with 2 carry wires (the pair code (p, p XOR q)).

A *carry code* on k wires says which wire values (words) stand for carry 0, 1
and 2. Every value needs at least one word, and different values need
different words; a word may be unused. Permuting or negating the wires costs
nothing (gates absorb input negation, and outputs may be negated freely), so
codes are counted up to that symmetry.

**2-wire codes, by hand.** Of the 60 tables, there are 9 classes:
- *U0, U1, U2:* one word unused. Uv means the word opposite the unused one
  means v. U0 is binary (2*b1 + b0), and U1 is the thermometer code.
- *A0, A1, A2:* value v has two opposite words. A1 is two plain bits u + v.
- *J0, J1, J2:* value v has two adjacent words. J1 is GKL's pair code
  (p, p XOR q).

For codes C, C', let cost(C -> C') be the fewest gates in one layer that reads
x, y and a carry in code C and writes s and the carry in code C'. A layered
circuit with 2-wire carries for s* with L layers then costs at least the sum
of cost(C_i -> C_{i+1}) along its sequence of codes. So its gates per layer
tend to at least the **minimum mean cycle** mu* of the 9 x 9 matrix of costs.
This is a proof, not a heuristic. At each cut, the two wires must tell carries
0, 1 and 2 apart, so they form one of the 9 classes, and every (word, x_i, y_i)
combination occurs. Layer 0 and the final carry add only O(1).

- If **mu* < 7**, the cheapest cycle gives an explicit circuit for s* with
  (mu*/2) n + O(1) < 3.5n gates.
- If **mu* = 7**, no layered circuit with 2-wire carries beats GKL on s*. This
  is a lower bound of 3.5n - O(1) for that class of circuits: a partial
  result toward alpha = 2.

## The job (`job_stage.py`, code in `stagecore.py`)

- **C1 (checks).** The SAT ladder finds the full adder at its known minimum of
  5 (nothing of size <= 4). Hand-built circuits pass on every row: GKL's layer
  (STAGE_D, 7 gates), the full adder plus half adder layer for code A1
  (7 gates), layer 0 (8 gates), the decoder (1 gate), and two GKL layers
  stacked (14 gates). Whole s* circuits built from them, with L = 1..4 layers
  after layer 0, are correct on every input and have exactly 7L + 9 gates.
  If C1 fails, the run is void.
- **Part 1.** For all 81 pairs of 2-wire classes, the job runs a SAT ladder
  (sizes 0, 1, ... up to 10, stopping at the first circuit). The first size
  with a circuit is the exact minimum. Same encoding as searches 1-3: normal
  non-degenerate two-input gates, every gate used, any correct output word,
  free output negation, each circuit re-checked on every row. The job then
  computes mu* with Karp's algorithm, plus a proved lower bound that uses
  (largest size ruled out) + 1 for any undecided entry. The cheapest cycle of
  at most 3 codes is built into whole s* circuits (L = 1..4) and checked on
  every input.
- **Part 2.** Every class of 3-wire carry codes, with the same code in and
  out: is there a layer with <= 6 gates? (90 minutes.)
- **Part 3.** 2-layer blocks (x_i, y_i, x_{i+1}, y_{i+1} plus the carry) with
  the same 2-wire code in and out: is there one with <= 13 gates (fewer than
  two GKL layers), or below the best two-step path of part 1 if that is
  cheaper? SAT ladders with about 33 minutes per code. **A timeout is not a
  proof.**

Any circuit found in part 2 or 3 is also built into whole s* circuits and
checked on every input.

## Pre-registered predictions (frozen before the run)

- **P1** (75%). mu* = 7: no layered circuit with 2-wire carries beats 3.5n
  on s*, and the proved lower bound also equals 7.
- **P2** (80%). cost(J1 -> J1) = 7 and cost(A1 -> A1) = 7 exactly: GKL's
  layer and the full-adder-plus-half-adder layer are both optimal for their
  codes.
- **P3** (80%). No 3-wire code has a same-code layer with <= 6 gates.
- **P4** (85%). No 2-layer block with <= 13 gates is found. Separately (50%),
  at least 5 of the 9 codes are decided within the time limit.
- **P5** (60%). The smallest entry of the whole 9 x 9 matrix is 7. Some
  transition between two different codes could be cheaper than 7 even if no
  cycle is.

## What happens next

- **If anything beats 7 per layer** and passes the whole-circuit check, it is
  re-verified by hand. It is then written up as an explicit circuit family for
  s*, and the new layer is tested as a building block for general s (does it
  give 4.5n - beta*m with beta > 2?). Only then is it claimed, and the authors
  are told.
- **If P1 holds,** the 9 x 9 table of exact layer costs is published as data,
  with the restricted lower bound. The next versions widen the class: cycles
  between 3-wire codes, 2-layer blocks between different codes, and layers
  that also pass a plain bit across the cut.

Results will be appended below this line, after the run, without changing
anything above it.
