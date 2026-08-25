"""Validation-layer tests (mirror: module under test = universality/validation).

Coverage per ``docs/architecture.md`` §10 and the validation task:

- one negative and one positive case per V-code (V1–V21; V15 is reserved
  for the export layer and has no validation rule here);
- EPSILON boundary discipline (weight sum ``1 ± 5e-10`` accepted,
  ``1 ± 5e-8`` rejected);
- first-rejection-wins ordering (structural → domain);
- the user-mandated rules: 0.96 weight sums are errors (parameters and
  group weights), score 0 is rejected (A20), NaN/±Infinity/booleans/None/
  negatives/oversized/duplicates are rejected;
- no silent fixing (names stored as provided; totals validated, not
  normalized) and no internal-exception exposure (adversarial battery);
- module purity: permitted imports only, no forbidden constructs, no
  formula bodies.
"""

import ast
import math
import os
import unittest
from decimal import Decimal
from fractions import Fraction

from universality import validation
from universality.domain import Evaluation, Parameter, Score, UserGroup, Weight
from universality.validation import (
    ValidationRejection,
    validate,
    validate_group_weights,
)


def make_raw(**overrides) -> dict:
    """A fully valid baseline (TV1-shaped); ``overrides`` replace top-level keys."""
    raw = {
        "product": "Sample chair",
        "scale_max": 5,
        "parameters": [
            {"name": "P1", "weight": 0.5, "scores": {"fap": 5, "sap": 4, "dap": 3}},
            {"name": "P2", "weight": 0.5, "scores": {"fap": 3, "sap": 2, "dap": 1}},
        ],
    }
    raw.update(overrides)
    return raw


def assert_rejects(testcase, raw, code, field=None) -> ValidationRejection:
    """Assert ``validate(raw)`` raises ValidationRejection with ``code`` (and field)."""
    with testcase.assertRaises(ValidationRejection) as ctx:
        validate(raw)
    rejection = ctx.exception
    testcase.assertEqual(rejection.code, code, msg=f"expected {code}, got {rejection.code}: {rejection.message}")
    if field is not None:
        testcase.assertEqual(rejection.field, field)
    return rejection


class TestValidationRejection(unittest.TestCase):
    def test_is_a_catchable_exception_with_fields(self) -> None:
        rejection = ValidationRejection(code="V4", field="f", message="m")
        self.assertIsInstance(rejection, Exception)
        self.assertEqual(rejection.code, "V4")
        self.assertEqual(rejection.field, "f")
        self.assertEqual(rejection.message, "m")
        self.assertEqual(str(rejection), "m")  # displayed to the user verbatim
        try:
            validate({})
            self.fail("expected ValidationRejection")
        except ValidationRejection as caught:
            self.assertEqual(caught.message, str(caught))
            self.assertEqual(caught.code, "V16")  # {} lacks the required product name

    def test_is_frozen(self) -> None:
        rejection = ValidationRejection(code="V1", field="f", message="m")
        with self.assertRaises(AttributeError):
            rejection.code = "V2"  # type: ignore[misc]


class TestProduct(unittest.TestCase):
    """V16 / V17 / V18 — product name: required, bounded, no control chars."""

    def test_valid_product_is_stored_as_provided(self) -> None:
        for good in ("Sample chair", "x" * 100, "café ☕ — produit", " spaced "):
            evaluation = validate(make_raw(product=good))
            self.assertEqual(evaluation.product, good)  # never trimmed

    def test_missing_product_rejected(self) -> None:
        raw = make_raw()
        del raw["product"]
        assert_rejects(self, raw, "V16", "product")
        assert_rejects(self, make_raw(product=None), "V16", "product")

    def test_blank_product_rejected(self) -> None:
        for blank in ("", "   ", "\u2000"):
            assert_rejects(self, make_raw(product=blank), "V16", "product")

    def test_non_text_product_rejected(self) -> None:
        for bad in (5, True, ["x"], b"x", {"p": 1}):
            assert_rejects(self, make_raw(product=bad), "V19", "product")

    def test_oversized_product_rejected(self) -> None:
        assert_rejects(self, make_raw(product="x" * 101), "V17", "product")

    def test_control_characters_in_product_rejected(self) -> None:
        for char in ("\x00", "\t", "\n", "\x1f", "\x7f", "\x80", "\x9f"):
            assert_rejects(self, make_raw(product=f"a{char}b"), "V18", "product")

    def test_non_control_unicode_is_accepted(self) -> None:
        # U+2028 (line separator) is NOT in the A18 control set — accepted.
        evaluation = validate(make_raw(product="a\u2028b"))
        self.assertEqual(evaluation.product, "a\u2028b")


class TestParametersStructure(unittest.TestCase):
    """V7 / V12 / V19 — presence, container shape, count, sub-object shape."""

    def test_valid_single_and_many_parameters(self) -> None:
        self.assertEqual(len(validate(make_raw()).parameters), 2)
        one = make_raw(parameters=[{"name": "Only", "weight": 1.0, "scores": {"fap": 2, "sap": 2, "dap": 2}}])
        self.assertEqual(len(validate(one).parameters), 1)
        many = make_raw(parameters=[
            {"name": f"P{i}", "weight": 0.01, "scores": {"fap": 1, "sap": 1, "dap": 1}}
            for i in range(100)
        ])
        self.assertEqual(len(validate(many).parameters), 100)

    def test_empty_parameter_list_rejected(self) -> None:
        assert_rejects(self, make_raw(parameters=[]), "V12", "parameters")

    def test_101_parameters_rejected(self) -> None:
        params = [
            {"name": f"P{i}", "weight": 1.0 / 101, "scores": {"fap": 1, "sap": 1, "dap": 1}}
            for i in range(101)
        ]
        assert_rejects(self, make_raw(parameters=params), "V12", "parameters")

    def test_missing_parameters_rejected(self) -> None:
        raw = make_raw()
        del raw["parameters"]
        assert_rejects(self, raw, "V7", "parameters")
        assert_rejects(self, make_raw(parameters=None), "V7", "parameters")

    def test_non_list_parameters_rejected(self) -> None:
        for bad in ("nope", {"a": 1}, ({"name": "A"},), 5):
            assert_rejects(self, make_raw(parameters=bad), "V19", "parameters")

    def test_parameter_entry_must_be_an_object(self) -> None:
        for bad in ("str", 1, ["x"], None, 0.5):
            assert_rejects(self, make_raw(parameters=[bad]), "V19", "parameters[0]")

    def test_missing_parameter_parts_rejected(self) -> None:
        base = {"name": "P1", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}}
        for key in ("name", "weight", "scores"):
            raw_params = dict(base)
            del raw_params[key]
            assert_rejects(self, make_raw(parameters=[raw_params]), "V7", f"parameters[0].{key}")
        for key in ("name", "weight", "scores"):
            raw_params = dict(base, **{key: None})
            assert_rejects(self, make_raw(parameters=[raw_params]), "V7", f"parameters[0].{key}")

    def test_non_text_name_rejected(self) -> None:
        for bad in (5, True, [], b"x"):
            assert_rejects(
                self,
                make_raw(parameters=[{"name": bad, "weight": 1.0, "scores": {"fap": 1, "sap": 1, "dap": 1}}]),
                "V19", "parameters[0].name",
            )

    def test_blank_name_rejected(self) -> None:
        for blank in ("", "   "):
            assert_rejects(
                self,
                make_raw(parameters=[{"name": blank, "weight": 1.0, "scores": {"fap": 1, "sap": 1, "dap": 1}}]),
                "V7", "parameters[0].name",
            )

    def test_non_object_scores_rejected(self) -> None:
        for bad in ("x", [1, 2, 3], 5, ()):
            assert_rejects(
                self,
                make_raw(parameters=[{"name": "P1", "weight": 1.0, "scores": bad}]),
                "V19", "parameters[0].scores",
            )

    def test_unknown_keys_are_ignored_not_rejected(self) -> None:
        evaluation = validate(make_raw(extra="ignored", parameters=[
            {"name": "P1", "weight": 1.0, "scores": {"fap": 1, "sap": 1, "dap": 1, "extra": 9}, "note": "x"},
        ]))
        self.assertEqual(len(evaluation.parameters), 1)


class TestParameterNames(unittest.TestCase):
    """V9 / V10 / V8 — bounded length, control characters, uniqueness."""

    def single(self, name, weight=1.0) -> dict:
        return make_raw(parameters=[{"name": name, "weight": weight, "scores": {"fap": 1, "sap": 1, "dap": 1}}])

    def test_name_length_boundaries(self) -> None:
        self.assertEqual(validate(self.single("x" * 100)).parameters[0].name, "x" * 100)
        assert_rejects(self, self.single("x" * 101), "V9", "parameters[0].name")

    def test_control_characters_rejected(self) -> None:
        for char in ("\x00", "\x07", "\n", "\x1f", "\x7f", "\x80", "\x9f"):
            assert_rejects(self, self.single(f"a{char}b"), "V10", "parameters[0].name")

    def test_duplicates_rejected_exact_case_and_trimming(self) -> None:
        dup_pairs = [
            ("P1", "P1"),   # exact
            ("P1", "p1"),   # case-insensitive (A10/A18)
            (" P1 ", "p1"), # case-insensitive after trimming
            ("A", " a "),
        ]
        for first, second in dup_pairs:
            raw = make_raw(parameters=[
                {"name": first, "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
                {"name": second, "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            ])
            rejection = assert_rejects(self, raw, "V8", "parameters[1].name")
            self.assertIn(second, rejection.message)

    def test_distinct_names_accepted(self) -> None:
        evaluation = validate(make_raw(parameters=[
            {"name": "A", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "AB", "weight": 0.25, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "a b", "weight": 0.25, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ]))
        self.assertEqual([p.name for p in evaluation.parameters], ["A", "AB", "a b"])


class TestScale(unittest.TestCase):
    """V7 / V3 / V11 — scale_max: required, integer, 2..100."""

    def test_valid_scale_boundaries(self) -> None:
        for scale in (2, 5, 50, 100):
            raw = make_raw(scale_max=scale, parameters=[
                {"name": "P1", "weight": 1.0, "scores": {"fap": 1, "sap": 1, "dap": scale}},
            ])
            self.assertEqual(validate(raw).scale_max, scale)

    def test_missing_scale_rejected(self) -> None:
        raw = make_raw()
        del raw["scale_max"]
        assert_rejects(self, raw, "V7", "scale_max")
        assert_rejects(self, make_raw(scale_max=None), "V7", "scale_max")

    def test_boolean_scale_rejected(self) -> None:
        assert_rejects(self, make_raw(scale_max=True), "V3", "scale_max")
        assert_rejects(self, make_raw(scale_max=False), "V3", "scale_max")

    def test_non_integer_or_out_of_range_scale_rejected(self) -> None:
        for bad in (0, 1, 101, -5, 10**9, 5.0, 2.5, "5", [5], {}):
            assert_rejects(self, make_raw(scale_max=bad), "V11", "scale_max")


class TestParameterWeights(unittest.TestCase):
    """V7 / V3 / V13 / V1 / V2 / V5 / V6 — finite, >= 0, <= 1, sum to 1."""

    def with_weight(self, weight, name="P1") -> dict:
        return make_raw(parameters=[{"name": name, "weight": weight, "scores": {"fap": 1, "sap": 1, "dap": 1}}])

    def test_missing_weight_rejected(self) -> None:
        raw = make_raw()
        del raw["parameters"][0]["weight"]
        assert_rejects(self, raw, "V7", "parameters[0].weight")

    def test_boolean_weight_rejected(self) -> None:
        assert_rejects(self, self.with_weight(True), "V3", "parameters[0].weight")
        assert_rejects(self, self.with_weight(False), "V3", "parameters[0].weight")

    def test_non_numeric_weight_rejected(self) -> None:
        for bad in ("0.5", 0.5j, {}, [], Decimal("0.5"), b"1"):
            assert_rejects(self, self.with_weight(bad), "V13", "parameters[0].weight")

    def test_nan_and_infinity_rejected(self) -> None:
        assert_rejects(self, self.with_weight(float("nan")), "V1", "parameters[0].weight")
        assert_rejects(self, self.with_weight(float("inf")), "V2", "parameters[0].weight")
        assert_rejects(self, self.with_weight(float("-inf")), "V2", "parameters[0].weight")

    def test_negative_or_over_unity_weight_rejected(self) -> None:
        for bad in (-0.001, -1, 1.0000001, 2.0):
            assert_rejects(self, self.with_weight(bad), "V5", "parameters[0].weight")

    def test_weight_sum_0_96_is_an_error(self) -> None:
        # The user-mandated rule: a total of 0.96 is an error, never
        # silently normalized to 1.
        raw = make_raw(parameters=[
            {"name": "P1", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "P2", "weight": 0.46, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ])
        assert_rejects(self, raw, "V6", "parameters")

    def _two_weight_raw(self, w1: float, w2: float) -> dict:
        # Split the total across two parameters so each individual weight
        # stays within [0, 1] (V5) and only the SUM is under test (V6).
        return make_raw(parameters=[
            {"name": "P1", "weight": w1, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "P2", "weight": w2, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ])

    def test_weight_sum_epsilon_boundary(self) -> None:
        # |sum - 1| <= 5e-10 is within EPSILON (1e-9) → accepted (A5).
        for w1, w2 in ((0.5 - 2.5e-10, 0.5), (0.5 + 2.5e-10, 0.5)):
            evaluation = validate(self._two_weight_raw(w1, w2))
            self.assertEqual(evaluation.parameters[0].weight.value, w1)
            self.assertEqual(evaluation.parameters[1].weight.value, w2)
        # |sum - 1| >= 5e-8 exceeds EPSILON → rejected (V6).
        for w1, w2 in ((0.5 - 2.5e-8, 0.5), (0.5 + 2.5e-8, 0.5)):
            assert_rejects(self, self._two_weight_raw(w1, w2), "V6", "parameters")

    def test_zero_weights_allowed(self) -> None:
        # A9: zero means "contributes nothing", not an error.
        raw = make_raw(parameters=[
            {"name": "P1", "weight": 0.0, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "P2", "weight": 1.0, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ])
        self.assertEqual(validate(raw).parameters[0].weight.value, 0.0)

    def test_decimal_weights_bit_exact_sum(self) -> None:
        # 0.3333333333333333 + 0.3333333333333333 + 0.3333333333333334 == 1.0
        # exactly in IEEE-754 (CPython round-to-even) → accepted.
        raw = make_raw(parameters=[
            {"name": f"P{i}", "weight": w, "scores": {"fap": 1, "sap": 1, "dap": 1}}
            for i, w in enumerate((0.3333333333333333, 0.3333333333333333, 0.3333333333333334))
        ])
        self.assertEqual(len(validate(raw).parameters), 3)


class TestScores(unittest.TestCase):
    """V14 / V7 / V13 / V3 / V1 / V2 / V4 — finite, numeric, not boolean, 1..scale_max."""

    def with_score(self, score, group="fap", scale_max=5) -> dict:
        scores = {"fap": 1, "sap": 1, "dap": 1}
        scores[group] = score
        return make_raw(scale_max=scale_max, parameters=[{"name": "P1", "weight": 1.0, "scores": scores}])

    def test_missing_group_score_rejected(self) -> None:
        for group in ("fap", "sap", "dap"):
            raw = make_raw()
            del raw["parameters"][0]["scores"][group]
            assert_rejects(self, raw, "V14", f"parameters[0].scores.{group}")
            raw = make_raw()
            raw["parameters"][0]["scores"][group] = None
            assert_rejects(self, raw, "V14", f"parameters[0].scores.{group}")

    def test_non_numeric_score_rejected(self) -> None:
        for bad in ("3", [], {}, 3j, b"3", Fraction(3, 2)):
            assert_rejects(self, self.with_score(bad), "V13", "parameters[0].scores.fap")

    def test_boolean_score_rejected(self) -> None:
        assert_rejects(self, self.with_score(True), "V3", "parameters[0].scores.fap")
        assert_rejects(self, self.with_score(False), "V3", "parameters[0].scores.fap")

    def test_nan_and_infinity_rejected(self) -> None:
        assert_rejects(self, self.with_score(float("nan")), "V1", "parameters[0].scores.fap")
        assert_rejects(self, self.with_score(float("inf")), "V2", "parameters[0].scores.fap")
        assert_rejects(self, self.with_score(float("-inf")), "V2", "parameters[0].scores.fap")

    def test_negative_and_zero_scores_rejected(self) -> None:
        # A20 (explicit user instruction): the user-input minimum is 1 —
        # 0 is no longer a valid user score (the engine domain stays [0, scale_max]).
        assert_rejects(self, self.with_score(-1), "V4", "parameters[0].scores.fap")
        assert_rejects(self, self.with_score(0), "V4", "parameters[0].scores.fap")
        assert_rejects(self, self.with_score(0.5), "V4", "parameters[0].scores.fap")

    def test_score_above_scale_max_rejected(self) -> None:
        assert_rejects(self, self.with_score(6), "V4", "parameters[0].scores.fap")
        assert_rejects(self, self.with_score(100), "V4", "parameters[0].scores.fap")

    def test_score_boundaries_accepted(self) -> None:
        self.assertEqual(validate(self.with_score(1)).parameters[0].scores.for_group(UserGroup.FAP).value, 1.0)
        self.assertEqual(validate(self.with_score(5)).parameters[0].scores.for_group(UserGroup.FAP).value, 5.0)
        self.assertEqual(validate(self.with_score(3.5)).parameters[0].scores.for_group(UserGroup.FAP).value, 3.5)
        self.assertEqual(validate(self.with_score(100, scale_max=100)).parameters[0].scores.for_group(UserGroup.FAP).value, 100.0)


class TestGroupWeights(unittest.TestCase):
    """V20 / V21 + value rules — group weights sum to 1 (defensive gate).

    Group weights are not raw user input in Simple Mode (A1, A8; M5);
    the validator protects the rule and the constant the application
    uses, and is the single validator the application layer applies.
    """

    def test_valid_group_weights(self) -> None:
        for triple in ((1 / 3, 1 / 3, 1 / 3), (0.5, 0.25, 0.25), (0.5, 0.5, 0.0), [0.4, 0.3, 0.3]):
            self.assertEqual(validate_group_weights(triple), tuple(float(w) for w in triple))
        # EPSILON tolerance: 1/3 + 1/3 + (1/3 + 5e-10) sums within EPSILON.
        self.assertEqual(
            validate_group_weights((1 / 3, 1 / 3, 1 / 3 + 5e-10)),
            (1 / 3, 1 / 3, 1 / 3 + 5e-10),
        )

    def test_group_weight_sum_0_96_is_an_error(self) -> None:
        rejection = self.assertRejectsSum((0.48, 0.26, 0.22))
        self.assertEqual(rejection.code, "V21")

    def test_group_weight_sum_epsilon_boundary(self) -> None:
        assert_rejection = self.assertRejectsSum((1 / 3, 1 / 3, 1 / 3 + 5e-8))
        self.assertEqual(assert_rejection.code, "V21")

    def test_wrong_arity_or_shape_rejected(self) -> None:
        for bad in ((), (0.5, 0.5), (0.25,) * 4, "abc", None, 5, {}, [5]):
            with self.assertRaises(ValidationRejection) as ctx:
                validate_group_weights(bad)
            self.assertEqual(ctx.exception.code, "V20")

    def test_value_rules_apply_per_element(self) -> None:
        cases = (
            ((True, 0.5, 0.5), "V3"),
            (("0.5", 0.25, 0.25), "V13"),
            ((float("nan"), 0.5, 0.5), "V1"),
            ((float("inf"), 0.5, 0.5), "V2"),
            ((-0.1, 0.6, 0.5), "V5"),
            ((1.5, -0.5, 0.0), "V5"),
        )
        for triple, code in cases:
            with self.assertRaises(ValidationRejection) as ctx:
                validate_group_weights(triple)
            self.assertEqual(ctx.exception.code, code, msg=repr(triple))

    def assertRejectsSum(self, triple):
        with self.assertRaises(ValidationRejection) as ctx:
            validate_group_weights(triple)
        return ctx.exception


class TestFirstRejectionWins(unittest.TestCase):
    """Ordering: structural → domain, in the documented sequence."""

    def test_product_precedes_scale_and_scores(self) -> None:
        raw = make_raw(product="", scale_max=1, parameters=[
            {"name": "P1", "weight": -1, "scores": {"fap": 99, "sap": 1, "dap": 1}},
        ])
        assert_rejects(self, raw, "V16", "product")

    def test_product_length_precedes_control_chars(self) -> None:
        assert_rejects(self, make_raw(product="x" * 100 + "\x00"), "V17", "product")

    def test_scale_precedes_weight_and_score(self) -> None:
        raw = make_raw(scale_max=1, parameters=[
            {"name": "P1", "weight": -1, "scores": {"fap": 99, "sap": 1, "dap": 1}},
        ])
        assert_rejects(self, raw, "V11", "scale_max")

    def test_structural_precedes_domain_same_field(self) -> None:
        # weight None (structural V7) beats weight NaN (domain V1).
        raw = make_raw(parameters=[
            {"name": "P1", "weight": None, "scores": {"fap": float("nan"), "sap": 1, "dap": 1}},
        ])
        assert_rejects(self, raw, "V7", "parameters[0].weight")

    def test_first_parameter_precedes_later_parameters(self) -> None:
        raw = make_raw(parameters=[
            {"name": "P1", "weight": True, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "P2", "weight": 0.5, "scores": {"fap": 99, "sap": 1, "dap": 1}},
        ])
        assert_rejects(self, raw, "V3", "parameters[0].weight")

    def test_group_key_order_fap_sap_dap(self) -> None:
        raw = make_raw(parameters=[
            {"name": "P1", "weight": 1.0, "scores": {"sap": float("nan"), "dap": 99}},
        ])
        assert_rejects(self, raw, "V14", "parameters[0].scores.fap")

    def test_name_length_precedes_control_chars(self) -> None:
        raw = make_raw(parameters=[{"name": "x" * 100 + "\x00", "weight": 1.0, "scores": {"fap": 1, "sap": 1, "dap": 1}}])
        assert_rejects(self, raw, "V9", "parameters[0].name")

    def test_duplicate_precedes_weight_sum(self) -> None:
        raw = make_raw(parameters=[
            {"name": "A", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "a", "weight": 0.4, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ])
        assert_rejects(self, raw, "V8", "parameters[1].name")

    def test_weight_value_precedes_score_value(self) -> None:
        raw = make_raw(parameters=[
            {"name": "P1", "weight": -1, "scores": {"fap": 0, "sap": 1, "dap": 1}},
        ])
        assert_rejects(self, raw, "V5", "parameters[0].weight")


class TestNoSilentFixing(unittest.TestCase):
    """Input is validated, never repaired, trimmed, or rescaled."""

    def test_names_stored_exactly_as_provided(self) -> None:
        raw = make_raw(product="  Padded  ", parameters=[
            {"name": "  Spaced  ", "weight": 1.0, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ])
        evaluation = validate(raw)
        self.assertEqual(evaluation.product, "  Padded  ")
        self.assertEqual(evaluation.parameters[0].name, "  Spaced  ")

    def test_wrong_weight_total_never_rescaled(self) -> None:
        raw = make_raw(parameters=[
            {"name": "P1", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "P2", "weight": 0.46, "scores": {"fap": 1, "sap": 1, "dap": 1}},
        ])
        with self.assertRaises(ValidationRejection) as ctx:
            validate(raw)
        self.assertEqual(ctx.exception.code, "V6")

    def test_missing_scores_never_converted_to_zero(self) -> None:
        raw = make_raw()
        del raw["parameters"][0]["scores"]["dap"]
        with self.assertRaises(ValidationRejection) as ctx:
            validate(raw)
        self.assertEqual(ctx.exception.code, "V14")


class TestNoInternalExposure(unittest.TestCase):
    """Adversarial battery: only ValidationRejection ever escapes; messages
    never leak internal exceptions, types, or stack traces."""

    FORBIDDEN_SUBSTRINGS = (
        "Traceback", "DomainInvariantError", "ValueError", "KeyError",
        "TypeError", "AttributeError", "IndexError", "universality.domain",
        "built-in", "def ", "raise",
    )

    def adversarial_raws(self):
        yield None
        yield []
        yield "not a dict"
        yield 42
        yield set()
        yield object()
        yield {"product": object()}
        yield {"product": "x" * 101, "scale_max": 5, "parameters": []}
        yield {"scale_max": [5], "parameters": []}
        yield {"scale_max": complex(2), "parameters": []}
        yield {"parameters": {"a": 1}}
        yield {"parameters": [object()]}
        yield {"parameters": [{"name": object(), "weight": 1.0, "scores": {}}]}
        yield {"parameters": [{"name": "A", "weight": "x", "scores": {}}]}
        yield {"parameters": [{"name": "A", "weight": 0.5, "scores": {}}]}
        yield {"parameters": [{"name": "A", "weight": 0.5, "scores": {"fap": object(), "sap": 1, "dap": 1}}]}
        yield {"parameters": [{"name": "A", "weight": 0.5, "scores": {"fap": memoryview(b"abc"), "sap": 1, "dap": 1}}]}
        yield {"parameters": [{"name": "A", "weight": 0.5, "scores": {"fap": Fraction(1, 2), "sap": 1, "dap": 1}}]}
        # one hostile parameter deep in a large (otherwise valid) list
        params = [{"name": f"P{i}", "weight": 0.01, "scores": {"fap": 1, "sap": 1, "dap": 1}} for i in range(100)]
        params[99] = {"name": object(), "weight": 0.01, "scores": {"fap": 1, "sap": 1, "dap": 1}}
        yield {"product": "X", "scale_max": 5, "parameters": params}

    def test_battery_never_exposes_internal_exceptions(self) -> None:
        for i, raw in enumerate(self.adversarial_raws()):
            with self.subTest(i=i):
                with self.assertRaises(ValidationRejection) as ctx:
                    validate(raw)
                message = ctx.exception.message
                for fragment in self.FORBIDDEN_SUBSTRINGS:
                    self.assertNotIn(fragment, message, msg=f"case {i}: {message!r}")


class TestBuildsDomain(unittest.TestCase):
    """Positive path: raw dict → frozen, trusted Evaluation."""

    def test_baseline_builds_expected_domain_object(self) -> None:
        evaluation = validate(make_raw())
        self.assertIsInstance(evaluation, Evaluation)
        self.assertEqual(evaluation.product, "Sample chair")
        self.assertEqual(evaluation.scale_max, 5)
        expected = Evaluation(
            product="Sample chair",
            scale_max=5,
            parameters=(
                Parameter("P1", Weight(0.5), scores_for(5, 4, 3)),
                Parameter("P2", Weight(0.5), scores_for(3, 2, 1)),
            ),
        )
        self.assertEqual(evaluation, expected)

    def test_int_scores_stored_as_equivalent_floats(self) -> None:
        evaluation = validate(make_raw())
        self.assertEqual(evaluation.parameters[0].scores.for_group(UserGroup.FAP).value, 5.0)
        self.assertIsInstance(evaluation.parameters[0].scores.for_group(UserGroup.FAP).value, float)

    def test_repeated_validation_is_deterministic(self) -> None:
        raw1 = make_raw()
        raw2 = make_raw()
        self.assertEqual(validate(raw1), validate(raw2))

    def test_full_range_evaluation_builds(self) -> None:
        raw = make_raw(scale_max=100, parameters=[
            {"name": "Low", "weight": 0.5, "scores": {"fap": 1, "sap": 1, "dap": 1}},
            {"name": "High", "weight": 0.5, "scores": {"fap": 100, "sap": 100, "dap": 100}},
        ])
        evaluation = validate(raw)
        self.assertEqual(evaluation.scale_max, 100)
        self.assertEqual(evaluation.parameters[1].scores.for_group(UserGroup.DAP).value, 100.0)


def scores_for(fap, sap, dap):
    from universality.domain import GroupScores

    return GroupScores(Score(fap), Score(sap), Score(dap))


class TestValidationModulePurity(unittest.TestCase):
    """The module obeys the import policy and the forbidden-constructs table."""

    def _source(self) -> str:
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "universality", "validation.py",
        )
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_imports_only_permitted_modules(self) -> None:
        tree = ast.parse(self._source())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module.split(".")[0])
        self.assertTrue(
            imported <= {"math", "dataclasses", "typing", "__future__", "universality"},
            msg=f"unexpected imports: {imported}",
        )
        self.assertFalse(imported & {"streamlit", "services", "ui", "diagnostics", "export"},
                         msg="validation must not import other layers")

    def test_no_forbidden_constructs(self) -> None:
        tree = ast.parse(self._source())
        forbidden = {"eval", "exec", "pickle", "system", "shell", "compile", "input"}
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in forbidden:
                found.add(node.func.id)
            elif isinstance(node, ast.Name) and node.id in forbidden:
                found.add(node.id)
        self.assertEqual(found, set(), msg=f"forbidden identifiers: {found}")

    def test_contains_no_formula_bodies(self) -> None:
        # Formulas live in FORMULA_SPECIFICATION.md / calculation.py only.
        source = self._source()
        for fragment in ("Σ", "s_norm(i, G) =", "/ scale_max"):
            self.assertNotIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
