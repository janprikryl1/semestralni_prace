import json
import urllib.request
from pathlib import Path

BASE_URL = "https://api.serious.broker/internal/trading/fgi_sma_ema/algo-config/?type="

CONFIGS = {
    "sma": Path(__file__).parent / "sma" / "config.json",
    "ema": Path(__file__).parent / "ema" / "config.json",
}

for algo, path in CONFIGS.items():
    with urllib.request.urlopen(BASE_URL + algo) as resp:
        payload = json.loads(resp.read())

    config = payload["data"]
    path.write_text(json.dumps(config, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"[{algo.upper()}] Saved {path}")