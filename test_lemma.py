# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stdlib tests for lemma.py. Every expected value is worked out by hand in a
comment (potentials P = 9/2, D = 8)."""
import unittest
from fractions import Fraction as F

import lemma

P0, D0, P1, D1, P2, D2 = ("P", 0), ("D", 0), ("P", 1), ("D", 1), ("P", 2), ("D", 2)


class TestKnownBlocks(unittest.TestCase):
    def test_slacks(self):
        # pairing XOR: 9 - 8 - 1 = 0
        self.assertEqual(lemma.slack([P0, P0], [D0], 1), 0)
        # MDFA: (9/2 + 16) - (9/2 + 8) - 8 = 0
        self.assertEqual(lemma.slack([P0, D0, D0], [P0, D1], 8), 0)
        # full adder: 27/2 - 9 - 5 = -1/2
        self.assertEqual(lemma.slack([P0, P0, P0], [P0, P1], 5), F(-1, 2))
        # Stockmeyer: 25/2 - 9 - 4 = -1/2
        self.assertEqual(lemma.slack([P0, D0], [P0, P1], 4), F(-1, 2))
        # MDFA': 16 - 25/2 - 6 = -5/2
        self.assertEqual(lemma.slack([D0, D0], [P0, D1], 6), F(-5, 2))

    def test_known_blocks_give_nothing(self):
        for ins, outs, size in (([P0, P0], [D0], 1), ([P0, D0, D0], [P0, D1], 8),
                                ([P0, P0, P0], [P0, P1], 5), ([P0, D0], [P0, P1], 4),
                                ([D0, D0], [P0, D1], 6)):
            self.assertEqual(lemma.epsilon(ins, outs, size), 0)
            self.assertEqual(lemma.gamma_bound(ins, outs, size), F(9, 2))


class TestHypothetical(unittest.TestCase):
    def test_seven_gate_mdfa(self):
        # slack 1; p0 = 1, d0 = 2, d1 = 0, delta = 0 -> R = 1 + 4 = 5 -> 1/5
        ins, outs = [P0, D0, D0], [P0, D1]
        self.assertEqual(lemma.slack(ins, outs, 7), 1)
        self.assertEqual(lemma.rate_denominator(ins, outs), 5)
        self.assertEqual(lemma.epsilon(ins, outs, 7), F(1, 5))
        self.assertEqual(lemma.gamma_bound(ins, outs, 7), F(43, 10))

    def test_long_shot_1(self):
        # P@0+D@0+D@0+P@1+D@1 -> P@0+P@1+D@2: phi 33 -> 17, drop 16.
        # k1 = 1, k1_out = 1 -> delta 0; R = 4*1 + 0 + 1 + 2*2 = 9.
        ins, outs = [P0, D0, D0, P1, D1], [P0, P1, D2]
        self.assertEqual(lemma.slack(ins, outs, 16), 0)
        self.assertEqual(lemma.delta(ins, outs), 0)
        self.assertEqual(lemma.rate_denominator(ins, outs), 9)
        self.assertEqual(lemma.epsilon(ins, outs, 16), 0)
        self.assertEqual(lemma.epsilon(ins, outs, 15), F(1, 9))

    def test_long_shot_2(self):
        # P@0+D@0+D@0+P@1+P@1+P@1 -> P@0+P@1+D@2: phi 34 -> 17, drop 17.
        # k1 = 3, k1_out = 1 -> delta 2; at 16 gates gain = 1 - 1 = 0 (no claim);
        # at 15 gates gain = 2 - 1 = 1, R = 0 + 4 + 1 + 4 = 9 -> 1/9.
        ins, outs = [P0, D0, D0, P1, P1, P1], [P0, P1, D2]
        self.assertEqual(lemma.slack(ins, outs, 17), 0)
        self.assertEqual(lemma.delta(ins, outs), 2)
        self.assertEqual(lemma.gain(ins, outs, 16), 0)
        self.assertEqual(lemma.epsilon(ins, outs, 16), 0)
        self.assertEqual(lemma.rate_denominator(ins, outs), 9)
        self.assertEqual(lemma.epsilon(ins, outs, 15), F(1, 9))

    def test_mdfa_pass(self):
        # P@0+D@0+D@0+P@1 -> P@0+P@1+D@1: phi 25 -> 17, drop 8; delta 0, R = 5.
        ins, outs = [P0, D0, D0, P1], [P0, P1, D1]
        self.assertEqual(lemma.slack(ins, outs, 8), 0)
        self.assertEqual(lemma.epsilon(ins, outs, 7), F(1, 5))

    def test_shift_invariance(self):
        ins = [("P", 3), ("D", 3), ("D", 3), ("P", 4), ("D", 4)]
        outs = [("P", 3), ("P", 4), ("D", 5)]
        self.assertEqual(lemma.counts(ins, outs)["base"], 3)
        self.assertEqual(lemma.epsilon(ins, outs, 15), F(1, 9))


class TestScope(unittest.TestCase):
    def test_three_columns_rejected(self):
        with self.assertRaises(ValueError):
            lemma.counts([P0, P2], [D1])

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            lemma.counts([], [P0])


if __name__ == "__main__":
    unittest.main()
