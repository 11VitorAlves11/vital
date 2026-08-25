from sqlalchemy import Numeric
from sqlalchemy.orm import DeclarativeBase

# Every clinical value (results, reference ranges, scan readings) shares this numeric
# column type — comparisons against band limits have to be exact, so no floats anywhere.
VALUE = Numeric(12, 4)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
