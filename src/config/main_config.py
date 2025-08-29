from dotenv import load_dotenv
from pathlib import Path

# Try multiple possible .env file locations
possible_env_paths = [
    Path('.env'),                    # Root directory
    Path('config/.env'),             # Config directory
    Path('../.env'),                 # Parent directory
    Path('../../.env'),              # Grandparent directory
]

env_loaded = False
for env_path in possible_env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"Loaded environment variables from {env_path}")
        env_loaded = True
        break

if not env_loaded:
    print("Warning: No .env file found in any of the expected locations")
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
        # Make admin_id optional for testing and development
        # Try ADMIN_ID first, then ADMIN_IDS (plural) as fallback
        admin_id_str = os.getenv("ADMIN_ID", "0")
        
        # Check if ADMIN_ID is a placeholder or invalid value
        if admin_id_str == "0" or admin_id_str == "your_telegram_user_id_here" or not admin_id_str.isdigit():
            # Try ADMIN_IDS as fallback
            admin_ids_str = os.getenv("ADMIN_IDS", "")
            if admin_ids_str:
                # Take the first admin ID from the comma-separated list
                admin_ids = [id.strip() for id in admin_ids_str.split(',') if id.strip()]
                if admin_ids:
                    admin_id_str = admin_ids[0]
        
        try:
            self.admin_id = self._parse_admin_id(admin_id_str) if admin_id_str != "0" else 0
        except ValueError:
            # If admin_id is invalid, set to 0 for development
            self.admin_id = 0
        self.bot_name = "AutoFarming Bot"
        
        # Database
        # Fallback to local SQLite file if DATABASE_URL is not provided
        self.database_url = os.getenv("DATABASE_URL") or "bot_database.db"
        
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
                "price": 15.00,
                "duration_days": 30,
                "ad_slots": 1
            },
            "pro": {
                "price": 45.00,
                "duration_days": 30,
                "ad_slots": 3
            },
            "enterprise": {
                "price": 75.00,
                "duration_days": 30,
                "ad_slots": 5
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
        
        # Only validate BOT_TOKEN if we're in production
        if self.environment == "production" and not self.bot_token:
            missing_configs.append("BOT_TOKEN")
        
        # Make admin_id optional for testing and development
        # Only require admin_id in production if bot_token is present
        if self.environment == "production" and self.bot_token and self.admin_id == 0:
            missing_configs.append("ADMIN_ID")
        
        # database_url has a safe default (bot_database.db), so it is not strictly required
        
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
    
    def get_crypto_address(self, crypto: str = None) -> Optional[str]:
        """Get cryptocurrency wallet address.
        
        Args:
            crypto: Cryptocurrency symbol (BTC, ETH, etc.) or None for all addresses
            
        Returns:
            Wallet address or None if not configured, or dict of all addresses if crypto is None
        """
        if crypto is None:
            # Return all configured addresses
            addresses = {}
            if self.btc_address:
                addresses['BTC'] = self.btc_address
            if self.eth_address:
                addresses['ETH'] = self.eth_address
            if self.sol_address:
                addresses['SOL'] = self.sol_address
            if self.ltc_address:
                addresses['LTC'] = self.ltc_address
            if self.ton_address:
                addresses['TON'] = self.ton_address
            if self.usdt_address:
                addresses['USDT'] = self.usdt_address
            if self.usdc_address:
                addresses['USDC'] = self.usdc_address
            if self.ada_address:
                addresses['ADA'] = self.ada_address
            if self.trx_address:
                addresses['TRX'] = self.trx_address
            return addresses
        
        # Return specific crypto address
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
        """Get all configured cryptocurrency addresses.
        
        Returns:
            Dictionary mapping crypto symbols to addresses
        """
        addresses = {}
        if self.btc_address:
            addresses['BTC'] = self.btc_address
        if self.eth_address:
            addresses['ETH'] = self.eth_address
        if self.sol_address:
            addresses['SOL'] = self.sol_address
        if self.ltc_address:
            addresses['LTC'] = self.ltc_address
        if self.ton_address:
            addresses['TON'] = self.ton_address
        if self.usdt_address:
            addresses['USDT'] = self.usdt_address
        if self.usdc_address:
            addresses['USDC'] = self.usdc_address
        if self.ada_address:
            addresses['ADA'] = self.ada_address
        if self.trx_address:
            addresses['TRX'] = self.trx_address
        return addresses