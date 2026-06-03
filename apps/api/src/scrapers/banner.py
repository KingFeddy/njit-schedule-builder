"""
Banner scraper — S1 portion: section upsert and meeting pattern parsing.
Full Playwright scraping logic is added in S7.
"""
from __future__ import annotations
import logging
from datetime import time
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Banner day keys in calendar order — order here determines the output string.
_DAY_MAP = [
    ("monday",    "M"),
    ("tuesday",   "T"),
    ("wednesday", "W"),
    ("thursday",  "R"),
    ("friday",    "F"),
]


def _parse_hhmm(banner_time: str) -> time:
    """Parse Banner's 4-digit 'HHMM' format (e.g. '1000', '0830') to datetime.time."""
    return time(int(banner_time[:2]), int(banner_time[2:]))


def _parse_meeting_pattern(
    pattern: dict,
) -> tuple[Optional[str], Optional[time], Optional[time], Optional[str]]:
    """
    Extract (days, start_time, end_time, location) from one Banner meetingsFaculty entry.
    Returns None for any field Banner doesn't provide (async/TBA sections).
    Day characters are always in MTWRF calendar order.
    """
    meeting_time = pattern.get("meetingTime", {})

    days_str = "".join(char for key, char in _DAY_MAP if meeting_time.get(key))
    days = days_str or None

    start_raw = meeting_time.get("beginTime")
    end_raw   = meeting_time.get("endTime")
    start_time = _parse_hhmm(start_raw) if start_raw else None
    end_time   = _parse_hhmm(end_raw)   if end_raw   else None

    location = (
        f"{pattern.get('building', '')} {pattern.get('room', '')}".strip() or None
    )

    return days, start_time, end_time, location


async def _upsert_section_with_meetings(
    session: AsyncSession,
    section_data: dict,
    meeting_patterns: list[dict],
    term: str,
) -> None:
    """
    Upsert one section and atomically replace all its meetings.
    DELETE + INSERT within one transaction so the solver never sees a section
    with zero meetings mid-update.
    """
    async with session.begin():
        # 1. Upsert the section row (deprecated flat time columns not written)
        await session.execute(
            text("""
                INSERT INTO sections (crn, term, course_code, professor_name,
                                      total_seats, open_seats, location, scraped_at)
                VALUES (:crn, :term, :course_code, :professor_name,
                        :total_seats, :open_seats, :location, NOW())
                ON CONFLICT (crn, term) DO UPDATE SET
                    professor_name = EXCLUDED.professor_name,
                    total_seats    = EXCLUDED.total_seats,
                    open_seats     = EXCLUDED.open_seats,
                    location       = EXCLUDED.location,
                    scraped_at     = EXCLUDED.scraped_at
            """),
            section_data,
        )

        # 2. Delete all existing meetings (handles Banner dropping a pattern)
        await session.execute(
            text("DELETE FROM meetings WHERE crn = :crn AND term = :term"),
            {"crn": section_data["crn"], "term": term},
        )

        # 3. Insert fresh meetings — one row per Banner pattern
        seen: set[tuple] = set()
        for pattern in meeting_patterns:
            days, start_time, end_time, location = _parse_meeting_pattern(pattern)

            dedup_key = (days, start_time, end_time)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            if (start_time is None) != (end_time is None):
                logger.warning(
                    "CRN %s: partial time in pattern (one of start/end is None), skipping",
                    section_data["crn"],
                )
                continue

            if start_time is not None and end_time is not None and start_time >= end_time:
                logger.warning(
                    "CRN %s: start %s >= end %s, skipping",
                    section_data["crn"], start_time, end_time,
                )
                continue

            await session.execute(
                text("""
                    INSERT INTO meetings (crn, term, days, start_time, end_time, location)
                    VALUES (:crn, :term, :days, :start_time, :end_time, :location)
                    ON CONFLICT (crn, term, days, start_time, end_time) DO NOTHING
                """),
                {
                    "crn":        section_data["crn"],
                    "term":       term,
                    "days":       days,
                    "start_time": start_time,
                    "end_time":   end_time,
                    "location":   location,
                },
            )
