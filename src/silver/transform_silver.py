"""Silver layer: flatten, standardize and clean the raw JIRA issues."""

import json
import logging

import pandas as pd

from src.config import BRONZE_ISSUES_FILE, SILVER_DIR, SILVER_ISSUES_FILE, SILVER_REJECTED_FILE

logger = logging.getLogger(__name__)

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATE_COLUMNS = ["created_at", "resolved_at", "extracted_at"]
VALID_STATUSES = ["Open", "Done", "Resolved"]
CLOSED_STATUSES = ["Done", "Resolved"]
VALID_PRIORITIES = ["High", "Medium", "Low"]

SILVER_COLUMNS = [
    "issue_id",
    "issue_type",
    "status",
    "priority",
    "assignee_id",
    "assignee_name",
    "assignee_email",
    "created_at",
    "resolved_at",
    "project_id",
    "extracted_at",
]


def read_bronze_issues(bronze_file=BRONZE_ISSUES_FILE):
    """Read the Bronze JSON file."""
    with open(bronze_file, encoding="utf-8") as file:
        return json.load(file)


def extract_nested_records(column):
    """Turn a column of exploded list items into a DataFrame of their fields.

    Empty lists become NaN after explode; they are treated as empty records.
    """
    records = [item if isinstance(item, dict) else {} for item in column]
    return pd.json_normalize(records)


def flatten_issues(raw_data):
    """Explode the nested lists and return one row per issue with snake_case columns."""
    issues = pd.DataFrame(raw_data["issues"])
    issues = issues.explode("assignee").explode("timestamps").reset_index(drop=True)

    assignee = extract_nested_records(issues["assignee"]).add_prefix("assignee_")
    timestamps = extract_nested_records(issues["timestamps"])

    flat_issues = pd.concat([issues.drop(columns=["assignee", "timestamps"]), assignee, timestamps], axis=1)
    flat_issues = flat_issues.rename(columns={"id": "issue_id"})
    flat_issues["project_id"] = raw_data["project"]["project_id"]
    flat_issues["extracted_at"] = raw_data["project"]["extracted_at"]
    return flat_issues[SILVER_COLUMNS]


def parse_dates(issues):
    """Convert ISO 8601 strings to UTC datetimes; invalid values become NaT."""
    parsed_issues = issues.copy()
    for column in DATE_COLUMNS:
        parsed_issues[column] = pd.to_datetime(parsed_issues[column], format=DATE_FORMAT, utc=True, errors="coerce")
    return parsed_issues


def find_rejection_reasons(raw_issues, parsed_issues):
    """Return the first data quality rule each issue breaks (None when the issue is valid)."""
    rules = [
        ("invalid_created_at", parsed_issues["created_at"].isna()),
        ("invalid_resolved_at", raw_issues["resolved_at"].notna() & parsed_issues["resolved_at"].isna()),
        ("resolved_before_created", parsed_issues["resolved_at"] < parsed_issues["created_at"]),
        ("invalid_status", ~parsed_issues["status"].isin(VALID_STATUSES)),
        ("invalid_priority", ~parsed_issues["priority"].isin(VALID_PRIORITIES)),
        (
            "missing_resolved_at",
            parsed_issues["status"].isin(CLOSED_STATUSES) & raw_issues["resolved_at"].isna(),
        ),
        ("duplicated_issue_id", parsed_issues["issue_id"].duplicated(keep="first")),
    ]

    reasons = pd.Series(None, index=raw_issues.index, dtype="object")
    for reason, is_broken in rules:
        reasons[is_broken & reasons.isna()] = reason
    return reasons


def split_invalid_records(raw_issues):
    """Split issues into valid (typed) and rejected (raw values + rejection_reason)."""
    parsed_issues = parse_dates(raw_issues)
    reasons = find_rejection_reasons(raw_issues, parsed_issues)
    is_valid = reasons.isna()

    valid_issues = parsed_issues[is_valid].reset_index(drop=True)
    rejected_issues = raw_issues[~is_valid].assign(rejection_reason=reasons[~is_valid]).reset_index(drop=True)
    return valid_issues, rejected_issues


def transform_silver():
    """Build the Silver layer from the Bronze file and persist it locally."""
    raw_data = read_bronze_issues()
    raw_issues = flatten_issues(raw_data)
    valid_issues, rejected_issues = split_invalid_records(raw_issues)

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    valid_issues.to_parquet(SILVER_ISSUES_FILE, index=False)
    rejected_issues.to_csv(SILVER_REJECTED_FILE, index=False)

    logger.info(
        "Silver written: %s (input=%d, valid=%d, rejected=%d)",
        SILVER_ISSUES_FILE,
        len(raw_issues),
        len(valid_issues),
        len(rejected_issues),
    )
    if not rejected_issues.empty:
        logger.warning(
            "Rejected records by reason: %s (details in %s)",
            rejected_issues["rejection_reason"].value_counts().to_dict(),
            SILVER_REJECTED_FILE,
        )
    return SILVER_ISSUES_FILE
