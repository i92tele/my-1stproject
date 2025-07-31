# 🧪 AutoFarming Bot - Test Run Instructions

## ✅ Priority Fixes Implemented

1. **Analytics Dashboard** - Users can see ROI and performance
2. **Referral System** - Viral growth mechanism
3. **Content Moderation** - Prevents spam and abuse
4. **TON Payments** - Fully automatic verification
5. **Enhanced Database** - Better tracking and analytics

## 🚀 Step-by-Step Test Instructions

### **Step 1: Environment Setup** (2 minutes)
```bash
# 1. Update your .env file with TON wallet
echo "TON_ADDRESS=your_ton_wallet_address" >> config/.env

# 2. Add at least one worker account
echo "WORKER_1_API_ID=your_worker1_api_id" >> config/.env
echo "WORKER_1_API_HASH=your_worker1_api_hash" >> config/.env
echo "WORKER_1_PHONE=your_worker1_phone_number" >> config/.env
```

### **Step 2: Test System Components** (1 minute)
```bash
# Run the test script
python3 test_run.py
```
**Expected Output:** All ✅ green checkmarks

### **Step 3: Deploy the Bot** (1 command)
```bash
./deploy.sh
```
**Expected Output:** All services started successfully

### **Step 4: Test Bot Commands** (5 minutes)

#### **4.1 Test Basic Commands**
```
/start - Should show welcome message
/help - Should show all available commands
```

#### **4.2 Test Subscription Flow**
```
/subscribe - Should show TON payment plans
```
- Click on a plan
- Should generate TON payment QR code
- Test payment verification (use small amount)

#### **4.3 Test Analytics**
```
/analytics - Should show performance metrics
```
*Note: Requires active subscription*

#### **4.4 Test Referral System**
```
/referral - Should show referral code and stats
```
- Copy the referral code
- Share with a friend for testing

### **Step 5: Test Admin Commands** (2 minutes)
```
/revenue_stats - Should show TON revenue
/pending_payments - Should show pending payments
/admin_stats - Should show general statistics
```

### **Step 6: Test Worker System** (3 minutes)
```
/add_group @testgroup crypto
```
- Add a test group
- Check if worker joins automatically
- Monitor logs for worker activity

### **Step 7: Test Content Moderation** (2 minutes)
- Try posting content with spam keywords
- Should get moderation warnings
- Test appropriate content (should pass)

## 📊 Expected Results

### **✅ Success Indicators:**
- All test commands respond correctly
- TON payment QR codes generate
- Analytics show performance data
- Referral codes are created
- Workers join groups automatically
- Content moderation works

### **❌ Common Issues & Fixes:**

#### **Issue 1: "Database connection failed"**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection string in .env
DATABASE_URL=postgresql://user:password@localhost/dbname
```

#### **Issue 2: "Worker authentication failed"**
```bash
# Check worker credentials in .env
WORKER_1_API_ID=12345
WORKER_1_API_HASH=abcdef123456
WORKER_1_PHONE=+1234567890
```

#### **Issue 3: "TON payment not working"**
```bash
# Check TON wallet address
TON_ADDRESS=your_ton_wallet_address
```

## 🎯 Test Scenarios

### **Scenario 1: New User Journey**
1. User starts bot (`/start`)
2. User subscribes (`/subscribe`)
3. User pays with TON
4. User creates ad content
5. User views analytics (`/analytics`)
6. User shares referral code (`/referral`)

### **Scenario 2: Revenue Generation**
1. Admin adds groups (`/add_group`)
2. Users subscribe and pay
3. Workers post ads automatically
4. Admin monitors revenue (`/revenue_stats`)
5. System generates daily reports

### **Scenario 3: Viral Growth**
1. User gets referral code
2. User shares with friends
3. Friends use referral code
4. Both users get rewards
5. System tracks referrals

## 📈 Performance Metrics to Monitor

### **Technical Metrics:**
- ✅ Service uptime (all 4 services running)
- ✅ Payment verification success rate
- ✅ Worker posting success rate
- ✅ Database response time

### **Business Metrics:**
- 📊 Revenue per day/week
- 📊 New subscriptions per day
- 📊 Referral conversion rate
- 📊 User retention rate

## 🚨 Emergency Procedures

### **If Bot Stops Responding:**
```bash
# Restart all services
pkill -f "python3.*bot"
./deploy.sh
```

### **If Payments Not Working:**
```bash
# Check payment monitor logs
tail -f logs/payment_monitor.log
```

### **If Workers Not Posting:**
```bash
# Check scheduler logs
tail -f logs/scheduler.log
```

## 🎉 Success Criteria

**Bot is ready for production when:**
- ✅ All test commands work
- ✅ TON payments process automatically
- ✅ Workers join and post to groups
- ✅ Analytics show performance data
- ✅ Referral system generates codes
- ✅ Content moderation prevents spam

**Expected Revenue Timeline:**
- **Week 1**: $50-200 (testing phase)
- **Month 1**: $500-2000 (scaling phase)
- **Month 3**: $2000-8000 (growth phase)

---

**🚀 Ready to test? Run the commands above and let me know the results!** 