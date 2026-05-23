# ASTO Global — poprawiona architektura infrastruktury v2

**Status:** wersja po audycie poprzedniego blueprintu
**Cel:** aplikacja API-first do astrologicznej eksploracji historycznych rezonansów planetarnych
**Tryb użycia:** lokalny/dev MVP teraz; docelowo publiczny web/server po guardrailach produkcyjnych; kwestie licencyjne Swiss Ephemeris odkładamy na później, ale nie kasujemy notatki, bo wróci przy dystrybucji
**Rekomendacja dla Cursor:** traktować ten plik jako `docs/architecture.md`

\---

## 0\. Najważniejsza korekta względem poprzedniej wersji

Aktualizacja 2026-05-23: produkt ma isc w publiczny web/server, ale bez przepisywania
rdzenia. Lokalny sidecar pozostaje trybem developerskim; publiczny server mode musi miec
osobny config, public CORS z env, brak dev-token fallbacku, rate/request limits, readiness
check oraz deploy smoke test. Struktura strony web jest opisana w
`WEB_PRODUCT_STRUCTURE_ASTRO_GLOBAL.md`.

Poprzednia architektura była ogólnie dobra jako kierunek, ale miała kilka dziur, które mogłyby potem rozwalić projekt technicznie:

1. **Za dużo odpowiedzialności wrzucone w Swiss Ephemeris.**
Swiss Ephemeris / pyswisseph powinien być providerem pozycji, prędkości i danych astronomicznych. Aspekty, znaki, ingresy, orb rules, scoring i similarity muszą być liczone w naszym kodzie, bo to są reguły produktu.
2. **Brak formalnego profilu astronomicznego.**
Bez jasnej decyzji, czy używamy geocentric apparent tropical ecliptic longitude, UTC/UT, kalendarza gregoriańskiego/juliańskiego i astronomicznej numeracji lat, wyniki mogą być niespójne, szczególnie dla BCE.
3. **Błąd pojęciowy: `0 CE`.**
Historycznie nie ma roku 0 CE. W kodzie można używać astronomicznej numeracji lat, gdzie rok `0` oznacza `1 BCE`, ale UI musi pokazywać daty historycznie zrozumiale.
4. **HNSW/FAISS za wcześnie.**
Dla MVP liczba punktów jest mała. Dokładne wyszukiwanie cosine similarity na macierzy NumPy / DuckDB będzie prostsze, bardziej debugowalne i wystarczająco szybkie. ANN dopiero po dojściu do milionów punktów albo wielu profili.
5. **Za słaby model dat historycznych.**
`DATE` w bazie nie wystarczy dla starożytności, dat niepewnych, przedziałów typu „lata 1848–1849”, epok prosperity albo okresów pokoju. Potrzebne są zakresy, precyzja daty, kalendarz i confidence.
6. **Ryzyko fałszywych dopasowań przez szybkie planety.**
Dla globalnego historycznego rezonansu domyślny profil powinien prawie całkowicie ignorować Księżyc i mocno ograniczyć Merkurego/Wenus/Słońce. One mogą być w Current Sky, ale nie powinny sterować historycznym silnikiem.
7. **Brak kalibracji scoringu.**
Progi typu `0.82 = strong` są tylko robocze. Trzeba dodać kalibrację przez rozkład tła: percentyle, liczba niezależnych epizodów, minimalna liczba mocnych cech wolnych planet.
8. **Brak warstwy antyduplikacyjnej.**
Wyszukiwanie co 7 dni zwróci wiele prawie identycznych dat wokół jednego tranzytu. Trzeba grupować punkty w epizody i pokazywać epizody, nie surowe daty.
9. **AI guardrails wymagały doprecyzowania.**
Sam prompt nie wystarczy. Narrative layer musi walidować output po modelu: każde wydarzenie wspomniane w tekście musi istnieć w wejściowym JSON i mieć `event\_id`.
10. **Lokalny sidecar wymaga zabezpieczenia.**
FastAPI na komputerze użytkownika powinno bind\_ować tylko do `127.0.0.1`, mieć losowy port albo token sesji i nie wystawiać API na sieć lokalną.

\---

## 1\. Docelowy obraz systemu

ASTO Global to lokalna aplikacja desktopowa typu **astrological planetary resonance explorer**. Nie analizuje użytkownika, nie potrzebuje daty urodzenia i nie jest predykcyjnym modelem przyszłości. Rdzeniem jest astrologia mundalna: cykle, aspekty, fazy, orby, rzadkość układów, wagi astrologiczne i ich symboliczna interpretacja. System bierze globalny układ planet względem Ziemi, koduje go jako zestaw cech astrologicznych, szuka historycznie podobnych konfiguracji, dołącza kontrolowane dane wydarzeń historycznych jako kontekst i generuje symboliczną narrację.

Najważniejsza zasada:

```txt
Astrologia = rdzeń produktu: cykle, aspekty, fazy, orby, scoring i interpretacja
Astronomia = deterministic engine + nasz kod reguł jako baza obliczeń
Historia   = curated/local DB + kontrolowane źródła jako kontekst porównawczy
AI         = narracja, nie źródło prawdy
```

\---

## 2\. Poprawiony stack

### 2.1. Desktop UI

Rekomendacja zostaje:

```txt
Tauri 2 + React + TypeScript + Vite
```

Dodatki:

```txt
TanStack Query       — komunikacja z lokalnym API
Zustand              — prosty lokalny stan UI
D3 / visx / SVG      — timeline, aspect graph, resonance map
Framer Motion        — animacje, jeśli chcesz bardziej immersyjny feeling
Three.js             — opcjonalnie dopiero po MVP
```

**Korekta:** Tauri + Python sidecar jest dobrym kierunkiem, ale trzeba traktować backend jako osobny binarny sidecar. W Tauri v2 zewnętrzne binaria deklaruje się przez `externalBin`; dla każdej architektury systemowej trzeba mieć odpowiednio nazwany plik z target triple. To oznacza, że w praktyce backend pakujemy np. PyInstallerem/Nuiką do binarki per OS.

Źródło: Tauri v2 sidecar docs — https://v2.tauri.app/develop/sidecar/

### 2.2. Backend lokalny

```txt
Python 3.12+
FastAPI
Pydantic v2
NumPy
DuckDB
pyswisseph
```

**Tryb działania:**

```txt
Tauri app startuje sidecar backend
backend wybiera losowy wolny port albo dostaje port z configu dev
backend binduje tylko na 127.0.0.1
backend wymaga session tokenu w headerze
UI używa tokenu przekazanego przez Tauri command/env
```

Minimalne zabezpieczenie lokalnego API:

```txt
host: 127.0.0.1, nie 0.0.0.0
random session token
CORS tylko dla lokalnego frontendu / Tauri dev origin
brak logowania API key i promptów z kluczami
```

### 2.3. Storage

MVP powinien być prostszy niż poprzednio:

```txt
DuckDB                      — event DB, metadata, cache, wynikowe tabele
Parquet                     — eksporty i tabele offline
NumPy .npy / .npz            — macierz wektorów planetary state
Parquet id\_map               — mapowanie vector row -> state\_id/date/jd/window
SQLite opcjonalnie           — tylko proste ustawienia UI, jeśli potrzebne
```

**Korekta:** hnswlib/FAISS/DuckDB VSS dopiero jako V1/V2. DuckDB ma eksperymentalną extension VSS z HNSW, ale dla MVP exact search będzie prostszy i wiarygodniejszy.

Źródło: DuckDB VSS docs — https://duckdb.org/docs/current/core\_extensions/vss.html

\---

## 3\. Odpowiedzialności modułów

```txt
Desktop UI
  pokazuje Current Sky, Search, Timeline, Summary, Debug
  nie liczy astronomii
  nie odpytuje bezpośrednio internetu

Local API Sidecar
  wystawia endpointy
  koordynuje pipeline
  pilnuje cache, tokenu i ścieżek

Ephemeris Provider
  liczy pozycje i prędkości planet przez pyswisseph
  zwraca surowe dane astronomiczne
  nie decyduje o scoringu ani interpretacji

Astro Rules Engine
  liczy znaki, elementy, modalności
  liczy aspekty i orb closeness
  wykrywa ingresy, retrograde, konfiguracje wieloplanetarne

Vectorizer
  zamienia PlanetaryState na feature groups
  wersjonuje wektor
  normalizuje grupy cech

Resonance Search Engine
  wykonuje exact search / optional ANN
  rozszerza okna historyczne
  grupuje kandydatów w epizody
  klasyfikuje strong/moderate/weak/rare/insufficient

Historical Event Layer
  przechowuje curated events
  opcjonalnie enrichment z Wikidata/Wikipedia
  liczy importance/confidence/source quality

Theme Engine
  agreguje motywy z wydarzeń
  działa deterministycznie przed AI

Narrative Layer
  generuje JSON narrative
  waliduje output
  nie dodaje faktów spoza inputu
```

\---

## 3.1. Przyszłe moduły poboczne jako API clients

Pomysły produktowe z `pomysl.md` są zgodne z architekturą, ale nie mogą zmienić
obecnego priorytetu prac. Traktujemy je jako przyszłe moduły poboczne konsumujące
ten sam astrologiczny backend, a nie jako powód do przepisania pipeline'u.

```txt
Current Resonance Search
  -> POST /resonance/search

At-Date Explorer
  -> POST /sky/at-date
  -> POST /resonance/search
  -> GET /events/window

Historical Compare Mode
  -> future POST /resonance/compare
  -> bazuje najpierw na dwoch PlanetaryState i dwoch zestawach CycleDrivers

Timeline Heatmap
  -> future GET /timeline/heatmap
  -> bazuje na precomputed index, cycle intensity i event coverage, nie na LLM

Archetype Engine
  -> future services/themes albo services/archetypes
  -> bazuje na cycle drivers, event tags i motifs, nie na swobodnej narracji AI
```

Wspólny kontrakt dla tych trybów:

```txt
PlanetaryState
CycleDrivers
ScoreBreakdown
MatchedFeatures
ResonanceEpisodes
MatchedEvents
EventCoverage
NarrativeConfidence
Sources
```

To oznacza, że UI może pokazać compare mode, heatmapę albo archetypy dopiero wtedy,
gdy backend zwraca explainable JSON. AI może opisywać wynik, ale nie może decydować,
które epoki są podobne ani tworzyć wydarzeń spoza danych.

Hierarchia odpowiedzialności produktu:

```txt
1. Astrologiczny silnik rezonansów jest centrum systemu.
2. Warstwa historyczna objaśnia i porównuje wyniki astrologiczne.
3. Compare Mode, Timeline Heatmap i Archetype Engine są modułami pobocznymi.
4. AI jest narratorem nad JSON, nie silnikiem astrologii ani historii.
```

\---

## 4\. Formalny profil astronomiczny

To jest krytyczne. Bez tego będziesz miał wyniki, które trudno porównać i debugować.

### 4.1. Default Astro Profile

```yaml
astro\_profile\_id: tropical\_geocentric\_apparent\_v1
observer: geocentric
time\_input: UTC
julian\_day: UT
zodiac: tropical
coordinate\_system: ecliptic\_longitude\_latitude
equinox: true\_equinox\_of\_date
position\_type: apparent
bodies:
  - Sun
  - Moon
  - Mercury
  - Venus
  - Mars
  - Jupiter
  - Saturn
  - Uranus
  - Neptune
  - Pluto
default\_swisseph\_flags:
  - SWIEPH
  - SPEED
calendar\_policy:
  ce\_dates: proleptic\_gregorian\_for\_internal\_storage
  historical\_display: display\_original\_calendar\_when\_known
  bce\_internal\_years: astronomical\_year\_numbering
```

Swiss Ephemeris przy domyślnych flagach zwraca typowe astrologiczne pozycje apparent geocentric ecliptic, a dla prędkości trzeba jawnie ustawić flagę speed. W pyswisseph odpowiada temu użycie `swe.calc\_ut(jd\_ut, planet, flags)` z flagami typu `FLG\_SWIEPH | FLG\_SPEED`.

Źródła:

* Swiss Ephemeris programming manual — https://www.astro.com/swisseph/swephprg.htm
* Swiss Ephemeris docs PDF — https://www.astro.com/ftp/swisseph/doc/swisseph.pdf

### 4.2. Rok 0 / BCE

W UI **nie wolno pisać `0 CE`**.

W kodzie można używać astronomicznej numeracji lat:

```txt
astronomical year  1  = 1 CE
astronomical year  0  = 1 BCE
astronomical year -1  = 2 BCE
astronomical year -499 = 500 BCE
```

Wewnętrznie:

```python
def historical\_bce\_to\_astro\_year(bce: int) -> int:
    # 1 BCE -> 0, 2 BCE -> -1, 500 BCE -> -499
    return 1 - bce
```

Dla zakresów:

```txt
Reliable History Window: 1500 CE – current build date
Deep History Window:     1 CE – 1499 CE
Ancient Window:          500 BCE – 1 BCE, internal astronomical\_year -499..0
Mythic Window:           przed 500 BCE, internal astronomical\_year <= -500
```

Swiss Ephemeris używa astronomicznej numeracji lat przy datach BCE; JPL Horizons używa historycznej bez roku 0, więc porównania BCE wymagają mapowania.

Źródło: Swiss Ephemeris docs PDF, sekcja porównania z JPL Horizons — https://www.astro.com/ftp/swisseph/doc/swisseph.pdf

### 4.3. Co robi ephemeris, a co robi nasz kod

**Ephemeris provider:**

```txt
pozycja ekliptyczna longitude/latitude
odległość, jeśli potrzebna
speed longitude deg/day
retrograde = speed < 0, ale flagę liczy nasz kod
Julian Day conversion
```

**Nasz Astro Rules Engine:**

```txt
znak zodiaku = floor(longitude / 30)
degree in sign = longitude % 30
element/modalność z mapy znaków
aspekty = angular\_distance(longitude\_a, longitude\_b)
orb = abs(distance - exact\_aspect\_angle)
ingress proximity = distance to 0° znaku + speed context
multi-planet patterns
```

\---

## 5\. Repozytorium po poprawce

```txt
asto-global/
  apps/
    desktop/
      src/
        app/
        api/
        components/
        screens/
          CurrentSky/
          ResonanceSearch/
          HistoricalTimeline/
          ResonanceSummary/
          DebugInspector/
          PoeticMode/
        state/
        styles/
      src-tauri/
        tauri.conf.json
        binaries/                 # sidecar per OS/arch after build
      package.json
      vite.config.ts

  services/
    api/
      app.py
      routes/
        health.py
        sky.py
        resonance.py
        events.py
        narrative.py
        data\_admin.py
      schemas/
        planetary.py
        resonance.py
        events.py
        narrative.py
      core/
        config.py
        paths.py
        security.py
        logging.py
        versioning.py

    ephemeris/
      provider.py
      swiss\_provider.py
      time\_utils.py
      astro\_profile.py
      tests/

    astro\_rules/
      angles.py
      signs.py
      aspects.py
      ingress.py
      retrograde.py
      patterns.py
      tests/

    resonance/
      feature\_groups.py
      vectorizer.py
      scoring.py
      calibration.py
      index\_builder.py
      exact\_search.py
      optional\_ann.py
      episode\_clustering.py
      windows.py
      tests/

    historical/
      schema.sql
      curated\_importer.py
      wikidata\_client.py
      wikipedia\_client.py
      categorizer.py
      importance.py
      confidence.py
      coverage.py
      seeds/
        curated\_events.csv
        category\_map.yaml
        source\_quality.yaml
      tests/

    themes/
      deterministic\_themes.py
      optional\_embeddings.py
      tests/

    narrative/
      schemas.py
      prompt\_builder.py
      llm\_adapter.py
      guardrails.py
      deterministic\_summary.py
      tests/

  data/
    ephe/
    duckdb/
      asto\_global.duckdb
    vectors/
      global\_slow\_v1.npy
      global\_slow\_v1\_id\_map.parquet
      full\_sky\_v1.npy
      full\_sky\_v1\_id\_map.parquet
    cache/
      wikidata/
      wikipedia/
      narrative/
    exports/

  scripts/
    build\_sidecar.py
    build\_planetary\_index.py
    rebuild\_current\_tail.py
    ingest\_curated\_events.py
    enrich\_events\_wikidata.py
    run\_backend\_dev.py
    smoke\_test\_pipeline.py

  docs/
    architecture.md
    data\_model.md
    cursor\_prompts.md
    astro\_profile.md
    known\_limitations.md

  pyproject.toml
  README.md
```

\---

## 6\. Pipeline v2

### 6.1. Current Sky

```txt
UI -> GET /sky/current
API -> EphemerisProvider.compute(datetime\_utc, astro\_profile)
API -> AstroRulesEngine.decorate\_positions()
API -> AstroRulesEngine.compute\_aspects()
API -> Vectorizer.vectorize\_current\_state()
API -> response
```

Current Sky może pokazywać wszystkie planety, w tym Księżyc.

### 6.2. Historical Resonance Search

```txt
UI -> POST /resonance/search
API -> compute current PlanetaryState
API -> vectorize with selected search\_profile
Search -> exact similarity in Reliable Window
Search -> cluster nearby candidate dates into episodes
Search -> classify episodes
Search -> if too few independent episodes, expand to Deep Window
Search -> if still too few and allowed, expand to Ancient Window
Events -> fetch events for episode windows
Themes -> deterministic theme aggregation
Narrative -> optional AI narrative + validation
API -> response
```

### 6.3. Historical Events

W UI nie odpalamy ciężkich zapytań Wikidata przy każdym kliknięciu. Domyślna ścieżka:

```txt
curated\_events.csv -> DuckDB -> search results
```

Dopiero potem:

```txt
manual refresh / enrichment -> Wikidata/Wikipedia -> cache -> DuckDB
```

Wikidata Query Service jest publicznym endpointem SPARQL dla datasetu Wikidata; Wikimedia/MediaWiki REST API daje dostęp do treści wiki, ale w produkcie powinny być traktowane jako enrichment/cache, nie jako jedyna prawda.

Źródła:

* Wikidata Query Service manual — https://www.mediawiki.org/wiki/Wikidata\_Query\_Service/User\_Manual
* Wikidata data model — https://www.wikidata.org/wiki/Wikidata:Data\_model
* MediaWiki REST API — https://www.mediawiki.org/wiki/API:REST\_API

### 6.4. AI Narrative

```txt
input = verified\_current\_state + verified\_matches + verified\_events + deterministic\_themes
LLM output = strict JSON schema
post\_validation = every factual claim maps to event\_id/source\_id
fallback = deterministic\_summary
```

Structured Outputs / JSON Schema są właściwym kierunkiem, bo wymuszają strukturę odpowiedzi i zmniejszają ryzyko luźnego formatu, ale nadal potrzebujesz walidacji faktów po swojej stronie.

Źródło: OpenAI Structured Outputs — https://developers.openai.com/api/docs/guides/structured-outputs

\---

## 7\. Search profiles

Zamiast jednego wektora dla wszystkiego, użyj profili.

### 7.1. `global\_slow\_v1` — domyślny profil MVP

Cel: historyczne cykle globalne.

```yaml
included\_bodies:
  - Jupiter
  - Saturn
  - Uranus
  - Neptune
  - Pluto
excluded\_from\_core:
  - Moon
  - Mercury
  - Venus
  - Sun
  - Mars
optional\_context\_only:
  - Mars
sampling\_step\_days: 7
refinement\_step\_days: 1
```

To powinien być główny silnik historycznego rezonansu.

### 7.2. `global\_slow\_plus\_mars\_v1`

Cel: ostrzejsze napięcia, konflikty, krótsze okresy.

```yaml
included\_bodies:
  - Mars
  - Jupiter
  - Saturn
  - Uranus
  - Neptune
  - Pluto
mars\_weight\_cap: 0.20
```

Mars może dodawać kontekst, ale nie może zdominować wyniku.

### 7.3. `full\_sky\_context\_v1`

Cel: opis Current Sky, nie domyślne historyczne dopasowania.

```yaml
included\_bodies:
  - Sun
  - Moon
  - Mercury
  - Venus
  - Mars
  - Jupiter
  - Saturn
  - Uranus
  - Neptune
  - Pluto
use\_for\_history\_search: false\_by\_default
```

\---

## 8\. Feature groups i scoring po poprawce

### 8.1. Zasada kątowa

Nie porównujemy kątów liniowo. Dla kątów i separacji używamy reprezentacji kołowej:

```txt
angle\_rad = deg \* pi / 180
feature = \[cos(angle\_rad), sin(angle\_rad)]
```

Dla odległości kątowej:

```python
def angular\_distance\_deg(a: float, b: float) -> float:
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)
```

SciPy circular statistics definiuje średnią kątową przez argument średniego wektora zespolonego, co dobrze pokazuje, dlaczego dane kątowe trzeba traktować jako kołowe, a nie liniowe.

Źródło: SciPy circmean docs — https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.circmean.html

### 8.2. Feature groups

```txt
G1. Outer synodic phase
- sin/cos separacji dla par:
  Jupiter-Saturn
  Jupiter-Uranus
  Jupiter-Neptune
  Jupiter-Pluto
  Saturn-Uranus
  Saturn-Neptune
  Saturn-Pluto
  Uranus-Neptune
  Uranus-Pluto
  Neptune-Pluto

G2. Major aspect channels
- conjunction 0°
- sextile 60°
- square 90°
- trine 120°
- opposition 180°
- orb closeness per pair/per aspect

G3. Sign/element/modal context
- niska waga
- znaki wolnych planet jako 12-sector circular encoding, nie ciężki one-hot
- element distribution
- modality distribution

G4. Ingress/retrograde context
- retrograde bits
- distance\_to\_sign\_boundary
- recent\_ingress flag
- station proximity: abs(speed) bardzo małe

G5. Rare pattern flags
- outer planet stellium/cluster
- T-square-like
- grand trine-like
- multiple hard aspects among slow planets
```

### 8.3. Wagi startowe v2

Poprzednie `0.55 aspect\_similarity` było zbyt szerokie. Lepszy start:

```txt
score =
  0.35 \* outer\_synodic\_phase\_similarity +
  0.30 \* outer\_major\_aspect\_similarity +
  0.10 \* jupiter\_saturn\_cycle\_similarity +
  0.10 \* sign\_element\_modal\_context\_similarity +
  0.07 \* ingress\_retrograde\_similarity +
  0.08 \* rare\_pattern\_similarity
```

Każda grupa musi być osobno normalizowana do zakresu `0..1`. Dopiero potem liczysz sumę ważoną.

### 8.4. Orb closeness

Prosty start:

```python
def orb\_closeness(orb\_deg: float, max\_orb\_deg: float) -> float:
    if orb\_deg > max\_orb\_deg:
        return 0.0
    return 1.0 - (orb\_deg / max\_orb\_deg)
```

Lepszy wariant później:

```python
def orb\_closeness\_gaussian(orb\_deg: float, sigma\_deg: float) -> float:
    return exp(-0.5 \* (orb\_deg / sigma\_deg) \*\* 2)
```

Startowe orby dla profilu `global\_slow\_v1`:

```yaml
outer\_outer:
  conjunction: 5.0
  opposition: 5.0
  square: 4.5
  trine: 4.0
  sextile: 3.5
jupiter\_saturn:
  conjunction: 6.0
  opposition: 6.0
  square: 5.0
  trine: 4.5
  sextile: 4.0
mars\_outer\_optional:
  conjunction: 4.0
  opposition: 4.0
  square: 3.5
```

### 8.5. Klasyfikacja wyników

Nie polegaj tylko na absolutnych progach.

```txt
strong resonance:
  score >= 0.82
  AND at least 2 strong outer features
  AND percentile >= 99.0 within searched window

moderate resonance:
  score >= 0.68
  AND percentile >= 95.0

weak resonance:
  score >= 0.55
  OR percentile >= 90.0

rare configuration:
  fewer than min\_matches independent moderate+ episodes after allowed expansion

insufficient comparable history:
  no useful independent episodes after all allowed windows
```

Percentyle liczysz z rozkładu podobieństwa current vector do wszystkich punktów w danym profilu/oknie.

\---

## 9\. Search windows po poprawce

### 9.1. Definicje

```yaml
reliable\_history:
  label: Reliable History Window
  start\_astro\_year: 1500
  end: current\_index\_build\_date
  historical\_confidence: high
  default: true

deep\_history:
  label: Deep History Window
  start\_astro\_year: 1
  end\_astro\_year: 1499
  historical\_confidence: medium
  default: fallback

ancient\_symbolic:
  label: Ancient / Symbolic Window
  start\_astro\_year: -499   # 500 BCE
  end\_astro\_year: 0        # 1 BCE
  historical\_confidence: low\_to\_medium
  default: optional

mythic:
  label: Mythic Window
  start\_astro\_year: -3000
  end\_astro\_year: -500
  historical\_confidence: low
  default: off
```

### 9.2. Precompute

MVP:

```txt
profile: global\_slow\_v1
range: 1500 CE – build\_date
step: 7 days
refinement: daily ±45 days around top raw candidates
search: exact cosine / group score
```

V1:

```txt
range: 1 CE – build\_date
step: 7 or 14 days
refinement: daily ±60 days
```

V2:

```txt
range: 500 BCE – build\_date
internal years: astronomical numbering
step: 14 or 30 days for slow-only
refinement: daily/weekly depending on profile
```

### 9.3. Grupowanie w epizody

To jest obowiązkowe.

Algorytm:

```txt
1. Weź top K punktów z raw search.
2. Posortuj po dacie.
3. Łącz punkty w epizod, jeśli przerwa <= max\_episode\_gap\_days.
4. Dla każdego epizodu wybierz best\_date = punkt z najwyższym score.
5. period\_start/period\_end = zakres punktów + padding wynikający z wolnych aspektów.
6. Odrzuć epizody zbyt bliskie już wybranym, np. min\_separation\_days = 365 albo dynamicznie per cykl.
7. Zwróć niezależne epizody, nie pojedyncze daty.
```

Startowe parametry:

```yaml
max\_episode\_gap\_days: 45
min\_independent\_episode\_separation\_days: 365
outer\_aspect\_padding\_days: 180
jupiter\_saturn\_padding\_days: 120
```

\---

## 10\. Dane historyczne po poprawce

### 10.1. Dlaczego stary model był za prosty

Wydarzenia historyczne nie zawsze są punktami w czasie. Często są:

```txt
punktowe: bitwa, odkrycie, publikacja
zakresowe: wojna, rewolucja, epidemia
rozmyte: okres prosperity, renesans, kryzys ideologiczny
niepewne: wydarzenia starożytne
wielokalendarzowe: daty juliańskie/gregoriańskie
```

Dlatego model musi obsługiwać datę jako **zakres + precyzja + confidence**, nie tylko `DATE`.

### 10.2. Schemat DuckDB v2

```sql
CREATE TABLE historical\_event (
  id TEXT PRIMARY KEY,
  wikidata\_id TEXT,
  title TEXT NOT NULL,
  short\_description TEXT,
  long\_description TEXT,

  -- time normalized for search
  start\_jd DOUBLE,
  end\_jd DOUBLE,
  point\_jd DOUBLE,

  -- time display and precision
  start\_astro\_year INTEGER,
  end\_astro\_year INTEGER,
  display\_date TEXT,
  date\_precision TEXT,      -- day/month/year/decade/century/period/unknown
  calendar\_system TEXT,     -- gregorian/julian/mixed/unknown
  date\_confidence DOUBLE,

  -- classification
  category TEXT,
  subcategory TEXT,
  region TEXT,
  country TEXT,
  geo\_scope TEXT,           -- local/regional/global

  -- quality
  importance\_score DOUBLE,
  confidence\_score DOUBLE,
  source\_quality TEXT,
  curated BOOLEAN DEFAULT FALSE,
  manual\_boost DOUBLE DEFAULT 0,

  -- text/search
  language TEXT,
  tags TEXT\[],
  created\_at TIMESTAMP,
  updated\_at TIMESTAMP
);

CREATE TABLE event\_source (
  id TEXT PRIMARY KEY,
  event\_id TEXT,
  source\_type TEXT,         -- curated/wikidata/wikipedia/book/manual
  source\_name TEXT,
  source\_url TEXT,
  retrieved\_at TIMESTAMP,
  source\_payload JSON,
  license\_note TEXT
);

CREATE TABLE planetary\_state\_index (
  id BIGINT PRIMARY KEY,
  profile\_id TEXT,
  astro\_profile\_id TEXT,
  vector\_version TEXT,
  jd\_ut DOUBLE,
  astro\_year INTEGER,
  iso\_date TEXT,
  window\_tag TEXT,
  positions\_json JSON,
  aspects\_json JSON,
  feature\_debug\_json JSON
);

CREATE TABLE resonance\_run (
  id TEXT PRIMARY KEY,
  input\_hash TEXT,
  datetime\_utc TEXT,
  search\_profile TEXT,
  astro\_profile\_id TEXT,
  created\_at TIMESTAMP,
  result\_json JSON
);

CREATE TABLE narrative\_cache (
  id TEXT PRIMARY KEY,
  input\_hash TEXT,
  model\_name TEXT,
  output\_json JSON,
  validation\_json JSON,
  created\_at TIMESTAMP
);
```

### 10.3. Importance score v2

```txt
importance =
  0.25 \* curated\_or\_manual\_boost +
  0.20 \* global\_scope\_weight +
  0.20 \* normalized\_wikipedia\_sitelinks +
  0.15 \* category\_weight +
  0.10 \* source\_quality +
  0.10 \* cross\_source\_presence
```

### 10.4. Confidence score v2

```txt
confidence =
  0.25 \* date\_confidence +
  0.20 \* source\_quality +
  0.20 \* curated\_reviewed +
  0.15 \* cross\_source\_confirmation +
  0.10 \* category\_confidence +
  0.10 \* description\_quality
```

### 10.5. Coverage report

Dodaj do wyników informację, czy event layer jest zbalansowany:

```json
{
  "coverage": {
    "events\_found": 42,
    "regions": {"Europe": 18, "Asia": 8, "Americas": 6, "Africa": 3, "Global": 7},
    "dominant\_region\_bias": "Europe",
    "warning": "Historical source coverage is uneven for this period."
  }
}
```

To ogranicza fałszywe wrażenie, że system zna „całą historię świata”.

\---

## 11\. Narrative Layer v2

### 11.1. Input do AI

AI dostaje wyłącznie dane z pipeline:

```json
{
  "run\_id": "...",
  "astro\_profile": "tropical\_geocentric\_apparent\_v1",
  "search\_profile": "global\_slow\_v1",
  "current\_state\_summary": {},
  "matches": \[
    {
      "match\_id": "m\_001",
      "period\_start": "1789-04",
      "period\_end": "1790-02",
      "best\_date": "1789-08-12",
      "score": 0.86,
      "percentile": 99.2,
      "label": "strong\_resonance",
      "matched\_features": \[
        {"feature": "Saturn-Uranus hard aspect", "strength": 0.91}
      ],
      "events": \[
        {
          "event\_id": "evt\_french\_revolution",
          "title": "French Revolution",
          "display\_date": "1789–1799",
          "category": "revolution",
          "source\_ids": \["src\_001"]
        }
      ]
    }
  ],
  "common\_themes": \[
    {"theme": "institutional pressure", "supporting\_event\_ids": \["evt\_..."]}
  ],
  "language\_rules": {
    "forbidden": \[
      "to się wydarzy",
      "planety spowodują",
      "przewidujemy",
      "pewne jest, że"
    ],
    "preferred": \[
      "historycznie współwystępowało",
      "rezonuje z okresami",
      "podobne konfiguracje pojawiały się w czasie",
      "symboliczna interpretacja",
      "nie jest to predykcja"
    ]
  }
}
```

### 11.2. Output schema

```json
{
  "current\_climate": "string",
  "historical\_resonance\_summary": "string",
  "match\_commentary": \[
    {
      "match\_id": "string",
      "commentary": "string",
      "mentioned\_event\_ids": \["string"],
      "dominant\_motifs": \["string"]
    }
  ],
  "common\_motifs": \[
    {
      "motif": "string",
      "supporting\_match\_ids": \["string"],
      "supporting\_event\_ids": \["string"]
    }
  ],
  "caveat": "To nie jest predykcja, tylko symboliczne porównanie historyczne."
}
```

### 11.3. Post-validation

Po odpowiedzi modelu:

```txt
1. JSON musi przejść walidację Pydantic.
2. Każdy mentioned\_event\_id musi istnieć w input events.
3. Każdy supporting\_event\_id musi istnieć w input events.
4. Tekst nie może zawierać forbidden phrases.
5. Jeśli AI doda tytuł wydarzenia, którego nie ma w input, wynik odrzucamy.
6. Jeśli walidacja nie przejdzie dwa razy, używamy deterministic\_summary.
```

\---

## 12\. API v2

```txt
GET  /health
GET  /data/status
GET  /sky/current
POST /sky/at-date
POST /resonance/search
GET  /resonance/run/{run\_id}
GET  /events/window
POST /events/enrich
POST /narrative/generate
POST /data/rebuild-index
```

### 12.1. `POST /resonance/search`

Request:

```json
{
  "datetime\_utc": "2026-05-22T12:00:00Z",
  "astro\_profile\_id": "tropical\_geocentric\_apparent\_v1",
  "search\_profile\_id": "global\_slow\_v1",
  "min\_independent\_matches": 2,
  "preferred\_matches": 8,
  "allow\_deep\_history": true,
  "allow\_ancient\_symbolic": false,
  "include\_narrative": true,
  "debug\_features": true
}
```

Response:

```json
{
  "run\_id": "run\_...",
  "current\_state": {},
  "search\_windows\_used": \["reliable\_history"],
  "classification": "sufficient\_comparable\_history",
  "matches": \[
    {
      "match\_id": "m\_001",
      "period\_start": "1789-04-01",
      "period\_end": "1790-02-28",
      "best\_date": "1789-08-12",
      "score": 0.86,
      "percentile": 99.2,
      "label": "strong\_resonance",
      "window\_tag": "reliable\_history",
      "matched\_features": \[
        {
          "group": "outer\_major\_aspect",
          "feature": "Saturn-Uranus square-like separation",
          "strength": 0.91
        }
      ],
      "events": \[]
    }
  ],
  "coverage": {},
  "themes": \[],
  "narrative": {}
}
```

\---

## 13\. MVP plan po korekcie

### MVP 0 — smoke test, zanim zrobisz UI

```txt
1. Python package structure.
2. SwissEphemerisProvider.
3. AstroRulesEngine: signs, angular distance, aspects.
4. Vectorizer global\_slow\_v1.
5. Build index 1900–today weekly.
6. Search current date and return top episodes.
7. CLI smoke test.
```

Cel: zanim dotkniesz Tauri, udowodnij, że pipeline działa.

### MVP 1 — lokalny backend

```txt
1. FastAPI endpoints /health, /sky/current, /sky/at-date, /resonance/search.
2. Precompute 1500–today weekly.
3. Exact search.
4. Episode clustering.
5. Curated events CSV.
6. Deterministic summary bez AI.
```

### MVP 2 — desktop

```txt
1. Tauri 2 + React.
2. Sidecar backend dev runner.
3. CurrentSky screen.
4. Analyze Current Sky button.
5. Match cards + timeline.
6. DebugInspector z matched\_features.
```

### MVP 3 — AI optional

```txt
1. NarrativeService.
2. Strict JSON schema.
3. Post-validation.
4. Deterministic fallback.
5. Cache.
```

### V1

```txt
1. Wikidata enrichment.
2. Wikipedia summaries.
3. Deep History Window 1–1499 CE.
4. Better calibration by percentiles.
5. Coverage report.
```

### V2

```txt
1. Ancient/Symbolic Window.
2. Optional DuckDB VSS / HNSW.
3. Embeddings for themes.
4. Export reports.
5. Poetic mode.
```

\---

## 14\. Cursor prompts po poprawce

### Prompt 1 — core first

```txt
Zbuduj Python backend core dla ASTO Global według docs/architecture.md. Zacznij bez UI. Utwórz moduły services/ephemeris, services/astro\_rules, services/resonance. Dodaj pyproject.toml, pytest i prosty CLI smoke\_test\_pipeline.py. Nie implementuj AI ani Wikidata.
```

### Prompt 2 — Swiss provider

```txt
Zaimplementuj SwissEphemerisProvider używający pyswisseph. Provider przyjmuje datetime UTC i astro\_profile\_id=tropical\_geocentric\_apparent\_v1. Zwraca longitude\_deg, latitude\_deg, speed\_longitude\_deg\_per\_day dla Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto. Użyj Julian Day UT i flag SWIEPH + SPEED. Dodaj ephemeris\_version i flags do wyniku.
```

### Prompt 3 — astro rules

```txt
Dodaj services/astro\_rules: angles.py, signs.py, aspects.py, ingress.py, retrograde.py. Angular distance musi obsługiwać 359° i 1° jako 2°. Znaki licz z longitude/30. Aspekty licz w naszym kodzie, nie w Swiss providerze. Dodaj testy jednostkowe.
```

### Prompt 4 — vectorizer global\_slow\_v1

```txt
Zaimplementuj Vectorizer dla search\_profile global\_slow\_v1. Użyj Jupiter, Saturn, Uranus, Neptune, Pluto. Feature groups: outer synodic phase sin/cos separacji, major aspect channels, sign/element/modal low weight, ingress/retrograde, rare pattern flags. Każdą grupę normalizuj do 0..1 i zwracaj feature\_debug\_json.
```

### Prompt 5 — exact search

```txt
Zbuduj index\_builder.py, który liczy profil global\_slow\_v1 dla zakresu 1500-01-01 do dziś co 7 dni. Zapisz macierz wektorów do data/vectors/global\_slow\_v1.npy, id\_map do Parquet, a szczegóły state do DuckDB. Dodaj resume i progress bar.
```

### Prompt 6 — episode clustering

```txt
Zaimplementuj exact\_search.py i episode\_clustering.py. Search ma liczyć similarity current vector do matrix, zwracać top K punktów, a clustering ma łączyć daty w epizody jeśli gap <= 45 dni. Zwracaj best\_date, period\_start, period\_end, score, percentile, matched\_features.
```

### Prompt 7 — API

```txt
Dodaj FastAPI app z lokalnym security: host 127.0.0.1, session token middleware, CORS dev tylko lokalnie. Endpointy /health, /sky/current, /sky/at-date, /resonance/search. /resonance/search używa exact search i episode clustering.
```

### Prompt 8 — historical curated events

```txt
Dodaj DuckDB schema v2 dla historical\_event i event\_source. Dodaj importer curated\_events.csv. Daty wydarzeń przechowuj jako start\_jd/end\_jd/point\_jd + display\_date + date\_precision + calendar\_system. Dodaj endpoint /events/window.
```

### Prompt 9 — deterministic summary

```txt
Zaimplementuj ThemeEngine i deterministic\_summary bez LLM. Na podstawie event categories i matched\_features wygeneruj krótkie podsumowanie po polsku, bez języka predykcyjnego. Dodaj test, że tekst nie zawiera forbidden phrases.
```

### Prompt 10 — Tauri UI

```txt
Stwórz Tauri 2 + React + TypeScript UI. Ekrany: CurrentSky, ResonanceSearch, HistoricalTimeline, ResonanceSummary, DebugInspector. Na razie uruchamiaj backend dev ręcznie albo przez prosty sidecar command. Po kliknięciu Analyze Current Sky wywołaj /resonance/search i pokaż epizody, score, percentile, matched\_features i wydarzenia.
```

\---

## 15\. Testy obowiązkowe

```txt
angles:
  angular\_distance(359, 1) == 2
  angular\_distance(1, 359) == 2
  angular\_distance(10, 190) == 180

bce:
  1 BCE -> astronomical year 0
  500 BCE -> astronomical year -499
  UI never displays 0 CE

ephemeris:
  result includes ephemeris\_version, flags, astro\_profile\_id
  speed < 0 => retrograde true

vectorizer:
  same input => same vector
  vector\_version stable
  feature groups normalized

search:
  no duplicate dates from same episode
  min independent episode separation respected
  score and percentile returned

narrative:
  no forbidden phrases
  mentioned\_event\_ids subset of input event ids
  fallback works without LLM

security:
  backend binds to 127.0.0.1
  missing token rejected outside /health
```

\---

## 16\. Decyzje odłożone, ale świadome

```txt
Swiss Ephemeris license:
  prywatne użycie: nie blokuje MVP
  dystrybucja/komercja: wrócić do tematu

AI provider:
  MVP może działać bez AI przez deterministic\_summary
  OpenAI / local LLM jako adapter później

ANN index:
  nie używać w MVP
  wrócić, jeśli exact search będzie wolny albo dojdą miliony wektorów

Ancient/Mythic history:
  wyłączone domyślnie
  wymaga mocnych disclaimerów i date\_confidence
```

\---

## 17\. Finalna rekomendacja

Buduj projekt w takiej kolejności:

```txt
1. Core astronomy + astro rules.
2. Vectorizer global\_slow\_v1.
3. Exact search + episode clustering.
4. Curated event DB.
5. Deterministic summary.
6. FastAPI endpoints.
7. Tauri UI.
8. AI narrative.
9. Wikidata enrichment.
10. Ancient/deep windows.
```

Najważniejsza praktyczna rada: **nie zaczynaj od UI i nie zaczynaj od AI**. Najpierw zbuduj mały pipeline, który dla jednej daty zwraca:

```txt
current planetary state
matched historical episodes
matched features
events from curated DB
deterministic summary
```

Dopiero gdy ten rdzeń działa, Cursor ma sensownie generować UI i narrację.

\---

## 18\. Krótka wersja architektury końcowej

```txt
Tauri 2 + React UI
        ↓
Local FastAPI sidecar on 127.0.0.1 with session token
        ↓
SwissEphemerisProvider: positions + speeds only
        ↓
AstroRulesEngine: signs, aspects, ingress, retrograde, patterns
        ↓
Vectorizer: global\_slow\_v1 feature groups
        ↓
ExactSearch: NumPy/DuckDB matrix similarity
        ↓
EpisodeClustering: dates -> independent historical periods
        ↓
HistoricalEventLayer: curated DuckDB events + optional enrichment
        ↓
ThemeEngine: deterministic motifs
        ↓
NarrativeLayer: optional strict JSON AI + post-validation
```

Ta wersja jest bardziej odporna na błędy niż poprzednia, bo oddziela astronomię od reguł astrologicznych, traktuje BCE i daty historyczne poprawnie, nie komplikuje MVP przez ANN, dodaje security dla lokalnego sidecara i wymusza, żeby AI nie wymyślało faktów.
