"""
Crypto Seasonality Analysis
----------------------------
Nacte denni ceny z databaze a spusti analyzy sezonniho chovani trhu.

Dostupne grafy:
  1  Prumerny sezonni vzor s pasem +/- 1 std
  2  Overlay vsech let (kazda cara = jeden rok)
  3  Elbow + Silhouette pro vyber poctu clusteru
  4  Heatmapa trzniho rezimu (rok x den, K-Means)
  5  Zastoupeni rezimu v prubehu roku
  6  Korelace sezonniho vzoru mezi roky (Pearson)
  7  STL dekompozice (trend + sezona + residuum) pro BTC
  8  Mesicni doporuceni s hvezdickovym hodnocenim

Pouziti:
  python main.py          # vsechny grafy
  python main.py 1 3 8    # vybrane grafy
  python main.py --list   # vypis dostupnych grafu
"""

import argparse
import warnings

import matplotlib.pyplot as plt
import numpy as np

warnings.filterwarnings("ignore")

from config import TEXT, MUTED
from db import load_price_data, normalize_by_year
from analysis import (
    compute_average_pattern,
    detect_regimes,
    elbow_and_silhouette,
    year_correlation,
    stl_decompose,
    compute_monthly_scores,
)
from plots import (
    plot_01_avg_seasonal,
    plot_02_all_years_overlay,
    plot_03_elbow,
    plot_04_regime_heatmap,
    plot_05_regime_calendar,
    plot_06_year_correlation,
    plot_07_stl,
    plot_08_monthly_recommendations,
)
from reports import print_correlation_summary, print_monthly_recommendations

_CHART_DESCRIPTIONS = {
    1: "Prumerny sezonni vzor s pasem +/- 1 std",
    2: "Overlay vsech let (kazda cara = jeden rok)",
    3: "Elbow + Silhouette pro vyber poctu clusteru",
    4: "Heatmapa trzniho rezimu (rok x den, K-Means)",
    5: "Zastoupeni rezimu v prubehu roku",
    6: "Korelace sezonniho vzoru mezi roky (Pearson)",
    7: "STL dekompozice (trend + sezona + residuum) pro BTC",
    8: "Mesicni doporuceni s hvezdickovym hodnocenim",
}


def _parse_args() -> list[int]:
    parser = argparse.ArgumentParser(
        description="Crypto Seasonality Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Priklad: python main.py 1 3 8",
    )
    parser.add_argument(
        "charts",
        nargs="*",
        type=int,
        metavar="N",
        help="Cisla grafu ke spusteni (1-8). Bez argumentu = vsechny.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Vypise dostupne grafy a skonci.",
    )
    args = parser.parse_args()

    if args.list:
        print("\nDostupne grafy:")
        for n, desc in _CHART_DESCRIPTIONS.items():
            print(f"  {n}  {desc}")
        print()
        raise SystemExit(0)

    if not args.charts:
        return list(_CHART_DESCRIPTIONS.keys())

    invalid = [n for n in args.charts if n not in _CHART_DESCRIPTIONS]
    if invalid:
        parser.error(f"Neplatna cisla grafu: {invalid}. Povoleno 1-8.")

    return sorted(set(args.charts))


def main():
    selected = _parse_args()

    plt.rcParams.update({"text.color": TEXT, "axes.labelcolor": MUTED})

    raw_df  = load_price_data()
    norm_df = normalize_by_year(raw_df)
    print(f"  Normalizovano: {len(norm_df):,} radku | "
          f"{norm_df['year'].nunique()} let | {norm_df['coin'].nunique()} coinu")

    # -- lazily computed shared artefacts --------------------------------
    avg_df     = None
    regime_df  = None
    corr_dict  = None
    scores     = None
    k_range    = range(2, 11)
    ks = inertias = silhouettes = best_k = None

    def _ensure_avg():
        nonlocal avg_df
        if avg_df is None:
            avg_df = compute_average_pattern(norm_df)

    def _ensure_elbow():
        nonlocal ks, inertias, silhouettes, best_k
        if ks is None:
            ks, inertias, silhouettes = elbow_and_silhouette(norm_df, k_range)
            best_k = ks[int(np.argmax(silhouettes))]
            print(f"  Optimalni k = {best_k} (silhouette = {max(silhouettes):.3f})")

    def _ensure_regimes():
        nonlocal regime_df
        if regime_df is None:
            _ensure_elbow()
            regime_df = detect_regimes(norm_df, n_clusters=best_k)

    def _ensure_corr():
        nonlocal corr_dict
        if corr_dict is None:
            corr_dict = year_correlation(norm_df)

    def _ensure_scores():
        nonlocal scores
        if scores is None:
            scores = compute_monthly_scores(norm_df)

    for n in selected:
        print(f"\n[Graph {n}] {_CHART_DESCRIPTIONS[n]}")
        if n == 1:
            _ensure_avg()
            plot_01_avg_seasonal(avg_df)
        elif n == 2:
            plot_02_all_years_overlay(norm_df)
        elif n == 3:
            _ensure_elbow()
            plot_03_elbow(ks, inertias, silhouettes)
        elif n == 4:
            _ensure_regimes()
            plot_04_regime_heatmap(regime_df)
        elif n == 5:
            _ensure_regimes()
            plot_05_regime_calendar(regime_df)
        elif n == 6:
            _ensure_corr()
            plot_06_year_correlation(corr_dict)
            print_correlation_summary(corr_dict)
        elif n == 7:
            stl_data = stl_decompose(norm_df, coin="BTC")
            plot_07_stl(stl_data, coin="BTC")
        elif n == 8:
            _ensure_scores()
            plot_08_monthly_recommendations(scores)
            print_monthly_recommendations(scores)

    plt.show()


if __name__ == "__main__":
    main()
