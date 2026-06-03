from __future__ import annotations
from datetime import time
import pytest

from src.scheduler.models import CommuterOptions, MeetingSlot, SectionSlot
from src.scheduler.conflicts import (
    passes_commuter_filters,
    sections_conflict,
    validate_schedule,
)
from src.scheduler.time_utils import intervals_overlap, to_minute_intervals


# ── Helpers ───────────────────────────────────────────────────────────────────

def t(hhmm: str) -> time:
    h, m = hhmm.split(":")
    return time(int(h), int(m))

def meeting(days: str, start: str, end: str) -> MeetingSlot:
    return MeetingSlot("CRN1", "202690", days, t(start), t(end))

def async_meeting() -> MeetingSlot:
    return MeetingSlot("CRN1", "202690", None, None, None)

def section(crn: str, course: str, meetings: list[MeetingSlot]) -> SectionSlot:
    return SectionSlot(crn=crn, term="202690", course_code=course,
                       professor_name=None, total_seats=30, open_seats=10,
                       meetings=meetings)


# ── TestToMinuteIntervals ─────────────────────────────────────────────────────

class TestToMinuteIntervals:
    """Verify that meeting patterns expand to the correct MOW integer intervals."""

    def test_mwf_produces_three_intervals(self):
        result = to_minute_intervals("MWF", t("10:00"), t("10:50"))
        assert len(result) == 3
        assert (600, 650) in result                       # Monday 10:00–10:50
        assert (2880 + 600, 2880 + 650) in result         # Wednesday
        assert (5760 + 600, 5760 + 650) in result         # Friday

    def test_tr_produces_two_intervals(self):
        result = to_minute_intervals("TR", t("14:00"), t("15:15"))
        assert len(result) == 2
        assert (1440 + 840, 1440 + 915) in result         # Tuesday 14:00–15:15
        assert (4320 + 840, 4320 + 915) in result         # Thursday

    def test_single_day_monday(self):
        result = to_minute_intervals("M", t("09:00"), t("09:50"))
        assert result == [(540, 590)]

    def test_none_days_returns_empty(self):
        """Async sections have no days → no intervals → no conflicts."""
        assert to_minute_intervals(None, t("10:00"), t("11:00")) == []

    def test_none_start_returns_empty(self):
        assert to_minute_intervals("MWF", None, t("11:00")) == []

    def test_none_end_returns_empty(self):
        assert to_minute_intervals("MWF", t("10:00"), None) == []

    def test_empty_string_days_returns_empty(self):
        assert to_minute_intervals("", t("10:00"), t("11:00")) == []

    def test_unknown_day_char_ignored(self):
        """'X' is not a valid day — should be skipped, not crash."""
        result = to_minute_intervals("MX", t("10:00"), t("11:00"))
        assert len(result) == 1   # only Monday


# ── TestIntervalsOverlap ──────────────────────────────────────────────────────

class TestIntervalsOverlap:
    """Verify the half-open interval overlap predicate on integers."""

    def test_identical_intervals_overlap(self):
        assert intervals_overlap((600, 700), (600, 700)) is True

    def test_partial_overlap_a_starts_first(self):
        assert intervals_overlap((600, 700), (650, 750)) is True

    def test_partial_overlap_b_starts_first(self):
        assert intervals_overlap((650, 750), (600, 700)) is True

    def test_b_fully_inside_a(self):
        assert intervals_overlap((600, 900), (700, 800)) is True

    def test_a_fully_inside_b(self):
        assert intervals_overlap((700, 800), (600, 900)) is True

    def test_adjacent_back_to_back_no_overlap(self):
        """
        CS101 ends at 710, CS201 starts at 710.
        Back-to-back classes must NOT conflict.
        Predicate: 600 < 800 ✓  but  710 < 710 ✗  → False.
        """
        assert intervals_overlap((600, 710), (710, 800)) is False

    def test_one_minute_overlap_is_conflict(self):
        """Ends 711, starts 710 — one minute overlap."""
        assert intervals_overlap((600, 711), (710, 800)) is True

    def test_no_overlap_a_entirely_before_b(self):
        assert intervals_overlap((600, 700), (800, 900)) is False

    def test_no_overlap_b_entirely_before_a(self):
        assert intervals_overlap((800, 900), (600, 700)) is False

    def test_different_mow_days_same_clock_no_overlap(self):
        """
        Monday 10:00–10:50 (600,650) vs Wednesday 10:00–10:50 (3480,3530).
        Same clock time, different days → different MOW regions → no overlap.
        This is the key property of the minute-of-week model.
        """
        monday    = (600, 650)
        wednesday = (2880 + 600, 2880 + 650)
        assert intervals_overlap(monday, wednesday) is False


# ── TestSectionsConflict ──────────────────────────────────────────────────────

class TestSectionsConflict:
    """
    Verify conflict detection across full SectionSlots with multi-meeting patterns.
    These are the tests that would have caught the original data model bug.
    """

    def test_different_days_no_conflict(self):
        """MWF lecture vs TR lecture — no shared MOW region → no conflict."""
        mwf = section("A", "CS101", [meeting("MWF", "10:00", "10:50")])
        tr  = section("B", "CS201", [meeting("TR",  "10:00", "10:50")])
        assert not sections_conflict(mwf, tr)

    def test_same_day_same_time_conflicts(self):
        """Two sections scheduled identically must conflict."""
        a = section("A", "CS101", [meeting("MW", "10:00", "11:20")])
        b = section("B", "CS201", [meeting("MW", "10:00", "11:20")])
        assert sections_conflict(a, b)

    def test_back_to_back_no_conflict(self):
        """
        CS101 ends 11:20, CS201 starts 11:20 — valid back-to-back.
        MOW: (1440+600, 1440+710) vs (1440+710, 1440+800) → 710 < 710 is False → no conflict.
        """
        a = section("A", "CS101", [meeting("TR", "10:00", "11:20")])
        b = section("B", "CS201", [meeting("TR", "11:20", "12:50")])
        assert not sections_conflict(a, b)

    def test_one_minute_overlap_is_conflict(self):
        a = section("A", "CS101", [meeting("TR", "10:00", "11:21")])
        b = section("B", "CS201", [meeting("TR", "11:20", "12:50")])
        assert sections_conflict(a, b)

    def test_async_vs_timed_no_conflict(self):
        """Online section must never conflict with any in-person section."""
        async_s   = section("A", "CS101", [async_meeting()])
        in_person = section("B", "CS201", [meeting("MWF", "08:00", "22:00")])
        assert not sections_conflict(async_s, in_person)

    def test_async_vs_async_no_conflict(self):
        a = section("A", "CS101", [async_meeting()])
        b = section("B", "CS201", [async_meeting()])
        assert not sections_conflict(a, b)

    def test_math340_lab_conflict_THE_regression_test(self):
        """
        THE regression test for the original data model bug.

        Old flat model stored MATH340 as: days='TRF', start=10:00, end=11:20
        What Banner actually reported:
          meetingsFaculty[0]: TR  10:00–11:20  (lecture)
          meetingsFaculty[1]: F   14:00–16:50  (lab)

        A student adding HIST301 (F 14:00–15:15) should see a CONFLICT.

        Under the old model: checking TRF 10:00–11:20 vs F 14:00–15:15
          → Friday shared ✓, but 14:00 < 11:20 ✗ → no conflict reported. WRONG.

        Under the new model: MATH340 expands to three MOW intervals:
          Tuesday 10:00–11:20, Thursday 10:00–11:20, Friday 14:00–16:50.
        HIST301 expands to: Friday 14:00–15:15.
        Friday 14:00–16:50 vs Friday 14:00–15:15 → overlap. CORRECT.
        """
        math340 = section("12345", "MATH340", [
            meeting("TR", "10:00", "11:20"),   # lecture
            meeting("F",  "14:00", "16:50"),   # lab
        ])
        hist301 = section("67890", "HIST301", [
            meeting("F", "14:00", "15:15"),
        ])
        assert sections_conflict(math340, hist301), \
            "F lab at 14:00 must conflict with HIST301 at 14:00"

    def test_math340_with_unrelated_morning_course_no_conflict(self):
        """MATH340 (TR+F) vs a MW-only morning course — completely disjoint MOW regions."""
        math340 = section("12345", "MATH340", [
            meeting("TR", "10:00", "11:20"),
            meeting("F",  "14:00", "16:50"),
        ])
        cs101 = section("11111", "CS101", [
            meeting("MW", "09:00", "10:20"),
        ])
        assert not sections_conflict(math340, cs101)

    def test_three_pattern_section_catches_third_conflict(self):
        """
        A section with lecture + lab + recitation (3 patterns).
        Another course that only conflicts with the recitation must still be caught.
        """
        complex_section = section("X", "ECE291", [
            meeting("TR",  "10:00", "11:20"),   # lecture
            meeting("F",   "14:00", "16:50"),   # lab
            meeting("W",   "12:00", "12:50"),   # recitation
        ])
        conflicts_only_on_wednesday = section("Y", "CS201", [
            meeting("W", "12:00", "12:50"),
        ])
        assert sections_conflict(complex_section, conflicts_only_on_wednesday)


# ── TestPassesCommuterFilters ─────────────────────────────────────────────────

class TestPassesCommuterFilters:
    """
    Verify commuter constraints applied across ALL meetings of a section.
    The critical insight: a section fails if ANY single meeting violates a constraint.
    """

    def test_no_constraints_passes_everything(self):
        s = section("A", "CS280", [meeting("F", "08:00", "09:00")])
        assert passes_commuter_filters(s, CommuterOptions()) is True

    def test_blocked_friday_catches_friday_lab(self):
        """
        A commuter who blocks Friday must not receive MATH340 even though its
        TR lecture starts at 10am — the F lab trips the constraint.
        """
        math340 = section("12345", "MATH340", [
            meeting("TR", "10:00", "11:20"),
            meeting("F",  "14:00", "16:50"),
        ])
        assert not passes_commuter_filters(math340, CommuterOptions(blocked_days=["F"]))

    def test_blocked_day_in_mwf_string_caught(self):
        """MWF contains F — blocking F must exclude an MWF section."""
        s = section("A", "CS280", [meeting("MWF", "10:00", "10:50")])
        assert not passes_commuter_filters(s, CommuterOptions(blocked_days=["F"]))

    def test_earliest_start_applies_to_all_meetings(self):
        """
        Commuter says 'not before 10:00'. MATH340 TR lecture starts at 10:00 (ok),
        but the F lab starts at 08:00 (violation). Section must be excluded.
        """
        math340 = section("12345", "MATH340", [
            MeetingSlot("12345", "202690", "TR", t("10:00"), t("11:20")),
            MeetingSlot("12345", "202690", "F",  t("08:00"), t("10:50")),
        ])
        opts = CommuterOptions(earliest_start="10:00")
        assert not passes_commuter_filters(math340, opts)

    def test_latest_end_applies_to_all_meetings(self):
        """
        Commuter says 'not after 17:00'. Lecture ends at 11:20 (ok),
        lab ends at 16:50 (ok). Both fine → section passes.
        """
        math340 = section("12345", "MATH340", [
            meeting("TR", "10:00", "11:20"),
            meeting("F",  "14:00", "16:50"),
        ])
        opts = CommuterOptions(latest_end="17:00")
        assert passes_commuter_filters(math340, opts)

    def test_latest_end_violation_on_second_meeting(self):
        """Lab ends at 18:00, commuter cutoff is 17:00 → excluded."""
        s = section("A", "CS291", [
            meeting("TR", "10:00", "11:20"),
            meeting("F",  "15:00", "18:00"),
        ])
        opts = CommuterOptions(latest_end="17:00")
        assert not passes_commuter_filters(s, opts)

    def test_async_passes_all_time_constraints(self):
        """Async/online section has no times → always passes time-bound constraints."""
        s = section("A", "CS101", [async_meeting()])
        opts = CommuterOptions(
            blocked_days=["M", "T", "W", "R", "F"],
            earliest_start="12:00",
            latest_end="12:30",
        )
        assert passes_commuter_filters(s, opts)


# ── TestValidateSchedule ──────────────────────────────────────────────────────

class TestValidateSchedule:
    """The post-solve safety net — must catch any conflict that slips through."""

    def test_valid_schedule_returns_no_violations(self):
        mwf = section("A", "CS101", [meeting("MWF", "10:00", "10:50")])
        tr  = section("B", "CS201", [meeting("TR",  "10:00", "11:20")])
        assert validate_schedule([mwf, tr]) == []

    def test_conflicting_schedule_returns_violation_string(self):
        a = section("A", "CS101", [meeting("MW", "10:00", "11:20")])
        b = section("B", "CS201", [meeting("MW", "10:00", "11:20")])
        violations = validate_schedule([a, b])
        assert len(violations) == 1
        assert "CS101" in violations[0]
        assert "CS201" in violations[0]

    def test_math340_hist301_generates_violation(self):
        """The exact scenario from the bug report must produce a violation."""
        math340 = section("12345", "MATH340", [
            meeting("TR", "10:00", "11:20"),
            meeting("F",  "14:00", "16:50"),
        ])
        hist301 = section("67890", "HIST301", [
            meeting("F", "14:00", "15:15"),
        ])
        violations = validate_schedule([math340, hist301])
        assert violations, "MATH340 F lab must conflict with HIST301"
