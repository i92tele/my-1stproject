#!/usr/bin/env python3
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.database.manager import DatabaseManager

class ReferralSystem:
    """Referral and viral growth system."""
    
    def __init__(self, db: DatabaseManager, logger):
        self.db = db
        self.logger = logger
    
    async def create_referral_code(self, user_id: int) -> str:
        """Create a unique referral code for a user."""
        try:
            # Generate unique referral code
            referral_code = f"REF_{secrets.token_urlsafe(8)}"
            
            async with self.db.pool.acquire() as conn:
                # Create referral table if not exists
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS referrals (
                        id SERIAL PRIMARY KEY,
                        referrer_id BIGINT REFERENCES users(user_id),
                        referred_id BIGINT REFERENCES users(user_id),
                        referral_code VARCHAR(50) UNIQUE NOT NULL,
                        status VARCHAR(20) DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        reward_claimed BOOLEAN DEFAULT false
                    )
                ''')
                
                # Store referral code
                await conn.execute('''
                    INSERT INTO referrals (referrer_id, referral_code)
                    VALUES ($1, $2)
                    ON CONFLICT (referral_code) DO NOTHING
                ''', user_id, referral_code)
                
                return referral_code
        except Exception as e:
            self.logger.error(f"Error creating referral code: {e}")
            return None
    
    async def process_referral(self, referral_code: str, new_user_id: int) -> Dict:
        """Process a referral when a new user signs up."""
        try:
            async with self.db.pool.acquire() as conn:
                # Get referral record
                referral = await conn.fetchrow('''
                    SELECT referrer_id, status FROM referrals 
                    WHERE referral_code = $1
                ''', referral_code)
                
                if not referral:
                    return {'success': False, 'message': 'Invalid referral code'}
                
                if referral['status'] != 'pending':
                    return {'success': False, 'message': 'Referral code already used'}
                
                # Update referral status
                await conn.execute('''
                    UPDATE referrals 
                    SET referred_id = $1, status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE referral_code = $2
                ''', new_user_id, referral_code)
                
                # Give rewards to both users
                referrer_id = referral['referrer_id']
                
                # Reward referrer (extend subscription by 7 days)
                await self._give_referrer_reward(referrer_id)
                
                # Reward new user (50% discount on first month)
                await self._give_new_user_reward(new_user_id)
                
                return {
                    'success': True,
                    'referrer_id': referrer_id,
                    'message': 'Referral processed successfully'
                }
                
        except Exception as e:
            self.logger.error(f"Error processing referral: {e}")
            return {'success': False, 'message': 'Error processing referral'}
    
    async def _give_referrer_reward(self, referrer_id: int):
        """Give reward to referrer (extend subscription)."""
        try:
            user = await self.db.get_user(referrer_id)
            if user and user.get('subscription_expires'):
                # Extend subscription by 7 days
                new_expiry = user['subscription_expires'] + timedelta(days=7)
                
                async with self.db.pool.acquire() as conn:
                    await conn.execute('''
                        UPDATE users 
                        SET subscription_expires = $1 
                        WHERE user_id = $2
                    ''', new_expiry, referrer_id)
                
                self.logger.info(f"Extended subscription for referrer {referrer_id}")
        except Exception as e:
            self.logger.error(f"Error giving referrer reward: {e}")
    
    async def _give_new_user_reward(self, new_user_id: int):
        """Give reward to new user (50% discount)."""
        try:
            # Store discount in user data
            async with self.db.pool.acquire() as conn:
                await conn.execute('''
                    UPDATE users 
                    SET referral_discount = true 
                    WHERE user_id = $1
                ''', new_user_id)
            
            self.logger.info(f"Applied referral discount for new user {new_user_id}")
        except Exception as e:
            self.logger.error(f"Error giving new user reward: {e}")
    
    async def get_referral_stats(self, user_id: int) -> Dict:
        """Get referral statistics for a user."""
        try:
            async with self.db.pool.acquire() as conn:
                # Get total referrals
                total_referrals = await conn.fetchval('''
                    SELECT COUNT(*) FROM referrals 
                    WHERE referrer_id = $1 AND status = 'completed'
                ''', user_id)
                
                # Get pending referrals
                pending_referrals = await conn.fetchval('''
                    SELECT COUNT(*) FROM referrals 
                    WHERE referrer_id = $1 AND status = 'pending'
                ''', user_id)
                
                # Get total rewards earned
                rewards_earned = await conn.fetchval('''
                    SELECT COUNT(*) FROM referrals 
                    WHERE referrer_id = $1 AND status = 'completed' AND reward_claimed = true
                ''', user_id)
                
                return {
                    'total_referrals': total_referrals,
                    'pending_referrals': pending_referrals,
                    'rewards_earned': rewards_earned,
                    'referral_code': await self.get_user_referral_code(user_id)
                }
        except Exception as e:
            self.logger.error(f"Error getting referral stats: {e}")
            return {}
    
    async def get_user_referral_code(self, user_id: int) -> Optional[str]:
        """Get referral code for a user."""
        try:
            async with self.db.pool.acquire() as conn:
                result = await conn.fetchrow('''
                    SELECT referral_code FROM referrals 
                    WHERE referrer_id = $1 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', user_id)
                
                return result['referral_code'] if result else None
        except Exception as e:
            self.logger.error(f"Error getting user referral code: {e}")
            return None
    
    async def check_referral_discount(self, user_id: int) -> bool:
        """Check if user has referral discount available."""
        try:
            user = await self.db.get_user(user_id)
            return user.get('referral_discount', False) if user else False
        except Exception as e:
            self.logger.error(f"Error checking referral discount: {e}")
            return False
    
    async def apply_referral_discount(self, user_id: int, tier: str) -> float:
        """Apply referral discount to subscription price."""
        try:
            has_discount = await self.check_referral_discount(user_id)
            if has_discount:
                tier_info = self.db.config.get_tier_info(tier)
                if tier_info:
                    original_price = tier_info['price']
                    discounted_price = original_price * 0.5  # 50% discount
                    
                    # Remove discount after use
                    async with self.db.pool.acquire() as conn:
                        await conn.execute('''
                            UPDATE users 
                            SET referral_discount = false 
                            WHERE user_id = $1
                        ''', user_id)
                    
                    return discounted_price
            
            # Return original price if no discount
            tier_info = self.db.config.get_tier_info(tier)
            return tier_info['price'] if tier_info else 0
            
        except Exception as e:
            self.logger.error(f"Error applying referral discount: {e}")
            return 0 