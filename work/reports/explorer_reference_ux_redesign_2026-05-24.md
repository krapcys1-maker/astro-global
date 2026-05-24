# Astro Global Explorer Reference UX Redesign - 2026-05-24

## Scope

Redesigned only the Explorer product UI. Backend math, scoring, endpoints and data contracts were not changed.

Reference target:

- `C:\Users\user\Downloads\ChatGPT Image 24 maj 2026, 18_17_15.png`

Local URL used for inspection:

- `http://127.0.0.1:5174/index.html?apiBase=http%3A%2F%2F127.0.0.1%3A8775&token=dev-local-token&date=2026-05-24#explorer`

## What Changed

- Added an Explorer workbench frame with a left rail and top mode bar matching the reference composition.
- Rebuilt the default result view around three product questions:
  - Current Regime
  - Historical Analogues
  - What Happened During Those Periods
- Made the Current Regime panel the visual hero:
  - regime year range
  - dominant structural cycles
  - key themes
  - orbit/cycle visual
- Rebuilt the Historical Analogues section as premium period cards, using backend `historical_analogues`.
- Added a Cycle Layers side panel from backend active regime/cycle data.
- Added a Timeline Overlay using backend current regime range and selected analogue period.
- Moved matched/context event evidence into a collapsed details section.
- Kept local resonance, score breakdown, exact cycle windows and diagnostics inside `Advanced / technical details`.

## Backend Fields Used

- `query_datetime_utc`
- `historical_analogues`
- `active_regime_windows`
- `active_cycle_windows`
- `regime_cycle_windows`
- `primary_cycles`
- `supporting_cycles`
- `matched_events`
- `context_events`
- `narrative_confidence`
- `score_breakdown`
- `local_resonance`
- `local_resonance_window`

## Manual Checks

### 2026-05-24

- Rendered Current Regime: `2025-2032`
- Historical Analogues shown from backend:
  - `2015`
  - `2013`
- Confirmed no same-current-regime date visually appears as the main historical analogue.

Screenshot:

- `work/reports/screenshots/after_explorer_2026_reference_ux.png`
- `work/reports/screenshots/reference_vs_explorer_2026.png`

### 2011-12-31

- Rendered Current Regime: `2011-2012`
- Historical Analogues shown from backend:
  - `1999`
  - `2006`
  - `1998-02-09`
- Chrome click-flow test changed the form date to `2011-12-31`, submitted it, and confirmed the rendered DOM included the new regime and historical events.

Screenshot:

- `work/reports/screenshots/after_explorer_2011_reference_ux.png`

## Remaining Differences From JPG

- The app still keeps the global public nav above the Explorer because this is the current web shell architecture.
- Icons are text-in-circle rail glyphs instead of custom SVG iconography.
- Analogue cards show only as many independent historical analogues as the backend returns; no fake third/fourth cards are added for visual fullness.
- Sparkline marks are decorative only and do not encode fake score data.

## Validation Notes

- Headless Chrome screenshot inspection was used for 2026 and 2011.
- Chrome DevTools Protocol click-flow verified the Analyze Date form updates the rendered Explorer for `2011-12-31`.
- No runtime/log errors were observed in that Chrome click-flow session.
