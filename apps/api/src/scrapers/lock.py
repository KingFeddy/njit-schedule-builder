from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

BANNER_SCRAPER_LOCK_ID = 12345001
RMP_SCRAPER_LOCK_ID    = 12345002


@asynccontextmanager
async def advisory_lock(session: AsyncSession, lock_id: int, scraper_name: str):
    """
    Acquires a Postgres transaction-level advisory lock.
    Yields True if acquired, False if another instance holds it.

    Uses pg_try_advisory_xact_lock (not session-level) so the lock releases
    on commit/rollback — a well-defined boundary that's safe with asyncpg
    connection pooling. Caller must have an open transaction.
    """
    result = await session.execute(
        text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
        {"lock_id": lock_id},
    )
    acquired = result.scalar()

    if not acquired:
        logger.info("%s: lock already held — another instance is running", scraper_name)
        yield False
        return

    yield True
    # Lock releases automatically on commit/rollback — no explicit unlock.
