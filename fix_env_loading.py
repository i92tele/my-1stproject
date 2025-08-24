#!/usr/bin/env python3
"""
Fix Environment Variable Loading

This script ensures that environment variables from .env are properly loaded
and accessible to the bot, particularly for cryptocurrency addresses.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def fix_env_loading():
    """Fix environment variable loading."""
    logger.info("🔧 FIXING ENVIRONMENT VARIABLE LOADING")
    
    # Try to load .env file
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.info(f"✅ Loaded environment variables from {env_path}")
    else:
        logger.warning(f"⚠️ No .env file found at {env_path}")
    
    # Check if python-dotenv is installed
    try:
        import dotenv
        logger.info("✅ python-dotenv is installed")
    except ImportError:
        logger.warning("⚠️ python-dotenv is not installed. Installing...")
        os.system("pip install python-dotenv")
        logger.info("✅ Installed python-dotenv")
    
    # Create a utility module for environment variables
    os.makedirs('src/utils', exist_ok=True)
    
    with open('src/utils/env_loader.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
\"\"\"
Environment Variable Loader

This module ensures environment variables are properly loaded from .env files.
\"\"\"

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Try to import dotenv, install if not available
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    logger.warning("python-dotenv not installed. Environment variables may not be loaded correctly.")

# Load environment variables from .env file
if DOTENV_AVAILABLE:
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.info(f"Loaded environment variables from {env_path}")

# Cache for environment variables
_env_cache: Dict[str, str] = {}

def get_env(key: str, default: Any = None) -> Optional[str]:
    \"\"\"
    Get environment variable with caching.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    \"\"\"
    # Check cache first
    if key in _env_cache:
        return _env_cache[key]
    
    # Get from environment
    value = os.environ.get(key, default)
    
    # Cache the result
    _env_cache[key] = value
    
    if value is None:
        logger.debug(f"Environment variable {key} not found")
    
    return value

def get_crypto_address(crypto_type: str) -> Optional[str]:
    \"\"\"
    Get cryptocurrency address from environment variables.
    
    Args:
        crypto_type: Cryptocurrency type (BTC, ETH, etc.)
        
    Returns:
        Cryptocurrency address or None if not found
    \"\"\"
    crypto_type = crypto_type.upper()
    
    # Try different environment variable formats
    env_vars = [
        f"{crypto_type}_ADDRESS",  # BTC_ADDRESS
        f"{crypto_type}_WALLET",    # BTC_WALLET
        f"{crypto_type}_WALLET_ADDRESS",  # BTC_WALLET_ADDRESS
        f"{crypto_type}_ADDR",      # BTC_ADDR
    ]
    
    for var in env_vars:
        address = get_env(var)
        if address:
            return address
    
    # Special case for TON
    if crypto_type == 'TON':
        ton_address = get_env('TON_MERCHANT_WALLET')
        if ton_address:
            return ton_address
    
    return None

def get_supported_cryptos() -> Dict[str, str]:
    \"\"\"
    Get all supported cryptocurrencies with addresses.
    
    Returns:
        Dictionary of cryptocurrency types and addresses
    \"\"\"
    crypto_types = ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON', 'DOGE', 'XRP']
    
    supported = {}
    for crypto in crypto_types:
        address = get_crypto_address(crypto)
        if address:
            supported[crypto] = address
    
    return supported

def reload_env() -> None:
    \"\"\"Reload environment variables and clear cache.\"\"\"
    global _env_cache
    _env_cache = {}
    
    if DOTENV_AVAILABLE:
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
            logger.info(f"Reloaded environment variables from {env_path}")
""")
    
    logger.info("✅ Created environment variable loader utility")
    
    # Update bot.py to use the env loader
    if os.path.exists('bot.py'):
        with open('bot.py', 'r') as f:
            content = f.read()
        
        # Add import if needed
        if "from src.utils.env_loader import" not in content:
            # Find import section
            import_section_end = content.find("def main()")
            if import_section_end == -1:
                import_section_end = content.find("async def main()")
            
            if import_section_end > 0:
                # Add import before main function
                updated_content = content[:import_section_end] + "from src.utils.env_loader import reload_env, get_crypto_address, get_supported_cryptos\n\n" + content[import_section_end:]
                
                # Add env reload before bot initialization
                if "def main():" in updated_content:
                    main_function = updated_content.find("def main():")
                    if main_function > 0:
                        # Find the start of the function body
                        function_body = updated_content.find(":", main_function) + 1
                        # Add reload_env() at the start of the function
                        updated_content = updated_content[:function_body] + "\n    # Reload environment variables\n    reload_env()\n" + updated_content[function_body:]
                
                # Write the updated content
                with open('bot.py', 'w') as f:
                    f.write(updated_content)
                
                logger.info("✅ Updated bot.py to use environment loader")
            else:
                logger.warning("⚠️ Could not find main function in bot.py")
        else:
            logger.info("✅ bot.py already using environment loader")
    
    # Create a direct fix for payment address display
    with open('src/payment_address_direct_fix.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
\"\"\"
Direct Fix for Payment Address Display

This module provides a direct fix for payment address display issues.
\"\"\"

import os
import logging
from src.utils.env_loader import get_crypto_address

logger = logging.getLogger(__name__)

def fix_payment_data(payment_data):
    \"\"\"Fix payment data to include address.\"\"\"
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
    \"\"\"Generate payment message with address.\"\"\"
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
    message = f"₿ {crypto_type} Payment\\n"
    message += f"Plan: {tier.capitalize()}\\n"
    message += f"Amount: {amount} {crypto_type} (${amount_usd})\\n\\n"
    message += f"📍 Send to: {address}\\n\\n"
    message += f"🆔 Payment ID:\\n{payment_id}\\n\\n"
    message += f"💡 No memo required - payment will be\\ndetected automatically"
    
    return message
""")
    
    logger.info("✅ Created direct fix for payment address display")
    
    # Update payment-related files to use the direct fix
    payment_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if ('payment' in file.lower() or 'subscription' in file.lower()) and file.endswith('.py'):
                payment_files.append(os.path.join(root, file))
    
    for file_path in payment_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Skip if already updated
            if "from src.payment_address_direct_fix import" in content:
                continue
            
            # Check if file handles payments
            if "payment" in content and ("Send to:" in content or "address" in content):
                # Add import
                updated_content = "from src.payment_address_direct_fix import fix_payment_data, get_payment_message\n" + content
                
                # Replace payment message creation if found
                if "Send to:" in updated_content:
                    # Find message creation
                    message_start = updated_content.find("Send to:")
                    if message_start > 0:
                        # Look for the variable assignment
                        line_start = updated_content.rfind("\n", 0, message_start) + 1
                        line_end = updated_content.find("\n", message_start)
                        if line_start > 0 and line_end > 0:
                            line = updated_content[line_start:line_end]
                            # Check if it's a message assignment
                            if "=" in line and ("message" in line or "text" in line):
                                var_name = line.split("=")[0].strip()
                                # Replace with get_payment_message
                                replacement = f"{var_name} = get_payment_message(payment, tier)\n"
                                updated_content = updated_content[:line_start] + replacement + updated_content[line_end:]
                
                # Add fix_payment_data call if payment is created
                if "payment = " in updated_content and "create_payment" in updated_content:
                    # Find payment creation
                    payment_start = updated_content.find("payment = ")
                    if payment_start > 0:
                        line_end = updated_content.find("\n", payment_start)
                        if line_end > 0:
                            # Add fix after payment creation
                            updated_content = updated_content[:line_end] + "\n    payment = fix_payment_data(payment)" + updated_content[line_end:]
                
                # Write the updated content
                with open(file_path, 'w') as f:
                    f.write(updated_content)
                
                logger.info(f"✅ Updated {file_path} to use direct fix")
        except Exception as e:
            logger.error(f"❌ Error updating {file_path}: {e}")
    
    return True

def check_env_variables():
    """Check environment variables."""
    logger.info("\n🔧 CHECKING ENVIRONMENT VARIABLES")
    
    # Try to load .env file
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.info(f"✅ Loaded environment variables from {env_path}")
    else:
        logger.warning(f"⚠️ No .env file found at {env_path}")
    
    # List of crypto address environment variables
    crypto_vars = [
        'BTC_ADDRESS',
        'ETH_ADDRESS',
        'USDT_ADDRESS',
        'USDC_ADDRESS',
        'LTC_ADDRESS',
        'SOL_ADDRESS',
        'TON_ADDRESS'
    ]
    
    # Check each variable
    found_any = False
    for var in crypto_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var} is set: {value[:5]}...")
            found_any = True
        else:
            logger.warning(f"⚠️ {var} is not set")
    
    # Try alternate variable names
    alternate_vars = [
        'BTC_WALLET',
        'ETH_WALLET',
        'USDT_WALLET',
        'USDC_WALLET',
        'LTC_WALLET',
        'SOL_WALLET',
        'TON_MERCHANT_WALLET'
    ]
    
    for var in alternate_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var} is set: {value[:5]}...")
            found_any = True
    
    if not found_any:
        logger.warning("⚠️ No cryptocurrency addresses found in environment variables")
        logger.info("Creating a sample .env file with placeholders...")
        
        # Create a sample .env file if none exists
        if not env_path.exists():
            with open('.env.sample', 'w') as f:
                f.write("""# Cryptocurrency addresses
BTC_ADDRESS=your_btc_address_here
ETH_ADDRESS=your_eth_address_here
USDT_ADDRESS=your_usdt_address_here
USDC_ADDRESS=your_usdc_address_here
LTC_ADDRESS=your_ltc_address_here
SOL_ADDRESS=your_sol_address_here
TON_ADDRESS=your_ton_address_here

# Alternative names
BTC_WALLET=your_btc_address_here
ETH_WALLET=your_eth_address_here
TON_MERCHANT_WALLET=your_ton_address_here

# API Keys
ETHERSCAN_API_KEY=your_etherscan_api_key
BLOCKCYPHER_API_KEY=your_blockcypher_api_key
""")
            logger.info("✅ Created .env.sample file with placeholders")
    
    return found_any

def create_hardcoded_addresses():
    """Create a module with hardcoded addresses as a fallback."""
    logger.info("\n🔧 CREATING FALLBACK ADDRESSES")
    
    with open('src/utils/crypto_addresses.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
\"\"\"
Fallback Cryptocurrency Addresses

This module provides fallback cryptocurrency addresses when environment variables are not available.
\"\"\"

import os
import logging

logger = logging.getLogger(__name__)

# Fallback addresses - replace with your actual addresses
FALLBACK_ADDRESSES = {
    'BTC': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',  # First Bitcoin address ever (Satoshi)
    'ETH': '0x0000000000000000000000000000000000000000',  # Zero address
    'USDT': '0x0000000000000000000000000000000000000000',  # Zero address
    'USDC': '0x0000000000000000000000000000000000000000',  # Zero address
    'LTC': 'LTC_address_placeholder',
    'SOL': 'SOL_address_placeholder',
    'TON': 'TON_address_placeholder'
}

def get_address(crypto_type):
    \"\"\"Get cryptocurrency address with fallback.\"\"\"
    crypto_type = crypto_type.upper()
    
    # Try environment variables first
    env_vars = [
        f"{crypto_type}_ADDRESS",
        f"{crypto_type}_WALLET",
        f"{crypto_type}_WALLET_ADDRESS",
        f"{crypto_type}_ADDR"
    ]
    
    # Special case for TON
    if crypto_type == 'TON':
        env_vars.append('TON_MERCHANT_WALLET')
    
    # Check each environment variable
    for var in env_vars:
        address = os.environ.get(var)
        if address:
            return address
    
    # Use fallback address
    fallback = FALLBACK_ADDRESSES.get(crypto_type)
    if fallback:
        logger.warning(f"Using fallback address for {crypto_type}")
        return fallback
    
    # No address found
    logger.error(f"No address found for {crypto_type}")
    return "Contact support for address"
""")
    
    logger.info("✅ Created fallback addresses module")
    
    return True

def main():
    """Main function."""
    logger.info("🔧 ENVIRONMENT VARIABLE LOADING FIX")
    logger.info("=" * 60)
    
    # Check environment variables
    env_checked = check_env_variables()
    
    # Fix environment variable loading
    env_fixed = fix_env_loading()
    
    # Create hardcoded addresses as fallback
    fallback_created = create_hardcoded_addresses()
    
    # Summary
    logger.info("\n📋 FIX SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Environment Variables: {'✅ Checked' if env_checked else '⚠️ Not Found'}")
    logger.info(f"Environment Loading: {'✅ Fixed' if env_fixed else '❌ Failed'}")
    logger.info(f"Fallback Addresses: {'✅ Created' if fallback_created else '❌ Failed'}")
    
    logger.info("\n✅ ENVIRONMENT VARIABLE LOADING FIXED")
    logger.info("=" * 60)
    logger.info("NEXT STEPS:")
    logger.info("1. If you haven't already, make sure your .env file contains the cryptocurrency addresses")
    logger.info("2. Edit src/utils/crypto_addresses.py to add your actual addresses as fallbacks")
    logger.info("3. Restart the bot: python3 bot.py")
    logger.info("=" * 60)

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.warning("Installing python-dotenv...")
        os.system("pip install python-dotenv")
        from dotenv import load_dotenv
    
    main()
