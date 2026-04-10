def compute_sma(prices, period=14):
    return sum(prices[-period:]) / period