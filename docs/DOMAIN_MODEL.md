# Domain model — field-level authority

Purpose: the single field-level specification of the domain model. Implemented in `universality/domain.py` (2026-08-25). Architecture context (bands, import policy): `architecture.md` §5/§8.

**Status: implemented.** Every field below has: type, meaning, valid range, and required/optional status. All fields are **required** — there are no optional fields in the domain model (absence is represented structurally, e.g. by `GroupScores` having exactly three mandatory fields, not by `Optional`).

## Invariant split (read first)

Two distinct, non-overlapping constraint mechanisms:

1. **Type invariants** — enforced at construction in `universality/domain.py`, violations raise `DomainInvariantError` (a `ValueError` subclass). These make illegal states *unrepresentable*: a `Score` is always finite and ≥ 0; a `Weight` is always in [0, 1]; an `Evaluation` always satisfies C1, C3-domain, and the A10 name rules.
2. **User-input validation** — `universality/validation.py` (**implemented 2026-08-25**) is the **single authoritative gate** for raw input, raising `ValidationRejection` with V-coded friendly messages (V1–V21, V15 reserved for export; `validation-and-security.md`). It runs *before* domain objects are constructed, so `DomainInvariantError` is unreachable from user input in production; if it ever occurs, it is a bug and takes the unexpected-error path (the gate's safety net maps it to the generic V-UNEXPECTED message).

**Single implementation:** the C1/C2 sum check is implemented exactly once — `domain.weights_sum_is_valid(values, target=1.0, epsilon=EPSILON) -> bool` — and is shared by `Evaluation` (now) and `validation.py` (later). No constraint predicate exists in two places.

**No formulas:** F1–F4 live exclusively in `universality/calculation.py` (implemented 2026-08-25). The result types below *carry* F1/F2/F3/F4 outputs as data; they compute nothing. Domain methods are limited to shape navigation (e.g. `for_group`) — no arithmetic.

## Types

### `UserGroup` (enum)

The three ability/needs user groups (R2, R3).

| Member | Value | Meaning |
|---|---|---|
| `FAP` | `"FAP"` | Fully Abled People |
| `SAP` | `"SAP"` | Specially Abled People |
| `DAP` | `"DAP"` | Differently Abled People |

Property: `label -> str` — the display name (research label, R3). Data, not computation. Enums are immutable by construction.

### `KanoCategory` (enum)

Kano-model attribute classes (K1 / [M1] — standard literature).

| Member | Value | Meaning (Kano model) |
|---|---|---|
| `MUST_BE` | `"must_be"` | basic / must-be quality |
| `ONE_DIMENSIONAL` | `"one_dimensional"` | performance / one-dimensional quality |
| `ATTRACTIVE` | `"attractive"` | delighter quality |
| `INDIFFERENT` | `"indifferent"` | indifferent attribute |
| `REVERSE` | `"reverse"` | reverse attribute |

**Scope (M2 note, 2026-08-25):** this is **inert vocabulary only** — approved by explicit user instruction for the domain model. No classification or scoring logic exists, F1–F4 do not reference this type, and it is not attached to any other model. Any Kano *behavior* remains gated (M2); an attachment point, and that field's required/optional status, will be defined by the M2 contract change.

### `Score` (frozen dataclass)

Observed satisfaction score for one (parameter, group) pair.

| Field | Type | Meaning | Valid range | Required |
|---|---|---|---|---|
| `value` | `float` | Observed score on the evaluation's scale | finite; ≥ 0. Upper bound `≤ scale_max` (C3) is context-dependent — enforced by `Evaluation`, the only type that knows the scale. `int` inputs are stored as the same real number (float); booleans, NaN, ±inf, non-numbers rejected | **Yes** |

### `Weight` (frozen dataclass)

Relative importance of one parameter.

| Field | Type | Meaning | Valid range | Required |
|---|---|---|---|---|
| `value` | `float` | Parameter importance weight (student-provided or 1/n default — A2; the application never generates weights) | finite; `[0, 1]` (C5). Zero allowed (A9). The sum constraint C1 is Evaluation-level, not here | **Yes** |

### `GroupScores` (frozen dataclass)

One parameter's satisfaction scores for all three user groups. Completeness (A15) is guaranteed by construction — no partial state is representable.

| Field | Type | Meaning | Valid range | Required |
|---|---|---|---|---|
| `fap` | `Score` | Score for Fully Abled People | `Score` domain | **Yes** |
| `sap` | `Score` | Score for Specially Abled People | `Score` domain | **Yes** |
| `dap` | `Score` | Score for Differently Abled People | `Score` domain | **Yes** |

Accessor: `for_group(group: UserGroup) -> Score` — shape navigation only.

### `Parameter` (frozen dataclass)

One evaluated product parameter (user value).

| Field | Type | Meaning | Valid range | Required |
|---|---|---|---|---|
| `name` | `str` | Parameter name | 1–100 characters; no control characters (exact set: C0 U+0000–U+001F, DEL U+007F, C1 U+0080–U+009F — A10/A18); ≥ 1 non-whitespace character; stored **as provided** (never trimmed or modified — no silent data change). Uniqueness across an `Evaluation` is checked there (case-insensitive, casefold, after trimming — A10) | **Yes** |
| `weight` | `Weight` | The parameter's importance weight | `Weight` domain | **Yes** |
| `scores` | `GroupScores` | The parameter's scores for all three groups | `GroupScores` domain | **Yes** |

### `Evaluation` (frozen dataclass)

A complete Simple Mode evaluation: product, declared scale + parameters.

| Field | Type | Meaning | Valid range | Required |
|---|---|---|---|---|
| `product` | `str` | Name of the product or service being evaluated (A21, added 2026-08-25, explicit user instruction) | Same name invariants as `Parameter.name` (A18): 1–100 characters; no control characters (exact set A18); ≥ 1 non-whitespace character; stored **as provided** (never trimmed or modified) | **Yes** |
| `scale_max` | `int` | Maximum value of the satisfaction scale, declared per evaluation; one scale applies to all parameters (A3) | `int` (booleans rejected); `[2, 100]` (A3) | **Yes** |
| `parameters` | `tuple[Parameter, ...]` | The evaluated parameters | `1 ≤ len ≤ 100` (A11); names unique (case-insensitive after trimming, A10); weights sum to 1 within EPSILON (C1, via the single predicate); every score `≤ scale_max` (C3) | **Yes** |

**Group weights are intentionally not a field:** Simple Mode fixes W_F = W_S = W_D = 1/3 (A1, A8); that constant lives in `universality/calculation.py`. Editable group weights are gated (M5) and would be a documented model change. The group-weight sum rule (C2) is enforced at the application gate (`validation.validate_group_weights`) and as a calculation-engine boundary guard.

### `PerGroupValue` (frozen dataclass)

A triple of real values, one per user group (result-side container; inputs use `GroupScores` of `Score`).

| Field | Type | Meaning | Valid range | Required |
|---|---|---|---|---|
| `fap`, `sap`, `dap` | `float` | One value per group | Type domain: finite, ≥ 0. Usage-specific upper bounds: as `ParameterResult.normalized` → `[0, 1]` (F1 output domain); as `ParameterResult.contributions` → `[0, 1]` (F2 summand domain); as `EvaluationResult.group_indices` → `[0, 1 + EPSILON]` (C1 tolerance) | **Yes** (all three) |

Accessor: `for_group(group: UserGroup) -> float` — shape navigation only.

### `ParameterResult` (frozen dataclass)

Per-parameter calculation output. Carries **existing** formula outputs as data — F1's output (normalized scores) and F2's per-parameter summands. **No new formula** is introduced; the entire calculation surface is F1–F4 (F4 registered 2026-08-25, explicit user instruction; interpretation A19).

| Field | Type | Meaning | Valid range | Required |
|---|---|---|---|---|
| `name` | `str` | The parameter's name | Same invariants as `Parameter.name` | **Yes** |
| `weight` | `Weight` | The weight used (traceability of contributions) | `Weight` domain | **Yes** |
| `normalized` | `PerGroupValue` | F1 outputs `s_norm(i, G)` per group | each value `[0, 1]` | **Yes** |
| `contributions` | `PerGroupValue` | F2 summands `w(i) · s_norm(i, G)` per group | each value `[0, 1]` | **Yes** |

### `EvaluationResult` (frozen dataclass)

The complete calculation output for one `Evaluation`.

| Field | Type | Meaning | Valid range | Required |
|---|---|---|---|---|
| `group_indices` | `PerGroupValue` | F2 outputs (UI_F, UI_S, UI_D) | each value `[0, 1 + EPSILON]` (C1 tolerance) | **Yes** |
| `overall` | `float` | F3 output (UI) | finite, ≥ 0. In exact arithmetic `[0, 1]` (C4); with the C1/C2 tolerances, floating point stays within `[0, 1 + 2·EPSILON]` — that bound is documented, not strictly asserted, so a legitimate C1-tolerated input cannot trip the type | **Yes** |
| `parameters` | `tuple[ParameterResult, ...]` | Per-parameter results | non-empty; same order and names as the input `Evaluation` (checked in `EvaluationOutcome`) | **Yes** |
| `group_gap` | `float` | F4 output (user-group gap; registered 2026-08-25, explicit user instruction; A19) | finite, ≥ 0. In exact arithmetic `[0, 1]`; with the C1/C2 tolerances, floating point stays within `[0, 1 + EPSILON]` (bound documented, not strictly asserted, as for `group_indices`) | **Yes** |

### `EvaluationOutcome` (frozen dataclass)

The single object crossing the Application→consumer boundary (`architecture.md` §7–8): pairs input with result so consumers (UI, future export) need no global state.

| Field | Type | Meaning | Valid range | Required |
|---|---|---|---|---|
| `evaluation` | `Evaluation` | The evaluated input | `Evaluation` domain | **Yes** |
| `result` | `EvaluationResult` | The calculation output | `EvaluationResult` domain; per-parameter entries match the evaluation's parameters in **count, order, and name** (consistency invariants) | **Yes** |

### `DomainInvariantError` (exception)

`ValueError` subclass. Raised by type invariants only. In production, reachable only via a bug (the validation gate precedes construction).

## Contract items (single locations)

| Item | Value | Location | Contract reference |
|---|---|---|---|
| `EPSILON` | `1e-9` (Final) | `domain.py` | A5; C1/C2. Moved here (from the planned `calculation.py` location) because the domain enforces the C1 invariant; `calculation.py` does not need it |
| `weights_sum_is_valid(values, target=1.0, epsilon=EPSILON)` | predicate | `domain.py` | C1/C2 — exactly one implementation |
| `SIMPLE_MODE_GROUP_WEIGHTS` | `(1/3, 1/3, 1/3)` | `calculation.py` | A1 |
| `SCALE_MIN`, `SCALE_MAX` | `2`, `100` (Final) | `domain.py` | A3 — promoted public 2026-08-25 so the validation gate reuses the single location |
| `NAME_MIN_LENGTH`, `NAME_MAX_LENGTH` | `1`, `100` (Final) | `domain.py` | A10/A18 (A21) — same |
| `PARAMETER_MIN`, `PARAMETER_MAX` | `1`, `100` (Final) | `domain.py` | A11 — same |
| `CONTROL_CHARS` | frozenset: C0 U+0000–U+001F, DEL U+007F, C1 U+0080–U+009F (Final) | `domain.py` | A18 (A21) — same |

## Constraint → contract map

| Invariant | Enforced by | Contract reference |
|---|---|---|
| Score: finite, ≥ 0, not bool/NaN/inf | `Score` | V1/V2/V3/V4 (input side); C3 (type side) |
| Weight: finite, `[0, 1]` | `Weight` | C5; V5 (input side) |
| Group score completeness (all three groups) | `GroupScores` | A15; V14 (input side) |
| Name: 1–100 chars, control-character set, non-whitespace, stored as provided | `Parameter`, `ParameterResult` | A10, A18; V8/V9/V10 (input side) |
| scale_max: int, `[2, 100]` | `Evaluation` | A3; V11 (input side) |
| Parameter count: `[1, 100]` | `Evaluation` | A11; V12 (input side) |
| Name uniqueness (case-insensitive after trim) | `Evaluation` | A10; V8 (input side) |
| Score ≤ scale_max | `Evaluation` | C3; V4 (input side) |
| Σ weights = 1 ± EPSILON | `Evaluation` (via `weights_sum_is_valid`) | C1; V6 (input side) |
| Result ranges (documented, per above) | `PerGroupValue`, `EvaluationResult` | C3/C4; C1 tolerance |
| Outcome consistency (count, order, names) | `EvaluationOutcome` | `architecture.md` §7 |

## Intentionally NOT in the domain

- **Research formulas** F1–F4 — `universality/calculation.py` (implemented 2026-08-25).
- **Group weights** — Simple Mode fixes them (A1, A8); constant in `calculation.py`; editability gated (M5).
- **Kano attachment** — `KanoCategory` is unattached until the M2 gate is satisfied.
- **Raw-input parsing and V-coded rejections** — `universality/validation.py` (implemented 2026-08-25). The domain enforces *type* invariants with `DomainInvariantError`; the APPLICATION layer enforces *user-input* acceptance with friendly `ValidationRejection` messages (V1–V21). Both reuse the same contract constants and the single C1/C2 predicate.
- **User-facing error messages** — `services.py` / UI (implemented 2026-08-26); `validation.py` supplies the friendly V-coded text.
- I/O, time, randomness, global mutable state, UI imports — never.
