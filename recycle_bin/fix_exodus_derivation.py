#!/usr/bin/env python3
"""
Fix Exodus HD Wallet Derivation Paths
Updates the derivation paths to match Exodus wallet exactly
"""

import os
from typing import Optional, Dict, Any
import logging
from dotenv import load_dotenv

# Load environment
load_dotenv('config/.env')

logger = logging.getLogger(__name__)

try:
    from bip_utils import Bip39SeedGenerator, Bip44Coins, Bip44, Bip84, Bip44Changes, Bip84Coins
    BIP_UTILS_AVAILABLE = True
except ImportError:
    logger.warning("bip_utils not installed. Run: pip install bip_utils")
    BIP_UTILS_AVAILABLE = False

class ExodusCompatibleHDWallet:
    """HD wallet with Exodus-compatible derivation paths."""
    
    def __init__(self):
        self.master_seed = os.getenv('EXODUS_MASTER_SEED', '')
        
        if not self.master_seed:
            logger.error("EXODUS_MASTER_SEED not configured")
            return
        
        if not BIP_UTILS_AVAILABLE:
            logger.error("bip_utils not available")
            return
        
        try:
            # Generate seed bytes from mnemonic
            self.seed_bytes = Bip39SeedGenerator(self.master_seed).Generate("")
            logger.info("✅ Exodus-compatible HD wallet initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing HD wallet: {e}")
            self.seed_bytes = None
    
    def payment_id_to_index(self, payment_id: str) -> int:
        """Convert payment ID to deterministic index."""
        import hashlib
        hash_result = hashlib.sha256(payment_id.encode('utf-8')).hexdigest()
        index = int(hash_result[:8], 16) % 1000000
        return index
    
    def get_bitcoin_address_exodus(self, payment_id: str) -> str:
        """Generate Bitcoin address using BIP84 (Native SegWit) - Exodus compatible."""
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
            logger.info(f"Generated Exodus-compatible BTC address (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating BTC address: {e}")
            raise
    
    def get_bitcoin_address_legacy(self, payment_id: str) -> str:
        """Generate Bitcoin address using BIP44 (Legacy) - for comparison."""
        try:
            if not self.seed_bytes:
                raise Exception("HD wallet not initialized")
            
            index = self.payment_id_to_index(payment_id)
            
            # Bitcoin - Use BIP44 for Legacy addresses
            # Derivation: m/44'/0'/0'/0/{index}
            bip44_mst_ctx = Bip44.FromSeed(self.seed_bytes, Bip44Coins.BITCOIN)
            bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
            bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
            bip44_addr_ctx = bip44_chg_ctx.AddressIndex(index)
            
            address = bip44_addr_ctx.PublicKey().ToAddress()
            logger.info(f"Generated Legacy BTC address (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating Legacy BTC address: {e}")
            raise
    
    def get_ethereum_address(self, payment_id: str) -> str:
        """Generate Ethereum address using BIP44 - Exodus compatible."""
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
            logger.info(f"Generated ETH address (index {index}): {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error generating ETH address: {e}")
            raise

def test_exodus_compatibility():
    """Test Exodus compatibility and show address differences."""
    print("🔍 Testing Exodus HD Wallet Compatibility")
    print("=" * 60)
    
    wallet = ExodusCompatibleHDWallet()
    
    if not wallet.seed_bytes:
        print("❌ HD wallet not initialized. Check your EXODUS_MASTER_SEED")
        return
    
    # Test with a sample payment ID
    test_payment_id = "test_payment_123"
    
    print(f"\n📋 Test Payment ID: {test_payment_id}")
    print(f"🔢 Generated Index: {wallet.payment_id_to_index(test_payment_id)}")
    
    try:
        # Generate addresses using different methods
        print(f"\n🔧 Address Generation Methods:")
        print("-" * 40)
        
        # Exodus-compatible (BIP84)
        exodus_btc = wallet.get_bitcoin_address_exodus(test_payment_id)
        print(f"✅ Exodus BTC (BIP84): {exodus_btc}")
        
        # Legacy (BIP44) - what the bot was using
        legacy_btc = wallet.get_bitcoin_address_legacy(test_payment_id)
        print(f"⚠️ Legacy BTC (BIP44): {legacy_btc}")
        
        # Ethereum
        eth_address = wallet.get_ethereum_address(test_payment_id)
        print(f"✅ ETH (BIP44): {eth_address}")
        
        print(f"\n🎯 ANALYSIS:")
        print(f"   📱 Exodus uses BIP84 for Bitcoin (Native SegWit)")
        print(f"   🤖 Bot was using BIP44 for Bitcoin (Legacy)")
        print(f"   💰 Your payments went to Legacy addresses, not Exodus addresses!")
        print(f"   🔧 Need to update bot to use BIP84 for Bitcoin")
        
        print(f"\n💡 SOLUTION:")
        print(f"   1. Update exodus_hd_wallet.py to use BIP84 for Bitcoin")
        print(f"   2. Generate new addresses using BIP84")
        print(f"   3. Test with small amounts first")
        
    except Exception as e:
        print(f"❌ Error testing addresses: {e}")

def show_derivation_paths():
    """Show the derivation paths used by different methods."""
    print("\n📚 Derivation Paths:")
    print("=" * 40)
    print("🔧 BIP44 (Legacy - what bot was using):")
    print("   BTC: m/44'/0'/0'/0/{index}")
    print("   ETH: m/44'/60'/0'/0/{index}")
    print("   LTC: m/44'/2'/0'/0/{index}")
    print("   SOL: m/44'/501'/0'/0/{index}")
    
    print("\n📱 BIP84 (Native SegWit - what Exodus uses):")
    print("   BTC: m/84'/0'/0'/0/{index}")
    
    print("\n⚠️ The bot needs to use BIP84 for Bitcoin to match Exodus!")

if __name__ == "__main__":
    test_exodus_compatibility()
    show_derivation_paths()
