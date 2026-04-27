from collections import Counter

from database_loader import load_decisions, load_trades


def average(values):
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def compute_statistics():
    decisions = load_decisions()
    trades = load_trades()

    signal_counts = Counter(item["signal"] for item in decisions)
    trade_status_counts = Counter(item["status"] for item in trades)
    trade_side_counts = Counter(item["side"] for item in trades)

    successful_trades = [item for item in trades if item["status"] == "SUCCESS"]
    total_buy_notional = sum(item["notional"] or 0.0 for item in successful_trades if item["side"] == "BUY")
    total_sell_notional = sum(item["notional"] or 0.0 for item in successful_trades if item["side"] == "SELL")
    avg_fear = average(item["fear"] for item in decisions if item["fear"] is not None)
    avg_strength = average(item["action_strength"] for item in decisions if item["action_strength"] is not None)

    return {
        "decision_count": len(decisions),
        "trade_count": len(trades),
        "signal_counts": dict(signal_counts),
        "trade_status_counts": dict(trade_status_counts),
        "trade_side_counts": dict(trade_side_counts),
        "successful_trade_count": len(successful_trades),
        "total_buy_notional": total_buy_notional,
        "total_sell_notional": total_sell_notional,
        "net_quote_flow": total_sell_notional - total_buy_notional,
        "average_fear": avg_fear,
        "average_action_strength": avg_strength,
    }


def print_statistics():
    stats = compute_statistics()

    print("=== Strategy Evaluation ===")
    print(f"Decisions recorded: {stats['decision_count']}")
    print(f"Trades recorded: {stats['trade_count']}")
    print(f"Successful trades: {stats['successful_trade_count']}")
    print()

    print("Signal counts:")
    for signal, count in sorted(stats["signal_counts"].items()):
        print(f"  {signal}: {count}")
    print()

    print("Trade status counts:")
    for status, count in sorted(stats["trade_status_counts"].items()):
        print(f"  {status}: {count}")
    print()

    print("Trade side counts:")
    for side, count in sorted(stats["trade_side_counts"].items()):
        print(f"  {side}: {count}")
    print()

    print(f"Total BUY volume (quote asset): {stats['total_buy_notional']:.4f}")
    print(f"Total SELL volume (quote asset): {stats['total_sell_notional']:.4f}")
    print(f"Net quote flow: {stats['net_quote_flow']:.4f}")
    print(f"Average Fear and Greed: {stats['average_fear']:.2f}")
    print(f"Average action strength: {stats['average_action_strength']:.4f}")


if __name__ == "__main__":
    print_statistics()
