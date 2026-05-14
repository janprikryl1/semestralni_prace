"""
Buy & Hold benchmark comparison for the trading bot live experiment.

Prices are fetched from Binance API (daily klines) because the database
does not store historical USDC pair prices.

Method:
  - Initial capital: 95 USDC split equally among 6 pairs.
  - Entry price: Binance open price of the daily candle on experiment start date.
  - Exit price:  Binance close price of the daily candle on experiment end date.
"""

import os
import sys
from binance.client import Client
from dotenv import load_dotenv
from datetime import datetime, timezone

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

PAIRS = ["BCHUSDC", "BTCUSDC", "PEPEUSDC", "SHIBUSDC", "TRXUSDC", "XRPUSDC"]
INITIAL_CAPITAL = 95.0
CAPITAL_PER_PAIR = INITIAL_CAPITAL / len(PAIRS)

# Fixed experiment period
START_DT = datetime(2026, 4, 23, 0, 0, 0, tzinfo=timezone.utc)
END_DT = datetime(2026, 5,  8, 23, 59, 59, tzinfo=timezone.utc)


def to_ms(dt: datetime) -> int:
    """Convert datetime to milliseconds UTC timestamp."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def get_kline_price(client: Client, symbol: str, dt: datetime, position: str) -> tuple:
    """
    Fetch a single daily kline at `dt` and return (price, candle_date).
    position: 'open' returns the open of that candle,
              'close' returns the close of that candle.
    """
    ms = to_ms(dt)
    klines = client.get_klines(
        symbol=symbol,
        interval=Client.KLINE_INTERVAL_1DAY,
        startTime=ms,
        limit=1,
    )
    if not klines:
        raise RuntimeError(f"No kline data for {symbol} at {dt}")
    k = klines[0]
    candle_open_ts = datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc)
    candle_close_ts = datetime.fromtimestamp(k[6] / 1000, tz=timezone.utc)
    price = float(k[1]) if position == "open" else float(k[4])
    ts = candle_open_ts if position == "open" else candle_close_ts
    return price, ts


def main():
    start_dt, end_dt = START_DT, END_DT

    print(f"Experimentální období: {start_dt.date()}  →  {end_dt.date()}")
    print(f"Počáteční kapitál:     {INITIAL_CAPITAL:.2f} USDC ({CAPITAL_PER_PAIR:.4f} USDC / pár)")
    print()

    # Binance API
    client = Client(
        api_key=os.getenv("API_KEY", ""),
        api_secret=os.getenv("API_SECRET", ""),
    )

    col_w = [10, 16, 16, 20, 11, 11, 9, 8]
    header = (
        f"{'Symbol':<{col_w[0]}} {'Cena vstup':>{col_w[1]}} {'Cena výstup':>{col_w[2]}} "
        f"{'Množství':>{col_w[3]}} {'Vstup USDC':>{col_w[4]}} {'Výstup USDC':>{col_w[5]}} "
        f"{'PnL USDC':>{col_w[6]}} {'PnL%':>{col_w[7]}}"
    )
    sep = "-" * len(header)

    print(header)
    print(sep)

    total_start = 0.0
    total_end = 0.0
    rows = []

    for symbol in PAIRS:
        try:
            entry_price, entry_ts = get_kline_price(client, symbol, start_dt, "open")
            exit_price, exit_ts = get_kline_price(client, symbol, end_dt, "close")
        except Exception as exc:
            print(f"[ERROR] {symbol:<{col_w[0]}}: {exc}")
            continue

        coins = CAPITAL_PER_PAIR / entry_price
        end_val = coins * exit_price
        pnl = end_val - CAPITAL_PER_PAIR
        pnl_pct = (end_val / CAPITAL_PER_PAIR - 1) * 100

        total_start += CAPITAL_PER_PAIR
        total_end += end_val
        rows.append(dict(
            symbol=symbol,
            entry_price=entry_price, entry_ts=entry_ts,
            exit_price=exit_price, exit_ts=exit_ts,
            coins=coins, end_val=end_val, pnl=pnl, pnl_pct=pnl_pct,
        ))

        print(
            f"{symbol:<{col_w[0]}} "
            f"{entry_price:>{col_w[1]}.8f} "
            f"{exit_price:>{col_w[2]}.8f} "
            f"{coins:>{col_w[3]}.8f} "
            f"{CAPITAL_PER_PAIR:>{col_w[4]}.2f} "
            f"{end_val:>{col_w[5]}.2f} "
            f"{pnl:>+{col_w[6]}.2f} "
            f"{pnl_pct:>+{col_w[7]}.2f}%"
        )

    print(sep)
    total_pnl = total_end - total_start
    total_pnl_pct = (total_end / total_start - 1) * 100 if total_start else 0
    print(
        f"{'CELKEM':<{col_w[0]}} "
        f"{'':>{col_w[1]}} "
        f"{'':>{col_w[2]}} "
        f"{'':>{col_w[3]}} "
        f"{total_start:>{col_w[4]}.2f} "
        f"{total_end:>{col_w[5]}.2f} "
        f"{total_pnl:>+{col_w[6]}.2f} "
        f"{total_pnl_pct:>+{col_w[7]}.2f}%"
    )

    print()
    print("Přesné časové razítko svíček (UTC):")
    for r in rows:
        print(
            f"  {r['symbol']:<10}  "
            f"vstup:  {r['entry_ts'].strftime('%Y-%m-%d')}  "
            f"cena: {r['entry_price']:.8f}  |  "
            f"výstup: {r['exit_ts'].strftime('%Y-%m-%d')}  "
            f"cena: {r['exit_price']:.8f}"
        )


if __name__ == "__main__":
    main()
