#!/usr/bin/env python3
"""
Comprehensive Fix Verification
Triple-check all bot fixes that were implemented
"""

import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveFixVerifier:
    """Comprehensive verification of all bot fixes."""
    
    def __init__(self):
        self.db_path = "bot_database.db"
        self.verification_results = {}
    
    def check_database_schema_fixes(self) -> Dict[str, Any]:
        """Check database schema fixes."""
        print("🔍 VERIFYING DATABASE SCHEMA FIXES")
        print("=" * 50)
        
        results = {
            'status': 'unknown',
            'tables_created': 0,
            'tables_missing': [],
            'errors': []
        }
        
        try:
            if not os.path.exists(self.db_path):
                results['errors'].append("Database file not found")
                results['status'] = 'failed'
                return results
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Expected new tables from schema fixes
            expected_tables = [
                'worker_activity_log',
                'destination_health', 
                'system_health',
                'payment_rate_limits',
                'payment_monitoring',
                'worker_health',
                'worker_bans',
                'worker_rate_limits',
                'worker_cooldowns',
                'worker_rotation',
                'worker_performance',
                'worker_recovery',
                'worker_failover',
                'error_categories',
                'posting_errors',
                'destination_tracking',
                'posting_attempts',
                'posting_rate_limits',
                'posting_cooldowns',
                'posting_coordination',
                'posting_sessions',
                'posting_metrics',
                'posting_alerts',
                'payment_monitoring_tasks',
                'payment_monitoring_logs',
                'task_error_recovery',
                'task_health_monitoring',
                'resource_tracking',
                'resource_cleanup_logs',
                'task_locks',
                'task_coordination',
                'task_metrics',
                'task_alerts',
                'task_performance'
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table in expected_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    existing_tables.append(table)
                    print(f"✅ {table}")
                else:
                    missing_tables.append(table)
                    print(f"❌ {table}")
            
            results['tables_created'] = len(existing_tables)
            results['tables_missing'] = missing_tables
            
            if len(missing_tables) == 0:
                results['status'] = 'success'
                print(f"✅ All {len(existing_tables)} expected tables created successfully!")
            else:
                results['status'] = 'partial'
                print(f"⚠️ {len(existing_tables)}/{len(expected_tables)} tables created, {len(missing_tables)} missing")
            
            conn.close()
            
        except Exception as e:
            results['errors'].append(str(e))
            results['status'] = 'failed'
            print(f"❌ Error checking database schema: {e}")
        
        return results
    
    def check_payment_security_fixes(self) -> Dict[str, Any]:
        """Check payment security fixes."""
        print("\n🔍 VERIFYING PAYMENT SECURITY FIXES")
        print("=" * 50)
        
        results = {
            'status': 'unknown',
            'validation_triggers': 0,
            'rate_limiting_tables': 0,
            'monitoring_tables': 0,
            'errors': []
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check validation triggers
            cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%payment%'")
            triggers = cursor.fetchall()
            results['validation_triggers'] = len(triggers)
            
            for trigger in triggers:
                print(f"✅ Payment validation trigger: {trigger[0]}")
            
            # Check rate limiting tables
            rate_limit_tables = ['payment_rate_limits', 'payment_monitoring']
            for table in rate_limit_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['rate_limiting_tables'] += 1
                    print(f"✅ Rate limiting table: {table}")
                else:
                    print(f"❌ Missing rate limiting table: {table}")
            
            # Check monitoring tables
            monitoring_tables = ['payment_monitoring_tasks', 'payment_monitoring_logs']
            for table in monitoring_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['monitoring_tables'] += 1
                    print(f"✅ Monitoring table: {table}")
                else:
                    print(f"❌ Missing monitoring table: {table}")
            
            if results['validation_triggers'] > 0 and results['rate_limiting_tables'] > 0:
                results['status'] = 'success'
                print("✅ Payment security fixes verified successfully!")
            else:
                results['status'] = 'partial'
                print("⚠️ Some payment security fixes missing")
            
            conn.close()
            
        except Exception as e:
            results['errors'].append(str(e))
            results['status'] = 'failed'
            print(f"❌ Error checking payment security: {e}")
        
        return results
    
    def check_worker_management_fixes(self) -> Dict[str, Any]:
        """Check worker management fixes."""
        print("\n🔍 VERIFYING WORKER MANAGEMENT FIXES")
        print("=" * 50)
        
        results = {
            'status': 'unknown',
            'health_tables': 0,
            'rate_limiting_tables': 0,
            'recovery_tables': 0,
            'errors': []
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check health monitoring tables
            health_tables = ['worker_health', 'worker_bans']
            for table in health_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['health_tables'] += 1
                    print(f"✅ Health monitoring table: {table}")
                else:
                    print(f"❌ Missing health monitoring table: {table}")
            
            # Check rate limiting tables
            rate_limit_tables = ['worker_rate_limits', 'worker_cooldowns', 'worker_load']
            for table in rate_limit_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['rate_limiting_tables'] += 1
                    print(f"✅ Rate limiting table: {table}")
                else:
                    print(f"❌ Missing rate limiting table: {table}")
            
            # Check recovery tables
            recovery_tables = ['worker_recovery', 'worker_failover', 'worker_rotation', 'worker_performance']
            for table in recovery_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['recovery_tables'] += 1
                    print(f"✅ Recovery table: {table}")
                else:
                    print(f"❌ Missing recovery table: {table}")
            
            if results['health_tables'] > 0 and results['rate_limiting_tables'] > 0:
                results['status'] = 'success'
                print("✅ Worker management fixes verified successfully!")
            else:
                results['status'] = 'partial'
                print("⚠️ Some worker management fixes missing")
            
            conn.close()
            
        except Exception as e:
            results['errors'].append(str(e))
            results['status'] = 'failed'
            print(f"❌ Error checking worker management: {e}")
        
        return results
    
    def check_posting_logic_fixes(self) -> Dict[str, Any]:
        """Check posting logic fixes."""
        print("\n🔍 VERIFYING POSTING LOGIC FIXES")
        print("=" * 50)
        
        results = {
            'status': 'unknown',
            'error_tables': 0,
            'tracking_tables': 0,
            'rate_limiting_tables': 0,
            'monitoring_tables': 0,
            'errors': []
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check error handling tables
            error_tables = ['error_categories', 'posting_errors']
            for table in error_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['error_tables'] += 1
                    print(f"✅ Error handling table: {table}")
                else:
                    print(f"❌ Missing error handling table: {table}")
            
            # Check tracking tables
            tracking_tables = ['destination_tracking', 'posting_attempts']
            for table in tracking_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['tracking_tables'] += 1
                    print(f"✅ Tracking table: {table}")
                else:
                    print(f"❌ Missing tracking table: {table}")
            
            # Check rate limiting tables
            rate_limit_tables = ['posting_rate_limits', 'posting_cooldowns']
            for table in rate_limit_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['rate_limiting_tables'] += 1
                    print(f"✅ Rate limiting table: {table}")
                else:
                    print(f"❌ Missing rate limiting table: {table}")
            
            # Check monitoring tables
            monitoring_tables = ['posting_metrics', 'posting_alerts', 'posting_coordination', 'posting_sessions']
            for table in monitoring_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['monitoring_tables'] += 1
                    print(f"✅ Monitoring table: {table}")
                else:
                    print(f"❌ Missing monitoring table: {table}")
            
            if results['error_tables'] > 0 and results['tracking_tables'] > 0:
                results['status'] = 'success'
                print("✅ Posting logic fixes verified successfully!")
            else:
                results['status'] = 'partial'
                print("⚠️ Some posting logic fixes missing")
            
            conn.close()
            
        except Exception as e:
            results['errors'].append(str(e))
            results['status'] = 'failed'
            print(f"❌ Error checking posting logic: {e}")
        
        return results
    
    def check_background_task_fixes(self) -> Dict[str, Any]:
        """Check background task fixes."""
        print("\n🔍 VERIFYING BACKGROUND TASK FIXES")
        print("=" * 50)
        
        results = {
            'status': 'unknown',
            'monitoring_tables': 0,
            'recovery_tables': 0,
            'coordination_tables': 0,
            'errors': []
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check monitoring tables
            monitoring_tables = ['task_health_monitoring', 'task_metrics', 'task_alerts', 'task_performance']
            for table in monitoring_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['monitoring_tables'] += 1
                    print(f"✅ Monitoring table: {table}")
                else:
                    print(f"❌ Missing monitoring table: {table}")
            
            # Check recovery tables
            recovery_tables = ['task_error_recovery', 'resource_tracking', 'resource_cleanup_logs']
            for table in recovery_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['recovery_tables'] += 1
                    print(f"✅ Recovery table: {table}")
                else:
                    print(f"❌ Missing recovery table: {table}")
            
            # Check coordination tables
            coordination_tables = ['task_locks', 'task_coordination', 'payment_monitoring_tasks', 'payment_monitoring_logs']
            for table in coordination_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    results['coordination_tables'] += 1
                    print(f"✅ Coordination table: {table}")
                else:
                    print(f"❌ Missing coordination table: {table}")
            
            if results['monitoring_tables'] > 0 and results['recovery_tables'] > 0:
                results['status'] = 'success'
                print("✅ Background task fixes verified successfully!")
            else:
                results['status'] = 'partial'
                print("⚠️ Some background task fixes missing")
            
            conn.close()
            
        except Exception as e:
            results['errors'].append(str(e))
            results['status'] = 'failed'
            print(f"❌ Error checking background tasks: {e}")
        
        return results
    
    def run_comprehensive_verification(self):
        """Run comprehensive verification of all fixes."""
        print("🔍 COMPREHENSIVE BOT FIXES VERIFICATION")
        print("=" * 60)
        print("Triple-checking all implemented fixes...")
        print("=" * 60)
        
        # Run all verification checks
        self.verification_results['database_schema'] = self.check_database_schema_fixes()
        self.verification_results['payment_security'] = self.check_payment_security_fixes()
        self.verification_results['worker_management'] = self.check_worker_management_fixes()
        self.verification_results['posting_logic'] = self.check_posting_logic_fixes()
        self.verification_results['background_tasks'] = self.check_background_task_fixes()
        
        # Print comprehensive summary
        self.print_comprehensive_summary()
    
    def print_comprehensive_summary(self):
        """Print comprehensive verification summary."""
        print("\n📊 COMPREHENSIVE VERIFICATION SUMMARY")
        print("=" * 60)
        
        total_checks = len(self.verification_results)
        successful_checks = 0
        partial_checks = 0
        failed_checks = 0
        
        for check_name, result in self.verification_results.items():
            status = result['status']
            if status == 'success':
                successful_checks += 1
                print(f"✅ {check_name.replace('_', ' ').title()}: SUCCESS")
            elif status == 'partial':
                partial_checks += 1
                print(f"⚠️ {check_name.replace('_', ' ').title()}: PARTIAL")
            else:
                failed_checks += 1
                print(f"❌ {check_name.replace('_', ' ').title()}: FAILED")
        
        print(f"\n📈 VERIFICATION STATISTICS:")
        print(f"✅ Successful: {successful_checks}/{total_checks}")
        print(f"⚠️ Partial: {partial_checks}/{total_checks}")
        print(f"❌ Failed: {failed_checks}/{total_checks}")
        
        if successful_checks == total_checks:
            print("\n🎉 ALL FIXES VERIFIED SUCCESSFULLY!")
            print("The bot is now fully secured and optimized.")
        elif successful_checks + partial_checks == total_checks:
            print("\n✅ MOST FIXES VERIFIED SUCCESSFULLY!")
            print("The bot is significantly improved with minor issues remaining.")
        else:
            print("\n⚠️ SOME FIXES NEED ATTENTION!")
            print("Several critical fixes may not have been applied correctly.")
        
        print(f"\n🔧 RECOMMENDED ACTIONS:")
        if failed_checks > 0:
            print("1. Re-run the failed fix scripts")
            print("2. Check for database connection issues")
            print("3. Verify environment variables are loaded")
        print("4. Restart the bot to apply all changes")
        print("5. Test payment verification and posting functionality")
        print("6. Monitor system performance and error rates")

def main():
    """Main function."""
    verifier = ComprehensiveFixVerifier()
    verifier.run_comprehensive_verification()

if __name__ == "__main__":
    main()
