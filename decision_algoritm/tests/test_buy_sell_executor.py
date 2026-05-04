import pytest
from unittest.mock import patch, MagicMock
import buy_sell_executor as executor


def _make_response(status_code: int, json_data: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = Exception(
            f"HTTP Error {status_code}"
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


SYMBOL = "BTCUSDC"
QUANTITY = 0.001

BINANCE_SUCCESS_PAYLOAD = {
    "symbol": SYMBOL,
    "orderId": 1470492054,
    "orderListId": -1,
    "clientOrderId": "iFXO0fDMJBjMkHmQgjKbmC",
    "transactTime": 1746355200000,
    "price": "0.00000000",
    "origQty": str(QUANTITY),
    "executedQty": str(QUANTITY),
    "cummulativeQuoteQty": "118.00",
    "status": "FILLED",
    "timeInForce": "GTC",
    "type": "MARKET",
    "side": "BUY",
    "selfTradePreventionMode": "EXPIRE_MAKER",
}

class TestPlaceMarketOrder:
    def test_returns_dict_with_correct_symbol(self):
        result = executor.place_market_order(SYMBOL, QUANTITY)
        assert result["symbol"] == SYMBOL

    def test_returns_dict_with_correct_quantity(self):
        result = executor.place_market_order(SYMBOL, QUANTITY)
        assert result["executedQty"] == QUANTITY

    def test_status_is_filled(self):
        result = executor.place_market_order(SYMBOL, QUANTITY)
        assert result["status"] == "FILLED"

    def test_order_id_is_int(self):
        result = executor.place_market_order(SYMBOL, QUANTITY)
        assert isinstance(result["orderId"], int)

    def test_price_is_string(self):
        result = executor.place_market_order(SYMBOL, QUANTITY)
        assert isinstance(result["price"], str)

    def test_price_is_numeric_string(self):
        result = executor.place_market_order(SYMBOL, QUANTITY)
        assert float(result["price"]) > 0

    def test_missing_symbol_raises(self):
        with pytest.raises(Exception, match="Missing required parameter"):
            executor.place_market_order("", QUANTITY)

    def test_missing_quantity_raises(self):
        with pytest.raises(Exception, match="Missing required parameter"):
            executor.place_market_order(SYMBOL, 0)



class TestCreateMarketOrderSuccess:
    @patch("buy_sell_executor.requests.post")
    def test_returns_json_from_api(self, mock_post):
        mock_post.return_value = _make_response(200, BINANCE_SUCCESS_PAYLOAD)

        result = executor.create_market_order(SYMBOL, QUANTITY)

        assert result == BINANCE_SUCCESS_PAYLOAD

    @patch("buy_sell_executor.requests.post")
    def test_symbol_in_response(self, mock_post):
        mock_post.return_value = _make_response(200, BINANCE_SUCCESS_PAYLOAD)

        result = executor.create_market_order(SYMBOL, QUANTITY)

        assert result["symbol"] == SYMBOL

    @patch("buy_sell_executor.requests.post")
    def test_status_filled(self, mock_post):
        mock_post.return_value = _make_response(200, BINANCE_SUCCESS_PAYLOAD)

        result = executor.create_market_order(SYMBOL, QUANTITY)

        assert result["status"] == "FILLED"

    @patch("buy_sell_executor.requests.post")
    def test_post_called_once(self, mock_post):
        mock_post.return_value = _make_response(200, BINANCE_SUCCESS_PAYLOAD)

        executor.create_market_order(SYMBOL, QUANTITY)

        mock_post.assert_called_once()

    @patch("buy_sell_executor.requests.post")
    def test_post_called_with_correct_url(self, mock_post):
        mock_post.return_value = _make_response(200, BINANCE_SUCCESS_PAYLOAD)

        executor.create_market_order(SYMBOL, QUANTITY)

        call_kwargs = mock_post.call_args
        assert executor.BASE_URL + "/v3/order" == call_kwargs[0][0]

    @patch("buy_sell_executor.requests.post")
    def test_api_key_header_present(self, mock_post):
        mock_post.return_value = _make_response(200, BINANCE_SUCCESS_PAYLOAD)

        executor.create_market_order(SYMBOL, QUANTITY)

        headers = mock_post.call_args[1]["headers"]
        assert headers["X-MBX-APIKEY"] == executor.API_KEY

    @patch("buy_sell_executor.requests.post")
    def test_params_contain_side_buy(self, mock_post):
        mock_post.return_value = _make_response(200, BINANCE_SUCCESS_PAYLOAD)

        executor.create_market_order(SYMBOL, QUANTITY)

        params = mock_post.call_args[1]["params"]
        assert params["side"] == "BUY"

    @patch("buy_sell_executor.requests.post")
    def test_params_contain_type_market(self, mock_post):
        mock_post.return_value = _make_response(200, BINANCE_SUCCESS_PAYLOAD)

        executor.create_market_order(SYMBOL, QUANTITY)

        params = mock_post.call_args[1]["params"]
        assert params["type"] == "MARKET"

class TestCreateMarketOrderFallback:
    @patch("buy_sell_executor.requests.post")
    def test_fallback_on_http_error(self, mock_post):
        """Return mock response when HTTP 400"""
        mock_post.return_value = _make_response(400, {"code": -1100, "msg": "Bad request"})

        result = executor.create_market_order(SYMBOL, QUANTITY)

        assert result["symbol"] == SYMBOL
        assert result["status"] == "FILLED"

    @patch("buy_sell_executor.requests.post")
    def test_fallback_on_network_error(self, mock_post):
        """Network error"""
        mock_post.side_effect = ConnectionError("Network unreachable")

        result = executor.create_market_order(SYMBOL, QUANTITY)

        assert result["status"] == "FILLED"
        assert result["symbol"] == SYMBOL

    @patch("buy_sell_executor.requests.post")
    def test_fallback_quantity_matches_input(self, mock_post):
        mock_post.side_effect = ConnectionError("Network unreachable")

        result = executor.create_market_order(SYMBOL, QUANTITY)

        assert result["executedQty"] == QUANTITY

    @patch("buy_sell_executor.requests.post")
    def test_fallback_has_order_id(self, mock_post):
        mock_post.side_effect = ConnectionError("Network unreachable")

        result = executor.create_market_order(SYMBOL, QUANTITY)

        assert "orderId" in result
        assert isinstance(result["orderId"], int)
