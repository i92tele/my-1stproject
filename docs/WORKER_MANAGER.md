# WorkerManager Documentation

## Overview

The `WorkerManager` class provides a comprehensive solution for managing multiple Telegram worker accounts with intelligent rotation, cooldown tracking, and error handling. It integrates seamlessly with your existing PostgreSQL database and bot systems.

## Features

- **Round-robin rotation** for even distribution of posts
- **30-minute cooldown** per worker to prevent spam
- **Automatic flood wait handling** with extended cooldowns
- **Ban detection and logging** for channel-specific issues
- **Health monitoring** for all workers
- **Database integration** for persistent cooldown tracking
- **Telethon session management** with automatic reconnections

## Database Schema

### Worker Cooldowns Table
```sql
CREATE TABLE worker_cooldowns (
    worker_id INTEGER PRIMARY KEY,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Worker Activity Log
```sql
CREATE TABLE worker_activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER,
    chat_id INTEGER,
    success BOOLEAN,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES worker_cooldowns(worker_id)
);
```

### Worker Bans
```sql
CREATE TABLE worker_bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER,
    chat_id INTEGER,
    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES worker_cooldowns(worker_id)
);
```

## Environment Variables

Set these environment variables for each worker:

```bash
# Worker 1
WORKER_1_API_ID=your_api_id
WORKER_1_API_HASH=your_api_hash
WORKER_1_PHONE=+1234567890

# Worker 2
WORKER_2_API_ID=your_api_id
WORKER_2_API_HASH=your_api_hash
WORKER_2_PHONE=+1234567891

# Worker 4
WORKER_4_API_ID=your_api_id
WORKER_4_API_HASH=your_api_hash
WORKER_4_PHONE=+1234567893
```

## Usage

### Basic Initialization

```python
from src.worker_manager import WorkerManager
from src.database import DatabaseManager
import logging

# Initialize
db_manager = DatabaseManager('data/bot.db', logger)
worker_manager = WorkerManager(db_manager, logger)

# Initialize workers
await worker_manager.initialize_workers()
```

### Posting Messages

```python
# Post a text message
success = await worker_manager.post_message(
    chat_id=-1001234567890,
    message_text="Hello from WorkerManager! 🚀"
)

# Post with media
success = await worker_manager.post_message(
    chat_id=-1001234567890,
    message_text="Check out this image!",
    file_id="your_file_id"
)
```

### Health Monitoring

```python
# Check worker health
health = await worker_manager.check_worker_health()
print(f"Active workers: {health['active_workers']}")
print(f"Workers in cooldown: {health['workers_in_cooldown']}")

# Get worker stats
stats = worker_manager.get_worker_stats()
print(f"Total workers: {stats['total_workers']}")
```

### Integration with Existing Bot

```python
from src.worker_integration import initialize_worker_integration, get_worker_integration

# Initialize integration
worker_integration = initialize_worker_integration(logger, db_manager)
await worker_integration.initialize()

# Post to slot destinations
results = await worker_integration.post_to_destinations(
    slot_id=1,
    content="Your ad content here",
    file_id="optional_file_id"
)

# Get worker status
status = await worker_integration.get_worker_status()
```

## Core Methods

### `async def initialize_workers()`
Initializes all worker accounts using environment variables. Creates database records for each worker.

### `async def get_available_worker()`
Returns the next available worker based on round-robin rotation and cooldown status.

### `async def mark_worker_used(worker_id)`
Marks a worker as used and updates its cooldown in the database.

### `async def check_worker_health()`
Returns comprehensive health report for all workers including status, availability, and errors.

### `async def post_message(chat_id, message_text, file_id=None)`
Posts a message using an available worker with automatic error handling.

## Error Handling

The WorkerManager handles several types of errors:

- **FloodWaitError**: Automatically extends cooldown based on wait time
- **UserBannedInChannelError**: Logs ban and continues with other workers
- **Connection errors**: Attempts reconnection and logs failures
- **Database errors**: Graceful degradation with logging

## Configuration

### Cooldown Settings
```python
# Default 30-minute cooldown
worker_manager.cooldown_minutes = 30

# Custom cooldown for specific workers
worker_manager.worker_configs[1]['cooldown_minutes'] = 45
```

### Worker IDs
```python
# Default workers: 1, 2, 4
worker_manager.worker_ids = [1, 2, 4]

# Add more workers
worker_manager.worker_ids = [1, 2, 3, 4, 5]
```

## Monitoring and Logging

### Activity Logging
All worker activities are logged to the database:
- Successful posts
- Failed posts with error details
- Worker bans by channel
- Cooldown updates

### Health Monitoring
Regular health checks provide:
- Worker connection status
- Availability status
- Error counts
- Performance metrics

## Best Practices

1. **Environment Variables**: Store worker credentials securely in environment variables
2. **Session Management**: Let Telethon handle session persistence automatically
3. **Error Monitoring**: Regularly check worker health and handle bans
4. **Database Backups**: Backup worker activity logs regularly
5. **Rate Limiting**: Respect Telegram's rate limits and use cooldowns

## Troubleshooting

### Common Issues

1. **Worker not initializing**: Check environment variables and API credentials
2. **Flood wait errors**: Increase cooldown periods or add more workers
3. **Ban errors**: Monitor ban logs and rotate workers more frequently
4. **Database errors**: Check database connectivity and schema

### Debug Mode
```python
import logging
logging.getLogger('worker_manager').setLevel(logging.DEBUG)
```

## Integration with Existing Systems

The WorkerManager integrates with:
- Your existing `DatabaseManager` for persistent storage
- The ad slot system for destination management
- The bot's logging system for consistent error reporting
- The payment system for subscription-based access

This provides a robust, scalable solution for managing multiple Telegram worker accounts with intelligent rotation and comprehensive monitoring. 