"""SLA business rules.

Business time is counted as 24 hours per business day (UTC dates).
Saturdays, Sundays and the given holidays do not count.
These functions are pure: holidays are received as a set of dates.
"""

from datetime import datetime, time, timedelta


def get_sla_expected_hours(priority):
    """Return the expected SLA in hours for a priority."""
    if priority == "High":
        return 24
    elif priority == "Medium":
        return 72
    elif priority == "Low":
        return 120
    else:
        raise ValueError(f"Unknown priority: {priority}")


def is_business_day(day, holidays):
    """Return True when the date is a weekday (Mon-Fri) and not a holiday."""
    return day.weekday() < 5 and day not in holidays


def calculate_resolution_hours(created_at, resolved_at, holidays):
    """Return the business hours between two UTC datetimes, rounded to 2 decimals.

    Each calendar day in the interval is checked: when it is a business day,
    the part of the interval that falls inside that day is added.
    """
    if resolved_at < created_at:
        raise ValueError("resolved_at must not be earlier than created_at")

    total_seconds = 0.0
    day_count = (resolved_at.date() - created_at.date()).days + 1

    for day_offset in range(day_count):
        day = created_at.date() + timedelta(days=day_offset)
        if not is_business_day(day, holidays):
            continue

        day_start = datetime.combine(day, time.min, tzinfo=created_at.tzinfo)
        day_end = day_start + timedelta(days=1)
        period_start = max(created_at, day_start)
        period_end = min(resolved_at, day_end)
        total_seconds += (period_end - period_start).total_seconds()

    return round(total_seconds / 3600, 2)


def check_sla_compliance(resolution_hours, sla_expected_hours):
    """Return True when the issue was resolved within the expected SLA."""
    return resolution_hours <= sla_expected_hours
