# Simple Wallet Setup Guide

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

