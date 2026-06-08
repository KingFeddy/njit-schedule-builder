-- Migration 013: add section_number to sections
--
-- Adds the Banner sequenceNumber (e.g. "001", "002") as a nullable TEXT column.
-- Nullable because existing rows have no value until the next scraper run,
-- and sections with missing Banner data (rare edge cases) may never get one.
--
-- Additive — safe to run while the API is live. The column defaults to NULL
-- so no backfill is needed; values populate on the next banner scrape.
--
-- Verify after:
--   SELECT crn, section_number FROM sections LIMIT 5;
--   (All NULL until next scrape run)

ALTER TABLE sections ADD COLUMN IF NOT EXISTS section_number TEXT;
