#!/usr/bin/env python3
"""
Main Scheduler Entry Point
Run with: python -m scheduler
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv('config/.env')

from src.config.bot_config import BotConfig
from src.database.manager import DatabaseManager
from scheduler.core.scheduler import AutomatedScheduler
from scheduler.config.scheduler_config import SchedulerConfig
from scheduler.config.worker_config import WorkerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main scheduler function."""
    try:
        logger.info("Starting automated scheduler...")
        
        # Load configuration
        config = BotConfig.load_from_env()
        scheduler_config = SchedulerConfig()
        worker_config = WorkerConfig()
        
        # Initialize database
        db = DatabaseManager(config.db_path, logger)
        await db.initialize()
        
        # Load worker credentials
        workers = worker_config.load_workers_from_env()
        if not workers:
            logger.error("No worker credentials found. Please add WORKER_*_API_ID, WORKER_*_API_HASH, WORKER_*_PHONE to environment.")
            return
            
        # Initialize scheduler
        scheduler = AutomatedScheduler(db, scheduler_config)
        await scheduler.initialize()
        
        # Start scheduler
        await scheduler.start()
        
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        raise
    finally:
        logger.info("Scheduler shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
