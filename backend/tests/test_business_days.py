"""Business-day arithmetic: weekends and US federal holidays (observed dates) are skipped."""

from datetime import date

import pytest

from app.opt.business_days import add_business_days, is_business_day, subtract_business_days, us_federal_holidays


def test_2027_federal_holidays_with_observed_dates():
    assert us_federal_holidays(2027) == {
        date(2027, 1, 1),  # New Year's Day (Friday)
        date(2027, 1, 18),  # MLK Day, 3rd Monday of January
        date(2027, 2, 15),  # Washington's Birthday, 3rd Monday of February
        date(2027, 5, 31),  # Memorial Day, last Monday of May
        date(2027, 6, 18),  # Juneteenth (Saturday) -> observed Friday
        date(2027, 7, 5),  # Independence Day (Sunday) -> observed Monday
        date(2027, 9, 6),  # Labor Day
        date(2027, 10, 11),  # Columbus Day
        date(2027, 11, 11),  # Veterans Day
        date(2027, 11, 25),  # Thanksgiving, 4th Thursday of November
        date(2027, 12, 24),  # Christmas (Saturday) -> observed Friday
    }


@pytest.mark.parametrize(
    "day,expected",
    [
        (date(2027, 3, 10), True),  # Wednesday
        (date(2027, 3, 13), False),  # Saturday
        (date(2027, 3, 14), False),  # Sunday
        (date(2027, 7, 5), False),  # observed Independence Day
    ],
)
def test_is_business_day(day, expected):
    assert is_business_day(day) is expected


def test_new_years_day_on_saturday_is_observed_the_friday_before():
    assert date(2021, 12, 31) in us_federal_holidays(2022)  # Jan 1 2022 was a Saturday
    assert is_business_day(date(2021, 12, 31)) is False


def test_add_skips_weekend():
    assert add_business_days(date(2027, 3, 12), 1) == date(2027, 3, 15)  # Fri + 1 -> Mon


def test_add_skips_holiday():
    assert add_business_days(date(2027, 7, 2), 1) == date(2027, 7, 6)  # Fri + 1 skips Mon 7/5


def test_subtract_skips_weekend_and_holiday():
    assert subtract_business_days(date(2027, 3, 30), 14) == date(2027, 3, 10)
    assert subtract_business_days(date(2027, 7, 6), 1) == date(2027, 7, 2)


def test_zero_days_is_same_day():
    assert add_business_days(date(2027, 3, 13), 0) == date(2027, 3, 13)
    assert subtract_business_days(date(2027, 3, 13), 0) == date(2027, 3, 13)


def test_thirty_business_days_is_about_six_weeks():
    assert add_business_days(date(2027, 3, 1), 30) == date(2027, 4, 12)
