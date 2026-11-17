# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stdlib-only tests for search 4 (s* layered stages). Every expected value
was worked out by hand (see the comments)."""
import unittest
from fractions import Fraction

import job_stage as js
import stagecore as sc


class TestCodes(unittest.TestCase):
    def test_two_wire_classes(self):
        codes, total = sc.carry_codes(2)
        # maps {4 words} -> {0,1,2,unused} hitting 0, 1, 2: 4^4 - 3*3^4 + 3*2^4 - 1 = 60
        self.assertEqual(total, 60)
        # 3 classes with an unused word, 3 with a doubled value on opposite words,
        # 3 with a doubled value on adjacent words
        self.assertEqual(len(codes), 9)
        self.assertEqual(sorted(sc.label(t) for t in codes),
                         ["A0", "A1", "A2", "J0", "J1", "J2", "U0", "U1", "U2"])
        seen = 0
        for t in codes:
            orb = sc.orbit(t, 2)
            self.assertEqual(t, min(orb))
            self.assertEqual(len(set(sc.label(u) for u in orb)), 1)
            seen += len(orb)
        self.assertEqual(seen, 60)

    def test_named_labels(self):
        self.assertEqual(sc.label(sc.DCODE[1]), "J1")      # (p, p^q)
        self.assertEqual(sc.label(sc.SUM2[1]), "A1")       # two plain bits
        self.assertEqual(sc.label((0, 1, 2, sc.UNUSED)), "U0")   # binary 2*b1 + b0
        self.assertEqual(sc.label((0, 1, sc.UNUSED, 2)), "U1")   # thermometer

    def test_three_wire_total(self):
        _codes, total = sc.carry_codes(3)
        # 4^8 - 3*3^8 + 3*2^8 - 1 = 65536 - 19683 + 768 - 1
        self.assertEqual(total, 46620)


class TestRelations(unittest.TestCase):
    def test_stage_row(self):
        n, m, rows = sc.stage_relation(sc.DCODE, sc.DCODE)
        self.assertEqual((n, m, len(rows)), (4, 3, 16))
        d = dict(rows)
        # r = 7: x = 1, y = 1, p = 1, w = 0 -> carry word 1 -> value 2; total 4
        # -> s = 0 and carry 2, whose only word is index 1 (b0 = 1, b1 = 0)
        self.assertEqual(d[7], frozenset([(0, 1, 0)]))
        for _r, allowed in rows:
            self.assertTrue(allowed)

    def test_unused_rows_dropped(self):
        n, m, rows = sc.stage_relation((2, (0, 1, 2, sc.UNUSED)), sc.DCODE)
        self.assertEqual(len(rows), 12)
        for r, _a in rows:
            self.assertNotEqual(r >> 2, 3)

    def test_two_layer_shape(self):
        n, m, rows = sc.stage_relation(sc.DCODE, sc.DCODE, 2)
        self.assertEqual((n, m, len(rows)), (6, 4, 64))

    def test_decode_and_sum(self):
        n, m, rows = sc.decode_relation(sc.DCODE)
        self.assertEqual((n, m, len(rows)), (2, 2, 4))
        self.assertEqual(dict(rows)[1], frozenset([(0, 1)]))   # (1, 0) means 2
        n, m, rows = sc.sum_relation(3, 2)
        self.assertEqual((n, m, len(rows)), (3, 2, 8))

    def test_spec_round_trip(self):
        a = sc.relation_from_spec(js.rel_stage(sc.DCODE, sc.DCODE))
        b = sc.stage_relation(sc.DCODE, sc.DCODE)
        self.assertEqual(a, b)


def explicit_cases():
    return [
        (sc.stage_relation(sc.DCODE, sc.DCODE), sc.STAGE_D, 7),
        (sc.stage_relation(sc.SUM2, sc.SUM2), sc.STAGE_SUM2, 7),
        (sc.stage_relation(sc.SUM2, sc.DCODE), sc.START_SUM2_D, 8),
        (sc.decode_relation(sc.DCODE), sc.DECODE_D, 1),
        (sc.sum_relation(3, 2), sc.FULL_ADDER, 5),
    ]


class TestExplicit(unittest.TestCase):
    def test_known_circuits(self):
        for (n, m, rows), circ, size in explicit_cases():
            self.assertEqual(len(circ["gates"]), size)
            self.assertTrue(sc.check_relation(n, m, rows, circ), size)

    def test_broken_rejected(self):
        bad = dict(sc.STAGE_D)
        bad["outs"] = [[8, 0], [10, 0], [6, 0]]    # carry wires swapped
        n, m, rows = sc.stage_relation(sc.DCODE, sc.DCODE)
        self.assertFalse(sc.check_relation(n, m, rows, bad))

    def test_stack(self):
        two = sc.stack(sc.STAGE_D, sc.STAGE_D)
        self.assertEqual(len(two["gates"]), 14)
        n, m, rows = sc.stage_relation(sc.DCODE, sc.DCODE, 2)
        self.assertTrue(sc.check_relation(n, m, rows, two))


class TestCNF(unittest.TestCase):
    def test_known_circuits_satisfy(self):
        for (n, m, rows), circ, size in explicit_cases():
            e = sc.encode_relation(n, m, rows, size)
            asg = sc.assignment_from_circuit(e, circ)
            self.assertEqual(len(asg), e.nvars)
            self.assertEqual(sc.unsatisfied(e.clauses, asg), [], size)


class TestCompose(unittest.TestCase):
    def test_gkl_counts(self):
        for L in (1, 2, 3):
            c = js.compose(sc.START_SUM2_D, [sc.STAGE_D] * L, 1, sc.DECODE_D)
            # 8 (layer 0) + 7 per layer + 1 (decode); n = 4 + 2L
            self.assertEqual(c, {"stage_layers": L, "n": 4 + 2 * L,
                                 "size": 7 * L + 9, "ok": True})

    def test_cycle_and_two_layer(self):
        c = js.compose_cycle({0: sc.START_SUM2_D}, {(0, 0): sc.STAGE_D},
                             {0: sc.DECODE_D}, [0], 2)
        self.assertEqual(c["size"], 23)
        self.assertTrue(c["ok"])
        two = sc.stack(sc.STAGE_D, sc.STAGE_D)
        c2 = js.compose(sc.START_SUM2_D, [two], 2, sc.DECODE_D)
        self.assertEqual((c2["n"], c2["size"], c2["ok"]), (8, 23, True))
        self.assertIsNone(js.compose_cycle({}, {}, {}, [0], 1))

    def test_code_mismatch_fails(self):
        # layer 0 writes the D code; a SUM2 stage reads it as two plain bits
        c = js.compose(sc.START_SUM2_D, [sc.STAGE_SUM2], 1, sc.DECODE_D)
        self.assertFalse(c["ok"])


class TestCycles(unittest.TestCase):
    def test_karp(self):
        self.assertEqual(sc.min_mean_cycle([[7, 6], [6, 7]]), Fraction(6))
        self.assertEqual(sc.min_mean_cycle([[5, None], [None, 9]]), Fraction(5))
        self.assertIsNone(sc.min_mean_cycle([[None, 1], [None, None]]))

    def test_short_cycle(self):
        self.assertEqual(sc.best_short_cycle([[7, 6], [6, 7]]), (Fraction(6), [0, 1]))
        self.assertEqual(sc.best_short_cycle([[7, None], [None, 7]]), (Fraction(7), [0]))
        self.assertIsNone(sc.best_short_cycle([[None, 1], [None, None]]))


if __name__ == "__main__":
    unittest.main()
