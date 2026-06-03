-- Migration 009: add prerequisites column to courses
-- Subsystem 6 — planner engine
--
-- Additive — safe to run at any time. Existing rows get an empty array default.
-- The planner does not enforce prerequisites in MVP; the column exists so the
-- scraper can populate it when Banner exposes prerequisite data, and enforcement
-- can be added later without a schema change.
--
-- Verify after: SELECT column_name FROM information_schema.columns
--               WHERE table_name = 'courses' AND column_name = 'prerequisites';

ALTER TABLE courses ADD COLUMN IF NOT EXISTS prerequisites TEXT[] NOT NULL DEFAULT '{}';
