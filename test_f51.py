# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stdlib tests for job_f51.py (no PySAT or stagecore needed)."""
import unittest

import job_f51 as jf


class TestNineGateF41(unittest.TestCase):
    def test_size(self):
        self.assertEqual(len(jf.F41_NINE["gates"]), 9)

    def test_gate_order(self):
        n = jf.F41_NINE["n"]
        for idx, (j, k, f) in enumerate(jf.F41_NINE["gates"]):
            self.assertTrue(0 <= j < k < n + idx)
            self.assertEqual(f[0], 0)          # normal gates (f00 = 0)

    def test_hand_traced_rows(self):
        c = jf.F41_NINE
        self.assertEqual(jf.evaluate(c, [0, 0, 0, 0]), [1, 0, 0])   # 1
        self.assertEqual(jf.evaluate(c, [1, 1, 1, 1]), [1, 0, 1])   # 5
        self.assertEqual(jf.evaluate(c, [1, 0, 0, 0]), [0, 1, 0])   # 2
        self.assertEqual(jf.evaluate(c, [1, 1, 1, 0]), [0, 0, 1])   # 4

    def test_computes_f41_on_all_rows(self):
        self.assertTrue(jf.computes_offset(jf.F41_NINE, 4, 1))

    def test_is_not_sum4(self):
        self.assertFalse(jf.computes_offset(jf.F41_NINE, 4, 0))


class TestDuality(unittest.TestCase):
    def test_values(self):
        self.assertEqual(jf.dual_offset(4, 1), 2)
        self.assertEqual(jf.dual_offset(4, 0), 3)
        self.assertEqual(jf.dual_offset(5, 1), 1)
        self.assertEqual(jf.dual_offset(5, 0), 2)
        self.assertEqual(jf.dual_offset(6, 0), 1)

    def test_identity_on_all_rows(self):
        for k, c in ((4, 0), (4, 1), (4, 2), (4, 3), (5, 0), (5, 1), (5, 2), (6, 0), (6, 1)):
            c2 = jf.dual_offset(k, c)
            for r in range(1 << k):
                rbar = (1 << k) - 1 - r
                self.assertEqual(jf.offset_value(k, c, rbar), 7 - jf.offset_value(k, c2, r))


class TestVerdict(unittest.TestCase):
    def v(self, **kw):
        return jf.verdict(kw)

    def test_rules_free_proof(self):
        self.assertEqual(self.v(licence=True, check5="sat_verified", f51_pruned="unsat",
                                f51_plain="unsat"), "F51_GE_12_SO_SUM6_GE_14")
        self.assertEqual(self.v(licence=False, check5="not_run", f51_pruned="not_run",
                                f51_plain="unsat"), "F51_GE_12_SO_SUM6_GE_14")

    def test_proof_with_rules(self):
        self.assertEqual(self.v(licence=True, check5="sat_verified", f51_pruned="unsat",
                                f51_plain="timeout"), "F51_GE_12_SO_SUM6_GE_14_WITH_RULES")

    def test_failed_check_gives_nothing(self):
        self.assertEqual(self.v(licence=True, check5="unsat", f51_pruned="not_run",
                                f51_plain="timeout"), "UNDECIDED")

    def test_circuit_found(self):
        self.assertEqual(self.v(licence=True, check5="sat_verified", f51_pruned="sat_verified",
                                f51_plain="not_run"), "F51_LE_11")
        self.assertEqual(self.v(licence=False, check5="not_run", f51_pruned="not_run",
                                f51_plain="sat_verified"), "F51_LE_11")

    def test_conflicts(self):
        self.assertEqual(self.v(licence=True, check5="sat_verified", f51_pruned="unsat",
                                f51_plain="sat_verified"), "RULES_CONFLICT")
        self.assertEqual(self.v(licence=True, check5="sat_verified", f51_pruned="sat_verified",
                                f51_plain="unsat"), "SOLVER_CONFLICT")
        self.assertEqual(self.v(licence=True, check5="sat_verified", f51_pruned="sat_BAD",
                                f51_plain="not_run"), "BUG_UNVERIFIED_CIRCUIT")


if __name__ == "__main__":
    unittest.main()
