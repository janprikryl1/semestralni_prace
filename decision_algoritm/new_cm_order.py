import logging
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv
from config_loader import config
from database import save_trade

load_dotenv()
client = Client(api_key=os.getenv("API_KEY"), api_secret=os.getenv("API_SECRET"))

USDC_PER_ORDER = 10.0
SYMBOL = config['trading']['symbol']
MIN_COIN_BALANCE = config['limits']['min_balance']
MIN_NOTIONAL = 5.0
STEP_SIZE = 0.00001

def check_balance(client, asset):
    try:
        info = client.get_asset_balance(asset=asset)
        free_amount = float(info['free'])
        print(f"*** DIAGNOSTIKA ZŮSTATKU: {asset} na Spotu (Dostupné): {free_amount:.4f} {asset} ***")
        if free_amount < MIN_COIN_BALANCE:
             print(f"!!! POZOR: Skript vidí, že dostupný zůstatek {asset} je PŘÍLIŠ NÍZKÝ (méně než {MIN_COIN_BALANCE} {asset}).")
        return free_amount
    except Exception as e:
        print(f"Nepodařilo se získat zůstatek {asset} přes API: {e}")
        return 0.0

def get_balance(client, asset):
    info = client.get_asset_balance(asset=asset)
    return float(info['free'])


def execute_buy(client, symbol, usdc_amount):
    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price'])

    quantity = usdc_amount / price

    logging.info(f"BUY attempt: {symbol}, USDC={usdc_amount}, qty={quantity}, price={price}")
    order = client.order_market_buy(
        symbol=symbol,
        quantity=round(quantity, 6)
    )
    logging.info(f"BUY SUCCESS: {order}")
    save_trade("BUY", symbol, quantity, price, "SUCCESS")
    return order


def execute_sell(client, symbol, btc_amount):
    try:
        quantity = round(btc_amount, 6)

        ticker = client.get_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])

        logging.info(f"SELL attempt: {symbol}, qty={quantity}, price={price}")
        order = client.order_market_sell(
            symbol=symbol,
            quantity=quantity
        )
        logging.info(f"SELL SUCCESS: {order}")
        save_trade("SELL", symbol, quantity, price, "SUCCESS")
        return order

    except BinanceAPIException as e:
        logging.error(f"SELL FAILED: {e}")
        save_trade("SELL", symbol, 0, 0, "ERROR")
        return None

if __name__ == '__main__':
    check_balance(client, 'BNB')
    #execute_experiment()