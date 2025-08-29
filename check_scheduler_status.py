#!/usr/bin/env python3
"""
Scheduler Status Check
Check if the scheduler is running and posting as it should
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SchedulerStatusChecker:
    """Check scheduler status and posting functionality."""
    
    def __init__(self):
        self.test_results = {}
    
    async def run_comprehensive_check(self):
        """Run comprehensive scheduler status check."""
        print("📅 SCHEDULER STATUS CHECK")
        print("=" * 50)
        
        # Test 1: Check if scheduler process is running
        await self.check_scheduler_process()
        
        # Test 2: Check scheduler database and configuration
        await self.check_scheduler_config()
        
        # Test 3: Check worker status
        await self.check_worker_status()
        
        # Test 4: Check posting queue and active slots
        await self.check_posting_queue()
        
        # Test 5: Check recent posting activity
        await self.check_recent_posts()
        
        # Test 6: Check scheduler logs
        await self.check_scheduler_logs()
        
        # Generate report
        self.generate_status_report()
    
    async def check_scheduler_process(self):
        """Check if scheduler process is running."""
        print("\n1️⃣ Scheduler Process Check")
        print("-" * 40)
        
        try:
            import psutil
            
            # Look for scheduler processes
            scheduler_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if 'scheduler' in cmdline.lower() or 'scheduler' in proc.info['name'].lower():
                        scheduler_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if scheduler_processes:
                print(f"✅ Found {len(scheduler_processes)} scheduler process(es):")
                for proc in scheduler_processes:
                    print(f"  - PID: {proc['pid']}")
                    print(f"    Name: {proc['name']}")
                    print(f"    Command: {' '.join(proc['cmdline'][:3])}...")
                self.test_results['scheduler_process'] = True
            else:
                print("❌ No scheduler processes found")
                self.test_results['scheduler_process'] = False
                
        except Exception as e:
            print(f"❌ Error checking scheduler process: {e}")
            self.test_results['scheduler_process'] = False
    
    async def check_scheduler_config(self):
        """Check scheduler configuration and database."""
        print("\n2️⃣ Scheduler Configuration Check")
        print("-" * 40)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            print("✅ Database connected successfully")
            
            # Check scheduler tables
            tables_to_check = [
                'ad_slots',
                'destinations', 
                'users',
                'subscriptions',
                'workers'
            ]
            
            # Check tables using proper methods
            try:
                users = await db.get_all_users()
                print(f"✅ users: {len(users)} records")
            except Exception as e:
                print(f"❌ users: Error - {e}")
            
            try:
                ad_slots = await db.get_ad_slots()
                print(f"✅ ad_slots: {len(ad_slots)} records")
            except Exception as e:
                print(f"❌ ad_slots: Error - {e}")
            
            try:
                destinations = await db.get_destinations()
                print(f"✅ destinations: {len(destinations)} records")
            except Exception as e:
                print(f"❌ destinations: Error - {e}")
            
            try:
                subscriptions = await db.get_all_subscriptions()
                print(f"✅ subscriptions: {len(subscriptions)} records")
            except Exception as e:
                print(f"❌ subscriptions: Error - {e}")
            
            try:
                workers = await db.get_all_workers()
                print(f"✅ workers: {len(workers)} records")
            except Exception as e:
                print(f"❌ workers: Error - {e}")
            
            await db.close()
            self.test_results['scheduler_config'] = True
            
        except Exception as e:
            print(f"❌ Scheduler config check failed: {e}")
            self.test_results['scheduler_config'] = False
    
    async def check_worker_status(self):
        """Check worker status and availability."""
        print("\n3️⃣ Worker Status Check")
        print("-" * 40)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Check workers table
            try:
                workers = await db.get_all_workers()
                active_workers = [w for w in workers if w.get('status') == 'active']
                print(f"✅ Active workers: {len(active_workers)}")
                
                if active_workers:
                    print("📋 Active worker details:")
                    for worker in active_workers[:5]:  # Show first 5
                        print(f"  - Worker {worker.get('worker_id')}: {worker.get('status')} (last used: {worker.get('last_used')})")
                    
                    self.test_results['worker_status'] = True
                else:
                    print("⚠️ No active workers found")
                    self.test_results['worker_status'] = False
                    
            except Exception as e:
                print(f"❌ Error checking workers: {e}")
                self.test_results['worker_status'] = False
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Worker status check failed: {e}")
            self.test_results['worker_status'] = False
    
    async def check_posting_queue(self):
        """Check posting queue and active slots."""
        print("\n4️⃣ Posting Queue Check")
        print("-" * 40)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Check active ad slots
            try:
                ad_slots = await db.get_ad_slots()
                active_slots = [s for s in ad_slots if s.get('is_active')]
                print(f"✅ Active ad slots: {len(active_slots)}")
                
                if active_slots:
                    print("📋 Active slot details:")
                    for slot in active_slots[:3]:  # Show first 3
                        print(f"  - Slot {slot.get('id')} (User {slot.get('user_id')}):")
                        content = slot.get('content', '')
                        print(f"    Content: {content[:50]}..." if content else "    Content: None")
                        print(f"    Last posted: {slot.get('last_sent_at')}")
                        print()
                
                # Check destinations
                destinations = await db.get_destinations()
                active_destinations = [d for d in destinations if d.get('is_active')]
                print(f"✅ Active destinations: {len(active_destinations)}")
                
                self.test_results['posting_queue'] = len(active_slots) > 0
                
            except Exception as e:
                print(f"❌ Error checking posting queue: {e}")
                self.test_results['posting_queue'] = False
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Posting queue check failed: {e}")
            self.test_results['posting_queue'] = False
    
    async def check_recent_posts(self):
        """Check recent posting activity."""
        print("\n5️⃣ Recent Posting Activity Check")
        print("-" * 40)
        
        try:
            # Check scheduler log file
            log_file = "scheduler.log"
            if os.path.exists(log_file):
                # Get last 10 lines of scheduler log
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-10:] if len(lines) > 10 else lines
                
                print(f"✅ Scheduler log found: {len(lines)} total lines")
                print("📋 Recent scheduler activity:")
                
                posting_activity = []
                for line in recent_lines:
                    if 'posting' in line.lower() or 'posted' in line.lower() or 'scheduled' in line.lower():
                        posting_activity.append(line.strip())
                
                if posting_activity:
                    for activity in posting_activity[-5:]:  # Show last 5 posting activities
                        print(f"  - {activity}")
                    self.test_results['recent_posts'] = True
                else:
                    print("⚠️ No recent posting activity found in logs")
                    self.test_results['recent_posts'] = False
            else:
                print("❌ Scheduler log file not found")
                self.test_results['recent_posts'] = False
                
        except Exception as e:
            print(f"❌ Recent posts check failed: {e}")
            self.test_results['recent_posts'] = False
    
    async def check_scheduler_logs(self):
        """Check scheduler logs for errors."""
        print("\n6️⃣ Scheduler Logs Check")
        print("-" * 40)
        
        try:
            # Check for errors in scheduler log
            log_file = "scheduler.log"
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    content = f.read()
                
                # Count different log levels
                error_count = content.lower().count('error')
                warning_count = content.lower().count('warning')
                info_count = content.lower().count('info')
                
                print(f"📊 Log statistics:")
                print(f"  - Errors: {error_count}")
                print(f"  - Warnings: {warning_count}")
                print(f"  - Info messages: {info_count}")
                
                if error_count > 0:
                    print("⚠️ Errors found in scheduler logs")
                    # Show recent errors
                    lines = content.split('\n')
                    error_lines = [line for line in lines[-50:] if 'error' in line.lower()]
                    if error_lines:
                        print("📋 Recent errors:")
                        for error in error_lines[-3:]:
                            print(f"  - {error}")
                else:
                    print("✅ No errors found in scheduler logs")
                
                self.test_results['scheduler_logs'] = error_count == 0
            else:
                print("❌ Scheduler log file not found")
                self.test_results['scheduler_logs'] = False
                
        except Exception as e:
            print(f"❌ Scheduler logs check failed: {e}")
            self.test_results['scheduler_logs'] = False
    
    def generate_status_report(self):
        """Generate scheduler status report."""
        print("\n📊 SCHEDULER STATUS REPORT")
        print("=" * 50)
        
        # Count successful tests
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        
        # Detailed results
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        # Overall status
        if passed == total:
            print("\n🎉 SCHEDULER STATUS: FULLY OPERATIONAL")
            print("✅ Scheduler process running")
            print("✅ Configuration correct")
            print("✅ Workers available")
            print("✅ Posting queue active")
            print("✅ Recent posting activity")
            print("✅ No critical errors")
        elif passed >= total * 0.7:
            print("\n⚠️ SCHEDULER STATUS: PARTIALLY OPERATIONAL")
            print("Some components working, but issues detected")
        else:
            print("\n❌ SCHEDULER STATUS: ISSUES DETECTED")
            print("Multiple problems found - manual intervention required")
        
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        
        if not self.test_results.get('scheduler_process', False):
            print("- Start the scheduler process")
            print("- Check if scheduler is running in background")
        
        if not self.test_results.get('worker_status', False):
            print("- Check worker configuration")
            print("- Verify worker accounts are active")
        
        if not self.test_results.get('posting_queue', False):
            print("- Check if users have active subscriptions")
            print("- Verify ad slots are configured")
        
        if not self.test_results.get('recent_posts', False):
            print("- Check posting schedule")
            print("- Verify destinations are active")
        
        if not self.test_results.get('scheduler_logs', False):
            print("- Review scheduler logs for errors")
            print("- Fix any configuration issues")

async def main():
    """Main check function."""
    checker = SchedulerStatusChecker()
    await checker.run_comprehensive_check()

if __name__ == "__main__":
    asyncio.run(main())
