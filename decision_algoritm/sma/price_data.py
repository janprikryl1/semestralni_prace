import os
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv
from config_loader import config
import time
import logging

load_dotenv()

HOURS_BACK = config['trading']['hours_back']


def create_client():
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError("Missing Binance API credentials")

    client = Client(api_key=api_key, api_secret=api_secret, requests_params={"timeout": 20})
    client.timestamp_offset = client.get_server_time()['serverTime'] - int(time.time() * 1000)
    return client


def get_price_data(symbol):
    client = create_client()
    try:
        klines = client.get_historical_klines(
            symbol,
            Client.KLINE_INTERVAL_1HOUR,
            f"{HOURS_BACK} hours ago UTC"
        )
    except BinanceAPIException as exc:
        logging.error("Failed to fetch historical price data: %s", exc)
        return []

    closes = [float(k[4]) for k in klines]
    return closes
