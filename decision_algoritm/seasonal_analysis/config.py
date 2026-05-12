import json
import os
import matplotlib.patches as mpatches

COINS = ["BTC", "ETH", "SOL", "XRP", "ADA"]
YEARS = list(range(2021, 2027))

MONTH_STARTS = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
MONTHS_CZ = ["Led", "Uno", "Bre", "Dub", "Kve", "Cvn", "Cvc", "Srp", "Zar", "Rij", "Lis", "Pro"]
MONTHS_FULL_CZ = ["Leden", "Unor", "Brezen", "Duben", "Kveten", "Cerven", "Cervenec", "Srpen", "Zari", "Rijen", "Listopad", "Prosinec"]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# load colors from config.json
_cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(_cfg_path, encoding="utf-8") as _f:
    _cfg = json.load(_f)

BG = _cfg["theme"]["bg"]
CARD_BG = _cfg["theme"]["card_bg"]
BORDER = _cfg["theme"]["border"]
TEXT = _cfg["theme"]["text"]
MUTED = _cfg["theme"]["muted"]
ZEROLINE = _cfg["theme"]["zeroline"]

COIN_COLORS = _cfg["coin_colors"]
CHART = _cfg["chart_colors"]

CHART_DESCRIPTIONS = {
    1: "Prumerny sezonni vzor",
    2: "Překrytí všech let (kazda cara = jeden rok)",
    3: "Elbow + Silhouette pro vyber poctu clusteru",
    4: "Heatmapa trzniho rezimu (rok x den, K-Means)",
    5: "Zastoupeni rezimu v prubehu roku",
    6: "Korelace sezonniho vzoru mezi roky (Pearson)",
    7: "Mesicni doporuceni s hvezdickovym hodnocenim",
}

THRESHOLDS = [
    (-10, CHART["bar_very_below"]),
    ( -3, CHART["bar_below"]),
    (  3, CHART["bar_neutral"]),
    ( 15, CHART["bar_above"]),
]

legend_items = [
    mpatches.Patch(color=CHART["bar_very_below"], label="Výrazně podprůměrný"),
    mpatches.Patch(color=CHART["bar_below"], label="Podprůměrný"),
    mpatches.Patch(color=CHART["bar_neutral"], label="Průměrný"),
    mpatches.Patch(color=CHART["bar_above"], label="Nadprůměrný"),
    mpatches.Patch(color=CHART["bar_very_above"], label="Výrazně nadprůměrný"),
]

ADVICES = {
    1: ("[1/5]", "Výrazně podprůměrné"),
    2: ("[2/5]", "Podprůměrné"),
    3: ("[3/5]", "Průměrné"),
    4: ("[4/5]", "Nadprůměrné"),
    5: ("[5/5]", "Výrazně nadprůměrný"),
}
