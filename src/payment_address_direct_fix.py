#!/usr/bin/env python3
"""
Direct Fix for Payment Address Display

This module provides a direct fix for payment address display issues.
"""

import os
import logging
from src.utils.env_loader import get_crypto_address

logger = logging.getLogger(__name__)

def fix_payment_data(payment_data):
    """Fix payment data to include address."""
    if not payment_data:
        return payment_data
    
    # If address is missing or N/A, add it
    if 'address' not in payment_data or payment_data.get('address') == 'N/A':
        crypto_type = payment_data.get('crypto_type', 'BTC')
        address = get_crypto_address(crypto_type)
        if address:
            payment_data['address'] = address
            logger.info(f"Added {crypto_type} address to payment data")
    
    return payment_data

def get_payment_message(payment_data, tier="basic"):
    """Generate payment message with address."""
    if not payment_data:
        return "Payment data not available."
    
    crypto_type = payment_data.get('crypto_type', 'BTC')
    amount = payment_data.get('amount_crypto', 0)
    amount_usd = payment_data.get('amount_usd', 15)
    payment_id = payment_data.get('payment_id', 'Unknown')
    
    # Get address - try multiple sources
    address = payment_data.get('address')
    if not address or address == 'N/A':
        address = get_crypto_address(crypto_type)
        if not address:
            address = "Contact support for address"
    
    # Create message
    message = f"₿ {crypto_type} Payment\n"
    message += f"Plan: {tier.capitalize()}\n"
    message += f"Amount: {amount} {crypto_type} (${amount_usd})\n\n"

    message += f"🆔 Payment ID:\n{payment_id}\n\n"
    message += f"💡 No memo required - payment will be\ndetected automatically"
    
    return message
