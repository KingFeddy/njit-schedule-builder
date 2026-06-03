from __future__ import annotations
from datetime import time
from unittest.mock import AsyncMock, patch
import pytest

from src.scheduler.models import CommuterOptions, MeetingSlot, SectionSlot
from src.scheduler.solver import Schedule, solve


def meeting(days, start, end):
    return MeetingSlot("CRN1", "202690", days, time(*map(int, start.split(":"))),
                       time(*map(int, end.split(":"))))

def section(crn, course, meetings_list):
    return SectionSlot(crn=crn, term="202690", course_code=course,
                       professor_name=None, total_seats=30, open_seats=5,
                       meetings=meetings_list)


class TestSolverValidationGuard:

    @pytest.mark.asyncio
    async def test_conflicting_result_never_returned(self):
        """
        If the search algorithm somehow produces a conflicting pair of sections,
        validate_schedule must catch it before it reaches the caller.
        The solver must never return a schedule with conflicts.
        """
        cs101 = section("A", "CS101", [meeting("MW", "10:00", "11:20")])
        cs201 = section("B", "CS201", [meeting("MW", "10:00", "11:20")])  # same time — conflict

        loader = AsyncMock(return_value={
            "CS101": [cs101],
            "CS201": [cs201],
        })

        with patch("src.scheduler.solver.load_sections_with_meetings", loader):
            schedules, _ = await solve(
                session=AsyncMock(),
                course_codes=["CS101", "CS201"],
                term="202690",
                options=CommuterOptions(),
            )

        for schedule in schedules:
            for i, a in enumerate(schedule.sections):
                for b in schedule.sections[i + 1:]:
                    from src.scheduler.conflicts import sections_conflict
                    assert not sections_conflict(a, b), (
                        f"Solver returned conflicting schedule: "
                        f"{a.course_code} vs {b.course_code}"
                    )

    @pytest.mark.asyncio
    async def test_commuter_filter_excludes_blocked_day(self):
        """Sections that violate commuter constraints must be excluded before solving."""
        friday_section = section("F1", "CS101", [meeting("F", "10:00", "11:00")])
        mw_section     = section("M1", "CS101", [meeting("MW", "10:00", "11:00")])

        loader = AsyncMock(return_value={"CS101": [friday_section, mw_section]})

        with patch("src.scheduler.solver.load_sections_with_meetings", loader):
            schedules, _ = await solve(
                session=AsyncMock(),
                course_codes=["CS101"],
                term="202690",
                options=CommuterOptions(blocked_days=["F"]),
            )

        # Every schedule must contain only the MW section, never the Friday section
        for schedule in schedules:
            crns = [s.crn for s in schedule.sections]
            assert "F1" not in crns, "Friday section must be excluded by commuter filter"

    @pytest.mark.asyncio
    async def test_no_sections_after_filter_returns_empty(self):
        """If all sections are filtered out, solver returns no schedules."""
        friday_only = section("F1", "CS101", [meeting("F", "10:00", "11:00")])
        loader = AsyncMock(return_value={"CS101": [friday_only]})

        with patch("src.scheduler.solver.load_sections_with_meetings", loader):
            schedules, _ = await solve(
                session=AsyncMock(),
                course_codes=["CS101"],
                term="202690",
                options=CommuterOptions(blocked_days=["F"]),
            )

        assert schedules == []

    @pytest.mark.asyncio
    async def test_schedule_has_sections_attribute(self):
        """Schedule objects returned by solve must have a .sections list."""
        cs101 = section("A", "CS101", [meeting("MWF", "10:00", "10:50")])
        loader = AsyncMock(return_value={"CS101": [cs101]})

        with patch("src.scheduler.solver.load_sections_with_meetings", loader):
            schedules, _ = await solve(
                session=AsyncMock(),
                course_codes=["CS101"],
                term="202690",
                options=CommuterOptions(),
            )

        assert len(schedules) >= 1
        assert hasattr(schedules[0], "sections")
        assert isinstance(schedules[0].sections, list)
