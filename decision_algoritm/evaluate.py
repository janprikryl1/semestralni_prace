"""
evaluate.py — Vyhodnocení live-trading běhu SMA_FG / EMA_FG strategií.

Použití:
  python evaluate.py --strategy sma
  python evaluate.py --strategy ema
  python evaluate.py --strategy both
  python evaluate.py --strategy sma --config-change 2026-04-28
  python evaluate.py --strategy both --from 2026-04-24 --to 2026-05-08

Výstup:
  - Textové shrnutí do konzole
  - Graf uložený jako evaluate_<strategy>.png
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import mysql.connector
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── Konfigurace ──────────────────────────────────────────────────────────────

STRATEGY_META = {
    "sma": {
        "trading_type": "SMA_FG",
        "indicator_col": "sma",
        "label": "SMA-14",
        "color": "#2196F3",
        # Starý config (fear_buy=60, fear_sell=55)
        "old_config": {
            "fear_buy_threshold": 60,
            "fear_sell_threshold": 55,
            "buy_strong_fear_threshold": 20,
            "buy_normal_fear_threshold": 56,
            "sell_normal_fear_threshold": 60,
            "sell_strong_fear_threshold": 80,
        },
        # Nový config (aktuální)
        "new_config": {
            "fear_buy_threshold": 40,
            "fear_sell_threshold": 45,
            "buy_strong_fear_threshold": 15,
            "buy_normal_fear_threshold": 40,
            "sell_normal_fear_threshold": 45,
            "sell_strong_fear_threshold": 85,
        },
    },
    "ema": {
        "trading_type": "EMA_FG",
        "indicator_col": "ema",
        "label": "EMA-21",
        "color": "#FF5722",
        "old_config": {
            "fear_buy_threshold": 60,
            "fear_sell_threshold": 55,
            "buy_strong_fear_threshold": 20,
            "buy_normal_fear_threshold": 56,
            "sell_normal_fear_threshold": 60,
            "sell_strong_fear_threshold": 80,
        },
        "new_config": {
            "fear_buy_threshold": 46,
            "fear_sell_threshold": 45,
            "buy_strong_fear_threshold": 15,
            "buy_normal_fear_threshold": 46,
            "sell_normal_fear_threshold": 45,
            "sell_strong_fear_threshold": 80,
        },
    },
}

SIGNAL_COLORS = {"BUY": "#4CAF50", "SELL": "#F44336", "HOLD": "#9E9E9E"}


# ── Databáze ──────────────────────────────────────────────────────────────────

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )


def load_decisions(trading_type: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    sql = """
        SELECT time, `signal`, symbol, price, fear, position_size, reason
        FROM decisions
        WHERE trading_type = %s
          AND time BETWEEN %s AND %s
        ORDER BY time
    """
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (trading_type, date_from, date_to))
        rows = cursor.fetchall()
    df = pd.DataFrame(rows)
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"])
    else:
        df = pd.DataFrame(columns=["time", "signal", "symbol", "price", "fear", "position_size", "reason"])
    return df


def load_trades(trading_type: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    sql = """
        SELECT time, side, symbol, quantity, price, notional, status, details
        FROM trades
        WHERE trading_type = %s
          AND time BETWEEN %s AND %s
        ORDER BY time
    """
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (trading_type, date_from, date_to))
        rows = cursor.fetchall()
    df = pd.DataFrame(rows)
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"])
        df["notional"] = pd.to_numeric(df["notional"], errors="coerce").fillna(0)
    else:
        df = pd.DataFrame(columns=["time", "side", "symbol", "quantity", "price", "notional", "status", "details"])
    return df


# ── Analytické funkce ─────────────────────────────────────────────────────────

def signal_stats(decisions: pd.DataFrame) -> dict:
    counts = decisions["signal"].value_counts().to_dict()
    total = len(decisions)
    return {
        "total_decisions": total,
        "buy_count": counts.get("BUY", 0),
        "sell_count": counts.get("SELL", 0),
        "hold_count": counts.get("HOLD", 0),
        "buy_pct": 100 * counts.get("BUY", 0) / total if total else 0,
        "sell_pct": 100 * counts.get("SELL", 0) / total if total else 0,
        "hold_pct": 100 * counts.get("HOLD", 0) / total if total else 0,
    }


def trade_stats(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"total_trades": 0, "buy_trades": 0, "sell_trades": 0,
                "total_volume_usd": 0, "buy_volume_usd": 0, "sell_volume_usd": 0,
                "failed_trades": 0}
    ok = trades[trades["status"] == "SUCCESS"]
    buys = ok[ok["side"] == "BUY"]
    sells = ok[ok["side"] == "SELL"]
    failed = trades[trades["status"] != "SUCCESS"]
    return {
        "total_trades": len(ok),
        "buy_trades": len(buys),
        "sell_trades": len(sells),
        "total_volume_usd": ok["notional"].sum(),
        "buy_volume_usd": buys["notional"].sum(),
        "sell_volume_usd": sells["notional"].sum(),
        "failed_trades": len(failed),
    }


def split_by_config(df: pd.DataFrame, config_change: datetime | None):
    """Rozdělí DataFrame na fáze old-config a new-config."""
    if config_change is None or df.empty:
        return None, df
    old = df[df["time"] < config_change]
    new = df[df["time"] >= config_change]
    return old, new


def cumulative_notional(trades: pd.DataFrame) -> pd.DataFrame:
    """Kumulativní objem obchodů v USD po hodinách (pro graf)."""
    if trades.empty:
        return pd.DataFrame(columns=["time", "cum_buy", "cum_sell"])
    ok = trades[trades["status"] == "SUCCESS"].copy()
    ok = ok.set_index("time").sort_index()
    buys = ok[ok["side"] == "BUY"]["notional"].resample("1h").sum().cumsum()
    sells = ok[ok["side"] == "SELL"]["notional"].resample("1h").sum().cumsum()
    merged = pd.DataFrame({"cum_buy": buys, "cum_sell": sells}).ffill().fillna(0)
    merged.index.name = "time"
    return merged.reset_index()


# ── Výpis shrnutí ─────────────────────────────────────────────────────────────

def print_summary(strategy: str, meta: dict, decisions: pd.DataFrame, trades: pd.DataFrame,
                  config_change: datetime | None):
    label = meta["label"]
    sep = "─" * 60

    print(f"\n{'═' * 60}")
    print(f"  Strategy: {label} ({meta['trading_type']})")
    print(f"{'═' * 60}")

    if decisions.empty:
        print("  [!] No data in decisions table for current season.")
    else:
        print(f"\n  Season:  {decisions['time'].min():%Y-%m-%d %H:%M}  →  {decisions['time'].max():%Y-%m-%d %H:%M}")
        print(f"  Symbols: {', '.join(sorted(decisions['symbol'].unique()))}")

    # ── Celkové signály ──
    print(f"\n{sep}")
    print("  SIGNALS (total)")
    print(sep)
    s = signal_stats(decisions)
    print(f"  Rozhodnutí celkem : {s['total_decisions']:>7}")
    print(f"  BUY               : {s['buy_count']:>7}  ({s['buy_pct']:.1f}%)")
    print(f"  SELL              : {s['sell_count']:>7}  ({s['sell_pct']:.1f}%)")
    print(f"  HOLD              : {s['hold_count']:>7}  ({s['hold_pct']:.1f}%)")

    # ── Signály per config fáze ──
    if config_change is not None and not decisions.empty:
        old_dec, new_dec = split_by_config(decisions, config_change)
        print(f"\n{sep}")
        print(f"  SIGNÁLY — starý config  (před {config_change:%Y-%m-%d})")
        print(sep)
        if old_dec is not None and not old_dec.empty:
            s_old = signal_stats(old_dec)
            print(f"  BUY  {s_old['buy_count']:>5} ({s_old['buy_pct']:.1f}%)  |  "
                  f"SELL {s_old['sell_count']:>5} ({s_old['sell_pct']:.1f}%)  |  "
                  f"HOLD {s_old['hold_count']:>5} ({s_old['hold_pct']:.1f}%)")
        else:
            print("  (žádná data)")

        print(f"\n{sep}")
        print(f"  SIGNÁLY — nový config  (od {config_change:%Y-%m-%d})")
        print(sep)
        if not new_dec.empty:
            s_new = signal_stats(new_dec)
            print(f"  BUY  {s_new['buy_count']:>5} ({s_new['buy_pct']:.1f}%)  |  "
                  f"SELL {s_new['sell_count']:>5} ({s_new['sell_pct']:.1f}%)  |  "
                  f"HOLD {s_new['hold_count']:>5} ({s_new['hold_pct']:.1f}%)")
        else:
            print("  (žádná data)")

    # ── Obchody ──
    print(f"\n{sep}")
    print("  OBCHODY (SUCCESS)")
    print(sep)
    t = trade_stats(trades)
    print(f"  Obchodů celkem    : {t['total_trades']:>7}")
    print(f"  BUY               : {t['buy_trades']:>7}   (objem: {t['buy_volume_usd']:>10.2f} USD)")
    print(f"  SELL              : {t['sell_trades']:>7}   (objem: {t['sell_volume_usd']:>10.2f} USD)")
    print(f"  Celkový objem     : {t['total_volume_usd']:>20.2f} USD")
    print(f"  Selhané pokusy    : {t['failed_trades']:>7}")

    # ── Obchody per symbol ──
    if not trades.empty:
        print(f"\n{sep}")
        print("  OBCHODY PER SYMBOL")
        print(sep)
        ok = trades[trades["status"] == "SUCCESS"]
        if not ok.empty:
            grp = ok.groupby(["symbol", "side"])["notional"].agg(["count", "sum"])
            grp.columns = ["počet", "objem USD"]
            print(grp.to_string())

    print(f"\n{'═' * 60}\n")


# ── Grafy ─────────────────────────────────────────────────────────────────────

def plot_strategy(strategy: str, meta: dict, decisions: pd.DataFrame, trades: pd.DataFrame,
                  config_change: datetime | None, out_path: str):
    label = meta["label"]
    color = meta["color"]

    fig = plt.figure(figsize=(18, 14))
    fig.suptitle(f"Vyhodnocení strategie {label}", fontsize=16, fontweight="bold", y=0.98)
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

    ax_sig_time = fig.add_subplot(gs[0, :2])   # signály v čase (scatter)
    ax_sig_pie  = fig.add_subplot(gs[0, 2])    # koláčový graf signálů
    ax_fear     = fig.add_subplot(gs[1, :2])   # fear vs signál
    ax_vol_sym  = fig.add_subplot(gs[1, 2])    # objem per symbol
    ax_cum      = fig.add_subplot(gs[2, :2])   # kumulativní objem
    ax_phase    = fig.add_subplot(gs[2, 2])    # porovnání fází

    # ── 1. Signály v čase ──
    if not decisions.empty:
        for sig, grp in decisions.groupby("signal"):
            ax_sig_time.scatter(grp["time"], grp["signal"],
                                c=SIGNAL_COLORS.get(sig, "#607D8B"),
                                label=sig, alpha=0.4, s=8)
        if config_change is not None:
            ax_sig_time.axvline(config_change, color="orange", linewidth=2,
                                linestyle="--", label=f"Config změna ({config_change:%d.%m.})")
        ax_sig_time.set_title("Signály v čase")
        ax_sig_time.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        ax_sig_time.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        ax_sig_time.tick_params(axis="x", rotation=30)
        ax_sig_time.legend(loc="upper right", markerscale=2)
        ax_sig_time.set_yticks(["BUY", "HOLD", "SELL"])
        ax_sig_time.set_ylabel("Signál")
        ax_sig_time.grid(axis="x", alpha=0.3)

    # ── 2. Koláč signálů ──
    s = signal_stats(decisions)
    sizes = [s["buy_count"], s["sell_count"], s["hold_count"]]
    labels_pie = [f"BUY\n{s['buy_pct']:.1f}%", f"SELL\n{s['sell_pct']:.1f}%", f"HOLD\n{s['hold_pct']:.1f}%"]
    colors_pie = [SIGNAL_COLORS["BUY"], SIGNAL_COLORS["SELL"], SIGNAL_COLORS["HOLD"]]
    non_zero = [(sz, lb, cl) for sz, lb, cl in zip(sizes, labels_pie, colors_pie) if sz > 0]
    if non_zero:
        nz_sizes, nz_labels, nz_colors = zip(*non_zero)
        ax_sig_pie.pie(nz_sizes, labels=nz_labels, colors=nz_colors,
                       autopct="%1.0f%%", startangle=90, pctdistance=0.75)
    ax_sig_pie.set_title(f"Rozložení signálů\n(celkem {s['total_decisions']})")

    # ── 3. Fear index vs signál ──
    if not decisions.empty:
        for sig, grp in decisions.groupby("signal"):
            ax_fear.hist(grp["fear"].dropna(), bins=20, alpha=0.6,
                         color=SIGNAL_COLORS.get(sig, "#607D8B"), label=sig)
        if config_change is not None:
            # vyznač thresholdy obou configů
            old_cfg = meta["old_config"]
            new_cfg = meta["new_config"]
            ax_fear.axvline(old_cfg["fear_buy_threshold"], color="#1565C0",
                            linestyle=":", linewidth=1.5, label=f"buy thr. (starý={old_cfg['fear_buy_threshold']})")
            ax_fear.axvline(new_cfg["fear_buy_threshold"], color="#1565C0",
                            linestyle="-", linewidth=1.5, label=f"buy thr. (nový={new_cfg['fear_buy_threshold']})")
            ax_fear.axvline(old_cfg["fear_sell_threshold"], color="#B71C1C",
                            linestyle=":", linewidth=1.5, label=f"sell thr. (starý={old_cfg['fear_sell_threshold']})")
            ax_fear.axvline(new_cfg["fear_sell_threshold"], color="#B71C1C",
                            linestyle="-", linewidth=1.5, label=f"sell thr. (nový={new_cfg['fear_sell_threshold']})")
        ax_fear.set_title("Distribuce Fear indexu dle signálu")
        ax_fear.set_xlabel("Fear & Greed index")
        ax_fear.set_ylabel("Počet rozhodnutí")
        ax_fear.legend(fontsize=7)
        ax_fear.grid(alpha=0.3)

    # ── 4. Objem obchodů per symbol ──
    if not trades.empty:
        ok = trades[trades["status"] == "SUCCESS"]
        if not ok.empty:
            sym_vol = ok.groupby(["symbol", "side"])["notional"].sum().unstack(fill_value=0)
            syms = sym_vol.index.tolist()
            x = range(len(syms))
            width = 0.35
            if "BUY" in sym_vol.columns:
                ax_vol_sym.bar([i - width / 2 for i in x], sym_vol["BUY"],
                               width, label="BUY", color=SIGNAL_COLORS["BUY"], alpha=0.8)
            if "SELL" in sym_vol.columns:
                ax_vol_sym.bar([i + width / 2 for i in x], sym_vol["SELL"],
                               width, label="SELL", color=SIGNAL_COLORS["SELL"], alpha=0.8)
            ax_vol_sym.set_xticks(list(x))
            ax_vol_sym.set_xticklabels([s.replace("USDC", "") for s in syms], rotation=45, ha="right")
            ax_vol_sym.set_title("Objem obchodů (USD) / symbol")
            ax_vol_sym.set_ylabel("USD")
            ax_vol_sym.legend()
            ax_vol_sym.grid(axis="y", alpha=0.3)

    # ── 5. Kumulativní objem v čase ──
    cum = cumulative_notional(trades)
    if not cum.empty:
        ax_cum.fill_between(cum["time"], cum["cum_buy"], alpha=0.4,
                            color=SIGNAL_COLORS["BUY"], label="Kumulativní BUY")
        ax_cum.fill_between(cum["time"], cum["cum_sell"], alpha=0.4,
                            color=SIGNAL_COLORS["SELL"], label="Kumulativní SELL")
        ax_cum.plot(cum["time"], cum["cum_buy"], color=SIGNAL_COLORS["BUY"], linewidth=1.2)
        ax_cum.plot(cum["time"], cum["cum_sell"], color=SIGNAL_COLORS["SELL"], linewidth=1.2)
        if config_change is not None:
            ax_cum.axvline(config_change, color="orange", linewidth=2,
                           linestyle="--", label=f"Config změna")
        ax_cum.set_title("Kumulativní objem obchodů v USD")
        ax_cum.set_ylabel("USD")
        ax_cum.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        ax_cum.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        ax_cum.tick_params(axis="x", rotation=30)
        ax_cum.legend()
        ax_cum.grid(alpha=0.3)

    # ── 6. Porovnání fází (starý vs nový config) ──
    if config_change is not None and not decisions.empty:
        old_dec, new_dec = split_by_config(decisions, config_change)
        phases = []
        if old_dec is not None and not old_dec.empty:
            s_old = signal_stats(old_dec)
            phases.append(("Starý config", s_old))
        if not new_dec.empty:
            s_new = signal_stats(new_dec)
            phases.append(("Nový config", s_new))

        if phases:
            x_ph = range(len(phases))
            buy_vals  = [p[1]["buy_pct"]  for p in phases]
            sell_vals = [p[1]["sell_pct"] for p in phases]
            hold_vals = [p[1]["hold_pct"] for p in phases]
            w = 0.25
            ax_phase.bar([i - w for i in x_ph], buy_vals,  w, label="BUY%",  color=SIGNAL_COLORS["BUY"],  alpha=0.85)
            ax_phase.bar([i     for i in x_ph], sell_vals, w, label="SELL%", color=SIGNAL_COLORS["SELL"], alpha=0.85)
            ax_phase.bar([i + w for i in x_ph], hold_vals, w, label="HOLD%", color=SIGNAL_COLORS["HOLD"], alpha=0.85)
            ax_phase.set_xticks(list(x_ph))
            ax_phase.set_xticklabels([p[0] for p in phases], fontsize=9)
            ax_phase.set_ylabel("%")
            ax_phase.set_title("Signály: starý vs nový config")
            ax_phase.legend(fontsize=8)
            ax_phase.grid(axis="y", alpha=0.3)
            ax_phase.set_ylim(0, 100)
    else:
        ax_phase.set_visible(False)

    plt.savefig(out_path, dpi=130, bbox_inches="tight")
    print(f"  Graf uložen: {out_path}")
    plt.show()


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Vyhodnocení live-trading strategií SMA_FG / EMA_FG"
    )
    parser.add_argument(
        "--strategy", choices=["sma", "ema", "both"], default="both",
        help="Která strategie se vyhodnotí (sma / ema / both)"
    )
    parser.add_argument(
        "--config-change",
        help="Datum přepnutí konfigurace ve formátu YYYY-MM-DD (odděluje staré a nové nastavení)"
    )
    parser.add_argument(
        "--from", dest="date_from", default=None,
        help="Začátek období YYYY-MM-DD (výchozí: 30 dní zpět)"
    )
    parser.add_argument(
        "--to", dest="date_to", default=None,
        help="Konec období YYYY-MM-DD (výchozí: dnes)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    date_to = datetime.strptime(args.date_to, "%Y-%m-%d") if args.date_to else datetime.now()
    date_from = (datetime.strptime(args.date_from, "%Y-%m-%d") if args.date_from
                 else date_to - timedelta(days=30))
    config_change = (datetime.strptime(args.config_change, "%Y-%m-%d")
                     if args.config_change else None)

    strategies = ["sma", "ema"] if args.strategy == "both" else [args.strategy]

    print(f"\nObdobí: {date_from:%Y-%m-%d} → {date_to:%Y-%m-%d}")
    if config_change:
        print(f"Přepnutí configu: {config_change:%Y-%m-%d}")

    for strat in strategies:
        meta = STRATEGY_META[strat]
        print(f"\nNačítám data pro {meta['trading_type']}...")
        try:
            decisions = load_decisions(meta["trading_type"], date_from, date_to)
            trades    = load_trades(meta["trading_type"], date_from, date_to)
        except Exception as exc:
            print(f"  [CHYBA] Připojení k databázi selhalo: {exc}", file=sys.stderr)
            continue

        print(f"  Načteno {len(decisions)} rozhodnutí, {len(trades)} obchodů.")

        print_summary(strat, meta, decisions, trades, config_change)

        out_png = f"evaluate_{strat}.png"
        plot_strategy(strat, meta, decisions, trades, config_change, out_png)


if __name__ == "__main__":
    main()
