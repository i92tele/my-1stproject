#!/usr/bin/env python3
"""
Improve TON API Reliability
Add multiple TON API fallbacks and improve payment verification
"""

import asyncio
import logging
import aiohttp
import time
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TONAPIImprover:
    """Improve TON API reliability with multiple fallbacks."""
    
    def __init__(self):
        self.ton_apis = [
            {
                'name': 'TON Center API',
                'base_url': 'https://toncenter.com/api/v2',
                'api_key': os.getenv('TON_API_KEY', ''),
                'timeout': 10,
                'priority': 1
            },
            {
                'name': 'TON RPC',
                'base_url': 'https://ton.org/api/v2',
                'api_key': '',
                'timeout': 10,
                'priority': 2
            },
            {
                'name': 'TON API (Alternative)',
                'base_url': 'https://api.ton.org',
                'api_key': '',
                'timeout': 10,
                'priority': 3
            },
            {
                'name': 'TON Blockchain API',
                'base_url': 'https://blockchain.ton.org/api',
                'api_key': '',
                'timeout': 10,
                'priority': 4
            },
            {
                'name': 'TON Explorer API',
                'base_url': 'https://explorer.ton.org/api',
                'api_key': '',
                'timeout': 10,
                'priority': 5
            }
        ]
        self.api_status = {}
        self.last_check = 0
        self.check_interval = 300  # 5 minutes
    
    async def check_api_health(self, api_config: Dict) -> bool:
        """Check if a TON API is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                # Try a simple balance check as health test
                test_address = "EQC_1YoM8RBix9CG6rRjS4-MqW1TglNTurgHqFJXeJjq4uCv"
                url = f"{api_config['base_url']}/getAddressBalance?address={test_address}"
                
                if api_config['api_key']:
                    url += f"&api_key={api_config['api_key']}"
                
                async with session.get(url, timeout=api_config['timeout']) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.warning(f"{api_config['name']} health check failed: {response.status}")
                        return False
        except Exception as e:
            logger.warning(f"{api_config['name']} health check error: {e}")
            return False
    
    async def update_api_status(self):
        """Update API health status."""
        current_time = time.time()
        if current_time - self.last_check < self.check_interval:
            return
        
        logger.info("🔍 Checking TON API health...")
        
        for api_config in self.ton_apis:
            is_healthy = await self.check_api_health(api_config)
            self.api_status[api_config['name']] = {
                'healthy': is_healthy,
                'last_check': current_time,
                'priority': api_config['priority']
            }
            
            status = "✅" if is_healthy else "❌"
            logger.info(f"{status} {api_config['name']}: {'Healthy' if is_healthy else 'Unhealthy'}")
        
        self.last_check = current_time
    
    async def get_working_apis(self) -> List[Dict]:
        """Get list of working TON APIs sorted by priority."""
        await self.update_api_status()
        
        working_apis = []
        for api_config in self.ton_apis:
            if self.api_status.get(api_config['name'], {}).get('healthy', False):
                working_apis.append(api_config)
        
        # Sort by priority (lower number = higher priority)
        working_apis.sort(key=lambda x: x['priority'])
        return working_apis
    
    async def verify_ton_payment_enhanced(self, wallet_address: str, expected_amount: float, 
                                        payment_memo: str, time_window: tuple) -> Dict[str, Any]:
        """Enhanced TON payment verification with multiple API fallbacks."""
        logger.info(f"🔍 Enhanced TON payment verification for {payment_memo}")
        
        working_apis = await self.get_working_apis()
        
        if not working_apis:
            logger.error("❌ No working TON APIs available")
            return {
                'success': False,
                'error': 'No working TON APIs available',
                'apis_tried': len(self.ton_apis),
                'working_apis': 0
            }
        
        logger.info(f"✅ Found {len(working_apis)} working TON APIs")
        
        # Try each working API in priority order
        for api_config in working_apis:
            try:
                logger.info(f"🔍 Trying {api_config['name']}...")
                
                result = await self._verify_with_api(
                    api_config, wallet_address, expected_amount, 
                    payment_memo, time_window
                )
                
                if result['success']:
                    logger.info(f"✅ Payment verified with {api_config['name']}")
                    return {
                        'success': True,
                        'api_used': api_config['name'],
                        'transaction_hash': result.get('tx_hash'),
                        'amount': result.get('amount'),
                        'confirmations': result.get('confirmations')
                    }
                else:
                    logger.warning(f"⚠️ {api_config['name']} failed: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"❌ {api_config['name']} error: {e}")
                continue
        
        logger.error("❌ All TON APIs failed to verify payment")
        return {
            'success': False,
            'error': 'All TON APIs failed',
            'apis_tried': len(working_apis),
            'working_apis': len(working_apis)
        }
    
    async def _verify_with_api(self, api_config: Dict, wallet_address: str, 
                              expected_amount: float, payment_memo: str, 
                              time_window: tuple) -> Dict[str, Any]:
        """Verify payment with a specific TON API."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get wallet transactions
                url = f"{api_config['base_url']}/getTransactions"
                params = {
                    'address': wallet_address,
                    'limit': 50
                }
                
                if api_config['api_key']:
                    params['api_key'] = api_config['api_key']
                
                async with session.get(url, params=params, timeout=api_config['timeout']) as response:
                    if response.status != 200:
                        return {
                            'success': False,
                            'error': f"API returned {response.status}"
                        }
                    
                    data = await response.json()
                    
                    if not data.get('ok'):
                        return {
                            'success': False,
                            'error': data.get('error', 'Unknown API error')
                        }
                    
                    transactions = data.get('result', [])
                    
                    # Check each transaction
                    for tx in transactions:
                        if self._matches_payment_criteria(tx, expected_amount, payment_memo, time_window):
                            return {
                                'success': True,
                                'tx_hash': tx.get('transaction_id'),
                                'amount': tx.get('amount'),
                                'confirmations': tx.get('confirmations', 1)
                            }
                    
                    return {
                        'success': False,
                        'error': 'Payment not found in transactions'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _matches_payment_criteria(self, tx: Dict, expected_amount: float, 
                                 payment_memo: str, time_window: tuple) -> bool:
        """Check if transaction matches payment criteria."""
        try:
            # Check amount (with 3% tolerance)
            tx_amount = float(tx.get('amount', 0))
            amount_tolerance = expected_amount * 0.03
            min_amount = expected_amount - amount_tolerance
            max_amount = expected_amount + amount_tolerance
            
            if not (min_amount <= tx_amount <= max_amount):
                return False
            
            # Check memo
            tx_memo = tx.get('memo', '')
            if payment_memo not in tx_memo:
                return False
            
            # Check time window
            tx_time = int(tx.get('timestamp', 0))
            start_time, end_time = time_window
            
            if not (start_time <= tx_time <= end_time):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def add_api_monitoring(self):
        """Add API monitoring to database."""
        logger.info("🔧 Adding TON API monitoring to database...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create TON API monitoring table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ton_api_monitoring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_name TEXT NOT NULL,
                    api_url TEXT,
                    status TEXT DEFAULT 'unknown',
                    response_time_ms INTEGER,
                    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    priority INTEGER DEFAULT 999,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert API configurations
            for api_config in self.ton_apis:
                cursor.execute('''
                    INSERT OR REPLACE INTO ton_api_monitoring 
                    (api_name, api_url, priority, is_active)
                    VALUES (?, ?, ?, ?)
                ''', (
                    api_config['name'],
                    api_config['base_url'],
                    api_config['priority'],
                    1
                ))
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ton_api_name ON ton_api_monitoring(api_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ton_api_status ON ton_api_monitoring(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ton_api_priority ON ton_api_monitoring(priority)")
            
            conn.commit()
            await db.close()
            
            logger.info("✅ TON API monitoring table created")
            
        except Exception as e:
            logger.error(f"❌ Error adding TON API monitoring: {e}")
    
    async def improve_payment_processor(self):
        """Improve the payment processor with enhanced TON verification."""
        logger.info("🔧 Improving payment processor with enhanced TON verification...")
        
        try:
            # This would modify the existing payment processor
            # to use the enhanced TON verification method
            
            improvement_code = '''
# Add to multi_crypto_payments.py

async def verify_ton_payment_enhanced(self, payment_data):
    """Enhanced TON payment verification with multiple API fallbacks."""
    ton_improver = TONAPIImprover()
    
    wallet_address = payment_data['wallet_address']
    expected_amount = payment_data['amount_crypto']
    payment_memo = payment_data['payment_id']
    
    # Calculate time window
    created_time = datetime.fromisoformat(payment_data['created_at'])
    start_time = int((created_time - timedelta(minutes=30)).timestamp())
    end_time = int((created_time + timedelta(minutes=30)).timestamp())
    
    result = await ton_improver.verify_ton_payment_enhanced(
        wallet_address, expected_amount, payment_memo, (start_time, end_time)
    )
    
    return result['success']
'''
            
            logger.info("✅ Payment processor improvement code generated")
            logger.info("💡 Add the above code to multi_crypto_payments.py")
            
        except Exception as e:
            logger.error(f"❌ Error improving payment processor: {e}")

async def main():
    """Main function."""
    improver = TONAPIImprover()
    
    print("🔧 IMPROVING TON API RELIABILITY")
    print("=" * 50)
    
    # Add API monitoring
    await improver.add_api_monitoring()
    
    # Test API health
    print("\n🔍 Testing TON API health...")
    working_apis = await improver.get_working_apis()
    
    print(f"\n📊 Results:")
    print(f"✅ Working APIs: {len(working_apis)}/{len(improver.ton_apis)}")
    
    if working_apis:
        print("✅ Available APIs:")
        for api in working_apis:
            print(f"  - {api['name']} (Priority: {api['priority']})")
    else:
        print("❌ No working TON APIs found")
    
    # Improve payment processor
    await improver.improve_payment_processor()
    
    print("\n🎯 RECOMMENDATIONS:")
    print("1. Add the improvement code to multi_crypto_payments.py")
    print("2. Restart the bot to apply TON API improvements")
    print("3. Monitor API health in the new monitoring table")
    print("4. Consider adding more TON API endpoints")

if __name__ == "__main__":
    asyncio.run(main())
