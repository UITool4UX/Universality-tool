"""UI band — pure presentation model (no Streamlit, no math).

Per ``docs/UI_ARCHITECTURE.md`` §3/§10: the functions here are pure and
unit-testable without Streamlit. They perform *assembly* and *label
mapping* only — no formulas, no tolerances, no sums, no rounding, no
clamping, no comparison of numeric magnitudes.

The two permitted non-formatting UI operations (flagged D-UI-5 / D-UI-9 in
``docs/UI_ARCHITECTURE.md`` §11) live in ``app.py``, not here:

- ``1.0 / n`` — the explicit "Reset weights to 1/n" action only;
- ``max``/``min`` over the three already-computed group indices — the gap
  card's sub-label only.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from universality import PARAMETER_MAX

__all__ = [
    "SCALE_DEFAULT",
    "GROUPS",
    "GROUP_LABELS",
    "GROUP_SHORT",
    "COPY",
    "FIX_HINTS",
    "fresh_state",
    "collect_raw",
    "parse_field",
    "human_label",
    "fix_hint",
]

#: Visible editable default for the scale (D-UI-4: number inputs cannot be
#: blank; 5 is the common 1–5 Likert maximum — shown and changeable).
SCALE_DEFAULT = 5

GROUPS: tuple[str, str, str] = ("fap", "sap", "dap")

GROUP_LABELS: dict[str, str] = {
    "fap": "Fully Abled People",
    "sap": "Specially Abled People",
    "dap": "Differently Abled People",
}

GROUP_SHORT: dict[str, str] = {"fap": "FAP", "sap": "SAP", "dap": "DAP"}

#: Normative visible strings (docs/UX_FLOW.md §7 — single location).
COPY: dict[str, str] = {
    "page_title": "Universality Index Tool",
    "wordmark": "Universality Index Tool",
    "purpose": "Enter your user-research findings to calculate the Universality Index.",
    "tag": "v0.1.0 · Simple Mode",
    "skip_link": "Skip to calculation",
    "part1_title": "Part I — Evaluation setup",
    "product_label": "Product name",
    "product_placeholder": "e.g., Accessible chair",
    "scale_label": "Scale maximum",
    "scale_caption": "The maximum value of the satisfaction scale you used (whole number, 2–100).",
    # {w} is filled with format_for_display(SIMPLE_MODE_GROUP_WEIGHTS[0]).
    "group_weights_note": "Simple Mode — group weights: {w} each (1/3, shown, not editable)",
    "part2_title": "Part II — Parameters",
    "counter": "{n} of {max}",
    "weight_label": "Weight (parameter {n})",
    "weight_caption": "All weights must sum to 1.00.",
    "name_label": "Name (parameter {n})",
    "name_placeholder": "e.g., Ease of reaching the handle",
    "score_label": "{short} score (parameter {n})",
    "legend": "FAP — Fully Abled People · SAP — Specially Abled People · DAP — Differently Abled People",
    "add": "+ Add parameter",
    "add_disabled_caption": "Maximum 100 parameters",
    "reset_weights": "Reset weights to 1/n",
    "remove_label": "Remove {n}",
    "calculate": "Calculate",
    "calculating": "Calculating…",
    "reset": "Reset evaluation",
    "reset_armed": "Confirm reset — clears all entered data?",
    "part3_title": "Part III — Results",
    "calculated": "✓ Calculated",
    "stale": "Showing previous calculation — new input was not accepted.",
    "results_placeholder": "Results will appear here after calculation.",
    "overall_label": "UNIVERSALITY INDEX (UI)",
    "overall_caption": "(range 0.0000–1.0000)",
    "gap_label": "USER-GROUP GAP",
    "per_param_title": "Per-parameter details",
    "table_caption": "Per-parameter normalized scores (s ÷ scale)",
    "table2_title": "Contribution to each group index (weight × normalized score)",
    "table2_caption": "Each cell is the parameter's weight multiplied by its normalized score.",
    "a6_note": "Values shown to 4 decimal places; full-precision values were used in all calculations.",
    "footer_a4": "Scores are taken as given — no shifting, rescaling, or normalization of your data.",
    "footer_a7": "This tool is a simplified implementation of the Singh & Tandon user-values framework, not a full reproduction of the research methodology.",
    "footer_local": "Calculated locally in your session — nothing is uploaded or stored.",
    "error_title": "Please check the highlighted field.",
}

#: Fix guidance per rejection code (the "how to fix it" line of the error
#: state — docs/UX_FLOW.md §6; presentation copy, never replaces the
#: verbatim gate message).
FIX_HINTS: dict[str, str] = {
    "V1": "Enter a real number — not blank, not a special value.",
    "V2": "Enter a finite number (no infinity).",
    "V3": "Enter a number — true/false is not accepted here.",
    "V4": "Enter a value between 1 and the declared scale maximum.",
    "V5": "Enter a weight between 0 and 1.",
    "V6": "Adjust the weights so they add up to exactly 1.00 (or press “Reset weights to 1/n”).",
    "V7": "Fill in the missing value — this field is required.",
    "V8": "Give every parameter a unique name.",
    "V9": "Shorten the name to at most 100 characters.",
    "V10": "Remove control or other non-printing characters from the name.",
    "V11": "Enter a whole number between 2 and 100.",
    "V12": "Add at least one parameter (maximum 100).",
    "V13": "Enter a real number in digits (for example 4 or 4.5).",
    "V14": "Enter a score for every group (FAP, SAP, and DAP) of this parameter.",
    "V16": "Enter the name of the product or service you evaluated.",
    "V17": "Shorten the product name to at most 100 characters.",
    "V18": "Remove control or other non-printing characters from the product name.",
    "V19": "Re-enter the value in the field — the format was unexpected.",
    "V20": "Internal group weights are misconfigured — this should not happen with user input.",
    "V21": "Internal group weights do not add to 1 — this should not happen with user input.",
    "V-UNEXPECTED": "",
}

_FIELD_RE = re.compile(
    r"^parameters\[(?P<i>\d+)\](?:\.(?P<part>name|weight|scores)(?:\.(?P<group>fap|sap|dap))?)?$"
)

#: 1-based display numbers "1".."100", precomputed so this module contains
#: no arithmetic operator at all (enforced by
#: ``tests/test_ui_model.py::TestModulePurity`` — the 0→1 relabel is a
#: presentation detail, not a calculation).
_ONE_BASED: tuple[str, ...] = tuple(str(n) for n in range(1, 101))  # 1..PARAMETER_MAX
if len(_ONE_BASED) != PARAMETER_MAX:
    # Static consistency check — fails at import if the table and the
    # domain constant ever drift apart.
    raise ValueError(
        f"_ONE_BASED has {len(_ONE_BASED)} entries, expected {PARAMETER_MAX}"
    )


def _display_number(index: object) -> str:
    """0-based parameter index -> 1-based display number ("" if out of range).

    Out-of-range indices come from stale field paths (a rejection recorded
    before a parameter was removed); the caller renders the summary panel
    only in that case (B-3), and the empty string keeps labels neutral.
    """
    if isinstance(index, int) and 0 <= index < len(_ONE_BASED):
        return _ONE_BASED[index]
    return ""


def fresh_state() -> dict[str, Any]:
    """A fresh UI session state (visible defaults, D-UI-4).

    Flat keys: the widget-backed values (``product``, ``scale_max``,
    ``p{i}_name`` / ``p{i}_weight`` / ``p{i}_fap|sap|dap``) and the
    bookkeeping (``param_count``, ``outcome``, ``rejection``,
    ``service_error``, ``reset_armed``, ``reset_armed_at``,
    ``_calc_status``).
    """
    state: dict[str, Any] = {
        "product": "",
        "scale_max": SCALE_DEFAULT,
        "param_count": 1,
        "outcome": None,
        "rejection": None,
        "service_error": False,
        "reset_armed": False,
        "reset_armed_at": 0.0,
        "_calc_status": None,
        "p0_name": "",
        "p0_weight": 1.0,
        "p0_fap": 1,
        "p0_sap": 1,
        "p0_dap": 1,
    }
    return state


def collect_raw(state: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble the documented raw schema from widget state.

    Assembly only (no math, no coercion): reads ``product``, ``scale_max``
    and the per-parameter keys in index order; produces exactly the schema
    ``validate`` expects — unknown keys are never added.
    """
    n = int(state["param_count"])
    parameters: list[dict[str, Any]] = []
    for i in range(n):
        parameters.append(
            {
                "name": state[f"p{i}_name"],
                "weight": state[f"p{i}_weight"],
                "scores": {group: state[f"p{i}_{group}"] for group in GROUPS},
            }
        )
    return {
        "product": state["product"],
        "scale_max": state["scale_max"],
        "parameters": parameters,
    }


def parse_field(field: str) -> dict[str, Any]:
    """Map a ``ValidationRejection.field`` path to a UI target (pure mapping).

    Returns ``{"scope", "index", "group", "summary_only"}`` where scope is
    one of ``product | scale | parameters | parameter | name | weight |
    scores | score | group_weights | global``. ``summary_only`` is True when
    the path has no renderable field target (global errors, internal group
    weights, unknown shapes). An index beyond the current parameter count is
    checked by the caller (graceful degradation: summary only, B-3).
    """
    if field == "product":
        return {"scope": "product", "index": None, "group": None, "summary_only": False}
    if field == "scale_max":
        return {"scope": "scale", "index": None, "group": None, "summary_only": False}
    if field == "parameters":
        return {"scope": "parameters", "index": None, "group": None, "summary_only": False}
    if field == "group_weights":
        return {"scope": "group_weights", "index": None, "group": None, "summary_only": True}
    match = _FIELD_RE.match(field)
    if not match:
        return {"scope": "global", "index": None, "group": None, "summary_only": True}
    index = int(match.group("i"))
    part = match.group("part")
    group = match.group("group")
    if part is None:
        return {"scope": "parameter", "index": index, "group": None, "summary_only": False}
    if part in ("name", "weight"):
        return {"scope": part, "index": index, "group": None, "summary_only": False}
    if group is None:
        return {"scope": "scores", "index": index, "group": None, "summary_only": False}
    return {"scope": "score", "index": index, "group": group, "summary_only": False}


def human_label(info: dict[str, Any]) -> str:
    """Translate a parsed field target to its normative human label
    (docs/UI_ARCHITECTURE.md §5 — pure presentation mapping)."""
    scope = info["scope"]
    index = info["index"]
    group = info["group"]
    if scope == "product":
        return "Product name"
    if scope == "scale":
        return "Scale maximum"
    if scope == "parameters":
        return "Parameters"
    if scope in ("parameter", "name", "weight", "scores", "score"):
        number = _display_number(index)
        if not number:
            return ""
        if scope == "parameter":
            return f"Parameter {number}"
        if scope == "name":
            return f"Name of parameter {number}"
        if scope == "weight":
            return f"Weight of parameter {number}"
        if scope == "scores":
            return f"Scores of parameter {number}"
        return (
            f"{GROUP_LABELS[group]} ({GROUP_SHORT[group]}) "
            f"score of parameter {number}"
        )
    if scope == "group_weights":
        return "Internal group weights"
    return ""


def fix_hint(code: str) -> str:
    """The fix-guidance line for a rejection code ("" = none)."""
    return FIX_HINTS.get(code, "")


def counter_text(n: int) -> str:
    """The parameter counter line ("3 of 100")."""
    return COPY["counter"].format(n=n, max=PARAMETER_MAX)
