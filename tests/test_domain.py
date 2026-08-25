"""Constraint tests for the domain model (``universality/domain.py``).

Scope: DOMAIN layer only (per the task instruction "do not continue to
other layers"). Covers, per ``docs/DOMAIN_MODEL.md``:

- every field's valid range (type-level invariants);
- required/optional status (all fields required — construction without a
  field is a TypeError by construction of the dataclass);
- immutability;
- the C1/C2 sum predicate (single implementation);
- domain purity: standard-library-only imports, no UI/framework, no
  research formulas (F1–F4 must not appear here).
"""

from __future__ import annotations

import ast
import math
import os
import unittest
from dataclasses import FrozenInstanceError

from universality import domain
from universality.domain import (
    EPSILON,
    DomainInvariantError,
    Evaluation,
    EvaluationOutcome,
    EvaluationResult,
    GroupScores,
    KanoCategory,
    Parameter,
    ParameterResult,
    PerGroupValue,
    Score,
    UserGroup,
    Weight,
    weights_sum_is_valid,
)


def make_parameter(
    name: str = "P1",
    weight: float = 0.5,
    fap: float = 5.0,
    sap: float = 4.0,
    dap: float = 3.0,
) -> Parameter:
    return Parameter(
        name=name,
        weight=Weight(weight),
        scores=GroupScores(Score(fap), Score(sap), Score(dap)),
    )


def make_evaluation(n: int = 2, scale_max: int = 5) -> Evaluation:
    """n distinct parameters, equal weights 1/n (valid under C1/EPSILON)."""
    return Evaluation(
        product="Test product",
        scale_max=scale_max,
        parameters=tuple(
            make_parameter(name=f"P{i}", weight=1.0 / n, fap=scale_max, sap=scale_max / 2, dap=1.0)
            for i in range(n)
        ),
    )


def make_result(n: int = 2, overall: float = 0.6, group_gap: float = 0.4) -> EvaluationResult:
    groups = PerGroupValue(0.8, 0.6, 0.4)
    return EvaluationResult(
        group_indices=groups,
        overall=overall,
        group_gap=group_gap,
        parameters=tuple(
            ParameterResult(
                name=f"P{i}",
                weight=Weight(1.0 / n),
                normalized=PerGroupValue(1.0, 0.5, 0.5),
                contributions=PerGroupValue(1.0 / n, 0.5 / n, 0.5 / n),
            )
            for i in range(n)
        ),
    )


class TestUserGroup(unittest.TestCase):
    def test_exactly_three_members_with_research_labels(self) -> None:
        self.assertEqual(
            {member.value for member in UserGroup}, {"FAP", "SAP", "DAP"}
        )
        self.assertEqual(UserGroup.FAP.label, "Fully Abled People")
        self.assertEqual(UserGroup.SAP.label, "Specially Abled People")
        self.assertEqual(UserGroup.DAP.label, "Differently Abled People")

    def test_enum_is_immutable(self) -> None:
        with self.assertRaises(AttributeError):
            UserGroup.FAP.value = "X"  # type: ignore[misc]


class TestKanoCategory(unittest.TestCase):
    def test_exactly_five_standard_members(self) -> None:
        self.assertEqual(
            {member.value for member in KanoCategory},
            {"must_be", "one_dimensional", "attractive", "indifferent", "reverse"},
        )

    def test_inert_vocabulary_no_behavior(self) -> None:
        # M2 scope: the type carries vocabulary only — no classification
        # or scoring behavior may exist on it (docs/LIMITATIONS.md).
        for attribute in ("classify", "score", "calculate", "weight"):
            self.assertFalse(hasattr(KanoCategory, attribute))


class TestScore(unittest.TestCase):
    def test_valid_values(self) -> None:
        for value in (0, 0.0, 1, 4.2, 100):
            self.assertEqual(Score(value).value, float(value))

    def test_int_is_stored_as_the_same_real_number(self) -> None:
        self.assertIsInstance(Score(5).value, float)
        self.assertEqual(Score(5).value, 5.0)

    def test_rejects_negative_nan_infinity_and_booleans(self) -> None:
        for bad in (-0.1, float("nan"), float("inf"), float("-inf"), True, False, "5", None, [1]):
            with self.assertRaises(DomainInvariantError, msg=repr(bad)):
                Score(bad)  # type: ignore[arg-type]


class TestWeight(unittest.TestCase):
    def test_valid_range_including_boundaries(self) -> None:
        for value in (0, 0.0, 1, 1.0, 0.5):
            self.assertEqual(Weight(value).value, float(value))

    def test_rejects_out_of_range_nan_infinity_and_booleans(self) -> None:
        for bad in (-0.01, 1.0000001, 5, float("nan"), float("inf"), True, False, "0.5"):
            with self.assertRaises(DomainInvariantError, msg=repr(bad)):
                Weight(bad)  # type: ignore[arg-type]


class TestGroupScores(unittest.TestCase):
    def test_holds_all_three_groups(self) -> None:
        scores = GroupScores(Score(1), Score(2), Score(3))
        self.assertEqual((scores.fap.value, scores.sap.value, scores.dap.value), (1.0, 2.0, 3.0))

    def test_for_group_accessor(self) -> None:
        scores = GroupScores(Score(1), Score(2), Score(3))
        self.assertEqual(scores.for_group(UserGroup.FAP).value, 1.0)
        self.assertEqual(scores.for_group(UserGroup.SAP).value, 2.0)
        self.assertEqual(scores.for_group(UserGroup.DAP).value, 3.0)

    def test_all_fields_required(self) -> None:
        with self.assertRaises(TypeError):
            GroupScores(fap=Score(1), sap=Score(2))  # type: ignore[call-arg]


class TestParameter(unittest.TestCase):
    def test_valid_names(self) -> None:
        for name in ("a", "P" * 100, "Üniversität & Ease-of-use"):
            self.assertEqual(make_parameter(name=name).name, name)

    def test_rejects_invalid_names(self) -> None:
        for bad in ("", "   ", "P" * 101, "a\nb", "a\x00b", "a\x7fb", "a\x80b", 42):
            with self.assertRaises(DomainInvariantError, msg=repr(bad)):
                Parameter(name=bad, weight=Weight(1.0),  # type: ignore[arg-type]
                          scores=GroupScores(Score(0), Score(0), Score(0)))

    def test_rejects_wrong_component_types(self) -> None:
        good_scores = GroupScores(Score(1), Score(1), Score(1))
        with self.assertRaises(DomainInvariantError):
            Parameter(name="P1", weight=0.5, scores=good_scores)  # type: ignore[arg-type]
        with self.assertRaises(DomainInvariantError):
            Parameter(name="P1", weight=Weight(0.5), scores=1.0)  # type: ignore[arg-type]


class TestEvaluation(unittest.TestCase):
    def test_valid_scale_boundaries(self) -> None:
        for scale in (2, 5, 10, 100):
            self.assertEqual(make_evaluation(n=2, scale_max=scale).scale_max, scale)

    def test_product_stored_as_provided(self) -> None:
        evaluation = make_evaluation()
        self.assertEqual(evaluation.product, "Test product")
        padded = Evaluation(
            product="  Padded  Name  ",
            scale_max=5,
            parameters=(make_parameter(weight=1.0),),
        )
        self.assertEqual(padded.product, "  Padded  Name  ")  # never trimmed

    def test_rejects_invalid_product(self) -> None:
        bad_products = (
            "",            # empty
            "   ",          # whitespace only
            "a\x00b",       # C0 control
            "a\x1fb",       # C0 control (unit separator)
            "a\x7fb",       # DEL
            "a\x80b",       # C1 control (first)
            "a\x9fb",       # C1 control (last)
            "x" * 101,      # too long
            5,              # not a string
            True,           # not a string
            None,           # not a string
        )
        for bad in bad_products:
            with self.assertRaises(DomainInvariantError, msg=repr(bad)):
                Evaluation(
                    product=bad,  # type: ignore[arg-type]
                    scale_max=5,
                    parameters=(make_parameter(),),
                )

    def test_product_boundaries_are_valid(self) -> None:
        for good in ("a", "x" * 100, "café ☕ — product", " spaced "):
            evaluation = Evaluation(
                product=good,
                scale_max=5,
                parameters=(make_parameter(weight=1.0),),
            )
            self.assertEqual(evaluation.product, good)

    def test_rejects_invalid_scale(self) -> None:
        for bad in (0, 1, 101, True, 5.0, "5", None):
            with self.assertRaises(DomainInvariantError, msg=repr(bad)):
                Evaluation(product="Test product", scale_max=bad, parameters=(make_parameter(),))  # type: ignore[arg-type]

    def test_rejects_empty_parameter_list(self) -> None:
        with self.assertRaises(DomainInvariantError):
            Evaluation(product="Test product", scale_max=5, parameters=())

    def test_rejects_non_tuple_parameter_container(self) -> None:
        with self.assertRaises(DomainInvariantError):
            Evaluation(product="Test product", scale_max=5, parameters=[make_parameter()])  # type: ignore[arg-type]

    def test_single_parameter_is_valid(self) -> None:
        self.assertEqual(len(make_evaluation(n=1).parameters), 1)

    def test_max_parameters_boundary(self) -> None:
        self.assertEqual(len(make_evaluation(n=100).parameters), 100)

    def test_rejects_101_parameters(self) -> None:
        with self.assertRaises(DomainInvariantError):
            make_evaluation(n=101)

    def test_rejects_duplicate_names_case_insensitive_after_trim(self) -> None:
        p1 = make_parameter(name="Ease of use", weight=0.5)
        for other in ("ease of use", "EASE OF USE", "  ease of use  "):
            with self.assertRaises(DomainInvariantError, msg=other):
                Evaluation(product="Test product", scale_max=5, parameters=(p1, make_parameter(name=other, weight=0.5)))

    def test_allows_distinct_names(self) -> None:
        evaluation = Evaluation(
            product="Test product",
            scale_max=5,
            parameters=(make_parameter(name="Stability", weight=0.5),
                        make_parameter(name="Stability risk", weight=0.5)),
        )
        self.assertEqual(len(evaluation.parameters), 2)

    def test_score_equal_to_scale_max_is_valid(self) -> None:
        self.assertEqual(make_evaluation(n=1, scale_max=5).parameters[0].scores.fap.value, 5.0)

    def test_rejects_score_above_scale_max(self) -> None:
        with self.assertRaises(DomainInvariantError):
            Evaluation(
                product="Test product",
                scale_max=5,
                parameters=(make_parameter(name="P1", weight=1.0, fap=5.5),),
            )

    def test_rejects_negative_scale_via_score(self) -> None:
        with self.assertRaises(DomainInvariantError):
            make_parameter(name="P1", weight=1.0, fap=-1.0)

    def test_weight_sum_exactly_one(self) -> None:
        evaluation = Evaluation(
            product="Test product",
            scale_max=5,
            parameters=(make_parameter(name="A", weight=0.5),
                        make_parameter(name="B", weight=0.5)),
        )
        self.assertEqual(len(evaluation.parameters), 2)

    def test_weight_sum_within_epsilon_accepted(self) -> None:
        # 1/3 + 1/3 + 1/3 = 0.9999999999999998 in IEEE-754 — within EPSILON.
        evaluation = Evaluation(
            product="Test product",
            scale_max=5,
            parameters=(make_parameter(name="A", weight=1 / 3),
                        make_parameter(name="B", weight=1 / 3),
                        make_parameter(name="C", weight=1 / 3)),
        )
        self.assertEqual(len(evaluation.parameters), 3)

    def test_weight_sum_just_within_epsilon_accepted(self) -> None:
        evaluation = Evaluation(
            product="Test product",
            scale_max=5,
            parameters=(make_parameter(name="A", weight=0.5 + 2.5e-10),
                        make_parameter(name="B", weight=0.5),
                        make_parameter(name="C", weight=2.5e-10)),
        )
        self.assertEqual(len(evaluation.parameters), 3)

    def test_rejects_weight_sum_outside_epsilon(self) -> None:
        for weights in ((0.4, 0.3, 0.25), (0.6, 0.6, 0.6), (0.5,)):
            with self.assertRaises(DomainInvariantError, msg=repr(weights)):
                Evaluation(
                    product="Test product",
                    scale_max=5,
                    parameters=tuple(
                        make_parameter(name=f"P{i}", weight=w) for i, w in enumerate(weights)
                    ),
                )


class TestPerGroupValue(unittest.TestCase):
    def test_valid_values(self) -> None:
        values = PerGroupValue(0.0, 0.5, 1.0)
        self.assertEqual((values.fap, values.sap, values.dap), (0.0, 0.5, 1.0))

    def test_rejects_negative_nan_infinity_and_booleans(self) -> None:
        for bad in (-1e-12, float("nan"), float("inf"), True, "0.5"):
            with self.assertRaises(DomainInvariantError, msg=repr(bad)):
                PerGroupValue(bad, 0.5, 0.5)  # type: ignore[arg-type]

    def test_type_domain_is_wider_than_usage_domains(self) -> None:
        # Documented: the type domain is "finite and >= 0"; usage-specific
        # upper bounds ([0, 1] for normalized/contributions) are enforced
        # by the producing calculation, not by the container type.
        self.assertEqual(PerGroupValue(1.5, 0.0, 0.0).fap, 1.5)

    def test_for_group_accessor(self) -> None:
        values = PerGroupValue(0.1, 0.2, 0.3)
        self.assertEqual(values.for_group(UserGroup.SAP), 0.2)


class TestParameterResult(unittest.TestCase):
    def test_valid_construction(self) -> None:
        result = ParameterResult(
            name="P1",
            weight=Weight(0.5),
            normalized=PerGroupValue(1.0, 0.8, 0.6),
            contributions=PerGroupValue(0.5, 0.4, 0.3),
        )
        self.assertEqual(result.contributions.for_group(UserGroup.FAP), 0.5)

    def test_name_invariants_apply(self) -> None:
        with self.assertRaises(DomainInvariantError):
            ParameterResult(name="P" * 101, weight=Weight(0.5),
                            normalized=PerGroupValue(0, 0, 0),
                            contributions=PerGroupValue(0, 0, 0))

    def test_rejects_wrong_component_types(self) -> None:
        with self.assertRaises(DomainInvariantError):
            ParameterResult(name="P1", weight=0.5,  # type: ignore[arg-type]
                            normalized=PerGroupValue(0, 0, 0),
                            contributions=PerGroupValue(0, 0, 0))
        with self.assertRaises(DomainInvariantError):
            ParameterResult(name="P1", weight=Weight(0.5),
                            normalized=0.5,  # type: ignore[arg-type]
                            contributions=PerGroupValue(0, 0, 0))


class TestEvaluationResult(unittest.TestCase):
    def test_valid_construction(self) -> None:
        result = make_result()
        self.assertEqual(result.overall, 0.6)
        self.assertEqual(result.group_indices.for_group(UserGroup.SAP), 0.6)

    def test_rejects_negative_nan_infinity_overall(self) -> None:
        for bad in (-1e-12, float("nan"), float("inf"), True, "0.6"):
            with self.assertRaises(DomainInvariantError, msg=repr(bad)):
                make_result(overall=bad)  # type: ignore[arg-type]

    def test_rejects_empty_parameters(self) -> None:
        with self.assertRaises(DomainInvariantError):
            EvaluationResult(
                group_indices=PerGroupValue(0, 0, 0), overall=0.0,
                group_gap=0.0, parameters=()
            )

    def test_rejects_wrong_component_types(self) -> None:
        with self.assertRaises(DomainInvariantError):
            EvaluationResult(group_indices=0.5,  # type: ignore[arg-type]
                             overall=0.5, group_gap=0.0,
                             parameters=(make_result().parameters[0],))

    def test_group_gap_range(self) -> None:
        for ok in (0.0, 0.4, 1.0):
            self.assertEqual(make_result(group_gap=ok).group_gap, ok)
        for bad in (-1e-12, float("nan"), float("inf"), True, "0.4"):
            with self.assertRaises(DomainInvariantError, msg=repr(bad)):
                make_result(group_gap=bad)  # type: ignore[arg-type]


class TestEvaluationOutcome(unittest.TestCase):
    def test_valid_pairing(self) -> None:
        evaluation = make_evaluation(n=2)
        outcome = EvaluationOutcome(evaluation=evaluation, result=make_result(n=2))
        self.assertIs(outcome.evaluation, evaluation)

    def test_rejects_parameter_count_mismatch(self) -> None:
        with self.assertRaises(DomainInvariantError):
            EvaluationOutcome(evaluation=make_evaluation(n=2), result=make_result(n=3))

    def test_rejects_name_order_mismatch(self) -> None:
        swapped = make_result(n=2)
        ordered = EvaluationResult(
            group_indices=swapped.group_indices,
            overall=swapped.overall,
            group_gap=swapped.group_gap,
            parameters=(swapped.parameters[1], swapped.parameters[0]),
        )
        with self.assertRaises(DomainInvariantError):
            EvaluationOutcome(
                evaluation=Evaluation(
                    product="Test product",
                    scale_max=5,
                    parameters=(make_parameter(name="P1", weight=0.5),
                                make_parameter(name="P2", weight=0.5)),
                ),
                result=ordered,
            )

    def test_rejects_wrong_component_types(self) -> None:
        with self.assertRaises(DomainInvariantError):
            EvaluationOutcome(evaluation="nope", result=make_result())  # type: ignore[arg-type]


class TestImmutability(unittest.TestCase):
    def test_value_objects_are_frozen(self) -> None:
        cases = (
            (Score(1), "value", 2.0),
            (Weight(0.5), "value", 0.1),
            (Parameter(name="P", weight=Weight(1.0),
                       scores=GroupScores(Score(0), Score(0), Score(0))), "name", "Q"),
            (make_evaluation(n=1), "scale_max", 10),
            (PerGroupValue(0.1, 0.2, 0.3), "fap", 0.9),
            (make_result(), "overall", 0.1),
        )
        for obj, field, new_value in cases:
            with self.assertRaises(FrozenInstanceError, msg=type(obj).__name__):
                setattr(obj, field, new_value)

    def test_parameters_container_is_a_tuple(self) -> None:
        evaluation = make_evaluation(n=2)
        self.assertIsInstance(evaluation.parameters, tuple)

    def test_result_parameters_container_is_a_tuple(self) -> None:
        self.assertIsInstance(make_result().parameters, tuple)


class TestWeightsSumPredicate(unittest.TestCase):
    def test_exact_and_tolerance_behaviour(self) -> None:
        self.assertTrue(weights_sum_is_valid([1.0]))
        self.assertTrue(weights_sum_is_valid([0.5, 0.5]))
        self.assertTrue(weights_sum_is_valid([1 / 3, 1 / 3, 1 / 3]))  # FP drift <= EPSILON
        self.assertTrue(weights_sum_is_valid([0.9, 0.1]))             # 0.9999999999999999
        self.assertFalse(weights_sum_is_valid([]))
        self.assertFalse(weights_sum_is_valid([0.5, 0.4]))
        self.assertFalse(weights_sum_is_valid([0.5, 0.5, 1.0]))

    def test_custom_target_and_epsilon(self) -> None:
        self.assertTrue(weights_sum_is_valid([1 / 3, 1 / 3, 1 / 3], target=1.0, epsilon=1e-9))
        self.assertFalse(weights_sum_is_valid([0.9999999], target=1.0, epsilon=1e-10))
        self.assertTrue(weights_sum_is_valid([2.0, 3.0], target=5.0))


class TestDomainContractConstants(unittest.TestCase):
    def test_epsilon_matches_the_contract(self) -> None:
        self.assertEqual(EPSILON, 1e-9)

    def test_domain_imports_are_stdlib_only(self) -> None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "universality", "domain.py")
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported <= {"math", "dataclasses", "enum", "typing", "__future__"},
                        msg=f"unexpected imports: {imported}")
        self.assertFalse(imported & {"streamlit", "universality"},
                         msg="domain must not import UI frameworks or sibling modules")

    def test_domain_contains_no_formula_bodies(self) -> None:
        # F1-F4 belong exclusively to universality/calculation.py (implemented 2026-08-25).
        # Docstrings may *name* the outputs (UI_F, s_norm), but no formula
        # expression may appear: no summation, no normalization expression.
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "universality", "domain.py")
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        for fragment in ("Σ", "s_norm(i, G) =", "/ scale_max"):
            self.assertNotIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
