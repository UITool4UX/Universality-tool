"""Edge-case tests: domain boundaries, extreme valid values, and pinned
IEEE-754 behaviors at the exact limits.

Complements ``tests/test_validation.py`` (per-rule V-table coverage) and
``tests/test_calculation.py`` (engine-level vectors) with cases at the
*boundaries*: values just inside and just outside each limit, extreme
valid inputs (scale 2/100, 100 parameters, 100-character names), and
floating-point edge values.

Pinned behaviors — if any of these ever changes it is a contract change
requiring change control, not a bug fix:

- weight ``-0.0`` is **accepted**: ``-0.0 == 0.0`` is the same real and
  C5 (``w >= 0``) holds; it produces the same results as weight ``0.0``;
- score ``-0.0`` is **rejected** by V4 (``-0.0 < 1``);
- score ``1e308`` is **rejected by V4, not V2** (it is finite; the range
  rule is the first violated rule);
- 100 x 0.01 parameter weights: the IEEE-754 sum is
  ``1.0000000000000007`` — within EPSILON, so **accepted**, and never
  "fixed" to 1.0;
- duplicate-name comparison applies **trim + Unicode casefold only** —
  no other normalization (whitespace inside names is not collapsed).
"""

from __future__ import annotations

import unittest

from universality import (
    EPSILON,
    ValidationRejection,
    compute,
    validate,
    validate_group_weights,
)
from universality.domain import CONTROL_CHARS

TOL = 1e-12  # vector comparison tolerance (FORMULA_SPECIFICATION.md)


def make_raw(
    product: str = "Edge product",
    scale_max: int = 5,
    parameters: list | None = None,
) -> dict:
    if parameters is None:
        parameters = [
            {"name": "P1", "weight": 1.0, "scores": {"fap": 1, "sap": 1, "dap": 1}}
        ]
    return {"product": product, "scale_max": scale_max, "parameters": parameters}


def assert_rejects(
    test: unittest.TestCase, raw: object, code: str, field: str = ""
) -> ValidationRejection:
    with test.assertRaises(ValidationRejection) as ctx:
        validate(raw)
    rejection = ctx.exception
    test.assertEqual(rejection.code, code, msg=rejection.message)
    if field:
        test.assertEqual(rejection.field, field, msg=rejection.message)
    return rejection


class TestEmptyAndMinimal(unittest.TestCase):
    """Empty input and the smallest valid evaluation."""

    def test_fully_empty_dict_rejected_at_product(self) -> None:
        assert_rejects(self, {}, "V16", "product")

    def test_product_only_rejected_at_scale(self) -> None:
        # Structural phase order: product -> scale presence -> parameters.
        assert_rejects(self, {"product": "X"}, "V7", "scale_max")

    def test_minimal_valid_evaluation(self) -> None:
        # Scale 2 (the minimum), one parameter, minimum scores.
        result = compute(validate(make_raw(scale_max=2)))
        # s_norm(1, 2) == 0.5 is exact in IEEE-754.
        self.assertEqual(result.group_indices.fap, 0.5)
        self.assertEqual(result.group_indices.sap, 0.5)
        self.assertEqual(result.group_indices.dap, 0.5)
        self.assertAlmostEqual(result.overall, 0.5, delta=TOL)
        self.assertEqual(result.group_gap, 0.0)

    def test_single_parameter_weight_just_outside_tolerance_rejected(self) -> None:
        # |0.999999998 - 1| = 2e-9 > EPSILON -> V6.
        assert_rejects(
            self, make_raw(parameters=[
                {"name": "P1", "weight": 0.999999998, "scores": {"fap": 1, "sap": 1, "dap": 1}}
            ]),
            "V6", "parameters",
        )

    def test_single_parameter_weight_at_tolerance_boundary_accepted(self) -> None:
        # |0.999999999 - 1| = 1e-9 == EPSILON -> accepted (inclusive bound).
        evaluation = validate(make_raw(parameters=[
            {"name": "P1", "weight": 0.999999999, "scores": {"fap": 1, "sap": 1, "dap": 1}}
        ]))
        self.assertEqual(evaluation.parameters[0].weight.value, 0.999999999)


class TestScaleEdges(unittest.TestCase):
    """scale_max at the minimum (2) and maximum (100)."""

    def test_scale_two_full_precision_quotients(self) -> None:
        raw = make_raw(scale_max=2, parameters=[
            {"name": "A", "weight": 0.5, "scores": {"fap": 2, "sap": 1.5, "dap": 1}},
            {"name": "B", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 2}},
        ])
        result = compute(validate(raw))
        # 2/2, 1.5/2, 1/2 are all exact in IEEE-754.
        self.assertEqual(result.parameters[0].normalized.fap, 1.0)
        self.assertEqual(result.parameters[0].normalized.sap, 0.75)
        self.assertEqual(result.parameters[0].normalized.dap, 0.5)

    def test_scale_hundred_compound_extreme(self) -> None:
        # Maximum scale + maximum-length product name + maximum-length
        # parameter name + boundary scores, all in one evaluation.
        raw = make_raw(
            product="x" * 100,
            scale_max=100,
            parameters=[
                {"name": "n" * 100, "weight": 1.0,
                 "scores": {"fap": 100, "sap": 99.99999999999999, "dap": 1.0}},
            ],
        )
        result = compute(validate(raw))
        self.assertEqual(result.parameters[0].name, "n" * 100)
        self.assertEqual(result.parameters[0].normalized.fap, 1.0)
        self.assertLess(result.parameters[0].normalized.sap, 1.0)
        self.assertGreater(result.parameters[0].normalized.sap, 1.0 - 1e-9)
        self.assertAlmostEqual(result.parameters[0].normalized.dap, 0.01, delta=TOL)


class TestScoreEdges(unittest.TestCase):
    """Scores just inside and just outside [1, scale_max]."""

    def test_score_just_below_minimum_rejected(self) -> None:
        raw = make_raw(parameters=[
            {"name": "P1", "weight": 1.0, "scores": {"fap": 0.9999999999999999, "sap": 1, "dap": 1}}
        ])
        assert_rejects(self, raw, "V4", "parameters[0].scores.fap")

    def test_score_just_above_maximum_rejected(self) -> None:
        for scale, bad in ((5, 5.000000000000001), (100, 100.00000000000001)):
            with self.subTest(scale=scale):
                raw = make_raw(scale_max=scale, parameters=[
                    {"name": "P1", "weight": 1.0, "scores": {"fap": bad, "sap": 1, "dap": 1}}
                ])
                assert_rejects(self, raw, "V4", "parameters[0].scores.fap")

    def test_huge_finite_score_fails_range_not_finiteness(self) -> None:
        # 1e308 is finite (V2 cannot fire); the range rule V4 is the first
        # violated rule. Pins the documented validation order.
        raw = make_raw(parameters=[
            {"name": "P1", "weight": 1.0, "scores": {"fap": 1e308, "sap": 1, "dap": 1}}
        ])
        assert_rejects(self, raw, "V4", "parameters[0].scores.fap")

    def test_negative_zero_score_rejected(self) -> None:
        # -0.0 is the same real as 0.0, and 0 < 1: V4 (not V3, not V13).
        raw = make_raw(parameters=[
            {"name": "P1", "weight": 1.0, "scores": {"fap": -0.0, "sap": 1, "dap": 1}}
        ])
        assert_rejects(self, raw, "V4", "parameters[0].scores.fap")

    def test_int_and_float_scores_pipeline_bit_identical(self) -> None:
        as_int = make_raw(scale_max=10, parameters=[
            {"name": "A", "weight": 0.5, "scores": {"fap": 7, "sap": 5, "dap": 3}},
            {"name": "B", "weight": 0.5, "scores": {"fap": 4, "sap": 8, "dap": 6}},
        ])
        as_float = make_raw(scale_max=10, parameters=[
            {"name": "A", "weight": 0.5, "scores": {"fap": 7.0, "sap": 5.0, "dap": 3.0}},
            {"name": "B", "weight": 0.5, "scores": {"fap": 4.0, "sap": 8.0, "dap": 6.0}},
        ])
        self.assertEqual(compute(validate(as_int)), compute(validate(as_float)))


class TestWeightEdges(unittest.TestCase):
    """Weights at the [0, 1] limits and floating-point extremes."""

    def test_negative_zero_weight_is_the_same_real_as_zero(self) -> None:
        # Pinned: -0.0 is accepted (C5: -0.0 >= 0.0) and produces results
        # bit-equal to those of weight 0.0.
        neg_zero = make_raw(parameters=[
            {"name": "A", "weight": -0.0, "scores": {"fap": 2, "sap": 3, "dap": 4}},
            {"name": "B", "weight": 1.0, "scores": {"fap": 5, "sap": 1, "dap": 1}},
        ])
        zero = make_raw(parameters=[
            {"name": "A", "weight": 0.0, "scores": {"fap": 2, "sap": 3, "dap": 4}},
            {"name": "B", "weight": 1.0, "scores": {"fap": 5, "sap": 1, "dap": 1}},
        ])
        result = compute(validate(neg_zero))
        self.assertEqual(result.parameters[0].contributions.fap, 0.0)
        self.assertEqual(result, compute(validate(zero)))

    def test_tiny_weight_accepted_with_unit_partner(self) -> None:
        # 1.0 + 1e-300 rounds to exactly 1.0: C1 holds bit-exactly.
        raw = make_raw(parameters=[
            {"name": "A", "weight": 1e-300, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "B", "weight": 1.0, "scores": {"fap": 5, "sap": 2, "dap": 3}},
        ])
        result = compute(validate(raw))
        # Tiny but exactly representable: 1e-300 * (1/5) = 2e-301.
        self.assertEqual(result.parameters[0].contributions.fap, 1e-300 * (1.0 / 5.0))

    def test_weight_just_above_one_rejected_just_below_accepted(self) -> None:
        for bad in (1.0000000000000002, 2.0):
            with self.subTest(bad=bad):
                raw = make_raw(parameters=[
                    {"name": "P1", "weight": bad, "scores": {"fap": 1, "sap": 1, "dap": 1}}
                ])
                assert_rejects(self, raw, "V5", "parameters[0].weight")
        raw = make_raw(parameters=[
            {"name": "P1", "weight": 0.9999999999999999, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ])
        # Sum 0.9999999999999999 is within EPSILON of 1: accepted.
        self.assertEqual(validate(raw).parameters[0].weight.value, 0.9999999999999999)

    def test_tiny_negative_weight_rejected(self) -> None:
        raw = make_raw(parameters=[
            {"name": "P1", "weight": -1e-12, "scores": {"fap": 1, "sap": 1, "dap": 1}}
        ])
        assert_rejects(self, raw, "V5", "parameters[0].weight")


class TestParameterCountEdges(unittest.TestCase):
    """The n = 100 limit with decimal weights (the classic FP case)."""

    def test_100_parameters_equal_decimal_weights(self) -> None:
        # Documented CPython fact: the IEEE-754 sum is NOT exactly 1.0...
        weights = [0.01] * 100
        self.assertEqual(sum(weights), 1.0000000000000007)
        self.assertNotEqual(sum(weights), 1.0)
        # ...but it is within EPSILON, so C1 accepts it — and the gate
        # must never "fix" it to exactly 1.0.
        raw = make_raw(scale_max=3, parameters=[
            {"name": f"P{i}", "weight": 0.01, "scores": {"fap": 1, "sap": 2, "dap": 3}}
            for i in range(100)
        ])
        evaluation = validate(raw)
        self.assertEqual(
            [p.weight.value for p in evaluation.parameters], weights
        )
        result = compute(evaluation)
        self.assertEqual(len(result.parameters), 100)
        self.assertEqual(
            [p.name for p in result.parameters], [f"P{i}" for i in range(100)]
        )
        for value in (
            result.group_indices.fap, result.group_indices.sap,
            result.group_indices.dap,
        ):
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0 + EPSILON)
        self.assertGreaterEqual(result.overall, 0.0)
        self.assertLessEqual(result.overall, 1.0 + 2 * EPSILON)


class TestNameEdges(unittest.TestCase):
    """The exact 95-character control set, Unicode casefolding, and the
    absence of any normalization beyond trim + casefold."""

    def test_every_control_character_rejected_in_names_and_product(self) -> None:
        self.assertEqual(len(CONTROL_CHARS), 65)  # C0 (32) + DEL (1) + C1 (32)
        for char in sorted(CONTROL_CHARS):
            with self.subTest(char=hex(ord(char))):
                raw = make_raw(parameters=[
                    {"name": f"a{char}b", "weight": 1.0, "scores": {"fap": 1, "sap": 1, "dap": 1}}
                ])
                assert_rejects(self, raw, "V10", "parameters[0].name")
                assert_rejects(self, make_raw(product=f"a{char}b"), "V18", "product")

    def test_non_control_chars_accepted(self) -> None:
        for char in (" ", "\xa0", "é", "✓", "中"):
            with self.subTest(char=repr(char)):
                raw = make_raw(product=f"a{char}b", parameters=[
                    {"name": f"a{char}b", "weight": 1.0, "scores": {"fap": 1, "sap": 1, "dap": 1}}
                ])
                evaluation = validate(raw)
                self.assertEqual(evaluation.product, f"a{char}b")
                self.assertEqual(evaluation.parameters[0].name, f"a{char}b")

    def test_unicode_casefold_duplicates_rejected(self) -> None:
        # casefold("Straße") == casefold("STRASSE") == "strasse" — pinned.
        raw = make_raw(parameters=[
            {"name": "Straße", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "STRASSE", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ])
        assert_rejects(self, raw, "V8", "parameters[1].name")

    def test_whitespace_inside_names_is_not_normalized(self) -> None:
        # "a b" and "a  b" differ after trim + casefold: distinct.
        raw = make_raw(parameters=[
            {"name": "a b", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "a  b", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ])
        evaluation = validate(raw)
        self.assertEqual([p.name for p in evaluation.parameters], ["a b", "a  b"])
        # But trim + casefold still catches the padded/cased duplicate.
        dup = make_raw(parameters=[
            {"name": "a b", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": " A B ", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ])
        assert_rejects(self, dup, "V8", "parameters[1].name")


class TestGroupWeightEdges(unittest.TestCase):
    """validate_group_weights at the corners of the [0, 1]^3 simplex."""

    def test_corner_and_zero_combinations_accepted(self) -> None:
        for triple in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (0.5, 0.5, 0.0), (0.0, 0.5, 0.5)):
            with self.subTest(triple=triple):
                self.assertEqual(
                    validate_group_weights(triple),
                    (float(triple[0]), float(triple[1]), float(triple[2])),
                )

    def test_value_rules_precede_sum(self) -> None:
        with self.assertRaises(ValidationRejection) as ctx:
            validate_group_weights((2.0, -1.0, 0.0))
        self.assertEqual((ctx.exception.code, ctx.exception.field), ("V5", "group_weights[0]"))
        with self.assertRaises(ValidationRejection) as ctx:
            validate_group_weights((0.5, 0.5, float("nan")))
        self.assertEqual((ctx.exception.code, ctx.exception.field), ("V1", "group_weights[2]"))
        with self.assertRaises(ValidationRejection) as ctx:
            validate_group_weights((True, 0.5, 0.5))
        self.assertEqual((ctx.exception.code, ctx.exception.field), ("V3", "group_weights[0]"))

    def test_decimal_group_weights_exact_sum_accepted(self) -> None:
        # Documented CPython fact: these three doubles sum to exactly 1.0.
        triple = (0.3333333333333333, 0.3333333333333333, 0.3333333333333334)
        self.assertEqual(sum(triple), 1.0)
        self.assertEqual(validate_group_weights(triple), triple)


class TestNoClampingEndToEnd(unittest.TestCase):
    """TV6 through the user-input pipeline: faithful, never clamped."""

    def test_tv6_c1_tolerated_input_not_clamped_through_pipeline(self) -> None:
        # Weights sum to 1 + 5e-10 <= 1 + EPSILON: a VALID evaluation.
        # All scores at the maximum (s_norm = 1) => indices equal the
        # weight sum, which exceeds 1.0. The engine computes faithfully.
        raw = make_raw(scale_max=5, parameters=[
            {"name": "A", "weight": 0.5 + 2.5e-10, "scores": {"fap": 5, "sap": 5, "dap": 5}},
            {"name": "B", "weight": 0.5, "scores": {"fap": 5, "sap": 5, "dap": 5}},
            {"name": "C", "weight": 2.5e-10, "scores": {"fap": 5, "sap": 5, "dap": 5}},
        ])
        result = compute(validate(raw))
        for value in (result.group_indices.fap, result.group_indices.sap, result.group_indices.dap):
            self.assertGreater(value, 1.0)
            self.assertLessEqual(value, 1.0 + EPSILON)
        self.assertGreater(result.overall, 1.0)
        self.assertLessEqual(result.overall, 1.0 + 2 * EPSILON)
        self.assertEqual(result.group_gap, 0.0)


if __name__ == "__main__":
    unittest.main()
