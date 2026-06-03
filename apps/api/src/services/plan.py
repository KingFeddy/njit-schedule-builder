from __future__ import annotations

import logging

from src.schemas.plan import (
    COURSE_CODE_PATTERN,
    WILDCARD_PATTERN,
    ParsedDegree,
    ParsedDegreeValidated,
    ParseValidationError,
)

logger = logging.getLogger(__name__)

CREDIT_CONSISTENCY_TOLERANCE = 6


def validate_parsed_degree(raw: ParsedDegree) -> ParsedDegreeValidated:
    """
    Business-logic validation. Raises ParseValidationError on violations.
    Only a ParsedDegreeValidated should be returned to the client or passed
    to the planner. Raw ParsedDegree is never trusted downstream.
    """
    if not raw.majors:
        raise ParseValidationError(
            "majors",
            "No major detected. Please verify this is a DegreeWorks degree audit PDF.",
        )

    if all(
        x is not None
        for x in [raw.credits_completed, raw.credits_required, raw.credits_remaining]
    ):
        computed = raw.credits_required - raw.credits_completed  # type: ignore[operator]
        delta = abs(raw.credits_remaining - computed)  # type: ignore[operator]
        if delta > CREDIT_CONSISTENCY_TOLERANCE:
            raise ParseValidationError(
                "credits",
                f"Credit counts are inconsistent: {raw.credits_completed} completed + "
                f"{raw.credits_remaining} remaining ≠ {raw.credits_required} required "
                f"(delta: {delta}). The PDF may not be a DegreeWorks audit.",
            )

    if raw.credits_required is not None and not (100 <= raw.credits_required <= 160):
        raise ParseValidationError(
            "credits_required",
            f"credits_required={raw.credits_required} is outside the plausible NJIT "
            f"range (100–160).",
        )

    # Filter completed_courses: keep valid NJIT codes, log and drop the rest.
    # AP credit and transfer credit lines produce non-standard codes (ENG121, CHEM5)
    # that the scraper never saw — drop them rather than letting them pollute the plan.
    valid_completed: list[str] = []
    for code in raw.completed_courses:
        if COURSE_CODE_PATTERN.match(code):
            valid_completed.append(code)
        elif WILDCARD_PATTERN.search(code):
            logger.warning("wildcard in completed_courses: %r — skipping", code)
        else:
            logger.warning(
                "non-standard code in completed_courses: %r (AP/transfer credit?)", code
            )

    valid_in_progress: list[str] = []
    for code in raw.in_progress_courses:
        if COURSE_CODE_PATTERN.match(code):
            valid_in_progress.append(code)
        else:
            logger.warning(
                "non-standard code in in_progress_courses: %r — skipping", code
            )

    for item in raw.still_needed:
        for code in item.options:
            if not WILDCARD_PATTERN.search(code) and not COURSE_CODE_PATTERN.match(code):
                logger.warning(
                    "non-standard code in still_needed: %r (%r)", code, item.requirement
                )

    if (
        raw.credits_remaining is not None
        and raw.credits_remaining > 15
        and len(raw.still_needed) < 2
    ):
        logger.warning(
            "credits_remaining=%d but only %d still_needed items — "
            "regex may have missed requirement blocks",
            raw.credits_remaining,
            len(raw.still_needed),
        )

    return ParsedDegreeValidated(
        student_name=raw.student_name,
        majors=raw.majors,
        minors=raw.minors,
        catalog_year=raw.catalog_year,
        credits_completed=raw.credits_completed,
        credits_required=raw.credits_required,
        credits_remaining=raw.credits_remaining,
        completed_courses=valid_completed,
        in_progress_courses=valid_in_progress,
        still_needed=raw.still_needed,
    )
