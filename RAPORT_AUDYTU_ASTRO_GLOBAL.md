# Raport Audytu - Astro Global

Data audytu: 2026-05-22  
Repo: `krapcys1-maker/astro-global`  
Branch: `astro-global`  
Folder roboczy: `D:\astro Global`

## Werdykt

Idziemy w dobrym kierunku.

Projekt zachowuje najważniejszą decyzję architektoniczną: najpierw deterministyczny rdzeń danych, dopiero potem UI i AI. Obecny stan jest sensownym backend proof/MVP core, ale nie jest jeszcze produkcyjnym MVP, bo najważniejsza astronomia nadal działa w praktyce na providerze syntetycznym, a nie na pełnym Swiss Ephemeris.

Status decyzyjny:

- GO: dalszy backend core, dane historyczne, confidence, source guardrails, indeks realnych efemeryd.
- HOLD: Tauri UI jako główny tor, DeepSeek narrative layer, packaging desktop, FAISS/HNSW, masowy import Wikidata.
- BLOCKER przed prawdziwym MVP: uruchomienie realnego ephemeris providera albo świadoma decyzja o alternatywnym providerze na Windows.

Aktualizacja po audycie: plan scoringu został poprawiony, `/resonance/search` zwraca już `narrative_confidence` per epizod, a API ma lokalny token sesji, local-only CORS i `GET /data/status`. Główne blokery po tej poprawce to nadal realny ephemeris runtime i persistent proof index.

## Co Zostało Wdrożone

### Repo i higiena

- Repo działa w poprawnym folderze `D:\astro Global`.
- Właściwy remote to `https://github.com/krapcys1-maker/astro-global.git`.
- Branch roboczy to `astro-global`.
- Repo jest publiczne.
- `.env` jest ignorowany i nie powinien trafić do repo.
- Błędny kierunek pracy w starym `astroapp` został porzucony.

### Kontrakty domenowe

- Jest pakiet Python `services/`.
- Są modele Pydantic dla pozycji planetarnych, stanu planetarnego, eventów i odpowiedzi API.
- Jest rozdział:
  - ephemeris provider: pozycje/prędkości,
  - astro rules: kąty/aspekty/znaki/retrograde,
  - resonance: vectorizer/search/scoring,
  - historical: eventy/source/coverage,
  - narrative: deterministic summary.

### Astro rules i vectorizer

- Działa `angular_distance_deg`, w tym wrap-around.
- Działają znaki, aspekty, retrograde, ingress/station proximity.
- Jest `cycle_registry.yaml`.
- Jest vectorizer `global_slow_v1`.
- Są `primary_cycles` i `supporting_cycles`.
- Testy pilnują m.in. tego, że `historical_event_support` nie wchodzi do `planetary_resonance_score`.

### Ephemeris

- Jest `SwissEphemerisProvider`.
- Jest provider syntetyczny `synthetic-dev` do deterministycznych smoke testów i API proof.
- Jest golden fixture NASA/JPL Horizons dla pozycji planet:
  `tests/golden/planetary_states/jpl_horizons_2026-05-22T12Z.json`.
- Jest test integracyjny porównujący Swiss Ephemeris do JPL Horizons, ale jest skipowany, gdy `swisseph` nie jest dostępny.

### Search i clustering

- Jest exact cosine search.
- Jest weekly index builder w pamięci.
- Jest episode clustering, który grupuje sąsiednie daty w epizody.
- Jest golden snapshot pełnej odpowiedzi `/resonance/search`.
- Jest skrypt aktualizacji/sprawdzania snapshotu:
  `python scripts/update_resonance_api_golden.py --check`.

### Dane historyczne

- Jest schema DuckDB:
  - `historical_event`,
  - `event_source`,
  - `planetary_state_index`,
  - `resonance_run`,
  - `narrative_cache`.
- Jest importer `curated_events.csv`.
- Seed ma obecnie 25 wydarzeń z lat 1914-2026.
- Seed obejmuje 9 regionów i 11 kategorii.
- Eventy mają źródła `event_source` z `source_quality = wikidata_seed`.
- API zwraca przy eventach `sources`.
- Coverage dla testowego epizodu 2026 ma 3 eventy, 3 regiony i brak warningu biasu.

### API

- Jest FastAPI app.
- Działa:
  - `GET /health`,
  - `GET /data/status`,
  - `POST /resonance/search`.
- Endpointy poza `/health` wymagają lokalnego tokenu sesji.
- CORS jest ograniczony do lokalnych originów dev/Tauri.
- `/data/status` raportuje dostępność providerów, stan DuckDB/curated CSV i konfigurację security.
- `/resonance/search` zwraca:
  - profile i wersję vectora,
  - provider,
  - zakres indeksu,
  - primary/supporting cycles,
  - clustered episodes,
  - matched events,
  - event coverage,
  - event sources,
  - deterministic summary.

### Narracja deterministyczna

- Jest polskie `deterministic_summary`.
- Summary nie używa DeepSeek.
- Summary ma guardrail: opis podobieństwa symboliczno-historycznego, nie prognoza.
- Test sprawdza, że summary używa tylko event IDs z wejściowych `matched_events`.

### Testy i jakość

Ostatnia bramka jakości:

```bash
pytest
python -m ruff check services tests scripts
python scripts/update_resonance_api_golden.py --check
python -m compileall services scripts tests
python scripts/smoke_test_pipeline.py --date 2020-01-12 --profile global_slow_v1
python scripts/smoke_test_pipeline.py --date 2020-12-21 --profile global_slow_v1
python scripts/smoke_test_pipeline.py --date now --profile global_slow_v1
```

Wynik:

- `pytest`: 30 passed, 1 skipped.
- `ruff`: passed.
- golden snapshot API: aktualny.
- smoke pipeline: przechodzi dla dat kontrolnych.
- `compileall`: przechodzi.

## Czego Jeszcze Nie Mamy

### 1. Realnego pipeline'u astronomicznego w runtime

Największa luka: API i smoke pipeline używają `synthetic-dev`.

To jest dobre do kontraktów, testów i proofu, ale nie wystarcza jako realny produkt. Dopóki `/resonance/search` nie potrafi działać na prawdziwych efemerydach, wyniki nie mają wartości merytorycznej poza testem architektury.

Problem techniczny: `pyswisseph` na obecnym Windows/Python 3.12 próbuje budować C extension i wymaga Microsoft Visual C++ Build Tools. Nie ma gotowego wheel w tej konfiguracji.

### 2. Precomputed indexu 1900-now / 1500-now

Obecnie indeks jest budowany w locie w pamięci na potrzeby requestu/testu. Nie mamy jeszcze:

- zapisanego indeksu `.npy/.npz`,
- mapowania row -> data w DuckDB/Parquet,
- resume/progress builda,
- top-candidate daily refinement,
- indeksu 1900-now na realnych efemerydach.

### 3. Pełnego scoringu MVP

Mamy części scoringu i cycle contribution, ale brakuje warstwy końcowej, która nadaje wynikowi etykiety:

- `strong`,
- `moderate`,
- `weak`,
- `rare_configuration`,
- `insufficient_comparable_history`.

Jest już `narrative_confidence` oparte o event coverage, source quality i evidence confidence. Nadal brakuje końcowej warstwy etykietującej siłę rezonansu:

- `cycle_power_score`,
- `rarity_adjusted_percentile`,
- `strong/moderate/weak/rare/insufficient`,
- jasnego score breakdown w odpowiedzi API.

Ważne: historia nie może wejść do `planetary_resonance_score`. Obecny kod tego pilnuje, a plan został poprawiony po audycie.

### 4. Source quality i narrative confidence

Mamy `source_quality` jako pole źródła i podstawowe `narrative_confidence`. Nie mamy jeszcze:

- zewnętrznej konfigurowalnej mapy jakości źródeł,
- wielu źródeł per event,
- rozróżnienia źródeł primary/institutional/encyclopedic w danych,
- polityki blokowania DeepSeek, gdy `source_quality_score` jest za niski.

### 5. Rozbudowanego modelu dat historycznych

Eventy są dziś roczne: `start_astro_year`, `end_astro_year`, `display_date`.

Nie mamy jeszcze:

- `point_jd`,
- `start_jd`,
- `end_jd`,
- `date_precision`,
- obsługi BCE w eventach,
- niepewności dat,
- osobnego displayu bez `0 CE` w warstwie API/UI.

### 6. Endpointów pomocniczych

Z planu nie mamy jeszcze:

- `GET /sky/current`,
- `POST /sky/at-date`,
- `GET /events/window`,
- `POST /narrative/generate`.

### 7. Bezpiecznego runnera lokalnego API

Mamy już:

- session token middleware,
- CORS tylko dla Tauri/dev origin,
- endpointy poza `/health` chronione tokenem.

Nie mamy jeszcze:

- wymuszenia lokalnego bindu na poziomie runnera,
- bezpiecznego runnera backendu.

To nie blokuje backend proof, ale blokuje desktop-ready sidecar.

### 8. DeepSeek

Nie ma jeszcze:

- `DeepSeekClient`,
- prompt/versioning,
- Pydantic output schema dla AI,
- validation `mentioned_event_ids`,
- retry/fallback logic,
- cache po `input_hash`,
- testów AI z mockiem.

To jest zgodne z decyzją HOLD. Nie powinniśmy zaczynać od DeepSeek przed realnym ephemeris/indexem.

### 9. UI/Tauri

Nie ma jeszcze:

- React/Tauri app,
- wheel/timeline/aspect graph,
- DebugInspector,
- desktop packaging,
- Playwright screenshotów.

To też jest zgodne z decyzją HOLD.

## Problemy i Ryzyka

### P1 - Największe ryzyko: syntetyczny provider może dawać fałszywe poczucie postępu

Backend działa, ale wyniki planetarne są syntetyczne. Architektura jest realna, dane eventowe są realne, ale astronomiczny runtime nie jest jeszcze realny.

Rekomendacja: następny duży kamień milowy to rozwiązać provider realnych efemeryd. Dopiero potem warto traktować wyniki jako coś więcej niż test pipeline'u.

### P1 - Plan scoringu został poprawiony po audycie

W audycie wykryto, że `PLAN_PRAC_ASTRO_GLOBAL.md` zawierał:

```txt
0.10 * historical_event_support
```

Ten problem został poprawiony: plan rozdziela teraz `planetary_resonance_score` i `narrative_confidence`.

Rekomendacja: pilnować tego rozdziału w kolejnych zmianach, zwłaszcza przy DeepSeek i UI.

### P2 - Source-quality confidence jest bazowe, ale jeszcze płytkie

API liczy już `narrative_confidence`, ale wszystkie źródła mają dziś `wikidata_seed`. To dobry start techniczny, ale nie wystarczy do wysokiego confidence.

Rekomendacja: dodać drugie źródła dla części eventów i mapę jakości `primary/institutional/encyclopedic/wikidata_seed`.

### P2 - Seed eventów jest nadal mały

25 eventów to dobry seed techniczny, ale nie baza historyczna. Coverage globalny jest lepszy niż wcześniej, ale nadal bardzo rzadki.

Rekomendacja: rozbudowywać curated CSV kontrolowanymi partiami, np. 25-50 eventów na commit, z coverage testem i snapshotem API.

### P2 - Brak realnego persistent index

Build indeksu per request będzie niewystarczający, gdy przejdziemy na realne efemerydy i dłuższy zakres.

Rekomendacja: zbudować proof index 1900-now weekly jako artifact lokalny, potem dopiero 1500-now.

### P2 - API ma podstawowe security guardrails, ale nie ma runnera

Na tym etapie endpointy poza `/health` wymagają tokenu, a CORS jest lokalny. Przed Tauri trzeba jeszcze dodać runner, który binduje do `127.0.0.1`, wybiera port i przekazuje token frontendowi.

Rekomendacja: nie uruchamiać tego jako publiczny serwer, nie wystawiać na `0.0.0.0`.

### P2 - Dane historyczne mają tylko jedno źródło typu Wikidata

Źródła są jawne, ale jednoźródłowe. To jest OK dla seeda, nie dla wysokiego confidence.

Rekomendacja: dodać drugi source dla części eventów, np. Wikimedia/Encyclopaedia/primary institutional source, i wtedy dopiero różnicować source quality.

### P3 - Dokumentacja częściowo nie nadąża za kodem

Status jest aktualny, README jest w miarę aktualny, ale plan ma stare fragmenty. To normalne przy szybkim starcie, ale trzeba to uporządkować przed większą pracą w Cursorze/AI.

## Czy Idziemy W Dobrym Kierunku?

Tak, bo kolejność pracy jest zdrowa:

1. Repo i plan.
2. Kontrakty domenowe.
3. Reguły astrologiczne i vectorizer.
4. Search i clustering.
5. Warstwa historyczna.
6. API.
7. Deterministyczne summary.
8. Golden snapshoty i skrypty aktualizacji.
9. Dopiero potem AI/UI.

To jest właściwa kolejność. Największa wartość dotychczasowej pracy to nie "ładny output", tylko testowalny szkielet, który blokuje regresje i nie pozwala AI wymyślać faktów.

Nie jesteśmy jeszcze na etapie "aplikacja działa merytorycznie". Jesteśmy na etapie "backend proof jest zdrowo ułożony i gotowy na realne efemerydy".

## Rekomendowana Kolejność Następnych Prac

### Krok 1 - rozwiązać realny ephemeris provider

Opcje:

1. Doinstalować Microsoft Visual C++ Build Tools i uruchomić `pyswisseph`.
2. Użyć środowiska/wersji Pythona z gotowym wheel.
3. Rozważyć alternatywny provider do MVP, ale tylko jeśli zachowamy kontrakt i golden comparison do JPL Horizons.

### Krok 2 - zbudować proof index 1900-now

Najpierw weekly, lokalnie, na realnym providerze. Dopiero potem:

- daily refinement top candidates,
- 1500-now,
- cache i resume.

### Krok 3 - dodać endpointy pomocnicze

`GET /data/status` już jest. Minimum przed UI:

- `GET /events/window`,
- `POST /sky/at-date`.

### Krok 4 - security local sidecar

Token i CORS są już w API proof. Przed UI/Tauri zostaje:

- runner bindujący do `127.0.0.1`.

### Krok 5 - dopiero potem DeepSeek i UI

DeepSeek powinien dostać stabilny JSON wejściowy i walidator. UI powinien dostać stabilne API i debug JSON. Nie odwracać tej kolejności.

## Aktualny Stan Techniczny W Jednym Zdaniu

Astro Global ma już sensowny, testowany backend proof z API, eventami, źródłami, summary, narrative confidence i snapshotami, ale kluczowe merytoryczne przejście przed MVP to zastąpienie syntetycznego providera realnymi efemerydami oraz zbudowanie persistent proof indexu.
