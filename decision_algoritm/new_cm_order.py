import logging
import os
from decimal import Decimal, ROUND_DOWN
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


def adjust_quantity_to_lot_size(client, symbol, quantity):
    filters = get_symbol_filter_map(client, symbol)
    lot_filter = filters.get("LOT_SIZE") or filters.get("MARKET_LOT_SIZE")
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
    quantity = quote_amount / price
    quantity = adjust_quantity_to_lot_size(client, symbol, quantity)
    notional = quantity * price
    formatted_quantity = format_quantity(quantity)

    if quantity <= 0:
        reason = "Skipped BUY: computed quantity is below Binance LOT_SIZE minimum"
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
    notional = quantity * price
    formatted_quantity = format_quantity(quantity)

    if quantity <= 0:
        reason = "Skipped SELL: computed quantity is below Binance LOT_SIZE minimum"
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