"""Total experience calculation (project.md §7, architecture.md §7.4). Pure and unit-tested."""

import re
from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any

_YM = re.compile(r"^\s*(\d{4})-(\d{1,2})\s*$")
_Y = re.compile(r"^\s*(\d{4})\s*$")


def _get(exp: Any, key: str) -> Any:
    if isinstance(exp, Mapping):
        return exp.get(key)
    return getattr(exp, key, None)


def _parse(value: str | None, *, is_end: bool, today: date) -> tuple[int, int] | None:
    if not value or not isinstance(value, str):
        return None
    m = _YM.match(value)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return year, month
        return None
    m = _Y.match(value)
    if m:
        year = int(m.group(1))
        if not is_end:
            return year, 1
        if year == today.year:
            return year, today.month
        return year, 12
    return None


def compute_experience(experiences: Iterable[Any], today: date) -> tuple[int, list[str]]:
    """Return (total_months, warnings). Overlapping intervals are merged; months are inclusive."""
    intervals: list[tuple[int, int]] = []
    warnings: list[str] = []
    today_idx = today.year * 12 + today.month

    for exp in experiences or []:
        company = _get(exp, "company") or "unknown company"
        is_current = bool(_get(exp, "is_current"))

        start = _parse(_get(exp, "start_date"), is_end=False, today=today)
        if start is None:
            warnings.append(f"Skipped experience at {company}: missing or unreadable start date")
            continue

        if is_current:
            end = (today.year, today.month)
        else:
            end = _parse(_get(exp, "end_date"), is_end=True, today=today)
            if end is None:
                warnings.append(f"Skipped experience at {company}: missing end date")
                continue

        start_idx = start[0] * 12 + start[1]
        end_idx = min(end[0] * 12 + end[1], today_idx)
        if end_idx < start_idx:
            warnings.append(f"Skipped experience at {company}: end date is before start date")
            continue
        intervals.append((start_idx, end_idx))

    if not intervals:
        return 0, warnings

    intervals.sort()
    merged: list[list[int]] = [list(intervals[0])]
    for s, e in intervals[1:]:
        current = merged[-1]
        if s <= current[1]:
            current[1] = max(current[1], e)
        else:
            merged.append([s, e])

    total = sum(e - s + 1 for s, e in merged)
    return total, warnings
