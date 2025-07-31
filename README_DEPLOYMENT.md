# 🚀 AutoFarming Bot - TON Payment & Worker Accounts Deployment Guide

## Quick Start (Minimal Human Intervention)

### 1. **One-Command Deployment**
```bash
./deploy.sh
```

This script will:
- ✅ Install all dependencies
- ✅ Test configuration
- ✅ Start all services automatically
- ✅ Monitor and restart failed services

### 2. **Manual Deployment** (if needed)
```bash
# Install dependencies
pip install -r requirements.txt

# Start all services
python3 start_services.py
```

## 📊 **Revenue Generation Features**

### **Subscription Plans**
- **Basic** ($15/month): 1 ad slot
- **Premium** ($45/month): 3 ad slots  
- **Pro** ($99/month): 5 ad slots

### **Payment Method**
- 💎 **TON (The Open Network)** - Fully automatic verification

### **Automated Features**
- ✅ QR code generation for TON payments
- ✅ Automatic payment verification (30-second intervals)
- ✅ Automatic subscription activation
- ✅ Worker account group joining
- ✅ Expired subscription cleanup
- ✅ Daily revenue reports
- ✅ Service health monitoring

## 🔧 **Configuration**

### **Required Environment Variables** (`config/.env`)
```env
# Bot Configuration
BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=your_telegram_user_id

# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# TON Wallet
TON_ADDRESS=your_ton_wallet_address

# Worker Accounts (for automated posting)
WORKER_1_API_ID=your_worker1_api_id
WORKER_1_API_HASH=your_worker1_api_hash
WORKER_1_PHONE=your_worker1_phone_number

WORKER_2_API_ID=your_worker2_api_id
WORKER_2_API_HASH=your_worker2_api_hash
WORKER_2_PHONE=your_worker2_phone_number

# Add more workers as needed...

# Security
ENCRYPTION_KEY=your_encryption_key
SECRET_KEY=your_secret_key

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

## 🏃‍♂️ **Services Running**

### **1. Main Bot** (`bot.py`)
- Telegram user interface
- Subscription management
- TON payment processing
- Ad campaign management

### **2. Ad Scheduler** (`scheduler.py`)
- Automated ad posting via worker accounts
- Automatic group joining
- Worker account management
- Anti-spam protection

### **3. Payment Monitor** (`payment_monitor.py`)
- Automatic TON payment verification
- Real-time blockchain monitoring
- Subscription activation
- User notifications

### **4. Maintenance Service** (`maintenance.py`)
- Expired subscription cleanup
- Payment expiration handling
- Daily revenue reports
- Database maintenance

## 👥 **Worker Account Management**

### **How It Works:**
1. **Worker accounts** are separate Telegram accounts that join groups
2. **Main bot** manages subscriptions and payments
3. **Scheduler** uses worker accounts to post ads
4. **Automatic joining** - workers join groups automatically when needed

### **Setting Up Worker Accounts:**
1. Create Telegram accounts for workers
2. Get API credentials from https://my.telegram.org
3. Add to `.env` file:
   ```env
   WORKER_1_API_ID=12345
   WORKER_1_API_HASH=abcdef123456
   WORKER_1_PHONE=+1234567890
   ```
4. Run the bot - workers will authenticate automatically

### **Manual Group Addition (Alternative):**
If automatic joining causes issues:
1. Manually add workers to groups
2. Workers will detect they're already members
3. No additional action needed

## 📈 **Revenue Monitoring**

### **Admin Commands**
```bash
/revenue_stats          # View TON revenue statistics
/pending_payments       # Check pending TON payments
/verify_payment <id> <tx_hash>  # Manual payment verification
/admin_stats            # General bot statistics
```

### **Automated Reports**
- Daily maintenance reports in logs
- TON revenue tracking
- User subscription analytics

## 🔄 **Minimal Human Intervention**

### **What Runs Automatically:**
- ✅ TON payment processing and verification
- ✅ Subscription activation/deactivation
- ✅ Worker account group joining
- ✅ Ad scheduling and posting
- ✅ Service health monitoring
- ✅ Failed service restart
- ✅ Database cleanup

### **Manual Intervention Needed:**
- 📱 Initial worker account setup (one-time)
- 📊 Revenue monitoring (optional)
- 🛠️ Service troubleshooting (rare)

## 📝 **Logs and Monitoring**

### **Log Files**
- `logs/services.log` - Service manager
- `logs/payment_monitor.log` - TON payment monitoring
- `logs/maintenance.log` - Maintenance tasks
- `logs/scheduler.log` - Ad scheduler
- `logs/bot.log` - Main bot

### **Health Checks**
```bash
# Check if services are running
ps aux | grep python3

# View recent logs
tail -f logs/services.log
```

## 💰 **Revenue Optimization**

### **Immediate Actions:**
1. **Set up TON wallet** in `.env`
2. **Add Telegram groups** using `/add_group`
3. **Set up worker accounts** with API credentials
4. **Test payment flow** with small amounts
5. **Monitor revenue** with `/revenue_stats`

### **Scaling Tips:**
- Add more worker accounts for higher posting frequency
- Use multiple TON wallets for better organization
- Set up monitoring alerts for revenue milestones
- Implement affiliate/referral system

## 🚨 **Troubleshooting**

### **Common Issues:**
1. **Bot not responding**: Check `BOT_TOKEN` and network
2. **TON payments not processing**: Verify `TON_ADDRESS`
3. **Ads not posting**: Check worker account credentials
4. **Workers can't join groups**: Manual group addition may be needed
5. **Database errors**: Verify `DATABASE_URL`

### **Emergency Commands:**
```bash
# Restart all services
pkill -f "python3.*bot"
./deploy.sh

# Check service status
python3 -c "import bot; print('Bot config OK')"
```

## 📊 **Expected Revenue Timeline**

### **Week 1:**
- Setup and testing
- First few subscribers
- Revenue: $50-200

### **Month 1:**
- 10-50 active subscribers
- Revenue: $500-2000

### **Month 3:**
- 50-200 active subscribers
- Revenue: $2000-8000

### **Month 6:**
- 200+ active subscribers
- Revenue: $8000+ monthly

## 🎯 **Next Steps for Maximum Revenue**

1. **Marketing**: Promote bot in crypto/telegram groups
2. **Automation**: Add more worker accounts for scaling
3. **Features**: Add analytics dashboard and advanced targeting
4. **Support**: Implement customer support system
5. **Integration**: Add more payment methods if needed

---

**🚀 Ready to generate revenue? Run `./deploy.sh` and start earning with TON!** 