import logging
import sys
from pathlib import Path

from extract import extract_ktmb_data
from transform import save_processed_data, transform_ktmb_data
from validate import validate_ktmb_data


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    """Show log messages in the terminal and save them to a file."""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                log_dir / "pipeline.log", encoding="utf-8"
            ),
        ],
    )


def run_pipeline() -> None:
    """Run the Phase 1 KTMB pipeline from download to processed CSV."""
    try:
        LOGGER.info("Starting KTMB ETL pipeline")
        LOGGER.info("Downloading source dataset")

        raw_data = extract_ktmb_data()
        LOGGER.info("Extracted %s rows", len(raw_data))

        validate_ktmb_data(raw_data)
        LOGGER.info("Raw validation passed")

        processed_data = transform_ktmb_data(raw_data)
        LOGGER.info("Transformation completed: %s rows", len(processed_data))

        validate_ktmb_data(processed_data)
        LOGGER.info("Processed validation passed")

        output_path = save_processed_data(processed_data)
        LOGGER.info("Processed dataset saved to %s", output_path)
        LOGGER.info("Pipeline completed successfully")

    except Exception:
        LOGGER.exception("KTMB ETL pipeline failed")
        raise


if __name__ == "__main__":
    configure_logging()
    run_pipeline()