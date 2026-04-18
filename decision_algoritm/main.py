from fear_and_grid_wrapper import get_fear_and_greed
from new_cm_order import get_balance, client, execute_buy, execute_sell
from sma import compute_sma
from price_data import get_price_data
from config_loader import config
from database import save_trade, save_decision
import logging
import time

logging.basicConfig(
    filename=config['logging']['log_file'],
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

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

def get_buy_amount(fear, usdc_balance, config):
    if fear < 20:
        return usdc_balance * config["risk_management"]["buy_strong"]
    elif fear < 30:
        return usdc_balance * config["risk_management"]["buy_normal"]
    return 0

def get_sell_amount(fear, btc_balance, config):
    if fear > 80:
        return btc_balance * config["risk_management"]["sell_strong"]
    elif fear > 70:
        return btc_balance * config["risk_management"]["sell_normal"]
    return 0



if __name__ == '__main__':
    signal = get_signal()
    symbol = config["trading"]["symbol"]

    usdc = get_balance(client, "USDC")
    btc = get_balance(client, "BTC")

    fear = int(get_fear_and_greed()[0]['value'])

    print(f"Signal: {signal}, USDC: {usdc}, BTC: {btc}")

    if signal == "BUY" and usdc > config["limits"]["min_usdc_balance"]:
        amount = get_buy_amount(fear, usdc, config)

        if amount > 0:
            print(f"Buying for {amount} USDC")
            execute_buy(client, symbol, amount)

    elif signal == "SELL" and btc > config["limits"]["min_btc_balance"]:
        amount = get_sell_amount(fear, btc, config)

        if amount > 0:
            print(f"Selling {amount} BTC")
            execute_sell(client, symbol, amount)

    else:
        print("HOLD")

    time.sleep(3600)  # 1 hour