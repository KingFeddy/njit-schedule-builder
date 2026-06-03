"""
One-time backfill: reads flat days/start_time/end_time from sections
and inserts a single meetings row per section that has time data.

This produces imperfect data — a TRF course gets one row covering
all days rather than two separate patterns — but it seeds the meetings
table with real data before the scraper is updated to write correctly.

Run AFTER applying migration 007 (meetings table).
Run BEFORE updating the solver to read from meetings.

Usage:
    uv run python -m scripts.backfill_meetings
"""

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill() -> None:
    engine = create_async_engine(settings.DATABASE_URL)

    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT crn, term, days, start_time, end_time, location
                FROM sections
                WHERE days IS NOT NULL
                  AND start_time IS NOT NULL
                  AND end_time IS NOT NULL
            """)
        )
        rows = result.mappings().all()
        logger.info(f"Found {len(rows)} sections with time data to backfill.")

        inserted = 0
        skipped = 0
        for row in rows:
            try:
                await conn.execute(
                    text("""
                        INSERT INTO meetings (crn, term, days, start_time, end_time, location)
                        VALUES (:crn, :term, :days, :start_time, :end_time, :location)
                        ON CONFLICT (crn, term, days, start_time, end_time) DO NOTHING
                    """),
                    {
                        "crn":        row["crn"],
                        "term":       row["term"],
                        "days":       row["days"],
                        "start_time": row["start_time"],
                        "end_time":   row["end_time"],
                        "location":   row["location"],
                    }
                )
                inserted += 1
            except Exception as e:
                logger.warning(f"Skipped CRN {row['crn']}: {e}")
                skipped += 1

    await engine.dispose()
    logger.info(f"Backfill complete. Inserted: {inserted}, Skipped: {skipped}")
    logger.info(
        "NOTE: Multi-pattern courses (TRF lectures+labs) get one row here, "
        "not two. The scraper rewrite (Step 4) corrects this on next scrape."
    )


if __name__ == "__main__":
    asyncio.run(backfill())
