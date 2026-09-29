from datetime import date, datetime, timezone

import pandas as pd
import pytest

from src.sla_calculation import (
    calculate_resolution_hours,
    check_sla_compliance,
    get_sla_expected_hours,
    is_business_day,
)

NO_HOLIDAYS = set()
CHRISTMAS = {date(2025, 12, 25)}


def utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


@pytest.mark.parametrize("priority, expected_hours", [("High", 24), ("Medium", 72), ("Low", 120)])
def test_get_sla_expected_hours(priority, expected_hours):
    assert get_sla_expected_hours(priority) == expected_hours


def test_get_sla_expected_hours_rejects_unknown_priority():
    with pytest.raises(ValueError):
        get_sla_expected_hours("Urgent")


def test_is_business_day():
    assert is_business_day(date(2025, 3, 7), NO_HOLIDAYS)  # Friday
    assert not is_business_day(date(2025, 3, 8), NO_HOLIDAYS)  # Saturday
    assert not is_business_day(date(2025, 3, 9), NO_HOLIDAYS)  # Sunday
    assert not is_business_day(date(2025, 12, 25), CHRISTMAS)  # Thursday holiday


def test_same_business_day():
    # Monday 09:00 -> Monday 17:30
    assert calculate_resolution_hours(utc(2025, 3, 10, 9), utc(2025, 3, 10, 17, 30), NO_HOLIDAYS) == 8.5


def test_consecutive_business_days():
    # Monday 20:00 -> Tuesday 04:00
    assert calculate_resolution_hours(utc(2025, 3, 10, 20), utc(2025, 3, 11, 4), NO_HOLIDAYS) == 8


def test_interval_crossing_weekend():
    # Friday 20:00 -> Monday 04:00: only Friday 4h + Monday 4h count
    assert calculate_resolution_hours(utc(2025, 3, 7, 20), utc(2025, 3, 10, 4), NO_HOLIDAYS) == 8


def test_created_on_saturday_starts_counting_on_monday():
    # Saturday 10:00 -> Monday 06:00
    assert calculate_resolution_hours(utc(2025, 3, 8, 10), utc(2025, 3, 10, 6), NO_HOLIDAYS) == 6


def test_resolved_on_sunday_stops_counting_on_friday_midnight():
    # Friday 18:00 -> Sunday 12:00
    assert calculate_resolution_hours(utc(2025, 3, 7, 18), utc(2025, 3, 9, 12), NO_HOLIDAYS) == 6


def test_interval_inside_weekend_is_zero():
    assert calculate_resolution_hours(utc(2025, 3, 8, 1), utc(2025, 3, 9, 23), NO_HOLIDAYS) == 0


def test_interval_crossing_holiday():
    # Wednesday 12:00 -> Friday 12:00 with Thursday 2025-12-25 as holiday
    created_at, resolved_at = utc(2025, 12, 24, 12), utc(2025, 12, 26, 12)
    assert calculate_resolution_hours(created_at, resolved_at, NO_HOLIDAYS) == 48
    assert calculate_resolution_hours(created_at, resolved_at, CHRISTMAS) == 24


def test_equal_timestamps_is_zero():
    assert calculate_resolution_hours(utc(2025, 3, 10, 9), utc(2025, 3, 10, 9), NO_HOLIDAYS) == 0


def test_resolved_before_created_raises():
    with pytest.raises(ValueError):
        calculate_resolution_hours(utc(2025, 3, 10, 9), utc(2025, 3, 10, 8), NO_HOLIDAYS)


def test_accepts_pandas_utc_timestamps():
    created_at = pd.Timestamp("2025-03-07T20:00:00Z")
    resolved_at = pd.Timestamp("2025-03-10T04:00:00Z")
    assert calculate_resolution_hours(created_at, resolved_at, NO_HOLIDAYS) == 8


@pytest.mark.parametrize(
    "resolution_hours, sla_expected_hours, expected",
    [(23.99, 24, True), (24, 24, True), (24.01, 24, False)],
)
def test_check_sla_compliance(resolution_hours, sla_expected_hours, expected):
    assert check_sla_compliance(resolution_hours, sla_expected_hours) is expected
