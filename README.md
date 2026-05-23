# Astro Global

Astro Global to lokalna aplikacja desktopowa do eksploracji historycznych rezonansów planetarnych. System porównuje aktualną globalną konfigurację planet z podobnymi układami z historii, łączy je z kontrolowaną bazą wydarzeń i generuje polską narrację interpretacyjną.

Projekt nie jest horoskopem natalnym, nie analizuje użytkownika i nie jest modelem predykcyjnym. To narzędzie do symbolicznej, historycznej eksploracji cykli.

## Zasady Pracy

1. Najpierw działa pipeline, potem UI, a AI na końcu.
2. Astronomia jest deterministyczna: pozycje i prędkości liczy Swiss Ephemeris / pyswisseph, a aspekty, orby, scoring i cykle liczymy w naszym kodzie.
3. Historia pochodzi z kontrolowanych danych: curated CSV + DuckDB, potem Wikidata/Wikimedia jako enrichment.
4. DeepSeek V4 Pro jest narratorem, nie źródłem faktów.
5. Każdy fakt historyczny w narracji musi mieć `event_id` i źródło.
6. Szybkie planety nie mogą dominować globalnego scoringu historycznego.
7. Rzadkość cyklu, waga astrologiczna i pewność historyczna są osobnymi miarami.
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

- `PLAN_PRAC_ASTRO_GLOBAL.md` - szczegółowy plan wdrożenia.
- `TEST_PLAN_ASTRO_GLOBAL.md` - testy silników, wyszukiwarki, scoringu i guardraili.
- `STATUS.md` - bieżący status, decyzje i postępy prac.
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
GET /data/status
GET /sky/current
POST /sky/at-date
GET /events/window
POST /resonance/search
```

`/health` działa bez tokenu. Pozostałe endpointy lokalnego API wymagają tokenu w
nagłówku `x-astro-global-session` albo `Authorization: Bearer`.
Domyślny token developerski to `dev-local-token`; docelowo Tauri sidecar ma generować
token sesji i przekazywać go frontendowi bez zapisu w repo.

`/data/status` raportuje aktualny stan runtime: dostępność providera synthetic/Swiss,
liczbę curated events, ścieżkę DuckDB, fallback CSV oraz konfigurację lokalnego CORS.

`/sky/current` i `/sky/at-date` zwracają stan planetarny dla wybranego providera.
Na dziś stabilny runtime to `synthetic`; `provider: "swiss"` jest obsługiwany przez API,
ale zwróci `503`, jeśli lokalnie nie ma modułu `swisseph`.

`/events/window` zwraca kontrolowane wydarzenia historyczne z danego zakresu lat,
ich źródła oraz coverage report. Dzięki temu UI/debug może pokazać kontekst
historyczny bez uruchamiania pełnego `/resonance/search`.

Na tym etapie endpoint używa deterministycznego providera `synthetic-dev`, żeby testować kontrakt API, vectorizer, exact search i episode clustering bez blokowania prac przez lokalną instalację Swiss Ephemeris. Swiss Ephemeris pozostaje docelowym providerem pozycji planetarnych.

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
```

Persistent proof index można zbudować w formacie `.npz`:

```bash
python scripts/build_planetary_index.py --start 2026-01-01 --end 2026-03-01 --step-days 7 --output data/vectors/proof_synthetic_test.npz
```

Pliki w `data/vectors/` są ignorowane przez git. Na dziś builder obsługuje provider
`synthetic`, żeby testować format indeksu; po rozwiązaniu Swiss Ephemeris ten sam
kontrakt zapisu/odczytu zostanie użyty dla realnego indeksu.

`/resonance/search` może użyć persistent indexu przez pole requestu `index_file`, np.
`"index_file": "proof_synthetic_global_slow_v1.npz"`. API przyjmuje tylko nazwę pliku
`.npz` z katalogu `data/vectors/`, waliduje metadane indeksu względem requestu i w
odpowiedzi zwraca `index_source` oraz `index_artifact`.

## Decyzje Potwierdzone

- Repo: `krapcys1-maker/astro-global`
- Branch roboczy: `astro-global`
- Nazwa produktu: `Astro Global`
- Widoczność GitHub: publiczne repo
- Charakter produktu: prywatny/lokalny projekt na tym etapie
- Język UI i narracji: polski
- AI: DeepSeek online dozwolony dla narracji

## Aktualny Status

Bieżący stan prac zapisujemy w `STATUS.md`. Ten plik powinien być aktualizowany po każdym większym kroku, szczególnie po zmianach architektury, implementacji modułów, testach i decyzjach produktowych.
