"""Pipeline entry point: python main.py"""

import logging

from src.bronze.ingest_bronze import ingest_bronze
from src.silver.transform_silver import transform_silver


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    # Keep Azure SDK HTTP logs out of the pipeline output.
    logging.getLogger("azure").setLevel(logging.WARNING)
    # azure.identity logs a WARNING on every failed attempt; our own WARNING already reports the failure.
    logging.getLogger("azure.identity").setLevel(logging.ERROR)


def run_pipeline():
    ingest_bronze()
    transform_silver()


if __name__ == "__main__":
    configure_logging()
    run_pipeline()
