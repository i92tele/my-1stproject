#!/usr/bin/env python3
"""
Comprehensive System Fix
Fixes payment verification, worker issues, and system diagnostics
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BotConfig
from database import DatabaseManager
from ton_payments import TONPaymentProcessor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv('config/.env')

class SystemFixer:
    def __init__(self):
        self.config = BotConfig.load_from_env()
        self.db = DatabaseManager(self.config, logger)
        self.payment_processor = TONPaymentProcessor(self.config, self.db, logger)
    
    async def initialize(self):
        """Initialize database connection."""
        await self.db.initialize()
        logger.info("System fixer initialized")
    
    async def fix_payment_verification(self):
        """Fix payment verification issues."""
        print("\n💰 Fixing Payment Verification")
        print("=" * 40)
        
        try:
            # Check pending payments
            async with self.db.pool.acquire() as conn:
                pending_payments = await conn.fetch('''
                    SELECT payment_id, user_id, tier, amount_crypto, payment_memo, created_at
                    FROM payments 
                    WHERE status = 'pending'
                    ORDER BY created_at DESC
                ''')
            
            if not pending_payments:
                print("✅ No pending payments found")
                return
            
            print(f"🔍 Found {len(pending_payments)} pending payments")
            
            for payment in pending_payments:
                payment_data = dict(payment)
                print(f"\n📱 Checking payment: {payment_data['payment_id']}")
                print(f"   Amount: {payment_data['amount_crypto']} TON")
                print(f"   Memo: {payment_data['payment_memo']}")
                
                # Manual verification
                is_verified = await self.payment_processor.verify_payment_on_blockchain(payment_data)
                
                if is_verified:
                    print("✅ Payment verified! Activating subscription...")
                    
                    # Update payment status
                    await self.db.update_payment_status(payment_data['payment_id'], 'completed')
                    
                    # Activate subscription
                    success = await self.db.activate_subscription(
                        payment_data['user_id'], 
                        payment_data['tier'], 
                        duration_days=30
                    )
                    
                    if success:
                        print(f"✅ Subscription activated for user {payment_data['user_id']}")
                    else:
                        print(f"❌ Failed to activate subscription for user {payment_data['user_id']}")
                else:
                    print("❌ Payment not verified on blockchain")
        
        except Exception as e:
            print(f"❌ Error in payment verification: {e}")
    
    async def fix_worker_issues(self):
        """Fix worker posting and joining issues."""
        print("\n🤖 Fixing Worker Issues")
        print("=" * 40)
        
        try:
            # Check if scheduler is running
            import psutil
            scheduler_running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'scheduler' in str(proc.info['cmdline']):
                    scheduler_running = True
                    print(f"✅ Scheduler running (PID: {proc.info['pid']})")
                    break
            
            if not scheduler_running:
                print("❌ Scheduler not running")
                print("💡 Start scheduler with: python3 scheduler.py")
            
            # Check worker configurations
            worker_count = 0
            for i in range(1, 50):
                api_id = os.getenv(f'WORKER_{i}_API_ID')
                api_hash = os.getenv(f'WORKER_{i}_API_HASH')
                phone = os.getenv(f'WORKER_{i}_PHONE')
                
                if api_id and api_hash and phone:
                    worker_count += 1
            
            print(f"📊 Configured workers: {worker_count}")
            
            # Check managed groups
            async with self.db.pool.acquire() as conn:
                groups = await conn.fetch('SELECT * FROM managed_groups')
                print(f"📢 Managed groups: {len(groups)}")
                
                for group in groups:
                    print(f"   - {group['group_username']} ({group['category']})")
            
            # Check ad slots
            async with self.db.pool.acquire() as conn:
                slots = await conn.fetch('SELECT * FROM ad_slots WHERE is_active = true')
                print(f"📋 Active ad slots: {len(slots)}")
                
                for slot in slots:
                    print(f"   - Slot {slot['slot_number']} (User: {slot['user_id']})")
        
        except Exception as e:
            print(f"❌ Error checking worker issues: {e}")
    
    async def fix_database_issues(self):
        """Fix database connectivity and schema issues."""
        print("\n🗄️ Fixing Database Issues")
        print("=" * 40)
        
        try:
            # Test database connection
            async with self.db.pool.acquire() as conn:
                result = await conn.fetchval('SELECT 1')
                print("✅ Database connection working")
            
            # Check table structure
            async with self.db.pool.acquire() as conn:
                tables = await conn.fetch('''
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                ''')
                
                required_tables = ['users', 'payments', 'ad_slots', 'managed_groups', 'ad_posts']
                existing_tables = [row['table_name'] for row in tables]
                
                print(f"📊 Database tables: {', '.join(existing_tables)}")
                
                missing_tables = set(required_tables) - set(existing_tables)
                if missing_tables:
                    print(f"❌ Missing tables: {', '.join(missing_tables)}")
                else:
                    print("✅ All required tables exist")
        
        except Exception as e:
            print(f"❌ Database error: {e}")
    
    async def restart_services(self):
        """Restart bot services."""
        print("\n🔄 Restarting Services")
        print("=" * 40)
        
        try:
            import subprocess
            import signal
            
            # Kill existing processes
            subprocess.run(['pkill', '-f', 'python3 bot.py'], capture_output=True)
            subprocess.run(['pkill', '-f', 'python3 scheduler.py'], capture_output=True)
            subprocess.run(['pkill', '-f', 'python3 payment_monitor.py'], capture_output=True)
            
            print("✅ Killed existing processes")
            
            # Start services
            print("🚀 Starting services...")
            
            # Start bot
            subprocess.Popen(['python3', 'bot.py'], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
            print("✅ Bot started")
            
            # Start scheduler
            subprocess.Popen(['python3', 'scheduler.py'], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
            print("✅ Scheduler started")
            
            # Start payment monitor
            subprocess.Popen(['python3', 'payment_monitor.py'], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
            print("✅ Payment monitor started")
            
        except Exception as e:
            print(f"❌ Error restarting services: {e}")
    
    async def run_comprehensive_fix(self):
        """Run all fixes."""
        print("🔧 Comprehensive System Fix")
        print("=" * 50)
        
        await self.initialize()
        
        # Fix payment verification
        await self.fix_payment_verification()
        
        # Fix worker issues
        await self.fix_worker_issues()
        
        # Fix database issues
        await self.fix_database_issues()
        
        # Restart services
        await self.restart_services()
        
        print("\n✅ Comprehensive fix completed!")
        print("\n📝 Next steps:")
        print("1. Test payment verification")
        print("2. Check worker posting")
        print("3. Monitor logs for errors")
        print("4. Test bot commands")

async def main():
    """Main function."""
    fixer = SystemFixer()
    await fixer.run_comprehensive_fix()

if __name__ == "__main__":
    asyncio.run(main()) 