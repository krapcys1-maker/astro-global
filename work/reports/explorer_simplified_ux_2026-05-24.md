# Astro Global Explorer Simplified UX

Date: 2026-05-24

## Goal

Reduce Explorer from a technical observatory dashboard into a readable
civilizational resonance experience.

## Main UI Now Answers Three Questions

1. Current Regime
   - Current cycle date range.
   - 2-4 dominant cycle/regime labels.
   - Short themes derived from returned event categories and active background
     regimes.

2. Similar Historical Periods
   - Independent historical analogue windows only.
   - Nearby/current-regime dates are not shown in the main analogue list.
   - Cards show period first, label, confidence, themes, and key events.
   - Exact `best_date` remains visible only as subtle `Peak match`.

3. What Happened During Those Periods?
   - Narrative explanation.
   - Key matched events.
   - Broader context events.
   - Sources remain visible under events.

## Moved Into Advanced

- Local resonance / nearby same-regime dates.
- Exact active cycle lists.
- Orb and cycle detail.
- Index coverage diagnostics.
- Score breakdown.
- Confidence breakdown.
- Event category metrics.
- Query profile/index/provider details.

## Manual Checks

Checked with local backend/web for:

- `2026-05-24`
- `2011-12-31`
- `1789-07-14`

Each rendered the three product sections, showed `Advanced / technical details`
collapsed by default, and had no visible error state.

Local test URL used:

- `http://127.0.0.1:5174/index.html?apiBase=http%3A%2F%2F127.0.0.1%3A8775&token=dev-local-token&date=2026-05-24#explorer`

## Validation

- `pytest -q`
- `ruff check .`
- `python -m compileall services scripts tests`
- `python scripts/smoke_test_web_shell.py`
- `python scripts/smoke_test_web_api_e2e.py`
- `python scripts/smoke_test_product_path.py`
- `python scripts/benchmark_known_resonance_cases.py`
- `python scripts/pre1900_quality_audit.py --check-regressions`
- `git diff --check`

## Screenshots

Before:

- `work/reports/screenshots/after_explorer_2026_cycle_window_ux.png`
- `work/reports/screenshots/after_explorer_2011_cycle_window_ux.png`

After:

- `work/reports/screenshots/after_explorer_2026_simplified_ux.png`
- `work/reports/screenshots/after_explorer_2011_simplified_ux.png`
- `work/reports/screenshots/after_explorer_1789_simplified_ux.png`
