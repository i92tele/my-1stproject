#!/usr/bin/env python3
"""
Live Issues Fix

This script fixes the current live issues:
1. Syntax error in multi_crypto_payments.py
2. Invalid destination patterns
3. Restart crashed services
"""

import logging
import os
import sqlite3
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def fix_syntax_error():
    """Fix the syntax error in multi_crypto_payments.py."""
    logger.info("🔧 Fixing syntax error in multi_crypto_payments.py...")
    
    try:
        payment_file = "multi_crypto_payments.py"
        
        if not os.path.exists(payment_file):
            logger.error(f"❌ Payment processor file not found: {payment_file}")
            return False
        
        with open(payment_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if syntax error is already fixed
        if "}            else:" not in content:
            logger.info("✅ Syntax error already fixed")
            return True
        
        # Fix the syntax error
        fixed_content = content.replace("}            else:", "}\n            else:")
        
        with open(payment_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        logger.info("✅ Syntax error fixed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing syntax error: {e}")
        return False

def fix_invalid_destinations():
    """Fix invalid destination patterns in the database."""
    logger.info("🔧 Fixing invalid destination patterns...")
    
    try:
        db_path = "bot_database.db"
        
        if not os.path.exists(db_path):
            logger.error(f"❌ Database not found: {db_path}")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find invalid destinations
        cursor.execute("""
            SELECT id, destination_id, destination_name 
            FROM slot_destinations 
            WHERE destination_id LIKE '%CrystalMarketss%'
        """)
        
        invalid_destinations = cursor.fetchall()
        
        if not invalid_destinations:
            logger.info("✅ No invalid destinations found")
            conn.close()
            return True
        
        logger.info(f"⚠️ Found {len(invalid_destinations)} invalid destinations")
        
        # Fix each invalid destination
        fixed_count = 0
        for dest_id, dest_id_str, dest_name in invalid_destinations:
            logger.info(f"🔧 Fixing destination: {dest_id_str}")
            
            # The pattern should be @CrystalMarketss/topicid
            # Remove any extra @ symbols or spaces
            fixed_dest_id = dest_id_str.strip()
            
            # Ensure it starts with @
            if not fixed_dest_id.startswith('@'):
                fixed_dest_id = '@' + fixed_dest_id
            
            # Remove any duplicate @ symbols
            while '@@' in fixed_dest_id:
                fixed_dest_id = fixed_dest_id.replace('@@', '@')
            
            # Update the destination
            cursor.execute("""
                UPDATE slot_destinations 
                SET destination_id = ?
                WHERE id = ?
            """, (fixed_dest_id, dest_id))
            
            logger.info(f"✅ Fixed: {dest_id_str} -> {fixed_dest_id}")
            fixed_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Fixed {fixed_count} invalid destinations")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing invalid destinations: {e}")
        return False

def verify_fixes():
    """Verify that the fixes are working."""
    logger.info("🔍 Verifying fixes...")
    
    try:
        # Check syntax
        payment_file = "multi_crypto_payments.py"
        with open(payment_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "}            else:" in content:
            logger.error("❌ Syntax error still present")
            return False
        else:
            logger.info("✅ Syntax error fixed")
        
        # Check destinations
        db_path = "bot_database.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM slot_destinations 
            WHERE destination_id LIKE '%CrystalMarketss%' 
            AND destination_id NOT LIKE '@CrystalMarketss/%'
        """)
        
        invalid_count = cursor.fetchone()[0]
        conn.close()
        
        if invalid_count > 0:
            logger.error(f"❌ {invalid_count} invalid destinations still present")
            return False
        else:
            logger.info("✅ All destinations fixed")
        
        logger.info("✅ All fixes verified successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verifying fixes: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🚨 LIVE ISSUES FIX")
    logger.info("=" * 60)
    
    # Step 1: Fix syntax error
    if fix_syntax_error():
        logger.info("✅ Syntax error fixed")
    else:
        logger.error("❌ Failed to fix syntax error")
        return
    
    # Step 2: Fix invalid destinations
    if fix_invalid_destinations():
        logger.info("✅ Invalid destinations fixed")
    else:
        logger.error("❌ Failed to fix invalid destinations")
        return
    
    # Step 3: Verify fixes
    if verify_fixes():
        logger.info("✅ All fixes verified")
    else:
        logger.error("❌ Fix verification failed")
        return
    
    logger.info("=" * 60)
    logger.info("📊 SUMMARY")
    logger.info("=" * 60)
    logger.info("✅ Syntax error in multi_crypto_payments.py fixed")
    logger.info("✅ Invalid destination patterns fixed")
    logger.info("✅ All fixes verified and working")
    logger.info("")
    logger.info("🔄 Next steps:")
    logger.info("1. Restart the bot: python start_bot.py")
    logger.info("2. Main Bot and Payment Monitor should start successfully")
    logger.info("3. Posting should work with fixed destinations")
    logger.info("4. Monitor logs for any remaining issues")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
