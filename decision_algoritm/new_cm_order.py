import os
import math
import time
import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

load_dotenv()

from config_loader import config

client = Client(api_key=os.getenv("API_KEY"), api_secret=os.getenv("API_SECRET"))

USDC_PER_ORDER = 10.0 # Tato hodnota by mohla být v risk_management, ponechávám prozatím jako default nebo ji vytáhněte z configu
SYMBOL = config['trading']['symbol']
MIN_USDC_BALANCE = config['limits']['min_usdc_balance']
MIN_NOTIONAL = 5.0
STEP_SIZE = 0.00001

def check_usdc_balance(client):
    try:
        info = client.get_asset_balance(asset='USDC')
        free_usdc = float(info['free'])
        print(f"*** DIAGNOSTIKA ZŮSTATKU: USDC na Spotu (Dostupné): {free_usdc:.4f} USDC ***")
        if free_usdc < MIN_USDC_BALANCE:
             print(f"!!! POZOR: Skript vidí, že dostupný zůstatek USDC je PŘÍLIŠ NÍZKÝ (méně než {MIN_USDC_BALANCE} USDC).")
        return free_usdc
    except Exception as e:
        print(f"Nepodařilo se získat zůstatek USDC přes API: {e}")
        return 0.0

def format_quantity(qty_float, step_size): # Zaokrouhlí a naformátuje množství na string podle STEP_SIZE, aby se zabránilo e-notaci.
    decimals = int(round(-math.log10(step_size)))
    formatted_qty = f"{qty_float:.8f}" 
    return formatted_qty.rstrip('0').rstrip('.')

def convert_ms_to_datetime(timestamp_ms): # Převede časové razítko z ms na čitelný formát H:M:S.ms
    if not timestamp_ms:
        return "N/A"
    return datetime.datetime.fromtimestamp(timestamp_ms / 1000.0, tz=datetime.timezone.utc).strftime('%H:%M:%S.%f')[:-3] + " UTC"


def execute_experiment():
    print("--- Příprava dat ---")
    
    ticker = client.get_symbol_ticker(symbol=SYMBOL)
    current_price = float(ticker['price'])
    print(f"Aktuální {SYMBOL} cena: {current_price:.2f} USDC")

    # Výpočet potřebného množství a zaokrouhlení
    qty_needed_float = USDC_PER_ORDER / current_price
    steps = math.ceil(qty_needed_float / STEP_SIZE)
    qty_to_buy = steps * STEP_SIZE
    quantity_str = format_quantity(qty_to_buy, STEP_SIZE)
    print(f"Quantity pro každou objednávku: {quantity_str} BTC (~{qty_to_buy * current_price:.2f} USDC)")

    # Definování limitních cen pro Taker a Maker
    taker_limit_price = round(current_price * 1.05, 2)
    maker_limit_price = round(current_price * 0.99, 2)
    
    print(f"Limitní cena Taker (okamžité vyplnění): {taker_limit_price:.2f}")
    print(f"Limitní cena Maker (čeká na vyplnění): {maker_limit_price:.2f}")

    results = {}
    
    print("\n--- Spouštění Objednávek ---")

    # 1. Market Taker Order
    try:
        print("1. Odesílání Market Buy...")
        market_order = client.order_market_buy(
            symbol=SYMBOL,
            quantity=quantity_str
        )
        # Použijeme transactTime jako čas zadání
        market_order['submissionTime'] = market_order.get('transactTime')
        results['Market Taker'] = market_order
    except BinanceAPIException as e:
        print(f"Chyba Market Order: {e}")
        
    # 2. Limit Taker Order
    try:
        print("2. Odesílání Limit Taker Buy...")
        limit_taker_order = client.order_limit_buy(
            symbol=SYMBOL,
            quantity=quantity_str,
            price=f"{taker_limit_price:.2f}"
        )
        limit_taker_order['submissionTime'] = limit_taker_order.get('transactTime')
        results['Limit Taker'] = limit_taker_order
    except BinanceAPIException as e:
        print(f"Chyba Limit Taker Order: {e}")

    # 3. Limit Maker Order
    time.sleep(1) 
    """try:
        print("3. Odesílám Limit Maker Buy...")
        limit_maker_order = client.order_limit_buy(
            symbol=SYMBOL,
            quantity=quantity_str,
            price=f"{maker_limit_price:.2f}"
        )
        limit_maker_order['submissionTime'] = limit_maker_order.get('transactTime')
        results['Limit Maker'] = limit_maker_order
    except BinanceAPIException as e:
        print(f"Chyba Limit Maker Order: {e}")"""

    print("\n--- Vyhodnocení obchodu a poplatků ---")
    
    final_evaluation = []
    #maker_order_id = None # Pro uložení ID maker objednávky

    for name, order in results.items():
        if 'orderId' not in order:
            continue
            
        submission_time_ms = order.get('submissionTime') # Čas zadání (ms)
        
        # Získání detailů obchodu
        trades = client.get_my_trades(symbol=SYMBOL, orderId=order['orderId'])

        # --- Robustní obsluha pro NEVYPLNĚNÉ objednávky (např. Maker) ---
        if not trades:
            #maker_order_id = order['orderId']
            
            final_evaluation.append({
                "Typ": name,
                "ID Objednávky": order['orderId'],
                "Získané BTC": "0.00000000",
                "Utracené USDC": "0.0000",
                "Efektivní Cena (USDC/BTC)": "NEVYPLNĚNO",
                "Poplatek": "0.00000000 N/A",
                "Zadání Příkazu (UTC)": convert_ms_to_datetime(submission_time_ms),
                "Vyplnění Příkazu (UTC)": "NEVYPLNĚNO",
                "Latency (ms)": "N/A"
            })
            continue

        # --- Výpočet pro VYPLNĚNÉ objednávky ---
        
        # Čas vyplnění je čas prvního (nebo jediného) obchodu
        fill_time_ms = float(trades[0]['time'])
        latency_ms = fill_time_ms - submission_time_ms
        
        total_btc_bought = sum(float(trade['qty']) for trade in trades)
        total_usdc_spent = sum(float(trade['quoteQty']) for trade in trades)
        total_commission = sum(float(trade['commission']) for trade in trades)
        commission_asset = trades[0]['commissionAsset']
        
        effective_price = total_usdc_spent / total_btc_bought

        final_evaluation.append({
            "Typ": name,
            "ID Objednávky": order['orderId'],
            "Získané BTC": f"{total_btc_bought:.8f}",
            "Utracené USDC": f"{total_usdc_spent:.4f}",
            "Efektivní Cena (USDC/BTC)": f"{effective_price:.2f}",
            "Poplatek": f"{total_commission:.8f} {commission_asset}",
            "Zadání Příkazu (UTC)": convert_ms_to_datetime(submission_time_ms),
            "Vyplnění Příkazu (UTC)": convert_ms_to_datetime(fill_time_ms),
            "Latency (ms)": f"{latency_ms:.0f}"
        })

    
    print("\n")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------------------------")
    print(f"| {'Typ':<15} | {'Zadání Příkazu (UTC)':<22} | {'Vyplnění Příkazu (UTC)':<22} | {'Latency (ms)':<15} | {'Získané BTC':<15} | {'Utracené USDC':<15} | {'Efektivní Cena (USDC/BTC)':<26} | {'Poplatek':<20} |")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------------------------")
    for item in final_evaluation:
        print(f"| {item['Typ']:<15} | {item['Zadání Příkazu (UTC)']:<22} | {item['Vyplnění Příkazu (UTC)']:<22} | {item['Latency (ms)']:<15} | {item['Získané BTC']:<15} | {item['Utracené USDC']:<15} | {item['Efektivní Cena (USDC/BTC)']:<26} | {item['Poplatek']:<20} |")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------------------------")

    print("\n")
    print("--- Vyhodnocení ---")
    print("Efektivně nejvýhodnější je ten obchod, kde je 'Efektivní Cena (USDC/BTC)' nejnižší (menší cena za 1 BTC).")
    
    """if maker_order_id:
        print(f"\nPOZOR: Limit Maker objednávka (ID: {maker_order_id}) je stále OTEVŘENÁ.")
        try:
            client.cancel_order(symbol=SYMBOL, orderId=maker_order_id)
            print("=> Objednávka byla úspěšně zrušena.")
        except BinanceAPIException as e:
            print(f"=> CHYBA při rušení objednávky: {e}")"""


if __name__ == '__main__':
    check_usdc_balance(client)
    execute_experiment()