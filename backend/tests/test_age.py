"""Age at a date, without a database or a stored age column anywhere."""

from datetime import date

import pytest

from app.services.age import age_at


@pytest.mark.parametrize(
    ("birth_date", "on", "expected"),
    [
        (date(1994, 4, 2), date(2026, 9, 1), 32),  # birthday not yet reached this year
        (date(1994, 4, 2), date(2026, 4, 2), 32),  # birthday itself
        (date(1994, 4, 2), date(2026, 4, 3), 32),
        (date(1994, 4, 2), date(2027, 4, 1), 32),  # day before the next birthday
        (date(2000, 2, 29), date(2026, 2, 28), 25),  # leap-day birth, non-leap year
        (date(2000, 2, 29), date(2026, 3, 1), 26),
    ],
)
def test_whole_years_elapsed(birth_date: date, on: date, expected: int) -> None:
    assert age_at(birth_date, on) == expected


def test_age_reads_against_the_date_of_the_measurement_not_today() -> None:
    """A weigh-in from 2019 is read against the age its owner was in 2019."""
    birth_date = date(1994, 4, 2)
    assert age_at(birth_date, date(2019, 1, 1)) == 24
    assert age_at(birth_date, date(2026, 9, 1)) == 32
