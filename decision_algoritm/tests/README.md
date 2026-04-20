# Testy, CI a CD

## Testování

Ve složce `tests` jsou umístěny automatizované testy projektu. Aktuálně je zde připraven test pro funkci `get_fear_and_greed` ze souboru `fear_and_grid_wrapper.py`.

Tento test ověřuje tři základní situace:

- úspěšné načtení dat z reálného API,
- chování při chybějícím API klíči,
- chování při chybě síťového požadavku.

Úspěšná větev testu používá skutečné CoinMarketCap API. Test se proto spustí pouze tehdy, když je nastavená proměnná prostředí `COINMARKETCAP_API_KEY` nebo `COINMARKETCUP`. Pokud klíč chybí, test se korektně přeskočí. Chybové scénáře jsou stále testovány řízeně, aby bylo možné ověřit i reakci na výpadek sítě nebo chybějící konfiguraci.

Lokální spuštění testů:

```bash
python -m pytest
```

Instalace potřebných balíčků:

```bash
pip install -r requirements.txt
```

## CI

Projekt využívá GitHub Actions jako CI pipeline. Workflow je umístěno v kořenové složce repozitáře v adresáři `.github/workflows`.

CI pipeline se spouští automaticky:

- po `push` do větve `main`,
- po vytvoření nebo aktualizaci `pull_request` do větve `main`.

Pipeline provádí tyto kroky:

- stáhne aktuální verzi repozitáře,
- nastaví prostředí s Pythonem 3.11,
- nainstaluje závislosti ze souboru `requirements.txt`,
- spustí automatizované testy pomocí `python -m pytest`.

Pokud je v GitHub repozitáři nastaven secret `COINMARKETCAP_API_KEY`, může CI ověřit i volání reálného API. Bez tohoto secretu se live test pouze přeskočí a pipeline zůstane stabilní.

Smyslem CI je ověřit, že změny v kódu neporušily základní funkčnost projektu. Díky tomu lze chyby zachytit ihned po odevzdání změn do repozitáře.

## CD

Plně automatizované CD v tomto projektu zatím zavedeno není. Důvodem je charakter aplikace: nejde o veřejně nasazovanou webovou službu, ale o interní a experimentální trading nástroj.

U tohoto typu projektu by automatický deployment po každé změně do `main` nebyl vhodný, protože:

- aplikace pracuje s API klíči a citlivou konfigurací,
- může provádět obchodní operace nad reálným nebo simulovaným portfoliem,
- nasazení nové verze bez kontroly by mohlo vést k chybnému obchodnímu chování.

Z tohoto důvodu je v projektu použito především CI, tedy automatické ověřování kvality kódu. Samotné spuštění nebo nasazení aplikace je ponecháno na manuálním rozhodnutí. Tento přístup je pro semestrální a interní projekt vhodnější než plně automatizované CD.
