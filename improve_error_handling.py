#!/usr/bin/env python3
"""
Improve Error Handling and Retry Logic
"""

def add_retry_logic():
    """Add retry logic with exponential backoff."""
    return '''
    async def _retry_api_call(self, api_func, *args, max_retries=3, base_delay=2):
        """Retry API call with exponential backoff."""
        for attempt in range(max_retries):
            try:
                result = await api_func(*args)
                if result:
                    return result
                # If API worked but no payment found, don't retry
                return False
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.warning(f"❌ API failed after {max_retries} attempts: {e}")
                    return False
                
                delay = base_delay * (2 ** attempt)
                self.logger.info(f"⚠️ API attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
        
        return False
'''

def add_api_health_check():
    """Add API health monitoring."""
    return '''
    async def _check_api_health(self, api_name, api_func, test_address):
        """Check if an API is healthy."""
        try:
            # Quick health check
            async with aiohttp.ClientSession() as session:
                if 'tonapi.io' in api_name.lower():
                    url = f"https://tonapi.io/v2/accounts/{test_address}"
                elif 'ton.sh' in api_name.lower():
                    url = f"https://ton.sh/api/v2/accounts/{test_address}"
                else:
                    return True  # Skip health check for other APIs
                
                async with session.get(url, timeout=5) as response:
                    return response.status in [200, 404]  # 404 is OK (address not found)
        except:
            return False
'''

def add_smart_api_selection():
    """Add smart API selection based on health."""
    return '''
    async def _get_healthy_apis(self, ton_apis, test_address):
        """Get list of healthy APIs."""
        healthy_apis = []
        
        for api_name, api_func in ton_apis:
            is_healthy = await self._check_api_health(api_name, api_func, test_address)
            if is_healthy:
                healthy_apis.append((api_name, api_func))
                self.logger.info(f"✅ {api_name} is healthy")
            else:
                self.logger.warning(f"❌ {api_name} is unhealthy, skipping")
        
        return healthy_apis
'''

def main():
    """Main function."""
    print("🔧 IMPROVING ERROR HANDLING")
    print("=" * 50)
    
    print("1. Retry Logic with Exponential Backoff:")
    print(add_retry_logic())
    
    print("\n2. API Health Checking:")
    print(add_api_health_check())
    
    print("\n3. Smart API Selection:")
    print(add_smart_api_selection())
    
    print("\n🎯 BENEFITS:")
    print("✅ Automatic retry on failures")
    print("✅ Exponential backoff (prevents spam)")
    print("✅ Health monitoring")
    print("✅ Smart API selection")
    print("✅ Better error recovery")

if __name__ == "__main__":
    main()
