import importlib.util
import sys
import types
from pathlib import Path


def load_order_executor(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "config_loader",
        types.SimpleNamespace(config={"trading": {"dry_run": False, "quantity_precision": 6}}),
    )
    monkeypatch.setitem(
        sys.modules,
        "database",
        types.SimpleNamespace(save_trade=lambda *args, **kwargs: None),
    )

    path = Path(__file__).resolve().parent.parent / "ema" / "order_executor.py"
    spec = importlib.util.spec_from_file_location("ema_order_executor_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adjust_and_format_uses_step_size_precision(monkeypatch):
    order_executor = load_order_executor(monkeypatch)
    filters = {
        "LOT_SIZE": {
            "minQty": "0.01000000",
            "maxQty": "1000.00000000",
            "stepSize": "0.01000000",
        }
    }

    quantity, formatted_quantity = order_executor._adjust_and_format(filters, 1.239)

    assert quantity == 1.23
    assert formatted_quantity == "1.23"


def test_adjust_and_format_handles_whole_unit_steps(monkeypatch):
    order_executor = load_order_executor(monkeypatch)
    filters = {
        "LOT_SIZE": {
            "minQty": "1.00000000",
            "maxQty": "1000000.00000000",
            "stepSize": "1.00000000",
        }
    }

    quantity, formatted_quantity = order_executor._adjust_and_format(filters, 42.9)

    assert quantity == 42.0
    assert formatted_quantity == "42"
