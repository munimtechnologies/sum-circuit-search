# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stdlib-only tests: semantics, known blocks, potentials, shape enumeration,
and that the CNF encoding accepts every known circuit and rejects broken ones."""
import copy
import unittest

import known_blocks as kb
import sumcore as sc

P0, P1, P2, D0, D1 = ("P", 0), ("P", 1), ("P", 2), ("D", 0), ("D", 1)


class TestSemantics(unittest.TestCase):
    def test_pair_values(self):
        self.assertEqual(sc.group_value("D", [0, 0]), 0)
        self.assertEqual(sc.group_value("D", [0, 1]), 1)
        self.assertEqual(sc.group_value("D", [1, 1]), 1)
        self.assertEqual(sc.group_value("D", [1, 0]), 2)

    def test_pair_is_p_and_p_xor_q(self):
        for p in (0, 1):
            for q in (0, 1):
                self.assertEqual(sc.group_value("D", [p, p ^ q]), p + q)

    def test_weighted_value(self):
        self.assertEqual(sc.value([P0, D1], [1, 1, 0]), 1 + 2 * 2)
        self.assertEqual(sc.value([P2, P0], [1, 1]), 5)


class TestKnownBlocks(unittest.TestCase):
    def test_all_known_blocks_correct(self):
        for name, blk in kb.ALL.items():
            ok, row = sc.check(blk["inputs"], blk["outputs"], blk["circuit"])
            self.assertTrue(ok, "%s fails at row %s" % (name, row))

    def test_sizes(self):
        self.assertEqual(len(kb.FULL_ADDER["circuit"]["gates"]), 5)
        self.assertEqual(len(kb.STOCKMEYER["circuit"]["gates"]), 4)
        self.assertEqual(len(kb.MDFA["circuit"]["gates"]), 8)
        self.assertEqual(len(kb.MDFA_PRIME["circuit"]["gates"]), 6)
        self.assertEqual(len(kb.PAIR_XOR["circuit"]["gates"]), 1)

    def test_broken_mdfa_rejected(self):
        circ = copy.deepcopy(kb.MDFA["circuit"])
        circ["gates"][6][2] = [0, 0, 0, 1]   # g7 becomes AND
        ok, _ = sc.check(kb.MDFA["inputs"], kb.MDFA["outputs"], circ)
        self.assertFalse(ok)

    def test_swapped_outputs_rejected(self):
        circ = copy.deepcopy(kb.FULL_ADDER["circuit"])
        circ["outs"] = [circ["outs"][1], circ["outs"][0]]
        ok, _ = sc.check(kb.FULL_ADDER["inputs"], kb.FULL_ADDER["outputs"], circ)
        self.assertFalse(ok)


class TestPotentials(unittest.TestCase):
    def test_tight_blocks(self):
        # phi(in) - phi(out) equals the size for the pairing XOR and the MDFA
        for blk in (kb.PAIR_XOR, kb.MDFA):
            d2 = sc.phi2(blk["inputs"]) - sc.phi2(blk["outputs"])
            self.assertEqual(d2, 2 * len(blk["circuit"]["gates"]))

    def test_s_max(self):
        self.assertEqual(sc.s_max(kb.MDFA["inputs"], kb.MDFA["outputs"]), 7)
        self.assertEqual(sc.s_max(kb.FULL_ADDER["inputs"], kb.FULL_ADDER["outputs"]), 4)
        self.assertEqual(sc.s_max(kb.STOCKMEYER["inputs"], kb.STOCKMEYER["outputs"]), 3)
        self.assertEqual(sc.s_max(kb.MDFA_PRIME["inputs"], kb.MDFA_PRIME["outputs"]), 3)
        self.assertEqual(sc.s_max(kb.PAIR_XOR["inputs"], kb.PAIR_XOR["outputs"]), 0)

    def test_no_known_block_profitable(self):
        for blk in kb.ALL.values():
            self.assertGreater(len(blk["circuit"]["gates"]),
                               sc.s_max(blk["inputs"], blk["outputs"]))


class TestShapes(unittest.TestCase):
    def test_input_shapes(self):
        shapes = sc.input_shapes(3)
        self.assertEqual(len(shapes), 5)   # P, PP, PPP, D, PD
        self.assertIn((P0, P0, P0), shapes)
        self.assertIn((P0, D0), shapes)

    def test_known_shapes_enumerated(self):
        allshapes = sc.enumerate_shapes(5)
        keys = set((ins, outs) for ins, outs, _ in allshapes)
        self.assertIn(((P0, D0, D0), (P0, D1)), keys)
        self.assertIn(((P0, P0, P0), (P0, P1)), keys)
        self.assertIn(((P0, D0), (P0, P1)), keys)
        self.assertIn(((D0, D0), (P0, D1)), keys)
        self.assertIn(((P0, P0), (D0,)), keys)

    def test_every_shape_can_hold_all_totals(self):
        for ins, outs, sm in sc.enumerate_shapes(5):
            V = sc.max_value(ins)
            self.assertTrue(set(range(V + 1)) <= sc.achievable(outs))
            self.assertEqual(sm, sc.s_max(ins, outs))
            self.assertGreaterEqual(sm, 0)

    def test_no_duplicates(self):
        allshapes = sc.enumerate_shapes(5)
        keys = [(ins, outs) for ins, outs, _ in allshapes]
        self.assertEqual(len(keys), len(set(keys)))

    def test_single_p_has_no_shape(self):
        self.assertEqual(sc.output_shapes((P0,)), [])


class TestEncoding(unittest.TestCase):
    def test_known_circuits_satisfy_cnf(self):
        for name, blk in kb.ALL.items():
            circ = blk["circuit"]
            e = sc.encode(blk["inputs"], blk["outputs"], len(circ["gates"]))
            asg = sc.assignment_from_circuit(e, circ)
            self.assertEqual(len(asg), e.nvars, name)
            self.assertEqual(sc.unsatisfied(e.clauses, asg), [], name)

    def test_decode_roundtrip(self):
        blk = kb.MDFA
        circ = blk["circuit"]
        e = sc.encode(blk["inputs"], blk["outputs"], len(circ["gates"]))
        asg = sc.assignment_from_circuit(e, circ)
        model = [v if asg[v] else -v for v in range(1, e.nvars + 1)]
        self.assertEqual(sc.decode(e, model), circ)

    def test_wrong_circuit_violates_cnf(self):
        blk = kb.FULL_ADDER
        circ = copy.deepcopy(blk["circuit"])
        circ["outs"] = [circ["outs"][1], circ["outs"][0]]
        e = sc.encode(blk["inputs"], blk["outputs"], 5)
        asg = sc.assignment_from_circuit(e, circ)
        self.assertNotEqual(sc.unsatisfied(e.clauses, asg), [])

    def test_degenerate_gate_violates_cnf(self):
        blk = kb.FULL_ADDER
        circ = copy.deepcopy(blk["circuit"])
        circ["gates"][0][2] = [0, 0, 1, 1]   # g1 = x1 (degenerate)
        e = sc.encode(blk["inputs"], blk["outputs"], 5)
        asg = sc.assignment_from_circuit(e, circ)
        self.assertNotEqual(sc.unsatisfied(e.clauses, asg), [])

    def test_unused_gate_violates_cnf(self):
        blk = kb.PAIR_XOR
        circ = copy.deepcopy(blk["circuit"])
        circ["gates"].append([0, 1, [0, 0, 0, 1]])   # dead AND gate
        e = sc.encode(blk["inputs"], blk["outputs"], 2)
        asg = sc.assignment_from_circuit(e, circ)
        self.assertNotEqual(sc.unsatisfied(e.clauses, asg), [])

    def test_wrong_negated_output_rejected(self):
        # pair XOR with its first wire negated: (~x1, x1^x2) encodes
        # 2 - (x1 + x2), not x1 + x2, so check and the CNF must reject it.
        blk = kb.PAIR_XOR
        circ = copy.deepcopy(blk["circuit"])
        circ["outs"][0][1] = 1
        ok, _ = sc.check(blk["inputs"], blk["outputs"], circ)
        self.assertFalse(ok)
        e = sc.encode(blk["inputs"], blk["outputs"], 1)
        asg = sc.assignment_from_circuit(e, circ)
        self.assertNotEqual(sc.unsatisfied(e.clauses, asg), [])

    def test_zero_gate_instance_has_expected_size(self):
        # s = 0: only output selectors, polarities and output values exist.
        e = sc.encode([P0, P0], [D0], 0)
        self.assertEqual(e.nvars, 2 * (3 + 1 + 4))


if __name__ == "__main__":
    unittest.main()
