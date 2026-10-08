import logging
import os
import sys
import time

# Add the project root to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from utils.database import initialize_database, health_check
from utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def run_initialization():
    """
    Runs the database initialization process.
    - Waits for the database to be ready (handled inside initialize_database).
    - Creates tables based on models.
    - Populates initial data if necessary.
    """
    logger.info("Starting database migration and initialization...")
    
    try:
        # The initialize_database function from utils.database handles the waiting,
        # table creation, and initial data population.
        initialize_database(reset=False)
        
        logger.info("Database initialization process completed successfully.")
        
        # Perform a final health check to confirm connectivity.
        health = health_check()
        logger.info(f"Final health check status: {health}")
        
        # Check if any of the main databases failed the health check
        main_dbs_health = {k: v for k, v in health.items() if k in ['main_db']}
        if any(status['status'] == 'error' for status in main_dbs_health.values()):
             logger.error("One or more databases are unhealthy after initialization.")
             sys.exit(1) # Exit with error code

        logger.info("All databases are healthy. Migration successful.")
        sys.exit(0) # Explicitly exit with success code

    except Exception as e:
        logger.error(f"An error occurred during database initialization: {e}", exc_info=True)
        # Exit with a non-zero status code to indicate failure.
        # This is crucial for Docker Compose's `depends_on` condition.
        sys.exit(1)

if __name__ == "__main__":
    run_initialization()
