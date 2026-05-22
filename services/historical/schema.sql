CREATE TABLE IF NOT EXISTS historical_event (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  display_date TEXT NOT NULL,
  start_astro_year INTEGER NOT NULL,
  end_astro_year INTEGER NOT NULL,
  category TEXT NOT NULL,
  event_kind TEXT NOT NULL,
  region TEXT NOT NULL,
  geo_scope TEXT NOT NULL,
  source_url TEXT NOT NULL,
  confidence_score DOUBLE NOT NULL,
  is_ongoing BOOLEAN NOT NULL,
  end_year_policy TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS event_source (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_quality TEXT NOT NULL,
  source_precision TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS planetary_state_index (
  id BIGINT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  astro_profile_id TEXT NOT NULL,
  vector_version TEXT NOT NULL,
  jd_ut DOUBLE NOT NULL,
  astro_year INTEGER NOT NULL,
  iso_date TEXT NOT NULL,
  window_tag TEXT NOT NULL,
  positions_json JSON NOT NULL,
  aspects_json JSON,
  feature_debug_json JSON
);

CREATE TABLE IF NOT EXISTS resonance_run (
  id TEXT PRIMARY KEY,
  input_hash TEXT NOT NULL,
  datetime_utc TEXT NOT NULL,
  search_profile TEXT NOT NULL,
  astro_profile_id TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT current_timestamp,
  result_json JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS narrative_cache (
  id TEXT PRIMARY KEY,
  input_hash TEXT NOT NULL,
  model_name TEXT NOT NULL,
  output_json JSON NOT NULL,
  validation_json JSON NOT NULL,
  created_at TIMESTAMP DEFAULT current_timestamp
);
