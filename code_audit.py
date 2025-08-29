#!/usr/bin/env python3
"""
Comprehensive Code Audit
Identify logic flaws, code duplicates, and potential issues
"""

import os
import re
import ast
from collections import defaultdict
from typing import Dict, List, Set, Tuple

def scan_directory(directory: str) -> List[str]:
    """Scan directory for Python files."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip common directories that shouldn't be audited
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', 'node_modules', '.pytest_cache']]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def find_duplicate_functions(files: List[str]) -> Dict[str, List[str]]:
    """Find duplicate function definitions across files."""
    function_signatures = defaultdict(list)
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST to find function definitions
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Create a signature based on function name and parameters
                    params = [arg.arg for arg in node.args.args]
                    signature = f"{node.name}({', '.join(params)})"
                    function_signatures[signature].append(file_path)
                    
        except Exception as e:
            print(f"⚠️  Error parsing {file_path}: {e}")
    
    # Return only duplicates
    return {sig: files for sig, files in function_signatures.items() if len(files) > 1}

def find_duplicate_code_blocks(files: List[str]) -> List[Tuple[str, List[str]]]:
    """Find duplicate code blocks across files."""
    code_blocks = defaultdict(list)
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Look for blocks of code (5+ lines) that might be duplicated
            for i in range(len(lines) - 4):
                block = ''.join(lines[i:i+5])
                # Normalize whitespace
                block = re.sub(r'\s+', ' ', block.strip())
                if len(block) > 50:  # Only consider substantial blocks
                    code_blocks[block].append(f"{file_path}:{i+1}")
                    
        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}")
    
    # Return only duplicates
    return [(block, locations) for block, locations in code_blocks.items() if len(locations) > 1]

def find_logic_flaws(files: List[str]) -> List[Dict]:
    """Find potential logic flaws in the code."""
    flaws = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for common logic flaws
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # 1. Hardcoded credentials or sensitive data
                if any(pattern in line_stripped.lower() for pattern in [
                    'password', 'secret', 'key', 'token', 'api_key'
                ]) and any(char in line_stripped for char in ['=', ':', '"', "'"]):
                    if not any(skip in line_stripped for skip in ['os.getenv', 'config', 'ENV']):
                        flaws.append({
                            'type': 'Hardcoded Credentials',
                            'file': file_path,
                            'line': i,
                            'code': line_stripped,
                            'severity': 'HIGH'
                        })
                
                # 2. Empty except blocks
                if line_stripped == 'except:' or line_stripped == 'except Exception:':
                    if i + 1 < len(lines) and not lines[i].strip():
                        flaws.append({
                            'type': 'Empty Exception Handler',
                            'file': file_path,
                            'line': i,
                            'code': line_stripped,
                            'severity': 'MEDIUM'
                        })
                
                # 3. Potential SQL injection
                if 'execute(' in line_stripped and any(op in line_stripped for op in ['+', 'f"', 'format(']):
                    if not any(safe in line_stripped for safe in ['?', '%s', 'params']):
                        flaws.append({
                            'type': 'Potential SQL Injection',
                            'file': file_path,
                            'line': i,
                            'code': line_stripped,
                            'severity': 'HIGH'
                        })
                
                # 4. Magic numbers
                if re.search(r'\b\d{4,}\b', line_stripped) and not any(skip in line_stripped for skip in [
                    'import', 'from', 'class', 'def', 'return', 'print', 'logger'
                ]):
                    flaws.append({
                        'type': 'Magic Number',
                        'file': file_path,
                        'line': i,
                        'code': line_stripped,
                        'severity': 'LOW'
                    })
                
                # 5. Unused imports (basic check)
                if line_stripped.startswith('import ') or line_stripped.startswith('from '):
                    import_name = line_stripped.split()[1].split('.')[0]
                    if import_name not in content[i*100:]:  # Check if used later in file
                        flaws.append({
                            'type': 'Potentially Unused Import',
                            'file': file_path,
                            'line': i,
                            'code': line_stripped,
                            'severity': 'LOW'
                        })
                        
        except Exception as e:
            print(f"⚠️  Error analyzing {file_path}: {e}")
    
    return flaws

def find_inconsistent_patterns(files: List[str]) -> List[Dict]:
    """Find inconsistent coding patterns."""
    inconsistencies = []
    
    # Check for inconsistent naming conventions
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Check for inconsistent variable naming
                if '=' in line_stripped and not line_stripped.startswith('#'):
                    var_name = line_stripped.split('=')[0].strip()
                    if re.search(r'[A-Z][a-z]+[A-Z]', var_name) and not var_name.isupper():
                        inconsistencies.append({
                            'type': 'Inconsistent Variable Naming',
                            'file': file_path,
                            'line': i,
                            'code': line_stripped,
                            'description': f'Mixed case variable: {var_name}'
                        })
                        
        except Exception as e:
            print(f"⚠️  Error checking patterns in {file_path}: {e}")
    
    return inconsistencies

def find_potential_bugs(files: List[str]) -> List[Dict]:
    """Find potential bugs and issues."""
    bugs = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # 1. Division by zero potential
                if '/' in line_stripped and any(var in line_stripped for var in ['/0', '/ 0']):
                    bugs.append({
                        'type': 'Potential Division by Zero',
                        'file': file_path,
                        'line': i,
                        'code': line_stripped,
                        'severity': 'HIGH'
                    })
                
                # 2. Unclosed resources
                if any(pattern in line_stripped for pattern in ['open(', 'connect(']) and 'with ' not in line_stripped:
                    bugs.append({
                        'type': 'Unclosed Resource',
                        'file': file_path,
                        'line': i,
                        'code': line_stripped,
                        'severity': 'MEDIUM'
                    })
                
                # 3. Potential race conditions
                if 'global ' in line_stripped:
                    bugs.append({
                        'type': 'Global Variable Usage',
                        'file': file_path,
                        'line': i,
                        'code': line_stripped,
                        'severity': 'MEDIUM'
                    })
                
                # 4. Missing error handling
                if any(pattern in line_stripped for pattern in ['requests.get', 'requests.post', 'aiohttp.get']):
                    if 'try:' not in content[max(0, i-10):i]:
                        bugs.append({
                            'type': 'Missing Error Handling',
                            'file': file_path,
                            'line': i,
                            'code': line_stripped,
                            'severity': 'MEDIUM'
                        })
                        
        except Exception as e:
            print(f"⚠️  Error checking bugs in {file_path}: {e}")
    
    return bugs

def analyze_database_operations(files: List[str]) -> List[Dict]:
    """Analyze database operations for potential issues."""
    db_issues = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Check for database operations without proper error handling
                if any(op in line_stripped for op in ['execute(', 'commit(', 'rollback(']):
                    # Check if there's proper error handling nearby
                    context = content[max(0, (i-5)*100):min(len(content), (i+5)*100)]
                    if 'try:' not in context and 'except' not in context:
                        db_issues.append({
                            'type': 'Database Operation Without Error Handling',
                            'file': file_path,
                            'line': i,
                            'code': line_stripped,
                            'severity': 'HIGH'
                        })
                
                # Check for potential connection leaks
                if 'connect(' in line_stripped and 'with ' not in line_stripped:
                    db_issues.append({
                        'type': 'Potential Database Connection Leak',
                        'file': file_path,
                        'line': i,
                        'code': line_stripped,
                        'severity': 'MEDIUM'
                    })
                        
        except Exception as e:
            print(f"⚠️  Error analyzing database operations in {file_path}: {e}")
    
    return db_issues

def main():
    """Run the comprehensive code audit."""
    print("🔍 Starting Comprehensive Code Audit")
    print("=" * 60)
    
    # Scan for Python files
    print("\n1️⃣ Scanning for Python files...")
    python_files = scan_directory('.')
    print(f"✅ Found {len(python_files)} Python files")
    
    # Find duplicate functions
    print("\n2️⃣ Checking for duplicate functions...")
    duplicate_functions = find_duplicate_functions(python_files)
    if duplicate_functions:
        print(f"⚠️  Found {len(duplicate_functions)} duplicate function signatures:")
        for sig, files in duplicate_functions.items():
            print(f"   {sig}:")
            for file in files:
                print(f"     - {file}")
    else:
        print("✅ No duplicate functions found")
    
    # Find duplicate code blocks
    print("\n3️⃣ Checking for duplicate code blocks...")
    duplicate_blocks = find_duplicate_code_blocks(python_files)
    if duplicate_blocks:
        print(f"⚠️  Found {len(duplicate_blocks)} duplicate code blocks:")
        for block, locations in duplicate_blocks[:5]:  # Show first 5
            print(f"   Block found in:")
            for location in locations:
                print(f"     - {location}")
            print(f"   Code: {block[:100]}...")
    else:
        print("✅ No duplicate code blocks found")
    
    # Find logic flaws
    print("\n4️⃣ Checking for logic flaws...")
    logic_flaws = find_logic_flaws(python_files)
    if logic_flaws:
        print(f"⚠️  Found {len(logic_flaws)} potential logic flaws:")
        for flaw in logic_flaws:
            print(f"   [{flaw['severity']}] {flaw['type']} in {flaw['file']}:{flaw['line']}")
            print(f"      {flaw['code']}")
    else:
        print("✅ No logic flaws found")
    
    # Find inconsistent patterns
    print("\n5️⃣ Checking for inconsistent patterns...")
    inconsistencies = find_inconsistent_patterns(python_files)
    if inconsistencies:
        print(f"⚠️  Found {len(inconsistencies)} inconsistencies:")
        for issue in inconsistencies:
            print(f"   {issue['type']} in {issue['file']}:{issue['line']}")
            print(f"      {issue['description']}")
    else:
        print("✅ No inconsistencies found")
    
    # Find potential bugs
    print("\n6️⃣ Checking for potential bugs...")
    bugs = find_potential_bugs(python_files)
    if bugs:
        print(f"⚠️  Found {len(bugs)} potential bugs:")
        for bug in bugs:
            print(f"   [{bug['severity']}] {bug['type']} in {bug['file']}:{bug['line']}")
            print(f"      {bug['code']}")
    else:
        print("✅ No potential bugs found")
    
    # Analyze database operations
    print("\n7️⃣ Analyzing database operations...")
    db_issues = analyze_database_operations(python_files)
    if db_issues:
        print(f"⚠️  Found {len(db_issues)} database issues:")
        for issue in db_issues:
            print(f"   [{issue['severity']}] {issue['type']} in {issue['file']}:{issue['line']}")
            print(f"      {issue['code']}")
    else:
        print("✅ No database issues found")
    
    # Summary
    print("\n8️⃣ Audit Summary:")
    print("-" * 30)
    total_issues = len(duplicate_functions) + len(duplicate_blocks) + len(logic_flaws) + len(inconsistencies) + len(bugs) + len(db_issues)
    
    print(f"📊 Total Issues Found: {total_issues}")
    print(f"   - Duplicate Functions: {len(duplicate_functions)}")
    print(f"   - Duplicate Code Blocks: {len(duplicate_blocks)}")
    print(f"   - Logic Flaws: {len(logic_flaws)}")
    print(f"   - Inconsistencies: {len(inconsistencies)}")
    print(f"   - Potential Bugs: {len(bugs)}")
    print(f"   - Database Issues: {len(db_issues)}")
    
    if total_issues == 0:
        print("\n🎉 Excellent! No issues found in the code audit!")
    else:
        print(f"\n🔧 Recommendations:")
        print("   - Address HIGH severity issues first")
        print("   - Consider refactoring duplicate code")
        print("   - Add proper error handling where missing")
        print("   - Review database operations for safety")
    
    print("\n✅ Code audit completed!")

if __name__ == "__main__":
    main()
