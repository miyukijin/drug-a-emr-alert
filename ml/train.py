"""Steps 3a-3c: compare models, evaluate honestly, export the serving artefact + report assets."""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (average_precision_score, brier_score_loss, precision_recall_curve,  # noqa: E402
                             roc_auc_score, roc_curve, log_loss)
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate, train_test_split  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from features import FEATURE_GROUPS  # noqa: E402

warnings.filterwarnings("ignore")
SEED = 42


def make_pre(cats, nums, scale=False, spline_age=False):
    num_tf = StandardScaler() if scale else "passthrough"
    parts = [("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=30, sparse_output=False), cats)]
    if spline_age:
        parts.append(("age", SplineTransformer(n_knots=5, degree=3), ["PATIENT_AGE"]))
        nums = [n for n in nums if n != "PATIENT_AGE"]
    parts.append(("num", num_tf, nums))
    return ColumnTransformer(parts)


def candidates(cats, nums):
    return {
        "Logistic regression (L2)": Pipeline([("pre", make_pre(cats, nums, scale=True)),
                                              ("m", LogisticRegression(C=0.3, max_iter=3000))]),
        "Logistic regression + age spline": Pipeline([("pre", make_pre(cats, nums, scale=True, spline_age=True)),
                                                      ("m", LogisticRegression(C=0.3, max_iter=3000))]),
        "Random forest": Pipeline([("pre", make_pre(cats, nums)),
                                   ("m", RandomForestClassifier(400, min_samples_leaf=15, n_jobs=-1, random_state=SEED))]),
        "Gradient boosting (HistGB)": Pipeline([("pre", make_pre(cats, nums)),
                                                ("m", HistGradientBoostingClassifier(
                                                    max_depth=3, learning_rate=0.04, max_iter=250,
                                                    l2_regularization=1.0, min_samples_leaf=40, random_state=SEED))]),
    }


def prep_X(df, cats, nums):
    X = df[cats + nums].copy()
    return X


def lift_table(y, p_treat, eligible, bins=10):
    d = pd.DataFrame({"y": y, "p": p_treat})[eligible]
    d["decile"] = pd.qcut(d["p"].rank(method="first"), bins, labels=False) + 1
    t = d.groupby("decile").agg(patients=("y", "size"), mean_pred=("p", "mean"), actual_treated=("y", "mean")).reset_index()
    t["untreated_rate"] = 1 - t["actual_treated"]
    return t


def main(model_table: str, models_dir: str, reports_dir: str) -> None:
    models, reports = Path(models_dir), Path(reports_dir)
    models.mkdir(exist_ok=True, parents=True)
    (reports / "figures").mkdir(exist_ok=True, parents=True)
    df = pd.read_csv(model_table)
    y = df["TARGET"]
    train_idx, test_idx = train_test_split(df.index, test_size=0.2, stratify=y, random_state=SEED)
    tr, te = df.loc[train_idx], df.loc[test_idx]
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=SEED)
    out: dict = {"n_train": len(tr), "n_test": len(te), "target_rate_train": float(tr.TARGET.mean()),
                 "target_rate_test": float(te.TARGET.mean())}

    # 1) feature ablation with the same CV protocol (train split only)
    abl = []
    for gname, (cats, nums) in FEATURE_GROUPS.items():
        for mname, pipe in candidates(cats, nums).items():
            r = cross_validate(pipe, prep_X(tr, cats, nums), tr.TARGET, cv=cv,
                               scoring=["roc_auc", "average_precision", "neg_log_loss"], n_jobs=1)
            abl.append({"features": gname, "model": mname,
                        "cv_roc_auc": r["test_roc_auc"].mean(), "cv_roc_auc_sd": r["test_roc_auc"].std(),
                        "cv_pr_auc": r["test_average_precision"].mean(), "cv_pr_auc_sd": r["test_average_precision"].std(),
                        "cv_logloss": -r["test_neg_log_loss"].mean()})
    abl = pd.DataFrame(abl).round(4)
    abl.to_csv(reports / "model_comparison_cv.csv", index=False)
    print(abl.to_string())

    # 2) selection: best CV PR-AUC (the metric that matters at ~16% prevalence), then apply the
    #    one-standard-error rule -> simplest candidate (fewest features, simplest model) within 1 SE of the best.
    n_folds = cv.get_n_splits()
    top = abl.sort_values("cv_pr_auc", ascending=False).iloc[0]
    se = top["cv_pr_auc_sd"] / np.sqrt(n_folds)
    group_rank = {g: i for i, g in enumerate(FEATURE_GROUPS)}
    model_rank = {m: i for i, m in enumerate(candidates(*FEATURE_GROUPS["core (model_table spec)"]))}
    pool = abl[abl["cv_pr_auc"] >= top["cv_pr_auc"] - se].copy()
    pool["g"] = pool["features"].map(group_rank)
    pool["m"] = pool["model"].map(model_rank)
    best = pool.sort_values(["g", "cv_pr_auc"], ascending=[True, False]).iloc[0]
    out["selection"] = {"top_cv_pr_auc": float(top["cv_pr_auc"]), "top_model": top["model"], "top_features": top["features"],
                        "one_se": float(se), "n_within_1se": int(len(pool))}
    cats, nums = FEATURE_GROUPS[best["features"]]
    chosen = candidates(cats, nums)[best["model"]]
    out["chosen_model"], out["chosen_features"] = best["model"], best["features"]
    chosen.fit(prep_X(tr, cats, nums), tr.TARGET)
    p_te = chosen.predict_proba(prep_X(te, cats, nums))[:, 1]
    yt = te.TARGET.values
    elig = te.ELIGIBLE.values == 1

    def metrics(mask, label):
        return {"slice": label, "n": int(mask.sum()), "treated_rate": float(yt[mask].mean()),
                "roc_auc": float(roc_auc_score(yt[mask], p_te[mask])),
                "pr_auc": float(average_precision_score(yt[mask], p_te[mask])),
                "brier": float(brier_score_loss(yt[mask], p_te[mask])),
                "log_loss": float(log_loss(yt[mask], p_te[mask]))}

    out["holdout"] = [metrics(np.ones(len(te), bool), "All patients"), metrics(elig, "Eligible (age>12 & high-risk)")]
    base_rate = float(tr.TARGET.mean())
    out["baselines"] = {"prevalence_brier_all": float(brier_score_loss(yt, np.full(len(yt), base_rate))),
                        "age_only_auc_all": float(roc_auc_score(yt, te.PATIENT_AGE))}
    # bootstrap CIs on holdout
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(1000):
        i = rng.integers(0, len(yt), len(yt))
        if yt[i].min() == yt[i].max():
            continue
        boots.append((roc_auc_score(yt[i], p_te[i]), average_precision_score(yt[i], p_te[i])))
    b = np.array(boots)
    out["holdout_ci95"] = {"roc_auc": np.percentile(b[:, 0], [2.5, 97.5]).tolist(), "pr_auc": np.percentile(b[:, 1], [2.5, 97.5]).tolist()}

    # 3) alert operating point on the eligible holdout: alert if P(treated) < threshold
    ee = np.where(elig)[0]
    pe, ye = p_te[ee], yt[ee]
    rows = []
    for thr in [0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30]:
        flag = pe < thr
        n_f = int(flag.sum())
        un = (ye == 0)
        rows.append({"threshold": thr, "flagged": n_f, "flag_rate": n_f / len(ee),
                     "precision_untreated": float((ye[flag] == 0).mean()) if n_f else np.nan,
                     "recall_untreated": float(((ye == 0) & flag).sum() / un.sum()),
                     "treated_missed_by_alert": int(((ye == 1) & flag).sum())})
    op = pd.DataFrame(rows)
    op.to_csv(reports / "alert_operating_points.csv", index=False)
    out["operating_points"] = op.round(4).to_dict("records")
    lt = lift_table(yt, p_te, elig)
    lt.to_csv(reports / "lift_table_eligible.csv", index=False)
    out["lift_table"] = lt.round(4).to_dict("records")

    # 4) permutation importance (holdout, PR-AUC)
    pi = permutation_importance(chosen, prep_X(te, cats, nums), yt, scoring="average_precision",
                                n_repeats=20, random_state=SEED, n_jobs=1)
    imp = pd.DataFrame({"feature": cats + nums, "importance": pi.importances_mean, "sd": pi.importances_std}) \
        .sort_values("importance", ascending=False)
    imp.to_csv(reports / "permutation_importance.csv", index=False)
    out["importance"] = imp.round(4).head(12).to_dict("records")

    # 5) fairness / subgroup view on holdout
    sub = []
    te2 = te.assign(p=p_te)
    te2["age_band"] = pd.cut(te2.PATIENT_AGE, [0, 12, 39, 64, 120], labels=["<=12", "13-39", "40-64", "65+"])
    for col in ["PATIENT_GENDER", "age_band", "PHYSICIAN_GROUP", "INSURANCE_TYPE"]:
        for k, g in te2.groupby(col, observed=True):
            if len(g) >= 40 and g.TARGET.nunique() > 1:
                sub.append({"dimension": col, "group": str(k), "n": len(g), "actual_treated": g.TARGET.mean(),
                            "mean_pred": g.p.mean(), "roc_auc": roc_auc_score(g.TARGET, g.p)})
    pd.DataFrame(sub).round(4).to_csv(reports / "subgroup_performance.csv", index=False)
    out["subgroups"] = pd.DataFrame(sub).round(4).to_dict("records")

    # 6) figures
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
    for mask, lab, c in [(np.ones(len(yt), bool), "All patients", "#1f4e9c"), (elig, "Eligible only", "#d9534f")]:
        fpr, tpr, _ = roc_curve(yt[mask], p_te[mask])
        ax[0].plot(fpr, tpr, label=f"{lab} (AUC {roc_auc_score(yt[mask], p_te[mask]):.3f})", color=c)
        pr, rc, _ = precision_recall_curve(yt[mask], p_te[mask])
        ax[1].plot(rc, pr, label=f"{lab} (AP {average_precision_score(yt[mask], p_te[mask]):.3f})", color=c)
        ax[1].axhline(yt[mask].mean(), color=c, ls=":", lw=1)
    ax[0].plot([0, 1], [0, 1], "k--", lw=1)
    ax[0].set(title="ROC curve (holdout, n=%d)" % len(yt), xlabel="False positive rate", ylabel="True positive rate")
    ax[1].set(title="Precision-recall (dotted = prevalence)", xlabel="Recall", ylabel="Precision")
    frac, mp = calibration_curve(yt, p_te, n_bins=8, strategy="quantile")
    ax[2].plot(mp, frac, "o-", color="#1f4e9c", label="Model")
    ax[2].plot([0, 0.5], [0, 0.5], "k--", lw=1)
    ax[2].set(title="Calibration (holdout)", xlabel="Mean predicted P(treated)", ylabel="Observed treated rate")
    for a in ax:
        a.legend(loc="best", fontsize=8)
        a.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(reports / "figures" / "model_performance.png", dpi=160)
    plt.close()

    fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
    bars = ax[0].bar(lt.decile, lt.actual_treated * 100, color="#1f4e9c")
    for b_, v_ in zip(bars, lt.actual_treated * 100):
        ax[0].text(b_.get_x() + b_.get_width() / 2, v_ + 0.8, f"{v_:.0f}%", ha="center", fontsize=8)
    ax[0].axhline(ye.mean() * 100, color="k", ls="--", lw=1, label=f"Eligible avg {ye.mean()*100:.1f}%")
    ax[0].set(title="Eligible holdout: actual treated rate by predicted decile\n(decile 1 = least likely to be treated)",
              xlabel="Predicted-likelihood decile", ylabel="Actually treated (%)", ylim=(0, 46), xticks=range(1, 11))
    ax[0].legend()
    top = imp.head(10).iloc[::-1]
    ax[1].barh(top.feature, top.importance, xerr=top.sd, color="#2a9d8f")
    ax[1].axvline(0, color="k", lw=0.8)
    ax[1].set(title="Permutation importance (drop in PR-AUC, holdout)",
              xlabel="Drop in PR-AUC when the feature is shuffled (0 or below = no signal)")
    for a in ax:
        a.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(reports / "figures" / "lift_and_importance.png", dpi=160)
    plt.close()

    # 7) refit on ALL data for serving; keep metadata for the API
    final = candidates(cats, nums)[best["model"]]
    final.fit(prep_X(df, cats, nums), y)
    eligible_threshold = 0.15
    meta = {"model_name": best["model"], "feature_set": best["features"], "categorical": cats, "numeric": nums,
            "trained_rows": int(len(df)), "train_target_rate": float(y.mean()), "alert_threshold": eligible_threshold,
            "holdout": out["holdout"], "holdout_ci95": out["holdout_ci95"], "version": "1.0.0",
            "numeric_defaults": {n: float(df[n].median()) for n in nums},
            "categories": {c: sorted(df[c].dropna().unique().tolist()) for c in cats}}
    joblib.dump(final, models / "model.joblib")
    (models / "model_metadata.json").write_text(json.dumps(meta, indent=2))
    (reports / "metrics.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps({k: out[k] for k in ("chosen_model", "chosen_features", "holdout", "holdout_ci95", "baselines")}, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:4])
