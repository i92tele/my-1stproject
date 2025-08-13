#!/usr/bin/env python3
"""
Notification Scheduler System
Handles automated user notifications for subscription expiry and other updates
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

class NotificationScheduler:
    """Handle automated user notifications."""
    
    def __init__(self, bot, db, logger):
        self.bot = bot
        self.db = db
        self.logger = logger
        self.is_running = False
        self.notification_task = None
        
    async def start(self):
        """Start the notification scheduler."""
        if self.is_running:
            self.logger.warning("Notification scheduler already running")
            return
            
        self.is_running = True
        self.notification_task = asyncio.create_task(self._notification_loop())
        self.logger.info("✅ Notification scheduler started")
        
    async def stop(self):
        """Stop the notification scheduler."""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.notification_task:
            self.notification_task.cancel()
            try:
                await self.notification_task
            except asyncio.CancelledError:
                pass
        self.logger.info("🛑 Notification scheduler stopped")
        
    async def _notification_loop(self):
        """Main notification loop."""
        while self.is_running:
            try:
                # Check for expiring subscriptions
                await self._check_expiring_subscriptions()
                
                # Check for expired subscriptions
                await self._check_expired_subscriptions()
                
                # Check for other notifications
                await self._check_other_notifications()
                
                # Wait 1 hour before next check
                await asyncio.sleep(3600)  # 1 hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in notification loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
    async def _check_expiring_subscriptions(self):
        """Check for subscriptions expiring soon and send notifications."""
        try:
            now = datetime.now()
            
            # Check for subscriptions expiring in 7 days
            seven_days_from_now = now + timedelta(days=7)
            expiring_7_days = await self._get_expiring_subscriptions(seven_days_from_now)
            
            for user in expiring_7_days:
                await self._send_expiry_notification(user['user_id'], 7)
                
            # Check for subscriptions expiring in 3 days
            three_days_from_now = now + timedelta(days=3)
            expiring_3_days = await self._get_expiring_subscriptions(three_days_from_now)
            
            for user in expiring_3_days:
                await self._send_expiry_notification(user['user_id'], 3)
                
            # Check for subscriptions expiring in 1 day
            one_day_from_now = now + timedelta(days=1)
            expiring_1_day = await self._get_expiring_subscriptions(one_day_from_now)
            
            for user in expiring_1_day:
                await self._send_expiry_notification(user['user_id'], 1)
                
            # Check for subscriptions expiring today
            today = now.date()
            expiring_today = await self._get_expiring_subscriptions_today(today)
            
            for user in expiring_today:
                await self._send_expiry_notification(user['user_id'], 0)
                
        except Exception as e:
            self.logger.error(f"Error checking expiring subscriptions: {e}")
            
    async def _check_expired_subscriptions(self):
        """Check for expired subscriptions and send daily notifications."""
        try:
            expired_users = await self._get_expired_subscriptions()
            
            for user in expired_users:
                await self._send_expired_notification(user['user_id'])
                
        except Exception as e:
            self.logger.error(f"Error checking expired subscriptions: {e}")
            
    async def _check_other_notifications(self):
        """Check for other types of notifications."""
        try:
            # Check for system maintenance notifications
            await self._check_maintenance_notifications()
            
            # Check for feature updates
            await self._check_feature_updates()
            
        except Exception as e:
            self.logger.error(f"Error checking other notifications: {e}")
            
    async def _get_expiring_subscriptions(self, target_date: datetime) -> List[Dict[str, Any]]:
        """Get users with subscriptions expiring on a specific date."""
        try:
            # Get users whose subscription expires on the target date
            # and haven't been notified recently
            query = '''
                SELECT DISTINCT u.user_id, u.username, u.first_name, u.subscription_tier, u.subscription_expires
                FROM users u
                WHERE u.subscription_expires BETWEEN ? AND ?
                AND u.subscription_tier IS NOT NULL
                AND u.subscription_expires > ?
                AND (u.last_notification_date IS NULL OR 
                     u.last_notification_date < ?)
            '''
            
            start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            now = datetime.now()
            notification_threshold = now - timedelta(hours=12)  # Don't notify more than once per 12 hours
            
            async with self.db._lock:
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute(query, (start_date, end_date, now, notification_threshold))
                users = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
                conn.close()
                
            return users
            
        except Exception as e:
            self.logger.error(f"Error getting expiring subscriptions: {e}")
            return []
            
    async def _get_expiring_subscriptions_today(self, target_date: datetime.date) -> List[Dict[str, Any]]:
        """Get users with subscriptions expiring today."""
        try:
            query = '''
                SELECT DISTINCT u.user_id, u.username, u.first_name, u.subscription_tier, u.subscription_expires
                FROM users u
                WHERE DATE(u.subscription_expires) = ?
                AND u.subscription_tier IS NOT NULL
                AND u.subscription_expires > ?
                AND (u.last_notification_date IS NULL OR 
                     u.last_notification_date < ?)
            '''
            
            now = datetime.now()
            notification_threshold = now - timedelta(hours=6)  # Don't notify more than once per 6 hours for same-day
            
            async with self.db._lock:
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute(query, (target_date, now, notification_threshold))
                users = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
                conn.close()
                
            return users
            
        except Exception as e:
            self.logger.error(f"Error getting today's expiring subscriptions: {e}")
            return []
            
    async def _get_expired_subscriptions(self) -> List[Dict[str, Any]]:
        """Get users with expired subscriptions."""
        try:
            query = '''
                SELECT DISTINCT u.user_id, u.username, u.first_name, u.subscription_tier, u.subscription_expires
                FROM users u
                WHERE u.subscription_expires < ?
                AND u.subscription_tier IS NOT NULL
                AND (u.last_notification_date IS NULL OR 
                     u.last_notification_date < ?)
            '''
            
            now = datetime.now()
            notification_threshold = now - timedelta(days=1)  # Don't notify more than once per day for expired
            
            async with self.db._lock:
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute(query, (now, notification_threshold))
                users = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
                conn.close()
                
            return users
            
        except Exception as e:
            self.logger.error(f"Error getting expired subscriptions: {e}")
            return []
            
    async def _send_expiry_notification(self, user_id: int, days_left: int):
        """Send subscription expiry notification to user."""
        try:
            if days_left == 0:
                message = (
                    "⚠️ **Your subscription expires TODAY!**\n\n"
                    "Your subscription will expire at the end of today.\n\n"
                    "**To continue using the bot:**\n"
                    "• Use /prolong_subscription to extend your current plan\n"
                    "• Use /upgrade_subscription to upgrade to a higher tier\n"
                    "• Use /subscribe to see all available plans\n\n"
                    "Don't lose access to your ad slots!"
                )
            else:
                day_text = "day" if days_left == 1 else "days"
                message = (
                    f"⚠️ **Your subscription expires in {days_left} {day_text}**\n\n"
                    f"Your subscription will expire on {self._format_date(datetime.now() + timedelta(days=days_left))}.\n\n"
                    "**To continue using the bot:**\n"
                    "• Use /prolong_subscription to extend your current plan\n"
                    "• Use /upgrade_subscription to upgrade to a higher tier\n"
                    "• Use /subscribe to see all available plans\n\n"
                    "Don't wait until the last minute!"
                )
            
            # Send the notification
            await self._send_message(user_id, message)
            
            # Update notification timestamp
            await self._update_notification_timestamp(user_id)
            
            self.logger.info(f"Sent expiry notification to user {user_id} ({days_left} days left)")
            
        except Exception as e:
            self.logger.error(f"Error sending expiry notification to user {user_id}: {e}")
            
    async def _send_expired_notification(self, user_id: int):
        """Send expired subscription notification to user."""
        try:
            message = (
                "❌ **Your subscription has expired**\n\n"
                "Your subscription has expired and your ad slots are now inactive.\n\n"
                "**To reactivate your service:**\n"
                "• Use /subscribe to choose a new plan\n"
                "• Use /prolong_subscription if you want to extend your previous plan\n"
                "• Use /upgrade_subscription if you want to upgrade\n\n"
                "Your ad slot content is preserved and will be restored when you resubscribe!"
            )
            
            # Send the notification
            await self._send_message(user_id, message)
            
            # Update notification timestamp
            await self._update_notification_timestamp(user_id)
            
            self.logger.info(f"Sent expired notification to user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending expired notification to user {user_id}: {e}")
            
    async def _send_message(self, user_id: int, message: str):
        """Send a message to a user safely."""
        try:
            if not self.bot:
                self.logger.warning("Bot instance not available for notifications")
                return
                
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send notification to user {user_id}: {e}")
            
    async def _update_notification_timestamp(self, user_id: int):
        """Update the last notification timestamp for a user."""
        try:
            async with self.db._lock:
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET last_notification_date = ? 
                    WHERE user_id = ?
                ''', (datetime.now(), user_id))
                conn.commit()
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Error updating notification timestamp for user {user_id}: {e}")
            
    async def _check_maintenance_notifications(self):
        """Check for system maintenance notifications."""
        # This can be implemented later for system maintenance announcements
        pass
        
    async def _check_feature_updates(self):
        """Check for feature update notifications."""
        # This can be implemented later for feature announcements
        pass
        
    def _format_date(self, date: datetime) -> str:
        """Format date for display."""
        return date.strftime("%B %d, %Y")
        
    async def send_broadcast_message(self, message: str, user_ids: Optional[List[int]] = None):
        """Send a broadcast message to all users or specific users."""
        try:
            if user_ids is None:
                # Get all users
                user_ids = await self._get_all_user_ids()
                
            success_count = 0
            failed_count = 0
            
            for user_id in user_ids:
                try:
                    await self._send_message(user_id, message)
                    success_count += 1
                    await asyncio.sleep(0.1)  # Small delay to avoid rate limiting
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"Failed to send broadcast to user {user_id}: {e}")
                    
            self.logger.info(f"Broadcast completed: {success_count} successful, {failed_count} failed")
            return {'success_count': success_count, 'failed_count': failed_count}
            
        except Exception as e:
            self.logger.error(f"Error in broadcast message: {e}")
            return {'success_count': 0, 'failed_count': len(user_ids) if user_ids else 0}
            
    async def _get_all_user_ids(self) -> List[int]:
        """Get all user IDs from the database."""
        try:
            async with self.db._lock:
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users WHERE user_id IS NOT NULL')
                user_ids = [row[0] for row in cursor.fetchall()]
                conn.close()
                return user_ids
                
        except Exception as e:
            self.logger.error(f"Error getting all user IDs: {e}")
            return []
