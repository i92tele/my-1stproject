#!/usr/bin/env python3
"""
Current State Analysis for AutoFarming Bot

This script analyzes the current state of all critical components
and provides a comprehensive status report.
"""

import sqlite3
import os
import sys
from datetime import datetime

def analyze_current_state():
    """Analyze the current state of the system."""
    print("🔍 CURRENT STATE ANALYSIS")
    print("=" * 60)
    print(f"Analysis time: {datetime.now()}")
    print("=" * 60)
    
    db_path = 'bot_database.db'
    
    if not os.path.exists(db_path):
        print("❌ CRITICAL: Database file not found!")
        return
    
    print("✅ Database file exists")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Check all tables
        print("\n📋 1. DATABASE TABLES")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Total tables: {len(tables)}")
        
        critical_tables = [
            'worker_usage', 'worker_cooldowns', 'ad_slots', 
            'posting_history', 'worker_activity_log'
        ]
        
        for table in critical_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✅ {table}: {count} records")
            else:
                print(f"  ❌ {table}: MISSING")
        
        # 2. Check worker_usage structure
        print("\n👥 2. WORKER USAGE ANALYSIS")
        if 'worker_usage' in tables:
            cursor.execute("PRAGMA table_info(worker_usage)")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"Columns: {len(columns)}")
            
            required_columns = [
                'worker_id', 'hourly_posts', 'daily_posts', 'hourly_limit', 
                'daily_limit', 'created_at', 'updated_at'
            ]
            
            missing_columns = [col for col in required_columns if col not in columns]
            if missing_columns:
                print(f"  ❌ Missing columns: {missing_columns}")
            else:
                print("  ✅ All required columns present")
            
            # Check worker count
            cursor.execute("SELECT COUNT(*) FROM worker_usage")
            worker_count = cursor.fetchone()[0]
            print(f"  📊 Total workers: {worker_count}")
            
            if worker_count > 0:
                cursor.execute("SELECT worker_id FROM worker_usage ORDER BY worker_id")
                worker_ids = [row[0] for row in cursor.fetchall()]
                print(f"  Worker IDs: {worker_ids}")
                
                # Check for duplicates
                cursor.execute("SELECT worker_id, COUNT(*) FROM worker_usage GROUP BY worker_id HAVING COUNT(*) > 1")
                duplicates = cursor.fetchall()
                if duplicates:
                    print(f"  ⚠️ Duplicates found: {len(duplicates)}")
                else:
                    print("  ✅ No duplicates")
                
                # Check UNIQUE constraint
                worker_id_column = None
                for col in cursor.fetchall():
                    if col[1] == 'worker_id':
                        worker_id_column = col
                        break
                
                if worker_id_column and worker_id_column[5] == 1:
                    print("  ✅ UNIQUE constraint on worker_id")
                else:
                    print("  ⚠️ No UNIQUE constraint on worker_id")
        
        # 3. Check worker_cooldowns structure
        print("\n⏰ 3. WORKER COOLDOWNS ANALYSIS")
        if 'worker_cooldowns' in tables:
            cursor.execute("PRAGMA table_info(worker_cooldowns)")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"Columns: {len(columns)}")
            
            required_columns = ['id', 'worker_id', 'cooldown_until', 'created_at', 'is_active', 'last_used_at']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"  ❌ Missing columns: {missing_columns}")
            else:
                print("  ✅ All required columns present")
            
            cursor.execute("SELECT COUNT(*) FROM worker_cooldowns")
            cooldown_count = cursor.fetchone()[0]
            print(f"  📊 Cooldown records: {cooldown_count}")
        
        # 4. Check posting_history structure
        print("\n📜 4. POSTING HISTORY ANALYSIS")
        if 'posting_history' in tables:
            cursor.execute("PRAGMA table_info(posting_history)")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"Columns: {len(columns)}")
            
            required_columns = ['ban_detected', 'ban_type', 'error_message', 'message_content_hash']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"  ❌ Missing columns: {missing_columns}")
            else:
                print("  ✅ All required columns present")
            
            cursor.execute("SELECT COUNT(*) FROM posting_history")
            history_count = cursor.fetchone()[0]
            print(f"  📊 History records: {history_count}")
        
        # 5. Check ad_slots
        print("\n📢 5. AD SLOTS ANALYSIS")
        if 'ad_slots' in tables:
            cursor.execute("SELECT COUNT(*) FROM ad_slots")
            slot_count = cursor.fetchone()[0]
            print(f"  📊 Total slots: {slot_count}")
            
            if slot_count > 0:
                cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE last_sent_at IS NULL")
                null_timestamps = cursor.fetchone()[0]
                print(f"  📊 Slots with NULL timestamps: {null_timestamps}")
                
                cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_paused = 1")
                paused_slots = cursor.fetchone()[0]
                print(f"  📊 Paused slots: {paused_slots}")
        
        # 6. Check critical files
        print("\n📁 6. CRITICAL FILES")
        critical_files = [
            'scheduler/core/posting_service.py',
            'src/database/manager.py',
            'restart_recovery.py',
            'config.py',
            'database.py'
        ]
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                print(f"  ✅ {file_path}")
            else:
                print(f"  ❌ {file_path}: MISSING")
        
        # 7. Check posting service methods
        print("\n🔧 7. POSTING SERVICE METHODS")
        posting_service_path = 'scheduler/core/posting_service.py'
        if os.path.exists(posting_service_path):
            with open(posting_service_path, 'r') as f:
                content = f.read()
            
            required_methods = [
                '_post_single_destination_parallel',
                '_mark_slot_as_posted',
                '_check_worker_cooldown',
                '_set_worker_cooldown'
            ]
            
            for method in required_methods:
                if method in content:
                    print(f"  ✅ {method}")
                else:
                    print(f"  ❌ {method}: MISSING")
            
            # Check for anti-ban features
            if 'asyncio.sleep' in content and 'random.uniform' in content:
                print("  ✅ Anti-ban delays implemented")
            else:
                print("  ⚠️ Anti-ban delays may be missing")
        else:
            print("  ❌ Posting service file not found")
        
        # 8. Generate summary
        print("\n📊 8. SUMMARY")
        
        # Count issues
        issues = []
        warnings = []
        
        # Check for critical issues
        if 'worker_usage' not in tables:
            issues.append("worker_usage table missing")
        elif worker_count != 10:
            issues.append(f"Expected 10 workers, found {worker_count}")
        
        if 'worker_cooldowns' not in tables:
            issues.append("worker_cooldowns table missing")
        
        if 'posting_history' not in tables:
            issues.append("posting_history table missing")
        
        if not os.path.exists('scheduler/core/posting_service.py'):
            issues.append("posting_service.py missing")
        
        if not os.path.exists('config.py'):
            issues.append("config.py missing")
        
        if not os.path.exists('database.py'):
            issues.append("database.py missing")
        
        # Report status
        if issues:
            print(f"  ❌ CRITICAL ISSUES: {len(issues)}")
            for issue in issues:
                print(f"    • {issue}")
        else:
            print("  ✅ No critical issues found")
        
        if warnings:
            print(f"  ⚠️ WARNINGS: {len(warnings)}")
            for warning in warnings:
                print(f"    • {warning}")
        
        # Overall status
        if issues:
            print("\n🎯 STATUS: NEEDS ATTENTION")
            print("   Some critical issues need to be resolved before testing.")
        else:
            print("\n🎯 STATUS: READY FOR TESTING")
            print("   All critical components are in place.")
        
        print(f"\n✅ Analysis completed at {datetime.now()}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    analyze_current_state()

