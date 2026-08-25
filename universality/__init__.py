"""Universality Index Tool — public API.

External consumers (UI, tests, future tooling) import **only** from this
package, never from submodules (``docs/architecture.md`` §5–6).

The public surface grows layer by layer:

- DOMAIN — implemented: the domain model (spec: ``docs/DOMAIN_MODEL.md``).
- CALCULATION — implemented: the engine for F1–F4
  (spec: ``docs/CALCULATION_ENGINE.md``; formulas: ``docs/FORMULA_SPECIFICATION.md``).
- APPLICATION — implemented: the validation gate
  (``validate``, ``validate_group_weights``, ``ValidationRejection``;
  spec: ``docs/validation-and-security.md``) and the application boundary
  (``evaluate``, ``format_for_display``, ``ServiceError``;
  spec: ``docs/architecture.md`` §5–7). Deferred: ``export`` (V15 lane),
  the research lane.
"""

from universality.calculation import (
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
    PARAMETER_MAX,
    SCALE_MAX,
    SCALE_MIN,
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
from universality.services import (
    ServiceError,
    evaluate,
    format_for_display,
)
from universality.validation import (
    ValidationRejection,
    validate,
    validate_group_weights,
)

__version__ = "0.1.0"

__all__ = [
    # APPLICATION — validation
    "ValidationRejection",
    "validate",
    "validate_group_weights",
    # APPLICATION — services
    "ServiceError",
    "evaluate",
    "format_for_display",
    # CALCULATION
    "SIMPLE_MODE_GROUP_WEIGHTS",
    "compute",
    "group_gap",
    "group_index",
    "normalize_score",
    "overall_index",
    "parameter_contributions",
    # DOMAIN
    "EPSILON",
    "PARAMETER_MAX",
    "SCALE_MAX",
    "SCALE_MIN",
    "DomainInvariantError",
    "Evaluation",
    "EvaluationOutcome",
    "EvaluationResult",
    "GroupScores",
    "KanoCategory",
    "Parameter",
    "ParameterResult",
    "PerGroupValue",
    "Score",
    "UserGroup",
    "Weight",
    "weights_sum_is_valid",
    "__version__",
]
