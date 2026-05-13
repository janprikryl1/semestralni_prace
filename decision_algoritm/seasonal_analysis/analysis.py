import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from statsmodels.tsa.seasonal import STL
from config import COINS, REGIME_NAMES


def compute_average_pattern(norm_df: pd.DataFrame) -> pd.DataFrame:
    """
    Agreguje % zmenu po dnech roku pres vsechna dostupna leta.
    Vraci: mean_pct a std_pct pro kazdy den (1-365) a coin.
    """
    return (
        norm_df
        .groupby(["coin", "day_of_year"])["pct"]
        .agg(mean_pct="mean", std_pct="std", n_years="count")
        .reset_index()
        .rename(columns={"day_of_year": "day"})
    )


def detect_regimes(norm_df: pd.DataFrame, n_clusters: int = 2) -> pd.DataFrame:
    """
    K-Means clustering na dennich vynosovych vektorech.
    Kazdy den = vektor [pct_BTC, pct_ETH, pct_SOL, pct_XRP, pct_ADA].
    Clustery jsou serazeny od nejvetsiho medveda (0) po nejvetsiho byka (N-1).
    """
    pivot = (
        norm_df
        .pivot_table(index=["year", "day_of_year"], columns="coin", values="pct", aggfunc="mean")
        .reset_index()
        .dropna(subset=COINS)
    )

    X = StandardScaler().fit_transform(pivot[COINS].values)
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=30, max_iter=500)
    pivot = pivot.copy()
    pivot["cluster"] = km.fit_predict(X)

    sil = silhouette_score(X, pivot["cluster"])
    print(f"Silhouette score: {sil:.3f}") #cim blize 1, tim lepe oddelene clustery

    cluster_mean = pivot.groupby("cluster")[COINS].mean().mean(axis=1).sort_values()
    rank_map = {old: new for new, old in enumerate(cluster_mean.index)}
    pivot["regime"] = pivot["cluster"].map(rank_map)
    pivot["regime_label"] = pivot["regime"].map(REGIME_NAMES)

    print("Tržní režimy:")
    for r in sorted(pivot["regime"].unique()):
        sub = pivot[pivot["regime"] == r]
        avg = sub[COINS].mean().mean()
        print(f"  [{r}] {REGIME_NAMES.get(r, r):<18} -- {len(sub):>4} dní | průměr {avg:+6.1f}%")

    return pivot


def year_correlation(norm_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Pearsonova korelacni matice rocnich vzoru pro kazdy coin.
    Odpovedá na otazku: jak moc je rok 2022 podobny roku 2024?
    """
    result = {}
    for coin in COINS:
        pivot = (
            norm_df[norm_df["coin"] == coin]
            .pivot_table(index="day_of_year", columns="year", values="pct")
            .dropna(thresh=2)
        )
        result[coin] = pivot.corr()
    return result


def compute_monthly_scores(norm_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pro kazdy mesic spocte prumerny vysledek obchodu (konec - zacatek mesice)
    agregovaný pres vsechny coiny a roky.

    Sloupce vystupu:
      month        -- cislo mesice (1-12)
      mean_return  -- prumerny mesicni vysledek v procentnich bodech
      std_return   -- smerodatna odchylka
      score_raw    -- linearni normalizace na interval 0-1
      score_1_5    -- zaokrouhlene skore 1-5 (1 = vyhni se, 5 = silne kupuj)
    """
    records = []
    for (coin, year, month), grp in norm_df.groupby(["coin", "year", "month"]):
        grp = grp.sort_values("date")
        if len(grp) < 5:
            continue
        records.append({
            "coin": coin,
            "year": year,
            "month": month,
            "monthly_return": grp["pct"].iloc[-1] - grp["pct"].iloc[0],
        })

    agg = (
        pd.DataFrame(records)
        .groupby("month")["monthly_return"]
        .agg(mean_return="mean", std_return="std")
        .reset_index()
    )

    lo, hi = agg["mean_return"].min(), agg["mean_return"].max()
    agg["score_raw"] = (agg["mean_return"] - lo) / (hi - lo)
    agg["score_1_5"] = (agg["score_raw"] * 4 + 1).round().clip(1, 5).astype(int)

    return agg.sort_values("month").reset_index(drop=True)
