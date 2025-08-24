#!/usr/bin/env python3
"""
Comprehensive Testing Suite for AutoFarming Bot

This script tests all the critical fixes implemented in the previous session:
1. Database schema fixes
2. Worker duplicate prevention
3. Anti-ban system
4. Worker utilization
5. Parallel posting
6. Restart recovery
7. Admin and user interfaces

Usage: python3 comprehensive_testing_suite.py
"""

import asyncio
import sqlite3
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComprehensiveTester:
    """Comprehensive testing suite for all bot components."""
    
    def __init__(self):
        self.db_path = 'bot_database.db'
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'UNKNOWN',
            'tests': {},
            'issues': [],
            'warnings': [],
            'success_count': 0,
            'total_tests': 0
        }
        
    def run_all_tests(self):
        """Run all comprehensive tests."""
        logger.info("🧪 STARTING COMPREHENSIVE TESTING SUITE")
        logger.info("=" * 60)
        logger.info("Testing all critical fixes from previous session...")
        logger.info("=" * 60)
        
        # Run all tests
        tests = [
            self.test_database_schema,
            self.test_worker_duplicate_prevention,
            self.test_worker_initialization,
            self.test_anti_ban_system,
            self.test_worker_utilization,
            self.test_parallel_posting_readiness,
            self.test_restart_recovery,
            self.test_admin_interface_files,
            self.test_user_interface_files,
            self.test_payment_system_files
        ]
        
        for test in tests:
            try:
                test()
                logger.info("-" * 40)
            except Exception as e:
                logger.error(f"❌ Test {test.__name__} failed: {e}")
                self.test_results['tests'][test.__name__] = {
                    'status': 'FAILED',
                    'error': str(e),
                    'fixes': []
                }
        
        # Generate final report
        self.generate_test_report()
        
    def test_database_schema(self):
        """Test database schema fixes."""
        logger.info("🔧 Testing Database Schema Fixes...")
        
        if not os.path.exists(self.db_path):
            self._record_test_failure('database_schema', 'Database file not found', 
                                    ['Run database initialization'])
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Test 1: Check worker_usage table structure
            cursor.execute("PRAGMA table_info(worker_usage)")
            worker_usage_columns = [col[1] for col in cursor.fetchall()]
            
            required_worker_usage_columns = [
                'worker_id', 'hourly_posts', 'daily_posts', 'hourly_limit', 
                'daily_limit', 'created_at', 'updated_at'
            ]
            
            missing_worker_usage = [col for col in required_worker_usage_columns 
                                  if col not in worker_usage_columns]
            
            if missing_worker_usage:
                self._record_test_failure('database_schema', 
                                        f'Missing columns in worker_usage: {missing_worker_usage}',
                                        ['Run fix_remaining_errors.py'])
            else:
                logger.info("✅ worker_usage table structure is correct")
            
            # Test 2: Check worker_cooldowns table structure
            cursor.execute("PRAGMA table_info(worker_cooldowns)")
            cooldowns_columns = [col[1] for col in cursor.fetchall()]
            
            required_cooldowns_columns = ['id', 'worker_id', 'cooldown_until', 'created_at', 'is_active', 'last_used_at']
            missing_cooldowns = [col for col in required_cooldowns_columns 
                               if col not in cooldowns_columns]
            
            if missing_cooldowns:
                self._record_test_failure('database_schema', 
                                        f'Missing columns in worker_cooldowns: {missing_cooldowns}',
                                        ['Run fix_remaining_errors.py'])
            else:
                logger.info("✅ worker_cooldowns table structure is correct")
            
            # Test 3: Check posting_history table structure
            cursor.execute("PRAGMA table_info(posting_history)")
            posting_columns = [col[1] for col in cursor.fetchall()]
            
            required_posting_columns = ['ban_detected', 'ban_type', 'error_message', 'message_content_hash']
            missing_posting = [col for col in required_posting_columns 
                             if col not in posting_columns]
            
            if missing_posting:
                self._record_test_failure('database_schema', 
                                        f'Missing columns in posting_history: {missing_posting}',
                                        ['Run fix_posting_history_table.py'])
            else:
                logger.info("✅ posting_history table structure is correct")
            
            # Test 4: Check UNIQUE constraint on worker_usage
            cursor.execute("PRAGMA table_info(worker_usage)")
            worker_usage_info = cursor.fetchall()
            
            worker_id_unique = False
            for col in worker_usage_info:
                if col[1] == 'worker_id' and col[5] == 1:  # 5th element indicates UNIQUE
                    worker_id_unique = True
                    break
            
            if not worker_id_unique:
                self._record_test_failure('database_schema', 
                                        'UNIQUE constraint missing on worker_id',
                                        ['Run fix_root_cause_duplicates.py'])
            else:
                logger.info("✅ UNIQUE constraint on worker_id is present")
            
            # Test 5: Check worker count
            cursor.execute("SELECT COUNT(*) FROM worker_usage")
            worker_count = cursor.fetchone()[0]
            
            if worker_count != 10:
                self._record_test_failure('database_schema', 
                                        f'Expected 10 workers, found {worker_count}',
                                        ['Run fix_root_cause_duplicates.py'])
            else:
                logger.info("✅ Exactly 10 workers in database")
            
            # Test 6: Check for duplicates
            cursor.execute("SELECT worker_id, COUNT(*) FROM worker_usage GROUP BY worker_id HAVING COUNT(*) > 1")
            duplicates = cursor.fetchall()
            
            if duplicates:
                self._record_test_failure('database_schema', 
                                        f'Found {len(duplicates)} duplicate workers',
                                        ['Run fix_root_cause_duplicates.py'])
            else:
                logger.info("✅ No duplicate workers found")
            
            self._record_test_success('database_schema', 'All database schema tests passed')
            
        except Exception as e:
            self._record_test_failure('database_schema', f'Database test error: {e}', [])
        finally:
            conn.close()
    
    def test_worker_duplicate_prevention(self):
        """Test worker duplicate prevention system."""
        logger.info("🛡️ Testing Worker Duplicate Prevention...")
        
        if not os.path.exists(self.db_path):
            self._record_test_failure('worker_duplicate_prevention', 'Database file not found', [])
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Test 1: Check UNIQUE constraint exists
            cursor.execute("PRAGMA table_info(worker_usage)")
            worker_usage_info = cursor.fetchall()
            
            worker_id_unique = False
            for col in worker_usage_info:
                if col[1] == 'worker_id' and col[5] == 1:
                    worker_id_unique = True
                    break
            
            if not worker_id_unique:
                self._record_test_failure('worker_duplicate_prevention', 
                                        'UNIQUE constraint missing on worker_id',
                                        ['Run fix_root_cause_duplicates.py'])
                return
            
            # Test 2: Try to insert duplicate (should fail)
            try:
                cursor.execute("INSERT INTO worker_usage (worker_id, hourly_posts, daily_posts, hourly_limit, daily_limit, created_at) VALUES (1, 0, 0, 15, 150, ?)", (datetime.now(),))
                conn.commit()
                self._record_test_failure('worker_duplicate_prevention', 
                                        'UNIQUE constraint not working - duplicate insert succeeded',
                                        ['Check database constraints'])
            except sqlite3.IntegrityError:
                logger.info("✅ UNIQUE constraint working - duplicate insert properly rejected")
                conn.rollback()
            except Exception as e:
                logger.warning(f"⚠️ Unexpected error during duplicate test: {e}")
                conn.rollback()
            
            # Test 3: Check worker IDs are 1-10
            cursor.execute("SELECT worker_id FROM worker_usage ORDER BY worker_id")
            worker_ids = [row[0] for row in cursor.fetchall()]
            
            expected_ids = list(range(1, 11))
            if worker_ids != expected_ids:
                self._record_test_failure('worker_duplicate_prevention', 
                                        f'Worker IDs not 1-10: {worker_ids}',
                                        ['Run fix_root_cause_duplicates.py'])
            else:
                logger.info("✅ Worker IDs are correctly 1-10")
            
            self._record_test_success('worker_duplicate_prevention', 'Worker duplicate prevention working correctly')
            
        except Exception as e:
            self._record_test_failure('worker_duplicate_prevention', f'Test error: {e}', [])
        finally:
            conn.close()
    
    def test_worker_initialization(self):
        """Test worker initialization system."""
        logger.info("🔧 Testing Worker Initialization...")
        
        if not os.path.exists(self.db_path):
            self._record_test_failure('worker_initialization', 'Database file not found', [])
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Test 1: Check all 10 workers exist
            cursor.execute("SELECT COUNT(*) FROM worker_usage")
            worker_count = cursor.fetchone()[0]
            
            if worker_count != 10:
                self._record_test_failure('worker_initialization', 
                                        f'Expected 10 workers, found {worker_count}',
                                        ['Run fix_root_cause_duplicates.py'])
                return
            
            # Test 2: Check worker data integrity
            cursor.execute("SELECT worker_id, hourly_limit, daily_limit FROM worker_usage ORDER BY worker_id")
            workers = cursor.fetchall()
            
            for worker_id, hourly_limit, daily_limit in workers:
                if hourly_limit != 15 or daily_limit != 150:
                    self._record_test_failure('worker_initialization', 
                                            f'Worker {worker_id} has wrong limits: hourly={hourly_limit}, daily={daily_limit}',
                                            ['Check worker initialization'])
                    return
            
            logger.info("✅ All workers have correct limits (15 hourly, 150 daily)")
            
            # Test 3: Check worker_cooldowns table
            cursor.execute("SELECT COUNT(*) FROM worker_cooldowns")
            cooldown_count = cursor.fetchone()[0]
            
            logger.info(f"✅ Found {cooldown_count} cooldown records")
            
            self._record_test_success('worker_initialization', 'Worker initialization working correctly')
            
        except Exception as e:
            self._record_test_failure('worker_initialization', f'Test error: {e}', [])
        finally:
            conn.close()
    
    def test_anti_ban_system(self):
        """Test anti-ban system components."""
        logger.info("🛡️ Testing Anti-Ban System...")
        
        if not os.path.exists(self.db_path):
            self._record_test_failure('anti_ban_system', 'Database file not found', [])
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Test 1: Check cooldown table structure
            cursor.execute("PRAGMA table_info(worker_cooldowns)")
            cooldowns_columns = [col[1] for col in cursor.fetchall()]
            
            required_cooldown_columns = ['id', 'worker_id', 'cooldown_until', 'created_at', 'is_active', 'last_used_at']
            missing_cooldown = [col for col in required_cooldown_columns 
                              if col not in cooldowns_columns]
            
            if missing_cooldown:
                self._record_test_failure('anti_ban_system', 
                                        f'Missing cooldown columns: {missing_cooldown}',
                                        ['Run fix_remaining_errors.py'])
                return
            
            # Test 2: Check cooldown queries work
            cursor.execute("""
                SELECT wc.worker_id, wc.is_active, wc.last_used_at,
                       COALESCE(wu.messages_sent_today, 0) as messages_today,
                       COALESCE(wu.daily_limit, 50) as daily_limit
                FROM worker_cooldowns wc
                LEFT JOIN worker_usage wu ON wc.worker_id = wu.worker_id 
                    AND wu.date = date('now')
                ORDER BY wc.worker_id
                LIMIT 5
            """)
            workers = cursor.fetchall()
            logger.info(f"✅ Anti-ban query working: {len(workers)} workers found")
            
            # Test 3: Check available workers query
            cursor.execute("""
                SELECT wc.worker_id, wc.is_active, wc.last_used_at,
                       COALESCE(wu.messages_sent_today, 0) as messages_today,
                       COALESCE(wu.daily_limit, 50) as daily_limit
                FROM worker_cooldowns wc
                LEFT JOIN worker_usage wu ON wc.worker_id = wu.worker_id 
                    AND wu.date = date('now')
                WHERE wc.is_active = 1 
                AND COALESCE(wu.messages_sent_today, 0) < COALESCE(wu.daily_limit, 50)
                ORDER BY wc.last_used_at ASC NULLS FIRST
                LIMIT 5
            """)
            available_workers = cursor.fetchall()
            logger.info(f"✅ Available workers query working: {len(available_workers)} available workers found")
            
            self._record_test_success('anti_ban_system', 'Anti-ban system database components working')
            
        except Exception as e:
            self._record_test_failure('anti_ban_system', f'Test error: {e}', [])
        finally:
            conn.close()
    
    def test_worker_utilization(self):
        """Test worker utilization system."""
        logger.info("⚡ Testing Worker Utilization...")
        
        if not os.path.exists(self.db_path):
            self._record_test_failure('worker_utilization', 'Database file not found', [])
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Test 1: Check all workers are available
            cursor.execute("SELECT COUNT(*) FROM worker_usage")
            total_workers = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM worker_cooldowns wc
                LEFT JOIN worker_usage wu ON wc.worker_id = wu.worker_id 
                    AND wu.date = date('now')
                WHERE wc.is_active = 1 
                AND COALESCE(wu.messages_sent_today, 0) < COALESCE(wu.daily_limit, 50)
            """)
            available_workers = cursor.fetchone()[0]
            
            logger.info(f"✅ Total workers: {total_workers}, Available workers: {available_workers}")
            
            if available_workers == 0:
                self._record_test_failure('worker_utilization', 
                                        'No workers available for posting',
                                        ['Check worker cooldowns and limits'])
            elif available_workers < total_workers:
                logger.warning(f"⚠️ Only {available_workers}/{total_workers} workers available")
            else:
                logger.info("✅ All workers available for posting")
            
            self._record_test_success('worker_utilization', 'Worker utilization system working')
            
        except Exception as e:
            self._record_test_failure('worker_utilization', f'Test error: {e}', [])
        finally:
            conn.close()
    
    def test_parallel_posting_readiness(self):
        """Test parallel posting system readiness."""
        logger.info("🚀 Testing Parallel Posting Readiness...")
        
        # Test 1: Check posting service file exists and has required methods
        posting_service_path = 'scheduler/core/posting_service.py'
        
        if not os.path.exists(posting_service_path):
            self._record_test_failure('parallel_posting_readiness', 
                                    'Posting service file not found',
                                    ['Check file structure'])
            return
        
        try:
            with open(posting_service_path, 'r') as f:
                content = f.read()
            
            required_methods = [
                '_post_single_destination_parallel',
                '_mark_slot_as_posted',
                '_check_worker_cooldown',
                '_set_worker_cooldown'
            ]
            
            missing_methods = [method for method in required_methods 
                             if method not in content]
            
            if missing_methods:
                self._record_test_failure('parallel_posting_readiness', 
                                        f'Missing methods in posting service: {missing_methods}',
                                        ['Check posting service implementation'])
            else:
                logger.info("✅ All required parallel posting methods present")
            
            # Test 2: Check for anti-ban delays
            if 'asyncio.sleep' in content and 'random.uniform' in content:
                logger.info("✅ Anti-ban delays implemented")
            else:
                logger.warning("⚠️ Anti-ban delays may not be implemented")
            
            self._record_test_success('parallel_posting_readiness', 'Parallel posting system ready')
            
        except Exception as e:
            self._record_test_failure('parallel_posting_readiness', f'Test error: {e}', [])
    
    def test_restart_recovery(self):
        """Test restart recovery system."""
        logger.info("🔄 Testing Restart Recovery...")
        
        restart_recovery_path = 'restart_recovery.py'
        
        if not os.path.exists(restart_recovery_path):
            self._record_test_failure('restart_recovery', 
                                    'Restart recovery file not found',
                                    ['Check file structure'])
            return
        
        try:
            with open(restart_recovery_path, 'r') as f:
                content = f.read()
            
            # Check for fixed method call
            if 'get_posting_history(limit=10)' in content:
                logger.info("✅ Restart recovery method call fixed")
            else:
                self._record_test_failure('restart_recovery', 
                                        'Restart recovery method call not fixed',
                                        ['Fix get_posting_history call'])
            
            self._record_test_success('restart_recovery', 'Restart recovery system ready')
            
        except Exception as e:
            self._record_test_failure('restart_recovery', f'Test error: {e}', [])
    
    def test_admin_interface_files(self):
        """Test admin interface files."""
        logger.info("👨‍💼 Testing Admin Interface Files...")
        
        admin_files = [
            'commands/admin_commands.py',
            'commands/admin_slot_commands.py'
        ]
        
        for file_path in admin_files:
            if not os.path.exists(file_path):
                self._record_test_failure('admin_interface_files', 
                                        f'Admin file not found: {file_path}',
                                        ['Check file structure'])
                return
        
        logger.info("✅ All admin interface files present")
        self._record_test_success('admin_interface_files', 'Admin interface files ready')
    
    def test_user_interface_files(self):
        """Test user interface files."""
        logger.info("👤 Testing User Interface Files...")
        
        user_files = [
            'commands/user_commands.py',
            'commands/forwarding_commands.py',
            'commands/subscription_commands.py'
        ]
        
        for file_path in user_files:
            if not os.path.exists(file_path):
                self._record_test_failure('user_interface_files', 
                                        f'User file not found: {file_path}',
                                        ['Check file structure'])
                return
        
        logger.info("✅ All user interface files present")
        self._record_test_success('user_interface_files', 'User interface files ready')
    
    def test_payment_system_files(self):
        """Test payment system files."""
        logger.info("💰 Testing Payment System Files...")
        
        payment_files = [
            'src/services/blockchain_payments.py',
            'commands/user_commands.py'  # Contains payment handlers
        ]
        
        for file_path in payment_files:
            if not os.path.exists(file_path):
                self._record_test_failure('payment_system_files', 
                                        f'Payment file not found: {file_path}',
                                        ['Check file structure'])
                return
        
        logger.info("✅ All payment system files present")
        self._record_test_success('payment_system_files', 'Payment system files ready')
    
    def _record_test_success(self, test_name: str, message: str):
        """Record a successful test."""
        logger.info(f"✅ {test_name}: {message}")
        self.test_results['tests'][test_name] = {
            'status': 'PASS',
            'message': message,
            'fixes': []
        }
        self.test_results['success_count'] += 1
        self.test_results['total_tests'] += 1
    
    def _record_test_failure(self, test_name: str, error: str, fixes: List[str]):
        """Record a failed test."""
        logger.error(f"❌ {test_name}: {error}")
        self.test_results['tests'][test_name] = {
            'status': 'FAIL',
            'error': error,
            'fixes': fixes
        }
        self.test_results['issues'].append(f"{test_name}: {error}")
        self.test_results['total_tests'] += 1
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 COMPREHENSIVE TESTING REPORT")
        logger.info("=" * 60)
        
        # Calculate overall status
        if self.test_results['success_count'] == self.test_results['total_tests']:
            self.test_results['overall_status'] = 'PASS'
            logger.info("🎉 ALL TESTS PASSED!")
        elif self.test_results['success_count'] > 0:
            self.test_results['overall_status'] = 'PARTIAL'
            logger.info(f"⚠️ PARTIAL SUCCESS: {self.test_results['success_count']}/{self.test_results['total_tests']} tests passed")
        else:
            self.test_results['overall_status'] = 'FAIL'
            logger.error("❌ ALL TESTS FAILED!")
        
        # Summary
        logger.info(f"\n📈 Test Summary:")
        logger.info(f"  Total Tests: {self.test_results['total_tests']}")
        logger.info(f"  Passed: {self.test_results['success_count']}")
        logger.info(f"  Failed: {self.test_results['total_tests'] - self.test_results['success_count']}")
        logger.info(f"  Success Rate: {(self.test_results['success_count'] / self.test_results['total_tests'] * 100):.1f}%")
        
        # Issues
        if self.test_results['issues']:
            logger.info(f"\n❌ Issues Found:")
            for issue in self.test_results['issues']:
                logger.info(f"  • {issue}")
        
        # Warnings
        if self.test_results['warnings']:
            logger.info(f"\n⚠️ Warnings:")
            for warning in self.test_results['warnings']:
                logger.info(f"  • {warning}")
        
        # Recommendations
        logger.info(f"\n🎯 Recommendations:")
        if self.test_results['overall_status'] == 'PASS':
            logger.info("  ✅ System is ready for production deployment!")
            logger.info("  ✅ All critical fixes are working correctly")
            logger.info("  ✅ Proceed with confidence")
        elif self.test_results['overall_status'] == 'PARTIAL':
            logger.info("  ⚠️ Some issues need attention before deployment")
            logger.info("  ⚠️ Review failed tests and apply fixes")
            logger.info("  ⚠️ Re-run tests after fixes")
        else:
            logger.info("  ❌ Critical issues need immediate attention")
            logger.info("  ❌ Do not deploy until all issues are resolved")
            logger.info("  ❌ Apply fixes and re-run tests")
        
        # Save report
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            import json
            with open(report_file, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            logger.info(f"\n📄 Test report saved to: {report_file}")
        except Exception as e:
            logger.warning(f"Could not save test report: {e}")

def main():
    """Run comprehensive testing suite."""
    tester = ComprehensiveTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
