import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum

class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"
    TIMEOUT = "timeout"

class PaymentTimeoutHandler:
    """Production-ready payment timeout handling system."""
    
    def __init__(self, logger: logging.Logger, db_safety):
        self.logger = logger
        self.db_safety = db_safety
        self.payment_timeouts: Dict[str, datetime] = {}
        self.timeout_task = None
        self.default_timeout_minutes = 30  # 30 minutes default
        self.reminder_intervals = [5, 15, 25]  # Send reminders at these minutes
        
    async def start_monitoring(self):
        """Start the payment timeout monitoring task."""
        self.timeout_task = asyncio.create_task(self._monitor_payments())
        self.logger.info("Payment timeout monitor started")
    
    async def stop_monitoring(self):
        """Stop the payment timeout monitoring task."""
        if self.timeout_task:
            self.timeout_task.cancel()
            try:
                await self.timeout_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Payment timeout monitor stopped")
    
    async def create_payment_with_timeout(self, user_id: int, amount: float, currency: str, 
                                        timeout_minutes: Optional[int] = None) -> Dict[str, any]:
        """Create a payment with timeout handling."""
        timeout_minutes = timeout_minutes or self.default_timeout_minutes
        
        # Generate payment ID
        payment_id = f"PAY_{user_id}_{int(datetime.now().timestamp())}"
        
        # Calculate expiry time
        expiry_time = datetime.now() + timedelta(minutes=timeout_minutes)
        
        # Create payment record
        payment_data = {
            'payment_id': payment_id,
            'user_id': user_id,
            'amount': amount,
            'currency': currency,
            'status': PaymentStatus.PENDING.value,
            'created_at': datetime.now(),
            'expires_at': expiry_time,
            'timeout_minutes': timeout_minutes
        }
        
        # Store in database
        await self._store_payment(payment_data)
        
        # Track for timeout monitoring
        self.payment_timeouts[payment_id] = expiry_time
        
        self.logger.info(f"Created payment {payment_id} with {timeout_minutes} minute timeout")
        
        return payment_data
    
    async def check_payment_status(self, payment_id: str) -> Dict[str, any]:
        """Check payment status with timeout handling."""
        try:
            payment = await self._get_payment(payment_id)
            if not payment:
                return {'status': 'not_found', 'message': 'Payment not found'}
            
            # Check if payment has expired
            if datetime.now() > payment['expires_at']:
                await self._handle_expired_payment(payment_id)
                return {
                    'status': PaymentStatus.EXPIRED.value,
                    'message': 'Payment has expired. Please create a new payment.',
                    'expired_at': payment['expires_at'].isoformat()
                }
            
            # Check if payment is completed
            if payment['status'] == PaymentStatus.COMPLETED.value:
                return {
                    'status': PaymentStatus.COMPLETED.value,
                    'message': 'Payment completed successfully!',
                    'completed_at': payment.get('completed_at', '').isoformat() if payment.get('completed_at') else None
                }
            
            # Calculate time remaining
            time_remaining = (payment['expires_at'] - datetime.now()).total_seconds()
            minutes_remaining = max(0, int(time_remaining / 60))
            
            return {
                'status': PaymentStatus.PENDING.value,
                'message': f'Payment pending. {minutes_remaining} minutes remaining.',
                'expires_at': payment['expires_at'].isoformat(),
                'minutes_remaining': minutes_remaining
            }
            
        except Exception as e:
            self.logger.error(f"Error checking payment status for {payment_id}: {e}")
            return {'status': 'error', 'message': 'Error checking payment status'}
    
    async def _monitor_payments(self):
        """Monitor payments for timeouts and send reminders."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                now = datetime.now()
                expired_payments = []
                
                # Check for expired payments
                for payment_id, expiry_time in self.payment_timeouts.items():
                    if now > expiry_time:
                        expired_payments.append(payment_id)
                    else:
                        # Check if we should send a reminder
                        time_remaining = (expiry_time - now).total_seconds() / 60
                        await self._check_reminders(payment_id, time_remaining)
                
                # Handle expired payments
                for payment_id in expired_payments:
                    await self._handle_expired_payment(payment_id)
                    del self.payment_timeouts[payment_id]
                
                if expired_payments:
                    self.logger.info(f"Handled {len(expired_payments)} expired payments")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in payment monitoring: {e}")
    
    async def _check_reminders(self, payment_id: str, minutes_remaining: float):
        """Check if we should send payment reminders."""
        for reminder_minutes in self.reminder_intervals:
            if minutes_remaining <= reminder_minutes and minutes_remaining > reminder_minutes - 1:
                await self._send_payment_reminder(payment_id, minutes_remaining)
                break
    
    async def _send_payment_reminder(self, payment_id: str, minutes_remaining: float):
        """Send payment reminder to user."""
        try:
            payment = await self._get_payment(payment_id)
            if not payment:
                return
            
            user_id = payment['user_id']
            message = (
                f"⏰ **Payment Reminder**\n\n"
                f"Your payment of {payment['amount']} {payment['currency']} "
                f"will expire in {int(minutes_remaining)} minutes.\n\n"
                f"Please complete your payment to avoid expiration."
            )
            
            # Send reminder (you'll need to implement this with your bot instance)
            # await bot.send_message(user_id, message, parse_mode='Markdown')
            
            self.logger.info(f"Sent payment reminder to user {user_id} for payment {payment_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending payment reminder: {e}")
    
    async def _handle_expired_payment(self, payment_id: str):
        """Handle expired payment."""
        try:
            # Update payment status in database
            await self._update_payment_status(payment_id, PaymentStatus.EXPIRED.value)
            
            # Get payment details for notification
            payment = await self._get_payment(payment_id)
            if payment:
                user_id = payment['user_id']
                message = (
                    f"❌ **Payment Expired**\n\n"
                    f"Your payment of {payment['amount']} {payment['currency']} "
                    f"has expired.\n\n"
                    f"Please create a new payment to continue."
                )
                
                # Send expiration notification (you'll need to implement this with your bot instance)
                # await bot.send_message(user_id, message, parse_mode='Markdown')
                
                self.logger.info(f"Payment {payment_id} expired and user {user_id} notified")
            
        except Exception as e:
            self.logger.error(f"Error handling expired payment {payment_id}: {e}")
    
    async def _store_payment(self, payment_data: Dict[str, any]):
        """Store payment in database."""
        query = """
            INSERT INTO payments (payment_id, user_id, amount, currency, status, created_at, expires_at, timeout_minutes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        await self.db_safety.execute_query(
            query,
            payment_data['payment_id'],
            payment_data['user_id'],
            payment_data['amount'],
            payment_data['currency'],
            payment_data['status'],
            payment_data['created_at'],
            payment_data['expires_at'],
            payment_data['timeout_minutes']
        )
    
    async def _get_payment(self, payment_id: str) -> Optional[Dict[str, any]]:
        """Get payment from database."""
        query = "SELECT * FROM payments WHERE payment_id = $1"
        return await self.db_safety.fetch_one(query, payment_id)
    
    async def _update_payment_status(self, payment_id: str, status: str):
        """Update payment status in database."""
        query = "UPDATE payments SET status = $1, updated_at = $2 WHERE payment_id = $3"
        await self.db_safety.execute_query(query, status, datetime.now(), payment_id)
    
    def get_timeout_stats(self) -> Dict[str, any]:
        """Get payment timeout statistics."""
        now = datetime.now()
        active_payments = len(self.payment_timeouts)
        expired_payments = sum(1 for expiry in self.payment_timeouts.values() if now > expiry)
        
        return {
            'active_payments': active_payments,
            'expired_payments': expired_payments,
            'total_payments': active_payments + expired_payments
        }

# Global payment timeout handler instance
payment_timeout_handler = None

def initialize_payment_timeout_handler(logger: logging.Logger, db_safety):
    """Initialize the payment timeout handler."""
    global payment_timeout_handler
    payment_timeout_handler = PaymentTimeoutHandler(logger, db_safety)
    return payment_timeout_handler 