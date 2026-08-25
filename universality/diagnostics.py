"""Diagnostics (APPLICATION support module) — redacted structured logging.

Error flow per ``docs/architecture.md`` §7–9: unexpected exceptions that get
past the validation gate are logged **redacted** — class, class chain, and
safe stack frames (``file:line:function``), never user values — and surface
to the user as the generic ``services.ServiceError`` message.

Rules:

- standard library only (``logging``, ``traceback``, ``re``);
- the log record carries: the internal call-site identifier, the exception
  class + class chain, cause/context presence flags, and the **safe stack
  frames** (``file:line:function`` — the traceback's call sites, per
  ``docs/architecture.md`` §9) — and **never** the exception
  type/message line (messages routinely embed user values), never source
  lines, never ``args``, never any user-provided data;
- the ``context`` argument is an internal call-site identifier
  (e.g. ``"evaluate.validation"``); callers must never pass user data in it.
  The shape is **enforced fail-closed** (security audit 2026-08-26):
  ``context`` must be a string matching ``[A-Za-z0-9._-]{1,64}`` or it is
  replaced by the fixed placeholder ``<invalid-context>`` — a malformed
  context (e.g. one containing newlines or user data) can therefore never
  forge or pollute a log line (log-injection hardening);
- default handler: ``NullHandler`` with ``propagate = False`` — the
  environment (or a test) attaches its own handler.
"""

from __future__ import annotations

import logging
import re
import traceback
from typing import Any, Final

__all__ = ["logger", "redacted_error", "log_unexpected"]

#: The single diagnostics logger for the application layer.
logger: Final[logging.Logger] = logging.getLogger("universality.diagnostics")

if not logger.handlers:
    logger.addHandler(logging.NullHandler())
logger.propagate = False

#: Permitted shape of a ``context`` identifier: a short internal call-site
#: identifier (letters, digits, ``.``, ``_``, ``-``; 1–64 characters).
#: Enforced fail-closed in :func:`log_unexpected` (see module docstring).
_CONTEXT_SHAPE: Final = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")

#: Fixed placeholder logged in place of a malformed ``context``.
_INVALID_CONTEXT: Final = "<invalid-context>"


def redacted_error(exc: BaseException) -> dict[str, Any]:
    """Structural descriptor of an exception: class names only.

    Deliberately excludes the message, ``args``, and any other payload:
    exception messages routinely embed user values (e.g.
    ``"score 5.0 exceeds scale_max 2"``) and must not reach a log sink.
    """
    return {
        "class": type(exc).__name__,
        "mro": [cls.__name__ for cls in type(exc).__mro__],
        "had_cause": exc.__cause__ is not None,
        "had_context": exc.__context__ is not None,
    }


def _safe_frames(exc: BaseException) -> str:
    """The traceback as ``file:line:function`` call sites — nothing else.

    Deliberately excludes the source-line text (which may contain string
    literals) and the exception type/message line (which embeds the
    message — a user-value vector). For an exception that was never
    raised, there is no traceback and the result is ``<no frames>``.
    """
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return "<no frames>"
    return " <- ".join(f"{fr.filename}:{fr.lineno}:{fr.name}" for fr in frames)


def log_unexpected(context: str, exc: BaseException) -> None:
    """Log an unexpected exception at ERROR level, fully redacted.

    The record message is a fixed template filled only with the context
    identifier, class-level information, and safe stack frames — so it
    contains no user data (architecture.md §9). A ``context`` that does not
    match the identifier shape is replaced by the fixed
    ``<invalid-context>`` placeholder (fail-closed; never logged verbatim).
    """
    if not isinstance(context, str) or _CONTEXT_SHAPE.match(context) is None:
        context = _INVALID_CONTEXT
    info = redacted_error(exc)
    logger.error(
        "unexpected exception in %s: class=%s chain=%s cause=%s context=%s frames=%s",
        context,
        info["class"],
        "+".join(info["mro"][:3]),
        info["had_cause"],
        info["had_context"],
        _safe_frames(exc),
    )
