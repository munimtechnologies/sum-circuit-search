# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stdlib tests for blocks_sandwich.py. Every expected value was worked out by
hand (THEORY-BLOCKS.md shows the arithmetic)."""
import unittest
from fractions import Fraction as F

import blocks_sandwich as bs


class TestDecoders(unittest.TestCase):
    def test_all_correct(self):
        for name, rep in bs.REPS.items():
            self.assertTrue(bs.decoder_ok(rep), name)

    def test_sizes(self):
        sizes = {n: len(r["decoder"]["gates"]) for n, r in bs.REPS.items()}
        self.assertEqual(sizes, {"P": 0, "D": 1, "P+P": 2, "P+P@1": 0, "P+D": 4, "P+P+P": 5})

    def test_phi_minus_dec(self):
        got = {n: bs.rep_cost(n) for n in bs.REPS}
        self.assertEqual(got, {"P": F(9, 2), "D": F(7), "P+P": F(7), "P+P@1": F(9),
                               "P+D": F(17, 2), "P+P+P": F(17, 2)})

    def test_max_values(self):
        got = {n: bs.max_value(r["groups"]) for n, r in bs.REPS.items()}
        self.assertEqual(got, {"P": 1, "D": 2, "P+P": 2, "P+P@1": 3, "P+D": 3, "P+P+P": 3})

    def test_wrong_decoder_is_caught(self):
        bad = {"groups": [("D", 0)], "decoder": {"n": 2, "gates": [], "outs": [[0, 0], [1, 0]]}}
        self.assertFalse(bs.decoder_ok(bad))


class TestKnownBlocks(unittest.TestCase):
    UNITS = {"full_adder": 3, "stockmeyer": 3, "mdfa": 5, "mdfa_prime": 4,
             "pair_xor": 2, "unpair": 2}
    SLACK = {"full_adder": F(-1, 2), "stockmeyer": F(-1, 2), "mdfa": F(0),
             "mdfa_prime": F(-5, 2), "pair_xor": F(0), "unpair": F(-2)}

    def test_units(self):
        self.assertEqual({n: bs.units_in(b) for n, b in bs.KNOWN.items()}, self.UNITS)

    def test_slacks(self):
        self.assertEqual({n: bs.block_slack(b) for n, b in bs.KNOWN.items()}, self.SLACK)

    def test_bound_is_tight(self):
        self.assertEqual({n: bs.block_bound(b) for n, b in bs.KNOWN.items()}, self.SLACK)

    def test_sandwiches_compute_sum_k_with_s_k_gates(self):
        expected = {"full_adder": 5, "stockmeyer": 5, "mdfa": 11, "mdfa_prime": 9,
                    "pair_xor": 2, "unpair": 2}
        for name, block in bs.KNOWN.items():
            good, size = bs.sandwich(block)
            self.assertTrue(good, name)
            self.assertEqual(size, expected[name], name)

    def test_broken_block_is_caught(self):
        broken = dict(bs.KNOWN["mdfa"])
        circ = dict(broken["circuit"])
        circ["outs"] = [circ["outs"][0], circ["outs"][2], circ["outs"][1]]   # swap the D wires
        broken["circuit"] = circ
        self.assertFalse(bs.sandwich(broken)[0])


class TestReducedTable(unittest.TestCase):
    def test_constants(self):
        got = {k: bs.reduced_constant(k) for k in range(2, 8)}
        self.assertEqual(got, {2: F(0), 3: F(9, 2), 4: F(13, 2), 5: F(11), 6: F(14), 7: F(37, 2)})

    def test_exact_cases_have_no_profitable_block(self):
        got = {k: bs.reduced_constant(k) - bs.SUM_EXACT[k] for k in range(2, 6)}
        self.assertEqual(got, {2: F(-2), 3: F(-1, 2), 4: F(-5, 2), 5: F(0)})

    def test_thresholds(self):
        self.assertEqual(bs.largest_profitable(bs.reduced_constant(6)), 13)
        self.assertEqual(bs.largest_profitable(bs.reduced_constant(7)), 18)

    def test_plain_blocks(self):
        got = {k: bs.largest_profitable(bs.plain_slack_constant(k)) for k in (5, 6, 7, 9, 11, 15)}
        self.assertEqual(got, {5: 8, 6: 13, 7: 17, 9: 22, 11: 31, 15: 49})


if __name__ == "__main__":
    unittest.main()
