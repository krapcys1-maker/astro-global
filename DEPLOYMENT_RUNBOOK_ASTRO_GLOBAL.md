# Astro Global Deployment Runbook

Ten dokument opisuje minimalny, bezpieczny kontrakt uruchomienia backendu Astro Global
w trybie server/web. Nie opisuje jeszcze publicznego UI ani generatora artykulow AI.
Rdzen produktu pozostaje w FastAPI; klient web/Tauri ma byc cienkim klientem API.

## Zakres

Runbook dotyczy backendu FastAPI:

- Swiss Ephemeris jako lokalny provider astronomiczny,
- DuckDB event store z curated events,
- persistent Swiss index `swiss_1500_now_global_slow_v1.npz`,
- token API, CORS, rate limit, request-size limit,
- `/health`, `/readiness`, `/data/status` i `/resonance/search`.

Nie wolno wystawiac publicznie katalogow `.env`, `data/vectors`, cache, dumpow,
DuckDB ani prywatnych plikow roboczych. API ma byc jedyna publiczna granica backendu.

## Wymagane Artefakty

Przed deployem backend musi miec lokalnie:

- Python 3.11,
- zaleznosci z `.[dev,astro]` albo produkcyjny odpowiednik z `pyswisseph`,
- dzialajacy Swiss Ephemeris provider,
- DuckDB event store z curated events,
- reliable Swiss index 1500-now:
  `data/vectors/swiss_1500_now_global_slow_v1.npz`.

Indeksy `.npz`, DuckDB i cache pozostaja ignorowane przez git.

## Wymagane Env Vars

Tryb produkcyjny musi miec jawne wartosci:

```bash
ASTRO_GLOBAL_ENV=production
ASTRO_GLOBAL_SESSION_TOKEN=<long-random-secret>
ASTRO_GLOBAL_CORS_ORIGINS=https://twoja-domena.example
ASTRO_GLOBAL_RATE_LIMIT_ENABLED=true
ASTRO_GLOBAL_RATE_LIMIT_PER_MINUTE=60
ASTRO_GLOBAL_MAX_REQUEST_BYTES=65536
```

Zasady:

- `ASTRO_GLOBAL_SESSION_TOKEN` nie moze byc `dev-local-token`.
- `ASTRO_GLOBAL_CORS_ORIGINS` nie moze zawierac wildcard `*`.
- `ASTRO_GLOBAL_RATE_LIMIT_PER_MINUTE` musi byc dodatnia liczba calkowita.
- `ASTRO_GLOBAL_MAX_REQUEST_BYTES` musi byc dodatnia liczba calkowita.
- `DEEPSEEK_API_KEY` nie jest wymagany dla deterministycznego core API i nie moze
  zmieniac faktow ani dodawac wydarzen spoza backendu.

## Preflight

Przed startem serwera uruchom:

```bash
ruff check .
pytest -q
python scripts/update_resonance_api_golden.py --check
python scripts/validate_curated_data.py
python scripts/ingest_curated_events.py --dry-run
python scripts/report_historical_data_bias.py
python scripts/smoke_test_deploy_config.py
python scripts/smoke_test_product_path.py --date 1789-07-14T00:00:00Z --index-file swiss_1500_now_global_slow_v1.npz --skip-expected-event-check
python scripts/benchmark_known_resonance_cases.py
python -m compileall services scripts tests -q
git diff --check
```

`smoke_test_deploy_config.py` nie potrzebuje prywatnego indeksu z `data/vectors`; tworzy
tymczasowy DuckDB i minimalny indeks, zeby sprawdzic produkcyjna konfiguracje API.
`smoke_test_product_path.py` wymaga realnego indeksu Swiss.

## Runtime Checks

Po starcie sprawdz:

```http
GET /health
GET /readiness
GET /data/status
```

Oczekiwania:

- `/health` zwraca `200` bez tokenu.
- `/readiness` wymaga tokenu i zwraca `200`, gdy Swiss, DuckDB, curated data i reliable
  index sa gotowe.
- `/data/status.security.runtime_environment` ma wartosc `production`.
- `/data/status.security.cors_allowed_origins` zawiera tylko produkcyjna domene.
- `/data/status.security.rate_limit_enabled` ma wartosc `true`.
- `/data/status.security.max_request_bytes` ma oczekiwana wartosc.
- Request bez tokenu do chronionych endpointow zwraca `401`.
- Payload powyzej limitu zwraca `413`.
- Nadmiar requestow z jednego klienta zwraca `429`.

## Monitoring

Minimalne metryki/logi do pilnowania:

- status i latency `/health`,
- status i latency `/readiness`,
- liczba odpowiedzi `401`, `413`, `429`, `5xx`,
- czas odpowiedzi `/resonance/search`,
- liczba requestow per IP / user / token,
- rozmiary payloadow,
- bledy Swiss Ephemeris,
- brak DuckDB lub indeksu reliable,
- wzrost kosztow AI, gdy warstwa AI zostanie dodana.

Alert powinien powstac przy:

- `/readiness` != `ready`,
- naglym wzroscie `429` albo `413`,
- dowolnym powtarzalnym `5xx`,
- braku indeksu `swiss_1500_now_global_slow_v1.npz`,
- probach path traversal w `index_file`,
- requestach bez tokenu z duza czestotliwoscia.

## Abuse Response

Przy naduzyciach:

1. Zweryfikuj, czy `ASTRO_GLOBAL_RATE_LIMIT_ENABLED=true`.
2. Tymczasowo obniz `ASTRO_GLOBAL_RATE_LIMIT_PER_MINUTE`.
3. Tymczasowo obniz `ASTRO_GLOBAL_MAX_REQUEST_BYTES`, jesli problemem sa duze payloady.
4. Zrotuj `ASTRO_GLOBAL_SESSION_TOKEN`, jesli token mogl wyciec.
5. Ogranicz CORS do jednej domeny produkcyjnej.
6. Przejrzyj logi `401`, `413`, `429`, `5xx` i najciezsze requesty.
7. Nie wlaczaj publicznego AI generation bez osobnych limitow kosztow i moderacji.

## Swiss License

Prywatny MVP moze dzialac lokalnie na Swiss Ephemeris, ale publiczna dystrybucja lub
komercjalizacja wymaga osobnej decyzji licencyjnej. Nie pakuj plikow Swiss, indeksow ani
cache w publiczny artefakt bez potwierdzenia licencji.

## Blokery Przed Publicznym Web

Publiczny web/server nie powinien ruszyc, dopoki nie ma:

- jawnych produkcyjnych env vars,
- zielonego deploy config smoke,
- zielonego product smoke na indeksie 1500-now,
- monitoringu statusow `401`, `413`, `429`, `5xx`,
- procedury rotacji tokena,
- decyzji licencyjnej Swiss dla sposobu dystrybucji,
- osobnych limitow kosztow dla kazdej warstwy AI.
