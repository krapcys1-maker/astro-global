# Live article draft review - revolutionary wave 1789/1848

## Verdict

Technical validation passed, but editorial quality needs prompt tightening before
we trust the style for more article seeds.

## What passed

- DeepSeek returned valid `ArticleDraftOutput` JSON.
- `validation.ok=true`.
- No event IDs or source IDs outside the backend fact-pack.
- The draft kept `editorial_status=draft_needs_human_review`.
- The draft did not present the comparison as a prediction.

## Issues

- The prose is too encyclopedic and not yet enough like an Astro Global research
  desk note.
- The draft adds broad interpretive language not explicitly present in the
  fact-pack, for example motivations, ideological framing and social goals.
- It uses valid source IDs, but the validator cannot know whether every sentence
  is strictly supported by the source content because source pages are not
  included in the fact-pack.
- Context separation is only partly visible. `evt_enlightenment` appears as
  context, but the prose still blends it into explanatory history rather than
  making the evidence/context boundary explicit.

## Root Cause

The validator is correctly enforcing IDs, schema and basic guardrails. The main
problem is prompt scope: the model is allowed to write like a historical summary,
so it fills in plausible but non-backend details.

## Patch Decision

Tighten the live prompt toward an evidence-ledger style:

- facts may only come from title/date/role/category/warnings in the fact-pack,
- no added motives, ideology, effects or causal explanations,
- matched/context distinction must remain explicit,
- draft remains a review artifact, not publishable text.

## Next Check

Run a second live draft after the prompt change and compare whether the prose is
less encyclopedic and more constrained to backend evidence.

## V2 Result

After tightening the prompt, a second live draft was generated:

- `work/reports/article_draft_live_revolutionary_wave_1789_1848_v2.json`
- `work/reports/article_draft_live_validation_revolutionary_wave_1789_1848_v2.json`

Validation:

```json
{
  "ok": true,
  "errors": [],
  "warnings": []
}
```

Editorial comparison:

- The draft is now closer to an evidence ledger.
- It reports query-vector similarity, episode windows, matched events and context
  events explicitly.
- It no longer adds broad causal or ideological explanations in the article
  paragraphs.
- It still reads like a structured research note rather than a publishable
  article, which is acceptable for the current draft harness.

Remaining watch item:

- The model translates some event titles into Polish. This is acceptable for a
  draft, but future UI/article rendering should preserve event IDs and may want
  backend-provided localized titles rather than ad hoc model translations.
