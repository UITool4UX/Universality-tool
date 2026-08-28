"""UI smoke tests: ``ui/app.py`` under Streamlit's AppTest harness.

Covers the interaction contract from ``docs/UX_FLOW.md`` and the verification
checklist from the UI task: empty state, calculation state, result state,
every error state, no-internal-exposure, disabled states, reset, and
label/aria hygiene. (Keyboard/focus and responsive behavior are browser-level
concerns — see ``docs/ACCESSIBILITY.md`` §9 for the Streamlit notes.)

Note: ``st.rerun()``-driven flows (Add / Remove / Reset weights / Calculate)
complete within a single AppTest ``.run()``, so the DOM after ``run()`` is
the state the user sees for that interaction.
"""

from __future__ import annotations

import html
import unittest
from pathlib import Path

from universality import format_for_display

try:
    from streamlit.testing.v1 import AppTest

    _STREAMLIT = True
except ImportError:  # streamlit is an optional dependency of the core layers
    AppTest = None  # type: ignore[assignment,misc]
    _STREAMLIT = False

# Streamlit 1.62 resolves relative app paths against the *calling file*, so
# the app path must be absolute for discovery from any working directory.
APP = str(Path(__file__).resolve().parent.parent / "ui" / "app.py")


def launch() -> AppTest:
    return AppTest.from_file(APP, default_timeout=120).run()


def markdown_text(at: AppTest) -> str:
    # The app renders some normative copy with st.caption (stale-results
    # line, footer notes); include captions so assertions see all visible text.
    parts = [element.value for element in at.markdown]
    parts.extend(element.value for element in at.caption)
    return " ".join(parts)


def enter_tv7(at: AppTest) -> AppTest:
    at.text_input(key="product").set_value("Accessible chair").run()
    at.text_input(key="p0_name").set_value("Reachability").run()
    at.number_input(key="scale_max").set_value(10).run()
    at.number_input(key="p0_weight").set_value(0.7).run()
    at.number_input(key="p0_fap").set_value(10).run()
    at.number_input(key="p0_sap").set_value(5).run()
    at.number_input(key="p0_dap").set_value(1).run()
    at.button(key="add_param").click().run()
    at.text_input(key="p1_name").set_value("Stability").run()
    at.number_input(key="p1_weight").set_value(0.3).run()
    at.number_input(key="p1_fap").set_value(4).run()
    at.number_input(key="p1_sap").set_value(8).run()
    at.number_input(key="p1_dap").set_value(6).run()
    return at


FORBIDDEN_TOKENS = (
    "Traceback", "ValueError", "KeyError", "TypeError", "AttributeError",
    "IndexError", "universality.", "streamlit.",
)


@unittest.skipUnless(_STREAMLIT, "streamlit not installed")
class TestEmptyState(unittest.TestCase):
    def test_initial_render(self) -> None:
        at = launch()
        self.assertFalse(at.exception)
        text = markdown_text(at)
        # Wordmark, purpose, tags, sections, placeholder (UX_FLOW.md §8).
        self.assertIn("Universality Index Tool", text)
        self.assertIn("Enter your user-research findings to calculate the Universality Index.", text)
        self.assertIn("Part I — Evaluation setup", text)
        self.assertIn("Part II — Parameters", text)
        self.assertIn("Results will appear here after calculation.", text)
        # Visible defaults (D-UI-4).
        self.assertEqual(at.text_input(key="product").value, "")
        self.assertEqual(at.number_input(key="scale_max").value, 5)
        self.assertEqual(at.number_input(key="p0_weight").value, 1.0)
        self.assertEqual(at.number_input(key="p0_fap").value, 1)
        # The full inventory of five buttons, with the correct disabled state.
        buttons = {b.key: b for b in at.button}
        self.assertEqual(
            set(buttons), {"reset_masthead", "reset_weights", "remove_0", "add_param", "calculate"}
        )
        self.assertTrue(buttons["remove_0"].disabled)      # n = 1 → cannot remove
        self.assertFalse(buttons["add_param"].disabled)
        self.assertFalse(buttons["calculate"].disabled)
        # NOTE: AppTest reports a button's *widget* type ("button"), not its
        # visual variant; "primary" is a CSS-level attribute (st.button(...,
        # type="primary") → button[kind="primary"]), not exposed here. The
        # single-primary-action contract is pinned in ui/app.py + the CSS.
        # No labels are placeholder-only: every input carries a visible label.
        for element in at.text_input:
            self.assertTrue(element.label)
        for element in at.number_input:
            self.assertTrue(element.label)

    def test_skip_link_present(self) -> None:
        at = launch()
        self.assertIn('href="#calculate-anchor"', markdown_text(at))
        self.assertIn("Skip to calculation", markdown_text(at))


@unittest.skipUnless(_STREAMLIT, "streamlit not installed")
class TestResultState(unittest.TestCase):
    def test_tv7_happy_path(self) -> None:
        at = enter_tv7(launch())
        at.button(key="calculate").click().run()
        self.assertFalse(at.exception)
        outcome = at.session_state["outcome"]
        self.assertIsNotNone(outcome)
        # Canonical TV7 values via the single A6 location.
        self.assertEqual(format_for_display(outcome.result.overall), "0.5533")
        text = markdown_text(at)
        for expected in ("0.5533", "0.8200", "0.5900", "0.2500", "0.5700"):
            self.assertIn(expected, text)
        self.assertIn("✓ Calculated", text)
        self.assertIn("Part III — Results", text)
        self.assertIn("UNIVERSALITY INDEX (UI)", text)
        self.assertIn("USER-GROUP GAP", text)
        self.assertIn("FAP − DAP", text)  # gap sub-label (D-UI-9)
        self.assertNotIn("Please check the highlighted field.", text)
        # Product name renders as plain text (escape rule).
        texts = [t.value for t in at.text]
        self.assertIn("Accessible chair", texts)
        # Per-parameter table present (rows carry escaped names).
        self.assertIn("Per-parameter details", text)

    def test_known_case_ui_072_fap_092_sap_072_dap_052_gap_040(self) -> None:
        # Known reference case (2026-08-28 design-system integration), driven
        # through the REAL calculation engine and the index-v6 components:
        # scale 50, one parameter (weight 1.0), scores 46/36/26 →
        # normalized 0.92/0.72/0.52 → group indices 0.92/0.72/0.52,
        # overall 0.72, group gap 0.40. Nothing is hard-coded in the app.
        at = launch()
        at.text_input(key="product").set_value("CampusGo").run()
        at.text_input(key="p0_name").set_value("Navigation").run()
        at.number_input(key="scale_max").set_value(50).run()
        at.number_input(key="p0_fap").set_value(46).run()
        at.number_input(key="p0_sap").set_value(36).run()
        at.number_input(key="p0_dap").set_value(26).run()
        at.button(key="calculate").click().run()
        self.assertFalse(at.exception)
        outcome = at.session_state["outcome"]
        self.assertIsNotNone(outcome)
        # The engine's real results, through the single A6 location.
        self.assertEqual(format_for_display(outcome.result.overall), "0.7200")
        self.assertEqual(format_for_display(outcome.result.group_indices.fap), "0.9200")
        self.assertEqual(format_for_display(outcome.result.group_indices.sap), "0.7200")
        self.assertEqual(format_for_display(outcome.result.group_indices.dap), "0.5200")
        self.assertEqual(format_for_display(outcome.result.group_gap), "0.4000")
        # And the same values are what the UI actually renders.
        text = markdown_text(at)
        for expected in ("0.7200", "0.9200", "0.5200", "0.4000"):
            self.assertIn(expected, text)
        self.assertIn("FAP − DAP", text)  # gap sub-label (D-UI-9)
        self.assertIn("✓ Calculated", text)

    def test_result_replaced_on_new_success(self) -> None:
        at = enter_tv7(launch())
        at.button(key="calculate").click().run()
        at.number_input(key="p0_fap").set_value(4).run()  # change one score
        at.button(key="calculate").click().run()
        outcome = at.session_state["outcome"]
        self.assertIsNotNone(outcome)
        self.assertIsNone(at.session_state["rejection"])
        self.assertNotIn("Showing previous calculation", markdown_text(at))

    def test_stale_results_kept_dimmed_on_failure(self) -> None:
        at = enter_tv7(launch())
        at.button(key="calculate").click().run()
        at.number_input(key="p1_weight").set_value(0.26).run()  # sum 0.96
        at.button(key="calculate").click().run()
        self.assertIsNotNone(at.session_state["rejection"])
        self.assertIsNotNone(at.session_state["outcome"])  # previous kept
        text = markdown_text(at)
        self.assertIn("Showing previous calculation — new input was not accepted.", text)
        self.assertIn("0.5533", text)  # previous results still visible


@unittest.skipUnless(_STREAMLIT, "streamlit not installed")
class TestErrorStates(unittest.TestCase):
    def assert_clean_error(self, at: AppTest, code: str, field: str, extra: str = "") -> None:
        rejection = at.session_state["rejection"]
        self.assertIsNotNone(rejection)
        self.assertEqual(rejection.code, code)
        self.assertEqual(rejection.field, field)
        text = markdown_text(at)
        self.assertIn("Please check the highlighted field.", text)
        # The app renders the message via html.escape, so compare the escaped
        # form (e.g. a quoted name 'reachability' appears as &#x27;…).
        self.assertIn(html.escape(rejection.message), text)  # verbatim gate message
        self.assertIn("How to fix", text)
        if extra:
            self.assertIn(extra, text)
        for token in FORBIDDEN_TOKENS:
            self.assertNotIn(token, text)

    def test_missing_product_v16(self) -> None:
        at = launch()
        at.text_input(key="p0_name").set_value("Reachability").run()
        at.button(key="calculate").click().run()
        self.assert_clean_error(at, "V16", "product", "Product name")

    def test_weight_sum_0_96_v6(self) -> None:
        at = enter_tv7(launch())
        at.number_input(key="p1_weight").set_value(0.26).run()
        at.button(key="calculate").click().run()
        self.assert_clean_error(at, "V6", "parameters", "Reset weights to 1/n")

    def test_duplicate_name_v8(self) -> None:
        at = enter_tv7(launch())
        at.text_input(key="p1_name").set_value("reachability").run()  # case-dup
        at.button(key="calculate").click().run()
        self.assert_clean_error(at, "V8", "parameters[1].name", "Name of parameter 2")

    def test_orphaned_score_after_scale_change_v4(self) -> None:
        # UX_FLOW.md E3: lowering the scale never modifies stored scores
        # (the framework would silently clamp them); the gate names the field.
        at = launch()
        at.text_input(key="product").set_value("Accessible chair").run()
        at.text_input(key="p0_name").set_value("Reachability").run()
        at.number_input(key="scale_max").set_value(10).run()
        at.number_input(key="p0_fap").set_value(8).run()
        at.number_input(key="scale_max").set_value(3).run()
        self.assertEqual(at.session_state["p0_fap"], 8)  # preserved, not clamped
        at.button(key="calculate").click().run()
        self.assert_clean_error(
            at, "V4", "parameters[0].scores.fap",
            "Fully Abled People (FAP) score of parameter 1",
        )

    def test_out_of_range_score_v4(self) -> None:
        at = launch()
        at.text_input(key="product").set_value("Chair").run()
        at.text_input(key="p0_name").set_value("Reach").run()
        at.number_input(key="p0_fap").set_value(100).run()  # scale default 5
        at.button(key="calculate").click().run()
        self.assert_clean_error(at, "V4", "parameters[0].scores.fap")

    def test_no_traceback_under_any_scenario(self) -> None:
        at = launch()
        at.button(key="calculate").click().run()  # everything blank
        hostile = "<script>alert(1)</script> **bold**"
        at.text_input(key="product").set_value(hostile).run()
        at.text_input(key="p0_name").set_value("P1").run()
        at.button(key="calculate").click().run()
        # The hostile product name is stored and displayed as inert plain text
        # (st.text) — verbatim, unmodified, never executed — and no live
        # <script> tag or markdown bold appears in any rendered HTML context.
        self.assertIn(hostile, [t.value for t in at.text])
        self.assertNotIn("<script", markdown_text(at))
        self.assertNotIn("**bold**", markdown_text(at))
        for token in FORBIDDEN_TOKENS:
            self.assertNotIn(token, markdown_text(at))


@unittest.skipUnless(_STREAMLIT, "streamlit not installed")
class TestLastResortGuard(unittest.TestCase):
    """An exception that escapes the controlled flows (ValidationRejection /
    ServiceError) is an internal bug: the page shows only the fixed generic
    error state — never the message, class, frames, or source lines
    (docs/validation-and-security.md error handling; §9 'Never')."""

    def test_unexpected_exception_renders_generic_state_not_traceback(self) -> None:
        from unittest import mock

        at = launch()

        def boom(raw):
            raise RuntimeError("SECRET-INTERNAL-DETAIL-42")

        with mock.patch("universality.evaluate", side_effect=boom):
            at.button(key="calculate").click().run()
        # No exception surfaced to the Streamlit framework (which would
        # render a full traceback), and the controlled error state is set.
        self.assertFalse(at.exception)
        self.assertTrue(at.session_state["service_error"])
        self.assertIsNone(at.session_state["rejection"])
        text = markdown_text(at)
        # The fixed generic message (E5) is shown...
        self.assertIn("Something went wrong. Please try again.", text)
        # ...and nothing of the internal exception leaks.
        for token in ("SECRET-INTERNAL-DETAIL-42", "RuntimeError", *FORBIDDEN_TOKENS):
            self.assertNotIn(token, text)

    def test_rerun_control_flow_is_not_treated_as_a_fault(self) -> None:
        # Regression pin for the guard: st.rerun() flows (Add parameter)
        # must keep working — RerunException is control flow, not a fault.
        at = launch()
        at.button(key="add_param").click().run()
        self.assertFalse(at.exception)
        self.assertFalse(at.session_state["service_error"])
        self.assertEqual(at.session_state["param_count"], 2)


@unittest.skipUnless(_STREAMLIT, "streamlit not installed")
class TestBuilderActions(unittest.TestCase):
    def test_add_parameter_appends_card_with_defaults(self) -> None:
        at = launch()
        at.button(key="add_param").click().run()
        self.assertEqual(at.session_state["param_count"], 2)
        self.assertEqual(at.session_state["p1_weight"], 0.0)  # D-UI-5
        self.assertEqual(at.session_state["p1_fap"], 1)
        buttons = {b.key for b in at.button}
        self.assertIn("remove_1", buttons)
        self.assertIn("Parameter 2", markdown_text(at))

    def test_add_never_redistributes_weights(self) -> None:
        at = launch()
        at.number_input(key="p0_weight").set_value(0.9).run()
        at.button(key="add_param").click().run()
        self.assertEqual(at.session_state["p0_weight"], 0.9)  # untouched
        self.assertEqual(at.session_state["p1_weight"], 0.0)

    def test_remove_parameter_reindexes_without_touching_values(self) -> None:
        at = enter_tv7(launch())
        values = {
            "name": at.session_state["p1_name"],
            "weight": at.session_state["p1_weight"],
            "fap": at.session_state["p1_fap"],
        }
        at.button(key="remove_0").click().run()
        self.assertEqual(at.session_state["param_count"], 1)
        self.assertEqual(at.session_state["p0_name"], values["name"])
        self.assertEqual(at.session_state["p0_weight"], values["weight"])
        self.assertEqual(at.session_state["p0_fap"], values["fap"])
        self.assertNotIn("remove_1", {b.key for b in at.button})

    def test_reset_weights_sets_equal_values(self) -> None:
        at = enter_tv7(launch())
        at.button(key="reset_weights").click().run()
        self.assertEqual(at.session_state["p0_weight"], 0.5)
        self.assertEqual(at.session_state["p1_weight"], 0.5)

    def test_reset_two_click(self) -> None:
        at = enter_tv7(launch())
        first = next(b for b in at.button if b.key == "reset_masthead")
        self.assertEqual(first.label, "Reset evaluation")
        at.button(key="reset_masthead").click().run()  # arm
        armed = next(b for b in at.button if b.key == "reset_masthead")
        self.assertEqual(
            armed.label, "Confirm reset — clears all entered data?"
        )
        self.assertTrue(at.session_state["reset_armed"])
        at.button(key="reset_masthead").click().run()  # confirm
        self.assertEqual(at.session_state["product"], "")
        self.assertEqual(at.session_state["param_count"], 1)
        self.assertIsNone(at.session_state["outcome"])
        self.assertIsNone(at.session_state["rejection"])
        self.assertIn("Results will appear here after calculation.", markdown_text(at))

    def test_add_disabled_at_100_parameters(self) -> None:
        # The AppTest session-state proxy (SafeSessionState) exposes only
        # item access — no .update() — so seed key by key.
        at = launch()
        at.session_state["param_count"] = 100
        at.run()
        add = next(b for b in at.button if b.key == "add_param")
        self.assertTrue(add.disabled)
        self.assertIn("Maximum 100 parameters", markdown_text(at))
        remove = next(b for b in at.button if b.key == "remove_50")
        self.assertFalse(remove.disabled)


if __name__ == "__main__":
    unittest.main()
