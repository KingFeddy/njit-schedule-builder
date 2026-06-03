-- Migration 012: scraper health tracking tables
-- Subsystem 7 — scraper resilience
--
-- Additive — safe to run at any time, no dependencies on other migrations.
--
-- scraper_runs: one row per scraper execution. Records whether the run
-- completed, failed, was blocked by Banner, or was skipped. The
-- duration_ms generated column lets you query slow runs without arithmetic.
--
-- rmp_cache: replaces the on-disk diskcache with a Postgres table so cached
-- RMP ratings survive container restarts on Railway.
--
-- Verify after:
--   SELECT tablename FROM pg_tables WHERE tablename IN ('scraper_runs', 'rmp_cache');

CREATE TABLE scraper_runs (
  id                BIGSERIAL     PRIMARY KEY,
  scraper           TEXT          NOT NULL CHECK (scraper IN ('banner', 'rmp')),
  subject           TEXT,         -- NULL for full-run records
  term              TEXT,
  status            TEXT          NOT NULL CHECK (status IN (
                                    'running', 'completed', 'failed',
                                    'blocked', 'schema_change', 'skipped_overlap'
                                  )),
  sections_upserted INTEGER,
  sections_failed   INTEGER       DEFAULT 0,
  error_message     TEXT,
  started_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  finished_at       TIMESTAMPTZ,
  -- NULL while the run is still 'running'
  duration_ms       INTEGER GENERATED ALWAYS AS (
    (EXTRACT(EPOCH FROM (finished_at - started_at)) * 1000)::integer
  ) STORED
);

CREATE INDEX idx_scraper_runs_recent ON scraper_runs(scraper, started_at DESC);

-- RMP cache in Postgres (replaces diskcache)
CREATE TABLE rmp_cache (
  professor_name  TEXT        PRIMARY KEY,
  rmp_data        JSONB,      -- NULL means professor was not found on RMP
  cached_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_rmp_cache_expiry ON rmp_cache(expires_at);
