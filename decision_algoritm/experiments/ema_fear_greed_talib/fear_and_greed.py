import logging
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_fear_and_greed(days=1):
    api_key = os.getenv("COINMARKETCAP_API_KEY") or os.getenv("COINMARKETCUP")
    if not api_key:
        logging.warning("Missing CoinMarketCap API key for Fear and Greed endpoint")
        return None

    api_url = f"https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical?limit={days}"
    headers = {
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=20)
        data = response.json()
        if response.status_code == 200 and str(data["status"]["error_code"]) == "0":
            logging.info("Fear and Greed response fetched successfully")
            return data["data"]

        error_msg = data.get("status", {}).get("error_message", "Unknown error")
        logging.error("Fear and Greed fetch failed: %s", error_msg)
        return None
    except requests.exceptions.RequestException as exc:
        logging.error("Fear and Greed request error: %s", exc)
        return None
