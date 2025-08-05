#!/usr/bin/env python3
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv('config/.env')

from config import BotConfig
from database import DatabaseManager

def activate_subscription():
    """Activate user subscription manually."""
    import logging
    logger = logging.getLogger(__name__)
    
    config = BotConfig.load_from_env()
    db = DatabaseManager(config, logger)
    
    # Use synchronous approach
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(db.initialize())
        
        user_id = 7172873873  # Your user ID
        tier = "basic"
        
        print(f"🔧 Activating subscription for user {user_id}...")
        
        # Activate subscription
        loop.run_until_complete(db.activate_subscription(user_id, tier, duration_days=30))
        print("✅ Subscription activated!")
        
        # Update payment status
        loop.run_until_complete(db.update_payment_status("TON_EkV9cyGQC5qLZgvu", "completed"))
        print("✅ Payment marked as completed!")
        
    finally:
        loop.close()

if __name__ == "__main__":
    activate_subscription() 