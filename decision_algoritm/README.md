# Algorithmic Trading Bot for Binance

Projekt implementuje jednoduchého algoritmického trading bota v Pythonu pro obchodování kryptoměnového páru `BTCUSDC` přes Binance API. Návrh kombinuje technickou a fundamentální analýzu a v pravidelném intervalu vyhodnocuje, zda má dojít k nákupu, prodeji, nebo držení pozice.

## Použitá logika

- Technická analýza: Simple Moving Average (`SMA`) nad hodinovými cenami z Binance.
- Fundamentální analýza: index Fear and Greed z CoinMarketCap API.
- Výstup strategie:
  - `BUY`: cena je nad SMA a trh je ve strachu
  - `SELL`: cena je pod SMA a trh je příliš chamtivý
  - `HOLD`: signály nejsou v souladu nebo chybí data

Síla signálu je odvozena z kombinace odchylky ceny od SMA a intenzity sentimentu. Na jejím základě se počítá velikost pozice.

## Hlavní vlastnosti

- pravidelné spouštění strategie, standardně každou hodinu
- řízení velikosti pozice podle sentimentu trhu
- práce s reálným portfoliem `USDC` a `BTC`
- režim `dry_run`, ve kterém se obchody pouze simulují
- logování rozhodnutí do souboru `trading.log`
- ukládání rozhodnutí a obchodů do databáze SQLite `trades.db`

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
  inicializace SQLite databáze a ukládání auditních záznamů
- `config.json`:
  parametry strategie, limity a provozní nastavení

## Konfigurace

Do souboru `.env` je potřeba doplnit:

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
- zapnutí nebo vypnutí `dry_run`

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
- Před přechodem na live obchodování je potřeba zkontrolovat limity účtu, přesnost množství a minimální notional pro konkrétní symbol na Binance.
- Projekt je vhodný jako demonstrační nebo semestrální základ, ne jako hotový produkční trading systém.
