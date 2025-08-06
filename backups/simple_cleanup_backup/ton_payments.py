#!/usr/bin/env python3
import secrets
import qrcode
import io
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging
from decimal import Decimal

class TONPaymentProcessor:
    """Handle TON cryptocurrency payments with automatic verification."""
    
    def __init__(self, config, db, logger):
        self.config = config
        self.db = db
        self.logger = logger
        self.ton_wallet_address = config.ton_address
        self.api_base_url = "https://toncenter.com/api/v2"
        
    async def create_payment(self, user_id: int, tier: str) -> Dict:
        """Create a new TON payment request."""
        # Generate unique payment ID
        payment_id = f"TON_{secrets.token_urlsafe(12)}"
        
        # Get tier pricing
        tier_info = self.config.get_tier_info(tier)
        if not tier_info:
            raise ValueError(f"Invalid subscription tier: {tier}")
            
        amount_usd = tier_info['price']
        
        # Get TON price from API
        ton_price = await self.get_ton_price()
        if not ton_price:
            # Fallback price if API fails
            ton_price = 2.5  # Approximate TON price
        
        # Calculate TON amount (with 2 decimal precision)
        ton_amount = round(amount_usd / ton_price, 2)
        
        # Generate payment memo
        payment_memo = f"PAY-{payment_id[:8]}"
        
        # Create payment record
        payment_data = {
            'payment_id': payment_id,
            'user_id': user_id,
            'tier': tier,
            'cryptocurrency': 'ton',
            'amount_usd': amount_usd,
            'amount_crypto': ton_amount,
            'wallet_address': self.ton_wallet_address,
            'payment_memo': payment_memo,
            'status': 'pending',
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=2)
        }
        
        # Store payment in database
        await self.db.create_payment(payment_data)
        
        return payment_data
    
    async def get_ton_price(self) -> Optional[float]:
        """Get current TON price from CoinGecko API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd') as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('the-open-network', {}).get('usd')
        except Exception as e:
            self.logger.error(f"Error fetching TON price: {e}")
        return None
    
    async def generate_payment_qr(self, payment_data: Dict) -> bytes:
        """Generate QR code for TON payment."""
        address = payment_data['wallet_address']
        amount = payment_data['amount_crypto']
        memo = payment_data['payment_memo']
        
        # Create TON payment URI
        payment_uri = f"ton://transfer/{address}?amount={int(amount * 1000000000)}&text={memo}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(payment_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
    
    async def check_payment_status(self, payment_id: str) -> Dict:
        """Check payment status from database and blockchain."""
        payment = await self.db.get_payment(payment_id)
        if not payment:
            return {'status': 'not_found', 'message': 'Payment not found'}
        
        # Check if payment is expired
        if payment['expires_at'] < datetime.now():
            return {'status': 'expired', 'message': 'Payment expired'}
        
        # Check if payment is already completed
        if payment['status'] == 'completed':
            return {'status': 'completed', 'message': 'Payment confirmed'}
        
        # Check blockchain for payment
        payment_found = await self.verify_payment_on_blockchain(payment)
        
        if payment_found:
            # Update payment status
            await self.db.update_payment_status(payment_id, 'completed')
            
            # Activate subscription
            await self.db.activate_subscription(
                payment['user_id'], 
                payment['tier'], 
                duration_days=30
            )
            
            self.logger.info(f"✅ Payment {payment_id} verified and subscription activated")
            return {'status': 'completed', 'message': 'Payment confirmed'}
        
        return {'status': 'pending', 'message': 'Payment pending verification'}
    
    async def verify_payment_on_blockchain(self, payment_data: Dict) -> bool:
        """Verify payment on TON blockchain with ±5% tolerance for market fluctuations."""
        try:
            # Get recent transactions for the wallet
            transactions = await self.get_wallet_transactions(payment_data['wallet_address'])
            
            if not transactions:
                self.logger.info(f"No transactions found for wallet {payment_data['wallet_address']}")
                return False
            
            # Look for matching payment
            expected_amount = int(float(payment_data['amount_crypto']) * 1000000000)  # Convert to nanoTON
            payment_memo = payment_data['payment_memo']
            
            self.logger.info(f"Checking for payment: {expected_amount} nanoTON, memo: {payment_memo}")
            
            for tx in transactions:
                tx_amount = int(tx.get('amount', 0))
                tx_comment = tx.get('comment', '')
                
                self.logger.info(f"Transaction: {tx_amount} nanoTON, comment: {tx_comment}")
                
                # Check if transaction amount matches exactly
                if tx_amount == expected_amount:
                    # Check if memo matches
                    if payment_memo in tx_comment:
                        self.logger.info(f"Payment verified: Exact amount match for {payment_data['payment_id']}")
                        return True
                
                # Check for transactions within ±5% tolerance (for market fluctuations)
                amount_range = expected_amount * 0.05
                if abs(tx_amount - expected_amount) <= amount_range:
                    if payment_memo in tx_comment:
                        tolerance_percent = abs(tx_amount - expected_amount) / expected_amount * 100
                        self.logger.info(f"Payment verified: Within ±5% tolerance ({tolerance_percent:.2f}% difference) for {payment_data['payment_id']}")
                        return True
            
            self.logger.info(f"No matching payment found for {payment_data['payment_id']}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying payment on blockchain: {e}")
            return False
    
    async def get_wallet_transactions(self, wallet_address: str) -> List[Dict]:
        """Get recent transactions for a TON wallet."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get recent transactions from TON Center API
                url = f"{self.api_base_url}/getTransactions"
                params = {
                    'address': wallet_address,
                    'limit': 10  # Check last 10 transactions
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            transactions = data.get('result', [])
                            # Parse transactions to extract amount and comment
                            parsed_transactions = []
                            for tx in transactions:
                                if 'in_msg' in tx:
                                    in_msg = tx['in_msg']
                                    amount = in_msg.get('value', 0)
                                    comment = in_msg.get('message', '')
                                    
                                    parsed_transactions.append({
                                        'amount': amount,
                                        'comment': comment,
                                        'time': tx.get('utime', 0)
                                    })
                            return parsed_transactions
        except Exception as e:
            self.logger.error(f"Error fetching wallet transactions: {e}")
        
        return []
    
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
        """Get TON payment statistics."""
        try:
            async with self.db.pool.acquire() as conn:
                # Total payments
                total_payments = await conn.fetchval("SELECT COUNT(*) FROM payments WHERE cryptocurrency = 'ton'")
                
                # Completed payments
                completed_payments = await conn.fetchval("SELECT COUNT(*) FROM payments WHERE cryptocurrency = 'ton' AND status = 'completed'")
                
                # Total revenue
                total_revenue = await conn.fetchval("SELECT COALESCE(SUM(amount_usd), 0) FROM payments WHERE cryptocurrency = 'ton' AND status = 'completed'")
                
                return {
                    'total_payments': total_payments,
                    'completed_payments': completed_payments,
                    'total_revenue': float(total_revenue) if total_revenue else 0,
                    'cryptocurrency': 'TON'
                }
        except Exception as e:
            self.logger.error(f"Error getting payment statistics: {e}")
            return {}
    
    async def start_payment_monitoring(self):
        """Start automatic payment monitoring."""
        self.logger.info("🔍 Starting TON payment monitoring...")
        
        while True:
            try:
                # Get pending payments
                async with self.db.pool.acquire() as conn:
                    pending_payments = await conn.fetch('''
                        SELECT payment_id, user_id, tier, amount_crypto, payment_memo, created_at
                        FROM payments 
                        WHERE status = 'pending' AND cryptocurrency = 'ton' AND expires_at > CURRENT_TIMESTAMP
                    ''')
                
                for payment in pending_payments:
                    payment_data = dict(payment)
                    
                    # Check if payment was received
                    payment_found = await self.verify_payment_on_blockchain(payment_data)
                    
                    if payment_found:
                        # Update payment status
                        await self.db.update_payment_status(payment_data['payment_id'], 'completed')
                        
                        # Activate subscription
                        await self.db.activate_subscription(
                            payment_data['user_id'], 
                            payment_data['tier'], 
                            duration_days=30
                        )
                        
                        self.logger.info(f"✅ Automatic payment verification: {payment_data['payment_id']}")
                
                # Wait 30 seconds before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error in payment monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error 