# Calculation engine — specification

Purpose: the engine specification for `universality/calculation.py` (implemented 2026-08-25). The formula statements themselves live in `FORMULA_SPECIFICATION.md` (F1–F4, referenced by ID only). Test vectors and their mapping to tests: `tests/CALCULATION_TEST_VECTORS.md`.

## Public API

| Member | Kind | Contract |
|---|---|---|
| `SIMPLE_MODE_GROUP_WEIGHTS` | `Final[tuple[float, float, float]]` = (1/3, 1/3, 1/3) | A1 — sole location. The UI displays it via the public API re-export, never hardcodes it |
| `normalize_score(score, scale_max) -> float` | function | **F1** — the only implementation. F1 project domain re-asserted (boundary guard): `2 ≤ scale_max ≤ 100` (int, not bool), finite `0 ≤ score ≤ scale_max` (bools rejected). Violations raise `DomainInvariantError` — never clamped |
| `parameter_contributions(parameter, scale_max) -> PerGroupValue` | function | F2 per-parameter summands `w(i)·s_norm(i, G)` — the values stored in `ParameterResult.contributions` |
| `group_index(evaluation, group) -> float` | function | **F2** for one group: `UI_G = Σᵢ w(i)·s_norm(i, G)` |
| `overall_index(group_indices, group_weights = SIMPLE_MODE_GROUP_WEIGHTS) -> float` | function | **F3** — the only implementation. C2 enforced on the engine surface |
| `group_gap(group_indices) -> float` | function | **F4** — the only implementation |
| `compute(evaluation, group_weights = SIMPLE_MODE_GROUP_WEIGHTS) -> EvaluationResult` | function | Top-level: F1 → F2 → F3 (+ F4). Returns the complete `EvaluationResult` |

## Guarantees (test-enforced)

- **Pure & deterministic:** no I/O, no global state, no time, no randomness. Fixed summation order: parameter input order, left-to-right IEEE-754 addition; group order F → S → D. No set/dict iteration anywhere.
- **Full precision, no rounding:** presentation rounding (A6) belongs to the APPLICATION layer (`services.format_for_display`, implemented 2026-08-26) and never reaches the engine. Test: `normalize_score(5, 7) == 5.0/7.0` bit-exact, `!= round(5/7, 4)`.
- **No clamping, no imputation, no inference:** domain violations raise `DomainInvariantError`. Test TV6: a valid C1-tolerated input produces `UI_G > 1.0` — computed faithfully, not clamped; the invalid counterpart is rejected at construction.
- **Bit-exact structural identity:** `UI_G == Σᵢ contribution(i, G)` — group indices are the left-to-right sum of the stored per-parameter F2 summands, so the identity holds by construction and is asserted with `==`.
- **Single implementation:** each formula (F1–F4) and the C1/C2 sum predicate (`domain.weights_sum_is_valid`) exists in exactly one place. The engine's public entry points re-assert the F1 project domain and C2 as *boundary guards* — that is constraint checking, not formula duplication.
- **Independence:** imports only `universality.domain` + stdlib (`math`, `typing`). No UI, no services, no validation, no I/O modules — test-enforced via `ast`.
- **No pandas/numpy** in the core calculation. Documented reason (dependency policy, step 2): standard-library arithmetic is sufficient for ≤ 100 terms; bit-determinism and dependency discipline are preserved; there is no compelling reason, so no dependency is added.

## Group weights, Simple Mode, and M5

F3 is implemented **exactly as specified**: `W_F, W_S, W_D` are formula inputs. Simple Mode = the default argument `SIMPLE_MODE_GROUP_WEIGHTS` (A1). C2 is enforced on the engine surface: exactly three values, each finite, ≥ 0, non-boolean, summing to 1 within EPSILON via the single domain predicate; violations raise.

Note on M5: user-*editable* group weights remain an application/UI decision (gate M5, unchanged). The engine's `group_weights` parameter is the formula being implemented — it is not a new mode and does not open the gate.

## F4 — user-group gap

Registered 2026-08-25 on **explicit user instruction** ("user-group gap"). The instruction named the concept without a definition; the smallest reasonable definition — the max−min spread of the three group indices — is recorded as assumption **A19** (reviewable). F4 is a derived diagnostic: built solely from F2 outputs, no new normalization or weighting, exact range [0, 1]. Pairwise differences remain trivially derivable from the fully exposed group indices — nothing is hidden.

## What the engine does NOT do

Raw-input validation (`validation.py`, implemented 2026-08-25) · orchestration (`services.py`, implemented 2026-08-26) · presentation rounding (A6, implemented 2026-08-26) · diagnostics (`diagnostics.py`, implemented 2026-08-26) · export (future) · persistence (future) · AHP · Kano.
