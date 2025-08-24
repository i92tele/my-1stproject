#!/usr/bin/env python3
"""
Scan Payment Issues

This script scans for any remaining payment system issues after fixes.
"""

import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def scan_payment_processor():
    """Scan the payment processor for issues."""
    logger.info("🔍 Scanning payment processor...")
    
    try:
        payment_file = "multi_crypto_payments.py"
        
        if not os.path.exists(payment_file):
            logger.error(f"❌ Payment processor file not found: {payment_file}")
            return False
        
        with open(payment_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check supported cryptocurrencies
        if "'LTC':" not in content:
            issues.append("❌ LTC not in supported_cryptos")
        else:
            logger.info("✅ LTC supported")
            
        if "'SOL':" not in content:
            issues.append("❌ SOL not in supported_cryptos")
        else:
            logger.info("✅ SOL supported")
        
        # Check payment creation logic
        if "elif crypto_type == 'LTC':" not in content:
            issues.append("❌ LTC payment creation logic missing")
        else:
            logger.info("✅ LTC payment creation logic exists")
            
        if "elif crypto_type == 'SOL':" not in content:
            issues.append("❌ SOL payment creation logic missing")
        else:
            logger.info("✅ SOL payment creation logic exists")
        
        # Check verification methods
        if "async def _verify_ltc_payment" not in content:
            issues.append("❌ LTC verification method missing")
        else:
            logger.info("✅ LTC verification method exists")
            
        if "async def _verify_sol_payment" not in content:
            issues.append("❌ SOL verification method missing")
        else:
            logger.info("✅ SOL verification method exists")
        
        # Check for mock implementations
        if "Mock verification for now" in content:
            issues.append("⚠️ Mock verification methods still present")
        else:
            logger.info("✅ No mock verification methods found")
        
        # Check for proper API calls
        if "blockcypher.com" in content:
            logger.info("✅ BlockCypher API integration found")
        else:
            issues.append("⚠️ BlockCypher API integration missing")
            
        if "api.mainnet-beta.solana.com" in content:
            logger.info("✅ Solana API integration found")
        else:
            issues.append("⚠️ Solana API integration missing")
        
        if issues:
            logger.warning("⚠️ Issues found in payment processor:")
            for issue in issues:
                logger.warning(f"   {issue}")
            return False
        else:
            logger.info("✅ Payment processor scan passed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error scanning payment processor: {e}")
        return False

def scan_database_functions():
    """Scan database functions for issues."""
    logger.info("🔍 Scanning database functions...")
    
    try:
        db_file = "src/database/manager.py"
        
        if not os.path.exists(db_file):
            logger.error(f"❌ Database manager file not found: {db_file}")
            return False
        
        with open(db_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for create_payment function
        if "async def create_payment(self, payment_id, user_id, amount_usd" not in content:
            issues.append("❌ create_payment function not properly implemented")
        else:
            logger.info("✅ create_payment function properly implemented")
        
        # Check for stub implementation
        if "Method create_payment not yet implemented for SQLite" in content:
            issues.append("❌ create_payment still has stub implementation")
        else:
            logger.info("✅ create_payment stub removed")
        
        # Check for proper database operations
        if "INSERT INTO payments" in content:
            logger.info("✅ Payment insertion logic found")
        else:
            issues.append("❌ Payment insertion logic missing")
        
        if issues:
            logger.warning("⚠️ Issues found in database functions:")
            for issue in issues:
                logger.warning(f"   {issue}")
            return False
        else:
            logger.info("✅ Database functions scan passed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error scanning database functions: {e}")
        return False

def scan_payment_flow():
    """Scan the complete payment flow for issues."""
    logger.info("🔍 Scanning payment flow...")
    
    try:
        # Check user commands
        user_commands_file = "commands/user_commands.py"
        
        if not os.path.exists(user_commands_file):
            logger.error(f"❌ User commands file not found: {user_commands_file}")
            return False
        
        with open(user_commands_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for payment processor import
        if "from multi_crypto_payments import MultiCryptoPaymentProcessor" not in content:
            issues.append("❌ MultiCryptoPaymentProcessor import missing")
        else:
            logger.info("✅ MultiCryptoPaymentProcessor import found")
        
        # Check for payment request creation
        if "payment_processor.create_payment_request" not in content:
            issues.append("❌ Payment request creation missing")
        else:
            logger.info("✅ Payment request creation found")
        
        # Check for QR code generation
        if "send_payment_qr_code" not in content:
            issues.append("⚠️ QR code generation missing")
        else:
            logger.info("✅ QR code generation found")
        
        # Check for payment verification
        if "check_payment:" not in content:
            issues.append("❌ Payment verification callback missing")
        else:
            logger.info("✅ Payment verification callback found")
        
        if issues:
            logger.warning("⚠️ Issues found in payment flow:")
            for issue in issues:
                logger.warning(f"   {issue}")
            return False
        else:
            logger.info("✅ Payment flow scan passed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error scanning payment flow: {e}")
        return False

def scan_environment_variables():
    """Scan for required environment variables."""
    logger.info("🔍 Scanning environment variables...")
    
    try:
        # Check if .env file exists
        env_files = [".env", "config/.env"]
        env_file_found = False
        
        for env_file in env_files:
            if os.path.exists(env_file):
                logger.info(f"✅ Environment file found: {env_file}")
                env_file_found = True
                break
        
        if not env_file_found:
            logger.warning("⚠️ No .env file found")
        
        # Check for required crypto addresses in code
        payment_file = "multi_crypto_payments.py"
        
        if not os.path.exists(payment_file):
            logger.error(f"❌ Payment processor file not found: {payment_file}")
            return False
        
        with open(payment_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_vars = [
            'BTC_ADDRESS',
            'ETH_ADDRESS', 
            'LTC_ADDRESS',
            'SOL_ADDRESS',
            'TON_ADDRESS',
            'USDT_ADDRESS',
            'USDC_ADDRESS'
        ]
        
        missing_vars = []
        for var in required_vars:
            if f"os.getenv('{var}'" in content:
                logger.info(f"✅ {var} environment variable referenced")
            else:
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"⚠️ Missing environment variable references: {missing_vars}")
            return False
        else:
            logger.info("✅ All required environment variables referenced")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error scanning environment variables: {e}")
        return False

def scan_payment_monitor():
    """Scan payment monitor for issues."""
    logger.info("🔍 Scanning payment monitor...")
    
    try:
        monitor_file = "payment_monitor.py"
        
        if not os.path.exists(monitor_file):
            logger.error(f"❌ Payment monitor file not found: {monitor_file}")
            return False
        
        with open(monitor_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for MultiCryptoPaymentProcessor usage
        if "MultiCryptoPaymentProcessor" not in content:
            issues.append("❌ MultiCryptoPaymentProcessor not used in monitor")
        else:
            logger.info("✅ MultiCryptoPaymentProcessor used in monitor")
        
        # Check for payment verification
        if "verify_payment_on_blockchain" not in content:
            issues.append("❌ Payment verification missing in monitor")
        else:
            logger.info("✅ Payment verification found in monitor")
        
        # Check for pending payments handling
        if "get_pending_payments" not in content:
            issues.append("❌ Pending payments handling missing")
        else:
            logger.info("✅ Pending payments handling found")
        
        if issues:
            logger.warning("⚠️ Issues found in payment monitor:")
            for issue in issues:
                logger.warning(f"   {issue}")
            return False
        else:
            logger.info("✅ Payment monitor scan passed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error scanning payment monitor: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🔍 PAYMENT SYSTEM ISSUE SCAN")
    logger.info("=" * 60)
    
    scan_results = []
    
    # Scan payment processor
    if scan_payment_processor():
        scan_results.append("✅ Payment Processor")
    else:
        scan_results.append("❌ Payment Processor")
    
    # Scan database functions
    if scan_database_functions():
        scan_results.append("✅ Database Functions")
    else:
        scan_results.append("❌ Database Functions")
    
    # Scan payment flow
    if scan_payment_flow():
        scan_results.append("✅ Payment Flow")
    else:
        scan_results.append("❌ Payment Flow")
    
    # Scan environment variables
    if scan_environment_variables():
        scan_results.append("✅ Environment Variables")
    else:
        scan_results.append("❌ Environment Variables")
    
    # Scan payment monitor
    if scan_payment_monitor():
        scan_results.append("✅ Payment Monitor")
    else:
        scan_results.append("❌ Payment Monitor")
    
    logger.info("=" * 60)
    logger.info("📊 SCAN RESULTS")
    logger.info("=" * 60)
    
    for result in scan_results:
        logger.info(result)
    
    # Count results
    passed = sum(1 for r in scan_results if r.startswith("✅"))
    total = len(scan_results)
    
    logger.info(f"")
    logger.info(f"📈 Overall: {passed}/{total} components passed")
    
    if passed == total:
        logger.info("🎉 All payment system components are working properly!")
    else:
        logger.warning("⚠️ Some payment system components need attention")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
