def compute_sma(prices, period=14):
    if period <= 0:
        raise ValueError("SMA period must be positive")
    if len(prices) < period:
        raise ValueError("Not enough prices to compute SMA")
    return sum(prices[-period:]) / period
