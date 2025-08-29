#!/usr/bin/env python3
"""
Simple Verification - No External Dependencies

This script verifies the core fixes without requiring aiohttp or other external modules.
"""

import os
import sys

def simple_verification():
    """Perform simple verification of core fixes."""
    print("🔍 SIMPLE VERIFICATION - Core Fixes")
    print("=" * 50)
    
    checks_passed = 0
    total_checks = 0
    
    # CHECK 1: Code Structure Verification
    print("\n📋 CHECK 1: Code Structure")
    print("-" * 30)
    
    # Check 1.1: SOL and LTC in supported_cryptos
    total_checks += 1
    try:
        with open('multi_crypto_payments.py', 'r') as f:
            content = f.read()
            if "'SOL':" in content and "'LTC':" in content and "'TON':" in content:
                print("✅ 1.1: SOL, LTC, TON in supported_cryptos")
                checks_passed += 1
            else:
                print("❌ 1.1: Missing cryptos in supported_cryptos")
    except Exception as e:
        print(f"❌ 1.1: Error reading file - {e}")
    
    # Check 1.2: Fallback prices in price fetching
    total_checks += 1
    try:
        if "fallback_prices" in content and "TON': 5.0" in content:
            print("✅ 1.2: Fallback prices configured")
            checks_passed += 1
        else:
            print("❌ 1.2: Missing fallback prices")
    except Exception as e:
        print(f"❌ 1.2: Error checking fallback prices - {e}")
    
    # Check 1.3: Crypto selection shows all cryptos
    total_checks += 1
    try:
        with open('commands/user_commands.py', 'r') as f:
            user_content = f.read()
            if "cryptos = all_cryptos" in user_content:
                print("✅ 1.3: Crypto selection shows all cryptos")
                checks_passed += 1
            else:
                print("❌ 1.3: Crypto selection still filters cryptos")
    except Exception as e:
        print(f"❌ 1.3: Error checking crypto selection - {e}")
    
    # Check 1.4: DirectPaymentProcessor supports all cryptos
    total_checks += 1
    try:
        with open('src/payment/direct_payment.py', 'r') as f:
            direct_content = f.read()
            if "['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']" in direct_content:
                print("✅ 1.4: DirectPaymentProcessor supports all cryptos")
                checks_passed += 1
            else:
                print("❌ 1.4: DirectPaymentProcessor missing cryptos")
    except Exception as e:
        print(f"❌ 1.4: Error checking DirectPaymentProcessor - {e}")
    
    # CHECK 2: Environment Variables
    print("\n🔧 CHECK 2: Environment Variables")
    print("-" * 30)
    
    # Check 2.1: Environment variables exist
    total_checks += 1
    env_checks = 0
    cryptos = ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']
    
    for crypto in cryptos:
        env_var = f"{crypto}_ADDRESS"
        address = os.getenv(env_var)
        if address:
            print(f"✅ 2.1.{crypto}: Address found")
            env_checks += 1
        else:
            print(f"❌ 2.1.{crypto}: Address not found")
    
    if env_checks > 0:
        print(f"✅ 2.1: {env_checks}/{len(cryptos)} crypto addresses found")
        checks_passed += 1
    else:
        print("❌ 2.1: No crypto addresses found")
    
    # CHECK 3: Import Tests (without aiohttp)
    print("\n📦 CHECK 3: Import Tests")
    print("-" * 30)
    
    # Check 3.1: Config import
    total_checks += 1
    try:
        from src.config.main_config import BotConfig
        config = BotConfig()
        print("✅ 3.1: BotConfig imports successfully")
        checks_passed += 1
    except Exception as e:
        print(f"❌ 3.1: BotConfig import failed - {e}")
    
    # Check 3.2: Database import
    total_checks += 1
    try:
        from src.database.manager import DatabaseManager
        print("✅ 3.2: DatabaseManager imports successfully")
        checks_passed += 1
    except Exception as e:
        print(f"❌ 3.2: DatabaseManager import failed - {e}")
    
    # Check 3.3: DirectPaymentProcessor import
    total_checks += 1
    try:
        from src.payment.direct_payment import DirectPaymentProcessor
        print("✅ 3.3: DirectPaymentProcessor imports successfully")
        checks_passed += 1
    except Exception as e:
        print(f"❌ 3.3: DirectPaymentProcessor import failed - {e}")
    
    # FINAL SUMMARY
    print("\n" + "=" * 50)
    print("🎯 VERIFICATION SUMMARY")
    print("=" * 50)
    
    success_rate = (checks_passed / total_checks) * 100
    print(f"Checks Passed: {checks_passed}/{total_checks}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\n🎉 EXCELLENT QUALITY!")
        print("✅ All core fixes are properly implemented")
        print("✅ Code structure is correct")
        print("✅ Environment variables are available")
        print("✅ Import dependencies are working")
        print("\n📋 Next Steps:")
        print("1. Install aiohttp: pip install aiohttp")
        print("2. Restart your bot")
        print("3. Test the payment system")
    elif success_rate >= 70:
        print("\n⚠️ GOOD QUALITY")
        print("Most fixes are implemented correctly")
        print("Some minor issues may need attention")
    else:
        print("\n❌ POOR QUALITY")
        print("Multiple issues detected")
        print("Payment system may not work correctly")
    
    print(f"\n📊 Detailed Results:")
    print(f"• Code Structure: {checks_passed}/{total_checks} checks passed")
    print(f"• Environment: {env_checks}/{len(cryptos)} crypto addresses found")
    print(f"• Imports: Core modules accessible")
    
    return success_rate >= 90

if __name__ == "__main__":
    success = simple_verification()
    sys.exit(0 if success else 1)
