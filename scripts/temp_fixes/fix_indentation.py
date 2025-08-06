#!/usr/bin/env python3
"""Fix indentation in scheduler file"""

# Read the current scheduler file
with open('scheduler/core/scheduler.py', 'r') as f:
    content = f.read()

# Fix the indentation issue
lines = content.split('\n')
fixed_lines = []

for i, line in enumerate(lines):
    if 'async def _initialize_workers(self):' in line:
        # This is the function definition
        fixed_lines.append(line)
        # Add the docstring with proper indentation
        fixed_lines.append('        """Initialize worker accounts."""')
        fixed_lines.append('        logger.info("Initializing worker accounts...")')
        fixed_lines.append('')
        fixed_lines.append('        # Load worker credentials from config')
        fixed_lines.append('        from ..config.worker_config import WorkerConfig')
        fixed_lines.append('        from ..workers.worker_client import WorkerClient')
        fixed_lines.append('')
        fixed_lines.append('        worker_config = WorkerConfig()')
        fixed_lines.append('        worker_creds = worker_config.load_workers_from_env()')
        fixed_lines.append('')
        fixed_lines.append('        # Create worker clients')
        fixed_lines.append('        self.workers = []')
        fixed_lines.append('        for creds in worker_creds:')
        fixed_lines.append('            try:')
        fixed_lines.append('                worker = WorkerClient(')
        fixed_lines.append('                    worker_id=creds.worker_id,')
        fixed_lines.append('                    api_id=creds.api_id,')
        fixed_lines.append('                    api_hash=creds.api_hash,')
        fixed_lines.append('                    phone=creds.phone,')
        fixed_lines.append('                    session_file=creds.session_file')
        fixed_lines.append('                )')
        fixed_lines.append('                success = await worker.connect()')
        fixed_lines.append('                if success:')
        fixed_lines.append('                    self.workers.append(worker)')
        fixed_lines.append('                    logger.info(f"Worker {creds.worker_id} initialized successfully")')
        fixed_lines.append('                else:')
        fixed_lines.append('                    logger.warning(f"Worker {creds.worker_id} failed to connect")')
        fixed_lines.append('            except Exception as e:')
        fixed_lines.append('                logger.error(f"Failed to initialize worker {creds.worker_id}: {e}")')
        fixed_lines.append('')
        fixed_lines.append('        logger.info(f"Initialized {len(self.workers)} workers")')
        
        # Skip the next few lines that were part of the old method
        j = i + 1
        while j < len(lines) and (lines[j].strip().startswith('"""') or 
                                 lines[j].strip().startswith('logger.info') or
                                 lines[j].strip().startswith('#') or
                                 lines[j].strip().startswith('from') or
                                 lines[j].strip().startswith('worker_config') or
                                 lines[j].strip().startswith('worker_creds') or
                                 lines[j].strip().startswith('self.workers') or
                                 lines[j].strip().startswith('for creds') or
                                 lines[j].strip().startswith('try:') or
                                 lines[j].strip().startswith('worker =') or
                                 lines[j].strip().startswith('success =') or
                                 lines[j].strip().startswith('if success:') or
                                 lines[j].strip().startswith('self.workers.append') or
                                 lines[j].strip().startswith('logger.info') or
                                 lines[j].strip().startswith('else:') or
                                 lines[j].strip().startswith('logger.warning') or
                                 lines[j].strip().startswith('except Exception') or
                                 lines[j].strip().startswith('logger.error') or
                                 lines[j].strip().startswith('logger.info(f"Initialized') or
                                 lines[j].strip() == ''):
            j += 1
        # Continue from the line after the old method
        i = j - 1
    else:
        fixed_lines.append(line)

# Write the fixed content
with open('scheduler/core/scheduler.py', 'w') as f:
    f.write('\n'.join(fixed_lines))

print("✅ Indentation fixed!")
