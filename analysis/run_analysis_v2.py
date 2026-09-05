"""
JEMI R1 reanalysis. Addresses statistical-editor comments 1-11.

Design changes relative to R0:
  C1  Leakage. The synthetic score is removed from every primary model. It is
      evaluated only as a *detector* against verification status, and only on
      the Stage-4 rows it played no part in selecting.
  C2  The taxonomy is coded on five separate dimensions (see build_audit_dataset).
  C3  Sample composition is reported as a CONSORT-style flow.
  C4  Baselines are majority + stratified + label permutation, never 1/K.
  C5  P1 is tested as verified synthetic/agentic vs control, its actual statement.
  C6  Kappa is reported with its CI and judged against the pre-set threshold
      honestly; the per-class confusion matrix is reported.
  C7  The full algorithm x k clustering matrix is reported, standardised, with
      and without the score.
  C8  Repeated + nested stratified CV, all preprocessing inside folds,
      per-class precision/recall, confusion matrices, bootstrap CIs.
  C9  AI-text detector score is treated as a noisy proxy; missingness analysed.
  C10 Holdouts: temporal, jurisdictional, source-family, plus grouped CV.

Usage:  python analysis/run_analysis_v2.py
Writes: analysis/results_v2.json, analysis/results_v2_summary.md
"""

from __future__ import annotations

import json
import warnings
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (adjusted_rand_score, confusion_matrix,
                             classification_report, roc_auc_score, silhouette_score)
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import (GridSearchCV, RepeatedStratifiedKFold, StratifiedKFold,
                                     StratifiedGroupKFold, cross_val_predict,
                                     cross_val_score, cross_validate,
                                     permutation_test_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
SEED = 42
rng = np.random.default_rng(SEED)
R = {}


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------
def load() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "audit_dataset.csv")
    df["is_confirmed"] = df["status_clean"].eq("Confirmed").astype(int)
    df["source_family"] = df["source"].fillna("unknown").map(source_family)
    return df


def source_family(s: str) -> str:
    s = str(s).lower()
    if any(k in s for k in ["companies house", "handelsregister", "kvk", "acra", "asic",
                            "borme", "registro", "infogreffe", "infocamere", "bolagsverket",
                            "mca", "dart", "edinet", "zefix", "cro ", "sec edgar", "sedar",
                            "registry", "reg.", "sos", "dmcc", "junta", "cima"]):
        return "corporate_registry"
    if any(k in s for k in ["deepdao", "etherscan", "snapshot", "tally", "coinmarketcap",
                            "coindesk", "decrypt", "crypto", "olas", "near"]):
        return "chain_analytics"
    if any(k in s for k in ["crunchbase", "product", "official site", "businesswire"]):
        return "company_or_startup_db"
    if any(k in s for k in ["wired", "futurism", "fortune", "fox", "euronews", "bbc",
                            "techcrunch", "reuters", "bloomberg", "press", "millionero",
                            "networkcultures"]):
        return "press"
    if "osint" in s or "manual" in s:
        return "osint_scan"
    return "other"


# ---------------------------------------------------------------------------
# Layer 0 - sample composition
# ---------------------------------------------------------------------------
def layer0(df: pd.DataFrame) -> pd.DataFrame:
    a = df[df["in_analytic_sample"]].copy().reset_index(drop=True)
    R["sample"] = {
        "rows_in_workbench": int(len(df)),
        "excluded_demo_record": int(df["provenance"].eq("demo_record").sum()),
        "excluded_not_established": int(df["provenance"].eq("not_established").sum()),
        "analytic_n": int(len(a)),
        "confirmed": int(a["is_confirmed"].sum()),
        "control": int((1 - a["is_confirmed"]).sum()),
        "by_channel": a["channel"].value_counts().to_dict(),
        "by_jurisdiction": a["jurisdiction_type"].value_counts().to_dict(),
        "by_source_family": a["source_family"].value_counts().to_dict(),
        "zero_employee_n": int((a["employees"] == 0).sum()),
        "zero_employee_pct": round(100 * (a["employees"] == 0).mean(), 1),
    }
    log(f"[L0] analytic n={len(a)}  confirmed={a['is_confirmed'].sum()}  "
        f"control={(1 - a['is_confirmed']).sum()}")
    return a


# ---------------------------------------------------------------------------
# Layer 1 - multidimensional description (replaces the nominal taxonomy)
# ---------------------------------------------------------------------------
def layer1(a: pd.DataFrame) -> None:
    dims = ["D1_legal_form", "D2_human_participation", "D3_ai_authority",
            "D4_architecture", "D5_governance_substrate"]
    marg = {d: a[d].value_counts().to_dict() for d in dims}
    profiles = a["dimension_profile"].value_counts()
    # Cramer's V between every pair of dimensions: are they really separate axes?
    assoc = {}
    for d1, d2 in combinations(dims, 2):
        ct = pd.crosstab(a[d1], a[d2])
        if ct.shape[0] < 2 or ct.shape[1] < 2:
            continue
        chi2 = stats.chi2_contingency(ct, correction=False)[0]
        n = ct.values.sum()
        v = np.sqrt((chi2 / n) / (min(ct.shape) - 1))
        assoc[f"{d1}~{d2}"] = round(float(v), 3)
    R["dimensions"] = {
        "marginals": marg,
        "n_distinct_profiles": int(profiles.size),
        "n_possible_profiles": int(np.prod([a[d].nunique() for d in dims])),
        "top_profiles": profiles.head(10).to_dict(),
        "cramers_v_between_dimensions": assoc,
        "delegation_index": {
            "mean": round(float(a["delegation_index"].mean()), 3),
            "sd": round(float(a["delegation_index"].std()), 3),
            "by_status": a.groupby("is_confirmed")["delegation_index"].mean().round(3).to_dict(),
        },
    }
    # Does the delegation index separate confirmed from control?
    g1 = a.loc[a["is_confirmed"] == 1, "delegation_index"]
    g0 = a.loc[a["is_confirmed"] == 0, "delegation_index"]
    u, p = stats.mannwhitneyu(g1, g0, alternative="two-sided")
    R["dimensions"]["delegation_index"]["mannwhitney_u"] = float(u)
    R["dimensions"]["delegation_index"]["p"] = float(p)
    # Rank-biserial effect size.
    R["dimensions"]["delegation_index"]["rank_biserial"] = round(
        float(1 - 2 * u / (len(g1) * len(g0))) * -1, 3)
    log(f"[L1] {profiles.size} distinct profiles occupied of "
        f"{R['dimensions']['n_possible_profiles']} combinatorially possible; "
        f"delegation index p={p:.4f}")


# ---------------------------------------------------------------------------
# Layer 2 - inter-rater reliability, reported honestly (comment 6)
# ---------------------------------------------------------------------------
def cohen_kappa(x, y) -> float:
    labs = sorted(set(x) | set(y))
    cm = confusion_matrix(x, y, labels=labs)
    n = cm.sum()
    po = np.trace(cm) / n
    pe = (cm.sum(0) * cm.sum(1)).sum() / n**2
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def layer2(df: pd.DataFrame, a: pd.DataFrame) -> None:
    def block(frame, tag):
        d = frame[frame["double_coded"]]
        if len(d) < 3:
            R.setdefault("irr", {})[tag] = {"n": int(len(d)),
                                            "note": "too few double-coded cases to estimate"}
            return
        x, y = d["rater1_label"].values, d["rater2_label"].values
        k = cohen_kappa(x, y)
        boots = []
        idx = np.arange(len(d))
        for _ in range(5000):
            s = rng.choice(idx, len(idx), replace=True)
            if len(set(x[s])) < 2 and len(set(y[s])) < 2:
                continue
            boots.append(cohen_kappa(x[s], y[s]))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        labs = sorted(set(x) | set(y))
        cm = confusion_matrix(x, y, labels=labs)
        po = float((x == y).mean())
        # Prevalence-adjusted bias-adjusted kappa.
        pabak = 2 * po - 1
        dis = [{"entity_id": r["entity_id"], "entity": r["entity"],
                "rater1": r["rater1_label"], "rater2": r["rater2_label"]}
               for _, r in d[d["rater_agreement"] == "disagree"].iterrows()]
        per_class = {}
        for lab in labs:
            n1, n2 = (x == lab).sum(), (y == lab).sum()
            both = ((x == lab) & (y == lab)).sum()
            per_class[lab] = {
                "rater1_n": int(n1), "rater2_n": int(n2),
                "both": int(both),
                "specific_agreement": round(float(2 * both / (n1 + n2)), 3) if (n1 + n2) else None,
            }
        R.setdefault("irr", {})[tag] = {
            "n": int(len(d)),
            "raw_agreement": round(po, 3),
            "kappa": round(k, 3),
            "kappa_ci95": [round(float(lo), 3), round(float(hi), 3)],
            "pabak": round(float(pabak), 3),
            "threshold_0_70_established": bool(lo >= 0.70),
            "labels": labs,
            "confusion_matrix": cm.tolist(),
            "per_class_specific_agreement": per_class,
            "disagreements": dis,
        }
        log(f"[L2] {tag}: n={len(d)} kappa={k:.3f} CI=[{lo:.3f},{hi:.3f}] "
            f">=0.70 established: {lo >= 0.70}")

    block(df, "all_double_coded_r0")
    block(a, "analytic_sample_only")


# ---------------------------------------------------------------------------
# Layer 3 - the synthetic score as a DETECTOR only (comments 1, 4, 10)
# ---------------------------------------------------------------------------
def layer3(a: pd.DataFrame) -> None:
    out = {}
    for tag, sub in (("all_observed", a),
                     ("stage4_score_independent",
                      a[a["channel"] == "stage4_manual"])):
        if sub["is_confirmed"].nunique() < 2:
            continue
        y = sub["is_confirmed"].values
        s = sub["score"].values.astype(float)
        auc = roc_auc_score(y, s)
        boots = []
        for _ in range(5000):
            i = rng.choice(len(y), len(y), replace=True)
            if len(set(y[i])) < 2:
                continue
            boots.append(roc_auc_score(y[i], s[i]))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        pred = (s >= 50).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        out[tag] = {
            "n": int(len(sub)), "positives": int(y.sum()),
            "auc": round(float(auc), 3),
            "auc_ci95": [round(float(lo), 3), round(float(hi), 3)],
            "at_cutoff_50": {
                "sensitivity": round(float(tp / (tp + fn)), 3) if (tp + fn) else None,
                "specificity": round(float(tn / (tn + fp)), 3) if (tn + fp) else None,
                "precision": round(float(tp / (tp + fp)), 3) if (tp + fp) else None,
                "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            },
            "n_score_at_default_50": int(sub["score_is_default_value"].sum()),
        }
        log(f"[L3] score-as-detector {tag}: AUC={auc:.3f} [{lo:.3f},{hi:.3f}] n={len(sub)}")
    R["score_as_detector"] = out


# ---------------------------------------------------------------------------
# Layer 4 - supervised models with everything inside the folds (comments 5, 8)
# ---------------------------------------------------------------------------
NUM_PRIMARY = ["log_employees", "domain_years"]
CAT_PRIMARY = ["jurisdiction_type", "source_family"]
NUM_WITH_AI = NUM_PRIMARY + ["ai_pct"]
NUM_LEAKY = NUM_WITH_AI + ["score"]


def make_pipe(estimator, num, cat):
    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                          ("sc", StandardScaler())]), num),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore",
                                               min_frequency=2))]), cat),
    ])
    return Pipeline([("pre", pre), ("clf", estimator)])


ESTIMATORS = {
    "logistic": (LogisticRegression(max_iter=2000, random_state=SEED),
                 {"clf__C": [0.05, 0.25, 1.0, 4.0]}),
    "random_forest": (RandomForestClassifier(random_state=SEED, n_estimators=200, n_jobs=1),
                      {"clf__max_depth": [2, 3, None],
                       "clf__min_samples_leaf": [1, 3, 5]}),
}


def evaluate(a, num, cat, tag, groups=None):
    X = a[num + cat]
    y = a["is_confirmed"].values
    res = {"n": int(len(a)), "positives": int(y.sum()),
           "features": {"numeric": num, "categorical": cat}}

    # Baselines.
    cv_b = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEED)
    for name, strat in (("majority", "most_frequent"), ("stratified", "stratified")):
        sc = cross_val_score(DummyClassifier(strategy=strat, random_state=SEED),
                             X, y, cv=cv_b, scoring="accuracy")
        res[f"baseline_{name}"] = {"mean": round(float(sc.mean()), 3),
                                   "sd": round(float(sc.std()), 3)}

    for ename, (est, grid) in ESTIMATORS.items():
        pipe = make_pipe(clone(est), num, cat)
        # Nested CV: inner grid search, outer repeated stratified.
        inner = RepeatedStratifiedKFold(n_splits=3, n_repeats=1, random_state=SEED)
        search = GridSearchCV(pipe, grid, cv=inner, scoring="balanced_accuracy", n_jobs=1)
        outer = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEED)
        # One nested-CV pass scored on every metric at once (4x cheaper than
        # refitting the whole search per metric).
        cvres = cross_validate(search, X, y, cv=outer, n_jobs=-1,
                               scoring=["accuracy", "balanced_accuracy",
                                        "f1_macro", "roc_auc"])
        acc = cvres["test_accuracy"]
        bal = cvres["test_balanced_accuracy"]
        f1 = cvres["test_f1_macro"]
        auc_m = round(float(np.nanmean(cvres["test_roc_auc"])), 3)
        # Out-of-fold confusion matrix from a single stratified 5-fold pass.
        oof = cross_val_predict(search, X, y, cv=StratifiedKFold(
            n_splits=5, shuffle=True, random_state=SEED), n_jobs=-1)
        cm = confusion_matrix(y, oof, labels=[0, 1])
        rep = classification_report(y, oof, output_dict=True, zero_division=0)
        # Permutation test against the label-permuted null.
        pscore, perm, pval = permutation_test_score(
            make_pipe(clone(est), num, cat), X, y, scoring="accuracy",
            cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED),
            n_permutations=300, random_state=SEED, n_jobs=-1)
        res[ename] = {
            "cv_accuracy_mean": round(float(acc.mean()), 3),
            "cv_accuracy_sd": round(float(acc.std()), 3),
            "cv_accuracy_ci95": [round(float(np.percentile(acc, 2.5)), 3),
                                 round(float(np.percentile(acc, 97.5)), 3)],
            "cv_balanced_accuracy_mean": round(float(bal.mean()), 3),
            "cv_f1_macro_mean": round(float(f1.mean()), 3),
            "cv_roc_auc_mean": auc_m,
            "oof_confusion_matrix": cm.tolist(),
            "per_class": {k: {kk: round(vv, 3) for kk, vv in v.items()}
                          for k, v in rep.items() if k in ("0", "1")},
            "permutation_test": {"score": round(float(pscore), 3),
                                 "null_mean": round(float(perm.mean()), 3),
                                 "p_value": round(float(pval), 4)},
        }
        log(f"[L4] {tag}/{ename}: acc={acc.mean():.3f} bal={bal.mean():.3f} "
            f"perm_p={pval:.4f} (majority={res['baseline_majority']['mean']:.3f})")

    # Group-aware CV by source family.
    if groups is not None and pd.Series(groups).nunique() >= 3:
        est, grid = ESTIMATORS["random_forest"]
        pipe = make_pipe(clone(est), num, cat)
        try:
            sgk = StratifiedGroupKFold(n_splits=min(5, pd.Series(groups).nunique()),
                                       shuffle=True, random_state=SEED)
            sc = cross_val_score(pipe, X, y, groups=groups, cv=sgk, scoring="accuracy")
            res["grouped_cv_by_source_family"] = {
                "mean": round(float(sc.mean()), 3), "sd": round(float(sc.std()), 3),
                "n_groups": int(pd.Series(groups).nunique())}
            log(f"[L4] {tag}/grouped-by-source: acc={sc.mean():.3f}")
        except Exception as e:  # pragma: no cover
            res["grouped_cv_by_source_family"] = {"error": str(e)}
    return res


def layer4(a: pd.DataFrame) -> None:
    R["supervised"] = {
        "primary_no_score_no_detector": evaluate(
            a, NUM_PRIMARY, CAT_PRIMARY, "primary", groups=a["source_family"]),
        "sensitivity_with_ai_detector": evaluate(
            a, NUM_WITH_AI, CAT_PRIMARY, "with_ai"),
        "r0_style_with_score_leaky": evaluate(
            a, NUM_LEAKY, [], "leaky_r0_style"),
    }


# ---------------------------------------------------------------------------
# Layer 5 - holdouts (comment 10)
# ---------------------------------------------------------------------------
def holdout(a, mask_test, tag):
    tr, te = a[~mask_test], a[mask_test]
    if len(te) < 5 or tr["is_confirmed"].nunique() < 2 or te["is_confirmed"].nunique() < 2:
        return {"tag": tag, "n_test": int(len(te)), "note": "holdout not estimable"}
    est, _ = ESTIMATORS["random_forest"]
    pipe = make_pipe(clone(est), NUM_PRIMARY, CAT_PRIMARY)
    pipe.fit(tr[NUM_PRIMARY + CAT_PRIMARY], tr["is_confirmed"])
    pred = pipe.predict(te[NUM_PRIMARY + CAT_PRIMARY])
    y = te["is_confirmed"].values
    acc = float((pred == y).mean())
    maj = float(max(np.mean(y), 1 - np.mean(y)))
    return {"tag": tag, "n_train": int(len(tr)), "n_test": int(len(te)),
            "accuracy": round(acc, 3), "majority_baseline": round(maj, 3),
            "beats_majority": bool(acc > maj),
            "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist()}


def layer5(a: pd.DataFrame) -> None:
    outs = []
    med = a["domain_years"].median()
    outs.append(holdout(a, a["domain_years"] <= med, "temporal_youngest_half"))
    outs.append(holdout(a, a["jurisdiction_type"].eq("permissive_or_decentralized"),
                        "jurisdictional_permissive_decentralized"))
    for fam in a["source_family"].value_counts().index[:4]:
        outs.append(holdout(a, a["source_family"].eq(fam), f"source_family_{fam}"))
    outs.append(holdout(a, a["channel"].eq("stage4_manual"),
                        "channel_stage4_manual_as_independent_test"))
    R["holdouts"] = outs
    for o in outs:
        if "accuracy" in o:
            log(f"[L5] {o['tag']}: acc={o['accuracy']:.3f} vs majority "
                f"{o['majority_baseline']:.3f}")


# ---------------------------------------------------------------------------
# Layer 6 - full clustering matrix (comment 7)
# ---------------------------------------------------------------------------
def layer6(a: pd.DataFrame) -> None:
    # Ex-ante criterion, declared before reading the ARIs (see manuscript 3.4):
    # partial recovery is ARI in [0.15, 0.45]; <0.15 unmoored; >0.45 redundant.
    crit = {"partial_recovery_band": [0.15, 0.45]}
    grids = {}
    for feat_tag, feats in (("without_score", ["log_employees", "domain_years", "ai_pct"]),
                            ("with_score", ["log_employees", "domain_years", "ai_pct", "score"])):
        X = a[feats]
        X = SimpleImputer(strategy="median").fit_transform(X)
        X = StandardScaler().fit_transform(X)  # standardisation stated explicitly
        truth = a["type_clean"].values
        labels_by = {}
        for k in (3, 4, 5):
            algs = {
                "kmeans": KMeans(n_clusters=k, n_init=25, random_state=SEED),
                "agglomerative": AgglomerativeClustering(n_clusters=k),
                "gaussian_mixture": GaussianMixture(n_components=k, random_state=SEED,
                                                    n_init=5),
            }
            for an, alg in algs.items():
                lab = alg.fit_predict(X)
                labels_by[(an, k)] = lab
                grids[f"{feat_tag}|{an}|k={k}"] = {
                    "silhouette": round(float(silhouette_score(X, lab)), 3),
                    "ari_vs_taxonomy": round(float(adjusted_rand_score(truth, lab)), 3),
                }
        for k in (3, 4, 5):
            for a1, a2 in combinations(["kmeans", "agglomerative", "gaussian_mixture"], 2):
                grids[f"{feat_tag}|{a1}~{a2}|k={k}"] = {
                    "ari_between_algorithms": round(
                        float(adjusted_rand_score(labels_by[(a1, k)], labels_by[(a2, k)])), 3)}
    aris = [v["ari_vs_taxonomy"] for v in grids.values() if "ari_vs_taxonomy" in v]
    crit.update({
        "n_configurations": len(aris),
        "ari_vs_taxonomy_min": round(float(min(aris)), 3),
        "ari_vs_taxonomy_max": round(float(max(aris)), 3),
        "ari_vs_taxonomy_median": round(float(np.median(aris)), 3),
        "share_in_partial_band": round(
            float(np.mean([(0.15 <= x <= 0.45) for x in aris])), 3),
    })
    R["clustering"] = {"criterion": crit, "grid": grids}
    log(f"[L6] clustering: {len(aris)} configs, ARI vs taxonomy "
        f"median={np.median(aris):.3f} range=[{min(aris):.3f},{max(aris):.3f}]")


# ---------------------------------------------------------------------------
# Layer 7 - missingness (comment 8)
# ---------------------------------------------------------------------------
def layer7(a: pd.DataFrame) -> None:
    miss = a["ai_pct"].isna()
    ct = pd.crosstab(miss, a["channel"])
    chi2, p, _, _ = stats.chi2_contingency(ct) if ct.shape[0] > 1 and ct.shape[1] > 1 \
        else (np.nan, np.nan, None, None)
    ct2 = pd.crosstab(miss, a["is_confirmed"])
    if ct2.shape[0] > 1 and ct2.shape[1] > 1:
        _, p2 = stats.fisher_exact(ct2.values) if ct2.shape == (2, 2) else (None, np.nan)
    else:
        p2 = np.nan
    R["missingness"] = {
        "ai_pct_missing_n": int(miss.sum()),
        "ai_pct_missing_pct": round(100 * float(miss.mean()), 1),
        "by_channel": ct.to_dict(),
        "chi2_missing_vs_channel_p": None if np.isnan(p) else round(float(p), 5),
        "fisher_missing_vs_status_p": None if p2 is None or np.isnan(p2) else round(float(p2), 5),
        "note": ("Missingness is structurally tied to recruitment channel, so it is "
                 "not missing at random; median imputation can bias in either "
                 "direction. The primary model therefore excludes the variable."),
    }
    log(f"[L7] ai_pct missing {miss.sum()}/{len(a)} "
        f"({100 * miss.mean():.0f}%), p(channel)={p:.5f}")


# ---------------------------------------------------------------------------
def main() -> None:
    df = load()
    a = layer0(df)
    layer1(a)
    layer2(df, a)
    layer3(a)
    layer4(a)
    layer5(a)
    layer6(a)
    layer7(a)

    R["_meta"] = {"seed": SEED, "n_workbench": int(len(df)), "n_analytic": int(len(a)),
                  "generated_by": "analysis/run_analysis_v2.py"}
    (ROOT / "results_v2.json").write_text(
        json.dumps(R, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"\nWrote {ROOT / 'results_v2.json'}")


if __name__ == "__main__":
    main()
