from typing import Dict, List
from datetime import datetime
import logging

class MonetizationEngine:
    """Basic monetization features."""
    
    def __init__(self, db, config, logger):
        self.db = db
        self.config = config
        self.logger = logger
    
    async def get_active_promotions(self, user_id: int) -> List[Dict]:
        """Get active promotional offers for user."""
        user_data = await self.db.get_user(user_id)
        current_tier = user_data.get('subscription_tier', None) if user_data else None
        
        promotions = []
        
        # New user promotion
        if not current_tier:
            promotions.append({
                'id': 'first_month_50',
                'type': 'discount',
                'name': '?? New User Special',
                'description': '50% off your first month!',
                'discount_percent': 50,
                'applicable_tiers': ['basic', 'premium', 'pro']
            })
        
        return promotions
    
    async def calculate_discount(self, user_id: int, tier: str, promotion_id: str = None) -> Dict:
        """Calculate pricing with any applicable discounts."""
        base_price = self.config.subscription_tiers[tier]['price']
        discount_amount = 0
        
        if promotion_id:
            promotions = await self.get_active_promotions(user_id)
            for promo in promotions:
                if promo['id'] == promotion_id:
                    discount_amount = base_price * (promo['discount_percent'] / 100)
                    break
        
        final_price = base_price - discount_amount
        
        return {
            'base_price': base_price,
            'discount': discount_amount,
            'final_price': final_price
        }