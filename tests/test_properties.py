"""Property-style invariant tests for the full pipeline (seeded, stdlib only).

No external property-testing framework is installed (the project is
standard-library only); each property is therefore exercised over a
fixed-seed pseudo-random sample of *valid* evaluations. The fixed seed
makes every failure reproducible: the ``subTest`` index identifies the
sample, and a second generator with the same seed reproduces it.

Invariants under test (QA audit 2026-08-26; constraints C1–C5 in
``docs/FORMULA_SPECIFICATION.md``):

- for every valid evaluation: ``0 <= UI_F, UI_S, UI_D, UI, group_gap``,
  with the documented floating-point upper bounds under the C1/C2
  tolerance (indices ``<= 1 + EPSILON``, overall ``<= 1 + 2*EPSILON``,
  gap ``<= 1 + EPSILON``);
- parameter weights sum to 1 (C1, within EPSILON);
- group weights sum to 1 (C2, within EPSILON);
- changing an individual satisfaction score never modifies another
  parameter's result (bit-identical for all untouched parameters);
- changing a parameter weight affects only the expected weighted
  calculation (the touched contributions, group indices, overall, gap —
  never another parameter's result);
- monotonicity: raising one score never decreases its group index or the
  overall index, and never changes the untouched group indices;
- determinism: identical inputs give bit-identical results and the
  generator itself is reproducible.
"""

from __future__ import annotations

import copy
import random
import unittest

from universality import (
    EPSILON,
    SIMPLE_MODE_GROUP_WEIGHTS,
    UserGroup,
    compute,
    validate,
    weights_sum_is_valid,
)
from universality.domain import SCALE_MAX, SCALE_MIN

SEED = 20260826
SAMPLES = 200

_KEY_TO_GROUP = {"fap": UserGroup.FAP, "sap": UserGroup.SAP, "dap": UserGroup.DAP}


def pipeline(raw: dict):
    """raw -> validate -> compute: the exact path ``services.evaluate``
    will use. Raises ``ValidationRejection`` on any violation."""
    return compute(validate(raw))


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


class Generator:
    """Seeded generator of *valid* raw evaluations (test-only helper).

    Weights are generated as normalized uniform randoms, so each weight
    lies in ``(0, 1]`` and the C1 sum holds within floating-point error
    (far below EPSILON) — a precondition asserted, not assumed.
    """

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self._draw = 0

    def raw(self) -> dict:
        rng = self._rng
        self._draw += 1
        scale = rng.randint(SCALE_MIN, SCALE_MAX)
        n = rng.randint(1, 12)
        raw_w = [max(rng.random(), 1e-9) for _ in range(n)]
        total = sum(raw_w)
        weights = [w / total for w in raw_w]
        if not weights_sum_is_valid(weights):
            raise AssertionError("generator produced weights violating C1")
        parameters = [
            {
                "name": f"P{i + 1}",
                "weight": weights[i],
                "scores": self._scores(scale),
            }
            for i in range(n)
        ]
        return {
            "product": f"Product n{n} s{scale} d{self._draw}",
            "scale_max": scale,
            "parameters": parameters,
        }

    def _scores(self, scale: int) -> dict:
        def one() -> int | float:
            if self._rng.random() < 0.5:
                return self._rng.randint(1, scale)
            return round(self._rng.uniform(1.0, float(scale)), 6)
        return {"fap": one(), "sap": one(), "dap": one()}


class TestRangeInvariants(unittest.TestCase):
    """For every valid evaluation the documented output bounds hold."""

    def test_all_outputs_within_documented_bounds(self) -> None:
        gen = Generator(SEED)
        for i in range(SAMPLES):
            with self.subTest(i=i):
                result = pipeline(gen.raw())
                for value in (
                    result.group_indices.fap,
                    result.group_indices.sap,
                    result.group_indices.dap,
                ):
                    self.assertGreaterEqual(value, 0.0)
                    self.assertLessEqual(value, 1.0 + EPSILON)
                self.assertGreaterEqual(result.overall, 0.0)
                self.assertLessEqual(result.overall, 1.0 + 2 * EPSILON)
                self.assertGreaterEqual(result.group_gap, 0.0)
                self.assertLessEqual(result.group_gap, 1.0 + EPSILON)
                for p in result.parameters:
                    for value in (p.normalized.fap, p.normalized.sap, p.normalized.dap):
                        self.assertGreaterEqual(value, 0.0)
                        self.assertLessEqual(value, 1.0)
                    for value in (
                        p.contributions.fap, p.contributions.sap, p.contributions.dap,
                    ):
                        self.assertGreaterEqual(value, 0.0)
                        self.assertLessEqual(value, 1.0)


class TestWeightSumInvariants(unittest.TestCase):
    """C1 and C2 hold for every valid evaluation."""

    def test_parameter_weights_satisfy_c1(self) -> None:
        gen = Generator(SEED)
        for i in range(SAMPLES):
            raw = gen.raw()
            with self.subTest(i=i):
                self.assertTrue(
                    weights_sum_is_valid([p["weight"] for p in raw["parameters"]])
                )
                result = pipeline(raw)
                # The result carries exactly the input weights (bit-exact).
                self.assertEqual(
                    [p.weight.value for p in result.parameters],
                    [p["weight"] for p in raw["parameters"]],
                )

    def test_group_weights_satisfy_c2(self) -> None:
        self.assertTrue(weights_sum_is_valid(list(SIMPLE_MODE_GROUP_WEIGHTS)))


class TestScoreIndependence(unittest.TestCase):
    """Changing one parameter's score must not modify another parameter."""

    def test_other_parameters_bit_identical_after_score_change(self) -> None:
        gen = Generator(SEED)
        executed = 0
        for i in range(SAMPLES):
            raw = gen.raw()
            if len(raw["parameters"]) < 2:
                continue
            executed += 1
            with self.subTest(i=i):
                old = raw["parameters"][0]["scores"]["fap"]
                new = 1 if old != 1 else 2  # valid, and different
                raw2 = copy.deepcopy(raw)
                raw2["parameters"][0]["scores"]["fap"] = new
                a, b = pipeline(raw), pipeline(raw2)
                for j in range(1, len(a.parameters)):
                    self.assertEqual(a.parameters[j].name, b.parameters[j].name)
                    self.assertEqual(a.parameters[j].weight, b.parameters[j].weight)
                    # Bit-identical: dataclass == compares fields with ==.
                    self.assertEqual(
                        a.parameters[j].normalized, b.parameters[j].normalized
                    )
                    self.assertEqual(
                        a.parameters[j].contributions, b.parameters[j].contributions
                    )
        self.assertGreaterEqual(executed, 100)


class TestWeightLocality(unittest.TestCase):
    """Changing a weight affects only the expected weighted calculation."""

    def test_only_touched_terms_change(self) -> None:
        gen = Generator(SEED)
        rng = random.Random(SEED ^ 0x5EED)
        executed = 0
        for i in range(SAMPLES):
            raw = gen.raw()
            if len(raw["parameters"]) < 3:
                continue
            executed += 1
            with self.subTest(i=i):
                w0 = raw["parameters"][0]["weight"]
                w1 = raw["parameters"][1]["weight"]
                new_w0 = w0 * rng.random()          # in [0, w0]
                new_w1 = w1 + (w0 - new_w0)         # in [0, 1] (w1 + w0 <= 1)
                self.assertGreaterEqual(new_w0, 0.0)
                self.assertLessEqual(new_w1, 1.0)
                raw2 = copy.deepcopy(raw)
                raw2["parameters"][0]["weight"] = new_w0
                raw2["parameters"][1]["weight"] = new_w1
                a, b = pipeline(raw), pipeline(raw2)

                # Untouched parameters: bit-identical.
                for j in range(2, len(a.parameters)):
                    self.assertEqual(
                        a.parameters[j].normalized, b.parameters[j].normalized
                    )
                    self.assertEqual(
                        a.parameters[j].contributions, b.parameters[j].contributions
                    )

                # Touched parameters: contributions are exactly
                # new_weight * normalized (same operands, same order).
                for j, new_w in ((0, new_w0), (1, new_w1)):
                    p = b.parameters[j]
                    self.assertEqual(p.contributions.fap, new_w * p.normalized.fap)
                    self.assertEqual(p.contributions.sap, new_w * p.normalized.sap)
                    self.assertEqual(p.contributions.dap, new_w * p.normalized.dap)

                # Structural identity: group index == left-to-right sum of
                # the stored contributions (documented engine property).
                for key in ("fap", "sap", "dap"):
                    total = 0.0
                    for p in b.parameters:
                        total += getattr(p.contributions, key)
                    self.assertEqual(getattr(b.group_indices, key), total)

                # F3 in documented order: overall == W_F*f + W_S*s + W_D*d.
                w_f, w_s, w_d = SIMPLE_MODE_GROUP_WEIGHTS
                self.assertEqual(
                    b.overall,
                    w_f * b.group_indices.fap
                    + w_s * b.group_indices.sap
                    + w_d * b.group_indices.dap,
                )
        self.assertGreaterEqual(executed, 60)


class TestMonotonicity(unittest.TestCase):
    """Raising one score never decreases its group index or the overall."""

    def test_raising_a_score_is_monotone(self) -> None:
        gen = Generator(SEED)
        executed = 0
        for i in range(SAMPLES):
            raw = gen.raw()
            with self.subTest(i=i):
                scale = raw["scale_max"]
                old = raw["parameters"][0]["scores"]["sap"]
                if old >= scale:
                    continue
                executed += 1
                new = old + 1.0 if old + 1.0 <= scale else float(scale)
                self.assertGreater(new, old)
                raw2 = copy.deepcopy(raw)
                raw2["parameters"][0]["scores"]["sap"] = new
                a, b = pipeline(raw), pipeline(raw2)
                # IEEE-754 addition is monotone in each operand: with the
                # same summation order the raised summand raises the sum.
                self.assertGreaterEqual(b.group_indices.sap, a.group_indices.sap)
                self.assertGreaterEqual(b.overall, a.overall)
                # Untouched group indices: bit-identical.
                self.assertEqual(a.group_indices.fap, b.group_indices.fap)
                self.assertEqual(a.group_indices.dap, b.group_indices.dap)
        self.assertGreaterEqual(executed, SAMPLES // 2)


class TestRepeatability(unittest.TestCase):
    """Determinism: identical inputs, bit-identical outputs, reproducible
    generator."""

    def test_identical_inputs_give_bit_identical_results(self) -> None:
        gen = Generator(SEED)
        for i in range(50):
            raw = gen.raw()
            with self.subTest(i=i):
                self.assertEqual(snapshot(pipeline(raw)), snapshot(pipeline(raw)))

    def test_generator_is_reproducible(self) -> None:
        first, second = Generator(SEED), Generator(SEED)
        raws_a = [first.raw() for _ in range(20)]
        raws_b = [second.raw() for _ in range(20)]
        self.assertEqual(raws_a, raws_b)
        for i, raw in enumerate(raws_a):
            with self.subTest(i=i):
                self.assertEqual(
                    snapshot(pipeline(raw)),
                    snapshot(pipeline(copy.deepcopy(raw))),
                )


class TestShapeAndStorage(unittest.TestCase):
    """The pipeline preserves shape, order, and values exactly."""

    def test_result_shape_matches_input(self) -> None:
        gen = Generator(SEED)
        for i in range(SAMPLES):
            raw = gen.raw()
            with self.subTest(i=i):
                evaluation = validate(raw)
                result = compute(evaluation)
                self.assertEqual(len(result.parameters), len(raw["parameters"]))
                self.assertEqual(
                    [p.name for p in result.parameters],
                    [p["name"] for p in raw["parameters"]],
                )
                self.assertEqual(evaluation.product, raw["product"])
                self.assertEqual(evaluation.scale_max, raw["scale_max"])
                # Scores are stored as the same real number (bit-exact
                # float: int -> float is exact, float -> float identity).
                for input_param, param in zip(raw["parameters"], evaluation.parameters):
                    for key, group in _KEY_TO_GROUP.items():
                        self.assertEqual(
                            param.scores.for_group(group).value,
                            float(input_param["scores"][key]),
                        )


if __name__ == "__main__":
    unittest.main()
