import argparse
import logging
import time
from binance.exceptions import BinanceAPIException
from config_loader import config
from database import initialize_db, save_decision
from fear_and_grid_wrapper import get_fear_and_greed
from new_cm_order import create_client, execute_buy, execute_sell, get_balance, get_buy_order_requirements
from price_data import get_price_data
from sma import compute_sma
from logging_init import setup_logging

_KNOWN_QUOTE_ASSETS = ["USDC", "USDT", "BUSD", "TUSD", "BNB", "ETH", "BTC"]

def parse_symbol(symbol: str) -> tuple:
    for quote in _KNOWN_QUOTE_ASSETS:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            if base:
                return base, quote
    raise ValueError(
        f"Cannot determine base/quote from symbol '{symbol}'. "
        f"Known quote assets: {', '.join(_KNOWN_QUOTE_ASSETS)}"
    )


def evaluate_market(symbol):
    prices = get_price_data(symbol)
    if len(prices) < config["indicators"]["sma_period"]:
        logging.warning("Not enough price data for SMA evaluation")
        return {
            "signal": "HOLD",
            "reason": "Insufficient historical price data",
            "price": prices[-1] if prices else 0.0,
            "sma": 0.0,
            "fear": None,
            "strength": 0.0,
        }

    current_price = prices[-1]
    sma = compute_sma(prices, config["indicators"]["sma_period"])
    data = get_fear_and_greed()
    if not data:
        logging.error("Failed to fetch Fear and Greed index")
        return {
            "signal": "HOLD",
            "reason": "Missing Fear and Greed data",
            "price": current_price,
            "sma": sma,
            "fear": None,
            "strength": 0.0,
        }

    fear = int(data[0]['value'])
    trend_up = current_price > sma
    distance_from_sma = abs(current_price - sma) / sma if sma else 0.0
    sentiment_component = 0.0
    signal = "HOLD"
    reason = "Signals are mixed"

    if fear < config["strategy"]["fear_buy_threshold"] and trend_up:
        signal = "BUY"
        sentiment_component = max(0.0, (config["strategy"]["fear_buy_threshold"] - fear) / 100)
        reason = "Bullish trend above SMA with fearful market sentiment"
    elif fear > config["strategy"]["fear_sell_threshold"] and not trend_up:
        signal = "SELL"
        sentiment_component = max(0.0, (fear - config["strategy"]["fear_sell_threshold"]) / 100)
        reason = "Bearish trend below SMA with greedy market sentiment"

    strength = min(1.0, sentiment_component + distance_from_sma)
    logging.info(
        "Signal=%s, price=%.2f, sma=%.2f, fear=%s, strength=%.4f",
        signal,
        current_price,
        sma,
        fear,
        strength,
    )

    return {
        "signal": signal,
        "reason": reason,
        "price": current_price,
        "sma": sma,
        "fear": fear,
        "strength": strength,
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


def run_cycle(symbol, base_asset, quote_asset):
    initialize_db()
    evaluation = evaluate_market(symbol)
    signal = evaluation["signal"]
    position_size = 0.0

    try:
        client = create_client()
        quote_balance = get_balance(client, quote_asset)
        base_balance = get_balance(client, base_asset)
    except (RuntimeError, BinanceAPIException, KeyError, TypeError, ValueError) as exc:
        logging.error("Unable to initialize Binance trading cycle: %s", exc)
        save_decision(
            signal,
            symbol,
            evaluation["price"],
            evaluation["sma"],
            evaluation["fear"],
            evaluation["strength"],
            position_size,
            f"Initialization failed: {exc}"
        )
        return "HOLD"

    logging.info("Balances: %s=%.4f %s=%.8f", quote_asset, quote_balance, base_asset, base_balance)

    if signal == "BUY" and quote_balance > config["limits"]["min_quote_balance"]:
        amount = get_buy_amount(evaluation["fear"], quote_balance)
        position_size = amount

        if amount > 0:
            requirements = get_buy_order_requirements(client, symbol, evaluation["price"])
            if amount >= requirements["required_quote"]:
                logging.info("Executing BUY for %.4f %s", amount, quote_asset)
                execute_buy(client, symbol, amount, quote_asset)
            else:
                logging.warning(
                    "BUY signal generated but computed amount %.4f %s is below exchange minimum %.4f %s",
                    amount,
                    quote_asset,
                    requirements["required_quote"],
                    quote_asset,
                )
        else:
            logging.info("BUY signal generated but computed amount was zero")

    elif signal == "SELL" and base_balance > config["limits"]["min_base_balance"]:
        amount = get_sell_amount(evaluation["fear"], base_balance)
        position_size = amount

        if amount > 0:
            logging.info("Executing SELL for %.8f %s", amount, base_asset)
            execute_sell(client, symbol, amount, quote_asset)
        else:
            logging.info("SELL signal generated but computed amount was zero")

    else:
        logging.info("Holding position for this cycle")

    save_decision(
        signal,
        symbol,
        evaluation["price"],
        evaluation["sma"],
        evaluation["fear"],
        evaluation["strength"],
        position_size,
        evaluation["reason"]
    )
    return signal


def main():
    parser = argparse.ArgumentParser(description="Simple Binance algorithmic trading bot")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single evaluation cycle and exit"
    )
    parser.add_argument(
        "--symbol",
        required=True,
        help="Trading pair symbol, e.g. BTCUSDC or ETHUSDT"
    )
    args = parser.parse_args()

    symbol = args.symbol.upper()
    base_asset, quote_asset = parse_symbol(symbol)
    setup_logging(symbol)
    interval_seconds = config["trading"].get("interval_seconds", 3600)

    if args.once:
        run_cycle(symbol, base_asset, quote_asset)
        return

    while True:
        try:
            run_cycle(symbol, base_asset, quote_asset)
        except Exception as exc:
            logging.exception("Unexpected error in trading loop: %s", exc)
        time.sleep(interval_seconds)


if __name__ == '__main__':
    main()
