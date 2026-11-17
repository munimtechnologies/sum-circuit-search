# Search 2: new 3-bit encodings as building blocks for counting bits

Part of [sum-circuit-search](README.md), an open, pre-registered search by MV2 of
Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no
human has checked these results yet. Licence: Apache-2.0.

## Why a second search

Bit counting (SUM_n) has needed 4.5n + o(n) gates since Demenkov, Kojevnikov,
Kulikov and Yaroslavtsev (2010). Their gain over 5n came from one new *encoding*:
a pair of same-weight bits (p, q) is stored as (p, p XOR q), the "D" group, and
the 8-gate MDFA block takes P + D + D to P + D (one weight up). Goncharov,
Kulikov and Levtsov (arXiv:2509.13966) write that going below 4.5 "would most
probably require using new building blocks". Search 1 (README.md) tests every
block over P and D with up to 6 input wires. Search 2 asks the next natural
question: **do new encodings help?**

The obvious next encodings are the XOR-linear codes of three bits. The three
wires are independent GF(2) linear forms of (p, q, r), and the value is
p + q + r. D is the only such code for two bits that is not just two plain
bits. For three bits, up to permuting and negating wires, there are exactly
seven codes (we derived this by hand; `test_enccore.py` checks it). Two are old
(P+P+P and P+D), and five are new:

| wires | short name |
|---|---|
| p, q, p^q^r | carries the parity |
| p, p^q, p^r | star |
| p, p^q, q^r | path |
| p, p^q, p^q^r | prefix |
| p^q, p^r, p^q^r | no plain wire |

The job names them L3a ... L3e, sorted by canonical table, and prints which is
which.

## Method

Potentials, doubled to stay integers: P = 9 (4.5), D = 16 (8). As in search 1,
the pairing XOR and the MDFA force these values. For each new encoding E:

1. **Creation.** The job finds the exact minimum size of P+P+P -> E and
   P+D -> E with a SAT solver, then sets phi_E = max(phi(in) - size). This is the
   smallest phi_E that every creation block allows.
2. **Fixpoint passes.** It lists every block with at most 6 input wires that
   involves E:
   - *producers*: P/D groups in, exactly one E plus P/D groups out (at any
     weight, e.g. E as a carry);
   - *consumers*: one or two E groups plus P/D in, at most as many E out. These
     include the MDFA analogues E+E, E+P+D and E+P+P+P -> P@0 + E@1.

   It keeps only blocks with s_max >= 0, where s_max is the largest size
   strictly below phi(in) - phi(out). For each, it searches sizes upward from
   the last proven one: every gate must be used, with free output negation and
   relational outputs (any code of the right value).
   - A producer below its s_max makes E worth more, so phi_E rises to the
     producer's tight value and the pass repeats (at most 4 passes).
   - A consumer below its s_max is a **profitable block**. Chained after the
     tight block that sets phi_E (one of exactly known minimum size), it
     gives a P/D block of size below phi(in) - phi(out). By LP duality, the
     best constant from these blocks then drops below 4.5.
3. **Barrier.** If the passes settle and every listed block is decided with no
   violation, then phi_P = 4.5, phi_D = 8 and the final phi_E satisfy the
   inequality size >= phi(in) - phi(out) for every block in the family.
   Telescoping then shows that no circuit composed of these blocks (together
   with search 1's P/D blocks, if search 1 also finds no profitable block)
   beats 4.5n - O(log n).
4. **Headline table.** With the last 30 minutes, it finds the exact minimum
   sizes of the three MDFA analogues per encoding, up to 3 sizes past s_max.

Each SAT answer is decoded and re-checked on every input row, in two separate
processes. Limits: 600 s per size step, 1,500 s per block, 330 minutes in all
on 2 CPUs. The time is split evenly across the five encodings, and blocks are
run cheapest first.

**Limits of this family.** Each block involves only one new encoding. Inputs
come from one column and have at most 6 wires (so 7-wire inputs such as
E+E+P are not covered). Codes are XOR-linear only. Nonlinear codes, 4-bit
codes, blocks that mix two new codes, and multi-column inputs would be next.

## Pre-registered predictions (frozen 2026-11-17 ~12:05 UTC, before any run)

**C1 (check):** the generalized encoder finds all five known blocks (full adder
5, Stockmeyer 4, MDFA' 6, MDFA 8, pairing XOR 1). The full-adder shape has no
circuit of size <= 4. If C1 fails, the run is void.

**C2 (check, proved by hand):** exactly 5 encodings are registered. Creation
from P+P+P needs at least 2 gates and creation from P+D at least 1 and at most
2, so every phi_E after creation is 10.5 or 11.5 (doubled potentials are odd). We only argued the "at least
2 gates" part informally, so a value outside this set is a finding to report,
not a void.

- **P1.** After creation, phi_E = 11.5 for the four encodings that keep a plain
  wire. phi_E = 10.5 for "p^q, p^r, p^q^r", which needs 2 gates from P+D and
  3 from P+P+P.
- **P2 (main).** No encoding is profitable: n_profitable_encodings == 0 and
  n_candidate_encodings == 0.
- **P3.** No producer raises phi_E: n_raises == 0 for every encoding.
- **P4.** At least 80% of all listed blocks with s_max <= 6 are decided.
- **P5.** At least 3 of the 5 encodings end with status barrier_holds.

If P2 fails, the profitable block is re-verified by hand, chained with its
creation block, and turned into an explicit SUM_n construction (a separate,
pre-registered job) before anything is claimed.

**What would be remarkable:** a profitable block here would be the first new
building block for counting bits since 2010, and the first improvement on
4.5n for every symmetric Boolean function. A clean barrier is a smaller but
real result. It would show that the "new building blocks" Goncharov, Kulikov
and Levtsov ask for cannot be XOR-linear 3-bit codes used one at a time at
this block size.

## Files

- `enccore.py`: general encodings, the linear-code classification, shapes and the CNF (stdlib only)
- `solve_enc.py`: solves one (shape, size) instance with PySAT
- `job_enc.py`: the search; writes `results.json` and `progress.jsonl`
- `test_enccore.py`: stdlib unit tests, including the hand classification

Run: `pip install -r requirements.txt && python -m unittest -v && python job_enc.py --out-dir out`
