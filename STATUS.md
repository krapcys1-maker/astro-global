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
- Dodano bezpieczny runner lokalnego API: `services/api/runner.py` oraz `scripts/run_api.py`.
- Runner binduje wyłącznie do `127.0.0.1`, wybiera wolny port przy `--port 0` i odrzuca hosty typu `0.0.0.0`.
- Runner używa `ASTRO_GLOBAL_SESSION_TOKEN` albo generuje token sesji bez wypisywania jego wartości do konsoli.
- Dodano entrypoint `astro-global-api`.
- Weryfikacja runnera: `pytest tests/test_astro_global_api_runner.py` przechodzi, `6 passed`.
- Dodano persistent index store: `services/resonance/index_store.py`.
- Dodano skrypt `scripts/build_planetary_index.py`, który buduje ignorowany artifact `.npz` w `data/vectors/`.
- Builder indeksu obsługuje provider `synthetic` i ma przygotowany tryb `swiss`; bez modułu `swisseph` kończy się jawnym komunikatem zamiast budować fałszywy artifact.
- Weryfikacja persistent index: mały build `2026-01-01..2026-03-01` utworzył `data/vectors/proof_synthetic_test.npz`, `rows=9`, `dimensions=104`.
- `data/vectors/` pozostaje ignorowane przez git.
- Weryfikacja index store: `pytest tests/test_astro_global_resonance.py` przechodzi, `11 passed`.
- Endpoint `/resonance/search` może teraz użyć persistent indexu przez `index_file`.
- API przyjmuje tylko nazwę pliku `.npz` z katalogu `data/vectors/` i odrzuca path traversal.
- Persistent index jest walidowany względem profilu, wersji vectora, providera, `step_days`, startu i końca okna requestu.
- Odpowiedź `/resonance/search` zawiera `index_source` (`in_memory` albo `persistent_npz`) i `index_artifact`.
- Weryfikacja persistent index w API: `pytest tests/test_astro_global_api.py` przechodzi, `18 passed`.
- Dodano `services/historical/seeds/curated_event_sources.csv` z 8 dodatkowymi źródłami dla wybranych eventów.
- Importer łączy automatyczne źródła `wikidata_seed` z dodatkowymi źródłami curated.
- Dodane jakości źródeł obejmują `primary`, `institutional` i `encyclopedic`.
- Dla epizodu testowego 2026 `source_quality_score` wzrósł z `0.65` do `0.8333333333333334`.
- `narrative_confidence` dla epizodu testowego 2026 wzrósł z `0.7283333333333333` do `0.7833333333333333`.
- Odświeżono lokalny DuckDB przez `python scripts/ingest_curated_events.py`.
- Golden snapshot `/resonance/search` został odświeżony o dodatkowe źródła.
- Wykonano gruntowny audyt kodu, testów i danych oraz zapisano `RAPORT_AUDYTU_GRUNTOWNEGO_2026-05-22.md`.
- Aktualna bramka jakości po audycie: `pytest` przechodzi (`60 passed, 1 skipped`), `ruff` przechodzi, golden snapshot API jest aktualny, importer curated events działa w dry-run, `compileall` przechodzi.
- Wyrywkowa kontrola danych po rozszerzeniu źródeł: 50/50 URL-i z `curated_events.csv` i `curated_event_sources.csv` zwróciło HTTP 200; nie znaleziono duplikatów event IDs ani błędnych referencji w source CSV.
- Zweryfikowano persistent index proof przez zbudowanie ignorowanego `data/vectors/audit_2025_2026_synthetic.npz` i ręczny request `/resonance/search` z `index_file`, który zwrócił `index_source=persistent_npz`.
- Rozszerzono `curated_event_sources.csv` z 8 do 25 dodatkowych źródeł, tak żeby każdy event z obecnego seeda miał co najmniej jedno źródło poza automatycznym `wikidata_seed`.
- Walidacja source layer po rozszerzeniu: 25 eventów, 25 curated sources, 25/25 eventów z curated source, 0 brakujących referencji, 25/25 URL-i zwraca HTTP 200.
- Przeniesiono wagi `source_quality` z kodu do `services/narrative/source_quality.yaml`, żeby kalibracja `narrative_confidence` nie wymagała zmiany logiki.
- Dodano `--provider swiss` i opcjonalne `--ephemeris-path` do `scripts/build_planetary_index.py`; realny build nadal czeka na dostępność `swisseph`.
- Dodano `scripts/benchmark_planetary_index.py` do pomiaru czasu builda i exact search na indeksie bez zapisywania `.npz`.
- Benchmark `synthetic-dev` dla `1900-01-01..2026-05-22`, weekly, `global_slow_v1`: `6595` wierszy, `104` wymiary, macierz `5.2328 MB`, build `0.639622 s`, search `0.004595 s`.
- Rozszerzono `curated_events.csv` z 25 do 50 kontrolowanych wydarzeń, dodając warstwę 1517-1913 przed I wojną światową.
- Rozszerzono `curated_event_sources.csv` z 25 do 50 curated sources, utrzymując zasadę: każdy event ma źródło poza automatycznym `wikidata_seed`.
- Walidacja seeda po rozszerzeniu: 50 eventów, zakres 1517-2026, 50 curated sources, 0 duplikatów, 0 brakujących referencji, 100/100 URL-i zwraca HTTP 200.
- Odświeżono lokalny DuckDB przez `python scripts/ingest_curated_events.py`; coverage pokazuje 13 regionów i 14 kategorii.
- Rozszerzono `curated_events.csv` z 50 do 75 kontrolowanych wydarzeń, dodając kolejne procesy 1526-1912 z Azji, Afryki, Ameryki Południowej, Ameryki Północnej i Europy.
- Rozszerzono `curated_event_sources.csv` z 50 do 75 curated sources; utrzymany jest warunek 1 curated source poza Wikidata na każdy event.
- Walidacja seeda po drugiej partii: 75 eventów, zakres 1517-2026, 75 curated sources, 0 duplikatów, 0 brakujących referencji, 150/150 URL-i zwraca HTTP 200.
- Odświeżono lokalny DuckDB przez `python scripts/ingest_curated_events.py`; coverage pokazuje 17 regionów i 15 kategorii.
- Rozszerzono `curated_events.csv` z 75 do 100 kontrolowanych wydarzeń, wzmacniając pokrycie Afryki, Bliskiego Wschodu, Azji Południowo-Wschodniej, Azji Południowej i Ameryki Południowej.
- Rozszerzono `curated_event_sources.csv` z 75 do 100 curated sources; nadal każdy event ma dokładnie jedno dodatkowe źródło poza automatycznym `wikidata_seed`.
- Walidacja seeda po trzeciej partii: 100 eventów, zakres 1501-2026, 100 curated sources, 0 duplikatów, 0 brakujących referencji, 200/200 URL-i zwraca HTTP 200.
- `python scripts/ingest_curated_events.py --dry-run` pokazuje 22 regiony i 17 kategorii; dominujący region nadal jest jawnie raportowany jako Europa, ale bez warningu coverage.
- Wykonano gruntowny audyt po seedzie 100 i zapisano raport `RAPORT_AUDYTU_GRUNTOWNEGO_2026-05-22_SEED100.md`.
- Audyt znalazł i naprawił niespójność kolejności wyników między DuckDB a fallbackiem CSV w warstwie `event_query`.
- Dodano testy parzystości fallback vs DuckDB dla eventów i źródeł.
- Dodano `event_kind` do kontraktu wydarzeń historycznych, schema DuckDB, CSV seeda, odpowiedzi API i golden snapshotu.
- Dodano ranking historii oparty o `event_kind`, confidence, długość trwania, start roku i id; krótkie konkretne wydarzenia nie są już wypychane przez długie procesy.
- Dodano test, że w oknie 1895-1896 konkretne wydarzenia typu First Sino-Japanese War i First Italo-Ethiopian War wygrywają z długimi procesami typu Scramble for Africa.
- Dodano `source_precision` do źródeł historycznych: `direct`, `contextual`, `broad_context` oraz `structured_reference` dla automatycznego Wikidata.
- `narrative_confidence.source_quality_score` uwzględnia teraz zarówno `source_quality`, jak i `source_precision`, więc szerokie źródła kontekstowe są punktowane niżej niż źródła bezpośrednie.
- Zaktualizowano schema DuckDB, importer, fallback CSV, API i golden snapshot o `source_precision`.
- Dodano drugi, bezpośredni curated source dla wszystkich eventów, które miały `source_precision=contextual` albo `source_precision=broad_context`.
- `curated_event_sources.csv` ma teraz 107 źródeł dla 100 eventów; każdy event ma minimum jedno curated source, a słabsze źródła mają direct backup.
- Podmieniono niedostępny URL Iranica dla Persian Constitutional Revolution na działający bezpośredni URL encyklopedyczny.
- Walidacja URL-i po rozszerzeniu źródeł: 207/207 URL-i działa.
- Rozszerzono `/data/status` o diagnostykę źródeł: `curated_event_sources_count`, `source_precision_counts`, `events_without_curated_sources` i `weak_precision_events_without_direct_backup`.
- `/data/status` raportuje teraz 100 eventów, 107 curated sources, 0 eventów bez curated source i 0 słabszych źródeł bez direct backup.
- Rozszerzono `curated_events.csv` ze 100 do 125 kontrolowanych wydarzeń, głównie z lat 1945-2015 i regionów pozaeuropejskich.
- Rozszerzono `curated_event_sources.csv` ze 107 do 132 curated sources; każdy nowy event ma źródło `direct`.
- Walidacja seeda po czwartej partii: 125 eventów, 132 curated sources, 257 źródeł razem z Wikidata, 0 duplikatów, 0 brakujących referencji, 257/257 URL-i działa.
- Odświeżono lokalny DuckDB przez `python scripts/ingest_curated_events.py`; coverage pokazuje 24 regiony i 18 kategorii.
- Rozszerzono `curated_events.csv` ze 125 do 150 kontrolowanych wydarzeń, dodając m.in. konflikty i transformacje z Afryki, Ameryki Łacińskiej, Azji Południowo-Wschodniej oraz globalne instytucje i przełomy naukowe.
- Rozszerzono `curated_event_sources.csv` ze 132 do 157 curated sources; każdy nowy event ma źródło `direct`.
- Walidacja seeda po piątej partii: 150 eventów, 157 curated sources, 307 źródeł razem z Wikidata, 0 duplikatów, 0 brakujących referencji, 307/307 URL-i działa.
- Odświeżono lokalny DuckDB przez `python scripts/ingest_curated_events.py`; coverage pokazuje 26 regionów i 18 kategorii.

- Wykonano gruntowny audyt po seedzie 150 i zapisano `RAPORT_AUDYTU_GRUNTOWNEGO_2026-05-22_SEED150.md`.
- Bramka audytu: `ruff` przechodzi, `pytest` przechodzi (`69 passed, 1 skipped, 1 warning`), `compileall` przechodzi, golden snapshot `/resonance/search` jest aktualny, importer curated events dry-run przechodzi.
- Audyt danych: 150 eventow, 157 curated sources, 307 zrodel lacznie, zakres 1501-2026, 26 regionow, 18 kategorii, 0 duplikatow event IDs, 0 brakujacych referencji source CSV, 307/307 URL-i dziala.
- Potwierdzono parzystosc DuckDB i fallback CSV dla probek okien: `1895-1896`, `1975-1979`, `1997-1999`, `2011-2016`, `2020-2026`.
- Wyrywkowo sprawdzono probki danych: Green Revolution, Eritrean War of Independence, Guatemalan Civil War, Colombian conflict, Montreal Protocol, Human Genome Project, SARS outbreak, Indian Ocean tsunami, Western African Ebola epidemic, Paris Agreement i HIV/AIDS pandemic.
- Audyt nie znalazl krytycznego bledu w kodzie, ale wskazal trzy luki: Swiss Ephemeris nadal niedostepny lokalnie, dataset jest zbyt mocno zdominowany przez wojny, a eventy trwajace wymagaja jawnego `is_ongoing` albo `end_policy`.
- Dodano jawne modelowanie wydarzen trwajacych: `HistoricalEvent.is_ongoing` oraz `end_year_policy`.
- Otwarte `display_date` typu `1964-` jest teraz walidowane jako ongoing i dostaje `end_year_policy=build_year`; proba zapisania otwartego displayu jako nie-ongoing konczy sie bledem walidacji.
- Schema DuckDB, importer, query fallback/DuckDB, `/events/window`, `/resonance/search`, `/data/status`, coverage report i golden snapshot API zostaly rozszerzone o ongoing metadata.
- `/data/status` raportuje teraz `event_kind_counts`, `source_quality_counts`, `source_precision_counts`, `ongoing_events_count` i `ongoing_event_ids`.
- Lokalny DuckDB zostal odswiezony przez `python scripts/ingest_curated_events.py`; coverage raportuje `ongoing_events_count=6`.
- Weryfikacja po ongoing metadata: `ruff` przechodzi, `pytest` przechodzi, `compileall` przechodzi, golden snapshot `/resonance/search` jest aktualny.
- Dodano `scripts/validate_curated_data.py` do walidacji stabilnego porzadku `curated_events.csv`.
- Dodano helpery `curated_event_sort_key`, `sort_curated_events` i `validate_curated_events_stable_order`.
- Posortowano `curated_events.csv` po `start_astro_year`, `end_astro_year`, `id`; pierwszy wykryty problem byl przy `evt_council_of_trent` przed `evt_scientific_revolution`.
- Dodano test, ktory wymusza stabilny porzadek chronologiczny seeda historycznego.
- Weryfikacja po stable export: `python scripts/validate_curated_data.py` pokazuje `stable_order=true`, `ruff` przechodzi, `pytest` przechodzi, `compileall` przechodzi, golden snapshot `/resonance/search` jest aktualny.

## W Trakcie / Następne

1. Dodac raport biasu danych, ktory jasno pokazuje nadreprezentacje `war`, udzial source quality, source precision i pokrycie regionow.
2. Rozwiazac realny ephemeris provider: `pyswisseph` na Windows albo swiadoma alternatywa zgodna z golden JPL Horizons.
3. Po instalacji `swisseph` uruchomic `scripts/build_planetary_index.py --provider swiss` i test JPL Horizons bez skipa.
4. Zbudowac realny `1900-now weekly` na Swiss po odblokowaniu providera.
5. Balansowac seed do 200-250 eventow, ale priorytetowo poza kategoriami wojennymi.

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
- 2026-05-22: Dodano bezpieczny runner API bindujący do `127.0.0.1`.
- 2026-05-22: Dodano persistent index store i skrypt builda indeksu `.npz` dla providera syntetycznego.
- 2026-05-22: Podłączono persistent index `.npz` do `/resonance/search` przez `index_file`.
- 2026-05-22: Dodano drugi curated source layer dla wybranych eventów i podniesiono source-quality confidence.
- 2026-05-22: Wykonano gruntowny audyt projektu, danych i testów; zapisano aktualny raport oraz plan naprawczy.
- 2026-05-22: Domknięto source-quality gap dla obecnego seeda: wszystkie 25 eventów ma teraz dodatkowe curated source poza Wikidata.
- 2026-05-22: Dodano konfigurowalne wagi source quality w YAML i test ich ładowania.
- 2026-05-22: Przygotowano builder persistent indexu pod provider Swiss oraz zweryfikowano jawny błąd, gdy `swisseph` nie jest dostępny.
- 2026-05-22: Dodano benchmark indeksu i zmierzono synthetic `1900-now weekly` dla `global_slow_v1`.
- 2026-05-22: Rozszerzono curated historical seed do 50 eventów i 50 dodatkowych źródeł.
- 2026-05-22: Rozszerzono curated historical seed do 75 eventów i 75 dodatkowych źródeł.
- 2026-05-22: Rozszerzono curated historical seed do 100 eventów i 100 dodatkowych źródeł.
- 2026-05-22: Wykonano audyt seed 100; naprawiono parzystość sortowania DuckDB i CSV fallback.
- 2026-05-22: Dodano `event_kind` i ranking historii chroniący krótkie wydarzenia przed dominacją długich procesów.
- 2026-05-22: Dodano `source_precision` i obniżanie confidence dla szerokich źródeł kontekstowych.
- 2026-05-22: Dodano bezpośrednie backup sources dla eventów z contextual/broad_context i zweryfikowano 207/207 URL-i.
- 2026-05-22: Dodano diagnostykę jakości źródeł do `/data/status`.
- 2026-05-22: Rozszerzono curated historical seed do 125 eventów i 132 curated sources.
- 2026-05-22: Rozszerzono curated historical seed do 150 eventów i 157 curated sources.
- 2026-05-22: Wykonano gruntowny audyt seed 150; zapisano raport, potwierdzono bramke jakosci i wskazano nastepny krok: `is_ongoing` / `end_policy` oraz szersza diagnostyka danych.
- 2026-05-22: Dodano `is_ongoing` i `end_year_policy` do warstwy historycznej, API, DuckDB, coverage report i testow; odswiezono golden snapshot.
- 2026-05-23: Dodano walidator/stable export dla `curated_events.csv`, posortowano seed i zabezpieczono porzadek testem.
