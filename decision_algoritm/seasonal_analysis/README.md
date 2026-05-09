# Seasonal Analysis

Detekuje opakujici se sezonni vzory v krypto trzich na zaklade historickych dennich cen.
Data se nacitaji z databaze, analyzy vyuzivaji metody strojoveho uceni.

## Obsah projektu
```
seasonal_analysis/
  config.json               - barevne tema a nastaveni grafu
  config.py                 - konstanty (coiny, mesice, cesty) + nacitani config.json
  db.py                     - pripojeni k DB a normalizace dat
  analysis.py               - ML analyzy (K-Means, korelace, STL, skore)
  plots.py                  - generovani vsech 8 grafu
  reports.py                - textove vystupy do konzole
  seasonality_analysis.py   - hlavni spustitelny soubor (argparse)
  requirements.txt          - seznam zavislosti
  .env                      - pripojovaci udaje k DB (neverzovat)
  output/                   - vygenerovane PNG soubory (generovano)
```

## Pozadavky
Python 3.10+. Instalace zavislosti:
```bash
pip install -r requirements.txt
```
Potrebne balicky: `mysql-connector-python`, `python-dotenv`, `pandas`, `numpy`,
`matplotlib`, `seaborn`, `scikit-learn>=1.5`, `statsmodels`.

## Konfigurace barev a motivu
Vsechny barvy grafu jsou uloženy v `config.json`.
```json
{
  "theme": {
    "bg":       "#ffffff",   // pozadi grafu
    "card_bg":  "#f5f4f0",   // pozadi legendy
    "border":   "#d8d4ce",   // barva mrizky a rámu
    "text":     "#1a1916",   // nadpisy a popisy
    "muted":    "#5a6272",   // popisky os
    "zeroline": "#aab0b8"    // prerusovana cara na urovni 0
  },
  "coin_colors": {
    "BTC": "#F7931A",
    "ETH": "#627EEA",
    ...
  },
  "chart_colors": {
    "accent":          "#b07d10",  // zvyrazneni (elbow cara, optimal k)
    "stl_trend":       "#b07d10",  // trend v STL grafu
    "stl_seasonal":    "#16803a",  // sezonni slozka v STL grafu
    "stl_resid":       "#6b7280",  // residuum v STL grafu
    "bar_strong_sell": "#dc2626",  // mesicni vynos < -10 %
    "bar_sell":        "#f97316",  // mesicni vynos -10 az -3 %
    "bar_neutral":     "#eab308",  // mesicni vynos -3 az +3 %
    "bar_buy":         "#22c55e",  // mesicni vynos +3 az +15 %
    "bar_strong_buy":  "#16a34a"   // mesicni vynos > +15 %
  }
}
```

## Spusteni
```bash
# Vsechny grafy
python seasonality_analysis.py

# Vybrane grafy
python seasonality_analysis.py 1 3 8

# Vypis dostupnych grafu
python seasonality_analysis.py --list
```

## Dostupne grafy
| # | Soubor | Popis |
|---|--------|-------|
| 1 | `01_avg_seasonal_pattern.png` | Prumerny sezonni vzor s pasem +/- 1 std |
| 2 | `02_all_years_overlay.png` | Overlay vsech let (kazda cara = jeden rok) |
| 3 | `03_elbow_silhouette.png` | Elbow + Silhouette pro vyber poctu clusteru |
| 4 | `04_regime_heatmap.png` | Heatmapa trzniho rezimu (rok x den, K-Means) |
| 5 | `05_regime_calendar.png` | Zastoupeni rezimu v prubehu roku |
| 6 | `06_year_correlation.png` | Korelace sezonniho vzoru mezi roky (Pearson) |
| 7 | `07_stl_BTC.png` | STL dekompozice (trend + sezona + residuum) pro BTC |
| 8 | `08_monthly_recommendations.png` | Mesicni doporuceni se skore 1–5 |


## Metodika
**Normalizace** — pro kazdy par (coin, rok) se vypocte procentualni zmena ceny
vuci prvni dostupne cene daneho roku. Umoznuje porovnani jednotlivych let na
spolecne ose (osa Y = % od 1. ledna).

**K-Means clustering** — kazdy den roku je reprezentovan vektorem
`[pct_BTC, pct_ETH, pct_SOL, pct_XRP, pct_ADA]`. Algoritmus sdruzuje
podobne trhy do rezimu (medved / bocni pohyb / byk). Pocet clusteru
se voli automaticky podle nejvyssiho Silhouette score v rozsahu k = 2–10.
Clustery jsou serazeny od nejvetsiho medveda (0) po nejvetsiho byka (N-1).

**Pearsonova korelace** — korelacni matice rocnich vzoru odpovida na otazku,
jak moc jsou si jednotliva leta navzajem podobna (hodnota blizka 1 = stejny
sezonni vzor, blizka -1 = zrcadlovy vzor).

**STL dekompozice** — rozklada prumerny sezonni signal na tri slozky:
trend (dlouhodoby smer), sezonni slozka (opakujici se vzor) a residuum
(nahodny sum). Parametr `period=52` odpovida tydenni periodicite.

**Mesicni skore (1–5)** — pro kazdy mesic se spocte prumerny vysledek
obchodu jako `pct(posledni den) - pct(prvni den mesice)`, agreguje se
pres vsechny coiny a vsechny dostupne roky. Vysledky se linearni
normalizaci prevadi na stupnici 1 (vyhni se) az 5 (silne koupit).
