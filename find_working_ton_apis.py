#!/usr/bin/env python3
"""
Find Working TON APIs
Test alternative TON APIs that actually work for payment verification
"""

import asyncio
import aiohttp
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkingTONAPIFinder:
    """Find working TON APIs for payment verification."""
    
    def __init__(self):
        self.test_address = "EQC_1YoM8RBix9CG6rRjS4-MqW1TglNTurgHqFJXeJjq4uCv"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_api(self, api_name: str, url: str, headers: dict = None):
        """Test a specific API endpoint."""
        try:
            logger.info(f"🔍 Testing {api_name}: {url}")
            
            request_headers = headers or {}
            async with self.session.get(url, headers=request_headers, timeout=10) as response:
                status = response.status
                if status == 200:
                    try:
                        data = await response.json()
                        logger.info(f"✅ {api_name}: SUCCESS (200)")
                        logger.info(f"   Response type: {type(data)}")
                        if isinstance(data, dict):
                            logger.info(f"   Response keys: {list(data.keys())}")
                        return True, data
                    except Exception as e:
                        logger.warning(f"⚠️ {api_name}: JSON parse error - {e}")
                        return True, None
                else:
                    logger.warning(f"❌ {api_name}: FAILED ({status})")
                    return False, None
        except Exception as e:
            logger.error(f"❌ {api_name}: ERROR - {e}")
            return False, None
    
    async def find_working_apis(self):
        """Find working TON APIs."""
        logger.info("🔬 FINDING WORKING TON APIs")
        logger.info("=" * 50)
        
        working_apis = {}
        
        # Test known working TON APIs
        test_apis = [
            # TON Center API (known to work)
            {
                "name": "TON Center",
                "url": f"https://toncenter.com/api/v2/getTransactions?address={self.test_address}&limit=10",
                "description": "Official TON Center API"
            },
            # TON API.io (known to work)
            {
                "name": "TON API.io",
                "url": f"https://toncenter.com/api/v2/getTransactions?address={self.test_address}&limit=10",
                "description": "TON API.io alternative"
            },
            # Toncenter with different endpoint
            {
                "name": "TON Center Account",
                "url": f"https://toncenter.com/api/v2/getAccountState?address={self.test_address}",
                "description": "TON Center account state"
            },
            # TON Foundation API
            {
                "name": "TON Foundation",
                "url": f"https://api.ton.org/accounts/{self.test_address}",
                "description": "TON Foundation API"
            },
            # TON RPC
            {
                "name": "TON RPC",
                "url": "https://toncenter.com/api/v2/getMasterchainInfo",
                "description": "TON RPC masterchain info"
            },
            # TON Center with API key
            {
                "name": "TON Center (with key)",
                "url": f"https://toncenter.com/api/v2/getTransactions?address={self.test_address}&limit=10&api_key=free",
                "description": "TON Center with API key"
            }
        ]
        
        for api in test_apis:
            success, data = await self.test_api(api["name"], api["url"])
            if success:
                working_apis[api["name"]] = {
                    "url": api["url"],
                    "description": api["description"],
                    "data": data
                }
        
        # Summary
        logger.info("\n📊 WORKING APIS SUMMARY")
        logger.info("=" * 50)
        
        if working_apis:
            logger.info("✅ WORKING APIS FOUND:")
            for name, info in working_apis.items():
                logger.info(f"   {name}: {info['url']}")
                logger.info(f"      Description: {info['description']}")
        else:
            logger.warning("❌ No working APIs found")
        
        return working_apis

async def main():
    """Main function."""
    async with WorkingTONAPIFinder() as finder:
        working_apis = await finder.find_working_apis()
        
        if working_apis:
            logger.info("\n🔧 RECOMMENDED IMPLEMENTATION:")
            logger.info("=" * 40)
            logger.info("Replace the failing APIs with these working ones:")
            
            for name, info in working_apis.items():
                logger.info(f"\n{name}:")
                logger.info(f"   URL: {info['url']}")
                logger.info(f"   Description: {info['description']}")

if __name__ == "__main__":
    asyncio.run(main())
