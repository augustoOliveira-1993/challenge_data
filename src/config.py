"""Project paths and environment settings."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
RESOURCES_DIR = PROJECT_ROOT / "resources"

LOCAL_SOURCE_FILE = RESOURCES_DIR / "jira_issues_raw.json"
BRONZE_ISSUES_FILE = BRONZE_DIR / "bronze_issues.json"
SILVER_ISSUES_FILE = SILVER_DIR / "silver_issues.parquet"
SILVER_REJECTED_FILE = SILVER_DIR / "silver_issues_rejected.csv"
GOLD_SLA_ISSUES_FILE = GOLD_DIR / "gold_sla_issues.csv"

AZURE_ENV_VARS = (
    "ACCOUNT_URL",
    "CONTAINER_NAME",
    "BLOB_NAME",
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
)

load_dotenv(PROJECT_ROOT / ".env")


def get_azure_settings():
    """Return the Azure settings as a dict, or None if any variable is missing.

    Only variable names are logged, never their values.
    """
    settings = {name: os.getenv(name) for name in AZURE_ENV_VARS}
    missing_vars = [name for name, value in settings.items() if not value]

    if missing_vars:
        logger.warning("Azure not configured (missing: %s)", ", ".join(missing_vars))
        return None

    return settings
