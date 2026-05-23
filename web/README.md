# Astro Global Web Shell

To jest statyczny frontend shell produktu: landing + Explorer desk inspirowany
ciemnym obserwatorium. Na tym etapie UI nie laczy sie z backendem i nie wykonuje
requestow do FastAPI.

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
- Explorer pokazuje planetary wheel, primary cycles, timeline, matched events,
  context events, confidence i sekcje "why this match".
- Insights jest oddzielone od Bloga: AI-assisted research notes kontra manualne
  teksty.

Backend/FastAPI wraca dopiero w kolejnym etapie integracji.

Smoke test:

```bash
python scripts/smoke_test_web_shell.py
python scripts/smoke_test_web_api_e2e.py
```
