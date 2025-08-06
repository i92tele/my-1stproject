#!/usr/bin/env python3
"""
Database migration script to add missing tables for worker management and payments.
"""

import asyncio
import asyncpg
import logging
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def migrate_database(db_manager):
    """Add missing tables for worker management and payments"""
    
    try:
        logger.info("🚀 Starting database migration...")
        
        # Get database connection from the manager
        pool = db_manager.pool
        if not pool:
            logger.error("❌ Database pool not available")
            return False
        
        async with pool.acquire() as conn:
            # Check if tables exist and create them if they don't
            await _create_worker_cooldowns_table(conn)
            await _create_worker_accounts_table(conn)
            await _add_missing_columns(conn)
            
        logger.info("✅ Database migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        return False

async def _create_worker_cooldowns_table(conn):
    """Create worker_cooldowns table if it doesn't exist."""
    try:
        # Check if table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'worker_cooldowns'
            )
        """)
        
        if not table_exists:
            logger.info("📋 Creating worker_cooldowns table...")
            await conn.execute('''
                CREATE TABLE worker_cooldowns (
                    worker_id INTEGER PRIMARY KEY,
                    last_used_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT true,
                    cooldown_minutes INTEGER DEFAULT 30,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logger.info("✅ worker_cooldowns table created")
        else:
            logger.info("ℹ️ worker_cooldowns table already exists")
            
    except Exception as e:
        logger.error(f"❌ Error creating worker_cooldowns table: {e}")
        raise

async def _create_worker_accounts_table(conn):
    """Create worker_accounts table if it doesn't exist."""
    try:
        # Check if table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'worker_accounts'
            )
        """)
        
        if not table_exists:
            logger.info("📋 Creating worker_accounts table...")
            await conn.execute('''
                CREATE TABLE worker_accounts (
                    id SERIAL PRIMARY KEY,
                    worker_index INTEGER UNIQUE,
                    phone VARCHAR(20),
                    username VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'active',
                    last_health_check TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logger.info("✅ worker_accounts table created")
        else:
            logger.info("ℹ️ worker_accounts table already exists")
            
    except Exception as e:
        logger.error(f"❌ Error creating worker_accounts table: {e}")
        raise

async def _add_missing_columns(conn):
    """Add missing columns to existing tables."""
    try:
        # Check and add cooldown_minutes column to worker_cooldowns if it doesn't exist
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'worker_cooldowns' 
                AND column_name = 'cooldown_minutes'
            )
        """)
        
        if not column_exists:
            logger.info("📋 Adding cooldown_minutes column to worker_cooldowns...")
            await conn.execute('''
                ALTER TABLE worker_cooldowns 
                ADD COLUMN cooldown_minutes INTEGER DEFAULT 30
            ''')
            logger.info("✅ cooldown_minutes column added")
        
        # Check and add updated_at column to worker_cooldowns if it doesn't exist
        updated_at_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'worker_cooldowns' 
                AND column_name = 'updated_at'
            )
        """)
        
        if not updated_at_exists:
            logger.info("📋 Adding updated_at column to worker_cooldowns...")
            await conn.execute('''
                ALTER TABLE worker_cooldowns 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')
            logger.info("✅ updated_at column added")
        
        # Check and add created_at column to worker_accounts if it doesn't exist
        created_at_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'worker_accounts' 
                AND column_name = 'created_at'
            )
        """)
        
        if not created_at_exists:
            logger.info("📋 Adding created_at column to worker_accounts...")
            await conn.execute('''
                ALTER TABLE worker_accounts 
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')
            logger.info("✅ created_at column added")
        
        # Check and add updated_at column to worker_accounts if it doesn't exist
        updated_at_accounts_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'worker_accounts' 
                AND column_name = 'updated_at'
            )
        """)
        
        if not updated_at_accounts_exists:
            logger.info("📋 Adding updated_at column to worker_accounts...")
            await conn.execute('''
                ALTER TABLE worker_accounts 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')
            logger.info("✅ updated_at column added to worker_accounts")
            
    except Exception as e:
        logger.error(f"❌ Error adding missing columns: {e}")
        raise

async def _insert_default_worker_data(conn):
    """Insert default worker data for workers 1, 2, and 4."""
    try:
        logger.info("📋 Inserting default worker data...")
        
        # Insert default worker cooldowns
        await conn.execute('''
            INSERT INTO worker_cooldowns (worker_id, is_active, cooldown_minutes)
            VALUES (1, true, 30), (2, true, 30), (4, true, 30)
            ON CONFLICT (worker_id) DO NOTHING
        ''')
        
        # Insert default worker accounts
        await conn.execute('''
            INSERT INTO worker_accounts (worker_index, status)
            VALUES (1, 'active'), (2, 'active'), (4, 'active')
            ON CONFLICT (worker_index) DO NOTHING
        ''')
        
        logger.info("✅ Default worker data inserted")
        
    except Exception as e:
        logger.error(f"❌ Error inserting default worker data: {e}")
        raise

async def run_migration(database_url: str):
    """Run the complete migration process."""
    try:
        # Create a temporary connection pool for migration
        pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=5,
            command_timeout=30.0
        )
        
        # Create a mock database manager for the migration
        class MockDBManager:
            def __init__(self, pool):
                self.pool = pool
        
        db_manager = MockDBManager(pool)
        
        # Run migration
        success = await migrate_database(db_manager)
        
        # Close pool
        await pool.close()
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

async def verify_migration(database_url: str):
    """Verify that all required tables and columns exist."""
    try:
        pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=5,
            command_timeout=30.0
        )
        
        async with pool.acquire() as conn:
            # Check worker_cooldowns table
            cooldowns_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'worker_cooldowns'
                )
            """)
            
            # Check worker_accounts table
            accounts_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'worker_accounts'
                )
            """)
            
            # Check columns in worker_cooldowns
            cooldown_columns = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'worker_cooldowns'
                ORDER BY column_name
            """)
            
            # Check columns in worker_accounts
            account_columns = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'worker_accounts'
                ORDER BY column_name
            """)
        
        await pool.close()
        
        logger.info("🔍 Migration verification results:")
        logger.info(f"worker_cooldowns table exists: {cooldowns_exists}")
        logger.info(f"worker_accounts table exists: {accounts_exists}")
        logger.info(f"worker_cooldowns columns: {[col['column_name'] for col in cooldown_columns]}")
        logger.info(f"worker_accounts columns: {[col['column_name'] for col in account_columns]}")
        
        return cooldowns_exists and accounts_exists
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv('config/.env')
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL not found in environment variables")
        exit(1)
    
    async def main():
        logger.info("🚀 Starting database migration...")
        
        # Run migration
        success = await run_migration(database_url)
        
        if success:
            logger.info("✅ Migration completed successfully!")
            
            # Verify migration
            logger.info("🔍 Verifying migration...")
            verified = await verify_migration(database_url)
            
            if verified:
                logger.info("✅ Migration verified successfully!")
            else:
                logger.error("❌ Migration verification failed!")
        else:
            logger.error("❌ Migration failed!")
    
    # Run the migration
    asyncio.run(main()) 