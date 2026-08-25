# References — bibliography and verification log

Purpose: the complete, current bibliography of everything the project's claims rest on, with access status, what each source actually establishes, and the log of verification work performed. Citation style: numbered, stable. Do not renumber; add new entries.

## Primary research sources

### [S1] Singh & Tandon (2016)
- **Citation:** Singh, R., & Tandon, P. (2016). User values based evaluation model to assess product universality. *International Journal of Industrial Ergonomics*, 55, 46–59.
- **Access (2026-08-25):** public abstract only. Full text **not** available to this repository.
- **Establishes (from the abstract):** R1, R2, R4, R5 (see `RESEARCH_BASIS.md`).
- **Does NOT establish (at current access level):** the exact formulas, the parameter list, the satisfaction scale, AHP usage, Kano usage, statistical procedures, group weights. These remain [P-UNVERIFIED] (U1–U7).

### [S2] Singh & Tandon (2018)
- **Citation:** Singh, R., & Tandon, P. (2018). Framework for improving universal design practice. *International Journal of Product Development*, 22(5), 377–407.
- **Access (2026-08-25):** bibliographic record only.
- **Establishes:** the existence of a companion framework paper in the same research line.
- **Does NOT establish:** any content claim — none has been made from it.

### [S3] Research-line literature (group labels)
- **Citation:** Public literature of the Singh–Tandon research line, e.g., "An approach to enhance product universality using vague numbers during initial design phase," *Proceedings of the Design Society* (2021).
- **Access (2026-08-25):** open access.
- **Establishes:** R3 — the group labels **Fully Abled People (FAP), Specially Abled People (SAP), Differently Abled People (DAP)**.
- **Does NOT establish:** any formula or method detail.

## Project sources

### [B1] Project brief
- **Citation:** Universality Index Tool — project brief (role specification), provided by the user, 2026-08-25.
- **Access:** available in full.
- **Establishes ([P-BRIEF]):** the formulas F1–F3 and their primary-formulation form, constraints (weight sums, ranges), Simple Mode semantics (1/3 group weights, visibility requirement, no AHP), the security contract, the numerical rules, the error-handling rules, and the mandated three-layer distinction (research / simplified implementation / application assumptions).
- **Does NOT establish:** anything about the research itself — [P-BRIEF] is authoritative as a project requirement, not as evidence about [S1]/[S2].

## Standard-literature sources (general methods)

### [M1] Kano model
- **Citation:** Kano, N., et al. (1984). Attractive Quality and Must-Be Quality. *Journal of the Quality Management Association of Japan*. (standard literature)
- **Access (2026-08-25):** standard literature; cited from the literature, not from this project's sources.
- **Establishes:** K1 — the Kano model as a general attribute-classification method (must-be, one-dimensional, attractive, indifferent, reverse).
- **Does NOT establish:** any connection to [S1] or [S2] (U8). **Nothing Kano-related may be implemented** (M2).

### [M2] Analytic Hierarchy Process
- **Citation:** Saaty, T. L. (1980). *The Analytic Hierarchy Process.* McGraw-Hill. (standard literature)
- **Access (2026-08-25):** standard literature; cited from the literature, not from this project's sources.
- **Establishes:** K2 — AHP as a general method (pairwise comparison on a 1–9 scale, priority vector, consistency check).
- **Does NOT establish:** any use of AHP in [S1] or [S2] (U4). **No AHP computation may be implemented** (M1).

## Verification log

| Date | Work performed | Method | Result |
|---|---|---|---|
| 2026-08-25 | Confirmed existence and abstract of [S1]; confirmed bibliographic record of [S2]; located open-access [S3] for group labels; confirmed [M1]/[M2] as standard literature | Public literature search (abstracts, open-access pages, faculty/citation records) | R1–R5, K1, K2 established; U1–U8 registered as open |
| 2026-08-25 | Audited 12 methodology concepts against the sources above; produced methodology map (`METHODOLOGY.md`), formula map (`FORMULA_SPECIFICATION.md`), assumptions (A1–A17 in `ASSUMPTIONS.md`), ambiguities (U1–U8) and must-not list (M1–M10) in `LIMITATIONS.md` | Documentary audit | All 12 concepts dispositioned; no claim promoted beyond its source |

## Upgrade path

To raise a source's access level (e.g., [S1] abstract → full text):

1. Obtain the full text (licensed copy or author-provided copy).
2. Record the access change in the entry above with a date.
3. Cross-check each relevant [P-UNVERIFIED] claim (U1–U8) line by line.
4. Update `RESEARCH_BASIS.md` (claim register), `LIMITATIONS.md` (ambiguities/must-not gates), and this file (verification log).
5. Record a `changelog.md` entry. Formula changes, if any, additionally require test vectors and explicit approval.
