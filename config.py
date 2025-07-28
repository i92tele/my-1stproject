import os
from typing import Optional

class BotConfig:
    """Bot configuration management."""
    
    def __init__(self):
        # Bot settings
        self.bot_token = os.getenv("BOT_TOKEN")
        self.admin_id = int(os.getenv("ADMIN_ID", "0"))
        self.bot_name = "Message Forwarding Bot"
        
        # Database
        self.database_url = os.getenv("DATABASE_URL")
        
        # Cryptocurrency wallets
        self.btc_address = os.getenv("BTC_ADDRESS")
        self.eth_address = os.getenv("ETH_ADDRESS")
        self.sol_address = os.getenv("SOL_ADDRESS")
        self.ltc_address = os.getenv("LTC_ADDRESS")
        
        # Security
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        self.secret_key = os.getenv("SECRET_KEY")
        
        # Redis
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # Subscription tiers
        self.subscription_tiers = {
            "basic": {
                "price": 5.00,
                "duration_days": 30,
                "max_destinations": 3,
                "max_messages_day": 1000
            },
            "premium": {
                "price": 15.00,
                "duration_days": 30,
                "max_destinations": 10,
                "max_messages_day": 10000
            },
            "pro": {
                "price": 30.00,
                "duration_days": 30,
                "max_destinations": -1,  # Unlimited
                "max_messages_day": -1   # Unlimited
            }
        }
        
        # Validate configuration
        self._validate()
    
    def _validate(self):
        """Validate required configuration."""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required")
        if not self.admin_id:
            raise ValueError("ADMIN_ID is required")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables."""
        return cls()
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id == self.admin_id
    
    def get_tier_info(self, tier: str) -> dict:
        """Get information for a specific tier."""
        return self.subscription_tiers.get(tier, None)