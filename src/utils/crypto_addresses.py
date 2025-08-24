#!/usr/bin/env python3
"""
Fallback Cryptocurrency Addresses

This module provides fallback cryptocurrency addresses when environment variables are not available.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Fallback addresses - replace with your actual addresses
FALLBACK_ADDRESSES = {
    'BTC': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',  # First Bitcoin address ever (Satoshi)
    'ETH': '0x0000000000000000000000000000000000000000',  # Zero address
    'USDT': '0x0000000000000000000000000000000000000000',  # Zero address
    'USDC': '0x0000000000000000000000000000000000000000',  # Zero address
    'LTC': 'LTC_address_placeholder',
    'SOL': 'SOL_address_placeholder',
    'TON': 'TON_address_placeholder'
}

def get_address(crypto_type):
    """Get cryptocurrency address with fallback."""
    crypto_type = crypto_type.upper()
    
    # Try environment variables first
    env_vars = [
        f"{crypto_type}_ADDRESS",
        f"{crypto_type}_WALLET",
        f"{crypto_type}_WALLET_ADDRESS",
        f"{crypto_type}_ADDR"
    ]
    
    # Special case for TON
    if crypto_type == 'TON':
        env_vars.append('TON_MERCHANT_WALLET')
    
    # Check each environment variable
    for var in env_vars:
        address = os.environ.get(var)
        if address:
            return address
    
    # Use fallback address
    fallback = FALLBACK_ADDRESSES.get(crypto_type)
    if fallback:
        logger.warning(f"Using fallback address for {crypto_type}")
        return fallback
    
    # No address found
    logger.error(f"No address found for {crypto_type}")
    return "Contact support for address"
