#!/usr/bin/env python3
"""
Quick Install Dependencies

This script quickly installs the missing dependencies without updating package lists.
"""

import subprocess
import sys
import os

def quick_install():
    """Quick install of missing dependencies."""
    print("⚡ Quick Install - Missing Dependencies")
    print("=" * 50)
    
    # Install python3-dotenv directly
    print("📦 Installing python3-dotenv...")
    try:
        result = subprocess.run(['apt', 'install', '-y', 'python3-dotenv'], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ python3-dotenv installed successfully")
        else:
            print(f"❌ Failed to install python3-dotenv: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Installation timed out")
        return False
    except Exception as e:
        print(f"❌ Error installing python3-dotenv: {e}")
        return False
    
    # Try to install aiohttp
    print("\n📦 Installing python3-aiohttp...")
    try:
        result = subprocess.run(['apt', 'install', '-y', 'python3-aiohttp'], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ python3-aiohttp installed successfully")
        else:
            print(f"⚠️ Failed to install python3-aiohttp: {result.stderr}")
            print("This is optional - system will use fallback prices")
    except subprocess.TimeoutExpired:
        print("⚠️ aiohttp installation timed out - optional package")
    except Exception as e:
        print(f"⚠️ Error installing aiohttp: {e} - optional package")
    
    print("\n🎉 Quick Install Complete!")
    print("\n📋 Next Steps:")
    print("1. Restart your bot")
    print("2. Test the payment system")
    
    return True

if __name__ == "__main__":
    success = quick_install()
    sys.exit(0 if success else 1)
