# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Known building blocks, transcribed gate by gate from Cirbo
(github.com/spbsat/cirbo, cirbo/synthesis/generation/arithmetics/summation.py):
add_sum3, add_stockmeyer_block, add_mdfa, add_simplified_mdfa.
Truth tables are [f00, f01, f10, f11] indexed by (first input, second input)."""

XOR = [0, 1, 1, 0]
OR = [0, 1, 1, 1]
AND = [0, 0, 0, 1]
FIRST_AND_NOT_SECOND = [0, 0, 1, 0]   # p and not q
SECOND_AND_NOT_FIRST = [0, 1, 0, 0]   # q and not p

P0, P1, D0, D1 = ("P", 0), ("P", 1), ("D", 0), ("D", 1)

# Full adder: x1, x2, x3 -> sum (P@0), carry (P@1). 5 gates (known optimal).
FULL_ADDER = {
    "inputs": [P0, P0, P0], "outputs": [P0, P1],
    "circuit": {"n": 3, "gates": [
        [0, 1, XOR],      # 3: g1 = x1 ^ x2
        [1, 2, XOR],      # 4: g2 = x2 ^ x3
        [3, 4, OR],       # 5: g3 = g1 | g2
        [2, 3, XOR],      # 6: o1 = g1 ^ x3  (sum)
        [5, 6, XOR],      # 7: o2 = g3 ^ o1  (carry)
    ], "outs": [[6, 0], [7, 0]]},
}

# Stockmeyer block: x1, (x2, x2^x3) -> sum, carry. 4 gates.
STOCKMEYER = {
    "inputs": [P0, D0], "outputs": [P0, P1],
    "circuit": {"n": 3, "gates": [
        [0, 2, XOR],                    # 3: w0 = x1 ^ x23
        [1, 2, FIRST_AND_NOT_SECOND],   # 4: x2 & ~x23
        [0, 2, AND],                    # 5: x1 & x23
        [4, 5, XOR],                    # 6: w1
    ], "outs": [[3, 0], [6, 0]]},
}

# MDFA (Demenkov, Kojevnikov, Kulikov, Yaroslavtsev 2010):
# z, (x1, x1^y1), (x2, x2^y2) -> parity (P@0), carry pair (D@1). 8 gates.
MDFA = {
    "inputs": [P0, D0, D0], "outputs": [P0, D1],
    "circuit": {"n": 5, "gates": [
        [0, 1, XOR],                    # 5: g1 = x1 ^ z
        [2, 5, OR],                     # 6: g2 = xy1 | g1
        [0, 2, XOR],                    # 7: g3 = xy1 ^ z
        [6, 7, XOR],                    # 8: g4 = g2 ^ g3
        [3, 7, XOR],                    # 9: g5 = x2 ^ g3
        [4, 7, XOR],                    # 10: g6 = g3 ^ xy2
        [4, 9, SECOND_AND_NOT_FIRST],   # 11: g7 = g5 & ~xy2
        [6, 11, XOR],                   # 12: g8 = g2 ^ g7
    ], "outs": [[10, 0], [8, 0], [12, 0]]},
}

# MDFA with z = 0: (x1, x1^y1), (x2, x2^y2) -> P@0, D@1. 6 gates.
MDFA_PRIME = {
    "inputs": [D0, D0], "outputs": [P0, D1],
    "circuit": {"n": 4, "gates": [
        [0, 1, OR],                     # 4: g2 = xy1 | x1
        [1, 4, XOR],                    # 5: g4 = g2 ^ xy1
        [1, 2, XOR],                    # 6: g5 = x2 ^ xy1
        [1, 3, XOR],                    # 7: g6 = xy1 ^ xy2
        [3, 6, SECOND_AND_NOT_FIRST],   # 8: g7 = g5 & ~xy2
        [4, 8, XOR],                    # 9: g8 = g2 ^ g7
    ], "outs": [[7, 0], [5, 0], [9, 0]]},
}

# Pairing XOR: two P bits -> one D group. 1 gate.
PAIR_XOR = {
    "inputs": [P0, P0], "outputs": [D0],
    "circuit": {"n": 2, "gates": [[0, 1, XOR]], "outs": [[0, 0], [2, 0]]},
}

ALL = {"full_adder": FULL_ADDER, "stockmeyer": STOCKMEYER, "mdfa": MDFA,
       "mdfa_prime": MDFA_PRIME, "pair_xor": PAIR_XOR}
