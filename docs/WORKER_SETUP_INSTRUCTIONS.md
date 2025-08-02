# 🔧 **Adding Worker Accounts - Step by Step**

## **Current Status:**
✅ **Worker 1**: Configured and working (+15512984981)
⚠️ **Workers 2-5**: Ready to be configured

## **How to Add More Workers:**

### **Step 1: Get Additional Telegram Accounts**

**Option A: Create New Accounts**
1. Download Telegram on different phones/devices
2. Create accounts with different phone numbers
3. Get API credentials for each

**Option B: Use Existing Accounts**
- Use accounts you already own
- Ensure they're not banned

### **Step 2: Get API Credentials**

For each new account:
1. **Go to**: https://my.telegram.org/auth
2. **Login** with the phone number
3. **Create application**:
   - App title: `AutoFarming Worker X`
   - Short name: `autofarming_worker_X`
   - Platform: `Other`
   - Description: `Automated posting worker`
4. **Copy credentials**:
   - API ID (e.g., `12345678`)
   - API Hash (e.g., `abcdef1234567890abcdef1234567890`)

### **Step 3: Update Your .env File**

**Edit `config/.env` and replace the placeholder values:**

```bash
# Current worker (working)
WORKER_1_API_ID=29187595
WORKER_1_API_HASH=243f71f06e9692a1f09a914ddb89d33c
WORKER_1_PHONE=+15512984981

# Worker 2 (Replace with your actual values)
WORKER_2_API_ID=YOUR_ACTUAL_API_ID
WORKER_2_API_HASH=YOUR_ACTUAL_API_HASH
WORKER_2_PHONE=YOUR_ACTUAL_PHONE_NUMBER

# Worker 3 (Replace with your actual values)
WORKER_3_API_ID=YOUR_ACTUAL_API_ID
WORKER_3_API_HASH=YOUR_ACTUAL_API_HASH
WORKER_3_PHONE=YOUR_ACTUAL_PHONE_NUMBER

# Worker 4 (Replace with your actual values)
WORKER_4_API_ID=YOUR_ACTUAL_API_ID
WORKER_4_API_HASH=YOUR_ACTUAL_API_HASH
WORKER_4_PHONE=YOUR_ACTUAL_PHONE_NUMBER

# Worker 5 (Replace with your actual values)
WORKER_5_API_ID=YOUR_ACTUAL_API_ID
WORKER_5_API_HASH=YOUR_ACTUAL_API_HASH
WORKER_5_PHONE=YOUR_ACTUAL_PHONE_NUMBER
```

### **Step 4: Test Your Workers**

After adding credentials, test them:

```bash
source venv/bin/activate && python3 add_workers.py
```

### **Step 5: Update Scheduler for Multi-Worker Support**

The scheduler needs to be updated to use multiple workers. Here's what needs to be changed:

**Current scheduler.py (single worker):**
```python
# Single worker setup
worker_api_id = os.getenv("WORKER_1_API_ID")
worker_api_hash = os.getenv("WORKER_1_API_HASH")
worker_phone = os.getenv("WORKER_1_PHONE")
```

**New multi-worker setup needed:**
```python
# Multi-worker setup
workers = []
for i in range(1, 6):
    api_id = os.getenv(f"WORKER_{i}_API_ID")
    api_hash = os.getenv(f"WORKER_{i}_API_HASH")
    phone = os.getenv(f"WORKER_{i}_PHONE")
    
    if api_id and api_hash and phone:
        workers.append({
            'api_id': api_id,
            'api_hash': api_hash,
            'phone': phone,
            'client': None,
            'index': i
        })
```

## **Benefits of Multiple Workers:**

### **Performance:**
- **Parallel Posting**: Multiple ads sent simultaneously
- **Faster Processing**: Reduced queue time
- **Higher Throughput**: More ads per hour

### **Reliability:**
- **Redundancy**: If one worker fails, others continue
- **Ban Protection**: Spread risk across multiple accounts
- **Uptime**: Higher overall system availability

### **Scalability:**
- **Easy Expansion**: Add more workers as needed
- **Load Distribution**: Balance work across accounts
- **Growth Ready**: Scale with your business

## **Example Worker Configuration:**

Here's what your `.env` file should look like with multiple workers:

```bash
# Worker 1 (Current - Working)
WORKER_1_API_ID=29187595
WORKER_1_API_HASH=243f71f06e9692a1f09a914ddb89d33c
WORKER_1_PHONE=+15512984981

# Worker 2 (Example - Replace with real values)
WORKER_2_API_ID=12345678
WORKER_2_API_HASH=abcdef1234567890abcdef1234567890
WORKER_2_PHONE=+1234567890

# Worker 3 (Example - Replace with real values)
WORKER_3_API_ID=87654321
WORKER_3_API_HASH=fedcba0987654321fedcba0987654321
WORKER_3_PHONE=+0987654321
```

## **Testing Commands:**

### **Test current worker:**
```bash
source venv/bin/activate && python3 add_workers.py
```

### **After adding workers, test all:**
```bash
source venv/bin/activate && python3 add_workers.py
```

### **Expected output with multiple workers:**
```
✅ Found worker 1: +15512984981
✅ Found worker 2: +1234567890
✅ Found worker 3: +0987654321
📊 Total workers loaded: 3
```

## **Next Steps:**

1. **Get additional Telegram accounts** (phones/numbers)
2. **Get API credentials** from https://my.telegram.org/auth
3. **Update your `.env` file** with real credentials
4. **Test the workers** with the provided script
5. **Update scheduler.py** for multi-worker support

**Ready to add more workers? Start with getting those additional Telegram accounts!** 🚀 