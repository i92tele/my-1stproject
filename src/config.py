import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from config/.env
load_dotenv('config/.env')

class BotConfig:
    """Bot configuration management."""
    
    def __init__(self, 
                 bot_token: str, 
                 admin_id: int, 
                 webhook_base_url: Optional[str] = None):
        if not bot_token:
            raise ValueError("Bot token is required")
        if not admin_id:
            raise ValueError("Admin ID is required")
            
        self.bot_token = bot_token
        self.admin_id = admin_id
        self.webhook_base_url = webhook_base_url
        
        self.db_path = "data/database.sqlite"
        self.log_file = "logs/bot_errors.log"
        
        self.subscription_tiers = self._load_tiers()
        
    def _load_tiers(self) -> Dict[str, Any]:
        """Load subscription tiers from a JSON file."""
        try:
            with open("config/tiers.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Fallback to a default if file is missing or corrupt
            print(f"Warning: Could not load tiers.json: {e}. Using default tiers.")
            return {
                "basic": {"price": 5.00, "duration_days": 30, "max_destinations": 3}
            }
            
    @staticmethod
    def load_from_env():
        """Load configuration from environment variables."""
        try:
            admin_id = int(os.getenv("ADMIN_ID", "0"))
        except ValueError:
            raise ValueError("ADMIN_ID must be a valid integer")
            
        return BotConfig(
            bot_token=os.getenv("BOT_TOKEN"),
            admin_id=admin_id,
            webhook_base_url=os.getenv("WEBHOOK_BASE_URL")
        )
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id == self.admin_id