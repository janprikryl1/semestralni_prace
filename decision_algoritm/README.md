# Algorithmic Trading Bot for Binance

## SM + fear and greed index trading bot

Algoritmický trading bot pro obchodování daného kryptoměnového páru přes Binance API. Návrh kombinuje **technickou** a **fundamentální** analýzu a v pravidelném intervalu vyhodnocuje, zda má dojít k nákupu, prodeji, nebo držení pozice.

## Použitá logika

- Technická analýza: Simple Moving Average (`SMA`) nad cenami z Binance (Když je cena nad SMA, naznačuje to rostoucí trend; pod ním naznačuje to klesající trend).
- Fundamentální analýza: Fear and Greed index.
- Výstup strategie:
  - `BUY`: cena je nad SMA a trh je ve strachu
  - `SELL`: cena je pod SMA a trh je příliš chamtivý
  - `HOLD`: signály nejsou v souladu nebo chybí data

Síla signálu je odvozena z kombinace odchylky ceny od SMA a intenzity sentimentu. Na jejím základě se počítá velikost pozice.

## Struktura projektu

- `main.py`:
  hlavní smyčka aplikace, vyhodnocení trhu a spuštění obchodní akce
- `price_data.py`:
  načítání historických cen z Binance
- `fear_and_grid_wrapper.py`:
  načítání indexu Fear and Greed
- `new_cm_order.py`:
  práce s Binance účtem, zůstatky a exekuce objednávek
- `database.py`:
  inicializace SQLite databáze a ukládání záznamů
- `config.json`:
  parametry strategie, limity a provozní nastavení
- `logs/`:
  provozní logy aplikace, včetně samostatných session logů

## Konfigurace

Do souboru `.env` je potřeba doplnit API klíče:
```env
API_KEY=your_binance_api_key
API_SECRET=your_binance_api_secret
COINMARKETCAP_API_KEY=your_coinmarketcap_api_key
```

V `config.json` lze upravit:

- obchodovaný symbol
- délku cenové historie pro SMA
- délku intervalu mezi běhy
- prahy Fear and Greed pro `BUY` a `SELL`
- procenta portfolia použitá pro position sizing
- hranice sentimentu pro silnější a běžný `BUY`/`SELL` sizing v sekci `risk_management`
- minimální zůstatky pro aktivaci `BUY` a `SELL` v sekci `limits`
- zapnutí nebo vypnutí `dry_run`
- umístění a retenci logů

### Limity Binance Spot

Při reálném obchodování nestačí pouze interní limity z `config.json`. Každý spot order na Binance musí zároveň projít filtry konkrétního symbolu:

- `LOT_SIZE`: minimální množství v base assetu a krok množství
- `NOTIONAL` nebo `MIN_NOTIONAL`: minimální hodnota orderu v quote assetu

To znamená, že strategie může vygenerovat platný `BUY` nebo `SELL` signál, ale objednávka se přesto neprovede, pokud je vypočtená velikost obchodu příliš malá pro daný symbol. Velikost obchodů je proto vhodné ladit přes `config.json`, zejména v sekcích `risk_management` a `limits`, ne přes umělé dorovnávání objednávek v exekuční vrstvě.

## Spuštění

Jednorázové spuštění:

```bash
python main.py --once
```

Nepřetržitý běh:

```bash
python main.py
```

## Poznámky k bezpečnosti

- Výchozí nastavení používá `dry_run: true`, takže se reálné obchody neodesílají.
- Před přechodem na live obchodování je potřeba zkontrolovat limity účtu, přesnost množství, `LOT_SIZE` a minimální `NOTIONAL` pro konkrétní symbol na Binance.
- Projekt je vhodný jako demonstrační nebo semestrální základ, ne jako hotový produkční trading systém.

## Coverage:
```bash
python -m coverage report
```
Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
fear_and_grid_wrapper.py      24      7    71%   24-30
price_data.py                 27      0   100%
sma.py                         6      0   100%
--------------------------------------------------------
TOTAL                         57      7    88%