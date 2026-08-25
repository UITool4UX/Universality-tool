"""Diagnostics tests: ``universality/diagnostics.py``.

The redaction contract (``docs/architecture.md`` §9): log records carry the
context identifier, the exception class + class chain, cause/context flags,
and the **safe stack frames** (``file:line:function``) — and never the
exception type/message line, source lines, ``args``, or any user value.
"""

from __future__ import annotations

import logging
import unittest

from universality import diagnostics


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)
        self.messages.append(record.getMessage())


class TestRedactedError(unittest.TestCase):
    def test_carries_class_and_structure_only(self) -> None:
        exc = ValueError("SECRET-USER-DATA-123")
        info = diagnostics.redacted_error(exc)
        self.assertEqual(info["class"], "ValueError")
        self.assertTrue(info["mro"][0] == "ValueError")
        self.assertIn("Exception", info["mro"])
        self.assertIsInstance(info["had_cause"], bool)
        self.assertIsInstance(info["had_context"], bool)
        # No payload of any kind leaks.
        self.assertNotIn("SECRET-USER-DATA-123", str(info))
        self.assertNotIn("SECRET-USER-DATA-123", repr(info))

    def test_cause_and_context_flags(self) -> None:
        plain = ValueError("a")
        self.assertFalse(diagnostics.redacted_error(plain)["had_cause"])
        try:
            try:
                raise KeyError("inner-secret")
            except KeyError as inner:
                raise ValueError("outer-secret") from inner
        except ValueError as chained:
            info = diagnostics.redacted_error(chained)
        self.assertTrue(info["had_cause"])
        self.assertNotIn("inner-secret", str(info))
        self.assertNotIn("outer-secret", str(info))


class TestLogUnexpected(unittest.TestCase):
    def setUp(self) -> None:
        self.capture = _Capture()
        diagnostics.logger.addHandler(self.capture)

    def tearDown(self) -> None:
        diagnostics.logger.removeHandler(self.capture)

    def test_logs_class_and_context_not_message(self) -> None:
        diagnostics.log_unexpected("evaluate.validation", ValueError("SECRET-USER-DATA"))
        self.assertEqual(len(self.capture.messages), 1)
        message = self.capture.messages[0]
        self.assertIn("evaluate.validation", message)
        self.assertIn("ValueError", message)
        self.assertNotIn("SECRET-USER-DATA", message)

    def test_log_level_is_error(self) -> None:
        diagnostics.log_unexpected("evaluate.outcome", RuntimeError("x"))
        self.assertEqual(self.capture.records[0].levelno, logging.ERROR)

    def test_message_template_is_deterministic(self) -> None:
        def _boom(label: str) -> None:
            raise ValueError(label)  # same line on every call → identical frames

        for label in ("a", "completely different b"):
            try:
                _boom(label)
            except ValueError as exc:
                diagnostics.log_unexpected("ctx", exc)
        self.assertEqual(self.capture.messages[1], self.capture.messages[0])

    def test_logs_safe_stack_frames_for_raised_exception(self) -> None:
        try:
            # SENTINEL-SOURCE-LINE must never reach the log (source lines excluded).
            raise ValueError("frame-secret")
        except ValueError as exc:
            diagnostics.log_unexpected("ctx", exc)
        message = self.capture.messages[0]
        self.assertIn("frames=", message)
        self.assertIn("test_diagnostics.py", message)  # file location
        self.assertIn(
            ":test_logs_safe_stack_frames_for_raised_exception", message
        )  # function name
        self.assertNotIn("SENTINEL-SOURCE-LINE", message)  # no source-line text
        self.assertNotIn("frame-secret", message)  # no exception message

    def test_malformed_context_is_never_logged_verbatim(self) -> None:
        # Log-injection hardening (2026-08-26 security audit): a context
        # containing newlines or other non-identifier characters is replaced
        # by the fixed placeholder — it can never forge a log line.
        diagnostics.log_unexpected("evil\nINJECTED-LINE", ValueError("x"))
        message = self.capture.messages[0]
        self.assertIn("<invalid-context>", message)
        self.assertNotIn("INJECTED-LINE", message)
        self.assertNotIn("\n", message)
        # The exception class is still reported (structure only).
        self.assertIn("ValueError", message)

    def test_non_string_context_is_replaced(self) -> None:
        diagnostics.log_unexpected(42, ValueError("x"))  # type: ignore[arg-type]
        self.assertIn("<invalid-context>", self.capture.messages[0])

    def test_unraised_exception_logs_no_frames(self) -> None:
        diagnostics.log_unexpected("ctx", ValueError("never-raised"))
        message = self.capture.messages[0]
        self.assertIn("frames=<no frames>", message)
        self.assertNotIn("never-raised", message)

    def test_chained_exception_leaks_nothing(self) -> None:
        try:
            try:
                raise KeyError("deep-secret")
            except KeyError as inner:
                raise ValueError("mid-secret") from inner
        except ValueError as exc:
            diagnostics.log_unexpected("ctx", exc)
        message = self.capture.messages[0]
        for secret in ("deep-secret", "mid-secret"):
            self.assertNotIn(secret, message)


class TestLoggerDefaults(unittest.TestCase):
    def test_default_sink_is_null(self) -> None:
        # Nothing may be emitted by default: a NullHandler is attached and
        # propagation is off, so no application default handler receives it.
        self.assertTrue(
            any(isinstance(h, logging.NullHandler) for h in diagnostics.logger.handlers)
        )
        self.assertFalse(diagnostics.logger.propagate)


if __name__ == "__main__":
    unittest.main()
