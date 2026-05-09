import os
import mysql.connector
import pandas as pd
from dotenv import load_dotenv

from config import COINS

load_dotenv()


def _connect():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )


def load_price_data() -> pd.DataFrame:
    placeholders = ", ".join(["%s"] * len(COINS))
    query = f"""
        SELECT DATE(t.datetime) AS date,
               t.close_eur     AS price,
               m.asset_label   AS coin
        FROM   binance_index_asset_buy_daily t
        JOIN   binance_index_asset_mapping   m ON t.asset_id = m.id
        WHERE  m.asset_label IN ({placeholders})
        ORDER  BY t.datetime ASC
    """
    with _connect() as conn:
        df = pd.read_sql(query, conn, params=COINS, parse_dates=["date"])

    print(f"[Debug]: {len(df):,} records | {df['coin'].nunique()} coin | "
          f"{df['date'].min().date()} -> {df['date'].max().date()}")
    return df


def normalize_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each pair (coin, year) calculates the percentage change
    in price relative to the first available price in that year.
    """
    df = df.copy()
    df["year"]        = df["date"].dt.year
    df["day_of_year"] = df["date"].dt.dayofyear
    df["month"]       = df["date"].dt.month

    parts = []
    for (coin, year), grp in df.groupby(["coin", "year"]):
        grp = grp.sort_values("date").copy()
        if len(grp) < 15:
            continue
        base = grp["price"].iloc[0]
        if base <= 0:
            continue
        grp["pct"] = (grp["price"] - base) / base * 100
        parts.append(grp)

    return pd.concat(parts, ignore_index=True)
