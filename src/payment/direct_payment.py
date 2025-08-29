from src.payment_address_direct_fix import fix_payment_data, get_payment_message
from src.payment_address_fix import fix_payment_data, get_crypto_address
#!/usr/bin/env python3
"""
Direct Payment Processor

This module handles direct cryptocurrency payments without third-party providers.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List

class DirectPaymentProcessor:
    """Direct cryptocurrency payment processor."""
    
    def __init__(self, db_manager, logger):
        """Initialize direct payment processor."""
        self.db = db_manager
        self.logger = logger
        self.payment_timeout_minutes = 60
        
        # Load crypto addresses
        self.crypto_addresses = {
            'BTC': os.getenv('BTC_ADDRESS', ''),
            'ETH': os.getenv('ETH_ADDRESS', ''),
            'USDT': os.getenv('USDT_ADDRESS', ''),
            'USDC': os.getenv('USDC_ADDRESS', ''),
            'LTC': os.getenv('LTC_ADDRESS', ''),
            'SOL': os.getenv('SOL_ADDRESS', ''),
            'TON': os.getenv('TON_ADDRESS', '')
        }
        
        # Log available cryptocurrencies
        available_cryptos = [crypto for crypto, address in self.crypto_addresses.items() if address]
        self.logger.info(f"Available cryptocurrencies: {', '.join(available_cryptos)}")
        
        # Tier configurations
        self.tiers = {
            'basic': {
                'slots': 1,
                'price_usd': 15,
                'duration_days': 30
            },
            'pro': {
                'slots': 3,
                'price_usd': 45,
                'duration_days': 30
            },
            'enterprise': {
                'slots': 5,
                'price_usd': 75,
                'duration_days': 30
            }
        }
        
        # Price cache
        self.price_cache = {}
        self.price_cache_time = {}
        self.price_cache_duration = 300  # 5 minutes
    
    async def create_payment(self, user_id: int, crypto_type: str, tier: str) -> Dict[str, Any]:
        """Create a new cryptocurrency payment."""
        try:
            # Validate crypto type
            crypto_type = crypto_type.upper()
            supported_cryptos = ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']
            if crypto_type not in supported_cryptos:
                return {'error': f"Unsupported cryptocurrency: {crypto_type}"}
            
            # Get crypto address
            try:
                from src.utils.env_loader import get_crypto_address
                address = get_crypto_address(crypto_type)
                if not address:
                    # Fall back to cached address
                    address = self.crypto_addresses.get(crypto_type)
                
                if not address:
                    return {'error': f"Payment address not configured for {crypto_type}. Please contact support to configure {crypto_type} payments."}
            except Exception as e:
                self.logger.error(f"Error getting {crypto_type} address: {e}")
                return {'error': f"Payment system error for {crypto_type}. Please try again or contact support."}
            
            # Validate tier
            if tier not in self.tiers:
                return {'error': f"Invalid tier: {tier}"}
            
            # Get tier price
            amount_usd = self.tiers[tier]['price_usd']
            
            # Get crypto price and calculate amount
            crypto_price = await self._get_crypto_price(crypto_type)
            if not crypto_price:
                return {'error': f"Could not get price for {crypto_type}"}
            
            crypto_amount = Decimal(amount_usd) / Decimal(crypto_price)
            
            # Round to appropriate decimal places based on crypto
            if crypto_type in ['BTC', 'ETH', 'LTC']:
                crypto_amount = round(crypto_amount, 8)  # 8 decimal places
            elif crypto_type in ['USDT', 'USDC']:
                crypto_amount = round(crypto_amount, 6)  # 6 decimal places
            elif crypto_type in ['SOL']:
                crypto_amount = round(crypto_amount, 9)  # 9 decimal places
            elif crypto_type in ['TON']:
                crypto_amount = round(crypto_amount, 9)  # 9 decimal places
            
            # Generate payment ID
            payment_id = f"{crypto_type}_{uuid.uuid4().hex[:16]}"
            
            # Calculate expiry
            expires_at = datetime.now() + timedelta(minutes=self.payment_timeout_minutes)
            
            # Create payment URL based on crypto type
            if crypto_type == 'BTC':
                payment_url = f"bitcoin:{address}?amount={crypto_amount}"
            elif crypto_type == 'ETH':
                payment_url = f"ethereum:{address}?value={crypto_amount}"
            elif crypto_type == 'LTC':
                payment_url = f"litecoin:{address}?amount={crypto_amount}"
            elif crypto_type == 'SOL':
                payment_url = f"solana:{address}?amount={crypto_amount}"
            elif crypto_type == 'TON':
                payment_url = f"ton://transfer/{address}?amount={crypto_amount}&text={payment_id}"
            else:
                payment_url = f"crypto:{crypto_type.lower()}:{address}?amount={crypto_amount}"
            
            # Store payment in database
            success = await self.db.create_payment(
                payment_id=payment_id,
                user_id=user_id,
                amount_usd=amount_usd,
                crypto_type=crypto_type,
                payment_provider="direct",
                pay_to_address=address,
                expected_amount_crypto=float(crypto_amount),
                payment_url=payment_url,
                expires_at=expires_at,
                attribution_method="amount_only"
            )
            
            if not success:
                return {'error': "Failed to store payment in database"}
            
            # Create ad slots for the user
            tier_config = self.tiers[tier]
            for i in range(tier_config['slots']):
                await self.db.create_ad_slot(user_id, i + 1)
            
            self.logger.info(f"✅ Created {crypto_type} payment request {payment_id} for user {user_id}")
            
            return {
                'payment_id': payment_id,
                'crypto_type': crypto_type,
                'amount_crypto': float(crypto_amount),
                'amount_usd': amount_usd,
                'payment_url': payment_url,
                'address': address,
                'expires_at': expires_at.isoformat(),
                'tier': tier,
                'slots_created': tier_config['slots']
            }
            
        except Exception as e:
            self.logger.error(f"Error creating payment: {e}")
            return {'error': str(e)}
    
    async def get_supported_cryptos(self) -> List[str]:
        """Get list of supported cryptocurrencies."""
        # Always return all supported cryptocurrencies
        # Address validation will happen during payment creation
        supported = ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']
        self.logger.info(f"Supported cryptocurrencies: {supported}")
        return supported
    
    async def _get_crypto_price(self, crypto_type: str) -> Optional[float]:
        """Get current price of cryptocurrency in USD."""
        try:
            # Check cache first
            if (crypto_type in self.price_cache and 
                crypto_type in self.price_cache_time and 
                (datetime.now() - self.price_cache_time[crypto_type]).seconds < self.price_cache_duration):
                return self.price_cache[crypto_type]
            
            # For now, use mock prices - in production, use CoinGecko or similar API
            mock_prices = {
                'BTC': 60000.0,
                'ETH': 3000.0,
                'USDT': 1.0,
                'USDC': 1.0,
                'LTC': 80.0,
                'SOL': 100.0,
                'TON': 5.0
            }
            
            price = mock_prices.get(crypto_type)
            
            if price:
                # Update cache
                self.price_cache[crypto_type] = price
                self.price_cache_time[crypto_type] = datetime.now()
            
            return price
            
        except Exception as e:
            self.logger.error(f"Error getting {crypto_type} price: {e}")
            return None

# Global instance
direct_payment_processor = None

def initialize_direct_payment_processor(db_manager, logger):
    """Initialize the global DirectPaymentProcessor instance."""
    global direct_payment_processor
    direct_payment_processor = DirectPaymentProcessor(db_manager, logger)
    return direct_payment_processor

def get_direct_payment_processor():
    """Get the global DirectPaymentProcessor instance."""
    return direct_payment_processor
