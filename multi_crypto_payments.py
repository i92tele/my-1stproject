import asyncio
import logging
import os
import uuid
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

class MultiCryptoPaymentProcessor:
    """Multi-cryptocurrency payment processor supporting BTC, ETH, USDT, USDC, TON."""
    
    def __init__(self, config, db_manager, logger: logging.Logger):
        self.config = config
        self.db = db_manager
        self.logger = logger
        
        # Coinbase Commerce API configuration
        self.coinbase_api_key = os.getenv('COINBASE_COMMERCE_API_KEY', '')
        self.coinbase_webhook_secret = os.getenv('COINBASE_WEBHOOK_SECRET', '')  # Optional for now
        self.coinbase_api_url = 'https://api.commerce.coinbase.com'
        
        # Payment timeout and retry settings
        self.payment_timeout_minutes = 30
        self.retry_attempts = 3
        self.retry_interval_seconds = 30
        
        # Supported cryptocurrencies
        self.supported_cryptos = {
            'BTC': {
                'name': 'Bitcoin',
                'symbol': 'BTC',
                'decimals': 8,
                'provider': 'direct'
            },
            'ETH': {
                'name': 'Ethereum',
                'symbol': 'ETH',
                'decimals': 18,
                'provider': 'direct'
            },
            'USDT': {
                'name': 'Tether USD',
                'symbol': 'USDT',
                'decimals': 6,
                'provider': 'direct'
            },
            'USDC': {
                'name': 'USD Coin',
                'symbol': 'USDC',
                'decimals': 6,
                'provider': 'direct'
            },
            'TON': {
                'name': 'Toncoin',
                'symbol': 'TON',
                'decimals': 9,
                'provider': 'direct'
            }
        }
        
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
        
        # Price cache with longer duration for better performance
        self.price_cache = {}
        self.price_cache_time = {}
        self.price_cache_duration = 600  # 10 minutes (doubled for better caching)
        # External API configuration (optional but recommended)
        self.ton_api_base = os.getenv('TON_API_BASE', 'https://tonapi.io')
        self.ton_api_key = os.getenv('TON_API_KEY', '')
        self.toncenter_api_key = os.getenv('TONCENTER_API_KEY', '')
        # Amount matching tolerance for minor fee/slippage differences (e.g., 0.03 = 3%)
        try:
            self.payment_tolerance = float(os.getenv('PAYMENT_TOLERANCE', '0.03'))
        except Exception:
            self.payment_tolerance = 0.03

    async def create_payment_request(self, user_id: int, tier: str, crypto_type: str) -> Dict[str, Any]:
        """Create a new payment request for the specified cryptocurrency."""
        try:
            # Validate inputs
            if tier not in self.tiers:
                raise ValueError(f"Invalid tier: {tier}")
            
            if crypto_type not in self.supported_cryptos:
                raise ValueError(f"Unsupported cryptocurrency: {crypto_type}")
            
            # Get tier configuration
            tier_config = self.tiers[tier]
            amount_usd = tier_config['price_usd']
            
            # Generate payment ID
            payment_id = f"{crypto_type}_{uuid.uuid4().hex[:16]}"
            
            # Calculate expiry
            expires_at = datetime.now() + timedelta(minutes=self.payment_timeout_minutes)
            
            # Create payment based on provider
            crypto_config = self.supported_cryptos[crypto_type]
            
            if crypto_config['provider'] == 'direct':
                payment_data = await self._create_direct_payment(payment_id, amount_usd, crypto_type)
            else:
                raise ValueError(f"Unknown payment provider: {crypto_config['provider']}")
            
            # Store payment in database
            await self.db.create_payment(
                payment_id=payment_id,
                user_id=user_id,
                amount_usd=amount_usd,
                crypto_type=crypto_type,
                payment_provider=crypto_config['provider'],
                pay_to_address=payment_data['pay_to_address'],
                expected_amount_crypto=payment_data['amount_crypto'],
                payment_url=payment_data['payment_url'],
                expires_at=expires_at,
                attribution_method=payment_data.get('attribution_method', 'amount_only')
            )
            
            return {
                'success': True,
                'payment_id': payment_id,
                'payment_url': payment_data['payment_url'],
                'amount_crypto': payment_data['amount_crypto'],
                'amount_usd': amount_usd,
                'expires_at': expires_at.isoformat(),
                'crypto_type': crypto_type
            }
            
        except Exception as e:
            self.logger.error(f"Error creating payment request: {e}")
            return {'success': False, 'error': str(e)}

    async def verify_payment_on_blockchain(self, payment_id: str) -> bool:
        """Verify if a payment has been received on the blockchain."""
        try:
            # Get payment from database
            payment = await self.db.get_payment(payment_id)
            if not payment:
                self.logger.error(f"Payment {payment_id} not found in database")
                return False
            
            if payment['status'] != 'pending':
                return payment['status'] == 'completed'
            
            # Check if payment has expired
            if datetime.now() > datetime.fromisoformat(payment['expires_at']):
                await self.db.update_payment_status(payment_id, 'expired')
                return False
            
            # Verify based on provider
            crypto_type = payment['crypto_type']
            provider = payment['payment_provider']
            
            if provider == 'direct':
                return await self._verify_direct_payment(payment)
            else:
                self.logger.error(f"Unknown payment provider: {provider}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying payment {payment_id}: {e}")
            return False

    async def _create_direct_payment(self, payment_id: str, amount_usd: float, crypto_type: str) -> Dict[str, Any]:
        """Create a direct payment using standard wallet addresses."""
        try:
            if crypto_type == 'TON':
                ton_price = await self._get_crypto_price('TON')
                if not ton_price:
                    raise Exception("Unable to get TON price")
                amount_crypto = amount_usd / ton_price
                ton_address = os.getenv('TON_ADDRESS', '')
                if not ton_address:
                    raise Exception("TON_ADDRESS not configured. Please set TON_ADDRESS in your .env file with your TON wallet address.")
                # Tonkeeper/Tonhub deep link; include payment_id as comment
                payment_url = f"ton://transfer/{ton_address}?amount={int(amount_crypto * 1e9)}&text={payment_id}"
                return {
                    'amount_crypto': amount_crypto,
                    'payment_url': payment_url,
                    'provider_payment_id': None,
                    'pay_to_address': ton_address,
                    'network': 'ton',
                    'payment_memo': payment_id,
                    'attribution_method': 'memo'
                }
            elif crypto_type == 'BTC':
                btc_price = await self._get_crypto_price('BTC')
                if not btc_price:
                    raise Exception("Unable to get BTC price")
                amount_crypto = amount_usd / btc_price
                btc_address = os.getenv('BTC_ADDRESS', '')
                if not btc_address:
                    raise Exception("BTC_ADDRESS not configured. Please set BTC_ADDRESS in your .env file with your Bitcoin wallet address.")
                # Bitcoin URI with amount and label
                payment_url = f"bitcoin:{btc_address}?amount={amount_crypto:.8f}&label=Payment-{payment_id}"
                return {
                    'amount_crypto': amount_crypto,
                    'payment_url': payment_url,
                    'provider_payment_id': None,
                    'pay_to_address': btc_address,
                    'network': 'bitcoin',
                    'payment_memo': f"Payment-{payment_id}",
                    'attribution_method': 'amount_time_window'
                }
            elif crypto_type == 'ETH':
                eth_price = await self._get_crypto_price('ETH')
                if not eth_price:
                    raise Exception("Unable to get ETH price")
                amount_crypto = amount_usd / eth_price
                eth_address = os.getenv('ETH_ADDRESS', '')
                if not eth_address:
                    raise Exception("ETH_ADDRESS not configured. Please set ETH_ADDRESS in your .env file with your Ethereum wallet address.")
                # Ethereum URI with amount
                payment_url = f"ethereum:{eth_address}?value={int(amount_crypto * 1e18)}"
                return {
                    'amount_crypto': amount_crypto,
                    'payment_url': payment_url,
                    'provider_payment_id': None,
                    'pay_to_address': eth_address,
                    'network': 'ethereum',
                    'payment_memo': f"Payment-{payment_id}",
                    'attribution_method': 'amount_time_window'
                }
            elif crypto_type in ['USDT', 'USDC']:
                # For stablecoins, amount is the same as USD
                amount_crypto = amount_usd
                eth_address = os.getenv('ETH_ADDRESS', '')
                if not eth_address:
                    raise Exception("ETH_ADDRESS not configured for ERC-20 tokens. Please set ETH_ADDRESS in your .env file.")
                # Note: ERC-20 transfers require contract interaction, this is simplified
                payment_url = f"ethereum:{eth_address}?data={payment_id}"
                return {
                    'amount_crypto': amount_crypto,
                    'payment_url': payment_url,
                    'provider_payment_id': None,
                    'pay_to_address': eth_address,
                    'network': 'ethereum',
                    'payment_memo': payment_id,
                    'attribution_method': 'amount_time_window'
                }
            elif crypto_type == 'SOL':
                sol_price = await self._get_crypto_price('SOL')
                if not sol_price:
                    raise Exception("Unable to get SOL price")
                amount_crypto = amount_usd / sol_price
                sol_address = os.getenv('SOL_ADDRESS', '')
                if not sol_address:
                    raise Exception("SOL_ADDRESS not configured. Please set SOL_ADDRESS in your .env file with your Solana wallet address.")
                # Solana with memo support
                payment_url = f"solana:{sol_address}?amount={amount_crypto}&memo={payment_id}"
                return {
                    'amount_crypto': amount_crypto,
                    'payment_url': payment_url,
                    'provider_payment_id': None,
                    'pay_to_address': sol_address,
                    'network': 'solana',
                    'payment_memo': payment_id,
                    'attribution_method': 'memo'
                }

            elif crypto_type == 'LTC':
                ltc_price = await self._get_crypto_price('LTC')
                if not ltc_price:
                    raise Exception("Unable to get LTC price")
                amount_crypto = amount_usd / ltc_price
                ltc_address = os.getenv('LTC_ADDRESS', '')
                if not ltc_address:
                    raise Exception("LTC_ADDRESS not configured. Please set LTC_ADDRESS in your .env file with your Litecoin wallet address.")
                # Litecoin URI with amount and label
                payment_url = f"litecoin:{ltc_address}?amount={amount_crypto:.8f}&label=Payment-{payment_id}"
                return {
                    'amount_crypto': amount_crypto,
                    'payment_url': payment_url,
                    'provider_payment_id': None,
                    'pay_to_address': ltc_address,
                    'network': 'litecoin',
                    'payment_memo': f"Payment-{payment_id}",
                    'attribution_method': 'amount_time_window'
                }
            elif crypto_type == 'SOL':
                sol_price = await self._get_crypto_price('SOL')
                if not sol_price:
                    raise Exception("Unable to get SOL price")
                amount_crypto = amount_usd / sol_price
                sol_address = os.getenv('SOL_ADDRESS', '')
                if not sol_address:
                    raise Exception("SOL_ADDRESS not configured. Please set SOL_ADDRESS in your .env file with your Solana wallet address.")
                # Solana with memo support
                payment_url = f"solana:{sol_address}?amount={amount_crypto}&memo={payment_id}"
                return {
                    'amount_crypto': amount_crypto,
                    'payment_url': payment_url,
                    'provider_payment_id': None,
                    'pay_to_address': sol_address,
                    'network': 'solana',
                    'payment_memo': payment_id,
                    'attribution_method': 'memo'
                }
            else:
                raise Exception(f"Unsupported cryptocurrency: {crypto_type}")
                
        except Exception as e:
            self.logger.error(f"Error creating direct payment: {e}")
            raise

    async def _get_crypto_price(self, crypto_type: str) -> Optional[float]:
        """Get current cryptocurrency price in USD."""
        try:
            # Check cache first
            if (crypto_type in self.price_cache and 
                crypto_type in self.price_cache_time and 
                (datetime.now() - self.price_cache_time[crypto_type]).seconds < self.price_cache_duration):
                return self.price_cache[crypto_type]
            
            # Fetch from CoinGecko API
            async with aiohttp.ClientSession() as session:
                crypto_ids = {
                    'BTC': 'bitcoin',
                    'ETH': 'ethereum',
                    'TON': 'toncoin',
                    'SOL': 'solana',
                    'LTC': 'litecoin'
                }
                
                if crypto_type in crypto_ids:
                    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_ids[crypto_type]}&vs_currencies=usd"
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            price = data[crypto_ids[crypto_type]]['usd']
                            self.price_cache[crypto_type] = price
                            self.price_cache_time[crypto_type] = datetime.now()
                            return price
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting {crypto_type} price: {e}")
            return None

    async def _verify_direct_payment(self, payment: Dict[str, Any]) -> bool:
        """Verify direct payment for all supported cryptocurrencies."""
        try:
            crypto_type = payment['crypto_type']
            required_amount = float(payment.get('expected_amount_crypto') or payment.get('amount') or 0)
            required_conf = int(payment.get('required_confirmations') or 1)
            
            self.logger.info(f"🔍 Verifying {crypto_type} payment: {payment.get('payment_id')}")
            self.logger.info(f"💰 Expected: {required_amount} {crypto_type} (min confirmations: {required_conf})")
            
            # Check attribution method
            attribution_method = payment.get('attribution_method', 'amount_only')
            if attribution_method == 'memo':
                memo = payment.get('payment_id')
                self.logger.info(f"🎯 Looking for: {required_amount} {crypto_type} with memo '{memo}'")
            else:
                self.logger.info(f"🎯 Looking for: {required_amount} {crypto_type} in time window")
            
            if crypto_type == 'TON':
                return await self._verify_ton_payment(payment, required_amount, required_conf)
            elif crypto_type == 'BTC':
                return await self._verify_btc_payment(payment, required_amount, required_conf)
            elif crypto_type == 'ETH':
                return await self._verify_eth_payment(payment, required_amount, required_conf)
            elif crypto_type in ['USDT', 'USDC']:
                return await self._verify_erc20_payment(payment, required_amount, required_conf)
            elif crypto_type == 'LTC':
                return await self._verify_ltc_payment(payment, required_amount, required_conf)
            elif crypto_type == 'SOL':
                return await self._verify_sol_payment(payment, required_amount, required_conf)
            else:
                self.logger.warning(f"Unsupported crypto type for verification: {crypto_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying direct payment: {e}")
            return False

    async def _verify_ton_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int) -> bool:
        """Verify TON payment with memo-based attribution or amount+time window."""
        try:
            ton_address = payment.get('pay_to_address') or os.getenv('TON_ADDRESS', '')
            if not ton_address:
                self.logger.error("TON address not configured for verification")
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
            
            self.logger.info(f"Verifying TON payment to {ton_address} in time window: {time_window_start} to {time_window_end}")
            
            # Use TON Center API
            async with aiohttp.ClientSession() as session:
                url = "https://toncenter.com/api/v2/getTransactions"
                params = {
                    'address': ton_address,
                    'limit': 20
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for tx in data.get('result', []):
                            # Check if transaction matches our payment
                            tx_value_ton = float(tx.get('in_msg', {}).get('value', 0)) / 1e9
                            tx_time_str = tx.get('utime')
                            
                            if tx_time_str:
                                try:
                                    tx_time = datetime.fromtimestamp(int(tx_time_str))
                                except:
                                    continue
                                
                                # Check if in time window
                                if tx_time < time_window_start or tx_time > time_window_end:
                                    continue
                            
                            # Amount matching with tolerance
                            tolerance = self.payment_tolerance
                            min_required = required_amount * (1.0 - tolerance)
                            max_allowed = required_amount * (1.0 + tolerance)
                            
                            if min_required <= tx_value_ton <= max_allowed:
                                # If memo attribution, check memo
                                if attribution_method == 'memo':
                                    tx_memo = tx.get('in_msg', {}).get('message', '')
                                    if payment_id and payment_id in tx_memo:
                                        self.logger.info(f"✅ TON payment verified by memo: {tx_value_ton} TON")
                                        return True
                                else:
                                    # Amount + time window verification
                                    self.logger.info(f"✅ TON payment verified by amount+time: {tx_value_ton} TON")
                                    return True
                        
                        return False
                    else:
                        self.logger.error(f"TON API error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error verifying TON payment: {e}")
            return False

    async def _verify_btc_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int) -> bool:
        """Verify Bitcoin payment using amount + time window."""
        try:
            btc_address = payment.get('pay_to_address') or os.getenv('BTC_ADDRESS', '')
            if not btc_address:
                self.logger.error("BTC address not configured for verification")
                return False
            
            # Get payment creation time for time window matching
            payment_created = payment.get('created_at')
            if payment_created:
                payment_time = datetime.fromisoformat(payment_created.replace('Z', '+00:00'))
                time_window_start = payment_time - timedelta(minutes=30)  # 30 minutes before
                time_window_end = payment_time + timedelta(minutes=30)    # 30 minutes after
            else:
                time_window_start = datetime.now() - timedelta(minutes=60)  # Default 1 hour back
                time_window_end = datetime.now() + timedelta(minutes=30)
            
            self.logger.info(f"Verifying BTC payment to {btc_address} in time window: {time_window_start} to {time_window_end}")
            
            # Mock verification for now - replace with actual BTC API calls
            # This should check for transactions with matching amount in time window
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying BTC payment: {e}")
            return False

    async def _verify_eth_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int) -> bool:
        """Verify Ethereum payment using amount + time window."""
        try:
            eth_address = payment.get('pay_to_address') or os.getenv('ETH_ADDRESS', '')
            if not eth_address:
                self.logger.error("ETH address not configured for verification")
                return False
            
            # Get payment creation time for time window matching
            payment_created = payment.get('created_at')
            if payment_created:
                payment_time = datetime.fromisoformat(payment_created.replace('Z', '+00:00'))
                time_window_start = payment_time - timedelta(minutes=30)  # 30 minutes before
                time_window_end = payment_time + timedelta(minutes=30)    # 30 minutes after
            else:
                time_window_start = datetime.now() - timedelta(minutes=60)  # Default 1 hour back
                time_window_end = datetime.now() + timedelta(minutes=30)
            
            self.logger.info(f"Verifying ETH payment to {eth_address} in time window: {time_window_start} to {time_window_end}")
            
            # Mock verification for now - replace with actual ETH API calls
            # This should check for transactions with matching amount in time window
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying ETH payment: {e}")
            return False

    async def _verify_erc20_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int) -> bool:
        """Verify ERC-20 token payment (USDT, USDC)."""
        try:
            eth_address = payment.get('pay_to_address') or os.getenv('ETH_ADDRESS', '')
            if not eth_address:
                self.logger.error("ETH address not configured for ERC-20 verification")
                return False
            
            self.logger.info(f"Verifying ERC-20 payment to {eth_address}")
            
            # Mock verification for now - replace with actual ERC-20 API calls
            # This should check for token transfers with matching amount in time window
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying ERC-20 payment: {e}")
            return False
      
    async def _verify_ltc_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int) -> bool:
        """Verify Litecoin payment using amount + time window."""
        try:
            ltc_address = payment.get('pay_to_address') or os.getenv('LTC_ADDRESS', '')
            if not ltc_address:
                self.logger.error("LTC address not configured for verification")
                return False
            
            # Get payment creation time for time window matching
            payment_created = payment.get('created_at')
            if payment_created:
                payment_time = datetime.fromisoformat(payment_created.replace('Z', '+00:00'))
                time_window_start = payment_time - timedelta(minutes=30)  # 30 minutes before
                time_window_end = payment_time + timedelta(minutes=30)    # 30 minutes after
            else:
                time_window_start = datetime.now() - timedelta(minutes=60)  # Default 1 hour back
                time_window_end = datetime.now() + timedelta(minutes=30)
            
            self.logger.info(f"Verifying LTC payment to {ltc_address} in time window: {time_window_start} to {time_window_end}")
            
            # Use BlockCypher API for LTC verification
            async with aiohttp.ClientSession() as session:
                url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{ltc_address}/full"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        transactions = data.get('txs', [])
                        
                        for tx in transactions:
                            tx_time = datetime.fromtimestamp(tx.get('confirmed', 0))
                            if time_window_start <= tx_time <= time_window_end:
                                # Check for matching amount (with tolerance)
                                for output in tx.get('outputs', []):
                                    if output.get('addr') == ltc_address:
                                        amount_ltc = output.get('value', 0) / 100000000  # Convert satoshis to LTC
                                        if abs(amount_ltc - required_amount) <= (required_amount * self.payment_tolerance):
                                            self.logger.info(f"✅ LTC payment verified: {amount_ltc} LTC received")
                                            return True
            
            self.logger.info("❌ LTC payment not found in time window")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying LTC payment: {e}")
            return False

    async def _verify_sol_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int) -> bool:
        """Verify Solana payment with memo-based attribution."""
        try:
            sol_address = payment.get('pay_to_address') or os.getenv('SOL_ADDRESS', '')
            if not sol_address:
                self.logger.error("SOL address not configured for verification")
                return False
            
            memo = payment.get('payment_id')
            self.logger.info(f"Verifying SOL payment to {sol_address} with memo '{memo}'")
            
            # Get payment creation time for time window matching
            payment_created = payment.get('created_at')
            if payment_created:
                payment_time = datetime.fromisoformat(payment_created.replace('Z', '+00:00'))
                time_window_start = payment_time - timedelta(minutes=30)  # 30 minutes before
                time_window_end = payment_time + timedelta(minutes=30)    # 30 minutes after
            else:
                time_window_start = datetime.now() - timedelta(minutes=60)  # Default 1 hour back
                time_window_end = datetime.now() + timedelta(minutes=30)
            
            # Use Solana RPC API for verification
            async with aiohttp.ClientSession() as session:
                # Get recent transactions for the address
                url = "https://api.mainnet-beta.solana.com"
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignaturesForAddress",
                    "params": [
                        sol_address,
                        {
                            "limit": 20
                        }
                    ]
                }
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        signatures = data.get('result', [])
                        
                        for sig_info in signatures:
                            sig = sig_info.get('signature')
                            if not sig:
                                continue
                            
                            # Get transaction details
                            tx_payload = {
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "getTransaction",
                                "params": [
                                    sig,
                                    {
                                        "encoding": "json",
                                        "maxSupportedTransactionVersion": 0
                                    }
                                ]
                            }
                            
                            async with session.post(url, json=tx_payload) as tx_response:
                                if tx_response.status == 200:
                                    tx_data = await tx_response.json()
                                    tx_result = tx_data.get('result')
                                    
                                    if tx_result:
                                        # Check if transaction is within time window
                                        block_time = tx_result.get('blockTime', 0)
                                        if block_time:
                                            tx_time = datetime.fromtimestamp(block_time)
                                            if time_window_start <= tx_time <= time_window_end:
                                                # Check for memo and amount
                                                meta = tx_result.get('meta', {})
                                                pre_balances = meta.get('preBalances', [])
                                                post_balances = meta.get('postBalances', [])
                                                
                                                if len(pre_balances) > 0 and len(post_balances) > 0:
                                                    balance_change = (post_balances[0] - pre_balances[0]) / 1e9  # Convert lamports to SOL
                                                    if abs(balance_change - required_amount) <= (required_amount * self.payment_tolerance):
                                                        # Check for memo in transaction
                                                        if memo in str(tx_result):
                                                            self.logger.info(f"✅ SOL payment verified: {balance_change} SOL received with memo '{memo}'")
                                                            return True
            
            self.logger.info("❌ SOL payment not found in time window")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying SOL payment: {e}")
            return False

    async def _complete_payment_verification(self, payment: Dict[str, Any], tx_hash: str) -> None:
        """Complete payment verification and activate subscription."""
        try:
            payment_id = payment['payment_id']
            user_id = payment['user_id']
            
            # Update payment status to completed
            await self.db.update_payment_status(payment_id, 'completed')
            
            # Determine tier based on amount
            tier = self._determine_tier_from_amount(payment['amount_usd'])
            
            # Activate subscription
            success = await self.db.activate_subscription(
                user_id=user_id,
                tier=tier,
                duration_days=self.tiers[tier]['duration_days']
            )
            
            if success:
                self.logger.info(f"✅ Payment {payment_id} completed and subscription activated for user {user_id}")
            else:
                self.logger.error(f"❌ Failed to activate subscription for payment {payment_id}")
                
        except Exception as e:
            self.logger.error(f"Error completing payment verification: {e}")

    def _determine_tier_from_amount(self, amount_usd: float) -> str:
        """Determine subscription tier based on payment amount."""
        if amount_usd >= 75:
            return 'enterprise'
        elif amount_usd >= 45:
            return 'pro'
        else:
            return 'basic'
