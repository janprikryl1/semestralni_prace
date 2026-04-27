import os
import pytest
import requests
from common.fear_and_greed import get_fear_and_greed


def test_get_fear_and_greed_returns_live_data():
    api_key = os.getenv("COINMARKETCAP_API_KEY") or os.getenv("COINMARKETCUP")
    if not api_key:
        pytest.skip("Live CoinMarketCap API key is not configured")

    result = get_fear_and_greed(days=1)
    if result is None:
        pytest.skip("Live CoinMarketCap API is currently unavailable")

    assert isinstance(result, list)
    assert len(result) > 0
    assert "value" in result[0]


def test_get_fear_and_greed_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("COINMARKETCAP_API_KEY", raising=False)
    monkeypatch.delenv("COINMARKETCUP", raising=False)

    assert get_fear_and_greed() is None


def test_get_fear_and_greed_returns_none_on_request_error(monkeypatch):
    monkeypatch.setenv("COINMARKETCAP_API_KEY", "test-key")

    def raise_request_error(*args, **kwargs):
        raise requests.exceptions.RequestException("network error")

    monkeypatch.setattr("common.fear_and_greed.requests.get", raise_request_error)

    assert get_fear_and_greed() is None
