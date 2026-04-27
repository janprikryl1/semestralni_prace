"""
Backtesting for strategy SMA-14 + Fear & Greed.
Tests coins from 3 categories to choose the best for live trading.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from binance.client import Client
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

COINS = {
    "TOP (BTC, ETH, XRP, BNB)": ["BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT"],
    "MID (SOL, TRX, LTC, BCH)": ["SOLUSDT", "TRXUSDT", "LTCUSDT", "BCHUSDT"],
    "WILD (DOGE, AVAX, SHIB, PEPE)": ["DOGEUSDT", "AVAXUSDT", "SHIBUSDT", "PEPEUSDT"],
}

# ---------------------------------------------------------------------------
# Parameters of strategy
# ---------------------------------------------------------------------------
SMA_PERIOD = 14
HOURS_BACK = 100

FEAR_BUY_THRESHOLD = 60
FEAR_SELL_THRESHOLD = 55

BUY_STRONG_FEAR = 20     # buy_strong_fear_threshold
BUY_NORMAL_FEAR = 56     # buy_normal_fear_threshold
SELL_NORMAL_FEAR = 60    # sell_normal_fear_threshold
SELL_STRONG_FEAR = 80    # sell_strong_fear_threshold

BUY_STRONG = 0.4
BUY_NORMAL = 0.26
SELL_STRONG = 1.0
SELL_NORMAL = 0.8

MIN_QUOTE_BALANCE = 6.0

# ---------------------------------------------------------------------------
# Parameters of backtest
# ---------------------------------------------------------------------------
INITIAL_CAPITAL = 1000.0  # USDT
LOOKBACK_DAYS = 365


def fetch_fear_greed_historical(days: int) -> dict:
    api_key = os.getenv("COINMARKETCAP_API_KEY") or os.getenv("COINMARKETCUP")
    if not api_key:
        raise RuntimeError("Missing COINMARKETCAP_API_KEY in .env")

    url = f"https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical?limit={days}"
    headers = {"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if str(body["status"]["error_code"]) != "0":
        raise RuntimeError(f"CMC API error: {body['status'].get('error_message')}")

    result = {}
    for entry in body["data"]:
        # CMC vrací timestamp jako Unix integer (např. 1777075200)
        date = datetime.utcfromtimestamp(int(entry["timestamp"])).date()
        result[date] = int(entry["value"])
    return result


def fetch_klines(client: Client, symbol: str, days: int) -> pd.DataFrame:
    klines = client.get_historical_klines(
        symbol, Client.KLINE_INTERVAL_1HOUR, f"{days} days ago UTC"
    )
    df = pd.DataFrame(klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close"] = df["close"].astype(float)
    df.set_index("open_time", inplace=True)
    return df[["close"]]


def interpolate_size(value, start, end, start_size, end_size):
    """Linear interpolation"""
    if start == end:
        return end_size
    ratio = (value - start) / (end - start)
    ratio = max(0.0, min(1.0, ratio))
    return start_size + ratio * (end_size - start_size)


def get_buy_fraction(fear: int, quote_balance: float) -> float:
    """Amount of order in USDT """
    if fear < BUY_STRONG_FEAR:
        return quote_balance * BUY_STRONG
    if fear < BUY_NORMAL_FEAR:
        return quote_balance * BUY_NORMAL
    if fear >= FEAR_BUY_THRESHOLD:
        return 0.0
    size_fraction = interpolate_size(fear, BUY_NORMAL_FEAR, FEAR_BUY_THRESHOLD, BUY_NORMAL, 0.0)
    return quote_balance * size_fraction


def get_sell_fraction(fear: int, base_balance: float) -> float:
    """Returns amount to sell"""
    if fear > SELL_STRONG_FEAR:
        return base_balance * SELL_STRONG
    if fear > SELL_NORMAL_FEAR:
        return base_balance * SELL_NORMAL
    if fear <= FEAR_SELL_THRESHOLD:
        return 0.0
    size_fraction = interpolate_size(fear, FEAR_SELL_THRESHOLD, SELL_NORMAL_FEAR, 0.0, SELL_NORMAL)
    return base_balance * size_fraction


def backtest_coin(df: pd.DataFrame, fear_greed: dict, symbol: str) -> dict:
    """Backtesting SMA strategy for one coin"""
    closes = df["close"].values
    timestamps = df.index

    usdt = INITIAL_CAPITAL
    coin = 0.0
    trades = []
    portfolio_values = []

    for i in range(SMA_PERIOD, len(closes)):
        price = closes[i]
        ts = timestamps[i]
        fear = fear_greed.get(ts.date())

        if fear is None:
            portfolio_values.append(usdt + coin * price)
            continue

        # SMA through last HOURS_BACK candles (max SMA_PERIOD)
        window = closes[max(0, i - HOURS_BACK + 1): i + 1]
        sma = float(np.mean(window[-SMA_PERIOD:]))
        trend_up = price > sma

        signal = "HOLD"
        if fear < FEAR_BUY_THRESHOLD and trend_up:
            signal = "BUY"
        elif fear > FEAR_SELL_THRESHOLD and not trend_up:
            signal = "SELL"

        if signal == "BUY" and usdt > MIN_QUOTE_BALANCE:
            amount_usdt = get_buy_fraction(fear, usdt)
            if amount_usdt > MIN_QUOTE_BALANCE:
                coin_bought = amount_usdt / price
                usdt -= amount_usdt
                coin += coin_bought
                trades.append({"type": "BUY", "price": price, "usdt": amount_usdt, "ts": str(ts), "fear": fear})

        elif signal == "SELL" and coin > 0:
            coin_to_sell = get_sell_fraction(fear, coin)
            if coin_to_sell > 0:
                received = coin_to_sell * price
                coin -= coin_to_sell
                usdt += received
                trades.append({"type": "SELL", "price": price, "usdt": received, "ts": str(ts), "fear": fear})

        portfolio_values.append(usdt + coin * price)

    final_value = usdt + coin * closes[-1]
    buy_hold_value = INITIAL_CAPITAL / closes[SMA_PERIOD] * closes[-1]

    pv = np.array(portfolio_values, dtype=float)
    hourly_returns = np.diff(pv) / np.where(pv[:-1] != 0, pv[:-1], np.nan)
    hourly_returns = hourly_returns[np.isfinite(hourly_returns)]
    sharpe = (
        float(np.mean(hourly_returns) / np.std(hourly_returns) * np.sqrt(8760))
        if np.std(hourly_returns) > 0 else 0.0
    )

    peak = pv[0]
    max_dd = 0.0
    for v in pv:
        peak = max(peak, v)
        dd = (peak - v) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    buys = [t for t in trades if t["type"] == "BUY"]
    sells = [t for t in trades if t["type"] == "SELL"]

    return {
        "symbol": symbol,
        "final_value": round(final_value, 2),
        "return_pct": round((final_value / INITIAL_CAPITAL - 1) * 100, 2),
        "buy_hold_return_pct": round((buy_hold_value / INITIAL_CAPITAL - 1) * 100, 2),
        "alpha_pct": round((final_value / INITIAL_CAPITAL - 1) * 100 - (buy_hold_value / INITIAL_CAPITAL - 1) * 100, 2),
        "sharpe": round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "num_trades": len(trades),
        "num_buys": len(buys),
        "num_sells": len(sells),
        "trades": trades,
    }


def print_results(results: dict):
    width = 100
    print("\n" + "=" * width)
    print(f"  BACKTEST RESULTS — SMA-{SMA_PERIOD} + Fear & Greed")
    print(f"  Season: last {LOOKBACK_DAYS} days  |  Initial: ${INITIAL_CAPITAL:.0f} USDT")
    print("=" * width)

    header = f"{'Coin':<12} {'Profit%':>9} {'Buy&Hold%':>11} {'Alpha%':>8} {'Sharpe':>8} {'MaxDD%':>8} {'Trades':>7} {'Buys':>6} {'Sells':>6}"
    sep = "-" * width

    for category, items in results.items():
        print(f"\n--- {category} ---")
        print(header)
        print(sep)
        for r in sorted(items, key=lambda x: x["return_pct"], reverse=True):
            alpha_mark = "+" if r["alpha_pct"] >= 0 else ""
            print(
                f"{r['symbol']:<12} "
                f"{r['return_pct']:>8.2f}% "
                f"{r['buy_hold_return_pct']:>10.2f}% "
                f"{alpha_mark}{r['alpha_pct']:>7.2f}% "
                f"{r['sharpe']:>8.3f} "
                f"{r['max_drawdown_pct']:>7.2f}% "
                f"{r['num_trades']:>7} "
                f"{r['num_buys']:>6} "
                f"{r['num_sells']:>6}"
            )


def main():
    api_key = os.getenv("API_KEY", "")
    api_secret = os.getenv("API_SECRET", "")
    client = Client(api_key, api_secret)
    fear_greed = fetch_fear_greed_historical(LOOKBACK_DAYS + 30)

    results = {}
    for category, symbols in COINS.items():
        results[category] = []
        for symbol in symbols:
            print(f"Backtest {symbol}...", end=" ", flush=True)
            try:
                df = fetch_klines(client, symbol, LOOKBACK_DAYS)
                result = backtest_coin(df, fear_greed, symbol)
                results[category].append(result)
                print(
                    f"profit={result['return_pct']:+.2f}%  "
                    f"alpha={result['alpha_pct']:+.2f}%  "
                    f"sharpe={result['sharpe']:.3f}  "
                    f"maxDD={result['max_drawdown_pct']:.2f}%"
                )
                time.sleep(0.3)
            except Exception as exc:
                print(f"Error: {exc}")
                results[category].append({"symbol": symbol, "error": str(exc)})

    print_results(results)

    out_path = Path(__file__).parent / "sma_backtest_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()

"""
Results (16. 4. 2026):
 Stahuji historická data Fear & Greed (395 dní)...
C:\Users\jan.prikryl\Desktop\Semestralni projekt\decision_algoritm\backtesting\sma_backtest.py:76: DeprecationWarning: datetime.datetime.utcfromtimestamp() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.fromtimestamp(timestamp, datetime.UTC).
  date = datetime.utcfromtimestamp(int(entry["timestamp"])).date()
  Staženo 395 denních hodnot.
Backtest BTCUSDT... výnos=-20.09%  alpha=-3.00%  sharpe=-0.402  maxDD=48.56%
Backtest ETHUSDT... výnos=-2.99%  alpha=-32.00%  sharpe=0.235  maxDD=61.53%
Backtest XRPUSDT... výnos=-26.75%  alpha=+7.51%  sharpe=-0.252  maxDD=61.04%
Backtest BNBUSDT... výnos=-24.65%  alpha=-29.52%  sharpe=-0.409  maxDD=57.52%
Backtest SOLUSDT... výnos=-31.34%  alpha=+10.10%  sharpe=-0.276  maxDD=68.09%
Backtest TRXUSDT... výnos=+14.73%  alpha=-13.78%  sharpe=0.690  maxDD=24.62%
Backtest LTCUSDT... výnos=-33.11%  alpha=+1.42%  sharpe=-0.353  maxDD=63.23%
Backtest BCHUSDT... výnos=+28.28%  alpha=+0.34%  sharpe=0.719  maxDD=36.25%
Backtest DOGEUSDT... výnos=-36.95%  alpha=+7.93%  sharpe=-0.344  maxDD=68.95%
Backtest AVAXUSDT... výnos=-43.18%  alpha=+14.39%  sharpe=-0.493  maxDD=74.22%
Backtest SHIBUSDT... výnos=-33.96%  alpha=+21.13%  sharpe=-0.372  maxDD=61.96%
Backtest PEPEUSDT... výnos=-26.75%  alpha=+30.30%  sharpe=0.056  maxDD=72.52%

====================================================================================================
  BACKTEST VÝSLEDKY — SMA-14 + Fear & Greed
  Období: posledních 365 dní  |  Počáteční kapitál: $1000 USDT
====================================================================================================

--- TOP (BTC, ETH, XRP, BNB) ---
Mince           Výnos%   Buy&Hold%   Alpha%   Sharpe   MaxDD%   Obch.   Nák.  Prod.
----------------------------------------------------------------------------------------------------
ETHUSDT         -2.99%      29.00%  -32.00%    0.235   61.53%    1214    373    841
BTCUSDT        -20.09%     -17.09%   -3.00%   -0.402   48.56%    1292    373    919
BNBUSDT        -24.65%       4.87%  -29.52%   -0.409   57.52%    1190    374    816
XRPUSDT        -26.75%     -34.26% +   7.51%   -0.252   61.04%    1285    352    933

--- MID (SOL, TRX, LTC, BCH) ---
Mince           Výnos%   Buy&Hold%   Alpha%   Sharpe   MaxDD%   Obch.   Nák.  Prod.
----------------------------------------------------------------------------------------------------
BCHUSDT         28.28%      27.94% +   0.34%    0.719   36.25%    1283    354    929
TRXUSDT         14.73%      28.51%  -13.78%    0.690   24.62%    1148    343    805
SOLUSDT        -31.34%     -41.44% +  10.10%   -0.276   68.09%    1276    362    914
LTCUSDT        -33.11%     -34.52% +   1.42%   -0.353   63.23%    1280    393    887

--- WILD (DOGE, AVAX, SHIB, PEPE) ---
Mince           Výnos%   Buy&Hold%   Alpha%   Sharpe   MaxDD%   Obch.   Nák.  Prod.
----------------------------------------------------------------------------------------------------
PEPEUSDT       -26.75%     -57.05% +  30.30%    0.056   72.52%    1325    365    960
SHIBUSDT       -33.96%     -55.09% +  21.13%   -0.372   61.96%    1310    368    942
DOGEUSDT       -36.95%     -44.88% +   7.93%   -0.344   68.95%    1324    373    951
AVAXUSDT       -43.18%     -57.58% +  14.39%   -0.493   74.22%    1283    370    913

Výsledky uloženy do: C:\Users\jan.prikryl\Desktop\Semestralni projekt\decision_algoritm\backtesting\sma_backtest_results.json
"""