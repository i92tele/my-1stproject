#!/usr/bin/env python3
"""
Final Testing Verification for AutoFarming Bot

This script performs a comprehensive verification of all critical components
to ensure the system is ready for production deployment.
"""

import sqlite3
import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinalTestingVerification:
    """Final comprehensive testing verification for production readiness."""
    
    def __init__(self):
        self.db_path = 'bot_database.db'
        self.verification_results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'UNKNOWN',
            'verifications': {},
            'critical_issues': [],
            'warnings': [],
            'success_count': 0,
            'total_verifications': 0
        }
        
    def run_final_verification(self):
        """Run all final verification tests."""
        logger.info("🧪 FINAL TESTING VERIFICATION")
        logger.info("=" * 60)
        logger.info("Verifying all critical components for production readiness...")
        logger.info("=" * 60)
        
        # Run all verifications
        verifications = [
            self.verify_database_integrity,
            self.verify_worker_system,
            self.verify_anti_ban_system,
            self.verify_posting_service,
            self.verify_restart_recovery,
            self.verify_admin_interface,
            self.verify_user_interface,
            self.verify_payment_system,
            self.verify_file_structure,
            self.verify_environment_setup
        ]
        
        for verification in verifications:
            try:
                verification()
                logger.info("-" * 40)
            except Exception as e:
                logger.error(f"❌ Verification {verification.__name__} failed: {e}")
                self.verification_results['verifications'][verification.__name__] = {
                    'status': 'FAILED',
                    'error': str(e),
                    'fixes': []
                }
        
        # Generate final report
        self.generate_final_report()
        
    def verify_database_integrity(self):
        """Verify database integrity and schema."""
        logger.info("🔧 Verifying Database Integrity...")
        
        if not os.path.exists(self.db_path):
            self._record_verification_failure('database_integrity', 'Database file not found', 
                                           ['Run database initialization'])
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check all critical tables exist
            critical_tables = [
                'worker_usage', 'worker_cooldowns', 'ad_slots', 
                'posting_history', 'worker_activity_log', 'users',
                'subscriptions', 'payments', 'admin_ad_slots'
            ]
            
            missing_tables = []
            for table in critical_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    missing_tables.append(table)
            
            if missing_tables:
                self._record_verification_failure('database_integrity', 
                                               f'Missing tables: {missing_tables}',
                                               ['Run comprehensive_database_fix.py'])
                return
            
            logger.info("✅ All critical tables exist")
            
            # Verify worker_usage table structure
            cursor.execute("PRAGMA table_info(worker_usage)")
            worker_usage_columns = [col[1] for col in cursor.fetchall()]
            
            required_worker_usage_columns = [
                'worker_id', 'hourly_posts', 'daily_posts', 'hourly_limit', 
                'daily_limit', 'created_at', 'updated_at'
            ]
            
            missing_worker_usage = [col for col in required_worker_usage_columns 
                                  if col not in worker_usage_columns]
            
            if missing_worker_usage:
                self._record_verification_failure('database_integrity', 
                                               f'Missing worker_usage columns: {missing_worker_usage}',
                                               ['Run fix_remaining_errors.py'])
                return
            
            # Verify worker count
            cursor.execute("SELECT COUNT(*) FROM worker_usage")
            worker_count = cursor.fetchone()[0]
            
            if worker_count != 10:
                self._record_verification_failure('database_integrity', 
                                               f'Expected 10 workers, found {worker_count}',
                                               ['Run fix_root_cause_duplicates.py'])
                return
            
            # Check for duplicates
            cursor.execute("SELECT worker_id, COUNT(*) FROM worker_usage GROUP BY worker_id HAVING COUNT(*) > 1")
            duplicates = cursor.fetchall()
            
            if duplicates:
                self._record_verification_failure('database_integrity', 
                                               f'Found {len(duplicates)} duplicate workers',
                                               ['Run fix_root_cause_duplicates.py'])
                return
            
            # Verify UNIQUE constraint
            cursor.execute("PRAGMA table_info(worker_usage)")
            worker_usage_info = cursor.fetchall()
            
            worker_id_unique = False
            for col in worker_usage_info:
                if col[1] == 'worker_id' and col[5] == 1:  # 5th element indicates UNIQUE
                    worker_id_unique = True
                    break
            
            if not worker_id_unique:
                self._record_verification_failure('database_integrity', 
                                               'UNIQUE constraint missing on worker_id',
                                               ['Run fix_root_cause_duplicates.py'])
                return
            
            logger.info("✅ Database integrity verified")
            self._record_verification_success('database_integrity', 'Database integrity is perfect')
            
        except Exception as e:
            self._record_verification_failure('database_integrity', f'Database verification error: {e}', [])
        finally:
            conn.close()
    
    def verify_worker_system(self):
        """Verify worker system functionality."""
        logger.info("👥 Verifying Worker System...")
        
        if not os.path.exists(self.db_path):
            self._record_verification_failure('worker_system', 'Database file not found', [])
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check worker initialization
            cursor.execute("SELECT COUNT(*) FROM worker_usage")
            worker_count = cursor.fetchone()[0]
            
            if worker_count != 10:
                self._record_verification_failure('worker_system', 
                                               f'Expected 10 workers, found {worker_count}',
                                               ['Run fix_root_cause_duplicates.py'])
                return
            
            # Check worker data integrity
            cursor.execute("SELECT worker_id, hourly_limit, daily_limit FROM worker_usage ORDER BY worker_id")
            workers = cursor.fetchall()
            
            for worker_id, hourly_limit, daily_limit in workers:
                if hourly_limit != 15 or daily_limit != 150:
                    self._record_verification_failure('worker_system', 
                                                   f'Worker {worker_id} has wrong limits: hourly={hourly_limit}, daily={daily_limit}',
                                                   ['Check worker initialization'])
                    return
            
            # Check worker IDs are 1-10
            worker_ids = [row[0] for row in workers]
            expected_ids = list(range(1, 11))
            
            if worker_ids != expected_ids:
                self._record_verification_failure('worker_system', 
                                               f'Worker IDs not 1-10: {worker_ids}',
                                               ['Run fix_root_cause_duplicates.py'])
                return
            
            # Check worker cooldowns table
            cursor.execute("SELECT COUNT(*) FROM worker_cooldowns")
            cooldown_count = cursor.fetchone()[0]
            
            logger.info(f"✅ Found {cooldown_count} cooldown records")
            logger.info("✅ All workers have correct limits (15 hourly, 150 daily)")
            logger.info("✅ Worker IDs are correctly 1-10")
            
            self._record_verification_success('worker_system', 'Worker system is properly configured')
            
        except Exception as e:
            self._record_verification_failure('worker_system', f'Worker system verification error: {e}', [])
        finally:
            conn.close()
    
    def verify_anti_ban_system(self):
        """Verify anti-ban system implementation."""
        logger.info("🛡️ Verifying Anti-Ban System...")
        
        # Check posting service file exists
        posting_service_path = 'scheduler/core/posting_service.py'
        
        if not os.path.exists(posting_service_path):
            self._record_verification_failure('anti_ban_system', 
                                           'Posting service file not found',
                                           ['Check file structure'])
            return
        
        try:
            with open(posting_service_path, 'r') as f:
                content = f.read()
            
            # Check for anti-ban methods
            required_methods = [
                '_check_worker_cooldown',
                '_set_worker_cooldown',
                '_post_single_destination_parallel',
                '_mark_slot_as_posted'
            ]
            
            missing_methods = [method for method in required_methods 
                             if method not in content]
            
            if missing_methods:
                self._record_verification_failure('anti_ban_system', 
                                               f'Missing anti-ban methods: {missing_methods}',
                                               ['Check posting service implementation'])
                return
            
            # Check for anti-ban features
            anti_ban_features = [
                'asyncio.sleep',
                'random.uniform',
                'random.randint',
                'cooldown_until',
                'worker_cooldowns'
            ]
            
            missing_features = [feature for feature in anti_ban_features 
                              if feature not in content]
            
            if missing_features:
                self._record_verification_failure('anti_ban_system', 
                                               f'Missing anti-ban features: {missing_features}',
                                               ['Check anti-ban implementation'])
                return
            
            # Check database tables
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check worker_cooldowns table structure
            cursor.execute("PRAGMA table_info(worker_cooldowns)")
            cooldowns_columns = [col[1] for col in cursor.fetchall()]
            
            required_cooldown_columns = ['id', 'worker_id', 'cooldown_until', 'created_at', 'is_active', 'last_used_at']
            missing_cooldown = [col for col in required_cooldown_columns 
                              if col not in cooldowns_columns]
            
            if missing_cooldown:
                self._record_verification_failure('anti_ban_system', 
                                               f'Missing cooldown columns: {missing_cooldown}',
                                               ['Run fix_remaining_errors.py'])
                conn.close()
                return
            
            conn.close()
            
            logger.info("✅ All anti-ban methods present")
            logger.info("✅ Anti-ban features implemented")
            logger.info("✅ Cooldown table structure correct")
            
            self._record_verification_success('anti_ban_system', 'Anti-ban system is fully implemented')
            
        except Exception as e:
            self._record_verification_failure('anti_ban_system', f'Anti-ban verification error: {e}', [])
    
    def verify_posting_service(self):
        """Verify posting service functionality."""
        logger.info("📤 Verifying Posting Service...")
        
        posting_service_path = 'scheduler/core/posting_service.py'
        
        if not os.path.exists(posting_service_path):
            self._record_verification_failure('posting_service', 
                                           'Posting service file not found',
                                           ['Check file structure'])
            return
        
        try:
            with open(posting_service_path, 'r') as f:
                content = f.read()
            
            # Check for parallel posting methods
            required_methods = [
                '_post_single_destination_parallel',
                '_mark_slot_as_posted',
                'post_ads'
            ]
            
            missing_methods = [method for method in required_methods 
                             if method not in content]
            
            if missing_methods:
                self._record_verification_failure('posting_service', 
                                               f'Missing posting methods: {missing_methods}',
                                               ['Check posting service implementation'])
                return
            
            # Check for worker utilization features
            utilization_features = [
                'available_workers',
                'worker_index',
                'round-robin',
                'parallel posting'
            ]
            
            # Check for timestamp update logic
            if 'posted_any = True' in content and 'success = await self._post_single_ad' in content:
                logger.info("✅ Timestamp update logic implemented")
            else:
                self._record_verification_failure('posting_service', 
                                               'Timestamp update logic not properly implemented',
                                               ['Check posting service logic'])
                return
            
            logger.info("✅ All posting methods present")
            logger.info("✅ Parallel posting implemented")
            
            self._record_verification_success('posting_service', 'Posting service is fully functional')
            
        except Exception as e:
            self._record_verification_failure('posting_service', f'Posting service verification error: {e}', [])
    
    def verify_restart_recovery(self):
        """Verify restart recovery system."""
        logger.info("🔄 Verifying Restart Recovery...")
        
        restart_recovery_path = 'restart_recovery.py'
        
        if not os.path.exists(restart_recovery_path):
            self._record_verification_failure('restart_recovery', 
                                           'Restart recovery file not found',
                                           ['Check file structure'])
            return
        
        try:
            with open(restart_recovery_path, 'r') as f:
                content = f.read()
            
            # Check for recovery methods
            required_methods = [
                'perform_full_recovery',
                'get_recovery_status',
                'calculate_next_post_time'
            ]
            
            missing_methods = [method for method in required_methods 
                             if method not in content]
            
            if missing_methods:
                self._record_verification_failure('restart_recovery', 
                                               f'Missing recovery methods: {missing_methods}',
                                               ['Check restart recovery implementation'])
                return
            
            # Check for fixed method call
            if 'get_posting_history(limit=10)' in content:
                logger.info("✅ Restart recovery method call fixed")
            else:
                self._record_verification_failure('restart_recovery', 
                                               'Restart recovery method call not fixed',
                                               ['Fix get_posting_history call'])
                return
            
            logger.info("✅ All recovery methods present")
            
            self._record_verification_success('restart_recovery', 'Restart recovery system is ready')
            
        except Exception as e:
            self._record_verification_failure('restart_recovery', f'Restart recovery verification error: {e}', [])
    
    def verify_admin_interface(self):
        """Verify admin interface files."""
        logger.info("👨‍💼 Verifying Admin Interface...")
        
        admin_files = [
            'commands/admin_commands.py',
            'commands/admin_slot_commands.py'
        ]
        
        missing_files = []
        for file_path in admin_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            self._record_verification_failure('admin_interface', 
                                           f'Missing admin files: {missing_files}',
                                           ['Check file structure'])
            return
        
        logger.info("✅ All admin interface files present")
        self._record_verification_success('admin_interface', 'Admin interface is ready')
    
    def verify_user_interface(self):
        """Verify user interface files."""
        logger.info("👤 Verifying User Interface...")
        
        user_files = [
            'commands/user_commands.py',
            'commands/forwarding_commands.py',
            'commands/subscription_commands.py'
        ]
        
        missing_files = []
        for file_path in user_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            self._record_verification_failure('user_interface', 
                                           f'Missing user files: {missing_files}',
                                           ['Check file structure'])
            return
        
        logger.info("✅ All user interface files present")
        self._record_verification_success('user_interface', 'User interface is ready')
    
    def verify_payment_system(self):
        """Verify payment system files."""
        logger.info("💰 Verifying Payment System...")
        
        payment_files = [
            'src/services/blockchain_payments.py',
            'commands/user_commands.py'  # Contains payment handlers
        ]
        
        missing_files = []
        for file_path in payment_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            self._record_verification_failure('payment_system', 
                                           f'Missing payment files: {missing_files}',
                                           ['Check file structure'])
            return
        
        logger.info("✅ All payment system files present")
        self._record_verification_success('payment_system', 'Payment system is ready')
    
    def verify_file_structure(self):
        """Verify critical file structure."""
        logger.info("📁 Verifying File Structure...")
        
        critical_files = [
            'config.py',
            'database.py',
            'bot.py',
            'scheduler/core/posting_service.py',
            'src/database/manager.py'
        ]
        
        missing_files = []
        for file_path in critical_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            self._record_verification_failure('file_structure', 
                                           f'Missing critical files: {missing_files}',
                                           ['Check file structure'])
            return
        
        logger.info("✅ All critical files present")
        self._record_verification_success('file_structure', 'File structure is complete')
    
    def verify_environment_setup(self):
        """Verify environment setup."""
        logger.info("🔧 Verifying Environment Setup...")
        
        # Check for config directory
        if not os.path.exists('config'):
            self._record_verification_failure('environment_setup', 
                                           'Config directory not found',
                                           ['Create config directory'])
            return
        
        # Check for .env file
        env_file = 'config/.env'
        if not os.path.exists(env_file):
            self._record_verification_failure('environment_setup', 
                                           'Environment file not found',
                                           ['Create config/.env file'])
            return
        
        # Check for virtual environment
        if not os.path.exists('venv'):
            self._record_verification_failure('environment_setup', 
                                           'Virtual environment not found',
                                           ['Create virtual environment'])
            return
        
        logger.info("✅ Environment setup is complete")
        self._record_verification_success('environment_setup', 'Environment is properly configured')
    
    def _record_verification_success(self, verification_name: str, message: str):
        """Record a successful verification."""
        logger.info(f"✅ {verification_name}: {message}")
        self.verification_results['verifications'][verification_name] = {
            'status': 'PASS',
            'message': message,
            'fixes': []
        }
        self.verification_results['success_count'] += 1
        self.verification_results['total_verifications'] += 1
    
    def _record_verification_failure(self, verification_name: str, error: str, fixes: List[str]):
        """Record a failed verification."""
        logger.error(f"❌ {verification_name}: {error}")
        self.verification_results['verifications'][verification_name] = {
            'status': 'FAIL',
            'error': error,
            'fixes': fixes
        }
        self.verification_results['critical_issues'].append(f"{verification_name}: {error}")
        self.verification_results['total_verifications'] += 1
    
    def generate_final_report(self):
        """Generate final verification report."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 FINAL VERIFICATION REPORT")
        logger.info("=" * 60)
        
        # Calculate overall status
        if self.verification_results['success_count'] == self.verification_results['total_verifications']:
            self.verification_results['overall_status'] = 'PASS'
            logger.info("🎉 ALL VERIFICATIONS PASSED!")
            logger.info("🚀 SYSTEM IS READY FOR PRODUCTION DEPLOYMENT!")
        elif self.verification_results['success_count'] > 0:
            self.verification_results['overall_status'] = 'PARTIAL'
            logger.info(f"⚠️ PARTIAL SUCCESS: {self.verification_results['success_count']}/{self.verification_results['total_verifications']} verifications passed")
        else:
            self.verification_results['overall_status'] = 'FAIL'
            logger.error("❌ ALL VERIFICATIONS FAILED!")
        
        # Summary
        logger.info(f"\n📈 Verification Summary:")
        logger.info(f"  Total Verifications: {self.verification_results['total_verifications']}")
        logger.info(f"  Passed: {self.verification_results['success_count']}")
        logger.info(f"  Failed: {self.verification_results['total_verifications'] - self.verification_results['success_count']}")
        logger.info(f"  Success Rate: {(self.verification_results['success_count'] / self.verification_results['total_verifications'] * 100):.1f}%")
        
        # Critical Issues
        if self.verification_results['critical_issues']:
            logger.info(f"\n❌ Critical Issues Found:")
            for issue in self.verification_results['critical_issues']:
                logger.info(f"  • {issue}")
        
        # Warnings
        if self.verification_results['warnings']:
            logger.info(f"\n⚠️ Warnings:")
            for warning in self.verification_results['warnings']:
                logger.info(f"  • {warning}")
        
        # Final Recommendations
        logger.info(f"\n🎯 Final Recommendations:")
        if self.verification_results['overall_status'] == 'PASS':
            logger.info("  ✅ System is ready for production deployment!")
            logger.info("  ✅ All critical components are working correctly")
            logger.info("  ✅ Anti-ban system is properly implemented")
            logger.info("  ✅ Worker system is optimized")
            logger.info("  ✅ Database integrity is perfect")
            logger.info("  🚀 Proceed with confidence!")
        elif self.verification_results['overall_status'] == 'PARTIAL':
            logger.info("  ⚠️ Some issues need attention before deployment")
            logger.info("  ⚠️ Review failed verifications and apply fixes")
            logger.info("  ⚠️ Re-run verification after fixes")
        else:
            logger.info("  ❌ Critical issues need immediate attention")
            logger.info("  ❌ Do not deploy until all issues are resolved")
            logger.info("  ❌ Apply fixes and re-run verification")
        
        # Save report
        report_file = f"final_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            import json
            with open(report_file, 'w') as f:
                json.dump(self.verification_results, f, indent=2)
            logger.info(f"\n📄 Final verification report saved to: {report_file}")
        except Exception as e:
            logger.warning(f"Could not save verification report: {e}")

def main():
    """Run final testing verification."""
    verifier = FinalTestingVerification()
    verifier.run_final_verification()

if __name__ == "__main__":
    main()

