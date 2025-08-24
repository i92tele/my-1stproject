#!/usr/bin/env python3
"""
Run Fresh Health Check

This script runs a comprehensive health check and generates an updated report.
"""

import logging
import os
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def run_health_check():
    """Run the health check."""
    logger.info("🏥 Running Fresh Health Check...")
    
    try:
        # Import and run the health check
        from health_check import main as health_check_main
        health_check_main()
        
        logger.info("✅ Health check completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False

def check_health_report():
    """Check if health report was generated."""
    logger.info("📊 Checking health report...")
    
    if os.path.exists("health_report.json"):
        logger.info("✅ Health report found: health_report.json")
        
        # Read and display summary
        try:
            import json
            with open("health_report.json", "r") as f:
                report = json.load(f)
            
            logger.info("=" * 60)
            logger.info("📋 HEALTH REPORT SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Timestamp: {report.get('timestamp', 'Unknown')}")
            logger.info(f"Overall Status: {report.get('overall_status', 'Unknown')}")
            logger.info(f"Passed: {report.get('success_count', 0)}/{report.get('total_checks', 0)}")
            
            # Show failed checks
            checks = report.get('checks', {})
            failed_checks = []
            for check_name, check_data in checks.items():
                if check_data.get('status') == 'FAIL':
                    failed_checks.append(check_name)
            
            if failed_checks:
                logger.info(f"❌ Failed checks: {', '.join(failed_checks)}")
            else:
                logger.info("✅ All checks passed!")
            
            # Show warnings
            warnings = report.get('warnings', [])
            if warnings:
                logger.info("⚠️ Warnings:")
                for warning in warnings:
                    logger.info(f"   - {warning}")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Error reading health report: {e}")
    else:
        logger.warning("⚠️ No health report found")

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🏥 FRESH HEALTH CHECK")
    logger.info("=" * 60)
    
    # Run health check
    if run_health_check():
        logger.info("✅ Health check completed")
        
        # Check the report
        check_health_report()
        
        logger.info("=" * 60)
        logger.info("📊 NEXT STEPS:")
        logger.info("1. Review the health report above")
        logger.info("2. Address any failed checks")
        logger.info("3. Fix any warnings if needed")
        logger.info("4. Run complete_bot_fixes.py if issues found")
        logger.info("=" * 60)
    else:
        logger.error("❌ Health check failed")
        logger.info("💡 Try running: python complete_bot_fixes.py")

if __name__ == "__main__":
    main()
