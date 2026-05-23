# Web-ready plan - Astro Global

Data: 2026-05-23

## Decyzja

Budujemy najpierw aplikacje desktopowa/local-first, ale od teraz utrzymujemy projekt tak,
zeby pozniejsza wersja webowa nie wymagala przepisywania rdzenia.

Najwazniejsza zasada:

```txt
logika produktu = backend/API
UI = klient API
```

To znaczy, ze Tauri/React nie moze zawierac logiki astronomii, scoringu, event rankingu,
promptow DeepSeek ani dostepu do danych jako glownego zrodla prawdy.

## Dlaczego to dziala

Astro Global jest juz blisko web-ready, bo ma architekture API-first:

- FastAPI,
- JSON contracts,
- token auth,
- local CORS,
- deterministic backend,
- Swiss Ephemeris provider,
- persistent `.npz` index,
- DuckDB/fallback CSV,
- confidence layers,
- deterministic summary,
- golden snapshoty API.

Desktop i web powinny roznic sie miejscem uruchomienia backendu, a nie logika produktu.

## Docelowy podzial

### Desktop teraz

```txt
Tauri / React
  -> local FastAPI sidecar on 127.0.0.1
  -> Swiss Ephemeris local runtime
  -> DuckDB local data
  -> local .npz vector index
```

### Web pozniej

```txt
React web
  -> FastAPI server
  -> Swiss Ephemeris server runtime
  -> DuckDB/Postgres server data
  -> server .npz vector index
```

Frontend moze byc prawie ten sam, jesli bedzie gadal tylko z API.

## Zasady dla UI od teraz

UI moze robic:

- formularze,
- wybor daty,
- wybor profilu,
- wizualizacje current sky,
- timeline,
- karty epizodow,
- debug inspector,
- wyswietlanie `primary_cycles`, `supporting_cycles`, `score_breakdown`,
- wyswietlanie `matched_events`, `sources`, `event_coverage`, `narrative_confidence`.

UI nie moze robic:

- liczenia pozycji planet,
- liczenia aspektow/orbow,
- budowania wektorow,
- exact search,
- episode clustering,
- rankingu wydarzen,
- source confidence,
- prompt logic DeepSeek,
- halucynacyjnego dopisywania faktow,
- bezposredniego czytania DuckDB/CSV/index jako runtime path.

## Warstwy API, ktore musza pozostac stabilne

Minimum do utrzymania pod desktop i web:

- `GET /health`
- `GET /data/status`
- `GET /sky/current`
- `POST /sky/at-date`
- `GET /events/window`
- `POST /resonance/search`

Przyszle tryby produktu tez maja isc przez API, nie przez logike w UI:

- `POST /resonance/compare` dla porownania dwoch dat/epok,
- `GET /timeline/heatmap` dla mapy intensywnosci cykli i coverage,
- `GET /cycles/drivers` albo pole `cycle_drivers` w odpowiedziach search,
- `GET /themes/archetypes` albo pole `archetypes` liczone deterministycznie z eventow i cykli.

Pozniej dla web:

- auth/session endpoint,
- rate-limit aware `/narrative/generate`,
- usage/quota status,
- saved analyses,
- shareable read-only report URLs.

## Co zmieni sie przy webie

Desktop nie wymaga:

- kont uzytkownikow,
- publicznego rate limitu,
- billing guardrails,
- abuse protection,
- kolejki zadan AI.

Web bedzie wymagal:

- publicznego auth albo anonymous session z limitem,
- rate limiting per IP/user,
- CORS dla domeny produkcyjnej,
- request size limits,
- cache wynikow dla popularnych dat,
- osobnych limitow dla Quick Insight i Deep Analysis,
- monitoring kosztow AI,
- logow bez sekretow i bez prywatnych danych.

## Koszty przy 1000 zapytan miesiecznie

1000 zapytan miesiecznie to okolo 33 zapytania dziennie. Dla obecnej architektury to niski ruch,
bo astronomia, search i historia sa lokalne/cacheowalne po stronie backendu.

Szacunek MVP web:

| Element | Szacunek miesieczny |
| --- | ---: |
| Backend VPS | 10-40 EUR |
| Frontend hosting | 0-5 EUR |
| Storage/index/DuckDB | ~0 EUR na tym etapie |
| AI Flash / Quick Insight | okolo 1-10 EUR przy krotkich narracjach |
| AI Pro / Deep Analysis | okolo 20-100 EUR, zalezne od dlugosci outputu |
| Domena | okolo 1-2 EUR miesiecznie w ujeciu rocznym |

Wniosek: dla 1000 zapytan miesiecznie koszt powinien byc raczej niski. Glownym ryzykiem
nie jest Swiss ani search, tylko publiczny abuse i niekontrolowane Deep Analysis.

Przed produkcja ceny trzeba sprawdzic ponownie, bo dostawcy moga je zmieniac.

## Strategia web migration

### Etap 1 - Desktop/local-first

Cel:

- realny Swiss runtime,
- indeks 1900-now / 1500-now,
- known-case calibration,
- UI jako klient API,
- deterministic summary.

### Etap 2 - Web preview

Zakres:

- read-only web,
- current sky,
- at-date search,
- quick deterministic insight,
- public demo bez kont albo z bardzo prostym limitem.

Backend:

- FastAPI na VPS,
- Swiss + index + DuckDB na serwerze,
- AI domyslnie off albo tylko Flash z limitem.

### Etap 3 - Web product

Zakres:

- konta,
- zapis analiz,
- share links,
- Deep Analysis,
- kolejka/caching,
- usage limits,
- admin cost dashboard.

## Guardraile architektoniczne

1. UI nie zawiera logiki produktu.
2. Kazdy ekran UI konsumuje te same JSON contracts, ktore moglby konsumowac web.
3. Endpointy musza byc deterministyczne bez AI.
4. DeepSeek jest enhancementem i kosztowym dodatkiem, nie dependency.
5. Index i DuckDB nie trafiaja do repo.
6. Publiczny web nie rusza bez rate limitu i limitow AI.
7. Desktop-first pozostaje najlepszym etapem debugowania, bo unika infra/security chaosu.
8. Compare Mode, Timeline Heatmap i Archetype Engine nie moga byc generowane przez LLM jako zrodlo prawdy; backend musi zwracac explainable JSON.

## Rekomendacja

Nie zaczynac teraz weba.

Zaczac UI desktopowe dopiero po benchmark/calibration core, ale budowac je tak, jakby jutro
ten sam React mial gadac z `https://api.astro-global...`.

Najblizszy praktyczny krok przed UI:

- dodac calibration expectations do known-case benchmarku,
- sprawdzic long_process vs instant_event w matched events,
- potem dopiero zaczac React UI jako cienkiego klienta API.

## Zrodla cen i ograniczen

- DeepSeek API pricing: https://api-docs.deepseek.com/quick_start/pricing/
- Cloudflare pricing: https://www.cloudflare.com/plans/
- Cloudflare Pages limits: https://developers.cloudflare.com/pages/platform/limits/
- Hetzner Cloud product/pricing page: https://www.hetzner.com/cloud/
- Hetzner Cloud docs: https://docs.hetzner.com/cloud/servers/overview/
