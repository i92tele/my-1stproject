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
from crypto_utils import EthereumPaymentData, SolanaPaymentMemo

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
            
            if crypto_config['provider'] == 'coinbase':
                payment_data = await self._create_coinbase_payment(payment_id, amount_usd, crypto_type)
            elif crypto_config['provider'] == 'direct':
                payment_data = await self._create_direct_payment(payment_id, amount_usd, crypto_type)
            else:
                raise ValueError(f"Unknown payment provider: {crypto_config['provider']}")
            
            # Record payment in database
            success = await self.db.record_payment(
                user_id=user_id,
                payment_id=payment_id,
                amount=payment_data['amount_crypto'],
                currency=crypto_type,
                status='pending',
                expires_at=expires_at,
                timeout_minutes=self.payment_timeout_minutes,
                crypto_type=crypto_type,
                payment_provider=crypto_config['provider'],
                provider_payment_id=payment_data.get('provider_payment_id'),
                expected_amount_crypto=payment_data.get('amount_crypto'),
                pay_to_address=payment_data.get('pay_to_address'),
                network=payment_data.get('network'),
                required_confirmations=1,
                attribution_method=payment_data.get('attribution_method', 'amount_only')
            )
            
            if not success:
                raise Exception("Failed to record payment in database")
            
            # Create ad slots for the user
            for i in range(tier_config['slots']):
                await self.db.create_ad_slot(user_id, i + 1)
            
            self.logger.info(f"✅ Created {crypto_type} payment request {payment_id} for user {user_id}")
            
            result = {
                'payment_id': payment_id,
                'amount_crypto': payment_data['amount_crypto'],
                'amount_usd': amount_usd,
                'crypto_type': crypto_type,
                'payment_url': payment_data['payment_url'],
                'expires_at': expires_at.isoformat(),
                'tier': tier,
                'slots_created': tier_config['slots'],
                'status': 'pending'
            }
            # Include address and memo for direct methods to support QR rendering in UI
            if crypto_config['provider'] == 'direct':
                result['pay_to_address'] = payment_data.get('pay_to_address')
                result['network'] = payment_data.get('network')
                result['payment_memo'] = payment_data.get('payment_memo')
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating payment request: {e}")
            return {
                'error': str(e),
                'success': False
            }
    
    async def _create_coinbase_payment(self, payment_id: str, amount_usd: float, crypto_type: str) -> Dict[str, Any]:
        """Create a payment using Coinbase Commerce API."""
        try:
            if not self.coinbase_api_key:
                raise Exception("Coinbase Commerce API key not configured")
            
            # Note: Webhook secret is optional for now - can be added later for enhanced security
            
            # Get crypto price
            crypto_price = await self._get_crypto_price(crypto_type)
            if not crypto_price:
                raise Exception(f"Unable to get {crypto_type} price")
            
            # Calculate crypto amount
            amount_crypto = amount_usd / crypto_price
            
            # Create Coinbase Commerce charge
            charge_data = {
                'name': f'Ad Slot Subscription - {crypto_type}',
                'description': f'Payment for ad slot subscription using {crypto_type}',
                'local_price': {
                    'amount': str(amount_usd),
                    'currency': 'USD'
                },
                'pricing_type': 'fixed_price',
                'metadata': {
                    'payment_id': payment_id,
                    'crypto_type': crypto_type
                },
                'redirect_url': f"https://t.me/your_bot_username?start=payment_{payment_id}",
                'cancel_url': f"https://t.me/your_bot_username?start=cancel_{payment_id}"
            }
            
            headers = {
                'X-CC-Api-Key': self.coinbase_api_key,
                'X-CC-Version': '2018-03-22',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.coinbase_api_url}/charges",
                    headers=headers,
                    json=charge_data
                ) as response:
                    if response.status == 201:
                        charge = await response.json()
                        return {
                            'amount_crypto': amount_crypto,
                            'payment_url': charge['data']['hosted_url'],
                            'provider_payment_id': charge['data']['id']
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"Coinbase API error: {response.status} - {error_text}")
                        
        except Exception as e:
            self.logger.error(f"Error creating Coinbase payment: {e}")
            raise
    
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
            else:
                raise Exception(f"Unsupported cryptocurrency: {crypto_type}")
                
        except Exception as e:
            self.logger.error(f"Error creating direct payment: {e}")
            raise
    
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
            
            if provider == 'coinbase':
                return await self._verify_coinbase_payment(payment)
            elif provider == 'direct':
                return await self._verify_direct_payment(payment)
            else:
                self.logger.error(f"Unknown payment provider: {provider}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying payment {payment_id}: {e}")
            return False
    
    async def _verify_coinbase_payment(self, payment: Dict[str, Any]) -> bool:
        """Verify payment using Coinbase Commerce API."""
        try:
            if not payment.get('provider_payment_id'):
                return False
            
            headers = {
                'X-CC-Api-Key': self.coinbase_api_key,
                'X-CC-Version': '2018-03-22'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.coinbase_api_url}/charges/{payment['provider_payment_id']}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        charge = await response.json()
                        status = charge['data']['timeline'][-1]['status']
                        
                        if status == 'COMPLETED':
                            await self.db.update_payment_status(payment['payment_id'], 'completed')
                            await self._activate_subscription(payment['user_id'], payment['payment_id'])
                            return True
                        elif status in ['EXPIRED', 'CANCELED']:
                            await self.db.update_payment_status(payment['payment_id'], 'expired')
                            return False
                        else:
                            # Still pending
                            return False
                    else:
                        self.logger.error(f"Coinbase API error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error verifying Coinbase payment: {e}")
            return False
    
    async def _verify_direct_payment(self, payment: Dict[str, Any]) -> bool:
        """Verify direct payment for all supported cryptocurrencies."""
        try:
            crypto_type = payment['crypto_type']
            required_amount = float(payment.get('expected_amount_crypto') or payment.get('amount') or 0)
            required_conf = int(payment.get('required_confirmations') or 1)
            
            self.logger.info(f"🔍 Verifying {crypto_type} payment: {payment.get('payment_id')}")
            self.logger.info(f"💰 Expected: {required_amount} {crypto_type} (min confirmations: {required_conf})")
            
            # Check if this payment uses unique addresses
            attribution_method = payment.get('attribution_method', 'amount_only')
            if attribution_method == 'unique_address':
                self.logger.info(f"🎯 Looking for: {required_amount} {crypto_type} to unique address")
            else:
                memo = payment.get('payment_id')
                self.logger.info(f"🎯 Looking for: {required_amount} {crypto_type} with memo '{memo}'")
            
            if crypto_type == 'TON':
                return await self._verify_ton_payment(payment, required_amount, required_conf, payment.get('payment_id'))
            elif crypto_type == 'BTC':
                return await self._verify_btc_payment(payment, required_amount, required_conf, payment.get('payment_id'))
            elif crypto_type == 'ETH':
                return await self._verify_eth_payment(payment, required_amount, required_conf, payment.get('payment_id'))
            elif crypto_type in ['USDT', 'USDC']:
                return await self._verify_erc20_payment(payment, required_amount, required_conf, payment.get('payment_id'))
            elif crypto_type == 'SOL':
                return await self._verify_sol_payment(payment, required_amount, required_conf, payment.get('payment_id'))
            elif crypto_type == 'LTC':
                return await self._verify_ltc_payment(payment, required_amount, required_conf, payment.get('payment_id'))
            else:
                self.logger.warning(f"Unsupported crypto type for verification: {crypto_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying direct payment: {e}")
            return False
    
    async def _verify_ton_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int, memo: str) -> bool:
        """Verify TON payment with optimized transaction monitoring."""
        try:
            ton_address = payment.get('pay_to_address') or getattr(self.config, 'ton_address', '') or os.getenv('TON_ADDRESS', '')
            if not ton_address:
                self.logger.error("TON address not configured for verification")
                return False
            
            # Fetch only recent transactions (last 10) to reduce clutter
            txs = await self._fetch_ton_recent_txs(ton_address, limit=10)
            self.logger.info(f"Found {len(txs)} recent transactions for {ton_address}")
            
            match = None
            for i, tx in enumerate(txs):
                self.logger.info(f"🔍 Processing TON TX {i+1}: {tx.get('hash', 'unknown')[:16]}...")
                
                # Extract transaction data
                comment = self._extract_ton_comment(tx)
                amount_ton = self._extract_ton_amount(tx)
                is_inbound = self._is_ton_inbound(tx, ton_address)
                confirmations = self._extract_ton_confirmations(tx)
                
                self.logger.info(f"TON TX {i+1}: amount={amount_ton}, inbound={is_inbound}, confirmations={confirmations}, comment='{comment}'")
                
                if not is_inbound:
                    self.logger.info(f"TON TX {i+1}: Skipping - not inbound to our address")
                    continue
                if comment != memo:
                    self.logger.info(f"TON TX {i+1}: Skipping - comment mismatch (expected: '{memo}', got: '{comment}')")
                    continue
                # Accept >= (required_amount * (1 - tolerance))
                # Use higher tolerance for very small amounts
                tolerance = self.payment_tolerance
                if required_amount < 1.0:  # For very small amounts, be more flexible
                    tolerance = max(tolerance, 0.05)  # At least 5% tolerance
                
                min_required = required_amount * (1.0 - max(0.0, min(tolerance, 0.2)))
                max_allowed = required_amount * (1.0 + max(0.0, min(tolerance, 0.2)))
                
                self.logger.info(f"TON TX {i+1}: Checking amount {amount_ton} vs required {required_amount} (range: {min_required} - {max_allowed})")
                
                if amount_ton < min_required or amount_ton > max_allowed:
                    self.logger.info(f"TON TX {i+1}: Amount out of range - {amount_ton} not in [{min_required}, {max_allowed}]")
                    continue
                
                if confirmations < required_conf:
                    self.logger.info(f"TON TX {i+1}: Not enough confirmations - {confirmations} < {required_conf}")
                    continue
                self.logger.info(f"✅ TX {i+1}: MATCH FOUND! amount={amount_ton}, comment='{comment}'")
                match = tx
                break
            
            if match:
                tx_hash = self._extract_ton_tx_hash(match)
                self.logger.info(f"✅ TON payment MATCHED! Completing verification...")
                await self._complete_payment_verification(payment, tx_hash)
                return True
            
            self.logger.warning(f"❌ No matching TON payment found for {payment.get('payment_id')}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying TON payment: {e}")
            return False
    
    async def _verify_btc_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int, memo: str) -> bool:
        """Verify Bitcoin payment using mempool.space API with standard address and time window."""
        try:
            # Get the standard BTC address
            btc_address = payment.get('pay_to_address')
            if not btc_address:
                self.logger.error("BTC address not found in payment data")
                return False
            
            self.logger.info(f"Verifying BTC payment to standard address: {btc_address}")
            
            # Fetch recent transactions from mempool.space
            txs = await self._fetch_btc_recent_txs(btc_address, limit=20)
            self.logger.info(f"Found {len(txs)} recent BTC transactions for {btc_address}")
            
            # Get payment creation time for time window matching
            payment_created = payment.get('created_at')
            if payment_created:
                payment_time = datetime.fromisoformat(payment_created.replace('Z', '+00:00'))
                time_window_start = payment_time - timedelta(minutes=30)  # 30 minutes before
                time_window_end = payment_time + timedelta(minutes=30)    # 30 minutes after
            else:
                time_window_start = datetime.now() - timedelta(minutes=60)  # Default 1 hour back
                time_window_end = datetime.now() + timedelta(minutes=30)
            
            self.logger.info(f"Time window: {time_window_start} to {time_window_end}")
            
            match = None
            for i, tx in enumerate(txs):
                self.logger.info(f"🔍 Processing BTC TX {i+1}: {tx.get('txid', 'unknown')[:16]}...")
                
                # Extract transaction data
                amount_btc = self._extract_btc_amount(tx, btc_address)
                is_inbound = self._is_btc_inbound(tx, btc_address)
                confirmations = self._extract_btc_confirmations(tx)
                tx_time = self._extract_btc_time(tx)
                
                self.logger.info(f"BTC TX {i+1}: amount={amount_btc}, inbound={is_inbound}, confirmations={confirmations}, time={tx_time}")
                
                if not is_inbound:
                    self.logger.info(f"BTC TX {i+1}: Skipping - not inbound to our address")
                    continue
                
                # Check time window
                if tx_time and (tx_time < time_window_start or tx_time > time_window_end):
                    self.logger.info(f"BTC TX {i+1}: Skipping - outside time window")
                    continue
                
                # Match by amount with tolerance
                tolerance = self.payment_tolerance
                if required_amount < 0.001:  # For very small amounts, be more flexible
                    tolerance = max(tolerance, 0.05)  # At least 5% tolerance
                
                min_required = required_amount * (1.0 - max(0.0, min(tolerance, 0.2)))
                max_allowed = required_amount * (1.0 + max(0.0, min(tolerance, 0.2)))
                
                self.logger.info(f"BTC TX {i+1}: Checking amount {amount_btc} vs required {required_amount} (range: {min_required} - {max_allowed})")
                
                if amount_btc < min_required or amount_btc > max_allowed:
                    self.logger.info(f"BTC TX {i+1}: Amount out of range - {amount_btc} not in [{min_required}, {max_allowed}]")
                    continue
                if confirmations < required_conf:
                    self.logger.info(f"BTC TX {i+1}: Not enough confirmations - {confirmations} < {required_conf}")
                    continue
                    
                self.logger.info(f"✅ BTC TX {i+1}: MATCH FOUND! amount={amount_btc} to standard address {btc_address}")
                match = tx
                break
            
            if match:
                tx_hash = self._extract_btc_tx_hash(match)
                self.logger.info(f"✅ BTC payment MATCHED! Completing verification...")
                await self._complete_payment_verification(payment, tx_hash)
                return True
            
            self.logger.warning(f"❌ No matching BTC payment found for {payment.get('payment_id')}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying BTC payment: {e}")
            return False
    
    async def _verify_eth_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int, memo: str) -> bool:
        """Verify Ethereum payment using Etherscan API with standard address and time window."""
        try:
            # Get the standard ETH address
            eth_address = payment.get('pay_to_address')
            if not eth_address:
                self.logger.error("ETH address not found in payment data")
                return False
            
            self.logger.info(f"Verifying ETH payment to standard address: {eth_address}")
            
            # Fetch recent transactions from Etherscan
            txs = await self._fetch_eth_recent_txs(eth_address, limit=20)
            self.logger.info(f"Found {len(txs)} recent ETH transactions for {eth_address}")
            
            # Get payment creation time for time window matching
            payment_created = payment.get('created_at')
            if payment_created:
                payment_time = datetime.fromisoformat(payment_created.replace('Z', '+00:00'))
                time_window_start = payment_time - timedelta(minutes=30)  # 30 minutes before
                time_window_end = payment_time + timedelta(minutes=30)    # 30 minutes after
            else:
                time_window_start = datetime.now() - timedelta(minutes=60)  # Default 1 hour back
                time_window_end = datetime.now() + timedelta(minutes=30)
            
            self.logger.info(f"Time window: {time_window_start} to {time_window_end}")
            
            match = None
            for i, tx in enumerate(txs):
                self.logger.info(f"🔍 Processing ETH TX {i+1}: {tx.get('hash', 'unknown')[:16]}...")
                
                # Extract transaction data
                amount_eth = self._extract_eth_amount(tx)
                is_inbound = self._is_eth_inbound(tx, eth_address)
                confirmations = self._extract_eth_confirmations(tx)
                tx_time = self._extract_eth_time(tx)
                
                self.logger.info(f"ETH TX {i+1}: amount={amount_eth}, inbound={is_inbound}, confirmations={confirmations}, time={tx_time}")
                
                if not is_inbound:
                    self.logger.info(f"ETH TX {i+1}: Skipping - not inbound to our address")
                    continue
                
                # Check time window
                if tx_time and (tx_time < time_window_start or tx_time > time_window_end):
                    self.logger.info(f"ETH TX {i+1}: Skipping - outside time window")
                    continue
                
                # Match by amount with tolerance
                tolerance = self.payment_tolerance
                if required_amount < 0.01:  # For very small amounts, be more flexible
                    tolerance = max(tolerance, 0.05)  # At least 5% tolerance
                
                min_required = required_amount * (1.0 - max(0.0, min(tolerance, 0.2)))
                max_allowed = required_amount * (1.0 + max(0.0, min(tolerance, 0.2)))
                
                self.logger.info(f"ETH TX {i+1}: Checking amount {amount_eth} vs required {required_amount} (range: {min_required} - {max_allowed})")
                
                if amount_eth < min_required or amount_eth > max_allowed:
                    self.logger.info(f"ETH TX {i+1}: Amount out of range - {amount_eth} not in [{min_required}, {max_allowed}]")
                    continue
                
                if confirmations < required_conf:
                    self.logger.info(f"ETH TX {i+1}: Not enough confirmations - {confirmations} < {required_conf}")
                    continue
                    
                self.logger.info(f"✅ ETH TX {i+1}: MATCH FOUND! amount={amount_eth} to standard address {eth_address}")
                match = tx
                break
            
            if match:
                tx_hash = self._extract_eth_tx_hash(match)
                self.logger.info(f"✅ ETH payment MATCHED! Completing verification...")
                await self._complete_payment_verification(payment, tx_hash)
                return True
            
            self.logger.warning(f"❌ No matching ETH payment found for {payment.get('payment_id')}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying ETH payment: {e}")
            return False
    
    async def _verify_erc20_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int, memo: str) -> bool:
        """Verify ERC-20 token payment (USDT/USDC) using Etherscan API with unique address support."""
        try:
            # Get the unique address for this payment
            eth_address = payment.get('pay_to_address')
            if not eth_address:
                self.logger.error("ETH address not found in payment data")
                return False
            
            crypto_type = payment['crypto_type']
            token_contract = self._get_erc20_contract_address(crypto_type)
            
            self.logger.info(f"Verifying {crypto_type} payment to unique address: {eth_address}")
            
            # Fetch recent ERC-20 transfers
            txs = await self._fetch_erc20_recent_txs(eth_address, token_contract, limit=10)
            self.logger.info(f"Found {len(txs)} recent {crypto_type} transactions for {eth_address}")
            
            match = None
            for i, tx in enumerate(txs):
                # Extract transaction data
                amount_token = self._extract_erc20_amount(tx, crypto_type)
                is_inbound = self._is_erc20_inbound(tx, eth_address)
                confirmations = self._extract_eth_confirmations(tx)
                
                # Only log potential matches
                if is_inbound and amount_token > 0:
                    self.logger.info(f"{crypto_type} TX {i+1}: amount={amount_token}, confirmations={confirmations}")
                
                if not is_inbound:
                    continue
                
                # For unique addresses, we match by amount (no memo needed)
                min_required = required_amount * (1.0 - max(0.0, min(self.payment_tolerance, 0.2)))
                if amount_token + 1e-9 < min_required:
                    continue
                if confirmations < required_conf:
                    continue
                    
                self.logger.info(f"✅ {crypto_type} TX {i+1}: MATCH FOUND! amount={amount_token} to unique address {eth_address}")
                match = tx
                break
            
            if match:
                tx_hash = self._extract_eth_tx_hash(match)
                await self._complete_payment_verification(payment, tx_hash)
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying {payment['crypto_type']} payment: {e}")
            return False
    
    async def _verify_sol_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int, memo: str) -> bool:
        """Verify Solana payment using Solana RPC API with standard address and memo support."""
        try:
            # Get the standard SOL address
            sol_address = payment.get('pay_to_address')
            if not sol_address:
                self.logger.error("SOL address not found in payment data")
                return False
            
            self.logger.info(f"Verifying SOL payment to standard address: {sol_address}")
            
            # Fetch recent transactions from Solana
            txs = await self._fetch_sol_recent_txs(sol_address, limit=20)
            self.logger.info(f"Found {len(txs)} recent SOL transactions for {sol_address}")
            
            match = None
            for i, tx in enumerate(txs):
                self.logger.info(f"🔍 Processing SOL TX {i+1}: {tx.get('signature', 'unknown')[:16]}...")
                
                # Extract transaction data
                amount_sol = self._extract_sol_amount(tx)
                is_inbound = self._is_sol_inbound(tx, sol_address)
                confirmations = self._extract_sol_confirmations(tx)
                memo_from_tx = SolanaPaymentMemo.extract_memo_from_transaction(tx)
                
                self.logger.info(f"SOL TX {i+1}: amount={amount_sol}, inbound={is_inbound}, confirmations={confirmations}, memo={memo_from_tx}")
                
                if not is_inbound:
                    self.logger.info(f"SOL TX {i+1}: Skipping - not inbound to our address")
                    continue
                
                # For SOL, we can use memo for attribution (more reliable than amount matching)
                if memo and memo_from_tx and memo == memo_from_tx:
                    self.logger.info(f"✅ SOL TX {i+1}: MATCH FOUND! amount={amount_sol} with memo '{memo}'")
                    match = tx
                    break
                
                # Fallback: match by amount with tolerance (if no memo match)
                tolerance = self.payment_tolerance
                if required_amount < 0.1:  # For very small amounts, be more flexible
                    tolerance = max(tolerance, 0.05)  # At least 5% tolerance
                
                min_required = required_amount * (1.0 - max(0.0, min(tolerance, 0.2)))
                max_allowed = required_amount * (1.0 + max(0.0, min(tolerance, 0.2)))
                
                self.logger.info(f"SOL TX {i+1}: Checking amount {amount_sol} vs required {required_amount} (range: {min_required} - {max_allowed})")
                
                if amount_sol < min_required or amount_sol > max_allowed:
                    self.logger.info(f"SOL TX {i+1}: Amount out of range - {amount_sol} not in [{min_required}, {max_allowed}]")
                    continue
                
                if confirmations < required_conf:
                    self.logger.info(f"SOL TX {i+1}: Not enough confirmations - {confirmations} < {required_conf}")
                    continue
                    
                self.logger.info(f"✅ SOL TX {i+1}: MATCH FOUND! amount={amount_sol} to standard address {sol_address}")
                match = tx
                break
            
            if match:
                tx_hash = self._extract_sol_tx_hash(match)
                self.logger.info(f"✅ SOL payment MATCHED! Completing verification...")
                await self._complete_payment_verification(payment, tx_hash)
                return True
            
            self.logger.warning(f"❌ No matching SOL payment found for {payment.get('payment_id')}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying SOL payment: {e}")
            return False
    
    async def _verify_ltc_payment(self, payment: Dict[str, Any], required_amount: float, required_conf: int, memo: str) -> bool:
        """Verify Litecoin payment using standard address and time window attribution."""
        try:
            ltc_address = payment.get('pay_to_address')  # This is the standard address
            if not ltc_address:
                self.logger.error("LTC address not found in payment data")
                return False
            
            self.logger.info(f"Verifying LTC payment to standard address: {ltc_address}")
            
            # Fetch recent transactions from Litecoin API (similar to Bitcoin)
            txs = await self._fetch_ltc_recent_txs(ltc_address, limit=20)
            self.logger.info(f"Found {len(txs)} recent LTC transactions for {ltc_address}")
            
            # Get payment creation time for time window matching
            payment_created = payment.get('created_at')
            if payment_created:
                payment_time = datetime.fromisoformat(payment_created.replace('Z', '+00:00'))
                time_window_start = payment_time - timedelta(minutes=30)  # 30 minutes before
                time_window_end = payment_time + timedelta(minutes=30)    # 30 minutes after
            else:
                time_window_start = datetime.now() - timedelta(minutes=60)  # Default 1 hour back
                time_window_end = datetime.now() + timedelta(minutes=30)
            
            self.logger.info(f"Time window: {time_window_start} to {time_window_end}")
            
            match = None
            for i, tx in enumerate(txs):
                self.logger.info(f"🔍 Processing LTC TX {i+1}: {tx.get('txid', 'unknown')[:16]}...")
                
                # Extract transaction data
                amount_ltc = self._extract_ltc_amount(tx)
                is_inbound = self._is_ltc_inbound(tx, ltc_address)
                confirmations = self._extract_ltc_confirmations(tx)
                tx_time = self._extract_ltc_time(tx)
                
                self.logger.info(f"LTC TX {i+1}: amount={amount_ltc}, inbound={is_inbound}, confirmations={confirmations}, time={tx_time}")
                
                if not is_inbound:
                    self.logger.info(f"LTC TX {i+1}: Skipping - not inbound to our address")
                    continue
                
                # Check time window
                if tx_time and (tx_time < time_window_start or tx_time > time_window_end):
                    self.logger.info(f"LTC TX {i+1}: Skipping - outside time window")
                    continue
                
                # Match by amount with tolerance
                tolerance = self.payment_tolerance
                if required_amount < 0.01:  # For very small amounts, be more flexible
                    tolerance = max(tolerance, 0.05)  # At least 5% tolerance
                
                min_required = required_amount * (1.0 - max(0.0, min(tolerance, 0.2)))
                max_allowed = required_amount * (1.0 + max(0.0, min(tolerance, 0.2)))
                
                self.logger.info(f"LTC TX {i+1}: Checking amount {amount_ltc} vs required {required_amount} (range: {min_required} - {max_allowed})")
                
                if amount_ltc < min_required or amount_ltc > max_allowed:
                    self.logger.info(f"LTC TX {i+1}: Amount out of range - {amount_ltc} not in [{min_required}, {max_allowed}]")
                    continue
                
                if confirmations < required_conf:
                    self.logger.info(f"LTC TX {i+1}: Not enough confirmations - {confirmations} < {required_conf}")
                    continue
                    
                self.logger.info(f"✅ LTC TX {i+1}: MATCH FOUND! amount={amount_ltc} to standard address {ltc_address}")
                match = tx
                break
            
            if match:
                tx_hash = self._extract_ltc_tx_hash(match)
                self.logger.info(f"✅ LTC payment MATCHED! Completing verification...")
                await self._complete_payment_verification(payment, tx_hash)
                return True
            
            self.logger.warning(f"❌ No matching LTC payment found for {payment.get('payment_id')}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying LTC payment: {e}")
            return False
    
    async def _complete_payment_verification(self, payment: Dict[str, Any], tx_hash: str) -> None:
        """Complete payment verification process."""
        await self.db.update_payment_detection(
            payment['payment_id'],
            detected_tx_hash=tx_hash,
            detected_at=datetime.now(),
            confirmed_at=datetime.now()
        )
        await self.db.update_payment_status(payment['payment_id'], 'completed')
        await self._activate_subscription(payment['user_id'], payment['payment_id'])

    async def _fetch_ton_recent_txs(self, address: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent transactions to the given TON address using TonAPI or Toncenter."""
        self.logger.info(f"🌐 Fetching {limit} transactions for TON address: {address}")
        
        # Try TonAPI first
        try:
            headers = {}
            if self.ton_api_key:
                headers['Authorization'] = f"Bearer {self.ton_api_key}"
            
            url = f"{self.ton_api_base.rstrip('/')}/v2/accounts/{address}/transactions?limit={limit}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        txs = data.get('transactions') if isinstance(data, dict) else data
                        result_txs = txs or []
                        self.logger.info(f"TonAPI returned {len(result_txs)} transactions")
                        if result_txs:
                            return result_txs
                    else:
                        error_text = await resp.text()
                        self.logger.warning(f"TonAPI error {resp.status}: {error_text}")
        except Exception as e:
            self.logger.warning(f"TonAPI fetch failed: {e}")

        # Fallback: Toncenter
        try:
            params = {'address': address, 'limit': limit}
            headers = {}
            if self.toncenter_api_key:
                headers['X-API-Key'] = self.toncenter_api_key
            
            url = "https://toncenter.com/api/v2/getTransactions"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        txs = data.get('result') or []
                        self.logger.info(f"Toncenter returned {len(txs)} transactions")
                        return txs
                    else:
                        error_text = await resp.text()
                        self.logger.warning(f"Toncenter error {resp.status}: {error_text}")
        except Exception as e:
            self.logger.warning(f"Toncenter fetch failed: {e}")
        
        self.logger.error("❌ All TON API attempts failed - no transactions fetched")
        return []
    
    async def _fetch_btc_recent_txs(self, address: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent Bitcoin transactions using mempool.space API."""
        self.logger.info(f"🌐 Fetching {limit} transactions for BTC address: {address}")
        
        try:
            # Use mempool.space API (free, no API key required)
            url = f"https://mempool.space/api/address/{address}/txs"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        txs = await resp.json()
                        # Limit to most recent transactions
                        limited_txs = txs[:limit] if isinstance(txs, list) else []
                        self.logger.info(f"Mempool.space returned {len(limited_txs)} transactions")
                        return limited_txs
                    else:
                        error_text = await resp.text()
                        self.logger.warning(f"Mempool.space error {resp.status}: {error_text}")
        except Exception as e:
            self.logger.warning(f"Mempool.space fetch failed: {e}")
        
        return []
    
    async def _fetch_eth_recent_txs(self, address: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent Ethereum transactions using Etherscan API."""
        self.logger.info(f"🌐 Fetching {limit} transactions for ETH address: {address}")
        
        try:
            # Get Etherscan API key from config
            etherscan_api_key = getattr(self.config, 'etherscan_api_key', '') or os.getenv('ETHERSCAN_API_KEY', '')
            
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': address,
                'startblock': 0,
                'endblock': 99999999,
                'page': 1,
                'offset': limit,
                'sort': 'desc',
                'apikey': etherscan_api_key
            }
            
            url = "https://api.etherscan.io/api"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('status') == '1':
                            txs = data.get('result', [])
                            self.logger.info(f"Etherscan returned {len(txs)} transactions")
                            return txs
                        else:
                            self.logger.warning(f"Etherscan API error: {data.get('message', 'Unknown error')}")
                    else:
                        error_text = await resp.text()
                        self.logger.warning(f"Etherscan error {resp.status}: {error_text}")
        except Exception as e:
            self.logger.warning(f"Etherscan fetch failed: {e}")
        
        return []
    
    async def _fetch_erc20_recent_txs(self, address: str, token_contract: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent ERC-20 token transfers using Etherscan API."""
        self.logger.info(f"🌐 Fetching {limit} ERC-20 transfers for address: {address}")
        
        try:
            # Get Etherscan API key from config
            etherscan_api_key = getattr(self.config, 'etherscan_api_key', '') or os.getenv('ETHERSCAN_API_KEY', '')
            
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': token_contract,
                'address': address,
                'startblock': 0,
                'endblock': 99999999,
                'page': 1,
                'offset': limit,
                'sort': 'desc',
                'apikey': etherscan_api_key
            }
            
            url = "https://api.etherscan.io/api"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('status') == '1':
                            txs = data.get('result', [])
                            self.logger.info(f"Etherscan ERC-20 returned {len(txs)} transactions")
                            return txs
                        else:
                            self.logger.warning(f"Etherscan ERC-20 API error: {data.get('message', 'Unknown error')}")
                    else:
                        error_text = await resp.text()
                        self.logger.warning(f"Etherscan ERC-20 error {resp.status}: {error_text}")
        except Exception as e:
            self.logger.warning(f"Etherscan ERC-20 fetch failed: {e}")
        
        return []

    def _extract_ton_comment(self, tx: Dict[str, Any]) -> Optional[str]:
        """Extract comment/memo from TON transaction - fixed for actual TonAPI v2 format."""
        comment = None
        try:
            # TonAPI v2 format: tx.in_msg.decoded_body.comment
            if 'in_msg' in tx and tx['in_msg'] and 'decoded_body' in tx['in_msg']:
                decoded = tx['in_msg']['decoded_body']
                if decoded and 'comment' in decoded:
                    comment = str(decoded['comment']).strip()
                    if comment:
                        return self._decode_comment_if_needed(comment)
            
            # TonAPI v2 alternative: tx.in_msg.msg_data.text  
            if 'in_msg' in tx and tx['in_msg'] and 'msg_data' in tx['in_msg']:
                msg_data = tx['in_msg']['msg_data']
                if isinstance(msg_data, dict) and 'text' in msg_data:
                    comment = str(msg_data['text']).strip()
                    if comment:
                        return self._decode_comment_if_needed(comment)
            
            # TonAPI v2 alternative: direct comment field
            if 'comment' in tx:
                comment = str(tx['comment']).strip()
                if comment:
                    return self._decode_comment_if_needed(comment)
                    
            # Toncenter format: in_msg.message or msg.body.data
            if 'in_msg' in tx and tx['in_msg']:
                in_msg = tx['in_msg']
                if 'message' in in_msg:
                    comment = str(in_msg['message']).strip()
                    if comment:
                        return self._decode_comment_if_needed(comment)
                        
        except Exception as e:
            self.logger.debug(f"Error extracting comment: {e}")
            
        return None
    
    def _extract_btc_amount(self, tx: Dict[str, Any], target_address: str = None) -> float:
        """Extract BTC amount from transaction."""
        try:
            # Debug: log the transaction structure
            self.logger.debug(f"BTC TX structure: {list(tx.keys())}")
            
            # Mempool.space format - check multiple possible fields
            if 'value' in tx:
                # Convert satoshis to BTC
                satoshis = int(tx['value'])
                amount = float(satoshis) / 100000000
                self.logger.debug(f"BTC amount from 'value': {amount}")
                return amount
            elif 'amount' in tx:
                # Direct BTC amount
                amount = float(tx['amount'])
                self.logger.debug(f"BTC amount from 'amount': {amount}")
                return amount
            elif 'vout' in tx:
                # Sum up only outputs to our specific address
                total_amount = 0.0
                for output in tx['vout']:
                    output_address = output.get('scriptpubkey_address', '')
                    if output_address == target_address and 'value' in output:
                        # Check if value is in satoshis or BTC
                        value = float(output['value'])
                        if value > 1.0:  # Likely satoshis
                            value = value / 100000000  # Convert to BTC
                        total_amount += value
                        self.logger.debug(f"Found output to our address: {value} BTC")
                self.logger.debug(f"BTC amount to our address: {total_amount}")
                return total_amount
            
            self.logger.warning(f"Could not extract BTC amount from transaction: {tx}")
            return 0.0
        except Exception as e:
            self.logger.error(f"Error extracting BTC amount: {e}")
            return 0.0
    
    def _is_btc_inbound(self, tx: Dict[str, Any], address: str) -> bool:
        """Check if BTC transaction is inbound to our address."""
        try:
            # Debug: log what we're checking
            self.logger.debug(f"Checking if BTC TX is inbound to {address}")
            
            # Check if our address is in the outputs
            if 'vout' in tx:
                for i, output in enumerate(tx['vout']):
                    output_address = output.get('scriptpubkey_address', '')
                    if output_address == address:
                        self.logger.debug(f"Found inbound transaction in output {i}: {output_address}")
                        return True
                    else:
                        self.logger.debug(f"Output {i} address: {output_address} (not matching)")
            
            self.logger.debug(f"No inbound transaction found for address {address}")
            return False
        except Exception as e:
            self.logger.error(f"Error checking BTC inbound: {e}")
            return False
    
    def _extract_btc_confirmations(self, tx: Dict[str, Any]) -> int:
        """Extract BTC confirmation count."""
        try:
            return int(tx.get('status', {}).get('confirmed', False))
        except Exception:
            return 0
    
    def _extract_btc_time(self, tx: Dict[str, Any]) -> Optional[datetime]:
        """Extract transaction time from BTC transaction."""
        try:
            timestamp = tx.get('status', {}).get('block_time')
            if timestamp:
                return datetime.fromtimestamp(timestamp)
            return None
        except:
            return None
    
    def _extract_btc_tx_hash(self, tx: Dict[str, Any]) -> Optional[str]:
        """Extract BTC transaction hash."""
        return tx.get('txid')
    
    def _extract_eth_amount(self, tx: Dict[str, Any]) -> float:
        """Extract ETH amount from transaction."""
        try:
            # Debug: log the transaction structure
            self.logger.debug(f"ETH TX structure: {list(tx.keys())}")
            
            # Etherscan format - convert from wei to ETH
            if 'value' in tx:
                wei = int(tx['value'])
                amount = float(wei) / 1e18
                self.logger.debug(f"ETH amount from 'value': {amount} (wei: {wei})")
                return amount
            
            self.logger.warning(f"Could not extract ETH amount from transaction: {tx}")
            return 0.0
        except Exception as e:
            self.logger.error(f"Error extracting ETH amount: {e}")
            return 0.0
    
    def _is_eth_inbound(self, tx: Dict[str, Any], address: str) -> bool:
        """Check if ETH transaction is inbound to our address."""
        try:
            return tx.get('to', '').lower() == address.lower()
        except Exception:
            return False
    
    def _extract_eth_confirmations(self, tx: Dict[str, Any]) -> int:
        """Extract ETH confirmation count."""
        try:
            # For ETH, we consider it confirmed if it has a block number
            return 1 if tx.get('blockNumber') else 0
        except Exception:
            return 0
    
    def _extract_eth_time(self, tx: Dict[str, Any]) -> Optional[datetime]:
        """Extract transaction time from ETH transaction."""
        try:
            timestamp = tx.get('timeStamp')
            if timestamp:
                return datetime.fromtimestamp(int(timestamp))
            return None
        except:
            return None
    
    def _extract_eth_tx_hash(self, tx: Dict[str, Any]) -> Optional[str]:
        """Extract ETH transaction hash."""
        return tx.get('hash')
    
    def _extract_eth_data(self, tx: Dict[str, Any]) -> Optional[str]:
        """Extract ETH transaction data field."""
        return tx.get('input', '')
    
    def _extract_sol_amount(self, tx: Dict[str, Any]) -> float:
        """Extract SOL amount from transaction."""
        try:
            # Debug: log the transaction structure
            self.logger.debug(f"SOL TX structure: {list(tx.keys())}")
            
            # Solana format - convert from lamports to SOL
            if 'amount' in tx:
                lamports = int(tx['amount'])
                amount = float(lamports) / 1e9  # 1 SOL = 1e9 lamports
                self.logger.debug(f"SOL amount from 'amount': {amount} (lamports: {lamports})")
                return amount
            
            self.logger.warning(f"Could not extract SOL amount from transaction: {tx}")
            return 0.0
        except Exception as e:
            self.logger.error(f"Error extracting SOL amount: {e}")
            return 0.0
    
    def _extract_ltc_amount(self, tx: Dict[str, Any]) -> float:
        """Extract LTC amount from transaction."""
        try:
            # Debug: log the transaction structure
            self.logger.debug(f"LTC TX structure: {list(tx.keys())}")
            
            # Litecoin format - similar to Bitcoin
            if 'value' in tx:
                # Convert satoshis to LTC
                satoshis = int(tx['value'])
                amount = float(satoshis) / 100000000
                self.logger.debug(f"LTC amount from 'value': {amount} (satoshis: {satoshis})")
                return amount
            elif 'amount' in tx:
                # Direct LTC amount
                amount = float(tx['amount'])
                self.logger.debug(f"LTC amount from 'amount': {amount}")
                return amount
            
            self.logger.warning(f"Could not extract LTC amount from transaction: {tx}")
            return 0.0
        except Exception as e:
            self.logger.error(f"Error extracting LTC amount: {e}")
            return 0.0
    
    def _extract_ltc_confirmations(self, tx: Dict[str, Any]) -> int:
        """Extract LTC confirmation count."""
        try:
            return int(tx.get('confirmations', 0))
        except Exception:
            return 0
    
    def _extract_ltc_time(self, tx: Dict[str, Any]) -> Optional[datetime]:
        """Extract transaction time from LTC transaction."""
        try:
            timestamp = tx.get('time')
            if timestamp:
                return datetime.fromtimestamp(timestamp)
            return None
        except:
            return None
    
    def _is_ltc_inbound(self, tx: Dict[str, Any], address: str) -> bool:
        """Check if LTC transaction is inbound to our address."""
        try:
            # Check if any output goes to our address
            if 'outputs' in tx:
                for output in tx['outputs']:
                    if output.get('addresses', []) and address in output['addresses']:
                        return True
            return False
        except Exception:
            return False
    
    def _extract_ltc_tx_hash(self, tx: Dict[str, Any]) -> Optional[str]:
        """Extract LTC transaction hash."""
        try:
            return tx.get('txid') or tx.get('hash')
        except Exception:
            return None
    
    def _extract_erc20_amount(self, tx: Dict[str, Any], crypto_type: str) -> float:
        """Extract ERC-20 token amount from transaction."""
        try:
            # Etherscan ERC-20 format
            if 'value' in tx:
                # Get token decimals
                decimals = int(tx.get('tokenDecimal', 18))
                raw_value = int(tx['value'])
                return float(raw_value) / (10 ** decimals)
            return 0.0
        except Exception:
            return 0.0
    
    def _is_erc20_inbound(self, tx: Dict[str, Any], address: str) -> bool:
        """Check if ERC-20 transaction is inbound to our address."""
        try:
            return tx.get('to', '').lower() == address.lower()
        except Exception:
            return False
    
    def _get_erc20_contract_address(self, crypto_type: str) -> str:
        """Get ERC-20 contract address for the given token."""
        contracts = {
            'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # Ethereum USDT
            'USDC': '0xA0b86a33E6441b8c4C8C8C8C8C8C8C8C8C8C8C8C8'  # Ethereum USDC (placeholder)
        }
        return contracts.get(crypto_type, '')
    
    def _decode_comment_if_needed(self, comment: str) -> str:
        """Decode Base64 encoded comments if needed."""
        try:
            # Try Base64 decoding if it looks like Base64
            import base64
            if len(comment) > 10 and comment.replace('=', '').replace('+', '').replace('/', '').isalnum():
                try:
                    decoded_bytes = base64.b64decode(comment)
                    decoded_text = decoded_bytes.decode('utf-8')
                    self.logger.debug(f"Decoded Base64 comment: '{comment}' → '{decoded_text}'")
                    return decoded_text
                except Exception:
                    # Not Base64, return original
                    pass
            return comment
        except Exception:
            return comment

    def _extract_ton_amount(self, tx: Dict[str, Any]) -> float:
        """Extract inbound value in TON - fixed for actual TonAPI v2 format."""
        try:
            # Debug: log the transaction structure
            self.logger.debug(f"TON TX structure: {list(tx.keys())}")
            
            # TonAPI v2 format: tx.in_msg.value (in nanotons)
            if 'in_msg' in tx and tx['in_msg'] and 'value' in tx['in_msg']:
                value = tx['in_msg']['value']
                if value is not None:
                    # Convert nanotons to TON
                    amount = float(int(value)) / 1e9
                    self.logger.debug(f"TON amount from 'in_msg.value': {amount} (nanotons: {value})")
                    return amount
            
            # Alternative: direct value field
            if 'value' in tx:
                value = tx['value']
                if value is not None:
                    amount = float(int(value)) / 1e9
                    self.logger.debug(f"TON amount from 'value': {amount} (nanotons: {value})")
                    return amount
                    
            # Toncenter format: in_msg.value as string
            if 'in_msg' in tx and tx['in_msg']:
                in_msg = tx['in_msg']
                if 'value' in in_msg and in_msg['value']:
                    value = in_msg['value']
                    # Handle both string and int values
                    if isinstance(value, str):
                        amount = float(int(value)) / 1e9
                        self.logger.debug(f"TON amount from 'in_msg.value' (string): {amount} (nanotons: {value})")
                        return amount
                    elif isinstance(value, (int, float)):
                        amount = float(value) / 1e9
                        self.logger.debug(f"TON amount from 'in_msg.value' (number): {amount} (nanotons: {value})")
                        return amount
            
            self.logger.warning(f"Could not extract TON amount from transaction: {tx}")
            return 0.0
                        
        except Exception as e:
            self.logger.error(f"Error extracting TON amount: {e}")
            return 0.0

    def _is_ton_inbound(self, tx: Dict[str, Any], address: str) -> bool:
        """Check if transaction is inbound to our address - fixed for actual TonAPI v2 format."""
        try:
            # TonAPI v2: For inbound transactions, check account_address or use transaction type
            # In TonAPI v2, we typically filter by account already, so all should be relevant to our address
            
            # Method 1: Check if transaction has in_msg with positive value
            if 'in_msg' in tx and tx['in_msg'] and 'value' in tx['in_msg']:
                value = tx['in_msg']['value']
                if value and int(value) > 0:
                    return True
            
            # Method 2: Check destination address if available
            if 'in_msg' in tx and tx['in_msg']:
                in_msg = tx['in_msg']
                
                # Check destination field
                destination = in_msg.get('destination')
                if destination:
                    # Normalize addresses for comparison (remove case sensitivity)
                    return self._normalize_ton_address(destination) == self._normalize_ton_address(address)
                
                # Check alternative destination fields
                dst = in_msg.get('dst') or in_msg.get('to')
                if dst:
                    return self._normalize_ton_address(dst) == self._normalize_ton_address(address)
            
            # Method 3: Check transaction type and account
            if 'account' in tx:
                account = tx['account'].get('address') if isinstance(tx['account'], dict) else tx['account']
                if account:
                    return self._normalize_ton_address(account) == self._normalize_ton_address(address)
                    
            # If no specific address match, and we fetched transactions for this address,
            # assume it's relevant (TonAPI filters by account)
            return True
            
        except Exception as e:
            self.logger.debug(f"Error checking inbound status: {e}")
            return False
    
    def _normalize_ton_address(self, address: str) -> str:
        """Normalize TON address for comparison (handle different formats)."""
        if not address:
            return ""
        # Convert to lowercase and remove any prefixes
        addr = str(address).lower().strip()
        # Remove common TON address prefixes if present
        if addr.startswith('0:'):
            return addr
        if addr.startswith('uq') or addr.startswith('eq'):
            return addr
        return addr

    def _extract_ton_confirmations(self, tx: Dict[str, Any]) -> int:
        # TON confirmation concept differs; we treat presence in latest blocks as confirmed (use 1)
        # If tx has 'utime' and 'block' info, we could infer; for simplicity, return 1 for now
        return 1

    def _extract_ton_tx_hash(self, tx: Dict[str, Any]) -> Optional[str]:
        """Extract transaction hash from TON transaction - fixed for TonAPI v2."""
        try:
            # TonAPI v2 format: hash field
            if 'hash' in tx and tx['hash']:
                return str(tx['hash'])
            
            # Alternative fields
            if 'transaction_id' in tx and tx['transaction_id']:
                return str(tx['transaction_id'])
                
            if 'id' in tx and tx['id']:
                return str(tx['id'])
                
            # Toncenter format
            if 'tx_hash' in tx and tx['tx_hash']:
                return str(tx['tx_hash'])
                
        except Exception as e:
            self.logger.debug(f"Error extracting tx hash: {e}")
            
        return None
    
    async def debug_ton_transaction_format(self, address: str) -> Dict[str, Any]:
        """Debug method to examine actual API response format."""
        self.logger.info(f"🔧 DEBUG: Fetching transactions for {address} to examine format")
        
        try:
            # Try TonAPI first
            headers = {}
            if self.ton_api_key:
                headers['Authorization'] = f"Bearer {self.ton_api_key}"
            
            url = f"{self.ton_api_base.rstrip('/')}/v2/accounts/{address}/transactions?limit=5"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.logger.info(f"🔧 DEBUG: TonAPI Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        # Extract transactions
                        txs = data.get('transactions') if isinstance(data, dict) else data
                        if txs and len(txs) > 0:
                            first_tx = txs[0]
                            self.logger.info(f"🔧 DEBUG: First Transaction Keys: {list(first_tx.keys()) if isinstance(first_tx, dict) else 'Not a dict'}")
                            
                            if 'in_msg' in first_tx:
                                in_msg = first_tx['in_msg']
                                self.logger.info(f"🔧 DEBUG: in_msg Keys: {list(in_msg.keys()) if isinstance(in_msg, dict) else 'Not a dict'}")
                                
                                if 'decoded_body' in in_msg:
                                    decoded = in_msg['decoded_body']
                                    self.logger.info(f"🔧 DEBUG: decoded_body Keys: {list(decoded.keys()) if isinstance(decoded, dict) else 'Not a dict'}")
                            
                            return {
                                'status': 'success',
                                'api': 'tonapi',
                                'sample_transaction': first_tx,
                                'total_transactions': len(txs)
                            }
                    else:
                        error_text = await resp.text()
                        self.logger.error(f"🔧 DEBUG: TonAPI Error {resp.status}: {error_text}")
                        
        except Exception as e:
            self.logger.error(f"🔧 DEBUG: TonAPI failed: {e}")
        
        # Try Toncenter fallback
        try:
            params = {'address': address, 'limit': 5}
            headers = {}
            if self.toncenter_api_key:
                headers['X-API-Key'] = self.toncenter_api_key
            
            url = "https://toncenter.com/api/v2/getTransactions"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.logger.info(f"🔧 DEBUG: Toncenter Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        txs = data.get('result') or []
                        if txs and len(txs) > 0:
                            first_tx = txs[0]
                            self.logger.info(f"🔧 DEBUG: First Toncenter TX Keys: {list(first_tx.keys()) if isinstance(first_tx, dict) else 'Not a dict'}")
                            
                            return {
                                'status': 'success',
                                'api': 'toncenter',
                                'sample_transaction': first_tx,
                                'total_transactions': len(txs)
                            }
                    else:
                        error_text = await resp.text()
                        self.logger.error(f"🔧 DEBUG: Toncenter Error {resp.status}: {error_text}")
                        
        except Exception as e:
            self.logger.error(f"🔧 DEBUG: Toncenter failed: {e}")
        
        return {'status': 'failed', 'error': 'Both APIs failed'}
    
    async def _activate_subscription(self, user_id: int, payment_id: str) -> bool:
        """Activate user subscription after successful payment."""
        try:
            self.logger.info(f"🎯 Activating subscription for user {user_id}, payment {payment_id}")
            
            payment = await self.db.get_payment(payment_id)
            if not payment:
                self.logger.error(f"Payment {payment_id} not found in database")
                return False
            
            self.logger.info(f"💰 Payment details: {payment['amount']} {payment['crypto_type']}")
            
            # Determine tier from payment amount using real-time prices
            tier = await self._determine_tier_from_amount(payment['amount'], payment['crypto_type'])
            if not tier:
                self.logger.error(f"Could not determine tier for payment {payment_id}")
                return False
            
            self.logger.info(f"📋 Determined tier: {tier}")
            
            # Activate subscription
            success = await self.db.activate_subscription(
                user_id=user_id,
                tier=tier,
                duration_days=self.tiers[tier]['duration_days']
            )
            
            if success:
                self.logger.info(f"✅ Subscription activated: user {user_id}, tier {tier}")
                
                # Verify ad slots are properly limited
                ad_slots = await self.db.get_or_create_ad_slots(user_id, tier)
                self.logger.info(f"📢 Ad slots after activation: {len(ad_slots)} slots for tier {tier}")
            else:
                self.logger.error(f"❌ Failed to activate subscription for user {user_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error activating subscription: {e}")
            return False
    
    async def _determine_tier_from_amount(self, amount: float, crypto_type: str) -> Optional[str]:
        """Determine subscription tier from payment amount using real-time prices."""
        try:
            self.logger.info(f"Determining tier for payment: {amount} {crypto_type}")
            
            # Get current crypto price in USD
            crypto_price = await self._get_crypto_price(crypto_type)
            if not crypto_price:
                self.logger.warning(f"Could not fetch {crypto_type} price, using fallback")
                return self._determine_tier_fallback(amount, crypto_type)
            
            # Convert crypto amount to USD value
            usd_value = amount * crypto_price
            self.logger.info(f"Payment value: {amount} {crypto_type} = ${usd_value:.2f} USD (price: ${crypto_price:.2f})")
            
            # Match to tier based on USD value with tolerance
            tolerance = 5.0  # $5 tolerance for price fluctuations
            
            for tier, config in self.tiers.items():
                tier_price = config['price_usd']
                if abs(usd_value - tier_price) <= tolerance:
                    self.logger.info(f"Matched tier: {tier} (target: ${tier_price}, actual: ${usd_value:.2f})")
                    return tier
            
            # If no exact match, find closest tier
            closest_tier = None
            closest_diff = float('inf')
            
            for tier, config in self.tiers.items():
                diff = abs(usd_value - config['price_usd'])
                if diff < closest_diff:
                    closest_diff = diff
                    closest_tier = tier
            
            if closest_tier and closest_diff <= 15.0:  # Max $15 difference allowed
                self.logger.info(f"Using closest tier: {closest_tier} (diff: ${closest_diff:.2f})")
                return closest_tier
            
            self.logger.warning(f"Payment amount ${usd_value:.2f} doesn't match any tier closely enough")
            return None
            
        except Exception as e:
            self.logger.error(f"Error determining tier from amount: {e}")
            return self._determine_tier_fallback(amount, crypto_type)
    
    def _determine_tier_fallback(self, amount: float, crypto_type: str) -> Optional[str]:
        """Fallback tier determination when price API is unavailable."""
        self.logger.info(f"Using fallback tier determination for {amount} {crypto_type}")
        
        if crypto_type == 'TON':
            # Rough estimates based on recent TON prices (~$5-8)
            if 1.5 <= amount <= 4.0:  # ~$7.5-32
                return 'basic'
            elif 4.0 < amount <= 10.0:  # ~$32-80
                return 'pro'
            elif amount > 10.0:  # ~$80+
                return 'enterprise'
        elif crypto_type == 'BTC':
            # BTC estimates (~$60,000-100,000)
            if 0.0002 <= amount <= 0.0008:  # ~$12-80
                return 'basic'
            elif 0.0008 < amount <= 0.0018:  # ~$80-180
                return 'pro' 
            elif amount > 0.0018:  # ~$180+
                return 'enterprise'
        elif crypto_type in ['USDT', 'USDC']:
            # USD stablecoins
            if 10 <= amount <= 25:
                return 'basic'
            elif 25 < amount <= 70:
                return 'pro'
            elif amount > 70:
                return 'enterprise'
        elif crypto_type == 'ETH':
            # ETH estimates (~$2,500-4,000)
            if 0.005 <= amount <= 0.012:  # ~$12.5-48
                return 'basic'
            elif 0.012 < amount <= 0.030:  # ~$48-120
                return 'pro'
            elif amount > 0.030:  # ~$120+
                return 'enterprise'
        
        # Default fallback
        return 'basic'
    
    async def _get_crypto_price(self, crypto_type: str) -> Optional[float]:
        """Get current cryptocurrency price in USD with optimized caching."""
        try:
            # Check cache first with longer cache duration for better performance
            current_time = datetime.now().timestamp()
            if (crypto_type in self.price_cache and 
                crypto_type in self.price_cache_time and
                current_time - self.price_cache_time[crypto_type] < self.price_cache_duration):
                self.logger.info(f"✅ Using cached {crypto_type} price: ${self.price_cache[crypto_type]}")
                return self.price_cache[crypto_type]
            
            # Fetch from CoinGecko API with shorter timeout for faster response
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={self._get_coingecko_id(crypto_type)}&vs_currencies=usd"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:  # Reduced timeout from 10 to 5 seconds
                    if response.status == 200:
                        data = await response.json()
                        coin_id = self._get_coingecko_id(crypto_type)
                        if coin_id in data and 'usd' in data[coin_id]:
                            price = data[coin_id]['usd']
                            self.price_cache[crypto_type] = price
                            self.price_cache_time[crypto_type] = current_time
                            self.logger.info(f"✅ Got {crypto_type} price: ${price}")
                            return price
                    else:
                        self.logger.warning(f"CoinGecko API returned status {response.status}")
            
            # Fallback to cached price if API fails
            if crypto_type in self.price_cache:
                self.logger.warning(f"Using fallback cached price for {crypto_type}: ${self.price_cache[crypto_type]}")
                return self.price_cache[crypto_type]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting {crypto_type} price: {e}")
            # Fallback to cached price if available
            if crypto_type in self.price_cache:
                self.logger.warning(f"Using fallback cached price for {crypto_type}: ${self.price_cache[crypto_type]}")
                return self.price_cache[crypto_type]
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
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get current payment status."""
        try:
            payment = await self.db.get_payment(payment_id)
            if not payment:
                return {'status': 'not_found', 'message': 'Payment not found'}
            
            # Check if payment has expired
            if datetime.now() > datetime.fromisoformat(payment['expires_at']):
                if payment['status'] == 'pending':
                    await self.db.update_payment_status(payment_id, 'expired')
                    payment['status'] = 'expired'
            
            return {
                'status': payment['status'],
                'amount': payment['amount'],
                'currency': payment['currency'],
                'crypto_type': payment['crypto_type'],
                'created_at': payment['created_at'],
                'expires_at': payment['expires_at']
            }
            
        except Exception as e:
            self.logger.error(f"Error getting payment status: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def get_supported_cryptocurrencies(self) -> Dict[str, Any]:
        """Get list of supported cryptocurrencies with current prices."""
        try:
            result = {}
            for crypto_type, config in self.supported_cryptos.items():
                price = await self._get_crypto_price(crypto_type)
                result[crypto_type] = {
                    'name': config['name'],
                    'symbol': config['symbol'],
                    'price_usd': price,
                    'provider': config['provider']
                }
            return result
        except Exception as e:
            self.logger.error(f"Error getting supported cryptocurrencies: {e}")
            return {}
