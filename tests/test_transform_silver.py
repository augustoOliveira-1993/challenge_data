import pandas as pd

from src.silver.transform_silver import SILVER_COLUMNS, flatten_issues, split_invalid_records


def build_issue(issue_id, status, created_at, resolved_at, priority="High"):
    return {
        "id": issue_id,
        "issue_type": "Bug",
        "status": status,
        "priority": priority,
        "assignee": [{"id": "u001", "name": "Analyst One", "email": "analyst.one@example.com"}],
        "timestamps": [{"created_at": created_at, "resolved_at": resolved_at}],
    }


def build_raw_data(issues):
    return {
        "project": {"project_id": "DT-ENG", "project_name": "Test", "extracted_at": "2026-01-22T13:55:26Z"},
        "issues": issues,
    }


def test_flatten_issues_extracts_nested_fields_with_snake_case_columns():
    raw_data = build_raw_data([build_issue("JIRA-0001", "Done", "2025-03-10T09:00:00Z", "2025-03-10T12:00:00Z")])

    flat_issues = flatten_issues(raw_data)

    assert list(flat_issues.columns) == SILVER_COLUMNS
    assert len(flat_issues) == 1
    row = flat_issues.iloc[0]
    assert row["issue_id"] == "JIRA-0001"
    assert row["assignee_id"] == "u001"
    assert row["assignee_name"] == "Analyst One"
    assert row["created_at"] == "2025-03-10T09:00:00Z"
    assert row["project_id"] == "DT-ENG"


def test_split_invalid_records_keeps_open_and_rejects_invalid_dates():
    raw_data = build_raw_data(
        [
            build_issue("JIRA-0001", "Done", "2025-03-10T09:00:00Z", "2025-03-10T12:00:00Z"),
            build_issue("JIRA-0002", "Open", "2025-03-11T09:00:00Z", None),
            build_issue("JIRA-0003", "Done", "2026-02-30T25:61:00Z", "not_a_date"),
            build_issue("JIRA-0004", "Resolved", "2025-03-12T09:00:00Z", "not_a_date"),
        ]
    )

    valid_issues, rejected_issues = split_invalid_records(flatten_issues(raw_data))

    assert list(valid_issues["issue_id"]) == ["JIRA-0001", "JIRA-0002"]
    assert pd.isna(valid_issues.loc[1, "resolved_at"])
    assert str(valid_issues["created_at"].dt.tz) == "UTC"
    assert dict(zip(rejected_issues["issue_id"], rejected_issues["rejection_reason"])) == {
        "JIRA-0003": "invalid_created_at",
        "JIRA-0004": "invalid_resolved_at",
    }
    assert rejected_issues.loc[0, "resolved_at"] == "not_a_date"


def test_split_invalid_records_applies_quality_rules():
    raw_data = build_raw_data(
        [
            build_issue("JIRA-0001", "Done", "2025-03-10T09:00:00Z", "2025-03-09T09:00:00Z"),
            build_issue("JIRA-0002", "Closed", "2025-03-10T09:00:00Z", "2025-03-10T10:00:00Z"),
            build_issue("JIRA-0003", "Done", "2025-03-10T09:00:00Z", "2025-03-10T10:00:00Z", priority="Urgent"),
            build_issue("JIRA-0004", "Done", "2025-03-10T09:00:00Z", None),
            build_issue("JIRA-0005", "Done", "2025-03-10T09:00:00Z", "2025-03-10T10:00:00Z"),
            build_issue("JIRA-0005", "Done", "2025-03-10T09:00:00Z", "2025-03-10T10:00:00Z"),
        ]
    )

    valid_issues, rejected_issues = split_invalid_records(flatten_issues(raw_data))

    assert list(valid_issues["issue_id"]) == ["JIRA-0005"]
    assert list(rejected_issues["rejection_reason"]) == [
        "resolved_before_created",
        "invalid_status",
        "invalid_priority",
        "missing_resolved_at",
        "duplicated_issue_id",
    ]
