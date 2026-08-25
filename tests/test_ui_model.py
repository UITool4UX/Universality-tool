"""UI presentation-model tests: ``ui/ui_model.py`` (pure, no Streamlit).

Per ``docs/UI_ARCHITECTURE.md`` §10 the model is unit-tested **without**
Streamlit. Enforced here:

- the module is math-free at the AST level (no binary operators at all —
  assembly and label mapping only; the two flagged D-UI operations live in
  ``app.py`` and are not exercised here);
- ``collect_raw`` assembles exactly the documented raw schema;
- the field-path → target/label mapping matches the normative table
  (``docs/UI_ARCHITECTURE.md`` §5) verbatim;
- the copy table carries the normative strings (``docs/UX_FLOW.md`` §7);
- no forbidden imports or constructs.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

from ui import ui_model

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "ui" / "ui_model.py"


def sample_state(n: int = 3) -> dict:
    state = {
        "product": "Accessible chair",
        "scale_max": 10,
        "param_count": n,
    }
    for i in range(n):
        state[f"p{i}_name"] = f"P{i + 1}"
        state[f"p{i}_weight"] = 1.0 / n if n > 1 else 1.0
        state[f"p{i}_fap"] = i + 1
        state[f"p{i}_sap"] = 2
        state[f"p{i}_dap"] = 3
    return state


class TestFreshState(unittest.TestCase):
    def test_defaults_match_design(self) -> None:
        state = ui_model.fresh_state()
        self.assertEqual(state["product"], "")
        self.assertEqual(state["scale_max"], ui_model.SCALE_DEFAULT)
        self.assertEqual(ui_model.SCALE_DEFAULT, 5)  # D-UI-4 visible default
        self.assertEqual(state["param_count"], 1)
        self.assertIsNone(state["outcome"])
        self.assertIsNone(state["rejection"])
        self.assertFalse(state["service_error"])
        self.assertFalse(state["reset_armed"])
        # Visible editable defaults for the single initial parameter.
        self.assertEqual(state["p0_name"], "")
        self.assertEqual(state["p0_weight"], 1.0)  # 1/n for n = 1
        self.assertEqual(state["p0_fap"], 1)
        self.assertEqual(state["p0_sap"], 1)
        self.assertEqual(state["p0_dap"], 1)

    def test_independent_copies(self) -> None:
        first = ui_model.fresh_state()
        second = ui_model.fresh_state()
        first["product"] = "mutated"
        self.assertEqual(second["product"], "")


class TestCollectRaw(unittest.TestCase):
    def test_exact_schema(self) -> None:
        raw = ui_model.collect_raw(sample_state(3))
        self.assertEqual(list(raw.keys()), ["product", "scale_max", "parameters"])
        self.assertEqual(raw["product"], "Accessible chair")
        self.assertEqual(raw["scale_max"], 10)
        self.assertEqual(len(raw["parameters"]), 3)
        for i, parameter in enumerate(raw["parameters"]):
            self.assertEqual(list(parameter.keys()), ["name", "weight", "scores"])
            self.assertEqual(list(parameter["scores"].keys()), ["fap", "sap", "dap"])
            self.assertEqual(parameter["name"], f"P{i + 1}")

    def test_single_parameter(self) -> None:
        raw = ui_model.collect_raw(sample_state(1))
        self.assertEqual(len(raw["parameters"]), 1)
        self.assertEqual(raw["parameters"][0]["weight"], 1.0)

    def test_values_pass_through_unmodified(self) -> None:
        state = sample_state(2)
        state["p1_weight"] = 0.3333333333333333
        state["p0_fap"] = 7
        raw = ui_model.collect_raw(state)
        self.assertIs(raw["parameters"][1]["weight"], 0.3333333333333333)
        self.assertIs(raw["parameters"][0]["scores"]["fap"], 7)

    def test_unknown_keys_never_added(self) -> None:
        state = sample_state(1)
        state["junk_top"] = "x"
        state["p0_junk"] = "y"
        raw = ui_model.collect_raw(state)
        self.assertNotIn("junk_top", raw)
        self.assertNotIn("junk", raw["parameters"][0])


class TestParseField(unittest.TestCase):
    CASES = (
        ("product", "product", None, None, False),
        ("scale_max", "scale", None, None, False),
        ("parameters", "parameters", None, None, False),
        ("parameters[0]", "parameter", 0, None, False),
        ("parameters[2]", "parameter", 2, None, False),
        ("parameters[1].name", "name", 1, None, False),
        ("parameters[1].weight", "weight", 1, None, False),
        ("parameters[1].scores", "scores", 1, None, False),
        ("parameters[0].scores.fap", "score", 0, "fap", False),
        ("parameters[0].scores.sap", "score", 0, "sap", False),
        ("parameters[0].scores.dap", "score", 0, "dap", False),
        ("group_weights", "group_weights", None, None, True),
        ("", "global", None, None, True),
        ("something else", "global", None, None, True),
        ("parameters[0].scores.unknown", "global", None, None, True),
    )

    def test_normative_mapping_table(self) -> None:
        for field, scope, index, group, summary_only in self.CASES:
            with self.subTest(field=field):
                info = ui_model.parse_field(field)
                self.assertEqual(info["scope"], scope)
                self.assertEqual(info["index"], index)
                self.assertEqual(info["group"], group)
                self.assertEqual(info["summary_only"], summary_only)


class TestHumanLabel(unittest.TestCase):
    CASES = (
        ("product", "Product name"),
        ("scale_max", "Scale maximum"),
        ("parameters", "Parameters"),
        ("parameters[0]", "Parameter 1"),
        ("parameters[2]", "Parameter 3"),
        ("parameters[1].name", "Name of parameter 2"),
        ("parameters[1].weight", "Weight of parameter 2"),
        ("parameters[1].scores", "Scores of parameter 2"),
        ("parameters[0].scores.fap", "Fully Abled People (FAP) score of parameter 1"),
        ("parameters[0].scores.sap", "Specially Abled People (SAP) score of parameter 1"),
        ("parameters[0].scores.dap", "Differently Abled People (DAP) score of parameter 1"),
        ("group_weights", "Internal group weights"),
    )

    def test_normative_labels_verbatim(self) -> None:
        for field, expected in self.CASES:
            with self.subTest(field=field):
                self.assertEqual(ui_model.human_label(ui_model.parse_field(field)), expected)

    def test_unknown_scope_has_no_label(self) -> None:
        self.assertEqual(ui_model.human_label(ui_model.parse_field("bogus")), "")


class TestFixHints(unittest.TestCase):
    def test_every_v_code_has_a_hint(self) -> None:
        for code in (
            "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10", "V11",
            "V12", "V13", "V14", "V16", "V17", "V18", "V19", "V20", "V21",
        ):
            with self.subTest(code=code):
                self.assertTrue(ui_model.fix_hint(code).strip())

    def test_unexpected_has_no_hint(self) -> None:
        self.assertEqual(ui_model.fix_hint("V-UNEXPECTED"), "")

    def test_unknown_code_has_no_hint(self) -> None:
        self.assertEqual(ui_model.fix_hint("V99"), "")


class TestCopyTable(unittest.TestCase):
    REQUIRED = (
        "page_title", "wordmark", "purpose", "tag", "skip_link",
        "part1_title", "part2_title", "part3_title",
        "product_label", "scale_label", "scale_caption",
        "weight_caption", "legend", "add", "add_disabled_caption",
        "reset_weights", "calculate", "calculating", "reset", "reset_armed",
        "calculated", "stale", "results_placeholder", "overall_label",
        "gap_label", "per_param_title", "table_caption", "a6_note",
        "footer_a4", "footer_a7", "footer_local", "error_title",
    )

    def test_all_required_strings_present(self) -> None:
        for key in self.REQUIRED:
            with self.subTest(key=key):
                self.assertTrue(ui_model.COPY[key].strip())

    def test_normative_strings_verbatim(self) -> None:
        self.assertEqual(ui_model.COPY["error_title"], "Please check the highlighted field.")
        self.assertEqual(
            ui_model.COPY["a6_note"],
            "Values shown to 4 decimal places; full-precision values were used in all calculations.",
        )
        self.assertEqual(
            ui_model.COPY["stale"],
            "Showing previous calculation — new input was not accepted.",
        )
        self.assertTrue(ui_model.COPY["footer_a7"].startswith("This tool is a simplified implementation"))
        self.assertTrue(ui_model.COPY["footer_a4"].startswith("Scores are taken as given"))

    def test_counter_uses_public_parameter_max(self) -> None:
        self.assertEqual(ui_model.counter_text(3), "3 of 100")
        self.assertEqual(ui_model.counter_text(100), "100 of 100")


class TestModulePurity(unittest.TestCase):
    """The model is math-free and dependency-clean at the AST level."""

    def setUp(self) -> None:
        self.tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))

    def test_contains_no_arithmetic_at_all(self) -> None:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.BinOp):
                self.fail(f"arithmetic at line {node.lineno}")

    def test_contains_no_forbidden_calls(self) -> None:
        forbidden = {"sum", "round", "max", "min", "eval", "exec", "compile", "getattr"}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, forbidden, msg=f"line {node.lineno}")

    def test_imports_only_permitted_modules(self) -> None:
        permitted = {"re", "typing", "universality", "__future__"}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], permitted, msg=alias.name)
            elif isinstance(node, ast.ImportFrom):
                self.assertIn((node.module or "").split(".")[0], permitted, msg=str(node.module))

    def test_no_forbidden_identifiers_anywhere(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        for token in ("eval(", "exec(", "pickle", "os.system", "subprocess", "requests", "urllib", "http."):
            self.assertNotIn(token, source, msg=token)


if __name__ == "__main__":
    unittest.main()
