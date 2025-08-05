#!/usr/bin/env python3
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from decimal import Decimal

class MultiCryptoPaymentProcessor:
    """Handle multi-cryptocurrency payments with automatic verification."""
    
    def __init__(self, config, db, logger):
        self.config = config
        self.db = db
        self.logger = logger
        
        # API endpoints for different blockchains
        self.api_endpoints = {
            'btc': 'https://api.blockcypher.com/v1/btc/main',
            'eth': 'https://api.etherscan.io/api',
            'sol': 'https://api.mainnet-beta.solana.com',
            'ton': 'https://toncenter.com/api/v2',
            'ltc': 'https://api.blockcypher.com/v1/ltc/main'
        }
        
        # API keys (add to config if needed)
        self.api_keys = {
            "eth": config.etherscan_api_key,
            "btc": config.blockcypher_api_key,
            "ltc": config.blockcypher_api_key,
            'eth': config.etherscan_api_key if hasattr(config, 'etherscan_api_key') else None,
            'btc': None,  # Blockstream.info is free
            'sol': None,  # Solana RPC is free
            'ton': None,  # TON Center is free
            'ltc': None   # BlockCypher is free
        }
    
    async def get_crypto_prices(self) -> Dict[str, float]:
        """Get current cryptocurrency prices from multiple APIs."""
        prices = {}
        
        try:
            # TON price from CoinGecko
            async with aiohttp.ClientSession() as session:
                url = "https://api.coingecko.com/api/v3/simple/price"
                params = {
                    'ids': 'the-open-network',
                    'vs_currencies': 'usd'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'the-open-network' in data and 'usd' in data['the-open-network']:
                            prices['TON'] = data['the-open-network']['usd']
                
                # Bitcoin price
                params = {
                    'ids': 'bitcoin',
                    'vs_currencies': 'usd'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'bitcoin' in data and 'usd' in data['bitcoin']:
                            prices['BTC'] = data['bitcoin']['usd']
                
                # Ethereum price
                params = {
                    'ids': 'ethereum',
                    'vs_currencies': 'usd'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'ethereum' in data and 'usd' in data['ethereum']:
                            prices['ETH'] = data['ethereum']['usd']
                
                # Solana price
                params = {
                    'ids': 'solana',
                    'vs_currencies': 'usd'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'solana' in data and 'usd' in data['solana']:
                            prices['SOL'] = data['solana']['usd']
                
                # Litecoin price
                params = {
                    'ids': 'litecoin',
                    'vs_currencies': 'usd'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'litecoin' in data and 'usd' in data['litecoin']:
                            prices['LTC'] = data['litecoin']['usd']
                
        except Exception as e:
            self.logger.error(f"Error fetching crypto prices: {e}")
            # Fallback prices
            prices = {
                'TON': 3.62,
                'BTC': 45000.0,
                'ETH': 2800.0,
                'SOL': 100.0,
                'LTC': 150.0
            }
        
        return prices
    
    async def verify_payment_on_blockchain(self, payment_data: Dict) -> bool:
        """Verify payment on the appropriate blockchain."""
        crypto = payment_data['cryptocurrency'].lower()
        wallet_address = payment_data['wallet_address']
        expected_amount = payment_data['amount_crypto']
        payment_id = payment_data['payment_id']
        
        try:
            if crypto == 'ton':
                return await self._verify_ton_payment(wallet_address, expected_amount, payment_id)
            elif crypto == 'btc':
                return await self._verify_btc_payment(wallet_address, expected_amount, payment_id)
            elif crypto == 'eth':
                return await self._verify_eth_payment(wallet_address, expected_amount, payment_id)
            elif crypto == 'sol':
                return await self._verify_sol_payment(wallet_address, expected_amount, payment_id)
            elif crypto == 'ltc':
                return await self._verify_ltc_payment(wallet_address, expected_amount, payment_id)
            else:
                self.logger.warning(f"Unsupported cryptocurrency: {crypto}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying {crypto} payment: {e}")
            return False
    
    async def _verify_ton_payment(self, wallet_address: str, expected_amount: float, payment_id: str) -> bool:
        """Verify TON payment using TON Center API."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get recent transactions
                url = f"{self.api_endpoints['ton']}/getTransactions"
                params = {
                    'address': wallet_address,
                    'limit': 10
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for tx in data.get('result', []):
                            # Check if transaction matches our payment
                            if (tx.get('in_msg', {}).get('source') and 
                                float(tx.get('in_msg', {}).get('value', 0)) / 1e9 >= expected_amount * 0.95):  # 5% tolerance
                                return True
                        
                        return False
                    else:
                        self.logger.error(f"TON API error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"TON verification error: {e}")
            return False
    
    async def _verify_btc_payment(self, wallet_address: str, expected_amount: float, payment_id: str) -> bool:
        """Verify Bitcoin payment using Blockstream API."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get address transactions
                url = f"{self.api_endpoints['btc']}/address/{wallet_address}/txs"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        transactions = await response.json()
                        
                        for tx in transactions[:10]:  # Check last 10 transactions
                            # Check if any input matches our expected amount
                            for output in tx.get('vout', []):
                                if (output.get('scriptpubkey_address') == wallet_address and
                                    output.get('value', 0) / 100000000 >= expected_amount * 0.95):  # Convert satoshis to BTC
                                    return True
                        
                        return False
                    else:
                        self.logger.error(f"Bitcoin API error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Bitcoin verification error: {e}")
            return False
    
    async def _verify_eth_payment(self, wallet_address: str, expected_amount: float, payment_id: str) -> bool:
        """Verify Ethereum payment using Etherscan API."""
        try:
            if not self.api_keys['eth']:
                self.logger.warning("Etherscan API key not configured")
                return False
                
            async with aiohttp.ClientSession() as session:
                # Get recent transactions
                url = f"{self.api_endpoints['eth']}/account"
                params = {
                    'module': 'account',
                    'action': 'txlist',
                    'address': wallet_address,
                    'startblock': 0,
                    'endblock': 99999999,
                    'sort': 'desc',
                    'apikey': self.api_keys['eth']
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == '1':
                            for tx in data.get('result', [])[:10]:  # Check last 10 transactions
                                # Check if transaction matches our expected amount
                                if (tx.get('to', '').lower() == wallet_address.lower() and
                                    float(tx.get('value', 0)) / 1e18 >= expected_amount * 0.95):  # Convert wei to ETH
                                    return True
                        
                        return False
                    else:
                        self.logger.error(f"Ethereum API error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Ethereum verification error: {e}")
            return False
    
    async def _verify_sol_payment(self, wallet_address: str, expected_amount: float, payment_id: str) -> bool:
        """Verify Solana payment using Solana RPC."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get recent transactions
                url = self.api_endpoints['sol']
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignaturesForAddress",
                    "params": [
                        wallet_address,
                        {"limit": 10}
                    ]
                }
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'result' in data:
                            for tx in data['result']:
                                # Get transaction details
                                tx_payload = {
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "getTransaction",
                                    "params": [tx['signature']]
                                }
                                
                                async with session.post(url, json=tx_payload) as tx_response:
                                    if tx_response.status == 200:
                                        tx_data = await tx_response.json()
                                        if 'result' in tx_data:
                                            # Check if transaction matches our expected amount
                                            # This is simplified - Solana verification is more complex
                                            if tx_data['result'].get('meta', {}).get('err') is None:
                                                return True
                        
                        return False
                    else:
                        self.logger.error(f"Solana API error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Solana verification error: {e}")
            return False
    
    async def _verify_ltc_payment(self, wallet_address: str, expected_amount: float, payment_id: str) -> bool:
        """Verify Litecoin payment using BlockCypher API."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get address transactions
                url = f"{self.api_endpoints['ltc']}/addrs/{wallet_address}/full"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for tx in data.get('txs', [])[:10]:  # Check last 10 transactions
                            # Check if any output matches our expected amount
                            for output in tx.get('outputs', []):
                                if (output.get('addresses', [{}])[0] == wallet_address and
                                    output.get('value', 0) / 100000000 >= expected_amount * 0.95):  # Convert satoshis to LTC
                                    return True
                        
                        return False
                    else:
                        self.logger.error(f"Litecoin API error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Litecoin verification error: {e}")
            return False
    
    async def start_payment_monitoring(self):
        """Start monitoring for payments across all cryptocurrencies."""
        while True:
            try:
                # Get pending payments
                pending_payments = await self.db.get_pending_payments()
                
                for payment in pending_payments:
                    # Check if payment is expired
                    if payment['expires_at'] < datetime.now():
                        await self.db.update_payment_status(payment['payment_id'], 'expired')
                        continue
                    
                    # Verify payment on blockchain
                    is_verified = await self.verify_payment_on_blockchain(payment)
                    
                    if is_verified:
                        # Activate subscription
                        await self.db.update_payment_status(payment['payment_id'], 'completed')
                        await self.activate_subscription(payment['user_id'], payment['tier'])
                        self.logger.info(f"Payment verified and subscription activated for user {payment['user_id']}")
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Payment monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def activate_subscription(self, user_id: int, tier: str):
        """Activate user subscription after payment verification."""
        try:
            # Validate inputs
            if not user_id or not tier:
                self.logger.error("Invalid user_id or tier provided")
                raise ValueError("Invalid user_id or tier")
            
            # Get tier info
            tier_info = self.config.get_tier_info(tier)
            if not tier_info:
                self.logger.error(f"Invalid tier: {tier}")
                raise ValueError(f"Invalid tier: {tier}")
            
            # Update user subscription
            success = await self.db.activate_subscription(
                user_id=user_id,
                tier=tier,
                ad_slots=tier_info['ad_slots'],
                duration_days=tier_info['duration_days']
            )
            
            if not success:
                self.logger.error(f"Failed to activate subscription for user {user_id}")
                raise Exception("Failed to activate subscription")
            
            # Create ad slots for user
            ad_slots_created = 0
            for i in range(tier_info['ad_slots']):
                try:
                    await self.db.get_or_create_ad_slots(user_id, tier)
                    ad_slots_created += 1
                except Exception as e:
                    self.logger.error(f"Error creating ad slot {i} for user {user_id}: {e}")
            
            self.logger.info(f"Subscription activated for user {user_id}: {tier} with {ad_slots_created} ad slots")
            return True
            
        except Exception as e:
            self.logger.error(f"Error activating subscription: {e}")
            raise 