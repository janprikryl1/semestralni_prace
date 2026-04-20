from unittest.mock import Mock
import pytest
import price_data


def test_create_client_raises_without_credentials(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="Missing Binance API credentials"):
        price_data.create_client()


def test_create_client_sets_timestamp_offset(monkeypatch):
    fake_client = Mock()
    fake_client.get_server_time.return_value = {"serverTime": 5000}
    fake_client.timestamp_offset = None
    client_factory = Mock(return_value=fake_client)

    monkeypatch.setenv("API_KEY", "key")
    monkeypatch.setenv("API_SECRET", "secret")
    monkeypatch.setattr("price_data.Client", client_factory)
    monkeypatch.setattr("price_data.time.time", Mock(return_value=2.0))

    client = price_data.create_client()

    assert client is fake_client
    client_factory.assert_called_once_with(
        api_key="key",
        api_secret="secret",
        requests_params={"timeout": 20},
    )
    assert fake_client.timestamp_offset == 3000