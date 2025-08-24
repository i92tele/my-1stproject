#!/usr/bin/env python3
"""
Fix Payment Address Display

This script specifically fixes the issue where the payment address is showing as N/A
in the payment UI. It directly modifies the relevant handlers to ensure the address
is properly retrieved and displayed.
"""

import asyncio
import logging
import os
import sys
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def fix_subscription_handler():
    """Find and fix the subscription handler that creates payment messages."""
    logger.info("🔧 FIXING SUBSCRIPTION HANDLER")
    
    # First, find the subscription handler file
    subscription_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if 'subscription' in file.lower() and file.endswith('.py'):
                subscription_files.append(os.path.join(root, file))
    
    if not subscription_files:
        logger.error("❌ Could not find subscription handler file")
        return False
    
    logger.info(f"Found subscription files: {subscription_files}")
    
    # Try to fix each file
    fixed = False
    for file_path in subscription_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Look for payment message creation
            if "Payment ID:" in content and "Send to:" in content:
                # This is likely the file with the payment message
                
                # Check if it's already using the address
                if "Send to: {payment['address']}" in content or "Send to: {address}" in content:
                    logger.info(f"✅ {file_path} already using address correctly")
                    continue
                
                # Find the payment message section
                payment_message_match = re.search(r'(["\']).*?Send to:.*?\1', content, re.DOTALL)
                if payment_message_match:
                    old_message = payment_message_match.group(0)
                    
                    # Replace "Send to: N/A" with "Send to: {address}" or similar
                    if "Send to: N/A" in old_message:
                        new_message = old_message.replace("Send to: N/A", "Send to: {address}")
                        updated_content = content.replace(old_message, new_message)
                        
                        # Also ensure we're getting the address from the payment
                        address_var_pattern = r'address\s*=\s*["\']N/A["\']'
                        if re.search(address_var_pattern, updated_content):
                            updated_content = re.sub(
                                address_var_pattern,
                                "address = payment.get('address', os.getenv('BTC_ADDRESS', 'N/A'))",
                                updated_content
                            )
                        
                        # Write the updated content
                        with open(file_path, 'w') as f:
                            f.write(updated_content)
                        
                        logger.info(f"✅ Fixed payment message in {file_path}")
                        fixed = True
                    else:
                        logger.info(f"⚠️ Could not find 'Send to: N/A' in {file_path}")
                else:
                    logger.info(f"⚠️ Could not find payment message section in {file_path}")
            
            # Look for payment creation
            if "create_payment" in content and "payment_id" in content:
                # This file likely creates payments
                
                # Check if it's already retrieving the address
                if "BTC_ADDRESS" in content or "crypto_address" in content:
                    logger.info(f"✅ {file_path} already retrieving address")
                    continue
                
                # Find the payment creation section
                payment_creation_match = re.search(r'async def .*?create_payment.*?\(.*?\).*?:.*?return', content, re.DOTALL)
                if payment_creation_match:
                    payment_creation = payment_creation_match.group(0)
                    
                    # Add address retrieval before return
                    if "return {" in payment_creation:
                        # Find the return statement
                        return_match = re.search(r'return\s*{.*?}', payment_creation, re.DOTALL)
                        if return_match:
                            return_stmt = return_match.group(0)
                            
                            # Check if address is already in return
                            if "'address':" in return_stmt:
                                logger.info(f"✅ {file_path} already returning address")
                                continue
                            
                            # Add address to return statement
                            new_return = return_stmt.replace(
                                "return {",
                                "# Get crypto address\n        address = os.getenv('BTC_ADDRESS', '')\n        return {"
                            )
                            new_return = new_return.replace(
                                "}",
                                ", 'address': address}"
                            )
                            
                            updated_content = content.replace(return_stmt, new_return)
                            
                            # Ensure os is imported
                            if "import os" not in updated_content:
                                updated_content = "import os\n" + updated_content
                            
                            # Write the updated content
                            with open(file_path, 'w') as f:
                                f.write(updated_content)
                            
                            logger.info(f"✅ Fixed payment creation in {file_path}")
                            fixed = True
                        else:
                            logger.info(f"⚠️ Could not find return statement in {file_path}")
                    else:
                        logger.info(f"⚠️ Could not find return statement in {file_path}")
                else:
                    logger.info(f"⚠️ Could not find payment creation section in {file_path}")
        except Exception as e:
            logger.error(f"❌ Error fixing {file_path}: {e}")
    
    return fixed

async def fix_payment_processor():
    """Fix the payment processor to ensure it's returning the address."""
    logger.info("\n🔧 FIXING PAYMENT PROCESSOR")
    
    try:
        # Check if the file exists
        if not os.path.exists('src/services/payment_processor.py'):
            logger.error("❌ src/services/payment_processor.py not found")
            return False
        
        # Read the current file
        with open('src/services/payment_processor.py', 'r') as f:
            content = f.read()
        
        # Check if we need to update the file
        if "async def create_payment_request" in content and "return {" in content:
            # Find the create_payment_request method
            method_match = re.search(r'async def create_payment_request.*?return {.*?}', content, re.DOTALL)
            if method_match:
                method = method_match.group(0)
                
                # Check if address is already in return
                if "'address':" in method:
                    logger.info("✅ Payment processor already returning address")
                    return False
                
                # Add address to return statement
                return_match = re.search(r'return\s*{.*?}', method, re.DOTALL)
                if return_match:
                    return_stmt = return_match.group(0)
                    
                    new_return = return_stmt.replace(
                        "return {",
                        "return {\n                'address': self.merchant_wallet,"
                    )
                    
                    updated_content = content.replace(return_stmt, new_return)
                    
                    # Write the updated content
                    with open('src/services/payment_processor.py', 'w') as f:
                        f.write(updated_content)
                    
                    logger.info("✅ Fixed payment processor return value")
                    return True
                else:
                    logger.error("❌ Could not find return statement in create_payment_request")
                    return False
            else:
                logger.error("❌ Could not find create_payment_request method")
                return False
        else:
            logger.info("✅ Payment processor doesn't need updating")
            return False
    except Exception as e:
        logger.error(f"❌ Error fixing payment processor: {e}")
        return False

async def create_direct_fix():
    """Create a direct fix for the payment address display."""
    logger.info("\n🔧 CREATING DIRECT FIX")
    
    try:
        # Create a direct fix file that can be imported
        with open('src/payment_address_fix.py', 'w') as f:
            f.write("""#!/usr/bin/env python3
\"\"\"
Payment Address Fix

This module provides a direct fix for the payment address display issue.
\"\"\"

import os
import logging

logger = logging.getLogger(__name__)

def get_crypto_address(crypto_type):
    \"\"\"Get cryptocurrency address from environment variables.\"\"\"
    crypto_type = crypto_type.upper()
    
    # Map crypto types to environment variable names
    crypto_map = {
        'BTC': 'BTC_ADDRESS',
        'ETH': 'ETH_ADDRESS',
        'USDT': 'USDT_ADDRESS',
        'USDC': 'USDC_ADDRESS',
        'LTC': 'LTC_ADDRESS',
        'SOL': 'SOL_ADDRESS',
        'TON': 'TON_ADDRESS'
    }
    
    env_var = crypto_map.get(crypto_type)
    if not env_var:
        logger.warning(f"Unknown cryptocurrency: {crypto_type}")
        return None
    
    address = os.getenv(env_var)
    if not address:
        logger.warning(f"No address configured for {crypto_type} ({env_var})")
        return None
    
    logger.info(f"Retrieved {crypto_type} address: {address[:10]}...")
    return address

def fix_payment_data(payment_data):
    \"\"\"Fix payment data to include address.\"\"\"
    if not payment_data:
        return payment_data
    
    # If address is missing, add it
    if 'address' not in payment_data and 'crypto_type' in payment_data:
        crypto_type = payment_data.get('crypto_type', 'BTC')
        address = get_crypto_address(crypto_type)
        if address:
            payment_data['address'] = address
    
    # If payment_url is missing, create it
    if 'payment_url' not in payment_data and 'address' in payment_data and 'amount_crypto' in payment_data:
        crypto_type = payment_data.get('crypto_type', 'BTC').lower()
        address = payment_data['address']
        amount = payment_data['amount_crypto']
        
        if crypto_type == 'btc':
            payment_data['payment_url'] = f"bitcoin:{address}?amount={amount}"
        elif crypto_type == 'eth':
            payment_data['payment_url'] = f"ethereum:{address}?value={amount}"
        elif crypto_type == 'ltc':
            payment_data['payment_url'] = f"litecoin:{address}?amount={amount}"
        elif crypto_type == 'sol':
            payment_data['payment_url'] = f"solana:{address}?amount={amount}"
        elif crypto_type == 'ton':
            payment_data['payment_url'] = f"ton://transfer/{address}?amount={amount}"
        else:
            payment_data['payment_url'] = f"crypto:{crypto_type}:{address}?amount={amount}"
    
    return payment_data

# Print environment variables for debugging (only crypto address prefixes)
for var in ['BTC_ADDRESS', 'ETH_ADDRESS', 'USDT_ADDRESS', 'USDC_ADDRESS', 'LTC_ADDRESS', 'SOL_ADDRESS', 'TON_ADDRESS']:
    value = os.getenv(var)
    if value:
        logger.info(f"{var} is set: {value[:10]}...")
    else:
        logger.warning(f"{var} is not set")
""")
        
        logger.info("✅ Created payment_address_fix.py")
        
        # Look for subscription command files to update
        subscription_files = []
        for root, dirs, files in os.walk('src'):
            for file in files:
                if ('subscription' in file.lower() or 'payment' in file.lower()) and file.endswith('.py'):
                    subscription_files.append(os.path.join(root, file))
        
        # Update each file to import and use the fix
        for file_path in subscription_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check if the file needs updating
                if "from src.payment_address_fix import" not in content:
                    # Add import
                    updated_content = "from src.payment_address_fix import fix_payment_data, get_crypto_address\n" + content
                    
                    # Look for places where payment data is used
                    if "payment = await" in updated_content and "payment_id" in updated_content:
                        # Add fix after payment creation
                        updated_content = updated_content.replace(
                            "payment = await",
                            "payment_raw = await"
                        )
                        updated_content = updated_content.replace(
                            "payment_raw = await",
                            "payment_raw = await",
                            1  # Only replace the first occurrence
                        )
                        
                        # Add fix after payment creation
                        payment_patterns = [
                            r"payment_raw = await .*?\n",
                            r"payment_raw = await .*?$"
                        ]
                        
                        for pattern in payment_patterns:
                            match = re.search(pattern, updated_content)
                            if match:
                                payment_line = match.group(0)
                                new_line = payment_line + "        payment = fix_payment_data(payment_raw)\n"
                                updated_content = updated_content.replace(payment_line, new_line)
                                break
                    
                    # Write the updated content
                    with open(file_path, 'w') as f:
                        f.write(updated_content)
                    
                    logger.info(f"✅ Updated {file_path} to use payment address fix")
                else:
                    logger.info(f"✅ {file_path} already using payment address fix")
            except Exception as e:
                logger.error(f"❌ Error updating {file_path}: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error creating direct fix: {e}")
        return False

async def check_env_variables():
    """Check if environment variables are set."""
    logger.info("\n🔧 CHECKING ENVIRONMENT VARIABLES")
    
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
    for var in crypto_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var} is set: {value[:10]}...")
        else:
            logger.warning(f"⚠️ {var} is not set")
    
    return True

async def main():
    """Main function."""
    logger.info("🔧 PAYMENT ADDRESS DISPLAY FIX")
    logger.info("=" * 60)
    
    # Check environment variables
    env_checked = await check_env_variables()
    
    # Fix subscription handler
    subscription_fixed = await fix_subscription_handler()
    
    # Fix payment processor
    processor_fixed = await fix_payment_processor()
    
    # Create direct fix
    direct_fixed = await create_direct_fix()
    
    # Summary
    logger.info("\n📋 FIX SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Environment Variables: {'✅ Checked' if env_checked else '❌ Failed'}")
    logger.info(f"Subscription Handler: {'✅ Fixed' if subscription_fixed else '⚠️ Not Found/Fixed'}")
    logger.info(f"Payment Processor: {'✅ Fixed' if processor_fixed else '⚠️ Not Found/Fixed'}")
    logger.info(f"Direct Fix: {'✅ Created' if direct_fixed else '❌ Failed'}")
    
    if subscription_fixed or processor_fixed or direct_fixed:
        logger.info("\n✅ PAYMENT ADDRESS DISPLAY FIXED")
        logger.info("Restart the bot to apply changes")
    else:
        logger.warning("\n⚠️ PAYMENT ADDRESS DISPLAY FIX INCOMPLETE")
        logger.warning("Check the logs for details")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
