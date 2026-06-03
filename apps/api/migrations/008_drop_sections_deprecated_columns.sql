-- Migration 008: drop deprecated time columns from sections
-- Subsystem 1 — cleanup after meetings table is fully populated
--
-- !! DEFERRED — DO NOT RUN UNTIL ALL THREE CONDITIONS ARE MET !!
--
--   1. Migration 007 (meetings table) has been applied.
--   2. The scraper has been running the meetings-based upsert in production
--      for at least 2 weeks with confirmed data.
--   3. SELECT COUNT(*) FROM meetings returns a non-zero count.
--
-- Dropping these columns while meetings is empty leaves the conflict engine
-- with no time data — it will treat every section as async and generate
-- schedules with zero conflict detection. No error is raised; schedules
-- will silently appear valid.
--
-- Verify before running:
--   SELECT COUNT(*) FROM meetings;   -- must be > 0
--   SELECT COUNT(*) FROM sections WHERE days IS NOT NULL;  -- compare against meetings count

ALTER TABLE sections DROP COLUMN IF EXISTS days;
ALTER TABLE sections DROP COLUMN IF EXISTS start_time;
ALTER TABLE sections DROP COLUMN IF EXISTS end_time;
