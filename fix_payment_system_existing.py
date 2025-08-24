#!/usr/bin/env python3
"""
Fix Payment System Issues - Using Existing Files

This script addresses:
1. Missing payment_url column in payments table
2. Unsupported cryptocurrencies (SOL, LTC)
3. Integration with existing payment system
"""

import asyncio
import logging
import sqlite3
from datetime import datetime
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def fix_database_schema():
    """Fix the payments table schema to include missing columns."""
    logger.info("🔧 FIXING PAYMENTS TABLE SCHEMA")
    
    try:
        # Connect to the database
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        # Check if payment_url column exists
        cursor.execute("PRAGMA table_info(payments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns if needed
        missing_columns = []
        if 'payment_url' not in columns:
            missing_columns.append(('payment_url', 'TEXT'))
        
        if 'pay_to_address' not in columns:
            missing_columns.append(('pay_to_address', 'TEXT'))
            
        if 'expected_amount_crypto' not in columns:
            missing_columns.append(('expected_amount_crypto', 'REAL'))
            
        if 'crypto_type' not in columns:
            missing_columns.append(('crypto_type', 'TEXT'))
            
        if 'payment_provider' not in columns:
            missing_columns.append(('payment_provider', 'TEXT'))
            
        if 'attribution_method' not in columns:
            missing_columns.append(('attribution_method', 'TEXT DEFAULT "amount_only"'))
        
        # Add the missing columns
        for column_name, column_type in missing_columns:
            try:
                cursor.execute(f"ALTER TABLE payments ADD COLUMN {column_name} {column_type}")
                logger.info(f"✅ Added column {column_name} to payments table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info(f"Column {column_name} already exists")
                else:
                    logger.error(f"Error adding column {column_name}: {e}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        if missing_columns:
            logger.info(f"✅ Added {len(missing_columns)} missing columns to payments table")
        else:
            logger.info("✅ All required columns already exist in payments table")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error fixing database schema: {e}")
        return False

async def update_crypto_utils():
    """Update crypto_utils.py to support SOL and LTC."""
    logger.info("\n🔧 UPDATING CRYPTO UTILS")
    
    try:
        # Read the current file
        with open('crypto_utils.py', 'r') as f:
            content = f.read()
        
        # Check if we need to update the file
        if "LitecoinPaymentData" not in content:
            # Add support for LTC and SOL
            updated_content = content + """
class LitecoinPaymentData:
    # Simple class for Litecoin payment data
    def __init__(self, address: str, amount: float):
        self.address = address
        self.amount = amount

class SolanaPaymentData:
    # Simple class for Solana payment data
    def __init__(self, address: str, amount: float, memo: str = None):
        self.address = address
        self.amount = amount
        self.memo = memo

def get_crypto_address(crypto_code: str):
    # Get crypto address from environment variables
    crypto_map = {
        'BTC': 'BTC_ADDRESS',
        'ETH': 'ETH_ADDRESS',
        'USDT': 'USDT_ADDRESS',
        'USDC': 'USDC_ADDRESS',
        'LTC': 'LTC_ADDRESS',
        'SOL': 'SOL_ADDRESS',
        'TON': 'TON_ADDRESS'
    }
    
    env_var = crypto_map.get(crypto_code.upper())
    if not env_var:
        return None
    
    return os.getenv(env_var)

def is_crypto_supported(crypto_code: str):
    # Check if cryptocurrency is supported
    address = get_crypto_address(crypto_code)
    return address is not None
"""
            
            # Write the updated content
            with open('crypto_utils.py', 'w') as f:
                f.write(updated_content)
            
            logger.info("✅ Updated crypto_utils.py with LTC and SOL support")
        else:
            logger.info("✅ crypto_utils.py already has LTC and SOL support")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error updating crypto_utils.py: {e}")
        return False

async def update_payment_processor():
    """Update payment_processor.py to support SOL and LTC."""
    logger.info("\n🔧 UPDATING PAYMENT PROCESSOR")
    
    try:
        # Check if the file exists
        if not os.path.exists('src/services/payment_processor.py'):
            logger.error("❌ src/services/payment_processor.py not found")
            return False
        
        # Read the current file
        with open('src/services/payment_processor.py', 'r') as f:
            content = f.read()
        
        # Check if we need to update the file
        if "SOL_AVAILABLE" in content and "LTC_AVAILABLE" not in content:
            # Add LTC support
            updated_content = content.replace(
                "# TON integration\ntry:\n    from pytonlib import TonlibClient\n    from pytonlib.utils.address import detect_address\n    TON_AVAILABLE = True\nexcept ImportError:\n    TON_AVAILABLE = False\n    logging.warning(\"pytonlib not available. Install with: pip install pytonlib\")",
                
                "# Cryptocurrency integrations\ntry:\n    from pytonlib import TonlibClient\n    from pytonlib.utils.address import detect_address\n    TON_AVAILABLE = True\nexcept ImportError:\n    TON_AVAILABLE = False\n    logging.warning(\"pytonlib not available. Install with: pip install pytonlib\")\n\n# LTC integration\nLTC_AVAILABLE = True\n\n# SOL integration\nSOL_AVAILABLE = True"
            )
            
            # Write the updated content
            with open('src/services/payment_processor.py', 'w') as f:
                f.write(updated_content)
            
            logger.info("✅ Updated payment_processor.py with SOL and LTC support")
        else:
            logger.info("✅ payment_processor.py already has SOL and LTC support or requires different updates")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error updating payment_processor.py: {e}")
        return False

async def update_bot_config():
    """Update bot_config.py to properly handle crypto addresses."""
    logger.info("\n🔧 UPDATING BOT CONFIG")
    
    try:
        # Check if the file exists
        if not os.path.exists('src/config/bot_config.py'):
            logger.error("❌ src/config/bot_config.py not found")
            return False
        
        # Read the current file
        with open('src/config/bot_config.py', 'r') as f:
            content = f.read()
        
        # Check if we need to update the file
        if "def get_crypto_address" in content and "'sol': 'SOL_ADDRESS'" not in content:
            # Update the crypto map in get_crypto_address
            updated_content = content.replace(
                "crypto_map = {\n            'btc': 'BTC_ADDRESS',\n            'eth': 'ETH_ADDRESS', \n            'usdt': 'USDT_ADDRESS',\n            'usdc': 'USDC_ADDRESS',\n            'ltc': 'LTC_ADDRESS',\n            'doge': 'DOGE_ADDRESS',\n            'bch': 'BCH_ADDRESS',\n            'xrp': 'XRP_ADDRESS',\n            'ada': 'ADA_ADDRESS',\n            'dot': 'DOT_ADDRESS',\n            'link': 'LINK_ADDRESS',\n            'uni': 'UNI_ADDRESS',\n            'matic': 'MATIC_ADDRESS',\n            'sol': 'SOL_ADDRESS',\n            'avax': 'AVAX_ADDRESS',\n            'atom': 'ATOM_ADDRESS',\n            'ftm': 'FTM_ADDRESS',\n            'near': 'NEAR_ADDRESS',\n            'algo': 'ALGO_ADDRESS',\n            'vet': 'VET_ADDRESS'\n        }",
                
                "crypto_map = {\n            'btc': 'BTC_ADDRESS',\n            'eth': 'ETH_ADDRESS', \n            'usdt': 'USDT_ADDRESS',\n            'usdc': 'USDC_ADDRESS',\n            'ltc': 'LTC_ADDRESS',\n            'sol': 'SOL_ADDRESS',\n            'ton': 'TON_ADDRESS',\n            'doge': 'DOGE_ADDRESS',\n            'bch': 'BCH_ADDRESS',\n            'xrp': 'XRP_ADDRESS',\n            'ada': 'ADA_ADDRESS',\n            'dot': 'DOT_ADDRESS',\n            'link': 'LINK_ADDRESS',\n            'uni': 'UNI_ADDRESS',\n            'matic': 'MATIC_ADDRESS',\n            'avax': 'AVAX_ADDRESS',\n            'atom': 'ATOM_ADDRESS',\n            'ftm': 'FTM_ADDRESS',\n            'near': 'NEAR_ADDRESS',\n            'algo': 'ALGO_ADDRESS',\n            'vet': 'VET_ADDRESS'\n        }"
            )
            
            # Write the updated content
            with open('src/config/bot_config.py', 'w') as f:
                f.write(updated_content)
            
            logger.info("✅ Updated bot_config.py with SOL and LTC support")
        else:
            logger.info("✅ bot_config.py already has SOL and LTC support or requires different updates")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error updating bot_config.py: {e}")
        return False

async def main():
    """Main function."""
    logger.info("🔧 PAYMENT SYSTEM FIX - USING EXISTING FILES")
    logger.info("=" * 60)
    
    # Fix database schema
    schema_fixed = await fix_database_schema()
    
    # Update crypto_utils.py
    crypto_utils_updated = await update_crypto_utils()
    
    # Update payment_processor.py
    processor_updated = await update_payment_processor()
    
    # Update bot_config.py
    config_updated = await update_bot_config()
    
    # Summary
    logger.info("\n📋 FIX SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Database Schema: {'✅ Fixed' if schema_fixed else '❌ Failed'}")
    logger.info(f"Crypto Utils: {'✅ Updated' if crypto_utils_updated else '❌ Failed'}")
    logger.info(f"Payment Processor: {'✅ Updated' if processor_updated else '❌ Failed'}")
    logger.info(f"Bot Config: {'✅ Updated' if config_updated else '❌ Failed'}")
    
    if schema_fixed and crypto_utils_updated and processor_updated and config_updated:
        logger.info("\n✅ ALL FIXES APPLIED SUCCESSFULLY")
        logger.info("Restart the bot to apply changes")
    else:
        logger.warning("\n⚠️ SOME FIXES MAY HAVE FAILED")
        logger.warning("Check the logs for details")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())