# Raport audytu gruntownego - Astro Global po seed 100

Data audytu: 2026-05-22  
Repo: `krapcys1-maker/astro-global`  
Branch: `astro-global`  
Folder: `D:\astro Global`

## Werdykt

Projekt idzie w dobrym kierunku jako backend proof / MVP core. Najważniejszy podział odpowiedzialności pozostaje zdrowy: obliczenia planetarne, reguły astrologiczne, scoring, historia i narracja są oddzielone. AI nadal nie jest źródłem prawdy.

Nie ma czerwonej blokady w kodzie proof. Główna blokada produktu nadal jest ta sama: brak realnego runtime Swiss Ephemeris w aktualnym środowisku Windows/Python, więc realny indeks planetarny nie może jeszcze zostać zbudowany na prawdziwych efemerydach.

## Co mamy

- Repo jest czyste, właściwy branch to `astro-global`, a `.env`, DuckDB, cache i indeksy są ignorowane.
- Backend proof działa: FastAPI, token lokalny, CORS lokalny, `/health`, `/data/status`, `/sky/current`, `/sky/at-date`, `/events/window`, `/resonance/search`.
- Synthetic provider działa stabilnie jako provider proof i testowy.
- Swiss provider jest zaimplementowany, ale `swisseph` nie jest dostępny lokalnie; API zwraca kontrolowane `503` dla providera `swiss`.
- AstroRulesEngine, cycle registry, vectorizer `global_slow_v1`, exact search, episode clustering i score breakdown są pokryte testami.
- Persistent index `.npz` działa na providerze syntetycznym; path traversal dla `index_file` jest odrzucany.
- `planetary_resonance_score` nie miesza danych historycznych do rankingu planetarnego.
- `narrative_confidence` jest osobnym wynikiem opartym o coverage, źródła i confidence eventów.
- Deterministic summary po polsku działa bez DeepSeek i nie referencjonuje eventów bez źródeł.
- Dane historyczne: `100` eventów, `100` curated sources, a razem z automatycznym Wikidata jest `200` źródeł.

## Bramka jakości

Uruchomione kontrole:

- `python -m ruff check services tests scripts` - OK.
- `pytest` - `66 passed, 1 skipped, 1 warning`.
- `python -m compileall services scripts tests` - OK.
- `python scripts/update_resonance_api_golden.py --check` - snapshot aktualny.
- `python scripts/ingest_curated_events.py --dry-run` - OK, `100` eventów.
- Pełna walidacja URL-i: `200/200` URL-i działa.
- Manualny smoke API:
  - `/health` bez tokenu: `200`.
  - `/data/status` bez tokenu: `401`.
  - `/data/status` z tokenem: `100` curated eventów.
  - `/events/window 1895-1896`: zwraca oczekiwane procesy historyczne, m.in. Scramble for Africa i First Italo-Ethiopian War.
  - `/sky/at-date` z `provider=swiss`: kontrolowane `503`, bo `swisseph` nie jest zainstalowany.

## Dane historyczne

Stan po walidacji:

- Eventy: `100`.
- Curated sources: `100`.
- Wszystkie źródła razem: `200`.
- Zakres lat: `1501-2026`.
- Duplikaty event IDs: `0`.
- Duplikaty source IDs: `0`.
- Eventy bez curated source: `0`.
- Curated sources wskazujące nieistniejący event: `0`.
- Regiony: `22`.
- Kategorie: `17`.

Coverage jest wyraźnie lepszy niż przy 75 eventach. Nadal istnieje bias europejski, ale jest jawnie raportowany i nie przekracza progu warningu. Największe niedobory dalej są w Afryce, Ameryce Południowej, Azji Południowo-Wschodniej oraz w długim ogonie lokalnych procesów XVIII-XIX wieku.

## Wyrywkowa kontrola danych

Sprawdzone ręcznie rekordy i źródła:

- `evt_atlantic_slave_trade`: Britannica opisuje transatlantycki handel niewolnikami jako proces od XVI do XIX wieku; zakres `1501-1867` jest akceptowalny jako roboczy zakres historyczny dla seeda.
- `evt_ethiopian_adal_war`: Wikidata `Q2915203` podaje konflikt `1529-1543`, zgodny z CSV.
- `evt_burmese_siamese_war_1765`: Wikidata `Q31307` podaje konflikt `1765-1767`, zgodny z CSV.
- `evt_java_war`: Britannica potwierdza Java War jako wydarzenie `1825-1830`, zgodne z CSV.
- `evt_first_italo_ethiopian_war`: Britannica potwierdza Italo-Ethiopian War `1895-1896`, zgodne z CSV.
- `evt_partition_of_india`: Britannica potwierdza Partition of India jako wydarzenie `1947`, zgodne z CSV.
- `evt_rwandan_genocide`: UN i Wikidata `Q131297` potwierdzają 1994 Genocide against Tutsi, zgodne z CSV.

Źródła użyte w kontroli:

- https://www.britannica.com/topic/transatlantic-slave-trade
- https://www.wikidata.org/wiki/Q2915203
- https://www.wikidata.org/wiki/Q31307
- https://www.britannica.com/event/Java-War
- https://www.britannica.com/topic/Italo-Ethiopian-War-1895-1896
- https://www.britannica.com/event/Partition-of-India
- https://www.un.org/en/preventgenocide/rwanda/

## Znaleziona luka i naprawa

Znaleziono niespójność między fallbackiem CSV a DuckDB:

- DuckDB sortował eventy po `confidence_score DESC, start_astro_year ASC, id ASC`.
- Fallback CSV zwracał eventy w kolejności pliku.

Efekt: świeże środowisko bez lokalnego DuckDB mogło zwrócić inne `matched_events` niż środowisko z DuckDB, mimo tych samych danych źródłowych.

Naprawa wykonana w audycie:

- Dodano sortowanie eventów w fallbacku CSV zgodne z DuckDB.
- Dodano sortowanie źródeł fallbacku zgodne z query DuckDB.
- Dodano testy parzystości fallback vs DuckDB dla eventów i źródeł.

Pliki zmienione:

- `services/historical/event_query.py`
- `tests/test_astro_global_historical.py`

## Ryzyka

1. Brak realnego Swiss Ephemeris

Najważniejsze ryzyko. Bez `swisseph` produkt nadal liczy proof na providerze syntetycznym. To jest dobre do pipeline'u, ale nie jest realnym niebem.

2. Długie procesy historyczne dominują okna

Eventy typu Atlantic slave trade, Mughal Empire, Tokugawa shogunate czy Scientific Revolution trwają bardzo długo. Dają kontekst epoki, ale mogą wypierać krótkie wydarzenia, jeśli w przyszłości nie rozdzielimy typów eventów na `process`, `conflict`, `institution`, `event`.

3. Źródła są poprawne jako start, ale część jest szeroka

Niektóre źródła są ogólne, np. Britannica o historii Nigerii dla Sokoto Caliphate. To wystarcza dla proof seeda, ale dla produktu warto później dodać bardziej precyzyjne źródła drugiego poziomu.

4. Coverage nadal jest małe dla produktu

100 eventów wystarcza do testów i proofu, ale nie wystarcza do pełnej aplikacji historycznej. Docelowo MVP powinno mieć minimum `500-1500` wydarzeń kontrolowanych.

5. Narracja AI nadal nie jest wdrożona

To nie blokuje MVP core. Dobrze, że deterministic summary działa bez DeepSeek. DeepSeek powinien wejść dopiero po stabilnym realnym pipeline.

## Plan naprawczy

1. Swiss Ephemeris

- Zainstalować `pyswisseph` w środowisku z gotowym wheel albo doinstalować Microsoft Visual C++ Build Tools.
- Uruchomić test JPL Horizons bez skipa.
- Zbudować `1900-now weekly` na `--provider swiss`.

2. Dane historyczne

- Rozszerzyć seed `100 -> 150` tylko jeśli Swiss dalej blokuje pracę.
- Priorytet: Afryka, Ameryka Południowa, Azja Południowo-Wschodnia, Bliski Wschód.
- Dodać pole lub model klasyfikacji eventów: `instant`, `short_event`, `war`, `long_process`, `institution`.

3. Search historyczny

- Dodać ranking eventów, który nie pozwoli długim procesom zawsze wygrywać z krótkimi wydarzeniami.
- Dodać test: krótkie wydarzenie o wysokim confidence w oknie nie znika pod kilkoma długimi procesami.

4. Źródła

- Dodać drugi curated source dla eventów wysokiego ryzyka albo szerokich.
- Zaznaczać w API `source_precision`: `direct`, `contextual`, `broad_context`.

5. UI dopiero po Swiss

- Nie zaczynać pełnego UI/Tauri przed realnym smoke testem Swiss.
- Po Swiss zacząć od małego widoku diagnostycznego: current sky, primary cycles, episodes, matched events, confidence/debug.

## Kolejny logiczny krok

Najbardziej logiczny krok po tym audycie:

1. Spróbować odblokować `swisseph` przez środowisko lub build tools.
2. Jeśli nadal blokuje: dodać klasyfikację eventów (`event_kind`) i ranking historii, żeby długie procesy nie dominowały wyników.

Nie zaczynać jeszcze pełnego UI ani DeepSeek.
