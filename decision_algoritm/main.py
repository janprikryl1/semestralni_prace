from fear_and_grid_wrapper import get_fear_and_greed
from indicator import compute_sma
from price_data import get_price_data


def should_buy():
    prices = get_price_data()
    current_price = prices[-1]

    sma = compute_sma(prices)
    fear = get_fear_and_greed()[-1]['value']

    print(f"Price: {current_price}, SMA: {sma}, Fear: {fear}")

    if fear < 30 and current_price > sma:
        return True

    return False

if __name__ == '__main__':
    print("Should buy?", should_buy())