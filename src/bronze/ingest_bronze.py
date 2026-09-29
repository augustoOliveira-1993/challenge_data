"""Bronze layer: ingest the raw JIRA JSON without changing its content."""

import json
import logging

from azure.core.exceptions import AzureError
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient, ExponentialRetry

from src.config import BRONZE_DIR, BRONZE_ISSUES_FILE, LOCAL_SOURCE_FILE, get_azure_settings

logger = logging.getLogger(__name__)


def read_blob_content(settings):
    """Download the blob (read-only) using a Service Principal and return its raw bytes."""
    credential = ClientSecretCredential(
        tenant_id=settings["AZURE_TENANT_ID"],
        client_id=settings["AZURE_CLIENT_ID"],
        client_secret=settings["AZURE_CLIENT_SECRET"],
    )
    # SDK default is 3 retries starting at 15s (~80s); one quick retry is enough since we have a local fallback.
    retry_policy = ExponentialRetry(initial_backoff=2, retry_total=1)
    blob_service_client = BlobServiceClient(
        account_url=settings["ACCOUNT_URL"],
        credential=credential,
        retry_policy=retry_policy,
    )
    blob_client = blob_service_client.get_blob_client(
        container=settings["CONTAINER_NAME"],
        blob=settings["BLOB_NAME"],
    )
    return blob_client.download_blob().readall()


def read_local_content():
    """Read the local copy of the source file and return its raw bytes."""
    return LOCAL_SOURCE_FILE.read_bytes()


def read_source_content():
    """Read the source from Azure, falling back to the local file.

    Returns a tuple (content, source_name).
    """
    settings = get_azure_settings()
    if settings is None:
        logger.warning("Azure source skipped. Pipeline will continue using local file: %s", LOCAL_SOURCE_FILE)
        return read_local_content(), "local"

    try:
        logger.info("Reading source from Azure Blob Storage (%s/%s)", settings["CONTAINER_NAME"], settings["BLOB_NAME"])
        return read_blob_content(settings), "azure"
    except (AzureError, ValueError) as error:
        logger.warning(
            "Official Azure source FAILED (%s: %s). Pipeline will continue using local file: %s",
            type(error).__name__,
            error,
            LOCAL_SOURCE_FILE,
        )
        return read_local_content(), "local"


def ingest_bronze():
    """Persist the source content in the Bronze layer exactly as received.

    The content is parsed only to check that it is valid JSON; the original
    bytes are written, not a re-serialized version.
    """
    content, source_name = read_source_content()

    raw_data = json.loads(content)
    issue_count = len(raw_data.get("issues", []))

    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    BRONZE_ISSUES_FILE.write_bytes(content)

    logger.info(
        "Bronze written: %s (source=%s, bytes=%d, issues=%d)",
        BRONZE_ISSUES_FILE,
        source_name,
        len(content),
        issue_count,
    )
    return BRONZE_ISSUES_FILE
