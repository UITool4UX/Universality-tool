"""Calculation engine of the Universality Index Tool.

CALCULATION band (``docs/architecture.md``): the **sole implementation**
of the formulas F1–F4. The formula statements themselves live in
``docs/FORMULA_SPECIFICATION.md`` (this module references them by ID);
the engine specification lives in ``docs/CALCULATION_ENGINE.md``.

Guarantees (test-enforced, see ``tests/test_calculation.py``):

- pure functions: no I/O, no global state, no time, no randomness;
- deterministic: fixed summation order (parameter input order,
  left-to-right IEEE-754 addition; group order F → S → D);
- full IEEE-754 double precision — **no rounding** of intermediate
  values (presentation rounding is A6, owned by the deferred
  APPLICATION layer);
- **no clamping, no imputation, no inference**: violations of the
  engine domain raise ``DomainInvariantError``;
- imports only ``universality.domain`` plus the standard library
  (no pandas/numpy — documented in the engine spec);
- the structural identity ``UI_G == Σᵢ contribution(i, G)`` holds
  **bit-exactly** (group indices are the left-to-right sum of the
  stored per-parameter F2 summands).
"""

from __future__ import annotations

import math
from typing import Final, Sequence

from universality.domain import (
    DomainInvariantError,
    Evaluation,
    EvaluationResult,
    Parameter,
    ParameterResult,
    PerGroupValue,
    UserGroup,
    weights_sum_is_valid,
)

__all__ = [
    "SIMPLE_MODE_GROUP_WEIGHTS",
    "normalize_score",
    "parameter_contributions",
    "group_index",
    "overall_index",
    "group_gap",
    "compute",
]

#: Simple Mode group weights (A1): W_F = W_S = W_D = 1/3. Sole location.
#: The UI displays these via the public API re-export — never hardcodes them.
SIMPLE_MODE_GROUP_WEIGHTS: Final[tuple[float, float, float]] = (
    1.0 / 3.0,
    1.0 / 3.0,
    1.0 / 3.0,
)

#: Fixed group order (F → S → D). Determinism: never iterate a set/dict.
_GROUPS: Final[tuple[UserGroup, UserGroup, UserGroup]] = (
    UserGroup.FAP,
    UserGroup.SAP,
    UserGroup.DAP,
)


# --------------------------------------------------------------------------
# Domain guards (layer boundaries — not formulas)
# --------------------------------------------------------------------------

def _check_f1_domain(score: object, scale_max: object, context: str) -> float:
    """F1 project-domain guard: ``2 <= scale_max <= 100`` (int, not bool)
    and ``0 <= score <= scale_max`` with score finite (not bool).

    This is a boundary assertion for the engine's public entry points —
    the formula F1 itself has exactly one implementation
    (:func:`normalize_score`). Invalid values raise; they are never
    clamped or repaired.
    """
    if isinstance(scale_max, bool) or not isinstance(scale_max, int):
        raise DomainInvariantError(
            f"{context}: scale_max must be an int, got {type(scale_max).__name__}"
        )
    if not 2 <= scale_max <= 100:
        raise DomainInvariantError(
            f"{context}: scale_max must be within [2, 100], got {scale_max}"
        )
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise DomainInvariantError(
            f"{context}: score must be a real number, got {type(score).__name__}"
        )
    value = float(score)
    if not math.isfinite(value):
        raise DomainInvariantError(f"{context}: score must be finite, got {score!r}")
    if not 0.0 <= value <= float(scale_max):
        raise DomainInvariantError(
            f"{context}: score must be within [0, {scale_max}], got {score!r}"
        )
    return value


def _validated_group_weights(group_weights: object) -> tuple[float, float, float]:
    """C2 guard (engine surface): exactly three finite, non-negative values
    summing to 1 within EPSILON, checked with the **single** predicate
    ``domain.weights_sum_is_valid``. Raises; never clamps.
    """
    if not isinstance(group_weights, (tuple, list)) or len(group_weights) != 3:
        raise DomainInvariantError(
            "group weights must be a tuple/list of exactly three values (W_F, W_S, W_D)"
        )
    values: list[float] = []
    for position, raw in enumerate(group_weights):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise DomainInvariantError(
                f"group weight[{position}] must be a real number, got {type(raw).__name__}"
            )
        value = float(raw)
        if not math.isfinite(value):
            raise DomainInvariantError(f"group weight[{position}] must be finite")
        if value < 0.0:
            raise DomainInvariantError(f"group weight[{position}] must be >= 0")
        values.append(value)
    if not weights_sum_is_valid(values):
        raise DomainInvariantError(
            "group weights must sum to 1 within EPSILON (C2)"
        )
    return (values[0], values[1], values[2])


# --------------------------------------------------------------------------
# Formulas (F1–F4 — the only implementations; see FORMULA_SPECIFICATION.md)
# --------------------------------------------------------------------------

def normalize_score(score: float, scale_max: int) -> float:
    """**F1** — satisfaction normalization: ``s_norm = s / scale_max``.

    Project domain: ``2 <= scale_max <= 100`` (int), finite
    ``0 <= score <= scale_max``. Violations raise
    ``DomainInvariantError`` — never clamped, never repaired.
    """
    value = _check_f1_domain(score, scale_max, "normalize_score")
    return value / scale_max


def parameter_contributions(parameter: Parameter, scale_max: int) -> PerGroupValue:
    """F2 per-parameter summands: ``w(i) · s_norm(i, G)`` for each group.

    The same values stored in ``ParameterResult.contributions``.
    """
    if not isinstance(parameter, Parameter):
        raise DomainInvariantError(
            f"parameter_contributions: parameter must be a Parameter, "
            f"got {type(parameter).__name__}"
        )
    _check_f1_domain(parameter.scores.fap.value, scale_max, "parameter_contributions")
    _check_f1_domain(parameter.scores.sap.value, scale_max, "parameter_contributions")
    _check_f1_domain(parameter.scores.dap.value, scale_max, "parameter_contributions")
    weight = parameter.weight.value
    return PerGroupValue(
        fap=weight * normalize_score(parameter.scores.fap.value, scale_max),
        sap=weight * normalize_score(parameter.scores.sap.value, scale_max),
        dap=weight * normalize_score(parameter.scores.dap.value, scale_max),
    )


def _summarize(
    evaluation: Evaluation,
) -> tuple[PerGroupValue, tuple[ParameterResult, ...]]:
    """Single F1+F2 pass over a validated evaluation.

    Returns (group indices, per-parameter results). The group index of
    each group is the left-to-right sum of that group's stored
    per-parameter summands — which is exactly F2's Σ, computed once.
    """
    parameter_results: list[ParameterResult] = []
    sum_f = 0.0
    sum_s = 0.0
    sum_d = 0.0
    for parameter in evaluation.parameters:
        normalized = PerGroupValue(
            fap=normalize_score(parameter.scores.fap.value, evaluation.scale_max),
            sap=normalize_score(parameter.scores.sap.value, evaluation.scale_max),
            dap=normalize_score(parameter.scores.dap.value, evaluation.scale_max),
        )
        contributions = PerGroupValue(
            fap=parameter.weight.value * normalized.fap,
            sap=parameter.weight.value * normalized.sap,
            dap=parameter.weight.value * normalized.dap,
        )
        sum_f += contributions.fap
        sum_s += contributions.sap
        sum_d += contributions.dap
        parameter_results.append(
            ParameterResult(
                name=parameter.name,
                weight=parameter.weight,
                normalized=normalized,
                contributions=contributions,
            )
        )
    return PerGroupValue(fap=sum_f, sap=sum_s, dap=sum_d), tuple(parameter_results)


def group_index(evaluation: Evaluation, group: UserGroup) -> float:
    """**F2** — group index ``UI_G = Σᵢ w(i) · s_norm(i, G)`` for one group.

    Deterministic: parameter input order, left-to-right addition.
    Bit-identical to the sum of the per-parameter contributions.
    """
    if not isinstance(evaluation, Evaluation):
        raise DomainInvariantError(
            f"group_index: evaluation must be an Evaluation, got {type(evaluation).__name__}"
        )
    indices, _ = _summarize(evaluation)
    return indices.for_group(group)


def overall_index(
    group_indices: PerGroupValue,
    group_weights: Sequence[float] = SIMPLE_MODE_GROUP_WEIGHTS,
) -> float:
    """**F3** — overall index ``UI = W_F·UI_F + W_S·UI_S + W_D·UI_D``.

    ``group_weights`` are F3's formula inputs (W_F, W_S, W_D); the
    Simple Mode default is ``SIMPLE_MODE_GROUP_WEIGHTS`` (A1). C2 is
    enforced (three finite, non-negative values summing to 1 within
    EPSILON); violations raise — never clamped.
    """
    if not isinstance(group_indices, PerGroupValue):
        raise DomainInvariantError(
            f"overall_index: group_indices must be a PerGroupValue, "
            f"got {type(group_indices).__name__}"
        )
    w_f, w_s, w_d = _validated_group_weights(group_weights)
    return w_f * group_indices.fap + w_s * group_indices.sap + w_d * group_indices.dap


def group_gap(group_indices: PerGroupValue) -> float:
    """**F4** — user-group gap: ``max(UI_F, UI_S, UI_D) − min(UI_F, UI_S, UI_D)``.

    Registered 2026-08-25 (explicit user instruction; interpretation
    recorded as A19). A derived diagnostic built solely from F2 outputs
    — no new normalization or weighting. Exact-arithmetic range [0, 1];
    floating point [0, 1 + EPSILON] under the C1 tolerance.
    """
    if not isinstance(group_indices, PerGroupValue):
        raise DomainInvariantError(
            f"group_gap: group_indices must be a PerGroupValue, "
            f"got {type(group_indices).__name__}"
        )
    values = (group_indices.fap, group_indices.sap, group_indices.dap)
    return max(values) - min(values)


def compute(
    evaluation: Evaluation,
    group_weights: Sequence[float] = SIMPLE_MODE_GROUP_WEIGHTS,
) -> EvaluationResult:
    """Top-level computation: F1 → F2 → F3 (+ F4) over a validated
    :class:`Evaluation`.

    Pure, deterministic, full precision. Returns the complete
    :class:`EvaluationResult` (group indices, overall, per-parameter
    normalized scores and contributions, group gap).

    ``group_weights`` are F3's formula inputs; the Simple Mode default
    is ``SIMPLE_MODE_GROUP_WEIGHTS`` (A1). User-editable group weights
    (M5) remain an application-level decision — this parameter is the
    formula being implemented, not a new mode.
    """
    if not isinstance(evaluation, Evaluation):
        raise DomainInvariantError(
            f"compute: evaluation must be an Evaluation, got {type(evaluation).__name__}"
        )
    _validated_group_weights(group_weights)
    group_indices, parameter_results = _summarize(evaluation)
    return EvaluationResult(
        group_indices=group_indices,
        overall=overall_index(group_indices, group_weights),
        parameters=parameter_results,
        group_gap=group_gap(group_indices),
    )
