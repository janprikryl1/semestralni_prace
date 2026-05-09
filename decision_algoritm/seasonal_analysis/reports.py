import numpy as np
import pandas as pd
from config import COINS, MONTHS_FULL_CZ

ADVICES = {
    1: ("[1/5]", "Vyhnout se"),
    2: ("[2/5]", "Opatrnost"),
    3: ("[3/5]", "Neutralni"),
    4: ("[4/5]", "Vhodny cas"),
    5: ("[5/5]", "Silne koupit"),
}


def print_correlation_summary(corr_dict: dict[str, pd.DataFrame]) -> None:
    """Prumerna mezirocni korelace pro kazdy coin."""
    w = 58
    print("\n" + "=" * w)
    print("  MEZIROCNI KORELACE (prumer pres vsechny pary let)")
    print("=" * w)
    for coin in COINS:
        corr = corr_dict[coin]
        vals = corr.values[np.tril_indices_from(corr.values, k=-1)]
        if len(vals) == 0:
            continue
        print(f"  {coin:<5}  prumer r = {np.nanmean(vals):+.3f}"
              f"  | min = {np.nanmin(vals):+.3f}"
              f"  | max = {np.nanmax(vals):+.3f}")
    print("=" * w)


def print_monthly_recommendations(scores: pd.DataFrame) -> None:
    def stars(n: int) -> str:
        return "*" * n + "." * (5 - n)

    w = 65
    print("\n" + "=" * w)
    print("  DOPORUCENI — Kdy kupovat / prodavat (z historickych dat)")
    print("=" * w)
    print(f"  {'Mesic':<12} {'Prumer':>10} Doporuceni")
    print("-" * w)
    for _, row in scores.iterrows():
        m   = int(row["month"])
        s   = int(row["score_1_5"])
        lbl, txt = ADVICES[s]
        print(f"  {MONTHS_FULL_CZ[m - 1]:<12} {row['mean_return']:>+9.1f}% {lbl} {txt}")
    print("=" * w)

    best  = scores.loc[scores["mean_return"].idxmax()]
    worst = scores.loc[scores["mean_return"].idxmin()]
    print(f"\n  Nejlepsi mesic pro nakup : "
          f"{MONTHS_FULL_CZ[int(best['month']) - 1]} "
          f"(prumer +{best['mean_return']:.1f}%)")
    print(f"  Nejhorsi mesic (vyhni se): "
          f"{MONTHS_FULL_CZ[int(worst['month']) - 1]} "
          f"(prumer {worst['mean_return']:+.1f}%)")
    print("=" * w)
