import argparse
import logging
import time
from config_loader import config
from database import save_decision
from ema_indicator import compute_ema
from fear_and_greed import get_fear_and_greed
from market_data import create_client, get_price_data
from order_executor import BASE_ASSET, QUOTE_ASSET, execute_buy, execute_sell, get_balance, get_buy_order_requirements
from logging_init import setup_logging

def evaluate_market(client):
    prices = get_price_data(client)
    ema_period = config["indicators"]["ema_period"]

    if len(prices) < ema_period:
        return {
            "signal": "HOLD",
            "reason": "Insufficient historical price data",
            "price": prices[-1] if prices else 0.0,
            "ema": 0.0,
            "fear": None,
        }

    current_price = prices[-1]
    ema = compute_ema(prices, ema_period)
    fear_data = get_fear_and_greed()

    if not fear_data:
        return {
            "signal": "HOLD",
            "reason": "Missing Fear and Greed data",
            "price": current_price,
            "ema": ema,
            "fear": None,
        }

    fear = int(fear_data[0]["value"])

    if current_price > ema and fear < config["strategy"]["fear_buy_threshold"]:
        signal = "BUY"
        reason = "Price is above EMA and market sentiment is fearful"
    elif current_price < ema and fear > config["strategy"]["fear_sell_threshold"]:
        signal = "SELL"
        reason = "Price is below EMA and market sentiment is greedy"
    else:
        signal = "HOLD"
        reason = "EMA trend and sentiment are not aligned"

    logging.info("Signal=%s, price=%.2f, ema=%.2f, fear=%s", signal, current_price, ema, fear)
    return {
        "signal": signal,
        "reason": reason,
        "price": current_price,
        "ema": ema,
        "fear": fear,
    }


def interpolate_size(value, start, end, start_size, end_size):
    if start == end:
        return end_size

    ratio = (value - start) / (end - start)
    ratio = max(0.0, min(1.0, ratio))
    return start_size + ratio * (end_size - start_size)


def get_buy_amount(fear, quote_balance):
    if fear is None:
        return 0.0
    risk_config = config["risk_management"]
    strategy_config = config["strategy"]
    strong_threshold = risk_config["buy_strong_fear_threshold"]
    normal_threshold = risk_config["buy_normal_fear_threshold"]
    buy_threshold = strategy_config["fear_buy_threshold"]
    strong_size = risk_config["buy_strong"]
    normal_size = risk_config["buy_normal"]

    if fear < strong_threshold:
        return quote_balance * strong_size
    if fear < normal_threshold:
        return quote_balance * normal_size
    if fear >= buy_threshold:
        return 0.0

    size_fraction = interpolate_size(
        fear,
        normal_threshold,
        buy_threshold,
        normal_size,
        0.0,
    )
    return quote_balance * size_fraction


def get_sell_amount(fear, base_balance):
    if fear is None:
        return 0.0
    risk_config = config["risk_management"]
    strategy_config = config["strategy"]
    sell_threshold = strategy_config["fear_sell_threshold"]
    normal_threshold = risk_config["sell_normal_fear_threshold"]
    strong_threshold = risk_config["sell_strong_fear_threshold"]
    normal_size = risk_config["sell_normal"]
    strong_size = risk_config["sell_strong"]

    if fear > strong_threshold:
        return base_balance * strong_size
    if fear > normal_threshold:
        return base_balance * normal_size
    if fear <= sell_threshold:
        return 0.0

    size_fraction = interpolate_size(
        fear,
        sell_threshold,
        normal_threshold,
        0.0,
        normal_size,
    )
    return base_balance * size_fraction


def run_cycle():
    client = create_client()
    evaluation = evaluate_market(client)
    signal = evaluation["signal"]
    symbol = config["trading"]["symbol"]
    position_size = 0.0

    quote_balance = get_balance(client, QUOTE_ASSET)
    base_balance = get_balance(client, BASE_ASSET)
    logging.info("Balances: %s=%.4f %s=%.8f", QUOTE_ASSET, quote_balance, BASE_ASSET, base_balance)

    if signal == "BUY" and quote_balance > config["limits"]["min_quote_balance"]:
        amount = get_buy_amount(evaluation["fear"], quote_balance)
        position_size = amount
        if amount > 0:
            requirements = get_buy_order_requirements(client, symbol, evaluation["price"])
            if amount >= requirements["required_quote"]:
                logging.info("Executing BUY for %.4f %s", amount, QUOTE_ASSET)
                execute_buy(client, symbol, amount)
            else:
                logging.warning(
                    "BUY signal generated but computed amount %.4f %s is below exchange minimum %.4f %s",
                    amount,
                    QUOTE_ASSET,
                    requirements["required_quote"],
                    QUOTE_ASSET,
                )
        else:
            logging.info("BUY signal generated but computed amount was zero")
    elif signal == "SELL" and base_balance > config["limits"]["min_base_balance"]:
        amount = get_sell_amount(evaluation["fear"], base_balance)
        position_size = amount
        if amount > 0:
            logging.info("Executing SELL for %.8f %s", amount, BASE_ASSET)
            execute_sell(client, symbol, amount)
    else:
        logging.info("Holding position for this cycle")

    save_decision(
        signal,
        evaluation["price"],
        evaluation["ema"],
        evaluation["fear"],
        position_size,
        evaluation["reason"],
    )


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="EMA + Fear and Greed trading bot")
    parser.add_argument("--once", action="store_true", help="Run a single evaluation cycle and exit")
    args = parser.parse_args()

    interval_seconds = config["trading"].get("interval_seconds", 3600)

    if args.once:
        run_cycle()
        return

    while True:
        try:
            run_cycle()
        except Exception as exc:
            logging.exception("Unexpected error in trading loop: %s", exc)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
