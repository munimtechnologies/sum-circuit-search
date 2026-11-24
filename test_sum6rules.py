# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stdlib tests for sum6rules.py. Tests marked 'real' need stagecore.py
(downloaded by the job) and are skipped without it."""
import unittest

import sum6rules as sr

try:
    import stagecore as sc
    HAVE_SC = hasattr(sc, "assignment_from_circuit") and hasattr(sc, "unsatisfied")
except ImportError:
    sc = None
    HAVE_SC = False

XOR = [0, 1, 1, 0]
AND = [0, 0, 0, 1]
OR = [0, 1, 1, 1]
FPQ = ((0, 1), (1, 0), (1, 1))


class FakeE:
    """Only the selector, function and output-source variables of the CNF."""

    def __init__(self, n, m, s):
        self.n, self.m, self.s = n, m, s
        self.nvars = 0
        self.first, self.second, self.f, self.src = {}, {}, {}, {}
        for g in range(n, n + s):
            for j in range(g):
                self.first[g, j] = self._v()
                self.second[g, j] = self._v()
            for pq in FPQ:
                self.f[g, pq] = self._v()
        for o in range(m):
            for v in [-1] + list(range(n + s)):
                self.src[o, v] = self._v()

    def _v(self):
        self.nvars += 1
        return self.nvars


def asg_of(e, circ):
    a = {}
    for (g, j), v in e.first.items():
        a[v] = circ["gates"][g - e.n][0] == j
    for (g, j), v in e.second.items():
        a[v] = circ["gates"][g - e.n][1] == j
    for (g, pq), v in e.f.items():
        a[v] = circ["gates"][g - e.n][2][2 * pq[0] + pq[1]] == 1
    for (o, u), v in e.src.items():
        a[v] = circ["outs"][o][0] == u
    return a


HALF_ADDER = {"n": 2, "gates": [[0, 1, XOR], [0, 1, AND]], "outs": [[2, 0], [3, 0]]}
FULL_ADDER = {"n": 3, "gates": [[0, 1, XOR], [0, 2, XOR], [2, 3, XOR], [3, 4, AND], [0, 6, XOR]],
              "outs": [[5, 0], [7, 0]]}


class TestRelation(unittest.TestCase):
    def test_offset(self):
        n, m, rows = sr.offset_relation(4, 1, 3)
        self.assertEqual((n, m, len(rows)), (4, 3, 16))
        self.assertEqual(rows[0], (0, frozenset({(1, 0, 0)})))
        self.assertEqual(rows[15], (15, frozenset({(1, 0, 1)})))
        n, m, rows = sr.offset_relation(2, 0, 2)
        self.assertEqual(rows[3], (3, frozenset({(0, 1)})))


class TestRulesFake(unittest.TestCase):
    def test_half_adder_breaks_const_rule(self):
        e = FakeE(2, 2, 2)
        a = asg_of(e, HALF_ADDER)
        for x in (0, 1):
            self.assertEqual(sr.violated(sr.outdeg_clauses(e, x, 2), a), [])
        self.assertEqual(sr.violated(sr.symmetry_clauses(e), a), [])
        # the AND gate (node 3) is constant at x0 = 0 but is an output
        self.assertTrue(sr.violated(sr.const_clauses(e, 3, 0, 0), a))
        self.assertTrue(sr.violated(sr.rule_clauses(e, 2, (0,)), a))

    def test_and_then_xor_obeys_all_rules(self):
        circ = {"n": 3, "gates": [[0, 1, AND], [2, 3, XOR]], "outs": [[4, 0]]}
        e = FakeE(3, 1, 2)
        a = asg_of(e, circ)
        self.assertEqual(sr.violated(sr.rule_clauses(e, 2, (0, 1)), a), [])

    def test_second_reader_of_x(self):
        circ = {"n": 3, "gates": [[0, 1, AND], [2, 3, XOR], [0, 4, XOR]], "outs": [[5, 0]]}
        e = FakeE(3, 1, 3)
        a = asg_of(e, circ)
        self.assertEqual(sr.violated(sr.outdeg_clauses(e, 0, 2), a), [])
        self.assertTrue(sr.violated(sr.const_clauses(e, 3, 0, 0), a))

    def test_two_readers_of_constant_gate(self):
        circ = {"n": 3, "gates": [[0, 1, AND], [2, 3, XOR], [3, 4, XOR]], "outs": [[5, 0]]}
        e = FakeE(3, 1, 3)
        a = asg_of(e, circ)
        self.assertTrue(sr.violated(sr.const_clauses(e, 3, 0, 0), a))

    def test_rule_at_one(self):
        # OR(x0, x1) is constant once x0 = 1, and x0 is read again
        circ = {"n": 2, "gates": [[0, 1, OR], [0, 2, XOR]], "outs": [[3, 0]]}
        e = FakeE(2, 1, 2)
        a = asg_of(e, circ)
        self.assertEqual(sr.violated(sr.rule_clauses(e, 2, (0,)), a), [])
        self.assertTrue(sr.violated(sr.rule_clauses(e, 2, (0, 1)), a))

    def test_fanout_three(self):
        e = FakeE(3, 2, 5)
        a = asg_of(e, FULL_ADDER)
        self.assertTrue(sr.violated(sr.outdeg_clauses(e, 0, 2), a))
        self.assertEqual(sr.violated(sr.outdeg_clauses(e, 0, 3), a), [])


@unittest.skipUnless(HAVE_SC, "stagecore.py not present")
class TestRulesReal(unittest.TestCase):
    def test_half_adder_real(self):
        n, m, rows = sc.sum_relation(2, 2)
        e = sc.encode_relation(n, m, rows, 2, all_used=True)
        a = sc.assignment_from_circuit(e, HALF_ADDER)
        self.assertEqual(sc.unsatisfied(e.clauses, a), [])
        self.assertTrue(sr.violated(sr.rule_clauses(e, 2, (0,)), a))

    def test_full_adder_real(self):
        n, m, rows = sc.sum_relation(3, 2)
        e = sc.encode_relation(n, m, rows, 5, all_used=True)
        a = sc.assignment_from_circuit(e, FULL_ADDER)
        self.assertEqual(sc.unsatisfied(e.clauses, a), [])
        self.assertTrue(sr.violated(sr.outdeg_clauses(e, 0, 2), a))
        self.assertEqual(sr.violated(sr.outdeg_clauses(e, 0, 3), a), [])
        self.assertEqual(sr.violated(sr.symmetry_clauses(e), a), [])

    def test_offset_matches_sum(self):
        self.assertEqual(sr.offset_relation(5, 0, 3), sc.sum_relation(5, 3))


if __name__ == "__main__":
    unittest.main()
