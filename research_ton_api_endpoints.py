#!/usr/bin/env python3
"""
Research TON API Endpoints
Test different TON API endpoints to find the correct ones that work
"""

import asyncio
import aiohttp
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TONAPIEndpointResearcher:
    """Research and test TON API endpoints."""
    
    def __init__(self):
        self.test_address = "EQC_1YoM8RBix9CG6rRjS4-MqW1TglNTurgHqFJXeJjq4uCv"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, api_name: str, url: str, description: str = ""):
        """Test a specific API endpoint."""
        try:
            logger.info(f"🔍 Testing {api_name}: {url}")
            
            async with self.session.get(url, timeout=10) as response:
                status = response.status
                if status == 200:
                    data = await response.json()
                    logger.info(f"✅ {api_name}: SUCCESS (200)")
                    logger.info(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    return True
                else:
                    logger.warning(f"❌ {api_name}: FAILED ({status})")
                    return False
        except Exception as e:
            logger.error(f"❌ {api_name}: ERROR - {e}")
            return False
    
    async def research_ton_apis(self):
        """Research all TON API endpoints."""
        logger.info("🔬 RESEARCHING TON API ENDPOINTS")
        logger.info("=" * 50)
        
        # Test addresses to use
        test_addresses = [
            "EQC_1YoM8RBix9CG6rRjS4-MqW1TglNTurgHqFJXeJjq4uCv",
            "EQD4FPq-PRDieyQKkizFTRtSDyucUIqrj0v_zXJmqaDp6_0t"
        ]
        
        results = {}
        
        for address in test_addresses:
            logger.info(f"\n📋 Testing with address: {address}")
            logger.info("-" * 40)
            
            # TON.sh API endpoints to test
            ton_sh_endpoints = [
                f"https://ton.sh/api/v2/accounts/{address}/transactions",
                f"https://ton.sh/api/v1/accounts/{address}/transactions",
                f"https://ton.sh/api/accounts/{address}/transactions",
                f"https://api.ton.sh/accounts/{address}/transactions",
                f"https://ton.sh/api/v2/accounts/{address}",
                f"https://ton.sh/api/v1/accounts/{address}",
                f"https://ton.sh/api/accounts/{address}"
            ]
            
            # TON Whales API endpoints to test
            ton_whales_endpoints = [
                f"https://tonwhales.com/api/accounts/{address}/transactions",
                f"https://api.tonwhales.com/accounts/{address}/transactions",
                f"https://tonwhales.com/api/v1/accounts/{address}/transactions",
                f"https://tonwhales.com/api/v2/accounts/{address}/transactions",
                f"https://tonwhales.com/api/accounts/{address}",
                f"https://api.tonwhales.com/accounts/{address}"
            ]
            
            # TON Labs API endpoints to test
            ton_labs_endpoints = [
                f"https://api.tonlabs.io/accounts/{address}/transactions",
                f"https://tonlabs.io/api/accounts/{address}/transactions",
                f"https://api.tonlabs.io/v1/accounts/{address}/transactions",
                f"https://api.tonlabs.io/v2/accounts/{address}/transactions",
                f"https://api.tonlabs.io/accounts/{address}",
                f"https://tonlabs.io/api/accounts/{address}"
            ]
            
            # Test TON.sh endpoints
            logger.info("\n🔍 Testing TON.sh endpoints:")
            for i, url in enumerate(ton_sh_endpoints, 1):
                success = await self.test_endpoint(f"TON.sh #{i}", url)
                if success:
                    results[f"TON.sh_{address}"] = url
                    break
            
            # Test TON Whales endpoints
            logger.info("\n🔍 Testing TON Whales endpoints:")
            for i, url in enumerate(ton_whales_endpoints, 1):
                success = await self.test_endpoint(f"TON Whales #{i}", url)
                if success:
                    results[f"TON_Whales_{address}"] = url
                    break
            
            # Test TON Labs endpoints
            logger.info("\n🔍 Testing TON Labs endpoints:")
            for i, url in enumerate(ton_labs_endpoints, 1):
                success = await self.test_endpoint(f"TON Labs #{i}", url)
                if success:
                    results[f"TON_Labs_{address}"] = url
                    break
        
        # Summary
        logger.info("\n📊 RESEARCH SUMMARY")
        logger.info("=" * 50)
        
        if results:
            logger.info("✅ WORKING ENDPOINTS FOUND:")
            for api, url in results.items():
                logger.info(f"   {api}: {url}")
        else:
            logger.warning("❌ No working endpoints found")
        
        return results

async def main():
    """Main function."""
    async with TONAPIEndpointResearcher() as researcher:
        results = await researcher.research_ton_apis()
        
        if results:
            logger.info("\n🔧 RECOMMENDED FIXES:")
            logger.info("=" * 30)
            logger.info("Update the following in multi_crypto_payments.py:")
            
            for api, url in results.items():
                if "TON.sh" in api:
                    logger.info(f"   TON.sh: {url}")
                elif "TON_Whales" in api:
                    logger.info(f"   TON Whales: {url}")
                elif "TON_Labs" in api:
                    logger.info(f"   TON Labs: {url}")

if __name__ == "__main__":
    asyncio.run(main())
