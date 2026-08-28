"""
ui/design_system.py

Design-system layer for the Streamlit app — CSS + component renderers only.
Contains NO calculation logic. Safe to edit freely without touching
universality/ or the evaluate() contract in ui/ui_model.py.

Usage in ui/app.py:

    from ui.design_system import inject_css, render_ring_gauge, render_group_pins, render_diagnostics, render_hero

    inject_css()                      # once, near the top of the script
    st.markdown(render_hero(...), unsafe_allow_html=True)
    ...
    st.markdown(render_ring_gauge(score=0.72, tier="good", label="Good fit",
                                   product_name="CampusGo"), unsafe_allow_html=True)
"""

import streamlit as st

# ============================================================================
# DESIGN TOKENS + CSS
# Part A (top): restyles Streamlit's OWN widgets (data-testid / baseweb
#   selectors) so st.text_input, st.number_input, st.button, st.slider match
#   the reference exactly. Requires .streamlit/config.toml with base="light"
#   — without it these selectors fight Streamlit's dark widget skin.
# Part B (bottom): the custom component classes (.card, .ring-*, .group-pin,
#   etc.) used only by the render_* functions below via unsafe_allow_html.
# ============================================================================

CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800;1,9..40,500&family=Lora:ital,wght@0,600;0,700;1,600&display=swap');

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

/* Slider */
div[data-baseweb="slider"] div[role="slider"]{ background: var(--signal) !important; border-color: #fff !important; }
div[data-baseweb="slider"] > div > div:nth-child(2){ background: var(--signal) !important; }

/* Select */
div[data-baseweb="select"] *{ color: var(--ink) !important; font-family: var(--ui) !important; }

/* Buttons */
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

/* Secondary-style button: wrap the st.button in a container with this class
   e.g. st.markdown('<div class="btn-secondary-zone">', unsafe_allow_html=True) around it */
.btn-secondary-zone .stButton > button{
  background: #fff !important; color: var(--ink) !important; border-color: var(--line) !important;
  box-shadow: 0 1px 2px rgba(9,20,52,0.04) !important;
}
.btn-secondary-zone .stButton > button:hover{ border-color: var(--signal) !important; color: var(--signal) !important; background: var(--signal-tint) !important; }

/* Containers used as cards: st.container(border=True) */
[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius: var(--r-card) !important;
  border-color: var(--line) !important;
  box-shadow: 0 1px 2px rgba(9,20,52,0.04), 0 14px 32px -12px rgba(9,20,52,0.10) !important;
  background: var(--surface) !important;
}

/* Dataframe / table */
[data-testid="stDataFrame"]{ border-radius: var(--r-card) !important; overflow: hidden !important; border: 1px solid var(--line) !important; }

/* ---------------------------------------------------------------------- */
/* PART B — Custom component classes (used by render_* functions below)   */
/* ---------------------------------------------------------------------- */

.card{ background: var(--surface); border-radius: var(--r-card); border: 1px solid var(--line);
  box-shadow: 0 1px 2px rgba(9,20,52,0.04), 0 14px 32px -12px rgba(9,20,52,0.10); }
.card__pad{ padding: 26px; }

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
.pill{ font-size:10.5px; font-weight:700; padding:3px 8px; border-radius:99px; }
.pill--good{ background: var(--success-bg); color: var(--success); }
.pill--mid{ background: var(--amber-bg); color: var(--amber); }
.pill--low{ background: var(--alert-bg); color: var(--alert); }
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
.group-pin__value{ font-weight:800; font-size:19px; color:var(--ink); line-height:1; }

.diag-title{ font-size:11.5px; font-weight:800; letter-spacing:0.05em; text-transform:uppercase; color:var(--alert); margin-bottom:12px; }
.diag-list{ margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:10px; }
.diag-list li{ font-size:12.5px; color:var(--slate); display:flex; justify-content:space-between; font-weight:500; }
.diag-list b{ color:var(--ink); font-weight:700; }

.eyebrow{ display:inline-flex; align-items:center; gap:8px; font-size:12px; font-weight:700; color:var(--signal);
  background:var(--signal-tint); padding:6px 13px 6px 10px; border-radius:99px; margin-bottom:18px; }
.eyebrow .dot{ width:6px; height:6px; border-radius:50%; background:var(--signal); }
"""


def inject_css() -> None:
    """Call once, near the top of ui/app.py, before rendering any widgets."""
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# ============================================================================
# COMPONENT RENDERERS
# Each returns an HTML string for st.markdown(..., unsafe_allow_html=True).
# Pure presentation — pass in already-computed values from your
# universality.evaluate() result; nothing here does math.
# ============================================================================

_TIER_LABELS = {
    "excellent": "Excellent fit",
    "good": "Good fit",
    "moderate": "Moderate fit",
    "poor": "Poor fit",
}


def score_to_tier(score: float) -> str:
    """Pure display mapping — mirrors the same thresholds your calculation
    layer already uses for `tier`. Kept here only so components have a
    fallback if you don't pass tier explicitly."""
    if score >= 0.8:
        return "excellent"
    if score >= 0.6:
        return "good"
    if score >= 0.4:
        return "moderate"
    return "poor"


def render_hero(title_html: str, lede: str, score: float, product_name: str,
                 mini_rows: list[tuple[str, str]]) -> str:
    """mini_rows: list of (label, pill_html) tuples, e.g.
    [("Ease of navigation", '<span class="pill pill--good">Strong</span>'), ...]
    """
    rows_html = "".join(
        f'<div class="mini-card__row"><span>{label}</span>{pill}</div>'
        for label, pill in mini_rows
    )
    return f"""
    <div class="eyebrow"><span class="dot"></span>Simplified Singh &amp; Tandon framework</div>
    <h1 style="font-size:clamp(30px,4vw,46px); max-width:15ch; line-height:1.08; margin-bottom:16px;">{title_html}</h1>
    <p style="font-size:16px; color:var(--slate); max-width:52ch; margin-bottom:28px; font-weight:500;">{lede}</p>
    <div class="hero-visual">
      <div class="hero-visual__inner">
        <div class="hero-visual__copy">
          <div class="kicker">Live readout</div>
          <div class="figure">{score:.2f}<small>/ 1.00</small></div>
          <p>{product_name} — {_TIER_LABELS[score_to_tier(score)]}.</p>
        </div>
        <div class="mini-card">{rows_html}</div>
      </div>
    </div>
    """


def render_ring_gauge(score: float, product_name: str, tier: str | None = None) -> str:
    """score: 0-1 float from your evaluate() result. tier: pass explicitly
    from your calculation layer if you already compute one; otherwise it's
    derived here for display purposes only."""
    tier = tier or score_to_tier(score)
    label = _TIER_LABELS[tier]
    circumference = 540.35  # 2 * pi * r(86)
    clamped = max(0.0, min(1.0, score))
    offset = circumference * (1 - clamped)
    return f"""
    <div class="card"><div class="card__pad" style="text-align:center;">
      <div class="ring-wrap">
        <svg class="ring-svg" viewBox="0 0 200 200">
          <circle class="ring-track" cx="100" cy="100" r="86"/>
          <circle class="ring-fill ring-fill--{tier}" cx="100" cy="100" r="86"
                  stroke-dasharray="{circumference}" stroke-dashoffset="{offset:.2f}"/>
        </svg>
        <div class="ring-center">
          <div class="dial-figure">{clamped:.2f}<span class="pct">/ 1.00</span></div>
          <div class="dial-caption">Universality Index</div>
          <span class="dial-tier tier-{tier}">{label}</span>
        </div>
      </div>
      <div class="dial-caption" style="margin-top:14px;">{product_name}</div>
    </div></div>
    """


def render_group_pins(fap: float, sap: float, dap: float) -> str:
    return f"""
    <div class="card"><div class="group-readouts">
      <div class="group-pin"><div class="group-pin__label">FAP</div><div class="group-pin__value">{fap:.2f}</div></div>
      <div class="group-pin"><div class="group-pin__label">SAP</div><div class="group-pin__value">{sap:.2f}</div></div>
      <div class="group-pin"><div class="group-pin__label">DAP</div><div class="group-pin__value">{dap:.2f}</div></div>
    </div></div>
    """


def render_diagnostics(items: list[tuple[str, str]]) -> str:
    """items: list of (left_label, right_value) tuples, e.g.
    [("Weight of the frame", "DAP · 0.40"), ("Widest group gap", "FAP–DAP · 0.40")]
    """
    list_html = "".join(f"<li>{left} <b>{right}</b></li>" for left, right in items)
    return f"""
    <div class="card"><div class="card__pad">
      <div class="diag-title">Needs attention</div>
      <ul class="diag-list">{list_html}</ul>
    </div></div>
    """
