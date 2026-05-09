"""
pnl.py — Přesný výpočet P&L z Binance API + aktuální ceny

Použití:
  python pnl.py
  python pnl.py --deposits 38.68
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


def load_trades_from_api(client: Client,
                         symbols: list[str],
                         from_ts: int | None,
                         exclude_ids: set[int]) -> tuple[list[dict], list[dict]]:
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
                print(f"[SKIPPED] ID {tid} {sym} {'BUY' if t['isBuyer'] else 'SELL'}  "
                      f"qty={t['qty']} notional={t['quoteQty']}")
                continue

            ts = int(t["time"])
            all_trades.append({
                "id":      tid,
                "time":    ts,
                "symbol":  sym,
                "side":    "BUY" if t["isBuyer"] else "SELL",
                "price":   float(t["price"]),
                "qty":     float(t["qty"]),
                "notional": float(t["quoteQty"]),
            })

            comm  = float(t["commission"])
            asset = t["commissionAsset"]
            if comm > 0 and asset:
                fee_events.append({"asset": asset, "amount": comm, "time": ts})

    all_trades.sort(key=lambda t: t["time"])
    return all_trades, fee_events


def fetch_price_history(client: Client, symbol: str,
                        timestamps_ms: list[int]) -> dict[int, float]:
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


def resolve_fees(client: Client,
                 fee_events: list[dict],
                 current_prices: dict[str, float]) -> dict[str, dict]:
    """
    Převede fee_events na USDC hodnoty:
      BNB   → historická cena z 1m klines (jedno hromadné volání)
      USDC  → přímá hodnota
      ostatní → aktuální cena (PEPE fees jsou zanedbatelné)

    Vrací {asset: {amount, usdc_value, method}}.
    """
    # Shromáždím BNB timestampy a stáhnu klines najednou
    bnb_times = [f["time"] for f in fee_events if f["asset"] == "BNB"]
    if bnb_times:
        print(f"  Načítám historické BNB klines ({len(bnb_times)} záznamů, 1 API volání)...")
    bnb_map = fetch_price_history(client, "BNBUSDC", bnb_times)

    resolved: dict[str, dict] = {}

    for f in fee_events:
        asset = f["asset"]
        amount = f["amount"]
        ts = f["time"]

        if asset == "USDC":
            usdc_val = amount
            method   = "přímá hodnota"
        elif asset == "BNB":
            minute_ts = (ts // 60_000) * 60_000
            if minute_ts in bnb_map:
                price = bnb_map[minute_ts]
            elif bnb_map:
                # Nejbližší dostupná minuta
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
        except Exception:
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
        self.pre_existing_sold: float = 0.0  # sold from previous holdings (unknown cost basis)

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


def calculate_pnl(trades: list[dict]) -> dict[str, Position]:
    positions: dict[str, Position] = defaultdict(Position)
    for t in trades:
        sym = t["symbol"]
        if t["side"] == "BUY":
            positions[sym].buy(t["qty"], t["notional"])
        elif t["side"] == "SELL":
            positions[sym].sell(t["qty"], t["notional"])
    return positions


def fmt(v: float, plus: bool = True) -> str:
    sign = "+" if plus and v >= 0 else ""
    return f"{sign}{v:>10.4f} USDC"


def print_report(positions: dict[str, Position],
                 resolved_fees: dict[str, dict],
                 current_prices: dict[str, float],
                 current_balances: dict[str, float],
                 deposits: float):

    sep  = "─" * 68
    sep2 = "═" * 68

    total_realized   = 0.0
    total_unrealized = 0.0
    total_pre_sold   = 0.0

    print(f"\n{sep2}")
    print("  P&L ANALÝZA  —  AVCO metodika")
    print(f"{sep2}")

    # ── Realized P&L ──
    print(f"\n{sep}")
    print("  REALIZOVANÝ P&L  (uzavřené pozice z bot-obchodů)")
    print(sep)
    print(f"  {'Symbol':<14} {'Realized P&L':>14}")
    print(f"  {'──────':<14} {'──────────────':>14}")
    for sym, pos in sorted(positions.items()):
        if abs(pos.realized) > 0.0001:
            total_realized += pos.realized
            color = ""
            print(f"  {sym:<14} {fmt(pos.realized)}")
    print(f"  {'CELKEM':<14} {fmt(total_realized)}")

    # ── Pre-existing sold ──
    pre_items = [(s, p) for s, p in positions.items() if p.pre_existing_sold > 0.0001]
    if pre_items:
        print(f"\n{sep}")
        print("  PRODÁNO Z PŘEDCHOZÍCH HOLDINGS  (cost basis neznámý)")
        print(sep)
        for sym, pos in sorted(pre_items):
            total_pre_sold += pos.pre_existing_sold
            print(f"  {sym:<14} příjem: {pos.pre_existing_sold:>10.4f} USDC  (BNB, BTC před botem)")

    # ── Open positions ──
    print(f"\n{sep}")
    print("  OTEVŘENÉ POZICE  (unrealized P&L)")
    print(sep)
    print(f"  {'Symbol':<14} {'Qty':>14} {'Avg cost':>10} {'Now':>10} {'UPnL':>12}")
    print(f"  {'──────':<14} {'───':>14} {'────────':>10} {'───':>10} {'────':>12}")

    open_cost  = 0.0
    open_value = 0.0

    for sym, pos in sorted(positions.items()):
        if pos.qty > 1e-9:
            cur_price = current_prices.get(sym, 0.0)
            cur_val   = pos.qty * cur_price
            upnl      = cur_val - pos.total_cost
            total_unrealized += upnl
            open_cost  += pos.total_cost
            open_value += cur_val
            sign = "+" if upnl >= 0 else ""
            print(f"  {sym:<14} {pos.qty:>14.6f} {pos.total_cost:>10.4f} {cur_val:>10.4f} {sign}{upnl:>10.4f}")

    print(f"\n  Investováno v otevřených pozicích: {open_cost:.4f} USDC")
    print(f"  Aktuální tržní hodnota:            {open_value:.4f} USDC")
    print(f"  Unrealized P&L:              {fmt(total_unrealized)}")

    # ── Aktuální portfolio ──
    print(f"\n{sep}")
    print("  AKTUÁLNÍ PORTFOLIO  (z Binance API)")
    print(sep)
    usdc = current_balances.get("USDC", 0.0)
    print(f"  {'USDC cash':<14} {usdc:>10.4f}")
    crypto_total = 0.0
    for asset, qty in sorted(current_balances.items()):
        if asset in ("USDC", "BNB") or qty < 1e-9:
            continue
        sym   = asset + "USDC"
        price = current_prices.get(sym, 0.0)
        val   = qty * price
        crypto_total += val
        if val > 0.01:
            print(f"  {asset:<14} {qty:>14.6f} × {price:>12.8f} = {val:>8.4f} USDC")
    bnb = current_balances.get("BNB", 0.0)
    bnb_price = current_prices.get("BNBUSDC", 0.0)
    bnb_val = bnb * bnb_price
    if bnb_val > 0.001:
        print(f"  {'BNB (fee)':<14} {bnb:>14.8f} × {bnb_price:>12.4f} = {bnb_val:>8.4f} USDC")
        crypto_total += bnb_val

    portfolio_total = usdc + crypto_total
    print(f"\n  Celková hodnota portfolia: {portfolio_total:.4f} USDC")

    # ── Poplatky ──
    total_fees_usdc = sum(v["usdc_value"] for v in resolved_fees.values())
    print(f"\n{sep}")
    print("  POPLATKY  (commission)  —  historické ceny kde dostupné")
    print(sep)
    print(f"  {'Asset':<8} {'Množství':>16}  {'≈ USDC':>10}  Metoda")
    print(f"  {'─────':<8} {'────────':>16}  {'──────':>10}  ──────")
    for asset, v in sorted(resolved_fees.items()):
        print(f"  {asset:<8} {v['amount']:>16.8f}  {v['usdc_value']:>10.4f}    {v['method']}")
    print(f"  {'CELKEM':<8} {'':>16}  {total_fees_usdc:>10.4f} USDC")

    # ── Shrnutí ──
    net_pnl       = total_realized + total_unrealized
    net_pnl_after = net_pnl - total_fees_usdc
    print(f"\n{sep2}")
    print("  SHRNUTÍ")
    print(sep2)
    print(f"  Realizovaný P&L (bot trades): {fmt(total_realized)}")
    print(f"  Unrealizovaný P&L:            {fmt(total_unrealized)}")
    print(f"  ─────────────────────────────────────────────────────────")
    print(f"  P&L před poplatky:            {fmt(net_pnl)}")
    print(f"  Poplatky celkem:              {fmt(-total_fees_usdc, plus=False)}")
    print(f"  ═════════════════════════════════════════════════════════")
    print(f"  Čistý P&L po poplatcích:      {fmt(net_pnl_after)}")
    if deposits > 0:
        print(f"\n  Vloženo (deposity):           {deposits:>10.2f} USD")
        print(f"  Celková hodnota portfolia:    {portfolio_total:>10.4f} USDC")
        simple_pnl = portfolio_total - deposits
        print(f"  Portfolio − deposity:         {fmt(simple_pnl)}")
    if abs(total_pre_sold) > 0.001:
        print(f"\n  Pozn.: {total_pre_sold:.4f} USDC pochází z prodeje pre-existing")
        print(f"         holdings (BNB, BTC před spuštěním botů) — tyto")
        print(f"         neovlivňují P&L z obchodní strategie.")
    print(f"{sep2}\n")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Výpočet P&L z Binance API (AVCO)")
    parser.add_argument(
        "--exclude-ids", default="2635588222,2635599964",
        help="Čárkou oddělená ID trades k ignorování (výchozí: 2635588222,2635599964)"
    )
    parser.add_argument(
        "--deposits", type=float, default=38.68,
        help="Celkový objem depositů v USD (výchozí: 38.68)"
    )
    parser.add_argument(
        "--from", dest="date_from", default="2026-04-09",
        help="Začátek období YYYY-MM-DD (výchozí: 2026-04-09)"
    )
    parser.add_argument(
        "--symbols", default=None,
        help="Čárkou oddělené symboly (výchozí: všechny known symbols)"
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

    print("Připojuji se k Binance API...")
    client = get_client()

    print(f"Načítám trades od {args.date_from} pro symboly: {', '.join(symbols)}")
    if exclude_ids:
        print(f"Ignoruji trade ID: {', '.join(str(i) for i in sorted(exclude_ids))}")

    trades, fee_events = load_trades_from_api(client, symbols, from_ts, exclude_ids)
    print(f"  Načteno {len(trades)} trades, {len(fee_events)} fee záznamů (po vyloučení)\n")

    print("Načítám aktuální ceny...")
    prices = get_current_prices(client, symbols + ["BNBUSDC"])

    print("Načítám zůstatky...")
    balances = get_balances(client)

    print("Přepočítávám poplatky na USDC (historické ceny)...")
    resolved_fees = resolve_fees(client, fee_events, prices)

    print("Počítám P&L...\n")
    positions = calculate_pnl(trades)

    print_report(positions, resolved_fees, prices, balances, args.deposits)


if __name__ == "__main__":
    main()
