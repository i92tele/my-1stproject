# AutoFarming Bot - Telegram Automated Ad Posting System

## 🚀 Overview

A comprehensive Telegram bot system for automated ad posting with cryptocurrency payments, worker management, and anti-ban protection. The bot provides subscription-based ad posting services with intelligent worker rotation, automatic group joining, and multi-cryptocurrency payment support.

## ✨ Features

### 🤖 **Core Bot Functionality**
- **User Management**: Complete subscription system with tier-based access
- **Ad Slot Management**: Create, edit, and manage advertising campaigns
- **🆕 Admin Slots System**: 20 unlimited admin slots fully integrated into posting system
- **Admin Controls**: Broadcasting, statistics, user management, service monitoring
- **Interactive Interface**: Inline keyboards, conversation handlers, callback queries

### 📅 **Automated Posting System**
- **Intelligent Scheduling**: Automated ad posting with customizable intervals
- **Worker Rotation**: Multiple Telegram accounts with intelligent rotation
- **🆕 Forum Topic Posting**: Direct posting to specific forum topics (eliminates TOPIC_CLOSED errors)
- **Automatic Group Joining**: Workers automatically join groups before posting
- **Failed Group Tracking**: Database tracking of groups workers can't join
- **Anti-Ban Protection**: Randomized delays, content variation, session management
- **Performance Monitoring**: Real-time tracking of posting success rates

### 🎯 **Smart Destination Management**
- **🆕 Enhanced Bulk Import**: Preserves forum topic IDs during group imports
- **User-Specific Changes**: Stop & restart approach for destination changes
- **Pause/Resume System**: Clean transitions when users change destinations
- **Admin Monitoring**: Track paused slots and destination changes
- **Category-Based Destinations**: Easy group management by categories
- **Forum Topic Support**: Full support for `t.me/group/topic_id` destinations

### 🔧 **🆕 Advanced Admin Interface**
- **🆕 Bulk Operations**: Clear all content, destinations, or purge slots
- **🆕 Safety Features**: Confirmation dialogs for destructive operations
- **🆕 Complete Integration**: Admin slots appear in all monitoring commands
- **🆕 Navigation System**: Seamless back button functionality throughout interface
- **🆕 System Visibility**: `/posting_status`, `/capacity_check`, `/worker_status` show complete data

### 💰 **Payment Processing**
- **TON Cryptocurrency**: Fully implemented TON payment integration
- **Multi-Crypto Support**: BTC, ETH, USDT, USDC (in development)
- **Automatic Verification**: Payment detection and subscription activation
- **Price Conversion**: Real-time cryptocurrency price fetching

### 🛡️ **Security & Monitoring**
- **Health Monitoring**: Comprehensive system health checks
- **Session Management**: Proper Telegram session handling
- **🆕 Worker Authentication**: One-time setup with persistent sessions
- **Error Handling**: Robust error handling with detailed logging
- **Admin Permissions**: Secure admin-only functionality

## 🏗️ Project Architecture

### **Organized Structure**
```
my-1stproject/
├── src/                    # Modern organized modules
│   ├── bot/               # Bot core functionality
│   ├── database/          # Database management
│   ├── commands/          # Bot commands
│   ├── payments/          # Payment processing
│   ├── monitoring/        # Analytics & monitoring
│   └── utils/             # Utility functions
├── scheduler/             # Automated posting system
│   ├── core/             # Main scheduler logic
│   ├── workers/          # Worker management
│   ├── anti_ban/         # Anti-ban protection
│   ├── monitoring/       # Performance tracking
│   └── config/           # Configuration
├── scripts/               # Utility scripts
├── config/               # Configuration files
├── sessions/             # Telegram session files
└── [legacy files]        # Original working system
```

### **Dual Architecture Benefits**
- **Legacy System**: Maintains original functionality for backwards compatibility
- **Modern Structure**: Organized modular architecture for scalable development
- **Seamless Migration**: Both systems work independently and can be used simultaneously

## 🚀 Quick Start

### **Prerequisites**
- Python 3.8+
- Virtual environment (recommended)
- Telegram Bot Token
- Worker Telegram accounts
- TON wallet address

### **Installation**

1. **Clone and Setup**
   ```bash
   cd my-1stproject
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   # Edit config/.env with your credentials
   nano config/.env
   ```

3. **🆕 Authenticate Workers**
   ```bash
   # One-time setup for worker accounts
   python3 setup_workers.py
   ```

4. **Run Health Check**
   ```bash
   python3 health_check.py
   ```

5. **Start the Bot** (Legacy)
   ```bash
   python3 bot.py
   ```

6. **Start the Scheduler**
   ```bash
   python3 -m scheduler
   ```

## 🆕 **New Features (August 12, 2025)**

### **🤖 Automatic Group Joining**
- **Smart Join System**: Workers automatically join groups before posting
- **Multiple Format Support**: `@username`, `t.me/username`, `https://t.me/username`
- **Rate Limiting**: Per-worker (3/day) and global (10/day) limits
- **Failed Group Tracking**: Database logging of groups workers can't join
- **Admin Management**: `/failed_groups` and `/retry_group` commands

### **🎯 User-Specific Destination Changes**
- **Stop & Restart Approach**: Clean transitions when users change destinations
- **User Isolation**: Only affects the changing user, others continue normally
- **Pause/Resume System**: Temporary pause during destination updates
- **Admin Monitoring**: `/paused_slots` command to track paused slots
- **Clear Notifications**: Users get detailed feedback about changes

### **🔧 Worker Authentication**
- **One-Time Setup**: `setup_workers.py` script for authentication
- **Persistent Sessions**: Session files for automatic login
- **2FA Support**: Handles two-factor authentication
- **Multiple Workers**: Supports multiple worker accounts
- **Automatic Detection**: Identifies real vs placeholder credentials

## 📊 **Admin Commands**

### **🆕 New Admin Commands**
- `/failed_groups` - View groups workers failed to join
- `/retry_group @username` - Remove group from failed list
- `/paused_slots` - Monitor paused ad slots
- `/bulk_add_groups` - Add multiple groups at once

### **Existing Admin Commands**
- `/admin_stats` - System statistics and health
- `/worker_status` - Worker account status
- `/payment_stats` - Payment statistics
- `/user_list` - List all registered users

## 🧪 **Testing**

### **🆕 New Test Scripts**
```bash
# Test group joining functionality
python3 test_group_joining.py

# Test destination change system
python3 test_destination_change.py
```

### **Health Checks**
```bash
# System health check
python3 health_check.py

# Database schema verification
python3 -c "import sqlite3; conn = sqlite3.connect('bot_database.db'); print('Database OK')"
```

## 📈 **Performance & Monitoring**

### **🆕 Group Joining Metrics**
- Success rate tracking
- Failed group analysis
- Rate limit monitoring
- Worker performance metrics

### **Destination Change Monitoring**
- Pause/resume tracking
- User change patterns
- System performance impact
- Error rate monitoring

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Bot Configuration
BOT_TOKEN=your_bot_token
ADMIN_ID=your_admin_id

# Database
DATABASE_URL=bot_database.db

# Worker Accounts
WORKER_1_API_ID=your_api_id
WORKER_1_API_HASH=your_api_hash
WORKER_1_PHONE=your_phone_number
```

### **🆕 New Configuration Options**
- Group joining rate limits
- Pause duration settings
- Failed group retention
- Worker authentication settings

## 🛡️ **Security Features**

### **🆕 Enhanced Security**
- **Worker Session Management**: Secure session handling
- **Rate Limiting**: Anti-ban protection for group joining
- **User Isolation**: Secure user-specific operations
- **Admin Monitoring**: Comprehensive admin oversight

### **Existing Security**
- **Admin Permissions**: Secure admin-only functionality
- **Database Concurrency**: WAL mode with proper locking
- **Error Handling**: Comprehensive error logging
- **Session Management**: Proper Telegram session handling

## 📚 **Documentation**

### **🆕 New Documentation**
- `GROUP_JOINING_IMPLEMENTATION.md` - Group joining system guide
- `DESTINATION_CHANGE_IMPLEMENTATION.md` - Destination change system guide
- `test_group_joining.py` - Group joining test suite
- `test_destination_change.py` - Destination change test suite

### **Existing Documentation**
- `DEVELOPMENT_PROGRESS.md` - Development progress tracking
- `health_check.py` - System health monitoring
- `requirements.txt` - Dependencies list

## 🎯 **Use Cases**

### **🆕 New Use Cases**
1. **Automatic Group Management**: Workers join groups automatically
2. **Clean Destination Changes**: Users change destinations without confusion
3. **Failed Group Recovery**: Admins can retry failed group joins
4. **Worker Authentication**: One-time setup for persistent worker sessions

### **Existing Use Cases**
1. **Automated Ad Posting**: Schedule and post ads automatically
2. **Multi-Crypto Payments**: Accept various cryptocurrencies
3. **Subscription Management**: Tier-based access control
4. **Performance Monitoring**: Track posting success rates

## 🚀 **Production Readiness**

### **🆕 Production Features**
- **Comprehensive Testing**: All new features tested
- **Error Handling**: Robust error handling throughout
- **Admin Tools**: Complete admin monitoring and management
- **User Experience**: Polished user interface and feedback

### **Status**: ✅ **BETA LAUNCH READY**
- ✅ **Admin Slots System**: Fully integrated into posting infrastructure
- ✅ **Forum Topic Posting**: Complete Telethon integration, eliminates TOPIC_CLOSED errors
- ✅ **Bulk Import Enhancement**: Preserves forum topic IDs during imports
- ✅ **Navigation System**: All back buttons and interface flows working properly
- ✅ **Comprehensive Monitoring**: All admin commands show complete system state
- ✅ **Database Migration**: Automatic and manual migration strategies implemented
- ✅ **Quality Implementation**: Safety features, error prevention, deep integration

### **New Features Completed Today (August 13, 2025)**:
- **Admin Slots Integration**: 20 unlimited admin slots now fully functional in posting system
- **Forum Topic Posting**: Direct posting to specific forum topics (e.g., `t.me/social/68316`)
- **Enhanced Bulk Import**: Forum topic IDs preserved during `/bulk_add_groups`
- **Interface Improvements**: Bulk operations, confirmation dialogs, seamless navigation
- **System Visibility**: All monitoring commands include admin slots in reports

### **Critical Pre-Launch Action**:
🚨 **Must execute before testing**: `python3 fix_admin_slots_migration.py`

---

**Last Updated**: August 13, 2025
**Version**: 2.1 (Beta Launch Release)
**Status**: **Ready for Beta Launch Tomorrow**