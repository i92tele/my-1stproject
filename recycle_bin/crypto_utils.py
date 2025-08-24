#!/usr/bin/env python3
"""
Cryptocurrency Utilities for Better Payment Attribution
Implements HD wallet derivation using Exodus + Tonkeeper
"""

import hashlib
import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Install required libraries
try:
    from hdwallet import HDWallet
    from hdwallet.symbols import BTC, ETH, LTC
    from mnemonic import Mnemonic
    HD_WALLET_AVAILABLE = True
except ImportError:
    logger.warning("HD wallet libraries not installed. Run: pip install hdwallet mnemonic")
    HD_WALLET_AVAILABLE = False

try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    import base58
    SOLANA_AVAILABLE = True
except ImportError:
    logger.warning("Solana libraries not installed. Run: pip install solders")
    SOLANA_AVAILABLE = False

class ExodusHDWallet:
    """Real HD wallet derivation using Exodus-compatible seeds."""
    
    def __init__(self, config):
        self.config = config
        self.master_seed = os.getenv('EXODUS_MASTER_SEED', '')
        
        if not self.master_seed:
            logger.warning("EXODUS_MASTER_SEED not configured. HD wallet features disabled.")
    
    def payment_id_to_index(self, payment_id: str) -> int:
        """Convert payment ID to deterministic index."""
        # Create deterministic index from payment ID
        hash_result = hashlib.sha256(payment_id.encode('utf-8')).hexdigest()
        # Use first 8 chars of hash as hex number, mod 1000000 for reasonable range
        index = int(hash_result[:8], 16) % 1000000
        return index
    
    def derive_btc_address(self, payment_id: str) -> str:
        """Generate unique Bitcoin address using HD wallet derivation."""
        try:
            if not HD_WALLET_AVAILABLE:
                raise Exception("HD wallet libraries not installed")
            
            if not self.master_seed:
                raise Exception("EXODUS_MASTER_SEED not configured")
            
            # Generate deterministic index from payment ID
            index = self.payment_id_to_index(payment_id)
            
            # Create HD wallet for Bitcoin
            hdwallet = HDWallet(cryptocurrency=BTC)
            hdwallet.from_mnemonic(self.master_seed)
            
            # Use standard BIP44 derivation path: m/44'/0'/0'/0/{index}
            derivation_path = f"m/44'/0'/0'/0/{index}"
            hdwallet.from_path(derivation_path)
            
            # Get P2WPKH (bech32) address - most modern Bitcoin address format
            address = hdwallet.p2wpkh_address()
            
            logger.info(f"Generated BTC address for payment {payment_id} (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating BTC HD address: {e}")
            # Fallback to env variable if available
            fallback = os.getenv('BTC_ADDRESS', '')
            if fallback:
                logger.warning(f"Using fallback BTC address: {fallback}")
                return fallback
            raise
    
    def derive_eth_address(self, payment_id: str) -> str:
        """Generate unique Ethereum address using HD wallet derivation."""
        try:
            if not HD_WALLET_AVAILABLE:
                raise Exception("HD wallet libraries not installed")
            
            if not self.master_seed:
                raise Exception("EXODUS_MASTER_SEED not configured")
            
            index = self.payment_id_to_index(payment_id)
            
            # Create HD wallet for Ethereum
            hdwallet = HDWallet(cryptocurrency=ETH)
            hdwallet.from_mnemonic(self.master_seed)
            
            # Use standard BIP44 derivation path: m/44'/60'/0'/0/{index}
            derivation_path = f"m/44'/60'/0'/0/{index}"
            hdwallet.from_path(derivation_path)
            
            address = hdwallet.p2pkh_address()  # Ethereum address
            
            logger.info(f"Generated ETH address for payment {payment_id} (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating ETH HD address: {e}")
            fallback = os.getenv('ETH_ADDRESS', '')
            if fallback:
                logger.warning(f"Using fallback ETH address: {fallback}")
                return fallback
            raise
    
    def derive_ltc_address(self, payment_id: str) -> str:
        """Generate unique Litecoin address using HD wallet derivation."""
        try:
            if not HD_WALLET_AVAILABLE:
                raise Exception("HD wallet libraries not installed")
            
            if not self.master_seed:
                raise Exception("EXODUS_MASTER_SEED not configured")
            
            index = self.payment_id_to_index(payment_id)
            
            # Create HD wallet for Litecoin
            hdwallet = HDWallet(cryptocurrency=LTC)
            hdwallet.from_mnemonic(self.master_seed)
            
            # Use standard BIP44 derivation path: m/44'/2'/0'/0/{index}
            derivation_path = f"m/44'/2'/0'/0/{index}"
            hdwallet.from_path(derivation_path)
            
            address = hdwallet.p2wpkh_address()  # Bech32 Litecoin address
            
            logger.info(f"Generated LTC address for payment {payment_id} (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating LTC HD address: {e}")
            fallback = os.getenv('LTC_ADDRESS', '')
            if fallback:
                logger.warning(f"Using fallback LTC address: {fallback}")
                return fallback
            raise
    
    def derive_sol_address(self, payment_id: str) -> str:
        """Generate unique Solana address using seed derivation."""
        try:
            if not SOLANA_AVAILABLE:
                raise Exception("Solana libraries not installed")
            
            if not self.master_seed:
                raise Exception("EXODUS_MASTER_SEED not configured")
            
            index = self.payment_id_to_index(payment_id)
            
            # For Solana, we'll create a deterministic keypair from seed + index
            # This is a simplified approach - production might use different derivation
            seed_with_index = f"{self.master_seed}_{index}".encode('utf-8')
            seed_hash = hashlib.sha256(seed_with_index).digest()
            
            # Ensure we have exactly 64 bytes for Solana keypair
            if len(seed_hash) < 64:
                # Extend the hash if needed
                extended_seed = seed_hash + hashlib.sha256(seed_hash).digest()
                seed_hash = extended_seed[:64]
            else:
                seed_hash = seed_hash[:64]
            
            # Create keypair from seed
            keypair = Keypair.from_bytes(seed_hash)
            address = str(keypair.pubkey())
            
            logger.info(f"Generated SOL address for payment {payment_id} (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating SOL address: {e}")
            fallback = os.getenv('SOL_ADDRESS', '')
            if fallback:
                logger.warning(f"Using fallback SOL address: {fallback}")
                return fallback
            raise

class EthereumPaymentData:
    """Generate Ethereum transaction data for payment attribution."""
    
    @staticmethod
    def encode_payment_id(payment_id: str) -> str:
        """
        Encode payment ID as hex data for Ethereum transaction.
        
        Ethereum allows including data in transactions that can be used
        for identification without affecting the transfer.
        """
        try:
            # Convert payment_id to hex
            payment_hex = payment_id.encode('utf-8').hex()
            # Prefix with 0x for Ethereum data field
            return f"0x{payment_hex}"
        except Exception as e:
            logger.error(f"Error encoding payment ID for ETH: {e}")
            return "0x"
    
    @staticmethod
    def decode_payment_id(hex_data: str) -> Optional[str]:
        """Decode payment ID from Ethereum transaction data."""
        try:
            if not hex_data or hex_data == "0x":
                return None
            
            # Remove 0x prefix
            clean_hex = hex_data[2:] if hex_data.startswith('0x') else hex_data
            
            # Convert hex to string
            payment_id = bytes.fromhex(clean_hex).decode('utf-8')
            return payment_id
            
        except Exception as e:
            logger.debug(f"Could not decode payment ID from hex data: {e}")
            return None

class SolanaPaymentMemo:
    """Generate Solana memo instructions for payment attribution."""
    
    @staticmethod
    def create_memo_instruction(payment_id: str) -> str:
        """
        Create memo instruction for Solana payment.
        
        Solana supports memo instructions that can include payment IDs
        without affecting the SPL token or SOL transfer.
        """
        return f"Payment-{payment_id}"
    
    @staticmethod
    def extract_memo_from_transaction(transaction_data: Dict[str, Any]) -> Optional[str]:
        """Extract memo from Solana transaction."""
        try:
            # Look for memo in transaction instructions
            instructions = transaction_data.get('transaction', {}).get('message', {}).get('instructions', [])
            
            for instruction in instructions:
                if instruction.get('program') == 'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr':
                    # This is a memo instruction
                    memo_data = instruction.get('data', '')
                    if memo_data.startswith('Payment-'):
                        return memo_data[8:]  # Remove 'Payment-' prefix
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract memo from Solana transaction: {e}")
            return None

# Main utility functions
def generate_unique_payment_data(crypto_type: str, payment_id: str, config) -> Dict[str, Any]:
    """
    Generate payment data using standard wallet addresses.
    
    Returns:
        Dictionary containing standard address/data for the payment
    """
    
    if crypto_type == 'TON':
        # TON uses single address + memo
        ton_address = os.getenv('TON_ADDRESS', '')
        if not ton_address:
            raise Exception("TON_ADDRESS not configured. Set up Tonkeeper wallet first.")
        
        return {
            'unique_address': ton_address,
            'payment_memo': payment_id,
            'attribution_method': 'memo'
        }
    
    elif crypto_type == 'SOL':
        # SOL uses single address + memo
        sol_address = os.getenv('SOL_ADDRESS', '')
        if not sol_address:
            raise Exception("SOL_ADDRESS not configured.")
        
        return {
            'unique_address': sol_address,
            'payment_memo': payment_id,
            'attribution_method': 'memo'
        }
    
    elif crypto_type in ['BTC', 'ETH', 'LTC']:
        # Use standard addresses with time window attribution
        master_address = os.getenv(f'{crypto_type}_ADDRESS', '')
        if not master_address:
            raise Exception(f"{crypto_type}_ADDRESS not configured")
        
        return {
            'unique_address': master_address,
            'attribution_method': 'amount_time_window'
        }
    
    else:
        # Fallback for unknown cryptos
        fallback_address = os.getenv(f'{crypto_type}_ADDRESS', '')
        return {
            'unique_address': fallback_address,
            'attribution_method': 'amount_time_window'
        }
