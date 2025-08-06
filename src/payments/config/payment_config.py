"""
Payment Configuration

Centralized configuration for the payment system.
"""

import os
from typing import Dict, Optional
from ..core.entities import CryptoCurrency
from ..core.interfaces import ConfigurationInterface


class PaymentConfig(ConfigurationInterface):
    """Payment system configuration."""
    
    def __init__(self):
        self.load_from_environment()
    
    def load_from_environment(self):
        """Load configuration from environment variables."""
        # Crypto wallet addresses
        self.wallet_addresses = {
            CryptoCurrency.BTC: os.getenv('BTC_WALLET_ADDRESS', ''),
            CryptoCurrency.ETH: os.getenv('ETH_WALLET_ADDRESS', ''),
            CryptoCurrency.USDT: os.getenv('USDT_WALLET_ADDRESS', ''),  # ERC-20
            CryptoCurrency.USDC: os.getenv('USDC_WALLET_ADDRESS', ''),  # ERC-20
            CryptoCurrency.TON: os.getenv('TON_WALLET_ADDRESS', ''),
            CryptoCurrency.SOL: os.getenv('SOL_WALLET_ADDRESS', ''),
            CryptoCurrency.LTC: os.getenv('LTC_WALLET_ADDRESS', '')
        }
        
        # API keys for blockchain services
        self.api_keys = {
            'etherscan': os.getenv('ETHERSCAN_API_KEY', ''),
            'blockcypher': os.getenv('BLOCKCYPHER_API_KEY', ''),
            'coingecko': os.getenv('COINGECKO_API_KEY', ''),  # Pro API key (optional)
            'coinmarketcap': os.getenv('COINMARKETCAP_API_KEY', ''),
            'alchemy': os.getenv('ALCHEMY_API_KEY', ''),  # Alternative ETH provider
            'infura': os.getenv('INFURA_API_KEY', '')  # Alternative ETH provider
        }
        
        # Confirmation requirements
        self.confirmation_requirements = {
            CryptoCurrency.BTC: int(os.getenv('BTC_CONFIRMATIONS', '2')),
            CryptoCurrency.ETH: int(os.getenv('ETH_CONFIRMATIONS', '12')),
            CryptoCurrency.USDT: int(os.getenv('USDT_CONFIRMATIONS', '12')),
            CryptoCurrency.USDC: int(os.getenv('USDC_CONFIRMATIONS', '12')),
            CryptoCurrency.TON: int(os.getenv('TON_CONFIRMATIONS', '1')),
            CryptoCurrency.SOL: int(os.getenv('SOL_CONFIRMATIONS', '1')),
            CryptoCurrency.LTC: int(os.getenv('LTC_CONFIRMATIONS', '6'))
        }
        
        # Payment settings
        self.payment_timeout_hours = int(os.getenv('PAYMENT_TIMEOUT_HOURS', '1'))
        self.verification_interval_seconds = int(os.getenv('VERIFICATION_INTERVAL_SECONDS', '30'))
        self.price_cache_minutes = int(os.getenv('PRICE_CACHE_MINUTES', '5'))
        
        # Network settings
        self.testnet_mode = os.getenv('TESTNET_MODE', 'false').lower() == 'true'
        
        # Blockchain RPC endpoints
        self.rpc_endpoints = {
            'ethereum': os.getenv('ETH_RPC_URL', 'https://eth-mainnet.alchemyapi.io/v2/'),
            'solana': os.getenv('SOL_RPC_URL', 'https://api.mainnet-beta.solana.com'),
            'ton': os.getenv('TON_RPC_URL', 'https://toncenter.com/api/v2/'),
            'bitcoin': os.getenv('BTC_RPC_URL', 'https://blockstream.info/api/'),
            'litecoin': os.getenv('LTC_RPC_URL', 'https://api.blockcypher.com/v1/ltc/main')
        }
    
    def get_wallet_address(self, cryptocurrency: CryptoCurrency) -> str:
        """Get wallet address for cryptocurrency."""
        address = self.wallet_addresses.get(cryptocurrency, '')
        if not address:
            raise ValueError(f"No wallet address configured for {cryptocurrency.value}")
        return address
    
    def get_confirmation_requirements(self, cryptocurrency: CryptoCurrency) -> int:
        """Get required confirmations for cryptocurrency."""
        return self.confirmation_requirements.get(cryptocurrency, 1)
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for external service."""
        return self.api_keys.get(service)
    
    def is_testnet(self) -> bool:
        """Check if running in testnet mode."""
        return self.testnet_mode
    
    def get_rpc_endpoint(self, blockchain: str) -> str:
        """Get RPC endpoint for blockchain."""
        endpoint = self.rpc_endpoints.get(blockchain, '')
        if not endpoint:
            raise ValueError(f"No RPC endpoint configured for {blockchain}")
        return endpoint
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Validate configuration completeness."""
        validation = {
            'wallet_addresses': True,
            'api_keys': True,
            'rpc_endpoints': True
        }
        
        # Check wallet addresses
        for crypto, address in self.wallet_addresses.items():
            if not address and crypto != CryptoCurrency.SOL:  # SOL is optional for now
                validation['wallet_addresses'] = False
                break
        
        # Check critical API keys
        critical_keys = ['etherscan']  # Minimum required
        for key in critical_keys:
            if not self.api_keys.get(key):
                validation['api_keys'] = False
                break
        
        # Check RPC endpoints
        for blockchain, endpoint in self.rpc_endpoints.items():
            if not endpoint:
                validation['rpc_endpoints'] = False
                break
        
        return validation
    
    def get_missing_config(self) -> Dict[str, list]:
        """Get list of missing configuration items."""
        missing = {
            'wallet_addresses': [],
            'api_keys': [],
            'rpc_endpoints': []
        }
        
        # Missing wallet addresses
        for crypto, address in self.wallet_addresses.items():
            if not address:
                missing['wallet_addresses'].append(f"{crypto.value}_WALLET_ADDRESS")
        
        # Missing API keys
        for service, key in self.api_keys.items():
            if not key and service in ['etherscan']:  # Only critical ones
                missing['api_keys'].append(f"{service.upper()}_API_KEY")
        
        # Missing RPC endpoints
        for blockchain, endpoint in self.rpc_endpoints.items():
            if not endpoint:
                missing['rpc_endpoints'].append(f"{blockchain.upper()}_RPC_URL")
        
        return missing