#!/usr/bin/env python3
"""
Priority 1 Critical Verification Test Runner
Runs all critical verification tests for the system
"""

import asyncio
import logging
import json
import subprocess
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test_script(script_name, description):
    """Run a test script and capture results."""
    print(f"\n🔧 Running {description}...")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Save output to file
        output_file = f"{script_name.replace('.py', '')}_output.txt"
        with open(output_file, 'w') as f:
            f.write(f"=== {description.upper()} TEST OUTPUT ===\n")
            f.write(f"Return Code: {result.returncode}\n")
            f.write(f"STDOUT:\n{result.stdout}\n")
            f.write(f"STDERR:\n{result.stderr}\n")
        
        print(f"✅ {description} completed")
        print(f"   Return code: {result.returncode}")
        print(f"   Output saved to: {output_file}")
        
        if result.stdout:
            print("\nOutput preview:")
            lines = result.stdout.split('\n')[:10]  # Show first 10 lines
            for line in lines:
                print(f"   {line}")
            if len(result.stdout.split('\n')) > 10:
                print("   ... (truncated)")
        
        if result.stderr:
            print("\nErrors:")
            lines = result.stderr.split('\n')[:5]  # Show first 5 error lines
            for line in lines:
                if line.strip():
                    print(f"   ❌ {line}")
        
        return result.returncode == 0, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print(f"❌ {description} timed out")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False, "", str(e)

async def run_priority1_tests():
    """Run all Priority 1 critical verification tests."""
    print("🚀 PRIORITY 1: CRITICAL VERIFICATION TESTS")
    print("=" * 80)
    print("Testing all critical fixes from previous session...")
    
    test_results = {}
    
    # Test 1: Ad Slot Correction System
    print("\n" + "=" * 80)
    print("🔥 PRIORITY 1.1: AD SLOT CORRECTION SYSTEM")
    print("=" * 80)
    
    success1, stdout1, stderr1 = run_test_script(
        "test_ad_slot_correction.py",
        "Ad Slot Correction System"
    )
    test_results["ad_slot_correction"] = {
        "success": success1,
        "stdout": stdout1,
        "stderr": stderr1
    }
    
    # Test 2: Forum Topic Posting
    print("\n" + "=" * 80)
    print("🔥 PRIORITY 1.2: FORUM TOPIC POSTING SYSTEM")
    print("=" * 80)
    
    success2, stdout2, stderr2 = run_test_script(
        "test_forum_topic_posting.py",
        "Forum Topic Posting System"
    )
    test_results["forum_topic_posting"] = {
        "success": success2,
        "stdout": stdout2,
        "stderr": stderr2
    }
    
    # Test 3: Admin Commands
    print("\n" + "=" * 80)
    print("🔥 PRIORITY 1.3: ADMIN COMMANDS SYSTEM")
    print("=" * 80)
    
    success3, stdout3, stderr3 = run_test_script(
        "test_admin_commands.py",
        "Admin Commands System"
    )
    test_results["admin_commands"] = {
        "success": success3,
        "stdout": stdout3,
        "stderr": stderr3
    }
    
    # Test 4: Quick Status Check
    print("\n" + "=" * 80)
    print("🔥 PRIORITY 1.4: SYSTEM STATUS CHECK")
    print("=" * 80)
    
    success4, stdout4, stderr4 = run_test_script(
        "quick_status_check.py",
        "System Status Check"
    )
    test_results["system_status"] = {
        "success": success4,
        "stdout": stdout4,
        "stderr": stderr4
    }
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 PRIORITY 1 TEST SUMMARY")
    print("=" * 80)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"{status} {test_name.replace('_', ' ').title()}")
        if result["success"]:
            passed_tests += 1
    
    overall_success = passed_tests == total_tests
    
    print(f"\n📈 Results: {passed_tests}/{total_tests} tests passed")
    print(f"🎯 Overall Status: {'ALL TESTS PASSED' if overall_success else 'SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 PRIORITY 1 VERIFICATION COMPLETE!")
        print("   ✅ All critical fixes are working correctly")
        print("   ✅ System is ready for production deployment")
        print("   ✅ Ready to proceed to Priority 2 (User Journey Testing)")
    else:
        print("\n⚠️ SOME CRITICAL ISSUES FOUND")
        print("   ❌ Some fixes may not be working correctly")
        print("   ❌ Issues need to be resolved before production")
        
        # Show specific failures
        failed_tests = [name for name, result in test_results.items() if not result["success"]]
        print(f"   ❌ Failed tests: {', '.join(failed_tests)}")
    
    # Save comprehensive results
    comprehensive_results = {
        "timestamp": datetime.now().isoformat(),
        "test_suite": "priority1_critical_verification",
        "overall_success": overall_success,
        "passed_tests": passed_tests,
        "total_tests": total_tests,
        "test_results": test_results
    }
    
    with open('priority1_test_results.json', 'w') as f:
        json.dump(comprehensive_results, f, indent=2)
    
    print(f"\n📄 Comprehensive results saved to: priority1_test_results.json")
    
    # Generate recommendations
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    
    if overall_success:
        print("✅ All critical systems verified - proceed to Priority 2:")
        print("   1. User Journey Testing")
        print("   2. Payment System Testing")
        print("   3. Scheduler Performance Testing")
    else:
        print("⚠️ Critical issues found - resolve before proceeding:")
        for test_name, result in test_results.items():
            if not result["success"]:
                print(f"   - Fix {test_name.replace('_', ' ')} issues")
        print("\nAfter fixing issues, re-run Priority 1 tests")
    
    return overall_success

def main():
    """Main function to run Priority 1 tests."""
    try:
        success = asyncio.run(run_priority1_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running Priority 1 tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
