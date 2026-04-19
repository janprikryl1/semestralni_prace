from pathlib import Path

import matplotlib.pyplot as plt

from database_loader import load_decisions, load_trades


OUTPUT_PATH = Path(__file__).resolve().parent / "evaluation_plot.png"


def build_plot(output_path=OUTPUT_PATH):
    decisions = load_decisions()
    trades = load_trades()

    if not decisions:
        raise RuntimeError("No decision data available for plotting")

    decision_times = [item["time"] for item in decisions]
    prices = [item["price"] for item in decisions]
    sma_values = [item["sma"] for item in decisions]

    buy_points = [item for item in trades if item["side"] == "BUY" and item["status"] == "SUCCESS"]
    sell_points = [item for item in trades if item["side"] == "SELL" and item["status"] == "SUCCESS"]

    figure, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)

    axes[0].plot(decision_times, prices, label="Price", color="#1f77b4", linewidth=2)
    axes[0].plot(decision_times, sma_values, label="SMA", color="#ff7f0e", linestyle="--", linewidth=1.8)

    if buy_points:
        axes[0].scatter(
            [item["time"] for item in buy_points],
            [item["price"] for item in buy_points],
            label="BUY",
            color="green",
            marker="^",
            s=100,
        )
    if sell_points:
        axes[0].scatter(
            [item["time"] for item in sell_points],
            [item["price"] for item in sell_points],
            label="SELL",
            color="red",
            marker="v",
            s=100,
        )

    axes[0].set_title("Strategy Price and Trade Overview")
    axes[0].set_ylabel("Price")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].plot(
        decision_times,
        [item["fear"] if item["fear"] is not None else 0 for item in decisions],
        label="Fear and Greed",
        color="#9467bd",
        linewidth=2,
    )
    axes[1].plot(
        decision_times,
        [item["action_strength"] if item["action_strength"] is not None else 0 for item in decisions],
        label="Action strength",
        color="#2ca02c",
        linewidth=2,
    )
    axes[1].set_title("Sentiment and Signal Strength")
    axes[1].set_ylabel("Value")
    axes[1].set_xlabel("Time")
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    figure.savefig(output_path, dpi=150)
    return output_path


if __name__ == "__main__":
    output_file = build_plot()
    print(f"Plot saved to: {output_file}")
