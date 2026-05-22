# Golden Fixtures

Golden fixtures are regression anchors for Astro Global. They verify that
astronomy, aspect detection, cycle registry, vectorizer, search, and clustering
stay consistent.

Planned folders:

- `planetary_states/`
- `aspects/`
- `cycles/`
- `resonance_search/`

Current planetary-state fixture:

- `planetary_states/jpl_horizons_2026-05-22T12Z.json` anchors the core
  bodies against NASA/JPL Horizons observer-centered ecliptic-of-date apparent
  longitude and latitude. Swiss Ephemeris tests compare against this fixture
  when the optional `swisseph` module is available locally.
