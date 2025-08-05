#!/usr/bin/env python3
"""
Simple Wallet Setup for Bot
Configure Tonkeeper and Exodus wallets
"""

import os
from dotenv import load_dotenv

def setup_simple_wallets():
    """Setup simple wallet configuration for the bot."""
    
    print("🎯 Simple Wallet Setup")
    print("=" * 30)
    print("Using Tonkeeper for TON and Exodus for other cryptos")
    
    # Load current .env
    load_dotenv('config/.env')
    
    # Read current .env file
    with open('config/.env', 'r') as f:
        lines = f.readlines()
    
    # Add simple wallet configuration
    wallet_config = """
# Simple Wallet Configuration
# ==========================

# TON Wallet (Tonkeeper)
TON_ADDRESS=your_tonkeeper_address_here

# Other Cryptocurrencies (Exodus)
BTC_ADDRESS=your_exodus_bitcoin_address_here
ETH_ADDRESS=your_exodus_ethereum_address_here
SOL_ADDRESS=your_exodus_solana_address_here
BNB_ADDRESS=your_exodus_bnb_address_here

# Wallet Security Settings
DAILY_WITHDRAWAL_LIMIT_TON=100
DAILY_WITHDRAWAL_LIMIT_BTC=0.01
DAILY_WITHDRAWAL_LIMIT_ETH=0.1
DAILY_WITHDRAWAL_LIMIT_SOL=10
DAILY_WITHDRAWAL_LIMIT_BNB=1

# Backup Wallet Addresses (Optional)
TON_BACKUP_ADDRESS=your_backup_ton_address_here
BTC_BACKUP_ADDRESS=your_backup_bitcoin_address_here

"""
    
    # Find where to insert the wallet config
    insert_index = -1
    for i, line in enumerate(lines):
        if line.startswith('# Cryptocurrency Wallets'):
            insert_index = i
            break
    
    if insert_index != -1:
        # Replace the existing crypto section
        lines[insert_index:insert_index+6] = wallet_config.splitlines(True)
    else:
        # Add at the end
        lines.append(wallet_config)
    
    # Write updated .env file
    with open('config/.env', 'w') as f:
        f.writelines(lines)
    
    print("✅ Simple wallet configuration added!")
    print("\n📋 Next Steps:")
    print("1. Get your Tonkeeper address")
    print("2. Get your Exodus addresses")
    print("3. Update the addresses in config/.env")
    print("4. Test the payment system")

def create_wallet_guide():
    """Create a guide for getting wallet addresses."""
    
    guide = """# Simple Wallet Setup Guide

## 🎯 Using Tonkeeper + Exodus

### Step 1: Get Tonkeeper Address
1. Open Tonkeeper app
2. Tap on your wallet
3. Copy the address (starts with EQ...)
4. Update TON_ADDRESS in config/.env

### Step 2: Get Exodus Addresses
1. Open Exodus app
2. For each cryptocurrency:
   - Select the crypto (BTC, ETH, SOL, BNB)
   - Tap "Receive"
   - Copy the address
   - Update in config/.env

### Step 3: Security Best Practices
1. **Backup both wallets** (write down seed phrases)
2. **Store backups securely** (different locations)
3. **Test with small amounts** first
4. **Monitor transactions** regularly

### Step 4: Update Bot Configuration
1. Open config/.env file
2. Replace placeholder addresses with real ones
3. Set appropriate daily limits
4. Test payment system

## 💡 Benefits of This Setup

### Simplicity:
- ✅ Easy to use
- ✅ No complex multi-sig setup
- ✅ Familiar wallets

### Security:
- ✅ Two separate wallets
- ✅ Backup options
- ✅ Daily limits
- ✅ Transaction monitoring

### Flexibility:
- ✅ Add more cryptos easily
- ✅ Change addresses anytime
- ✅ Scale as needed

## 🔧 Bot Integration

The bot will now:
1. **Accept TON payments** via Tonkeeper
2. **Accept other crypto payments** via Exodus
3. **Verify payments** using blockchain APIs
4. **Apply daily limits** for security
5. **Send notifications** for large transactions

## 📱 Wallet Management

### Tonkeeper (TON):
- Primary wallet for TON payments
- Easy to use on mobile
- Good for daily transactions

### Exodus (Other Cryptos):
- Multi-currency support
- Desktop and mobile apps
- Good for BTC, ETH, SOL, BNB

## 🚀 Ready to Start!

Once you update the addresses:
1. Test with small payments
2. Monitor for 24 hours
3. Scale up gradually
4. Add more cryptos as needed

"""
    
    with open('SIMPLE_WALLET_GUIDE.md', 'w') as f:
        f.write(guide)
    
    print("✅ Simple wallet guide created!")

def main():
    """Main function to setup simple wallets."""
    
    # Setup wallet configuration
    setup_simple_wallets()
    
    # Create guide
    create_wallet_guide()
    
    print("\n🎉 Simple wallet setup complete!")
    print("\n📋 What to do next:")
    print("1. Get your Tonkeeper address")
    print("2. Get your Exodus addresses") 
    print("3. Update config/.env with real addresses")
    print("4. Test the payment system")

if __name__ == "__main__":
    main() 