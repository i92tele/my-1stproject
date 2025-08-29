#!/usr/bin/env python3
"""
Add TON API.io Support to Payment Processor
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

async def test_tonapi_io():
    """Test TON API.io with your address."""
    your_address = "UQCOHY_oPfi-3Kot37ViZZ5wI_puavpSCa3Cs-zAd3o73lBK"
    
    print("🔍 TESTING TON API.io")
    print("=" * 50)
    
    # Test endpoints
    endpoints = [
        f"https://tonapi.io/v2/accounts/{your_address}",
        f"https://tonapi.io/v2/accounts/{your_address}/jettons",
        f"https://tonapi.io/v2/accounts/{your_address}/transactions"
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 Testing: {endpoint}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, timeout=10) as response:
                    print(f"   Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ Success: {json.dumps(data, indent=2)[:200]}...")
                    else:
                        print(f"   ❌ Error: {response.status}")
                        
        except Exception as e:
            print(f"   ❌ Exception: {e}")

def add_tonapi_io_to_payment_processor():
    """Add TON API.io verification method to payment processor."""
    
    tonapi_io_method = '''
    async def _verify_tonapi_io(self, ton_address: str, required_amount: float, required_conf: int, 
                               time_window_start: datetime, time_window_end: datetime, 
                               attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON API.io."""
        try:
            # Rate limiting
            await self._rate_limit_ton_api()
            
            async with aiohttp.ClientSession() as session:
                # Get account transactions
                url = f"https://tonapi.io/v2/accounts/{ton_address}/transactions"
                params = {
                    'limit': 20,
                    'archival': False
                }
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        transactions = data.get('transactions', [])
                        self.logger.info(f"🔍 Found {len(transactions)} transactions for {ton_address}")
                        
                        for tx in transactions:
                            # Extract transaction data
                            tx_value_ton = float(tx.get('in_msg', {}).get('value', 0)) / 1e9
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
                                        tx_memo = tx.get('in_msg', {}).get('message', '')
                                        if payment_id and payment_id in tx_memo:
                                            self.logger.info(f"✅ TON payment verified by TON API.io (memo): {tx_value_ton} TON (seqno: {seqno})")
                                            return True
                                    else:
                                        # Amount + time window verification
                                        self.logger.info(f"✅ TON payment verified by TON API.io (amount+time): {tx_value_ton} TON (seqno: {seqno})")
                                        return True
                                else:
                                    self.logger.info(f"⏳ TON payment found but not yet confirmed")
                        
                        return False
                    elif response.status == 429:
                        self.logger.warning(f"❌ TON API.io rate limited (429)")
                        return False
                    elif response.status == 404:
                        self.logger.error(f"❌ TON API.io address not found (404): {ton_address}")
                        return False
                    else:
                        self.logger.error(f"❌ TON API.io error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"❌ TON API.io failed: {e}")
            return False
'''
    
    return tonapi_io_method

def update_ton_verification_method():
    """Update the main TON verification method to include TON API.io."""
    
    updated_verification = '''
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
                ('TON API.io', self._verify_tonapi_io),  # New primary API
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
    
    return updated_verification

async def main():
    """Main function."""
    print("🔧 ADDING TON API.io SUPPORT")
    print("=" * 50)
    
    # Test TON API.io first
    print("1. Testing TON API.io connectivity...")
    await test_tonapi_io()
    
    # Show what to add
    print("\n2. TON API.io verification method:")
    print(add_tonapi_io_to_payment_processor())
    
    print("\n3. Updated verification method:")
    print(update_ton_verification_method())
    
    print("\n🎯 NEXT STEPS:")
    print("1. Add the TON API.io method to multi_crypto_payments.py")
    print("2. Update the _verify_ton_payment method")
    print("3. Test with your address")
    print("4. No environment variables needed (works without API key)")

if __name__ == "__main__":
    asyncio.run(main())
