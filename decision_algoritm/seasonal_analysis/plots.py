import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from config import (
    COINS, YEARS, COIN_COLORS, CHART,
    MONTH_STARTS, MONTHS_CZ, MONTHS_FULL_CZ,
    BG, CARD_BG, BORDER, TEXT, MUTED, ZEROLINE, OUTPUT_DIR, THRESHOLDS, legend_items,
)


def _style_ax(ax, title: str = "", xlabel: bool = False) -> None:
    ax.set_facecolor(BG)
    ax.tick_params(colors=MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
    ax.grid(True, color=BORDER, alpha=0.6, linewidth=0.6)
    ax.axhline(0, color=ZEROLINE, linestyle="--", linewidth=0.8)
    if title:
        ax.set_title(title, color=TEXT, fontsize=11, pad=6)
    if xlabel:
        ax.set_xticks(MONTH_STARTS)
        ax.set_xticklabels(MONTHS_CZ, color=MUTED, fontsize=9)
    ax.set_xlim(1, 365)


def save_graph(fig, filename: str) -> None:
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)


def plot_avg_seasonal(avg_df: pd.DataFrame) -> plt.Figure:
    """Prumerny sezonni vzor pro kazdy coin s pasem +/- 1 std."""
    fig, axes = plt.subplots(
        len(COINS), 1, figsize=(16, 3.5 * len(COINS)),
        sharex=True, facecolor=BG,
    )
    fig.suptitle("Průměrný sezonní vzor (2021–2026)", color=TEXT, fontsize=14, y=1.01)

    for ax, coin in zip(axes, COINS):
        d = avg_df[avg_df["coin"] == coin].sort_values("day")
        _style_ax(ax, title=coin, xlabel=(coin == COINS[-1]))
        ax.fill_between(
            d["day"],
            d["mean_pct"] - d["std_pct"],
            d["mean_pct"] + d["std_pct"],
            alpha=0.18, color=COIN_COLORS[coin],
        )
        ax.plot(d["day"], d["mean_pct"], color=COIN_COLORS[coin], linewidth=2.2, label=f"{coin} prumer")
        ax.set_ylabel("% od 1. ledna", color=MUTED, fontsize=9)
        ax.legend(loc="upper right", facecolor=CARD_BG, labelcolor=TEXT, framealpha=0.8, fontsize=9)

    plt.tight_layout()
    save_graph(fig, "01_avg_seasonal_pattern.png")
    return fig


def plot_all_years_overlay(norm_df: pd.DataFrame) -> plt.Figure:
    """Vsechna leta pres sebe pro kazdy coin (kazda cara = 1 rok)."""
    fig, axes = plt.subplots(
        len(COINS), 1, figsize=(16, 3.5 * len(COINS)),
        sharex=True, facecolor=BG,
    )
    fig.suptitle("Překrytí let dle aktiv", color=TEXT, fontsize=14, y=1.01)

    palette = plt.cm.tab10(np.linspace(0, 0.6, len(YEARS)))

    for ax, coin in zip(axes, COINS):
        _style_ax(ax, title=coin, xlabel=(coin == COINS[-1]))
        ax.set_ylabel("% od 1. ledna", color=MUTED, fontsize=9)

        for year, color in zip(sorted(norm_df[norm_df["coin"] == coin]["year"].unique()), palette):
            d = (norm_df[(norm_df["coin"] == coin) & (norm_df["year"] == year)]
                 .sort_values("day_of_year"))
            ax.plot(d["day_of_year"], d["pct"], color=color, linewidth=1.6, alpha=0.85, label=str(year))

        ax.legend(loc="upper right", facecolor=CARD_BG, labelcolor=TEXT, framealpha=0.8, fontsize=9, ncol=3)

    plt.tight_layout()
    save_graph(fig, "02_all_years_overlay.png")
    return fig


def plot_elbow(k_range: list, inertias: list, silhouettes: list) -> plt.Figure:
    """Elbow (inertia) a Silhouette score pro vyber poctu clusteru."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4), facecolor=BG)
    fig.suptitle("Vyber poctu clusteru (K-Means)", color=TEXT, fontsize=14)

    for ax in (ax1, ax2):
        _style_ax(ax)
        ax.set_xlim(min(k_range) - 0.5, max(k_range) + 0.5)

    ax1.plot(k_range, inertias, "o-", color=CHART["accent"], linewidth=2)
    ax1.set_title("Elbow (inertia)", color=TEXT, fontsize=11)
    ax1.set_xlabel("Pocet clusteru k", color=MUTED)
    ax1.set_ylabel("Inertia", color=MUTED)

    ax2.plot(k_range, silhouettes, "o-", color=CHART["bar_above"], linewidth=2)
    ax2.set_title("Silhouette score", color=TEXT, fontsize=11)
    ax2.set_xlabel("Pocet clusteru k", color=MUTED)
    ax2.set_ylabel("Score (cim vyssi, tim lepe)", color=MUTED)
    best_k = k_range[int(np.argmax(silhouettes))]
    ax2.axvline(best_k, color=CHART["accent"], linestyle="--", linewidth=1.2, label=f"Optimalni k={best_k}")
    ax2.legend(facecolor=CARD_BG, labelcolor=TEXT, fontsize=9)

    plt.tight_layout()
    save_graph(fig, "03_elbow_silhouette.png")
    return fig


def plot_regime_heatmap(regime_df: pd.DataFrame) -> plt.Figure:
    """Heatmapa rok x den obarvena podle trzniho rezimu (K-Means)."""
    years = sorted(regime_df["year"].unique())
    n_reg = regime_df["regime"].nunique()
    matrix = np.full((len(years), 365), np.nan)

    for _, row in regime_df.iterrows():
        yi = years.index(row["year"])
        di = int(row["day_of_year"]) - 1
        if 0 <= di < 365:
            matrix[yi, di] = row["regime"]

    fig, ax = plt.subplots(
        figsize=(18, max(3, len(years) * 0.9 + 1.5)), facecolor=BG,
    )
    cmap = plt.cm.get_cmap("RdYlGn", n_reg)
    im = ax.imshow(
        matrix, aspect="auto", cmap=cmap, interpolation="nearest",
        extent=[1, 365, len(years) - 0.5, -0.5],
        vmin=-0.5, vmax=n_reg - 0.5,
    )

    ax.set_yticks(range(len(years)))
    ax.set_yticklabels(years, color=MUTED, fontsize=10)
    ax.set_xticks(MONTH_STARTS)
    ax.set_xticklabels(MONTHS_CZ, color=MUTED, fontsize=9)
    ax.set_facecolor(BG)
    ax.tick_params(colors=MUTED)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
    ax.set_title("Tržní režimy (rok x den, K-Means)", color=TEXT, fontsize=13)

    lbl_map = regime_df.drop_duplicates("regime").set_index("regime")["regime_label"]
    patches = [
        mpatches.Patch(color=cmap(r / max(n_reg - 1, 1)), label=lbl_map[r])
        for r in sorted(lbl_map.index)
    ]
    ax.legend(handles=patches, loc="lower right", facecolor=CARD_BG, labelcolor=TEXT, fontsize=8, framealpha=0.9)

    cb = plt.colorbar(im, ax=ax, pad=0.01)
    cb.ax.tick_params(colors=MUTED)
    cb.set_label("Režim", color=MUTED)

    plt.tight_layout()
    save_graph(fig, "04_regime_heatmap.png")
    return fig


def plot_regime_calendar(regime_df: pd.DataFrame) -> plt.Figure:
    """Podil trzniho rezimu na kazdem dni roku (agregace pres vsechna leta)."""
    agg = (
        regime_df
        .groupby(["day_of_year", "regime_label"])
        .size()
        .reset_index(name="count")
    )
    total = agg.groupby("day_of_year")["count"].sum()
    agg["share"] = agg.apply(lambda r: r["count"] / total[r["day_of_year"]], axis=1)

    sorted_labels = sorted(regime_df["regime_label"].unique())
    n_reg = len(sorted_labels)
    cmap = plt.cm.get_cmap("RdYlGn", n_reg)
    colors = {lbl: cmap(i / max(n_reg - 1, 1)) for i, lbl in enumerate(sorted_labels)}

    fig, ax = plt.subplots(figsize=(16, 5), facecolor=BG)
    _style_ax(ax, xlabel=True)
    ax.set_title("Zastoupení tržního režimu v průběhu roku", color=TEXT, fontsize=13)
    ax.set_ylabel("Podil dni", color=MUTED)
    ax.set_ylim(0, 1)

    for lbl in sorted_labels:
        d = agg[agg["regime_label"] == lbl].sort_values("day_of_year")
        ax.fill_between(d["day_of_year"], 0, d["share"], alpha=0.55, color=colors[lbl], label=lbl)

    ax.legend(loc="upper right", facecolor=CARD_BG, labelcolor=TEXT, framealpha=0.85, fontsize=9)
    plt.tight_layout()
    save_graph(fig, "05_regime_calendar.png")
    return fig


def plot_year_correlation(corr_dict: dict) -> plt.Figure:
    """Korelacni matice sezonniho vzoru rok vs. rok pro kazdy coin."""
    fig, axes = plt.subplots(1, len(COINS), figsize=(3.8 * len(COINS), 4.5), facecolor=BG)
    fig.suptitle("Korelace sezonn. vzoru mezi roky (Pearson)", color=TEXT, fontsize=14)

    for ax, coin in zip(axes, COINS):
        corr = corr_dict[coin]
        mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
        sns.heatmap(
            corr, ax=ax, annot=True, fmt=".2f",
            cmap="RdYlGn", vmin=-1, vmax=1,
            mask=mask, cbar=(coin == COINS[-1]),
            annot_kws={"size": 8, "color": TEXT},
            linewidths=0.5, linecolor=BORDER,
        )
        ax.set_title(coin, color=COIN_COLORS[coin], fontsize=12, pad=4)
        ax.set_facecolor(BG)
        ax.tick_params(colors=MUTED, labelsize=8)

    plt.tight_layout()
    save_graph(fig, "06_year_correlation.png")
    return fig


def plot_monthly_recommendations(scores: pd.DataFrame) -> plt.Figure:
    """
    Sloupovy graf mesicnich vynos s hvezdickovym hodnocenim.
    Barva sloupce je odvozena z dat (cervena = zaporny vynos, zelena = kladny).
    """
    def _bar_color(v: float) -> str:
        for threshold, color in THRESHOLDS:
            if v < threshold:
                return color
        return CHART["bar_very_above"]

    x = scores["month"].values
    y = scores["mean_return"].values
    yerr = scores["std_return"].values
    colors = [_bar_color(v) for v in y]

    fig, ax = plt.subplots(figsize=(14, 6), facecolor=BG)
    bars = ax.bar(x, y, color=colors, width=0.7, alpha=0.85, zorder=3)
    ax.errorbar(x, y, yerr=yerr, fmt="none", color=MUTED, capsize=5, linewidth=1.3, alpha=0.55, zorder=4)

    for bar, (_, row) in zip(bars, scores.iterrows()):
        h = bar.get_height()
        ypos = h + (1.5 if h >= 0 else -4)
        ax.text(bar.get_x() + bar.get_width() / 2, ypos,
                f"{int(row['score_1_5'])}/5",
                ha="center", va="bottom", fontsize=9, color=TEXT, zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels(MONTHS_FULL_CZ, rotation=30, ha="right", color=MUTED, fontsize=9)
    ax.set_ylabel("Průměrný mesíční výnos (% bodu)", color=MUTED)
    ax.set_title("Měsíční doporučeni", color=TEXT, fontsize=13)
    ax.set_facecolor(BG)
    ax.tick_params(colors=MUTED)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
    ax.grid(True, color=BORDER, alpha=0.4, axis="y", zorder=0)
    ax.axhline(0, color=ZEROLINE, linestyle="--", linewidth=0.9, zorder=2)
    ax.legend(handles=legend_items, loc="upper right", facecolor=CARD_BG, labelcolor=TEXT, fontsize=8, framealpha=0.9)

    plt.tight_layout()
    save_graph(fig, "08_monthly_recommendations.png")
    return fig
