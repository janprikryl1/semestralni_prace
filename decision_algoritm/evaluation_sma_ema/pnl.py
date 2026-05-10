"""
pnl.py — Přesný výpočet P&L z Binance API + aktuální ceny

Použití:
  python pnl.py
  python pnl.py --exclude-ids 2635588222,2635599964
  python pnl.py --from 2026-04-09

Metodika: Average Cost (AVCO)
  realized P&L  = (prodejní cena − průměrná nákupní cena) × prodané množství
  unrealized P&L = (aktuální cena − průměrná nákupní cena) × držené množství
  total P&L     = realized + unrealized
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict
from binance.client import Client
from dotenv import load_dotenv

load_dotenv()
KNOWN_SYMBOLS = ["BTCUSDC", "XRPUSDC", "BCHUSDC", "TRXUSDC", "PEPEUSDC", "SHIBUSDC", "BNBUSDC"]


def get_client() -> Client:
    key = os.getenv("API_KEY")
    secret = os.getenv("API_SECRET")
    if not key or not secret:
        sys.exit("[ERROR] Missing API_KEY or API_SECRET in .env")
    return Client(key, secret)


def load_trades_from_api(client: Client, symbols: list[str], from_ts: int | None, exclude_ids: set[int]) -> tuple[list[dict], list[dict]]:
    """
    Vrací (trades, fee_events).
    fee_events = [{asset, amount, time}, ...] — jeden záznam na každý trade,
    uchovává timestamp pro pozdější historický přepočet.
    """
    all_trades: list[dict] = []
    fee_events: list[dict] = []

    for sym in symbols:
        try:
            kwargs = {"symbol": sym, "limit": 1000}
            if from_ts:
                kwargs["startTime"] = from_ts
            raw = client.get_my_trades(**kwargs)
        except Exception as e:
            print(f"[WARNING] Couldn't load {sym}: {e}")
            continue

        for t in raw:
            tid = int(t["id"])
            if tid in exclude_ids:
                print(f"[SKIPPED] ID {tid} {sym} {'BUY' if t['isBuyer'] else 'SELL'} "
                      f"qty={t['qty']} notional={t['quoteQty']}")
                continue

            ts = int(t["time"])
            all_trades.append({
                "id": tid,
                "time": ts,
                "symbol": sym,
                "side": "BUY" if t["isBuyer"] else "SELL",
                "price": float(t["price"]),
                "qty": float(t["qty"]),
                "notional": float(t["quoteQty"]),
                "commission": float(t["commission"]),
                "commissionAsset": t["commissionAsset"],
            })

            comm = float(t["commission"])
            asset = t["commissionAsset"]
            if comm > 0 and asset:
                fee_events.append({"asset": asset, "amount": comm, "time": ts})

    all_trades.sort(key=lambda t: t["time"])
    return all_trades, fee_events


def fetch_price_history(client: Client, symbol: str, timestamps_ms: list[int]) -> dict[int, float]:
    """
    Načte minutové klines pro daný symbol jedním API voláním
    a vrátí mapu {open_time_ms → close_price}.
    """
    if not timestamps_ms:
        return {}
    start = min(timestamps_ms)
    end = max(timestamps_ms) + 60_000
    try:
        klines = client.get_historical_klines(
            symbol, Client.KLINE_INTERVAL_1MINUTE,
            start_str=str(start), end_str=str(end)
        )
    except Exception as e:
        print(f"[WARNING] Couldn't load klines for {symbol}: {e}")
        return {}
    return {int(k[0]): float(k[4]) for k in klines}


def resolve_fees(client: Client, fee_events: list[dict], current_prices: dict[str, float]) -> dict[str, dict]:
    """
    Převede fee_events na USDC hodnoty:
      BNB   → historická cena z 1m klines (jedno hromadné volání)
      USDC  → přímá hodnota
      ostatní → aktuální cena (PEPE fees jsou zanedbatelné)

    Vrací {asset: {amount, usdc_value, method}}.
    """
    bnb_times = [f["time"] for f in fee_events if f["asset"] == "BNB"]
    bnb_map = fetch_price_history(client, "BNBUSDC", bnb_times)

    resolved: dict[str, dict] = {}

    for f in fee_events:
        asset = f["asset"]
        amount = f["amount"]
        ts = f["time"]

        if asset == "USDC":
            usdc_val = amount
            method = "přímá hodnota"
        elif asset == "BNB":
            minute_ts = (ts // 60_000) * 60_000
            if minute_ts in bnb_map:
                price = bnb_map[minute_ts]
            elif bnb_map:
                # Nearest available minute
                closest = min(bnb_map, key=lambda t: abs(t - ts))
                price = bnb_map[closest]
            else:
                price = current_prices.get("BNBUSDC", 0.0)
            usdc_val = amount * price
            method = "historická cena (1m kline)"
        else:
            price = current_prices.get(asset + "USDC", 0.0)
            usdc_val = amount * price
            method = "aktuální cena"

        if asset not in resolved:
            resolved[asset] = {"amount": 0.0, "usdc_value": 0.0, "method": method}
        resolved[asset]["amount"] += amount
        resolved[asset]["usdc_value"] += usdc_val

    return resolved


def get_current_prices(client: Client, symbols: list[str]) -> dict[str, float]:
    prices = {}
    for sym in symbols:
        try:
            prices[sym] = float(client.get_symbol_ticker(symbol=sym)["price"])
        except Exception as e:
            print(f"[WARNING] Price for {sym} not loaded ({e})")
            prices[sym] = 0.0
    return prices


def get_balances(client: Client) -> dict[str, float]:
    account = client.get_account()
    return {
        b["asset"]: float(b["free"]) + float(b["locked"])
        for b in account["balances"]
        if float(b["free"]) + float(b["locked"]) > 0
    }


# P&L count (AVCO)
class Position:
    def __init__(self):
        self.qty: float = 0.0
        self.total_cost: float = 0.0
        self.avg_cost: float = 0.0
        self.realized: float = 0.0
        self.pre_existing_sold: float = 0.0 # sold from previous holdings (unknown cost basis)

    def buy(self, qty: float, notional: float):
        self.total_cost += notional
        self.qty += qty
        self.avg_cost = self.total_cost / self.qty if self.qty > 0 else 0

    def sell(self, qty: float, notional: float):
        if self.qty >= qty - 1e-9:
            cost = self.avg_cost * qty
            self.realized += notional - cost
            self.qty = max(0.0, self.qty - qty)
            self.total_cost = self.avg_cost * self.qty
        else:
            # Prodáváme víc než jsme koupili — předchozí holding
            # Část se prodává z bot-koupených pozic, část z pre-existing
            bot_qty = self.qty
            pre_qty = qty - bot_qty
            if bot_qty > 0:
                cost = self.avg_cost * bot_qty
                bot_notional = notional * (bot_qty / qty)
                self.realized += bot_notional - cost
            pre_notional = notional * (pre_qty / qty)
            self.pre_existing_sold += pre_notional
            self.qty = 0.0
            self.total_cost = 0.0
            self.avg_cost = 0.0


def calculate_pnl(trades: list[dict], verbose: bool = False) -> tuple[dict[str, Position], list[dict]]:
    """
    Returns (positions, trade_log).
    trade_log is an empty list if verbose=False.
    Each entry in trade_log contains the AVCO status *after* the trade has been executed.
    Fee is stored directly in each trade, not matched by timestamp.
    """
    positions: dict[str, Position] = defaultdict(Position)

    trade_log: list[dict] = []
    cum_realized: dict[str, float] = defaultdict(float)

    for t in trades:
        sym = t["symbol"]
        pos = positions[sym]

        if t["side"] == "BUY":
            pos.buy(t["qty"], t["notional"])
            trade_pnl = None

        elif t["side"] == "SELL":
            realized_before = pos.realized
            pos.sell(t["qty"], t["notional"])
            trade_pnl = pos.realized - realized_before
            cum_realized[sym] += trade_pnl

        else:
            continue

        if verbose:
            commission = t.get("commission", 0.0)
            commission_asset = t.get("commissionAsset", "")

            fee_str = (
                f"{commission:.8f} {commission_asset}"
                if commission > 0 and commission_asset
                else "—"
            )

            trade_log.append({
                "time": datetime.fromtimestamp(
                    t["time"] / 1000,
                    tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": sym,
                "side": t["side"],
                "price": t["price"],
                "qty": t["qty"],
                "notional": t["notional"],
                "fee": fee_str,
                "fee_amount": commission,
                "fee_asset": commission_asset,
                "avg_cost": pos.avg_cost,
                "qty_after": pos.qty,
                "trade_pnl": trade_pnl,
                "cum_realized": cum_realized[sym],
            })

    return positions, trade_log


def print_trades_verbose(trade_log: list[dict]): #Binance Trade History
    sep = "─" * 148
    print(f"\n{sep}")
    print("AvgCost = průměrná pořizovací cena (AVCO) po tomto obchodu")
    print("TradePnL = notional − AvgCost × qty (pouze pro SELL)")
    print(sep)
    hdr = (f"{'Datum (UTC)':<22} {'Symbol':<12} {'Side':<5} "
           f"{'Cena':>12} {'Qty':>16} {'Notional':>10} "
           f"{'Fee':<28} {'AvgCost':>10} {'QtyPo':>16} "
           f"{'TradePnL':>10} {'KumPnL':>10}")
    print(hdr)
    print(f"{'─'*22} {'─'*12} {'─'*5} {'─'*12} {'─'*16} {'─'*10} "
          f"{'─'*28} {'─'*10} {'─'*16} {'─'*10} {'─'*10}")

    for r in trade_log:
        pnl_s = f"{r['trade_pnl']:>+10.4f}" if r["trade_pnl"] is not None else f"{'—':>10}"
        cum_s = f"{r['cum_realized']:>+10.4f}" if r["trade_pnl"] is not None else f"{'—':>10}"
        print(
            f"{r['time']:<22} {r['symbol']:<12} {r['side']:<5} "
            f"{r['price']:>12.6f} {r['qty']:>16.6f} {r['notional']:>10.4f} "
            f"{r['fee']:<28} {r['avg_cost']:>10.6f} {r['qty_after']:>16.6f} "
            f"{pnl_s} {cum_s}"
        )

    print(sep)


def print_report(positions: dict[str, Position], resolved_fees: dict[str, dict], current_prices: dict[str, float], current_balances: dict[str, float]):
    sep = "─" * 68
    sep2 = "═" * 68

    total_realized = 0.0
    total_unrealized = 0.0
    total_pre_sold = 0.0

    print(f"\n{sep2}")
    print("P&L ANALÝZA — AVCO metodika")
    print(f"{sep2}")

    # Realized P&L
    print(f"\n{sep}")
    print("REALIZOVANÝ P&L (uzavřené pozice z bot-obchodů)")
    print(sep)
    print(f"{'Symbol':<14} {'Realized P&L':>14}")
    print(f"{'──────':<14} {'──────────────':>14}")
    for sym, pos in sorted(positions.items()):
        if abs(pos.realized) > 0.0001:
            total_realized += pos.realized
            print(f"{sym:<14} {pos.realized}")
    print(f"{'CELKEM':<14} {total_realized}")

    # Pre-existing sold
    pre_items = [(s, p) for s, p in positions.items() if p.pre_existing_sold > 0.0001]
    if pre_items:
        print(f"\n{sep}")
        print("PRODÁNO Z PŘEDCHOZÍCH HOLDINGS (cost basis neznámý)")
        print(sep)
        for sym, pos in sorted(pre_items):
            total_pre_sold += pos.pre_existing_sold
            print(f"{sym:<14} příjem: {pos.pre_existing_sold:>10.4f} USDC (před spuštěním algoritmu)")

    # Open positions
    print(f"\n{sep}")
    print("OTEVŘENÉ POZICE (unrealized P&L)")
    print(sep)
    print(f"{'Symbol':<14} {'Qty':>14} {'Cost basis':>10} {'Avg cost':>10} {'Now':>10} {'UPnL':>12}")
    print(f"{'──────':<14} {'───':>14} {'──────────':>10} {'────────':>10} {'───':>10} {'────':>12}")

    open_cost = 0.0
    open_value = 0.0

    for sym, pos in sorted(positions.items()):
        if pos.qty > 1e-9:
            cur_price = current_prices.get(sym, 0.0)
            cur_val = pos.qty * cur_price
            upnl = cur_val - pos.total_cost
            total_unrealized += upnl
            open_cost += pos.total_cost
            open_value += cur_val
            sign = "+" if upnl >= 0 else ""
            print(f"{sym:<14} {pos.qty:>14.6f} {pos.total_cost:>10.4f} {pos.avg_cost:>10.6f} {cur_val:>10.4f} {sign}{upnl:>10.4f}")

    print(f"\nInvestováno v otevřených pozicích: {open_cost:.4f} USDC")
    print(f"Aktuální tržní hodnota: {open_value:.4f} USDC")
    print(f"Unrealized P&L: {total_unrealized}")

    # Current assets
    print(f"\n{sep}")
    print("AKTUÁLNÍ PORTFOLIO (Spot wallet)")
    print(f"[Info] Earn/Savings/BNB Vault zůstatky jsou mimo Spot a nejsou zahrnuty")
    print(sep)
    usdc = current_balances.get("USDC", 0.0)
    print(f"{'USDC cash':<14} {usdc:>10.4f}")
    crypto_total = 0.0
    for asset, qty in sorted(current_balances.items()):
        if asset in ("USDC", "BNB") or qty < 1e-9:
            continue
        sym = asset + "USDC"
        price = current_prices.get(sym, 0.0)
        val = qty * price
        crypto_total += val
        if val > 0.01:
            print(f"{asset:<14} {qty:>14.6f} × {price:>12.8f} = {val:>8.4f} USDC")
    bnb = current_balances.get("BNB", 0.0)
    bnb_price = current_prices.get("BNBUSDC", 0.0)
    bnb_val = bnb * bnb_price
    if bnb > 1e-9:
        warn = "[!] CENA NENAČTENA — nezapočítáno!" if bnb_price == 0.0 else ""
        print(f"{'BNB':<14} {bnb:>14.8f} × {bnb_price:>12.4f} = {bnb_val:>8.4f} USDC{warn}")
        crypto_total += bnb_val

    portfolio_total = usdc + crypto_total
    print(f"\nSpot celkem: {portfolio_total:.4f} USDC")

    # Fees
    total_fees_usdc = sum(v["usdc_value"] for v in resolved_fees.values())
    print(f"\n{sep}")
    print("POPLATKY (commission) — historické ceny kde dostupné")
    print(sep)
    print(f"{'Asset':<8} {'Množství':>16}  {'≈ USDC':>10}  Metoda")
    print(f"{'─────':<8} {'────────':>16}  {'──────':>10}  ──────")
    for asset, v in sorted(resolved_fees.items()):
        print(f"{asset:<8} {v['amount']:>16.8f}  {v['usdc_value']:>10.4f} {v['method']}")
    print(f"{'CELKEM':<8} {'':>16}  {total_fees_usdc:>10.4f} USDC")

    # Summary
    net_pnl = total_realized + total_unrealized
    net_pnl_after = net_pnl - total_fees_usdc
    print(f"\n{sep2}")
    print("SHRNUTÍ")
    print(sep2)
    print(f"Realizovaný P&L (bot trades): {total_realized}")
    print(f"Unrealizovaný P&L: {total_unrealized}")
    print(f"─────────────────────────────────────────────────────────")
    print(f"P&L před poplatky: {net_pnl}")
    print(f"Poplatky celkem: {total_fees_usdc}")
    print(f"═════════════════════════════════════════════════════════")
    print(f"Čistý P&L po poplatcích: {net_pnl_after}")
    print(f"{sep2}\n")


def main():
    parser = argparse.ArgumentParser(description="P&L Calculation Using the Binance API (AVCO)")
    parser.add_argument(
        "--exclude-ids", default="2635588222,2635599964",
        help="Comma-separated list of trade IDs to ignore (default: 2635588222,2635599964)"
    )

    parser.add_argument(
        "--from", dest="date_from", default="2026-04-09",
        help="Start date: YYYY-MM-DD (default: 2026-04-09)"
    )
    parser.add_argument(
        "--symbols", default=None,
        help="Comma-separated symbols (default: all known symbols)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Displays the transaction details for each trade (similar to Binance Trade History)"
    )
    args = parser.parse_args()

    exclude_ids: set[int] = set()
    if args.exclude_ids:
        for raw in args.exclude_ids.split(","):
            raw = raw.strip()
            if raw:
                exclude_ids.add(int(raw))

    from_ts: int | None = None
    if args.date_from:
        dt = datetime.strptime(args.date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        from_ts = int(dt.timestamp() * 1000)

    symbols = KNOWN_SYMBOLS
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]

    client = get_client()

    print(f"[Info] Loading trades form {args.date_from} for symbols: {', '.join(symbols)}")
    trades, fee_events = load_trades_from_api(client, symbols, from_ts, exclude_ids)
    print(f"[Info] Loaded {len(trades)} trades, {len(fee_events)} fee records\n")
    prices = get_current_prices(client, symbols + ["BNBUSDC"])
    balances = get_balances(client)
    resolved_fees = resolve_fees(client, fee_events, prices)
    positions, trade_log = calculate_pnl(trades, verbose=args.verbose)
    if args.verbose:
        print_trades_verbose(trade_log)
    print_report(positions, resolved_fees, prices, balances)


if __name__ == "__main__":
    main()
