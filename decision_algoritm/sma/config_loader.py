from pathlib import Path
from common.config_loader import load_config

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

config = load_config(CONFIG_PATH)
