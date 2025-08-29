#!/usr/bin/env python3
"""
Payment Detection Diagnostic
Check why payments aren't being automatically detected
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PaymentDetectionDiagnostic:
    """Diagnose payment detection issues."""
    
    def __init__(self):
        self.test_results = {}
    
    async def run_diagnostic(self):
        """Run comprehensive payment detection diagnostic."""
        print("🔍 PAYMENT DETECTION DIAGNOSTIC")
        print("=" * 50)
        
        # Test 1: Database connection and pending payments
        await self.test_database_pending_payments()
        
        # Test 2: Payment processor initialization
        await self.test_payment_processor()
        
        # Test 3: Background verification task
        await self.test_background_verification()
        
        # Test 4: Payment monitor service
        await self.test_payment_monitor()
        
        # Test 5: Manual payment verification
        await self.test_manual_verification()
        
        # Generate report
        self.generate_diagnostic_report()
    
    async def test_database_pending_payments(self):
        """Test database pending payments query."""
        print("\n1️⃣ Database Pending Payments Test")
        print("-" * 40)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Test get_pending_payments method
            pending_payments = await db.get_pending_payments(age_limit_minutes=1440)  # 24 hours
            
            print(f"✅ Database connected successfully")
            print(f"📊 Pending payments found: {len(pending_payments)}")
            
            if pending_payments:
                print("📋 Pending payments details:")
                for payment in pending_payments[:3]:  # Show first 3
                    print(f"  - ID: {payment['payment_id']}")
                    print(f"    Status: {payment['status']}")
                    print(f"    Crypto: {payment['crypto_type']}")
                    print(f"    Amount: {payment['expected_amount_crypto']} {payment['crypto_type']}")
                    print(f"    Created: {payment['created_at']}")
                    print(f"    Expires: {payment['expires_at']}")
                    print()
            else:
                print("⚠️ No pending payments found in database")
            
            await db.close()
            self.test_results['database'] = True
            
        except Exception as e:
            print(f"❌ Database test failed: {e}")
            self.test_results['database'] = False
    
    async def test_payment_processor(self):
        """Test payment processor initialization."""
        print("\n2️⃣ Payment Processor Test")
        print("-" * 40)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            from multi_crypto_payments import MultiCryptoPaymentProcessor
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            processor = MultiCryptoPaymentProcessor(config, db, logger)
            print("✅ Payment processor initialized successfully")
            
            # Check if background verification method exists
            if hasattr(processor, '_background_payment_verification'):
                print("✅ Background verification method available")
                self.test_results['payment_processor'] = True
            else:
                print("❌ Background verification method not found")
                self.test_results['payment_processor'] = False
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Payment processor test failed: {e}")
            self.test_results['payment_processor'] = False
    
    async def test_background_verification(self):
        """Test background verification task."""
        print("\n3️⃣ Background Verification Test")
        print("-" * 40)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            from multi_crypto_payments import MultiCryptoPaymentProcessor
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            processor = MultiCryptoPaymentProcessor(config, db, logger)
            
            # Test background verification method directly
            print("🧪 Testing background verification method...")
            
            # Create a test task
            task = asyncio.create_task(processor._background_payment_verification())
            
            # Let it run for a few seconds
            await asyncio.sleep(3)
            
            # Cancel the task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            print("✅ Background verification method executed successfully")
            self.test_results['background_verification'] = True
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Background verification test failed: {e}")
            self.test_results['background_verification'] = False
    
    async def test_payment_monitor(self):
        """Test payment monitor service."""
        print("\n4️⃣ Payment Monitor Test")
        print("-" * 40)
        
        try:
            from payment_monitor import PaymentMonitorService
            
            monitor = PaymentMonitorService()
            await monitor.initialize()
            
            print("✅ Payment monitor service initialized")
            
            # Test the monitoring logic
            pending = await monitor.db.get_pending_payments(age_limit_minutes=0)
            to_check = [p for p in pending if p.get('expires_at') is None or datetime.fromisoformat(p['expires_at']) > datetime.now()]
            
            print(f"📊 Found {len(pending)} total payments")
            print(f"📊 {len(to_check)} payments to check")
            
            if to_check:
                print("📋 Payments to check:")
                for payment in to_check[:2]:  # Show first 2
                    print(f"  - {payment['payment_id']} ({payment['crypto_type']})")
            
            await monitor.db.close()
            self.test_results['payment_monitor'] = True
            
        except Exception as e:
            print(f"❌ Payment monitor test failed: {e}")
            self.test_results['payment_monitor'] = False
    
    async def test_manual_verification(self):
        """Test manual payment verification."""
        print("\n5️⃣ Manual Verification Test")
        print("-" * 40)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            from multi_crypto_payments import MultiCryptoPaymentProcessor
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            processor = MultiCryptoPaymentProcessor(config, db, logger)
            
            # Get a pending payment to test
            pending_payments = await db.get_pending_payments(age_limit_minutes=1440)
            
            if pending_payments:
                test_payment = pending_payments[0]
                payment_id = test_payment['payment_id']
                
                print(f"🧪 Testing manual verification for payment: {payment_id}")
                
                # Test manual verification
                result = await processor.verify_payment_on_blockchain(payment_id)
                
                print(f"📊 Manual verification result: {result}")
                self.test_results['manual_verification'] = True
            else:
                print("⚠️ No pending payments to test manual verification")
                self.test_results['manual_verification'] = False
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Manual verification test failed: {e}")
            self.test_results['manual_verification'] = False
    
    def generate_diagnostic_report(self):
        """Generate diagnostic report."""
        print("\n📊 DIAGNOSTIC REPORT")
        print("=" * 50)
        
        # Count successful tests
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        
        # Detailed results
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        
        if not self.test_results.get('database', False):
            print("- Check database connection and schema")
            print("- Verify pending payments exist in database")
        
        if not self.test_results.get('payment_processor', False):
            print("- Check payment processor initialization")
            print("- Verify all dependencies are installed")
        
        if not self.test_results.get('background_verification', False):
            print("- Background verification task not working")
            print("- Check asyncio event loop")
        
        if not self.test_results.get('payment_monitor', False):
            print("- Payment monitor service has issues")
            print("- Check monitor service logs")
        
        if not self.test_results.get('manual_verification', False):
            print("- Manual verification failing")
            print("- Check payment verification logic")
        
        if all(self.test_results.values()):
            print("✅ All systems working - payments should be detected automatically")
            print("💡 Check if payments are actually being sent to the correct addresses")

async def main():
    """Main diagnostic function."""
    diagnostic = PaymentDetectionDiagnostic()
    await diagnostic.run_diagnostic()

if __name__ == "__main__":
    asyncio.run(main())

