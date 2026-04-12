from fear_and_grid_wrapper import get_fear_and_greed
from sma import compute_sma
from price_data import get_price_data
import logging
import sqlite3
import datetime
import json

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

config = load_config()

logging.basicConfig(
    filename=config['logging']['log_file'],
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

conn = sqlite3.connect(config['database']['db_file'])
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS decisions (
    time TEXT,
    signal TEXT,
    price REAL,
    sma REAL,
    fear INTEGER
)
""")

def save_decision(signal, price, sma, fear):
    conn = sqlite3.connect(config['database']['db_file'])
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO decisions VALUES (?, ?, ?, ?, ?)
    """, (datetime.datetime.now(), signal, price, sma, fear))

    conn.commit()
    conn.close()

def get_signal():
    prices = get_price_data()
    if len(prices) < config["indicators"]["sma_period"]:
        logging.warning("Not enough data for SMA")
        return "HOLD"

    current_price = prices[-1]
    # Technical analysis
    sma = compute_sma(prices, config["indicators"]["sma_period"])
    # Fundamental analysis
    data = get_fear_and_greed()
    if not data:
        logging.error("Failed to fetch Fear & Greed index")
        return "HOLD"

    fear = int(data[0]['value'])

    if fear < config["strategy"]["fear_buy_threshold"] and current_price > sma:
        signal = "BUY"
    elif fear > config["strategy"]["fear_sell_threshold"] and current_price < sma:
        signal = "SELL"
    else:
        signal = "HOLD"

    logging.info(f"Signal={signal}, price={current_price}, sma={sma}, fear={fear}")
    save_decision(signal, current_price, sma, fear)

    return signal

if __name__ == '__main__':
    signal = get_signal()

    print("SIGNAL:", signal)

    if signal == "BUY":
        print("Nakupuju...")
        # execute_buy()

    elif signal == "SELL":
        print("Prodávám...")
        # execute_sell()

    else:
        print("Nedělám nic")