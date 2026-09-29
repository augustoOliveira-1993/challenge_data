"""End-to-end check of the transformations on the real dataset (no network, no files written)."""

from datetime import date

import pytest

from src.config import LOCAL_SOURCE_FILE
from src.gold.build_gold import GOLD_SLA_COLUMNS, build_sla_report, build_sla_table, filter_closed_issues
from src.silver.transform_silver import flatten_issues, read_bronze_issues, split_invalid_records

# Fixed BrasilAPI national holidays for 2025-2026, so the test does not depend on the network.
HOLIDAYS_2025_2026 = {
    date.fromisoformat(day)
    for day in [
        "2025-01-01", "2025-03-03", "2025-03-04", "2025-04-18", "2025-04-20", "2025-04-21", "2025-05-01",
        "2025-06-19", "2025-09-07", "2025-10-12", "2025-11-02", "2025-11-15", "2025-11-20", "2025-12-25",
        "2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03", "2026-04-05", "2026-04-21", "2026-05-01",
        "2026-06-04", "2026-09-07", "2026-10-12", "2026-11-02", "2026-11-15", "2026-11-20", "2026-12-25",
    ]
}


@pytest.fixture(scope="module")
def pipeline_layers():
    raw_issues = flatten_issues(read_bronze_issues(LOCAL_SOURCE_FILE))
    silver_issues, rejected_issues = split_invalid_records(raw_issues)
    gold_issues = build_sla_table(filter_closed_issues(silver_issues), HOLIDAYS_2025_2026)
    return raw_issues, silver_issues, rejected_issues, gold_issues


def test_layer_counts(pipeline_layers):
    raw_issues, silver_issues, rejected_issues, gold_issues = pipeline_layers

    assert len(raw_issues) == 1000
    assert len(silver_issues) == 990
    assert len(rejected_issues) == 10
    assert len(gold_issues) == 804


def test_silver_keeps_open_issues(pipeline_layers):
    _, silver_issues, _, _ = pipeline_layers

    assert (silver_issues["status"] == "Open").sum() == 186


def test_gold_contains_only_closed_issues_without_nulls(pipeline_layers):
    _, silver_issues, _, gold_issues = pipeline_layers
    status_by_issue = silver_issues.set_index("issue_id")["status"]

    assert list(gold_issues.columns) == GOLD_SLA_COLUMNS
    assert set(status_by_issue[gold_issues["issue_id"]]) == {"Done", "Resolved"}
    assert gold_issues.notna().all().all()
    assert (gold_issues["resolution_hours"] >= 0).all()


def test_reports_cover_all_gold_issues(pipeline_layers):
    _, _, _, gold_issues = pipeline_layers

    assert build_sla_report(gold_issues, "assignee_name")["issue_count"].sum() == 804
    assert build_sla_report(gold_issues, "issue_type")["issue_count"].sum() == 804
