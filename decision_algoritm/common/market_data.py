import logging
import os
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

load_dotenv()


def create_client():
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError("Missing Binance API credentials")

    client = Client(api_key=api_key, api_secret=api_secret, requests_params={"timeout": 20})
    client.timestamp_offset = client.get_server_time()["serverTime"] - int(time.time() * 1000)
    return client


def get_price_data(client, symbol, hours_back):
    try:
        klines = client.get_historical_klines(
            symbol,
            Client.KLINE_INTERVAL_1HOUR,
            f"{hours_back} hours ago UTC",
        )
    except BinanceAPIException as exc:
        logging.error("Failed to fetch historical price data: %s", exc)
        return []

    return [float(item[4]) for item in klines]
