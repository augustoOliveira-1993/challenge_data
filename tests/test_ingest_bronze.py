import hashlib

from azure.core.exceptions import ServiceRequestError

from src.bronze import ingest_bronze
from src.config import LOCAL_SOURCE_FILE


def calculate_sha256(content):
    return hashlib.sha256(content).hexdigest()


def use_temporary_bronze_dir(monkeypatch, tmp_path):
    bronze_file = tmp_path / "bronze_issues.json"
    monkeypatch.setattr(ingest_bronze, "BRONZE_DIR", tmp_path)
    monkeypatch.setattr(ingest_bronze, "BRONZE_ISSUES_FILE", bronze_file)
    return bronze_file


def test_read_source_content_uses_local_file_when_azure_is_not_configured(monkeypatch):
    monkeypatch.setattr(ingest_bronze, "get_azure_settings", lambda: None)

    content, source_name = ingest_bronze.read_source_content()

    assert source_name == "local"
    assert content == LOCAL_SOURCE_FILE.read_bytes()


def test_read_source_content_falls_back_to_local_file_when_azure_fails(monkeypatch):
    def fail_to_read_blob(settings):
        raise ServiceRequestError("simulated Azure failure")

    monkeypatch.setattr(ingest_bronze, "get_azure_settings", lambda: {"CONTAINER_NAME": "c", "BLOB_NAME": "b"})
    monkeypatch.setattr(ingest_bronze, "read_blob_content", fail_to_read_blob)

    content, source_name = ingest_bronze.read_source_content()

    assert source_name == "local"
    assert content == LOCAL_SOURCE_FILE.read_bytes()


def test_read_source_content_uses_azure_when_available(monkeypatch):
    monkeypatch.setattr(ingest_bronze, "get_azure_settings", lambda: {"CONTAINER_NAME": "c", "BLOB_NAME": "b"})
    monkeypatch.setattr(ingest_bronze, "read_blob_content", lambda settings: b'{"issues": []}')

    content, source_name = ingest_bronze.read_source_content()

    assert source_name == "azure"
    assert content == b'{"issues": []}'


def test_ingest_bronze_preserves_source_bytes(monkeypatch, tmp_path):
    bronze_file = use_temporary_bronze_dir(monkeypatch, tmp_path)
    monkeypatch.setattr(ingest_bronze, "get_azure_settings", lambda: None)

    ingest_bronze.ingest_bronze()

    assert calculate_sha256(bronze_file.read_bytes()) == calculate_sha256(LOCAL_SOURCE_FILE.read_bytes())
