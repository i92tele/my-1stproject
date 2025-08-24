#!/usr/bin/env python3
"""
Price Update Service
Automatically fetches and caches cryptocurrency prices with multiple API fallbacks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import aiohttp
import json

logger = logging.getLogger(__name__)

class PriceUpdateService:
    """Background service for automatic crypto price updates with multiple API fallbacks."""
    
    def __init__(self, payment_processor, update_interval_minutes: int = 5):
        self.payment_processor = payment_processor
        self.update_interval_minutes = update_interval_minutes
        self.is_running = False
        self.task = None
        
        # Supported cryptocurrencies
        self.supported_cryptos = ['BTC', 'ETH', 'SOL', 'LTC', 'TON', 'USDT', 'USDC']
        
        # API configurations with fallback order
        self.price_apis = [
            {
                'name': 'CoinGecko',
                'url': 'https://api.coingecko.com/api/v3/simple/price',
                'params': {'vs_currencies': 'usd'},
                'timeout': 10,
                'rate_limit_delay': 1,  # 1 second between requests
                'enabled': True
            },
            {
                'name': 'CoinCap',
                'url': 'https://api.coincap.io/v2/assets',
                'params': {},
                'timeout': 10,
                'rate_limit_delay': 0.5,
                'enabled': True
            },
            {
                'name': 'CryptoCompare',
                'url': 'https://min-api.cryptocompare.com/data/price',
                'params': {'fsym': 'BTC', 'tsyms': 'USD'},
                'timeout': 10,
                'rate_limit_delay': 0.5,
                'enabled': True
            }
        ]
        
        # API status tracking
        self.api_status = {api['name']: {'last_success': None, 'failures': 0, 'disabled_until': None} for api in self.price_apis}
        
    async def start(self):
        """Start the price update service."""
        if self.is_running:
            logger.warning("Price update service already running")
            return
            
        self.is_running = True
        self.task = asyncio.create_task(self._price_update_loop())
        logger.info(f"Price update service started (interval: {self.update_interval_minutes} minutes)")
        
    async def stop(self):
        """Stop the price update service."""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Price update service stopped")
        
    async def _price_update_loop(self):
        """Main loop for updating prices."""
        while self.is_running:
            try:
                await self._update_all_prices()
                await asyncio.sleep(self.update_interval_minutes * 60)  # Convert to seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in price update loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
    async def _update_all_prices(self):
        """Update prices for all supported cryptocurrencies using multiple APIs."""
        logger.info("🔄 Updating crypto prices...")
        
        updated_count = 0
        for crypto in self.supported_cryptos:
            try:
                price = await self._get_crypto_price_with_fallbacks(crypto)
                if price:
                    updated_count += 1
                    logger.debug(f"✅ {crypto}: ${price}")
                else:
                    logger.warning(f"⚠️  Could not get price for {crypto}")
            except Exception as e:
                logger.error(f"❌ Error updating {crypto} price: {e}")
                
        logger.info(f"📊 Price update complete: {updated_count}/{len(self.supported_cryptos)} updated")
        
    async def _get_crypto_price_with_fallbacks(self, crypto_type: str) -> Optional[float]:
        """Get crypto price using multiple API fallbacks."""
        
        # Check cache first
        if (crypto_type in self.payment_processor.price_cache and 
            crypto_type in self.payment_processor.price_cache_time and
            datetime.now().timestamp() - self.payment_processor.price_cache_time[crypto_type] < self.payment_processor.price_cache_duration):
            return self.payment_processor.price_cache[crypto_type]
        
        # Try each API in order
        for api_config in self.price_apis:
            if not api_config['enabled']:
                continue
                
            # Check if API is temporarily disabled
            if self.api_status[api_config['name']]['disabled_until']:
                if datetime.now() < self.api_status[api_config['name']]['disabled_until']:
                    continue
                else:
                    # Re-enable API
                    self.api_status[api_config['name']]['disabled_until'] = None
                    self.api_status[api_config['name']]['failures'] = 0
            
            try:
                price = await self._fetch_price_from_api(api_config, crypto_type)
                if price:
                    # Cache the price
                    self.payment_processor.price_cache[crypto_type] = price
                    self.payment_processor.price_cache_time[crypto_type] = datetime.now().timestamp()
                    
                    # Update API status
                    self.api_status[api_config['name']]['last_success'] = datetime.now()
                    self.api_status[api_config['name']]['failures'] = 0
                    
                    logger.info(f"✅ Got {crypto_type} price from {api_config['name']}: ${price}")
                    return price
                    
            except Exception as e:
                logger.warning(f"⚠️  {api_config['name']} failed for {crypto_type}: {e}")
                self.api_status[api_config['name']]['failures'] += 1
                
                # Disable API if too many failures
                if self.api_status[api_config['name']]['failures'] >= 3:
                    disable_until = datetime.now() + timedelta(minutes=15)
                    self.api_status[api_config['name']]['disabled_until'] = disable_until
                    logger.warning(f"🚫 Disabled {api_config['name']} until {disable_until.strftime('%H:%M:%S')}")
            
            # Rate limiting delay
            await asyncio.sleep(api_config['rate_limit_delay'])
        
        logger.error(f"❌ All APIs failed for {crypto_type}")
        return None
        
    async def _fetch_price_from_api(self, api_config: Dict, crypto_type: str) -> Optional[float]:
        """Fetch price from a specific API."""
        
        if api_config['name'] == 'CoinGecko':
            return await self._fetch_coingecko_price(crypto_type, api_config)
        elif api_config['name'] == 'CoinCap':
            return await self._fetch_coincap_price(crypto_type, api_config)
        elif api_config['name'] == 'CryptoCompare':
            return await self._fetch_cryptocompare_price(crypto_type, api_config)
        else:
            raise ValueError(f"Unknown API: {api_config['name']}")
            
    async def _fetch_coingecko_price(self, crypto_type: str, api_config: Dict) -> Optional[float]:
        """Fetch price from CoinGecko API."""
        coin_id = self._get_coingecko_id(crypto_type)
        params = api_config['params'].copy()
        params['ids'] = coin_id
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_config['url'], params=params, timeout=api_config['timeout']) as response:
                if response.status == 200:
                    data = await response.json()
                    if coin_id in data and 'usd' in data[coin_id]:
                        return data[coin_id]['usd']
                else:
                    raise Exception(f"HTTP {response.status}")
        return None
        
    async def _fetch_coincap_price(self, crypto_type: str, api_config: Dict) -> Optional[float]:
        """Fetch price from CoinCap API."""
        # CoinCap uses different symbols
        coincap_symbols = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'LTC': 'litecoin',
            'TON': 'toncoin',  # Fixed: CoinCap uses 'toncoin' not 'the-open-network'
            'USDT': 'tether',
            'USDC': 'usd-coin'
        }
        
        symbol = coincap_symbols.get(crypto_type, crypto_type.lower())
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_config['url']}/{symbol}", timeout=api_config['timeout']) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'data' in data and 'priceUsd' in data['data']:
                        return float(data['data']['priceUsd'])
                elif response.status == 404:
                    # CoinCap doesn't have this crypto, skip silently
                    return None
                else:
                    raise Exception(f"HTTP {response.status}")
        return None
        
    async def _fetch_cryptocompare_price(self, crypto_type: str, api_config: Dict) -> Optional[float]:
        """Fetch price from CryptoCompare API."""
        params = api_config['params'].copy()
        params['fsym'] = crypto_type
        params['tsyms'] = 'USD'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_config['url'], params=params, timeout=api_config['timeout']) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'USD' in data:
                        return data['USD']
                else:
                    raise Exception(f"HTTP {response.status}")
        return None
        
    def _get_coingecko_id(self, crypto_type: str) -> str:
        """Get CoinGecko API ID for cryptocurrency."""
        coingecko_ids = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'USDT': 'tether',
            'USDC': 'usd-coin',
            'SOL': 'solana',
            'LTC': 'litecoin',
            'TON': 'the-open-network'
        }
        return coingecko_ids.get(crypto_type, crypto_type.lower())
        
    async def force_update(self):
        """Force an immediate price update."""
        logger.info("🔄 Forcing immediate price update...")
        await self._update_all_prices()
        
    def get_status(self) -> Dict[str, any]:
        """Get service status."""
        return {
            'is_running': self.is_running,
            'update_interval_minutes': self.update_interval_minutes,
            'supported_cryptos': self.supported_cryptos,
            'cached_prices': self.payment_processor.price_cache if hasattr(self.payment_processor, 'price_cache') else {},
            'api_status': self.api_status
        }

# Global instance
price_service = None

def initialize_price_service(payment_processor, update_interval_minutes: int = 5):
    """Initialize the global price update service."""
    global price_service
    price_service = PriceUpdateService(payment_processor, update_interval_minutes)
    return price_service

async def start_price_service():
    """Start the global price update service."""
    global price_service
    if price_service:
        await price_service.start()
    else:
        logger.error("Price service not initialized")

async def stop_price_service():
    """Stop the global price update service."""
    global price_service
    if price_service:
        await price_service.stop()

def get_price_service():
    """Get the global price service instance."""
    return price_service
