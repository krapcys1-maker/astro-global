# Known Resonance Event Drift

- Baseline: `seed 204 before a685d4e`
- Current: `seed 220 current`
- Cases compared: 10
- Cases with matched-event changes: 3
- Expected-event regressions: 0
- Warning count delta: `{"war_bias": -1}`
- Event-mix warning count delta: `{"long_process_heavy": 1}`
- Drift warning counts: `{"candidate_long_process_share_increased": 4, "matched_event_set_changed": 3, "matched_events_removed": 3, "new_event_mix_warning": 1}`

## Case Deltas

### 1914-07-28

- Added matched events: `evt_progressive_era, evt_womens_suffrage_movement`
- Removed matched events: `evt_second_industrial_revolution`
- Expected events: `evt_world_war_i`
- Lost expected events: `none`
- Candidate long-process share: `0.429 -> 0.556`
- Selected long-process share: `0.333 -> 0.333`
- Event-mix warnings: `none -> long_process_heavy`
- Drift warnings: `matched_event_set_changed, matched_events_removed, new_event_mix_warning`

### 1939-09-01

- Added matched events: `none`
- Removed matched events: `none`
- Expected events: `evt_great_depression, evt_world_war_ii`
- Lost expected events: `none`
- Candidate long-process share: `0.167 -> 0.167`
- Selected long-process share: `0.167 -> 0.167`
- Event-mix warnings: `none -> none`
- Drift warnings: `none`

### 1965-10-09

- Added matched events: `evt_space_race`
- Removed matched events: `evt_eritrea_independence_war`
- Expected events: `evt_cultural_revolution, evt_green_revolution, evt_vietnam_war`
- Lost expected events: `none`
- Candidate long-process share: `0.455 -> 0.647`
- Selected long-process share: `0.167 -> 0.167`
- Event-mix warnings: `none -> none`
- Drift warnings: `matched_event_set_changed, matched_events_removed, candidate_long_process_share_increased`

### 1968-05-01

- Added matched events: `none`
- Removed matched events: `none`
- Expected events: `evt_cultural_revolution, evt_vietnam_war`
- Lost expected events: `none`
- Candidate long-process share: `0.400 -> 0.605`
- Selected long-process share: `0.000 -> 0.000`
- Event-mix warnings: `none -> none`
- Drift warnings: `candidate_long_process_share_increased`

### 1989-03-03

- Added matched events: `none`
- Removed matched events: `none`
- Expected events: `evt_fall_berlin_wall, evt_tiananmen_1989`
- Lost expected events: `none`
- Candidate long-process share: `0.361 -> 0.521`
- Selected long-process share: `0.000 -> 0.000`
- Event-mix warnings: `none -> none`
- Drift warnings: `candidate_long_process_share_increased`

### 1989-11-09

- Added matched events: `none`
- Removed matched events: `none`
- Expected events: `evt_fall_berlin_wall, evt_soviet_dissolution, evt_tiananmen_1989`
- Lost expected events: `none`
- Candidate long-process share: `0.341 -> 0.460`
- Selected long-process share: `0.000 -> 0.000`
- Event-mix warnings: `none -> none`
- Drift warnings: `none`

### 2008-09-15

- Added matched events: `evt_millennium_development_goals`
- Removed matched events: `evt_colombian_conflict`
- Expected events: `evt_financial_crisis_2007_2008`
- Lost expected events: `none`
- Candidate long-process share: `0.353 -> 0.621`
- Selected long-process share: `0.312 -> 0.312`
- Event-mix warnings: `none -> none`
- Drift warnings: `matched_event_set_changed, matched_events_removed, candidate_long_process_share_increased`

### 2020-01-12

- Added matched events: `none`
- Removed matched events: `none`
- Expected events: `evt_covid_19_pandemic`
- Lost expected events: `none`
- Candidate long-process share: `0.148 -> 0.258`
- Selected long-process share: `0.000 -> 0.000`
- Event-mix warnings: `none -> none`
- Drift warnings: `none`

### 2020-12-21

- Added matched events: `none`
- Removed matched events: `none`
- Expected events: `evt_covid_19_pandemic`
- Lost expected events: `none`
- Candidate long-process share: `0.158 -> 0.273`
- Selected long-process share: `0.000 -> 0.000`
- Event-mix warnings: `none -> none`
- Drift warnings: `none`

### 2021-02-17

- Added matched events: `none`
- Removed matched events: `none`
- Expected events: `evt_covid_19_pandemic`
- Lost expected events: `none`
- Candidate long-process share: `0.154 -> 0.267`
- Selected long-process share: `0.000 -> 0.000`
- Event-mix warnings: `none -> none`
- Drift warnings: `none`
