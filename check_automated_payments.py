#!/usr/bin/env python3
"""
Check Automated Payments System

This script verifies that the automated payment system is properly configured
and can be started for automatic payment verification.
"""

import os
import sys
import asyncio
import sqlite3
from datetime import datetime

def check_automated_payments():
    """Check the automated payment system setup."""
    print("💰 AUTOMATED PAYMENTS SYSTEM CHECK")
    print("=" * 50)
    
    results = {
        'passed': [],
        'failed': [],
        'warnings': []
    }
    
    try:
        # 1. Check Payment Monitor Service
        print("\n🔍 1. Payment Monitor Service...")
        check_payment_monitor(results)
        
        # 2. Check Multi-Crypto Payment Processor
        print("\n💳 2. Multi-Crypto Payment Processor...")
        check_payment_processor(results)
        
        # 3. Check Database Payment Tables
        print("\n🗄️ 3. Payment Database Tables...")
        check_payment_database(results)
        
        # 4. Check Payment Configuration
        print("\n⚙️ 4. Payment Configuration...")
        check_payment_config(results)
        
        # 5. Check Payment Files
        print("\n📁 5. Payment System Files...")
        check_payment_files(results)
        
        # Generate report
        print("\n" + "=" * 50)
        print("📊 AUTOMATED PAYMENTS REPORT")
        print("=" * 50)
        
        print(f"✅ Passed: {len(results['passed'])}")
        print(f"❌ Failed: {len(results['failed'])}")
        print(f"⚠️ Warnings: {len(results['warnings'])}")
        
        if results['passed']:
            print(f"\n✅ PASSED TESTS:")
            for test in results['passed']:
                print(f"  • {test}")
        
        if results['failed']:
            print(f"\n❌ FAILED TESTS:")
            for test in results['failed']:
                print(f"  • {test}")
        
        if results['warnings']:
            print(f"\n⚠️ WARNINGS:")
            for warning in results['warnings']:
                print(f"  • {warning}")
        
        # Final status
        if not results['failed']:
            print(f"\n🎉 AUTOMATED PAYMENTS SYSTEM READY!")
            print("🚀 Payment monitoring can be started!")
            print("💡 Run: python3 payment_monitor.py")
            return True
        else:
            print(f"\n⚠️ Automated payments system has {len(results['failed'])} issues.")
            print("🔧 Some components need attention before starting.")
            return False
            
    except Exception as e:
        print(f"❌ Critical error during check: {e}")
        return False

def check_payment_monitor(results):
    """Check payment monitor service."""
    try:
        # Check payment_monitor.py
        monitor_path = 'payment_monitor.py'
        if os.path.exists(monitor_path):
            with open(monitor_path, 'r') as f:
                content = f.read()
            
            if 'PaymentMonitorService' in content:
                results['passed'].append("Payment monitor service exists")
            else:
                results['failed'].append("Payment monitor service class not found")
            
            if 'verify_payment_on_blockchain' in content:
                results['passed'].append("Payment verification method exists")
            else:
                results['failed'].append("Payment verification method missing")
            
            if 'asyncio.sleep(30)' in content:
                results['passed'].append("Payment monitoring interval set (30s)")
            else:
                results['warnings'].append("Payment monitoring interval not found")
        else:
            results['failed'].append("Payment monitor file not found")
        
        # Check scripts/payment_monitor.py
        scripts_monitor_path = 'scripts/payment_monitor.py'
        if os.path.exists(scripts_monitor_path):
            results['passed'].append("Alternative payment monitor exists")
        else:
            results['warnings'].append("Alternative payment monitor not found")
        
    except Exception as e:
        results['failed'].append(f"Payment monitor check failed: {e}")

def check_payment_processor(results):
    """Check multi-crypto payment processor."""
    try:
        # Check multi_crypto_payments.py
        processor_path = 'multi_crypto_payments.py'
        if os.path.exists(processor_path):
            with open(processor_path, 'r') as f:
                content = f.read()
            
            if 'MultiCryptoPaymentProcessor' in content:
                results['passed'].append("Multi-crypto payment processor exists")
            else:
                results['failed'].append("Multi-crypto payment processor class not found")
            
            # Check supported cryptocurrencies
            supported_cryptos = ['BTC', 'ETH', 'USDT', 'USDC', 'TON']
            for crypto in supported_cryptos:
                if crypto in content:
                    results['passed'].append(f"{crypto} payment support exists")
                else:
                    results['warnings'].append(f"{crypto} payment support not found")
            
            # Check verification methods
            verification_methods = [
                'verify_payment_on_blockchain',
                '_verify_direct_payment',
                '_verify_coinbase_payment'
            ]
            for method in verification_methods:
                if method in content:
                    results['passed'].append(f"Payment verification method '{method}' exists")
                else:
                    results['warnings'].append(f"Payment verification method '{method}' not found")
        else:
            results['failed'].append("Multi-crypto payment processor not found")
        
    except Exception as e:
        results['failed'].append(f"Payment processor check failed: {e}")

def check_payment_database(results):
    """Check payment database tables."""
    try:
        db_path = 'bot_database.db'
        if not os.path.exists(db_path):
            results['failed'].append("Database file not found")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check payment-related tables
        payment_tables = ['payments', 'subscriptions']
        for table in payment_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone():
                results['passed'].append(f"Payment table '{table}' exists")
            else:
                results['failed'].append(f"Payment table '{table}' missing")
        
        # Check payments table structure
        cursor.execute("PRAGMA table_info(payments)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = ['payment_id', 'user_id', 'amount', 'status', 'crypto_type']
        for column in required_columns:
            if column in columns:
                results['passed'].append(f"Payments table has '{column}' column")
            else:
                results['warnings'].append(f"Payments table missing '{column}' column")
        
        # Check for pending payments
        cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
        pending_count = cursor.fetchone()[0]
        if pending_count >= 0:
            results['passed'].append(f"Payments table accessible ({pending_count} pending payments)")
        else:
            results['failed'].append("Payments table not accessible")
        
        conn.close()
        
    except Exception as e:
        results['failed'].append(f"Payment database check failed: {e}")

def check_payment_config(results):
    """Check payment configuration."""
    try:
        # Check environment variables
        env_vars = [
            'TON_ADDRESS',
            'BTC_ADDRESS', 
            'ETH_ADDRESS',
            'SOL_ADDRESS',
            'LTC_ADDRESS'
        ]
        
        for var in env_vars:
            if os.getenv(var):
                results['passed'].append(f"Payment address configured: {var}")
            else:
                results['warnings'].append(f"Payment address not configured: {var}")
        
        # Check API keys (optional)
        api_keys = [
            'TON_API_KEY',
            'ETHERSCAN_API_KEY',
            'BLOCKCYPHER_API_KEY'
        ]
        
        for key in api_keys:
            if os.getenv(key):
                results['passed'].append(f"API key configured: {key}")
            else:
                results['warnings'].append(f"API key not configured: {key}")
        
        # Check config.py
        config_path = 'config.py'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
            
            if 'BotConfig' in content:
                results['passed'].append("Payment configuration file exists")
            else:
                results['warnings'].append("Payment configuration incomplete")
        else:
            results['failed'].append("Payment configuration file not found")
        
    except Exception as e:
        results['failed'].append(f"Payment config check failed: {e}")

def check_payment_files(results):
    """Check payment system files."""
    try:
        # Check payment-related files
        payment_files = [
            'payment_monitor.py',
            'multi_crypto_payments.py',
            'src/payments/payment_monitor.py',
            'src/services/payment_processor.py'
        ]
        
        for file_path in payment_files:
            if os.path.exists(file_path):
                results['passed'].append(f"Payment file exists: {file_path}")
            else:
                results['warnings'].append(f"Payment file not found: {file_path}")
        
        # Check recycle bin for additional payment files
        recycle_files = [
            'recycle_bin/multi_crypto_payments.py',
            'recycle_bin/enhanced_crypto_payments.py',
            'recycle_bin/ton_payments.py'
        ]
        
        for file_path in recycle_files:
            if os.path.exists(file_path):
                results['passed'].append(f"Payment backup exists: {file_path}")
            else:
                results['warnings'].append(f"Payment backup not found: {file_path}")
        
    except Exception as e:
        results['failed'].append(f"Payment files check failed: {e}")

if __name__ == "__main__":
    success = check_automated_payments()
    sys.exit(0 if success else 1)

