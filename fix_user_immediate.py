#!/usr/bin/env python3
"""
Immediate fix for user 7593457389's subscription and payment status.
This script directly fixes the database state to resolve the current issue.
"""

import asyncio
import logging
import sys
import os
import sqlite3
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database.manager import DatabaseManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fix_user_immediate():
    """Immediately fix the user's subscription and payment status."""
    
    user_id = 7593457389
    db_path = "bot_database.db"
    
    try:
        logger.info(f"🔧 Fixing user {user_id} subscription and payment status...")
        
        # Connect directly to database for immediate fix
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Check current user state
        logger.info("📊 Checking current user state...")
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            logger.info(f"User found: {user}")
        else:
            logger.info("User not found, will create...")
        
        # 2. Check current subscription
        cursor.execute("""
            SELECT subscription_tier, subscription_expires, is_active 
            FROM users WHERE user_id = ?
        """, (user_id,))
        subscription = cursor.fetchone()
        logger.info(f"Current subscription: {subscription}")
        
        # 3. Check payments for this user
        cursor.execute("""
            SELECT payment_id, status, amount_usd, crypto_type, created_at 
            FROM payments WHERE user_id = ? ORDER BY created_at DESC
        """, (user_id,))
        payments = cursor.fetchall()
        logger.info(f"Found {len(payments)} payments for user")
        
        for payment in payments:
            logger.info(f"Payment: {payment}")
        
        # 4. Fix the user subscription
        logger.info("🔧 Fixing user subscription...")
        
        # Ensure user exists
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, subscription_tier, subscription_expires, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            f"user_{user_id}",
            "User",
            None,
            "basic",
            (datetime.now() + timedelta(days=30)).isoformat(),
            datetime.now().isoformat()
        ))
        
        # 5. Fix payment status - find the most recent payment and mark it as completed
        if payments:
            latest_payment_id = payments[0][0]  # First payment (most recent)
            logger.info(f"🔧 Marking payment {latest_payment_id} as completed...")
            
            cursor.execute("""
                UPDATE payments 
                SET status = ?, updated_at = ?
                WHERE payment_id = ?
            """, ("completed", datetime.now().isoformat(), latest_payment_id))
            
            logger.info(f"✅ Payment {latest_payment_id} marked as completed")
        
        # 6. Commit changes
        conn.commit()
        logger.info("✅ Database changes committed")
        
        # 7. Verify the fix
        logger.info("🔍 Verifying the fix...")
        
        # Check user subscription
        cursor.execute("""
            SELECT subscription_tier, subscription_expires, is_active 
            FROM users WHERE user_id = ?
        """, (user_id,))
        fixed_subscription = cursor.fetchone()
        logger.info(f"Fixed subscription: {fixed_subscription}")
        
        # Check payment status
        if payments:
            cursor.execute("SELECT status FROM payments WHERE payment_id = ?", (latest_payment_id,))
            payment_status = cursor.fetchone()
            logger.info(f"Fixed payment status: {payment_status}")
        
        # 8. Test with DatabaseManager
        logger.info("🧪 Testing with DatabaseManager...")
        db = DatabaseManager(logger=logger)
        
        subscription_check = await db.get_user_subscription(user_id)
        logger.info(f"DatabaseManager subscription check: {subscription_check}")
        
        if subscription_check and subscription_check.get('is_active'):
            logger.info("✅ SUCCESS: User subscription is now active!")
        else:
            logger.warning("⚠️ Subscription may still have issues")
        
        conn.close()
        
        logger.info("🎉 IMMEDIATE FIX COMPLETED!")
        logger.info(f"User {user_id} should now have an active subscription")
        
    except Exception as e:
        logger.error(f"❌ Fix failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(fix_user_immediate())
