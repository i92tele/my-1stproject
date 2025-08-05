# AutoPoster Documentation

## Overview

The `AutoPoster` class provides a comprehensive automated ad posting system that integrates with your existing database schema and WorkerManager. It handles intelligent scheduling, worker rotation, error handling, and comprehensive logging.

## Features

- **🔄 Automated Scheduling** - Posts ads based on interval settings
- **👥 Worker Rotation** - Uses WorkerManager for intelligent worker selection
- **⏰ Cooldown Respect** - Respects 30-minute worker cooldowns
- **📊 Comprehensive Logging** - Logs all post attempts to database
- **🛡️ Error Handling** - Handles Telegram rate limits and bans gracefully
- **🔄 Retry Logic** - Automatic retry with exponential backoff
- **📈 Status Monitoring** - Real-time status and health monitoring

## Database Integration

### Tables Used

1. **`ad_slots`** - Ad content and scheduling
2. **`slot_destinations`** - Where to post each ad
3. **`ad_posts`** - Logging of all post attempts
4. **`managed_groups`** - Group information and categories
5. **`worker_cooldowns`** - Worker usage tracking

### Key Methods Added

- `get_active_ads_to_send()` - Gets ads ready for posting
- `update_slot_last_sent()` - Updates posting timestamps
- `log_ad_post()` - Logs post attempts and results
- `get_managed_groups()` - Gets available groups

## Usage

### Basic Initialization

```python
from src.auto_poster import AutoPoster
from src.worker_manager import WorkerManager
from src.database import DatabaseManager
import logging

# Initialize components
db_manager = DatabaseManager('data/bot.db', logger)
worker_manager = WorkerManager(db_manager, logger)
await worker_manager.initialize_workers()

# Initialize AutoPoster
auto_poster = AutoPoster(db_manager, worker_manager, logger)
```

### Start Automated Posting

```python
# Start the continuous posting cycle
await auto_poster.start()

# Or run a single cycle manually
ads_to_post = await auto_poster.get_ads_to_post()
for ad_slot in ads_to_post:
    result = await auto_poster.process_ad_slot(ad_slot)
    print(f"Processed: {result}")
```

### Process Single Ad

```python
# Process a specific ad slot
result = await auto_poster.process_single_ad(slot_id=1)
print(f"Result: {result}")
```

### Get Status

```python
# Get comprehensive status
status = await auto_poster.get_status()
print(f"Running: {status['is_running']}")
print(f"Pending ads: {status['pending_ads_count']}")
print(f"Worker health: {status['worker_health']}")
```

## Core Methods

### `async def get_ads_to_post()`
Returns active ad slots that are due for posting based on:
- Slot is active (`is_active = 1`)
- Has content (`content IS NOT NULL`)
- Interval has elapsed since last post

### `async def post_ad(ad_slot, destinations, worker_id)`
Posts a single ad to all destinations using specified worker:
- Handles text and media content
- Logs all attempts to database
- Returns detailed results

### `async def run_posting_cycle()`
Main posting loop that:
- Checks for ads every 60 seconds
- Processes each ad with retry logic
- Handles errors gracefully
- Updates posting timestamps

### `async def handle_posting_errors(error, ad_slot, destination)`
Handles specific Telegram errors:
- **FloodWaitError**: Waits and retries
- **UserBannedInChannelError**: Skips banned channels
- **ChatWriteForbiddenError**: Skips no-permission channels

## Configuration

### Cycle Settings
```python
auto_poster.cycle_interval = 60  # Check every 60 seconds
auto_poster.max_retries = 3      # Max retry attempts
auto_poster.retry_delay = 30     # Seconds between retries
```

### Worker Integration
```python
# AutoPoster automatically uses WorkerManager for:
# - Worker selection (round-robin)
# - Cooldown checking (30-minute minimum)
# - Error handling (flood waits, bans)
# - Health monitoring
```

## Error Handling

### Telegram Rate Limits
- **FloodWaitError**: Automatically waits and retries
- **UserBannedInChannelError**: Logs ban and skips channel
- **ChatWriteForbiddenError**: Skips channels without permission

### Database Errors
- Connection failures are logged
- Graceful degradation with retries
- Comprehensive error logging

### Worker Errors
- Failed workers are marked as unavailable
- Automatic worker rotation
- Health monitoring and alerts

## Logging and Monitoring

### Database Logging
All post attempts are logged to `ad_posts` table:
- Success/failure status
- Error messages
- Worker used
- Destination information
- Timestamps

### Status Monitoring
```python
status = await auto_poster.get_status()
# Returns:
{
    'is_running': bool,
    'cycle_interval': int,
    'worker_health': dict,
    'pending_ads_count': int,
    'pending_ads': list
}
```

### Health Checks
- Worker availability
- Database connectivity
- Posting success rates
- Error frequency

## Integration with Existing Systems

### Database Schema
AutoPoster integrates with your existing tables:
- **`ad_slots`**: Content and scheduling
- **`slot_destinations`**: Posting destinations
- **`ad_posts`**: Activity logging
- **`managed_groups`**: Group management
- **`worker_cooldowns`**: Worker tracking

### WorkerManager Integration
- Uses existing worker rotation
- Respects cooldown periods
- Handles worker errors
- Maintains worker health

### Bot Integration
```python
# In your main bot file
from src.auto_poster import initialize_auto_poster

# Initialize during bot startup
auto_poster = initialize_auto_poster(db_manager, worker_manager, logger)

# Start posting cycle
asyncio.create_task(auto_poster.start())
```

## Best Practices

### 1. Environment Setup
```bash
# Set worker credentials
WORKER_1_API_ID=your_api_id
WORKER_1_API_HASH=your_api_hash
WORKER_1_PHONE=+1234567890
# ... repeat for workers 2 and 4
```

### 2. Database Preparation
```python
# Ensure tables exist
await db_manager.initialize()

# Add managed groups
await db_manager.add_managed_group(
    group_id="-1001234567890",
    group_name="My Group",
    category="general"
)
```

### 3. Monitoring
```python
# Regular health checks
status = await auto_poster.get_status()
if status['worker_health']['failed_workers'] > 0:
    logger.warning("Some workers are failing")

# Monitor posting success
if status['pending_ads_count'] > 10:
    logger.warning("Many ads pending - check intervals")
```

### 4. Error Handling
```python
# Handle AutoPoster errors
try:
    await auto_poster.start()
except Exception as e:
    logger.error(f"AutoPoster error: {e}")
    # Implement recovery logic
```

## Troubleshooting

### Common Issues

1. **No ads posting**: Check slot activation and intervals
2. **Worker errors**: Verify API credentials and session files
3. **Database errors**: Check connectivity and table structure
4. **Rate limits**: Increase intervals or add more workers

### Debug Mode
```python
import logging
logging.getLogger('auto_poster').setLevel(logging.DEBUG)
```

### Manual Testing
```python
# Test single ad posting
result = await auto_poster.process_single_ad(slot_id=1)
print(f"Test result: {result}")

# Check worker health
health = await worker_manager.check_worker_health()
print(f"Worker health: {health}")
```

## Performance Optimization

### Settings for High Volume
```python
# Faster cycles for more ads
auto_poster.cycle_interval = 30  # 30 seconds

# More retries for reliability
auto_poster.max_retries = 5

# Shorter retry delays
auto_poster.retry_delay = 15
```

### Settings for Low Volume
```python
# Slower cycles to reduce load
auto_poster.cycle_interval = 120  # 2 minutes

# Fewer retries
auto_poster.max_retries = 2

# Longer retry delays
auto_poster.retry_delay = 60
```

This AutoPoster system provides a robust, scalable solution for automated ad posting with comprehensive error handling, logging, and monitoring capabilities. 