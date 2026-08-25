"""Application-layer tests: ``universality/services.py``.

Contracts under test (``docs/architecture.md`` §5–7,
``docs/validation-and-security.md`` error handling, A6):

- ``evaluate(raw)`` is the single boundary: controlled failures raise
  ``ValidationRejection`` **unchanged**; anything else is mapped to
  ``ServiceError`` with the fixed generic message (never an internal
  exception, never a traceback);
- ``format_for_display`` is the **sole** presentation-rounding location
  (4 dp fixed-point; no clamping; no feedback into computation) — enforced
  here by a repository-wide scan;
- the application surface is deterministic and leak-free under adversarial
  input.
"""

from __future__ import annotations

import math
import re
import unittest
from pathlib import Path
from unittest import mock

from universality import (
    ServiceError,
    ValidationRejection,
    compute,
    evaluate,
    format_for_display,
    validate,
)
from universality.domain import EvaluationOutcome
from universality import services as services_module

ROOT = Path(__file__).resolve().parent.parent


def tv7_raw() -> dict:
    return {
        "product": "Accessible chair",
        "scale_max": 10,
        "parameters": [
            {"name": "Reachability", "weight": 0.7, "scores": {"fap": 10, "sap": 5, "dap": 1}},
            {"name": "Stability", "weight": 0.3, "scores": {"fap": 4, "sap": 8, "dap": 6}},
        ],
    }


class TestEvaluateSuccess(unittest.TestCase):
    def test_tv7_matches_direct_pipeline(self) -> None:
        raw = tv7_raw()
        outcome = evaluate(raw)
        self.assertIsInstance(outcome, EvaluationOutcome)
        direct_result = compute(validate(raw))
        self.assertEqual(outcome.evaluation, validate(raw))
        self.assertEqual(outcome.result, direct_result)
        # Canonical TV7 values (FORMULA_SPECIFICATION.md), via A6 formatting.
        self.assertEqual(format_for_display(outcome.result.overall), "0.5533")
        self.assertEqual(format_for_display(outcome.result.group_indices.fap), "0.8200")
        self.assertEqual(format_for_display(outcome.result.group_indices.sap), "0.5900")
        self.assertEqual(format_for_display(outcome.result.group_indices.dap), "0.2500")
        self.assertEqual(format_for_display(outcome.result.group_gap), "0.5700")

    def test_deterministic_across_calls(self) -> None:
        raw = tv7_raw()
        first = evaluate(raw)
        second = evaluate(raw)
        self.assertEqual(first.result, second.result)
        self.assertEqual(first.evaluation, second.evaluation)

    def test_preserves_shape_and_order(self) -> None:
        outcome = evaluate(tv7_raw())
        self.assertEqual(
            [p.name for p in outcome.result.parameters], ["Reachability", "Stability"]
        )
        self.assertEqual(outcome.evaluation.product, "Accessible chair")
        self.assertEqual(outcome.evaluation.scale_max, 10)


class TestEvaluateControlledFailures(unittest.TestCase):
    def test_validation_rejection_propagates_unchanged(self) -> None:
        cases = (
            # (mutation of the TV7 baseline, expected code, expected field)
            ({"scale_max": 101}, "V11", "scale_max"),
            ({"product": ""}, "V16", "product"),
        )
        for mutation, code, field in cases:
            with self.subTest(code=code):
                raw = tv7_raw()
                raw.update(mutation)
                with self.assertRaises(ValidationRejection) as ctx:
                    evaluate(raw)
                self.assertNotIsInstance(ctx.exception, ServiceError)
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual(ctx.exception.field, field)

    def test_weight_sum_0_96_propagates_v6_verbatim(self) -> None:
        raw = tv7_raw()
        raw["parameters"][1]["weight"] = 0.26
        with self.assertRaises(ValidationRejection) as ctx:
            evaluate(raw)
        self.assertEqual(ctx.exception.code, "V6")
        self.assertEqual(ctx.exception.message, "Invalid weights: parameter weights must sum to 1. (parameters)")

    def test_score_zero_propagates_v4(self) -> None:
        raw = tv7_raw()
        raw["parameters"][0]["scores"]["dap"] = 0
        with self.assertRaises(ValidationRejection) as ctx:
            evaluate(raw)
        self.assertEqual(ctx.exception.code, "V4")
        self.assertEqual(ctx.exception.field, "parameters[0].scores.dap")


class TestEvaluateUnexpectedFailures(unittest.TestCase):
    """Anything that is not a ValidationRejection maps to ServiceError —
    internals never escape."""

    def _assert_service_error(self, exc: BaseException) -> None:
        self.assertIsInstance(exc, ServiceError)
        self.assertEqual(str(exc), "Something went wrong. Please try again.")
        self.assertNotIn("SECRET", str(exc))
        self.assertNotIn("Traceback", str(exc))

    def test_unexpected_failure_in_validation_maps_to_service_error(self) -> None:
        def hostile(raw):
            raise RuntimeError("SECRET internal detail")

        with mock.patch.object(services_module, "validate", side_effect=hostile):
            with self.assertRaises(ServiceError) as ctx:
                evaluate(tv7_raw())
        self._assert_service_error(ctx.exception)

    def test_unexpected_failure_in_computation_maps_to_service_error(self) -> None:
        def hostile(evaluation, group_weights=None):
            raise ValueError("SECRET computation detail")

        with mock.patch.object(services_module, "compute", side_effect=hostile):
            with self.assertRaises(ServiceError) as ctx:
                evaluate(tv7_raw())
        self._assert_service_error(ctx.exception)

    def test_unexpected_failure_in_outcome_construction_maps_to_service_error(self) -> None:
        class HostileOutcome:
            def __init__(self, **kwargs) -> None:
                raise RuntimeError("SECRET outcome detail")

        with mock.patch.object(services_module, "EvaluationOutcome", HostileOutcome):
            with self.assertRaises(ServiceError) as ctx:
                evaluate(tv7_raw())
        self._assert_service_error(ctx.exception)

    def test_adversarial_raw_only_controlled_errors_escape(self) -> None:
        hostile_raws = (
            None, [], "not a dict", 42, set(), object(),
            {"product": object()}, {"product": "x" * 101, "scale_max": 5, "parameters": []},
            {"scale_max": [5], "parameters": []}, {"scale_max": complex(2), "parameters": []},
            {"parameters": {"a": 1}}, {"parameters": [object()]},
            {"product": "X", "scale_max": 5, "parameters": [
                {"name": object(), "weight": object(), "scores": object()}
            ]},
        )
        forbidden = (
            "Traceback", "ValueError", "KeyError", "TypeError",
            "AttributeError", "IndexError", "universality.",
        )
        for i, raw in enumerate(hostile_raws):
            with self.subTest(i=i):
                try:
                    evaluate(raw)
                    self.fail("expected a controlled error")
                except (ValidationRejection, ServiceError) as exc:
                    message = str(exc)
                    for fragment in forbidden:
                        self.assertNotIn(fragment, message, msg=message)


class TestFormatForDisplay(unittest.TestCase):
    def test_four_decimal_fixed_point(self) -> None:
        self.assertEqual(format_for_display(0.623), "0.6230")
        self.assertEqual(format_for_display(0.5), "0.5000")
        self.assertEqual(format_for_display(0), "0.0000")
        self.assertEqual(format_for_display(1), "1.0000")
        self.assertEqual(format_for_display(83 / 150), "0.5533")
        self.assertEqual(format_for_display(0.1 + 0.2), "0.3000")

    def test_no_clamping_in_tolerance_band(self) -> None:
        # C1-tolerated values slightly above 1 print faithfully (TV6).
        self.assertEqual(format_for_display(1.0 + 5e-10), "1.0000")
        self.assertEqual(format_for_display(1.0000000000000007), "1.0000")

    def test_int_input_accepted(self) -> None:
        self.assertEqual(format_for_display(7), "7.0000")

    def test_rejects_non_numbers(self) -> None:
        for bad in (True, False, "0.5", None, [0.5], object()):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    format_for_display(bad)

    def test_rejects_non_finite(self) -> None:
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    format_for_display(bad)

    def test_deterministic(self) -> None:
        self.assertEqual(format_for_display(0.3333333333333333), format_for_display(1.0 / 3.0))


class TestSingleRoundingLocation(unittest.TestCase):
    """A6: rounding lives in exactly one place (services.format_for_display).

    Scans the production modules for rounding constructs (fixed-point
    format specifiers or ``round(`` calls). Test modules are excluded —
    assertions legitimately format expected strings.
    """

    PATTERN = re.compile(r":\.\d+f\b|\brand\s*\(")

    def test_only_services_rounds(self) -> None:
        offenders: list[str] = []
        for directory in ("universality", "ui"):
            for path in (ROOT / directory).glob("*.py"):
                source = path.read_text(encoding="utf-8")
                for lineno, line in enumerate(source.splitlines(), start=1):
                    if self.PATTERN.search(line):
                        offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
        for offender in offenders:
            self.assertIn("universality/services.py", offender, msg=offender)


class TestServiceErrorType(unittest.TestCase):
    def test_is_catchable_as_exception(self) -> None:
        try:
            raise ServiceError()
        except Exception as exc:  # plain-Exception catch works
            self.assertIsInstance(exc, ServiceError)

    def test_str_is_the_fixed_generic_message(self) -> None:
        self.assertEqual(str(ServiceError()), "Something went wrong. Please try again.")

    def test_is_frozen(self) -> None:
        with self.assertRaises(Exception):
            ServiceError().message = "hacked"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
