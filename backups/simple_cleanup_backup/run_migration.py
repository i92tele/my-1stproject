#!/usr/bin/env python3
"""
Simple script to run the database migration.
"""

import asyncio
import os
from dotenv import load_dotenv
from database_migration import run_migration, verify_migration

# Load environment variables
load_dotenv('config/.env')

async def main():
    """Run the database migration."""
    print("🚀 Starting database migration...")
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("Please set DATABASE_URL in your .env file")
        return
    
    print(f"📋 Using database: {database_url}")
    
    # Run migration
    success = await run_migration(database_url)
    
    if success:
        print("✅ Migration completed successfully!")
        
        # Verify migration
        print("🔍 Verifying migration...")
        verified = await verify_migration(database_url)
        
        if verified:
            print("✅ Migration verified successfully!")
            print("\n📊 Migration Summary:")
            print("• worker_cooldowns table: ✅ Created/Updated")
            print("• worker_accounts table: ✅ Created")
            print("• Missing columns: ✅ Added")
            print("• Default data: ✅ Inserted")
        else:
            print("❌ Migration verification failed!")
    else:
        print("❌ Migration failed!")

if __name__ == "__main__":
    asyncio.run(main()) 