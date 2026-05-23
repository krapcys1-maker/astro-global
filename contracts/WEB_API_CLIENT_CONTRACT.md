# Astro Global Web API Client Contract

Ten kontrakt opisuje granice dla przyszlego web/Tauri klienta. Klient moze tylko
wysylac requesty do FastAPI i renderowac odpowiedzi. Nie moze liczyc astrologii,
rankingow historycznych, confidence, coverage ani summary po swojej stronie.

## Endpointy Klienta

Dozwolone endpointy dla cienkiego klienta:

- `GET /health` - lekki healthcheck bez tokenu.
- `GET /readiness` - chroniony readiness backendu: Swiss, DuckDB, curated data i reliable index.
- `GET /today` - dzienny snapshot backendu z rekomendowanym requestem do search.
- `GET /data/status` - status runtime, providerow, danych i guardraili security.
- `GET /sky/current` - stan planetarny dla wybranego providera.
- `POST /sky/at-date` - stan planetarny dla konkretnej daty.
- `GET /events/window` - kontrolowany kontekst wydarzen i zrodel dla zakresu lat.
- `POST /resonance/search` - glowny produktowy search rezonansow.

Snapshot OpenAPI jest w `contracts/openapi_astro_global.json`.
Aktualizacja kontraktu wymaga jawnego uruchomienia:

```bash
python scripts/export_openapi_contract.py
```

CI sprawdza stabilnosc kontraktu:

```bash
python scripts/export_openapi_contract.py --check
```

## Reguly Klienta

Klient moze:

- wysylac token w `x-astro-global-session` albo `Authorization: Bearer`,
- pokazywac `matched_events`, `context_events`, `sources`, `event_coverage`,
  `narrative_confidence`, `score_breakdown`, `index_coverage` i
  `deterministic_summary` dokladnie z odpowiedzi API,
- uzyc `GET /today` jako backendowego punktu startowego i wyslac jego
  `recommended_search_request` do `/resonance/search`,
- pokazywac ostrzezenia coverage/confidence zwrocone przez backend,
- obslugiwac statusy `401`, `413`, `429`, `503` jako stany UI.

Klient nie moze:

- czytac bezposrednio DuckDB, CSV seeda, `data/vectors` ani cache,
- liczyc pozycji planet, aspektow, scoringu, rarity albo confidence,
- wybierac/rankingowac wydarzen historycznych poza tym, co zwroci API,
- dodawac wydarzen przez AI albo z zewnetrznych runtime sources,
- ukrywac `context_events` jako zwyklych `matched_events`,
- traktowac deep-history 1000-1500 jako reliable core,
- wysylac requestow z wildcard CORS ani bez tokenu do chronionych endpointow.

## Minimalne Stany UI

Przyszly web shell powinien obslugiwac:

- backend offline: `/health` niedostepne,
- backend not ready: `/readiness` zwraca `503`,
- brak lub bledny token: `401`,
- zbyt duzy payload: `413`,
- rate limit: `429`,
- request poza reliable history: `index_coverage.index_coverage_status != "full"`,
- niska pewnosc narracji: `narrative_confidence` z backendu,
- rozdzial `matched_events` i `context_events`.

## Zakres Reliable History

Klient musi respektowac etykiety backendu:

- `reliable_early_modern` dla 1500-1899,
- `reliable_modern` dla 1900-now,
- `mixed_reliable` dla requestow przecinajacych 1900,
- partial/out-of-range warning dla requestow zahaczajacych o zakres przed 1500.

Deep-history 1000-1500 nie jest jeszcze czescia reliable core.
