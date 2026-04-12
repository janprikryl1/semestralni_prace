import os
from dotenv import load_dotenv
import requests

load_dotenv()

def get_fear_and_greed(days=1):
    api_key = os.getenv("COINMARKETCUP")
    if not api_key:
        print("Missing API key")
        quit(-1)

    api_url = f"https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical?limit={days}"

    headers = {
        'X-CMC_PRO_API_KEY': api_key,
        'Accept': 'application/json'
    }

    try:
        response = requests.get(api_url, headers=headers)
        data = response.json()
        print(data)
        if response.status_code == 200 and str(data['status']['error_code']) == "0":
            return data['data']
        else:
            error_msg = data.get('status', {}).get('error_message', 'Unknown error')
            print(f"Nepodařilo se získat data z API: {error_msg}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Chyba při požadavku: {e}")
        return None