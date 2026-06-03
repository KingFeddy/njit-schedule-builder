from __future__ import annotations
from datetime import time

# Minute-of-week offsets: each day starts this many minutes after Monday 00:00.
# Monday 10:00 = 600. Wednesday 10:00 = 3480. Day separation falls out of the math.
DAY_OFFSETS: dict[str, int] = {
    'M': 0,
    'T': 1440,
    'W': 2880,
    'R': 4320,
    'F': 5760,
    'S': 7200,
    'U': 8640,
}


def to_minute_intervals(
    days: str | None,
    start: time | None,
    end: time | None,
) -> list[tuple[int, int]]:
    """
    Expand one meeting pattern into (start_mow, end_mow) integer intervals,
    one per day the meeting occurs. Returns [] for async sections.
    """
    if not days or start is None or end is None:
        return []
    start_min = start.hour * 60 + start.minute
    end_min   = end.hour * 60 + end.minute
    return [
        (DAY_OFFSETS[d] + start_min, DAY_OFFSETS[d] + end_min)
        for d in days
        if d in DAY_OFFSETS
    ]


def intervals_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """
    True iff two MOW intervals overlap. Back-to-back (a[1] == b[0]) does NOT conflict.

    Predicate: a[0] < b[1] AND b[0] < a[1]
    """
    return a[0] < b[1] and b[0] < a[1]


def parse_hhmm(s: str) -> time:
    """Parse 'HH:MM' string to datetime.time. Used by commuter filters."""
    h, m = s.split(':')
    return time(int(h), int(m))
