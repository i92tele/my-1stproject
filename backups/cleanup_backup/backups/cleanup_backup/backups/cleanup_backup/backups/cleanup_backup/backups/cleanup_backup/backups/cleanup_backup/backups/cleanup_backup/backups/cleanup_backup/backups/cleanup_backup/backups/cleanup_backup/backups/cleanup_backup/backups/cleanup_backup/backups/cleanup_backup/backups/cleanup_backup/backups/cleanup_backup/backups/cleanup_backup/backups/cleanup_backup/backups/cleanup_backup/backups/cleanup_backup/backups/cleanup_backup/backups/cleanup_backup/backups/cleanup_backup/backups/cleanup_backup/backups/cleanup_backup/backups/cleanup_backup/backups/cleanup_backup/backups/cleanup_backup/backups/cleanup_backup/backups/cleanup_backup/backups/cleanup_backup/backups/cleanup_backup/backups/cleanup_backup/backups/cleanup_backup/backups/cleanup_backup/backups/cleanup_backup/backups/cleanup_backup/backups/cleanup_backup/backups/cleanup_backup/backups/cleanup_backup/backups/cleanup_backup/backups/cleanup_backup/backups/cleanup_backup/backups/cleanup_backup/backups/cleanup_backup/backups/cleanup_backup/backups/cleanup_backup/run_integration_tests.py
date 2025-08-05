#!/usr/bin/env python3
"""
Integration Test Runner for AutoFarming Bot

This script provides an easy way to run integration tests with different options.

Usage:
    python3 run_integration_tests.py                    # Run all tests
    python3 run_integration_tests.py --quick           # Run quick tests only
    python3 run_integration_tests.py --verbose         # Run with verbose logging
    python3 run_integration_tests.py --clean           # Clean test data before running
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime

def main():
    """Main function to run integration tests with options."""
    parser = argparse.ArgumentParser(description='Run AutoFarming Bot integration tests')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--clean', action='store_true', help='Clean test data before running')
    parser.add_argument('--test', choices=['worker', 'payment', 'posting', 'flow', 'all'], 
                       default='all', help='Run specific test category')
    
    args = parser.parse_args()
    
    print("🧪 AutoFarming Bot Integration Test Runner")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Options: quick={args.quick}, verbose={args.verbose}, clean={args.clean}, test={args.test}")
    print("=" * 50)
    
    # Import and run the integration tester
    try:
        from test_integration import IntegrationTester
        
        async def run_tests():
            tester = IntegrationTester()
            
            # Set logging level based on verbose flag
            if args.verbose:
                import logging
                logging.getLogger().setLevel(logging.DEBUG)
            
            # Run tests based on options
            if args.test == 'all':
                await tester.run_all_tests()
            else:
                # Run specific test category
                if args.test == 'worker':
                    await tester.test_worker_rotation()
                elif args.test == 'payment':
                    await tester.test_payment_creation_and_verification()
                elif args.test == 'posting':
                    await tester.test_test_group_posting()
                elif args.test == 'flow':
                    await tester.test_complete_user_flow()
        
        asyncio.run(run_tests())
        
    except ImportError as e:
        print(f"❌ Error importing test modules: {e}")
        print("Make sure all required dependencies are installed.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 