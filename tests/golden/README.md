# Golden Fixtures

Golden fixtures are regression anchors for Astro Global. They verify that
astronomy, aspect detection, cycle registry, vectorizer, search, and clustering
stay consistent.

Planned folders:

- `planetary_states/`
- `aspects/`
- `cycles/`
- `resonance_search/`
- `resonance_compare/`
- `articles/`

Current planetary-state fixture:

- `planetary_states/jpl_horizons_2026-05-22T12Z.json` anchors the core
  bodies against NASA/JPL Horizons observer-centered ecliptic-of-date apparent
  longitude and latitude. Swiss Ephemeris tests compare against this fixture
  when the optional `swisseph` module is available locally.

Current resonance-search fixture:

- `resonance_search/synthetic_2026-05-22T12Z.json` locks the full
  `/resonance/search` response for the deterministic synthetic provider,
  including clustered episodes, matched events, coverage, cycles, and Polish
  deterministic summary.

Current resonance-compare fixture:

- `resonance_compare/synthetic_2026-05-22T12Z_vs_2020-03-11T00Z.json` locks the
  full `/resonance/compare` response for the deterministic synthetic provider,
  including both search payloads, query-vector similarity, shared cycles,
  shared events, warnings, and deterministic comparison summary.
- `resonance_compare/presets_swiss_1500_now.json` locks the
  `/resonance/compare/presets` response used by thin web clients to fill compare
  requests without inventing dates or event pairs outside backend data.

Current article seed fixture:

- `articles/seeds_swiss_1500_now.json` locks the `/articles/seeds` response.
  It must remain seed-only: no generated article body, no added facts, and no
  events outside backend data.
