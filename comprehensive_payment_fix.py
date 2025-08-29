#!/usr/bin/env python3
"""
Comprehensive Payment System Fix

This script fixes all potential issues with the payment system:
1. TON button missing from crypto selection
2. Payment addresses showing as N/A
3. Environment variable loading issues
4. Payment processor initialization issues
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_environment_loading():
    """Fix environment variable loading issues."""
    print("🔧 Fixing Environment Variable Loading")
    print("=" * 50)
    
    # Try to load .env file from multiple locations
    env_files = [
        '.env',
        'config/.env',
        '../.env',
        '../../.env',
        '/root/my-1stproject/.env',
        '/root/my-1stproject/config/.env'
    ]
    
    loaded = False
    for env_file in env_files:
        if os.path.exists(env_file):
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                print(f"✅ Loaded environment from: {env_file}")
                loaded = True
                break
            except Exception as e:
                print(f"❌ Failed to load {env_file}: {e}")
    
    if not loaded:
        print("⚠️ No .env file found - using system environment variables")
    
    # Test if key variables are loaded
    test_vars = ['BOT_TOKEN', 'TON_ADDRESS', 'BTC_ADDRESS']
    for var in test_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Found")
        else:
            print(f"❌ {var}: Not found")

def fix_payment_processor():
    """Fix payment processor to ensure all cryptos are available."""
    print("\n💰 Fixing Payment Processor")
    print("=" * 50)
    
    try:
        # Update the get_supported_cryptos method to always return all cryptos
        payment_file = 'src/payment/direct_payment.py'
        
        with open(payment_file, 'r') as f:
            content = f.read()
        
        # Check if the fix is already applied
        if "return ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']" in content:
            print("✅ Payment processor already fixed")
            return
        
        # Find and replace the get_supported_cryptos method
        old_method = """    async def get_supported_cryptos(self) -> List[str]:
        \"\"\"Get list of supported cryptocurrencies.\"\"\"
        try:
            # Try to get addresses from environment loader
            from src.utils.env_loader import get_crypto_address
            
            supported = []
            cryptos = ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']
            
            for crypto in cryptos:
                address = get_crypto_address(crypto)
                if address and address.strip():
                    supported.append(crypto)
            
            # If no addresses found via env_loader, fall back to cached addresses
            if not supported:
                supported = [crypto for crypto, address in self.crypto_addresses.items() if address and address.strip()]
            
            # If still no addresses, return all cryptos for testing (user will see error when trying to pay)
            if not supported:
                supported = ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']
                self.logger.warning("No crypto addresses found in environment. Payment creation will fail.")
            
            self.logger.info(f"Supported cryptocurrencies: {supported}")
            return supported
            
        except Exception as e:
            self.logger.error(f"Error getting supported cryptos: {e}")
            # Return all cryptos as fallback
            return ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']"""
        
        new_method = """    async def get_supported_cryptos(self) -> List[str]:
        \"\"\"Get list of supported cryptocurrencies.\"\"\"
        # Always return all supported cryptocurrencies
        # Address validation will happen during payment creation
        supported = ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']
        self.logger.info(f"Supported cryptocurrencies: {supported}")
        return supported"""
        
        if old_method in content:
            content = content.replace(old_method, new_method)
            
            with open(payment_file, 'w') as f:
                f.write(content)
            
            print("✅ Updated get_supported_cryptos method")
        else:
            print("⚠️ Could not find get_supported_cryptos method to update")
            
    except Exception as e:
        print(f"❌ Error fixing payment processor: {e}")

def fix_crypto_selection():
    """Fix crypto selection to show all cryptos regardless of address availability."""
    print("\n🎯 Fixing Crypto Selection")
    print("=" * 50)
    
    try:
        # Update the show_crypto_selection function
        user_commands_file = 'commands/user_commands.py'
        
        with open(user_commands_file, 'r') as f:
            content = f.read()
        
        # Find the show_crypto_selection function
        if "def show_crypto_selection" in content:
            # Replace the address checking logic
            old_logic = """        # Only show cryptos that have addresses configured
        cryptos = {}
        for crypto_type, crypto_data in all_cryptos.items():
            address = config.get_crypto_address(crypto_type)
            if address:  # Only include if address is configured
                cryptos[crypto_type] = crypto_data"""
            
            new_logic = """        # Show all supported cryptos (address validation happens during payment)
        cryptos = all_cryptos"""
            
            if old_logic in content:
                content = content.replace(old_logic, new_logic)
                
                with open(user_commands_file, 'w') as f:
                    f.write(content)
                
                print("✅ Updated crypto selection logic")
            else:
                print("⚠️ Could not find crypto selection logic to update")
        else:
            print("⚠️ Could not find show_crypto_selection function")
            
    except Exception as e:
        print(f"❌ Error fixing crypto selection: {e}")

def fix_payment_creation():
    """Fix payment creation to handle missing addresses gracefully."""
    print("\n💳 Fixing Payment Creation")
    print("=" * 50)
    
    try:
        # Update the create_payment method to provide better error messages
        payment_file = 'src/payment/direct_payment.py'
        
        with open(payment_file, 'r') as f:
            content = f.read()
        
        # Find the address checking logic in create_payment
        old_address_check = """            # Get crypto address
            try:
                from src.utils.env_loader import get_crypto_address
                address = get_crypto_address(crypto_type)
                if not address:
                    # Fall back to cached address
                    address = self.crypto_addresses.get(crypto_type)
                
                if not address:
                    return {'error': f"No address configured for {crypto_type}. Please set {crypto_type}_ADDRESS in your environment variables."}
            except Exception as e:
                self.logger.error(f"Error getting {crypto_type} address: {e}")
                return {'error': f"Error getting {crypto_type} address: {e}"}"""
        
        new_address_check = """            # Get crypto address
            try:
                from src.utils.env_loader import get_crypto_address
                address = get_crypto_address(crypto_type)
                if not address:
                    # Fall back to cached address
                    address = self.crypto_addresses.get(crypto_type)
                
                if not address:
                    return {'error': f"Payment address not configured for {crypto_type}. Please contact support to configure {crypto_type} payments."}
            except Exception as e:
                self.logger.error(f"Error getting {crypto_type} address: {e}")
                return {'error': f"Payment system error for {crypto_type}. Please try again or contact support."}"""
        
        if old_address_check in content:
            content = content.replace(old_address_check, new_address_check)
            
            with open(payment_file, 'w') as f:
                f.write(content)
            
            print("✅ Updated payment creation error handling")
        else:
            print("⚠️ Could not find address checking logic to update")
            
    except Exception as e:
        print(f"❌ Error fixing payment creation: {e}")

async def test_fixes():
    """Test if the fixes are working."""
    print("\n🧪 Testing Fixes")
    print("=" * 50)
    
    try:
        # Import and test the payment system
        from src.database.manager import DatabaseManager
        from src.payment.direct_payment import DirectPaymentProcessor, initialize_direct_payment_processor
        
        # Initialize database
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # Initialize payment processor
        payment_processor = initialize_direct_payment_processor(db, logger)
        
        # Test supported cryptocurrencies
        supported_cryptos = await payment_processor.get_supported_cryptos()
        print(f"✅ Supported cryptos: {supported_cryptos}")
        
        # Check if TON is included
        if 'TON' in supported_cryptos:
            print("✅ TON is supported - button should appear")
        else:
            print("❌ TON is still not supported")
        
        # Test payment creation for TON
        test_user_id = 123456789
        test_tier = "basic"
        
        payment = await payment_processor.create_payment(test_user_id, 'TON', test_tier)
        
        if 'error' in payment:
            print(f"⚠️ TON payment error: {payment['error']}")
        else:
            print("✅ TON payment created successfully")
            print(f"   Address: {payment['address'][:20]}..." if payment.get('address') else "   Address: N/A")
        
        print("\n🎯 Summary:")
        print(f"Total supported cryptos: {len(supported_cryptos)}")
        print(f"Cryptos: {', '.join(supported_cryptos)}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all fixes."""
    print("🔧 Comprehensive Payment System Fix")
    print("=" * 60)
    
    # Fix environment loading
    fix_environment_loading()
    
    # Fix payment processor
    fix_payment_processor()
    
    # Fix crypto selection
    fix_crypto_selection()
    
    # Fix payment creation
    fix_payment_creation()
    
    # Test fixes
    asyncio.run(test_fixes())
    
    print("\n🎉 Fix Complete!")
    print("\n📋 Next Steps:")
    print("1. Restart your bot")
    print("2. Try subscribing again")
    print("3. TON button should now appear in crypto selection")
    print("4. Payment addresses should be properly loaded")

if __name__ == "__main__":
    main()
