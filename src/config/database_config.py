"""
Database configuration for AutoFarming Bot
"""
class DatabaseConfig:
    """Database configuration settings."""
    
    def __init__(self):
        self.db_path = "bot_database.db"
        self.timeout = 60
        self.journal_mode = "WAL"
        self.busy_timeout = 60000
