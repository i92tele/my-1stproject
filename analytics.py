#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from src.database.manager import DatabaseManager

class AnalyticsEngine:
    """Analytics and performance tracking for users."""
    
    def __init__(self, db: DatabaseManager, logger):
        self.db = db
        self.logger = logger
    
    async def get_user_analytics(self, user_id: int, days: int = 30) -> Dict:
        """Get comprehensive analytics for a user."""
        try:
            # Get user's ad slots
            ad_slots = await self.db.get_or_create_ad_slots(user_id, 'basic')
            
            # Get posting statistics
            posting_stats = await self._get_posting_stats(user_id, days)
            
            # Get subscription analytics
            subscription_stats = await self._get_subscription_stats(user_id)
            
            # Calculate ROI
            roi_data = await self._calculate_roi(user_id, days)
            
            return {
                'ad_slots': len(ad_slots),
                'active_slots': len([slot for slot in ad_slots if slot.get('is_active')]),
                'total_posts': posting_stats.get('total_posts', 0),
                'successful_posts': posting_stats.get('successful_posts', 0),
                'success_rate': posting_stats.get('success_rate', 0),
                'subscription_cost': subscription_stats.get('total_cost', 0),
                'estimated_reach': posting_stats.get('estimated_reach', 0),
                'roi_percentage': roi_data.get('roi_percentage', 0),
                'days_remaining': subscription_stats.get('days_remaining', 0)
            }
        except Exception as e:
            self.logger.error(f"Error getting user analytics: {e}")
            return {}
    
    async def _get_posting_stats(self, user_id: int, days: int) -> Dict:
        """Get posting statistics for user."""
        try:
            # For now, return basic stats since we don't have comprehensive posting data yet
            return {
                'total_posts': 0,
                'successful_posts': 0,
                'success_rate': 0,
                'estimated_reach': 0
            }
        except Exception as e:
            self.logger.error(f"Error getting posting stats: {e}")
        
        return {}
    
    async def _get_subscription_stats(self, user_id: int) -> Dict:
        """Get subscription statistics for user."""
        try:
            subscription = await self.db.get_user_subscription(user_id)
            if subscription and subscription.get('expires'):
                # Handle string vs datetime
                expires_value = subscription['expires']
                if isinstance(expires_value, str):
                    try:
                        expires_dt = datetime.fromisoformat(expires_value)
                    except Exception:
                        try:
                            expires_dt = datetime.strptime(expires_value, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            expires_dt = datetime.now()
                else:
                    expires_dt = expires_value
                
                days_remaining = max(0, (expires_dt - datetime.now()).days)
                tier = subscription.get('tier', 'basic')
                
                # Get tier pricing
                tier_prices = {'basic': 15, 'pro': 45, 'enterprise': 75}
                total_cost = tier_prices.get(tier, 0)
                
                return {
                    'tier': tier,
                    'days_remaining': days_remaining,
                    'total_cost': total_cost
                }
        except Exception as e:
            self.logger.error(f"Error getting subscription stats: {e}")
        
        return {}
    
    async def _calculate_roi(self, user_id: int, days: int) -> Dict:
        """Calculate ROI for user's advertising investment."""
        try:
            # Get subscription cost
            subscription_stats = await self._get_subscription_stats(user_id)
            total_cost = subscription_stats.get('total_cost', 0)
            
            # Get posting stats
            posting_stats = await self._get_posting_stats(user_id, days)
            estimated_reach = posting_stats.get('estimated_reach', 0)
            
            # Rough ROI calculation (assume 1% conversion rate, $10 average sale)
            estimated_revenue = estimated_reach * 0.01 * 10  # 1% conversion, $10 per sale
            roi_percentage = ((estimated_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0
            
            return {
                'roi_percentage': round(roi_percentage, 2),
                'estimated_revenue': round(estimated_revenue, 2),
                'total_cost': total_cost
            }
        except Exception as e:
            self.logger.error(f"Error calculating ROI: {e}")
        
        return {}
    
    async def log_ad_post(self, user_id: int, slot_id: int, destination: str, success: bool):
        """Log an ad post for analytics."""
        try:
            # For now, just log to console since we don't have comprehensive posting data yet
            self.logger.info(f"Ad post logged: user={user_id}, slot={slot_id}, dest={destination}, success={success}")
        except Exception as e:
            self.logger.error(f"Error logging ad post: {e}")
    
    async def get_group_analytics(self, group_username: str) -> Dict:
        """Get analytics for a specific group."""
        try:
            # For now, return basic stats since we don't have comprehensive posting data yet
            return {
                'total_posts': 0,
                'successful_posts': 0,
                'success_rate': 0
            }
        except Exception as e:
            self.logger.error(f"Error getting group analytics: {e}")
        
        return {} 