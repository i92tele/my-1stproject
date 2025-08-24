"""
Configuration management for AutoFarming Bot
"""
try:
    from .bot_config import BotConfig
except ImportError:
    BotConfig = None

try:
    from .database_config import DatabaseConfig
except ImportError:
    DatabaseConfig = None

__all__ = ['BotConfig', 'DatabaseConfig']
