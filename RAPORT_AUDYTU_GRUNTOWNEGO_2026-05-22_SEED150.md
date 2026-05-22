# Raport audytu gruntownego - Astro Global seed 150

Data audytu: 2026-05-22  
Folder: `D:\astro Global`  
Repo: `krapcys1-maker/astro-global`  
Branch: `astro-global`

## Werdykt

Projekt idzie w dobrym kierunku jako backend proof / MVP core. Kod przechodzi bramke jakosci, kontrakty API sa chronione snapshotem, seed historyczny urosl do sensownego proof datasetu, a zrodla sa kompletne i walidowalne.

Nie ma obecnie czerwonego bledu w kodzie, ktory blokuje dalsza prace nad warstwa core. Sa natomiast trzy wazne luki produktowe:

1. Realny Swiss Ephemeris nadal nie dziala w runtime lokalnym, wiec produkt nadal liczy proof na `SyntheticEphemerisProvider`.
2. Dataset 150 wydarzen jest juz dobry do testow, ale za maly i zbyt wojennie skrzywiony na pelny produkt historyczny.
3. Procesy trwajace maja techniczne `end_astro_year=2026`; trzeba dodac jawne `is_ongoing` albo `end_policy=build_year`, zeby aplikacja nie udawala, ze te procesy zakonczyly sie w 2026.

## Co mamy

- Repo jest uporzadkowane i pracuje w poprawnym miejscu: `D:\astro Global`.
- Branch roboczy to `astro-global`.
- `.env`, DuckDB, cache i indeksy nie sa sledzone przez git.
- Backend proof core ma kontrakty domenowe, provider synthetic, kod Swiss providera, reguly astrologiczne, vectorizer `global_slow_v1`, scoring, exact search i episode clustering.
- API ma lokalny token, lokalny CORS, endpointy `/health`, `/data/status`, `/sky/current`, `/sky/at-date`, `/events/window`, `/resonance/search`.
- Historia ma schema DuckDB, importer CSV, fallback CSV, event sources, source quality, source precision i diagnostyke `/data/status`.
- Narracja deterministyczna po polsku dziala bez DeepSeek i nie moze referencjonowac eventow spoza wejscia.
- Golden snapshot `/resonance/search` chroni kontrakt API.

## Bramka jakosci

Wykonane komendy:

```powershell
python -m ruff check services tests scripts
pytest
python -m compileall services scripts tests
python scripts\update_resonance_api_golden.py --check
python scripts\ingest_curated_events.py --dry-run
```

Wynik:

- `ruff`: przechodzi.
- `pytest`: `69 passed, 1 skipped, 1 warning`.
- `compileall`: przechodzi.
- golden snapshot API: aktualny.
- importer curated events: dry-run przechodzi.
- test Swiss/JPL pozostaje `skipped`, bo lokalnie nie ma modulu `swisseph`.

## Audyt danych

Stan danych po seed 150:

- `curated_events.csv`: 150 eventow.
- `curated_event_sources.csv`: 157 dodatkowych curated sources.
- Razem z automatycznym `wikidata_seed`: 307 zrodel.
- Zakres lat: 1501-2026.
- Regiony: 26.
- Kategorie: 18.
- Brak duplikatow event IDs.
- Brak zrodel wskazujacych na nieistniejace event IDs.
- Brak eventow bez curated source.
- Brak slabych zrodel `contextual` / `broad_context` bez bezposredniego backupu.

Walidacja URL:

- Sprawdzono 307/307 source URL.
- Bledy HTTP / wyjatki: 0.

Parzystosc DuckDB i fallback CSV:

- Okna `1895-1896`, `1975-1979`, `1997-1999`, `2011-2016`, `2020-2026` zwracaja te same event IDs w DuckDB i fallbacku CSV.
- Ranking eventow dziala stabilnie i nie rozjezdza sie miedzy backendami danych.

Najwieksze rozklady:

- Kategorie: `war` = 69/150, `revolution` = 25/150, dalej znacznie mniejsze grupy.
- Event kind: `war` = 59, `long_process` = 27, `instant_event` = 26, `revolution` = 22, `crisis` = 13.
- Source quality: przewazaja zrodla encyklopedyczne i Wikidata seed; primary/institutional sa nadal mniejszoscia.

## Reczna kontrola probek

Wyrywkowo sprawdzono eventy, daty, typy i zrodla:

- `evt_green_revolution`: 1950-1970, `science_technology`, direct source `https://en.wikipedia.org/wiki/Green_Revolution`.
- `evt_eritrea_independence_war`: 1961-1991, `war`, direct source `https://en.wikipedia.org/wiki/Eritrean_War_of_Independence`.
- `evt_guatemalan_civil_war`: 1960-1996, `war`, direct source `https://en.wikipedia.org/wiki/Guatemalan_Civil_War`.
- `evt_colombian_conflict`: 1964-, technicznie `1964-2026`, direct source `https://en.wikipedia.org/wiki/Colombian_conflict`.
- `evt_montreal_protocol`: 1987, `institution`, direct source `https://en.wikipedia.org/wiki/Montreal_Protocol`.
- `evt_human_genome_project`: 1990-2003, `science_technology`, direct source `https://en.wikipedia.org/wiki/Human_Genome_Project`.
- `evt_sars_outbreak`: 2002-2004, `epidemic`, direct source `https://en.wikipedia.org/wiki/2002%E2%80%932004_SARS_outbreak`.
- `evt_indian_ocean_tsunami`: 2004, `disaster`, direct source `https://en.wikipedia.org/wiki/2004_Indian_Ocean_earthquake_and_tsunami`.
- `evt_west_africa_ebola`: 2013-2016, `epidemic`, direct source `https://en.wikipedia.org/wiki/Western_African_Ebola_epidemic`.
- `evt_paris_agreement`: 2015, `institution`, direct source `https://en.wikipedia.org/wiki/Paris_Agreement`.
- `evt_hiv_aids_pandemic`: 1981-, technicznie `1981-2026`, direct source `https://en.wikipedia.org/wiki/Epidemiology_of_HIV/AIDS`.

Nie znaleziono oczywistych bledow w tych probkach. Wykryto jednak klase danych wymagajaca lepszego modelowania: wydarzenia trwajace.

## Znalezione luki i ryzyka

### 1. Swiss Ephemeris nadal blokuje produkt

`/sky/at-date` dla `provider=synthetic` dziala. Dla `provider=swiss` API zwraca oczekiwane `503`:

```txt
Swiss Ephemeris support requires 'pip install -e .[astro]'.
```

To jest najwieksza luka produktowa. Bez `swisseph` aplikacja nie liczy jeszcze realnego nieba jako runtime produktu.

### 2. Dataset jest za bardzo wojenny

`war` to 69/150 kategorii, a `event_kind=war` to 59/150. To nie psuje kodu, ale moze znieksztalcac narracje i coverage historyczne. Aplikacja moze czesciej opisywac rezonanse przez wojny niz przez instytucje, nauke, ekonomie, epidemie, reformy, migracje, prawa obywatelskie albo kulture.

### 3. Brak jawnego modelu wydarzen trwajacych

Wykryto 6 kandydatow na ongoing:

- `evt_covid_19_pandemic`
- `evt_russian_invasion_ukraine`
- `evt_syrian_civil_war`
- `evt_yemeni_civil_war_2014`
- `evt_colombian_conflict`
- `evt_hiv_aids_pandemic`

Ich `display_date` ma forme otwarta, np. `1964-`, ale `end_astro_year` jest ustawiony na `2026`. To powinno byc jawnie opisane w kontrakcie, bo inaczej kolejne etapy moga interpretowac `2026` jako faktyczny koniec.

### 4. Source quality jest formalnie poprawne, ale jeszcze plytkie

Wszystkie eventy maja zrodla, ale wiekszosc zrodel to Wikidata/Wikipedia. Dla proofu to OK. Dla produktu warto dodac wiecej zrodel primary/institutional i raportowac ich udzial.

### 5. CSV nie jest idealnie utrzymywany porzadkowo

Runtime sortuje wyniki poprawnie, wiec to nie jest bug uzytkowy. Ale przy dalszym powiekszaniu danych reczny CSV moze stawac sie trudny w utrzymaniu. Warto dodac walidator/stable export wymuszajacy sort po `start_astro_year`, `end_astro_year`, `id`.

## Plan naprawczy

Najbardziej logiczna kolejnosc:

1. Dodac do modelu historycznego `is_ongoing` albo `end_policy`.
2. Dodac walidacje: event z otwartym `display_date` musi miec `is_ongoing=true` albo `end_policy=build_year`.
3. Rozszerzyc `/data/status` i coverage report o `event_kind_counts`, `source_quality_counts`, `source_precision_counts`, `ongoing_events_count`.
4. Dodac testy dla ongoing events i statusu danych.
5. Dodac walidator sortowania CSV albo skrypt eksportu w stabilnej kolejnosc.
6. Zbalansowac seed do 200-250 eventow, ale nie przez kolejne wojny; priorytet: nauka, instytucje, gospodarka, prawa czlowieka, zdrowie publiczne, klimat, migracje, kultura i technologie.
7. Wrocic do Swiss Ephemeris: zainstalowac `swisseph` albo podjac decyzje o alternatywnym providerze zgodnym z fixture JPL.

## Kolejny logiczny krok

Najlepszy kolejny krok techniczny to nie kolejna paczka danych, tylko formalizacja jakosci danych:

- dodac `is_ongoing` / `end_policy`,
- dodac diagnostyke rozkladow do `/data/status`,
- dodac testy, ktore zablokuja ciche udawanie konca wydarzen trwajacych.

Dopiero po tym warto albo balansowac seed do 200+, albo ponownie uderzyc w Swiss Ephemeris.
