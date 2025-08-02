# 🔧 **Adding More Worker Accounts - Complete Guide**

## **Why Add More Workers?**
- **Increased Capacity**: Post to more groups simultaneously
- **Better Performance**: Distribute load across multiple accounts
- **Reduced Risk**: If one account gets banned, others continue working
- **Higher Throughput**: More ads posted per hour

## **Step 1: Get Additional Telegram Accounts**

### **Option A: Create New Telegram Accounts**
1. **Download Telegram** on different devices/phones
2. **Create new accounts** with different phone numbers
3. **Get API credentials** for each account

### **Option B: Use Existing Accounts**
- Use accounts you already own
- Ensure they're not banned or restricted

## **Step 2: Get API Credentials for Each Account**

### **For Each New Account:**
1. **Go to**: https://my.telegram.org/auth
2. **Login** with the phone number
3. **Create a new application**:
   - **App title**: AutoFarming Worker X
   - **Short name**: autofarming_worker_X
   - **Platform**: Other
   - **Description**: Automated posting worker

4. **Copy the credentials**:
   - **API ID**: (e.g., 12345678)
   - **API Hash**: (e.g., abcdef1234567890abcdef1234567890)

## **Step 3: Update Your .env File**

Add the new worker credentials to your `config/.env` file:

```bash
# Current worker (keep as is)
WORKER_1_API_ID=29187595
WORKER_1_API_HASH=243f71f06e9692a1f09a914ddb89d33c
WORKER_1_PHONE=+15512984981

# Add new workers below
WORKER_2_API_ID=YOUR_SECOND_API_ID
WORKER_2_API_HASH=YOUR_SECOND_API_HASH
WORKER_2_PHONE=YOUR_SECOND_PHONE_NUMBER

WORKER_3_API_ID=YOUR_THIRD_API_ID
WORKER_3_API_HASH=YOUR_THIRD_API_HASH
WORKER_3_PHONE=YOUR_THIRD_PHONE_NUMBER

WORKER_4_API_ID=YOUR_FOURTH_API_ID
WORKER_4_API_HASH=YOUR_FOURTH_API_HASH
WORKER_4_PHONE=YOUR_FOURTH_PHONE_NUMBER

WORKER_5_API_ID=YOUR_FIFTH_API_ID
WORKER_5_API_HASH=YOUR_FIFTH_API_HASH
WORKER_5_PHONE=YOUR_FIFTH_PHONE_NUMBER
```

## **Step 4: Update the Scheduler Code**

The scheduler needs to be updated to handle multiple workers. Here's how to modify it:

### **Current scheduler.py Structure:**
```python
# Current single worker setup
worker_api_id = os.getenv("WORKER_1_API_ID")
worker_api_hash = os.getenv("WORKER_1_API_HASH")
worker_phone = os.getenv("WORKER_1_PHONE")
```

### **New Multi-Worker Structure:**
```python
# Multi-worker setup
workers = []
for i in range(1, 6):  # Support up to 5 workers
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

## **Step 5: Initialize All Workers**

### **Updated Initialization Code:**
```python
async def initialize_workers():
    """Initialize all worker accounts."""
    global workers
    
    for worker in workers:
        try:
            # Create Telethon client for this worker
            worker['client'] = TelegramClient(
                f'session_worker_{worker["index"]}',
                worker['api_id'],
                worker['api_hash']
            )
            
            # Start the client
            await worker['client'].start(phone=worker['phone'])
            
            logger.info(f"✅ Worker {worker['index']} initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize worker {worker['index']}: {e}")
            worker['client'] = None
```

## **Step 6: Distribute Work Across Workers**

### **Load Balancing Strategy:**
```python
async def get_available_worker():
    """Get the next available worker in round-robin fashion."""
    global current_worker_index
    
    available_workers = [w for w in workers if w['client'] and w['client'].is_connected()]
    
    if not available_workers:
        return None
    
    # Round-robin selection
    worker = available_workers[current_worker_index % len(available_workers)]
    current_worker_index += 1
    
    return worker

async def send_ad_with_worker(ad_data, destination):
    """Send ad using an available worker."""
    worker = await get_available_worker()
    
    if not worker:
        logger.error("❌ No available workers")
        return False
    
    try:
        # Send the ad using this worker
        await worker['client'].send_message(destination, ad_data['content'])
        logger.info(f"✅ Ad sent via worker {worker['index']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Worker {worker['index']} failed: {e}")
        return False
```

## **Step 7: Test the Multi-Worker Setup**

### **Test Script:**
```python
async def test_workers():
    """Test all worker accounts."""
    for worker in workers:
        if worker['client']:
            try:
                # Test sending a message to yourself
                me = await worker['client'].get_me()
                logger.info(f"✅ Worker {worker['index']}: @{me.username}")
            except Exception as e:
                logger.error(f"❌ Worker {worker['index']} test failed: {e}")
```

## **Step 8: Restart Services**

After adding workers:

```bash
# Stop current services
pkill -f "python3 scheduler.py"

# Start with new configuration
source venv/bin/activate && python3 scheduler.py
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

## **Best Practices:**

### **Account Management:**
- **Use different phone numbers** for each worker
- **Avoid suspicious activity** patterns
- **Monitor account health** regularly
- **Rotate workers** to prevent bans

### **Technical Setup:**
- **Test each worker** individually first
- **Monitor logs** for worker status
- **Implement fallback** mechanisms
- **Track performance** per worker

### **Security:**
- **Keep API credentials** secure
- **Don't share** worker accounts
- **Monitor for** unauthorized access
- **Regular credential** rotation

## **Monitoring Multiple Workers:**

### **Add to your monitoring:**
```python
async def check_worker_health():
    """Check health of all workers."""
    for worker in workers:
        if worker['client']:
            try:
                await worker['client'].get_me()
                logger.info(f"✅ Worker {worker['index']} healthy")
            except:
                logger.error(f"❌ Worker {worker['index']} unhealthy")
```

**Ready to add more workers? Start with Step 1 and get those additional Telegram accounts!** 🚀 