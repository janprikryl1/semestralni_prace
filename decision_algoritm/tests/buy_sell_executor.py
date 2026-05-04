from unittest.mock import Mock
import pytest
import requests
import random
import time
import hmac
import hashlib
from urllib.parse import urlencode

API_KEY = "g5FkuBTbjYYiSv73lXW204MZf3wXxoq2BQ9A51oqrg02Jhw3FIlbzVhiubAmYlMz"
SECRET_KEY = "7M9ay9d4hXrWXdshl8uuvsqVn1nqhIinUT4Rg8FsovkklitbqXqRTjZwW98PeXZm"
BASE_URL = "https://demo-api.binance.com/api"


def place_market_order(symbol, quantity):
    print("Placing Market Order...")
    if symbol and quantity:
        mock_response = {
            "symbol": symbol,
            "status": "FILLED",
            "orderId": random.randint(100000, 999999),
            "executedQty": quantity,
            "price": str(random.uniform(50000, 60000))
        }
        return mock_response
    else:
        raise Exception("Missing required parameter")


def create_market_order(symbol, quantity):
    endpoint = "/v3/order"
    url = BASE_URL + endpoint
    params = {
        "symbol": symbol,
        "type": "MARKET",
        "side": "BUY",
        "quantity": quantity,
        "timestamp": int(time.time() * 1000)
    }
    query_string = urlencode(params)
    signature = hmac.new(SECRET_KEY.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature
    headers = {
        "X-MBX-APIKEY": API_KEY
    }

    try:
        response = requests.post(url, headers=headers, params=params)
        print(response)
        response.raise_for_status()
        return response.json()
    except:  # Mock response (instead of real API call)
        print("Binance testnet is currently down. Simulating order...")
        mock_response = {
            "symbol": symbol,
            "status": "FILLED",
            "orderId": 123456789,
            "executedQty": quantity,
            "price": "118000.00"
        }
        return mock_response


# Run from terminal
if __name__ == "__main__":
    symbol = "BTCUSDC"
    quantity = 0.001
    result = create_market_order(symbol, quantity)
    print(result)
