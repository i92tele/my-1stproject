"""
Database module for AutoFarming Bot
Imports the DatabaseManager from src/database.py for compatibility
"""

# Import the DatabaseManager from the src directory
from src.database import DatabaseManager

# Re-export for compatibility
__all__ = ['DatabaseManager']
