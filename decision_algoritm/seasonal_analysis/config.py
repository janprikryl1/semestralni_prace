import json
import os

COINS = ["BTC", "ETH", "SOL", "XRP", "ADA"]
YEARS = list(range(2021, 2027))

MONTH_STARTS   = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
MONTHS_CZ      = ["Led", "Uno", "Bre", "Dub", "Kve", "Cvn",
                   "Cvc", "Srp", "Zar", "Rij", "Lis", "Pro"]
MONTHS_FULL_CZ = ["Leden", "Unor", "Brezen", "Duben", "Kveten", "Cerven",
                   "Cervenec", "Srpen", "Zari", "Rijen", "Listopad", "Prosinec"]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -- load colors from config.json ------------------------------------------
_cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(_cfg_path, encoding="utf-8") as _f:
    _cfg = json.load(_f)

BG       = _cfg["theme"]["bg"]
CARD_BG  = _cfg["theme"]["card_bg"]
BORDER   = _cfg["theme"]["border"]
TEXT     = _cfg["theme"]["text"]
MUTED    = _cfg["theme"]["muted"]
ZEROLINE = _cfg["theme"]["zeroline"]

COIN_COLORS = _cfg["coin_colors"]
CHART       = _cfg["chart_colors"]
