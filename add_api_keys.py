#!/usr/bin/env python3
"""
Add API Keys to .env
Add the missing API keys to the .env file for payment verification
"""

import os

def add_api_keys():
    """Add API keys to .env file."""
    print("🔧 ADDING API KEYS TO .ENV")
    print("=" * 50)
    
    env_file = "config/.env"
    
    # Check if .env file exists
    if not os.path.exists(env_file):
        print(f"❌ {env_file} not found")
        return
    
    # Read current .env content
    with open(env_file, 'r') as f:
        content = f.read()
    
    print("📋 Current .env file found")
    
    # Check what's already there
    has_blockcypher = "BLOCKCYPHER_API_KEY" in content
    has_etherscan = "ETHERSCAN_API_KEY" in content
    has_toncenter = "TONCENTER_API_KEY" in content
    
    print(f"🔑 BlockCypher API: {'✅ Already configured' if has_blockcypher else '❌ Missing'}")
    print(f"🔑 Etherscan API: {'✅ Already configured' if has_etherscan else '❌ Missing'}")
    print(f"🔑 TONCenter API: {'✅ Already configured' if has_toncenter else '❌ Missing'}")
    
    # Prepare to add missing keys
    additions = []
    
    if not has_blockcypher:
        additions.append("BLOCKCYPHER_API_KEY=your_blockcypher_api_key_here")
    
    if not has_etherscan:
        additions.append("ETHERSCAN_API_KEY=your_etherscan_api_key_here")
    
    if not has_toncenter:
        additions.append("TONCENTER_API_KEY=your_toncenter_api_key_here")
    
    if additions:
        print(f"\n📝 Adding {len(additions)} missing API keys...")
        
        # Add to .env file
        with open(env_file, 'a') as f:
            f.write("\n# Payment Verification API Keys\n")
            for addition in additions:
                f.write(f"{addition}\n")
        
        print("✅ API keys added to .env file")
        print("\n💡 NEXT STEPS:")
        print("1. Edit config/.env and replace 'your_api_key_here' with your actual API keys")
        print("2. Restart the bot to load the new configuration")
        print("3. The bot should now be able to verify BTC payments automatically")
    else:
        print("\n✅ All API keys are already configured!")
    
    print(f"\n📁 .env file location: {os.path.abspath(env_file)}")

if __name__ == "__main__":
    add_api_keys()
