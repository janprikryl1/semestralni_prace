import logging
import numpy as np
import talib

def compute_ema(prices, period):
    if period <= 0:
        raise ValueError("EMA period must be positive")
    if len(prices) < period:
        raise ValueError("Not enough prices to compute EMA")

    ema_values = talib.EMA(np.array(prices, dtype=float), timeperiod=period)
    latest_ema = ema_values[-1]
    if np.isnan(latest_ema):
        logging.warning("EMA returned NaN for the latest value")
        raise ValueError("EMA result is NaN")
    return float(latest_ema)
