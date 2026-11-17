# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stdlib-only tests for search 3 (two-column blocks): the input list, the
shape list (one case enumerated by hand), the MDFA + pass-through block, and
explicit circuits for the two long-shot composites (16 and 17 gates)."""
import unittest

import enccore as ec
import job_twocol as jt
import known_blocks as kb

P0, D0, P1, D1, P2, D2 = jt.P0, jt.D0, jt.P1, jt.D1, jt.P2, jt.D2
XOR = [0, 1, 1, 0]


def place(template, input_map, start):
    """Gates of `template` re-wired: template input i -> node input_map[i],
    template gate t -> node start + (t - n). Returns (gates, outs)."""
    n = template["n"]

    def mv(x):
        return input_map[x] if x < n else start + (x - n)
    gates = [[mv(j), mv(k), list(f)] for j, k, f in template["gates"]]
    outs = [[mv(s), p] for s, p in template["outs"]]
    return gates, outs


def mdfa_then_mdfa():
    """Wires: 0 z, (1, 2) D, (3, 4) D at weight 0; 5 z', (6, 7) D at weight 1."""
    g1, o1 = place(kb.MDFA["circuit"], [0, 1, 2, 3, 4], 8)       # gates 8..15
    carry = [o1[1][0], o1[2][0]]
    g2, o2 = place(kb.MDFA["circuit"], [5, carry[0], carry[1], 6, 7], 16)
    return {"n": 8, "gates": g1 + g2, "outs": [o1[0], o2[0], o2[1], o2[2]]}


def mdfa_then_pair_mdfa():
    """Wires: 0 z, (1, 2) D, (3, 4) D at weight 0; 5, 6, 7 plain at weight 1."""
    g1, o1 = place(kb.MDFA["circuit"], [0, 1, 2, 3, 4], 8)       # gates 8..15
    pair = [[6, 7, XOR]]                                         # gate 16: D = (6, 16)
    carry = [o1[1][0], o1[2][0]]
    g2, o2 = place(kb.MDFA["circuit"], [5, carry[0], carry[1], 6, 16], 17)
    return {"n": 8, "gates": g1 + pair + g2, "outs": [o1[0], o2[0], o2[1], o2[2]]}


class TestInputs(unittest.TestCase):
    def test_count_by_hand(self):
        # P/D multisets with exactly k wires: k=1:1, 2:2, 3:2, 4:3, 5:3.
        # sum over w0 of combos(w0) * #(multisets with 1..6-w0 wires) = 11+16+10+9+3
        ins = jt.twocol_inputs(6)
        self.assertEqual(len(ins), 49)
        self.assertEqual(len(set(ins)), 49)
        for g in ins:
            ws = set(w for _n, w in g)
            self.assertEqual(ws, {0, 1})
            self.assertLessEqual(ec.wire_count(g), 6)


class TestShapes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shapes = jt.twocol_shapes(6, 8)

    def test_hand_case(self):
        # P@0+P@0+P@1 (values 0..4, phi 13.5): only D@0+P@1 and P@0+D@1 fit.
        outs = ec.output_shapes((P0, P0, P1), ("P", "D"), jt.PHI, 8)
        self.assertEqual(set(outs), {(D0, P1), (P0, D1)})
        for o in outs:
            self.assertEqual(ec.s_max((P0, P0, P1), o, jt.PHI), 0)

    def test_mdfa_pass_listed(self):
        self.assertIn(((P0, D0, D0, P1), (P0, P1, D1)), self.shapes)
        self.assertEqual(ec.s_max((P0, D0, D0, P1), (P0, P1, D1), jt.PHI), 7)

    def test_invariants(self):
        self.assertEqual(len(self.shapes), len(set(self.shapes)))
        for ins, outs in self.shapes:
            self.assertLessEqual(ec.wire_count(ins), 6)
            self.assertLessEqual(ec.wire_count(outs), 8)
            self.assertGreaterEqual(ec.s_max(ins, outs, jt.PHI), 0)
            self.assertTrue(ec.achievable(ins) <= ec.achievable(outs))
            for name, _w in outs:
                self.assertIn(name, ("P", "D"))


class TestCircuits(unittest.TestCase):
    def test_mdfa_pass_circuit(self):
        ins, outs = (P0, D0, D0, P1), (P0, P1, D1)
        circ = jt.mdfa_pass_circuit()
        self.assertEqual(len(circ["gates"]), 8)
        self.assertEqual(ec.check(ins, outs, circ), (True, None))
        e = ec.encode(ins, outs, 8)
        asg = ec.assignment_from_circuit(e, circ)
        self.assertEqual(len(asg), e.nvars)
        self.assertEqual(ec.unsatisfied(e.clauses, asg), [])

    def test_broken_pass_rejected(self):
        circ = jt.mdfa_pass_circuit()
        circ["outs"][1] = [0, 0]
        self.assertFalse(ec.check((P0, D0, D0, P1), (P0, P1, D1), circ)[0])

    def test_long_shot_composites(self):
        builders = {"mdfa_then_mdfa": mdfa_then_mdfa,
                    "mdfa_then_pair_mdfa": mdfa_then_pair_mdfa}
        self.assertEqual(sorted(builders), sorted(x[0] for x in jt.LONG_SHOTS))
        for name, ins, outs, tight in jt.LONG_SHOTS:
            circ = builders[name]()
            self.assertEqual(ec.wire_count(ins), 8, name)
            self.assertEqual(len(circ["gates"]), tight, name)
            self.assertEqual(ec.check(ins, outs, circ), (True, None), name)
            self.assertTrue(ec.achievable(ins) <= ec.achievable(outs), name)
            # the composite is tight: phi(in) - phi(out) == its size
            self.assertEqual(ec.phi2(ins, jt.PHI) - ec.phi2(outs, jt.PHI), 2 * tight, name)
            self.assertEqual(ec.s_max(ins, outs, jt.PHI), tight - 1, name)


if __name__ == "__main__":
    unittest.main()
