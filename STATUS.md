# Status Prac - Astro Global

Data aktualizacji: 2026-05-22  
Folder roboczy: `D:\astro Global`  
Repo docelowe: `krapcys1-maker/astro-global`  
Branch roboczy: `astro-global`  
Widoczność repo: publiczne  
Język produktu: polski

## Stan Ogólny

Projekt ma być nową aplikacją `Astro Global`, prowadzoną bezpośrednio w folderze `D:\astro Global`. Nie tworzymy podfolderów projektu i nie mieszamy kodu ze starym `astroapp`/AstroLabb.

Zakres GO: fazy 0-5, czyli repo hygiene, kontrakty domenowe, ephemeris, reguły astrologiczne, cycle registry, vectorizer, proof index, exact search, episode clustering i smoke test pipeline.

Zakres HOLD do pierwszego smoke testu: pełny UI, Tauri packaging, DeepSeek narrative layer jako główny tor, starożytność, FAISS/HNSW i masowy import Wikidata.

## Ukończone

- Przygotowano dokumenty startowe: `README.md`, `STATUS.md`, `PLAN_PRAC_ASTRO_GLOBAL.md`, `TEST_PLAN_ASTRO_GLOBAL.md`.
- Ustalono nazwę produktu: `Astro Global`.
- Ustalono język UI i narracji: polski.
- Ustalono repo docelowe: `krapcys1-maker/astro-global`.
- Ustalono branch roboczy: `astro-global`.
- Ustalono, że repo ma być publiczne.
- Ustalono Windows-first jako pierwszy target.
- Ustalono, że DeepSeek online może być użyty później dla narracji, ale MVP ma działać bez niego.
- Usunięto błędny lokalny folder `astroapp`.
- Usunięto błędny lokalny folder `astro-global`.
- Usunięto błędny branch `astro-global` ze starego repo `krapcys1-maker/astroapp`.
- Dodano `.gitignore`, żeby `.env` i dane build/cache/index nie trafiły do repo.
- Zainicjalizowano Git bezpośrednio w `D:\astro Global`.
- Utworzono publiczne repo `krapcys1-maker/astro-global`.
- Wypchnięto `main` oraz branch roboczy `astro-global`.
- Dodano `pyproject.toml` i czysty pakiet `services/`.
- Dodano kontrakty domenowe ephemeris, `SwissEphemerisProvider`, AstroRulesEngine, cycle registry, vectorizer `global_slow_v1`, scoring, exact search i episode clustering.
- Dodano `tests/golden/` oraz pierwsze testy jednostkowe i proof smoke pipeline.
- Dodano minimalny `curated_events.csv`.
- Weryfikacja: `pytest` przechodzi, `15 passed`.
- Weryfikacja: `python scripts/smoke_test_pipeline.py --date now --profile global_slow_v1` generuje JSON.
- Weryfikacja: `python -m compileall services scripts tests` przechodzi.
- `ruff` nie został uruchomiony, bo moduł nie jest zainstalowany w aktualnym środowisku.
- Commit `fc0f604` (`feat: add Astro Global backend proof core`) został wypchnięty na `origin/astro-global`.
- Dodano DuckDB schema dla eventów, indeksu stanów, runów rezonansu i cache narracji.
- Dodano importer curated events z walidacją Pydantic i zapisem do DuckDB.
- Dodano coverage report dla eventów historycznych.
- Dodano `scripts/ingest_curated_events.py`.
- Weryfikacja po importerze: `pytest` przechodzi, `19 passed`.
- Weryfikacja po importerze: `python -m ruff check services tests scripts` przechodzi.
- Weryfikacja po importerze: `python scripts/ingest_curated_events.py --dry-run` działa.
- Weryfikacja po importerze: `python scripts/ingest_curated_events.py` zapisuje bazę do ignorowanego `data/duckdb/astro_global.duckdb`.
- Commit `dfb6724` (`feat: add historical event importer`) został wypchnięty na `origin/astro-global`.
- Dodano generator fixture z NASA/JPL Horizons: `scripts/fetch_horizons_planetary_goldens.py`.
- Dodano golden fixture `tests/golden/planetary_states/jpl_horizons_2026-05-22T12Z.json`.
- Dodano test integracyjny porównujący `SwissEphemerisProvider` z niezależnym oracle JPL Horizons, uruchamiany gdy lokalnie dostępny jest moduł `swisseph`.
- Weryfikacja po golden fixture: `pytest` przechodzi, `20 passed, 1 skipped`.
- Weryfikacja po golden fixture: `python -m ruff check services tests scripts` przechodzi.
- Dodano `services/ephemeris/synthetic_provider.py`, żeby smoke pipeline i API korzystały z jednego deterministycznego providera proof.
- Dodano FastAPI app `services/api/app.py` z endpointami `GET /health` i `POST /resonance/search`.
- Dodano testy API dla healthchecka, happy path `/resonance/search` i walidacji nieznanego profilu.
- Dopisano zależności API do `pyproject.toml`: FastAPI, Uvicorn i HTTPX dla testów.
- Weryfikacja po API: `pytest` przechodzi, `23 passed, 1 skipped`.
- Weryfikacja po API: `python -m ruff check services tests scripts` przechodzi.
- Weryfikacja po API: `python scripts/smoke_test_pipeline.py --date 2026-05-22T12:00:00 --profile global_slow_v1` przechodzi.
- Dodano `services/historical/event_query.py` do pobierania wydarzeń historycznych nachodzących na zakres lat epizodu.
- Endpoint `/resonance/search` zwraca teraz przy epizodach `matched_events` oraz `event_coverage`.
- Event query czyta z DuckDB `data/duckdb/astro_global.duckdb`, a gdy baza nie istnieje w świeżym środowisku, używa fallbacku z kontrolowanego `curated_events.csv`.
- Weryfikacja eventów w API: ręczny test `/resonance/search` dla `2026-05-22T12:00:00Z` zwraca `evt_covid_19_pandemic`.
- Weryfikacja po podpięciu eventów: `pytest` przechodzi, `25 passed, 1 skipped`.
- Weryfikacja po podpięciu eventów: `python -m ruff check services tests scripts` przechodzi.
- Weryfikacja po podpięciu eventów: `python scripts/smoke_test_pipeline.py --date 2026-05-22T12:00:00 --profile global_slow_v1` przechodzi.
- Dodano `services/narrative/deterministic_summary.py`, czyli polskie summary bez DeepSeek, oparte wyłącznie o JSON odpowiedzi API.
- Endpoint `/resonance/search` zwraca teraz `deterministic_summary` z `summary`, `key_points`, `referenced_event_ids` i guardrailem anty-predykcyjnym.
- Dodano test narracji sprawdzający, że summary referencjonuje tylko `event_id` z wejściowych `matched_events`.
- Weryfikacja po summary: `pytest` przechodzi, `26 passed, 1 skipped`.
- Weryfikacja po summary: `python -m ruff check services tests scripts` przechodzi.
- Weryfikacja po summary: ręczny test API zwraca polskie `deterministic_summary` i `referenced_event_ids = ['evt_covid_19_pandemic']`.

## W Trakcie / Następne

1. Rozszerzyć `curated_events.csv` poza minimalny seed.
2. Dodać snapshot/golden test pełnej odpowiedzi `/resonance/search`, żeby API nie zmieniało kontraktu po cichu.
3. Wrócić do pełnego uruchomienia Swiss Ephemeris po rozwiązaniu zależności Windows/C++ albo po użyciu środowiska z gotowym `swisseph`.

## Otwarte Decyzje

1. Czy dostarczasz własną listę ważnych wydarzeń historycznych, czy startujemy od curated CSV z Wikidata.
2. UI cykli po smoke teście: prosty tryb z etykietami czy pełny DebugInspector z wagami, orbami i contribution score.

## Ryzyka Do Pilnowania

- Publiczne repo: nie wolno commitować `.env`, kluczy API, cache, indeksów, dumpów ani prywatnych danych.
- Swiss Ephemeris: prywatny MVP jest OK, ale dystrybucja lub komercjalizacja wymaga decyzji licencyjnej.
- `pyswisseph` na aktualnym Windows/Python 3.12 nie ma gotowego wheel z PyPI i próbuje budować C extension; bez Microsoft Visual C++ Build Tools test Swiss Ephemeris pozostaje skipped.
- AI: DeepSeek nie może dodawać faktów spoza wejściowych eventów.
- Wikidata nie może być runtime dependency endpointów aplikacji; tylko build/enrichment/cache.
- Scoring planetarny nie może zawierać `historical_event_support`.
- Częste aktywatory Jowisza i Marsa nie mogą zdominować ciężkich cykli mundalnych.
- UI nie może pokazywać `0 CE`.

## Historia Aktualizacji

- 2026-05-22: Uporządkowano projekt po błędnej próbie pracy w starym `astroapp`. Właściwy projekt ma startować w `D:\astro Global`, repo `krapcys1-maker/astro-global`, branch `astro-global`.
- 2026-05-22: Rozpoczęto Fazę 0-5 w poprawnym repo: dodano skeleton backend core, reguły, resonance search, test layout i smoke pipeline.
- 2026-05-22: Zweryfikowano rdzeń: pytest, smoke pipeline i compileall przechodzą; ruff wymaga instalacji dev dependency.
- 2026-05-22: Wypchnięto backend proof core na `origin/astro-global` w commicie `fc0f604`.
- 2026-05-22: Dodano historyczny event layer: schema, importer curated CSV, coverage report, testy i skrypt ingest.
- 2026-05-22: Wypchnięto event importer na `origin/astro-global` w commicie `dfb6724`.
- 2026-05-22: Dodano JPL Horizons golden fixture i test integracyjny dla przyszłej weryfikacji Swiss Ephemeris.
- 2026-05-22: Dodano pierwszy lokalny FastAPI endpoint `/resonance/search` na providerze syntetycznym.
- 2026-05-22: Podłączono `/resonance/search` do warstwy wydarzeń historycznych i coverage report.
- 2026-05-22: Dodano deterministyczne polskie summary bez DeepSeek do odpowiedzi `/resonance/search`.
