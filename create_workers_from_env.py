#!/usr/bin/env python3
"""
Create Workers from Environment Variables
Check for worker credentials in environment and create workers in database
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkerCreator:
    """Create workers from environment variables."""
    
    def __init__(self):
        self.logger = logger
    
    def check_worker_credentials(self):
        """Check which worker credentials are available."""
        print("🔍 CHECKING WORKER CREDENTIALS")
        print("=" * 50)
        
        available_workers = []
        
        # Check for worker credentials (1-10)
        for i in range(1, 11):
            api_id = os.getenv(f'WORKER_{i}_API_ID')
            api_hash = os.getenv(f'WORKER_{i}_API_HASH')
            phone = os.getenv(f'WORKER_{i}_PHONE')
            
            if api_id and api_hash and phone:
                # Check if they're not placeholder values
                if (api_id != 'your_worker_1_api_id' and 
                    api_id != 'your_api_id_here' and
                    api_id != 'your_api_id_1' and
                    api_id != 'YOUR_SECOND_API_ID' and
                    api_id != 'YOUR_THIRD_API_ID' and
                    api_id != 'YOUR_FOURTH_API_ID' and
                    api_id != 'YOUR_FIFTH_API_ID' and
                    api_id != 'YOUR_ACTUAL_API_ID'):
                    
                    available_workers.append({
                        'worker_id': i,
                        'api_id': api_id,
                        'api_hash': api_hash,
                        'phone': phone
                    })
                    print(f"✅ Worker {i}: Configured")
                else:
                    print(f"⚠️ Worker {i}: Placeholder values (not configured)")
            else:
                print(f"❌ Worker {i}: Missing credentials")
        
        print(f"\n📊 Found {len(available_workers)} configured workers")
        return available_workers
    
    async def create_workers_in_database(self, workers):
        """Create workers in the database."""
        print(f"\n🔧 CREATING {len(workers)} WORKERS IN DATABASE")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Get connection for direct SQL
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            created_count = 0
            
            for worker in workers:
                worker_id = worker['worker_id']
                api_id = worker['api_id']
                api_hash = worker['api_hash']
                phone = worker['phone']
                
                # Check if worker already exists
                cursor.execute("SELECT worker_id FROM workers WHERE worker_id = ?", (worker_id,))
                existing = cursor.fetchone()
                
                if existing:
                    print(f"⚠️ Worker {worker_id}: Already exists in database")
                    continue
                
                # Create worker
                cursor.execute("""
                    INSERT INTO workers (
                        worker_id, api_id, api_hash, phone, 
                        is_active, is_registered, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (worker_id, api_id, api_hash, phone))
                
                print(f"✅ Worker {worker_id}: Created in database")
                created_count += 1
            
            conn.commit()
            print(f"\n📊 Created {created_count} new workers")
            
            # Verify workers
            cursor.execute("SELECT COUNT(*) FROM workers")
            total_workers = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
            active_workers = cursor.fetchone()[0]
            
            print(f"📊 Total workers in database: {total_workers}")
            print(f"📊 Active workers: {active_workers}")
            
            await db.close()
            return created_count
            
        except Exception as e:
            print(f"❌ Error creating workers: {e}")
            return 0
    
    async def test_worker_connections(self, workers):
        """Test worker connections (optional)."""
        print(f"\n🔍 TESTING WORKER CONNECTIONS")
        print("=" * 50)
        
        try:
            from telethon import TelegramClient
            
            successful_connections = 0
            
            for worker in workers[:3]:  # Test first 3 workers only
                worker_id = worker['worker_id']
                api_id = worker['api_id']
                api_hash = worker['api_hash']
                phone = worker['phone']
                
                try:
                    print(f"🔍 Testing Worker {worker_id}...")
                    
                    # Create session name
                    session_name = f"sessions/worker_{worker_id}"
                    os.makedirs('sessions', exist_ok=True)
                    
                    # Create client
                    client = TelegramClient(session_name, int(api_id), api_hash)
                    
                    # Start client with timeout
                    await asyncio.wait_for(client.start(phone=phone), timeout=30.0)
                    
                    # Test connection
                    me = await client.get_me()
                    if me:
                        print(f"✅ Worker {worker_id}: Connected as @{me.username or 'Unknown'}")
                        successful_connections += 1
                    else:
                        print(f"❌ Worker {worker_id}: Failed to get user info")
                    
                    # Disconnect
                    await client.disconnect()
                    
                except asyncio.TimeoutError:
                    print(f"❌ Worker {worker_id}: Connection timeout")
                except Exception as e:
                    print(f"❌ Worker {worker_id}: Connection failed - {e}")
            
            print(f"\n📊 Connection test results: {successful_connections}/{min(3, len(workers))} successful")
            return successful_connections
            
        except Exception as e:
            print(f"❌ Error testing connections: {e}")
            return 0
    
    async def verify_scheduler_readiness(self):
        """Verify if scheduler is ready to post."""
        print(f"\n🔍 VERIFYING SCHEDULER READINESS")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Get connection for direct SQL
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Check all components
            cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
            active_workers = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
            active_slots = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM destinations WHERE status = 'active'")
            active_destinations = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
            active_subscriptions = cursor.fetchone()[0]
            
            print(f"📊 Scheduler Components:")
            print(f"  - Active workers: {active_workers}")
            print(f"  - Active ad slots: {active_slots}")
            print(f"  - Active destinations: {active_destinations}")
            print(f"  - Active subscriptions: {active_subscriptions}")
            
            # Determine readiness
            if active_workers > 0 and active_slots > 0 and active_destinations > 0:
                print(f"\n✅ SCHEDULER READY: Can post ads!")
                print(f"🚀 Expected posting capacity: {active_workers} workers × {active_slots} slots")
            else:
                print(f"\n❌ SCHEDULER NOT READY:")
                if active_workers == 0:
                    print(f"  - No active workers")
                if active_slots == 0:
                    print(f"  - No active ad slots")
                if active_destinations == 0:
                    print(f"  - No active destinations")
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Error verifying scheduler: {e}")

async def main():
    """Main function."""
    creator = WorkerCreator()
    
    # Check available worker credentials
    workers = creator.check_worker_credentials()
    
    if not workers:
        print("\n❌ NO WORKER CREDENTIALS FOUND")
        print("💡 To add workers, add these to your config/.env file:")
        print("   WORKER_1_API_ID=your_api_id")
        print("   WORKER_1_API_HASH=your_api_hash")
        print("   WORKER_1_PHONE=your_phone")
        print("   (Repeat for workers 2-10 as needed)")
        return
    
    # Create workers in database
    created_count = await creator.create_workers_in_database(workers)
    
    if created_count > 0:
        # Test connections (optional)
        await creator.test_worker_connections(workers)
    
    # Verify scheduler readiness
    await creator.verify_scheduler_readiness()
    
    print(f"\n📊 WORKER CREATION SUMMARY")
    print("=" * 50)
    print(f"✅ Available workers: {len(workers)}")
    print(f"✅ Created in database: {created_count}")
    print(f"✅ Scheduler should now be able to post!")

if __name__ == "__main__":
    asyncio.run(main())
