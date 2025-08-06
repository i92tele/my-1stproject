import asyncio
import aiohttp
import logging
from datetime import datetime

class BlockchainPaymentProcessor:
    """Handle direct blockchain payments."""

    def __init__(self, db, notifier, config, logger: logging.Logger):
        self.db = db
        self.notifier = notifier
        self.config = config
        self.logger = logger
        self.session = None  # Initialize as None
        self.monitoring_task = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Creates a session if it doesn't exist or is closed."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _get_btc_price(self) -> float:
        """Get current BTC price in USD from a public API."""
        session = await self._get_session()
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return float(data['bitcoin']['usd'])
        except Exception as e:
            self.logger.error(f"Could not fetch BTC price: {e}")
            return 0.0

    def _generate_new_btc_address(self, charge_id: str) -> str:
        """Generates a new, unique Bitcoin address for a payment."""
        self.logger.warning("Using a placeholder for BTC address generation. NOT FOR PRODUCTION.")
        return f"dummy_btc_address_{charge_id}"

    async def create_charge(self, user_id: int, tier: str) -> dict:
        """Create a new payment charge for a user."""
        tier_info = self.config.subscription_tiers.get(tier)
        if not tier_info:
            return {"error": "Invalid subscription tier."}

        price_usd = tier_info['price']
        btc_price = await self._get_btc_price()
        if btc_price == 0.0:
            return {"error": "Could not retrieve crypto price. Please try again later."}

        amount_btc = round(price_usd / btc_price, 8)
        charge_id = f"charge_{user_id}_{int(datetime.now().timestamp())}"
        payment_address = self._generate_new_btc_address(charge_id)

        await self.db.record_payment(
            user_id=user_id, charge_id=charge_id, tier=tier, usd_amount=price_usd,
            crypto_currency='BTC', crypto_amount=amount_btc, payment_address=payment_address
        )
        return {"address": payment_address, "amount": amount_btc, "currency": "BTC", "usd_value": price_usd}

    async def _monitor_pending_payments(self):
        """Periodically check for payments to pending addresses."""
        session = await self._get_session()
        while True:
            try:
                pending_payments = await self.db.get_pending_payments(age_limit_minutes=60)
                for payment in pending_payments:
                    address = payment['payment_address']
                    expected_amount = payment['crypto_amount']
                    url = f"https://blockstream.info/api/address/{address}/utxo"
                    balance = 0
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                utxos = await response.json()
                                for utxo in utxos:
                                    balance += utxo['value']
                    except Exception as api_error:
                        self.logger.error(f"Failed to check balance for {address}: {api_error}")
                        continue

                    balance_btc = balance / 100_000_000
                    if balance_btc >= expected_amount:
                        self.logger.info(f"Payment detected for {address}!")
                        await self.db.update_payment_status(payment['charge_id'], 'completed')
                        tier_info = self.config.subscription_tiers[payment['tier']]
                        await self.db.update_subscription(user_id=payment['user_id'], tier=payment['tier'], duration_days=tier_info['duration_days'])
                        await self.notifier.notify_payment_success(payment['user_id'], payment['tier'])
            except asyncio.CancelledError:
                self.logger.info("Payment monitoring cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in payment monitoring loop: {e}")
            
            # Sleep for 2 minutes before next check
            try:
                await asyncio.sleep(120)
            except asyncio.CancelledError:
                break

    async def _monitor_expiring_subscriptions(self):
        """Periodically check for subscriptions that are about to expire."""
        while True:
            try:
                for days in [3, 1]:
                    expiring_soon = await self.db.get_expiring_subscriptions(days_from_now=days)
                    for sub in expiring_soon:
                        self.logger.info(f"Notifying user {sub['user_id']} about subscription expiring in {days} days.")
                        await self.notifier.notify_subscription_expiring(sub['user_id'], days)
            except asyncio.CancelledError:
                self.logger.info("Subscription monitoring cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in subscription expiry monitoring loop: {e}")
            
            # Sleep for 24 hours before next check
            try:
                await asyncio.sleep(86400)
            except asyncio.CancelledError:
                break

    async def start_monitoring(self):
        """Start all background monitoring tasks."""
        try:
            if not self.monitoring_task or self.monitoring_task.done():
                self.monitoring_task = asyncio.gather(
                    self._monitor_pending_payments(),
                    self._monitor_expiring_subscriptions(),
                    return_exceptions=True
                )
                self.logger.info("All background monitors started.")
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")

    async def stop_monitoring(self):
        """Stop the background monitoring task."""
        try:
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            if self.session and not self.session.closed:
                await self.session.close()
            self.logger.info("All background monitors stopped.")
        except Exception as e:
            self.logger.error(f"Error stopping monitoring: {e}")
