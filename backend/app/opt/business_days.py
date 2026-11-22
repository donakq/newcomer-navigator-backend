"""Business-day arithmetic for school and premium-processing times.

A business day is Monday-Friday and not a US federal holiday (5 U.S.C. 6103, with the federal
observed-date rule: a Saturday holiday is observed Friday, a Sunday holiday Monday).
"""

from datetime import date, timedelta
from functools import lru_cache


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The n-th given weekday (Mon = 0) of a month; n = -1 means the last one."""
    if n > 0:
        first = date(year, month, 1)
        return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    last = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(day: date) -> date:
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


@lru_cache
def us_federal_holidays(year: int) -> frozenset[date]:
    """Observed dates of the year's 11 federal holidays (New Year's may be observed on Dec 31 of the year before)."""
    fixed = [date(year, 1, 1), date(year, 6, 19), date(year, 7, 4), date(year, 11, 11), date(year, 12, 25)]
    floating = [
        _nth_weekday(year, 1, 0, 3),  # Martin Luther King Jr. Day
        _nth_weekday(year, 2, 0, 3),  # Washington's Birthday
        _nth_weekday(year, 5, 0, -1),  # Memorial Day
        _nth_weekday(year, 9, 0, 1),  # Labor Day
        _nth_weekday(year, 10, 0, 2),  # Columbus Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving Day
    ]
    return frozenset([_observed(d) for d in fixed] + floating)


def is_business_day(day: date) -> bool:
    if day.weekday() >= 5:
        return False
    # Dec 31 can be the observed New Year's Day of the following year.
    return day not in us_federal_holidays(day.year) and day not in us_federal_holidays(day.year + 1)


def _step(day: date, n: int, direction: int) -> date:
    while n > 0:
        day += timedelta(days=direction)
        if is_business_day(day):
            n -= 1
    return day


def add_business_days(day: date, n: int) -> date:
    return _step(day, n, 1)


def subtract_business_days(day: date, n: int) -> date:
    return _step(day, n, -1)
