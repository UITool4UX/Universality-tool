"""
ui/design_system.py

Design-system layer for the Streamlit app — visual styling + reusable
presentation components (the index-v6 design reference). **Presentation-only**:

- No Streamlit import. The composition root ``ui/app.py`` injects the CSS
  (``st.markdown(inject_css(), unsafe_allow_html=True)``) and renders the
  returned HTML strings — the security audit (architecture.md §6) permits
  ``streamlit`` in ``ui/app.py`` only.
- No calculation logic. Every number that is *shown* is passed in as an
  already display-ready string produced by the single A6 location
  (``universality.services.format_for_display``); this module contains no
  fixed-point formatting and no rounding. The only raw numeric input is the
  0–1 ``arc_fraction`` of the ring gauge, which drives SVG arc geometry in
  browser-side CSS (``pathLength`` + ``calc()``) — no Python arithmetic,
  rounding, or clamping, and the fraction is never displayed as text.
- All user-derived strings (product names, labels, diagnostic rows) are
  ``html.escape``d inside the renderers, so a component can never inject
  markup through data (docs/UI_ARCHITECTURE.md §7 escape rule).

Usage in ui/app.py::

    from ui import design_system

    st.markdown(design_system.inject_css(), unsafe_allow_html=True)   # once
    ...
    st.markdown(design_system.render_ring_gauge(
        figure=overall_display,            # format_for_display(result.overall)
        tier=design_system.score_to_tier(result.overall),
        caption="(range 0.0000–1.0000)",   # fixed copy — never user input
        arc_fraction=result.overall,       # raw 0–1, geometry only
    ), unsafe_allow_html=True)
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

_FONTS_DIR = Path(__file__).resolve().parent / "fonts"


# ============================================================================
# DESIGN TOKENS + CSS
# Part A (top): restyles Streamlit's OWN widgets (data-testid / baseweb
#   selectors) so st.text_input, st.number_input, st.button, st.slider match
#   the reference exactly. Requires .streamlit/config.toml with base="light"
#   — without it these selectors fight Streamlit's dark widget skin.
# Part B (middle): the custom component classes (.card, .hero-visual,
#   .ring-*, .group-pin, …) used only by the render_* functions below via
#   unsafe_allow_html.
# Part C (bottom): application chrome (masthead, part cards, error/success
#   elements, results band, progress line, skip link, footer) — the same
#   marker-span :has() hooks the app has always used (documented
#   best-effort; degrades to neutral Streamlit styling).
#
# Fonts are local only (no CDN / no network): the @font-face rules below are
# emitted for self-hosted Lora woff2 assets in ui/fonts when present, and
# the reference stacks fall back to system faces otherwise.
# ============================================================================

CSS = """
:root{
  --paper:#F5F7FB; --surface:#FFFFFF; --wash:#EAF1FD; --wash-2:#DCE9FC;
  --ink:#0E1A30; --slate:#57647C; --slate-2:#93A0B8; --line:#E4E9F2;
  --signal:#2454E8; --signal-hover:#1C45C9; --signal-active:#1638A6; --signal-tint:#EAF0FE;
  --success:#178A5B; --success-bg:#E6F6EE; --success-line:#A7DEC1;
  --alert:#D0432E; --alert-bg:#FCEBE8; --alert-line:#F0B7AB;
  --amber:#B4791C; --amber-bg:#FBF2E0;
  --display:'Lora', Georgia, serif; --ui:'DM Sans', -apple-system, sans-serif;
  --r-card:18px; --r-card-lg:22px; --r-control:6px;
  color-scheme:light;
}

/* ---------------------------------------------------------------------- */
/* PART A — Streamlit native widget overrides                             */
/* ---------------------------------------------------------------------- */

html, body, [class*="css"]{ font-family: var(--ui); color: var(--slate); }

.stApp{
  background:
    radial-gradient(900px 500px at 8% -8%, var(--wash) 0%, transparent 60%),
    radial-gradient(800px 600px at 100% 10%, #EFF4FD 0%, transparent 55%),
    var(--paper);
  background-attachment: fixed;
}

.block-container{ max-width: 1600px; padding: 2.5rem 4rem 5rem; }
@media (max-width: 920px){ .block-container{ padding: 1.5rem 2rem 3rem; } }

h1, h2, h3, h4{ color: var(--ink); font-family: var(--ui); font-weight: 800; letter-spacing:-0.02em; }

/* Text / number inputs */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input{
  background: var(--paper) !important;
  border: 1.5px solid var(--line) !important;
  border-radius: var(--r-control) !important;
  color: var(--ink) !important;
  font-family: var(--ui) !important;
  font-weight: 500 !important;
  padding: 10px 12px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus{
  border-color: var(--signal) !important;
  box-shadow: 0 0 0 3px var(--signal-tint) !important;
}
[data-testid="stNumberInput"] button{
  background: var(--surface) !important;
  border-color: var(--line) !important;
  color: var(--signal) !important;
}
[data-testid="stNumberInput"] button:hover{ background: var(--signal-tint) !important; }
[data-testid="stNumberInput"] button:disabled{ color: var(--slate-2) !important; }

/* Slider */
div[data-baseweb="slider"] div[role="slider"]{ background: var(--signal) !important; border-color: #fff !important; }
div[data-baseweb="slider"] > div > div:nth-child(2){ background: var(--signal) !important; }

/* Select */
div[data-baseweb="select"] *{ color: var(--ink) !important; font-family: var(--ui) !important; }
div[data-baseweb="select"] svg{ fill: var(--slate-2) !important; }

/* Buttons — baseline renders as Primary (the reference's single accent);
   the app's five-button inventory is differentiated in Part C via the
   marker-span sibling hooks (best-effort, documented fragility). */
.stButton > button{
  font-family: var(--ui) !important; font-weight: 700 !important; font-size: 14px !important;
  border-radius: var(--r-control) !important; padding: 0.6rem 1.3rem !important;
  border: 1.5px solid var(--signal) !important; background: var(--signal) !important; color: #fff !important;
  box-shadow: 0 8px 20px -6px rgba(36,84,232,0.5) !important;
  transition: background 120ms ease, box-shadow 120ms ease !important;
}
.stButton > button:hover{ background: var(--signal-hover) !important; box-shadow: 0 10px 24px -6px rgba(36,84,232,0.6) !important; }
.stButton > button:active{ background: var(--signal-active) !important; }
.stButton > button:disabled{ opacity: 0.45 !important; box-shadow: none !important; }

/* Containers used as cards: st.container(border=True) */
[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius: var(--r-card) !important;
  border-color: var(--line) !important;
  box-shadow: 0 1px 2px rgba(9,20,52,0.04), 0 14px 32px -12px rgba(9,20,52,0.10) !important;
  background: var(--surface) !important;
}

/* Dataframe / table */
[data-testid="stDataFrame"]{ border-radius: var(--r-card) !important; overflow: hidden !important; border: 1px solid var(--line) !important; }
[data-testid="stDataFrame"] th{ background: var(--wash) !important; font-family: var(--ui) !important; }

/* ---------------------------------------------------------------------- */
/* PART B — Custom component classes (used by the render_* functions)     */
/* ---------------------------------------------------------------------- */

.card{ background: var(--surface); border-radius: var(--r-card); border: 1px solid var(--line);
  box-shadow: 0 1px 2px rgba(9,20,52,0.04), 0 14px 32px -12px rgba(9,20,52,0.10); }
.card__pad{ padding: 26px; }

.eyebrow{ display:inline-flex; align-items:center; gap:8px; font-size:12px; font-weight:700; color:var(--signal);
  background:var(--signal-tint); padding:6px 13px 6px 10px; border-radius:99px; margin-bottom:18px; }
.eyebrow .dot{ width:6px; height:6px; border-radius:50%; background:var(--signal); }

/* The hero title is a styled div, NOT an <h1>: the page's heading structure
   (masthead wordmark as the H1 role; Part I–III as H2) is owned by the app
   and must not gain a second level-1 heading (ACCESSIBILITY.md §2). */
.hero-title{ font-family: var(--ui); font-weight: 800; letter-spacing: -0.02em;
  font-size: clamp(30px, 4vw, 46px); line-height: 1.08; max-width: 15ch;
  color: var(--ink); margin-bottom: 16px; }
.hero-lede{ font-size:16px; color:var(--slate); max-width:52ch; margin-bottom:28px; font-weight:500; }

.hero-visual{
  border-radius: var(--r-card-lg);
  background: linear-gradient(135deg, #1B3FC4 0%, #2454E8 45%, #4E7BF2 100%);
  padding: 40px; box-shadow: 0 20px 50px -12px rgba(36,84,232,0.35);
}
.hero-visual__inner{ display:grid; grid-template-columns:1fr 1fr; gap:32px; align-items:center; }
.hero-visual__copy{ color:#fff; }
.hero-visual__copy .kicker{ font-size:11px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; opacity:0.75; margin-bottom:10px; }
.hero-visual__copy .figure{ font-family: var(--display); font-style: italic; font-weight:700; font-size:56px; line-height:1; }
.hero-visual__copy .figure small{ font-size:20px; font-style:normal; opacity:0.7; font-weight:500; }
.hero-visual__copy p{ font-size:13.5px; opacity:0.85; margin-top:10px; max-width:32ch; }
.mini-card{ background: rgba(255,255,255,0.97); border-radius:14px; padding:16px; box-shadow: 0 12px 30px rgba(9,20,52,0.25); }
.mini-card__row{ display:flex; justify-content:space-between; align-items:center; font-size:12.5px; padding:8px 0; border-bottom:1px solid var(--line); }
.mini-card__row:last-child{ border-bottom:none; }
.mini-card__row span{ color: var(--ink); font-weight: 500; }
.pill{ font-size:10.5px; font-weight:700; padding:3px 8px; border-radius:99px; }
.pill--good{ background: var(--success-bg); color: var(--success); }
.pill--mid{ background: var(--amber-bg); color: var(--amber); }
.pill--low{ background: var(--alert-bg); color: var(--alert); }
.pill--neutral{ background: var(--wash-2); color: var(--slate); }
@media (max-width:760px){ .hero-visual__inner{ grid-template-columns:1fr; } }

.ring-wrap{ position:relative; width:196px; height:196px; margin:0 auto; }
.ring-svg{ width:100%; height:100%; transform:rotate(-90deg); }
.ring-track{ fill:none; stroke:var(--wash); stroke-width:14; }
.ring-fill{ fill:none; stroke-width:14; stroke-linecap:round; }
.ring-fill--excellent{ stroke:var(--success); } .ring-fill--good{ stroke:var(--signal); }
.ring-fill--moderate{ stroke:var(--amber); } .ring-fill--poor{ stroke:var(--alert); }
.ring-center{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; }
.dial-tier{ display:inline-block; font-size:10.5px; font-weight:700; padding:4px 10px; border-radius:99px; margin-top:8px; }
.tier-good{ color:var(--signal); background:var(--signal-tint); }
.tier-excellent{ color:var(--success); background:var(--success-bg); }
.tier-moderate{ color:var(--amber); background:var(--amber-bg); }
.tier-poor{ color:var(--alert); background:var(--alert-bg); }
.dial-figure{ font-family: var(--display); font-style: italic; font-weight:700; font-size:38px; color:var(--ink); line-height:1; }
.dial-figure .pct{ font-size:14px; font-style:normal; color:var(--slate-2); font-weight:600; }
.dial-caption{ font-size:11px; color:var(--slate-2); margin-top:2px; font-weight:500; }

.group-readouts{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; padding:20px; }
.group-pin{ background:var(--wash); border-radius:12px; padding:16px 10px 14px; text-align:center;
  display:flex; flex-direction:column; gap:6px; align-items:center; }
.group-pin__label{ font-size:10px; font-weight:800; letter-spacing:0.04em; color:var(--slate); text-transform:uppercase; line-height:1; }
.group-pin__value{ font-family: var(--display); font-weight: 700; font-size:19px; color:var(--ink); line-height:1; }

.diag-title{ font-size:11.5px; font-weight:800; letter-spacing:0.05em; text-transform:uppercase; color:var(--alert); margin-bottom:12px; }
.diag-list{ margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:10px; }
.diag-list li{ font-size:12.5px; color:var(--slate); display:flex; justify-content:space-between; font-weight:500; }
.diag-list b{ color:var(--ink); font-weight:700; }

/* ---------------------------------------------------------------------- */
/* PART C — Application chrome (masthead, cards, errors, results band)    */
/* ---------------------------------------------------------------------- */

.wordmark{ font-family: var(--display); font-style: italic; font-weight: 700; font-size: 30px; line-height: 1.2; color: var(--ink); }
.purpose{ font-size: 15px; color: var(--slate); margin-top: 4px; }
.masthead-tag{ font-size:11px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; color:var(--slate-2); }
.masthead-rule{ border:none; border-top:1px solid var(--line); margin:14px 0 4px 0; }

/* Part cards and parameter cards: hidden marker spans set by the app are
   the :has() hooks (best-effort; degrades to neutral styling). */
[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdown"] span.part-card){
  border-radius: var(--r-card) !important; border: 1px solid var(--line) !important;
  background: var(--surface) !important;
  box-shadow: 0 1px 2px rgba(9,20,52,0.04), 0 14px 32px -12px rgba(9,20,52,0.10) !important;
  padding: 26px !important; margin-bottom: 28px !important;
}
[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdown"] span.param-card){
  border-radius: 14px !important; border: 1px solid var(--line) !important;
  background: var(--surface) !important; padding: 18px !important; margin-bottom: 14px !important;
}
.card-title{ font-size:15px; font-weight:700; color:var(--ink); letter-spacing:-0.01em; }

/* Results band (Part III): success carries the 2px signal top rule;
   stale results dim. */
[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdown"] span.part-results-success){
  border-radius: var(--r-card-lg) !important; border: 1px solid var(--line) !important;
  border-top: 2px solid var(--signal) !important; background: var(--surface) !important;
  box-shadow: 0 1px 2px rgba(9,20,52,0.04), 0 14px 32px -12px rgba(9,20,52,0.10) !important;
  padding: 26px !important; margin-bottom: 28px !important;
}
[data-testid="stVerticalBlock"]:has(> div[data-testid="stMarkdown"] span.part-results-stale){
  border-radius: var(--r-card-lg) !important; border: 1px solid var(--line) !important;
  border-top: 2px solid var(--slate-2) !important; background: var(--surface) !important;
  padding: 26px !important; margin-bottom: 28px !important; opacity: 0.6;
}

.placeholder-box{
  border:1.5px dashed var(--slate-2); border-radius:var(--r-card); background:var(--surface);
  padding:40px; text-align:center; color:var(--slate); font-style:italic; font-size:14px;
}

/* Error & success elements (all user data escaped by the app before
   interpolation — the verbatim gate message contract). */
.error-summary, .field-error{
  background: var(--alert-bg); border-left: 3px solid var(--alert);
  border-radius: 12px; padding: 14px 18px; margin: 8px 0;
  color: var(--alert); font-size: 14px; line-height: 1.5;
}
.error-summary{ font-size: 14.5px; }
.error-summary .summary-where{ color: var(--slate); margin-top: 4px; }
.field-error .fix-hint{ color: var(--slate); }
.ok-caption{ color: var(--success); font-weight: 700; font-size: 13px; }

/* Result figures (display face) and the group-gap card. */
.micro-label{ font-size:10.5px; font-weight:800; letter-spacing:0.08em; text-transform:uppercase; color:var(--slate); }
.stat-figure{ font-family:var(--display); font-style:italic; font-weight:700; font-size:30px; line-height:1.1; color:var(--ink); margin-top:4px; }
.group-card{ background:var(--wash); border-radius:14px; padding:18px; }

/* Button inventory (five kinds): the baseline above is Primary; the
   marker span emitted by the app just before each button selects the
   sibling button (best-effort, documented fragility). */
div[data-testid="stMarkdown"]:has(span.btn-secondary) + div[data-testid="stButton"] > button{
  background:#fff !important; color:var(--ink) !important; border-color:var(--line) !important;
  box-shadow: 0 1px 2px rgba(9,20,52,0.04) !important;
}
div[data-testid="stMarkdown"]:has(span.btn-secondary) + div[data-testid="stButton"] > button:hover{
  border-color:var(--signal) !important; color:var(--signal) !important; background:var(--signal-tint) !important;
}
div[data-testid="stMarkdown"]:has(span.btn-tertiary) + div[data-testid="stButton"] > button{
  background:transparent !important; border-color:transparent !important; color:var(--slate) !important;
  box-shadow:none !important;
}
div[data-testid="stMarkdown"]:has(span.btn-tertiary) + div[data-testid="stButton"] > button:hover{
  color:var(--signal) !important; background:var(--signal-tint) !important;
}
div[data-testid="stMarkdown"]:has(span.btn-tertiary-dashed) + div[data-testid="stButton"] > button{
  background:transparent !important; border:1.5px dashed var(--slate-2) !important;
  color:var(--slate) !important; box-shadow:none !important; width:100%;
}
div[data-testid="stMarkdown"]:has(span.btn-tertiary-dashed) + div[data-testid="stButton"] > button:hover{
  border-color:var(--signal) !important; color:var(--signal) !important;
}

/* Loading line, skip link, footer. */
.progress-line{ height:2px; width:40%; background:var(--signal); opacity:0.6; margin:4px 0; }
.skip-link{ position:absolute; left:-9999px; top:0; z-index:100; }
.skip-link:focus{
  left:8px; top:8px; background:var(--surface); color:var(--signal);
  padding:10px 14px; border-radius:var(--r-control); border:1.5px solid var(--signal);
  font-family:var(--ui); font-size:14px; font-weight:700;
}
.footer-rule{ border:none; border-top:1px solid var(--line); margin-top:32px; }
span[hidden]{ display:none; }

@media (max-width:720px){
  .hero-visual__copy .figure{ font-size:44px; }
  .wordmark{ font-size:24px; line-height:30px; }
}
@media (prefers-reduced-motion: reduce){
  *{ transition:none !important; scroll-behavior:auto !important; animation:none !important; }
}
@media (prefers-contrast: more){
  .purpose, .caption, [data-testid="stMarkdownContainer"] p, .micro-label, .masthead-tag,
  .dial-caption, .hero-lede, .diag-list li{ color: var(--ink) !important; }
}
"""


def _font_faces() -> str:
    """@font-face rules for the Lora assets present in ``ui/fonts``
    (naming convention ``lora-{style}-{weight}.woff2``), base64-embedded —
    self-hosted only, no CDN. With no assets the documented fallback
    stacks apply (DESIGN_SYSTEM.md §3.1, D-UI-1)."""
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


def inject_css() -> str:
    """The single ``<style>`` block (self-hosted font faces + the full
    stylesheet). Call once, near the top of ui/app.py, before rendering
    any widgets::

        st.markdown(design_system.inject_css(), unsafe_allow_html=True)
    """
    return "<style>" + _font_faces() + CSS + "</style>"


# ============================================================================
# COMPONENT RENDERERS
# Each returns an HTML string for st.markdown(..., unsafe_allow_html=True).
# Pure presentation — pass in already-computed values from your
# universality.evaluate() result (displayed numbers pre-formatted by
# format_for_display); nothing here does math or formatting.
# ============================================================================

_TIER_LABELS = {
    "excellent": "Excellent fit",
    "good": "Good fit",
    "moderate": "Moderate fit",
    "poor": "Poor fit",
}

#: Display-only tier → pill color mapping (presentation semantics).
_TIER_PILLS = {
    "excellent": "pill--good",
    "good": "pill--good",
    "moderate": "pill--mid",
    "poor": "pill--low",
}


def score_to_tier(score: float) -> str:
    """Pure display mapping (comparisons only — the same class of
    operation the gap card's max/min sub-label uses, D-UI-9). Mirrors the
    reference's tier thresholds; kept here only so components have a
    fallback if the caller does not pass a tier explicitly."""
    if score >= 0.8:
        return "excellent"
    if score >= 0.6:
        return "good"
    if score >= 0.4:
        return "moderate"
    return "poor"


def tier_label(tier: str) -> str:
    """The human label for a display tier (neutral when unknown)."""
    return _TIER_LABELS.get(tier, "")


def tier_pill_class(score: float) -> str:
    """Display-only mapping: score → pill CSS class (tier colors)."""
    return _TIER_PILLS[score_to_tier(score)]


def render_hero(
    eyebrow: str,
    title: str,
    lede: str,
    figure: str,
    figure_caption: str,
    mini_rows: list[tuple[str, str, str]],
) -> str:
    """The live-readout banner. ``figure`` is the already-formatted overall
    index string; ``mini_rows`` is a list of ``(label, value, pill_class)``
    tuples where ``value`` is an already-formatted display string (e.g. the
    three group indices via format_for_display, plus the group gap). All
    string arguments are escaped. **Never pass user input here** — the app's
    pinned contract renders user strings (product name, parameter names)
    only via st.text / st.dataframe, never in an HTML context; the title,
    lede, and caption are fixed copy or formatted numbers."""
    rows_html = "".join(
        f'<div class="mini-card__row"><span>{html.escape(label)}</span>'
        f'<span class="pill {html.escape(pill_class)}">{html.escape(value)}</span></div>'
        for label, value, pill_class in mini_rows
    )
    return f"""
    <div class="eyebrow"><span class="dot"></span>{html.escape(eyebrow)}</div>
    <div class="hero-title">{html.escape(title)}</div>
    <p class="hero-lede">{html.escape(lede)}</p>
    <div class="hero-visual">
      <div class="hero-visual__inner">
        <div class="hero-visual__copy">
          <div class="kicker">Live readout</div>
          <div class="figure">{html.escape(figure)}<small>/ 1.00</small></div>
          <p>{html.escape(figure_caption)}</p>
        </div>
        <div class="mini-card">{rows_html}</div>
      </div>
    </div>
    """


def render_ring_gauge(figure: str, tier: str, caption: str, arc_fraction: float) -> str:
    """The ring-gauge dial. ``figure`` is the already-formatted index string
    (format_for_display); ``caption`` is fixed copy below the dial (never
    user input — see the renderers' contract); ``arc_fraction`` is the raw
    0–1 index value used **for SVG arc geometry only** — it reaches the
    browser as a CSS custom property and the arc length is computed by CSS
    ``calc()`` (pathLength normalization), so no Python arithmetic,
    rounding, or clamping touches it. A value in the documented tolerance
    band (slightly above 1) simply renders a full arc — faithful,
    unclamped."""
    label = _TIER_LABELS.get(tier, "")
    return f"""
    <div class="card"><div class="card__pad" style="text-align:center;">
      <div class="ring-wrap">
        <svg class="ring-svg" viewBox="0 0 200 200" aria-hidden="true">
          <circle class="ring-track" cx="100" cy="100" r="86" pathLength="100"/>
          <circle class="ring-fill ring-fill--{html.escape(tier)}" cx="100" cy="100" r="86"
                  pathLength="100"
                  style="--arc:{arc_fraction};stroke-dasharray:100;stroke-dashoffset:calc(100 - var(--arc) * 100)"/>
        </svg>
        <div class="ring-center">
          <div class="dial-figure">{html.escape(figure)}<span class="pct">/ 1.00</span></div>
          <div class="dial-caption">Universality Index</div>
          <span class="dial-tier tier-{html.escape(tier)}">{html.escape(label)}</span>
        </div>
      </div>
      <div class="dial-caption" style="margin-top:14px;">{html.escape(caption)}</div>
    </div></div>
    """


def render_group_pins(fap: str, sap: str, dap: str) -> str:
    """The three group-index readouts. Values are already-formatted display
    strings (format_for_display)."""
    return f"""
    <div class="card"><div class="group-readouts">
      <div class="group-pin"><div class="group-pin__label">FAP</div><div class="group-pin__value">{html.escape(fap)}</div></div>
      <div class="group-pin"><div class="group-pin__label">SAP</div><div class="group-pin__value">{html.escape(sap)}</div></div>
      <div class="group-pin"><div class="group-pin__label">DAP</div><div class="group-pin__value">{html.escape(dap)}</div></div>
    </div></div>
    """


def render_diagnostics(items: list[tuple[str, str]]) -> str:
    """The "Needs attention" card. ``items`` is a list of
    ``(left_label, right_value)`` tuples of plain strings (e.g. the widest
    user-group gap with its max–min groups and formatted value); every
    string is escaped."""
    list_html = "".join(f"<li>{html.escape(left)} <b>{html.escape(right)}</b></li>" for left, right in items)
    return f"""
    <div class="card"><div class="card__pad">
      <div class="diag-title">Needs attention</div>
      <ul class="diag-list">{list_html}</ul>
    </div></div>
    """
