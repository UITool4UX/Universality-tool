"""Cross-layer integration tests: raw input -> validation gate -> engine.

Covers the full pipeline the APPLICATION layer will expose via
``services.evaluate`` (deferred): ``validate(raw)`` ->
``compute(evaluation)`` -> ``EvaluationOutcome``. Canonical vector values
are owned by ``docs/FORMULA_SPECIFICATION.md``; the vector -> test map and
worksheet live in ``tests/CALCULATION_TEST_VECTORS.md``.

Tolerance discipline (``docs/FORMULA_SPECIFICATION.md``): vector values
are compared with ``1e-12`` — never ``==`` on computed results. ``==`` is
used only for documented bit-exact identities (e.g. TV1's overall ``0.6``).
"""

from __future__ import annotations

import copy
import unittest

import universality
from universality import (
    SIMPLE_MODE_GROUP_WEIGHTS,
    DomainInvariantError,
    Evaluation,
    EvaluationOutcome,
    GroupScores,
    Parameter,
    Score,
    ValidationRejection,
    Weight,
    compute,
    validate,
    validate_group_weights,
)

TOL = 1e-12  # vector comparison tolerance (FORMULA_SPECIFICATION.md)


def tv1_raw() -> dict:
    """TV1 as raw user input: scale 5; P1 5/4/3, P2 3/2/1; weights 1/2."""
    return {
        "product": "Test product",
        "scale_max": 5,
        "parameters": [
            {"name": "P1", "weight": 0.5, "scores": {"fap": 5, "sap": 4, "dap": 3}},
            {"name": "P2", "weight": 0.5, "scores": {"fap": 3, "sap": 2, "dap": 1}},
        ],
    }


def tv7_raw() -> dict:
    """TV7 (Accessible chair reference case) as raw user input.

    scale 10; Reachability w=0.7 (10/5/1); Stability w=0.3 (4/8/6).
    Hand-verifiable: UI_F 41/50, UI_S 59/100, UI_D 1/4, UI 83/150,
    group_gap 57/100.
    """
    return {
        "product": "Accessible chair",
        "scale_max": 10,
        "parameters": [
            {"name": "Reachability", "weight": 0.7, "scores": {"fap": 10, "sap": 5, "dap": 1}},
            {"name": "Stability", "weight": 0.3, "scores": {"fap": 4, "sap": 8, "dap": 6}},
        ],
    }


def tv5_engine_evaluation() -> Evaluation:
    """TV5 constructed directly on the domain (engine-level; DAP 0 is not
    producible through the validation gate since A20)."""
    return Evaluation(
        product="Test product",
        scale_max=10,
        parameters=(
            Parameter(
                name="A", weight=Weight(0.7),
                scores=GroupScores(Score(10), Score(5), Score(0)),
            ),
            Parameter(
                name="B", weight=Weight(0.3),
                scores=GroupScores(Score(4), Score(8), Score(6)),
            ),
        ),
    )


def snapshot(result) -> tuple:
    """A full bit-comparable snapshot of an ``EvaluationResult``."""
    rows = tuple(
        (
            p.name, p.weight.value,
            p.normalized.fap, p.normalized.sap, p.normalized.dap,
            p.contributions.fap, p.contributions.sap, p.contributions.dap,
        )
        for p in result.parameters
    )
    return (
        result.group_indices.fap, result.group_indices.sap, result.group_indices.dap,
        result.overall, result.group_gap, rows,
    )


class TestPublicSurface(unittest.TestCase):
    """The package exposes exactly the documented public contract."""

    EXPECTED_SURFACE = frozenset({
        # APPLICATION — validation
        "ValidationRejection", "validate", "validate_group_weights",
        # APPLICATION — service layer (turn 8)
        "ServiceError", "evaluate", "format_for_display",
        # CALCULATION
        "SIMPLE_MODE_GROUP_WEIGHTS", "compute", "group_gap", "group_index",
        "normalize_score", "overall_index", "parameter_contributions",
        # DOMAIN
        "EPSILON", "PARAMETER_MAX", "SCALE_MAX", "SCALE_MIN",
        "DomainInvariantError", "Evaluation", "EvaluationOutcome",
        "EvaluationResult", "GroupScores", "KanoCategory", "Parameter",
        "ParameterResult", "PerGroupValue", "Score", "UserGroup", "Weight",
        "weights_sum_is_valid",
        # metadata
        "__version__",
    })

    def test_public_surface_is_exactly_the_documented_contract(self) -> None:
        self.assertEqual(set(universality.__all__), set(self.EXPECTED_SURFACE))
        for name in self.EXPECTED_SURFACE:
            self.assertIsNotNone(getattr(universality, name), name)

    def test_validation_rejection_is_a_catchable_exception(self) -> None:
        raw = tv1_raw()
        raw["parameters"][0]["weight"] = 0.96  # sum 0.96 -> V6
        try:
            validate(raw)
            self.fail("expected ValidationRejection")
        except Exception as exc:  # must be catchable as a plain Exception
            self.assertIsInstance(exc, ValidationRejection)
            self.assertEqual(str(exc), exc.message)
            self.assertEqual(exc.code, "V6")


class TestPipelineVectors(unittest.TestCase):
    """Canonical vectors through the full user-input pipeline."""

    def test_tv1_pipeline(self) -> None:
        result = compute(validate(tv1_raw()))
        # Documented bit-exact identities (turn-4 verification, CPython).
        self.assertEqual(result.group_indices.fap, 0.8)   # UI_F == 4/5
        self.assertEqual(result.overall, 0.6)             # UI == 3/5
        self.assertEqual(result.group_gap, 0.4)           # gap == 2/5
        # Tolerance-compared values.
        self.assertAlmostEqual(result.group_indices.sap, 0.6, delta=TOL)
        self.assertAlmostEqual(result.group_indices.dap, 0.4, delta=TOL)

    def test_tv7_accessible_chair_pipeline(self) -> None:
        result = compute(validate(tv7_raw()))
        self.assertAlmostEqual(result.group_indices.fap, 0.82, delta=TOL)   # 41/50
        self.assertAlmostEqual(result.group_indices.sap, 0.59, delta=TOL)   # 59/100
        self.assertAlmostEqual(result.group_indices.dap, 0.25, delta=TOL)   # 1/4
        self.assertAlmostEqual(result.overall, 83 / 150, delta=TOL)         # 0.5533...
        self.assertAlmostEqual(result.group_gap, 0.57, delta=TOL)           # 57/100
        evaluation = validate(tv7_raw())
        self.assertEqual(evaluation.product, "Accessible chair")
        self.assertEqual(
            [p.name for p in result.parameters], ["Reachability", "Stability"]
        )
        # Weight traceability: the result carries the input weights.
        self.assertEqual(result.parameters[0].weight.value, 0.7)
        self.assertEqual(result.parameters[1].weight.value, 0.3)

    def test_tv5_engine_level_vector_blocked_at_user_gate(self) -> None:
        # The same data as TV5, attempted as raw user input, is rejected by
        # the A20 gate (score 0 < 1) — never silently repaired.
        raw = tv5_as_raw()
        with self.assertRaises(ValidationRejection) as ctx:
            validate(raw)
        self.assertEqual(ctx.exception.code, "V4")
        self.assertEqual(ctx.exception.field, "parameters[0].scores.dap")
        # Constructed at engine level (the documented engine domain
        # [0, scale_max]) it computes to the canonical TV5 values.
        result = compute(tv5_engine_evaluation(), (0.5, 0.3, 0.2))
        self.assertAlmostEqual(result.group_indices.fap, 0.82, delta=TOL)
        self.assertAlmostEqual(result.group_indices.sap, 0.59, delta=TOL)
        self.assertAlmostEqual(result.group_indices.dap, 0.18, delta=TOL)
        self.assertAlmostEqual(result.overall, 0.623, delta=TOL)
        self.assertAlmostEqual(result.group_gap, 0.64, delta=TOL)


def tv5_as_raw() -> dict:
    return {
        "product": "Test product",
        "scale_max": 10,
        "parameters": [
            {"name": "A", "weight": 0.7, "scores": {"fap": 10, "sap": 5, "dap": 0}},
            {"name": "B", "weight": 0.3, "scores": {"fap": 4, "sap": 8, "dap": 6}},
        ],
    }


class TestPipelineBehavior(unittest.TestCase):
    """End-to-end error handling, determinism, and outcome consistency."""

    def test_invalid_weight_sum_raises_v6_and_nothing_is_computed(self) -> None:
        raw = tv7_raw()
        raw["parameters"][1]["weight"] = 0.26  # sum 0.96
        with self.assertRaises(ValidationRejection) as ctx:
            compute(validate(raw))
        self.assertEqual(ctx.exception.code, "V6")
        self.assertIn("sum to 1", ctx.exception.message)

    def test_rejection_is_deterministic(self) -> None:
        raw = tv1_raw()
        raw["scale_max"] = 101
        first = second = None
        for _ in range(2):
            with self.assertRaises(ValidationRejection) as ctx:
                validate(copy.deepcopy(raw))
            captured = (ctx.exception.code, ctx.exception.field, ctx.exception.message)
            if first is None:
                first = captured
            second = captured
        self.assertEqual(first, second)

    def test_pipeline_is_bit_identical_across_runs(self) -> None:
        raw = tv7_raw()
        reference = snapshot(compute(validate(raw)))
        for _ in range(10):
            self.assertEqual(snapshot(compute(validate(raw))), reference)

    def test_unknown_keys_are_ignored_end_to_end(self) -> None:
        clean = tv7_raw()
        noisy = copy.deepcopy(clean)
        noisy["unknown_top"] = {"x": 1}
        noisy["parameters"][0]["unknown_param"] = "junk"
        noisy["parameters"][1]["scores"]["unknown_group"] = 99
        self.assertEqual(
            snapshot(compute(validate(noisy))), snapshot(compute(validate(clean)))
        )

    def test_simple_mode_group_weights_roundtrip(self) -> None:
        evaluation = validate(tv7_raw())
        default = compute(evaluation)
        explicit = compute(evaluation, SIMPLE_MODE_GROUP_WEIGHTS)
        self.assertEqual(snapshot(default), snapshot(explicit))
        self.assertEqual(
            validate_group_weights(SIMPLE_MODE_GROUP_WEIGHTS),
            (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
        )

    def test_outcome_pairs_evaluation_and_result(self) -> None:
        evaluation = validate(tv7_raw())
        result = compute(evaluation)
        outcome = EvaluationOutcome(evaluation=evaluation, result=result)
        self.assertEqual(outcome.evaluation, evaluation)
        self.assertEqual(outcome.result, result)
        self.assertEqual(
            [p.name for p in outcome.result.parameters],
            [p.name for p in outcome.evaluation.parameters],
        )

    def test_outcome_rejects_mismatched_pairing(self) -> None:
        evaluation = validate(tv7_raw())
        result = compute(evaluation)
        swapped = EvaluationResult_swapped(result)
        with self.assertRaises(DomainInvariantError):
            EvaluationOutcome(evaluation=evaluation, result=swapped)

    def test_only_validation_rejection_escapes_the_pipeline(self) -> None:
        hostile = (
            None,
            42,
            {"product": object()},
            {"scale_max": 5, "parameters": []},
            {"product": "X", "scale_max": 5, "parameters": [object()]},
            {"product": "X", "scale_max": 5, "parameters": [
                {"name": "A", "weight": object(), "scores": {}}
            ]},
        )
        forbidden = (
            "Traceback", "ValueError", "KeyError", "TypeError",
            "AttributeError", "IndexError", "universality.",
        )
        for i, raw in enumerate(hostile):
            with self.subTest(i=i):
                with self.assertRaises(ValidationRejection) as ctx:
                    compute(validate(raw))
                message = ctx.exception.message
                for fragment in forbidden:
                    self.assertNotIn(fragment, message, msg=message)

    def test_int_and_float_scores_are_indistinguishable(self) -> None:
        as_int = tv7_raw()
        as_float = {
            "product": "Accessible chair",
            "scale_max": 10,
            "parameters": [
                {"name": "Reachability", "weight": 0.7, "scores": {"fap": 10.0, "sap": 5.0, "dap": 1.0}},
                {"name": "Stability", "weight": 0.3, "scores": {"fap": 4.0, "sap": 8.0, "dap": 6.0}},
            ],
        }
        self.assertEqual(
            snapshot(compute(validate(as_float))),
            snapshot(compute(validate(as_int))),
        )


def EvaluationResult_swapped(result: "EvaluationResult") -> EvaluationResult:
    """Rebuild ``result`` with per-parameter order reversed.

    The reversed names still satisfy every field-level invariant, so this
    isolates the EvaluationOutcome-level consistency invariant.
    """
    from universality import EvaluationResult as _ER
    obj = _ER.__new__(_ER)
    object.__setattr__(obj, "group_indices", result.group_indices)
    object.__setattr__(obj, "overall", result.overall)
    object.__setattr__(obj, "parameters", tuple(reversed(result.parameters)))
    object.__setattr__(obj, "group_gap", result.group_gap)
    _ER.__post_init__(obj)
    return obj


if __name__ == "__main__":
    unittest.main()
