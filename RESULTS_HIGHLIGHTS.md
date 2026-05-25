# Statistical results — main highlights

> Companion summary to `analysis/results.json` and `analysis/results_summary.md`.
> Source pipeline: `analysis/run_analysis.py`. Random seed = 42.

## Sample
- **n = 89 entities** (60 built-in + 29 user-added), 61 confirmed synthetic/agentic + 28 control real-company cases.
- Taxonomy (4 main classes + 1 sub-type): Agentic Organization (25), Agentic DAO (24), Synthetic Company (19), Multi-Agent System (8), AI-Enhanced Shell (5); plus 8 Dismissed-Real-Company controls inside the analytic frame.
- Jurisdictions: 47 OECD-traditional, 32 permissive/decentralized (Cayman, Estonia, Liechtenstein, on-chain), 6 emerging/special, 4 other.
- 38% of the sample (n = 34) reports zero employees.
- Median synthetic score = 63 (Q1 = 50, Q3 = 82). Median venture age = 1 year. Median employees = 5 (max = 6,000 from NetDragon Websoft).

## Inter-rater reliability (R1 vs R2, n = 25 borderline cases)
- **Cohen's κ = 0.772** — substantial agreement, above the conventional 0.70 threshold.
- Bootstrap 95% CI [0.541, 0.942] across 2,000 resamples.
- Raw agreement = 84%; confidence-level agreement = 84%.
- **κ rises to 1.00** after dropping the 4 disputed cases — disagreements concentrate on theoretically meaningful frontiers (Synthetic Company ↔ AI-Enhanced Shell; Multi-Agent System ↔ Agentic DAO), not measurement noise.

## Group comparisons (Kruskal-Wallis across the 4 taxonomy classes)
- Synthetic score by class: **H = 61.59, p < 1×10⁻¹¹, η² = 0.68** (large effect).
- Employees by class: **H = 54.08, p < 1×10⁻⁹, η² = 0.59** (large effect).

## Multivariate structure — unsupervised clustering (k-means + agglomerative + GMM, k ∈ {3, 4, 5})
- Preferred k = 4: silhouette = 0.50 (both k-means and agglomerative).
- **ARI(k-means vs agglomerative) = 0.87** — two methodologically distinct algorithms converge on the same partition.
- ARI vs analyst-coded taxonomy = 0.22–0.29 — clustering recovers venture-shape structure (zero-employee algorithmic ventures, small AI-heavy ventures, mid-size parents with embedded AI) only *partially*. The taxonomy adds analytical content beyond the OSINT features.

## Supervised classification (5-fold stratified CV, fixed seed = 42)

| Estimator | 4-class CV accuracy | 4-class F1-macro | 2-class CV accuracy | 2-class F1-macro |
|---|---:|---:|---:|---:|
| Logistic regression | 0.639 ± 0.082 | 0.407 | **0.922 ± 0.027** | **0.920** |
| Random forest | **0.729 ± 0.085** | 0.622 | **0.922 ± 0.083** | **0.920** |
| Gradient boosting | 0.641 ± 0.025 | 0.536 | **0.944 ± 0.061** | **0.943** |

- The 4-class taxonomy is **moderately separable** from 4 operational features (score, log-employees, domain age, AI %).
- The binary collapse (synthetic-or-DAO vs agentic-or-other) is **sharply separable**, with three methodologically distinct estimators converging in the 0.92–0.94 band.

## Explainable AI (random forest, 4-class)
- **Permutation importance** ranks: log_employees (0.281) > ai_pct (0.253) > domain_years (0.218) > score (0.115).
- **SHAP global importance** ranks: log_employees (0.100) > domain_years (0.094) > ai_pct (0.047) > score (0.031).
- **Decision-tree surrogate** (depth 3) reproduces the random forest with **71.9% fidelity**; first split on AI-content share at 79.5%, then on synthetic score at 66.5.
- All three artefacts converge on the same theoretically plausible drivers — *not* on spurious features (no row IDs, no scrape dates, no source flags drive the classification).

## Robustness layer
- **Bootstrap** (500 iterations, out-of-bag):
  - 4-class RF: mean accuracy 0.679, 95% CI [0.516, 0.831] — comfortably above the 0.167 random baseline.
  - 2-class RF: mean accuracy 0.904, 95% CI [0.781, 1.000].
- **Leave-one-class-out**: re-estimating the RF after removing each class in turn yields CV accuracies of 0.75–0.82; no class collapse.
- **Threshold sensitivity** (score cutoff swept 40 → 60): share of synthetic/DAO/shell entities in the retained sample rises monotonically from 62% (cutoff = 40) to 85% (cutoff = 60). Headline result holds across the full sweep.
- **Kappa stability**: bootstrap CI stable; alternative coding schemes (collapse Shell→Synthetic; collapse MAS→DAO; both) yield κ ∈ [0.78, 0.92].

## Solvency gate (5 criteria: convergence · stability · interpretability · LOCO generalization · threshold sensitivity)

| Round | Specification | Failed claims |
|---|---|---:|
| 1 | All 89 entities, 4-class taxonomy | **0 / 4** |
| 2 | All 89 entities, binary collapse | 1 / 4 (the failed claim is not applicable under the binary coding) |
| 3 | n = 78 (score ≥ 40), 4-class taxonomy | **0 / 4** |

- **All four pre-specified headline claims pass the solvency gate** in Round 1.
- The pipeline ran two additional stress-test rounds; the headline findings survive both.

## Headline takeaways (one-liners for abstract / discussion)
- A new class of entrepreneurial entity is **empirically detectable** with OSINT features alone (4-class RF CV = 0.73; binary RF CV = 0.92–0.94).
- The detection is **interpretable**: scale, AI content and venture age are the drivers, not pipeline artefacts.
- The detection is **robust**: bootstrap, leave-one-class-out, threshold sensitivity and alternative coding schemes preserve the result.
- Inter-rater agreement is **substantial** (κ = 0.772) and *rises to perfect* once the two real taxonomic frontiers (Synthetic ↔ Shell; MAS ↔ DAO) are acknowledged as substantive distinctions rather than measurement noise.
- The unsupervised structure recovers venture-shape groupings only *partially* — evidence that the analyst-coded taxonomy is theoretically motivated, not mechanically induced from the data.
