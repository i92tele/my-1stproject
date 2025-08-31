#!/usr/bin/env python3
"""
Analyze Posting Issues
Comprehensive analysis of posting failures and channel access issues
"""

import sqlite3
import os
import re
from collections import defaultdict, Counter

def analyze_log_file():
    """Analyze the scheduler.log file for posting issues."""
    print("🔍 ANALYZING POSTING ISSUES FROM LOGS")
    print("=" * 60)
    
    log_file = "scheduler.log"
    if not os.path.exists(log_file):
        print(f"❌ Log file not found: {log_file}")
        return
    
    # Read recent log entries
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Get last 1000 lines for recent analysis
    recent_lines = lines[-1000:] if len(lines) > 1000 else lines
    
    # Analyze error patterns
    error_patterns = {
        'database_error': r'Error recording posting attempt: table worker_activity_log has no column named chat_id',
        'permission_denied': r'permission_denied',
        'rate_limit': r'rate_limit',
        'private_channel': r'private and you lack permission',
        'banned': r'you were banned from it',
        'invalid_destination': r'Invalid destination',
        'cannot_find_entity': r'Cannot find any entity',
        'flood_wait': r'wait of \d+ seconds is required',
        'forum_posting_failed': r'Forum topic posting failed'
    }
    
    error_counts = defaultdict(int)
    destination_errors = defaultdict(list)
    worker_errors = defaultdict(list)
    
    for line in recent_lines:
        for error_type, pattern in error_patterns.items():
            if re.search(pattern, line):
                error_counts[error_type] += 1
                
                # Extract destination info
                dest_match = re.search(r'@(\w+)(?:/\d+)?', line)
                if dest_match:
                    destination = dest_match.group(0)
                    destination_errors[destination].append(error_type)
                
                # Extract worker info
                worker_match = re.search(r'Worker (\d+)', line)
                if worker_match:
                    worker_id = worker_match.group(1)
                    worker_errors[worker_id].append(error_type)
    
    # Print analysis
    print(f"\n📊 ERROR ANALYSIS (Last {len(recent_lines)} log lines):")
    print("-" * 50)
    
    for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {error_type}: {count} occurrences")
    
    print(f"\n🎯 TOP PROBLEMATIC DESTINATIONS:")
    print("-" * 40)
    
    dest_error_counts = {dest: len(errors) for dest, errors in destination_errors.items()}
    for dest, count in sorted(dest_error_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        error_types = Counter(destination_errors[dest])
        print(f"  @{dest}: {count} errors")
        for error_type, error_count in error_types.most_common(3):
            print(f"    - {error_type}: {error_count}")
    
    print(f"\n👥 WORKER ERROR ANALYSIS:")
    print("-" * 30)
    
    worker_error_counts = {worker: len(errors) for worker, errors in worker_errors.items()}
    for worker, count in sorted(worker_error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        error_types = Counter(worker_errors[worker])
        print(f"  Worker {worker}: {count} errors")
        for error_type, error_count in error_types.most_common(3):
            print(f"    - {error_type}: {error_count}")

def analyze_database_posts():
    """Analyze posting data from database."""
    print(f"\n📊 DATABASE POSTING ANALYSIS:")
    print("-" * 40)
    
    db_path = "bot_database.db"
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if worker_activity_log table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_activity_log'")
        if not cursor.fetchone():
            print("❌ worker_activity_log table doesn't exist")
            return
        
        # Get posting statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_posts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_posts,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_posts
            FROM worker_activity_log 
            WHERE created_at > datetime('now', '-24 hours')
        """)
        
        stats = cursor.fetchone()
        if stats and stats[0] > 0:
            total, successful, failed = stats
            success_rate = (successful / total) * 100 if total > 0 else 0
            
            print(f"📈 Last 24 Hours:")
            print(f"  Total posts: {total}")
            print(f"  Successful: {successful}")
            print(f"  Failed: {failed}")
            print(f"  Success rate: {success_rate:.1f}%")
        
        # Get error breakdown
        cursor.execute("""
            SELECT error_message, COUNT(*) as count
            FROM worker_activity_log 
            WHERE success = 0 AND created_at > datetime('now', '-24 hours')
            GROUP BY error_message
            ORDER BY count DESC
            LIMIT 10
        """)
        
        errors = cursor.fetchall()
        if errors:
            print(f"\n❌ TOP ERROR MESSAGES:")
            for error, count in errors:
                print(f"  {error}: {count}")
        
        # Get destination performance
        cursor.execute("""
            SELECT destination_id, 
                   COUNT(*) as total,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM worker_activity_log 
            WHERE destination_id IS NOT NULL AND created_at > datetime('now', '-24 hours')
            GROUP BY destination_id
            ORDER BY total DESC
            LIMIT 10
        """)
        
        destinations = cursor.fetchall()
        if destinations:
            print(f"\n🎯 DESTINATION PERFORMANCE:")
            for dest, total, successful in destinations:
                success_rate = (successful / total) * 100 if total > 0 else 0
                print(f"  {dest}: {successful}/{total} ({success_rate:.1f}%)")
        
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")
    finally:
        conn.close()

def generate_recommendations():
    """Generate recommendations based on the analysis."""
    print(f"\n💡 RECOMMENDATIONS:")
    print("-" * 30)
    
    print("🔧 IMMEDIATE ACTIONS:")
    print("  1. Fix database schema (chat_id column issue)")
    print("  2. Update channel access permissions")
    print("  3. Implement better rate limiting")
    
    print("\n📊 MONITORING IMPROVEMENTS:")
    print("  1. Add destination health tracking")
    print("  2. Implement worker performance metrics")
    print("  3. Create automated channel validation")
    
    print("\n🛡️ PREVENTION STRATEGIES:")
    print("  1. Pre-validate channels before posting")
    print("  2. Implement exponential backoff for rate limits")
    print("  3. Add channel blacklist for consistently failing destinations")
    
    print("\n📈 OPTIMIZATION OPPORTUNITIES:")
    print("  1. Focus on high-success-rate destinations")
    print("  2. Rotate workers more intelligently")
    print("  3. Implement adaptive posting schedules")

def main():
    """Main function."""
    print("🔍 COMPREHENSIVE POSTING ISSUE ANALYSIS")
    print("=" * 60)
    
    # Analyze log files
    analyze_log_file()
    
    # Analyze database
    analyze_database_posts()
    
    # Generate recommendations
    generate_recommendations()
    
    print(f"\n🎯 PRIORITY ACTION PLAN:")
    print("=" * 40)
    print("1. 🔧 Fix database schema (chat_id column)")
    print("2. 🎯 Focus on high-success destinations")
    print("3. 🛡️ Implement better error handling")
    print("4. 📊 Add comprehensive monitoring")

if __name__ == "__main__":
    main()
