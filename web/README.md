# Astro Global Web Shell

To jest pierwszy cienki klient API. Nie zawiera logiki astrologii, scoringu, event
rankingu, confidence ani dostepu do DuckDB/indeksow. Renderuje tylko odpowiedzi FastAPI.

Uruchomienie statycznego shell:

```bash
python -m http.server 5173 -d web
```

Backend lokalny:

```bash
$env:ASTRO_GLOBAL_SESSION_TOKEN="dev-local-token"
python scripts/run_api.py --port 8765
```

Adres shell:

```txt
http://127.0.0.1:5173
```

Kontrakt klienta jest w `../contracts/WEB_API_CLIENT_CONTRACT.md`.
Smoke test guardraili shell:

```bash
python scripts/smoke_test_web_shell.py
python scripts/smoke_test_web_api_e2e.py
```
