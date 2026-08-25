"""Validation layer (APPLICATION band) — the single authoritative user-input gate.

The binding contract is ``docs/validation-and-security.md``: the rejection
table (V1–V21; **V15 is reserved** for the future export layer), the
validation order (structural → domain), the message themes, and the
error-handling rules.

Guarantees:

- Every violation raises :class:`ValidationRejection` carrying the
  **first** violated rule in validation order (structural → domain);
  validation stops at the first rejection (fail-fast).
- Messages are friendly, specific, and name the offending field. No
  stack traces, no internal exception details — ever.
- User input is **never** silently repaired, trimmed, rescaled, or
  imputed: weight totals are validated (a sum of 0.96 is an error, not
  something to normalize); names are stored exactly as provided; a
  missing value is never converted to zero.
- Domain objects are constructed only on fully validated input. A
  :class:`~universality.domain.DomainInvariantError` after that point
  would be a bug; the safety net maps it to the generic unexpected-error
  message instead of exposing an internal exception.

Validation order (first violated rule wins):

1. structural: input object → product (V16/V17/V18) → scale presence →
   parameter container and count (V12) → per parameter: object shape,
   name presence/type/whitespace/length/control characters (V7/V19/V9/V10),
   weight presence, scores object shape;
2. domain: scale value (V3/V11) → per parameter in order: weight value
   (V3/V13/V1/V2/V5), then scores per group fap → sap → dap
   (V14/V7/V13/V1/V2/V4) → duplicate names (V8) → parameter weight sum
   (V6) → group weights used by Simple Mode (V20/V21 + value rules);
3. construction of the frozen :class:`~universality.domain.Evaluation`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from universality.calculation import SIMPLE_MODE_GROUP_WEIGHTS
from universality.domain import (
    CONTROL_CHARS,
    EPSILON,
    NAME_MAX_LENGTH,
    PARAMETER_MAX,
    PARAMETER_MIN,
    SCALE_MAX,
    SCALE_MIN,
    DomainInvariantError,
    Evaluation,
    GroupScores,
    Parameter,
    Score,
    Weight,
    weights_sum_is_valid,
)

__all__ = ["ValidationRejection", "validate", "validate_group_weights"]

#: Group score keys, in fixed validation order (deterministic; the
#: ``UserGroup`` order FAP → SAP → DAP).
_GROUP_KEYS: Final[tuple[str, str, str]] = ("fap", "sap", "dap")


@dataclass(frozen=True)
class ValidationRejection(Exception):
    """A controlled, user-facing validation outcome (not a fault).

    code:    V-code from ``docs/validation-and-security.md`` (e.g. ``"V4"``);
             ``"V-UNEXPECTED"`` for the internal construction safety net.
    field:   path of the offending field (``""`` for global errors).
    message: friendly, specific text — displayed to the user verbatim.
    """

    code: str
    field: str
    message: str

    def __str__(self) -> str:
        return self.message


def _rej(code: str, field: str, message: str) -> ValidationRejection:
    return ValidationRejection(code=code, field=field, message=message)


def _validated_number(value: object, field: str) -> float:
    """Common numeric rules (V7 → V3 → V13 → V1 → V2). Returns ``float(value)``.

    Booleans are not numbers here (V3); NaN is not real (V1); infinities
    are not finite (V2); anything else that is not ``int``/``float`` is
    rejected (V13). No coercion of strings or other types (no silent
    repair).
    """
    if value is None:
        raise _rej("V7", field, f"Missing value: {field} is required.")
    if isinstance(value, bool):
        raise _rej(
            "V3", field,
            f"Invalid number: expected a number, not a boolean. ({field})",
        )
    if not isinstance(value, (int, float)):
        raise _rej("V13", field, f"Invalid number: expected a real number. ({field})")
    number = float(value)
    if math.isnan(number):
        raise _rej(
            "V1", field,
            f"Invalid number: value must be a real number. ({field})",
        )
    if math.isinf(number):
        raise _rej("V2", field, f"Invalid number: value must be finite. ({field})")
    return number


def _validated_weight(value: object, field: str) -> float:
    """Weight rules: numeric rules (V7/V3/V13/V1/V2) + range 0..1 (V5)."""
    number = _validated_number(value, field)
    if not (0.0 <= number <= 1.0):
        raise _rej("V5", field, f"Invalid weight: {field} must be between 0 and 1.")
    return number


def _validated_score(value: object, field: str, scale_max: int) -> float:
    """Score rules: numeric rules (V7/V3/V13/V1/V2) + range 1..scale_max (V4, A20).

    The user-input minimum is 1 (A20, explicit user instruction); the
    engine/formula domain remains ``[0, scale_max]`` (C3).
    """
    number = _validated_number(value, field)
    if not (1.0 <= number <= float(scale_max)):
        raise _rej(
            "V4", field,
            f"Out-of-range score: {field} must lie between 1 "
            "and the declared scale maximum.",
        )
    return number


def validate_group_weights(group_weights: object) -> tuple[float, float, float]:
    """Validate F3's group weights (C2 + C5). The single validator.

    The application layer applies this to whatever group weights it
    passes to calculation (Simple Mode: the constant
    ``SIMPLE_MODE_GROUP_WEIGHTS``); the calculation engine re-asserts C2
    as a boundary guard. Rules: exactly three numbers (V20), each a
    finite non-boolean real in ``[0, 1]`` (V3/V13/V1/V2/V5), summing to
    1 within EPSILON (V21). Group weights are **not** part of the raw
    user input in Simple Mode (A1, A8; editing gated M5) — this
    validator exists so the rule is enforced and testable at the
    application gate.
    """
    if (
        isinstance(group_weights, (str, bytes))
        or not isinstance(group_weights, (tuple, list))
        or len(group_weights) != 3
    ):
        raise _rej(
            "V20", "group_weights",
            "Invalid weights: group weights must be exactly three numbers. "
            "(group_weights)",
        )
    values = [
        _validated_weight(w, f"group_weights[{i}]")
        for i, w in enumerate(group_weights)
    ]
    if not weights_sum_is_valid(values, target=1.0, epsilon=EPSILON):
        raise _rej(
            "V21", "group_weights",
            "Invalid weights: group weights must sum to 1. (group_weights)",
        )
    return (values[0], values[1], values[2])


def validate(raw: object) -> Evaluation:
    """The single authoritative user-input gate.

    ``raw`` is the plain-primitive input from the UI (a JSON-like
    ``dict`` with keys ``"product"``, ``"scale_max"``, and
    ``"parameters"``; unknown keys are ignored). On success, returns a
    frozen, trusted :class:`~universality.domain.Evaluation`. On any
    violation, raises :class:`ValidationRejection` for the first
    violated rule in validation order (module docstring).
    """
    # ---- Phase 1 — structural (presence, type, size) -------------------
    if not isinstance(raw, dict):
        raise _rej("V19", "input", "Invalid input: input has an unexpected format.")

    # product name (V16/V17/V18; A21 — same name rules as parameters, A18)
    product = raw.get("product")
    if product is None:
        raise _rej("V16", "product", "Missing value: product name is required.")
    if not isinstance(product, str):
        raise _rej("V19", "product", "Invalid input: product has an unexpected format.")
    if not product.strip():
        raise _rej("V16", "product", "Missing value: product name is required.")
    if len(product) > NAME_MAX_LENGTH:
        raise _rej(
            "V17", "product",
            f"Input too long: product name must be at most {NAME_MAX_LENGTH} "
            "characters.",
        )
    if any(char in CONTROL_CHARS for char in product):
        raise _rej(
            "V18", "product",
            "Invalid characters: product name must not contain control characters.",
        )

    # scale_max presence (value is checked in the domain phase: V3/V11)
    if raw.get("scale_max") is None:
        raise _rej("V7", "scale_max", "Missing value: scale_max is required.")

    # parameters presence, container shape, count (V7/V19/V12)
    parameters_raw = raw.get("parameters")
    if parameters_raw is None:
        raise _rej("V7", "parameters", "Missing value: parameters is required.")
    if not isinstance(parameters_raw, list):
        raise _rej("V19", "parameters", "Invalid input: parameters has an unexpected format.")
    if not (PARAMETER_MIN <= len(parameters_raw) <= PARAMETER_MAX):
        raise _rej(
            "V12", "parameters",
            "Invalid evaluation: between 1 and 100 parameters are required.",
        )

    names: list[str] = []
    for i, parameter_raw in enumerate(parameters_raw):
        path = f"parameters[{i}]"
        if not isinstance(parameter_raw, dict):
            raise _rej(
                "V19", path,
                f"Invalid input: {path} has an unexpected format.",
            )

        # name: presence → type → whitespace → length → control characters
        name = parameter_raw.get("name")
        name_path = f"{path}.name"
        if name is None:
            raise _rej("V7", name_path, f"Missing value: {name_path} is required.")
        if not isinstance(name, str):
            raise _rej(
                "V19", name_path,
                f"Invalid input: {name_path} has an unexpected format.",
            )
        if not name.strip():
            raise _rej("V7", name_path, f"Missing value: {name_path} is required.")
        if len(name) > NAME_MAX_LENGTH:
            raise _rej(
                "V9", name_path,
                f"Input too long: {name_path} must be at most {NAME_MAX_LENGTH} "
                "characters.",
            )
        if any(char in CONTROL_CHARS for char in name):
            raise _rej(
                "V10", name_path,
                f"Invalid characters: {name_path} must not contain control "
                "characters.",
            )
        names.append(name)

        # weight presence (value is checked in the domain phase)
        weight_path = f"{path}.weight"
        if parameter_raw.get("weight") is None:
            raise _rej("V7", weight_path, f"Missing value: {weight_path} is required.")

        # scores object presence and shape (group keys in the domain phase)
        scores_path = f"{path}.scores"
        scores_raw = parameter_raw.get("scores")
        if scores_raw is None:
            raise _rej("V7", scores_path, f"Missing value: {scores_path} is required.")
        if not isinstance(scores_raw, dict):
            raise _rej(
                "V19", scores_path,
                f"Invalid input: {scores_path} has an unexpected format.",
            )

    # ---- Phase 2 — domain (ranges, sums, duplicates, coverage) ---------
    scale_raw = raw["scale_max"]
    if isinstance(scale_raw, bool):
        raise _rej(
            "V3", "scale_max",
            "Invalid number: expected a number, not a boolean. (scale_max)",
        )
    if not isinstance(scale_raw, int) or not (SCALE_MIN <= scale_raw <= SCALE_MAX):
        raise _rej(
            "V11", "scale_max",
            f"Invalid scale: the scale maximum must be a whole number "
            f"between {SCALE_MIN} and {SCALE_MAX}.",
        )
    scale_max: int = scale_raw

    weights: list[float] = []
    score_sets: list[tuple[float, float, float]] = []
    for i, parameter_raw in enumerate(parameters_raw):
        path = f"parameters[{i}]"

        weight = _validated_weight(parameter_raw["weight"], f"{path}.weight")
        weights.append(weight)

        scores_raw = parameter_raw["scores"]
        triple: list[float] = []
        for key in _GROUP_KEYS:
            score_field = f"{path}.scores.{key}"
            if scores_raw.get(key) is None:
                raise _rej(
                    "V14", score_field,
                    "Missing value: every parameter needs a score for each of "
                    f"the FAP, SAP, and DAP groups. ({score_field})",
                )
            triple.append(_validated_score(scores_raw[key], score_field, scale_max))
        score_sets.append((triple[0], triple[1], triple[2]))

    # duplicate parameter names (case-insensitive after trimming, A10/A18)
    seen: set[str] = set()
    for i, name in enumerate(names):
        key = name.strip().casefold()
        if key in seen:
            raise _rej(
                "V8", f"parameters[{i}].name",
                f"Duplicate parameter name: {name!r} is already used. "
                f"(parameters[{i}].name)",
            )
        seen.add(key)

    # parameter weights must sum to 1 within EPSILON (C1) — validated,
    # never rescaled or normalized.
    if not weights_sum_is_valid(weights, target=1.0, epsilon=EPSILON):
        raise _rej(
            "V6", "parameters",
            "Invalid weights: parameter weights must sum to 1. (parameters)",
        )

    # group weights used by Simple Mode: the constant (A1). Validated
    # here as a defensive application-gate check; the engine re-asserts
    # C2 as a boundary guard.
    validate_group_weights(SIMPLE_MODE_GROUP_WEIGHTS)

    # ---- Phase 3 — construction (validated input only) ------------------
    try:
        return Evaluation(
            product=product,
            scale_max=scale_max,
            parameters=tuple(
                Parameter(
                    name=names[i],
                    weight=Weight(weights[i]),
                    scores=GroupScores(Score(score_sets[i][0]), Score(score_sets[i][1]), Score(score_sets[i][2])),
                )
                for i in range(len(names))
            ),
        )
    except DomainInvariantError:
        # Should be unreachable: the gate precedes construction. If a bug
        # ever lets a domain invariant fire here, map it to the generic
        # unexpected-error message — never expose an internal exception.
        raise _rej(
            "V-UNEXPECTED", "",
            "Something went wrong. Please try again.",
        ) from None
