# Astro Global Web Shell

To jest cienki frontend klient API dla Astro Global. UI nie liczy astrologii,
rankingu, confidence ani zrodel; wysyla requesty do FastAPI i renderuje odpowiedzi.

Uruchomienie lokalne:

```bash
python -m http.server 5173 -d web
```

Adresy:

```txt
http://127.0.0.1:5173
http://127.0.0.1:5173/transparency/
```

Zakres shell:

- Home, Today, Explorer, Compare, Calendar, Insights, Library, Blog, Contact.
- Today uzywa `GET /today`.
- Explorer uzywa `POST /resonance/search`.
- Compare uzywa `POST /resonance/compare`.
- Calendar uzywa `GET /timeline/seeds`.
- Insights uzywa `GET /articles/seeds`, bez live AI generation.
- Explorer pokazuje backendowe primary/supporting cycles, timeline epizodow,
  matched events, context events, confidence, score breakdown i source links.

Backend lokalny:

```bash
$env:ASTRO_GLOBAL_SESSION_TOKEN="dev-local-token"
python scripts/run_api.py --port 8765
```

Mozna tez przekazac inny backend bez edycji plikow:

```txt
http://127.0.0.1:5173?apiBase=http://127.0.0.1:8765&token=dev-local-token
```

Smoke test:

```bash
python scripts/smoke_test_web_shell.py
python scripts/smoke_test_web_api_e2e.py
```
