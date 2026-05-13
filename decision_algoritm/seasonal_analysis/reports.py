import numpy as np
import pandas as pd
from config import COINS, MONTHS_FULL_CZ, ADVICES


def print_correlation_summary(corr_dict: dict[str, pd.DataFrame]) -> None:
    w = 58
    print("\n" + "=" * w)
    print("MEZIROCNI KORELACE (prumer pres vsechny pary let)")
    print("=" * w)
    for coin in COINS:
        corr = corr_dict[coin]
        vals = corr.values[np.tril_indices_from(corr.values, k=-1)]
        if len(vals) == 0:
            continue
        print(f"{coin:<5}  prumer r = {np.nanmean(vals):+.3f}  | min = {np.nanmin(vals):+.3f}  | max = {np.nanmax(vals):+.3f}")
    print("=" * w)


def print_monthly_recommendations(scores: pd.DataFrame) -> None:
    w = 65
    print("\n" + "=" * w)
    print("DOPORUČENÍ — Kdy nakupovat")
    print("=" * w)
    print(f"{'Měsíc':<12} {'Průměr':>10} Doporučeni")
    print("-" * w)
    for _, row in scores.iterrows():
        m = int(row["month"])
        s = int(row["score_1_5"])
        lbl, txt = ADVICES[s]
        print(f"{MONTHS_FULL_CZ[m - 1]:<12} {row['mean_return']:>+9.1f}% {lbl} - {txt}")
    print("=" * w)
    best = scores.loc[scores["mean_return"].idxmax()]
    worst = scores.loc[scores["mean_return"].idxmin()]
    print(f"  Nejlepší měsíc pro nákup : {MONTHS_FULL_CZ[int(best['month']) - 1]} (průměr {best['mean_return']:.1f}%)")
    print(f"  Nejhorší měsíc pro nákup: {MONTHS_FULL_CZ[int(worst['month']) - 1]} (průměr {worst['mean_return']:+.1f}%)")
