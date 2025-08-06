#!/usr/bin/env python3
"""Fix scheduler to use correct WorkerClient constructor"""

# Read the current scheduler file
with open('scheduler/core/scheduler.py', 'r') as f:
    content = f.read()

# Replace the WorkerClient instantiation
old_instantiation = '''                worker = WorkerClient(
                    worker_id=creds.worker_id,
                    api_id=creds.api_id,
                    api_hash=creds.api_hash,
                    phone=creds.phone,
                    session_file=creds.session_file
                )'''

new_instantiation = '''                worker = WorkerClient(
                    api_id=creds.api_id,
                    api_hash=creds.api_hash,
                    phone=creds.phone,
                    session_file=creds.session_file,
                    worker_id=creds.worker_id
                )'''

# Replace the instantiation
content = content.replace(old_instantiation, new_instantiation)

# Write back to file
with open('scheduler/core/scheduler.py', 'w') as f:
    f.write(content)

print("✅ Scheduler WorkerClient instantiation fixed!")
