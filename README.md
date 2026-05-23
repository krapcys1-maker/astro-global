# Astro Global

Aktualizacja 2026-05-23: produkt pozostaje API-first i lokalny tryb nadal sluzy do
debugowania rdzenia, ale docelowy kierunek przesuwa sie w strone publicznej wersji
web/server po dodaniu guardraili produkcyjnych. Publiczny UX ma byc bardziej
`astrological history research desk` niz horoskop online.

Astro Global to aplikacja API-first do astrologicznej eksploracji historycznych rezonansów planetarnych. Lokalny backend/desktop pozostaje trybem developerskim i proofem rdzenia, a docelowy kierunek produktu to publiczny web/server po dodaniu guardraili produkcyjnych. Rdzeniem produktu jest astrologia mundalna: cykle planetarne, aspekty, fazy, rzadkość konfiguracji i ich symboliczna interpretacja. Warstwa historyczna służy jako materiał porównawczy i kontekstowy, a nie jako osobny główny produkt.

Projekt nie jest horoskopem natalnym, nie analizuje użytkownika i nie jest modelem predykcyjnym. To narzędzie do symbolicznej, historycznej eksploracji cykli.

## Zasady Pracy

1. Najpierw działa astrologiczny pipeline rezonansów, potem UI, a AI na końcu.
2. Astronomia jest deterministyczna: pozycje i prędkości liczy Swiss Ephemeris / pyswisseph, a aspekty, orby, scoring i cykle liczymy w naszym kodzie.
3. Historia pochodzi z kontrolowanych danych: curated CSV + DuckDB, potem Wikidata/Wikimedia jako enrichment.
4. DeepSeek V4 Pro jest narratorem, nie źródłem faktów.
5. Każdy fakt historyczny w narracji musi mieć `event_id` i źródło.
6. Szybkie planety nie mogą dominować globalnego scoringu historycznego.
7. Rzadkość cyklu, waga astrologiczna i pewność historyczna są osobnymi miarami; waga astrologiczna pozostaje najważniejszym kontekstem interpretacji.
8. Repo jest publiczne, więc nie commitujemy `.env`, kluczy API, cache, indeksów ani prywatnych danych.
9. UI i narracja są po polsku.
10. Każdy etap kończy się testem lub smoke testem, nie samym opisem.
11. Nie ufamy modelowi w ciemno: każdy silnik ma golden tests, negative controls albo snapshot regresyjny.

## Definicja Sukcesu MVP

MVP uznajemy za udane, gdy lokalnie działa przepływ:

```txt
current sky
  -> planetary state
  -> vector global_slow_v1
  -> exact historical search
  -> episode clustering
  -> curated historical events
  -> deterministic Polish summary
  -> optional DeepSeek narrative with validation
```

Minimalny wynik z `/resonance/search` musi zawierać:

- aktualny stan planetarny,
- niezależne epizody historyczne, nie duplikaty sąsiednich dni,
- `score`, `percentile`, `label` i `window_tag`,
- główne cykle: `primary_cycles`, `supporting_cycles`, `cycle_tier`,
- matched features z orbami i wkładem do wyniku,
- wydarzenia historyczne ze źródłem i confidence,
- podsumowanie bez języka predykcyjnego.

## Czego Nie Robimy W MVP

- Nie budujemy własnego silnika orbit.
- Nie zaczynamy od Tauri UI przed działającym backendem.
- Nie używamy FAISS/HNSW, dopóki exact search wystarcza.
- Nie pozwalamy AI wymyślać faktów.
- Nie traktujemy `rare` jako automatycznie `strong`.
- Nie pokazujemy `0 CE`; BCE obsługujemy przez astronomical year numbering wewnętrznie i historyczny display w UI.

## Główne Etapy

1. Dokumentacja i kontrakty domenowe.
2. Python package, `pyproject.toml`, `pytest`.
3. SwissEphemerisProvider.
4. AstroRulesEngine: kąty, znaki, aspekty, ingress, retrograde.
5. `cycle_registry.yaml` i `cycle_power_score`.
6. Vectorizer `global_slow_v1`.
7. Indeks 1900-dziś jako szybki proof, potem 1500-dziś.
8. Exact search i episode clustering.
9. DuckDB + curated historical events.
10. FastAPI local sidecar.
11. Deterministic summary po polsku.
12. DeepSeek V4 Pro narrative layer.
13. Tauri 2 + React UI.

## Pliki Projektowe

- `WEB_PRODUCT_STRUCTURE_ASTRO_GLOBAL.md` - docelowa struktura publicznej strony, routes, UX i mapping do backendu.
- `contracts/WEB_API_CLIENT_CONTRACT.md` - granice cienkiego klienta API i dozwolone endpointy web/Tauri.
- `contracts/openapi_astro_global.json` - snapshot OpenAPI eksportowany z FastAPI i sprawdzany w CI.
- `web/README.md` - pierwszy statyczny web shell, ktory konsumuje FastAPI bez przenoszenia logiki backendu.
- `DEPLOYMENT_RUNBOOK_ASTRO_GLOBAL.md` - minimalny kontrakt deploy/server: env vars, smoke checks, monitoring i abuse response.
- `PLAN_PRAC_ASTRO_GLOBAL.md` - szczegółowy plan wdrożenia.
- `TEST_PLAN_ASTRO_GLOBAL.md` - testy silników, wyszukiwarki, scoringu i guardraili.
- `STATUS.md` - bieżący status, decyzje i postępy prac.
- `WEB_READY_PLAN_ASTRO_GLOBAL.md` - zasady budowania desktopu tak, żeby późniejszy web nie wymagał przepisywania rdzenia.
- `pomysl.md` - notatki produktowe o przyszłych modułach pobocznych wokół głównego silnika astrologicznego.
- `architektura.md` - bazowa architektura techniczna.
- `zarys.md` - pierwotny opis produktu.

## Środowisko Python

Projekt wspiera Python `3.11+`. Dla Windows-first i realnego Swiss Ephemeris zalecane
jest lokalne `.venv` na Pythonie 3.11, bo `pyswisseph` ma gotowy wheel dla `cp311`
i nie wymaga wtedy lokalnego kompilowania C extension:

```powershell
& "D:\AI\Stability Matrix\Assets\Python\cpython-3.11.13-windows-x86_64-none\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e .[dev,astro]
.\.venv\Scripts\python.exe -c "import swisseph; print(swisseph.__version__)"
```

Jeśli lokalny launcher `py -3.11` nie widzi Pythona 3.11, użyj bezpośredniej ścieżki
do instalacji 3.11. `.venv/` jest ignorowany przez git.

## Bramka Jakości

MVP nie jest uznane za gotowe, dopóki nie przechodzą:

```bash
pytest
python scripts/smoke_test_pipeline.py --date 2020-01-12 --profile global_slow_v1
python scripts/smoke_test_pipeline.py --date 2020-12-21 --profile global_slow_v1
python scripts/smoke_test_pipeline.py --date now --profile global_slow_v1
```

Testy mają potwierdzić nie tylko happy path, ale też przypadki negatywne: brak mocnych cykli, zbyt częste aktywatory, brak eventów, halucynacje AI i duplikaty tego samego tranzytu.

## Lokalny Endpoint Core

Backend proof udostępnia pierwszy endpoint:

```bash
$env:ASTRO_GLOBAL_SESSION_TOKEN="dev-local-token"
python scripts/run_api.py --port 8765
```

Runner zawsze binduje API do `127.0.0.1`. Jeśli port nie zostanie podany, wybiera wolny
port lokalny. Jeśli `ASTRO_GLOBAL_SESSION_TOKEN` nie jest ustawiony, generuje token sesji,
ustawia go dla procesu API i nie wypisuje wartości tokenu do konsoli.

```http
GET /health
GET /readiness
GET /today
GET /data/status
GET /sky/current
POST /sky/at-date
GET /events/window
POST /resonance/search
POST /resonance/compare
GET /resonance/compare/presets
GET /articles/seeds
```

`/health` działa bez tokenu. Pozostałe endpointy lokalnego API wymagają tokenu w
nagłówku `x-astro-global-session` albo `Authorization: Bearer`.
Domyślny token developerski to `dev-local-token`; docelowo Tauri sidecar ma generować
token sesji i przekazywać go frontendowi bez zapisu w repo.

`/data/status` raportuje aktualny stan runtime: dostępność providera synthetic/Swiss,
liczbę curated events, ścieżkę DuckDB, fallback CSV oraz konfigurację lokalnego CORS.

`/readiness` jest chronionym endpointem deploy/runtime readiness. Sprawdza produktowa
sciezke Swiss + DuckDB + curated data + reliable Swiss index 1500-now. Zwraca `200`,
gdy backend jest gotowy, albo `503` z lista checkow, gdy brakuje np. DuckDB albo
`data/vectors/swiss_1500_now_global_slow_v1.npz`.

`/today` jest chronionym dziennym snapshotem backendu. Zwraca date UTC, cache window,
zakres reliable history oraz `recommended_search_request`, ktory cienki klient moze
wyslac do `/resonance/search` bez liczenia czegokolwiek po stronie UI.

`/resonance/compare` jest chronionym, deterministycznym porownaniem dwoch dat. Backend
uruchamia dwie sciezki `/resonance/search`, liczy podobienstwo wektorow zapytania,
wspolne cykle i wspolne `matched_events`/`context_events`; cienki klient tylko renderuje
otrzymany JSON.

`/resonance/compare/presets` zwraca backendowe presety porownan zbudowane z curated
events. Daty presetow sa kotwiczone w roku startowym eventu (`YYYY-01-01T00:00:00Z`),
bo obecna warstwa curated ma precyzje roczna dla tych przypadkow.

`/articles/seeds` zwraca tylko seed-only katalog tematow oparty o backendowe compare
presets i curated events. Nie generuje artykulow, nie dodaje faktow i wymaga recenzji
redakcyjnej przed publikacja.

Tryb produkcyjny wlacza sie przez `ASTRO_GLOBAL_ENV=production`. W tym trybie backend
nie uzywa `dev-local-token` ani lokalnego CORS jako fallbacku: wymagane sa
`ASTRO_GLOBAL_SESSION_TOKEN` oraz jawne `ASTRO_GLOBAL_CORS_ORIGINS`, rozdzielone
przecinkami. Wildcard `*` w CORS jest odrzucany.

Rate limit wlacza sie domyslnie w trybie produkcyjnym i jest wylaczony lokalnie.
Mozna go ustawic przez `ASTRO_GLOBAL_RATE_LIMIT_ENABLED=true/false` oraz
`ASTRO_GLOBAL_RATE_LIMIT_PER_MINUTE`; `/health` i `/readiness` pozostaja poza limitem,
zeby monitoring i deploy checks nie byly blokowane przez ruch uzytkownika.

Limit rozmiaru requestu jest ustawiany przez `ASTRO_GLOBAL_MAX_REQUEST_BYTES`
(`65536` domyslnie). Za duze payloady sa odrzucane statusem `413`, zanim wejda w
walidacje endpointow takich jak `/resonance/search`.

`/sky/current` i `/sky/at-date` zwracają stan planetarny dla wybranego providera.
Provider `swiss` działa w lokalnym `.venv` na Pythonie 3.11 z `pyswisseph`; provider
`synthetic` zostaje tylko do deterministycznych testów i proofów.

`/events/window` zwraca kontrolowane wydarzenia historyczne z danego zakresu lat,
ich źródła oraz coverage report. Dzięki temu UI/debug może pokazać kontekst
historyczny bez uruchamiania pełnego `/resonance/search`.

Domyślna ścieżka produktu ma używać Swiss Ephemeris jako providera astronomicznego.
Deterministyczny provider `synthetic-dev` służy do testów kontraktu API, vectorizera,
exact search i episode clusteringu.

Odpowiedź `/resonance/search` zawiera teraz przy każdym epizodzie:

- `matched_events` z kontrolowanej bazy historycznej DuckDB albo fallbacku curated CSV,
- `sources` przy każdym wydarzeniu, z `source_quality`,
- `score_breakdown` z `planetary_resonance_score`, etykietą `strong/moderate/weak/rare_configuration/insufficient_comparable_history` i flagą rzadkiej konfiguracji,
- `event_coverage` z liczbą wydarzeń, kategoriami, regionami i ostrzeżeniem o biasie pokrycia.
- `narrative_confidence` przy każdym epizodzie, liczone z coverage, jakości źródeł i confidence eventów.
- `deterministic_summary`, czyli polski opis oparty wyłącznie o JSON odpowiedzi.

Eventy historyczne są opisem kontekstu, nie składnikiem `planetary_resonance_score`.
Summary deterministyczne nie używa DeepSeek i nie może dopisywać `event_id` spoza
`matched_events`.

Dane startowe są rozdzielone na:

- `services/historical/seeds/curated_events.csv` - ręcznie kontrolowane eventy,
- `services/historical/seeds/curated_event_sources.csv` - dodatkowe źródła dla wybranych eventów.

Importer zawsze generuje źródło `wikidata_seed` z `source_url` eventu, a dodatkowy plik
pozwala podnieść jakość źródeł przez wpisy `primary`, `institutional` albo
`encyclopedic`.

Golden snapshot kontraktu API aktualizujemy wyłącznie świadomie:

```bash
python scripts/update_resonance_api_golden.py
python scripts/update_resonance_api_golden.py --check
python scripts/update_resonance_compare_golden.py
python scripts/update_resonance_compare_golden.py --check
python scripts/update_resonance_compare_presets_golden.py
python scripts/update_resonance_compare_presets_golden.py --check
python scripts/update_article_seeds_golden.py
python scripts/update_article_seeds_golden.py --check
python scripts/export_openapi_contract.py
python scripts/export_openapi_contract.py --check
```

Persistent index można zbudować w formacie `.npz`:

```bash
python scripts/build_planetary_index.py --start 2026-01-01 --end 2026-03-01 --step-days 7 --output data/vectors/proof_synthetic_test.npz
```

Pliki w `data/vectors/` są ignorowane przez git. Pełny realny indeks Swiss 1900-now
został zbudowany lokalnie jako `data/vectors/swiss_1900_now_global_slow_v1.npz`.
Provider `synthetic` zostaje do testów, a provider `swiss` jest ścieżką produktu.

`/resonance/search` może użyć persistent indexu przez pole requestu `index_file`, np.
`"index_file": "proof_synthetic_global_slow_v1.npz"`. API przyjmuje tylko nazwę pliku
`.npz` z katalogu `data/vectors/`, waliduje metadane indeksu względem requestu i w
odpowiedzi zwraca `index_source` oraz `index_artifact`.

Produktowy smoke test realnej sciezki Swiss/API mozna uruchomic po zbudowaniu indeksu
`data/vectors/swiss_1900_now_global_slow_v1.npz` albo reliable indexu
`data/vectors/swiss_1500_now_global_slow_v1.npz`:

```bash
python scripts/smoke_test_deploy_config.py
python scripts/smoke_test_web_shell.py
python scripts/smoke_test_product_path.py
python scripts/pre1900_quality_audit.py --check-regressions
```

Deploy config smoke sprawdza produkcyjne env guardrails: token, CORS, readiness,
rate limit i request-size limit. Web shell smoke pilnuje, zeby statyczny klient nie
czytal danych ani indeksow poza API. Product smoke przechodzi przez FastAPI, provider
`swiss`, persistent index `.npz`, DuckDB event layer, zrodla wydarzen, `score_breakdown`,
`narrative_confidence` i deterministic summary. Pre-1900 quality audit sprawdza
28 recznie wybranych dat 1500-1900 przez `/resonance/search`, zapisuje raporty
`work/reports/pre1900_quality_audit.md/json` i failuje tylko na oznaczonych regresjach.

## Decyzje Potwierdzone

- Repo: `krapcys1-maker/astro-global`
- Branch roboczy: `astro-global`
- Nazwa produktu: `Astro Global`
- Widoczność GitHub: publiczne repo
- Charakter produktu: API-first; lokalny/dev teraz, publiczny web/server po guardrailach
- Język UI i narracji: polski
- AI: DeepSeek online dozwolony dla narracji

## Aktualny Status

Aktualny kierunek produktu: publiczny web/server jako docelowy tryb po dodaniu
guardraili produkcyjnych. Kontrakt `/resonance/search` ma byc dalej zrodlem prawdy dla
Explorera; epizody rozdzielaja teraz `matched_events` od `context_events`, zeby szerokie
tlo historyczne nie konkurowalo z bezposrednimi dopasowaniami.

Bieżący stan prac zapisujemy w `STATUS.md`. Ten plik powinien być aktualizowany po każdym większym kroku, szczególnie po zmianach architektury, implementacji modułów, testach i decyzjach produktowych.
