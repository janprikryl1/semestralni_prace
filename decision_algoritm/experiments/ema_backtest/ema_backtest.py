#!/usr/bin/env python3
"""
Backtesting pro experimentální strategii EMA-21 + Fear & Greed.

Testuje mince ze tří kategorií, aby pomohl vybrat nejlepší kandidáty pro live trading.
Tether (USDT) je vynechán, protože jde o stablecoin.

Vyžaduje: ta-lib (stejná závislost jako experiments/ema_fear_greed_talib)

Spuštění: python ema_backtest.py
Výstup:   výsledky na konzoli + ema_backtest_results.json
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import talib
from binance.client import Client
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# ---------------------------------------------------------------------------
# Mince — Tether vynechán (stablecoin)
# ---------------------------------------------------------------------------
COINS = {
    "TOP (BTC, ETH, XRP, BNB)": ["BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT"],
    "MID (SOL, TRX, LTC, BCH)": ["SOLUSDT", "TRXUSDT", "LTCUSDT", "BCHUSDT"],
    "WILD (DOGE, AVAX, SHIB, PEPE)": ["DOGEUSDT", "AVAXUSDT", "SHIBUSDT", "PEPEUSDT"],
}

# ---------------------------------------------------------------------------
# Parametry strategie — přesně z experiments/ema_fear_greed_talib/config.json
# ---------------------------------------------------------------------------
EMA_PERIOD = 21
HOURS_BACK = 200  # warm-up pro EMA konvergenci

FEAR_BUY_THRESHOLD = 45
FEAR_SELL_THRESHOLD = 60

BUY_STRONG = 0.3
BUY_NORMAL = 0.15
SELL_STRONG = 1.0
SELL_NORMAL = 0.5

MIN_QUOTE_BALANCE = 0.25

# ---------------------------------------------------------------------------
# Parametry backtestu
# ---------------------------------------------------------------------------
INITIAL_CAPITAL = 1000.0  # USDT
LOOKBACK_DAYS = 365


def fetch_fear_greed_historical(days: int) -> dict:
    """Stáhne historický Fear & Greed index z CoinMarketCap (stejný endpoint jako produkce)."""
    api_key = os.getenv("COINMARKETCAP_API_KEY") or os.getenv("COINMARKETCUP")
    if not api_key:
        raise RuntimeError("Chybí COINMARKETCAP_API_KEY nebo COINMARKETCUP v .env")

    url = f"https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical?limit={days}"
    headers = {"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if str(body["status"]["error_code"]) != "0":
        raise RuntimeError(f"CMC API chyba: {body['status'].get('error_message')}")

    result = {}
    for entry in body["data"]:
        # CMC vrací timestamp jako Unix integer (např. 1777075200)
        date = datetime.utcfromtimestamp(int(entry["timestamp"])).date()
        result[date] = int(entry["value"])
    return result


def fetch_klines(client: Client, symbol: str, days: int, warmup_hours: int) -> pd.DataFrame:
    """Stáhne 1h OHLCV data z Binance — přidá warmup_hours navíc pro EMA."""
    extra_days = (warmup_hours // 24) + 2
    total_days = days + extra_days
    klines = client.get_historical_klines(
        symbol, Client.KLINE_INTERVAL_1HOUR, f"{total_days} days ago UTC"
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


def get_buy_amount(fear: int, usdt: float) -> float:
    """Vrátí výši nákupu v USDT.

    EMA config nemá tiered fear prahy pro nákup — používáme flat BUY_NORMAL,
    s výjimkou extrémního strachu (< 20), kde se použije BUY_STRONG.
    """
    if fear < 20:
        return usdt * BUY_STRONG
    return usdt * BUY_NORMAL


def get_sell_amount(fear: int, coin: float) -> float:
    """Vrátí množství mince k prodeji."""
    if fear > 80:
        return coin * SELL_STRONG
    return coin * SELL_NORMAL


def backtest_coin(df: pd.DataFrame, fear_greed: dict, symbol: str) -> dict:
    """Provede backtesting EMA strategie pro jednu minci."""
    closes = df["close"].values
    timestamps = df.index

    # Spočítáme EMA přes celou řadu najednou (ta-lib potřebuje kompletní array)
    ema_series = talib.EMA(closes, timeperiod=EMA_PERIOD)

    usdt = INITIAL_CAPITAL
    coin = 0.0
    trades = []
    portfolio_values = []

    # Backtest začíná po warm-up periodě
    start_idx = HOURS_BACK

    for i in range(start_idx, len(closes)):
        price = closes[i]
        ema = ema_series[i]
        ts = timestamps[i]
        fear = fear_greed.get(ts.date())

        if fear is None or np.isnan(ema):
            portfolio_values.append(usdt + coin * price)
            continue

        # Signál — přesná logika z experiments/ema_fear_greed_talib/main.py
        signal = "HOLD"
        if price > ema and fear < FEAR_BUY_THRESHOLD:
            signal = "BUY"
        elif price < ema and fear > FEAR_SELL_THRESHOLD:
            signal = "SELL"

        if signal == "BUY" and usdt > MIN_QUOTE_BALANCE:
            amount_usdt = get_buy_amount(fear, usdt)
            if amount_usdt > MIN_QUOTE_BALANCE:
                coin_bought = amount_usdt / price
                usdt -= amount_usdt
                coin += coin_bought
                trades.append({"type": "BUY", "price": price, "usdt": amount_usdt, "ts": str(ts), "fear": fear})

        elif signal == "SELL" and coin > 0:
            coin_to_sell = get_sell_amount(fear, coin)
            if coin_to_sell > 0:
                received = coin_to_sell * price
                coin -= coin_to_sell
                usdt += received
                trades.append({"type": "SELL", "price": price, "usdt": received, "ts": str(ts), "fear": fear})

        portfolio_values.append(usdt + coin * price)

    final_value = usdt + coin * closes[-1]
    buy_hold_value = INITIAL_CAPITAL / closes[start_idx] * closes[-1]

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
    print(f"  BACKTEST VÝSLEDKY — EMA-{EMA_PERIOD} + Fear & Greed")
    print(f"  Období: posledních {LOOKBACK_DAYS} dní  |  Počáteční kapitál: ${INITIAL_CAPITAL:.0f} USDT")
    print("=" * width)

    header = f"{'Mince':<12} {'Výnos%':>9} {'Buy&Hold%':>11} {'Alpha%':>8} {'Sharpe':>8} {'MaxDD%':>8} {'Obch.':>7} {'Nák.':>6} {'Prod.':>6}"
    sep = "-" * width

    for category, items in results.items():
        print(f"\n--- {category} ---")
        print(header)
        print(sep)
        for r in sorted(items, key=lambda x: x.get("return_pct", float("-inf")), reverse=True):
            if "error" in r:
                print(f"{r['symbol']:<12}  CHYBA: {r['error']}")
                continue
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

    print(f"Stahuji historická data Fear & Greed ({LOOKBACK_DAYS + 30} dní)...")
    fear_greed = fetch_fear_greed_historical(LOOKBACK_DAYS + 30)
    print(f"  Staženo {len(fear_greed)} denních hodnot.")

    results = {}
    for category, symbols in COINS.items():
        results[category] = []
        for symbol in symbols:
            print(f"Backtest {symbol}...", end=" ", flush=True)
            try:
                df = fetch_klines(client, symbol, LOOKBACK_DAYS, HOURS_BACK)
                result = backtest_coin(df, fear_greed, symbol)
                results[category].append(result)
                print(
                    f"výnos={result['return_pct']:+.2f}%  "
                    f"alpha={result['alpha_pct']:+.2f}%  "
                    f"sharpe={result['sharpe']:.3f}  "
                    f"maxDD={result['max_drawdown_pct']:.2f}%"
                )
                time.sleep(0.3)
            except Exception as exc:
                print(f"CHYBA: {exc}")
                results[category].append({"symbol": symbol, "error": str(exc)})

    print_results(results)

    out_path = Path(__file__).parent / "ema_backtest_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nVýsledky uloženy do: {out_path}")


if __name__ == "__main__":
    main()

"""
Results (26. 4.):
Backtest BTCUSDT... výnos=-14.52%  alpha=+2.40%  sharpe=-0.244  maxDD=45.77%
Backtest ETHUSDT... výnos=-21.67%  alpha=-54.26%  sharpe=-0.201  maxDD=57.60%
Backtest XRPUSDT... výnos=-23.85%  alpha=+11.42%  sharpe=-0.243  maxDD=56.78%
Backtest BNBUSDT... výnos=-20.29%  alpha=-25.36%  sharpe=-0.320  maxDD=58.08%
Backtest SOLUSDT... výnos=-33.93%  alpha=+9.41%  sharpe=-0.411  maxDD=63.89%
Backtest TRXUSDT... výnos=+9.72%  alpha=-22.15%  sharpe=0.540  maxDD=18.76%
Backtest LTCUSDT... výnos=-31.36%  alpha=+2.22%  sharpe=-0.445  maxDD=55.38%
Backtest BCHUSDT... výnos=+4.46%  alpha=-22.14%  sharpe=0.344  maxDD=36.49%
Backtest DOGEUSDT... výnos=-23.04%  alpha=+22.81%  sharpe=-0.136  maxDD=61.69%
Backtest AVAXUSDT... výnos=-32.66%  alpha=+25.05%  sharpe=-0.338  maxDD=68.59%
Backtest SHIBUSDT... výnos=-26.56%  alpha=+28.41%  sharpe=-0.277  maxDD=57.07%
Backtest PEPEUSDT... výnos=-33.68%  alpha=+21.68%  sharpe=-0.165  maxDD=65.75%

====================================================================================================
  BACKTEST VÝSLEDKY — EMA-21 + Fear & Greed
  Období: posledních 365 dní  |  Počáteční kapitál: $1000 USDT
====================================================================================================

--- TOP (BTC, ETH, XRP, BNB) ---
Mince           Výnos%   Buy&Hold%   Alpha%   Sharpe   MaxDD%   Obch.   Nák.  Prod.
----------------------------------------------------------------------------------------------------
BTCUSDT        -14.52%     -16.91% +   2.40%   -0.244   45.77%     415    129    286
BNBUSDT        -20.29%       5.07%  -25.36%   -0.320   58.08%     334    126    208
ETHUSDT        -21.67%      32.59%  -54.26%   -0.201   57.60%     332    116    216
XRPUSDT        -23.85%     -35.28% +  11.42%   -0.243   56.78%     404    133    271

--- MID (SOL, TRX, LTC, BCH) ---
Mince           Výnos%   Buy&Hold%   Alpha%   Sharpe   MaxDD%   Obch.   Nák.  Prod.
----------------------------------------------------------------------------------------------------
TRXUSDT          9.72%      31.87%  -22.15%    0.540   18.76%     381    125    256
BCHUSDT          4.46%      26.60%  -22.14%    0.344   36.49%     408    108    300
LTCUSDT        -31.36%     -33.57% +   2.22%   -0.445   55.38%     436    147    289
SOLUSDT        -33.93%     -43.34% +   9.41%   -0.411   63.89%     424    142    282

--- WILD (DOGE, AVAX, SHIB, PEPE) ---
Mince           Výnos%   Buy&Hold%   Alpha%   Sharpe   MaxDD%   Obch.   Nák.  Prod.
----------------------------------------------------------------------------------------------------
DOGEUSDT       -23.04%     -45.85% +  22.81%   -0.136   61.69%     446    142    304
SHIBUSDT       -26.56%     -54.97% +  28.41%   -0.277   57.07%     439    139    300
AVAXUSDT       -32.66%     -57.71% +  25.05%   -0.338   68.59%     422    140    282
PEPEUSDT       -33.68%     -55.37% +  21.68%   -0.165   65.75%     466    141    325

Výsledky uloženy do: C:\Users\jan.prikryl\Desktop\Semestralni projekt\decision_algoritm\experiments\ema_backtest\ema_backtest_results.json
"""