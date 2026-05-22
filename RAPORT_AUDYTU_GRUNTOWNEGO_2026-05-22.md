# Raport Gruntownego Audytu - Astro Global

Data audytu: 2026-05-22  
Repo: `krapcys1-maker/astro-global`  
Branch: `astro-global`  
Folder roboczy: `D:\astro Global`

## Werdykt

Idziemy w dobrym kierunku, ale to nadal jest backend proof/MVP core, nie gotowy produkt merytoryczny. Architektura jest zdrowa: rdzen danych, reguly, search, historia, confidence i API sa testowalne oraz rozdzielone. Najwieksza luka pozostaje ta sama: realne efemerydy Swiss Ephemeris nie dzialaja jeszcze w runtime na tej maszynie, wiec produktowe wyniki astronomiczne nie moga opierac sie na obecnym providerze `synthetic-dev`.

Status decyzyjny:

- GO: dalsze wzmacnianie backend core, danych historycznych, source quality, index store i testow.
- HOLD: UI/Tauri, DeepSeek narrative layer, packaging desktop, FAISS/HNSW, masowy Wikidata import.
- BLOCKER przed realnym MVP: uruchomienie prawdziwego ephemeris providera albo swiadoma decyzja o alternatywie walidowanej fixture JPL Horizons.

## Sprawdzone Bramy Jakosci

Wykonane lokalnie:

```bash
pytest
python -m ruff check services tests scripts
python scripts/update_resonance_api_golden.py --check
python scripts/ingest_curated_events.py --dry-run
python -m compileall services scripts tests
python scripts/build_planetary_index.py --start 2025-01-15 --end 2026-01-15 --step-days 7 --output data\vectors\audit_2025_2026_synthetic.npz
```

Wyniki:

- `pytest`: `60 passed, 1 skipped`.
- `ruff`: bez bledow.
- golden snapshot `/resonance/search`: aktualny.
- importer curated events: `25` eventow zaladowanych w dry-run.
- `compileall`: bez bledow skladni.
- persistent index proof: `53` wiersze, `104` wymiary, provider `synthetic-dev`.
- reczny test `/resonance/search` z `index_file=audit_2025_2026_synthetic.npz`: HTTP `200`, `index_source=persistent_npz`.

## Co Mamy

### Repo i porzadek

- Projekt jest w poprawnym folderze `D:\astro Global`.
- Remote jest poprawny: `krapcys1-maker/astro-global`.
- Branch roboczy jest poprawny: `astro-global`.
- `.env`, cache, buildy i indeksy sa ignorowane.
- Nie widac pracy w starym `astroapp`; obecny `git status` jest czysty poza ignorowanymi artefaktami.

### Backend core

Mamy dzialajace elementy:

- `services/` jako pakiet backendu.
- Pydantic contracts.
- `SwissEphemerisProvider` jako docelowy provider.
- `SyntheticEphemerisProvider` jako deterministyczny proof provider.
- AstroRulesEngine: katy, aspekty, znaki, retrograde, ingress/station proximity.
- `cycle_registry.yaml`.
- vectorizer `global_slow_v1`.
- scoring z rozdzieleniem `planetary_resonance_score` od historii.
- exact search.
- episode clustering.
- score labels: `strong`, `moderate`, `weak`, `rare_configuration`, `insufficient_comparable_history`.

### API

Dziala:

- `GET /health`.
- `GET /data/status`.
- `GET /sky/current`.
- `POST /sky/at-date`.
- `GET /events/window`.
- `POST /resonance/search`.

Security:

- endpointy poza `/health` wymagaja tokenu sesji,
- CORS jest ograniczony do lokalnych originow dev/Tauri,
- runner binduje tylko do `127.0.0.1`,
- runner odrzuca `0.0.0.0`,
- token nie jest wypisywany do konsoli.

### Historia i zrodla

Mamy:

- DuckDB schema dla eventow, zrodel, indexu, runow i cache narracji.
- `curated_events.csv` z 25 eventami.
- `curated_event_sources.csv` z 8 dodatkowymi zrodlami.
- automatyczne `wikidata_seed` dla kazdego eventu.
- dodatkowe typy jakosci zrodel: `primary`, `institutional`, `encyclopedic`.
- `event_coverage`.
- `narrative_confidence`.
- zrodla zwracane w API przy `matched_events`.

Statystyka danych:

- eventy: `25`.
- zakres lat: `1914-2026`.
- duplikaty `id`: brak.
- dodatkowe zrodla curated: `8`.
- eventy z dodatkowym zrodlem poza Wikidata: `8/25`.
- eventy tylko z `wikidata_seed`: `17/25`.
- nieznane referencje w pliku zrodel: brak.
- bledne zakresy lat: brak.

Kategorie:

- `war`: 7,
- `revolution`: 3,
- `economic_crisis`: 3,
- `geopolitical_crisis`: 2,
- `geopolitical_transition`: 2,
- `disaster`: 2,
- `terrorism`: 2,
- `epidemic`: 1,
- `institution`: 1,
- `political_referendum`: 1,
- `science_technology`: 1.

Regiony:

- `Global`: 10,
- `East Asia`: 3,
- `Middle East`: 3,
- `Eastern Europe`: 2,
- `Eurasia`: 2,
- `Europe`: 2,
- `Middle East and North Africa`: 1,
- `North America`: 1,
- `Southeast Asia`: 1.

### Narracja

Mamy polskie `deterministic_summary`, bez DeepSeek. Dobrze, ze AI nie jest zrodlem prawdy. Summary referencjonuje tylko eventy z wejscia, a testy pilnuja, ze nie wychodzi poza `matched_events`.

## Wyrywkowa Kontrola Danych

Sprawdzilem technicznie wszystkie URL-e z `curated_events.csv` i `curated_event_sources.csv`: 33/33 zwrocily HTTP `200`.

Manualnie sprawdzone probki:

- `evt_world_war_i`: Britannica potwierdza zakres `1914-1918`; nasz CSV ma `1914-1918`.
- `evt_world_war_ii`: Britannica potwierdza zakres `1939-1945`; nasz CSV ma `1939-1945`.
- `evt_great_depression`: Britannica opisuje start w 1929 i trwanie do okolo 1939; nasz CSV ma `1929-1939`.
- `evt_united_nations`: Britannica wskazuje ustanowienie ONZ `October 24, 1945`; nasz CSV ma `1945`.
- `evt_covid_19_pandemic`: WHO potwierdza strone COVID-19 i biezacy charakter tematu; nasz CSV ma `2019-2026`.
- `evt_russian_invasion_ukraine`: Britannica potwierdza pelnoskalowa inwazje `February 24, 2022`; nasz CSV ma `2022-2026`.
- `evt_october_7_attacks`: dodatkowy URL curated source jest poprawny i zwraca HTTP 200 pod `https://www.britannica.com/event/October-7-attack`; nasz CSV uzywa tego poprawnego adresu.

Nie znalazlem w probkach oczywistego bledu daty, duplikatu albo martwego URL-a. Znalazlem natomiast ograniczenie modelu: trwajace eventy maja dzis `end_astro_year=2026`, co jest akceptowalne jako snapshot na date audytu, ale wymaga polityki aktualizacji przy kolejnych buildach.

## Znalezione Luki i Ryzyka

### P1 - Realny ephemeris runtime nadal jest zablokowany

Kod Swiss providera istnieje, ale lokalne srodowisko nie ma dzialajacego `swisseph`. Wczesniejsza proba instalacji `pyswisseph` na Windows/Python 3.12 wymagala Microsoft Visual C++ Build Tools. Test JPL Horizons jest gotowy, ale pozostaje skipowany bez modulu `swisseph`.

Plan naprawczy:

1. Doinstalowac Microsoft Visual C++ Build Tools albo przejsc na wersje Pythona/srodowisko z gotowym wheel.
2. Uruchomic `python -m pip install -e .[astro]`.
3. Uruchomic test JPL Horizons bez skipa.
4. Przelaczyc smoke/API na Swiss w kontrolowanym trybie.
5. Zostawic `SyntheticEphemerisProvider` tylko do deterministycznych testow.

### P1 - Wyniki produktowe nie moga jeszcze opierac sie na `synthetic-dev`

Search, clustering i API dzialaja, ale astronomiczna zawartosc `synthetic-dev` jest techniczna, nie merytoryczna.

Plan naprawczy:

1. Nie zaczynac UI jako glownego toru.
2. Nie dodawac DeepSeek jako glownego toru.
3. Najpierw doprowadzic realny provider i indeks 1900-now.

### P2 - Seed historii jest za maly

25 eventow wystarcza do testow, ale nie do aplikacji historycznej. Zakres zaczyna sie od 1914, a plan MVP wymaga minimum 1500-now.

Plan naprawczy:

1. Rozszerzac `curated_events.csv` partiami po 25-50 eventow.
2. Kazda partia: walidacja CSV, zrodla, coverage report, testy.
3. Najpierw dojsc do 100-150 eventow reprezentujacych 1500-2026.
4. Dopiero potem planowac 500-1500 eventow.

### P2 - Wiekszosc eventow nadal ma tylko Wikidata jako zrodlo

8/25 eventow ma dodatkowe curated source. Pozostale 17 ma tylko `wikidata_seed`. To wystarcza do proofu, ale nie do wysokiego `narrative_confidence`.

Plan naprawczy:

1. Dodac drugie zrodlo dla pozostalych 17 eventow.
2. Dla eventow w narracji wymagac minimum jednego nie-Wikidata zrodla dla wysokiego confidence.
3. Przeniesc wagi `source_quality` z kodu do konfiguracji `source_quality.yaml`.

### P2 - Brakuje realnego indeksu 1900-now / 1500-now

Persistent `.npz` dziala technicznie, ale tylko na proof indexie synthetic.

Plan naprawczy:

1. Po uruchomieniu Swiss zbudowac `1900-now weekly`.
2. Dodac resume/progress do buildera.
3. Dodac benchmark czasu i rozmiaru.
4. Po stabilizacji rozszerzyc do `1500-now weekly`.
5. Dodac daily refinement dla top candidates.

### P2 - Dokumentacja audytu byla czesciowo przestarzala

Starszy `RAPORT_AUDYTU_ASTRO_GLOBAL.md` nadal zawiera stare liczby testow i stan sprzed kilku commitow. Ten dokument jest aktualnym raportem gruntownym.

Plan naprawczy:

1. Traktowac ten raport jako aktualne zrodlo stanu.
2. Przy kolejnym porzadkowaniu dopisac na poczatku starego raportu, ze zostal zastapiony.
3. Aktualizowac `STATUS.md` po kazdym wiekszym kroku.

### P3 - Ongoing events wymagaja polityki dat

Eventy typu COVID-19 i wojna Rosja-Ukraina maja `end_astro_year=2026`. To jest poprawne jako snapshot audytu, ale za rok bedzie przestarzale.

Plan naprawczy:

1. Dodac pole `is_ongoing` albo `end_date_precision`.
2. Przy buildzie danych ustawic end na date buildu dla ongoing.
3. W UI pokazywac `2019-` / `2022-`, a nie sztuczne domkniecie.

### P3 - Brakuje endpointu narracji AI

`POST /narrative/generate` nadal nie istnieje. To nie jest blokada, bo DeepSeek jest HOLD.

Plan naprawczy:

1. Najpierw realny provider i index.
2. Potem mockowany `DeepSeekClient`.
3. Dopiero potem prawdziwy DeepSeek z walidacja JSON i fallbackiem do deterministic summary.

## Co Nie Wyszlo Jako Problem

- Nie znaleziono duplikatow event IDs.
- Nie znaleziono zlych referencji `event_id` w `curated_event_sources.csv`.
- Nie znaleziono martwych URL-i w obecnym seedzie.
- Nie znaleziono `TODO/FIXME/HACK` w kodzie.
- Nie znaleziono niebezpiecznego `eval()`/`exec()` w kodzie.
- `np.load` uzywa `allow_pickle=False`, czyli dobrze.
- `0.0.0.0` pojawia sie tylko w testach/security guardrail, nie jako domyslny bind.

## Najbardziej Logiczny Kolejny Krok

Najbardziej logiczny kolejny krok po tym audycie to nie UI i nie DeepSeek, tylko:

1. Rozwiazac instalacje `swisseph` na Windows.
2. Uruchomic test Swiss vs JPL Horizons bez skipa.
3. Dodac provider Swiss do `scripts/build_planetary_index.py`.
4. Zbudowac pierwszy realny proof index `1900-now weekly`.

Jesli instalacja Swiss nadal bedzie blokowala prace, najlepszy krok zastepczy to rozszerzyc historyczny seed i curated sources do minimum 50-75 eventow, bo to poprawia wartosc API bez ryzyka mieszania warstw.
