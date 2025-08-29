#!/usr/bin/env python3
"""
Add Missing API Support
Add support for Blockchain.info, Mempool, and Blockstream APIs
"""

def add_missing_api_support():
    """Add missing API key support to multi_crypto_payments.py."""
    
    print("🔧 ADDING MISSING API SUPPORT")
    print("=" * 50)
    
    # Read the current file
    with open('multi_crypto_payments.py', 'r') as f:
        content = f.read()
    
    # Check what's already there
    has_blockchain_info = 'BLOCKCHAIN_INFO_API_KEY' in content
    has_mempool = 'MEMPOOL_API_KEY' in content
    has_blockstream = 'BLOCKSTREAM_API_KEY' in content
    
    print(f"📋 Current API Support:")
    print(f"  - BLOCKCHAIN_INFO_API_KEY: {'✅ Supported' if has_blockchain_info else '❌ Missing'}")
    print(f"  - MEMPOOL_API_KEY: {'✅ Supported' if has_mempool else '❌ Missing'}")
    print(f"  - BLOCKSTREAM_API_KEY: {'✅ Supported' if has_blockstream else '❌ Missing'}")
    
    if has_blockchain_info and has_mempool and has_blockstream:
        print("\n✅ All APIs are already supported!")
        return
    
    print("\n🔧 Adding missing API support...")
    
    # Add the missing API keys to the __init__ method
    api_keys_to_add = []
    
    if not has_blockchain_info:
        api_keys_to_add.append("        self.blockchain_info_api_key = os.getenv('BLOCKCHAIN_INFO_API_KEY', '')")
    
    if not has_mempool:
        api_keys_to_add.append("        self.mempool_api_key = os.getenv('MEMPOOL_API_KEY', '')")
    
    if not has_blockstream:
        api_keys_to_add.append("        self.blockstream_api_key = os.getenv('BLOCKSTREAM_API_KEY', '')")
    
    if api_keys_to_add:
        # Find the right place to insert (after existing API keys)
        lines = content.split('\n')
        
        # Find the line after TONCENTER_API_KEY
        insert_index = None
        for i, line in enumerate(lines):
            if 'TONCENTER_API_KEY' in line:
                insert_index = i + 1
                break
        
        if insert_index:
            # Insert the new API keys
            for api_key in api_keys_to_add:
                lines.insert(insert_index, api_key)
                insert_index += 1
            
            # Write back the file
            new_content = '\n'.join(lines)
            with open('multi_crypto_payments.py', 'w') as f:
                f.write(new_content)
            
            print("✅ Added missing API key support!")
            print(f"📝 Added {len(api_keys_to_add)} API keys")
        else:
            print("❌ Could not find insertion point")
    
    print("\n💡 NEXT STEPS:")
    print("1. Restart the bot to load the new API support")
    print("2. The bot will now use multiple fallback APIs for payment verification")
    print("3. This should resolve the rate limit issues")

if __name__ == "__main__":
    add_missing_api_support()
