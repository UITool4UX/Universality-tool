# Universality Index Tool

A student-facing evaluation tool for the user-value / product-universality research framework associated with Singh & Tandon. Students enter user-research findings (parameter weights and per-group satisfaction scores) and the tool calculates a normalized **Universality Index (UI)** for a product or service.

The tool is designed to make a complex methodology feel simple **without hiding important assumptions**.

> ## Current status: all MVP layers implemented (domain, calculation, validation, application, UI)
>
> Implemented: `universality/domain.py` (domain model), `universality/calculation.py`
> (calculation engine, F1–F4), `universality/validation.py` (the user-input
> gate, V1–V21), `universality/services.py` (the application boundary:
> `evaluate`, `format_for_display`, `ServiceError`), `universality/diagnostics.py`
> (redacted logging), the single-page Streamlit UI
> (`ui/app.py` + `ui/ui_model.py`), and the machine-checkable security audit
> (`scripts/security_audit.py` — forbidden constructs + import policy, run by
> the test suite per `docs/architecture.md` §12), with unit, integration,
> property, edge-case, services, diagnostics, UI, and security-audit tests in
> `tests/` (291 tests).
> Not yet implemented: export, the research lane, and packaging.
> Run: install the pinned dependency once
> (`.venv/bin/pip install -r requirements.txt` — Streamlit 1.62.0, the only
> third-party dependency; security-reviewed 2026-08-26 via pip-audit), then
> `.venv/bin/streamlit run ui/app.py --server.address 0.0.0.0`
> (Python 3.11; no other dependencies).
> UI design contract (2026-08-26): `docs/DESIGN_SYSTEM.md`,
> `docs/UI_ARCHITECTURE.md`, `docs/UX_FLOW.md`, `docs/ACCESSIBILITY.md`.
> The documents below remain the binding design specification; code conforms to them.
> See [`docs/changelog.md`](docs/changelog.md).

## The three layers of truth

| Layer | What it is | Document |
|---|---|---|
| Research methodology | What Singh & Tandon's published research actually establishes — verified claims only, with sources and provenance | [`docs/RESEARCH_BASIS.md`](docs/RESEARCH_BASIS.md), [`docs/REFERENCES.md`](docs/REFERENCES.md) |
| Simplified computational implementation | The exact formulas this application implements (authoritative statement) | [`docs/FORMULA_SPECIFICATION.md`](docs/FORMULA_SPECIFICATION.md) |
| Assumptions introduced by the application | Every assumption, interpretation, and choice beyond verified research, with status and justification | [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md), [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) |

The audited **methodology map** — the definition, mathematical role, mode placement (MVP / Research Mode), optionality, and user-visibility of all 12 audited concepts — is in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

**This project never claims that the MVP reproduces every mathematical operation of the complete research methodology** unless that operation has actually been implemented *and* independently verified (claim register: [`docs/RESEARCH_BASIS.md`](docs/RESEARCH_BASIS.md); must-not list: [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md)).

## The formulas (summary — not authoritative)

For each group G ∈ {FAP, SAP, DAP}, parameter weights wᵢ with Σwᵢ = 1, and normalized scores s_norm = observed_score / maximum_scale:

    UI_F = Σᵢ wᵢ · s_norm(i, FAP)
    UI_S = Σᵢ wᵢ · s_norm(i, SAP)
    UI_D = Σᵢ wᵢ · s_norm(i, DAP)

    UI = W_F·UI_F + W_S·UI_S + W_D·UI_D        (W_F + W_S + W_D = 1)

Simple Mode (the only mode in the MVP): W_F = W_S = W_D = **1/3**, shown to the user. Parameter weights default to **1/n**, shown and editable by the student. The application never performs or implies AHP. Kano categories are **not** part of the current contract.

The engine also computes the **user-group gap (F4)** — the spread of the three group indices (registered 2026-08-25, explicit user instruction; interpretation A19). Its registered definition is in [`docs/FORMULA_SPECIFICATION.md`](docs/FORMULA_SPECIFICATION.md); it is not restated here.

The authoritative statement of formulas, constraints, and numerical rules is [`docs/FORMULA_SPECIFICATION.md`](docs/FORMULA_SPECIFICATION.md). Do not restate formulas elsewhere with different constants or semantics.

## Document map

**Research-methodology contract** (established 2026-08-25, audit task):

| Document | Purpose |
|---|---|
| `docs/RESEARCH_BASIS.md` | Verified research claims with per-claim provenance + claim register + upgrade path |
| `docs/METHODOLOGY.md` | Methodology map: the 13 audited concepts (incl. the F4 user-group gap diagnostic); formal MVP and Research Mode definitions |
| `docs/FORMULA_SPECIFICATION.md` | **Authoritative** formulas F1–F4, constraints C1–C5, numerical rules, test vectors TV1–TV6 |
| `docs/ASSUMPTIONS.md` | Complete assumptions register A1–A21 (mandated / confirmed / proposed) |
| `docs/LIMITATIONS.md` | Negative contract: must-NOT-implement M1–M10 + ambiguities register U1–U8 |
| `docs/REFERENCES.md` | Bibliography, access status, verification log, upgrade path |

**Implementation governance:**

| Document | Purpose |
|---|---|
| `docs/architecture.md` | **Finalized production architecture**: band model and strict dependency direction, directory tree, module responsibilities, dependency graph, data/error flow, domain model, testing architecture, extension strategy, security boundaries |
| `docs/DOMAIN_MODEL.md` | Domain model — field-level authority (implemented: `universality/domain.py`) |
| `docs/CALCULATION_ENGINE.md` | Calculation engine specification (implemented: `universality/calculation.py`) |
| `tests/CALCULATION_TEST_VECTORS.md` | Test-vector map + hand-verification worksheet for TV1–TV7 |
| `docs/validation-and-security.md` | Trust model, raw input schema, rejection table V1–V21 (V15 reserved), validation order, group-weight gate, error-handling contract, forbidden constructs, input limits (implemented: `universality/validation.py`) |
| `docs/DESIGN_SYSTEM.md` | UI design contract — visual tokens (white/blue, Lora/Baskerville, 4–7px radius, color blocking, 6% grid), components and states (implemented in `ui/app.py`, 2026-08-26) |
| `docs/UI_ARCHITECTURE.md` | UI architecture contract — Streamlit mapping, session-state + error-path contracts, no-math boundary, flagged decisions D-UI-1…D-UI-9 (implemented in `ui/app.py` + `ui/ui_model.py`, 2026-08-26) |
| `docs/UX_FLOW.md` | UX flow contract — page map, form state machine, event table, normative copy (implemented, 2026-08-26) |
| `docs/ACCESSIBILITY.md` | Accessibility contract — WCAG 2.1 AA, focus/live-region management, contrast table, manual acceptance checklist (implemented, 2026-08-26) |
| `docs/changelog.md` | Change history; every formula / architecture / assumption change requires an entry here |
| `ai/ai-guidelines.md` | Guardrails and protocol for AI agents contributing to this repository |
| `docs/research-methodology.md`, `docs/computational-model.md`, `docs/application-assumptions.md` | Superseded redirects (2026-08-25) — see each file's target |

## Research sources

- Singh, R., & Tandon, P. (2016). *User values based evaluation model to assess product universality.* International Journal of Industrial Ergonomics, 55, 46–59.
- Singh, R., & Tandon, P. (2018). *Framework for improving universal design practice.* International Journal of Product Development, 22(5), 377–407.

Group labels, per the public literature of this research line: **FAP** = Fully Abled People, **SAP** = Specially Abled People, **DAP** = Differently Abled People. Full bibliography and verification log: [`docs/REFERENCES.md`](docs/REFERENCES.md).

## Contribution rules (summary)

- Documentation is the source of truth; code must conform to it. If documentation and code ever conflict: identify it, do not silently choose, explain it, propose the smallest correction.
- A formula change requires: documentation update + test-vector update + regression tests + changelog entry + explicit approval.
- Items in the must-NOT-implement list (`docs/LIMITATIONS.md`, M1–M10) require their documented gate before implementation.
- No new dependency without the documented four-step justification (standard library first).
- Every new file must have a documented purpose and a single owner of its responsibility.
- AI agents: read [`ai/ai-guidelines.md`](ai/ai-guidelines.md) before making any change.
