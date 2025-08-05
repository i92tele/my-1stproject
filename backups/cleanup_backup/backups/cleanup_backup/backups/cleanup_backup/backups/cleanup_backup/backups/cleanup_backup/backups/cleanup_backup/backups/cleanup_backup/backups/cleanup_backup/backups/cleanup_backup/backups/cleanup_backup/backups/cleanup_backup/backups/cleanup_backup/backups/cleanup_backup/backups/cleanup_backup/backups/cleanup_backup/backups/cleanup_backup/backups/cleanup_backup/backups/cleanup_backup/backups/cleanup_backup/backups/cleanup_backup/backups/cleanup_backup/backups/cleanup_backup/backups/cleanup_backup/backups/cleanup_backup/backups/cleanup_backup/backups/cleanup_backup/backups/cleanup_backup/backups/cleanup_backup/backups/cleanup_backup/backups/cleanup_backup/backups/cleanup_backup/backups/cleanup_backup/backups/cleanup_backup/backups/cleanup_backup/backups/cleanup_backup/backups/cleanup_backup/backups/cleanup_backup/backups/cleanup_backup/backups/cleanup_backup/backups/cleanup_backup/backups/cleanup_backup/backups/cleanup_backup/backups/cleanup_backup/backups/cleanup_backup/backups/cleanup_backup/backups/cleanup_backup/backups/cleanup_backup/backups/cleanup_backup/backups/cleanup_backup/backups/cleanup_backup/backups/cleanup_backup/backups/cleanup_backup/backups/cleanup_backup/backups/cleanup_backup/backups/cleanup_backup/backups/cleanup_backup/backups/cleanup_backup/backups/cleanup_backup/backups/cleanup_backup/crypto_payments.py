import secrets
import qrcode
import io
from datetime import datetime, timedelta
from typing import Dict, Optional
import aiohttp
import logging

class CryptoPaymentProcessor:
    """Handle direct cryptocurrency payments."""
    
    def __init__(self, config, db, logger):
        self.config = config
        self.db = db
        self.logger = logger
        
        # Cryptocurrency info
        self.crypto_info = {
            'bitcoin': {'symbol': 'BTC', 'decimals': 8},
            'ethereum': {'symbol': 'ETH', 'decimals': 18},
            'solana': {'symbol': 'SOL', 'decimals': 9},
            'litecoin': {'symbol': 'LTC', 'decimals': 8}
        }
        
    async def create_payment(self, user_id: int, tier: str, crypto: str) -> Dict:
        """Create a new payment request."""
        # Get wallet address
        wallet_addresses = {
            'bitcoin': self.config.btc_address,
            'ethereum': self.config.eth_address,
            'solana': self.config.sol_address,
            'litecoin': self.config.ltc_address
        }
        
        if crypto not in wallet_addresses:
            raise ValueError(f"Unsupported cryptocurrency: {crypto}")
            
        # Generate unique payment ID
        payment_id = secrets.token_urlsafe(16)
        
        # Get tier pricing
        tier_info = self.config.get_tier_info(tier)
        if not tier_info:
            raise ValueError(f"Invalid subscription tier: {tier}")
            
        amount_usd = tier_info['price']
        
        # Get crypto price (simplified - using fixed rates for now)
        crypto_prices = {
            'bitcoin': 45000,
            'ethereum': 2500,
            'solana': 100,
            'litecoin': 70
        }
        
        crypto_price = crypto_prices.get(crypto, 1)
        crypto_amount = round(amount_usd / crypto_price, self.crypto_info[crypto]['decimals'])
        
        # Generate payment memo
        payment_memo = f"PAY-{payment_id[:8]}"
        
        # Create payment record
        payment_data = {
            'payment_id': payment_id,
            'user_id': user_id,
            'tier': tier,
            'cryptocurrency': crypto,
            'amount_usd': amount_usd,
            'amount_crypto': crypto_amount,
            'wallet_address': wallet_addresses[crypto],
            'payment_memo': payment_memo,
            'status': 'pending',
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=2)
        }
        
        # Store payment in database
        await self.db.create_payment(payment_data)
        
        return payment_data
    
    async def generate_payment_qr(self, payment_data: Dict) -> bytes:
        """Generate QR code for payment."""
        crypto = payment_data['cryptocurrency']
        address = payment_data['wallet_address']
        amount = payment_data['amount_crypto']
        
        # Create payment URI
        payment_uri = f"{address}?amount={amount}&message={payment_data['payment_memo']}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(payment_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        return bio.read()
    
    async def check_payment_status(self, payment_id: str) -> Dict:
        """Check payment status from database."""
        payment = await self.db.get_payment(payment_id)
        if not payment:
            return {'status': 'not_found', 'message': 'Payment not found'}
        
        # Check if payment is expired
        if payment['expires_at'] < datetime.now():
            return {'status': 'expired', 'message': 'Payment expired'}
        
        # Check if payment is completed
        if payment['status'] == 'completed':
            return {'status': 'completed', 'message': 'Payment confirmed'}
        
        # For now, return pending status
        # In production, you would integrate with blockchain APIs to verify transactions
        return {'status': 'pending', 'message': 'Payment pending verification'}

    async def verify_payment_manually(self, payment_id: str, tx_hash: str) -> bool:
        """Manually verify payment with transaction hash."""
        try:
            # Update payment status
            success = await self.db.update_payment_status(payment_id, 'completed', tx_hash)
            if success:
                # Get payment details
                payment = await self.db.get_payment(payment_id)
                if payment:
                    # Activate user subscription
                    await self.db.activate_subscription(
                        payment['user_id'], 
                        payment['tier'], 
                        duration_days=30
                    )
                    self.logger.info(f"Subscription activated for user {payment['user_id']}")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error verifying payment: {e}")
            return False

    async def process_expired_payments(self):
        """Process and clean up expired payments."""
        try:
            # Get expired payments
            async with self.db.pool.acquire() as conn:
                expired_payments = await conn.fetch('''
                    SELECT payment_id FROM payments 
                    WHERE status = 'pending' AND expires_at < CURRENT_TIMESTAMP
                ''')
                
                for payment in expired_payments:
                    await self.db.update_payment_status(payment['payment_id'], 'expired')
                    self.logger.info(f"Payment {payment['payment_id']} marked as expired")
                    
        except Exception as e:
            self.logger.error(f"Error processing expired payments: {e}")

    async def get_payment_statistics(self) -> Dict:
        """Get payment statistics."""
        try:
            async with self.db.pool.acquire() as conn:
                # Total payments
                total_payments = await conn.fetchval("SELECT COUNT(*) FROM payments")
                
                # Completed payments
                completed_payments = await conn.fetchval("SELECT COUNT(*) FROM payments WHERE status = 'completed'")
                
                # Total revenue
                total_revenue = await conn.fetchval("SELECT COALESCE(SUM(amount_usd), 0) FROM payments WHERE status = 'completed'")
                
                # Revenue by cryptocurrency
                revenue_by_crypto = await conn.fetch('''
                    SELECT cryptocurrency, SUM(amount_usd) as total_usd, COUNT(*) as count
                    FROM payments 
                    WHERE status = 'completed' 
                    GROUP BY cryptocurrency
                ''')
                
                return {
                    'total_payments': total_payments,
                    'completed_payments': completed_payments,
                    'total_revenue': float(total_revenue) if total_revenue else 0,
                    'revenue_by_crypto': [dict(row) for row in revenue_by_crypto]
                }
        except Exception as e:
            self.logger.error(f"Error getting payment statistics: {e}")
            return {}