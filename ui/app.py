"""Universality Index Tool — UI band (Streamlit composition root).

Implements the four design contracts (2026-08-26): ``docs/DESIGN_SYSTEM.md``,
``docs/UI_ARCHITECTURE.md``, ``docs/UX_FLOW.md``, ``docs/ACCESSIBILITY.md``.
The visual styling and the index-v6 result components (hero live readout,
ring gauge, group pins, diagnostics) come from ``ui/design_system.py``
(2026-08-28, presentation-only — see that module's contract).

**No math in this module** (docs/UI_ARCHITECTURE.md §1): no formulas, no
tolerances, no sums, no rounding, no clamping, no coercion of user values.
Results are displayed only through ``universality.format_for_display``
(the single A6 location). The two permitted non-formatting operations
(flagged D-UI-5 / D-UI-9 in docs/UI_ARCHITECTURE.md §11) are:

- ``1.0 / n`` — on the explicit "Reset weights to 1/n" action only;
- ``max``/``min`` over the three already-computed group indices — for the
  gap card's sub-label only (comparisons, not arithmetic). The gap
  diagnostics row reuses exactly that ordering read.

Safety (docs/UI_ARCHITECTURE.md §7): every static string rendered in an
HTML context is passed through ``html.escape``; ``unsafe_allow_html`` is
used only for static structure and escaped content; no CDNs, no network
calls. **User input (product name, parameter names) never enters an HTML
context at all** — it renders only via ``st.text`` / ``st.dataframe``
(framework-escaped / plain), pinned by the hostile-input AppTest — so the
index-v6 components are fed fixed copy and ``format_for_display`` strings
only (the design-system renderers escape every string argument as
defense-in-depth).

Error contract (``docs/validation-and-security.md``, error handling §3):
the controlled flows are ``ValidationRejection`` (gate) and ``ServiceError``
(application boundary). A **last-resort guard** in ``main()`` catches any
other exception that ever escapes the render path (a bug or a corrupted
session) and shows only the fixed generic error state — never the message,
class, frames, or source lines (no user-facing stack traces, §9 "Never").
Streamlit's ``RerunException`` (``st.rerun``) is re-raised,
never treated as a fault.

Run: ``streamlit run ui/app.py`` (binds 0.0.0.0; no host/origin allowlist).
"""

from __future__ import annotations

import html
import re
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402  (framework; contractually the only one)
from streamlit.runtime.scriptrunner import RerunException  # noqa: E402  (st.rerun control flow)

from universality import (  # noqa: E402  (public API only)
    PARAMETER_MAX,
    SCALE_MAX,
    SCALE_MIN,
    SIMPLE_MODE_GROUP_WEIGHTS,
    ServiceError,
    ValidationRejection,
    evaluate,
    format_for_display,
)
from ui import design_system  # noqa: E402  (presentation-only, no Streamlit)
from ui import ui_model  # noqa: E402

_C = ui_model.COPY

#: Fixed presentation copy for the index-v6 hero banner (the framework
#: attribution mirrors the footer_a7 method line). The hero never carries
#: user input: the product name renders only via st.text above it (the
#: pinned hostile-input contract — user strings never enter an HTML
#: context).
_HERO_EYEBROW = "Simplified Singh & Tandon framework"
_HERO_TITLE = "Your universality index"


# ---------------------------------------------------------------------------
# Static presentation layer hooks (marker spans for :has() container styling
# — design_system.py Part C; documented best-effort, degrades to neutral
# Streamlit styling)
# ---------------------------------------------------------------------------

def _marker(css_class: str) -> None:
    """A hidden marker span: the :has() hook for container/button styling
    (documented best-effort; degrades to neutral Streamlit styling)."""
    st.markdown(f'<span class="{css_class}" hidden></span>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

_PARAM_KEYS = ("name", "weight", "fap", "sap", "dap")


def _seed_parameter(index: int, *, weight: float) -> None:
    """Seed the widget keys of a new parameter card (visible defaults)."""
    st.session_state[f"p{index}_name"] = ""
    st.session_state[f"p{index}_weight"] = weight
    st.session_state[f"p{index}_fap"] = 1
    st.session_state[f"p{index}_sap"] = 1
    st.session_state[f"p{index}_dap"] = 1


def _remove_parameter(index: int, count: int) -> None:
    """Delete card ``index`` and re-key the rest (no value is modified)."""
    ss = st.session_state
    for key in _PARAM_KEYS:
        for j in range(index, count - 1):
            ss[f"p{j}_{key}"] = ss[f"p{j + 1}_{key}"]
        del ss[f"p{count - 1}_{key}"]
    ss["param_count"] = count - 1


def _reset_all() -> None:
    """Two-click Reset: clear every entered value back to fresh state."""
    ss = st.session_state
    for key in [k for k in list(ss.keys()) if re.match(r"^p\d+_(name|weight|fap|sap|dap)$", k)]:
        del ss[key]
    ss.update(ui_model.fresh_state())


# ---------------------------------------------------------------------------
# Error rendering (validation feedback — UX_FLOW.md §6)
# ---------------------------------------------------------------------------

def _inline_error(path: str) -> None:
    """Render the gate's inline error directly under a field, when the
    current rejection targets it. Verbatim message + translated label
    (what/where) + fix hint (how). All user data escaped."""
    rejection = st.session_state["rejection"]
    if rejection is None or rejection.field != path:
        return
    info = ui_model.parse_field(rejection.field)
    label = ui_model.human_label(info)
    if info["summary_only"] or (
        info["scope"] in ("name", "weight", "scores", "score", "parameter")
        and (info["index"] is None or info["index"] >= st.session_state["param_count"])
    ):
        return  # out-of-range index: summary panel only (B-3)
    label_html = f"<strong>{html.escape(label)}.</strong> " if label else ""
    hint = ui_model.fix_hint(rejection.code)
    hint_html = f'<span class="fix-hint"> How to fix: {html.escape(hint)}</span>' if hint else ""
    st.markdown(
        f'<div class="field-error" role="alert">{label_html}'
        f"{html.escape(str(rejection.message))}{hint_html}</div>",
        unsafe_allow_html=True,
    )


def _error_summary(part: str) -> None:
    """The error summary panel at the top of the affected part
    (role=alert; verbatim message; where; how)."""
    rejection = st.session_state["rejection"]
    if st.session_state["service_error"]:
        # Global failure (no field target): the single panel lives in
        # Part II, next to the Calculate action (UX_FLOW.md E5).
        if part != "part2":
            return
        st.markdown(
            f'<div class="error-summary" role="alert"><strong>'
            f"{html.escape(_C['error_title'])}</strong><br>"
            f"{html.escape(ServiceError().message)} "
            f"{html.escape(ui_model.fix_hint('V-UNEXPECTED'))}</div>",
            unsafe_allow_html=True,
        )
        return
    if rejection is None:
        return
    info = ui_model.parse_field(rejection.field)
    label = ui_model.human_label(info)
    # Placement (UX_FLOW.md): Part I for product/scale; otherwise Part II.
    target = "part1" if info["scope"] in ("product", "scale") else "part2"
    if target != part:
        return
    where_html = f'<div class="summary-where">Where: {html.escape(label)}</div>' if label else ""
    hint = ui_model.fix_hint(rejection.code)
    hint_html = f'<div class="summary-where">How to fix: {html.escape(hint)}</div>' if hint else ""
    st.markdown(
        f'<div class="error-summary" role="alert"><strong>'
        f"{html.escape(_C['error_title'])}</strong><br>"
        f"{html.escape(str(rejection.message))}{where_html}{hint_html}</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sections (page map — UX_FLOW.md §2)
# ---------------------------------------------------------------------------

def render_masthead() -> None:
    ss = st.session_state
    st.markdown(f'<a class="skip-link" href="#calculate-anchor">{html.escape(_C["skip_link"])}</a>', unsafe_allow_html=True)
    left, right = st.columns([5, 1], vertical_alignment="center")
    with left:
        st.markdown(
            f'<div class="wordmark">{html.escape(_C["wordmark"])}</div>'
            f'<div class="purpose">{html.escape(_C["purpose"])}</div>',
            unsafe_allow_html=True,
        )
    with right:
        _marker("btn-secondary")
        reset_label = _C["reset_armed"] if ss["reset_armed"] else _C["reset"]
        if st.button(reset_label, key="reset_masthead"):
            if ss["reset_armed"]:
                _reset_all()
                st.rerun()  # display the fresh state in this interaction
            else:
                ss["reset_armed"] = True
                ss["reset_armed_at"] = time.monotonic()
                # The label was computed before the click, so without a
                # re-run the armed ("Confirm reset …") label would only
                # appear on the next interaction (same pattern as Add/Remove).
                st.rerun()
    st.markdown(
        f'<div class="masthead-tag">{html.escape(_C["tag"])}</div><hr class="masthead-rule">',
        unsafe_allow_html=True,
    )


def render_part1() -> None:
    ss = st.session_state
    with st.container():
        _marker("part-card")
        st.markdown(f"<h2>{html.escape(_C['part1_title'])}</h2>", unsafe_allow_html=True)
        _error_summary("part1")
        left, right = st.columns([3, 2])
        with left:
            st.text_input(
                _C["product_label"],
                key="product",
                placeholder=_C["product_placeholder"],
            )
            _inline_error("product")
        with right:
            st.number_input(
                _C["scale_label"],
                min_value=SCALE_MIN,
                max_value=SCALE_MAX,
                step=1,
                key="scale_max",
            )
            _inline_error("scale_max")
            st.caption(_C["scale_caption"])
        st.caption(_C["group_weights_note"].format(
            w=format_for_display(SIMPLE_MODE_GROUP_WEIGHTS[0])
        ))


def _render_parameter_card(index: int, count: int) -> None:
    ss = st.session_state
    n = index + 1
    with st.container():
        _marker("param-card")
        head, rm = st.columns([6, 1], vertical_alignment="bottom")
        with head:
            st.markdown(f'<span class="card-title">Parameter {n}</span>', unsafe_allow_html=True)
            if index == 0:
                st.caption(_C["legend"])
        with rm:
            _marker("btn-tertiary")
            if st.button(_C["remove_label"].format(n=n), key=f"remove_{index}", disabled=(count <= 1)):
                _remove_parameter(index, count)
                st.rerun()
        st.text_input(
            _C["name_label"].format(n=n),
            key=f"p{index}_name",
            placeholder=_C["name_placeholder"],
        )
        _inline_error(f"parameters[{index}].name")
        weight_col, *score_cols = st.columns([2, 1, 1, 1])
        with weight_col:
            st.number_input(
                _C["weight_label"].format(n=n),
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                key=f"p{index}_weight",
                format="%.4f",
            )
            _inline_error(f"parameters[{index}].weight")
            if index == 0:
                st.caption(_C["weight_caption"])
        for group, col in zip(ui_model.GROUPS, score_cols):
            with col:
                # Convenience bound: the absolute scale ceiling (100), NOT
                # the current scale — Streamlit clamps stored values that
                # fall outside a number_input's bounds, which would silently
                # modify user data (docs/UI_ARCHITECTURE.md §4 forbids that).
                # The validation gate remains the authority: an orphaned
                # score surfaces as a V4 error on exactly that field (E3).
                st.number_input(
                    _C["score_label"].format(short=ui_model.GROUP_SHORT[group], n=n),
                    min_value=1,
                    max_value=SCALE_MAX,
                    step=1,
                    key=f"p{index}_{group}",
                )
                _inline_error(f"parameters[{index}].scores.{group}")


def render_part2() -> None:
    ss = st.session_state
    count = ss["param_count"]
    with st.container():
        _marker("part-card")
        st.markdown(f"<h2>{html.escape(_C['part2_title'])}</h2>", unsafe_allow_html=True)
        _error_summary("part2")
        head, actions = st.columns([5, 2])
        with head:
            st.caption(ui_model.counter_text(count))
        with actions:
            _marker("btn-tertiary")
            if st.button(_C["reset_weights"], key="reset_weights"):
                equal_weight = 1.0 / count  # D-UI-5 — the permitted division
                for i in range(count):
                    st.session_state[f"p{i}_weight"] = equal_weight
                st.rerun()  # display the new weight values in this interaction
        for i in range(count):
            _render_parameter_card(i, count)
        if count >= PARAMETER_MAX:
            st.caption(_C["add_disabled_caption"])
        _marker("btn-tertiary-dashed")
        if st.button(_C["add"], key="add_param", disabled=(count >= PARAMETER_MAX), width="stretch"):
            _seed_parameter(count, weight=0.0)  # D-UI-5: never redistribute
            ss["param_count"] = count + 1
            st.rerun()  # render the new card in this interaction
        # Calculate (the single primary action).
        st.markdown('<span id="calculate-anchor"></span>', unsafe_allow_html=True)
        if st.button(_C["calculate"], key="calculate", type="primary"):
            _run_calculation()
        status = ss.get("_calc_status")
        if status == "calculating":
            st.markdown('<div class="progress-line" aria-hidden="true"></div>', unsafe_allow_html=True)
            st.caption(_C["calculating"])


def _run_calculation() -> None:
    """Calculate click: collect (assembly only) -> evaluate -> store the
    controlled outcome or the controlled rejection (UX_FLOW.md §3)."""
    ss = st.session_state
    ss["reset_armed"] = False
    raw = ui_model.collect_raw(ss)
    ss["_calc_status"] = "calculating"
    try:
        ss["outcome"] = evaluate(raw)
        ss["rejection"] = None
        ss["service_error"] = False
        ss["_calc_status"] = "done"
    except ValidationRejection as rejection:
        ss["rejection"] = rejection  # previous outcome stays (dimmed)
        ss["service_error"] = False
        ss["_calc_status"] = "error"
    except ServiceError:
        ss["rejection"] = None
        ss["service_error"] = True
        ss["_calc_status"] = "error"
    # The error summary and inline errors render above this button in script
    # order, so the stored outcome/rejection would otherwise only appear on
    # the next interaction. Re-run so the result of THIS Calculate click is
    # what the user sees (same pattern as Add/Remove).
    st.rerun()


def _render_results(outcome) -> None:
    """Part III body: the index-v6 components, wired to THIS outcome.

    Every displayed number is ``format_for_display`` (single A6 location);
    the components receive display-ready strings (plus the raw 0–1 index
    for the ring-gauge arc geometry only). The gap's max/min sub-label is
    the D-UI-9 ordering read (comparisons, no arithmetic)."""
    evaluation, result = outcome.evaluation, outcome.result
    st.text(evaluation.product)  # plain text — never markdown (escape rule)
    st.caption(
        f"Scale 1–{evaluation.scale_max} · {len(evaluation.parameters)} parameters · "
        + _C["group_weights_note"].format(w=format_for_display(SIMPLE_MODE_GROUP_WEIGHTS[0]))
    )
    if st.session_state.get("_calc_status") == "done":
        st.markdown(f'<span class="ok-caption">{html.escape(_C["calculated"])}</span>', unsafe_allow_html=True)

    overall_display = format_for_display(result.overall)
    group_values = (
        ("fap", result.group_indices.fap),
        ("sap", result.group_indices.sap),
        ("dap", result.group_indices.dap),
    )
    gap_display = format_for_display(result.group_gap)
    # Gap ordering read (D-UI-9 — comparisons over already-computed values).
    max_group = max(group_values, key=lambda item: item[1])[0]
    min_group = min(group_values, key=lambda item: item[1])[0]
    gap_shorts = f"{ui_model.GROUP_SHORT[max_group]} − {ui_model.GROUP_SHORT[min_group]}"

    # Live readout banner: overall figure + the three group indices + the
    # user-group gap, all from this outcome. The banner carries no user
    # input — the product name is the plain st.text line above (pinned
    # hostile-input contract).
    mini_rows = [
        (
            f"{ui_model.GROUP_SHORT[group]} · {ui_model.GROUP_LABELS[group]}",
            format_for_display(value),
            design_system.tier_pill_class(value),
        )
        for group, value in group_values
    ]
    mini_rows.append(("User-group gap", gap_display, "pill--neutral"))
    overall_tier = design_system.score_to_tier(result.overall)
    st.markdown(
        design_system.render_hero(
            eyebrow=_HERO_EYEBROW,
            title=_HERO_TITLE,
            lede=(
                f"Scale 1–{evaluation.scale_max} · {len(evaluation.parameters)} parameters · "
                f"Simple Mode group weights {format_for_display(SIMPLE_MODE_GROUP_WEIGHTS[0])} each"
            ),
            figure=overall_display,
            figure_caption=f"{design_system.tier_label(overall_tier)}.",
            mini_rows=mini_rows,
        ),
        unsafe_allow_html=True,
    )

    overall_col, gap_col = st.columns([3, 2], vertical_alignment="center")
    with overall_col:
        st.markdown(
            f'<div class="micro-label" style="text-align:center">{html.escape(_C["overall_label"])}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            design_system.render_ring_gauge(
                figure=overall_display,
                tier=overall_tier,
                caption=_C["overall_caption"],
                arc_fraction=result.overall,
            ),
            unsafe_allow_html=True,
        )
    # Gap card (F4 output + max/min sub-label — D-UI-9, comparisons only).
    with gap_col:
        st.markdown(
            f'<div class="group-card" style="text-align:center">'
            f'<div class="micro-label">{html.escape(_C["gap_label"])}</div>'
            f'<div class="stat-figure">{html.escape(gap_display)}</div>'
            f'<div class="caption">{html.escape(gap_shorts)}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        design_system.render_group_pins(
            format_for_display(result.group_indices.fap),
            format_for_display(result.group_indices.sap),
            format_for_display(result.group_indices.dap),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(f"<h3>{html.escape(_C['per_param_title'])}</h3>", unsafe_allow_html=True)
    st.caption(_C["table_caption"])
    rows = []
    for parameter in result.parameters:
        rows.append(
            {
                "Parameter": parameter.name,
                "Weight": format_for_display(parameter.weight.value),
                "FAP": format_for_display(parameter.normalized.fap),
                "SAP": format_for_display(parameter.normalized.sap),
                "DAP": format_for_display(parameter.normalized.dap),
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)
    with st.expander(_C["table2_title"]):
        st.caption(_C["table2_caption"])
        contribution_rows = []
        for parameter in result.parameters:
            contribution_rows.append(
                {
                    "Parameter": parameter.name,
                    "Weight": format_for_display(parameter.weight.value),
                    "FAP": format_for_display(parameter.contributions.fap),
                    "SAP": format_for_display(parameter.contributions.sap),
                    "DAP": format_for_display(parameter.contributions.dap),
                }
            )
        st.dataframe(contribution_rows, width="stretch", hide_index=True)
    st.caption(_C["a6_note"])
    # Diagnostics: the widest user-group gap, from this outcome only
    # (D-UI-9 ordering read + the F4 gap value; no new computation).
    st.markdown(
        design_system.render_diagnostics(
            [
                (
                    "Widest user-group gap",
                    f"{ui_model.GROUP_SHORT[max_group]}–{ui_model.GROUP_SHORT[min_group]} · {gap_display}",
                )
            ]
        ),
        unsafe_allow_html=True,
    )


def render_part3() -> None:
    ss = st.session_state
    outcome = ss["outcome"]
    if outcome is None:
        st.markdown(
            f'<div class="placeholder-box">{html.escape(_C["results_placeholder"])}</div>',
            unsafe_allow_html=True,
        )
        return
    stale = ss["rejection"] is not None or ss["service_error"]
    marker_class = "part-results-stale" if stale else "part-results-success"
    with st.container():
        _marker(marker_class)
        st.markdown(f"<h2>{html.escape(_C['part3_title'])}</h2>", unsafe_allow_html=True)
        if stale:
            st.caption(_C["stale"])
        _render_results(outcome)


def render_footer() -> None:
    st.markdown('<hr class="footer-rule">', unsafe_allow_html=True)
    st.caption(_C["footer_a4"])
    st.caption(_C["footer_a7"])
    st.caption(_C["footer_local"])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _render_unexpected() -> None:
    """Last-resort guard (error contract, ``docs/validation-and-security.md``).

    An exception that escapes the controlled flows (``ValidationRejection`` /
    ``ServiceError``) is an internal bug or a corrupted session. It is never
    displayed: no message, no class name, no frames, no source lines — only
    the fixed generic error state (E5). The handler in ``main()``
    intentionally does not bind the exception object, so nothing of it can
    reach the page. (Redacted logging is owned by ``universality.
    diagnostics``, Application band — the UI may import the package public
    API only, ``docs/architecture.md`` §6; that observability trade-off is
    recorded in the 2026-08-26 security-audit changelog entry.)
    """
    ss = st.session_state
    ss["service_error"] = True
    ss["rejection"] = None
    ss["_calc_status"] = "error"
    st.markdown(
        f'<div class="error-summary" role="alert"><strong>'
        f"{html.escape(_C['error_title'])}</strong><br>"
        f"{html.escape(ServiceError().message)} "
        f"{html.escape(ui_model.fix_hint('V-UNEXPECTED'))}</div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title=_C["page_title"],
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(design_system.inject_css(), unsafe_allow_html=True)
    if "param_count" not in st.session_state:
        st.session_state.update(ui_model.fresh_state())
    # Two-click Reset: auto-disarm after 5 seconds (presentation timing only).
    # .get() keeps a corrupted session (flag without timestamp) from raising
    # a KeyError on every run — such a state simply disarms the Reset.
    if st.session_state.get("reset_armed") and time.monotonic() - st.session_state.get("reset_armed_at", 0.0) > 5.0:
        st.session_state["reset_armed"] = False
    try:
        render_masthead()
        render_part1()
        render_part2()
        render_part3()
        render_footer()
    except RerunException:
        raise  # st.rerun() control flow — never a fault
    except Exception:
        # Deliberately not bound: nothing of the exception may be rendered.
        _render_unexpected()


main()
