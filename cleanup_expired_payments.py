#!/usr/bin/env python3
"""
Cleanup Expired Payments
Clean up expired payments to improve performance
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Main function."""
    print("🧹 CLEANING UP EXPIRED PAYMENTS")
    print("=" * 50)
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        # Get connection
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        # Check current payment status
        cursor.execute("SELECT status, COUNT(*) FROM payments GROUP BY status")
        status_counts = cursor.fetchall()
        
        print("📊 CURRENT PAYMENT STATUS:")
        print("-" * 40)
        for status, count in status_counts:
            print(f"  - {status}: {count}")
        
        # Count expired payments
        cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'expired'")
        expired_count = cursor.fetchone()[0]
        
        if expired_count == 0:
            print("\n✅ No expired payments to clean up")
            return
        
        print(f"\n🧹 FOUND {expired_count} EXPIRED PAYMENTS")
        print("-" * 40)
        
        # Show some examples of expired payments
        cursor.execute("""
            SELECT payment_id, user_id, crypto_type, created_at, expires_at
            FROM payments 
            WHERE status = 'expired'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        examples = cursor.fetchall()
        print("📋 Examples of expired payments:")
        for payment in examples:
            payment_id, user_id, crypto_type, created_at, expires_at = payment
            print(f"  - {payment_id}: {crypto_type} payment from user {user_id}")
            print(f"    Created: {created_at}, Expired: {expires_at}")
        
        # Clean up expired payments
        print(f"\n🧹 CLEANING UP...")
        print("-" * 40)
        
        cursor.execute("DELETE FROM payments WHERE status = 'expired'")
        deleted_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ Deleted {deleted_count} expired payments")
        
        # Show new payment status
        cursor.execute("SELECT status, COUNT(*) FROM payments GROUP BY status")
        new_status_counts = cursor.fetchall()
        
        print(f"\n📊 NEW PAYMENT STATUS:")
        print("-" * 40)
        for status, count in new_status_counts:
            print(f"  - {status}: {count}")
        
        # Check database size improvement
        cursor.execute("SELECT COUNT(*) FROM payments")
        total_payments = cursor.fetchone()[0]
        
        print(f"\n📈 PERFORMANCE IMPROVEMENT:")
        print("-" * 40)
        print(f"  - Total payments: {total_payments}")
        print(f"  - Database queries will be faster")
        print(f"  - Reduced storage usage")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
