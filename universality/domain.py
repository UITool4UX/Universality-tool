"""Domain model of the Universality Index Tool.

DOMAIN band (``docs/architecture.md``): frozen value objects plus the
domain's own constraint machinery. Field-level specification (type,
meaning, valid range, required/optional for every field):
``docs/DOMAIN_MODEL.md``.

Rules this module obeys:

- imports nothing project-internal (standard library only);
- contains **no research formulas** — F1–F4 live exclusively in
  ``universality/calculation.py``. This module enforces
  constraints and navigates shape; it performs no calculation;
- enforces *type invariants*: an object of a given type is always inside
  that type's domain (violations raise :class:`DomainInvariantError`).
  User-input rejection with friendly V-coded messages is the single
  responsibility of ``universality/validation.py`` (implemented
  2026-08-25) — see "Invariant split" in ``docs/DOMAIN_MODEL.md``;
- no global mutable state, no I/O, no time, no randomness.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Final, Sequence

__all__ = [
    "EPSILON",
    "SCALE_MIN",
    "SCALE_MAX",
    "NAME_MIN_LENGTH",
    "NAME_MAX_LENGTH",
    "PARAMETER_MIN",
    "PARAMETER_MAX",
    "CONTROL_CHARS",
    "DomainInvariantError",
    "UserGroup",
    "KanoCategory",
    "Score",
    "Weight",
    "GroupScores",
    "Parameter",
    "Evaluation",
    "PerGroupValue",
    "ParameterResult",
    "EvaluationResult",
    "EvaluationOutcome",
    "weights_sum_is_valid",
]

# --------------------------------------------------------------------------
# Contract constants (single locations)
# --------------------------------------------------------------------------

#: Floating-point tolerance for the sum constraints C1/C2
#: (``docs/FORMULA_SPECIFICATION.md``; assumption A5).
#: Lives in the domain because the domain enforces the C1 invariant;
#: ``validation.py`` imports it from here.
EPSILON: Final[float] = 1e-9

# Evaluation-level limits (assumptions A3, A10, A11).
SCALE_MIN: Final[int] = 2
SCALE_MAX: Final[int] = 100
NAME_MIN_LENGTH: Final[int] = 1
NAME_MAX_LENGTH: Final[int] = 100
PARAMETER_MIN: Final[int] = 1
PARAMETER_MAX: Final[int] = 100

#: Control characters rejected in parameter names (assumption A10,
#: exact set fixed by the domain implementation, 2026-08-25):
#: C0 controls U+0000–U+001F, DEL U+007F, C1 controls U+0080–U+009F.
CONTROL_CHARS: Final[frozenset[str]] = frozenset(
    chr(code) for code in [*range(0x00, 0x20), 0x7F, *range(0x80, 0xA0)]
)


class DomainInvariantError(ValueError):
    """A domain type invariant was violated (explicit-constraint contract).

    In production this can only be raised by a bug: the validation gate
    (deferred) rejects invalid user input *before* domain objects are
    constructed. Subclasses ``ValueError`` so callers may catch either.
    """


# --------------------------------------------------------------------------
# Vocabularies
# --------------------------------------------------------------------------

class UserGroup(Enum):
    """The three ability/needs user groups (``docs/RESEARCH_BASIS.md``, R2, R3).

    FAP = Fully Abled People, SAP = Specially Abled People,
    DAP = Differently Abled People.
    """

    FAP = "FAP"
    SAP = "SAP"
    DAP = "DAP"

    @property
    def label(self) -> str:
        """Display name (research label, R3). Data, not computation."""
        return _USER_GROUP_LABELS[self]


_USER_GROUP_LABELS: Final[dict[UserGroup, str]] = {
    UserGroup.FAP: "Fully Abled People",
    UserGroup.SAP: "Specially Abled People",
    UserGroup.DAP: "Differently Abled People",
}


class KanoCategory(Enum):
    """Kano-model attribute classes (``docs/REFERENCES.md``, K1 / [M1]).

    STATUS — inert domain vocabulary only:

    - the MVP formulas F1–F4 do not reference this type;
    - no classification logic exists, and none may be added without the
      M2 gate (``docs/LIMITATIONS.md``);
    - this type is intentionally **not attached to any other model**; an
      attachment point (and that field's required/optional status) will
      be defined by the M2 contract change, not guessed here.

    Inclusion as a vocabulary type was explicitly approved on 2026-08-25
    (user instruction; scope note recorded in ``docs/LIMITATIONS.md`` M2).
    """

    MUST_BE = "must_be"
    ONE_DIMENSIONAL = "one_dimensional"
    ATTRACTIVE = "attractive"
    INDIFFERENT = "indifferent"
    REVERSE = "reverse"


# --------------------------------------------------------------------------
# Invariant helpers (single implementations)
# --------------------------------------------------------------------------

def _require_real_number(value: object, field: str) -> float:
    """Invariant: a numeric field is a real number.

    Accepts ``int`` or ``float`` (stored as ``float`` — the same real
    number; no other normalization is performed). Rejects booleans
    (V3: booleans are not numbers here), NaN, and infinities (V1/V2).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DomainInvariantError(
            f"{field} must be a real number, got {type(value).__name__}"
        )
    number = float(value)
    if not math.isfinite(number):
        raise DomainInvariantError(f"{field} must be finite, got {value!r}")
    return number


def _check_name(name: object, context: str, field: str = "name") -> str:
    """Invariant: name validity (parameter names and the product name;
    assumptions A10 / A18, A21).

    1–100 characters, no control characters (exact set above), at least
    one non-whitespace character. The name is returned **as provided** —
    never trimmed or modified (no silent change of research data).
    """
    if not isinstance(name, str):
        raise DomainInvariantError(f"{context}.{field} must be a str")
    if not NAME_MIN_LENGTH <= len(name) <= NAME_MAX_LENGTH:
        raise DomainInvariantError(
            f"{context}.{field} must be 1..{NAME_MAX_LENGTH} characters, "
            f"got {len(name)}"
        )
    for char in name:
        if char in CONTROL_CHARS:
            raise DomainInvariantError(
                f"{context}.{field} must not contain control characters"
            )
    if not name.strip():
        raise DomainInvariantError(
            f"{context}.{field} must contain at least one non-whitespace character"
        )
    return name


def weights_sum_is_valid(
    values: Sequence[int | float],
    target: float = 1.0,
    epsilon: float = EPSILON,
) -> bool:
    """The single implementation of the sum-constraint check (C1/C2):
    ``abs(sum(values) - target) <= epsilon``.

    Used by :class:`Evaluation` (C1) and, when implemented, by
    ``validation.py`` and for group weights (C2). One authoritative
    predicate — constraint checks exist in exactly one place.
    """
    return abs(sum(values) - target) <= epsilon


# --------------------------------------------------------------------------
# Value objects — evaluation input
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Score:
    """Observed satisfaction score for one (parameter, group) pair.

    value: real number. Type domain: finite and >= 0. The upper bound is
    context-dependent — ``0 <= value <= scale_max`` (C3) — and is enforced
    by :class:`Evaluation`, the only type that knows the scale.
    """

    value: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", _require_real_number(self.value, "Score.value")
        )
        if self.value < 0:
            raise DomainInvariantError("Score.value must be >= 0")


@dataclass(frozen=True)
class Weight:
    """Relative importance of one parameter (C5 domain part).

    value: real number in [0, 1]. Zero is allowed (the parameter
    contributes nothing; assumption A9). The sum-of-weights constraint
    C1 is Evaluation-level (it needs all parameters), not here.
    """

    value: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", _require_real_number(self.value, "Weight.value")
        )
        if not 0.0 <= self.value <= 1.0:
            raise DomainInvariantError("Weight.value must be within [0, 1]")


@dataclass(frozen=True)
class GroupScores:
    """One parameter's satisfaction scores for all three user groups.

    Completeness (A15) is guaranteed by construction: all three fields
    are required, so no partial state is representable.
    """

    fap: Score
    sap: Score
    dap: Score

    def for_group(self, group: UserGroup) -> Score:
        """Shape-navigation accessor (not a calculation)."""
        match group:
            case UserGroup.FAP:
                return self.fap
            case UserGroup.SAP:
                return self.sap
            case UserGroup.DAP:
                return self.dap
            case _:
                raise DomainInvariantError(f"unknown user group: {group!r}")


@dataclass(frozen=True)
class Parameter:
    """One evaluated product parameter (user value).

    name:   1–100 characters, no control characters, >= 1 non-whitespace
            character; stored as provided (never modified). Uniqueness
            across an :class:`Evaluation` is checked there
            (case-insensitive after trimming, A10).
    weight: the parameter's importance weight (``Weight``).
    scores: the parameter's scores for all three groups (``GroupScores``).
    """

    name: str
    weight: Weight
    scores: GroupScores

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _check_name(self.name, "Parameter"))
        if not isinstance(self.weight, Weight):
            raise DomainInvariantError(
                f"Parameter.weight must be a Weight, got {type(self.weight).__name__}"
            )
        if not isinstance(self.scores, GroupScores):
            raise DomainInvariantError(
                f"Parameter.scores must be a GroupScores, "
                f"got {type(self.scores).__name__}"
            )


@dataclass(frozen=True)
class Evaluation:
    """A complete Simple Mode evaluation: product, declared scale + parameters.

    product:    the name of the product or service being evaluated
                (A21). Same name invariants as parameter names (A18):
                1–100 characters, no control characters, at least one
                non-whitespace character, stored **as provided**.
    scale_max:  integer, ``2 <= scale_max <= 100`` (A3). One scale
                applies to all parameters of the evaluation.
    parameters: 1–100 parameters (A11) with unique names
                (case-insensitive after trimming, A10), weights summing
                to 1 within EPSILON (C1), and every score within
                ``[0, scale_max]`` (C3).

    Group weights are intentionally **not a field**: Simple Mode fixes
    ``W_F = W_S = W_D = 1/3`` (A1, A8); that constant lives in
    ``universality/calculation.py``. Editable group weights are gated
    (M5) and would be a documented model change.
    """

    product: str
    scale_max: int
    parameters: tuple[Parameter, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "product", _check_name(self.product, "Evaluation", field="product"))
        if isinstance(self.scale_max, bool) or not isinstance(self.scale_max, int):
            raise DomainInvariantError(
                f"Evaluation.scale_max must be an int, got {type(self.scale_max).__name__}"
            )
        if not SCALE_MIN <= self.scale_max <= SCALE_MAX:
            raise DomainInvariantError(
                f"Evaluation.scale_max must be within [{SCALE_MIN}, {SCALE_MAX}], "
                f"got {self.scale_max}"
            )
        if not isinstance(self.parameters, tuple):
            raise DomainInvariantError(
                f"Evaluation.parameters must be a tuple, got {type(self.parameters).__name__}"
            )
        if not PARAMETER_MIN <= len(self.parameters) <= PARAMETER_MAX:
            raise DomainInvariantError(
                f"Evaluation.parameters must contain 1..{PARAMETER_MAX} parameters, "
                f"got {len(self.parameters)}"
            )
        seen: set[str] = set()
        for parameter in self.parameters:
            if not isinstance(parameter, Parameter):
                raise DomainInvariantError(
                    "Evaluation.parameters entries must be Parameter, "
                    f"got {type(parameter).__name__}"
                )
            key = parameter.name.strip().casefold()
            if key in seen:
                raise DomainInvariantError(
                    f"duplicate parameter name: {parameter.name!r} (A10)"
                )
            seen.add(key)
            for score in (parameter.scores.fap, parameter.scores.sap, parameter.scores.dap):
                if score.value > self.scale_max:
                    raise DomainInvariantError(
                        f"score {score.value!r} exceeds scale_max {self.scale_max} (C3)"
                    )
        if not weights_sum_is_valid([p.weight.value for p in self.parameters]):
            raise DomainInvariantError(
                "parameter weights must sum to 1 within EPSILON (C1)"
            )


# --------------------------------------------------------------------------
# Value objects — calculation output
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class PerGroupValue:
    """A triple of real values, one per user group.

    Type domain: each value finite and >= 0. Usage-specific upper bounds
    (documented in ``docs/DOMAIN_MODEL.md``):

    - as ``ParameterResult.normalized``:    [0, 1]  (F1 output domain)
    - as ``ParameterResult.contributions``: [0, 1]  (F2 summand domain)
    - as ``EvaluationResult.group_indices``: [0, 1 + EPSILON] (C1 tolerance)
    """

    fap: float
    sap: float
    dap: float

    def __post_init__(self) -> None:
        for field in ("fap", "sap", "dap"):
            value = _require_real_number(getattr(self, field), f"PerGroupValue.{field}")
            if value < 0:
                raise DomainInvariantError(f"PerGroupValue.{field} must be >= 0")
            object.__setattr__(self, field, value)

    def for_group(self, group: UserGroup) -> float:
        """Shape-navigation accessor (not a calculation)."""
        match group:
            case UserGroup.FAP:
                return self.fap
            case UserGroup.SAP:
                return self.sap
            case UserGroup.DAP:
                return self.dap
            case _:
                raise DomainInvariantError(f"unknown user group: {group!r}")


@dataclass(frozen=True)
class ParameterResult:
    """Per-parameter calculation output.

    Carries F1's output (``normalized``: the normalized scores
    ``s_norm(i, G)`` per group) and F2's per-parameter summands
    (``contributions``: ``w(i) * s_norm(i, G)`` per group). These are
    existing formula outputs structured for inspection — no new formula
    is introduced (the entire calculation surface is F1–F4; F4 was
    registered 2026-08-25 per explicit user instruction, A19).

    name:          same invariants as ``Parameter.name``.
    weight:        the weight used (traceability of contributions).
    normalized:    F1 outputs, each within [0, 1].
    contributions: F2 summands, each within [0, 1].
    """

    name: str
    weight: Weight
    normalized: PerGroupValue
    contributions: PerGroupValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _check_name(self.name, "ParameterResult"))
        if not isinstance(self.weight, Weight):
            raise DomainInvariantError(
                f"ParameterResult.weight must be a Weight, got {type(self.weight).__name__}"
            )
        if not isinstance(self.normalized, PerGroupValue):
            raise DomainInvariantError(
                "ParameterResult.normalized must be a PerGroupValue, "
                f"got {type(self.normalized).__name__}"
            )
        if not isinstance(self.contributions, PerGroupValue):
            raise DomainInvariantError(
                "ParameterResult.contributions must be a PerGroupValue, "
                f"got {type(self.contributions).__name__}"
            )


@dataclass(frozen=True)
class EvaluationResult:
    """The complete calculation output for one :class:`Evaluation`.

    group_indices: F2 outputs (UI_F, UI_S, UI_D); each within
                   ``[0, 1 + EPSILON]`` given the C1 tolerance.
    overall:       F3 output (UI); finite and >= 0. In exact arithmetic
                   within [0, 1] (C4); with the C1/C2 tolerances within
                   ``[0, 1 + 2*EPSILON]`` in floating point.
    parameters:    per-parameter results, non-empty; same order and
                   names as the input Evaluation (checked in
                   :class:`EvaluationOutcome`).
    group_gap:     F4 output (max-min spread of the group indices);
                   finite and >= 0; [0, 1] in exact arithmetic,
                   ``[0, 1 + EPSILON]`` in floating point (C1 tolerance).
    """

    group_indices: PerGroupValue
    overall: float
    parameters: tuple[ParameterResult, ...]
    group_gap: float

    def __post_init__(self) -> None:
        if not isinstance(self.group_indices, PerGroupValue):
            raise DomainInvariantError(
                "EvaluationResult.group_indices must be a PerGroupValue, "
                f"got {type(self.group_indices).__name__}"
            )
        object.__setattr__(
            self, "overall", _require_real_number(self.overall, "EvaluationResult.overall")
        )
        if self.overall < 0:
            raise DomainInvariantError("EvaluationResult.overall must be >= 0")
        object.__setattr__(
            self, "group_gap", _require_real_number(self.group_gap, "EvaluationResult.group_gap")
        )
        if self.group_gap < 0:
            raise DomainInvariantError("EvaluationResult.group_gap must be >= 0")
        if not (isinstance(self.parameters, tuple) and self.parameters):
            raise DomainInvariantError(
                "EvaluationResult.parameters must be a non-empty tuple"
            )
        for parameter in self.parameters:
            if not isinstance(parameter, ParameterResult):
                raise DomainInvariantError(
                    "EvaluationResult.parameters entries must be ParameterResult, "
                    f"got {type(parameter).__name__}"
                )


@dataclass(frozen=True)
class EvaluationOutcome:
    """The single object crossing the Application-to-consumer boundary
    (``docs/architecture.md`` §7–8).

    Pairs the input :class:`Evaluation` with its
    :class:`EvaluationResult` so consumers (UI, future export) need no
    global state. Consistency invariants: the result's per-parameter
    entries match the evaluation's parameters in count, order, and name.
    """

    evaluation: Evaluation
    result: EvaluationResult

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation, Evaluation):
            raise DomainInvariantError(
                "EvaluationOutcome.evaluation must be an Evaluation, got "
                f"{type(self.evaluation).__name__}"
            )
        if not isinstance(self.result, EvaluationResult):
            raise DomainInvariantError(
                "EvaluationOutcome.result must be an EvaluationResult, got "
                f"{type(self.result).__name__}"
            )
        if len(self.result.parameters) != len(self.evaluation.parameters):
            raise DomainInvariantError(
                "EvaluationOutcome.result must carry one ParameterResult per parameter of the evaluation"
            )

        if [p.name for p in self.result.parameters] != [
            p.name for p in self.evaluation.parameters
        ]:
            raise DomainInvariantError(
                "EvaluationOutcome.result parameter names must match the evaluation's parameter names in order"
            )
