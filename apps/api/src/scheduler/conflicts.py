from __future__ import annotations
from .models import CommuterOptions, MeetingSlot, SectionSlot
from .time_utils import to_minute_intervals, intervals_overlap, parse_hhmm


def _meeting_intervals(meeting: MeetingSlot) -> list[tuple[int, int]]:
    return to_minute_intervals(meeting.days, meeting.start_time, meeting.end_time)


def _section_intervals(section: SectionSlot) -> list[tuple[int, int]]:
    """Flatten all meetings of a section into MOW intervals. Async → []."""
    result: list[tuple[int, int]] = []
    for meeting in section.meetings:
        result.extend(_meeting_intervals(meeting))
    return result


def sections_conflict(section_a: SectionSlot, section_b: SectionSlot) -> bool:
    """True iff any MOW interval of section_a overlaps any interval of section_b."""
    intervals_a = _section_intervals(section_a)
    intervals_b = _section_intervals(section_b)
    return any(
        intervals_overlap(a, b)
        for a in intervals_a
        for b in intervals_b
    )


def passes_commuter_filters(section: SectionSlot, options: CommuterOptions) -> bool:
    """
    True iff ALL meetings of the section satisfy all commuter constraints.
    A section fails if ANY single meeting violates a constraint.
    Async meetings (no days, no times) always pass time-bound constraints.
    """
    earliest = parse_hhmm(options.earliest_start) if options.earliest_start else None
    latest   = parse_hhmm(options.latest_end)     if options.latest_end     else None

    for meeting in section.meetings:
        if options.blocked_days and meeting.days:
            if any(d in meeting.days for d in options.blocked_days):
                return False

        if meeting.start_time is not None:
            if earliest is not None and meeting.start_time < earliest:
                return False
            if latest is not None and meeting.end_time is not None and meeting.end_time > latest:
                return False

    return True


def validate_schedule(sections: list[SectionSlot]) -> list[str]:
    """
    Returns conflict descriptions for any pair of sections that overlap.
    Empty list means the schedule is valid. Call after every solve result.
    """
    violations = []
    for i, a in enumerate(sections):
        for b in sections[i + 1:]:
            if sections_conflict(a, b):
                violations.append(
                    f"Conflict: {a.course_code} ({a.crn}) overlaps {b.course_code} ({b.crn})"
                )
    return violations
