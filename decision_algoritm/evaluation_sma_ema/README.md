# evaluation_sma_ema
Nástroje pro vyhodnocení výsledků live-tradingových strategií **SMA_FG** a **EMA_FG**.

## Struktura adresáře
| Soubor | Popis                                                                        |
|---|------------------------------------------------------------------------------|
| `evaluate.py` | Načte rozhodnutí a obchody z databáze a vygeneruje textové shrnutí a grafy   |
| `pnl.py` | Vypočítá realizovaný a nerealizovaný P&L přímo z Binance API (metodika AVCO) |
| `evaluate_sma.png` | Výstupní graf pro strategii SMA-14                                           |
| `evaluate_ema.png` | Výstupní graf pro strategii EMA-21                                           |
---

## evaluate.py — vyhodnocení signálů a obchodů
Skript čte z tabulek `decisions` a `trades`, pro zvolené strategie vypíše statistiky, zobrazí a uloží vizualizaci.
```bash
python evaluate.py --strategy sma
python evaluate.py --strategy ema
python evaluate.py --strategy both
python evaluate.py --strategy sma --config-change 2026-04-28
python evaluate.py --strategy both --from 2026-04-24 --to 2026-05-08
```

#### Parametry
| Parametr | Výchozí     | Popis                                                                |
|---|-------------|----------------------------------------------------------------------|
| `--strategy` | `both`      | Strategie k vyhodnocení: `sma`, `ema` nebo `both`                    |
| `--config-change` | -           | Datum změny konfigurace (`YYYY-MM-DD`) - rozdělí analýzu na dvě fáze |
| `--from` | 30 dní zpět | Začátek sledovaného období (`YYYY-MM-DD`)                            |
| `--to` | dnes        | Konec sledovaného období (`YYYY-MM-DD`)                              |

### Výstup

**Textové shrnutí**:
- Počty a procentuální zastoupení signálů BUY / SELL / HOLD
- Porovnání signálů před a po změně konfigurace (bylo-li zadáno `--config-change`)
- Počty a objemy obchodů (celkový objem v USD, rozdělení dle strany a symbolu)

**Graf** `evaluate_<strategy>.png` obsahuje šest panelů:
1. Signály v čase
2. Koláčový graf rozložení signálů
3. Histogram Fear & Greed indexu dle signálu (s vyznačenými prahy)
4. Objem obchodů v USD per symbol (BUY vs. SELL)
5. Kumulativní objem obchodů v čase
6. Srovnání podílu signálů: starý vs. nový config

---
## pnl.py — výpočet P&L z Binance API

Skript stáhne historii obchodů přímo z Binance API a spočítá zisk/ztrátu metodou **AVCO** (průměrné pořizovací ceny).

### Použití
```bash
python pnl.py
python pnl.py --deposits 38.68
python pnl.py --exclude-ids 2635588222,2635599964
python pnl.py --from 2026-04-09
```

### Parametry

| Parametr | Výchozí | Popis                               |
|---|---|-------------------------------------|
| `--deposits` | `38.68` | Celková výše vkladů v USD           |
| `--exclude-ids` | `2635588222,2635599964` | ID obchodů, které se mají přeskočit |
| `--from` | `2026-04-09` | Začátek období (`YYYY-MM-DD`)       |
| `--symbols` | všechny | Symboly, např. `BTCUSDC,XRPUSDC`    |
Výchozí sledované symboly: `BTCUSDC`, `XRPUSDC`, `BCHUSDC`, `TRXUSDC`, `PEPEUSDC`, `SHIBUSDC`, `BNBUSDC`.

### Metodika AVCO
- **Realizovaný P&L** = (prodejní cena − průměrná nákupní cena) × prodané množství
- **Nerealizovaný P&L** = (aktuální cena − průměrná nákupní cena) × držené množství
- **Celkový P&L** = realizovaný + nerealizovaný − poplatky

Poplatky (commission) jsou převáděny na USDC:
- `USDC` → přímá hodnota
- `BNB` → historická cena z 1minutových klines
- ostatní aktiva → aktuální cena

### Výsledky posledního spuštění (pnl.txt, stav ~2026-05-09)

| Položka | Hodnota |
|---|---|
| Počet obchodů | 81 |
| Realizovaný P&L | **+0.4800 USDC** |
| Nerealizovaný P&L | +0.1290 USDC |
| Čistý P&L z obchodování | **+0.6090 USDC** |
| Vloženo (deposity) | 38.68 USD |
| Hodnota portfolia | 95.03 USDC |
| Portfolio − deposity | +56.35 USDC ¹ |

> ¹ Rozdíl zahrnuje ~51.40 USDC z prodeje předchozích holdings (BNB, BTC před spuštěním botů), které nevstupují do P&L obchodní strategie.
