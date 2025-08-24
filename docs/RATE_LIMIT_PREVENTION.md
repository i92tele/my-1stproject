# Rate Limit Prevention Strategies

This document outlines strategies for preventing rate limits in the AutoFarming Bot when posting to Telegram channels and groups.

## Currently Implemented

1. **Increased Anti-Ban Delays**
   - Increased sleep time between posts from 3 to 5 seconds
   - Location: `scheduler/core/posting_service.py` in `_post_single_destination_parallel` method
   - Purpose: Prevents triggering Telegram's spam detection

2. **Worker Ban Recording**
   - Added `record_worker_ban` method to track bans
   - Location: `src/database/manager.py`
   - Purpose: Records ban events for analysis and prevention

3. **Staggered Posting Schedule**
   - Added 10-second delay every 5 destinations within a slot
   - Location: `scheduler/core/posting_service.py` in `post_ads` method
   - Purpose: Spreads out posting activity to avoid triggering global rate limits

## Future Enhancements (Beta)

### 1. Adaptive Delays

**Implementation Plan:**
```python
# In _post_single_ad method
if "wait" in error_text or "rate limit" in error_text:
    # Extract wait time if possible, otherwise use default
    wait_seconds = 60
    if "wait of" in error_text and "seconds" in error_text:
        wait_match = re.search(r'wait of (\d+) seconds', error_text)
        if wait_match:
            wait_seconds = int(wait_match.group(1))
    
    logger.info(f"Rate limit detected, cooling down worker {worker.worker_id} for {wait_seconds} seconds")
    await asyncio.sleep(wait_seconds)
```

**Complexity:** Moderate (30 minutes)
**Benefits:** Automatically adapts to Telegram's rate limit requirements

### 2. Worker Cooldown Periods

**Implementation Plan:**
```python
# Add to PostingService class
self.worker_cooldowns = {}  # Track worker cooldowns

async def is_worker_in_cooldown(self, worker_id: int) -> bool:
    """Check if worker is in cooldown period."""
    if worker_id in self.worker_cooldowns:
        cooldown_until = self.worker_cooldowns[worker_id]
        if datetime.now() < cooldown_until:
            # Still in cooldown
            remaining = (cooldown_until - datetime.now()).total_seconds()
            logger.info(f"Worker {worker_id} in cooldown for {remaining:.0f} more seconds")
            return True
        else:
            # Cooldown expired
            del self.worker_cooldowns[worker_id]
    return False

async def set_worker_cooldown(self, worker_id: int, seconds: int = 300):
    """Put a worker in cooldown for specified seconds."""
    cooldown_until = datetime.now() + timedelta(seconds=seconds)
    self.worker_cooldowns[worker_id] = cooldown_until
    logger.info(f"Worker {worker_id} put in cooldown until {cooldown_until}")
```

**Complexity:** Moderate (45 minutes)
**Benefits:** Prevents workers from hitting rate limits repeatedly

### 3. Destination-Specific Rate Limiting

**Implementation Plan:**
```python
# Add to PostingService class
self.destination_cooldowns = {}  # Track destination cooldowns

async def is_destination_in_cooldown(self, destination_id: str) -> bool:
    """Check if destination is in cooldown period."""
    if destination_id in self.destination_cooldowns:
        cooldown_until = self.destination_cooldowns[destination_id]
        if datetime.now() < cooldown_until:
            # Still in cooldown
            remaining = (cooldown_until - datetime.now()).total_seconds()
            logger.info(f"Destination {destination_id} in cooldown for {remaining:.0f} more seconds")
            return True
        else:
            # Cooldown expired
            del self.destination_cooldowns[destination_id]
    return False

async def set_destination_cooldown(self, destination_id: str, seconds: int = 3600):
    """Put a destination in cooldown for specified seconds."""
    cooldown_until = datetime.now() + timedelta(seconds=seconds)
    self.destination_cooldowns[destination_id] = cooldown_until
    logger.info(f"Destination {destination_id} put in cooldown until {cooldown_until}")
```

**Complexity:** Complex (60 minutes)
**Benefits:** Prevents hitting rate limits on specific channels/groups

### 4. Worker Rotation System

**Implementation Plan:**
```python
# Add to PostingService class
self.last_worker_rotation = datetime.now()
self.worker_rotation_index = 0

async def get_rotated_workers(self, all_workers: List[Dict], max_workers_per_cycle: int = 5):
    """Get a subset of workers using rotation strategy."""
    now = datetime.now()
    
    # Rotate workers every hour
    if (now - self.last_worker_rotation).total_seconds() > 3600:
        self.worker_rotation_index = (self.worker_rotation_index + max_workers_per_cycle) % len(all_workers)
        self.last_worker_rotation = now
        logger.info(f"Rotating workers, new index: {self.worker_rotation_index}")
    
    # Get subset of workers for this cycle
    worker_count = min(max_workers_per_cycle, len(all_workers))
    
    # Handle wrap-around
    if self.worker_rotation_index + worker_count > len(all_workers):
        # Need to wrap around
        first_part = all_workers[self.worker_rotation_index:]
        second_part = all_workers[:worker_count - len(first_part)]
        active_workers = first_part + second_part
    else:
        active_workers = all_workers[self.worker_rotation_index:self.worker_rotation_index + worker_count]
    
    logger.info(f"Using {len(active_workers)}/{len(all_workers)} workers for this cycle")
    return active_workers
```

**Complexity:** Moderate (40 minutes)
**Benefits:** Prevents global rate limits by rotating which workers are active

## Implementation Priority

1. Adaptive Delays (most immediate benefit)
2. Worker Cooldown Periods (prevents repeated rate limits)
3. Destination-Specific Rate Limiting (prevents channel-specific issues)
4. Worker Rotation System (long-term stability)

## Testing Recommendations

After implementing each strategy:

1. Run a small test cycle with 1-2 slots and 5-10 destinations
2. Monitor logs for rate limit errors and worker utilization
3. Gradually increase load to test limits
4. Check Telegram client logs for flood wait messages

## References

- [Telegram Bot API Rate Limits](https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this)
- [MTProto API Rate Limits](https://core.telegram.org/api/flood)


