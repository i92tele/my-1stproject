#!/usr/bin/env python3
"""
Environment Variable Loader

This module ensures environment variables are properly loaded from .env files.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Try to import dotenv, install if not available
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    logger.warning("python-dotenv not installed. Environment variables may not be loaded correctly.")

# Load environment variables from .env file
if DOTENV_AVAILABLE:
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
            logger.info(f"Loaded environment variables from {env_path}")
            env_loaded = True
            break
    
    if not env_loaded:
        logger.warning("No .env file found in any of the expected locations")

# Cache for environment variables
_env_cache: Dict[str, str] = {}

def get_env(key: str, default: Any = None) -> Optional[str]:
    """
    Get environment variable with caching.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    # Check cache first
    if key in _env_cache:
        return _env_cache[key]
    
    # Get from environment
    value = os.environ.get(key, default)
    
    # Cache the result
    _env_cache[key] = value
    
    if value is None:
        logger.debug(f"Environment variable {key} not found")
    
    return value

def get_crypto_address(crypto_type: str) -> Optional[str]:
    """
    Get cryptocurrency address from environment variables.
    
    Args:
        crypto_type: Cryptocurrency type (BTC, ETH, etc.)
        
    Returns:
        Cryptocurrency address or None if not found
    """
    crypto_type = crypto_type.upper()
    
    # Try different environment variable formats
    env_vars = [
        f"{crypto_type}_ADDRESS",  # BTC_ADDRESS
        f"{crypto_type}_WALLET",    # BTC_WALLET
        f"{crypto_type}_WALLET_ADDRESS",  # BTC_WALLET_ADDRESS
        f"{crypto_type}_ADDR",      # BTC_ADDR
    ]
    
    for var in env_vars:
        address = get_env(var)
        if address:
            return address
    
    # Special case for TON
    if crypto_type == 'TON':
        ton_address = get_env('TON_MERCHANT_WALLET')
        if ton_address:
            return ton_address
    
    return None

def get_supported_cryptos() -> Dict[str, str]:
    """Get all supported cryptocurrencies with their addresses."""
    supported = {}
    cryptos = ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']
    
    for crypto in cryptos:
        address = get_crypto_address(crypto)
        if address:
            supported[crypto] = address
    
    return supported

def reload_env() -> None:
    """Reload environment variables and clear cache."""
    global _env_cache
    _env_cache = {}
    
    if DOTENV_AVAILABLE:
        # Try multiple possible .env file locations
        possible_env_paths = [
            Path('.env'),                    # Root directory
            Path('config/.env'),             # Config directory
            Path('../.env'),                 # Parent directory
            Path('../../.env'),              # Grandparent directory
        ]
        
        for env_path in possible_env_paths:
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=True)
                logger.info(f"Reloaded environment variables from {env_path}")
                break
