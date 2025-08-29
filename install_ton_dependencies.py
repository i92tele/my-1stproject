#!/usr/bin/env python3
"""
Install TON Dependencies

This script installs the required dependencies for TON cryptocurrency support.
"""

import subprocess
import sys
import os

def install_ton_dependencies():
    """Install TON-related dependencies."""
    print("🔧 Installing TON Dependencies")
    print("=" * 50)
    
    dependencies = [
        "pytonlib",
        "aiohttp",
        "requests"
    ]
    
    print("📦 Installing required packages...")
    
    for package in dependencies:
        try:
            print(f"Installing {package}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {package} installed successfully")
            else:
                print(f"❌ Failed to install {package}")
                print(f"Error: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error installing {package}: {e}")
    
    print("\n🎯 TON Dependencies Installation Complete!")
    print("\n📋 Next Steps:")
    print("1. Restart your bot to apply the changes")
    print("2. TON payments should now work without warnings")
    print("3. If you still see warnings, they're just informational")

if __name__ == "__main__":
    install_ton_dependencies()
