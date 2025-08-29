#!/usr/bin/env python3
"""
Worker Database Cleanup Script
Clean up worker database and keep only 10 active workers
"""

import asyncio
import logging
from dotenv import load_dotenv

load_dotenv("config/.env")

async def cleanup_workers():
    """Clean up worker database."""
    from src.config.main_config import BotConfig
    from src.database.manager import DatabaseManager
    
    config = BotConfig.load_from_env()
    db = DatabaseManager(config.database_url or "bot_database.db", logging.getLogger(__name__))
    await db.initialize()
    
    conn = await db.get_connection()
    cursor = conn.cursor()
    
    # Remove all workers except the first 10
    cursor.execute("DELETE FROM workers WHERE id > 10")
    deleted_count = cursor.rowcount
    
    # Activate the first 10 workers
    cursor.execute("UPDATE workers SET status = 'active' WHERE id <= 10")
    activated_count = cursor.rowcount
    
    conn.commit()
    await db.close()
    
    print(f"✅ Deleted {deleted_count} excess workers")
    print(f"✅ Activated {activated_count} workers")

if __name__ == "__main__":
    asyncio.run(cleanup_workers())
