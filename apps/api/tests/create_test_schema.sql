-- Test schema for CI. Applied to the empty PostgreSQL container before pytest runs.
-- Mirrors the production schema exactly. Kept in sync with the migration files.
-- When a new migration is added to apps/api/migrations/, update this file too.

-- ── Base tables (no migration number — existed before migrations were tracked) ──

CREATE TABLE IF NOT EXISTS courses (
  course_code   TEXT        PRIMARY KEY,
  title         TEXT        NOT NULL,
  credits       INTEGER     NOT NULL,
  prerequisites TEXT[]      NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS sections (
  crn             TEXT        NOT NULL,
  term            TEXT        NOT NULL,
  course_code     TEXT        NOT NULL REFERENCES courses(course_code) ON DELETE CASCADE,
  professor_name  TEXT,
  total_seats     INTEGER     NOT NULL DEFAULT 0,
  open_seats      INTEGER     NOT NULL DEFAULT 0,
  location        TEXT,
  scraped_at      TIMESTAMPTZ,

  PRIMARY KEY (crn, term)
);

CREATE INDEX IF NOT EXISTS idx_sections_course_term ON sections(course_code, term);
CREATE INDEX IF NOT EXISTS idx_sections_term        ON sections(term);

-- ── Migration 007: meetings table ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS meetings (
  id          BIGSERIAL   PRIMARY KEY,
  crn         TEXT        NOT NULL,
  term        TEXT        NOT NULL,
  days        TEXT,
  start_time  TIME,
  end_time    TIME,
  location    TEXT,

  FOREIGN KEY (crn, term) REFERENCES sections(crn, term) ON DELETE CASCADE,

  CONSTRAINT meetings_time_pair CHECK (
    (start_time IS NULL AND end_time IS NULL) OR
    (start_time IS NOT NULL AND end_time IS NOT NULL)
  ),
  CONSTRAINT meetings_time_order CHECK (
    start_time IS NULL OR start_time < end_time
  ),

  UNIQUE (crn, term, days, start_time, end_time)
);

CREATE INDEX IF NOT EXISTS idx_meetings_crn_term ON meetings(crn, term);

-- ── Migration 012: scraper health tables ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS scraper_runs (
  id                BIGSERIAL     PRIMARY KEY,
  scraper           TEXT          NOT NULL CHECK (scraper IN ('banner', 'rmp')),
  subject           TEXT,
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
  duration_ms       INTEGER GENERATED ALWAYS AS (
    (EXTRACT(EPOCH FROM (finished_at - started_at)) * 1000)::integer
  ) STORED
);

CREATE INDEX IF NOT EXISTS idx_scraper_runs_recent ON scraper_runs(scraper, started_at DESC);

CREATE TABLE IF NOT EXISTS rmp_cache (
  professor_name  TEXT        PRIMARY KEY,
  rmp_data        JSONB,
  cached_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rmp_cache_expiry ON rmp_cache(expires_at);
