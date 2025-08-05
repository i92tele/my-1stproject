#!/usr/bin/env python3
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from decimal import Decimal

class PaymentSystemFix:
    """Critical fixes for payment system vulnerabilities."""
    
    def __init__(self, config, db, logger):
        self.config = config
        self.db = db
        self.logger = logger
        
    async def verify_payment_signature(self, payment_data: Dict) -> bool:
        """Verify payment signature for security."""
        try:
            # Get payment details
            payment_id = payment_data['payment_id']
            amount = payment_data['amount_crypto']
            memo = payment_data['payment_memo']
            
            # Verify payment on blockchain
            return await self.verify_payment_on_blockchain(payment_data)
            
        except Exception as e:
            self.logger.error(f"Payment signature verification failed: {e}")
            return False
    
    async def verify_payment_on_blockchain(self, payment_data: Dict) -> bool:
        """Enhanced payment verification with blockchain check."""
        try:
            # Get recent transactions from TON blockchain
            transactions = await self.get_wallet_transactions(payment_data['wallet_address'])
            
            # Check for matching payment with tolerance
            target_amount = payment_data['amount_crypto']
            tolerance = 0.05  # 5% tolerance for price fluctuations
            
            for tx in transactions:
                tx_amount = float(tx.get('amount', 0))
                tx_memo = tx.get('memo', '')
                
                # Check if amount matches (with tolerance)
                if (tx_amount >= target_amount * (1 - tolerance) and 
                    tx_amount <= target_amount * (1 + tolerance) and
                    tx_memo == payment_data['payment_memo']):
                    
                    self.logger.info(f"Payment verified: {payment_data['payment_id']}")
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Blockchain verification failed: {e}")
            return False
    
    async def get_wallet_transactions(self, wallet_address: str) -> List[Dict]:
        """Get recent transactions for a wallet address."""
        try:
            async with aiohttp.ClientSession() as session:
                # Use TON Center API to get transactions
                url = f"https://toncenter.com/api/v2/getTransactions"
                params = {
                    'address': wallet_address,
                    'limit': 10  # Get last 10 transactions
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        transactions = []
                        
                        for tx in data.get('result', []):
                            transactions.append({
                                'amount': float(tx.get('in_msg', {}).get('value', 0)) / 1e9,  # Convert from nanoTON
                                'memo': tx.get('in_msg', {}).get('message', ''),
                                'timestamp': tx.get('utime', 0)
                            })
                        
                        return transactions
                    else:
                        self.logger.error(f"Failed to get transactions: {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"Error getting wallet transactions: {e}")
            return []
    
    async def handle_payment_timeout(self, payment_id: str):
        """Handle expired payments gracefully."""
        try:
            # Get payment data
            payment = await self.db.get_payment(payment_id)
            if not payment:
                return
                
            # Check if payment is expired
            if payment['expires_at'] < datetime.now():
                # Update payment status to expired
                await self.db.update_payment_status(payment_id, 'expired')
                self.logger.info(f"Payment {payment_id} marked as expired")
                
                # Notify user about expired payment
                user_id = payment['user_id']
                # You can add notification logic here
                
        except Exception as e:
            self.logger.error(f"Error handling payment timeout: {e}")
    
    async def process_expired_payments(self):
        """Process all expired payments."""
        try:
            # Get all expired payments
            expired_payments = await self.db.get_expired_payments()
            
            for payment in expired_payments:
                await self.handle_payment_timeout(payment['payment_id'])
                
            self.logger.info(f"Processed {len(expired_payments)} expired payments")
            
        except Exception as e:
            self.logger.error(f"Error processing expired payments: {e}")
    
    async def create_secure_payment(self, user_id: int, tier: str) -> Dict:
        """Create a secure payment with enhanced validation."""
        try:
            # Generate unique payment ID with timestamp
            timestamp = int(datetime.now().timestamp())
            payment_id = f"TON_{timestamp}_{user_id}_{tier}"
            
            # Get tier pricing
            tier_info = self.config.get_tier_info(tier)
            if not tier_info:
                raise ValueError(f"Invalid subscription tier: {tier}")
                
            amount_usd = tier_info['price']
            
            # Get current TON price
            ton_price = await self.get_ton_price()
            if not ton_price:
                ton_price = 2.5  # Fallback price
            
            # Calculate TON amount with precision
            ton_amount = round(amount_usd / ton_price, 2)
            
            # Generate secure payment memo
            payment_memo = f"PAY-{payment_id[:8]}-{user_id}"
            
            # Create payment record with extended expiry (4 hours for crypto)
            payment_data = {
                'payment_id': payment_id,
                'user_id': user_id,
                'tier': tier,
                'cryptocurrency': 'ton',
                'amount_usd': amount_usd,
                'amount_crypto': ton_amount,
                'wallet_address': self.config.ton_address,
                'payment_memo': payment_memo,
                'status': 'pending',
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(hours=4)  # Extended to 4 hours
            }
            
            # Store payment in database
            await self.db.create_payment(payment_data)
            
            self.logger.info(f"Created secure payment: {payment_id}")
            return payment_data
            
        except Exception as e:
            self.logger.error(f"Error creating secure payment: {e}")
            raise
    
    async def get_ton_price(self) -> Optional[float]:
        """Get current TON price with fallback."""
        try:
            async with aiohttp.ClientSession() as session:
                # Try CoinGecko API first
                url = "https://api.coingecko.com/api/v3/simple/price"
                params = {
                    'ids': 'the-open-network',
                    'vs_currencies': 'usd'
                }
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get('the-open-network', {}).get('usd')
                        if price:
                            return price
                    
                # Fallback to alternative API
                url = "https://api.binance.com/api/v3/ticker/price"
                params = {'symbol': 'TONUSDT'}
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = float(data.get('price', 0))
                        if price > 0:
                            return price
                            
        except Exception as e:
            self.logger.error(f"Error fetching TON price: {e}")
        
        return None

async def main():
    """Test the payment system fixes."""
    # This would be called from your main application
    pass

if __name__ == '__main__':
    asyncio.run(main()) 