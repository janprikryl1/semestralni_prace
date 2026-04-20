import logging
import os
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv
from config_loader import config
from database import save_trade
import time

load_dotenv()

SYMBOL = config['trading']['symbol']
BASE_ASSET = config["trading"].get("base_asset", "BTC")
QUOTE_ASSET = config["trading"].get("quote_asset", "USDC")
MIN_COIN_BALANCE = config['limits']['min_balance']
DRY_RUN = config["trading"].get("dry_run", True)
ORDER_DECIMALS = config["trading"].get("quantity_precision", 6)


def create_client():
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError("Missing Binance API credentials")

    client = Client(api_key=api_key, api_secret=api_secret, requests_params={"timeout": 20})
    client.timestamp_offset = client.get_server_time()['serverTime'] - int(time.time() * 1000)
    return client

def check_balance(client, asset):
    try:
        info = client.get_asset_balance(asset=asset)
        free_amount = float(info['free'])
        if free_amount < MIN_COIN_BALANCE:
            logging.warning("Balance for %s is below minimum threshold: %.8f", asset, free_amount)
        return free_amount
    except Exception as e:
        logging.error("Failed to fetch balance for %s: %s", asset, e)
        return 0.0


def get_balance(client, asset):
    info = client.get_asset_balance(asset=asset)
    return float(info['free'])


def format_quantity(quantity):
    return f"{quantity:.{ORDER_DECIMALS}f}"


def get_symbol_filter_map(client, symbol):
    symbol_info = client.get_symbol_info(symbol)
    if not symbol_info:
        raise RuntimeError(f"Missing symbol info for {symbol}")
    return {item["filterType"]: item for item in symbol_info["filters"]}


def get_lot_size_filter(filters):
    return filters.get("LOT_SIZE") or filters.get("MARKET_LOT_SIZE")


def get_min_notional_filter(filters):
    return filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL")


def get_buy_order_requirements(client, symbol, price):
    filters = get_symbol_filter_map(client, symbol)
    lot_filter = get_lot_size_filter(filters)
    notional_filter = get_min_notional_filter(filters)

    min_qty = Decimal(lot_filter["minQty"]) if lot_filter else Decimal("0")
    step_size = Decimal(lot_filter["stepSize"]) if lot_filter else Decimal("0")
    min_notional = Decimal(notional_filter["minNotional"]) if notional_filter else Decimal("0")
    price_decimal = Decimal(str(price))
    required_qty = min_qty

    if min_notional > 0 and price_decimal > 0:
        raw_qty_for_notional = min_notional / price_decimal
        if step_size > 0:
            required_steps = (raw_qty_for_notional / step_size).to_integral_value(rounding=ROUND_UP)
            qty_for_notional = required_steps * step_size
        else:
            qty_for_notional = raw_qty_for_notional
        required_qty = max(required_qty, qty_for_notional)

    required_quote = required_qty * price_decimal

    return {
        "min_qty": float(min_qty),
        "required_qty": float(required_qty),
        "min_notional": float(min_notional),
        "required_quote": float(required_quote),
    }


def adjust_quantity_to_lot_size(client, symbol, quantity):
    filters = get_symbol_filter_map(client, symbol)
    lot_filter = get_lot_size_filter(filters)
    if not lot_filter:
        return round(quantity, ORDER_DECIMALS)

    quantity_decimal = Decimal(str(quantity))
    min_qty = Decimal(lot_filter["minQty"])
    max_qty = Decimal(lot_filter["maxQty"])
    step_size = Decimal(lot_filter["stepSize"])

    if quantity_decimal < min_qty:
        return 0.0

    adjusted_quantity = quantity_decimal.quantize(step_size, rounding=ROUND_DOWN)
    adjusted_quantity = (adjusted_quantity // step_size) * step_size
    adjusted_quantity = adjusted_quantity.quantize(step_size, rounding=ROUND_DOWN)

    if adjusted_quantity < min_qty:
        return 0.0
    if adjusted_quantity > max_qty:
        adjusted_quantity = max_qty

    return float(adjusted_quantity)


def execute_buy(client, symbol, quote_amount):
    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price'])
    requirements = get_buy_order_requirements(client, symbol, price)

    if quote_amount < requirements["required_quote"]:
        reason = (
            f"Skipped BUY: quote amount {quote_amount:.4f} {QUOTE_ASSET} "
            f"is below exchange minimum {requirements['required_quote']:.4f} {QUOTE_ASSET}"
        )
        logging.warning(reason)
        save_trade("BUY", symbol, 0.0, price, 0.0, "SKIPPED", reason)
        return None

    quantity = quote_amount / price
    quantity = adjust_quantity_to_lot_size(client, symbol, quantity)
    notional = quantity * price
    formatted_quantity = format_quantity(quantity)

    if quantity <= 0:
        reason = "Skipped BUY: computed quantity is below Binance LOT_SIZE minimum"
        logging.warning(reason)
        save_trade("BUY", symbol, quantity, price, notional, "SKIPPED", reason)
        return None

    if requirements["min_notional"] > 0 and notional < requirements["min_notional"]:
        reason = (
            f"Skipped BUY: adjusted notional {notional:.4f} {QUOTE_ASSET} "
            f"is below exchange minimum {requirements['min_notional']:.4f} {QUOTE_ASSET}"
        )
        logging.warning(reason)
        save_trade("BUY", symbol, quantity, price, notional, "SKIPPED", reason)
        return None

    if DRY_RUN:
        logging.info("DRY RUN BUY: %s, %s=%s, qty=%s, price=%s", symbol, QUOTE_ASSET, quote_amount, quantity, price)
        simulated_order = {"mode": "DRY_RUN", "side": "BUY", "symbol": symbol, "quantity": quantity, "price": price}
        save_trade("BUY", symbol, quantity, price, notional, "SIMULATED", str(simulated_order))
        return simulated_order

    try:
        logging.info("BUY attempt: %s, %s=%s, qty=%s, price=%s", symbol, QUOTE_ASSET, quote_amount, quantity, price)
        order = client.order_market_buy(symbol=symbol, quantity=formatted_quantity)
        logging.info("BUY success: %s", order)
        save_trade("BUY", symbol, quantity, price, notional, "SUCCESS", str(order))
        return order
    except BinanceAPIException as exc:
        logging.error("BUY failed: %s", exc)
        save_trade("BUY", symbol, quantity, price, notional, "ERROR", str(exc))
        return None


def execute_sell(client, symbol, base_amount):
    quantity = adjust_quantity_to_lot_size(client, symbol, base_amount)
    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price'])
    requirements = get_buy_order_requirements(client, symbol, price)
    notional = quantity * price
    formatted_quantity = format_quantity(quantity)

    if quantity <= 0:
        reason = "Skipped SELL: computed quantity is below Binance LOT_SIZE minimum"
        logging.warning(reason)
        save_trade("SELL", symbol, quantity, price, notional, "SKIPPED", reason)
        return None

    if requirements["min_notional"] > 0 and notional < requirements["min_notional"]:
        reason = (
            f"Skipped SELL: notional {notional:.4f} {QUOTE_ASSET} "
            f"is below exchange minimum {requirements['min_notional']:.4f} {QUOTE_ASSET}"
        )
        logging.warning(reason)
        save_trade("SELL", symbol, quantity, price, notional, "SKIPPED", reason)
        return None

    if DRY_RUN:
        logging.info("DRY RUN SELL: %s, qty=%s, price=%s", symbol, quantity, price)
        simulated_order = {"mode": "DRY_RUN", "side": "SELL", "symbol": symbol, "quantity": quantity, "price": price}
        save_trade("SELL", symbol, quantity, price, notional, "SIMULATED", str(simulated_order))
        return simulated_order

    try:
        logging.info("SELL attempt: %s, qty=%s, price=%s", symbol, quantity, price)
        order = client.order_market_sell(symbol=symbol, quantity=formatted_quantity)
        logging.info("SELL success: %s", order)
        save_trade("SELL", symbol, quantity, price, notional, "SUCCESS", str(order))
        return order
    except BinanceAPIException as e:
        logging.error("SELL failed: %s", e)
        save_trade("SELL", symbol, quantity, price, notional, "ERROR", str(e))
        return None
