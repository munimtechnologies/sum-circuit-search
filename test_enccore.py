# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stdlib-only tests for search 2: general encodings, the classification of
linear 3-bit encodings (checked against a hand derivation), shapes, and that
the CNF accepts known circuits and rejects broken ones."""
import copy
import unittest

import enccore as ec
import known_blocks as kb

P0, P1, D0, D1 = ("P", 0), ("P", 1), ("D", 0), ("D", 1)
XOR = [0, 1, 1, 0]

# Hand derivation: three independent rows over (p, q, r), up to row and
# column permutations, give 7 classes; 2 are P+P+P (identity) and P+D.
# The 5 others, as row bit masks (p = 1, q = 2, r = 4):
HAND_INDECOMPOSABLE = {
    "p, q, p^q^r": (1, 2, 7),
    "p, p^q, p^r (star)": (1, 3, 5),
    "p, p^q, q^r (path)": (1, 3, 6),
    "p, p^q, p^q^r (prefix)": (1, 3, 7),
    "p^q, p^r, p^q^r": (3, 5, 7),
}

ec.register("TSTAR", 3, ec.linear_table((1, 3, 5)), "p, p^q, p^r")
T0, T1 = ("TSTAR", 0), ("TSTAR", 1)
PHI = {"P": 9, "D": 16, "TSTAR": 23}


def pppt():
    """P+P+P -> TSTAR: (p, p^q, p^r) with 2 XORs."""
    return {"n": 3, "gates": [[0, 1, XOR], [0, 2, XOR]], "outs": [[0, 0], [3, 0], [4, 0]]}


def pdt():
    """P(r) + D(p, p^q) -> TSTAR: only p^r is new, 1 XOR."""
    return {"n": 3, "gates": [[0, 1, XOR]], "outs": [[1, 0], [2, 0], [3, 0]]}


class TestSemantics(unittest.TestCase):
    def test_pair_values(self):
        self.assertEqual(ec.group_value("D", [0, 0]), 0)
        self.assertEqual(ec.group_value("D", [0, 1]), 1)
        self.assertEqual(ec.group_value("D", [1, 1]), 1)
        self.assertEqual(ec.group_value("D", [1, 0]), 2)

    def test_weighted_value(self):
        self.assertEqual(ec.value([P0, D1], [1, 1, 0]), 5)

    def test_star_table(self):
        for x in range(8):
            p, q, r = x & 1, (x >> 1) & 1, (x >> 2) & 1
            self.assertEqual(ec.group_value("TSTAR", [p, p ^ q, p ^ r]), p + q + r)


class TestLinearClasses(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(ec.linear_classes(1)), 1)
        self.assertEqual(len(ec.linear_classes(2)), 2)
        self.assertEqual(len(ec.linear_classes(3)), 7)
        self.assertEqual(len(ec.indecomposable_linear_classes(2)), 1)
        self.assertEqual(len(ec.indecomposable_linear_classes(3)), 5)

    def test_d_is_the_only_new_two_bit_code(self):
        (canon, _rows), = ec.indecomposable_linear_classes(2)
        self.assertEqual(canon, ec.canonical(ec.linear_table((3, 1)), 2))
        self.assertEqual(canon, ec.canonical(ec.ENC["D"]["table"], 2))

    def test_matches_hand_derivation(self):
        got = set(c for c, _ in ec.indecomposable_linear_classes(3))
        hand = set(ec.canonical(ec.linear_table(r), 3) for r in HAND_INDECOMPOSABLE.values())
        self.assertEqual(len(hand), 5)
        self.assertEqual(got, hand)

    def test_decomposable_ones(self):
        k, ppp = ec.product_table([(1, (0, 1))] * 3)
        k2, pd = ec.product_table([(1, (0, 1)), (2, ec.ENC["D"]["table"])])
        self.assertEqual((k, k2), (3, 3))
        self.assertEqual(ec.canonical(ec.linear_table((1, 2, 4)), 3), ec.canonical(ppp, 3))
        self.assertEqual(ec.canonical(ec.linear_table((1, 3, 4)), 3), ec.canonical(pd, 3))
        got = set(c for c, _ in ec.indecomposable_linear_classes(3))
        self.assertNotIn(ec.canonical(ppp, 3), got)
        self.assertNotIn(ec.canonical(pd, 3), got)

    def test_canonical_invariant(self):
        t = ec.linear_table((1, 3, 7))
        self.assertEqual(ec.canonical(ec.transform(t, 3, (2, 0, 1), 5), 3), ec.canonical(t, 3))

    def test_register_linear(self):
        names = ec.register_linear(3)
        self.assertEqual(names, ["L3a", "L3b", "L3c", "L3d", "L3e"])
        for nm in names:
            self.assertEqual(ec.ENC[nm]["k"], 3)
            self.assertEqual(sorted(ec.ENC[nm]["table"]), [0, 1, 1, 1, 2, 2, 2, 3])
        hand = set(ec.canonical(ec.linear_table(r), 3) for r in HAND_INDECOMPOSABLE.values())
        self.assertEqual(set(ec.canonical(ec.ENC[nm]["table"], 3) for nm in names), hand)


class TestCircuits(unittest.TestCase):
    def test_known_blocks(self):
        for name, blk in kb.ALL.items():
            ok, row = ec.check(blk["inputs"], blk["outputs"], blk["circuit"])
            self.assertTrue(ok, "%s fails at row %s" % (name, row))

    def test_star_creation(self):
        self.assertTrue(ec.check([P0, P0, P0], [T0], pppt())[0])
        self.assertTrue(ec.check([P0, D0], [T0], pdt())[0])

    def test_broken_star_rejected(self):
        circ = pdt()
        circ["outs"][2] = [0, 0]   # r instead of p^r
        self.assertFalse(ec.check([P0, D0], [T0], circ)[0])


class TestEncoding(unittest.TestCase):
    def test_known_circuits_satisfy_cnf(self):
        for name, blk in kb.ALL.items():
            circ = blk["circuit"]
            e = ec.encode(blk["inputs"], blk["outputs"], len(circ["gates"]))
            asg = ec.assignment_from_circuit(e, circ)
            self.assertEqual(len(asg), e.nvars, name)
            self.assertEqual(ec.unsatisfied(e.clauses, asg), [], name)

    def test_star_creation_satisfies_cnf(self):
        for ins, circ in (([P0, P0, P0], pppt()), ([P0, D0], pdt())):
            e = ec.encode(ins, [T0], len(circ["gates"]))
            asg = ec.assignment_from_circuit(e, circ)
            self.assertEqual(len(asg), e.nvars)
            self.assertEqual(ec.unsatisfied(e.clauses, asg), [])

    def test_decode_roundtrip(self):
        circ = pdt()
        e = ec.encode([P0, D0], [T0], 1)
        asg = ec.assignment_from_circuit(e, circ)
        model = [v if asg[v] else -v for v in range(1, e.nvars + 1)]
        self.assertEqual(ec.decode(e, model), circ)

    def test_wrong_star_violates_cnf(self):
        circ = pppt()
        circ["outs"] = [circ["outs"][1], circ["outs"][0], circ["outs"][2]]
        self.assertFalse(ec.check([P0, P0, P0], [T0], circ)[0])
        e = ec.encode([P0, P0, P0], [T0], 2)
        asg = ec.assignment_from_circuit(e, circ)
        self.assertNotEqual(ec.unsatisfied(e.clauses, asg), [])

    def test_broken_mdfa_violates_cnf(self):
        circ = copy.deepcopy(kb.MDFA["circuit"])
        circ["gates"][6][2] = [0, 0, 0, 1]
        e = ec.encode(kb.MDFA["inputs"], kb.MDFA["outputs"], 8)
        asg = ec.assignment_from_circuit(e, circ)
        self.assertNotEqual(ec.unsatisfied(e.clauses, asg), [])

    def test_zero_gate_instance_size(self):
        e = ec.encode([P0, P0], [D0], 0)
        self.assertEqual(e.nvars, 2 * (3 + 1 + 4))


class TestShapes(unittest.TestCase):
    def setUp(self):
        self.shapes = ec.e_shapes("TSTAR", PHI)

    def test_pd_multisets(self):
        self.assertEqual(len(ec.pd_multisets(3, 1)), 5)
        self.assertEqual(len(ec.pd_multisets(3, 0)), 6)

    def test_creation_shapes(self):
        self.assertIn(("producer", (P0, P0, P0), (T0,)), self.shapes)
        self.assertIn(("producer", (P0, D0), (T0,)), self.shapes)
        self.assertEqual(ec.s_max((P0, P0, P0), (T0,), PHI), 1)
        self.assertEqual(ec.s_max((P0, D0), (T0,), PHI), 0)

    def test_mdfa_analogues(self):
        self.assertIn(("consumer", (T0, T0), (P0, T1)), self.shapes)
        self.assertIn(("consumer", (T0, P0, P0, P0), (P0, T1)), self.shapes)
        self.assertIn(("consumer", (T0, P0, D0), (P0, T1)), self.shapes)
        self.assertIn(("consumer", (T0,), (P0, P1)), self.shapes)
        self.assertEqual(ec.s_max((T0, T0), (P0, T1), PHI), 6)
        self.assertEqual(ec.s_max((T0, P0, P0, P0), (P0, T1), PHI), 8)
        self.assertEqual(ec.s_max((T0,), (P0, P1), PHI), 2)

    def test_shape_invariants(self):
        keys = [(ins, outs) for _k, ins, outs in self.shapes]
        self.assertEqual(len(keys), len(set(keys)))
        for kind, ins, outs in self.shapes:
            cin = sum(1 for g in ins if g[0] == "TSTAR")
            cout = sum(1 for g in outs if g[0] == "TSTAR")
            if kind == "producer":
                self.assertEqual((cin, cout), (0, 1))
            else:
                self.assertIn(cin, (1, 2))
                self.assertLessEqual(cout, cin)
            self.assertLessEqual(ec.wire_count(ins), 6)
            self.assertLessEqual(ec.wire_count(outs), 8)
            self.assertGreaterEqual(ec.s_max(ins, outs, PHI), 0)
            self.assertTrue(ec.achievable(ins) <= ec.achievable(outs))


class TestJobModule(unittest.TestCase):
    def test_import_and_balance(self):
        import job_enc
        st = job_enc.new_state("TSTAR", "consumer", (T0, T0), (P0, T1))
        self.assertEqual(job_enc.e_balance(st), 1)
        self.assertEqual(st["key"], "TSTAR@0+TSTAR@0 -> P@0+TSTAR@1")


if __name__ == "__main__":
    unittest.main()
