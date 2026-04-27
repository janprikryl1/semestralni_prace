# EMA + Fear and Greed Experiment

Tento adresář obsahuje  experimentální variantu  bota založenou na:
- `EMA` z knihovny `TA-Lib`
- sentimentu trhu přes `Fear and Greed`

## Strategie

- `BUY`: aktuální cena je nad `EMA` a Fear and Greed je pod nákupním prahem
- `SELL`: aktuální cena je pod `EMA` a Fear and Greed je nad prodejním prahem
- `HOLD`: jinak

## Závislosti

Tato varianta používá `TA-Lib`, který není čistě Python knihovna. Pokud není nainstalovaný, skript skončí s jasnou chybovou hláškou.

Základní instalace Python balíčků:

```bash
pip install -r requirements.txt
```

## Spuštění

Jednorázový běh:

```bash
python main.py --once
```

Nepřetržitý běh:

```bash
python main.py
```

## Poznámka

Tato varianta používá vlastní:

- konfiguraci `config.json`
- databázi `ema_fng_trades.db`
- logy v adresáři `logs/`
