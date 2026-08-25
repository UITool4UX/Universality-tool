"""Computation engine tests (``universality/calculation.py``).

Canonical vectors TV1–TV6: values owned by ``docs/FORMULA_SPECIFICATION.md``;
mapping to these tests and the hand-verification worksheet:
``tests/CALCULATION_TEST_VECTORS.md``.

Tolerance discipline (``docs/FORMULA_SPECIFICATION.md``): vector values
are compared with ``1e-12`` — never ``==`` on computed results. ``==``
is used only for documented bit-exact structural identities.
"""

from __future__ import annotations

import ast
import math
import os
import unittest

from universality import (
    SIMPLE_MODE_GROUP_WEIGHTS,
    compute,
    group_gap,
    group_index,
    normalize_score,
    overall_index,
    parameter_contributions,
)
from universality.domain import (
    EPSILON,
    DomainInvariantError,
    Evaluation,
    GroupScores,
    Parameter,
    PerGroupValue,
    Score,
    UserGroup,
    Weight,
)

TOL = 1e-12  # vector comparison tolerance (FORMULA_SPECIFICATION.md)


def make_parameter(
    name: str,
    weight: float,
    fap: float,
    sap: float,
    dap: float,
) -> Parameter:
    return Parameter(
        name=name,
        weight=Weight(weight),
        scores=GroupScores(Score(fap), Score(sap), Score(dap)),
    )


def tv1_evaluation() -> Evaluation:
    """TV1: scale 5; P1 (w=1/2) 5/4/3; P2 (w=1/2) 3/2/1."""
    return Evaluation(
        product="Test product",
        scale_max=5,
        parameters=(
            make_parameter("P1", 0.5, 5, 4, 3),
            make_parameter("P2", 0.5, 3, 2, 1),
        ),
    )


def tv5_evaluation() -> Evaluation:
    """TV5 (hand-verifiable reference case; worksheet in
    tests/CALCULATION_TEST_VECTORS.md): scale 10;
    A (w=0.7) 10/5/0; B (w=0.3) 4/8/6."""
    return Evaluation(
        product="Test product",
        scale_max=10,
        parameters=(
            make_parameter("A", 0.7, 10, 5, 0),
            make_parameter("B", 0.3, 4, 8, 6),
        ),
    )


class TestNormalizationF1(unittest.TestCase):
    def test_f1_basic_quotients(self) -> None:
        self.assertEqual(normalize_score(2.5, 5), 0.5)  # bit-exact
        self.assertEqual(normalize_score(0, 5), 0.0)
        self.assertEqual(normalize_score(5, 5), 1.0)

    def test_f1_alternate_likert_scales(self) -> None:
        # Scale 3, 7, 100 spot values (hand: 2/3, 5/7, 42/100).
        self.assertAlmostEqual(normalize_score(2, 3), 2 / 3, delta=TOL)
        self.assertAlmostEqual(normalize_score(5, 7), 5 / 7, delta=TOL)
        self.assertAlmostEqual(normalize_score(42, 100), 0.42, delta=TOL)
        # Full-precision quotient preserved — NOT rounded to 4 dp (A6 is
        # presentation-only and lives in the APPLICATION layer).
        self.assertEqual(normalize_score(5, 7), 5.0 / 7.0)
        self.assertNotEqual(normalize_score(5, 7), round(5 / 7, 4))

    def test_f1_rejects_invalid_inputs(self) -> None:
        for score, scale in (
            (-1, 5), (5.1, 5), (float("nan"), 5), (float("inf"), 5),
            (True, 5), (False, 5), ("5", 5), (None, 5),
            (5, 1), (5, 101), (5, 5.0), (5, True), (5, "5"),
        ):
            with self.assertRaises(DomainInvariantError, msg=repr((score, scale))):
                normalize_score(score, scale)  # type: ignore[arg-type]

    def test_f1_no_clamping(self) -> None:
        # Exactly-at-scale returns exactly 1.0; out-of-scale RAISES
        # (never clamps to the domain).
        self.assertEqual(normalize_score(5, 5), 1.0)
        with self.assertRaises(DomainInvariantError):
            normalize_score(5.0000001, 5)


class TestGroupIndexF2(unittest.TestCase):
    def test_tv1_group_indices(self) -> None:
        evaluation = tv1_evaluation()
        # Hand: UI_F = .5*1 + .5*.6 = .8; UI_S = .5*.8 + .5*.4 = .6;
        # UI_D = .5*.6 + .5*.2 = .4.
        self.assertAlmostEqual(group_index(evaluation, UserGroup.FAP), 0.8, delta=TOL)
        self.assertAlmostEqual(group_index(evaluation, UserGroup.SAP), 0.6, delta=TOL)
        self.assertAlmostEqual(group_index(evaluation, UserGroup.DAP), 0.4, delta=TOL)

    def test_group_index_equals_stored_contributions_bit_exact(self) -> None:
        # Documented structural identity: UI_G IS the left-to-right sum
        # of the stored per-parameter F2 summands.
        result = compute(tv5_evaluation())
        for group in (UserGroup.FAP, UserGroup.SAP, UserGroup.DAP):
            expected = sum(p.contributions.for_group(group) for p in result.parameters)
            self.assertEqual(result.group_indices.for_group(group), expected)

    def test_group_index_order_determinism(self) -> None:
        # Deterministic per input order: swapped parameter order may
        # differ only by last-ulp summation effects, never more.
        a = Evaluation(product="Test product", scale_max=10, parameters=(
            make_parameter("A", 0.3, 4, 8, 6), make_parameter("B", 0.7, 10, 5, 0)))
        b = Evaluation(product="Test product", scale_max=10, parameters=(
            make_parameter("B", 0.7, 10, 5, 0), make_parameter("A", 0.3, 4, 8, 6)))
        for group in (UserGroup.FAP, UserGroup.SAP, UserGroup.DAP):
            self.assertLessEqual(
                abs(group_index(a, group) - group_index(b, group)), 1e-15)

    def test_group_index_rejects_invalid_evaluation_type(self) -> None:
        for bad in (None, "eval", 5, tv1_evaluation().parameters):
            with self.assertRaises(DomainInvariantError, msg=repr(type(bad))):
                group_index(bad, UserGroup.FAP)  # type: ignore[arg-type]


class TestOverallF3(unittest.TestCase):
    def test_tv1_overall(self) -> None:
        result = compute(tv1_evaluation())
        # Hand: UI = (0.8 + 0.6 + 0.4) / 3 = 0.6.
        self.assertAlmostEqual(result.overall, 0.6, delta=TOL)

    def test_tv5_unequal_user_group_weights(self) -> None:
        # W = (0.5, 0.3, 0.2): UI = .5*.82 + .3*.59 + .2*.18 = .623.
        result = compute(tv5_evaluation(), group_weights=(0.5, 0.3, 0.2))
        self.assertAlmostEqual(result.overall, 0.623, delta=TOL)

    def test_decimal_group_weights_accepted(self) -> None:
        # 0.3333333333333333 x2 + 0.3333333333333334 sums to exactly
        # 1.0 in IEEE-754 — a legitimate decimal-weight input.
        evaluation = Evaluation(product="Test product", scale_max=10, parameters=(
            make_parameter("A", 0.4, 10, 8, 6),
            make_parameter("B", 0.6, 5, 5, 5)))
        result = compute(evaluation, group_weights=(
            0.3333333333333333, 0.3333333333333333, 0.3333333333333334))
        self.assertGreaterEqual(result.overall, 0.0)
        self.assertLessEqual(result.overall, 1.0 + 2 * EPSILON)

    def test_default_weights_are_simple_mode(self) -> None:
        evaluation = tv1_evaluation()
        self.assertEqual(compute(evaluation).overall,
                         compute(evaluation, group_weights=SIMPLE_MODE_GROUP_WEIGHTS).overall)

    def test_overall_index_rejects_invalid_group_weights(self) -> None:
        indices = PerGroupValue(0.8, 0.6, 0.4)
        for bad in (
            (0.5, 0.5), (0.5, 0.5, 0.5, 0.5), (),
            (0.4, 0.3, 0.25), (0.6, 0.6, 0.6), (1 + 5e-8, 0.5, 0.0),
            (-0.1, 0.5, 0.6), (float("nan"), 0.5, 0.5), (float("inf"), 0.5, 0.5),
            (True, 0.5, 0.5), ("0.5", 0.5, 0.5), (0.5, 0.5, None),
        ):
            with self.assertRaises(DomainInvariantError, msg=repr(bad)):
                overall_index(indices, group_weights=bad)  # type: ignore[arg-type]
        with self.assertRaises(DomainInvariantError):
            overall_index(0.5)  # type: ignore[arg-type]


class TestParameterContributions(unittest.TestCase):
    def test_tv5_contributions(self) -> None:
        # Hand: A -> (0.7*1, 0.7*0.5, 0.7*0) = (0.7, 0.35, 0.0)
        #       B -> (0.3*0.4, 0.3*0.8, 0.3*0.6) = (0.12, 0.24, 0.18)
        result = compute(tv5_evaluation())
        a, b = result.parameters
        for group, expected in ((UserGroup.FAP, 0.7), (UserGroup.SAP, 0.35), (UserGroup.DAP, 0.0)):
            self.assertAlmostEqual(a.contributions.for_group(group), expected, delta=TOL)
        for group, expected in ((UserGroup.FAP, 0.12), (UserGroup.SAP, 0.24), (UserGroup.DAP, 0.18)):
            self.assertAlmostEqual(b.contributions.for_group(group), expected, delta=TOL)

    def test_contributions_within_unit_interval(self) -> None:
        result = compute(tv5_evaluation())
        for p in result.parameters:
            for group in (UserGroup.FAP, UserGroup.SAP, UserGroup.DAP):
                value = p.contributions.for_group(group)
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_zero_weight_contributes_zero(self) -> None:
        # A9: zero weight is valid and contributes nothing.
        evaluation = Evaluation(product="Test product", scale_max=10, parameters=(
            make_parameter("A", 0.0, 10, 10, 10),
            make_parameter("B", 1.0, 4, 8, 6)))
        result = compute(evaluation)
        for group in (UserGroup.FAP, UserGroup.SAP, UserGroup.DAP):
            self.assertEqual(result.parameters[0].contributions.for_group(group), 0.0)
            self.assertAlmostEqual(result.parameters[1].contributions.for_group(group),
                                   normalize_score(
                                        evaluation.parameters[1].scores.for_group(group).value, 10),
                                   delta=TOL)

    def test_parameter_contributions_rejects_invalid(self) -> None:
        with self.assertRaises(DomainInvariantError):
            parameter_contributions("nope", 5)  # type: ignore[arg-type]
        with self.assertRaises(DomainInvariantError):
            parameter_contributions(make_parameter("A", 1.0, 5, 5, 5), 5.0)  # type: ignore[arg-type]
        with self.assertRaises(DomainInvariantError):
            parameter_contributions(make_parameter("A", 1.0, 6, 5, 5), 5)


class TestGroupGapF4(unittest.TestCase):
    def test_tv1_gap(self) -> None:
        # Hand: max(0.8, 0.6, 0.4) - min(0.8, 0.6, 0.4) = 0.4.
        self.assertAlmostEqual(compute(tv1_evaluation()).group_gap, 0.4, delta=TOL)

    def test_gap_is_max_minus_min_of_exposed_indices(self) -> None:
        result = compute(tv5_evaluation())
        values = (result.group_indices.fap, result.group_indices.sap,
                  result.group_indices.dap)
        self.assertEqual(result.group_gap, max(values) - min(values))

    def test_gap_zero_when_groups_equal_bit_exact(self) -> None:
        # TV4-style: single parameter, equal scores -> all indices equal.
        evaluation = Evaluation(product="Test product", scale_max=10, parameters=(make_parameter("A", 1.0, 7, 7, 7),))
        self.assertEqual(compute(evaluation).group_gap, 0.0)

    def test_gap_order_independent(self) -> None:
        self.assertEqual(group_gap(PerGroupValue(0.8, 0.6, 0.4)),
                         group_gap(PerGroupValue(0.4, 0.6, 0.8)))

    def test_gap_range_and_invalid_type(self) -> None:
        result = compute(tv5_evaluation())
        self.assertGreaterEqual(result.group_gap, 0.0)
        self.assertLessEqual(result.group_gap, 1.0 + EPSILON)
        with self.assertRaises(DomainInvariantError):
            group_gap(0.5)  # type: ignore[arg-type]


class TestEndToEndVectors(unittest.TestCase):
    def test_tv1_mixed_scores_all_fields(self) -> None:
        result = compute(tv1_evaluation())
        self.assertAlmostEqual(result.group_indices.fap, 0.8, delta=TOL)
        self.assertAlmostEqual(result.group_indices.sap, 0.6, delta=TOL)
        self.assertAlmostEqual(result.group_indices.dap, 0.4, delta=TOL)
        self.assertAlmostEqual(result.overall, 0.6, delta=TOL)
        self.assertAlmostEqual(result.group_gap, 0.4, delta=TOL)
        a, b = result.parameters
        for group, expected in ((UserGroup.FAP, 1.0), (UserGroup.SAP, 0.8), (UserGroup.DAP, 0.6)):
            self.assertAlmostEqual(a.normalized.for_group(group), expected, delta=TOL)
        for group, expected in ((UserGroup.FAP, 0.6), (UserGroup.SAP, 0.4), (UserGroup.DAP, 0.2)):
            self.assertAlmostEqual(b.normalized.for_group(group), expected, delta=TOL)

    def test_tv5_hand_verifiable_case(self) -> None:
        """TV5 — the independently hand-verifiable reference case.

        Full decimal worksheet (every value is an exact terminating
        decimal): tests/CALCULATION_TEST_VECTORS.md.
        """
        result = compute(tv5_evaluation(), group_weights=(0.5, 0.3, 0.2))
        self.assertAlmostEqual(result.group_indices.fap, 0.82, delta=TOL)   # 41/50
        self.assertAlmostEqual(result.group_indices.sap, 0.59, delta=TOL)   # 59/100
        self.assertAlmostEqual(result.group_indices.dap, 0.18, delta=TOL)   # 9/50
        self.assertAlmostEqual(result.overall, 0.623, delta=TOL)           # 623/1000
        self.assertAlmostEqual(result.group_gap, 0.64, delta=TOL)          # 16/25

    def test_tv2_perfect_scores_bit_exact_with_halves(self) -> None:
        # w = 0.5/0.5 makes every FP operation here exact: 0.5*1.0 +
        # 0.5*1.0 = 1.0, and (1/3)*1.0*3 terms sum within 1e-12 of 1.
        evaluation = Evaluation(product="Test product", scale_max=10, parameters=(
            make_parameter("A", 0.5, 10, 10, 10),
            make_parameter("B", 0.5, 10, 10, 10)))
        result = compute(evaluation)
        self.assertEqual(result.group_indices.fap, 1.0)
        self.assertEqual(result.group_indices.sap, 1.0)
        self.assertEqual(result.group_indices.dap, 1.0)
        self.assertAlmostEqual(result.overall, 1.0, delta=TOL)
        self.assertEqual(result.group_gap, 0.0)

    def test_tv3_minimum_scores_bit_exact_zero(self) -> None:
        evaluation = Evaluation(product="Test product", scale_max=10, parameters=(
            make_parameter("A", 0.5, 0, 0, 0),
            make_parameter("B", 0.5, 0, 0, 0)))
        result = compute(evaluation)
        self.assertEqual(result.group_indices.fap, 0.0)
        self.assertEqual(result.group_indices.sap, 0.0)
        self.assertEqual(result.group_indices.dap, 0.0)
        self.assertEqual(result.overall, 0.0)
        self.assertEqual(result.group_gap, 0.0)

    def test_tv4_one_parameter(self) -> None:
        evaluation = Evaluation(product="Test product", scale_max=10, parameters=(make_parameter("A", 1.0, 7, 7, 7),))
        result = compute(evaluation)
        self.assertAlmostEqual(result.overall, 0.7, delta=TOL)
        self.assertEqual(result.group_gap, 0.0)
        self.assertAlmostEqual(result.parameters[0].normalized.fap, 0.7, delta=TOL)

    def test_many_parameters_midpoint_vector(self) -> None:
        # n = 100, all scores at the scale midpoint (5 of 10): every
        # s_norm = exactly 0.5, every index = 0.5 * sum(w) = 0.5 (to
        # within FP drift), and all three indices are bit-equal, so the
        # gap is exactly 0.0.
        evaluation = Evaluation(
            product="Test product",
            scale_max=10,
            parameters=tuple(
                make_parameter(f"P{i}", 1.0 / 100, 5, 5, 5) for i in range(100)))
        result = compute(evaluation)
        self.assertAlmostEqual(result.group_indices.fap, 0.5, delta=TOL)
        self.assertAlmostEqual(result.group_indices.sap, 0.5, delta=TOL)
        self.assertAlmostEqual(result.group_indices.dap, 0.5, delta=TOL)
        self.assertAlmostEqual(result.overall, 0.5, delta=TOL)
        self.assertEqual(result.group_gap, 0.0)
        self.assertEqual(len(result.parameters), 100)

    def test_many_parameters_bounds_and_identity(self) -> None:
        # n = 100 with a non-symmetric pattern; asserts the documented
        # bounds and the bit-exact contributions identity only (the
        # values themselves are not hand-derived here by design).
        evaluation = Evaluation(
            product="Test product",
            scale_max=10,
            parameters=tuple(
                make_parameter(f"P{i}", 1.0 / 100,
                               (i * 7) % 11, (i * 5) % 11, (i * 3) % 11)
                for i in range(100)))
        result = compute(evaluation)
        for group in (UserGroup.FAP, UserGroup.SAP, UserGroup.DAP):
            value = result.group_indices.for_group(group)
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0 + EPSILON)
            self.assertEqual(value, sum(
                p.contributions.for_group(group) for p in result.parameters))
        self.assertGreaterEqual(result.overall, 0.0)
        self.assertLessEqual(result.overall, 1.0 + 2 * EPSILON)
        self.assertGreaterEqual(result.group_gap, 0.0)
        self.assertLessEqual(result.group_gap, 1.0 + EPSILON)

    def test_unequal_parameter_weights_derived_case(self) -> None:
        # Hand (exact decimals): w = 0.7/0.2/0.1, scale 10.
        # P1 10/0/10 -> (1, 0, 1); P2 0/10/0 -> (0, 1, 0); P3 5/5/5 -> (.5, .5, .5)
        # UI_F = .7*1 + .2*0 + .1*.5 = .75; UI_S = .25; UI_D = .75
        # UI = (.75 + .25 + .75)/3 = 7/12; gap = .75 - .25 = .5
        evaluation = Evaluation(product="Test product", scale_max=10, parameters=(
            make_parameter("P1", 0.7, 10, 0, 10),
            make_parameter("P2", 0.2, 0, 10, 0),
            make_parameter("P3", 0.1, 5, 5, 5)))
        result = compute(evaluation)
        self.assertAlmostEqual(result.group_indices.fap, 0.75, delta=TOL)
        self.assertAlmostEqual(result.group_indices.sap, 0.25, delta=TOL)
        self.assertAlmostEqual(result.group_indices.dap, 0.75, delta=TOL)
        self.assertAlmostEqual(result.overall, 7 / 12, delta=TOL)
        self.assertAlmostEqual(result.group_gap, 0.5, delta=TOL)

    def test_decimal_parameter_weights_bit_exact_sum(self) -> None:
        # 0.3333333333333333 x2 + 0.3333333333333334 sums to exactly
        # 1.0 in IEEE-754; with all scores at scale max the group index
        # is that exact sum: bit-exact 1.0 (no clamping involved).
        evaluation = Evaluation(product="Test product", scale_max=10, parameters=(
            make_parameter("A", 0.3333333333333333, 10, 10, 10),
            make_parameter("B", 0.3333333333333333, 10, 10, 10),
            make_parameter("C", 0.3333333333333334, 10, 10, 10)))
        result = compute(evaluation)
        self.assertEqual(result.group_indices.fap, 1.0)
        self.assertAlmostEqual(result.overall, 1.0, delta=TOL)


class TestTv6NoClamping(unittest.TestCase):
    def test_valid_c1_tolerated_weights_are_not_clamped(self) -> None:
        # C1: sum = 1 + 5e-10 <= 1 + EPSILON -> VALID input. All scores
        # at scale max -> UI_G = sum of weights > 1.0. The engine must
        # compute faithfully (no clamping to 1.0).
        evaluation = Evaluation(product="Test product", scale_max=5, parameters=(
            make_parameter("A", 0.5 + 2.5e-10, 5, 5, 5),
            make_parameter("B", 0.5, 5, 5, 5),
            make_parameter("C", 2.5e-10, 5, 5, 5)))
        result = compute(evaluation)
        for value in (result.group_indices.fap, result.group_indices.sap,
                      result.group_indices.dap):
            self.assertGreater(value, 1.0)
            self.assertLessEqual(value, 1.0 + EPSILON)
        self.assertGreater(result.overall, 1.0)
        self.assertLessEqual(result.overall, 1.0 + 2 * EPSILON)
        self.assertEqual(result.group_gap, 0.0)

    def test_invalid_weight_sum_is_rejected_not_clamped(self) -> None:
        # sum = 1 + 5e-8 > 1 + EPSILON -> C1 violation: rejected at
        # construction (domain), never clamped or repaired.
        with self.assertRaises(DomainInvariantError):
            Evaluation(product="Test product", scale_max=5, parameters=(
                make_parameter("A", 0.5 + 2.5e-8, 5, 5, 5),
                make_parameter("B", 0.5, 5, 5, 5),
                make_parameter("C", 2.5e-8, 5, 5, 5)))

    def test_out_of_range_score_is_rejected_not_clamped(self) -> None:
        # Score 6 on scale 5: Score itself allows it (type domain is
        # >= 0), but the Evaluation C3 domain rejects it — never
        # clamped, never repaired.
        with self.assertRaises(DomainInvariantError):
            Evaluation(product="Test product", scale_max=5, parameters=(make_parameter("A", 1.0, 6, 5, 5),))


class TestFloatingPointTolerance(unittest.TestCase):
    def test_why_tolerances_are_required(self) -> None:
        # Documents the concrete FP facts the tolerance discipline
        # addresses: decimal arithmetic misses literals in general
        # (0.1 + 0.2 != 0.3), so C1's `abs(sum - 1) <= EPSILON` is a
        # tolerance check — a naive `==` would reject valid decimal
        # weights. Weights that do drift still sit far inside EPSILON.
        self.assertNotEqual(0.1 + 0.2, 0.3)
        self.assertLessEqual(abs(0.1 + 0.2 + 0.7 - 1.0), EPSILON)
        evaluation = Evaluation(product="Test product", scale_max=10, parameters=(
            make_parameter("A", 0.1, 10, 8, 6),
            make_parameter("B", 0.2, 5, 5, 5),
            make_parameter("C", 0.7, 4, 8, 6)))
        result = compute(evaluation)
        self.assertGreaterEqual(result.overall, 0.0)
        self.assertLessEqual(result.overall, 1.0 + 2 * EPSILON)

    def test_c1_tolerance_boundary(self) -> None:
        # CPython's left-to-right sum of three 1/3 lands on exactly 1.0
        # here (round-to-even); other decimal weight sums drift by a few
        # ulps. Both cases sit within EPSILON, so C1 never rejects valid
        # decimal weights — and the engine computes the documented result.
        evaluation = Evaluation(product="Test product", scale_max=5, parameters=(
            make_parameter("A", 1 / 3, 5, 4, 3),
            make_parameter("B", 1 / 3, 3, 2, 1),
            make_parameter("C", 1 / 3, 2, 3, 4)))
        result = compute(evaluation)
        # Hand (exact rational arithmetic): w = 1/3 each.
        # s_norm A: 1, 4/5, 3/5 ; B: 3/5, 2/5, 1/5 ; C: 2/5, 3/5, 4/5
        # UI_F = (1/3)(1 + 3/5 + 2/5) = (1/3)(2)   = 2/3
        # UI_S = (1/3)(4/5 + 2/5 + 3/5) = (1/3)(9/5) = 3/5
        # UI_D = (1/3)(3/5 + 1/5 + 4/5) = (1/3)(8/5) = 8/15
        # UI   = (1/3)(2/3 + 3/5 + 8/15) = (1/3)(27/15) = 3/5
        # gap  = 2/3 - 8/15 = 10/15 - 8/15 = 2/15
        self.assertAlmostEqual(result.group_indices.fap, 2 / 3, delta=TOL)
        self.assertAlmostEqual(result.group_indices.sap, 3 / 5, delta=TOL)
        self.assertAlmostEqual(result.group_indices.dap, 8 / 15, delta=TOL)
        self.assertAlmostEqual(result.overall, 3 / 5, delta=TOL)
        self.assertAlmostEqual(result.group_gap, 2 / 15, delta=TOL)


class TestDeterminismAndPurity(unittest.TestCase):
    def test_repeated_computation_is_bit_identical(self) -> None:
        evaluation = tv5_evaluation()
        first = compute(evaluation, group_weights=(0.5, 0.3, 0.2))
        second = compute(evaluation, group_weights=(0.5, 0.3, 0.2))
        self.assertEqual(first.overall, second.overall)
        self.assertEqual(first.group_indices, second.group_indices)
        self.assertEqual(first.group_gap, second.group_gap)
        self.assertEqual(first.parameters, second.parameters)

    def test_input_evaluation_is_unmodified(self) -> None:
        evaluation = tv5_evaluation()
        before = (evaluation.scale_max, evaluation.parameters)
        compute(evaluation)
        self.assertEqual((evaluation.scale_max, evaluation.parameters), before)

    def test_engine_imports_are_domain_plus_stdlib_only(self) -> None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "universality", "calculation.py")
        tree = ast.parse(open(path, encoding="utf-8").read())
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported_modules.add(node.module)
        self.assertTrue(
            imported_modules <= {"math", "typing", "__future__", "universality.domain"},
            msg=f"unexpected imports: {imported_modules}")
        self.assertFalse(
            imported_modules & {"pandas", "numpy", "streamlit"},
            msg="core calculation must not use pandas/numpy or UI frameworks")

    def test_engine_contains_no_forbidden_constructs(self) -> None:
        # Security contract (docs/validation-and-security.md): no
        # eval/exec, no pickle, no os/subprocess, no dynamic import —
        # checked on the code tree (identifier level), not on docstrings.
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "universality", "calculation.py")
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
        forbidden = {"eval", "exec", "pickle", "system", "shell", "compile", "input"}
        self.assertFalse(identifiers & forbidden,
                         msg=f"forbidden identifiers present: {identifiers & forbidden}")


if __name__ == "__main__":
    unittest.main()
