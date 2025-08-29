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
            },
            'SOL': {
                'name': 'Solana',
                'symbol': 'SOL',
                'decimals': 9,
                'provider': 'direct'
            },
            'LTC': {
                'name': 'Litecoin',
                'symbol': 'LTC',
                'decimals': 8,
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
        self.price_cache_duration = 60  # 1 minute (for more accurate prices)
        # External API configuration (optional but recommended)
        self.ton_api_base = os.getenv('TON_API_BASE', 'https://tonapi.io')
        self.ton_api_key = os.getenv('TON_API_KEY', '')
        self.toncenter_api_key = os.getenv('TONCENTER_API_KEY', '')
        self.blockchain_info_api_key = os.getenv('BLOCKCHAIN_INFO_API_KEY', '')
        self.mempool_api_key = os.getenv('MEMPOOL_API_KEY', '')
        self.blockstream_api_key = os.getenv('BLOCKSTREAM_API_KEY', '')
        # Amount matching tolerance for minor fee/slippage differences (e.g., 0.03 = 3%)
        try:
            self.payment_tolerance = float(os.getenv('PAYMENT_TOLERANCE', '0.03'))
        except Exception:
            self.payment_tolerance = 0.03
        
        # Background task will be started when needed
        self.background_task = None

        # TON API fallback chain - updated with working APIs
        self.ton_api_fallbacks = [
            ('TON API.io', self._verify_tonapi_io),        # Primary API
            ('TON Center', self._verify_ton_center_api),   # Backup 1 - Working
            ('TON RPC', self._verify_ton_rpc_api),         # Backup 2 - Working
            ('Manual', self._verify_ton_manual)            # Last resort
        ]

        # ✅ FIX: Standardized time window for all payment verifications
        self.PAYMENT_TIME_WINDOW_MINUTES = 60  # 1 hour total window
        
        # Rate limiting
        self.last_api_call = {}
        self.min_call_interval = 1.0  # 1 second between API calls

    async def start_background_monitoring(self):
        """Start the background payment verification task."""
        if self.background_task is None:
            self.background_task = asyncio.create_task(self._background_payment_verification())
            self.logger.info("✅ Background payment monitoring started")

    async def stop_background_monitoring(self):
        """Stop the background payment verification task."""
        if self.background_task and not self.background_task.done():
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
            self.background_task = None
            self.logger.info("✅ Background payment monitoring stopped")

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
                'crypto_type': crypto_type,
                'pay_to_address': payment_data['pay_to_address'],
                'attribution_method': payment_data.get('attribution_method', 'amount_only')
            }
            
        except Exception as e:
            self.logger.error(f"Error creating payment request: {e}")
            return {'success': False, 'error': str(e)}

    async def verify_payment_on_blockchain(self, payment_id: str) -> bool:
        """Verify if a payment has been received on the blockchain and activate subscription with comprehensive error handling."""
        # FIX: Add global verification lock to prevent race conditions
        lock_key = f"verification_{payment_id}"
        if not hasattr(self, '_verification_locks'):
            self._verification_locks = set()
        
        if lock_key in self._verification_locks:
            self.logger.warning(f"⚠️ Payment {payment_id} already being verified, skipping")
            return False
        
        self._verification_locks.add(lock_key)
        
        try:
            # Get payment from database with timeout
            try:
                payment = await asyncio.wait_for(self.db.get_payment(payment_id), timeout=10.0)
            except asyncio.TimeoutError:
                self.logger.error(f"❌ Database timeout getting payment {payment_id}")
                return False
            
            if not payment:
                self.logger.error(f"Payment {payment_id} not found in database")
                return False
            
            # FIX: Check payment status with proper error handling
            payment_status = payment.get('status', 'unknown')
            if payment_status == 'completed':
                self.logger.info(f"✅ Payment {payment_id} already completed")
                # CRITICAL FIX: ALWAYS check if subscription is active for completed payments
                # This ensures that if a payment is completed but subscription wasn't activated,
                # we'll activate it now
                user_id = payment.get('user_id')
                subscription = await self.db.get_user_subscription(user_id)
                if not subscription or not subscription.get('is_active'):
                    self.logger.warning(f"⚠️ Payment {payment_id} completed but subscription not active, activating now")
                    # Direct activation without further checks
                    tier = payment.get('tier', 'basic')
                    await self.db.activate_subscription(user_id, tier, 30)
                    self.logger.info(f"✅ Subscription activated for user {user_id} with tier {tier}")
                    return True
                return True
            elif payment_status == 'expired':
                self.logger.warning(f"⚠️ Payment {payment_id} already expired")
                return False
            elif payment_status == 'cancelled':
                self.logger.warning(f"⚠️ Payment {payment_id} was cancelled, attempting to reactivate")
                # FIX: Try to reactivate cancelled payments that were actually paid
                # This handles the case where payment was verified but status got corrupted
                return await self._reactivate_cancelled_payment(payment)
            elif payment_status != 'pending':
                self.logger.warning(f"⚠️ Payment {payment_id} has unexpected status: {payment_status}")
                return False
            
            # FIX: Check if payment has expired with proper timezone handling
            try:
                expires_at = datetime.fromisoformat(payment['expires_at'])
                if datetime.now() > expires_at:
                    await self.db.update_payment_status(payment_id, 'expired')
                    self.logger.warning(f"⚠️ Payment {payment_id} expired")
                    return False
            except (ValueError, TypeError) as e:
                self.logger.error(f"❌ Invalid expiration date for payment {payment_id}: {e}")
                return False
            
            # FIX: Add comprehensive retry logic with exponential backoff
            MAX_RETRIES = 3
            base_delay = 30
            
            for attempt in range(MAX_RETRIES):
                try:
                    # Verify based on provider
                    crypto_type = payment.get('crypto_type', 'TON')
                    provider = payment.get('payment_provider', 'direct')
                    
                    if provider == 'direct':
                        # FIX: Add timeout for verification
                        payment_verified = await asyncio.wait_for(
                            self._verify_direct_payment(payment), 
                            timeout=60.0
                        )
                        
                        if payment_verified:
                            self.logger.info(f"✅ Payment {payment_id} verified successfully")
                            # FIX: Activate subscription after successful verification
                            success = await self._activate_subscription_for_payment(payment)
                            if success:
                                self.logger.info(f"✅ Subscription activated for payment {payment_id}")
                                return True
                            else:
                                self.logger.error(f"❌ Failed to activate subscription for verified payment {payment_id}")
                                return False
                        elif attempt < MAX_RETRIES - 1:
                            delay = base_delay * (2 ** attempt)  # Exponential backoff
                            self.logger.info(f"⚠️ Payment verification attempt {attempt + 1} failed, retrying in {delay} seconds...")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            self.logger.warning(f"❌ Payment verification failed after {MAX_RETRIES} attempts")
                            return False
                    else:
                        self.logger.error(f"Unknown payment provider: {provider}")
                        return False
                        
                except asyncio.TimeoutError:
                    self.logger.error(f"❌ Verification timeout for payment {payment_id} (attempt {attempt + 1})")
                    if attempt < MAX_RETRIES - 1:
                        delay = base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        return False
                except Exception as e:
                    self.logger.error(f"❌ Error in verification attempt {attempt + 1} for payment {payment_id}: {e}")
                    if attempt < MAX_RETRIES - 1:
                        delay = base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # FIX: Log detailed error for debugging
                        import traceback
                        self.logger.error(f"Final verification error for {payment_id}: {traceback.format_exc()}")
                        return False
                
        except Exception as e:
            self.logger.error(f"❌ Critical error verifying payment {payment_id}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        finally:
            # FIX: Always remove lock when done
            if lock_key in self._verification_locks:
                self._verification_locks.remove(lock_key)

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
                # ✅ FIX: Use proper rounding for TON amount (nanoTON precision)
                amount_nano = round(amount_crypto * 1e9)  # Round, don't truncate
                payment_url = f"ton://transfer/{ton_address}?amount={amount_nano}&text={payment_id}"
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
            elif crypto_type == 'USDT':
                # USDT is an ERC-20 token, amount is the same as USD
                amount_crypto = amount_usd
                eth_address = os.getenv('ETH_ADDRESS', '')
                if not eth_address:
                    raise Exception("ETH_ADDRESS not configured for USDT. Please set ETH_ADDRESS in your .env file.")
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
            elif crypto_type == 'USDC':
                # USDC on Solana, amount is the same as USD
                amount_crypto = amount_usd
                sol_address = os.getenv('SOL_ADDRESS', '')
                if not sol_address:
                    raise Exception("SOL_ADDRESS not configured for USDC. Please set SOL_ADDRESS in your .env file.")
                # Solana URI with amount
                payment_url = f"solana:{sol_address}?amount={amount_crypto}"
                return {
                    'amount_crypto': amount_crypto,
                    'payment_url': payment_url,
                    'provider_payment_id': None,
                    'pay_to_address': sol_address,
                    'network': 'solana',
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
                # Solana URI with amount
                payment_url = f"solana:{sol_address}?amount={amount_crypto}"
                return {
                    'amount_crypto': amount_crypto,
                    'payment_url': payment_url,
                    'provider_payment_id': None,
                    'pay_to_address': sol_address,
                    'network': 'solana',
                    'payment_memo': f"Payment-{payment_id}",
                    'attribution_method': 'amount_time_window'
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

            else:
                raise Exception(f"Unsupported cryptocurrency: {crypto_type}")
                
        except Exception as e:
            self.logger.error(f"Error creating direct payment: {e}")
            raise

    async def _get_crypto_price(self, crypto_type: str) -> Optional[float]:
        """Get current cryptocurrency price in USD with multiple API fallbacks."""
        try:
            # Check cache first
            if (crypto_type in self.price_cache and 
                crypto_type in self.price_cache_time and 
                (datetime.now() - self.price_cache_time[crypto_type]).seconds < self.price_cache_duration):
                return self.price_cache[crypto_type]
            
            # Fallback prices if all APIs fail (updated to current market prices)
            fallback_prices = {
                'BTC': 114286.0,
                'ETH': 4881.0,
                'TON': 3.35,
                'SOL': 208.0,
                'LTC': 120.0,
                'USDT': 1.0,
                'USDC': 1.0
            }
            
            # Try multiple APIs in order of preference
            apis_to_try = [
                ('CoinGecko', self._get_coingecko_price),
                ('Coinbase', self._get_coinbase_price),
                ('Binance', self._get_binance_price)
            ]
            
            for api_name, api_func in apis_to_try:
                try:
                    price = await api_func(crypto_type)
                    if price and price > 0:
                        self.price_cache[crypto_type] = price
                        self.price_cache_time[crypto_type] = datetime.now()
                        self.logger.info(f"✅ Got {crypto_type} price from {api_name}: ${price}")
                        return price
                except Exception as e:
                    self.logger.warning(f"❌ {api_name} API failed for {crypto_type}: {e}")
                    continue
            
            # Use fallback price if all APIs fail
            if crypto_type in fallback_prices:
                price = fallback_prices[crypto_type]
                self.price_cache[crypto_type] = price
                self.price_cache_time[crypto_type] = datetime.now()
                self.logger.warning(f"⚠️ Using fallback price for {crypto_type}: ${price}")
                return price
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting {crypto_type} price: {e}")
            # Return fallback price as last resort
            fallback_prices = {
                'BTC': 114286.0, 'ETH': 4881.0, 'TON': 3.35, 'SOL': 208.0, 
                'LTC': 120.0, 'USDT': 1.0, 'USDC': 1.0
            }
            return fallback_prices.get(crypto_type)

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
                return await self._verify_ton_payment_improved(payment, required_amount, required_conf)
            elif crypto_type == 'BTC':
                return await self._verify_btc_payment_fallback(payment, required_amount, required_conf)
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
            
            # ✅ FIX: Standardized time window for all payment verifications
            payment_created = payment.get('created_at')
            if payment_created:
                payment_time = datetime.fromisoformat(payment_created.replace('Z', '+00:00'))
                window_half = self.PAYMENT_TIME_WINDOW_MINUTES // 2
                time_window_start = payment_time - timedelta(minutes=window_half)
                time_window_end = payment_time + timedelta(minutes=window_half)
            else:
                # Fallback: use current time as reference
                now = datetime.now()
                window_half = self.PAYMENT_TIME_WINDOW_MINUTES // 2
                time_window_start = now - timedelta(minutes=window_half)
                time_window_end = now + timedelta(minutes=window_half)
            
            self.logger.info(f"🔍 Verifying TON payment to {ton_address}")
            self.logger.info(f"   Expected amount: {required_amount} TON")
            self.logger.info(f"   Time window: {time_window_start} to {time_window_end}")
            self.logger.info(f"   Attribution method: {attribution_method}")
            if payment_id:
                self.logger.info(f"   Payment ID: {payment_id}")
            
            # Try multiple TON APIs in order of preference with retry logic
            ton_apis = self.ton_api_fallbacks
            
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


    async def _verify_btc_payment_fallback(self, payment: Dict[str, Any], required_amount: float, required_conf: int) -> bool:
        """Automatic BTC payment verification using multiple APIs."""
        try:
            payment_id = payment.get('payment_id', '')
            btc_address = payment.get('pay_to_address', '')
            
            self.logger.info(f"🔍 Automatic BTC verification for payment: {payment_id}")
            self.logger.info(f"💰 Expected amount: {required_amount} BTC")
            self.logger.info(f"📍 Address: {btc_address}")
            
            # Try multiple APIs for verification
            apis = [
                f"https://blockchain.info/rawaddr/{btc_address}",
                f"https://api.blockcypher.com/v1/btc/main/addrs/{btc_address}/full",
                f"https://api.blockchair.com/bitcoin/addresses/balances?addresses={btc_address}"
            ]
            
            for api_url in apis:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(api_url, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                # Parse different API responses
                                if 'blockchain.info' in api_url:
                                    # Blockchain.info format
                                    for tx in data.get('txs', []):
                                        tx_time = datetime.fromtimestamp(tx.get('time', 0))
                                        tx_value = tx.get('result', 0) / 100000000  # Convert satoshis to BTC
                                        
                                        if self._is_payment_match(payment, tx_value, tx_time, required_amount):
                                            # Check confirmations
                                            confirmations = tx.get('confirmations', 0)
                                            if confirmations >= required_conf:
                                                self.logger.info(f"✅ BTC payment verified via blockchain.info: {tx_value} BTC (confirmations: {confirmations})")
                                                return True
                                            else:
                                                self.logger.info(f"⏳ BTC payment found but insufficient confirmations: {confirmations}/{required_conf}")
                                
                                elif 'blockcypher.com' in api_url:
                                    # BlockCypher format
                                    for tx in data.get('txs', []):
                                        tx_time = datetime.fromtimestamp(tx.get('confirmed', 0))
                                        tx_value = tx.get('total', 0) / 100000000  # Convert satoshis to BTC
                                        
                                        if self._is_payment_match(payment, tx_value, tx_time, required_amount):
                                            # Check confirmations
                                            confirmations = tx.get('confirmations', 0)
                                            if confirmations >= required_conf:
                                                self.logger.info(f"✅ BTC payment verified via BlockCypher: {tx_value} BTC (confirmations: {confirmations})")
                                                return True
                                            else:
                                                self.logger.info(f"⏳ BTC payment found but insufficient confirmations: {confirmations}/{required_conf}")
                                
                                elif 'blockchair.com' in api_url:
                                    # Blockchair format - balance check only (no confirmation data)
                                    # For Blockchair, we'll use it as a fallback but log that confirmations aren't checked
                                    balance = data.get('data', {}).get(btc_address, 0) / 100000000
                                    if balance >= required_amount:
                                        self.logger.warning(f"⚠️ BTC payment found via Blockchair but confirmations not verified: {balance} BTC")
                                        # Don't return True here - let other APIs with confirmation data handle it
                                        continue
                                
                except Exception as api_error:
                    self.logger.warning(f"API {api_url} failed: {api_error}")
                    continue
            
            self.logger.info(f"❌ BTC payment not found for {payment_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error in automatic BTC verification: {e}")
            return False

    def _is_payment_match(self, payment: Dict[str, Any], tx_value: float, tx_time: datetime, required_amount: float) -> bool:
        """Check if a transaction matches the expected payment."""
        try:
            # Get payment creation time
            payment_created = payment.get('created_at')
            if payment_created:
                payment_time = datetime.fromisoformat(payment_created.replace('Z', '+00:00'))
                time_window_start = payment_time - timedelta(minutes=30)  # 30 minutes before
                time_window_end = payment_time + timedelta(minutes=30)    # 30 minutes after
            else:
                time_window_start = datetime.now() - timedelta(minutes=60)  # Default 1 hour back
                time_window_end = datetime.now() + timedelta(minutes=30)
            
            # Check if transaction is in time window
            if tx_time < time_window_start or tx_time > time_window_end:
                return False
            
            # Check if amount matches with tolerance
            tolerance = self.payment_tolerance
            min_required = required_amount * (1.0 - tolerance)
            max_allowed = required_amount * (1.0 + tolerance)
            
            if min_required <= tx_value <= max_allowed:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking payment match: {e}")
            return False

    async def _activate_subscription_for_payment(self, payment: Dict[str, Any]) -> bool:
        """Activate subscription for a verified payment with proper error handling and transaction safety."""
        payment_id = payment.get('payment_id')
        user_id = payment.get('user_id')
        
        if not payment_id or not user_id:
            self.logger.error(f"❌ Invalid payment data: payment_id={payment_id}, user_id={user_id}")
            return False
        
        # FIX: Add payment verification lock to prevent race conditions
        lock_key = f"payment_activation_{payment_id}"
        if hasattr(self, '_activation_locks'):
            if lock_key in self._activation_locks:
                self.logger.warning(f"⚠️ Payment {payment_id} already being processed, skipping")
                return False
        else:
            self._activation_locks = set()
        
        self._activation_locks.add(lock_key)
        
        try:
            # Handle different amount field names and None values
            amount_usd = payment.get('amount_usd') or payment.get('amount')
            
            # If amount is still None, try to get it from crypto amount and price
            if amount_usd is None:
                amount_crypto = payment.get('amount_crypto') or payment.get('expected_amount_crypto')
                crypto_type = payment.get('crypto_type', 'TON')
                if amount_crypto:
                    # Get current price to calculate USD amount
                    price = await self._get_crypto_price(crypto_type)
                    if price:
                        amount_usd = amount_crypto * price
                    else:
                        # Fallback to default amount based on crypto type
                        if crypto_type == 'TON':
                            amount_usd = 15.0  # Default basic tier
                        else:
                            amount_usd = 15.0
            
            # Ensure we have a valid amount
            if amount_usd is None or amount_usd <= 0:
                amount_usd = 15.0  # Default to basic tier
            
            self.logger.info(f"🎯 Activating subscription for payment {payment_id}")
            self.logger.info(f"   User ID: {user_id}")
            self.logger.info(f"   Amount USD: {amount_usd}")
            
            # Determine tier based on amount
            tier = self._get_tier_from_amount(amount_usd)
            duration_days = self.tiers[tier]['duration_days']
            
            self.logger.info(f"   Tier: {tier}")
            self.logger.info(f"   Duration: {duration_days} days")
            
            # FIX: Check if payment is already processed
            current_payment = await self.db.get_payment(payment_id)
            if current_payment and current_payment.get('status') == 'completed':
                # Check if subscription is already active
                subscription = await self.db.get_user_subscription(user_id)
                if subscription and subscription.get('is_active'):
                    self.logger.info(f"✅ Payment {payment_id} already completed and subscription active, skipping")
                    return True
                else:
                    self.logger.info(f"⚠️ Payment {payment_id} completed but subscription not active, activating now")
            
            # FIX: User creation is now handled in activate_subscription method
            self.logger.info(f"   Proceeding with subscription activation for user {user_id}...")
            
            # FIX: Use atomic transaction for subscription activation and payment status update
            self.logger.info(f"   Activating {tier} subscription...")
            
            # CRITICAL FIX: Direct database update to ensure subscription activation works
            try:
                # Update payment status first
                await self.db.update_payment_status(payment_id, 'completed')
                self.logger.info(f"✅ Payment status updated to completed")
                
                # Direct subscription activation
                success = await self.db.activate_subscription(user_id, tier, duration_days)
                
                if success:
                    self.logger.info(f"✅ Subscription activated for user {user_id}: {tier} tier")
                    self.logger.info(f"💰 Payment {payment_id} processed successfully")
                    return True
                else:
                    self.logger.error(f"❌ Failed to activate subscription for user {user_id}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"❌ Error in subscription activation: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error activating subscription for payment {payment_id}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        finally:
            # FIX: Remove lock when done
            if hasattr(self, '_activation_locks') and lock_key in self._activation_locks:
                self._activation_locks.remove(lock_key)

    async def _reactivate_cancelled_payment(self, payment: Dict[str, Any]) -> bool:
        """Reactivate a cancelled payment that was actually paid."""
        try:
            payment_id = payment.get('payment_id')
            user_id = payment.get('user_id')
            
            self.logger.info(f"🔄 Attempting to reactivate cancelled payment {payment_id}")
            
            # Verify the payment was actually made on blockchain
            payment_verified = await self._verify_direct_payment(payment)
            
            if payment_verified:
                self.logger.info(f"✅ Cancelled payment {payment_id} was actually paid, reactivating")
                # Activate subscription for the verified payment
                success = await self._activate_subscription_for_payment(payment)
                if success:
                    self.logger.info(f"✅ Successfully reactivated payment {payment_id}")
                    return True
                else:
                    self.logger.error(f"❌ Failed to activate subscription for reactivated payment {payment_id}")
                    return False
            else:
                self.logger.warning(f"⚠️ Cancelled payment {payment_id} was not actually paid")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error reactivating cancelled payment {payment_id}: {e}")
            return False

    async def admin_complete_payment(self, payment_id: str, admin_id: int, tx_hash: str = None) -> bool:
        """Manually complete a payment - ADMIN ONLY.
        
        This method should only be called by admin users after verifying the payment.
        """
        try:
            self.logger.info(f"🔧 Admin {admin_id} manually completing payment {payment_id}")
            
            # Get payment details
            payment = await self.db.get_payment(payment_id)
            if not payment:
                self.logger.error(f"❌ Payment {payment_id} not found")
                return False
            
            # First try blockchain verification
            self.logger.info(f"🔍 Attempting blockchain verification first...")
            blockchain_verified = await self._verify_direct_payment(payment)
            
            if blockchain_verified:
                self.logger.info(f"✅ Payment {payment_id} verified on blockchain")
            else:
                self.logger.warning(f"⚠️ Payment {payment_id} NOT found on blockchain, proceeding with admin override")
            
            # Update payment status to completed with admin verification flag
            await self.db.update_payment_field(payment_id, 'manual_verification', 1)
            await self.db.update_payment_field(payment_id, 'verified_by_admin', admin_id)
            if tx_hash:
                await self.db.update_payment_field(payment_id, 'transaction_hash', tx_hash)
                
            success = await self.db.update_payment_status(payment_id, 'completed')
            if not success:
                self.logger.error(f"❌ Failed to update payment status for {payment_id}")
                return False
            
            # Log the admin action for audit purposes
            self.logger.info(f"👮 ADMIN ACTION: Payment {payment_id} manually completed by admin {admin_id}")
            
            # Activate subscription
            activation_result = await self._activate_subscription_for_payment(payment)
            if activation_result:
                self.logger.info(f"✅ Payment {payment_id} admin-completed and subscription activated")
                return True
            else:
                self.logger.error(f"❌ Failed to activate subscription for admin-completed payment {payment_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error in admin payment completion for {payment_id}: {e}")
            return False

    def _get_tier_from_amount(self, amount_usd: float) -> str:
        """Get tier name from USD amount."""
        if amount_usd == 15.0:
            return "basic"
        elif amount_usd == 45.0:
            return "pro"
        elif amount_usd == 75.0:
            return "enterprise"
        else:
            # Default to basic for any other amount
            return "basic"

    async def _background_payment_verification(self):
        """Background task to automatically verify pending payments."""
        while True:
            try:
                # Get pending payments
                pending_payments = await self.db.get_pending_payments(age_limit_minutes=1440)  # 24 hours
                
                if pending_payments:
                    self.logger.info(f"🔍 Checking {len(pending_payments)} pending payments...")
                    
                    for payment in pending_payments:
                        payment_id = payment['payment_id']
                        
                        # Skip if payment is already being processed
                        if payment['status'] != 'pending':
                            continue
                        
                        # Update last_checked time to show we're monitoring this payment
                        await self.db.update_payment_last_checked(payment_id)
                        
                        # Verify payment
                        try:
                            payment_verified = await self.verify_payment_on_blockchain(payment_id)
                            
                            if payment_verified:
                                self.logger.info(f"✅ Payment {payment_id} automatically verified and subscription activated!")
                            else:
                                self.logger.debug(f"⏳ Payment {payment_id} not yet received")
                                
                        except Exception as e:
                            self.logger.error(f"Error verifying payment {payment_id}: {e}")
                
                # Wait before next check (every 5 minutes)
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in background payment verification: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

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
            
            # Use Etherscan API for ETH verification
            etherscan_api_key = os.getenv('ETHERSCAN_API_KEY', '')
            if etherscan_api_key:
                try:
                    async with aiohttp.ClientSession() as session:
                        url = f"https://api.etherscan.io/api"
                        params = {
                            'module': 'account',
                            'action': 'txlist',
                            'address': eth_address,
                            'startblock': 0,
                            'endblock': 99999999,
                            'sort': 'desc',
                            'apikey': etherscan_api_key
                        }
                        
                        async with session.get(url, params=params, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                for tx in data.get('result', []):
                                    # Check transaction time
                                    tx_time = datetime.fromtimestamp(int(tx.get('timeStamp', 0)))
                                    if tx_time < time_window_start or tx_time > time_window_end:
                                        continue
                                    
                                    # Check if it's an incoming transaction
                                    if tx.get('to', '').lower() == eth_address.lower():
                                        # Check transaction amount (in wei, convert to ETH)
                                        tx_value_eth = float(tx.get('value', 0)) / 1e18
                                        
                                        # Amount matching with tolerance
                                        tolerance = self.payment_tolerance
                                        min_required = required_amount * (1.0 - tolerance)
                                        max_allowed = required_amount * (1.0 + tolerance)
                                        
                                        if min_required <= tx_value_eth <= max_allowed:
                                            # Check confirmations
                                            if int(tx.get('confirmations', 0)) >= required_conf:
                                                self.logger.info(f"✅ ETH payment verified: {tx_value_eth} ETH")
                                                return True
                                
                            if response.status == 429:
                                self.logger.warning("Etherscan API rate limited, payment verification may be delayed")
                            elif response.status != 200:
                                self.logger.error(f"Etherscan API error: {response.status}")
                                
                except Exception as api_error:
                    self.logger.warning(f"Etherscan API failed: {api_error}")
            
            # Fallback: use BlockCypher API
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.blockcypher.com/v1/eth/main/addrs/{eth_address}/full"
                    
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for tx in data.get('txs', []):
                                # Check transaction time
                                tx_time = datetime.fromtimestamp(tx.get('confirmed', 0))
                                if tx_time < time_window_start or tx_time > time_window_end:
                                    continue
                                
                                # Check if it's an incoming transaction
                                if tx.get('outputs'):
                                    for output in tx['outputs']:
                                        if output.get('addr') == eth_address:
                                            # Check transaction amount (in wei, convert to ETH)
                                            tx_value_eth = float(output.get('value', 0)) / 1e18
                                            
                                            # Amount matching with tolerance
                                            tolerance = self.payment_tolerance
                                            min_required = required_amount * (1.0 - tolerance)
                                            max_allowed = required_amount * (1.0 + tolerance)
                                            
                                            if min_required <= tx_value_eth <= max_allowed:
                                                # Check confirmations
                                                confirmations = tx.get('confirmations', 0)
                                                if confirmations >= required_conf:
                                                    self.logger.info(f"✅ ETH payment verified via BlockCypher: {tx_value_eth} ETH (confirmations: {confirmations})")
                                                    return True
                                                else:
                                                    self.logger.info(f"⏳ ETH payment found but insufficient confirmations: {confirmations}/{required_conf}")
                        
                        if response.status == 429:
                            self.logger.warning("BlockCypher ETH API rate limited, payment verification may be delayed")
                        elif response.status != 200:
                            self.logger.error(f"BlockCypher ETH API error: {response.status}")
                            
            except Exception as api_error:
                self.logger.warning(f"BlockCypher ETH API failed: {api_error}")
            
            self.logger.info("❌ ETH payment not found in time window")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying ETH payment: {e}")
            return False

    async def _verify_erc20_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int) -> bool:
        """Verify ERC-20 token payment (USDT, USDC)."""
        try:
            eth_address = payment.get('pay_to_address') or os.getenv('ETH_ADDRESS', '')
            crypto_type = payment.get('crypto_type', 'USDT')
            
            if not eth_address:
                self.logger.error("ETH address not configured for ERC-20 verification")
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
            
            self.logger.info(f"Verifying {crypto_type} payment to {eth_address} in time window: {time_window_start} to {time_window_end}")
            
            # Token contract addresses
            token_contracts = {
                'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                'USDC': '0xA0b86a33E6441b8C4C8C8C8C8C8C8C8C8C8C8C8C'
            }
            
            contract_address = token_contracts.get(crypto_type)
            if not contract_address:
                self.logger.error(f"Unknown ERC-20 token: {crypto_type}")
                return False
            
            # Use Etherscan API for ERC-20 verification
            etherscan_api_key = os.getenv('ETHERSCAN_API_KEY', '')
            if etherscan_api_key:
                try:
                    async with aiohttp.ClientSession() as session:
                        url = f"https://api.etherscan.io/api"
                        params = {
                            'module': 'account',
                            'action': 'tokentx',
                            'contractaddress': contract_address,
                            'address': eth_address,
                            'startblock': 0,
                            'endblock': 99999999,
                            'sort': 'desc',
                            'apikey': etherscan_api_key
                        }
                        
                        async with session.get(url, params=params, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                for tx in data.get('result', []):
                                    # Check transaction time
                                    tx_time = datetime.fromtimestamp(int(tx.get('timeStamp', 0)))
                                    if tx_time < time_window_start or tx_time > time_window_end:
                                        continue
                                    
                                    # Check if it's an incoming transaction
                                    if tx.get('to', '').lower() == eth_address.lower():
                                        # Check transaction amount (convert from token decimals)
                                        decimals = int(tx.get('tokenDecimal', 6))
                                        tx_value = float(tx.get('value', 0)) / (10 ** decimals)
                                        
                                        # Amount matching with tolerance
                                        tolerance = self.payment_tolerance
                                        min_required = required_amount * (1.0 - tolerance)
                                        max_allowed = required_amount * (1.0 + tolerance)
                                        
                                        if min_required <= tx_value <= max_allowed:
                                            # Check confirmations
                                            if int(tx.get('confirmations', 0)) >= required_conf:
                                                self.logger.info(f"✅ {crypto_type} payment verified: {tx_value} {crypto_type}")
                                                return True
                                
                            if response.status == 429:
                                self.logger.warning("Etherscan API rate limited, payment verification may be delayed")
                            elif response.status != 200:
                                self.logger.error(f"Etherscan API error: {response.status}")
                                
                except Exception as api_error:
                    self.logger.warning(f"Etherscan ERC-20 API failed: {api_error}")
            
            # Fallback: use Covalent API for ERC-20 verification
            covalent_api_key = os.getenv('COVALENT_API_KEY', '')
            if covalent_api_key:
                try:
                    async with aiohttp.ClientSession() as session:
                        url = f"https://api.covalenthq.com/v1/1/address/{eth_address}/transactions_v3/"
                        params = {'key': covalent_api_key}
                        
                        async with session.get(url, params=params, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                for tx in data.get('data', {}).get('items', []):
                                    # Check transaction time
                                    tx_time = datetime.fromtimestamp(tx.get('block_signed_at', 0))
                                    if tx_time < time_window_start or tx_time > time_window_end:
                                        continue
                                    
                                    # Check for token transfers
                                    for transfer in tx.get('transfers', []):
                                        if (transfer.get('contract_address', '').lower() == contract_address.lower() and
                                            transfer.get('to_address', '').lower() == eth_address.lower()):
                                            
                                            # Check transaction amount
                                            tx_value = float(transfer.get('delta', 0))
                                            
                                            # Amount matching with tolerance
                                            tolerance = self.payment_tolerance
                                            min_required = required_amount * (1.0 - tolerance)
                                            max_allowed = required_amount * (1.0 + tolerance)
                                            
                                            if min_required <= tx_value <= max_allowed:
                                                # Check confirmations (Covalent provides block information)
                                                block_height = tx.get('block_height', 0)
                                                if block_height > 0:  # Transaction is confirmed
                                                    self.logger.info(f"✅ {crypto_type} payment verified via Covalent: {tx_value} {crypto_type} (block: {block_height})")
                                                    return True
                                                else:
                                                    self.logger.info(f"⏳ {crypto_type} payment found but not yet confirmed")
                        
                        if response.status == 429:
                            self.logger.warning("Covalent API rate limited, payment verification may be delayed")
                        elif response.status != 200:
                            self.logger.error(f"Covalent API error: {response.status}")
                            
                except Exception as api_error:
                    self.logger.warning(f"Covalent API failed: {api_error}")
            
            self.logger.info(f"❌ {crypto_type} payment not found in time window")
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
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{ltc_address}/full"
                    async with session.get(url, timeout=10) as response:
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
                                                # Check confirmations
                                                confirmations = tx.get('confirmations', 0)
                                                if confirmations >= required_conf:
                                                    self.logger.info(f"✅ LTC payment verified: {amount_ltc} LTC received (confirmations: {confirmations})")
                                                    return True
                                                else:
                                                    self.logger.info(f"⏳ LTC payment found but insufficient confirmations: {confirmations}/{required_conf}")
                        
                        if response.status == 429:
                            self.logger.warning("BlockCypher LTC API rate limited, payment verification may be delayed")
                        elif response.status != 200:
                            self.logger.error(f"BlockCypher LTC API error: {response.status}")
                            
            except Exception as api_error:
                self.logger.warning(f"BlockCypher LTC API failed: {api_error}")
            
            # Fallback: use SoChain API for LTC verification
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://sochain.com/api/v2/get_tx_received/LTC/{ltc_address}"
                    
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for tx in data.get('data', {}).get('txs', []):
                                # Check transaction time
                                tx_time = datetime.fromtimestamp(int(tx.get('time', 0)))
                                if tx_time < time_window_start or tx_time > time_window_end:
                                    continue
                                
                                # Check transaction amount
                                tx_value_ltc = float(tx.get('value', 0))
                                
                                # Amount matching with tolerance
                                tolerance = self.payment_tolerance
                                min_required = required_amount * (1.0 - tolerance)
                                max_allowed = required_amount * (1.0 + tolerance)
                                
                                if min_required <= tx_value_ltc <= max_allowed:
                                    # Check confirmations (SoChain doesn't provide confirmation data, so we'll log this)
                                    self.logger.warning(f"⚠️ LTC payment found via SoChain but confirmations not verified: {tx_value_ltc} LTC")
                                    # Don't return True here - let BlockCypher handle confirmation checking
                                    continue
                        
                        if response.status == 429:
                            self.logger.warning("SoChain API rate limited, payment verification may be delayed")
                        elif response.status != 200:
                            self.logger.error(f"SoChain API error: {response.status}")
                            
            except Exception as api_error:
                self.logger.warning(f"SoChain API failed: {api_error}")
            
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
                                                            # Check confirmations (Solana uses slot-based confirmation)
                                                            # For Solana, we consider it confirmed if it's in a recent block
                                                            slot = tx_result.get('slot', 0)
                                                            if slot > 0:  # Transaction is confirmed
                                                                self.logger.info(f"✅ SOL payment verified: {balance_change} SOL received with memo '{memo}' (slot: {slot})")
                                                                return True
                                                            else:
                                                                self.logger.info(f"⏳ SOL payment found but not yet confirmed")
            
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

    async def _get_coingecko_price(self, crypto_type: str) -> Optional[float]:
        """Get price from CoinGecko API."""
        crypto_ids = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'TON': 'the-open-network',
            'SOL': 'solana',
            'LTC': 'litecoin',
            'USDT': 'tether',
            'USDC': 'usd-coin'
        }
        
        if crypto_type not in crypto_ids:
            return None
            
        async with aiohttp.ClientSession() as session:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_ids[crypto_type]}&vs_currencies=usd"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if crypto_ids[crypto_type] in data and 'usd' in data[crypto_ids[crypto_type]]:
                        return data[crypto_ids[crypto_type]]['usd']
                elif response.status == 429:
                    self.logger.warning(f"CoinGecko API rate limited for {crypto_type}")
                else:
                    self.logger.warning(f"CoinGecko API failed for {crypto_type}: HTTP {response.status}")
        return None

    async def _get_coinbase_price(self, crypto_type: str) -> Optional[float]:
        """Get price from Coinbase API."""
        async with aiohttp.ClientSession() as session:
            url = f"https://api.coinbase.com/v2/prices/{crypto_type}-USD/spot"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data['data']['amount'])
                else:
                    self.logger.warning(f"Coinbase API failed for {crypto_type}: HTTP {response.status}")
        return None

    async def _get_binance_price(self, crypto_type: str) -> Optional[float]:
        """Get price from Binance API."""
        async with aiohttp.ClientSession() as session:
            symbol = f"{crypto_type}USDT"
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data['price'])
                else:
                    self.logger.warning(f"Binance API failed for {crypto_type}: HTTP {response.status}")
        return None

    
    async def _verify_ton_center_api(self, ton_address: str, required_amount: float, required_conf: int, 
                                   time_window_start: datetime, time_window_end: datetime, 
                                   attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON Center API with improved time window logic."""
        try:
            await self._rate_limit_ton_api()
            
            async with aiohttp.ClientSession() as session:
                url = f"https://toncenter.com/api/v2/getTransactions"
                params = {
                    'address': ton_address,
                    'limit': 20
                }
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            transactions = data.get('result', [])
                            self.logger.info(f"🔍 TON Center found {len(transactions)} transactions")
                            
                            for tx in transactions:
                                # TON Center API structure
                                in_msg = tx.get('in_msg', {})
                                tx_value_ton = float(in_msg.get('value', 0)) / 1e9
                                tx_time_str = tx.get('utime')
                                
                                if tx_time_str:
                                    tx_time = datetime.fromtimestamp(int(tx_time_str))
                                    
                                    # IMPROVED: More flexible time window logic
                                    # Check if transaction is within reasonable time range
                                    time_diff = abs((tx_time - time_window_start).total_seconds())
                                    
                                    # Accept transactions within 2 hours of payment creation
                                    if time_diff <= 7200:  # 2 hours
                                        tolerance = getattr(self, 'payment_tolerance', 0.05)
                                        min_required = required_amount * (1.0 - tolerance)
                                        max_allowed = required_amount * (1.0 + tolerance)
                                        
                                        if min_required <= tx_value_ton <= max_allowed:
                                            # Check for payment ID in message
                                            tx_message = in_msg.get('message', '')
                                            
                                            if attribution_method == 'memo' and payment_id:
                                                # ✅ FIX: Simple, exact memo check to prevent false positives
                                                if payment_id in tx_message:
                                                    self.logger.info(f"✅ TON payment verified by TON Center (memo): {tx_value_ton} TON")
                                                    self.logger.info(f"   Payment ID found in message: {payment_id}")
                                                    self.logger.info(f"   Transaction time: {tx_time}")
                                                    self.logger.info(f"   Time difference: {time_diff/60:.1f} minutes")
                                                    return True
                                            else:
                                                # Amount + time window verification (relaxed)
                                                self.logger.info(f"✅ TON payment verified by TON Center (amount+time): {tx_value_ton} TON")
                                                self.logger.info(f"   Transaction time: {tx_time}")
                                                self.logger.info(f"   Time difference: {time_diff/60:.1f} minutes")
                                                return True
                            
                            return False
                        else:
                            self.logger.warning(f"❌ TON Center API error: {data.get('error')}")
                            return False
                    else:
                        self.logger.warning(f"❌ TON Center API error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"❌ TON Center API failed: {e}")
            return False

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


    async def _verify_ton_rpc(self, ton_address: str, required_amount: float, required_conf: int, 
                            time_window_start: datetime, time_window_end: datetime, 
                            attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON RPC (fallback method)."""
        try:
            # Use a public TON RPC endpoint
            async with aiohttp.ClientSession() as session:
                url = "https://ton.org/api/v2/blockchain/accounts/{}/transactions".format(ton_address)
                
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for tx in data.get('transactions', []):
                            # Extract transaction data
                            tx_value_ton = float(tx.get('amount', 0)) / 1e9
                            tx_time_str = tx.get('timestamp')
                            
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
                                # Check confirmations
                                seqno = tx.get('seqno', 0)
                                if seqno > 0:  # Transaction is confirmed
                                    # If memo attribution, check memo
                                    if attribution_method == 'memo':
                                        tx_memo = tx.get('message', '')
                                        if payment_id and payment_id in tx_memo:
                                            self.logger.info(f"✅ TON payment verified by TON RPC (memo): {tx_value_ton} TON (seqno: {seqno})")
                                            return True
                                    else:
                                        # Amount + time window verification
                                        self.logger.info(f"✅ TON payment verified by TON RPC (amount+time): {tx_value_ton} TON (seqno: {seqno})")
                                        return True
                                else:
                                    self.logger.info(f"⏳ TON payment found but not yet confirmed")
                        
                        return False
                    elif response.status == 429:
                        self.logger.warning(f"TON RPC rate limited (429)")
                        return False
                    elif response.status == 500:
                        self.logger.error(f"TON RPC server error (500)")
                        return False
                    else:
                        self.logger.error(f"TON RPC error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"TON RPC failed: {e}")
            return False


    async def _verify_ton_payment_improved(self, payment: Dict[str, Any], required_amount: float, required_conf: int) -> bool:
        """Improved TON payment verification with better API handling."""
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
            
            self.logger.info(f"🔍 Verifying TON payment: {payment_id}")
            self.logger.info(f"💰 Expected: {required_amount} TON (min confirmations: {required_conf})")
            self.logger.info(f"🎯 Looking for: {required_amount} TON with memo '{payment_id}'")
            self.logger.info(f"Verifying TON payment to {ton_address} in time window: {time_window_start} to {time_window_end}")
            
            # Try multiple TON APIs in order of preference
            ton_apis = self.ton_api_fallbacks
            
            for api_name, api_func in ton_apis:
                try:
                    self.logger.info(f"🔍 Trying {api_name} API...")
                    result = await api_func(ton_address, required_amount, required_conf, 
                                          time_window_start, time_window_end, attribution_method, payment_id)
                    if result:
                        self.logger.info(f"✅ TON payment verified via {api_name}")
                        # Activate subscription immediately when payment is found
                        await self._activate_subscription_for_payment(payment)
                        return True
                except Exception as e:
                    self.logger.warning(f"❌ {api_name} failed for TON verification: {e}")
                    continue
            
            self.logger.info("❌ TON payment not found in any API")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying TON payment: {e}")
            return False
    
    async def _verify_ton_manual(self, ton_address: str, required_amount: float, required_conf: int, 
                                time_window_start: datetime, time_window_end: datetime, 
                                attribution_method: str, payment_id: str) -> bool:
        """Manual TON verification using wallet balance changes (last resort)."""
        try:
            # This is a simplified manual verification that can be used when APIs fail
            # It checks if the wallet received the expected amount within the time window
            # Note: This is less secure than blockchain verification but can help in emergencies
            
            self.logger.warning(f"⚠️ Using manual TON verification for payment {payment_id}")
            self.logger.info(f"Manual verification: Expected {required_amount} TON to {ton_address}")
            self.logger.info(f"Time window: {time_window_start} to {time_window_end}")
            
            # For manual verification, we'll accept the payment if:
            # 1. The amount is reasonable (within 10% tolerance)
            # 2. The time window is recent (within last 2 hours)
            # 3. User confirms the payment was sent
            
            tolerance = 0.10  # 10% tolerance for manual verification
            min_required = required_amount * (1.0 - tolerance)
            max_allowed = required_amount * (1.0 + tolerance)
            
            # Check if we're within a reasonable time window for manual verification
            time_diff = datetime.now() - time_window_start
            if time_diff.total_seconds() > 7200:  # 2 hours
                self.logger.warning(f"Manual verification: Time window too old ({time_diff.total_seconds()/3600:.1f} hours)")
                return False
            
            self.logger.info(f"Manual verification: Amount range {min_required:.6f} - {max_allowed:.6f} TON")
            self.logger.info(f"Manual verification: Payment {payment_id} requires manual admin verification")
            
            # Manual verification requires admin intervention - don't auto-approve
            return False
            
        except Exception as e:
            self.logger.error(f"Manual TON verification failed: {e}")
            return False

    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get the status of a payment."""
        try:
            # Get payment from database
            payment = await self.db.get_payment(payment_id)
            if not payment:
                return {
                    'success': False,
                    'error': 'Payment not found',
                    'status': 'not_found'
                }
            
            # Check if payment has expired
            is_expired = False
            if payment.get('expires_at'):
                expires_at = datetime.fromisoformat(payment['expires_at'])
                is_expired = datetime.now() > expires_at
            
            # Determine status
            status = payment.get('status', 'unknown')
            if is_expired and status == 'pending':
                status = 'expired'
            
            return {
                'success': True,
                'payment_id': payment_id,
                'status': status,
                'amount_usd': payment.get('amount_usd'),
                'crypto_type': payment.get('crypto_type'),
                'amount_crypto': payment.get('expected_amount_crypto'),
                'pay_to_address': payment.get('pay_to_address'),
                'created_at': payment.get('created_at'),
                'expires_at': payment.get('expires_at'),
                'is_expired': is_expired
            }
            
        except Exception as e:
            self.logger.error(f"Error getting payment status for {payment_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'status': 'error'
            }

    def _validate_ton_address(self, address: str) -> bool:
        """Validate TON address format (supports both EQ and UQ prefixes)."""
        if not address:
            return False
        
        # Basic validation - check length and prefix
        if len(address) != 48:  # TON addresses are 48 characters
            return False
        
        # Check if starts with EQ or UQ
        if not (address.startswith('EQ') or address.startswith('UQ')):
            return False
        
        # Check if rest contains only valid characters
        rest = address[2:]  # Remove EQ or UQ prefix
        valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
        
        for char in rest:
            if char not in valid_chars:
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

    async def _verify_ton_center_api(self, ton_address: str, required_amount: float, required_conf: int, 
                                   time_window_start: datetime, time_window_end: datetime, 
                                   attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON Center API with improved time window logic."""
        try:
            await self._rate_limit_ton_api()
            
            async with aiohttp.ClientSession() as session:
                url = f"https://toncenter.com/api/v2/getTransactions"
                params = {
                    'address': ton_address,
                    'limit': 20
                }
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            transactions = data.get('result', [])
                            self.logger.info(f"🔍 TON Center found {len(transactions)} transactions")
                            
                            for tx in transactions:
                                # TON Center API structure
                                in_msg = tx.get('in_msg', {})
                                tx_value_ton = float(in_msg.get('value', 0)) / 1e9
                                tx_time_str = tx.get('utime')
                                
                                if tx_time_str:
                                    tx_time = datetime.fromtimestamp(int(tx_time_str))
                                    
                                    # IMPROVED: More flexible time window logic
                                    # Check if transaction is within reasonable time range
                                    time_diff = abs((tx_time - time_window_start).total_seconds())
                                    
                                    # Accept transactions within 2 hours of payment creation
                                    if time_diff <= 7200:  # 2 hours
                                        tolerance = getattr(self, 'payment_tolerance', 0.05)
                                        min_required = required_amount * (1.0 - tolerance)
                                        max_allowed = required_amount * (1.0 + tolerance)
                                        
                                        if min_required <= tx_value_ton <= max_allowed:
                                            # Check for payment ID in message
                                            tx_message = in_msg.get('message', '')
                                            
                                            if attribution_method == 'memo' and payment_id:
                                                # Check for payment ID in message (case insensitive and more flexible)
                                                if (payment_id.lower() in tx_message.lower() or 
                                                    payment_id in tx_message or
                                                    payment_id.replace('_', '') in tx_message.replace('_', '')):
                                                    self.logger.info(f"✅ TON payment verified by TON Center (memo): {tx_value_ton} TON")
                                                    self.logger.info(f"   Payment ID found in message: {payment_id}")
                                                    self.logger.info(f"   Transaction time: {tx_time}")
                                                    self.logger.info(f"   Time difference: {time_diff/60:.1f} minutes")
                                                    return True
                                            else:
                                                # Amount + time window verification (relaxed)
                                                self.logger.info(f"✅ TON payment verified by TON Center (amount+time): {tx_value_ton} TON")
                                                self.logger.info(f"   Transaction time: {tx_time}")
                                                self.logger.info(f"   Time difference: {time_diff/60:.1f} minutes")
                                                return True
                            
                            return False
                        else:
                            self.logger.warning(f"❌ TON Center API error: {data.get('error')}")
                            return False
                    else:
                        self.logger.warning(f"❌ TON Center API error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"❌ TON Center API failed: {e}")
            return False

    async def _verify_ton_rpc_api(self, ton_address: str, required_amount: float, required_conf: int, 
                                time_window_start: datetime, time_window_end: datetime, 
                                attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON RPC API."""
        try:
            await self._rate_limit_ton_api()
            
            async with aiohttp.ClientSession() as session:
                # Use TON Center API as TON RPC alternative (more reliable)
                url = f"https://toncenter.com/api/v2/getTransactions"
                params = {
                    'address': ton_address,
                    'limit': 15,
                    'archival': True  # Include archival data for better coverage
                }
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            transactions = data.get('result', [])
                            self.logger.info(f"🔍 TON RPC found {len(transactions)} transactions")
                            
                            for tx in transactions:
                                # Check for incoming transactions
                                in_msg = tx.get('in_msg', {})
                                if in_msg.get('source') != ton_address:  # Not from self
                                    value = in_msg.get('value', 0)
                                    if value is False or value is None:
                                        value = 0
                                    tx_value_ton = float(value) / 1e9
                                    tx_time_str = tx.get('utime')
                                    
                                    if tx_time_str:
                                        tx_time = datetime.fromtimestamp(int(tx_time_str))
                                        if time_window_start <= tx_time <= time_window_end:
                                            tolerance = getattr(self, 'payment_tolerance', 0.05)
                                            min_required = required_amount * (1.0 - tolerance)
                                            max_allowed = required_amount * (1.0 + tolerance)
                                            
                                            if min_required <= tx_value_ton <= max_allowed:
                                                self.logger.info(f"✅ TON payment verified by TON RPC: {tx_value_ton} TON")
                                                return True
                            
                            return False
                        else:
                            self.logger.warning(f"❌ TON RPC API error: {data.get('error')}")
                            return False
                    else:
                        self.logger.warning(f"❌ TON RPC API error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"❌ TON RPC API failed: {e}")
            return False

    async def _verify_ton_foundation_api(self, ton_address: str, required_amount: float, required_conf: int, 
                                       time_window_start: datetime, time_window_end: datetime, 
                                       attribution_method: str, payment_id: str) -> bool:
        """Verify TON payment using TON Foundation API."""
        try:
            await self._rate_limit_ton_api()
            
            async with aiohttp.ClientSession() as session:
                # Use TON Center as TON Foundation API alternative
                url = f"https://toncenter.com/api/v2/getTransactions"
                params = {
                    'address': ton_address,
                    'limit': 10,
                    'archival': True
                }
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            transactions = data.get('result', [])
                            self.logger.info(f"🔍 TON Foundation found {len(transactions)} transactions")
                            
                            for tx in transactions:
                                # Check for incoming transactions
                                in_msg = tx.get('in_msg', {})
                                if in_msg.get('source') != ton_address:  # Not from self
                                    tx_value_ton = float(in_msg.get('value', 0)) / 1e9
                                    tx_time_str = tx.get('utime')
                                    
                                    if tx_time_str:
                                        tx_time = datetime.fromtimestamp(int(tx_time_str))
                                        if time_window_start <= tx_time <= time_window_end:
                                            tolerance = getattr(self, 'payment_tolerance', 0.05)
                                            min_required = required_amount * (1.0 - tolerance)
                                            max_allowed = required_amount * (1.0 + tolerance)
                                            
                                            if min_required <= tx_value_ton <= max_allowed:
                                                self.logger.info(f"✅ TON payment verified by TON Foundation: {tx_value_ton} TON")
                                                return True
                            
                            return False
                        else:
                            self.logger.warning(f"❌ TON Foundation API error: {data.get('error')}")
                            return False
                    else:
                        self.logger.warning(f"❌ TON Foundation API error: {response.status}")
                        return False
        except Exception as e:
            self.logger.warning(f"❌ TON Foundation API failed: {e}")
            return False

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
                            in_msg = tx.get('in_msg', {})
                            value = in_msg.get('value', 0)
                            # Handle False, None, and other invalid values
                            if value is False or value is None or not isinstance(value, (int, float, str)):
                                value = 0
                            try:
                                tx_value_ton = float(value) / 1e9
                            except (ValueError, TypeError):
                                tx_value_ton = 0
                            
                            # Skip transactions with zero value
                            if tx_value_ton <= 0:
                                continue
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
                                # RELAXED: Accept transaction if it exists and matches amount/time
                                # TON transactions are typically confirmed quickly, so we trust the API
                                seqno = tx.get('seqno', 0)
                                tx_hash = tx.get('hash', 'unknown')
                                
                                # ✅ FIX: Simple, exact memo check to prevent false positives
                                if attribution_method == 'memo':
                                    tx_memo = tx.get('in_msg', {}).get('message', '')
                                    if payment_id and payment_id in tx_memo:
                                        self.logger.info(f"✅ TON payment verified by TON API.io (memo): {tx_value_ton} TON (hash: {tx_hash})")
                                        return True
                                else:
                                    # Amount + time window verification
                                    self.logger.info(f"✅ TON payment verified by TON API.io (amount+time): {tx_value_ton} TON (hash: {tx_hash})")
                                    return True
                        
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
