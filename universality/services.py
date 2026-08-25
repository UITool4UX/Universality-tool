"""Application layer — the single boundary between UI and computation.

``docs/architecture.md`` §5–7: the UI (composition root) calls
:func:`evaluate`; everything below is validated domain, everything above
is presentation.

Error contract (``docs/validation-and-security.md``, error handling):

- :class:`~universality.validation.ValidationRejection` (controlled user-input
  failure) propagates **unchanged** — the UI renders its ``code`` / ``field``
  / ``message`` (the message is verbatim; the UI adds the translated label and
  the fix hint — presentation, not computation).
- Any other exception is caught at this boundary, logged **redacted** via
  :mod:`universality.diagnostics`, and surfaced as
  :class:`ServiceError` with a fixed generic message. Internal exceptions
  never escape this module.

Presentation rounding (A6): :func:`format_for_display` is the **sole**
location in the codebase where results are rounded (4 decimal places,
fixed-point string). Display rounding never feeds back into computation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from universality.calculation import compute
from universality.diagnostics import log_unexpected
from universality.domain import EvaluationOutcome, DomainInvariantError
from universality.validation import ValidationRejection, validate

__all__ = ["GENERIC_SERVICE_MESSAGE", "ServiceError", "evaluate", "format_for_display"]

#: The fixed, generic message for every unexpected failure. Never exposes
#: internals; displayed to the user verbatim (UI error flow E5).
GENERIC_SERVICE_MESSAGE: Final[str] = "Something went wrong. Please try again."


@dataclass(frozen=True)
class ServiceError(Exception):
    """An unexpected internal failure surfaced at the application boundary.

    Carries no details: ``str()`` is the fixed generic message. The
    underlying exception is logged redacted (``diagnostics``) and never
    re-raised, chained, or exposed.
    """

    message: str = GENERIC_SERVICE_MESSAGE

    def __str__(self) -> str:
        return self.message


def evaluate(raw: object) -> EvaluationOutcome:
    """The application entry point: raw user input → validated → computed.

    Returns an :class:`~universality.domain.EvaluationOutcome` pairing the
    validated evaluation with its result (Simple Mode group weights — the
    public-API constant; A1/A8). Raises
    :class:`~universality.validation.ValidationRejection` unchanged for
    controlled input failures, or :class:`ServiceError` for anything else.
    """
    try:
        evaluation = validate(raw)
    except ValidationRejection:
        raise
    except Exception as exc:  # unreachable in practice — the gate is total
        log_unexpected("evaluate.validation", exc)
        raise ServiceError() from None

    try:
        result = compute(evaluation)
        return EvaluationOutcome(evaluation=evaluation, result=result)
    except Exception as exc:
        # A DomainInvariantError here would be a bug (the gate precedes
        # construction); any other type is an internal failure either way.
        log_unexpected("evaluate.outcome", exc)
        raise ServiceError() from None


def format_for_display(value: float) -> str:
    """A6 — the single presentation-rounding location.

    Renders a computed value as a fixed-point string with 4 decimal places
    (``0.623 -> "0.6230"``). Pure: never mutates state, and the string is
    never fed back into computation. No clamping: values in the documented
    C1/C2 tolerance band (slightly above 1) print faithfully.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"format_for_display expects a real number, got {type(value).__name__}"
        )
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("format_for_display expects a finite number")
    return f"{number:.4f}"
