# AI article draft harness - 2026-05-23

## Decyzja

Silnik danych i rezonansu jest gotowy do lokalnych testow AI jako autora szkicu
artykulu, ale nie do automatycznej publikacji. Ten patch dodaje warstwe testowa:
backend fact-pack, schemat draftu, walidator i mock-generator bez live LLM.

## Zakres patcha

- Dodano `services/narrative/article_draft.py` z modelami:
  - `ArticleDraftFactPack`
  - `ArticleDraftOutput`
  - `ArticleDraftValidationResult`
- Fact-pack powstaje z istniejacego `ArticleSeedResponse` oraz deterministycznego
  `ResonanceCompareResponse`.
- Draft musi pozostac w polityce `backend_facts_only_no_prediction` i statusie
  `draft_needs_human_review`.
- Walidator odrzuca:
  - `event_id` spoza fact-packa,
  - `source_id` spoza fact-packa,
  - claim bez dowodu event/cycle,
  - claim z eventami bez source IDs,
  - jezyk predykcyjny typu `to sie wydarzy`.
- Dodano `scripts/generate_article_draft.py`, ktory lokalnie uruchamia:
  `/articles/seeds` -> `/resonance/compare` -> fact-pack -> mock draft -> validator.
- Dodano tryb `--mode live` dla OpenAI-compatible chat completions. Tryb live
  wymaga jawnych zmiennych env i nadal przechodzi przez ten sam walidator.

## Lokalny smoke

Komenda:

```powershell
python scripts/generate_article_draft.py --seed-id article_revolutionary_wave_1789_1848 --output work/reports/article_draft_mock_revolutionary_wave_1789_1848.json
```

Wynik:

```json
{
  "seed_id": "article_revolutionary_wave_1789_1848",
  "mode": "mock",
  "validation_ok": true
}
```

## Live LLM

Tryb live jest opt-in i nie ma domyslnego dostawcy. Wymagane env:

```powershell
$env:ASTRO_GLOBAL_LLM_BASE_URL = "https://provider.example/v1/chat/completions"
$env:ASTRO_GLOBAL_LLM_API_KEY = "..."
$env:ASTRO_GLOBAL_LLM_MODEL = "model-name"
```

Opcjonalne env:

```powershell
$env:ASTRO_GLOBAL_LLM_TIMEOUT_SECONDS = "60"
$env:ASTRO_GLOBAL_LLM_TEMPERATURE = "0.2"
```

Komenda:

```powershell
python scripts/generate_article_draft.py --mode live-preflight --seed-id article_revolutionary_wave_1789_1848
```

Preflight sprawdza backend/fact-pack/env bez requestu do dostawcy LLM. Aktualny
wynik lokalny:

```json
{
  "seed_id": "article_revolutionary_wave_1789_1848",
  "mode": "live-preflight",
  "live_ready": false,
  "error": "Live LLM mode requires env vars: ASTRO_GLOBAL_LLM_BASE_URL, ASTRO_GLOBAL_LLM_API_KEY, ASTRO_GLOBAL_LLM_MODEL"
}
```

Fact-pack jest gotowy: 13 allowed events, 26 allowed sources, 2 episodes. Live run
czeka tylko na jawne env vars dostawcy/modelu.

Wlasciwy live run:

```powershell
python scripts/generate_article_draft.py --mode live --seed-id article_revolutionary_wave_1789_1848
```

Skrypt zapisuje wynik lokalnie tylko jesli draft przejdzie walidacje
`backend_facts_only_no_prediction`.

## Prompt preview

Przed pierwszym live runem mozna zapisac dokladne wejscie dla LLM bez requestu
do providera:

```powershell
python scripts/generate_article_draft.py --mode prompt-preview --seed-id article_revolutionary_wave_1789_1848 --output work/reports/article_draft_prompt_preview_revolutionary_wave_1789_1848.json
```

Aktualny preview dla `article_revolutionary_wave_1789_1848`:

```json
{
  "mode": "prompt-preview",
  "request_sent": false,
  "message_count": 2,
  "allowed_event_ids": 13,
  "allowed_source_ids": 26,
  "episodes": 2
}
```

## Co dalej

Nastepny bezpieczny krok to pierwszy reczny live run z wybranym dostawca i
modelem, po przejrzeniu prompt preview. Live output nie powinien trafic do
publikacji bez review czlowieka.

## Manual draft validation

Bez klucza API mozna uzyc prompt-preview w dowolnym zewnetrznym UI LLM, zapisac
otrzymany JSON do pliku i sprawdzic go lokalnym walidatorem:

```powershell
python scripts/generate_article_draft.py --mode validate-draft --seed-id article_revolutionary_wave_1789_1848 --draft-input path\to\draft.json
```

Walidator akceptuje czysty `ArticleDraftOutput` albo wrapper z polem `draft`.
Lokalny smoke na mock output:

```json
{
  "mode": "validate-draft",
  "draft_input": "work\\reports\\article_draft_mock_revolutionary_wave_1789_1848.json",
  "validation_ok": true,
  "request_sent": false
}
```
