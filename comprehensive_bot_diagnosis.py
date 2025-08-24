#!/usr/bin/env python3
"""
Comprehensive Bot Diagnosis
Checks all systems and identifies issues
"""

import asyncio
import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv('config/.env')

class ComprehensiveBotDiagnosis:
    def __init__(self):
        self.db_path = 'bot_database.db'
        self.issues = []
        self.warnings = []
        self.successes = []
    
    def log_issue(self, category: str, issue: str):
        """Log an issue."""
        self.issues.append(f"[{category}] {issue}")
        logger.error(f"❌ {category}: {issue}")
    
    def log_warning(self, category: str, warning: str):
        """Log a warning."""
        self.warnings.append(f"[{category}] {warning}")
        logger.warning(f"⚠️ {category}: {warning}")
    
    def log_success(self, category: str, success: str):
        """Log a success."""
        self.successes.append(f"[{category}] {success}")
        logger.info(f"✅ {category}: {success}")
    
    def check_environment(self):
        """Check environment variables and configuration."""
        print("\n🔧 ENVIRONMENT CHECK:")
        print("=" * 50)
        
        required_vars = [
            'BOT_TOKEN', 'EXODUS_MASTER_SEED', 'TON_ADDRESS',
            'WORKER_1_API_ID', 'WORKER_1_API_HASH', 'WORKER_1_PHONE'
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                if var == 'BOT_TOKEN':
                    self.log_success("ENV", f"{var}: {'*' * 10}...{value[-4:]}")
                elif var == 'EXODUS_MASTER_SEED':
                    words = value.split()
                    self.log_success("ENV", f"{var}: {len(words)} words")
                else:
                    self.log_success("ENV", f"{var}: Configured")
            else:
                self.log_issue("ENV", f"{var}: Missing")
        
        # Check worker configuration
        worker_count = 0
        for i in range(1, 11):
            api_id = os.getenv(f'WORKER_{i}_API_ID')
            api_hash = os.getenv(f'WORKER_{i}_API_HASH')
            phone = os.getenv(f'WORKER_{i}_PHONE')
            if api_id and api_hash and phone:
                worker_count += 1
                self.log_success("WORKERS", f"Worker {i}: {phone}")
            else:
                self.log_warning("WORKERS", f"Worker {i}: Incomplete configuration")
        
        self.log_success("WORKERS", f"Total configured: {worker_count}/10")
    
    def check_database(self):
        """Check database structure and data."""
        print("\n🗄️ DATABASE CHECK:")
        print("=" * 50)
        
        if not os.path.exists(self.db_path):
            self.log_issue("DB", "Database file not found")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = [
                'users', 'ad_slots', 'payments', 'workers', 
                'worker_usage', 'worker_health', 'failed_group_joins'
            ]
            
            for table in required_tables:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    self.log_success("DB", f"Table {table}: {count} records")
                else:
                    self.log_issue("DB", f"Table {table}: Missing")
            
            # Check recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM ad_slots 
                WHERE last_sent > datetime('now', '-24 hours')
            """)
            recent_ads = cursor.fetchone()[0]
            self.log_success("DB", f"Recent ad activity: {recent_ads} slots in 24h")
            
            # Check pending payments
            cursor.execute("""
                SELECT COUNT(*) FROM payments 
                WHERE status = 'pending'
            """)
            pending_payments = cursor.fetchone()[0]
            if pending_payments > 0:
                self.log_warning("DB", f"Pending payments: {pending_payments}")
            else:
                self.log_success("DB", "No pending payments")
            
            conn.close()
            
        except Exception as e:
            self.log_issue("DB", f"Database error: {e}")
    
    def check_scheduler_status(self):
        """Check if scheduler is running."""
        print("\n⏰ SCHEDULER CHECK:")
        print("=" * 50)
        
        try:
            import psutil
            scheduler_found = False
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'python3' in cmdline and 'scheduler' in cmdline:
                        scheduler_found = True
                        self.log_success("SCHEDULER", f"Running (PID: {proc.info['pid']})")
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not scheduler_found:
                self.log_issue("SCHEDULER", "Not running")
            
        except ImportError:
            self.log_warning("SCHEDULER", "psutil not available - cannot check process")
        except Exception as e:
            self.log_issue("SCHEDULER", f"Error checking scheduler: {e}")
    
    def check_worker_sessions(self):
        """Check worker session files."""
        print("\n🤖 WORKER SESSIONS CHECK:")
        print("=" * 50)
        
        sessions_dir = 'sessions'
        if not os.path.exists(sessions_dir):
            self.log_issue("SESSIONS", "Sessions directory not found")
            return
        
        session_files = [f for f in os.listdir(sessions_dir) if f.endswith('.session')]
        
        for i in range(1, 11):
            session_file = f'worker_{i}.session'
            if session_file in session_files:
                file_path = os.path.join(sessions_dir, session_file)
                file_size = os.path.getsize(file_path)
                if file_size > 0:
                    self.log_success("SESSIONS", f"Worker {i}: Session file exists ({file_size} bytes)")
                else:
                    self.log_warning("SESSIONS", f"Worker {i}: Empty session file")
            else:
                self.log_warning("SESSIONS", f"Worker {i}: No session file")
        
        self.log_success("SESSIONS", f"Total session files: {len(session_files)}")
    
    def check_ad_slots_status(self):
        """Check ad slots status."""
        print("\n📢 AD SLOTS CHECK:")
        print("=" * 50)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check active ad slots
            cursor.execute("""
                SELECT slot_id, user_id, is_active, last_sent, interval_minutes,
                       CASE 
                           WHEN last_sent IS NULL THEN 'Never sent'
                           WHEN datetime(last_sent, '+' || interval_minutes || ' minutes') <= datetime('now') 
                           THEN 'Due'
                           ELSE 'Not due'
                       END as status
                FROM ad_slots 
                WHERE is_active = 1
                ORDER BY slot_id
            """)
            
            active_slots = cursor.fetchall()
            
            if not active_slots:
                self.log_warning("AD_SLOTS", "No active ad slots")
            else:
                for slot in active_slots:
                    slot_id, user_id, is_active, last_sent, interval, status = slot
                    if status == 'Due':
                        self.log_warning("AD_SLOTS", f"Slot {slot_id}: Due for posting")
                    else:
                        self.log_success("AD_SLOTS", f"Slot {slot_id}: {status}")
            
            # Check paused slots
            cursor.execute("""
                SELECT slot_id, user_id, pause_reason 
                FROM ad_slots 
                WHERE is_paused = 1
            """)
            
            paused_slots = cursor.fetchall()
            for slot in paused_slots:
                slot_id, user_id, reason = slot
                self.log_warning("AD_SLOTS", f"Slot {slot_id}: Paused - {reason}")
            
            conn.close()
            
        except Exception as e:
            self.log_issue("AD_SLOTS", f"Error checking ad slots: {e}")
    
    def check_payment_system(self):
        """Check payment system status."""
        print("\n💰 PAYMENT SYSTEM CHECK:")
        print("=" * 50)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check recent payments
            cursor.execute("""
                SELECT crypto_type, status, COUNT(*) 
                FROM payments 
                WHERE created_at > datetime('now', '-7 days')
                GROUP BY crypto_type, status
            """)
            
            recent_payments = cursor.fetchall()
            for crypto, status, count in recent_payments:
                if status == 'completed':
                    self.log_success("PAYMENTS", f"{crypto}: {count} completed")
                elif status == 'pending':
                    self.log_warning("PAYMENTS", f"{crypto}: {count} pending")
                else:
                    self.log_issue("PAYMENTS", f"{crypto}: {count} {status}")
            
            # Check payment verification
            cursor.execute("""
                SELECT COUNT(*) FROM payments 
                WHERE status = 'pending' 
                AND created_at < datetime('now', '-1 hour')
            """)
            
            old_pending = cursor.fetchone()[0]
            if old_pending > 0:
                self.log_warning("PAYMENTS", f"{old_pending} payments pending for >1 hour")
            
            conn.close()
            
        except Exception as e:
            self.log_issue("PAYMENTS", f"Error checking payments: {e}")
    
    def check_failed_groups(self):
        """Check failed group joins."""
        print("\n🚫 FAILED GROUPS CHECK:")
        print("=" * 50)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT group_username, fail_reason, fail_count, last_attempt
                FROM failed_group_joins 
                ORDER BY fail_count DESC
            """)
            
            failed_groups = cursor.fetchall()
            
            if not failed_groups:
                self.log_success("FAILED_GROUPS", "No failed group joins")
            else:
                for group, reason, count, last_attempt in failed_groups:
                    self.log_warning("FAILED_GROUPS", f"{group}: {reason} ({count} attempts)")
            
            conn.close()
            
        except Exception as e:
            self.log_issue("FAILED_GROUPS", f"Error checking failed groups: {e}")
    
    def generate_summary(self):
        """Generate diagnosis summary."""
        print("\n📊 DIAGNOSIS SUMMARY:")
        print("=" * 50)
        
        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        total_successes = len(self.successes)
        
        print(f"✅ Successes: {total_successes}")
        print(f"⚠️ Warnings: {total_warnings}")
        print(f"❌ Issues: {total_issues}")
        
        if total_issues == 0:
            print("\n🎉 Bot appears to be healthy!")
        else:
            print(f"\n🔧 Issues to address:")
            for issue in self.issues:
                print(f"  • {issue}")
        
        if total_warnings > 0:
            print(f"\n⚠️ Warnings to monitor:")
            for warning in self.warnings:
                print(f"  • {warning}")
    
    def run_full_diagnosis(self):
        """Run complete diagnosis."""
        print("🔍 COMPREHENSIVE BOT DIAGNOSIS")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.check_environment()
        self.check_database()
        self.check_scheduler_status()
        self.check_worker_sessions()
        self.check_ad_slots_status()
        self.check_payment_system()
        self.check_failed_groups()
        self.generate_summary()

def main():
    """Main diagnosis function."""
    diagnosis = ComprehensiveBotDiagnosis()
    diagnosis.run_full_diagnosis()

if __name__ == "__main__":
    main()
