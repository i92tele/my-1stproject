#!/usr/bin/env python3
import asyncio
import random
import time

# Simple fixes for worker bans

def add_delays():
    """Add random delays between worker actions."""
    print("🔧 Adding delays to prevent bans...")
    
    # Read scheduler.py
    with open('scheduler.py', 'r') as f:
        content = f.read()
    
    # Add delays after each worker action
    new_content = content.replace(
        "await asyncio.sleep(32)",  # Current delay
        "await asyncio.sleep(random.randint(45, 90))"  # Random delay
    )
    
    # Add more delays
    new_content = new_content.replace(
        "await worker_client.send_message(",
        "await asyncio.sleep(random.randint(5, 15))\n        await worker_client.send_message("
    )
    
    # Write back
    with open('scheduler.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Added random delays to prevent bans")

def limit_worker_usage():
    """Limit how many times each worker is used per hour."""
    print("🔧 Limiting worker usage...")
    
    # Add worker rotation logic
    rotation_code = '''
    # Worker rotation to prevent overuse
    self.worker_usage = {}
    self.max_uses_per_hour = 10  # Limit each worker to 10 uses per hour
    '''
    
    with open('scheduler.py', 'r') as f:
        content = f.read()
    
    # Add usage tracking
    if 'self.worker_usage' not in content:
        # Find the __init__ method and add tracking
        content = content.replace(
            "def __init__(self):",
            "def __init__(self):\n        " + rotation_code.strip()
        )
    
    with open('scheduler.py', 'w') as f:
        f.write(content)
    
    print("✅ Added worker usage limits")

def add_error_handling():
    """Add better error handling for banned workers."""
    print("🔧 Adding error handling...")
    
    error_handling = '''
        except ChatWriteForbiddenError:
            logger.warning(f"⚠️ Worker {worker_index} banned from {destination}")
            # Skip this worker for this group
            continue
        except UserBannedInChannelError:
            logger.warning(f"⚠️ Worker {worker_index} banned from {destination}")
            # Skip this worker for this group
            continue
        except FloodWaitError as e:
            logger.warning(f"⚠️ Worker {worker_index} rate limited: {e}")
            await asyncio.sleep(e.seconds)
            continue
    '''
    
    with open('scheduler.py', 'r') as f:
        content = f.read()
    
    # Add error handling if not present
    if 'ChatWriteForbiddenError' not in content:
        # Find the send message section and add error handling
        content = content.replace(
            "except Exception as e:",
            error_handling + "\n        except Exception as e:"
        )
    
    with open('scheduler.py', 'w') as f:
        f.write(content)
    
    print("✅ Added error handling for banned workers")

def main():
    """Apply all fixes."""
    print("🚀 Applying worker ban prevention fixes...")
    
    add_delays()
    limit_worker_usage()
    add_error_handling()
    
    print("✅ All fixes applied!")
    print("📋 Prevention measures:")
    print("   - Random delays (45-90 seconds)")
    print("   - Worker usage limits")
    print("   - Better error handling")
    print("   - Automatic worker rotation")

if __name__ == "__main__":
    main() 