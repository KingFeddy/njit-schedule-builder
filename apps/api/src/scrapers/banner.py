"""
Banner scraper — resilient Playwright implementation (S7).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time as time_module
from datetime import time
from typing import Optional

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .lock import advisory_lock, BANNER_SCRAPER_LOCK_ID

logger = logging.getLogger(__name__)

BANNER_BASE = "https://reg-prod.ec.njit.edu/StudentRegistrationSsb/ssb"
PAGE_SIZE   = 500
RETRY_DELAYS = [5, 15, 30]

# Keys that must be present in every Banner section object.
# Absence means Banner's JSON schema changed — abort, don't silently corrupt.
REQUIRED_SECTION_KEYS = {"courseReferenceNumber", "subject", "courseNumber", "meetingsFaculty"}

# Banner day keys in calendar order — order determines the output string.
_DAY_MAP = [
    ("monday",    "M"),
    ("tuesday",   "T"),
    ("wednesday", "W"),
    ("thursday",  "R"),
    ("friday",    "F"),
]


class BannerBlockedError(Exception):
    """Banner returned 403, an HTML error page, or unparseable content."""


class BannerSchemaError(Exception):
    """Banner JSON is missing expected keys — likely an Ellucian upgrade."""


# ─── Parsing helpers ──────────────────────────────────────────────────────────

def _parse_hhmm(banner_time: str) -> time:
    """Parse Banner's 4-digit 'HHMM' string to datetime.time."""
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


def _extract_professor_name(raw_section: dict) -> Optional[str]:
    """Return the first faculty displayName found in meetingsFaculty, or None."""
    for meeting in raw_section.get("meetingsFaculty", []):
        for member in meeting.get("faculty", []):
            name = member.get("displayName")
            if name:
                return name
    return None


# ─── Schema validation ────────────────────────────────────────────────────────

def _validate_section_schema(section: dict) -> None:
    """
    Raise BannerSchemaError if the section dict is missing any required Banner key.
    Called before processing each section — catches Ellucian upgrades early.
    """
    missing = REQUIRED_SECTION_KEYS - set(section.keys())
    if missing:
        raise BannerSchemaError(
            f"Banner section missing expected keys: {missing}. "
            f"Banner may have been upgraded. Keys present: {list(section.keys())[:10]}"
        )

    for meeting in section.get("meetingsFaculty", []):
        if "meetingTime" not in meeting:
            raise BannerSchemaError(
                f"Banner meeting entry missing 'meetingTime'. "
                f"Meeting keys present: {list(meeting.keys())}"
            )


# ─── HTTP layer ───────────────────────────────────────────────────────────────

async def _fetch_page(
    page,
    url: str,
    params: dict,
    timeout_ms: int = 30_000,
) -> dict:
    """
    Fetch one Banner results page and return parsed JSON.

    Raises:
      BannerBlockedError — 403, HTML content-type, or non-JSON body
      PlaywrightTimeout  — network timeout (retriable by caller)
    """
    query = "&".join(f"{k}={v}" for k, v in params.items())
    response = await page.goto(
        f"{url}?{query}",
        timeout=timeout_ms,
        wait_until="networkidle",
    )

    if response.status == 403:
        raise BannerBlockedError(f"Banner returned 403 — IP may be blocked.")

    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        raise BannerBlockedError(
            f"Banner returned HTML (status {response.status}) — session may have expired."
        )

    body = await response.text()
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise BannerBlockedError(f"Banner returned non-JSON body: {exc}") from exc

    # Log the top-level keys and 'data' field type so we can diagnose null responses
    # and term availability without having to decode the full payload.
    data_field = data.get("data")
    logger.debug(
        "_fetch_page: status=%s keys=%s data_type=%s totalCount=%s success=%s",
        response.status,
        list(data.keys()) if isinstance(data, dict) else type(data).__name__,
        type(data_field).__name__,
        data.get("totalCount"),
        data.get("success"),
    )
    return data


# ─── Section upsert ───────────────────────────────────────────────────────────

async def _upsert_section_with_meetings(
    session: AsyncSession,
    raw_section: dict,
    term: str,
) -> None:
    """
    Upsert one section and atomically replace all its meetings.
    Takes a raw Banner section dict and extracts all fields internally.
    DELETE + INSERT within one transaction so the solver never sees a section
    with zero meetings mid-update.
    open_seats is clamped to 0 — Banner returns negative values for waitlisted sections.
    """
    crn          = raw_section["courseReferenceNumber"]
    course_code  = f"{raw_section['subject']}{raw_section['courseNumber']}"
    open_seats   = max(0, raw_section.get("seatsAvailable", 0))
    total_seats  = raw_section.get("maximumEnrollment", 0)
    professor    = _extract_professor_name(raw_section)
    patterns     = raw_section.get("meetingsFaculty", [])

    # Section-level location from the first meeting that has one
    section_location: Optional[str] = None
    for p in patterns:
        loc = f"{p.get('building', '')} {p.get('room', '')}".strip() or None
        if loc:
            section_location = loc
            break

    async with session.begin():
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
            {
                "crn":           crn,
                "term":          term,
                "course_code":   course_code,
                "professor_name": professor,
                "total_seats":   total_seats,
                "open_seats":    open_seats,
                "location":      section_location,
            },
        )

        await session.execute(
            text("DELETE FROM meetings WHERE crn = :crn AND term = :term"),
            {"crn": crn, "term": term},
        )

        seen: set[tuple] = set()
        for pattern in patterns:
            days, start_time, end_time, location = _parse_meeting_pattern(pattern)

            dedup_key = (days, start_time, end_time)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            if (start_time is None) != (end_time is None):
                logger.warning("CRN %s: partial time in pattern, skipping", crn)
                continue

            if start_time is not None and end_time is not None and start_time >= end_time:
                logger.warning("CRN %s: start %s >= end %s, skipping", crn, start_time, end_time)
                continue

            await session.execute(
                text("""
                    INSERT INTO meetings (crn, term, days, start_time, end_time, location)
                    VALUES (:crn, :term, :days, :start_time, :end_time, :location)
                    ON CONFLICT (crn, term, days, start_time, end_time) DO NOTHING
                """),
                {
                    "crn":        crn,
                    "term":       term,
                    "days":       days,
                    "start_time": start_time,
                    "end_time":   end_time,
                    "location":   location,
                },
            )


# ─── Subject scrape ───────────────────────────────────────────────────────────

async def scrape_subject(
    session: AsyncSession,
    subject: str,
    term: str,
) -> tuple[int, int]:
    """
    Scrape all sections for one subject+term via Playwright.
    Returns (sections_upserted, sections_failed).

    Raises BannerBlockedError or BannerSchemaError on unrecoverable failures.
    Timeouts and transient errors are retried per RETRY_DELAYS.
    """
    upserted          = 0
    failed            = 0
    offset            = 0
    schema_error_count = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            await page.goto(
                f"{BANNER_BASE}/classSearch/classSearch",
                timeout=30_000,
                wait_until="networkidle",
            )

            while True:
                params = {
                    "term":        term,
                    "subject":     subject,
                    "pageOffset":  offset,
                    "pageMaxSize": PAGE_SIZE,
                }

                page_data = None
                for attempt, delay in enumerate([0] + RETRY_DELAYS):
                    if delay > 0:
                        logger.info(
                            "Banner/%s: offset %d, attempt %d, waiting %ds",
                            subject, offset, attempt + 1, delay,
                        )
                        await asyncio.sleep(delay)

                    try:
                        page_data = await _fetch_page(
                            page,
                            f"{BANNER_BASE}/searchResults/searchResults",
                            params,
                        )
                        break
                    except BannerBlockedError:
                        raise  # never retry a block
                    except BannerSchemaError:
                        raise  # never retry a schema error
                    except PlaywrightTimeout:
                        if attempt == len(RETRY_DELAYS):
                            raise
                        logger.warning(
                            "Banner/%s: timeout at offset %d, retrying in %ds",
                            subject, offset, RETRY_DELAYS[attempt],
                        )
                    except Exception as exc:
                        if attempt == len(RETRY_DELAYS):
                            raise
                        logger.warning("Banner/%s: %s, retrying", subject, exc)

                if page_data is None:
                    logger.error("Banner/%s: exhausted retries at offset %d", subject, offset)
                    break

                # Use `or []` not `get("data", [])` — Banner returns `"data": null`
                # for terms with no sections, and get(key, default) only uses the
                # default when the key is absent, not when its value is null.
                sections = page_data.get("data") or []
                total    = page_data.get("totalCount") or 0

                if page_data.get("data") is None:
                    logger.warning(
                        "Banner/%s: 'data' field is null at offset %d "
                        "(totalCount=%s, success=%s) — term may have no sections yet",
                        subject, offset, page_data.get("totalCount"), page_data.get("success"),
                    )

                for raw in sections:
                    try:
                        _validate_section_schema(raw)
                        await _upsert_section_with_meetings(session, raw, term)
                        upserted += 1
                    except BannerSchemaError as exc:
                        schema_error_count += 1
                        logger.error(
                            "Schema error on CRN %s: %s",
                            raw.get("courseReferenceNumber"), exc,
                        )
                        failed += 1
                        if schema_error_count >= 5:
                            raise BannerSchemaError(
                                f"5+ schema errors in {subject} — Banner may have been upgraded."
                            )
                    except Exception as exc:
                        logger.error(
                            "Failed to upsert CRN %s: %s",
                            raw.get("courseReferenceNumber"), exc,
                        )
                        failed += 1

                offset += PAGE_SIZE
                if offset >= total:
                    break

                await asyncio.sleep(2)

        finally:
            await browser.close()

    return upserted, failed


# ─── Full run ─────────────────────────────────────────────────────────────────

async def run_banner_scrape(
    session: AsyncSession,
    subjects: list[str],
    term: str,
) -> None:
    """
    Full Banner scrape with concurrency guard, per-subject isolation, and health log.

    Each subject is independent: a block on one subject logs it and continues.
    A schema change on any subject aborts all remaining subjects — the whole
    Banner JSON structure has changed and continuing would corrupt data.
    """
    async with advisory_lock(session, BANNER_SCRAPER_LOCK_ID, "banner") as acquired:
        if not acquired:
            await session.execute(
                text("""
                    INSERT INTO scraper_runs (scraper, term, status)
                    VALUES ('banner', :term, 'skipped_overlap')
                """),
                {"term": term},
            )
            await session.commit()
            return

        result = await session.execute(
            text("""
                INSERT INTO scraper_runs (scraper, term, status)
                VALUES ('banner', :term, 'running')
                RETURNING id
            """),
            {"term": term},
        )
        run_id = result.scalar()
        await session.commit()

        total_upserted = 0
        total_failed   = 0

        for subject in subjects:
            t0 = time_module.monotonic()
            try:
                upserted, failed = await scrape_subject(session, subject, term)
                total_upserted += upserted
                total_failed   += failed
                logger.info(
                    "Banner/%s: %d upserted, %d failed, %.1fs",
                    subject, upserted, failed, time_module.monotonic() - t0,
                )

            except BannerBlockedError as exc:
                logger.error("Banner/%s: BLOCKED — %s", subject, exc)
                total_failed += 1
                await session.execute(
                    text("""
                        INSERT INTO scraper_runs (scraper, subject, term, status, error_message)
                        VALUES ('banner', :subject, :term, 'blocked', :msg)
                    """),
                    {"subject": subject, "term": term, "msg": str(exc)},
                )
                await session.commit()
                # One block may be subject-specific — continue with others

            except BannerSchemaError as exc:
                logger.error("Banner/%s: SCHEMA CHANGE — %s", subject, exc)
                total_failed += 1
                await session.execute(
                    text("""
                        INSERT INTO scraper_runs
                            (scraper, subject, term, status, error_message)
                        VALUES ('banner', :subject, :term, 'schema_change', :msg)
                    """),
                    {"subject": subject, "term": term, "msg": str(exc)},
                )
                await session.commit()
                break  # Schema change affects all subjects — abort

            except Exception as exc:
                logger.error("Banner/%s: unexpected — %s", subject, exc, exc_info=True)
                total_failed += 1

        final_status = (
            "failed"    if total_upserted == 0 and total_failed > 0
            else "completed"
        )
        await session.execute(
            text("""
                UPDATE scraper_runs
                SET status            = :status,
                    sections_upserted = :upserted,
                    sections_failed   = :failed,
                    finished_at       = NOW()
                WHERE id = :run_id
            """),
            {
                "status":   final_status,
                "upserted": total_upserted,
                "failed":   total_failed,
                "run_id":   run_id,
            },
        )
        await session.commit()
        logger.info(
            "Banner scrape complete: %d upserted, %d failed, status=%s",
            total_upserted, total_failed, final_status,
        )
