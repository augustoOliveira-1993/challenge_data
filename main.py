"""Pipeline entry point: python main.py

Runs the Medallion layers in order: Bronze -> Silver -> Gold.
Each layer reads the file persisted by the previous one.
"""

import logging
import sys

from src.bronze.ingest_bronze import ingest_bronze
from src.gold.build_gold import build_gold
from src.silver.transform_silver import transform_silver

logger = logging.getLogger("pipeline")


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
    logger.info("Pipeline started")
    ingest_bronze()
    transform_silver()
    build_gold()
    logger.info("Pipeline finished successfully")


if __name__ == "__main__":
    configure_logging()
    try:
        run_pipeline()
    except Exception:
        logger.exception("Pipeline failed")
        sys.exit(1)
