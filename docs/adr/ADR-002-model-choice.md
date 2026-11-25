# ADR-002: Gradient-boosted trees on a parsimonious feature set, one-standard-error selection

- **Status:** Accepted
## Context
Tabular, 4,020 patients, 15.7% positives, mixed categorical (physician specialty, state, care setting) and numeric features, non-linear age effect (treatment rises to 65-74, falls after 75).
## Decision
Scikit-learn `HistGradientBoostingClassifier` (depth 3, 250 iterations, L2 regularised) on the six model_table features. Selected with repeated 5x3 stratified CV on the training split using **PR-AUC**, then the **one-standard-error rule** (simplest candidate within 1 SE of the best).
## Rationale
- GBDT captures age non-linearity and category interactions without hand-built transforms; handles unseen categories via infrequent-category grouping.
- Logistic regression (with and without age splines) and random forest were evaluated with identical CV; differences were within noise (see `reports/model_comparison_cv.csv`). GBDT had the best CV PR-AUC and log-loss.
- XGBoost and LightGBM, benchmarked under the same protocol (`ml/benchmark_gbm.py`, `reports/gbm_benchmark_cv.csv`), did not beat HistGB: regularised LightGBM 0.358 and XGBoost 0.349 CV PR-AUC vs 0.359; default settings overfit (0.30-0.31). HistGB is kept for equal accuracy with a scikit-learn-only runtime.
- Engineered extras (symptoms, contraindication level, hypertension, care-setting counts) did **not** improve CV beyond noise, so by the 1-SE rule they are not in the served model, but remain in `model_table.csv` for future work.
## Consequences
- Probabilities are reasonably calibrated without a separate calibration step (hold-out Brier 0.117 vs 0.132 for prevalence-only).
- Explanations use occlusion (swap-one-feature) rather than SHAP to keep the runtime dependency footprint to scikit-learn only.
- Revisit when longitudinal physician-level features (prior prescribing) become available; expect the largest gain there.
