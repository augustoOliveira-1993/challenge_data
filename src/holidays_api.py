"""Brazilian national holidays from BrasilAPI (https://brasilapi.com.br)."""

import logging
from datetime import date

import requests

logger = logging.getLogger(__name__)

HOLIDAYS_API_URL = "https://brasilapi.com.br/api/feriados/v1/{year}"
REQUEST_TIMEOUT_SECONDS = 10


def fetch_holidays_by_year(year):
    """Return the national holidays of one year as a set of dates."""
    response = requests.get(HOLIDAYS_API_URL.format(year=year), timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return {date.fromisoformat(holiday["date"]) for holiday in response.json()}


def fetch_national_holidays(years):
    """Return the national holidays of all given years as a single set of dates."""
    holidays = set()
    for year in years:
        year_holidays = fetch_holidays_by_year(year)
        logger.info("Holidays fetched for %d: %d dates", year, len(year_holidays))
        holidays.update(year_holidays)
    return holidays
