#!/usr/bin/env python3
"""
Wrapper script to run status check and capture output
"""

import subprocess
import sys
import os

def run_status_check():
    """Run the status check and capture output."""
    try:
        # Run the status check
        result = subprocess.run(
            [sys.executable, 'quick_status_check.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Save output to file
        with open('status_check_output.txt', 'w') as f:
            f.write("=== STATUS CHECK OUTPUT ===\n")
            f.write(f"Return Code: {result.returncode}\n")
            f.write(f"STDOUT:\n{result.stdout}\n")
            f.write(f"STDERR:\n{result.stderr}\n")
        
        print("✅ Status check completed and saved to status_check_output.txt")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("\nOutput:")
            print(result.stdout)
        
        if result.stderr:
            print("\nErrors:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Status check timed out")
        return False
    except Exception as e:
        print(f"❌ Error running status check: {e}")
        return False

if __name__ == "__main__":
    success = run_status_check()
    sys.exit(0 if success else 1)
