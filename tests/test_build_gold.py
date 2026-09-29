from datetime import date

import pandas as pd

from src.gold.build_gold import (
    GOLD_SLA_COLUMNS,
    build_sla_report,
    build_sla_table,
    filter_closed_issues,
    get_holiday_years,
)


def build_silver_issues():
    return pd.DataFrame(
        {
            "issue_id": ["JIRA-0001", "JIRA-0002", "JIRA-0003", "JIRA-0004"],
            "issue_type": ["Bug", "Task", "Story", "Bug"],
            "status": ["Done", "Resolved", "Open", "Done"],
            "priority": ["High", "Medium", "Low", "High"],
            "assignee_name": ["Analyst One", "Analyst Two", "Analyst One", "Analyst Two"],
            "created_at": pd.to_datetime(
                [
                    "2025-12-24T12:00:00Z",  # Wednesday, crosses Christmas
                    "2025-03-07T20:00:00Z",  # Friday, crosses weekend
                    "2025-03-10T09:00:00Z",
                    "2025-12-31T23:00:00Z",  # crosses year boundary
                ],
                utc=True,
            ),
            "resolved_at": pd.to_datetime(
                ["2025-12-26T12:00:00Z", "2025-03-10T04:00:00Z", None, "2026-01-02T01:00:00Z"],
                utc=True,
            ),
        }
    )


def test_filter_closed_issues_drops_open():
    closed_issues = filter_closed_issues(build_silver_issues())

    assert list(closed_issues["issue_id"]) == ["JIRA-0001", "JIRA-0002", "JIRA-0004"]


def test_get_holiday_years_covers_creation_and_resolution():
    closed_issues = filter_closed_issues(build_silver_issues())

    assert get_holiday_years(closed_issues) == [2025, 2026]


def test_build_sla_table_applies_sla_rules():
    holidays = {date(2025, 12, 25), date(2026, 1, 1)}
    closed_issues = filter_closed_issues(build_silver_issues())

    sla_issues = build_sla_table(closed_issues, holidays).set_index("issue_id")

    assert list(sla_issues.reset_index().columns) == GOLD_SLA_COLUMNS
    # Wed 12:00 -> Fri 12:00 minus Christmas = 24h, High SLA 24h -> met
    assert sla_issues.loc["JIRA-0001", "resolution_hours"] == 24
    assert sla_issues.loc["JIRA-0001", "is_sla_met"]
    # Fri 20:00 -> Mon 04:00 = 8h, Medium SLA 72h -> met
    assert sla_issues.loc["JIRA-0002", "resolution_hours"] == 8
    assert sla_issues.loc["JIRA-0002", "sla_expected_hours"] == 72
    # Wed 23:00 -> Fri 01:00 minus New Year = 1h + 1h
    assert sla_issues.loc["JIRA-0004", "resolution_hours"] == 2


def test_build_sla_report_aggregates_count_and_average():
    sla_issues = pd.DataFrame(
        {
            "issue_id": ["JIRA-0001", "JIRA-0002", "JIRA-0003"],
            "assignee_name": ["Analyst One", "Analyst One", "Analyst Two"],
            "resolution_hours": [10.0, 15.5, 30.0],
        }
    )

    report = build_sla_report(sla_issues, "assignee_name")

    assert list(report.columns) == ["assignee_name", "issue_count", "avg_resolution_hours"]
    assert report.to_dict("records") == [
        {"assignee_name": "Analyst One", "issue_count": 2, "avg_resolution_hours": 12.75},
        {"assignee_name": "Analyst Two", "issue_count": 1, "avg_resolution_hours": 30.0},
    ]
