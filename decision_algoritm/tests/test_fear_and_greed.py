from unittest.mock import Mock

import requests

from fear_and_grid_wrapper import get_fear_and_greed


def test_get_fear_and_greed_returns_data_on_success(monkeypatch):
    expected_data = [{"value": "42", "value_classification": "Fear"}]
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "status": {"error_code": 0},
        "data": expected_data,
    }

    monkeypatch.setenv("COINMARKETCAP_API_KEY", "test-key")
    requests_get_mock = Mock(return_value=response)
    monkeypatch.setattr("fear_and_grid_wrapper.requests.get", requests_get_mock)

    result = get_fear_and_greed(days=3)

    assert result == expected_data
    requests_get_mock.assert_called_once_with(
        "https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical?limit=3",
        headers={
            "X-CMC_PRO_API_KEY": "test-key",
            "Accept": "application/json",
        },
        timeout=20,
    )


def test_get_fear_and_greed_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("COINMARKETCAP_API_KEY", raising=False)
    monkeypatch.delenv("COINMARKETCUP", raising=False)

    assert get_fear_and_greed() is None


def test_get_fear_and_greed_returns_none_on_request_error(monkeypatch):
    monkeypatch.setenv("COINMARKETCAP_API_KEY", "test-key")

    def raise_request_error(*args, **kwargs):
        raise requests.exceptions.RequestException("network error")

    monkeypatch.setattr("fear_and_grid_wrapper.requests.get", raise_request_error)

    assert get_fear_and_greed() is None
