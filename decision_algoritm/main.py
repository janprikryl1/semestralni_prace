import argparse
import datetime
import logging
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from binance.exceptions import BinanceAPIException
from config_loader import config
from database import initialize_db, save_decision
from fear_and_grid_wrapper import get_fear_and_greed
from new_cm_order import create_client, execute_buy, execute_sell, get_balance
from price_data import get_price_data
from sma import compute_sma

BASE_ASSET = config["trading"].get("base_asset", "BTC")
QUOTE_ASSET = config["trading"].get("quote_asset", "USDC")
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


def setup_logging():
    logging_config = config["logging"]
    logs_dir = Path(logging_config.get("log_dir", "logs"))
    logs_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, logging_config.get("level", "INFO").upper(), logging.INFO))
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)

    combined_log_path = logs_dir / logging_config.get("combined_log_file", "old.log")
    combined_handler = TimedRotatingFileHandler(
        combined_log_path,
        when="midnight",
        interval=1,
        backupCount=logging_config.get("backup_count", 14),
        encoding="utf-8"
    )
    combined_handler.setFormatter(formatter)

    session_timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    session_log_name = logging_config.get("session_log_template", "run-{timestamp}.log").format(
        timestamp=session_timestamp
    )
    session_handler = logging.FileHandler(logs_dir / session_log_name, encoding="utf-8")
    session_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger.addHandler(combined_handler)
    root_logger.addHandler(session_handler)
    root_logger.addHandler(console_handler)


def evaluate_market():
    prices = get_price_data()
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
        strength
    )

    return {
        "signal": signal,
        "reason": reason,
        "price": current_price,
        "sma": sma,
        "fear": fear,
        "strength": strength,
    }


def get_buy_amount(fear, quote_balance):
    if fear is None:
        return 0.0
    if fear < 20:
        return quote_balance * config["risk_management"]["buy_strong"]
    if fear < 30:
        return quote_balance * config["risk_management"]["buy_normal"]
    return quote_balance * max(0.0, min(config["risk_management"]["buy_normal"], (50 - fear) / 100))


def get_sell_amount(fear, base_balance):
    if fear is None:
        return 0.0
    if fear > 80:
        return base_balance * config["risk_management"]["sell_strong"]
    if fear > 70:
        return base_balance * config["risk_management"]["sell_normal"]
    return base_balance * max(config["risk_management"]["sell_normal"], max(0.0, (fear - 50) / 100))


def run_cycle():
    initialize_db()
    evaluation = evaluate_market()
    signal = evaluation["signal"]
    symbol = config["trading"]["symbol"]
    position_size = 0.0

    try:
        client = create_client()
        quote_balance = get_balance(client, QUOTE_ASSET)
        base_balance = get_balance(client, BASE_ASSET)
    except (RuntimeError, BinanceAPIException, KeyError, TypeError, ValueError) as exc:
        logging.error("Unable to initialize Binance trading cycle: %s", exc)
        save_decision(
            signal,
            evaluation["price"],
            evaluation["sma"],
            evaluation["fear"],
            evaluation["strength"],
            position_size,
            f"Initialization failed: {exc}"
        )
        return "HOLD"

    logging.info("Balances: %s=%.4f %s=%.8f", QUOTE_ASSET, quote_balance, BASE_ASSET, base_balance)

    if signal == "BUY" and quote_balance > config["limits"]["min_quote_balance"]:
        amount = get_buy_amount(evaluation["fear"], quote_balance)
        position_size = amount

        if amount > 0:
            logging.info("Executing BUY for %.4f %s", amount, QUOTE_ASSET)
            execute_buy(client, symbol, amount)
        else:
            logging.info("BUY signal generated but computed amount was zero")

    elif signal == "SELL" and base_balance > config["limits"]["min_base_balance"]:
        amount = get_sell_amount(evaluation["fear"], base_balance)
        position_size = amount

        if amount > 0:
            logging.info("Executing SELL for %.8f %s", amount, BASE_ASSET)
            execute_sell(client, symbol, amount)
        else:
            logging.info("SELL signal generated but computed amount was zero")

    else:
        logging.info("Holding position for this cycle")

    save_decision(
        signal,
        evaluation["price"],
        evaluation["sma"],
        evaluation["fear"],
        evaluation["strength"],
        position_size,
        evaluation["reason"]
    )
    return signal


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Simple Binance algorithmic trading bot")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single evaluation cycle and exit"
    )
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


if __name__ == '__main__':
    main()
