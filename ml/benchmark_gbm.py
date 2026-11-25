"""XGBoost / LightGBM vs the served HistGB: same split, CV protocol and preprocessing as train.py.

Usage: pip install -r ml/requirements-benchmark.txt
       python ml/benchmark_gbm.py data/model_table.csv reports
Not part of the serving image: xgboost / lightgbm are benchmark-only dependencies.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).parent))
from features import FEATURE_GROUPS  # noqa: E402
from train import SEED, candidates, make_pre  # noqa: E402

warnings.filterwarnings("ignore")


def gbm_candidates(cats, nums):
    pre = lambda: make_pre(cats, nums)  # noqa: E731
    return {
        "Gradient boosting (HistGB) - served": candidates(cats, nums)["Gradient boosting (HistGB)"],
        "XGBoost (default)": Pipeline([("pre", pre()), ("m", XGBClassifier(
            n_estimators=300, random_state=SEED, n_jobs=4, eval_metric="logloss", verbosity=0))]),
        "XGBoost (regularised)": Pipeline([("pre", pre()), ("m", XGBClassifier(
            n_estimators=300, max_depth=3, learning_rate=0.04, min_child_weight=10, subsample=0.8,
            colsample_bytree=0.8, reg_lambda=1.0, random_state=SEED, n_jobs=4, eval_metric="logloss", verbosity=0))]),
        "LightGBM (default)": Pipeline([("pre", pre()), ("m", LGBMClassifier(
            n_estimators=300, random_state=SEED, n_jobs=4, verbose=-1))]),
        "LightGBM (regularised)": Pipeline([("pre", pre()), ("m", LGBMClassifier(
            n_estimators=300, num_leaves=8, max_depth=3, learning_rate=0.04, min_child_samples=40,
            subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
            random_state=SEED, n_jobs=4, verbose=-1))]),
    }


def main(model_table: str, reports_dir: str) -> None:
    df = pd.read_csv(model_table)
    tr_idx, te_idx = train_test_split(df.index, test_size=0.2, stratify=df["TARGET"], random_state=SEED)
    tr, te = df.loc[tr_idx], df.loc[te_idx]
    elig = te.ELIGIBLE.values == 1
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=SEED)
    rows = []
    for gname in ["core (model_table spec)", "core + all extras"]:
        cats, nums = FEATURE_GROUPS[gname]
        for mname, pipe in gbm_candidates(cats, nums).items():
            r = cross_validate(pipe, tr[cats + nums], tr.TARGET, cv=cv,
                               scoring=["roc_auc", "average_precision", "neg_log_loss"], n_jobs=1)
            p = pipe.fit(tr[cats + nums], tr.TARGET).predict_proba(te[cats + nums])[:, 1]
            rows.append({"features": gname, "model": mname,
                         "cv_roc_auc": r["test_roc_auc"].mean(), "cv_pr_auc": r["test_average_precision"].mean(),
                         "cv_pr_auc_sd": r["test_average_precision"].std(), "cv_logloss": -r["test_neg_log_loss"].mean(),
                         "holdout_roc_auc": roc_auc_score(te.TARGET, p), "holdout_pr_auc": average_precision_score(te.TARGET, p),
                         "holdout_roc_auc_eligible": roc_auc_score(te.TARGET[elig], p[elig])})
    res = pd.DataFrame(rows).round(4)
    res.to_csv(Path(reports_dir) / "gbm_benchmark_cv.csv", index=False)
    print(res.to_string())


if __name__ == "__main__":
    main(*sys.argv[1:3])
