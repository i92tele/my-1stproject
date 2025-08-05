#!/usr/bin/env python3
"""
Database Merger Script
Safely merges methods from PostgreSQL database into SQLite database
"""

import re
import os

def extract_methods(file_path):
    """Extract all method definitions from a Python file."""
    methods = {}
    current_method = None
    current_content = []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Find all async def methods
        method_pattern = r'async def (\w+)\s*\([^)]*\)[^:]*:(.*?)(?=\n\s*async def|\n\s*def|\Z)'
        matches = re.finditer(method_pattern, content, re.DOTALL)
        
        for match in matches:
            method_name = match.group(1)
            method_content = match.group(2).strip()
            methods[method_name] = method_content
            
    except FileNotFoundError:
        print(f"File {file_path} not found")
        return {}
    
    return methods

def merge_databases():
    """Merge missing methods from PostgreSQL to SQLite database."""
    print("�� Comparing database files...")
    
    # Extract methods from both files
    postgresql_methods = extract_methods('database.py')
    sqlite_methods = extract_methods('src/database.py')
    
    print(f"📊 PostgreSQL database has {len(postgresql_methods)} methods")
    print(f"📊 SQLite database has {len(sqlite_methods)} methods")
    
    # Find methods in PostgreSQL that are missing in SQLite
    missing_methods = {}
    for method_name, method_content in postgresql_methods.items():
        if method_name not in sqlite_methods:
            missing_methods[method_name] = method_content
            print(f"➕ Found missing method: {method_name}")
    
    if not missing_methods:
        print("✅ No missing methods found!")
        return
    
    # Add missing methods to SQLite database
    print(f"\n📝 Adding {len(missing_methods)} missing methods to SQLite database...")
    
    with open('src/database.py', 'a') as f:
        f.write('\n    # --- Methods merged from PostgreSQL database ---\n')
        for method_name, method_content in missing_methods.items():
            f.write(f'\n    async def {method_name}(self, *args, **kwargs):\n')
            f.write(f'        """{method_name} - merged from PostgreSQL database."""\n')
            f.write(f'        # TODO: Implement this method for SQLite\n')
            f.write(f'        self.logger.warning(f"Method {method_name} not yet implemented for SQLite")\n')
            f.write(f'        return None\n')
    
    print("✅ Database merger completed!")
    print("📝 Missing methods have been added as stubs to src/database.py")
    print("⚠️  You may need to implement these methods for SQLite compatibility")

if __name__ == "__main__":
    merge_databases()
