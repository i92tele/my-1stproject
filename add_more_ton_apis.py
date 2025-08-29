#!/usr/bin/env python3
"""
Add More TON API Fallbacks
"""

def add_ton_sh_api():
    """Add TON.sh API verification method."""
    return '''
    async def _verify_ton_sh_api(self, ton_address: str, required_amount: float, required_conf: int, 
                                time_window_start: datetime, time_window_end: datetime, 
                                attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON.sh API."""
        try:
            await self._rate_limit_ton_api()
            
            async with aiohttp.ClientSession() as session:
                url = f"https://ton.sh/api/v2/accounts/{ton_address}/transactions"
                params = {'limit': 20}
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        transactions = data.get('transactions', [])
                        self.logger.info(f"🔍 TON.sh found {len(transactions)} transactions")
                        
                        for tx in transactions:
                            tx_value_ton = float(tx.get('amount', 0)) / 1e9
                            tx_time_str = tx.get('timestamp')
                            
                            if tx_time_str:
                                tx_time = datetime.fromtimestamp(int(tx_time_str))
                                if time_window_start <= tx_time <= time_window_end:
                                    tolerance = getattr(self, 'payment_tolerance', 0.05)
                                    min_required = required_amount * (1.0 - tolerance)
                                    max_allowed = required_amount * (1.0 + tolerance)
                                    
                                    if min_required <= tx_value_ton <= max_allowed:
                                        self.logger.info(f"✅ TON payment verified by TON.sh: {tx_value_ton} TON")
                                        return True
                        
                        return False
                    else:
                        self.logger.warning(f"❌ TON.sh API error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"❌ TON.sh API failed: {e}")
            return False
'''

def add_ton_whales_api():
    """Add TON Whales API verification method."""
    return '''
    async def _verify_ton_whales_api(self, ton_address: str, required_amount: float, required_conf: int, 
                                   time_window_start: datetime, time_window_end: datetime, 
                                   attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON Whales API."""
        try:
            await self._rate_limit_ton_api()
            
            async with aiohttp.ClientSession() as session:
                url = f"https://tonwhales.com/api/accounts/{ton_address}/transactions"
                params = {'limit': 20}
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        transactions = data.get('data', [])
                        self.logger.info(f"🔍 TON Whales found {len(transactions)} transactions")
                        
                        for tx in transactions:
                            tx_value_ton = float(tx.get('amount', 0)) / 1e9
                            tx_time_str = tx.get('timestamp')
                            
                            if tx_time_str:
                                tx_time = datetime.fromtimestamp(int(tx_time_str))
                                if time_window_start <= tx_time <= time_window_end:
                                    tolerance = getattr(self, 'payment_tolerance', 0.05)
                                    min_required = required_amount * (1.0 - tolerance)
                                    max_allowed = required_amount * (1.0 + tolerance)
                                    
                                    if min_required <= tx_value_ton <= max_allowed:
                                        self.logger.info(f"✅ TON payment verified by TON Whales: {tx_value_ton} TON")
                                        return True
                        
                        return False
                    else:
                        self.logger.warning(f"❌ TON Whales API error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"❌ TON Whales API failed: {e}")
            return False
'''

def add_ton_labs_api():
    """Add TON Labs API verification method."""
    return '''
    async def _verify_ton_labs_api(self, ton_address: str, required_amount: float, required_conf: int, 
                                 time_window_start: datetime, time_window_end: datetime, 
                                 attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON Labs API."""
        try:
            await self._rate_limit_ton_api()
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.tonlabs.io/accounts/{ton_address}/transactions"
                params = {'limit': 20}
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        transactions = data.get('transactions', [])
                        self.logger.info(f"🔍 TON Labs found {len(transactions)} transactions")
                        
                        for tx in transactions:
                            tx_value_ton = float(tx.get('amount', 0)) / 1e9
                            tx_time_str = tx.get('timestamp')
                            
                            if tx_time_str:
                                tx_time = datetime.fromtimestamp(int(tx_time_str))
                                if time_window_start <= tx_time <= time_window_end:
                                    tolerance = getattr(self, 'payment_tolerance', 0.05)
                                    min_required = required_amount * (1.0 - tolerance)
                                    max_allowed = required_amount * (1.0 + tolerance)
                                    
                                    if min_required <= tx_value_ton <= max_allowed:
                                        self.logger.info(f"✅ TON payment verified by TON Labs: {tx_value_ton} TON")
                                        return True
                        
                        return False
                    else:
                        self.logger.warning(f"❌ TON Labs API error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"❌ TON Labs API failed: {e}")
            return False
'''

def update_api_list():
    """Update the API list with more fallbacks."""
    return '''
            # Try multiple TON APIs in order of preference with retry logic
            ton_apis = [
                ('TON API.io', self._verify_tonapi_io),  # Primary API
                ('TON.sh', self._verify_ton_sh_api),     # Backup 1
                ('TON Whales', self._verify_ton_whales_api),  # Backup 2
                ('TON Labs', self._verify_ton_labs_api),      # Backup 3
                ('TON Center', self._verify_ton_center_api),  # Backup 4
                ('TON API', self._verify_ton_api),            # Backup 5
                ('Manual', self._verify_ton_manual)           # Last resort
            ]
'''

def main():
    """Main function."""
    print("🔧 ADDING MORE TON API FALLBACKS")
    print("=" * 50)
    
    print("1. TON.sh API method:")
    print(add_ton_sh_api())
    
    print("\n2. TON Whales API method:")
    print(add_ton_whales_api())
    
    print("\n3. TON Labs API method:")
    print(add_ton_labs_api())
    
    print("\n4. Updated API list:")
    print(update_api_list())
    
    print("\n🎯 BENEFITS:")
    print("✅ 7 API fallbacks instead of 3")
    print("✅ Higher success rate")
    print("✅ Better reliability")
    print("✅ All free APIs")

if __name__ == "__main__":
    main()
