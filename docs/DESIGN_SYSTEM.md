# Design system — Universality Index Tool (UI band)

**Status: design contract — implemented 2026-08-26 (`ui/app.py` + `ui/ui_model.py`); this document remains binding. Flagged deviations are recorded in `UI_ARCHITECTURE.md` §4.1 and `docs/changelog.md` (2026-08-26).**
Companion documents: `UI_ARCHITECTURE.md` (structure), `UX_FLOW.md` (behavior), `ACCESSIBILITY.md` (a11y).
Upstream contracts this document must not contradict: `architecture.md` (bands, imports, security), `DOMAIN_MODEL.md`, `validation-and-security.md` (error messages are displayed verbatim), `FORMULA_SPECIFICATION.md` (A6 display rounding), `LIMITATIONS.md`.

## 1. Product identity

A **research data sheet**, not a SaaS dashboard. The student has already done the research; the page is where findings are transcribed and the index is read off — the visual equivalent of a lab notebook page: serif type, ruled structure, one page, one action.

**Tone:** academic · calm · trustworthy · clean · approachable · research-oriented.

**Mood-board constraints (hard rules):**

- White and blue branding only (no third brand hue; green/red/amber exist as *status* colors, not brand).
- No glassmorphism, no translucency, no backdrop blur.
- No shadows for elevation (zero `box-shadow` on cards/panels; borders + color blocking carry the hierarchy). The only permitted glow is the focus ring.
- No pill components (no fully-rounded buttons/chips); corner radius 4–7px everywhere.
- No neon or multi-stop gradients (single flat fills only).
- No marketing sections, no hero images, no carousels, no empty-state illustrations with characters.
- No generic SaaS dashboard appearance: no sidebars, no card-grid kpis, no icon-heavy toolbars.

## 2. Color

### 2.1 Brand & surface palette

| Token | Value | Use |
|---|---|---|
| `--bg-paper` | `#F7F8FA` | Page background (off-white) |
| `--bg-card` | `#FFFFFF` | Form cards, parameter cards, table |
| `--bg-blue-wash` | `#EAF1FB` | Section color blocks (results band, parameter header band) |
| `--bg-blue-block` | `#D7E4F7` | Sub-block inside the results band (group-index cards) |
| `--brand-600` | `#2563EB` | Links, focus border |
| `--brand-700` | `#1D4ED8` | Primary button fill, section rules, wordmark accent |
| `--brand-800` | `#1E40AF` | Primary button hover |
| `--brand-900` | `#172554` | Strong accents in results (hero figure underline) |
| `--grid-line` | `rgba(29, 78, 216, 0.06)` | Background grid pattern (6% — within the 5–10% spec) |

### 2.2 Text palette

| Token | Value | Use | Min contrast |
|---|---|---|---|
| `--ink` | `#111827` | Body text, labels, figures | 15.9:1 on `--bg-card` |
| `--ink-2` | `#4B5563` | Secondary text, hints, captions, micro-labels | 7.5:1 on white · 6.6:1 on `--bg-blue-wash` |
| `--ink-disabled` | `#9CA3AF` | Disabled text only (WCAG-exempt) | — |
| `--brand-700` on white | — | Links, primary text-on-white accents | 6.7:1 |

### 2.3 Status palette (used sparingly; never decorative)

| Token | Value | Use |
|---|---|---|
| `--err-700` | `#B91C1C` | Error message text (6.5:1 on white) |
| `--err-600` | `#DC2626` | Error left-rule, error icon |
| `--err-50` | `#FEF2F2` | Error element background |
| `--ok-700` | `#15803D` | "Calculated" caption, success rule (5.0:1 on white) |
| `--warn-700` | `#B45309` | Reserved for the optional live weight-total (not used in baseline) |

**Explicit non-decision (flagged):** the three user groups (FAP/SAP/DAP) receive **no distinct colors**. Group cards are visually identical neutral blocks; blue shading is reserved for the brand. Rationale: no visual hierarchy may be implied between user groups (trust + research integrity). Any future per-group coloring requires change control.

## 3. Typography

### 3.1 Typefaces

| Role | Face | Stack |
|---|---|---|
| Display (wordmark, section titles, result figures) | **Baskerville** | `"Baskerville", "Baskerville Old Face", "Hoefler Text", "Garamond", "Libertine", "Times New Roman", serif` |
| Body & UI text | **Lora** (self-hosted woff2, SIL OFL; weights 400/500/600 + italic 400) | `"Lora", "Iowan Old Style", "Palatino", serif` |
| Numeric table cells | system monospace (no extra download) | `"SFMono-Regular", "Consolas", "Liberation Mono", monospace` |

> **Flagged decision (D-UI-1):** classic Baskerville has no web-embeddable licensed font file. It is specified as a **system font stack**: on Apple platforms real Baskerville renders; elsewhere the stack falls back to comparable old-style serifs. Lora (Open Font License) is self-hosted in `ui/` assets for cross-platform consistency of the body voice. If pixel-identical display type across all platforms is ever required, a licensed OFL equivalent (e.g. "EB Garamond") is the change-control path — do not substitute silently.

### 3.2 Type scale (at 100% zoom; sizes in px, line-height in px)

| Token | Spec | Use |
|---|---|---|
| `--type-wordmark` | Baskerville 28 / 34, weight 600 | Masthead title |
| `--type-section` | Baskerville 21 / 30, weight 600 | "Part I — Evaluation setup" etc. |
| `--type-h3` | Lora 17 / 26, weight 600 | Sub-block titles ("Overall index", "Per-parameter details") |
| `--type-body` | Lora 16 / 26, weight 400 | Guidance text, table labels |
| `--type-label` | Lora 14 / 20, weight 500 | Field labels |
| `--type-caption` | Lora 13 / 20, weight 400 *italic* | Hints, method notes, footnotes |
| `--type-micro` | Lora 11.5 / 16, weight 600, uppercase, letter-spacing 0.08em | Stat labels ("UNIVERSALITY INDEX (UI)") |
| `--type-figure-hero` | Baskerville 48 / 56, weight 400 | Overall UI value |
| `--type-figure-stat` | Baskerville 26 / 34, weight 400 | Group indices, group gap |
| `--type-table-num` | monospace 13.5 / 20 | All numeric table cells (`font-variant-numeric: tabular-nums` where supported) |

Mobile (≤720px): `--type-figure-hero` 44/52; wordmark 24/30. Nothing below 11.5px. Body text never below 16px.

## 4. Shape, elevation, texture

- **Radius:** `--r-sm: 4px` (inputs, buttons), `--r-md: 6px` (cards, panels, error elements), `--r-lg: 7px` (results section only). Nothing larger; nothing fully rounded.
- **Elevation:** flat. Cards are distinguished by a 1px `--border` (`#D8DEE9`) and background color blocking. No `box-shadow` anywhere except the focus ring (see §6).
- **Grid pattern (page texture):** the page background carries a subtle graph-paper grid: 24px × 24px cells, 1px lines in `--grid-line` (brand blue at **6%** opacity, within the 5–10% spec), implemented as two CSS linear-gradients on the root element. Cards are opaque, so the grid is visible only in the page margins — lab-notebook paper. The pattern is static (no motion) and must not reduce text contrast (it sits behind the paper background, under all content).
- **Rules (hairlines):** 1px `--border` for dividers; section titles sit above a 1px rule that spans the content width; the results section carries a 2px `--brand-700` top rule on success (see `UX_FLOW.md` success state).

## 5. Color-blocking scheme (page anatomy)

```
┌────────────────────────────────────────────────────────────┐
│ page: --bg-paper + 6% blue grid (24px cells)               │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ MASTHEAD (no card): wordmark + one-line purpose +      │ │
│ │ version/Simple Mode tag · thin 1px rule underneath     │ │
│ ├────────────────────────────────────────────────────────┤ │
│ │ PART I  card: --bg-card, 1px border, r6                │ │
│ │   (product name | scale maximum)                       │ │
│ ├────────────────────────────────────────────────────────┤ │
│ │ PART II card: --bg-card, 1px border, r6                │ │
│ │   header band: --bg-blue-wash (title + count)          │ │
│ │   parameter cards: --bg-card, 1px border, r6,          │ │
│ │     on --bg-paper inset strip (cards sit on paper)     │ │
│ │   [+ Add parameter — dashed outline] [Calculate →]     │ │
│ ├────────────────────────────────────────────────────────┤ │
│ │ PART III (appears after calculation): --bg-blue-wash,  │ │
│ │   r7, 2px --brand-700 top rule on success              │ │
│ │   overall figure on --bg-card inset · group cards on   │ │
│ │   --bg-blue-block · parameter table on --bg-card       │ │
│ ├────────────────────────────────────────────────────────┤ │
│ │ FOOTER (no card): method line + disclaimer, caption    │ │
│ └────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

Content column: **max-width 880px, centered** — the page reads like a paper, not a dashboard. Side gutters grow on wide screens (the grid shows through).

## 6. Component states

### 6.1 Buttons (baseline inventory: exactly five)

| Button | Kind | Where |
|---|---|---|
| Calculate | **Primary** | End of Part II (and the only primary on the page) |
| Reset evaluation | **Secondary** | Masthead-right and footer of Part II |
| Add parameter | **Tertiary** | Below the parameter list (full-width dashed) |
| Reset weights to 1/n | **Tertiary** | Part II header band, right side |
| Remove parameter (×) | **Tertiary icon** | Each parameter card header (disabled at n = 1) |

- **Primary** — fill `--brand-700`, white text (6.7:1), Lora 500 16px, height 40px, padding 0 28px, r4. Hover `--brand-800` (120ms color transition — no lift, no shadow). Active `--brand-900`. Disabled: fill `#E5E7EB`, text `--ink-disabled`. Focus: `2px solid --brand-600` outline, 2px offset (visible on white and on the blue wash).
- **Secondary** — fill `--bg-card`, 1px solid `--brand-700` border, `--brand-700` text (6.7:1). Hover: fill `#EFF4FC`. Same geometry as primary.
- **Tertiary** — no fill, no border (Add parameter: 1px **dashed** `#C6CFDD` border), `--ink-2` text, Lora 500 14–16px, height 36px (hit area ≥ 44px via padding), r4. Hover: text `--brand-700`. Remove (×): icon-only 16px line icon, 44×44 hit area, aria-label "Remove parameter {n}".
- **No loading spinner inside buttons** (see `UX_FLOW.md` loading state: label change + quiet progress line).

### 6.2 Inputs (all fields: `st.text_input` / `st.number_input` equivalents; 40px height; r4; 1px border `--border`; white fill; Lora 400 16px)

| State | Visual | Trigger |
|---|---|---|
| **Default** | 1px `--border`, white fill, `--ink` text; label above (Lora 500 14px `--ink`); optional caption below (italic 13px `--ink-2`) | always |
| **Focus** | 1px `--brand-600` border + `box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18)` (the only glow on the page); label unchanged | keyboard or pointer focus |
| **Success** | *No per-field success state in the baseline* (flagged, D-UI-2). The success signal is section-level: the results section + "Calculated" caption. Rationale: green ticks on every field read as "gamification," not academia. | — |
| **Error** | Inline error element **directly under the field** (Streamlit-mapped; see `UI_ARCHITECTURE.md` §6): `--err-50` fill, 1px `--err-600` left rule 3px, `--err-700` text 14px, 16px line icon (⚠), message **verbatim from the gate** + translated field label ("DAP score of parameter 3"). Best-effort enhancement: input border → `--err-600` where the framework allows class hooks (non-normative). | Field is the target of the last rejection (path mapping, `UI_ARCHITECTURE.md` §5) |
| **Disabled** | Fill `#F3F4F6`, border `--border`, text `--ink-disabled`, `cursor: not-allowed`, `aria-disabled="true"` | Remove (×) at n = 1; Add at n = 100; Calculate while calculating |

Numeric fields: spinner buttons of the framework, restyled neutral (1px border, `--ink-2` chevrons); step and min/max are **convenience bounds only** — the validation gate is the sole authority (see `UI_ARCHITECTURE.md` §4).

### 6.3 Cards, panels, table

- **Parameter card:** r6, 1px `--border`, header row ("Parameter {n}" + ×), body grid (§8 of `UI_ARCHITECTURE.md`), 20px padding; sits on the paper inset strip of Part II (cards are white on paper — the grid shows only in the strip's 12px gaps).
- **Error summary panel:** r6, `--err-50` fill, 3px `--err-600` left rule, title "Please check the highlighted field." (Lora 600 16px `--err-700`), then the gate message verbatim, then the field list (one line per field, translated label, `--ink-2`). `role="alert"`.
- **Results section:** §5 scheme; group cards: r6, `--bg-blue-block` fill, no border, 16px padding, micro-label + Baskerville figure; **parameter table:** real `<table>` (or framework dataframe styled as a table), `--bg-card`, 1px `--border` outer, 1px row dividers `#E8ECF3`, header row `--bg-blue-wash` with Lora 600 13px labels, numeric cells monospace right-aligned, first column (name) left-aligned Lora 400 14px, caption line above: "Per-parameter normalized scores (s ÷ scale)" — see `ACCESSIBILITY.md` for table semantics.

### 6.4 Motion

| Event | Animation |
|---|---|
| Results appear / update | fade-in 200ms ease-out + 4px upward translate; then scroll-into-view 300ms smooth (only if the trigger was the Calculate button) |
| Error summary appears | fade-in 150ms; scroll-into-view 250ms |
| Button color states | 120ms ease |
| Anything else | none |

All motion honors `prefers-reduced-motion: reduce` (instant, no scroll animation). No entrance animations on initial page load.

## 7. Iconography

Five 16px line icons, 1.5px stroke, `--ink-2` (error icon `--err-600`, success check `--ok-700`): `+` (add), `×` (remove), `⚠` (error), `✓` (calculated), `ℹ` (hints). Inline SVG, hand-set (no icon-library brand style). No other icons.

## 8. Density & spacing

Base unit 4px. Section vertical padding 28–32px; card padding 20px; field-to-field gap 16px; field label-to-input gap 6px; section-to-section gap 28px; page top padding 40px / bottom 48px. Whitespace is generous — the page should feel *ruled*, not *packed*.

## 9. Do/Don't quick reference

| Do | Don't |
|---|---|
| Flat cards, 1px borders, color blocks | Glassmorphism, shadows for elevation |
| 4–7px radius | Pill components, fully rounded anything |
| 6% blue grid in margins only | Grid behind text, pattern > 10% |
| One primary action per page | Multiple competing CTAs |
| Verbatim gate messages in error text | Rewriting/softening gate messages in the UI |
| Neutral group cards | Per-group colors or ranking cues |
| Static values (no count-up, no sparklines) | Animated numbers, micro-charts, KPI cards |
