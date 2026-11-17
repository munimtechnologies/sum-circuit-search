# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stdlib tests for verify_layers.py (the hand-built s* layers of THEORY-SSTAR.md)."""
import itertools
import unittest

import verify_layers as v


class TestHandLayers(unittest.TestCase):
    def test_labels(self):
        for name, table in v.CODES.items():
            self.assertEqual(v.label(table), name)

    def test_layers_correct_and_phi(self):
        self.assertEqual(len(v.LAYERS), 9)
        for (cin, cout), circ in v.LAYERS.items():
            self.assertTrue(v.check_layer(cin, cout, circ), (cin, cout))
            self.assertEqual(len(circ["gates"]), 7 + v.PHI[cout] - v.PHI[cin], (cin, cout))

    def test_pass_through_layer_is_a_full_adder(self):
        circ = v.LAYERS[("U0", "A1")]
        self.assertEqual(len(circ["gates"]), 5)
        self.assertIn("E", circ["outs"])

    def test_decoders(self):
        for code, circ in v.DECODERS.items():
            self.assertTrue(v.check_decoder(code, circ), code)
            self.assertEqual(len(circ["gates"]), 2 - v.PHI[code])

    def test_chains_cost_7L_plus_2(self):
        for L in range(1, 4):
            for tail in itertools.product(sorted(v.CODES), repeat=L):
                ok, size = v.check_chain(("A1",) + tail)
                self.assertTrue(ok, tail)
                self.assertEqual(size, 7 * L + 2, tail)

    def test_broken_layer_is_caught(self):
        circ = dict(v.LAYERS[("U0", "U0")])
        circ["outs"] = ["s", "e2", "d2"]   # carry wires swapped
        self.assertFalse(v.check_layer("U0", "U0", circ))
        circ = dict(v.LAYERS[("J1", "A1")])
        circ["outs"] = ["s", "m", "R"]     # wrong pass-through
        self.assertFalse(v.check_layer("J1", "A1", circ))


if __name__ == "__main__":
    unittest.main()
