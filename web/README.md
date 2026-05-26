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

- `/` - Start.
- `/dzis` - Dzis, publiczny dashboard biezacego rezimu.
- `/kosmogram` - Kosmogram, placeholder formularza astrologii osobistej.
- `/cykle-historyczne` - Cykle historyczne, explorer rezonansu historycznego.
- `/porownania` - Porownania dwoch dat/okresow.
- `/blog` - Blog i wpisy redakcyjne.
- `/o-silniku` - Transparentnosc/metodologia silnika.
- `/kontakt` - Kontakt.
- `/logowanie` - placeholder panelu administracyjnego.
- Dzis uzywa `GET /today`.
- Cykle historyczne uzywaja `POST /resonance/search`.
- Porownania uzywaja `POST /resonance/compare`.
- Blog uzywa `GET /articles/seeds`, bez live AI generation.
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
