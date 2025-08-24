#!/usr/bin/env python3
"""
Real HD Wallet Implementation using bip_utils
Generates valid, unique addresses from Exodus seed phrase
"""

import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

try:
    from bip_utils import Bip39SeedGenerator, Bip44Coins, Bip84Coins, Bip44, Bip84, Bip44Changes
    BIP_UTILS_AVAILABLE = True
except ImportError:
    logger.warning("bip_utils not installed. Run: pip install bip_utils")
    BIP_UTILS_AVAILABLE = False

class ExodusHDWallet:
    """Real HD wallet implementation using bip_utils with Exodus compatibility."""
    
    def __init__(self, config):
        self.config = config
        self.master_seed = os.getenv('EXODUS_MASTER_SEED', '')
        
        if not self.master_seed:
            logger.warning("EXODUS_MASTER_SEED not configured. HD wallet features disabled.")
            return
        
        if not BIP_UTILS_AVAILABLE:
            logger.warning("bip_utils not available. HD wallet features disabled.")
            return
        
        try:
            # Try to fix common seed phrase issues
            fixed_seed = self.master_seed
            
            # Fix common typos
            word_fixes = {
                'belive': 'believe',
                'recieve': 'receive',
                'seperate': 'separate',
                'occured': 'occurred',
                'begining': 'beginning',
                'neccessary': 'necessary'
            }
            
            for wrong, correct in word_fixes.items():
                if wrong in fixed_seed:
                    fixed_seed = fixed_seed.replace(wrong, correct)
                    logger.info(f"Fixed seed word: {wrong} -> {correct}")
            
            # Generate seed bytes from mnemonic
            self.seed_bytes = Bip39SeedGenerator(fixed_seed).Generate("")
            logger.info("HD wallet initialized successfully with Exodus seed")
        except Exception as e:
            logger.error(f"Error initializing HD wallet: {e}")
            logger.error(f"Original seed: {self.master_seed}")
            self.seed_bytes = None
    
    def payment_id_to_index(self, payment_id: str) -> int:
        """Convert payment ID to deterministic index."""
        import hashlib
        hash_result = hashlib.sha256(payment_id.encode('utf-8')).hexdigest()
        index = int(hash_result[:8], 16) % 1000000
        return index
    
    def get_bitcoin_address(self, payment_id: str) -> str:
        """Generate unique Bitcoin address using BIP84 (Native SegWit) - Exodus compatible."""
        try:
            if not self.seed_bytes:
                raise Exception("HD wallet not initialized")
            
            index = self.payment_id_to_index(payment_id)
            
            # Bitcoin - Use BIP84 for Native SegWit (Exodus uses this)
            # Derivation: m/84'/0'/0'/0/{index}
            bip84_mst_ctx = Bip84.FromSeed(self.seed_bytes, Bip84Coins.BITCOIN)
            bip84_acc_ctx = bip84_mst_ctx.Purpose().Coin().Account(0)
            bip84_chg_ctx = bip84_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
            bip84_addr_ctx = bip84_chg_ctx.AddressIndex(index)
            
            address = bip84_addr_ctx.PublicKey().ToAddress()
            logger.info(f"Generated Exodus-compatible BTC address for payment {payment_id} (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating BTC address: {e}")
            fallback = os.getenv('BTC_ADDRESS', '')
            if fallback:
                logger.warning(f"Using fallback BTC address: {fallback}")
                return fallback
            raise
    
    def get_ethereum_address(self, payment_id: str) -> str:
        """Generate unique Ethereum address using BIP44."""
        try:
            if not self.seed_bytes:
                raise Exception("HD wallet not initialized")
            
            index = self.payment_id_to_index(payment_id)
            
            # Ethereum: m/44'/60'/0'/0/{index}
            bip44_mst_ctx = Bip44.FromSeed(self.seed_bytes, Bip44Coins.ETHEREUM)
            bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
            bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
            bip44_addr_ctx = bip44_chg_ctx.AddressIndex(index)
            
            address = bip44_addr_ctx.PublicKey().ToAddress()
            logger.info(f"Generated ETH address for payment {payment_id} (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating ETH address: {e}")
            fallback = os.getenv('ETH_ADDRESS', '')
            if fallback:
                logger.warning(f"Using fallback ETH address: {fallback}")
                return fallback
            raise
    
    def get_litecoin_address(self, payment_id: str) -> str:
        """Generate unique Litecoin address using BIP44."""
        try:
            if not self.seed_bytes:
                raise Exception("HD wallet not initialized")
            
            index = self.payment_id_to_index(payment_id)
            
            # Litecoin: m/44'/2'/0'/0/{index}
            bip44_mst_ctx = Bip44.FromSeed(self.seed_bytes, Bip44Coins.LITECOIN)
            bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
            bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
            bip44_addr_ctx = bip44_chg_ctx.AddressIndex(index)
            
            address = bip44_addr_ctx.PublicKey().ToAddress()
            logger.info(f"Generated LTC address for payment {payment_id} (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating LTC address: {e}")
            fallback = os.getenv('LTC_ADDRESS', '')
            if fallback:
                logger.warning(f"Using fallback LTC address: {fallback}")
                return fallback
            raise
    
    def get_solana_address(self, payment_id: str) -> str:
        """Generate unique Solana address using BIP44."""
        try:
            if not self.seed_bytes:
                raise Exception("HD wallet not initialized")
            
            index = self.payment_id_to_index(payment_id)
            
            # Solana: m/44'/501'/0'/0/{index}
            bip44_mst_ctx = Bip44.FromSeed(self.seed_bytes, Bip44Coins.SOLANA)
            bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
            bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
            bip44_addr_ctx = bip44_chg_ctx.AddressIndex(index)
            
            address = bip44_addr_ctx.PublicKey().ToAddress()
            logger.info(f"Generated SOL address for payment {payment_id} (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating SOL address: {e}")
            fallback = os.getenv('SOL_ADDRESS', '')
            if fallback:
                logger.warning(f"Using fallback SOL address: {fallback}")
                return fallback
            raise

# Standard payment data generation (no HD wallet)
def generate_standard_payment_data(crypto_type: str, payment_id: str, config) -> Dict[str, Any]:
    """
    Generate payment data using standard wallet addresses.
    This replaces the HD wallet approach to prevent lost funds.
    """
    
    if crypto_type == 'TON':
        # TON uses single address + memo (this works perfectly)
        ton_address = os.getenv('TON_ADDRESS', '')
        if not ton_address:
            raise Exception("TON_ADDRESS not configured")
        
        return {
            'unique_address': ton_address,
            'payment_memo': payment_id,
            'attribution_method': 'memo'
        }
    
    elif crypto_type == 'SOL':
        # SOL uses single address + memo
        sol_address = os.getenv('SOL_ADDRESS', '')
        if not sol_address:
            raise Exception("SOL_ADDRESS not configured")
        
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
