"""Shared booking utilities (e.g. date range to datetime range for filters)."""
from datetime import datetime, time
from typing import Optional, Tuple

from django.utils import timezone as tz


def date_range_to_datetime_range(
    date_from: Optional[object],
    date_to: Optional[object],
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Convert date_from and date_to to timezone-aware start-of-day and end-of-day datetimes
    in the project timezone (e.g. Asia/Kathmandu).
    - date_from -> that day at 00:00:01
    - date_to -> that day at 23:59:59
    Returns (start_dt, end_dt); either may be None if the corresponding date is None.
    """
    if date_from is None and date_to is None:
        return None, None
    tz_info = tz.get_current_timezone()
    start_dt = None
    end_dt = None
    if date_from is not None:
        d = date_from.date() if hasattr(date_from, 'date') else date_from
        start_dt = tz.make_aware(datetime.combine(d, time(0, 0, 1)), tz_info)
    if date_to is not None:
        d = date_to.date() if hasattr(date_to, 'date') else date_to
        end_dt = tz.make_aware(datetime.combine(d, time(23, 59, 59)), tz_info)
    return start_dt, end_dt
