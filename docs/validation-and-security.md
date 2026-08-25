# Validation and security contract

Purpose: define exactly what input the application accepts, what it rejects, how rejections are phrased, and which constructs are forbidden in this codebase. Applies to every layer that touches user input. The **APPLICATION layer is the single authoritative validation point**; UI hints never replace it.

**Implemented 2026-08-25 (validation task):** `universality/validation.py` — `validate(raw) -> Evaluation` (fail-fast; first violated rule wins) and `validate_group_weights(...)`; rejections raised as `ValidationRejection(code, field, message)`.

## Trust model

- Every user input is **untrusted**.
- Server-side (APPLICATION-layer) validation is the only authority, even though UI validation may exist.
- The application **never** silently repairs invalid research data, **never** normalizes an incorrect weight total (a total of 0.96 is an error — it is rejected, never rescaled to 1), **never** converts a missing value to zero, and **never** treats a missing score as a valid satisfaction score.
- Names (product and parameter) are stored **exactly as provided** — never trimmed, normalized, or corrected.

## Raw input schema

Plain primitives only. The UI passes a JSON-like `dict`; the raw `dict` exists **only** at the Application entry point (`architecture.md` §7).

| Key | Type | Rule |
|---|---|---|
| `product` | `str` | Required (V16/V17/V18; A21): 1–100 characters, no control characters, at least one non-whitespace character |
| `scale_max` | `int` | Required (V7); `2 ≤ scale_max ≤ 100` (V3/V11; A3) |
| `parameters` | `list` | 1–100 entries (V7/V19/V12; A11) |
| `parameters[i].name` | `str` | 1–100 characters, no control characters, non-whitespace; unique case-insensitively after trimming (V7/V19/V9/V10/V8; A10/A18) |
| `parameters[i].weight` | number | finite, not boolean, `0 ≤ w ≤ 1`; parameter weights sum to 1 ± EPSILON (V7/V3/V13/V1/V2/V5/V6; C1/C5) |
| `parameters[i].scores` | object with `fap`, `sap`, `dap` | all three required (V7/V19/V14; A15); each a finite, non-boolean real with `1 ≤ s ≤ scale_max` (V3/V13/V1/V2/V4; A20) |

Unknown keys at any level are **ignored** (not rejected, not used). Group weights are **not** part of the raw input in Simple Mode (A1, A8; gate M5) — see "Group weights" below.

## Rejection table

Each item must produce a friendly, specific validation message naming the rule and the offending field. Never a stack trace, never a raw internal error. **Message format:** the theme below, with the offending field named in the message; `ValidationRejection.message` is displayed to the user verbatim.

| ID | Rejected input | Error category (message theme) |
|---|---|---|
| V1 | NaN in any numeric field | "Invalid number: value must be a real number." |
| V2 | ±Infinity in any numeric field | "Invalid number: value must be finite." |
| V3 | Boolean where a number is expected (e.g., `true` as a score, weight, or scale) | "Invalid number: expected a number, not a boolean." |
| V4 | Score < 1 or score > scale_max. **Changed 2026-08-25 by explicit user instruction (A20); previously "Score < 0"** | "Out-of-range score: scores must lie between 1 and the declared scale maximum." |
| V5 | Weight < 0 or weight > 1 (w(i) or W(G)). **Range made explicit 2026-08-25, aligning the rule with C5 and the input limits (previously stated as negative only)** | "Invalid weight: weights must be between 0 and 1." |
| V6 | Parameter weights whose sum deviates from 1 by more than EPSILON. **Never normalized — a total of 0.96 is this error** | "Invalid weights: parameter weights must sum to 1." |
| V7 | Missing required field (product name, parameter name, weight, scale_max, parameter list) — key absent or `null` | "Missing value: <field> is required." |
| V8 | Duplicate parameter name (case-insensitive after trimming, A10) | "Duplicate parameter name: '<name>' is already used." |
| V9 | Parameter name longer than 100 characters (A10) | "Input too long: parameter names must be at most 100 characters." |
| V10 | Control characters in a parameter name (exact set, A18: C0 U+0000–U+001F, DEL U+007F, C1 U+0080–U+009F) | "Invalid characters: parameter names must not contain control characters." |
| V11 | scale_max not a positive integer in [2, 100] (A3) — including floats, strings, and booleans | "Invalid scale: the scale maximum must be a whole number between 2 and 100." |
| V12 | Parameter count n outside [1, 100] (A11) | "Invalid evaluation: between 1 and 100 parameters are required." |
| V13 | Non-real value where a number is expected (e.g., a non-numeric string, a complex number) | "Invalid number: expected a real number." |
| V14 | A parameter missing a score for any of FAP, SAP, DAP (A15) — key absent or `null` | "Missing value: every parameter needs a score for each of the FAP, SAP, and DAP groups." |
| **V15** | **Reserved** — candidate CSV-injection guard for the future export layer (changelog 2026-08-25, "Production architecture finalized"; `architecture.md` §12). Not a validation-layer rule. | — |
| V16 | Product name missing or blank (A21) | "Missing value: product name is required." |
| V17 | Product name longer than 100 characters (A21) | "Input too long: product name must be at most 100 characters." |
| V18 | Control characters in the product name (A21; exact set per A18) | "Invalid characters: product name must not contain control characters." |
| V19 | Structural type error: input not an object; `parameters` not a list; a parameter entry or `scores` not an object; a name or the product not text | "Invalid input: <field> has an unexpected format." |
| V20 | Group weights not exactly three numbers (defensive gate — see "Group weights") | "Invalid weights: group weights must be exactly three numbers." |
| V21 | Group weights whose sum deviates from 1 by more than EPSILON (defensive gate — see "Group weights") | "Invalid weights: group weights must sum to 1." |
| V-UNEXPECTED | Internal safety net: a domain invariant fires *after* the gate (a bug; unreachable from documented input). Not part of the public table | "Something went wrong. Please try again." |

**Validation order (first violated rule wins):**
structural — input object (V19) → product (V16 → V17 → V18) → scale_max presence (V7) → parameter container (V7 → V19 → V12) → per parameter: object (V19), name (V7 → V19 → V7 blank → V9 → V10), weight presence (V7), scores object (V7 → V19) —
domain — scale value (V3 → V11) → per parameter in order: weight value (V3 → V13 → V1 → V2 → V5), then scores in order fap → sap → dap (V14 → V13 → V1 → V2 → V4) → duplicate names (V8) → parameter weight sum (V6) → group weights (V20 → per-element rules → V21) —
construction (safety net: V-UNEXPECTED).

## Group weights

Group weights are **not user input** in Simple Mode: fixed at W_F = W_S = W_D = 1/3 (A1, A8); editability is gated (M5). The sum-to-1 rule (C2) is nevertheless enforced and testable at the application gate: `validation.validate_group_weights(...)` is the **single validator** (V20/V21 + per-element value rules); the application layer applies it to the group weights it uses (Simple Mode: the constant `SIMPLE_MODE_GROUP_WEIGHTS`, defensively re-validated on every `validate` call), and the calculation engine re-asserts C2 as a boundary guard. One rule, no behavior change, no mode opened.

## Error-handling contract

1. **Expected errors** (the V-table) → friendly, specific messages. No stack traces, no internal details.
2. `validate` never lets any exception other than `ValidationRejection` escape, for any input. The construction safety net maps an internal `DomainInvariantError` (a bug, unreachable on validated input) to the generic V-UNEXPECTED message rather than exposing an internal exception.
3. **Unexpected exceptions** outside `validate` (e.g., in calculation) → caught at the APPLICATION boundary (`services.evaluate`, implemented 2026-08-26), logged via DIAGNOSTICS (redacted: class, class chain, and safe stack frames `file:line:function` only — never raw user data, never the exception message line, never source lines), and reported to the user as the generic "Something went wrong. Please try again." message.
4. No silent repair, no guessing, no imputation of invalid research data, ever.

## Forbidden constructs (any layer, for any reason)

| Forbidden | Rationale |
|---|---|
| `eval()`, `exec()` | Arbitrary code execution |
| `pickle.loads()`, `pickle.load()` | Unsafe deserialization |
| `os.system()`, `subprocess` with `shell=True` on user-derived content | Shell injection |
| Dynamic imports or dynamic code generation driven by user input | Code injection |
| Executable code constructed from user input, in any form | Code injection |
| SQL constructed from user input (if a database is ever introduced) | SQL injection — parameterized queries only |

**Machine enforcement (implemented 2026-08-26, security audit task):** `scripts/security_audit.py` (stdlib `ast`; owner: `docs/architecture.md` §5/§12) checks these constructs — plus any `shell=True`, `pickle`/`subprocess`/`importlib` imports, and the §6 import policy — on every test run via `tests/test_security_audit.py`.

## Input limits (application choices — see `ASSUMPTIONS.md`)

- product name: 1–100 characters, no control characters (exact set A18), at least one non-whitespace character, stored as provided (A21)
- `scale_max`: integer, `2 ≤ scale_max ≤ 100` (A3)
- score: finite real; **user input: `1 ≤ score ≤ scale_max` (A20)**; engine/formula domain: `0 ≤ score ≤ scale_max` (C3) — the engine still accepts 0 (engine-level test vectors such as TV3), but the validation gate never produces it
- weight: finite real, `0 ≤ weight ≤ 1` (C5)
- parameter name: 1–100 characters, no control characters, unique (A10)
- parameter count: `1 ≤ n ≤ 100` (A11)
- group coverage: scores for all three groups required per parameter (A15)
- group weights: not user input (A1, A8); C2 enforced by validator + constant + engine guard

## Persistence (future, A13)

If storage is ever added: parameterized queries only; stored data is untrusted input and is re-validated on load; no raw user data in logs.
