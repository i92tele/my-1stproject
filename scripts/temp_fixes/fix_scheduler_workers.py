#!/usr/bin/env python3
"""Fix scheduler worker initialization"""

import re

# Read the current scheduler file
with open('scheduler/core/scheduler.py', 'r') as f:
    content = f.read()

# Replace the _initialize_workers method
old_pattern = r'async def _initialize_workers\(self\):.*?self\.workers = \[\]'
new_method = '''    async def _initialize_workers(self):
        """Initialize worker accounts."""
        logger.info("Initializing worker accounts...")
        
        # Load worker credentials from config
        from ..config.worker_config import WorkerConfig
        from ..workers.worker_client import WorkerClient
        
        worker_config = WorkerConfig()
        worker_creds = worker_config.load_workers_from_env()
        
        # Create worker clients
        self.workers = []
        for creds in worker_creds:
            try:
                worker = WorkerClient(
                    worker_id=creds.worker_id,
                    api_id=creds.api_id,
                    api_hash=creds.api_hash,
                    phone=creds.phone,
                    session_file=creds.session_file
                )
                success = await worker.connect()
                if success:
                    self.workers.append(worker)
                    logger.info(f"Worker {creds.worker_id} initialized successfully")
                else:
                    logger.warning(f"Worker {creds.worker_id} failed to connect")
            except Exception as e:
                logger.error(f"Failed to initialize worker {creds.worker_id}: {e}")
        
        logger.info(f"Initialized {len(self.workers)} workers")'''

# Replace using regex
content = re.sub(old_pattern, new_method, content, flags=re.DOTALL)

# Write back to file
with open('scheduler/core/scheduler.py', 'w') as f:
    f.write(content)

print("✅ Worker initialization fixed!")
