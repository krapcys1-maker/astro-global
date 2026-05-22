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
- Dodano golden fixture pełnej odpowiedzi `/resonance/search`: `tests/golden/resonance_search/synthetic_2026-05-22T12Z.json`.
- Dodano test snapshot kontraktu API: `tests/test_astro_global_api_golden.py`.
- Golden response obejmuje epizody, cykle, `matched_events`, `event_coverage` i `deterministic_summary`.
- Weryfikacja po golden API: `pytest` przechodzi, `27 passed, 1 skipped`.
- Weryfikacja po golden API: `python -m ruff check services tests scripts` przechodzi.
- Dodano `scripts/update_resonance_api_golden.py`, czyli jawny skrypt aktualizacji i sprawdzania snapshotu `/resonance/search`.
- Test golden API korzysta z tego samego requestu co skrypt aktualizacji, żeby uniknąć rozjazdu parametrów.
- Weryfikacja skryptu golden API: `python scripts/update_resonance_api_golden.py --check` potwierdza aktualny snapshot.
- Weryfikacja po skrypcie golden API: `pytest` przechodzi, `27 passed, 1 skipped`.
- Weryfikacja po skrypcie golden API: `python -m ruff check services tests scripts` przechodzi.
- Rozszerzono `services/historical/seeds/curated_events.csv` z 4 do 25 ręcznie kontrolowanych wydarzeń z lat 1914-2026.
- Seed obejmuje 9 regionów i 11 kategorii, w tym wojny, rewolucje, kryzysy gospodarcze, katastrofy, terroryzm, referenda i przełomy technologiczne.
- Dodano testy pilnujące minimalnej wielkości seeda oraz różnorodności regionów i kategorii.
- Odświeżono lokalny DuckDB przez `python scripts/ingest_curated_events.py`.
- Odświeżono golden snapshot `/resonance/search`; dla testu 2026 endpoint zwraca teraz `evt_russian_invasion_ukraine`, `evt_october_7_attacks` i `evt_covid_19_pandemic`.
- Coverage dla epizodu 2026 ma 3 wydarzenia, 3 regiony i brak warningu biasu.
- Weryfikacja po rozszerzeniu seeda: `pytest` przechodzi, `28 passed, 1 skipped`.
- Weryfikacja po rozszerzeniu seeda: `python -m ruff check services tests scripts` przechodzi.
- Dodano walidację `EventSource` oraz automatyczne generowanie źródeł `wikidata_seed` z `source_url` eventów.
- Importer zapisuje teraz tabelę `event_source` razem z `historical_event`.
- Dodano query `find_sources_for_event_ids`, które czyta źródła z DuckDB albo fallbacku curated CSV.
- Endpoint `/resonance/search` zwraca teraz `sources` przy każdym `matched_event`.
- Golden snapshot `/resonance/search` został odświeżony o `sources`.
- Weryfikacja event sources: `pytest` przechodzi, `30 passed, 1 skipped`.
- Weryfikacja event sources: `python -m ruff check services tests scripts` przechodzi.
- Wykonano audyt kierunku projektu i zapisano raport: `RAPORT_AUDYTU_ASTRO_GLOBAL.md`.
- Audyt potwierdza dobry kierunek backend proof, ale wskazuje blokery przed realnym MVP: provider syntetyczny zamiast realnego ephemeris runtime oraz brak persistent indexu.
- Poprawiono plan scoringu: `historical_event_support` nie wchodzi do `planetary_resonance_score`; historia zasila osobne `narrative_confidence`.
- Dodano `services/narrative/confidence.py`, które liczy `event_coverage_score`, `source_quality_score`, `evidence_confidence` i `narrative_confidence`.
- Endpoint `/resonance/search` zwraca teraz `narrative_confidence` przy każdym epizodzie.
- Summary deterministyczne pomija eventy bez źródeł przy `referenced_event_ids`.
- Odświeżono golden snapshot `/resonance/search` o `narrative_confidence`.
- Weryfikacja po `narrative_confidence`: `pytest` przechodzi, `34 passed, 1 skipped`.
- Weryfikacja po `narrative_confidence`: `python -m ruff check services tests scripts` przechodzi.
- Weryfikacja po `narrative_confidence`: `python scripts/update_resonance_api_golden.py --check` potwierdza aktualny snapshot.
- Dodano lokalne zabezpieczenie API: endpointy poza `/health` wymagają tokenu sesji w `x-astro-global-session` albo `Authorization: Bearer`.
- Dodano lokalny CORS tylko dla originów dev/Tauri: `127.0.0.1`/`localhost` na portach `1420` i `5173`.
- Dodano endpoint `GET /data/status`, który raportuje dostępność synthetic/Swiss providera, stan DuckDB, curated CSV i konfigurację security.
- `GET /data/status` pokazuje teraz jawnie, że `swisseph` nie jest zainstalowany w aktualnym środowisku.
- Weryfikacja po API security/status: `pytest` przechodzi, `37 passed, 1 skipped`.
- Weryfikacja po API security/status: `python -m ruff check services tests scripts` przechodzi.
- Weryfikacja po API security/status: `python scripts/update_resonance_api_golden.py --check` potwierdza aktualny snapshot.
- Próba `python -m pip install -e .[astro]` potwierdziła blokadę Windows/Python 3.12: `pyswisseph` buduje wheel ze źródeł i wymaga Microsoft Visual C++ 14.0+ Build Tools.
- Dodano wybór providera w API: `synthetic` działa stabilnie, `swiss` próbuje użyć `SwissEphemerisProvider` i zwraca `503`, gdy `swisseph` nie jest dostępny.
- Dodano `GET /sky/current` i `POST /sky/at-date`, chronione tokenem sesji.
- `POST /sky/at-date` zwraca pozycje, prędkości, retrograde flag, Julian Day, wersję ephemeris i flagi providera.
- Weryfikacja endpointów sky: `pytest tests/test_astro_global_api.py` przechodzi, `11 passed`.
- Dodano `GET /events/window`, chronione tokenem sesji.
- `GET /events/window` zwraca wydarzenia historyczne z zakresu lat, źródła eventów i `event_coverage`.
- Endpoint `/events/window` korzysta z DuckDB albo fallbacku curated CSV, tak samo jak `/resonance/search`.
- Weryfikacja endpointu events window: `pytest tests/test_astro_global_api.py` przechodzi, `15 passed`.
- Dodano docelowy `score_breakdown` dla epizodów `/resonance/search`.
- `score_breakdown` rozdziela `structural_similarity`, `cycle_power_score`, `rarity_adjusted_percentile` i `planetary_resonance_score`.
- Dodano etykiety siły: `strong`, `moderate`, `weak`, `rare_configuration`, `insufficient_comparable_history`.
- Guardrail scoringu: `strong` wymaga mocnego primary outer cycle i nie wynika z samego wysokiego similarity/percentyla.
- Golden snapshot `/resonance/search` odświeżono o `score_breakdown`.

## W Trakcie / Następne

1. Rozwiązać realny ephemeris provider: `pyswisseph` na Windows albo świadoma alternatywa zgodna z golden JPL Horizons.
2. Dodać persistent proof index 1900-now weekly na realnym providerze.
3. Dodać bezpieczny runner API bindujący do `127.0.0.1` i drukujący lokalny port bez ujawniania sekretów.
4. Rozszerzyć seed wydarzeń historycznych poza 25 eventów technicznych albo dodać drugie źródła dla wybranych eventów.

## Otwarte Decyzje

1. Czy dostarczasz własną listę ważnych wydarzeń historycznych, czy startujemy od curated CSV z Wikidata.
2. UI cykli po smoke teście: prosty tryb z etykietami czy pełny DebugInspector z wagami, orbami i contribution score.

## Ryzyka Do Pilnowania

- Publiczne repo: nie wolno commitować `.env`, kluczy API, cache, indeksów, dumpów ani prywatnych danych.
- Swiss Ephemeris: prywatny MVP jest OK, ale dystrybucja lub komercjalizacja wymaga decyzji licencyjnej.
- `pyswisseph` na aktualnym Windows/Python 3.12 nie ma gotowego wheel z PyPI i próbuje budować C extension; bez Microsoft Visual C++ Build Tools test Swiss Ephemeris pozostaje skipped.
- AI: DeepSeek nie może dodawać faktów spoza wejściowych eventów.
- Wikidata nie może być runtime dependency endpointów aplikacji; tylko build/enrichment/cache.
- Endpointy poza `/health` muszą pozostać za tokenem sesji.
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
- 2026-05-22: Dodano golden snapshot pełnej odpowiedzi `/resonance/search`.
- 2026-05-22: Dodano skrypt aktualizacji/sprawdzenia golden snapshotu `/resonance/search`.
- 2026-05-22: Rozszerzono curated events do 25 kontrolowanych wydarzeń i odświeżono snapshot API.
- 2026-05-22: Dodano obsługę `event_source` i źródła w odpowiedzi `/resonance/search`.
- 2026-05-22: Wykonano audyt projektu i zapisano `RAPORT_AUDYTU_ASTRO_GLOBAL.md`.
- 2026-05-22: Poprawiono plan scoringu i dodano `narrative_confidence` do API.
- 2026-05-22: Dodano lokalny token API, lokalny CORS i endpoint `GET /data/status`.
- 2026-05-22: Potwierdzono blokadę instalacji `pyswisseph` bez MSVC Build Tools i dodano endpointy `GET /sky/current` oraz `POST /sky/at-date`.
- 2026-05-22: Dodano endpoint `GET /events/window` dla niezależnego pobierania historii i coverage.
- 2026-05-22: Dodano `score_breakdown` i etykiety siły rezonansu do epizodów `/resonance/search`.
