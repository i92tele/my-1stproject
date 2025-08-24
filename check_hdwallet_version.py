#!/usr/bin/env python3
"""
Check HD Wallet Library Version and API
"""

try:
    import hdwallet
    print(f"HD Wallet version: {hdwallet.__version__}")
    
    # Check available symbols
    from hdwallet.symbols import BTC, ETH, LTC
    print(f"BTC symbol: {BTC}")
    print(f"ETH symbol: {ETH}")
    print(f"LTC symbol: {LTC}")
    
    # Test HD wallet creation
    try:
        wallet = hdwallet.HDWallet()
        print("✅ HDWallet() works without arguments")
    except Exception as e:
        print(f"❌ HDWallet() error: {e}")
    
    try:
        wallet = hdwallet.HDWallet(cryptocurrency=BTC)
        print("✅ HDWallet(cryptocurrency=BTC) works")
    except Exception as e:
        print(f"❌ HDWallet(cryptocurrency=BTC) error: {e}")
    
    try:
        wallet = hdwallet.HDWallet(symbol=BTC)
        print("✅ HDWallet(symbol=BTC) works")
    except Exception as e:
        print(f"❌ HDWallet(symbol=BTC) error: {e}")
        
except ImportError as e:
    print(f"❌ HD wallet not installed: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
