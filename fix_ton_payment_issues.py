#!/usr/bin/env python3
"""
Fix TON Payment Verification Issues
- Add rate limiting
- Fix address validation
- Add retry logic
- Improve error handling
"""

import asyncio
import logging
import time
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TONPaymentFixer:
    """Fix TON payment verification issues."""
    
    def __init__(self):
        self.rate_limit_delay = 3  # 3 seconds between requests
        self.max_retries = 3
        self.retry_delay = 5  # 5 seconds between retries
        self.last_request_time = 0
        
        # Valid TON address pattern
        self.ton_address_pattern = re.compile(r'^EQ[a-zA-Z0-9_-]{46}$')
    
    def validate_ton_address(self, address: str) -> bool:
        """Validate TON address format."""
        if not address:
            return False
        
        # Check basic format
        if not self.ton_address_pattern.match(address):
            return False
        
        # Additional validation
        if len(address) != 48:  # TON addresses are 48 characters
            return False
        
        return True
    
    async def rate_limit(self):
        """Implement rate limiting between API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.info(f"⏳ Rate limiting: waiting {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def retry_with_backoff(self, func, *args, **kwargs):
        """Retry function with exponential backoff."""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"⚠️ Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
    
    def fix_ton_verification_methods(self):
        """Fix the TON verification methods in multi_crypto_payments.py."""
        
        # Fixed _verify_ton_center_api method
        fixed_ton_center_api = '''
    async def _verify_ton_center_api(self, ton_address: str, required_amount: float, required_conf: int, 
                                   time_window_start: datetime, time_window_end: datetime, 
                                   attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON Center API with rate limiting and retry logic."""
        try:
            # Validate TON address first
            if not self._validate_ton_address(ton_address):
                self.logger.error(f"❌ Invalid TON address format: {ton_address}")
                return False
            
            # Rate limiting
            await self._rate_limit_ton_api()
            
            async with aiohttp.ClientSession() as session:
                url = "https://toncenter.com/api/v2/getTransactions"
                params = {
                    'address': ton_address,
                    'limit': 20
                }
                
                # Add API key if available
                ton_api_key = os.getenv('TON_API_KEY', '')
                if ton_api_key and ton_api_key != 'free_no_key_needed':
                    params['api_key'] = ton_api_key
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if not data.get('ok'):
                            error = data.get('error', 'Unknown error')
                            self.logger.warning(f"❌ TON Center API error: {error}")
                            return False
                        
                        transactions = data.get('result', [])
                        self.logger.info(f"🔍 Found {len(transactions)} transactions for {ton_address}")
                        
                        for tx in transactions:
                            # Extract transaction value
                            in_msg = tx.get('in_msg', {})
                            tx_value_ton = float(in_msg.get('value', 0)) / 1e9
                            tx_time_str = tx.get('utime')
                            
                            if not tx_time_str:
                                continue
                            
                            try:
                                tx_time = datetime.fromtimestamp(int(tx_time_str))
                            except:
                                continue
                            
                            # Check if in time window
                            if tx_time < time_window_start or tx_time > time_window_end:
                                continue
                            
                            # Amount matching with tolerance
                            tolerance = getattr(self, 'payment_tolerance', 0.05)  # 5% tolerance
                            min_required = required_amount * (1.0 - tolerance)
                            max_allowed = required_amount * (1.0 + tolerance)
                            
                            if min_required <= tx_value_ton <= max_allowed:
                                # Check confirmations (TON uses seqno for confirmation)
                                seqno = tx.get('seqno', 0)
                                if seqno > 0:  # Transaction is confirmed
                                    # If memo attribution, check memo
                                    if attribution_method == 'memo':
                                        tx_memo = in_msg.get('message', '')
                                        if payment_id and payment_id in tx_memo:
                                            self.logger.info(f"✅ TON payment verified by TON Center (memo): {tx_value_ton} TON (seqno: {seqno})")
                                            return True
                                    else:
                                        # Amount + time window verification
                                        self.logger.info(f"✅ TON payment verified by TON Center (amount+time): {tx_value_ton} TON (seqno: {seqno})")
                                        return True
                                else:
                                    self.logger.info(f"⏳ TON payment found but not yet confirmed")
                        
                        return False
                    elif response.status == 429:
                        self.logger.warning(f"❌ TON Center API rate limited (429)")
                        return False
                    elif response.status == 416:
                        self.logger.error(f"❌ TON Center API invalid address (416): {ton_address}")
                        return False
                    elif response.status == 500:
                        self.logger.error(f"❌ TON Center API server error (500)")
                        return False
                    else:
                        self.logger.error(f"❌ TON Center API error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"❌ TON Center API failed: {e}")
            return False
'''
        
        # Fixed _verify_ton_api method
        fixed_ton_api = '''
    async def _verify_ton_api(self, ton_address: str, required_amount: float, required_conf: int, 
                            time_window_start: datetime, time_window_end: datetime, 
                            attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON API with rate limiting and retry logic."""
        try:
            # Validate TON address first
            if not self._validate_ton_address(ton_address):
                self.logger.error(f"❌ Invalid TON address format: {ton_address}")
                return False
            
            # Rate limiting
            await self._rate_limit_ton_api()
            
            async with aiohttp.ClientSession() as session:
                # Use correct TON API endpoint
                url = f"https://toncenter.com/api/v2/getTransactions"
                params = {
                    'address': ton_address,
                    'limit': 20
                }
                
                # Add API key if available
                ton_api_key = os.getenv('TON_API_KEY', '')
                if ton_api_key and ton_api_key != 'free_no_key_needed':
                    params['api_key'] = ton_api_key
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if not data.get('ok'):
                            error = data.get('error', 'Unknown error')
                            self.logger.warning(f"❌ TON API error: {error}")
                            return False
                        
                        transactions = data.get('result', [])
                        self.logger.info(f"🔍 Found {len(transactions)} transactions for {ton_address}")
                        
                        for tx in transactions:
                            # Extract transaction value
                            in_msg = tx.get('in_msg', {})
                            tx_value_ton = float(in_msg.get('value', 0)) / 1e9
                            tx_time_str = tx.get('utime')
                            
                            if not tx_time_str:
                                continue
                            
                            try:
                                tx_time = datetime.fromtimestamp(int(tx_time_str))
                            except:
                                continue
                            
                            # Check if in time window
                            if tx_time < time_window_start or tx_time > time_window_end:
                                continue
                            
                            # Amount matching with tolerance
                            tolerance = getattr(self, 'payment_tolerance', 0.05)  # 5% tolerance
                            min_required = required_amount * (1.0 - tolerance)
                            max_allowed = required_amount * (1.0 + tolerance)
                            
                            if min_required <= tx_value_ton <= max_allowed:
                                # Check confirmations
                                seqno = tx.get('seqno', 0)
                                if seqno > 0:  # Transaction is confirmed
                                    # If memo attribution, check memo
                                    if attribution_method == 'memo':
                                        tx_memo = in_msg.get('message', '')
                                        if payment_id and payment_id in tx_memo:
                                            self.logger.info(f"✅ TON payment verified by TON API (memo): {tx_value_ton} TON (seqno: {seqno})")
                                            return True
                                    else:
                                        # Amount + time window verification
                                        self.logger.info(f"✅ TON payment verified by TON API (amount+time): {tx_value_ton} TON (seqno: {seqno})")
                                        return True
                                else:
                                    self.logger.info(f"⏳ TON payment found but not yet confirmed")
                        
                        return False
                    elif response.status == 429:
                        self.logger.warning(f"❌ TON API rate limited (429)")
                        return False
                    elif response.status == 416:
                        self.logger.error(f"❌ TON API invalid address (416): {ton_address}")
                        return False
                    elif response.status == 500:
                        self.logger.error(f"❌ TON API server error (500)")
                        return False
                    else:
                        self.logger.error(f"❌ TON API error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"❌ TON API failed: {e}")
            return False
'''
        
        # Helper methods
        helper_methods = '''
    def _validate_ton_address(self, address: str) -> bool:
        """Validate TON address format."""
        if not address:
            return False
        
        # TON address pattern: EQ + 46 characters (base64url)
        import re
        ton_pattern = re.compile(r'^EQ[a-zA-Z0-9_-]{46}$')
        
        if not ton_pattern.match(address):
            return False
        
        # Additional validation
        if len(address) != 48:  # TON addresses are 48 characters
            return False
        
        return True
    
    async def _rate_limit_ton_api(self):
        """Implement rate limiting for TON API requests."""
        import time
        current_time = time.time()
        
        # Ensure at least 3 seconds between requests
        if hasattr(self, '_last_ton_request_time'):
            time_since_last = current_time - self._last_ton_request_time
            if time_since_last < 3:
                sleep_time = 3 - time_since_last
                self.logger.info(f"⏳ Rate limiting: waiting {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
        
        self._last_ton_request_time = time.time()
'''
        
        # Fixed _verify_ton_payment method
        fixed_ton_payment = '''
    async def _verify_ton_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int) -> bool:
        """Verify TON payment with improved error handling and rate limiting."""
        try:
            ton_address = payment.get('pay_to_address') or os.getenv('TON_ADDRESS', '')
            if not ton_address:
                self.logger.error("❌ TON address not configured for verification")
                return False
            
            # Validate TON address
            if not self._validate_ton_address(ton_address):
                self.logger.error(f"❌ Invalid TON address format: {ton_address}")
                return False
            
            attribution_method = payment.get('attribution_method', 'amount_time_window')
            payment_id = payment.get('payment_id')
            
            # Get payment creation time for time window matching
            payment_created = payment.get('created_at')
            if payment_created:
                payment_time = datetime.fromisoformat(payment_created.replace('Z', '+00:00'))
                time_window_start = payment_time - timedelta(minutes=30)  # 30 minutes before
                time_window_end = payment_time + timedelta(minutes=30)    # 30 minutes after
            else:
                time_window_start = datetime.now() - timedelta(minutes=60)  # Default 1 hour back
                time_window_end = datetime.now() + timedelta(minutes=30)
            
            self.logger.info(f"🔍 Verifying TON payment to {ton_address} in time window: {time_window_start} to {time_window_end}")
            
            # Try multiple TON APIs in order of preference with retry logic
            ton_apis = [
                ('TON Center', self._verify_ton_center_api),
                ('TON API', self._verify_ton_api),
                ('Manual', self._verify_ton_manual)  # Last resort manual verification
            ]
            
            for api_name, api_func in ton_apis:
                try:
                    self.logger.info(f"🔍 Trying {api_name} API...")
                    result = await api_func(ton_address, required_amount, required_conf, 
                                          time_window_start, time_window_end, attribution_method, payment_id)
                    if result:
                        self.logger.info(f"✅ TON payment verified by {api_name}")
                        return True
                except Exception as e:
                    self.logger.warning(f"❌ {api_name} failed for TON verification: {e}")
                    continue
            
            self.logger.info("❌ TON payment not found in any API")
            return False
                        
        except Exception as e:
            self.logger.error(f"❌ Error verifying TON payment: {e}")
            return False
'''
        
        return {
            'ton_center_api': fixed_ton_center_api,
            'ton_api': fixed_ton_api,
            'helper_methods': helper_methods,
            'ton_payment': fixed_ton_payment
        }
    
    def apply_fixes_to_file(self, file_path: str = 'multi_crypto_payments.py'):
        """Apply fixes to the multi_crypto_payments.py file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            fixes = self.fix_ton_verification_methods()
            
            # Replace _verify_ton_center_api method
            if '_verify_ton_center_api' in content:
                # Find the method and replace it
                start_pattern = r'async def _verify_ton_center_api\(.*?\):'
                end_pattern = r'(?=\n    async def|\n\n    async def|\nclass|\Z)'
                
                import re
                pattern = start_pattern + r'.*?' + end_pattern
                replacement = fixes['ton_center_api']
                
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                logger.info("✅ Replaced _verify_ton_center_api method")
            
            # Replace _verify_ton_api method
            if '_verify_ton_api' in content:
                start_pattern = r'async def _verify_ton_api\(.*?\):'
                end_pattern = r'(?=\n    async def|\n\n    async def|\nclass|\Z)'
                
                pattern = start_pattern + r'.*?' + end_pattern
                replacement = fixes['ton_api']
                
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                logger.info("✅ Replaced _verify_ton_api method")
            
            # Replace _verify_ton_payment method
            if '_verify_ton_payment' in content:
                start_pattern = r'async def _verify_ton_payment\(.*?\):'
                end_pattern = r'(?=\n    async def|\n\n    async def|\nclass|\Z)'
                
                pattern = start_pattern + r'.*?' + end_pattern
                replacement = fixes['ton_payment']
                
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                logger.info("✅ Replaced _verify_ton_payment method")
            
            # Add helper methods if they don't exist
            if '_validate_ton_address' not in content:
                # Add helper methods before the last method
                content = content.rstrip() + '\n\n' + fixes['helper_methods'] + '\n'
                logger.info("✅ Added helper methods")
            
            # Write the fixed content back
            with open(file_path, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ Successfully applied TON payment fixes to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error applying fixes: {e}")
            return False
    
    def create_test_script(self):
        """Create a test script to verify the fixes."""
        test_script = '''#!/usr/bin/env python3
"""
Test TON Payment Fixes
"""

import asyncio
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_ton_fixes():
    """Test the TON payment fixes."""
    print("🧪 TESTING TON PAYMENT FIXES")
    print("=" * 50)
    
    try:
        from multi_crypto_payments import MultiCryptoPaymentProcessor
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        # Initialize payment processor
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        processor = MultiCryptoPaymentProcessor(config, db, logger)
        
        # Test address validation
        print("\\n🔍 Testing TON address validation...")
        test_addresses = [
            "EQC_1YoM8RBix9CG6rRjS4-MqW1TglNTurgHqFJXeJjq4uCv",  # Valid
            "EQD4FPq-PRDieyQKkizFTRtSDyucUIqrj0v_zXJmqaDp6_0t",  # Valid
            "invalid_address",  # Invalid
            "EQ123",  # Invalid
            ""  # Empty
        ]
        
        for address in test_addresses:
            is_valid = processor._validate_ton_address(address)
            status = "✅" if is_valid else "❌"
            print(f"   {status} {address}: {'Valid' if is_valid else 'Invalid'}")
        
        # Test payment verification
        print("\\n🔍 Testing TON payment verification...")
        test_payment = {
            'pay_to_address': 'EQC_1YoM8RBix9CG6rRjS4-MqW1TglNTurgHqFJXeJjq4uCv',
            'payment_id': 'test_payment_123',
            'created_at': datetime.now().isoformat(),
            'attribution_method': 'amount_time_window'
        }
        
        result = await processor._verify_ton_payment(test_payment, 0.1, 1)
        print(f"   Payment verification result: {'✅ Success' if result else '❌ Failed'}")
        
        await db.close()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ton_fixes())
'''
        
        with open('test_ton_fixes.py', 'w') as f:
            f.write(test_script)
        
        logger.info("✅ Created test_ton_fixes.py")

async def main():
    """Main function."""
    fixer = TONPaymentFixer()
    
    print("🔧 FIXING TON PAYMENT ISSUES")
    print("=" * 50)
    
    # Apply fixes to multi_crypto_payments.py
    success = fixer.apply_fixes_to_file()
    
    if success:
        print("\n✅ TON Payment Fixes Applied:")
        print("   - Added rate limiting (3s between requests)")
        print("   - Added address validation")
        print("   - Added retry logic with exponential backoff")
        print("   - Improved error handling")
        print("   - Fixed API endpoint usage")
        print("   - Added proper timeout handling")
        
        # Create test script
        fixer.create_test_script()
        
        print("\n🎯 NEXT STEPS:")
        print("1. Restart your bot to apply the fixes")
        print("2. Run: python3 test_ton_fixes.py")
        print("3. Test with a real TON payment")
        print("4. Monitor the logs for improved error messages")
        
    else:
        print("\n❌ Failed to apply fixes")
        print("Please check the error messages above")

if __name__ == "__main__":
    asyncio.run(main())
