# Does counting 6 bits need 14 gates? Rules for a 13-gate SUM_6 circuit (added 2026-11-24)

Apache-2.0. Made with AI agents working in MV2's name (MV2, Munim, Inc.). No human has checked these
proofs yet. Written and committed **before** job `sum6-lb-v1` has run; the predictions below are frozen.

## Why this number matters here

THEORY-BLOCKS.md (Theorem 3) showed: a profitable *reduced* one-column block on 6 units (one that would
push bit counting below 4.5n gates) exists **if and only if size(SUM_6) <= 13**. SUM_6 maps 6 bits to
their count in binary (3 outputs); the gate basis is all two-input Boolean functions (B2). The best
published circuit has 16 gates (Kulikov, Pechenev and Slezkin, MFCS 2022, arXiv:2102.12579, table of
size(SUM_n)). They note that exact sizes for 6-input functions are "already a difficult computational
task"; exhaustive exact costs end at 5 inputs (Knuth, TAOCP 7.1.2). We found no published lower bound
for SUM_6 above the elementary one in Lemma 0.

Notation: S_n = size(SUM_n) with ceil(log2(n+1)) outputs. Known exactly: S_2..S_5 = 2, 5, 9, 11.
F(k, c) = the 3-bit binary value of c + (number of ones among k bits); F(k, 0) = SUM_k (3 outputs).

## Lemma 0 (standard gate elimination): S_n >= S_{n-1} + 2 for n >= 2

Take an optimal circuit. Its first gate g reads two inputs x, y. If both had fan-out 1, everything
would depend on (x, y) only through the single bit g(x, y), but with the other inputs at 0 the outputs
take three different values on (0,0), (0,1), (1,1). So one of them, say x, is read by two different
gates. Set x = 0: both readers become constant or (negated) copies of their other input and can be
removed (negations move into readers or output polarity). What is left computes SUM_{n-1}. QED.

So **S_6 >= 13**, and with Theorem 3: *a profitable reduced 6-unit block exists iff S_6 = 13 exactly.*
Also S_5 = 11 = S_4 + 2: SUM_5 meets Lemma 0 with equality, so the rules below also describe every
optimal SUM_5 circuit. That gives the job a real soundness check.

## The rules (proved here, for a circuit C of exactly S_{n-1} + 2 gates computing SUM_n, n in {5, 6})

C is optimal (Lemma 0), so its gates are non-degenerate and normalised (f(0,0) = 0), and each is read by
a later gate or is an output. For an input x write N(x) for the set of gates reading x. Setting x = c
removes every gate in N(x). If some g in N(x) becomes **constant**, every reader of g is removed too.
The rest computes F(n-1, c), so at most s - size(F(n-1, c)) gates can disappear. For c = 0 that budget
is (S_{n-1} + 2) - S_{n-1} = **2**.

**R1 (fan-out).** Every input is read by at most 2 gates. (Setting x = 0 removes |N(x)| <= 2 gates.)

**R2 (constant gate), for each c with size(F(n-1, c)) >= S_{n-1}.** Suppose gate g reads input x and is
constant once x = c. Then:
(a) g is not an output, because no output of F(n-1, c) is constant for n in {5, 6} and c in {0, 1};
(b) g has a reader, and the removed set contains N(x) together with the readers of g, so it has at
    least 2 gates; with budget 2 it is exactly {g, g'}: g has the single reader g', and N(x) is a
    subset of {g, g'};
(c) N(x) = {g, g'} is impossible. Then g' reads x and g, g reads x and some h, nothing else reads g,
    and nothing else reads x. So g' is a function of (x, h) alone. Replace g and g' by one gate on
    (x, h): that gives a circuit of s - 1 < S_n gates, a contradiction.
Hence **x has fan-out 1, g is not an output, and exactly one gate reads g.**

**Corollary.** If size(F(n-1, 1)) >= S_{n-1} as well, R2 holds for both constants. Every AND-type gate
is constant at some value of each of its inputs. So *every input of fan-out 2 feeds only XOR-type gates*
(gates of the form x XOR h, up to negation), and an input that feeds an AND-type gate has fan-out 1.

**S (symmetry).** SUM is symmetric, so we may name the two inputs of the first gate x0 and x1.

R1 and R2 at c = 0 need only S_{n-1} (S_4 = 9 for the check, S_5 = 11 for SUM_6). R2 at c = 1 needs
size(F(4, 1)) >= 9 (check) or size(F(5, 1)) >= 11 (SUM_6), which the job computes first.

## Job sum6-lb-v1 (sum6rules.py, job_sum6lb.py, test_sum6rules.py; uses stagecore.py)

1. Table ("at most s gates"; UNSAT at s proves size >= s + 1): SUM_4@8, F(4,1)@8,9, F(4,2)@8,9,
   SUM_5@10, F(5,1)@10,11.
2. Soundness check: SUM_5 at exactly 11 gates with R1 + R2(c=0) + S, then with R2(c=1) too if
   F(4,1) >= 9 is certified. Both must be SAT (11-gate SUM_5 circuits exist and obey the rules). If
   either is UNSAT, the encoding or a lemma is wrong and step 3 is skipped.
3. SUM_6 at exactly 13 gates with all rules licensed by step 1. **UNSAT proves S_6 >= 14** (conditional
   on S_5 = 11, which step 1 re-proves). Then, with THEORY-BLOCKS Theorem 3, no reduced one-column
   block on up to 6 units can beat 4.5n. SAT would give a 13-gate circuit (best published 16), which
   by Theorem 3 would beat 4.5n. A timeout proves nothing.

## Frozen predictions (2026-11-24 ~08:05 UTC, before any run)

| id | statement | our probability |
|---|---|---|
| T0 | SUM_4@8 UNSAT (S_4 = 9 re-proved) | 99% |
| T1 | F(4,1)@8 UNSAT, so size(F(4,1)) >= 9 | 70% |
| T2 | F(4,2)@8 UNSAT | 65% |
| T3 | SUM_5@10 UNSAT within 60 min (S_5 = 11 re-proved) | 85% |
| T4 | F(5,1)@10 UNSAT within 60 min, so R2(c=1) is licensed for SUM_6 | 55% |
| C5 | soundness check: every SUM_5@11 pruned run that is run is SAT and verified | 95% |
| M6a | SUM_6@13 pruned is UNSAT within 3 h (S_6 >= 14 proved) | 30% |
| M6b | SUM_6@13 pruned is SAT (a 13-gate circuit) | 2% |
| M6c | SUM_6@13 times out | 68% |

If C5 fails, the result is a bug report against our own lemmas or encoder, not a bound.

## Prior art (searched 2026-11-24)

Searches: "exact circuit size SUM_6 lower bound"; Stockmeyer 1977 2.5n gate elimination; Knuth
sideways sum six variables minimum cost; Wegener section 5.4. Closest work: Stockmeyer (Math. Systems
Theory 10, 1977) gives 2.5n - O(1) for SUM_n by eliminating 5 gates with paired substitutions
x_i <- f, x_j <- not f. Its additive constant does not decide 13 versus 14 at n = 6, and we could not read
the paper's text. Kulikov, Pechenev and Slezkin (arXiv:2102.12579) give S_6 <= 16 and exact values only
up to n = 5. Goucher (2023) and Lee et al. (IWLS 2019) cover exhaustive minimum circuits up to 5 inputs.
What is new here, if the job succeeds, is using exact small sizes (S_4, S_5, F(k, 1)) as
**structural constraints** inside the SAT search for the next size. We have not seen that done for SUM_6.
