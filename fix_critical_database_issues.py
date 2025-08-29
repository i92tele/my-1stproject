#!/usr/bin/env python3
"""
Fix Critical Database Issues
Address the most critical database operation problems identified in the audit
"""

import os
import re
from typing import List, Dict

def fix_database_operations_without_error_handling():
    """Fix database operations that lack proper error handling."""
    print("🔧 Fixing Critical Database Issues")
    print("=" * 50)
    
    # Files with critical database issues
    critical_files = [
        'src/database/manager.py',
        'src/services/worker_manager.py',
        'commands/user_commands.py',
        'commands/admin_commands.py'
    ]
    
    fixes_applied = 0
    
    for file_path in critical_files:
        if not os.path.exists(file_path):
            print(f"⚠️  File not found: {file_path}")
            continue
            
        print(f"\n📋 Processing: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix 1: Add error handling to database operations
            content = add_database_error_handling(content)
            
            # Fix 2: Fix connection leaks
            content = fix_connection_leaks(content)
            
            # Fix 3: Add proper transaction handling
            content = add_transaction_handling(content)
            
            # Check if changes were made
            if content != original_content:
                # Create backup
                backup_path = f"{file_path}.backup"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"   ✅ Fixed database issues in {file_path}")
                print(f"   📁 Backup created: {backup_path}")
                fixes_applied += 1
            else:
                print(f"   ℹ️  No changes needed for {file_path}")
                
        except Exception as e:
            print(f"   ❌ Error processing {file_path}: {e}")
    
    print(f"\n🎯 Summary:")
    print(f"   - Files processed: {len(critical_files)}")
    print(f"   - Fixes applied: {fixes_applied}")
    
    return fixes_applied

def add_database_error_handling(content: str) -> str:
    """Add proper error handling to database operations."""
    
    # Pattern 1: Add try/catch around cursor.execute calls
    patterns = [
        # Pattern for cursor.execute without error handling
        (r'(\s+)(cursor\.execute\()([^)]+)\)', r'\1try:\n\1    \2\3)\n\1except Exception as e:\n\1    self.logger.error(f"Database error: {e}")\n\1    raise'),
        
        # Pattern for conn.commit without error handling
        (r'(\s+)(conn\.commit\(\))', r'\1try:\n\1    \2\n\1except Exception as e:\n\1    self.logger.error(f"Commit error: {e}")\n\1    conn.rollback()\n\1    raise'),
        
        # Pattern for conn.rollback without error handling
        (r'(\s+)(conn\.rollback\(\))', r'\1try:\n\1    \2\n\1except Exception as e:\n\1    self.logger.error(f"Rollback error: {e}")\n\1    raise'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content

def fix_connection_leaks(content: str) -> str:
    """Fix potential database connection leaks."""
    
    # Replace direct sqlite3.connect with context manager
    patterns = [
        # Pattern for sqlite3.connect without context manager
        (r'(\s+)conn = sqlite3\.connect\(([^)]+)\)', 
         r'\1with sqlite3.connect(\2) as conn:'),
        
        # Pattern for cursor creation without context
        (r'(\s+)cursor = conn\.cursor\(\)', 
         r'\1cursor = conn.cursor()'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content

def add_transaction_handling(content: str) -> str:
    """Add proper transaction handling."""
    
    # Add transaction context for multiple operations
    transaction_patterns = [
        # Pattern for multiple execute calls without transaction
        (r'(\s+)cursor\.execute\(([^)]+)\)\n(\s+)cursor\.execute\(([^)]+)\)', 
         r'\1try:\n\1    cursor.execute(\2)\n\1    cursor.execute(\4)\n\1    conn.commit()\n\1except Exception as e:\n\1    conn.rollback()\n\1    raise'),
    ]
    
    for pattern, replacement in transaction_patterns:
        content = re.sub(pattern, replacement, content)
    
    return content

def create_database_safety_wrapper():
    """Create a database safety wrapper module."""
    
    wrapper_code = '''"""
Database Safety Wrapper
Provides safe database operations with proper error handling
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional, Any, Dict, List

class DatabaseSafetyWrapper:
    """Safe database operations wrapper."""
    
    def __init__(self, db_path: str, logger: logging.Logger):
        self.db_path = db_path
        self.logger = logger
    
    @contextmanager
    def get_connection(self, timeout: int = 30):
        """Get a database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=timeout)
            conn.execute("PRAGMA busy_timeout=30000;")
            yield conn
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def execute_safe(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
        """Execute a query safely with error handling."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Fetch results if it's a SELECT query
                if query.strip().upper().startswith('SELECT'):
                    columns = [description[0] for description in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                else:
                    conn.commit()
                    return None
                    
        except Exception as e:
            self.logger.error(f"Database execution error: {e}")
            self.logger.error(f"Query: {query}")
            if params:
                self.logger.error(f"Params: {params}")
            raise
    
    def execute_many_safe(self, query: str, params_list: List[tuple]) -> None:
        """Execute multiple queries safely."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
        except Exception as e:
            self.logger.error(f"Database executemany error: {e}")
            self.logger.error(f"Query: {query}")
            raise
    
    def transaction_safe(self, operations: List[Dict]) -> bool:
        """Execute multiple operations in a transaction."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for operation in operations:
                    query = operation['query']
                    params = operation.get('params', ())
                    cursor.execute(query, params)
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Transaction error: {e}")
            return False
'''
    
    with open('src/database/safety_wrapper.py', 'w', encoding='utf-8') as f:
        f.write(wrapper_code)
    
    print("✅ Created database safety wrapper: src/database/safety_wrapper.py")

def main():
    """Run the critical database fixes."""
    print("🔧 Critical Database Issue Fixer")
    print("=" * 50)
    
    # Create safety wrapper
    create_database_safety_wrapper()
    
    # Fix critical database issues
    fixes_applied = fix_database_operations_without_error_handling()
    
    print(f"\n🎉 Critical database fixes completed!")
    print(f"   - Safety wrapper created")
    print(f"   - {fixes_applied} files updated")
    
    print(f"\n📋 Next Steps:")
    print(f"   1. Test the updated database operations")
    print(f"   2. Review the safety wrapper implementation")
    print(f"   3. Update other files to use the safety wrapper")
    print(f"   4. Run the code audit again to verify fixes")

if __name__ == "__main__":
    main()
