"""
Setup orchestrator for the collector.

This script runs all setup tasks in the correct order:
1. Database initialization
2. (Future: Add more setup tasks here)
"""

import sys
import logging
from init_db import DatabaseInitializer


def setup_logging():
    """Configure logging for the setup process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def run_setup():
    """
    Run all setup tasks.

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
        if db_initializer.run():
            logger.info("✓ Database initialization completed")
        else:
            logger.error("✗ Database initialization failed")
            all_success = False
    except Exception as e:
        logger.error(f"✗ Database initialization failed with exception: {e}")
        all_success = False

    # Future tasks can be added here:
    # Task 2: Initialize other resources
    # Task 3: Run migrations
    # etc.

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
    exit_code = run_setup()
    sys.exit(exit_code)
