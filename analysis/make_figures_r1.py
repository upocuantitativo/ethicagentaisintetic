# -*- coding: utf-8 -*-
"""
R1 figures. Six PNGs at 300 dpi into analysis/figures_r1/.

Every legend is placed OUTSIDE the plot area, which the reviewer asked for on
Figures 3, 4 and 5 and which we apply throughout for consistency. Figure 4 now
plots the majority baseline rather than a uniform 1/K reference, correcting the
1/6-versus-four-class inconsistency the statistical editors identified.

Usage: python analysis/make_figures_r1.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, Rectangle
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures_r1"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 9,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#333333",
    "savefig.dpi": 300,
    "figure.dpi": 300,
})

INK = "#1a1a1a"
GREY = "#8a8a8a"
ACCENT = "#2f5d8a"
ACCENT2 = "#a34a2a"
BASE = "#b9b9b9"


def load():
    res = json.loads((ROOT / "results_v2.json").read_text(encoding="utf-8"))
    df = pd.read_csv(ROOT / "audit_dataset.csv")
    return res, df[df["in_analytic_sample"]].reset_index(drop=True)


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  wrote", name)


# ---------------------------------------------------------------------------
def fig1_dimensions():
    """The five-dimensional scheme replacing the four nominal classes."""
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.4); ax.axis("off")

    dims = [
        ("D1  Legal form", "registered company | foundation |\nunincorporated on-chain"),
        ("D2  Human operational\n       participation", "none | nominee | small team |\nsubstantial workforce"),
        ("D3  AI decision authority", "none/advisory | single function |\nmulti-function | governance"),
        ("D4  Agent architecture", "not agentic | single agent |\nmulti-agent"),
        ("D5  Governance substrate", "conventional | hybrid | on-chain"),
    ]
    y = 5.55
    for i, (title, levels) in enumerate(dims):
        ax.add_patch(Rectangle((0.15, y - 0.86), 6.5, 0.92, facecolor="#f4f4f4",
                               edgecolor=INK, linewidth=0.8))
        ax.text(0.35, y - 0.20, title, fontsize=8.6, fontweight="bold", va="top", color=INK)
        ax.text(3.35, y - 0.22, levels, fontsize=7.4, va="top", color="#444444")
        y -= 1.06

    ax.add_patch(Rectangle((7.05, 1.05), 2.75, 4.45, facecolor="#eef3f8",
                           edgecolor=ACCENT, linewidth=1.0))
    ax.text(8.42, 5.22, "Derived types", fontsize=8.8, fontweight="bold",
            ha="center", color=ACCENT)
    ax.text(8.42, 4.78,
            "combinations of\ndimension values,\nnot mutually\nexclusive classes",
            fontsize=7.4, ha="center", va="top", color="#333333")
    ax.text(8.42, 3.30,
            "Delegation index\n= f(D2, D3, D5)",
            fontsize=7.6, ha="center", va="top", color=INK, fontweight="bold")
    ax.text(8.42, 2.45,
            "AI-Enhanced Shell\n(D1 company, D2 nominee,\nD3 multi-function,\nD5 conventional)\n— cell not observed —",
            fontsize=6.9, ha="center", va="top", color=ACCENT2, style="italic")

    ax.add_patch(FancyArrowPatch((6.72, 3.3), (7.0, 3.3), arrowstyle="-|>",
                                 mutation_scale=11, color=INK, linewidth=1.0))
    save(fig, "fig1_dimensions.png")


# ---------------------------------------------------------------------------
def fig2_consort():
    """CONSORT-style sample flow, including the excluded rows."""
    flow = pd.read_csv(ROOT / "consort_flow.csv")
    fig, ax = plt.subplots(figsize=(6.6, 6.0))
    ax.set_xlim(0, 10); ax.set_ylim(0, 12.2); ax.axis("off")

    main_stages = [
        ("Raw scrape, six source families", 520),
        ("AI-keyword filter (≥2 signals)", 210),
        ("Rows carried into the workbench", 89),
        ("Analytic sample: observed entities", 45),
    ]
    y = 11.2
    for i, (label, n) in enumerate(main_stages):
        ax.add_patch(Rectangle((0.5, y - 0.78), 5.4, 0.85, facecolor="#f4f4f4",
                               edgecolor=INK, linewidth=0.9))
        ax.text(3.2, y - 0.36, f"{label}\nn = {n:,}", fontsize=8.0, ha="center",
                va="center", color=INK)
        if i < len(main_stages) - 1:
            ax.add_patch(FancyArrowPatch((3.2, y - 0.80), (3.2, y - 1.62),
                                         arrowstyle="-|>", mutation_scale=11,
                                         color=INK, linewidth=0.9))
        y -= 2.45

    # Side boxes sit on the transition they actually describe.
    side = [
        (9.98, "#fbf3ef", ACCENT2, "--",
         "Excluded: not AI-related\nn = 310"),
        (7.53, "#f4f4f4", GREY, "-",
         "Score pipeline carried 60 rows\n(12 scoring < 50 kept as hard\nnegatives) + 29 added by\nstructured manual search"),
        (5.08, "#fbf3ef", ACCENT2, "--",
         "Excluded: demonstration records\nn = 44\n(36 not found; 8 name collision;\n0 established)"),
    ]
    for ey, face, edge, ls, text in side:
        ax.add_patch(Rectangle((6.25, ey - 1.02), 3.55, 1.12, facecolor=face,
                               edgecolor=edge, linewidth=0.9, linestyle=ls))
        ax.text(8.02, ey - 0.46, text, fontsize=6.9, ha="center", va="center",
                color=edge if edge != GREY else "#444444")
        ax.add_patch(FancyArrowPatch((5.92, ey - 0.46), (6.22, ey - 0.46),
                                     arrowstyle="-|>", mutation_scale=9,
                                     color=edge, linewidth=0.8, linestyle=ls))

    # Composition of the analytic sample, joined to it.
    ax.add_patch(FancyArrowPatch((3.2, 3.05), (3.2, 2.02), arrowstyle="-|>",
                                 mutation_scale=11, color=INK, linewidth=0.9))
    ax.add_patch(Rectangle((0.5, 0.62), 5.4, 1.38, facecolor="#eef3f8",
                           edgecolor=ACCENT, linewidth=0.9))
    ax.text(3.2, 1.31,
            "19 verified AI-delegated   |   26 controls\n"
            "16 score pipeline   |   29 manual search\n"
            "10 double-coded by two raters",
            fontsize=7.4, ha="center", va="center", color=INK)
    save(fig, "fig2_consort_flow.png")


# ---------------------------------------------------------------------------
def fig3_pca(df):
    """PCA projection. Legend below the axes, per reviewer comment."""
    feats = ["log_employees", "domain_years", "ai_pct"]
    X = SimpleImputer(strategy="median").fit_transform(df[feats])
    X = StandardScaler().fit_transform(X)
    p = PCA(n_components=2, random_state=42)
    xy = p.fit_transform(X)

    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    groups = [(0, "Control (human-led)", GREY, "o"),
              (1, "Verified AI-delegated", ACCENT, "^")]
    conf = df["status_clean"].eq("Confirmed").astype(int).values
    for val, label, colour, marker in groups:
        m = conf == val
        ax.scatter(xy[m, 0], xy[m, 1], s=46, c=colour, marker=marker,
                   edgecolors="white", linewidths=0.6, label=f"{label} (n = {m.sum()})",
                   alpha=0.9)
    ax.axhline(0, color="#dddddd", linewidth=0.7, zorder=0)
    ax.axvline(0, color="#dddddd", linewidth=0.7, zorder=0)
    ax.set_xlabel(f"PC1 ({p.explained_variance_ratio_[0]*100:.0f}% of variance)")
    ax.set_ylabel(f"PC2 ({p.explained_variance_ratio_[1]*100:.0f}% of variance)")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    # Legend outside the plot area.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2,
              fontsize=8, frameon=False)
    save(fig, "fig3_pca_projection.png")


# ---------------------------------------------------------------------------
def fig4_classifier(res):
    """Accuracy against the MAJORITY baseline, not a uniform 1/K reference."""
    sup = res["supervised"]
    specs = [
        ("Primary\n(no score, no detector)", sup["primary_no_score_no_detector"]),
        ("Sensitivity\n(+ AI-text detector)", sup["sensitivity_with_ai_detector"]),
        ("Prior specification\n(score included)", sup["r0_style_with_score_leaky"]),
    ]
    labels = [s[0] for s in specs]
    lr = [s[1]["logistic"]["cv_accuracy_mean"] for s in specs]
    rf = [s[1]["random_forest"]["cv_accuracy_mean"] for s in specs]
    maj = specs[0][1]["baseline_majority"]["mean"]
    strat = specs[0][1]["baseline_stratified"]["mean"]

    x = np.arange(len(specs)); w = 0.34
    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    ax.bar(x - w/2, lr, w, label="Logistic regression", color=BASE,
           edgecolor=INK, linewidth=0.7)
    ax.bar(x + w/2, rf, w, label="Random forest", color=ACCENT,
           edgecolor=INK, linewidth=0.7)
    ax.axhline(maj, color=ACCENT2, linestyle="--", linewidth=1.1,
               label=f"Majority baseline ({maj:.3f})")
    ax.axhline(strat, color="#999999", linestyle=":", linewidth=1.1,
               label=f"Stratified-random baseline ({strat:.3f})")
    for xi, v in zip(x - w/2, lr):
        ax.text(xi, v + 0.012, f"{v:.3f}", ha="center", fontsize=7.4)
    for xi, v in zip(x + w/2, rf):
        ax.text(xi, v + 0.012, f"{v:.3f}", ha="center", fontsize=7.4)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Nested cross-validated accuracy")
    ax.set_ylim(0, 1.06)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2,
              fontsize=7.8, frameon=False)
    save(fig, "fig4_classifier_vs_baseline.png")


# ---------------------------------------------------------------------------
def fig5_holdouts(res):
    """Holdout accuracy against each holdout's own majority baseline."""
    hs = [h for h in res["holdouts"] if "accuracy" in h]
    pretty = {
        "temporal_youngest_half": "Temporal\n(youngest half)",
        "jurisdictional_permissive_decentralized": "Jurisdictional\n(permissive/on-chain)",
        "source_family_press": "Source family\n(press)",
        "source_family_chain_analytics": "Source family\n(chain analytics)",
        "channel_stage4_manual_as_independent_test": "Channel\n(manual as test set)",
    }
    hs = [h for h in hs if h["tag"] in pretty]
    labels = [pretty[h["tag"]] for h in hs]
    acc = [h["accuracy"] for h in hs]
    base = [h["majority_baseline"] for h in hs]

    y = np.arange(len(hs))[::-1]; h = 0.36
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.barh(y + h/2, acc, h, label="Holdout accuracy", color=ACCENT,
            edgecolor=INK, linewidth=0.7)
    ax.barh(y - h/2, base, h, label="Majority baseline within holdout",
            color=BASE, edgecolor=INK, linewidth=0.7)
    for yi, v in zip(y + h/2, acc):
        ax.text(v + 0.012, yi, f"{v:.3f}", va="center", fontsize=7.4)
    for yi, v in zip(y - h/2, base):
        ax.text(v + 0.012, yi, f"{v:.3f}", va="center", fontsize=7.4)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Accuracy"); ax.set_xlim(0, 1.04)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2,
              fontsize=8, frameon=False)
    save(fig, "fig5_holdouts.png")


# ---------------------------------------------------------------------------
def fig6_detector(res, df):
    """ROC for the synthetic score used as a detector, not as a predictor."""
    from sklearn.metrics import roc_curve
    d = res["score_as_detector"]
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    sets = [("all_observed", df, "All observed entities", ACCENT, "-"),
            ("stage4_score_independent", df[df["channel"] == "stage4_manual"],
             "Stage-4 only (score played no\npart in selection)", ACCENT2, "--")]
    for key, sub, label, colour, ls in sets:
        y = sub["status_clean"].eq("Confirmed").astype(int).values
        fpr, tpr, _ = roc_curve(y, sub["score"].values)
        auc = d[key]["auc"]; lo, hi = d[key]["auc_ci95"]
        ax.plot(fpr, tpr, color=colour, linestyle=ls, linewidth=1.6,
                label=f"{label}\nAUC = {auc:.3f} [{lo:.3f}, {hi:.3f}], n = {len(sub)}")
    ax.plot([0, 1], [0, 1], color="#bbbbbb", linewidth=0.9, linestyle=":",
            label="Chance")
    ax.set_xlabel("False-positive rate"); ax.set_ylabel("True-positive rate")
    ax.set_xlim(-0.01, 1.01); ax.set_ylim(-0.01, 1.01)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), fontsize=7.4,
              frameon=False)
    save(fig, "fig6_score_as_detector.png")


def main():
    res, df = load()
    print("building R1 figures ->", OUT)
    fig1_dimensions()
    fig2_consort()
    fig3_pca(df)
    fig4_classifier(res)
    fig5_holdouts(res)
    fig6_detector(res, df)


if __name__ == "__main__":
    main()
