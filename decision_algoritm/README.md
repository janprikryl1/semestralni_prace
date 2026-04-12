V rámci práce byl implementován rozhodovací modul pro automatizované obchodování kryptoměn. Tento modul kombinuje prvky technické a fundamentální analýzy.

Technická analýza je realizována pomocí klouzavého průměru (SMA), který slouží k identifikaci trendu trhu na základě historických cenových dat získaných z burzy Binance.

Fundamentální analýza je zastoupena indexem Fear and Greed, který reflektuje sentiment trhu a psychologii investorů.

Výsledná obchodní strategie využívá kombinaci těchto dvou přístupů. Nákupní signál je generován pouze v případě, že trh vykazuje známky přeprodanosti (nízká hodnota indexu Fear and Greed) a zároveň se cena nachází nad klouzavým průměrem, což indikuje potenciální růstový trend.


Pro ukládání rozhodnutí obchodního algoritmu byla kromě logovacího systému využita také jednoduchá relační databáze SQLite. Do databáze jsou ukládány informace o jednotlivých rozhodnutích, včetně hodnot vstupních parametrů, jako je aktuální cena, klouzavý průměr a index Fear and Greed.

Tento přístup umožňuje zpětnou analýzu chování algoritmu a poskytuje podklady pro jeho další optimalizaci.

Konfigurační parametry systému byly uloženy do externího souboru ve formátu JSON. Tento přístup umožňuje oddělení aplikační logiky od konfiguračních dat a usnadňuje experimentování s různými nastaveními strategie bez nutnosti zásahu do zdrojového kódu.

Konfigurační soubor obsahuje zejména parametry technické analýzy, prahové hodnoty fundamentálních indikátorů a nastavení řízení rizika.
