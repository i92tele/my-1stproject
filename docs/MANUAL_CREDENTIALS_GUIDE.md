# 🔧 **Manual Telegram API Credentials Guide**

## **When my.telegram.org Fails - Alternative Methods**

### **Method 1: Use the Script (Recommended)**

```bash
python3 get_telegram_credentials.py
```

This script will:
1. Ask for your worker phone numbers
2. Connect to each account using test API credentials
3. Generate session strings for each account
4. Create the .env format for you

### **Method 2: Manual Process**

If the script doesn't work, here's the manual process:

#### **Step 1: Get Your Own API Credentials**
1. **Try my.telegram.org again** with these exact settings:
   - App title: `My Helper`
   - Short name: `my_helper`
   - Platform: `Other`
   - Description: `Helper app`

2. **If that fails, try these alternatives:**
   - App title: `Test App`
   - Short name: `test_app`
   - Platform: `Desktop`
   - Description: `Testing`

#### **Step 2: Use Existing Session Files**
If you already have Telegram session files:

1. **Find your session files:**
   ```bash
   find ~/.local/share/TelegramDesktop/ -name "*.session"
   ```

2. **Use them directly** in your bot

#### **Step 3: Create Simple Test App**
Try creating the simplest possible app:
- App title: `Test`
- Short name: `test`
- Platform: `Desktop`
- Description: `Test`

### **Method 3: Use Telegram Bot API Directly**

If you can't get API credentials, we can modify the bot to use the Bot API directly instead of Telethon.

### **Method 4: Temporary Solution**

For now, you can:
1. **Use the test API credentials** (2040/b18441a1ff607e10a989891a5462e627)
2. **Get your own credentials later** when the web interface works
3. **Test with 1-2 workers first**

## **Quick Test:**

Let's try the script first:

```bash
python3 get_telegram_credentials.py
```

**What phone numbers do you want to add as workers?** Enter them one by one when prompted. 