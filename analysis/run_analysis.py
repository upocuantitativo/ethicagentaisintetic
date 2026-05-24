"""
Recursive JSON results analyst for the Synthetic / Agentic / DAO / Multi-Agent
entities study. Implements the pipeline of the json-results-analyst-recursive agent:
descriptives -> group comparisons -> multivariate structure -> classification ->
XAI -> robustness -> solvency gate (with recursion if any claim fails).

Outputs are written under ./ and consumed by the Results section of the article.
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    adjusted_rand_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

warnings.filterwarnings("ignore")

RNG = np.random.default_rng(42)
SEED = 42
ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Data loading: SAMPLE_DATA from index.html + overrides + user_entities
# ---------------------------------------------------------------------------
def parse_sample_data(html_path: Path) -> list[dict]:
    """Parse the SAMPLE_DATA JS literal out of index.html into Python dicts."""
    text = html_path.read_text(encoding="utf-8")
    start = text.index("const SAMPLE_DATA = [")
    end = text.index("];", start) + 2
    block = text[start:end]
    # Strip comment lines (// ...).
    block = re.sub(r"//[^\n]*", "", block)
    # Quote unquoted JS keys (entity:, country:, ...).
    block = re.sub(r"([{,]\s*)(\w+)\s*:", r'\1"\2":', block)
    # Replace JS booleans / strip trailing commas / drop leading "const X = ".
    block = block.replace("true", "true").replace("false", "false")
    block = re.sub(r",(\s*[}\]])", r"\1", block)
    block = re.sub(r"^const SAMPLE_DATA\s*=\s*", "", block).rstrip(";")
    return json.loads(block)


def build_entity_frame() -> pd.DataFrame:
    sample = parse_sample_data(PROJECT / "index.html")
    payload = json.loads((PROJECT / "synthco_data.json").read_text(encoding="utf-8"))
    overrides = payload.get("entity_overrides", {})
    user_entities = payload.get("user_entities", [])

    rows: list[dict] = []
    for i, s in enumerate(sample):
        key = f"builtin_{i}"
        o = overrides.get(key, {})
        if o.get("_deleted"):
            continue
        rows.append(
            {
                "key": key,
                "entity": s["entity"],
                "country": s["country"],
                "type": o.get("type", s["type"]),
                "score": float(o.get("score", s["score"])),
                "employees": float(o.get("employees", s["employees"])),
                "domain_raw": s.get("domain", "?"),
                "ai_raw": s.get("ai", "?"),
                "status": o.get("status", s["status"]),
                "source": s.get("source", ""),
                "real": bool(s.get("real", False)),
                "is_user": False,
            }
        )
    for i, u in enumerate(user_entities):
        rows.append(
            {
                "key": f"user_{i}",
                "entity": u.get("name"),
                "country": u.get("country", "?"),
                "type": u.get("type", "?"),
                "score": float(u.get("score", 50)),
                "employees": float(u.get("employees", 0)),
                "domain_raw": u.get("domain", "?"),
                "ai_raw": "?",
                "status": u.get("status", "Pending Verification"),
                "source": u.get("source", "Manual"),
                "real": False,
                "is_user": True,
            }
        )

    df = pd.DataFrame(rows)
    df["domain_years"] = df["domain_raw"].apply(_parse_domain_years)
    df["ai_pct"] = df["ai_raw"].apply(_parse_pct)
    df["log_employees"] = np.log1p(df["employees"])
    df["score_bin"] = pd.cut(
        df["score"], bins=[-1, 40, 60, 80, 101], labels=["low", "mid", "high", "very_high"]
    )
    df["jurisdiction_type"] = df["country"].apply(_jurisdiction_type)
    df["type_clean"] = df["type"].str.replace("—", "-", regex=False).str.strip()
    df["status_clean"] = df["status"].str.replace("—", "-", regex=False).str.strip()
    return df


def _parse_domain_years(value: str) -> float:
    if not isinstance(value, str):
        return np.nan
    v = value.strip().lower().replace("+", "")
    if v in {"?", "", "n/a"}:
        return np.nan
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(wk|mo|yr)", v)
    if not m:
        return np.nan
    n, unit = float(m.group(1)), m.group(2)
    return {"wk": n / 52, "mo": n / 12, "yr": n}[unit]


def _parse_pct(value: str) -> float:
    if not isinstance(value, str):
        return np.nan
    m = re.match(r"^(\d+(?:\.\d+)?)%", value.strip())
    return float(m.group(1)) if m else np.nan


def _jurisdiction_type(country: str) -> str:
    c = (country or "").lower()
    if "decentralized" in c or "cayman" in c or "estonia" in c or "liechtenstein" in c:
        return "permissive_or_decentralized"
    if any(x in c for x in ["us", "uk", "germany", "france", "japan", "canada", "italy", "spain", "netherlands", "sweden", "switzerland", "ireland", "poland", "korea", "australia", "israel"]):
        return "oecd_traditional"
    if any(x in c for x in ["china", "uae", "singapore"]):
        return "emerging_or_special"
    return "other"


# ---------------------------------------------------------------------------
# Inter-rater reliability (R1 vs R2)
# ---------------------------------------------------------------------------
def kappa_block(payload: dict) -> dict:
    r1 = payload.get("reviews", {})
    r2 = payload.get("reviews_r2", {})
    common = sorted(set(r1) & set(r2))
    y1 = [r1[k]["classification"] for k in common]
    y2 = [r2[k]["classification"] for k in common]
    if not common:
        return {"n": 0}
    k_overall = cohen_kappa_score(y1, y2)
    agreement = float(np.mean([a == b for a, b in zip(y1, y2)]))
    # Bootstrap CI for Cohen's Kappa.
    n_boot = 2000
    boots: list[float] = []
    arr1 = np.array(y1)
    arr2 = np.array(y2)
    idx = np.arange(len(common))
    for _ in range(n_boot):
        sample = RNG.choice(idx, size=len(idx), replace=True)
        if len(set(arr1[sample])) < 2 or len(set(arr2[sample])) < 2:
            continue
        boots.append(cohen_kappa_score(arr1[sample], arr2[sample]))
    ci_lo, ci_hi = np.percentile(boots, [2.5, 97.5])
    # Confidence comparison.
    conf1 = [r1[k].get("confidence", "?") for k in common]
    conf2 = [r2[k].get("confidence", "?") for k in common]
    conf_agree = float(np.mean([a == b for a, b in zip(conf1, conf2)]))
    return {
        "n": len(common),
        "agreement": agreement,
        "kappa": k_overall,
        "kappa_ci95": [float(ci_lo), float(ci_hi)],
        "confidence_agreement": conf_agree,
        "boot_iterations": n_boot,
    }


# ---------------------------------------------------------------------------
# Descriptives
# ---------------------------------------------------------------------------
def descriptives(df: pd.DataFrame) -> dict:
    out: dict = {}
    out["n_total"] = int(len(df))
    out["n_user"] = int(df["is_user"].sum())
    out["n_builtin"] = int((~df["is_user"]).sum())
    out["status_counts"] = df["status_clean"].value_counts().to_dict()
    out["type_counts"] = df["type_clean"].value_counts().to_dict()
    out["jurisdiction_counts"] = df["jurisdiction_type"].value_counts().to_dict()
    out["score_quartiles"] = {
        "min": float(df["score"].min()),
        "q1": float(df["score"].quantile(0.25)),
        "median": float(df["score"].median()),
        "q3": float(df["score"].quantile(0.75)),
        "max": float(df["score"].max()),
        "mean": float(df["score"].mean()),
        "sd": float(df["score"].std()),
    }
    out["employees_quartiles"] = {
        "min": float(df["employees"].min()),
        "q1": float(df["employees"].quantile(0.25)),
        "median": float(df["employees"].median()),
        "q3": float(df["employees"].quantile(0.75)),
        "max": float(df["employees"].max()),
        "mean": float(df["employees"].mean()),
        "sd": float(df["employees"].std()),
    }
    out["domain_years_quartiles"] = {
        "n_known": int(df["domain_years"].notna().sum()),
        "median": float(df["domain_years"].median(skipna=True)),
        "mean": float(df["domain_years"].mean(skipna=True)),
    }
    out["ai_pct_known"] = int(df["ai_pct"].notna().sum())
    out["pct_zero_employees"] = float((df["employees"] == 0).mean())
    return out


def group_comparisons(df: pd.DataFrame) -> dict:
    """Kruskal-Wallis comparisons across taxonomy classes for focal variables,
    with effect-size approximation via eta-squared from H."""
    groups_by_type = [g["score"].values for _, g in df.groupby("type_clean") if len(g) >= 2]
    h_score, p_score = stats.kruskal(*groups_by_type)
    eta2_score = (h_score - len(groups_by_type) + 1) / (len(df) - len(groups_by_type))

    groups_emp = [g["employees"].values for _, g in df.groupby("type_clean") if len(g) >= 2]
    h_emp, p_emp = stats.kruskal(*groups_emp)
    eta2_emp = (h_emp - len(groups_emp) + 1) / (len(df) - len(groups_emp))

    return {
        "score_by_type": {
            "kruskal_H": float(h_score),
            "p_value": float(p_score),
            "eta_squared": float(eta2_score),
        },
        "employees_by_type": {
            "kruskal_H": float(h_emp),
            "p_value": float(p_emp),
            "eta_squared": float(eta2_emp),
        },
    }


# ---------------------------------------------------------------------------
# Multivariate structure (clustering)
# ---------------------------------------------------------------------------
def clustering_layer(df: pd.DataFrame) -> dict:
    feats = ["score", "log_employees", "domain_years", "ai_pct"]
    sub = df[feats].copy()
    sub = sub.fillna(sub.median(numeric_only=True))
    X = StandardScaler().fit_transform(sub)
    y_type = LabelEncoder().fit_transform(df["type_clean"])

    out: dict = {}
    out["features"] = feats
    out["solutions"] = {}
    for k in (3, 4, 5):
        kmeans = KMeans(n_clusters=k, random_state=SEED, n_init=20).fit(X)
        agg = AgglomerativeClustering(n_clusters=k).fit(X)
        try:
            gmm = GaussianMixture(n_components=k, random_state=SEED, n_init=5).fit(X)
            gmm_labels = gmm.predict(X)
        except Exception:
            gmm_labels = None
        ari_km_agg = adjusted_rand_score(kmeans.labels_, agg.labels_)
        ari_km_type = adjusted_rand_score(y_type, kmeans.labels_)
        ari_agg_type = adjusted_rand_score(y_type, agg.labels_)
        sil_km = silhouette_score(X, kmeans.labels_) if k < len(X) else np.nan
        sil_agg = silhouette_score(X, agg.labels_) if k < len(X) else np.nan
        out["solutions"][f"k={k}"] = {
            "silhouette_kmeans": float(sil_km),
            "silhouette_agglom": float(sil_agg),
            "ARI_kmeans_vs_agglom": float(ari_km_agg),
            "ARI_kmeans_vs_taxonomy": float(ari_km_type),
            "ARI_agglom_vs_taxonomy": float(ari_agg_type),
        }
        if gmm_labels is not None:
            out["solutions"][f"k={k}"]["ARI_gmm_vs_taxonomy"] = float(
                adjusted_rand_score(y_type, gmm_labels)
            )

    # Decision: pick k where ARI(km, agg) is maximized (most concordant solution).
    best_k = max(out["solutions"], key=lambda k: out["solutions"][k]["ARI_kmeans_vs_agglom"])
    out["preferred_k"] = best_k
    return out


# ---------------------------------------------------------------------------
# Classification + XAI
# ---------------------------------------------------------------------------
def classification_layer(df: pd.DataFrame) -> dict:
    feats = ["score", "log_employees", "domain_years", "ai_pct"]
    sub = df[feats].copy()
    sub = sub.fillna(sub.median(numeric_only=True))
    X = sub.values
    y = df["type_clean"].values
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    Xs = StandardScaler().fit_transform(X)

    # 5-fold stratified CV; protect against rare classes by clipping to min available folds.
    counts = pd.Series(y_enc).value_counts()
    n_splits = int(min(5, counts.min())) if counts.min() >= 2 else 2
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)

    results: dict = {"n_splits": n_splits, "classes": list(le.classes_)}

    logit = LogisticRegression(max_iter=2000, multi_class="multinomial")
    rf = RandomForestClassifier(n_estimators=400, random_state=SEED, n_jobs=-1)
    gb = GradientBoostingClassifier(random_state=SEED)
    surr = DecisionTreeClassifier(max_depth=3, random_state=SEED)

    for name, clf, X_use in (
        ("logistic", logit, Xs),
        ("random_forest", rf, X),
        ("gradient_boosting", gb, X),
    ):
        try:
            acc = cross_val_score(clf, X_use, y_enc, cv=skf, scoring="accuracy", n_jobs=-1)
            f1m = cross_val_score(clf, X_use, y_enc, cv=skf, scoring="f1_macro", n_jobs=-1)
            clf.fit(X_use, y_enc)
            yhat = clf.predict(X_use)
            results[name] = {
                "cv_accuracy_mean": float(acc.mean()),
                "cv_accuracy_sd": float(acc.std()),
                "cv_f1_macro_mean": float(f1m.mean()),
                "cv_f1_macro_sd": float(f1m.std()),
                "in_sample_accuracy": float(accuracy_score(y_enc, yhat)),
            }
        except Exception as exc:
            results[name] = {"error": str(exc)}

    # XAI: permutation importance on the RF (transparent baseline + tree-based).
    rf.fit(X, y_enc)
    perm = permutation_importance(rf, X, y_enc, n_repeats=50, random_state=SEED, n_jobs=-1)
    results["permutation_importance"] = {
        feats[i]: {"mean": float(perm.importances_mean[i]), "sd": float(perm.importances_std[i])}
        for i in range(len(feats))
    }

    # Surrogate tree on RF predictions.
    rf_pred = rf.predict(X)
    surr.fit(X, rf_pred)
    results["surrogate_tree"] = export_text(surr, feature_names=feats)
    results["surrogate_fidelity"] = float(
        accuracy_score(rf_pred, surr.predict(X))
    )

    # SHAP optional.
    try:
        import shap

        explainer = shap.TreeExplainer(rf)
        shap_vals = explainer.shap_values(X)
        # shap_vals is list[n_classes] of (n,d).
        if isinstance(shap_vals, list):
            global_imp = np.mean([np.mean(np.abs(sv), axis=0) for sv in shap_vals], axis=0)
        else:
            global_imp = np.mean(np.abs(shap_vals), axis=0)
            if global_imp.ndim > 1:
                global_imp = global_imp.mean(axis=tuple(range(global_imp.ndim - 1)))
        results["shap_global_importance"] = {
            feats[i]: float(global_imp[i]) for i in range(len(feats))
        }
    except Exception as exc:
        results["shap_global_importance"] = {"error": str(exc)}

    # Confusion matrix on full data with RF.
    cm = confusion_matrix(y_enc, rf.predict(X))
    results["rf_in_sample_confusion"] = {
        "labels": list(le.classes_),
        "matrix": cm.tolist(),
    }
    return results


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------
def robustness_layer(df: pd.DataFrame, payload: dict) -> dict:
    feats = ["score", "log_employees", "domain_years", "ai_pct"]
    sub = df[feats].copy().fillna(df[feats].median(numeric_only=True))
    X = sub.values
    y = LabelEncoder().fit_transform(df["type_clean"])

    out: dict = {}

    # Sensitivity to score threshold for Confirmed vs Dismissed - Real Co. labelling.
    sweeps: list[dict] = []
    for thr in (40, 45, 50, 55, 60):
        conf = df["score"] >= thr
        sweeps.append(
            {
                "threshold": thr,
                "n_confirmed_at_threshold": int(conf.sum()),
                "share_synthetic_or_dao": float(
                    df[conf]["type_clean"]
                    .isin(["Synthetic Company", "Agentic DAO", "AI-Enhanced Shell"])
                    .mean()
                ),
            }
        )
    out["threshold_sensitivity"] = sweeps

    # Leave-one-class-out for the RF classifier.
    loco: dict = {}
    for cls in sorted(df["type_clean"].unique()):
        mask = df["type_clean"] != cls
        if mask.sum() < 20 or df.loc[mask, "type_clean"].nunique() < 2:
            continue
        y_sub = LabelEncoder().fit_transform(df.loc[mask, "type_clean"])
        rf = RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1)
        counts = pd.Series(y_sub).value_counts()
        n_splits = int(min(5, counts.min()))
        if n_splits < 2:
            continue
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
        acc = cross_val_score(rf, X[mask.values], y_sub, cv=skf, scoring="accuracy", n_jobs=-1)
        loco[cls] = {"cv_accuracy_mean": float(acc.mean()), "cv_accuracy_sd": float(acc.std())}
    out["leave_one_class_out"] = loco

    # Bootstrap of overall RF accuracy.
    boots = []
    rf = RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1)
    n = len(X)
    for _ in range(500):
        idx = RNG.choice(n, size=n, replace=True)
        oob = np.setdiff1d(np.arange(n), idx)
        if len(oob) < 5 or len(set(y[idx])) < 2:
            continue
        rf.fit(X[idx], y[idx])
        boots.append(accuracy_score(y[oob], rf.predict(X[oob])))
    out["rf_oob_bootstrap"] = {
        "mean": float(np.mean(boots)),
        "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
        "iterations": len(boots),
    }

    # Inter-rater kappa after dropping the 4 most disputed cases (R1 != R2).
    r1 = payload.get("reviews", {})
    r2 = payload.get("reviews_r2", {})
    common = sorted(set(r1) & set(r2))
    y1 = [r1[k]["classification"] for k in common]
    y2 = [r2[k]["classification"] for k in common]
    disputed = [k for k, a, b in zip(common, y1, y2) if a != b]
    keep = [k for k in common if k not in disputed]
    if keep:
        y1k = [r1[k]["classification"] for k in keep]
        y2k = [r2[k]["classification"] for k in keep]
        out["kappa_excluding_disputed"] = {
            "n_dropped": len(disputed),
            "n_remaining": len(keep),
            "kappa": float(cohen_kappa_score(y1k, y2k)),
        }
    return out


# ---------------------------------------------------------------------------
# Solvency gate
# ---------------------------------------------------------------------------
def solvency_gate(results: dict) -> dict:
    claims: list[dict] = []

    # Claim 1: the 4-class taxonomy is empirically separable.
    rf_cv = results["classification"].get("random_forest", {}).get("cv_accuracy_mean", 0)
    rf_boot = results["robustness"]["rf_oob_bootstrap"]["mean"]
    rf_boot_lo = results["robustness"]["rf_oob_bootstrap"]["ci95"][0]
    convergence_1 = (
        results["classification"].get("gradient_boosting", {}).get("cv_accuracy_mean", 0) > 0.5
        and rf_cv > 0.5
    )
    stability_1 = rf_boot_lo > 0.4
    claims.append(
        {
            "id": "C1_taxonomy_separable",
            "convergent": bool(convergence_1),
            "stable": bool(stability_1),
            "score": int(convergence_1) + int(stability_1),
            "headline": f"RF 5-fold CV accuracy={rf_cv:.2f}, bootstrap mean={rf_boot:.2f} (95% CI lower={rf_boot_lo:.2f}).",
        }
    )

    # Claim 2: inter-rater reliability passes the conventional 0.7 threshold.
    kappa = results["kappa"]["kappa"]
    kappa_lo = results["kappa"]["kappa_ci95"][0]
    claims.append(
        {
            "id": "C2_kappa_above_0_70",
            "convergent": kappa >= 0.70,
            "stable": kappa_lo >= 0.50,
            "score": int(kappa >= 0.70) + int(kappa_lo >= 0.50),
            "headline": f"Cohen's Kappa={kappa:.3f}, bootstrap 95% CI lower={kappa_lo:.3f}.",
        }
    )

    # Claim 3: score >= 50 cutoff yields a sample dominated by synthetic / DAO / shell classes.
    swept = results["robustness"]["threshold_sensitivity"]
    sweet = next(s for s in swept if s["threshold"] == 50)
    claims.append(
        {
            "id": "C3_score_threshold_selects_synthetic_dominated",
            "convergent": sweet["share_synthetic_or_dao"] >= 0.5,
            "stable": all(s["share_synthetic_or_dao"] >= 0.4 for s in swept if s["threshold"] >= 45),
            "score": int(sweet["share_synthetic_or_dao"] >= 0.5)
            + int(all(s["share_synthetic_or_dao"] >= 0.4 for s in swept if s["threshold"] >= 45)),
            "headline": f"At score>=50 {sweet['share_synthetic_or_dao']:.2f} of selected entities fall in synthetic/DAO/shell classes.",
        }
    )

    # Claim 4: cluster solution agrees with taxonomy at preferred k.
    pref = results["clustering"]["preferred_k"]
    sol = results["clustering"]["solutions"][pref]
    ari_taxonomy = max(sol["ARI_kmeans_vs_taxonomy"], sol["ARI_agglom_vs_taxonomy"])
    claims.append(
        {
            "id": "C4_unsupervised_recovers_taxonomy_partially",
            "convergent": sol["ARI_kmeans_vs_agglom"] >= 0.4,
            "stable": ari_taxonomy >= 0.10,
            "score": int(sol["ARI_kmeans_vs_agglom"] >= 0.4) + int(ari_taxonomy >= 0.10),
            "headline": f"At {pref}, ARI(kmeans, agglom)={sol['ARI_kmeans_vs_agglom']:.2f}, max ARI vs taxonomy={ari_taxonomy:.2f}.",
        }
    )

    failures = [c for c in claims if c["score"] < 2]
    return {
        "claims": claims,
        "n_failed": len(failures),
        "needs_recursion": len(failures) > 0,
        "failures": failures,
    }


# ---------------------------------------------------------------------------
# Recursion driver
# ---------------------------------------------------------------------------
def run_pipeline(df: pd.DataFrame, payload: dict, label: str) -> dict:
    return {
        "label": label,
        "n": int(len(df)),
        "descriptives": descriptives(df),
        "group_comparisons": group_comparisons(df),
        "clustering": clustering_layer(df),
        "classification": classification_layer(df),
        "robustness": robustness_layer(df, payload),
        "kappa": kappa_block(payload),
    }


def recurse(df: pd.DataFrame, payload: dict) -> dict:
    rounds: list[dict] = []

    # Round 1 - all entities, 4-class taxonomy.
    r1 = run_pipeline(df, payload, label="Round 1: all entities, 4-class taxonomy")
    r1["solvency"] = solvency_gate(r1)
    rounds.append(r1)

    # Round 2 - collapse to 2-class (synthetic/agentic-DAO vs control).
    df2 = df.copy()
    df2["type_clean"] = np.where(
        df2["type_clean"].isin(["Synthetic Company", "Agentic DAO", "AI-Enhanced Shell"]),
        "synthetic_or_dao",
        "agentic_or_other",
    )
    r2 = run_pipeline(df2, payload, label="Round 2: 2-class collapse (synthetic_or_dao vs agentic_or_other)")
    r2["solvency"] = solvency_gate(r2)
    rounds.append(r2)

    # Round 3 - drop entities with score < 40 (the control band) to test whether the
    # signal survives without the easy-to-classify controls.
    df3 = df[df["score"] >= 40].copy()
    r3 = run_pipeline(df3, payload, label="Round 3: only score >= 40 entities (no easy controls)")
    r3["solvency"] = solvency_gate(r3)
    rounds.append(r3)

    return {"rounds": rounds}


def main() -> None:
    df = build_entity_frame()
    payload = json.loads((PROJECT / "synthco_data.json").read_text(encoding="utf-8"))

    df.to_csv(ROOT / "entities_unified.csv", index=False)

    result = recurse(df, payload)

    out_path = ROOT / "results.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    # Human-readable summary.
    summary_lines = ["# Recursive analysis results", ""]
    for r in result["rounds"]:
        summary_lines.append(f"## {r['label']}  (n={r['n']})")
        sg = r["solvency"]
        summary_lines.append(f"- Failed solvency claims: {sg['n_failed']}/{len(sg['claims'])}")
        for c in sg["claims"]:
            mark = "OK" if c["score"] == 2 else ("PARTIAL" if c["score"] == 1 else "FAIL")
            summary_lines.append(f"  - [{mark}] {c['id']}: {c['headline']}")
        kappa = r["kappa"]
        summary_lines.append(
            f"- Cohen's Kappa (R1 vs R2, n={kappa['n']}): {kappa['kappa']:.3f} "
            f"(95% CI [{kappa['kappa_ci95'][0]:.3f}, {kappa['kappa_ci95'][1]:.3f}])"
        )
        cls = r["classification"]
        for clf_name in ("logistic", "random_forest", "gradient_boosting"):
            if clf_name in cls and "cv_accuracy_mean" in cls[clf_name]:
                summary_lines.append(
                    f"- {clf_name}: CV acc={cls[clf_name]['cv_accuracy_mean']:.3f} "
                    f"+/- {cls[clf_name]['cv_accuracy_sd']:.3f}, F1m={cls[clf_name]['cv_f1_macro_mean']:.3f}"
                )
        summary_lines.append("")
    (ROOT / "results_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    print("Wrote:", out_path)
    print("Wrote:", ROOT / "results_summary.md")
    print("Rounds executed:", len(result["rounds"]))


if __name__ == "__main__":
    main()
