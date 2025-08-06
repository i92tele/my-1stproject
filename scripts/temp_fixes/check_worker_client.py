#!/usr/bin/env python3
"""Check the actual WorkerClient constructor"""

# Read the current worker client file
with open('scheduler/workers/worker_client.py', 'r') as f:
    content = f.read()

# Find the constructor
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'def __init__' in line:
        print(f"Constructor found at line {i+1}: {line}")
        # Print the next few lines
        for j in range(i+1, min(i+15, len(lines))):
            if lines[j].strip() and not lines[j].strip().startswith('#'):
                print(f"Line {j+1}: {lines[j]}")
            if 'self.client = None' in lines[j]:
                break
        break
