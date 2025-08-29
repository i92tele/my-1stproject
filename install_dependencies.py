#!/usr/bin/env python3
"""
Install Missing Dependencies

This script installs the missing dependencies for the payment system.
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install missing dependencies."""
    print("📦 Installing Missing Dependencies")
    print("=" * 50)
    
    # Update package list
    print("🔄 Updating package list...")
    try:
        subprocess.run(['apt', 'update'], check=True, capture_output=True)
        print("✅ Package list updated")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update package list: {e}")
        return False
    
    # Install python3-dotenv
    print("\n📦 Installing python3-dotenv...")
    try:
        subprocess.run(['apt', 'install', '-y', 'python3-dotenv'], check=True, capture_output=True)
        print("✅ python3-dotenv installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install python3-dotenv: {e}")
        return False
    
    # Install aiohttp if needed
    print("\n📦 Installing python3-aiohttp...")
    try:
        subprocess.run(['apt', 'install', '-y', 'python3-aiohttp'], check=True, capture_output=True)
        print("✅ python3-aiohttp installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Failed to install python3-aiohttp: {e}")
        print("This is optional - the system will use fallback prices")
    
    print("\n🎉 Dependencies Installation Complete!")
    print("\n📋 Next Steps:")
    print("1. Restart your bot")
    print("2. Run the verification script again")
    print("3. Test the payment system")
    
    return True

if __name__ == "__main__":
    success = install_dependencies()
    sys.exit(0 if success else 1)
