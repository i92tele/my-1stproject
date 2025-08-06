#!/usr/bin/env python3
"""Fix WorkerClient constructor"""

# Read the current worker client file
with open('scheduler/workers/worker_client.py', 'r') as f:
    content = f.read()

# Check the current constructor
print("Current WorkerClient constructor:")
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'def __init__' in line and 'WorkerClient' in line:
        print(f"Line {i+1}: {line}")
        # Print the next few lines to see the parameters
        for j in range(i+1, min(i+10, len(lines))):
            if lines[j].strip() and not lines[j].strip().startswith('#'):
                print(f"Line {j+1}: {lines[j]}")
            if lines[j].strip() == 'self.client = None':
                break

# Fix the constructor to accept worker_id
old_constructor = '''    def __init__(self, worker_id: int, api_id: str, api_hash: str, phone: str, session_file: str):'''
new_constructor = '''    def __init__(self, api_id: str, api_hash: str, phone: str, session_file: str, worker_id: int = None):'''

# Replace the constructor
content = content.replace(old_constructor, new_constructor)

# Write back to file
with open('scheduler/workers/worker_client.py', 'w') as f:
    f.write(content)

print("✅ WorkerClient constructor fixed!")
