# Manual Review - New Events 204 to 220

- Baseline: `9652fe2` / seed 204
- Current scope: 16 events added in seed 220 expansion
- Review date: 2026-05-23

## Summary

- Reviewed: 16 events
- Kept unchanged: 15 events
- Corrected: 1 event
- Removed: 0 events
- Main risk checked: broad `long_process` events increasing candidate-pool drift.

## Correction

### `evt_non_aligned_movement`

- Before: `Non-Aligned Movement`, `1961-`, `long_process`, ongoing through build year.
- After: `Non-Aligned Movement founding`, `1961`, `instant_event`.
- Reason: in the current curated seed this event is more useful as a founding/institution marker, not as an always-overlapping ongoing process. The previous open-ended long-process form inflated modern candidate pools and appeared in the 2008 benchmark window despite not being a direct 2008 event.

## Kept Unchanged

These events remain acceptable for the current seed, but several should be watched as the dataset grows:

- `evt_womens_suffrage_movement` - broad but bounded civil-rights process; appears in 1914 drift without losing expected events.
- `evt_progressive_era` - bounded national reform period; appears in 1914 drift without increasing selected long-process share.
- `evt_urbanization_acceleration` - very broad ongoing global process; keep for now because it is demographic context, but monitor modern windows.
- `evt_european_integration` - bounded regional integration period ending at Maastricht/EU formation.
- `evt_space_race` - bounded global technological process; added in 1965 drift without losing expected events.
- `evt_second_wave_feminism` - bounded transregional civil-rights process.
- `evt_modern_environmental_movement` - bounded transregional environmental process.
- `evt_great_society` - bounded national social-policy period.
- `evt_history_of_internet` - bounded global technology process before web commercialization.
- `evt_neoliberal_turn` - broad ideological/economic process; keep but monitor overlap with globalization.
- `evt_globalization_era` - broad global process; keep but monitor 2008 windows.
- `evt_world_wide_web` - bounded global technology development period.
- `evt_eurozone_launch` - bounded European transition.
- `evt_millennium_development_goals` - bounded global institutional program.
- `evt_belt_and_road_initiative` - ongoing transregional infrastructure initiative; keep but monitor future modern-window density.

## Follow-up Watchlist

- `evt_urbanization_acceleration`, `evt_neoliberal_turn`, `evt_globalization_era`, and `evt_belt_and_road_initiative` are broad context events. They are not wrong, but if future benchmark drift shows long-process displacement, they should be narrowed, down-weighted, or moved to a separate context layer.
