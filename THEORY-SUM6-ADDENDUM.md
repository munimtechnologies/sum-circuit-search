# A shorter road to "SUM_6 needs 14 gates": the constant-1 step (added 2026-11-26)

Apache-2.0. Made with AI agents working in MV2's name (MV2, Munim, Inc., mv2@munimtech.com). No human
has checked this note yet. Written and committed **before** jobs `sum6-lb-v1` (queued 2026-11-24) and
`f51-direct-v1` (filed today) have run. THEORY-SUM6.md stays as it was frozen; this note only adds.

Notation as in THEORY-SUM6.md: S_n = size(SUM_n) over all two-input gates (B2), outputs may be negated
for free; F(k, c) = the 3-bit binary value of c + (number of ones among k bits), so F(k, 0) = SUM_k;
G(k, c) = size(F(k, c)).

## Lemma 0' (the same gate-elimination step, with either constant)

For n >= 2 and any c with c + n <= 7: **G(n, c) >= 2 + max(G(n-1, c), G(n-1, c+1)).**

Proof. Take an optimal circuit for F(n, c). Its first gate reads two inputs x, y. If both had fan-out 1,
then with the other inputs at 0 the outputs would depend on (x, y) only through one bit, yet (0,0),
(0,1), (1,1) give the three different values c, c+1, c+2. So one of them, say x (F is symmetric), is
read by two different gates. Fix x = 0 or x = 1. Both readers then compute a constant or a literal of
their other input. Remove both and let their readers read that constant or literal directly (negations
are absorbed). If a removed reader was an output, the output now points at the literal or constant,
which costs nothing in this model (outputs may be any node, an input or the constant, with free
negation; this is also the encoder's model). In the cases used below (F(5,0), F(5,1), F(4,1), F(4,2))
no output is a constant or a literal anyway. What is left computes F(n-1, c) or F(n-1, c+1) with two
gates fewer. QED.

THEORY-SUM6.md used only x = 0. With x = 1 the same step gives

    S_6 >= G(5,1) + 2.

So **if F(5,1) = 1 + (count of 5 bits) has no circuit of at most 11 gates, then S_6 >= 14.** That is
one SAT question on 5 inputs. The 6-input search at 13 gates and the rules R1 and R2 are not needed for
it. Combined with THEORY-BLOCKS.md Theorem 3, S_6 >= 14 means that no reduced one-column block on up to
6 units can push bit counting below 4.5n.

## Duality (free input and output negation)

Flipping all inputs turns a count w into k - w, and flipping all three outputs turns v into 7 - v. So
F(k, c)(NOT x) = NOT F(k, c')(x) with c' = 7 - k - c, and G(k, c) = G(k, 7 - k - c). In particular
G(4,2) = G(4,1), G(4,3) = G(4,0) = 9, G(5,2) = G(5,0) = 11, F(5,1) is self-dual, and S_6 = G(6,1).
`test_f51.py` checks the identity on every row.

## What is known about G(5,1)

- Lower: G(5,1) >= 2 + max(G(4,1), G(4,2)) = 2 + G(4,1) by Lemma 0' and duality.
- G(4,1) <= 9: `job_f51.py` lists a 9-gate circuit (a full adder on (1, x0, x1) costs 2 gates, a full
  adder on the weight-1 bits 5, a half adder on the weight-2 bits 2). `test_f51.py` checks it on all 16
  rows. Lemma 0' with G(3,2) = 5 (a full adder, up to output negation) gives only G(4,1) >= 7. So
  G(4,1) is 7, 8 or 9.
- Upper: G(5,1) <= S_6 - 2 <= 14 (S_6 <= 16, Kulikov, Pechenev and Slezkin, arXiv:2102.12579). Plain
  adders also give 14.

So if G(4,1) = 9 then G(5,1) is 11, 12, 13 or 14, and every value except 11 proves S_6 >= 14.

## Two consistency checks for sum6-lb-v1 (registered now, before it runs)

- K1. By Lemma 0', "F(4,1) at most 8 gates UNSAT" implies "F(5,1) at most 10 gates UNSAT". So that
  job's T4 must hold whenever its T1 holds. T1 true with T4 false (SAT) would be a bug in the encoder.
- K2. By duality, F(4,1)@8 and F(4,2)@8 have the same answer (T1 and T2), apart from timeouts.

sum6-lb-v1 also runs F(5,1) at most 11 gates, but with only a 600 s limit, which is short for an UNSAT
proof at 11 gates. Today that run matters most, so it gets its own job.

## Job f51-direct-v1 (job_f51.py, test_f51.py; uses stagecore.py and sum6rules.py)

1. F(4,1)@8 and F(4,2)@8 ("at most"). Both UNSAT licenses the rules below and gives G(5,1) >= 11.
2. Soundness check: SUM_5 at exactly 11 gates with R1, R2 (c = 0 and 1) and the symmetry rule must be
   SAT (11-gate SUM_5 circuits exist).
3. F(5,1) at exactly 11 gates with the same rules (3 h limit). For F(5,1) the rules are licensed
   exactly as in THEORY-SUM6.md: x = 0 leaves F(4,1) and x = 1 leaves F(4,2), both of size >= 9, so
   the budget is 2; no output of F(4,1) or F(4,2) is constant; F(5,1) is symmetric.
4. F(5,1) at most 11 gates with no rules (2 h 20 min limit), which depends on nothing but Lemma 0' and
   the encoder. Skipped if step 3 finds a circuit.

Verdicts: F51_GE_12_SO_SUM6_GE_14 (step 4 UNSAT), F51_GE_12_SO_SUM6_GE_14_WITH_RULES (step 3 UNSAT
after a passed check, step 4 timed out), F51_LE_11 (a verified 11-gate circuit for F(5,1); this road
is closed and the 13-gate question goes back to sum6-lb-v1), UNDECIDED, or a conflict/bug verdict.
A timeout proves nothing.

## Frozen predictions (2026-11-26, before any run)

| id | statement | our probability |
|---|---|---|
| D1 | F(4,1)@8 and F(4,2)@8 return the same status (duality check) | 97% |
| D2 | both are UNSAT, so G(4,1) = G(4,2) = 9 | 70% |
| D3 | the SUM_5@11 soundness check is SAT and verified | 95% |
| D4 | verdict is F51_GE_12_SO_SUM6_GE_14 or ..._WITH_RULES (S_6 >= 14 proved) | 40% |
| D5 | verdict is F51_LE_11 (an 11-gate F(5,1) circuit exists) | 40% |
| D6 | verdict is UNDECIDED | 20% |

If D3 fails, any UNSAT with rules is void and only step 4 counts.

## Prior art (searched 2026-11-24 and again 2026-11-26)

Lemma 0' is the textbook gate-elimination step (Schnorr; Stockmeyer, Math. Systems Theory 10, 1977,
whose 2.5n - O(1) bound for symmetric functions also uses complementary pairs). We claim nothing new
about the step itself. Kulikov, Pechenev and Slezkin (arXiv:2102.12579) give S_6 <= 16 and exact values
up to n = 5. Goncharov, Kulikov and Levtsov (arXiv:2509.13966) build the 11-gate SUM_5 from the 8-gate
MDFA. We found no published lower bound for SUM_6 above 13 and no published value of size(F(5,1)).
What is new here is using the constant-1 restriction to turn the 6-input question into a 5-input one.
