#!/usr/bin/env python3
import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from config import BotConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler_fix.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('config/.env')

class SchedulerFixer:
    def __init__(self):
        self.config = BotConfig.load_from_env()
        self.db = DatabaseManager(self.config, logger)
        
    async def cleanup_stale_sessions(self):
        """Clean up stale session files that might cause hanging."""
        sessions_dir = 'sessions'
        if os.path.exists(sessions_dir):
            for file in os.listdir(sessions_dir):
                if file.endswith('.session'):
                    file_path = os.path.join(sessions_dir, file)
                    # Check if file is older than 1 hour
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if datetime.now() - file_mtime > timedelta(hours=1):
                        try:
                            os.remove(file_path)
                            logger.info(f"Removed stale session file: {file}")
                        except Exception as e:
                            logger.error(f"Failed to remove {file}: {e}")
                            
    async def reset_failed_ads(self):
        """Reset ads that have been stuck in failed states."""
        try:
            await self.db.initialize()
            
            # Reset ads that haven't been sent in the last hour
            async with self.db.pool.acquire() as conn:
                # Get ads that are active but haven't been sent recently
                result = await conn.fetch("""
                    SELECT id, user_id, slot_number, last_sent_at 
                    FROM ad_slots 
                    WHERE is_active = true 
                    AND (last_sent_at IS NULL OR last_sent_at < NOW() - INTERVAL '1 hour')
                """)
                
                for row in result:
                    logger.info(f"Resetting stuck ad slot {row['slot_number']} for user {row['user_id']}")
                    await conn.execute("""
                        UPDATE ad_slots 
                        SET last_sent_at = NULL 
                        WHERE id = $1
                    """, row['id'])
                    
            logger.info(f"Reset {len(result)} stuck ad slots")
            
        except Exception as e:
            logger.error(f"Error resetting failed ads: {e}")
            
    async def cleanup_database_connections(self):
        """Clean up any stuck database connections."""
        try:
            if self.db.pool:
                # Close all connections in the pool
                await self.db.pool.close()
                logger.info("Closed database connection pool")
                
                # Reinitialize the pool
                await self.db.initialize()
                logger.info("Reinitialized database connection pool")
                
        except Exception as e:
            logger.error(f"Error cleaning up database connections: {e}")
            
    async def fix_worker_issues(self):
        """Fix common worker account issues."""
        # Remove stale session files
        await self.cleanup_stale_sessions()
        
        # Check for worker account files that might be corrupted
        worker_files = [
            'session_worker_1.session', 'session_worker_2.session',
            'session_worker_3.session', 'session_worker_4.session',
            'session_worker_5.session'
        ]
        
        for file in worker_files:
            if os.path.exists(file):
                try:
                    # Check file size - if too small, it might be corrupted
                    if os.path.getsize(file) < 1000:  # Less than 1KB
                        os.remove(file)
                        logger.info(f"Removed corrupted worker session: {file}")
                except Exception as e:
                    logger.error(f"Error checking worker file {file}: {e}")
                    
    async def run_fixes(self):
        """Run all fixes."""
        logger.info("Starting scheduler fixes...")
        
        try:
            # Clean up stale sessions
            await self.cleanup_stale_sessions()
            
            # Reset failed ads
            await self.reset_failed_ads()
            
            # Clean up database connections
            await self.cleanup_database_connections()
            
            # Fix worker issues
            await self.fix_worker_issues()
            
            logger.info("All fixes completed successfully!")
            
        except Exception as e:
            logger.error(f"Error running fixes: {e}")
        finally:
            await self.db.close()

async def main():
    fixer = SchedulerFixer()
    await fixer.run_fixes()

if __name__ == '__main__':
    asyncio.run(main()) 