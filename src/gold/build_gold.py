"""Gold layer: apply the SLA business rules and build the final table."""

import logging

import pandas as pd

from src.config import (
    GOLD_DIR,
    GOLD_SLA_BY_ANALYST_FILE,
    GOLD_SLA_BY_ISSUE_TYPE_FILE,
    GOLD_SLA_ISSUES_FILE,
    SILVER_ISSUES_FILE,
)
from src.holidays_api import fetch_national_holidays
from src.silver.transform_silver import CLOSED_STATUSES, DATE_FORMAT
from src.sla_calculation import calculate_resolution_hours, check_sla_compliance, get_sla_expected_hours

logger = logging.getLogger(__name__)

GOLD_SLA_COLUMNS = [
    "issue_id",
    "issue_type",
    "assignee_name",
    "priority",
    "created_at",
    "resolved_at",
    "resolution_hours",
    "sla_expected_hours",
    "is_sla_met",
]


def read_silver_issues(silver_file=SILVER_ISSUES_FILE):
    """Read the Silver Parquet file."""
    return pd.read_parquet(silver_file)


def filter_closed_issues(issues):
    """Keep only Done and Resolved issues (Open issues have no resolution date)."""
    return issues[issues["status"].isin(CLOSED_STATUSES)].reset_index(drop=True)


def get_holiday_years(issues):
    """Return every year covered by the issues, from the first creation to the last resolution."""
    return list(range(issues["created_at"].min().year, issues["resolved_at"].max().year + 1))


def build_sla_table(closed_issues, holidays):
    """Add resolution hours, expected SLA and compliance flag to each closed issue."""
    sla_issues = closed_issues.copy()
    sla_issues["resolution_hours"] = sla_issues.apply(
        lambda issue: calculate_resolution_hours(issue["created_at"], issue["resolved_at"], holidays),
        axis=1,
    )
    sla_issues["sla_expected_hours"] = sla_issues["priority"].apply(get_sla_expected_hours)
    sla_issues["is_sla_met"] = sla_issues.apply(
        lambda issue: check_sla_compliance(issue["resolution_hours"], issue["sla_expected_hours"]),
        axis=1,
    )
    return sla_issues[GOLD_SLA_COLUMNS]


def build_sla_report(sla_issues, group_column):
    """Aggregate issue count and average resolution hours (average SLA) by a column."""
    report = (
        sla_issues.groupby(group_column)
        .agg(issue_count=("issue_id", "count"), avg_resolution_hours=("resolution_hours", "mean"))
        .reset_index()
    )
    report["avg_resolution_hours"] = report["avg_resolution_hours"].round(2)
    return report


def build_gold():
    """Build the Gold layer from the Silver file and persist it locally."""
    closed_issues = filter_closed_issues(read_silver_issues())
    holidays = fetch_national_holidays(get_holiday_years(closed_issues))
    sla_issues = build_sla_table(closed_issues, holidays)

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    sla_issues.to_csv(GOLD_SLA_ISSUES_FILE, index=False, date_format=DATE_FORMAT)
    logger.info(
        "Gold written: %s (issues=%d, sla_met=%d, sla_violated=%d)",
        GOLD_SLA_ISSUES_FILE,
        len(sla_issues),
        sla_issues["is_sla_met"].sum(),
        (~sla_issues["is_sla_met"]).sum(),
    )

    reports = {
        GOLD_SLA_BY_ANALYST_FILE: build_sla_report(sla_issues, "assignee_name"),
        GOLD_SLA_BY_ISSUE_TYPE_FILE: build_sla_report(sla_issues, "issue_type"),
    }
    for report_file, report in reports.items():
        report.to_csv(report_file, index=False)
        logger.info("Report written: %s (rows=%d)", report_file, len(report))

    return GOLD_SLA_ISSUES_FILE
