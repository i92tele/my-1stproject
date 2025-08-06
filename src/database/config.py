from dotenv import load_dotenv
load_dotenv("config/.env")
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class BotConfig:
    """Bot configuration management for AutoFarming Bot.
    
    Handles all environment variables, validation, and configuration
    settings for the Telegram bot application.
    """
    
    def __init__(self):
        """Initialize bot configuration from environment variables."""
        # Bot settings
        self.bot_token = os.getenv("BOT_TOKEN")
        self.admin_id = self._parse_admin_id(os.getenv("ADMIN_ID", "0"))
        self.bot_name = "AutoFarming Bot"
        
        # Database
        self.database_url = os.getenv("DATABASE_URL")
        
        # Cryptocurrency wallets
        self.btc_address = os.getenv("BTC_ADDRESS")
        self.eth_address = os.getenv("ETH_ADDRESS")
        self.sol_address = os.getenv("SOL_ADDRESS")
        self.ltc_address = os.getenv("LTC_ADDRESS")
        self.ton_address = os.getenv("TON_ADDRESS")
        self.usdt_address = os.getenv("USDT_ADDRESS")
        self.usdc_address = os.getenv("USDC_ADDRESS")
        self.ada_address = os.getenv("ADA_ADDRESS")
        self.trx_address = os.getenv("TRX_ADDRESS")
        self.etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
        self.blockcypher_api_key = os.getenv("BLOCKCYPHER_API_KEY")
        
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
                "price": 9.99,
                "duration_days": 30,
                "ad_slots": 1
            },
            "pro": {
                "price": 39.99,
                "duration_days": 30,
                "ad_slots": 5
            },
            "enterprise": {
                "price": 99.99,
                "duration_days": 30,
                "ad_slots": 15
            }
        }
        
        # Validate configuration
        self._validate()
    
    def _parse_admin_id(self, admin_id_str: str) -> int:
        """Parse admin ID from string with error handling.
        
        Args:
            admin_id_str: Admin ID as string
            
        Returns:
            Parsed admin ID as integer
            
        Raises:
            ValueError: If admin ID is invalid
        """
        try:
            return int(admin_id_str)
        except ValueError:
            logger.error(f"Invalid ADMIN_ID: {admin_id_str}")
            raise ValueError(f"ADMIN_ID must be a valid integer, got: {admin_id_str}")
    
    def _validate(self) -> None:
        """Validate required configuration values.
        
        Raises:
            ValueError: If required configuration is missing
        """
        missing_configs = []
        
        if not self.bot_token:
            missing_configs.append("BOT_TOKEN")
        if not self.admin_id:
            missing_configs.append("ADMIN_ID")
        if not self.database_url:
            missing_configs.append("DATABASE_URL")
        
        if missing_configs:
            error_msg = f"Missing required configuration: {', '.join(missing_configs)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("Configuration validation passed")
    
    @classmethod
    def load_from_env(cls) -> 'BotConfig':
        """Load configuration from environment variables.
        
        Returns:
            Configured BotConfig instance
            
        Raises:
            ValueError: If required configuration is missing
        """
        return cls()
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin.
        
        Args:
            user_id: Telegram user ID to check
            
        Returns:
            True if user is admin, False otherwise
        """
        return user_id == self.admin_id
    
    def get_tier_info(self, tier: str) -> Optional[Dict[str, Any]]:
        """Get information for a specific subscription tier.
        
        Args:
            tier: Tier name (basic, pro, enterprise)
            
        Returns:
            Tier configuration dict or None if tier doesn't exist
        """
        return self.subscription_tiers.get(tier, None)
    
    def get_crypto_address(self, crypto: str) -> Optional[str]:
        """Get cryptocurrency wallet address.
        
        Args:
            crypto: Cryptocurrency symbol (BTC, ETH, etc.)
            
        Returns:
            Wallet address or None if not configured
        """
        address_map = {
            'BTC': self.btc_address,
            'ETH': self.eth_address,
            'SOL': self.sol_address,
            'LTC': self.ltc_address,
            'TON': self.ton_address,
            'USDT': self.usdt_address,
            'USDC': self.usdc_address,
            'ADA': self.ada_address,
            'TRX': self.trx_address
        }
        return address_map.get(crypto.upper())
    
    def is_production(self) -> bool:
        """Check if running in production environment.
        
        Returns:
            True if production, False otherwise
        """
        return self.environment.lower() == "production"