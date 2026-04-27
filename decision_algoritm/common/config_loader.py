import json
from pathlib import Path


def load_config(config_path: Path):
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)
