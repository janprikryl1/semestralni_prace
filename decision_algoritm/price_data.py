import os
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv
import json

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

load_dotenv()
client = Client(api_key=os.getenv("API_KEY"), api_secret=os.getenv("API_SECRET"))
config = load_config()
SYMBOL = config['trading']['symbol']

def get_price_data():
    klines = client.get_historical_klines(SYMBOL, Client.KLINE_INTERVAL_1HOUR, "100 hours ago UTC")

    closes = [float(k[4]) for k in klines]
    return closes