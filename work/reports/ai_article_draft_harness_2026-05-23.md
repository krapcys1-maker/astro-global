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

## Co dalej

Nastepny bezpieczny krok to dodanie trybu live LLM za flaga/env, nadal lokalnie i
nadal z tym samym walidatorem. Live output nie powinien trafic do publikacji bez
review czlowieka.
