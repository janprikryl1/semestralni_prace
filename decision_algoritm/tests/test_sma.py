import pytest
from sma import compute_sma


def test_compute_sma_returns_average_of_last_period():
    prices = [10, 20, 30, 40, 50]
    result = compute_sma(prices, period=3)
    assert result == 40


def test_compute_sma_raises_for_non_positive_period():
    with pytest.raises(ValueError, match="SMA period must be positive"):
        compute_sma([10, 20, 30], period=0)


def test_compute_sma_raises_when_not_enough_prices():
    with pytest.raises(ValueError, match="Not enough prices to compute SMA"):
        compute_sma([10, 20], period=3)
