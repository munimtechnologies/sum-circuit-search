# Search 4 addendum: one extra prediction and one known failure

Part of [sum-circuit-search](README.md), by MV2 of Munim, Inc.
(mv2@munimtech.com). Made with AI agents working in MV2's name; no human has
checked this yet. Licence: Apache-2.0.

Written 2026-11-17, ~20:00 UTC. That is after [SEARCH4.md](SEARCH4.md) was
frozen and its job `sstar-stage-search-v1` filed (~19:20 UTC), and **before the
job has started or produced any output**. This is not part of the original
pre-registration, which stays unchanged in SEARCH4.md. It is graded together
with it.

## Known before the results: P5 fails

SEARCH4.md's P5 (60%) says the smallest entry of the 9 x 9 matrix is 7. A
layer U0 -> A1 with 5 gates exists: a full adder on (x, y, D), with the wire
E = [C = 2] passed straight through
([THEORY-SSTAR.md](THEORY-SSTAR.md), section 2). So P5 is false whatever the
job finds. It will be reported as failed. This does not touch P1 (mu* = 7).

## H1 (new, registered now): the conservation law on {A1, J1, U0}

Let phi(A1) = 0, phi(J1) = 1, phi(U0) = 2. These are the gates needed to pack
two plain bits into each code. Hand-built layers achieve
7 + phi(out) - phi(in) on all nine pairs (THEORY-SSTAR.md, section 3).

**H1 (55%).** Search 4's exact table has, for these three classes,

|        | -> A1 | -> J1 | -> U0 |
|---|---|---|---|
| A1 ->  | 7 | 8 | 9 |
| J1 ->  | 6 | 7 | 8 |
| U0 ->  | 5 | 6 | 7 |

with every one of the nine entries decided (not a timeout). In other words,
all nine hand-built layers are optimal.

- *H1 fails* if any of these entries is smaller. That would mean a layer
  cheaper than every hand construction. If it also lowers a cycle below mean 7,
  it is the "beats 3.5n" case of SEARCH4.md.
- *H1 is undecided* if any entry times out. The proved lower bound for that
  entry is then reported instead.

**Certificate (not a prediction).** Suppose P1 (mu* = 7) and H1 both hold.
Then a potential phi with cost(C -> C') >= 7 + phi(C') - phi(C) on all 81
pairs exists by LP duality. On these three codes it must equal (0, 1, 2) up to
a shift: the pairs 5/9 and 6/8 force it. The other six values come from
Bellman-Ford on cost - 7, and the full certificate will be published with the
table.

## Grading inputs

`results.json` of `sstar-stage-search-v1`: `codes2` (label of each row and
column), `matrix[i][j]` (`min`, `none_up_to`), `stats_for_verdicts.p1_mu_star`,
`p1_mu_star_lower_bound` and `p5_min_entry`. The labels A1, J1 and U0 are
`stagecore.label`'s classes. That is: two plain bits; value 1 on two adjacent
words (the pair code); and one word unused, with value 0 opposite it (binary).
