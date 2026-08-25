# Architecture — FINALIZED (2026-08-25)

Purpose: the production architecture of the Universality Index Tool. Any implementation must conform. This document is the single owner of the architecture. Formulas remain owned by `FORMULA_SPECIFICATION.md` — this document references F1–F4 by ID only and **never restates them**.

**Status: design finalized; DOMAIN, CALCULATION, and VALIDATION layers implemented (2026-08-25); APPLICATION (services, diagnostics) and the UI band implemented (2026-08-26). Remaining: export, the research lane, packaging.** See `docs/changelog.md`.

## 1. Design constraints

- Bands and direction: **UI → Application → Domain/Calculation → Infrastructure** (strict).
- The calculation engine is UI-independent, pure, independently executable and testable.
- Standard library only (Python 3.11); no microservices; no database (A13, M8); no new frameworks (Streamlit is the only permitted UI framework — implemented 2026-08-26); no global mutable business state; no circular dependencies; MVP stays small.
- No formula may exist in two places (F1–F4: `FORMULA_SPECIFICATION.md` in docs, `universality/calculation.py` in code — the only two locations, doc and code).
- Every new file has a documented purpose; existing owners of a responsibility are reused (see §13).

## 2. Band model and dependency direction

```
┌────────────────────────────────────────────────────────────┐
│ UI                     ui/app.py, ui/ui_model.py           │
├────────────────────────────────────────────────────────────┤
│ APPLICATION            universality/services.py            │
│                        universality/validation.py          │
│                        universality/diagnostics.py         │
│                        universality/export.py      (future)│
├────────────────────────────────────────────────────────────┤
│ DOMAIN / CALCULATION   universality/domain.py              │
│                        universality/calculation.py         │
│                        universality/research/*     (future)│
├────────────────────────────────────────────────────────────┤
│ INFRASTRUCTURE         (reserved — zero MVP modules)       │
└────────────────────────────────────────────────────────────┘
        (below every band: Python standard library only)
```

**Direction policy:** an import is permitted only **downward** (a band may import modules in itself or lower bands, plus stdlib). A band is **not obligated** to depend on the band below it. Consequences:

- `universality/domain.py` and `universality/calculation.py` import **nothing** project-internal (domain) / only `domain.py` (calculation). This is the strongest form of UI-independence: the engine has no import path to any UI.
- **Infrastructure is a reserved band with zero MVP modules.** Rationale: no persistence requirement exists (A13, M8), "no database unless required", and creating an empty package would be over-engineering. **Entry criteria:** a module enters Infrastructure only with an approved task (persistence per M8, or diagnostics growth), and each such module is listed here with its permitted imports before implementation.
- **Diagnostics is a logical layer (per the brief) realized as an Application-band module** (`universality/diagnostics.py`) in the MVP, because its only caller is `services.py`. If diagnostics grows (metrics, telemetry), it graduates to `universality/infrastructure/diagnostics/` — see §11.

## 3. Directory tree

```
universality-tool/
├── universality/                  # THE library. Everything below this line is importable production code.
│   ├── __init__.py                # PUBLIC API: version + re-exports only.
│   ├── domain.py                  # DOMAIN band: frozen value objects.
│   ├── calculation.py             # CALCULATION band: F1–F4. The only formulas in the codebase.
│   ├── validation.py              # APPLICATION band: the V1–V21 rejection gate (implemented).
│   ├── services.py                # APPLICATION band: orchestration, error mapping, display formatting.
│   ├── diagnostics.py             # APPLICATION band: stdlib logging config + redacted error logging.
│   ├── export.py                  # APPLICATION band, FUTURE: pure formatters (outcome → CSV/JSON text).
│   └── research/                  # CALCULATION band, FUTURE (reserved lane; created with first approved feature)
├── ui/
│   ├── __init__.py                # Package marker (docstring only).
│   ├── app.py                     # UI band: Streamlit composition root (implemented 2026-08-26).
│   ├── ui_model.py                # UI band: pure assembly/label-mapping (no Streamlit, no math — AST-enforced).
│   └── fonts/                     # Self-hosted Lora woff2 (4 expected files; README documents the convention).
├── tests/
│   ├── test_domain.py             # Domain model + invariants (58).
│   ├── test_calculation.py        # TV1–TV4 + invariants + determinism (40).
│   ├── test_validation.py         # V1–V21 (V15 reserved), each with positive and negative cases (69).
│   ├── test_integration.py        # Public surface (31 names), pipeline vectors, catchability (14).
│   ├── test_properties.py         # Seeded property checks (9).
│   ├── test_edge_cases.py         # Boundary / adversarial (25).
│   ├── test_services.py           # Orchestration, error mapping, single-rounding-location scan (20).
│   ├── test_diagnostics.py        # Redaction, leak-freedom, logging configuration (7).
│   ├── test_ui_model.py           # Pure-band unit + AST purity (no arithmetic) tests (19).
│   ├── test_ui_app.py             # AppTest rendering / interaction contract (17; skipped if Streamlit absent).
│   ├── test_security_audit.py     # Runs the security audit over the source tree; asserts zero findings (implemented 2026-08-26).
│   └── test_export.py             # FUTURE, with export.py.
├── scripts/
│   └── security_audit.py          # stdlib-only static checks — forbidden constructs + import policy (implemented 2026-08-26; owner per §12/§15).
├── docs/                          # Source of truth (existing; see README document map).
└── ai/ai-guidelines.md            # Contributor/AI guardrails (existing).
```

## 4. Responsibility of every directory

| Directory | Responsibility | Must NOT contain |
|---|---|---|
| `universality/` | The entire library: all business logic, models, and pure computation. No I/O except diagnostics' stdlib logging. | UI code, formulas outside `calculation.py`, file/network access, global mutable state |
| `universality/research/` | One directory per **approved** research-mode feature (M-gated). Pure modules, same band as `calculation.py` | Ungated features, anything that imports `services`/`validation`/`ui` |
| `ui/` | The Streamlit application: rendering, input capture, composition root (wires `services`), future download buttons for export | Mathematical business logic, authoritative validation, direct imports of library submodules (public API only) |
| `tests/` | Automated verification: test vectors, rejection cases, orchestration/error flows, security regression. May import any production module (tests sit outside the bands) | Production code; importing each other in ways that create order dependencies |
| `scripts/` | Developer/CI tooling that inspects the codebase without importing it (stdlib only) | Business logic, anything importable by production code |
| `docs/`, `ai/` | The contract (existing) | — |

## 5. Responsibility of every module

| Module | Band | Owns | May import | Must NOT import |
|---|---|---|---|---|
| `universality/__init__.py` | public API | **Implemented (2026-08-26).** `__version__`; re-exports of the 31-name public surface: the domain types + contract constants (`SCALE_MIN/MAX`, `PARAMETER_MAX`, `EPSILON`, …), the calculation surface (F1–F4 + `SIMPLE_MODE_GROUP_WEIGHTS`), the validation surface (`validate`, `validate_group_weights`, `ValidationRejection`), the application surface (`evaluate`, `ServiceError`, `format_for_display`) | `services`, `domain`, `calculation`, `validation` (re-exports only, no logic) | `ui`, `scripts`, `tests`, `research` |
| `universality/domain.py` | Domain | **Implemented (2026-08-25).** The domain model per `docs/DOMAIN_MODEL.md`: frozen value objects, type invariants (`DomainInvariantError`), the single C1/C2 predicate `weights_sum_is_valid`, constant `EPSILON`. **No research formulas, no I/O** | stdlib only | any project-internal module |
| `universality/calculation.py` | Calculation | **Implemented (2026-08-25).** F1–F4 as pure functions; constant `SIMPLE_MODE_GROUP_WEIGHTS` (A1) — its only location (`EPSILON` (A5) lives in `domain.py`, where the C1/C2 invariants are enforced). Precondition: input is validated (C1–C5 hold — structurally guaranteed by the `Evaluation` type); the user-input gate is `validation.py` | `domain` | `validation`, `services`, `diagnostics`, `export`, `research`, `ui`, stdlib I/O modules |
| `universality/validation.py` | Application | **Implemented (2026-08-25).** The single authoritative rejection gate implementing V1–V21 (V15 reserved for export; order: structural → domain; fail-fast); `validate(raw) -> Evaluation`; `validate_group_weights(...)` (single C2 validator, defensive for Simple Mode); `ValidationRejection(code, field, message)`; raw-dict → `Evaluation` construction; safety net maps any post-gate `DomainInvariantError` to the generic V-UNEXPECTED message. Reuses `domain.EPSILON`, `domain.weights_sum_is_valid`, and the domain's public contract constants (`SCALE_MIN/MAX`, `NAME_MIN_LENGTH/MAX_LENGTH`, `PARAMETER_MIN/MAX`, `CONTROL_CHARS`) — never re-implements the checks | `domain`, `calculation` (per §6) | `services`, `diagnostics`, `export`, `ui`, stdlib I/O modules |
| `universality/services.py` | Application | **Implemented (2026-08-26).** `evaluate(raw) -> EvaluationOutcome`; the unexpected-error boundary (propagates `ValidationRejection` unchanged; maps anything else to `ServiceError` + redacted log); `format_for_display` — the **single** location of A6 presentation rounding (4 dp); `ServiceError`; `GENERIC_SERVICE_MESSAGE` | `domain`, `calculation`, `validation`, `diagnostics`, `research.*` (future, gated) | `ui` |
| `universality/diagnostics.py` | Application | **Implemented (2026-08-26).** The `universality.diagnostics` logger (default `NullHandler`, `propagate = False`); `redacted_error(exc) -> dict` (class chain only — never the message/args); `log_unexpected(context, exc)` with the redaction rule (§9) — **`context` shape enforced fail-closed (`[A-Za-z0-9._-]{1,64}` or the fixed `<invalid-context>` placeholder; log-injection hardening, 2026-08-26 security audit)** | stdlib only (`logging`, `traceback`, `re`) | any project-internal module |
| `universality/export.py` *(future)* | Application | Pure formatters `EvaluationOutcome` → CSV/JSON **text** (returns strings; performs no I/O); CSV-injection guard at landing (§12) | `domain` | `services`, `ui`, stdlib I/O modules (`os`, `pathlib` file writes, …) |
| `universality/research/<name>.py` *(future, gated)* | Calculation | One approved research feature: its own formulas (registered in `FORMULA_SPECIFICATION.md` first) as pure functions | `domain`, `calculation` | `services`, `validation`, `ui`, stdlib I/O modules |
| `ui/app.py` | UI | **Implemented (2026-08-26).** Streamlit rendering/input capture; composition root (builds raw via `ui_model.collect_raw` and calls `evaluate`); displays A1/A2/A3/A4/A6/A7 surfaces; the single 4-dp display is `format_for_display`; future export download buttons; **last-resort exception guard (2026-08-26 security audit): any exception escaping the render path renders only the fixed generic error state — never a traceback (error contract §3, §9 "Never"); `RerunException` (`st.rerun`) is re-raised, never a fault** | `universality` **package public API only** (`from universality import …`), `ui.ui_model` (intra-band), `streamlit` (framework; incl. `streamlit.runtime.scriptrunner.RerunException` for the guard) | any `universality.<submodule>`, `scripts`, `tests` |
| `ui/ui_model.py` | UI | **Implemented (2026-08-26).** Pure presentation model: `fresh_state`, `collect_raw` (assembly only), `parse_field` (rejection path → UI target), `human_label`, `fix_hint`, the normative `COPY`/`FIX_HINTS` tables. **No Streamlit, no arithmetic operator at all** (AST-enforced by `tests/test_ui_model.py`) | `universality` **package public API only** (currently `PARAMETER_MAX`), stdlib `re`/`typing` | `streamlit`, any `universality.<submodule>`, `ui.app`, I/O modules |
| `tests/test_*.py` | tests | See §10 | any production module | — (production code must never import `tests`) |
| `scripts/security_audit.py` | tooling | **Implemented (2026-08-26, security audit task).** Stdlib-`ast` scans: (a) forbidden constructs per `validation-and-security.md` (`eval`/`exec`/`compile`/`__import__`/`input` calls, `os.system`/`os.popen`, `pickle`/`subprocess`/`importlib` imports, any `shell=True`) over `universality/`, `ui/`, `scripts/`, (b) import policy per §6 over all four directories (`tests/*` exempt from the edge table, still third-party-checked; `streamlit` permitted only in `ui/app.py` and `tests/*`). Emits findings; exit code reflects count | stdlib only (`ast`, `pathlib`, `sys`) | any project module (it inspects text, never imports) |

## 6. Dependency graph

```
 ui/app.py ──────────────┐
   (public API only)     ▼
                 universality (package __init__)
                        ╱   │   ╲
                       ▼    ▼    ▼
                services  domain  (re-exports)
                 │  │  │  │
                 ▼  ▼  ▼  ▼
         validation  diagnostics  calculation ──▶ domain
                 │        (stdlib only)      ▲
                 ▼                           │
               domain              research.* ─┘ (future, gated)
                 (stdlib only)
                 export ──▶ domain (future)
```

**Permitted import edges (complete list — anything else is a violation):**

| From | To |
|---|---|
| `ui/app.py` | `universality` (public API only), `ui.ui_model` (intra-band) |
| `ui/ui_model.py` | `universality` (public API only) |
| `universality/__init__.py` | `services`, `domain`, `calculation`, `validation` |
| `services.py` | `domain`, `calculation`, `validation`, `diagnostics`, `research.*` (future) |
| `validation.py` | `domain`, `calculation` |
| `calculation.py` | `domain` |
| `diagnostics.py` | — (stdlib only) |
| `export.py` (future) | `domain` |
| `research/*` (future) | `domain`, `calculation` |
| `tests/*` | any production module |

**Forbidden (illustrative, non-exhaustive — the table above is exhaustive):** `domain` → anything; `calculation` → `validation`/`services`/`diagnostics`/`export`/`research`; `export` → `services`; `research` → `services`/`validation`; anything → `ui/*`; anything → `scripts/*`; `universality` → `tests`; any edge that creates a cycle.

**Enforcement:** `scripts/security_audit.py` parses every `.py` file with `ast` and checks imports against the table; `tests/test_security_audit.py` keeps it green in every test run. Adding an edge is a contract change (this file + changelog + approval), not an implementation detail.

## 7. Data flow (happy path)

```
 UI (form values → plain Python primitives: dict)
   │  services.evaluate(raw)
   ▼
 services.evaluate
   │
   ├─▶ validation.validate(raw)
   │       structural (V19,V16–V18,V7,V12,V9,V10) → domain (V3,V11,V13,V1–V2,V5,V14,V4,V8,V6,V20–V21)
   │       │ pass                                    │ fail
   │       ▼                                         ▼
   │  Evaluation (frozen, trusted)        raise ValidationRejection(code, field, message)
   │       │                                          │
   ▼       ▼                                          ▼
 calculation.evaluate(evaluation, SIMPLE_MODE_GROUP_WEIGHTS)      UI shows .message
   │  F1 → F2 → F3, full IEEE-754 precision, deterministic        (friendly, no stack trace)
   ▼
 EvaluationResult (frozen, full precision)
   │
   ▼
 EvaluationOutcome(evaluation, result)   ← single object crosses the boundary
   │
   ▼
 UI: services.format_for_display(outcome) → strings, 4 dp (A6 — single rounding location)
     + displays: declared scale (A3), parameter weights / 1/n default (A2),
       group weights 1/3 each (A1), as-given-scores note (A4), A7 statement
 (future) UI: export.to_csv(outcome) / export.to_json(outcome) → str → st.download_button
     (formatting is pure in Application; the file transfer is I/O at the UI edge)
```

Rules visible in the flow: the raw `dict` exists **only** at the Application entry point; below `services.evaluate` there is only frozen domain data. The calculation never sees raw input, and the UI never sees the calculation (public API only).

## 8. Domain model

**Field-level authority: `docs/DOMAIN_MODEL.md`** (implemented in `universality/domain.py`, 2026-08-25).

Type set: `UserGroup` (enum), `KanoCategory` (enum — inert vocabulary; M2 scope note), `Score`, `Weight`, `GroupScores`, `Parameter`, `Evaluation`, `PerGroupValue`, `ParameterResult`, `EvaluationResult`, `EvaluationOutcome`, plus `DomainInvariantError` and the single C1/C2 predicate `weights_sum_is_valid`.

Rules (details and every field's type/meaning/range/required-status: `DOMAIN_MODEL.md`):

- All object types are **frozen dataclasses**; all fields are **required** (no `Optional` anywhere).
- **No research formulas** in the domain: F1–F4 live only in `calculation.py`; the result types carry F1/F2/F3/F4 outputs as data (e.g. `ParameterResult` = F1 outputs + F2 summands; `EvaluationResult.group_gap` = F4 output). Methods are shape navigation only — no arithmetic.
- **Invariant split:** the domain enforces *type invariants* (self-contained field ranges; single-object cross-field invariants: C1 weight sum, C3 score-vs-scale domain, A10 name rules) via `DomainInvariantError`; `validation.py` (**implemented 2026-08-25**) is the single authoritative *user-input* gate (V1–V21, V15 reserved; friendly messages) and runs before construction. The C1/C2 check predicate is implemented exactly once (`domain.weights_sum_is_valid`) and shared by both.
- **Constants:** `domain.EPSILON = 1e-9` (A5); `calculation.SIMPLE_MODE_GROUP_WEIGHTS = (1/3, 1/3, 1/3)` (A1, implemented module). The UI displays these via the public API re-exports — it never hardcodes them.

Input-side error types (owned where the layers land): `ValidationRejection(code, field, message)` in `validation.py` (**implemented 2026-08-25**; frozen dataclass, `Exception` subclass, `str()` returns the user-facing message); `ServiceError` (fixed generic message, `str()` = the message) in `services.py` (**implemented 2026-08-26**).

## 9. Error flow

**Expected errors (V1–V21, V15 reserved):**
1. `validation.validate` raises `ValidationRejection(code, field, message)` — the first violated rule in validation order (structural → domain); validation stops at the first rejection.
2. `services.evaluate` does **not** swallow it: it propagates. It is a controlled outcome, not a fault.
3. The UI catches `ValidationRejection` and displays `.message` verbatim. No stack trace, no internal detail, ever.

**Unexpected errors:**
1. Any exception other than `ValidationRejection` raised inside `services.evaluate` (a bug, e.g., in `calculation`) is caught at that single boundary.
2. `diagnostics.log_unexpected(context, exc)` logs, at ERROR level via the fixed template: the internal call-site identifier (`context`, e.g. `"evaluate.validation"` — never user data; the design sketch's `stage` + field identification, collapsed into one internal identifier because unexpected faults are internal bugs with no user field to attribute), the exception class, its class chain, cause/context presence flags, and the **safe stack frames** — the traceback's call sites as `file:line:function`. **Redaction rule:** the log record contains **no** exception type/message line (messages routinely embed user values), **no** source-line text (it may contain string literals), **no** field values, **no** parameter names, **no** raw user data — ever. Redaction is structural (only class names and code locations are recorded), not pattern-based.
3. `services.evaluate` raises `ServiceError` with the fixed generic message; the UI displays it.

**Never:** silent repair, imputation, or zero-filling (A14, A15, A17); user-facing stack traces; logging of user values.

## 10. Testing architecture

- **Framework:** stdlib `unittest` + `unittest.mock` (zero new dependencies — confirmed decision). Run: `python -m unittest discover -s tests -v` (or `.venv/bin/python -m unittest discover -s tests` — the venv adds Streamlit for the AppTest-based UI smoke tests; without Streamlit those 19 tests skip and the rest run unchanged).
- **Mirror principle:** one test module per production module; the module under test is the only production dependency of its test module beyond `domain`.
- **Determinism:** seeded `random.Random(20260825)` for any randomized case; no network, time, or filesystem in library tests (`test_export.py`, when it lands, may use `tempfile` only).
- **Tolerance discipline:** TV1–TV4 compared with `1e-12` per `FORMULA_SPECIFICATION.md`; never `==` on computed results.

| Test module | Owns |
|---|---|
| `tests/test_domain.py` | Domain model + invariants: construction, frozen-ness, `DomainInvariantError` on invariant violation, `weights_sum_is_valid` (C1/C2), constant ranges (58) |
| `tests/test_calculation.py` | TV1–TV4; invariants (0 ≤ UI ≤ 1 on seeded random valid inputs); boundaries (all-max → 1 within tolerance, all-zero → 0 exactly, TV4 single parameter); determinism (identical inputs → bit-identical results) (40) |
| `tests/test_validation.py` | One negative + one positive case per V1–V21 (V15 reserved); EPSILON boundary (e.g. weight sum `1 ± 5e-10` accepted, `1 ± 5e-8` rejected); first-rejection-wins ordering (69) |
| `tests/test_integration.py` | Public-surface contract (exactly the 31 documented names, each importable); pipeline vectors TV1/TV7 through `validate`→`compute`; `ValidationRejection` catchability (14) |
| `tests/test_properties.py` | Seeded (`20260826`) property checks over the engine (9) |
| `tests/test_edge_cases.py` | Boundary / adversarial inputs at the gate and engine (25) |
| `tests/test_services.py` | `evaluate` happy path vs the direct pipeline (canonical TV7 strings); rejection propagation unchanged; unexpected-failure mapping (mocked internals carrying "SECRET" payloads → `ServiceError` + exact generic message + no leakage); 13-raw adversarial battery; `format_for_display` table + rejections; **TestSingleRoundingLocation** (repository scan: the only rounding construct is in `services.py`) (20) |
| `tests/test_diagnostics.py` | Redaction: class/chain + safe stack frames, never the message/source-line/args/user value (incl. chained exceptions); deterministic template; ERROR level; `NullHandler` + `propagate False`; malformed/non-string context replaced, never logged verbatim (11) |
| `tests/test_ui_model.py` | Pure-band unit tests: `fresh_state` defaults, `collect_raw` exact schema/key order, `parse_field` table, `human_label` verbatim labels, `FIX_HINTS`/`COPY` tables, `counter_text`; **AST purity: zero arithmetic-operator nodes, forbidden-call scan, import whitelist** (19) |
| `tests/test_ui_app.py` | `streamlit.testing.v1.AppTest` rendering/interaction contract: empty state + five-button inventory + visible labels + skip link; TV7 happy path (canonical strings + gap sub-label); result replacement; stale results dimmed; V16/V6/V8/V4 error states (verbatim message + translated label + fix hint); no-traceback / hostile input; last-resort guard (unexpected exception → generic state, no class/message/forbidden tokens; `st.rerun` not a fault); Add/Remove/Reset-weights actions; two-click Reset; Add disabled at 100 (19; skipped if Streamlit is absent) |
| `tests/test_security_audit.py` | **Implemented (2026-08-26).** Runs `scripts/security_audit.py` over the source tree (subprocess, never `shell=True`); asserts zero findings (forbidden constructs **and** import policy) + CLI contract (exit code = finding count, usage error = 2); negative controls: 11 planted violations each detected with the matching rule; `requirements.txt` pins exactly the validated Streamlit version (7) |
| `tests/test_export.py` *(future)* | Round-trip formatter checks; CSV-injection guard cases |

**No coverage tool** (dependency discipline); the test-vector discipline, the mirror principle, and the changelog's vector column substitute.

## 11. Extension strategy

How each future capability lands **without touching the core** (F1–F4, C1–C5, the domain model, and the import policy remain stable):

| Future capability | Lands in | Core impact | Gate |
|---|---|---|---|
| Research-mode feature (any of M1–M4, M7, M9, if approved) | `universality/research/<name>.py` + `tests/test_research_<name>.py` | `services` gains a dispatch branch; the feature's formulas are registered in `FORMULA_SPECIFICATION.md` **before** implementation (lane rule: verify → contract → approval → implement + vectors) | M-gate + contract change |
| Export (CSV/JSON) | `universality/export.py` (pure) + UI download button + `tests/test_export.py` | None (additive module). **Must land with the CSV-injection guard** (§12). Export precision (4 dp per A6 vs full precision) is a decision at that task's start — not invented here | Task approval |
| Diagnostics growth (metrics, telemetry) | `universality/infrastructure/diagnostics/` (graduation of the module) | None; `services` calls stay the same | Task approval |
| Persistence / database | `universality/infrastructure/persistence/` implementing a port defined in `services` (dependency inversion); **documented, scoped exception** to the import policy: the adapter may import the port + `domain` | One listed exception in §6, added with the M8 approval | M8; parameterized queries only; re-validate on load |
| Headless CLI (optional) | `universality/__main__.py` — JSON in / JSON out, stdlib only | None | Optional; candidate, not MVP |
| UI | `ui/app.py` (Streamlit; composition root; binds `0.0.0.0` for preview environments) | None | **Implemented 2026-08-26** (see §16) |
| Packaging (`pyproject.toml`) | Repository root | None — the project runs from the repository root until a non-root consumer appears | When needed |
| Any new dependency | — | — | The four-step rule in the README (stdlib first), always |

## 12. Security boundaries

**Trust zones:**
1. **UI** — the untrusted-input origin. Everything crossing this boundary is data, nothing is trusted.
2. **Validation gate** (`validation.py`) — the single authority (V1–V21, validation order, input limits per A3/A10/A11/A15/A20/A21). UI hints never replace it.
3. **Core** (`domain.py`, `calculation.py`, future `research/*`) — trusted, pure, no I/O; receives only validated, frozen data.
4. **Output plane** (display via `format_for_display`; future `export.py`) — derived data. Export output is **data, never code**: the CSV-injection guard is mandatory at export landing — string fields whose rendered value would begin with `=`, `+`, `-`, or `@` must be rejected or neutralized (OWASP CSV injection). **This is a candidate rule (proposed as V15 for the export task)**; it is not added to the V-table silently — the V-table belongs to `validation-and-security.md` and changes only through change control.
5. **Diagnostics plane** — redacted logs only (exception class, traceback, stage, schema field names; never values or parameter names).

**Enforcement (machine + process):**
- `scripts/security_audit.py` (stdlib `ast`) — **implemented 2026-08-26 (security audit task)**: (a) forbidden constructs per `validation-and-security.md` — `eval`/`exec`/`compile`/`__import__`/`input` calls, `os.system`/`os.popen`, `pickle`/`subprocess`/`importlib` imports, any `shell=True`; (b) the import policy of §6 (exhaustive edge table; fail-closed for unlisted modules; no third-party except the documented `streamlit` exception in `ui/app.py` and `tests/*`). Run in every test run via `tests/test_security_audit.py` and in CI/pre-commit.
- Process: the security review is step 7 of the protocol in `ai/ai-guidelines.md`; this section plus the V-table are the checklist.

**State rule:** no global mutable business state anywhere. The single documented exception is the stdlib `logging` handler registry (framework state), configured exactly once, idempotently, in `diagnostics.py`.

**Future data stores (M8, gated):** parameterized queries only; stored data is untrusted input and is re-validated on load.

## 13. Hard boundaries (violation = architectural defect)

1. UI code never contains mathematical business logic.
2. Business logic never imports Streamlit or any other UI framework.
3. A calculation exists in **exactly one place**: `universality/calculation.py` (doc-side authority: `FORMULA_SPECIFICATION.md`). Any second implementation of any formula is a defect, in any layer.
4. `calculation.py` is pure: no I/O, no global state, deterministic; independently executable and testable without a UI.
5. No global mutable business state (sole exception: stdlib logging handlers, §12).
6. Presentation rounding (A6) happens in exactly one place: `services.format_for_display`; it never reaches `calculation`.
7. Imports occur only per the permitted-edge table (§6); cycles are defects; the UI imports the package public API only.
8. Research modules are importable only from `services` (lane discipline, §11); no research feature ships without its M-gate and contract entry.

## 14. Single source of truth

- **Formulas:** `docs/FORMULA_SPECIFICATION.md` — exactly one such document (supersedes `computational-model.md`, now a redirect).
- **Assumptions:** `docs/ASSUMPTIONS.md` (supersedes `application-assumptions.md`).
- **Research claims & bibliography:** `docs/RESEARCH_BASIS.md` + `docs/REFERENCES.md` (supersede `research-methodology.md`).
- **Negative contract:** `docs/LIMITATIONS.md` — must-NOT-implement M1–M10, ambiguities U1–U8.
- **Validation & security contract:** `docs/validation-and-security.md`.
- **Architecture:** this file.

Code may *implement* these documents but never *redefine* them. Redefinition is a documentation change and follows change control.

## 15. Reuse check — responsibility → owner (no duplicate modules)

Per the rule "check whether an existing file already owns a proposed responsibility; reuse it":

| Responsibility | Existing owner before this design? | Decision |
|---|---|---|
| Calculation engine (F1–F4) | Yes — `universality/calculation.py` (prior proposed layout) | **Reused** |
| Domain model | Yes — `universality/domain.py` | **Reused** |
| Validation gate | Yes — `universality/validation.py` | **Reused** |
| Orchestration + error mapping | Yes — `universality/services.py` | **Reused** |
| Calculation/validation tests | Yes — `tests/test_calculation.py`, `tests/test_validation.py` | **Reused** |
| UI | Yes — `ui/app.py` | **Reused** (implemented 2026-08-26) |
| Public API surface | Yes — `universality/__init__.py` | **Reused** (re-export spec added) |
| Diagnostics | No module owner (the brief names a DIAGNOSTICS layer; the prior proposed layout named no file) | **New:** `universality/diagnostics.py` — purpose: brief-mandated safe logging of unexpected errors with redaction |
| Orchestration/error-flow tests | No existing test file owned them | **New:** `tests/test_services.py` |
| Future export | None | **New (deferred):** `universality/export.py` — purpose: supported future capability, pure formatters only |
| Future research mode | None | **New (deferred):** `universality/research/` — purpose: the governed lane defined in `METHODOLOGY.md` |
| Security-review tooling | None | **New (implemented 2026-08-26, security audit task):** `scripts/security_audit.py` + `tests/test_security_audit.py` — purpose: machine-checkable forbidden-construct and import-policy checks (stdlib only) |

## 16. UI task — implementation notes

- **Status: implemented 2026-08-26** in `ui/app.py` (Streamlit composition root) + `ui/ui_model.py` (pure presentation model) + `ui/fonts/` (self-hosted font convention). The four flagged deviations from the design contract (Streamlit `number_input` silent-clamp → score `max_value = SCALE_MAX`; `st.rerun()` render-order pattern; base64 data-URI fonts; `width="stretch"` replacing the deprecated `use_container_width`) are recorded in `docs/UI_ARCHITECTURE.md` §4.1 and in `docs/changelog.md`; each is regression-pinned by `tests/test_ui_app.py` / `tests/test_ui_model.py`.
- **Design contract (created 2026-08-26):** `docs/DESIGN_SYSTEM.md` (visual), `docs/UI_ARCHITECTURE.md` (structure, state, error-path mapping, flagged decisions D-UI-1…D-UI-9), `docs/UX_FLOW.md` (flows, state machine, copy), `docs/ACCESSIBILITY.md` (WCAG 2.1 AA). The implementation conforms to these four documents and the notes below; any deviation is a change-control item.
- Framework: Streamlit (the framework the project brief anticipates).
- The UI is the **composition root**: it builds the call into `services.evaluate` and renders the outcome; it owns no state beyond what Streamlit provides per session.
- The UI must display: the declared scale (A3), parameter weights with the 1/n default (A2), group weights 1/3 each (A1, imported from the public API — never hardcoded), results via `format_for_display` (A6), the as-given-scores note (A4), and the A7 statement that the tool is a simplified implementation, not a full reproduction of the research methodology.
- Server-side (Application-layer) validation is the only authority; UI hints never replace it.
- Servers bind `0.0.0.0` for preview environments; no host/origin allowlist may reject the preview host.
