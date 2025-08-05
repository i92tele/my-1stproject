import os
from typing import Optional

class EnhancedBotConfig:
    """Enhanced bot configuration with competitive pricing and AutoADS-inspired features."""
    
    def __init__(self):
        # Bot settings
        self.bot_token = os.getenv("BOT_TOKEN")
        self.admin_id = int(os.getenv("ADMIN_ID", "0"))
        self.bot_name = "AutoFarming Pro"  # More professional name
        
        # Database
        self.database_url = os.getenv("DATABASE_URL")
        
        # Cryptocurrency wallets
        self.btc_address = os.getenv("BTC_ADDRESS")
        self.eth_address = os.getenv("ETH_ADDRESS")
        self.sol_address = os.getenv("SOL_ADDRESS")
        self.ltc_address = os.getenv("LTC_ADDRESS")
        self.ton_address = os.getenv("TON_ADDRESS")
        self.usdt_address = os.getenv("USDT_ADDRESS")
        self.trx_address = os.getenv("TRX_ADDRESS")
        self.xmr_address = os.getenv("XMR_ADDRESS")
        self.bnb_address = os.getenv("BNB_ADDRESS")
        
        # Security
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        self.secret_key = os.getenv("SECRET_KEY")
        
        # Redis
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Environment
        self.environment = os.getenv("ENVIRONMENT", "production")
        
        # Enhanced subscription tiers with competitive pricing
        self.subscription_tiers = {
            "basic": {
                "price": 9.99,  # Keep competitive pricing
                "duration_days": 30,
                "ad_slots": 1,
                "posting_interval": 60,  # Hourly posting like AutoADS
                "features": [
                    "🚀 Send message every hour",
                    "🤖 Fully customized bot",
                    "✨ Custom emojis",
                    "🔄 Automatic message updates",
                    "📊 Basic analytics"
                ],
                "max_services": 1,
                "ban_replacements": 0
            },
            "pro": {
                "price": 19.99,  # Competitive vs AutoADS $35
                "duration_days": 30,
                "ad_slots": 3,
                "posting_interval": 60,
                "features": [
                    "🚀 Send message every hour",
                    "🤖 Fully customized bot",
                    "📈 Generate channel views",
                    "🔄 Automatic message updates",
                    "🛡️ 1 free ban replacement",
                    "📊 Advanced analytics",
                    "🎯 Advertise 2 services"
                ],
                "max_services": 2,
                "ban_replacements": 1
            },
            "enterprise": {
                "price": 29.99,  # Competitive vs AutoADS $40
                "duration_days": 30,
                "ad_slots": 5,
                "posting_interval": 60,
                "features": [
                    "🚀 Send message every hour",
                    "🤖 Fully customized bot",
                    "📈 Generate channel views",
                    "🔄 Automatic renewal",
                    "🔄 Automatic message updates",
                    "🛡️ 2 free ban replacements",
                    "📊 Premium analytics",
                    "🎯 Advertise 3 services",
                    "⚡ Priority support"
                ],
                "max_services": 3,
                "ban_replacements": 2
            }
        }
        
        # Payment methods (inspired by AutoADS)
        self.payment_methods = {
            "ton": {"name": "TON", "address": self.ton_address},
            "btc": {"name": "Bitcoin", "address": self.btc_address},
            "eth": {"name": "Ethereum", "address": self.eth_address},
            "usdt": {"name": "USDT", "address": self.usdt_address},
            "sol": {"name": "Solana", "address": self.sol_address},
            "ltc": {"name": "Litecoin", "address": self.ltc_address},
            "trx": {"name": "Tron", "address": self.trx_address},
            "xmr": {"name": "Monero", "address": self.xmr_address},
            "bnb": {"name": "BNB", "address": self.bnb_address}
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
    
    def get_payment_methods(self) -> dict:
        """Get available payment methods."""
        return {k: v for k, v in self.payment_methods.items() if v.get('address')}
    
    def get_tier_features(self, tier: str) -> list:
        """Get features for a specific tier."""
        tier_info = self.get_tier_info(tier)
        return tier_info.get('features', []) if tier_info else [] 