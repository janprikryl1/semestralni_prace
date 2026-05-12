import argparse
import matplotlib.pyplot as plt
import numpy as np
from config import TEXT, MUTED, CHART_DESCRIPTIONS
from db import load_price_data, normalize_by_year
from reports import print_correlation_summary, print_monthly_recommendations
from analysis import (
    compute_average_pattern,
    detect_regimes,
    elbow_and_silhouette,
    year_correlation,
    compute_monthly_scores,
)
from plots import (
    plot_avg_seasonal,
    plot_all_years_overlay,
    plot_elbow,
    plot_regime_heatmap,
    plot_regime_calendar,
    plot_year_correlation,
    plot_monthly_recommendations,
)


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
        for n, desc in CHART_DESCRIPTIONS.items():
            print(f"  {n}  {desc}")
        print()
        raise SystemExit(0)

    if not args.charts:
        return list(CHART_DESCRIPTIONS.keys())

    invalid = [n for n in args.charts if n not in CHART_DESCRIPTIONS]
    if invalid:
        parser.error(f"Neplatna cisla grafu: {invalid}. Povoleno 1-8.")

    return sorted(set(args.charts))


def main():
    selected = _parse_args()
    plt.rcParams.update({"text.color": TEXT, "axes.labelcolor": MUTED})

    raw_df = load_price_data()
    norm_df = normalize_by_year(raw_df)

    avg_df = compute_average_pattern(norm_df)
    ks, inertias, silhouettes = elbow_and_silhouette(norm_df, range(2, 11))
    best_k = ks[int(np.argmax(silhouettes))]
    regime_df = detect_regimes(norm_df, n_clusters=best_k)
    corr_dict = year_correlation(norm_df)
    scores = compute_monthly_scores(norm_df)

    for n in selected:
        if   n == 1: plot_avg_seasonal(avg_df)
        elif n == 2: plot_all_years_overlay(norm_df)
        elif n == 3: plot_elbow(ks, inertias, silhouettes)
        elif n == 4: plot_regime_heatmap(regime_df)
        elif n == 5: plot_regime_calendar(regime_df)
        elif n == 6: plot_year_correlation(corr_dict); print_correlation_summary(corr_dict)
        elif n == 7: plot_monthly_recommendations(scores); print_monthly_recommendations(scores)
    plt.show()


if __name__ == "__main__":
    main()
