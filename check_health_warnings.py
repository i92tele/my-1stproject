#!/usr/bin/env python3
"""
Check Health Check Warnings

This script runs the health check and shows what specific warnings are being generated.
"""

import subprocess
import sys
import os

def check_health_warnings():
    """Check what health warnings are being generated."""
    print("🔍 Checking Health Check Warnings")
    print("=" * 50)
    
    try:
        # Run health check and capture output
        result = subprocess.run(['python3', 'health_check.py'], 
                              capture_output=True, text=True, timeout=60)
        
        print("📋 Health Check Output:")
        print("-" * 30)
        
        # Print stdout
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        # Print stderr
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"\nReturn Code: {result.returncode}")
        
        # Check if there are specific warning patterns
        output = result.stdout + result.stderr
        
        warnings = []
        if "Missing required" in output:
            warnings.append("Missing required environment variables")
        if "Missing optional" in output:
            warnings.append("Missing optional environment variables")
        if "Missing required package" in output:
            warnings.append("Missing required packages")
        if "Missing optional package" in output:
            warnings.append("Missing optional packages")
        if "ImportError" in output:
            warnings.append("Import errors")
        if "SyntaxError" in output:
            warnings.append("Syntax errors")
        if "Database" in output and "error" in output.lower():
            warnings.append("Database connection issues")
        
        if warnings:
            print("\n⚠️ Detected Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("\n✅ No specific warnings detected")
            
    except subprocess.TimeoutExpired:
        print("❌ Health check timed out")
    except Exception as e:
        print(f"❌ Error running health check: {e}")

if __name__ == "__main__":
    check_health_warnings()
