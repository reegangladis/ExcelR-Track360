"""
ExcelR Track360 - Business Calendar & Working Days Utility
Computes working business days excluding weekends (Saturdays & Sundays)
and optional organizational/national holiday calendar.
Governed by BRD Part 7 (15-business-day project allocation target).
"""
from datetime import date, datetime, timedelta
from typing import List, Optional, Set, Union


def calculate_business_days(
    start: Union[date, datetime],
    end: Optional[Union[date, datetime]] = None,
    holidays: Optional[List[date]] = None,
) -> int:
    """
    Calculates working business days elapsed between start and end date.
    - If end is not specified, defaults to current date.
    - Excludes Saturdays (weekday 5) and Sundays (weekday 6).
    - Excludes dates present in the holidays list.
    """
    if isinstance(start, datetime):
        start_date = start.date()
    else:
        start_date = start

    if end is None:
        end_date = date.today()
    elif isinstance(end, datetime):
        end_date = end.date()
    else:
        end_date = end

    if start_date >= end_date:
        return 0

    holiday_set: Set[date] = set(holidays or [])
    business_days = 0
    current = start_date

    while current < end_date:
        current += timedelta(days=1)
        # Weekday: 0 = Monday, ..., 4 = Friday, 5 = Saturday, 6 = Sunday
        if current.weekday() < 5 and current not in holiday_set:
            business_days += 1

    return business_days


def is_allocation_overdue(
    completion_timestamp: Optional[datetime],
    sla_business_days: int = 15,
    holidays: Optional[List[date]] = None,
) -> bool:
    """Returns True if days in queue exceed the 15-business-day allocation SLA."""
    if not completion_timestamp:
        return False
    elapsed = calculate_business_days(completion_timestamp, holidays=holidays)
    return elapsed > sla_business_days
