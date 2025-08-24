#!/usr/bin/env python3
"""
Payment Address Fix

This module provides a direct fix for the payment address display issue.
"""

import os
import logging

logger = logging.getLogger(__name__)

def get_crypto_address(crypto_type):
    """Get cryptocurrency address from environment variables."""
    crypto_type = crypto_type.upper()
    
    # Map crypto types to environment variable names
    crypto_map = {
        'BTC': 'BTC_ADDRESS',
        'ETH': 'ETH_ADDRESS',
        'USDT': 'USDT_ADDRESS',
        'USDC': 'USDC_ADDRESS',
        'LTC': 'LTC_ADDRESS',
        'SOL': 'SOL_ADDRESS',
        'TON': 'TON_ADDRESS'
    }
    
    env_var = crypto_map.get(crypto_type)
    if not env_var:
        logger.warning(f"Unknown cryptocurrency: {crypto_type}")
        return None
    
    address = os.getenv(env_var)
    if not address:
        logger.warning(f"No address configured for {crypto_type} ({env_var})")
        return None
    
    logger.info(f"Retrieved {crypto_type} address: {address[:10]}...")
    return address

def fix_payment_data(payment_data):
    """Fix payment data to include address."""
    if not payment_data:
        return payment_data
    
    # If address is missing, add it
    if 'address' not in payment_data and 'crypto_type' in payment_data:
        crypto_type = payment_data.get('crypto_type', 'BTC')
        address = get_crypto_address(crypto_type)
        if address:
            payment_data['address'] = address
    
    # If payment_url is missing, create it
    if 'payment_url' not in payment_data and 'address' in payment_data and 'amount_crypto' in payment_data:
        crypto_type = payment_data.get('crypto_type', 'BTC').lower()
        address = payment_data['address']
        amount = payment_data['amount_crypto']
        
        if crypto_type == 'btc':
            payment_data['payment_url'] = f"bitcoin:{address}?amount={amount}"
        elif crypto_type == 'eth':
            payment_data['payment_url'] = f"ethereum:{address}?value={amount}"
        elif crypto_type == 'ltc':
            payment_data['payment_url'] = f"litecoin:{address}?amount={amount}"
        elif crypto_type == 'sol':
            payment_data['payment_url'] = f"solana:{address}?amount={amount}"
        elif crypto_type == 'ton':
            payment_data['payment_url'] = f"ton://transfer/{address}?amount={amount}"
        else:
            payment_data['payment_url'] = f"crypto:{crypto_type}:{address}?amount={amount}"
    
    return payment_data

# Print environment variables for debugging (only crypto address prefixes)
for var in ['BTC_ADDRESS', 'ETH_ADDRESS', 'USDT_ADDRESS', 'USDC_ADDRESS', 'LTC_ADDRESS', 'SOL_ADDRESS', 'TON_ADDRESS']:
    value = os.getenv(var)
    if value:
        logger.info(f"{var} is set: {value[:10]}...")
    else:
        logger.warning(f"{var} is not set")
