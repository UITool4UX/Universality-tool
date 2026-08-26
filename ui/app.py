"""Universality Index Tool — UI band (Streamlit composition root).

Implements the four design contracts (2026-08-26): ``docs/DESIGN_SYSTEM.md``,
``docs/UI_ARCHITECTURE.md``, ``docs/UX_FLOW.md``, ``docs/ACCESSIBILITY.md``.

**No math in this module** (docs/UI_ARCHITECTURE.md §1): no formulas, no
tolerances, no sums, no rounding, no clamping, no coercion of user values.
Results are displayed only through ``universality.format_for_display``
(the single A6 location). The two permitted non-formatting operations
(flagged D-UI-5 / D-UI-9 in docs/UI_ARCHITECTURE.md §11) are:

- ``1.0 / n`` — on the explicit "Reset weights to 1/n" action only;
- ``max``/``min`` over the three already-computed group indices — for the
  gap card's sub-label only (comparisons, not arithmetic).

Safety (docs/UI_ARCHITECTURE.md §7): every user string rendered in an HTML
context is passed through ``html.escape``; ``unsafe_allow_html`` is used
only for static structure and escaped content; no CDNs, no network calls.

Error contract (``docs/validation-and-security.md``, error handling §3):
the controlled flows are ``ValidationRejection`` (gate) and ``ServiceError``
(application boundary). A **last-resort guard** in ``main()`` catches any
other exception that ever escapes the render path (a bug or a corrupted
session) and shows only the fixed generic error state — never the message,
class, frames, or source lines (no user-facing stack traces, §9 "Never").
Streamlit's ``RerunException`` (``st.rerun`` control flow) is re-raised,
never treated as a fault.

Run: ``streamlit run ui/app.py`` (binds 0.0.0.0; no host/origin allowlist).
"""

from __future__ import annotations

import base64
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
from ui import ui_model  # noqa: E402

_C = ui_model.COPY
_FONTS_DIR = Path(__file__).resolve().parent / "fonts"


# ---------------------------------------------------------------------------
# Static presentation layer (design tokens — DESIGN_SYSTEM.md)
# ---------------------------------------------------------------------------

def _font_faces() -> str:
    """@font-face rules for the Lora assets present in ``ui/fonts``
    (naming convention ``lora-{style}-{weight}.woff2``). With no assets the
    documented fallback stack applies (DESIGN_SYSTEM.md §3.1, D-UI-1)."""
    faces: list[str] = []
    for path in sorted(_FONTS_DIR.glob("lora-*.woff2")):
        parts = path.stem.split("-")
        if len(parts) != 3:
            continue
        _, style, weight = parts
        if style not in ("normal", "italic") or not weight.isdigit():
            continue
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        faces.append(
            "@font-face{font-family:'Lora';font-style:"
            f"{style};font-weight:{weight};font-display:swap;"
            f"src:url(data:font/woff2;base64,{encoded}) format('woff2');}}"
        )
    return "\n".join(faces)


_CSS = """
:root{
  --bg-paper:#F7F8FA; --bg-card:#FFFFFF; --bg-blue-wash:#EAF1FB; --bg-blue-block:#D7E4F7;
  --brand-600:#2563EB; --brand-700:#1D4ED8; --brand-800:#1E40AF; --brand-900:#172554;
  --grid-line:rgba(29,78,216,0.06);
  --ink:#111827; --ink-2:#4B5563; --ink-disabled:#9CA3AF;
  --err-700:#B91C1C; --err-600:#DC2626; --err-50:#FEF2F2;
  --ok-700:#15803D;
  --border:#D8DEE9; --r-sm:4px; --r-md:6px; --r-lg:7px;
  --serif-display:"Baskerville","Baskerville Old Face","Hoefler Text","Garamond","Libertine","Times New Roman",serif;
  --serif-body:"Lora","Iowan Old Style","Palatino",serif;
  --mono:"SFMono-Regular","Consolas","Liberation Mono",monospace;
}
html, body, [data-testid="stApp"], #stApp { background: var(--bg-paper); }
body, .stMarkdown, [data-testid="stMarkdownContainer"] {
  font-family: var(--serif-body); color: var(--ink);
}
/* Content column: paper width, graph-paper grid in the margins only (6%). */
.main .block-container, section[data-testid="stMainBlockContainer"] {
  max-width: 880px; margin: auto; padding: 2.5rem 1.5rem 3rem;
  background:
    linear-gradient(var(--grid-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-line) 1px, transparent 1px),
    var(--bg-paper);
  background-size: 24px 24px;
}
/* Typography scale (DESIGN_SYSTEM.md §3.2). */
h1 { font-family: var(--serif-display); font-size: 28px; line-height: 34px; font-weight: 600; margin: 0 0 4px 0; }
h2 { font-family: var(--serif-display); font-size: 21px; line-height: 30px; font-weight: 600;
     border-bottom: 1px solid var(--border); padding-bottom: 8px; margin: 8px 0 12px 0; }
h3 { font-family: var(--serif-body); font-size: 17px; line-height: 26px; font-weight: 600; }
.wordmark { font-family: var(--serif-display); font-size: 28px; line-height: 34px; font-weight: 600; color: var(--ink); }
.purpose { font-size: 16px; line-height: 26px; color: var(--ink-2); margin-bottom: 8px; }
.masthead-tag { font-size: 11.5px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-2); }
.masthead-rule { border: none; border-top: 1px solid var(--border); margin: 10px 0 4px 0; }
.caption, [data-testid="stMarkdownContainer"] p.caption { color: var(--ink-2); }
/* Inputs: default / focus / disabled states (DESIGN_SYSTEM.md §6.2). */
[data-testid="stTextInput"] > div, [data-testid="stNumberInput"] > div,
div[data-baseweb="select"] > div {
  border-radius: var(--r-sm) !important; border-color: var(--border) !important;
  background: var(--bg-card) !important;
}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {
  font-family: var(--serif-body) !important; font-size: 16px !important; color: var(--ink) !important;
}
[data-testid="stTextInput"] > div:focus-within, [data-testid="stNumberInput"] > div:focus-within,
[data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus {
  border-color: var(--brand-600) !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18) !important;
}
[data-testid="stTextInput"] input:disabled, [data-testid="stNumberInput"] input:disabled {
  background: #F3F4F6 !important; color: var(--ink-disabled) !important;
}
/* Buttons: baseline inventory of five (DESIGN_SYSTEM.md §6.1).
   Default kind renders as Secondary; Primary via [kind="primary"];
   Tertiary/Dashed via marker spans + :has (best-effort, documented
   fragility — UI_ARCHITECTURE.md §2). */
[data-testid="stButton"] button {
  border-radius: var(--r-sm) !important; font-family: var(--serif-body) !important;
  font-weight: 500 !important; border: 1px solid var(--brand-700) !important;
  background: var(--bg-card) !important; color: var(--brand-700) !important;
  box-shadow: none !important; transition: background 120ms ease;
}
[data-testid="stButton"] button:hover { background: #EFF4FC !important; }
[data-testid="stButton"] button[kind="primary"] {
  background: var(--brand-700) !important; color: #fff !important;
  border-color: var(--brand-700) !important; min-width: 180px;
}
[data-testid="stButton"] button[kind="primary"]:hover { background: var(--brand-800) !important; }
[data-testid="stButton"] button:disabled {
  background: #E5E7EB !important; color: var(--ink-disabled) !important;
  border-color: transparent !important; cursor: not-allowed;
}
div[data-testid="stMarkdown"]:has(span.btn-tertiary) + div[data-testid="stButton"] button {
  border-color: transparent !important; background: transparent !important; color: var(--ink-2) !important;
}
div[data-testid="stMarkdown"]:has(span.btn-tertiary) + div[data-testid="stButton"] button:hover {
  color: var(--brand-700) !important; background: transparent !important;
}
div[data-testid="stMarkdown"]:has(span.btn-tertiary-dashed) + div[data-testid="stButton"] button {
  border: 1px dashed #C6CFDD !important; background: transparent !important;
  color: var(--ink-2) !important; width: 100%;
}
/* Cards, panels, color blocking (DESIGN_SYSTEM.md §5). */
[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdown"] span.part-card) {
  border: 1px solid var(--border); border-radius: var(--r-md);
  background: var(--bg-card); padding: 20px; margin-bottom: 28px;
}
[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdown"] span.param-card) {
  border: 1px solid var(--border); border-radius: var(--r-md);
  background: var(--bg-card); padding: 16px; margin-bottom: 12px;
}
.card-title { font-size: 15px; font-weight: 600; color: var(--ink); }
[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdown"] span.part-results-success) {
  border-radius: var(--r-lg); background: var(--bg-blue-wash);
  border-top: 2px solid var(--brand-700); padding: 20px; margin-bottom: 28px;
}
[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdown"] span.part-results-stale) {
  border-radius: var(--r-lg); background: var(--bg-blue-wash);
  padding: 20px; margin-bottom: 28px; opacity: 0.6;
}
.placeholder-box {
  border: 1px dashed #C6CFDD; border-radius: var(--r-md); background: var(--bg-card);
  padding: 36px; text-align: center; color: var(--ink-2); font-style: italic; font-size: 14px;
}
/* Error & success elements (escaped HTML, DESIGN_SYSTEM.md §6.2/§6.3). */
.error-summary, .field-error {
  background: var(--err-50); border-left: 3px solid var(--err-600);
  border-radius: var(--r-md); padding: 12px 16px; margin: 8px 0;
  color: var(--err-700); font-size: 14px; line-height: 22px;
}
.error-summary { font-size: 15px; }
.error-summary .summary-where { color: var(--ink-2); margin-top: 4px; }
.field-error .fix-hint { color: var(--ink-2); }
.ok-caption { color: var(--ok-700); font-weight: 600; font-size: 14px; }
/* Results figures (Baskerville display numerals). */
.stat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--r-md); padding: 16px; }
.hero-figure { font-family: var(--serif-display); font-size: 48px; line-height: 56px; color: var(--ink); margin: 4px 0; }
.stat-figure { font-family: var(--serif-display); font-size: 26px; line-height: 34px; color: var(--ink); margin-top: 4px; }
.group-card { background: var(--bg-blue-block); border-radius: var(--r-md); padding: 16px; }
.micro-label { font-size: 11.5px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-2); }
/* Dataframe (parameter table). */
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: var(--r-md); }
[data-testid="stDataFrame"] th { background: var(--bg-blue-wash); font-family: var(--serif-body); }
/* Loading line, skip link, footer. */
.progress-line { height: 2px; width: 40%; background: var(--brand-700); opacity: 0.6; margin: 4px 0; }
.skip-link { position: absolute; left: -9999px; top: 0; z-index: 100; }
.skip-link:focus {
  left: 8px; top: 8px; background: var(--bg-card); color: var(--brand-700);
  padding: 10px 14px; border-radius: var(--r-sm); border: 1px solid var(--brand-600);
  font-family: var(--serif-body); font-size: 14px;
}
.footer-rule { border: none; border-top: 1px solid var(--border); margin-top: 32px; }
span[hidden] { display: none; }
@media (max-width: 720px) {
  .hero-figure { font-size: 44px; line-height: 52px; }
  h1, .wordmark { font-size: 24px; line-height: 30px; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; scroll-behavior: auto !important; animation: none !important; }
}
@media (prefers-contrast: more) {
  .purpose, .caption, [data-testid="stMarkdownContainer"] p, .micro-label, .masthead-tag { color: var(--ink) !important; }
}
/* --- Addendum: append inside the existing _CSS string in ui/app.py --- */

/* Forces native browser chrome (scrollbars, some pickers) to light,
   independent of OS preference — belt-and-braces alongside config.toml. */
:root { color-scheme: light; }

/* stNumberInput step (+/-) buttons: not covered by the existing
   [data-testid="stNumberInput"] > div rule, so they were still
   falling back to BaseWeb's dark button skin. */
[data-testid="stNumberInput"] button {
  background: var(--bg-card) !important;
  border-color: var(--border) !important;
  color: var(--brand-700) !important;
}
[data-testid="stNumberInput"] button:hover {
  background: var(--bg-blue-wash) !important;
}
[data-testid="stNumberInput"] button:disabled {
  color: var(--ink-disabled) !important;
}

/* st.slider track + thumb (BaseWeb slider is a separate component tree
   from the text/number inputs — needs its own selectors). */
div[data-baseweb="slider"] div[role="slider"] {
  background: var(--brand-700) !important;
  border-color: var(--bg-card) !important;
}
div[data-baseweb="slider"] > div > div:first-child {
  background: var(--border) !important;           /* track */
}
div[data-baseweb="slider"] > div > div:nth-child(2) {
  background: var(--brand-600) !important;         /* filled portion */
}

/* st.selectbox chevron + text color, same reasoning as text/number inputs. */
div[data-baseweb="select"] * { color: var(--ink) !important; }
div[data-baseweb="select"] svg { fill: var(--ink-2) !important; }
"""


def _style_block() -> str:
    return "<style>" + _font_faces() + _CSS + "</style>"


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
    evaluation, result = outcome.evaluation, outcome.result
    st.text(evaluation.product)  # plain text — never markdown (escape rule)
    st.caption(
        f"Scale 1–{evaluation.scale_max} · {len(evaluation.parameters)} parameters · "
        + _C["group_weights_note"].format(w=format_for_display(SIMPLE_MODE_GROUP_WEIGHTS[0]))
    )
    if st.session_state.get("_calc_status") == "done":
        st.markdown(f'<span class="ok-caption">{html.escape(_C["calculated"])}</span>', unsafe_allow_html=True)
    overall_col, fap_col, sap_col, dap_col, gap_col = st.columns([3, 1.2, 1.2, 1.2, 1.2])
    with overall_col:
        st.markdown(
            f'<div class="stat-card"><div class="micro-label">{html.escape(_C["overall_label"])}</div>'
            f'<div class="hero-figure">{html.escape(format_for_display(result.overall))}</div>'
            f'<div class="caption">{html.escape(_C["overall_caption"])}</div></div>',
            unsafe_allow_html=True,
        )
    group_values = (
        ("fap", result.group_indices.fap),
        ("sap", result.group_indices.sap),
        ("dap", result.group_indices.dap),
    )
    for (group, value), col in zip(group_values, (fap_col, sap_col, dap_col)):
        with col:
            st.markdown(
                f'<div class="group-card"><div class="micro-label">'
                f"{html.escape(ui_model.GROUP_SHORT[group])} · {html.escape(ui_model.GROUP_LABELS[group])}</div>"
                f'<div class="stat-figure">{html.escape(format_for_display(value))}</div></div>',
                unsafe_allow_html=True,
            )
    # Gap card (F4 output + max/min sub-label — D-UI-9, comparisons only).
    max_group = max(group_values, key=lambda item: item[1])[0]
    min_group = min(group_values, key=lambda item: item[1])[0]
    with gap_col:
        st.markdown(
            f'<div class="group-card"><div class="micro-label">{html.escape(_C["gap_label"])}</div>'
            f'<div class="stat-figure">{html.escape(format_for_display(result.group_gap))}</div>'
            f'<div class="caption">{html.escape(ui_model.GROUP_SHORT[max_group])} − '
            f'{html.escape(ui_model.GROUP_SHORT[min_group])}</div></div>',
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
    st.markdown(_style_block(), unsafe_allow_html=True)
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
