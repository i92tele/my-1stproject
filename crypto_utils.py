#!/usr/bin/env python3
"""
Simple Crypto Utilities for Multi-Crypto Payment Processor
Basic classes for payment data structures
"""

class EthereumPaymentData:
    """Simple class for Ethereum payment data."""
    def __init__(self, address: str, amount: float, memo: str = None):
        self.address = address
        self.amount = amount
        self.memo = memo

class SolanaPaymentMemo:
    """Simple class for Solana payment memo."""
    def __init__(self, memo: str):
        self.memo = memo

class LitecoinPaymentData:
    # Simple class for Litecoin payment data
    def __init__(self, address: str, amount: float):
        self.address = address
        self.amount = amount

class SolanaPaymentData:
    # Simple class for Solana payment data
    def __init__(self, address: str, amount: float, memo: str = None):
        self.address = address
        self.amount = amount
        self.memo = memo

def get_crypto_address(crypto_code: str):
    # Get crypto address from environment variables
    crypto_map = {
        'BTC': 'BTC_ADDRESS',
        'ETH': 'ETH_ADDRESS',
        'USDT': 'USDT_ADDRESS',
        'USDC': 'USDC_ADDRESS',
        'LTC': 'LTC_ADDRESS',
        'SOL': 'SOL_ADDRESS',
        'TON': 'TON_ADDRESS'
    }
    
    env_var = crypto_map.get(crypto_code.upper())
    if not env_var:
        return None
    
    return os.getenv(env_var)

def is_crypto_supported(crypto_code: str):
    # Check if cryptocurrency is supported
    address = get_crypto_address(crypto_code)
    return address is not None
