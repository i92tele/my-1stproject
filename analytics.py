#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from database import DatabaseManager

class AnalyticsEngine:
    """Analytics and performance tracking for users."""
    
    def __init__(self, db: DatabaseManager, logger):
        self.db = db
        self.logger = logger
    
    async def get_user_analytics(self, user_id: int, days: int = 30) -> Dict:
        """Get comprehensive analytics for a user."""
        try:
            # Get user's ad slots
            ad_slots = await self.db.get_user_ad_slots(user_id)
            
            # Get posting statistics
            posting_stats = await self._get_posting_stats(user_id, days)
            
            # Get subscription analytics
            subscription_stats = await self._get_subscription_stats(user_id)
            
            # Calculate ROI
            roi_data = await self._calculate_roi(user_id, days)
            
            return {
                'ad_slots': len(ad_slots),
                'active_slots': len([slot for slot in ad_slots if slot['is_active']]),
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
            async with self.db.pool.acquire() as conn:
                # Get posts in last N days
                result = await conn.fetchrow('''
                    SELECT 
                        COUNT(*) as total_posts,
                        COUNT(CASE WHEN success = true THEN 1 END) as successful_posts
                    FROM ad_posts 
                    WHERE user_id = $1 AND created_at >= $2
                ''', user_id, datetime.now() - timedelta(days=days))
                
                if result:
                    total_posts = result['total_posts']
                    successful_posts = result['successful_posts']
                    success_rate = (successful_posts / total_posts * 100) if total_posts > 0 else 0
                    
                    # Estimate reach (rough calculation)
                    estimated_reach = successful_posts * 100  # Assume 100 views per post
                    
                    return {
                        'total_posts': total_posts,
                        'successful_posts': successful_posts,
                        'success_rate': round(success_rate, 2),
                        'estimated_reach': estimated_reach
                    }
        except Exception as e:
            self.logger.error(f"Error getting posting stats: {e}")
        
        return {}
    
    async def _get_subscription_stats(self, user_id: int) -> Dict:
        """Get subscription statistics for user."""
        try:
            user = await self.db.get_user(user_id)
            if user and user.get('subscription_expires'):
                days_remaining = (user['subscription_expires'] - datetime.now()).days
                tier = user.get('subscription_tier', 'basic')
                tier_info = self.db.config.get_tier_info(tier)
                total_cost = tier_info.get('price', 0) if tier_info else 0
                
                return {
                    'tier': tier,
                    'days_remaining': max(0, days_remaining),
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
            async with self.db.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO ad_posts (user_id, slot_id, destination, success, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                ''', user_id, slot_id, destination, success, datetime.now())
        except Exception as e:
            self.logger.error(f"Error logging ad post: {e}")
    
    async def get_group_analytics(self, group_username: str) -> Dict:
        """Get analytics for a specific group."""
        try:
            async with self.db.pool.acquire() as conn:
                result = await conn.fetchrow('''
                    SELECT 
                        COUNT(*) as total_posts,
                        COUNT(CASE WHEN success = true THEN 1 END) as successful_posts,
                        AVG(CASE WHEN success = true THEN 1 ELSE 0 END) as success_rate
                    FROM ad_posts 
                    WHERE destination = $1
                ''', group_username)
                
                if result:
                    return {
                        'total_posts': result['total_posts'],
                        'successful_posts': result['successful_posts'],
                        'success_rate': round(result['success_rate'] * 100, 2)
                    }
        except Exception as e:
            self.logger.error(f"Error getting group analytics: {e}")
        
        return {} 