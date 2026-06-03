from __future__ import annotations
from datetime import time

from hypothesis import given, assume, strategies as st

from src.scheduler.time_utils import intervals_overlap, to_minute_intervals


class TestIntervalsOverlapProperty:

    @given(
        start_a=st.integers(min_value=0, max_value=9000),
        dur_a=st.integers(min_value=1, max_value=300),
        start_b=st.integers(min_value=0, max_value=9000),
        dur_b=st.integers(min_value=1, max_value=300),
    )
    def test_overlap_is_symmetric(self, start_a, dur_a, start_b, dur_b):
        """If A overlaps B, B must overlap A."""
        a = (start_a, start_a + dur_a)
        b = (start_b, start_b + dur_b)
        assert intervals_overlap(a, b) == intervals_overlap(b, a)

    @given(
        st.integers(min_value=0, max_value=9000),
        st.integers(min_value=1, max_value=300),
    )
    def test_interval_overlaps_itself(self, start, dur):
        """Any interval overlaps itself (same section listed twice would conflict)."""
        i = (start, start + dur)
        assert intervals_overlap(i, i) is True

    @given(
        days1=st.text(alphabet="MTWRF", min_size=1, max_size=5),
        days2=st.text(alphabet="MTWRF", min_size=1, max_size=5),
    )
    def test_disjoint_days_never_conflict(self, days1, days2):
        """
        If day sets are completely disjoint, the MOW intervals will be in
        separate week-regions and can never overlap regardless of clock time.
        """
        assume(not (set(days1) & set(days2)))
        i1 = to_minute_intervals(days1, time(10, 0), time(11, 0))
        i2 = to_minute_intervals(days2, time(10, 0), time(11, 0))
        assert not any(intervals_overlap(a, b) for a in i1 for b in i2)
