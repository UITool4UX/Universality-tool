# Calculation test vectors — implementation map and verification worksheet

Companion to `tests/test_calculation.py`. **Canonical vector values are owned by `docs/FORMULA_SPECIFICATION.md`** (single source of truth); this document maps each vector to its test(s) and holds the hand-verification worksheet. It does not restate vector values except inside the derivation worksheet, which is a computation, not a second specification.

**Vector levels.** Most vectors are constructed directly on the domain (engine-level; the engine's domain is `0 ≤ s ≤ scale_max`, C3). The user-input validation gate is stricter since A20 (2026-08-25, explicit user instruction): `1 ≤ s ≤ scale_max`. Vectors containing score 0 (TV3, and the DAP 0 of TV5) remain valid **engine** inputs but are not producible from user input through `validation.validate`. **TV7 is user-constructible** and is exercised end-to-end through the full `validate` → `compute` pipeline in `tests/test_integration.py`.

## Vector → test map

| Vector | Protects | Test(s) in `tests/test_calculation.py` |
|---|---|---|
| TV1 (scale 5, 1/2 weights, mixed scores) | F1, F2, F3, F4 end-to-end; tolerance discipline | `TestNormalizationF1` (quotients), `TestGroupIndexF2.test_tv1_group_indices`, `TestOverallF3.test_tv1_overall`, `TestGroupGapF4.test_tv1_gap`, `TestEndToEndVectors.test_tv1_mixed_scores_all_fields` |
| TV2 (all scores at maximum) | Perfect scores; `UI = 1` within tolerance; gap 0 | `TestEndToEndVectors.test_tv2_perfect_scores_bit_exact_with_halves` (w = 0.5/0.5 ⇒ every operation bit-exact: indices `== 1.0`, gap `== 0.0`) |
| TV3 (all scores zero) | Minimum scores; bit-exact zeros | `TestEndToEndVectors.test_tv3_minimum_scores_bit_exact_zero` |
| TV4 (single parameter) | `n = 1`; gap 0 exact | `TestEndToEndVectors.test_tv4_one_parameter` |
| TV5 (hand-verifiable reference case) | Unequal parameter weights (0.7/0.3) **and** unequal group weights (0.5/0.3/0.2); F4 | `TestEndToEndVectors.test_tv5_hand_verifiable_case`, `TestOverallF3.test_tv5_unequal_user_group_weights`, `TestParameterContributions.test_tv5_contributions` |
| TV6 (no-clamping behavior) | No clamping of valid C1-tolerated inputs; rejection (not clamping) of invalid ones | `TestTv6NoClamping.test_valid_c1_tolerated_weights_are_not_clamped`, `TestTv6NoClamping.test_invalid_weight_sum_is_rejected_not_clamped`, `TestTv6NoClamping.test_out_of_range_score_is_rejected_not_clamped`; pipeline-level: `tests/test_edge_cases.py::TestNoClampingEndToEnd` |
| TV7 (pipeline reference case, user-constructible) | F1–F4 end-to-end through `validate` → `compute`; weight traceability; product metadata | `tests/test_integration.py::TestPipelineVectors.test_tv7_accessible_chair_pipeline` |

## Additional implementation vectors (derived in-test, not in the contract)

| Vector | Protects | Test |
|---|---|---|
| n = 100, all scores at scale midpoint (5 of 10) | Many parameters; exact 0.5 quotients; gap exactly 0.0; `len(parameters) == 100` | `TestEndToEndVectors.test_many_parameters_midpoint_vector` |
| n = 100, non-symmetric pattern `(i·7, i·5, i·3) mod 11` | Documented bounds (indices ≤ 1 + EPSILON, overall ≤ 1 + 2·EPSILON); bit-exact contributions identity | `TestEndToEndVectors.test_many_parameters_bounds_and_identity` |
| w = 0.7/0.2/0.1; scores 10/0/10, 0/10/0, 5/5/5 (scale 10) | Unequal parameter weights; hand: UI_F 0.75, UI_S 0.25, UI_D 0.75, UI 7/12, gap 0.5 | `TestEndToEndVectors.test_unequal_parameter_weights_derived_case` |
| w = 0.3333333333333333 ×2 + 0.3333333333333334; all scores at max | Decimal parameter weights; the sum is exactly 1.0 in IEEE-754 ⇒ indices bit-exact `== 1.0` | `TestEndToEndVectors.test_decimal_parameter_weights_bit_exact_sum`; decimal group weights: `TestOverallF3.test_decimal_group_weights_accepted` |
| Scales 3, 7, 100 (2→2/3, 5→5/7, 42→0.42) | Alternate Likert scales; full-precision quotients (no 4-dp rounding) | `TestNormalizationF1.test_f1_alternate_likert_scales` |
| w = 1/3 ×3 (scale 5, mixed scores) | C1 tolerance path: accepted sum, documented results (UI_F 2/3, UI_S 3/5, UI_D 8/15, UI 3/5, gap 2/15) | `TestFloatingPointTolerance.test_c1_tolerance_boundary` |
| 0.1 + 0.2 ≠ 0.3 (FP fact) + weights 0.1/0.2/0.7 | Why C1 is a tolerance check, never `==` | `TestFloatingPointTolerance.test_why_tolerances_are_required` |
| Invalid inputs: NaN/±inf/bools/non-numbers; scores out of scale domain; scale 1/101/float/bool; weight sums 0.95/1.2/1+5e−8; group weights of length 0/2/4, negative, NaN, bool, string, None | Rejection everywhere; never clamped, never repaired | `TestNormalizationF1.test_f1_rejects_invalid_inputs`, `TestOverallF3.test_overall_index_rejects_invalid_group_weights`, `TestGroupIndexF2.test_group_index_rejects_invalid_evaluation_type`, `TestParameterContributions.test_parameter_contributions_rejects_invalid`, `TestGroupGapF4.test_gap_range_and_invalid_type` |
| Repeated computation | Determinism: bit-identical results (`==` on all fields) | `TestDeterminismAndPurity.test_repeated_computation_is_bit_identical` |
| `UI_G == Σᵢ contribution(i, G)` | Bit-exact structural identity (documented in the engine spec) | `TestGroupIndexF2.test_group_index_equals_stored_contributions_bit_exact`, `TestEndToEndVectors.test_many_parameters_bounds_and_identity` |
| Engine imports & constructs | Stdlib + `universality.domain` only; no pandas/numpy/streamlit; no eval/exec/pickle/os/subprocess identifiers | `TestDeterminismAndPurity.test_engine_imports_are_domain_plus_stdlib_only`, `test_engine_contains_no_forbidden_constructs` |

Run: `.venv/bin/python -m unittest discover -s tests` (full suite as of 2026-08-26: 280 tests — 58 domain + 40 calculation + 69 validation + 14 integration + 9 property + 25 edge-case + 20 services + 9 diagnostics + 19 ui_model + 17 ui_app). System Python without Streamlit runs the same 280 with the 17 AppTest UI tests skipped.

## Hand-verification worksheet — TV5 (the independently hand-verifiable case)

Every value below is an **exact terminating decimal**, so the whole case can be verified with ordinary decimal arithmetic — no floating-point reasoning required.

**Inputs:** scale_max = 10 · parameters A (w = 0.7) and B (w = 0.3) · group weights W_F = 0.5, W_S = 0.3, W_D = 0.2.

**Step 1 — normalize (F1):**

| Parameter | Group | Score | ÷ 10 = s_norm |
|---|---|---|---|
| A | FAP | 10 | 1.0 |
| A | SAP | 5 | 0.5 |
| A | DAP | 0 | 0.0 |
| B | FAP | 4 | 0.4 |
| B | SAP | 8 | 0.8 |
| B | DAP | 6 | 0.6 |

**Step 2 — parameter contributions (F2 summands, w · s_norm):**

| Parameter | FAP | SAP | DAP |
|---|---|---|---|
| A (w = 0.7) | 0.7 · 1.0 = **0.70** | 0.7 · 0.5 = **0.35** | 0.7 · 0.0 = **0.00** |
| B (w = 0.3) | 0.3 · 0.4 = **0.12** | 0.3 · 0.8 = **0.24** | 0.3 · 0.6 = **0.18** |

**Step 3 — group indices (F2, sum the column):**

- UI_F = 0.70 + 0.12 = **0.82**
- UI_S = 0.35 + 0.24 = **0.59**
- UI_D = 0.00 + 0.18 = **0.18**

**Step 4 — overall (F3):**

UI = 0.5 · 0.82 + 0.3 · 0.59 + 0.2 · 0.18 = 0.41 + 0.177 + 0.036 = **0.623**

**Step 5 — user-group gap (F4):**

group_gap = max(0.82, 0.59, 0.18) − min(0.82, 0.59, 0.18) = 0.82 − 0.18 = **0.64**

**Check:** all intermediate products (0.70, 0.35, 0.12, 0.24, 0.18, 0.41, 0.177, 0.036) and all sums terminate in decimal, so a person can reproduce 0.82 / 0.59 / 0.18 / 0.623 / 0.64 by hand and confirm the engine's output (compared in tests with a `1e−12` tolerance).
