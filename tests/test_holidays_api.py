from datetime import date

import pytest
import requests

from src import holidays_api


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


FAKE_API_DATA = {
    "https://brasilapi.com.br/api/feriados/v1/2025": [
        {"date": "2025-01-01", "name": "Confraternização mundial", "type": "national"},
        {"date": "2025-12-25", "name": "Natal", "type": "national"},
    ],
    "https://brasilapi.com.br/api/feriados/v1/2026": [
        {"date": "2026-01-01", "name": "Confraternização mundial", "type": "national"},
    ],
}


def fake_get(url, timeout):
    if url not in FAKE_API_DATA:
        return FakeResponse([], status_code=404)
    return FakeResponse(FAKE_API_DATA[url])


def test_fetch_national_holidays_merges_years(monkeypatch):
    monkeypatch.setattr(holidays_api.requests, "get", fake_get)

    holidays = holidays_api.fetch_national_holidays([2025, 2026])

    assert holidays == {date(2025, 1, 1), date(2025, 12, 25), date(2026, 1, 1)}


def test_fetch_holidays_by_year_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(holidays_api.requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        holidays_api.fetch_holidays_by_year(1999)
