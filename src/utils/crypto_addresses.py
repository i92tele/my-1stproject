#!/usr/bin/env python3
"""
Cryptocurrency Addresses

This module provides cryptocurrency addresses from environment variables.
IMPORTANT: All addresses must be set in environment variables (.env file).
"""

import os
import logging

logger = logging.getLogger(__name__)

def get_address(crypto_type):
    """Get cryptocurrency address from environment variables."""
    crypto_type = crypto_type.upper()
    
    # Special handling for tokens that use different addresses
    if crypto_type == 'USDT':
        # USDT is an ERC-20 token that uses the same address as ETH
        eth_address = os.environ.get('ETH_ADDRESS')
        if eth_address:
            return eth_address
        else:
            logger.error(f"No ETH_ADDRESS found for {crypto_type}. Please set ETH_ADDRESS in your .env file.")
            return f"Contact support for {crypto_type} address"
    elif crypto_type == 'USDC':
        # USDC can be on Solana, so use SOL address
        sol_address = os.environ.get('SOL_ADDRESS')
        if sol_address:
            return sol_address
        else:
            logger.error(f"No SOL_ADDRESS found for {crypto_type}. Please set SOL_ADDRESS in your .env file.")
            return f"Contact support for {crypto_type} address"
    
    env_vars = [
        f"{crypto_type}_ADDRESS",
        f"{crypto_type}_WALLET",
        f"{crypto_type}_WALLET_ADDRESS",
        f"{crypto_type}_ADDR"
    ]
    
    if crypto_type == 'TON':
        env_vars.append('TON_MERCHANT_WALLET')
    
    for var in env_vars:
        address = os.environ.get(var)
        if address:
            return address
    
    logger.error(f"No address found for {crypto_type}. Please set {crypto_type}_ADDRESS in your .env file.")
    return f"Contact support for {crypto_type} address"
