"""
Generate publication-quality academic figures (300 DPI, serif fonts, minimal
chartjunk) from analysis/results.json and analysis/entities_unified.csv.

Outputs in analysis/figures/:
  fig1_conceptual_model.png     - Taxonomy + algorithmic governance positioning
  fig2_osint_funnel.png         - Detection pipeline (520 -> 89)
  fig3_pca_clusters.png         - PCA scatter coloured by taxonomy class
  fig4_classifier_performance.png - 4-class vs binary CV accuracy with SD bars
  fig5_xai_importance.png       - Permutation + SHAP feature importance
  fig6_threshold_sensitivity.png  - Score cutoff sweep
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(exist_ok=True)

# Academic style — serif, neutral grid, no chartjunk
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Liberation Serif"],
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "legend.frameon": False,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.15,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "grid.linewidth": 0.5,
})

# Colour-blind safe palette (Okabe-Ito derived, journal-friendly)
CLASS_COLOURS = {
    "Synthetic Company": "#D55E00",       # vermillion
    "Agentic DAO": "#0072B2",             # blue
    "Agentic Organization": "#009E73",    # green
    "Multi-Agent System": "#CC79A7",      # mauve
    "AI-Enhanced Shell": "#E69F00",       # orange
    "Dismissed – Real Co.": "#999999",    # grey
}


def load() -> tuple[dict, pd.DataFrame]:
    results = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    df = pd.read_csv(ROOT / "entities_unified.csv")
    df["type_clean"] = df["type_clean"].str.replace("–", "-", regex=False).str.replace("–", "-", regex=False).str.strip()
    # Normalise label spelling for the palette
    df["type_display"] = df["type_clean"].replace({
        "Dismissed - Real Co.": "Dismissed – Real Co.",
    })
    return results, df


# ---------------------------------------------------------------------------
# Figure 1 - Conceptual model: 4 classes + sub-type + algorithmic governance
# ---------------------------------------------------------------------------
def fig1_conceptual_model() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # Top: phenomenon
    _box(ax, 0.2, 5.7, 9.6, 0.9,
         "Phenomenon: entrepreneurial entities in which the legal,\n"
         "decisional or operational locus of the firm is itself synthetic or agentic",
         face="#f0f0f0", edge="#444444", fontweight="bold", fontsize=10)

    # Middle: 4 classes + sub-type as 5 boxes
    classes = [
        ("Synthetic Company",   "0 employees;\nAI runs all functions",  CLASS_COLOURS["Synthetic Company"]),
        ("Agentic Organization", "Humans + AI agent\nin a core function",  CLASS_COLOURS["Agentic Organization"]),
        ("Multi-Agent System",  "Orchestration of\nmultiple AI agents", CLASS_COLOURS["Multi-Agent System"]),
        ("Agentic DAO",         "On-chain smart\ncontracts + AI agents", CLASS_COLOURS["Agentic DAO"]),
    ]
    w = 2.1
    spacing = (10 - w * 4) / 5
    for i, (name, sub, col) in enumerate(classes):
        x = spacing + i * (w + spacing)
        _box(ax, x, 3.0, w, 1.6, f"{name}\n\n{sub}", face=col, alpha=0.18, edge=col, fontsize=9, fontweight="bold")

    # AI-Enhanced Shell as a sub-type sitting between Synthetic and Agentic Org
    _box(ax, 1.2, 1.5, 3.0, 0.9,
         "AI-Enhanced Shell (sub-type)\nnominee human(s) + AI operates",
         face=CLASS_COLOURS["AI-Enhanced Shell"], alpha=0.18,
         edge=CLASS_COLOURS["AI-Enhanced Shell"], fontsize=8.5, fontweight="bold")

    # Bottom: algorithmic governance positioning
    _box(ax, 0.2, 0.05, 9.6, 1.0,
         "Algorithmic governance  (proposed fourth mode)\n"
         "enforcement-by-code  +  principal substitution,\n"
         "alongside market, hierarchy and network  (Powell, 1990; Williamson, 1991)",
         face="#222244", alpha=0.10, edge="#222244", fontsize=8.5, fontweight="bold")

    # Arrows: phenomenon → 4 classes
    for i in range(4):
        x = spacing + i * (w + spacing) + w / 2
        ax.annotate("", xy=(x, 4.65), xytext=(x, 5.65),
                    arrowprops=dict(arrowstyle="-|>", color="#666666", lw=1.0))
    # Sub-type arrow upward
    ax.annotate("", xy=(2.7, 2.95), xytext=(2.7, 2.45),
                arrowprops=dict(arrowstyle="-|>", color=CLASS_COLOURS["AI-Enhanced Shell"], lw=1.0))
    # All 5 → algorithmic governance
    for x in [spacing + i * (w + spacing) + w / 2 for i in range(4)] + [2.7]:
        ax.annotate("", xy=(x, 1.05), xytext=(x, max(1.45, 2.95) if x != 2.7 else 1.5),
                    arrowprops=dict(arrowstyle="-|>", color="#888888", lw=0.7, alpha=0.6))

    # figure title removed (caption in manuscript)
    fig.savefig(FIG_DIR / "fig1_conceptual_model.png")
    plt.close(fig)


def _box(ax, x, y, w, h, text, face="#eeeeee", edge="#444444",
         alpha=1.0, fontsize=9, fontweight="normal"):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                         linewidth=1.2, edgecolor=edge, facecolor=face, alpha=alpha)
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, fontweight=fontweight, color="#111111", wrap=True)


# ---------------------------------------------------------------------------
# Figure 2 - OSINT funnel
# ---------------------------------------------------------------------------
def fig2_funnel() -> None:
    stages = [
        ("Raw scrape\n(6 source families)", 520, "#74b9ff"),
        ("AI-keyword filter", 210, "#74b9ff"),
        ("Synthetic-score ≥ 50", 60, "#00b894"),
        ("Manual expansion", 89, "#fdcb6e"),
        ("Human-verified sample", 89, "#e94560"),
        ("Confirmed synthetic/agentic", 61, "#a29bfe"),
    ]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    y_pos = np.arange(len(stages))[::-1]
    counts = [s[1] for s in stages]
    labels = [s[0] for s in stages]
    colours = [s[2] for s in stages]
    bars = ax.barh(y_pos, counts, color=colours, alpha=0.78, edgecolor="black", linewidth=0.6, height=0.62)
    for bar, c in zip(bars, counts):
        ax.text(bar.get_width() + 8, bar.get_y() + bar.get_height() / 2,
                f"n = {c}", va="center", fontsize=9)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Number of entities")
    ax.set_xlim(0, max(counts) * 1.15)
    # figure title removed (caption in manuscript)
    ax.grid(axis="x", alpha=0.25, linestyle="--", linewidth=0.5)
    ax.grid(axis="y", visible=False)
    fig.savefig(FIG_DIR / "fig2_osint_funnel.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3 - PCA scatter of the 89 entities, coloured by class
# ---------------------------------------------------------------------------
def fig3_pca_clusters(df: pd.DataFrame) -> None:
    feats = ["score", "log_employees", "domain_years", "ai_pct"]
    sub = df[feats].copy()
    sub = sub.fillna(sub.median(numeric_only=True))
    X = StandardScaler().fit_transform(sub)
    pca = PCA(n_components=2, random_state=42)
    XY = pca.fit_transform(X)
    explained = pca.explained_variance_ratio_

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for cls, col in CLASS_COLOURS.items():
        mask = df["type_display"] == cls
        if not mask.any():
            continue
        ax.scatter(XY[mask, 0], XY[mask, 1], c=col, label=f"{cls} (n={int(mask.sum())})",
                   s=58, alpha=0.78, edgecolor="black", linewidth=0.45)
    ax.axhline(0, color="#999", lw=0.6, alpha=0.5)
    ax.axvline(0, color="#999", lw=0.6, alpha=0.5)
    ax.set_xlabel(f"Principal Component 1 ({explained[0]*100:.1f}% variance)")
    ax.set_ylabel(f"Principal Component 2 ({explained[1]*100:.1f}% variance)")
    # figure title removed (caption in manuscript)
    ax.legend(loc="upper right", fontsize=8.5, markerscale=0.9, frameon=False)
    fig.savefig(FIG_DIR / "fig3_pca_clusters.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4 - Classifier performance (4-class vs binary) with SD error bars
# ---------------------------------------------------------------------------
def fig4_classifier_performance(results: dict) -> None:
    r1 = results["rounds"][0]["classification"]
    r2 = results["rounds"][1]["classification"]
    estimators = ["logistic", "random_forest", "gradient_boosting"]
    labels = ["Logistic regression", "Random forest", "Gradient boosting"]
    four_acc = [r1[e]["cv_accuracy_mean"] for e in estimators]
    four_sd = [r1[e]["cv_accuracy_sd"] for e in estimators]
    bin_acc = [r2[e]["cv_accuracy_mean"] for e in estimators]
    bin_sd = [r2[e]["cv_accuracy_sd"] for e in estimators]

    x = np.arange(len(estimators))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    b1 = ax.bar(x - w / 2, four_acc, w, yerr=four_sd, capsize=4,
                color="#fdcb6e", edgecolor="black", linewidth=0.7,
                label="4-class taxonomy", error_kw={"linewidth": 1.1, "ecolor": "#333"})
    b2 = ax.bar(x + w / 2, bin_acc, w, yerr=bin_sd, capsize=4,
                color="#00b894", edgecolor="black", linewidth=0.7,
                label="Binary (synthetic/DAO vs other)", error_kw={"linewidth": 1.1, "ecolor": "#333"})
    ax.axhline(0.167, color="#c0392b", lw=0.8, ls=":", label="4-class random baseline (1/6)")
    ax.axhline(0.500, color="#c0392b", lw=0.8, ls="--", label="Binary random baseline (1/2)")

    for bars, accs in ((b1, four_acc), (b2, bin_acc)):
        for bar, val in zip(bars, accs):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.025,
                    f"{val:.2f}", ha="center", fontsize=8.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("5-fold stratified CV accuracy")
    ax.set_ylim(0, 1.05)
    # figure title removed (caption in manuscript)
    ax.legend(loc="lower right", fontsize=8.5)
    fig.savefig(FIG_DIR / "fig4_classifier_performance.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 5 - XAI feature importance (permutation + SHAP)
# ---------------------------------------------------------------------------
def fig5_xai_importance(results: dict) -> None:
    cls = results["rounds"][0]["classification"]
    perm = cls["permutation_importance"]
    shap = cls.get("shap_global_importance", {})
    features = ["log_employees", "ai_pct", "domain_years", "score"]
    perm_vals = [perm[f]["mean"] for f in features]
    perm_sd = [perm[f]["sd"] for f in features]
    shap_vals = [shap.get(f, 0) if isinstance(shap, dict) else 0 for f in features]

    # Order by permutation importance
    order = np.argsort(perm_vals)
    features = [features[i] for i in order]
    perm_vals = [perm_vals[i] for i in order]
    perm_sd = [perm_sd[i] for i in order]
    shap_vals = [shap_vals[i] for i in order]

    y = np.arange(len(features))
    h = 0.38
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.barh(y + h / 2, perm_vals, h, xerr=perm_sd, capsize=3,
            color="#74b9ff", edgecolor="black", linewidth=0.6,
            label="Permutation importance (±SD)", error_kw={"linewidth": 1.0, "ecolor": "#333"})
    ax.barh(y - h / 2, shap_vals, h,
            color="#e94560", edgecolor="black", linewidth=0.6,
            label="SHAP global importance (mean |φ|)")
    ax.set_yticks(y)
    ax.set_yticklabels(features)
    ax.set_xlabel("Importance")
    # figure title removed (caption in manuscript)
    ax.legend(loc="lower right", fontsize=8.5)
    fig.savefig(FIG_DIR / "fig5_xai_importance.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 6 - Threshold sensitivity sweep
# ---------------------------------------------------------------------------
def fig6_threshold_sensitivity(results: dict) -> None:
    sweep = results["rounds"][0]["robustness"]["threshold_sensitivity"]
    thresholds = [s["threshold"] for s in sweep]
    shares = [s["share_synthetic_or_dao"] * 100 for s in sweep]
    n_retained = [s["n_confirmed_at_threshold"] for s in sweep]

    fig, ax1 = plt.subplots(figsize=(7.5, 4.6))
    color1 = "#00b894"
    color2 = "#74b9ff"
    line1, = ax1.plot(thresholds, shares, marker="o", linewidth=2.0, markersize=7,
                      color=color1, label="% synthetic/DAO/shell in retained sample")
    ax1.fill_between(thresholds, shares, alpha=0.12, color=color1)
    ax1.set_xlabel("Synthetic-score threshold (≥)")
    ax1.set_ylabel("% in synthetic / DAO / shell classes", color=color1)
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.set_ylim(0, 100)
    for t, s in zip(thresholds, shares):
        ax1.text(t, s + 2, f"{s:.0f}%", ha="center", color=color1, fontsize=8.5, fontweight="bold")

    ax2 = ax1.twinx()
    ax2.spines["top"].set_visible(False)
    line2, = ax2.plot(thresholds, n_retained, marker="s", linewidth=1.4, markersize=6,
                      color=color2, linestyle="--", label="N retained")
    ax2.set_ylabel("N entities retained", color=color2)
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.grid(False)

    lines = [line1, line2]
    ax1.legend(lines, [l.get_label() for l in lines], loc="lower right", fontsize=8.5)
    # figure title removed (caption in manuscript)
    fig.savefig(FIG_DIR / "fig6_threshold_sensitivity.png")
    plt.close(fig)


def main() -> None:
    results, df = load()
    fig1_conceptual_model()
    fig2_funnel()
    fig3_pca_clusters(df)
    fig4_classifier_performance(results)
    fig5_xai_importance(results)
    fig6_threshold_sensitivity(results)
    print("Wrote 6 figures to", FIG_DIR)


if __name__ == "__main__":
    main()
