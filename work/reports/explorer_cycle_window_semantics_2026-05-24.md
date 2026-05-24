# Astro Global Explorer Cycle-Window Semantics

Date: 2026-05-24

## Goal

Shift Explorer presentation from exact-date matching to cycle-window semantics while
keeping vector search, scoring, and astrology math unchanged.

## Backend Change

`POST /resonance/search` now returns backend-derived cycle windows:

- `active_cycle_windows`
- `regime_cycle_windows`

Each item contains:

- `cycle_id`
- `planets`
- `aspect`
- `role`
- `label`
- `start_date`
- `peak_date`
- `end_date`
- `orb_at_query`
- `closeness_at_query`
- `confidence_scope`

The windows are derived from the same ephemeris provider and cycle drivers used by
the resonance engine. Boundary detection scans while the cycle remains active.
`peak_date` is sampled weekly from the ephemeris window and is therefore marked
with `confidence_scope=sampled_weekly_from_ephemeris`.

No ranking, vectorizer, or astrology math was rewritten.

## UI Change

Explorer now presents:

- Current Active Regime: cycle windows and slow-body sign regimes around the query date.
- Local Resonance Window: nearby/same-regime continuity evidence, separated from history.
- Historical Analogues: independent historical windows outside the current active regime.

Exact dates are now secondary labels:

- `Matching resonance window`
- `Peak match`

## Manual Check Summary

`2026-05-24`:

- Active cycle windows include Neptune-Pluto sextile, Neptune-Uranus sextile, and
  Pluto-Uranus trine with start/peak/end dates.
- Local peak match remains `2026-05-18`, but it is shown under Local Resonance
  Window instead of Historical Analogues.
- Historical analogue peaks start at older independent windows such as `2015-04-20`
  and `2013-04-22`.

`2011-12-31`:

- Active cycle windows include Neptune-Saturn trine, Jupiter-Saturn opposition,
  and Jupiter-Neptune sextile.
- Local peak match `2011-12-26` is shown as current-cycle continuity.
- Historical analogue peaks remain older independent windows such as `1999-02-15`
  and `2006-11-27`.

`2020-01-12`:

- Active cycle window includes Pluto-Saturn conjunction with start `2019-11-10`,
  peak `2020-01-12`, and end `2020-03-15`.

`1789-07-14`:

- Active cycle windows include Neptune-Pluto trine and Jupiter-Uranus conjunction.
- Local peak `1789-07-13` is separated from historical analogues.

## Screenshots

- `work/reports/screenshots/after_explorer_2026_cycle_window_ux.png`
- `work/reports/screenshots/after_explorer_2011_cycle_window_ux.png`
