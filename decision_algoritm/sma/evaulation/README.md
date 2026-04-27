Adresář `evaulation/` slouží k vyhodnocení strategie nad daty uloženými v `trades.db`.

Obsah:

- `database_loader.py`
  načítání rozhodnutí a obchodů z SQLite databáze
- `statistics.py`
  výpis základních statistik strategie
- `graph_data.py`
  vytvoření grafu s cenou, SMA, sentimentem a úspěšnými obchody

Spuštění statistik:

```bash
python evaulation/statistics.py
```

Vygenerování grafu:

```bash
python evaulation/graph_data.py
```

Výstupní graf se uloží jako `evaulation/evaluation_plot.png`.
