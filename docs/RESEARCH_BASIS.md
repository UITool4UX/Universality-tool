# Research basis — verified claims and provenance

Purpose: record **exactly what the research foundation establishes**, with a source attached to every claim. This is the documentary basis for the methodology audit. No claim appears here without a provenance tag.

**Provenance classes:**
- **[P-BRIEF]** — established by the project brief (2026-08-25). Authoritative as a *project requirement*. Its research pedigree is **not** independently verified.
- **[P-PUBLIC]** — verified on 2026-08-25 against a cited public source (see `REFERENCES.md`).
- **[P-UNVERIFIED]** — **not conclusively established** by any source available to this repository. Must never be stated as fact in any document, UI text, or code comment.

## Sources

| # | Citation | Access status (2026-08-25) | Establishes |
|---|---|---|---|
| [S1] | Singh, R., & Tandon, P. (2016). *User values based evaluation model to assess product universality.* International Journal of Industrial Ergonomics, 55, 46–59. | Public abstract only; **full text not available** to this repository | R1, R2, R4, R5 |
| [S2] | Singh, R., & Tandon, P. (2018). *Framework for improving universal design practice.* International Journal of Product Development, 22(5), 377–407. | Bibliographic record only | Existence of a companion framework paper; **no content claims are made from it** |
| [S3] | Public literature of the Singh–Tandon research line, e.g., *Proceedings of the Design Society* (2021), "An approach to enhance product universality using vague numbers during initial design phase" | Open access | R3 (group labels) |
| [B1] | Project brief (2026-08-25), user-provided specification | Available in full | All formulas, constraints, Simple Mode semantics, security and numerical rules ([P-BRIEF]) |
| [M1] | Kano, N., et al. (1984). *Attractive Quality and Must-Be Quality.* Journal of the Quality Management Association of Japan. (standard literature) | Standard literature | The Kano model as a general method — **and nothing else** (see claim K1) |
| [M2] | Saaty, T. L. (1980). *The Analytic Hierarchy Process.* McGraw-Hill. (standard literature) | Standard literature | AHP as a general method — **and nothing else** (see claim K2) |

Full details, verification log, and upgrade path: `REFERENCES.md`.

## Verified claims

| ID | Claim | Source | Class |
|---|---|---|---|
| R1 | The 2016 work proposes a user-values-based evaluation model to assess the universality of a designed product | [S1] abstract | [P-PUBLIC] |
| R2 | The model classifies users into **three groups** based on their abilities and needs | [S1] abstract | [P-PUBLIC] |
| R3 | In this research line the three groups are **Fully Abled People (FAP), Specially Abled People (SAP), and Differently Abled People (DAP)** | [S3] | [P-PUBLIC] |
| R4 | The model analyses the values associated with the individual needs of the different user groups | [S1] abstract | [P-PUBLIC] |
| R5 | Universal design aims to integrate users of all ages and distinct abilities without requiring adaptation or specialized design | [S1] abstract; standard universal-design literature | [P-PUBLIC] |
| K1 | The Kano model is a general product-attribute classification by shape of satisfaction response (must-be, one-dimensional, attractive, indifferent, reverse) | [M1] | [P-PUBLIC] — **with no established connection to [S1] or [S2]** |
| K2 | AHP is a general multi-criteria method (pairwise comparison, priority vector, consistency check) | [M2] | [P-PUBLIC] — **with no established use in [S1] or [S2]** |

## Claim register

Every statement the application might be tempted to make about the research, and its honest status:

| Claim | Status |
|---|---|
| "The tool computes the Universality Index of the Singh & Tandon (2016) model" | **Partially verified** — the three-group structure (R2, R3) is verified. The formula is the project's *simplified implementation* [P-BRIEF], not yet cross-checked against the full text of [S1] |
| "The formula `UI = Σ(wᵢ × sᵢ) / max(S)` is the formula of [S1]" | **UNVERIFIED** (U1, U2) — the formula is [P-BRIEF]; research pedigree unconfirmed |
| "The tool reproduces the research's AHP weight derivation" | **UNVERIFIED as to the research** (U4); **prohibited in the MVP in any case** (M1) |
| "The tool reproduces the research's parameter list" | **UNVERIFIED** (U5) — no parameter list is available; MVP uses student-defined parameters |
| "The tool reproduces the research's satisfaction scale" | **UNVERIFIED** (U6) — the research scale is unknown; the scale is student-declared in the MVP |
| "The research defines group weights W_F, W_S, W_D" | **UNVERIFIED** (U7) — not established by any available source; MVP fixes 1/3 each per the brief |
| "Kano categories are part of the research methodology" | **UNVERIFIED** (U8) — no available source connects Kano to [S1]/[S2]; do not implement (M2) |
| "The tool reproduces the research's statistical procedures" | **UNVERIFIED** — full text unavailable; nothing implemented, nothing claimed (M9) |
| "Interpretation bands such as '0.80 = excellent' come from the research" | **No** — verified in no source; inventing them is prohibited (A12, M3) |
| "The research aggregates individual responses into group scores by <method>" | **UNVERIFIED** (U3) — no aggregation method is established; the MVP takes a single scalar per (parameter, group) (A17) |

## Upgrade path (how a claim becomes verified)

1. Obtain the full text of the cited work (licensed copy or author-provided copy).
2. Cross-check the specific formula/operation/claim against `FORMULA_SPECIFICATION.md` / this register, line by line.
3. If it matches: update the claim register to **Verified**, update `REFERENCES.md` access status, add test vectors where formulas are concerned, and record a changelog entry.
4. If it differs: follow change control — document the discrepancy, do not silently choose a side, propose the smallest correction, and obtain explicit approval before changing any formula.

Until every step above is completed for a given claim, the register keeps the conservative status.
