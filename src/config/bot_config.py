"""
Bot configuration management for AutoFarming Bot
"""
import os
from typing import List, Optional

class BotConfig:
    """Bot configuration management."""
    
    def __init__(self):
        """Initialize bot configuration."""
        self.bot_token = os.getenv('BOT_TOKEN', '')
        self.database_url = os.getenv('DATABASE_URL', 'bot_database.db')
        self.db_path = os.getenv('DATABASE_PATH', 'bot_database.db')
        self.admin_ids = self._parse_admin_ids()
        
    def _parse_admin_ids(self) -> List[int]:
        """Parse admin IDs from environment variable."""
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        if not admin_ids_str:
            return []
        
        try:
            return [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]
        except ValueError:
            return []
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin."""
        return user_id in self.admin_ids
    
    def get_crypto_address(self, crypto: str = None) -> Optional[str]:
        """Get crypto address for payment processing."""
        # Map crypto types to environment variable names
        crypto_map = {
            'btc': 'BTC_ADDRESS',
            'eth': 'ETH_ADDRESS', 
            'usdt': 'USDT_ADDRESS',
            'usdc': 'USDC_ADDRESS',
            'ltc': 'LTC_ADDRESS',
            'doge': 'DOGE_ADDRESS',
            'bch': 'BCH_ADDRESS',
            'xrp': 'XRP_ADDRESS',
            'ada': 'ADA_ADDRESS',
            'dot': 'DOT_ADDRESS',
            'link': 'LINK_ADDRESS',
            'uni': 'UNI_ADDRESS',
            'matic': 'MATIC_ADDRESS',
            'sol': 'SOL_ADDRESS',
            'avax': 'AVAX_ADDRESS',
            'atom': 'ATOM_ADDRESS',
            'ftm': 'FTM_ADDRESS',
            'near': 'NEAR_ADDRESS',
            'algo': 'ALGO_ADDRESS',
            'vet': 'VET_ADDRESS'
        }
        
        if crypto:
            # Get specific crypto address
            env_var = crypto_map.get(crypto.lower())
            if env_var:
                return os.getenv(env_var)
            return None
        else:
            # Return first available crypto address
            for crypto_type, env_var in crypto_map.items():
                address = os.getenv(env_var)
                if address:
                    return address
            return None
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables."""
        return cls()

    @property
    def admin_id(self) -> int:
        """Get first admin ID for backward compatibility."""
        return self.admin_ids[0] if self.admin_ids else 0
