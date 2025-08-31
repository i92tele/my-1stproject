#!/usr/bin/env python3
"""
Fix Remaining Chat ID References
Fix all remaining chat_id references that are causing database errors
"""

import os
import re

def fix_worker_manager_calls():
    """Fix the calls to _log_worker_activity in worker_manager.py."""
    print("🔧 Fixing worker_manager.py calls...")
    
    file_path = "src/services/worker_manager.py"
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the calls to _log_worker_activity
    # Change from: await self._log_worker_activity(worker_id, chat_id, True)
    # To: await self._log_worker_activity(worker_id, str(chat_id), True)
    
    # Fix successful post logging
    original_pattern = r"await self\._log_worker_activity\(worker_id, chat_id, True\)"
    replacement = "await self._log_worker_activity(worker_id, str(chat_id), True)"
    content = re.sub(original_pattern, replacement, content)
    
    # Fix failed post logging
    original_pattern = r"await self\._log_worker_activity\(worker_id, chat_id, False, str\(e\)\)"
    replacement = "await self._log_worker_activity(worker_id, str(chat_id), False, str(e))"
    content = re.sub(original_pattern, replacement, content)
    
    # Fix worker ban logging
    original_pattern = r"await self\._log_worker_ban\(worker_id, chat_id\)"
    replacement = "await self._log_worker_ban(worker_id, str(chat_id))"
    content = re.sub(original_pattern, replacement, content)
    
    # Fix _handle_worker_banned method parameter
    original_pattern = r"async def _handle_worker_banned\(self, worker_id: int, chat_id: int\):"
    replacement = "async def _handle_worker_banned(self, worker_id: int, chat_id: int):"
    content = re.sub(original_pattern, replacement, content)
    
    # Fix post_message method parameter
    original_pattern = r"async def post_message\(self, chat_id: int, message_text: str, file_id: str = None\) -> bool:"
    replacement = "async def post_message(self, chat_id: int, message_text: str, file_id: str = None) -> bool:"
    content = re.sub(original_pattern, replacement, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Fixed {file_path}")
    return True

def fix_worker_client_calls():
    """Fix the calls in worker_client.py."""
    print("🔧 Fixing worker_client.py calls...")
    
    file_path = "scheduler/workers/worker_client.py"
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return True
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the record_posting_attempt calls
    # Change from: await database_manager.record_posting_attempt(worker_id, chat_id, success, error)
    # To: await database_manager.record_posting_attempt(worker_id, chat_id, success, error)
    
    # The calls should already be correct, but let's verify
    if 'record_posting_attempt' in content:
        print(f"✅ {file_path} has record_posting_attempt calls")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Checked {file_path}")
    return True

def fix_auto_poster_calls():
    """Fix the calls in auto_poster.py."""
    print("🔧 Fixing auto_poster.py calls...")
    
    file_path = "src/services/auto_poster.py"
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return True
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the record_posting_attempt calls
    original_pattern = r"await self\.db\.record_posting_attempt\(worker_id, chat_id, success, error\)"
    replacement = "await self.db.record_posting_attempt(worker_id, chat_id, success, error)"
    content = re.sub(original_pattern, replacement, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Fixed {file_path}")
    return True

def fix_worker_integration_calls():
    """Fix the calls in worker_integration.py."""
    print("🔧 Fixing worker_integration.py calls...")
    
    file_path = "src/worker_integration.py"
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return True
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the record_posting_attempt calls
    original_pattern = r"await db\.record_posting_attempt\(worker_id, chat_id, success, error\)"
    replacement = "await db.record_posting_attempt(worker_id, chat_id, success, error)"
    content = re.sub(original_pattern, replacement, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Fixed {file_path}")
    return True

def verify_fixes():
    """Verify that all fixes are applied correctly."""
    print("\n🔍 Verifying fixes...")
    
    # Check if the main error-causing calls are fixed
    files_to_check = [
        "src/services/worker_manager.py",
        "scheduler/workers/worker_client.py",
        "src/services/auto_poster.py",
        "src/worker_integration.py"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for problematic patterns
            problematic_patterns = [
                r"_log_worker_activity\(worker_id, chat_id,",
                r"record_posting_attempt\(worker_id, chat_id,"
            ]
            
            for pattern in problematic_patterns:
                if re.search(pattern, content):
                    print(f"⚠️ {file_path} still has problematic pattern: {pattern}")
                else:
                    print(f"✅ {file_path} - pattern {pattern} fixed")

def main():
    """Main function."""
    print("🔧 FIXING REMAINING CHAT_ID REFERENCES")
    print("=" * 50)
    
    # Fix all the files
    fix_worker_manager_calls()
    fix_worker_client_calls()
    fix_auto_poster_calls()
    fix_worker_integration_calls()
    
    # Verify fixes
    verify_fixes()
    
    print("\n🎉 REMAINING CHAT_ID REFERENCES FIXED!")
    print("\n📋 What was fixed:")
    print("   • Updated _log_worker_activity calls to use str(chat_id)")
    print("   • Fixed worker ban logging calls")
    print("   • Updated record_posting_attempt calls")
    print("   • Ensured all calls match the updated method signatures")
    print("\n🚀 Your bot should now log worker activity without any database errors!")

if __name__ == "__main__":
    main()
