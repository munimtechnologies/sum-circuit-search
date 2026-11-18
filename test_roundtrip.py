# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stdlib tests for roundtrip.py (the round-trip barrier, THEORY-ROUNDTRIP.md).
Every expected value below was worked out by hand first."""
import itertools
import unittest
from fractions import Fraction

import roundtrip as rt
import verify_layers as vl

# (pack, dec) per class, derived by hand in THEORY-ROUNDTRIP.md
EXPECTED = {
    "A1": (0, 2), "J1": (1, 1), "U0": (2, 0),
    "U1": (2, 1), "U2": (2, 1), "J2": (2, 1),
    "A0": (2, 2), "A2": (2, 2), "J0": (2, 2),
}


class TestTables(unittest.TestCase):
    def test_sixty_tables_nine_classes(self):
        tabs = rt.all_tables()
        self.assertEqual(len(tabs), 60)
        counts = {}
        for t in tabs:
            lab = vl.label(t)
            counts[lab] = counts.get(lab, 0) + 1
        self.assertEqual(counts, {"U0": 8, "U1": 8, "U2": 8, "A0": 4, "A1": 4, "A2": 4,
                                  "J0": 8, "J1": 8, "J2": 8})

    def test_achievable_pairs(self):
        best = rt.achievable_pairs()
        self.assertEqual(rt.IN1, 0b1010)
        self.assertEqual(rt.IN2, 0b1100)
        self.assertEqual(best[(rt.IN1, rt.IN2)], 0)            # (u, v)
        self.assertEqual(best[(rt.IN2 ^ 15, 0)], 0)            # (not v, 0)
        self.assertEqual(best[(rt.IN1, 0b0110)], 1)            # (u, u^v)
        self.assertEqual(best[(0b0110, 0b1000)], 2)            # half adder (u^v, u&v)
        self.assertEqual(best[(0b1000, 0b0001)], 2)            # (u&v, nor)

    def test_known_pack_and_dec(self):
        best = rt.achievable_pairs()
        a1, j1, u0 = vl.CODES["A1"], vl.CODES["J1"], vl.CODES["U0"]
        self.assertTrue(rt.pack_ok(a1, rt.IN1, rt.IN2))
        self.assertTrue(rt.pack_ok(j1, rt.IN1, 0b0110))
        self.assertTrue(rt.pack_ok(u0, 0b0110, 0b1000))
        self.assertFalse(rt.pack_ok(u0, rt.IN1, rt.IN2))
        self.assertTrue(rt.dec_ok(u0, rt.IN1, rt.IN2))         # binary: free
        self.assertTrue(rt.dec_ok(j1, rt.IN2, 0b0010))         # (w2, w1 & ~w2)
        self.assertTrue(rt.dec_ok(a1, 0b0110, 0b1000))
        self.assertEqual(rt.min_cost(a1, rt.pack_ok, best), 0)
        self.assertEqual(rt.min_cost(u0, rt.dec_ok, best), 0)

    def test_class_costs(self):
        classes = rt.class_costs()
        got = {c: (v["pack"], v["dec"]) for c, v in classes.items()}
        self.assertEqual(got, EXPECTED)
        for v in classes.values():
            self.assertGreaterEqual(v["rt"], 2)      # pack then dec is a half adder
        self.assertEqual(sorted(c for c, v in classes.items() if v["rt"] == 2), ["A1", "J1", "U0"])

    def test_phi_is_pack_on_rt2_classes(self):
        classes = rt.class_costs()
        for c in ("A1", "J1", "U0"):
            self.assertEqual(classes[c]["pack"], vl.PHI[c])
            self.assertEqual(classes[c]["dec"], 2 - vl.PHI[c])

    def test_lb_matrix_matches_conservation_law(self):
        classes = rt.class_costs()
        labs, w = rt.lb_matrix(classes)
        idx = {c: i for i, c in enumerate(labs)}
        for a, b in itertools.product(("A1", "J1", "U0"), repeat=2):
            self.assertEqual(w[idx[a]][idx[b]], 7 + vl.PHI[b] - vl.PHI[a])
            self.assertEqual(w[idx[a]][idx[b]], len(vl.LAYERS[(a, b)]["gates"]))
        self.assertEqual(w[idx["A0"]][idx["A0"]], 5)
        self.assertEqual(w[idx["U0"]][idx["A1"]], 5)

    def test_min_mean_cycles(self):
        classes = rt.class_costs()
        labs, w = rt.lb_matrix(classes)
        self.assertEqual(rt.min_mean_cycle(w), Fraction(5))
        rt3 = {c for c in labs if classes[c]["rt"] <= 3}
        rt2 = {c for c in labs if classes[c]["rt"] == 2}
        self.assertEqual(rt.min_mean_cycle(rt.restricted(labs, w, rt3)), Fraction(6))
        self.assertEqual(rt.min_mean_cycle(rt.restricted(labs, w, rt2)), Fraction(7))
        self.assertEqual(rt.min_mean_cycle([[3, None], [None, 5]]), Fraction(3))
        self.assertEqual(rt.min_mean_cycle([[None, 1], [4, None]]), Fraction(5, 2))

    def test_sandwiches_are_9_gate_sum4_circuits(self):
        for (a, b) in vl.LAYERS:
            good, size = rt.sandwich(a, b)
            self.assertTrue(good, (a, b))
            self.assertEqual(size, 9, (a, b))

    def test_chains_meet_bound_exactly(self):
        classes = rt.class_costs()
        for L in (1, 2, 3):
            for tail in itertools.product(sorted(vl.CODES), repeat=L):
                codes = ("A1",) + tail
                correct, size = vl.check_chain(codes)
                self.assertTrue(correct)
                self.assertEqual(rt.chain_lower_bound(codes, classes), 7 * L + 2)
                self.assertEqual(size, 7 * L + 2)

    def test_chain_bound_with_costly_codes(self):
        classes = rt.class_costs()
        # 3 layers with internal cuts A0 (rt 4) and U1 (rt 3): 27 - 0 - 7 = 20
        self.assertEqual(rt.chain_lower_bound(("A1", "A0", "U1", "J1"), classes), 20)


if __name__ == "__main__":
    unittest.main()
