"""
Setup orchestrator for the collector.

This script runs all setup tasks in the correct order:
1. Database initialization (creates tables and populates cities from Zoneomics)
"""

import sys
import logging
import argparse
from init_db import DatabaseInitializer


def setup_logging():
    """Configure logging for the setup process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def run_setup(populate: bool = True, test_mode: bool = False):
    """
    Run all setup tasks.

    Args:
        populate: If True, populate cities from Zoneomics.
        test_mode: If True, only process first state when populating.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    logger = setup_logging()

    logger.info("=" * 50)
    logger.info("Starting Collector Setup")
    logger.info("=" * 50)

    # Track overall success
    all_success = True

    # Task 1: Initialize Database
    logger.info("\n[Task 1/1] Initializing Database...")
    try:
        db_initializer = DatabaseInitializer(logger=logger)
        if db_initializer.run(populate=populate, test_mode=test_mode):
            logger.info("✓ Database initialization completed")
        else:
            logger.error("✗ Database initialization failed")
            all_success = False
    except Exception as e:
        logger.error(f"✗ Database initialization failed with exception: {e}")
        all_success = False

    # Summary
    logger.info("\n" + "=" * 50)
    if all_success:
        logger.info("Setup completed successfully!")
        logger.info("=" * 50)
        return 0
    else:
        logger.error("Setup completed with errors")
        logger.info("=" * 50)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database setup for collector")
    parser.add_argument(
        "--populate",
        action="store_true",
        default=False,
        help="Populate cities from Zoneomics"
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Only process first state (for testing)"
    )
    args = parser.parse_args()

    exit_code = run_setup(populate=args.populate, test_mode=args.test_mode)
    sys.exit(exit_code)
