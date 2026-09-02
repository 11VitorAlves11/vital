"""Age at a given date, derived from a birth date and never stored.

The only date that matters for an age-partitioned reference is the one on the
measurement, not today's: a weigh-in from 2019 reads against the age its owner
was in 2019, whatever age they have turned since.
"""

from datetime import date


def age_at(birth_date: date, on: date) -> int:
    """Whole years elapsed — the ordinary meaning of an age, off by one from a
    naive year subtraction until the birthday has happened yet that year."""
    had_birthday_yet = (on.month, on.day) >= (birth_date.month, birth_date.day)
    return on.year - birth_date.year - (0 if had_birthday_yet else 1)
