#!/usr/bin/env python3
"""
Fix Payment System Issues

This script addresses:
1. Missing payment_url column in payments table
2. Unsupported cryptocurrencies (SOL, LTC)
3. Integration between BotConfig and payment system
"""

import asyncio
import logging
import sqlite3
from datetime import datetime
import sys

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

async def fix_crypto_support():
    """Fix support for SOL and LTC cryptocurrencies."""
    logger.info("\n🔧 FIXING CRYPTOCURRENCY SUPPORT")
    
    try:
        # Create or update the crypto_support.py file
        with open('src/payment/crypto_support.py', 'w') as f:
            f.write('''"""
Cryptocurrency Support Module

This module provides support for various cryptocurrencies in the payment system.
"""

import os
from typing import Dict, Optional, List

class CryptoSupport:
    """Cryptocurrency support management."""
    
    def __init__(self):
        """Initialize cryptocurrency support."""
        self._supported_cryptos = {
            'BTC': {
                'name': 'Bitcoin',
                'address_env': 'BTC_ADDRESS',
                'enabled': True
            },
            'ETH': {
                'name': 'Ethereum',
                'address_env': 'ETH_ADDRESS',
                'enabled': True
            },
            'USDT': {
                'name': 'Tether (ERC-20)',
                'address_env': 'USDT_ADDRESS',
                'enabled': True
            },
            'USDC': {
                'name': 'USD Coin (ERC-20)',
                'address_env': 'USDC_ADDRESS',
                'enabled': True
            },
            'SOL': {
                'name': 'Solana',
                'address_env': 'SOL_ADDRESS',
                'enabled': True
            },
            'LTC': {
                'name': 'Litecoin',
                'address_env': 'LTC_ADDRESS',
                'enabled': True
            },
            'TON': {
                'name': 'Toncoin',
                'address_env': 'TON_ADDRESS',
                'enabled': True
            }
        }
    
    def get_supported_cryptos(self) -> List[str]:
        """Get list of supported cryptocurrency codes."""
        return [crypto for crypto, data in self._supported_cryptos.items() 
                if data['enabled'] and os.getenv(data['address_env'])]
    
    def get_crypto_address(self, crypto_code: str) -> Optional[str]:
        """Get wallet address for specified cryptocurrency."""
        if crypto_code not in self._supported_cryptos:
            return None
        
        crypto = self._supported_cryptos[crypto_code]
        if not crypto['enabled']:
            return None
        
        return os.getenv(crypto['address_env'])
    
    def is_supported(self, crypto_code: str) -> bool:
        """Check if cryptocurrency is supported."""
        if crypto_code not in self._supported_cryptos:
            return False
        
        crypto = self._supported_cryptos[crypto_code]
        return crypto['enabled'] and bool(os.getenv(crypto['address_env']))
    
    def get_crypto_info(self, crypto_code: str) -> Optional[Dict]:
        """Get information about a cryptocurrency."""
        if not self.is_supported(crypto_code):
            return None
        
        crypto = self._supported_cryptos[crypto_code]
        return {
            'code': crypto_code,
            'name': crypto['name'],
            'address': os.getenv(crypto['address_env'])
        }
''')
        logger.info("✅ Created/updated crypto_support.py")
        
        # Create directory if it doesn't exist
        import os
        os.makedirs('src/payment', exist_ok=True)
        
        # Create a basic payment processor that uses the new crypto support
        with open('src/payment/payment_processor.py', 'w') as f:
            f.write('''"""
Payment Processor Module

This module handles cryptocurrency payment processing.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from decimal import Decimal

from .crypto_support import CryptoSupport

class PaymentProcessor:
    """Cryptocurrency payment processor."""
    
    def __init__(self, db_manager, logger):
        """Initialize payment processor."""
        self.db = db_manager
        self.logger = logger
        self.crypto_support = CryptoSupport()
        self.payment_timeout_minutes = 60
    
    async def create_payment(self, user_id: int, crypto_code: str, amount_usd: float) -> Dict[str, Any]:
        """Create a new cryptocurrency payment."""
        try:
            # Check if cryptocurrency is supported
            if not self.crypto_support.is_supported(crypto_code):
                raise ValueError(f"Unsupported cryptocurrency: {crypto_code}")
            
            # Get crypto address
            crypto_address = self.crypto_support.get_crypto_address(crypto_code)
            if not crypto_address:
                raise ValueError(f"No address configured for {crypto_code}")
            
            # Generate payment ID
            payment_id = f"{crypto_code}_{uuid.uuid4().hex[:16]}"
            
            # Get crypto price and calculate amount
            crypto_price = await self._get_crypto_price(crypto_code)
            if not crypto_price:
                raise ValueError(f"Could not get price for {crypto_code}")
            
            crypto_amount = Decimal(amount_usd) / Decimal(crypto_price)
            crypto_amount = round(crypto_amount, 8)  # Round to 8 decimal places
            
            # Calculate expiry
            expires_at = datetime.now() + timedelta(minutes=self.payment_timeout_minutes)
            
            # Generate payment URL (simple format for now)
            payment_url = f"crypto:{crypto_code.lower()}:{crypto_address}?amount={crypto_amount}"
            
            # Store payment in database
            success = await self.db.create_payment(
                payment_id=payment_id,
                user_id=user_id,
                amount_usd=amount_usd,
                crypto_type=crypto_code,
                payment_provider="direct",
                pay_to_address=crypto_address,
                expected_amount_crypto=float(crypto_amount),
                payment_url=payment_url,
                expires_at=expires_at,
                attribution_method="amount_only"
            )
            
            if not success:
                raise ValueError("Failed to store payment in database")
            
            return {
                "payment_id": payment_id,
                "crypto_code": crypto_code,
                "amount_usd": amount_usd,
                "amount_crypto": float(crypto_amount),
                "address": crypto_address,
                "payment_url": payment_url,
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error creating payment: {e}")
            return {"error": str(e)}
    
    async def _get_crypto_price(self, crypto_code: str) -> Optional[float]:
        """Get current price of cryptocurrency in USD."""
        # Mock prices for now - in production, use CoinGecko or similar API
        mock_prices = {
            "BTC": 60000.0,
            "ETH": 3000.0,
            "USDT": 1.0,
            "USDC": 1.0,
            "SOL": 100.0,
            "LTC": 80.0,
            "TON": 5.0
        }
        return mock_prices.get(crypto_code)
''')
        logger.info("✅ Created/updated payment_processor.py")
        
        # Update bot_config.py to integrate with the new crypto support
        with open('src/config/bot_config.py', 'r') as f:
            content = f.read()
        
        # Check if we need to update the file
        if "from ..payment.crypto_support import CryptoSupport" not in content:
            # Add import
            import_line = "from typing import List, Optional"
            new_import = "from typing import List, Optional\nfrom ..payment.crypto_support import CryptoSupport"
            content = content.replace(import_line, new_import)
            
            # Update get_crypto_address method
            old_method = """    def get_crypto_address(self, crypto: str = None) -> Optional[str]:
        \"\"\"Get crypto address for payment processing.\"\"\"
        # Map crypto types to environment variable names
        crypto_map = {
            'btc': 'BTC_ADDRESS',
            'eth': 'ETH_ADDRESS', 
            'usdt': 'USDT_ADDRESS',
            'usdc': 'USDC_ADDRESS',
            'ltc': 'LTC_ADDRESS',
            'doge': 'DOGE_ADDRESS',
            'bch': 'BCH_ADDRESS',
            'xrp': 'XRP_ADDRESS',
            'ada': 'ADA_ADDRESS',
            'dot': 'DOT_ADDRESS',
            'link': 'LINK_ADDRESS',
            'uni': 'UNI_ADDRESS',
            'matic': 'MATIC_ADDRESS',
            'sol': 'SOL_ADDRESS',
            'avax': 'AVAX_ADDRESS',
            'atom': 'ATOM_ADDRESS',
            'ftm': 'FTM_ADDRESS',
            'near': 'NEAR_ADDRESS',
            'algo': 'ALGO_ADDRESS',
            'vet': 'VET_ADDRESS'
        }
        
        if crypto:
            # Get specific crypto address
            env_var = crypto_map.get(crypto.lower())
            if env_var:
                return os.getenv(env_var)
            return None
        else:
            # Return first available crypto address
            for crypto_type, env_var in crypto_map.items():
                address = os.getenv(env_var)
                if address:
                    return address
            return None"""
            
            new_method = """    def get_crypto_address(self, crypto: str = None) -> Optional[str]:
        \"\"\"Get crypto address for payment processing.\"\"\"
        # Use CryptoSupport for consistent handling
        crypto_support = CryptoSupport()
        
        if crypto:
            # Get specific crypto address
            return crypto_support.get_crypto_address(crypto.upper())
        else:
            # Return first available crypto address
            supported = crypto_support.get_supported_cryptos()
            if supported:
                return crypto_support.get_crypto_address(supported[0])
            return None"""
            
            content = content.replace(old_method, new_method)
            
            # Write updated content
            with open('src/config/bot_config.py', 'w') as f:
                f.write(content)
            
            logger.info("✅ Updated bot_config.py to use new CryptoSupport")
        else:
            logger.info("✅ bot_config.py already updated")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error fixing cryptocurrency support: {e}")
        return False

async def main():
    """Main function."""
    logger.info("🔧 PAYMENT SYSTEM FIX")
    logger.info("=" * 60)
    
    # Fix database schema
    schema_fixed = await fix_database_schema()
    
    # Fix cryptocurrency support
    crypto_fixed = await fix_crypto_support()
    
    # Summary
    logger.info("\n📋 FIX SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Database Schema: {'✅ Fixed' if schema_fixed else '❌ Failed'}")
    logger.info(f"Cryptocurrency Support: {'✅ Fixed' if crypto_fixed else '❌ Failed'}")
    
    if schema_fixed and crypto_fixed:
        logger.info("\n✅ ALL FIXES APPLIED SUCCESSFULLY")
        logger.info("Restart the bot to apply changes")
    else:
        logger.error("\n❌ SOME FIXES FAILED")
        logger.error("Check the logs for details")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
