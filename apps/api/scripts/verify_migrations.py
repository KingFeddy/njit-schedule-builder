import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings

EXPECTED_TABLES = [
    "courses",
    "sections",
    "meetings",
    "professors",
    "scraper_runs",
    "rmp_cache",
]

EXPECTED_COLUMNS = {
    "sections":     ["crn", "term", "course_code", "open_seats", "scraped_at"],
    "meetings":     ["id", "crn", "term", "days", "start_time", "end_time"],
    "courses":      ["course_code", "title", "credits", "prerequisites"],
    "scraper_runs": ["id", "scraper", "status", "started_at"],
    "rmp_cache":    ["professor_name", "rmp_data", "expires_at"],
}


async def verify() -> bool:
    engine = create_async_engine(settings.DATABASE_URL)
    errors = []

    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        existing_tables = {row[0] for row in result}

        for table in EXPECTED_TABLES:
            if table not in existing_tables:
                errors.append(f"MISSING TABLE: {table}")

        for table, columns in EXPECTED_COLUMNS.items():
            if table not in existing_tables:
                continue
            col_result = await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :table AND table_schema = 'public'"
                ),
                {"table": table},
            )
            existing_cols = {row[0] for row in col_result}
            for col in columns:
                if col not in existing_cols:
                    errors.append(f"MISSING COLUMN: {table}.{col}")

    await engine.dispose()

    if errors:
        print("MIGRATION VERIFICATION FAILED:")
        for e in errors:
            print(f"  x {e}")
        return False

    print("All migrations verified.")
    return True


if __name__ == "__main__":
    ok = asyncio.run(verify())
    sys.exit(0 if ok else 1)
