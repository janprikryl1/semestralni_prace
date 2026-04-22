import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


config = load_config()
