-- Migration 007: meetings table
-- Subsystem 1 — meetings table redesign
--
-- Replaces the flat days/start_time/end_time columns on sections with a
-- normalized meetings table that supports multi-pattern sections (e.g. a
-- lecture on TR plus a lab on F at a different time).
--
-- The deprecated columns on sections (days, start_time, end_time) are NOT
-- dropped here. They stay nullable and unused until Migration 008 runs,
-- which is gated on 2+ weeks of meetings data confirmed in production.
--
-- Prerequisite: sections table must exist.
-- Verify after: SELECT COUNT(*) FROM meetings;
-- Run before deploying any code that reads from meetings.

CREATE TABLE meetings (
  id           BIGSERIAL    PRIMARY KEY,
  crn          TEXT         NOT NULL,
  term         TEXT         NOT NULL,
  days         TEXT,        -- single contiguous pattern: 'MW', 'TR', 'F', 'MWF'
                            -- NULL for fully async/online
  start_time   TIME,        -- NULL for async/online; Eastern Time (naive)
  end_time     TIME,        -- NULL for async/online; Eastern Time (naive)
  location     TEXT,        -- room/building; nullable

  FOREIGN KEY (crn, term) REFERENCES sections(crn, term) ON DELETE CASCADE,

  -- Time integrity: both null or both present
  CONSTRAINT meetings_time_pair CHECK (
    (start_time IS NULL AND end_time IS NULL) OR
    (start_time IS NOT NULL AND end_time IS NOT NULL)
  ),

  -- Start must precede end (guards against midnight-spanning/bad Banner data)
  CONSTRAINT meetings_time_order CHECK (
    start_time IS NULL OR start_time < end_time
  ),

  -- Deduplicate identical patterns for the same section
  UNIQUE (crn, term, days, start_time, end_time)
);

-- Primary access pattern: load all meetings for a set of (crn, term) pairs
CREATE INDEX idx_meetings_crn_term ON meetings (crn, term);
