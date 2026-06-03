"""
Schedule solver — S1 skeleton.

Data loading and filtering are implemented here. The CSP search algorithm
(backtracking with MRV ordering) is added in S2. Until then, solve() uses
a brute-force product of all filtered candidates and validates every result.
"""
from __future__ import annotations
import itertools
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CommuterOptions, SectionSlot
from .conflicts import passes_commuter_filters, sections_conflict, validate_schedule
from ..services.courses import load_sections_with_meetings


@dataclass
class Schedule:
    """One conflict-free combination of sections, one per requested course."""
    sections: list[SectionSlot] = field(default_factory=list)


async def solve(
    session: AsyncSession,
    course_codes: list[str],
    term: str,
    options: CommuterOptions,
    max_results: int = 10,
) -> tuple[list[Schedule], list[str]]:
    """
    Return up to `max_results` conflict-free schedules covering all course_codes.

    Returns (schedules, warnings). warnings is a list of informational strings
    (e.g. courses with no available sections after filtering).

    S1 implementation: brute-force product filtered by conflicts.
    S2 replaces the inner loop with a backtracking CSP solver.
    """
    sections_by_course = await load_sections_with_meetings(session, course_codes, term)

    warnings: list[str] = []

    # Apply commuter filters per course
    filtered: dict[str, list[SectionSlot]] = {}
    for code in course_codes:
        candidates = [
            s for s in sections_by_course.get(code, [])
            if passes_commuter_filters(s, options)
        ]
        if not candidates:
            warnings.append(f"No sections available for {code} after applying filters.")
        filtered[code] = candidates

    # If any course has zero candidates, no complete schedule is possible
    if any(len(v) == 0 for v in filtered.values()):
        return [], warnings

    # Brute-force: try every combination of one section per course.
    # S2 replaces this with backtracking + MRV ordering.
    schedules: list[Schedule] = []
    for combo in itertools.product(*filtered.values()):
        sections = list(combo)

        # Validate before accepting — the safety net catches any solver bug
        violations = validate_schedule(sections)
        if violations:
            continue

        schedules.append(Schedule(sections=sections))
        if len(schedules) >= max_results:
            break

    return schedules, warnings
