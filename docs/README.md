# AutoFarming Telegram Bot

A comprehensive Telegram bot for automated ad posting and management with TON cryptocurrency payment processing.

## 🚀 Features

### Core Functionality
- **Automated Ad Posting**: Schedule and manage ads across multiple Telegram groups
- **TON Payment Processing**: Accept cryptocurrency payments for subscriptions
- **Multi-tier Subscriptions**: Basic, Premium, and VIP subscription levels
- **Category-based Targeting**: Post ads to specific group categories (crypto, discord, etc.)
- **Real-time Analytics**: Track ad performance and user engagement
- **Referral System**: Earn rewards by referring new users

### Technical Features
- **Asynchronous Architecture**: Built with `asyncio` for high performance
- **PostgreSQL Database**: Robust data storage and management
- **Telethon Integration**: Advanced Telegram client for automated posting
- **Payment Verification**: Blockchain-based TON payment verification
- **Modular Design**: Clean, maintainable codebase

## 📋 Requirements

- Python 3.10+
- PostgreSQL database
- Telegram Bot API token
- TON wallet for payments
- Telethon session files for worker accounts

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd my-telegram-bot
```

### 2. Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Create a `.env` file in the `config/` directory:
```env
# Bot Configuration
BOT_TOKEN=your_telegram_bot_token
ADMIN_USER_ID=your_admin_user_id

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# TON Configuration
TON_WALLET_ADDRESS=your_ton_wallet_address
TON_API_KEY=your_ton_api_key

# Worker Accounts (Telethon)
WORKER_ACCOUNT_1=phone_number_1
WORKER_ACCOUNT_2=phone_number_2
# Add more worker accounts as needed
```

### 5. Set Up Database
```bash
# Create PostgreSQL database
createdb your_database_name

# Run database migrations (if any)
python database.py
```

## 🚀 Quick Start

### Start All Services
```bash
chmod +x start_all_services.sh
./start_all_services.sh
```

This will start:
- Main bot (`bot.py`)
- Payment monitor (`payment_monitor.py`)
- Ad scheduler (`scheduler.py`)
- Maintenance service (`maintenance.py`)

### Manual Start
```bash
# Start main bot
python3 bot.py &

# Start payment monitor
python3 payment_monitor.py &

# Start scheduler
python3 scheduler.py &

# Start maintenance
python3 maintenance.py &
```

## 📖 Usage

### For Users
1. **Start the Bot**: Send `/start` to your bot
2. **Subscribe**: Use `/subscribe` to choose a plan
3. **Create Ads**: Use `/my_ads` to manage your ad slots
4. **Set Destinations**: Choose which groups to post to
5. **Schedule Posts**: Set timing for your ads

### For Admins
1. **Add Groups**: Use `/admin` to manage target groups
2. **Monitor Payments**: Check payment status and statistics
3. **View Analytics**: Get detailed performance reports
4. **Manage Users**: Handle user subscriptions and support

## 🏗️ Project Structure

```
my-telegram-bot/
├── bot.py                 # Main bot application
├── config/               # Configuration files
│   ├── .env             # Environment variables
│   └── config.py        # Configuration management
├── commands/            # Bot command handlers
│   ├── admin_commands.py
│   └── user_commands.py
├── database.py          # Database operations
├── ton_payments.py      # TON payment processing
├── payment_monitor.py   # Payment monitoring service
├── scheduler.py         # Ad scheduling service
├── maintenance.py       # Maintenance tasks
├── analytics.py         # Analytics and reporting
├── referral_system.py   # Referral program
├── content_moderation.py # Content filtering
├── start_all_services.sh # Service startup script
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── USER_GUIDE.md       # User documentation
└── TEST_INSTRUCTIONS.md # Testing guide
```

## 🔧 Configuration

### Bot Settings
- **Admin User ID**: Set in `.env` file
- **Subscription Tiers**: Configure pricing in `database.py`
- **Payment Timeout**: Adjust in `ton_payments.py`
- **Posting Intervals**: Modify in `scheduler.py`

### Database Schema
The bot uses PostgreSQL with tables for:
- Users and subscriptions
- Ad slots and content
- Payment transactions
- Group management
- Analytics data

## 🧪 Testing

Run the test suite to verify functionality:
```bash
python test_bot.py
python test_payments.py
python test_ad_management.py
python test_admin.py
python test_analytics.py
```

## 📊 Monitoring

### Log Files
- `bot_output.log`: Main bot activity
- `payment_monitor.log`: Payment processing
- `scheduler.log`: Ad scheduling
- `maintenance.log`: Maintenance tasks

### Health Checks
```bash
# Check service status
ps aux | grep python

# View recent logs
tail -f bot_output.log
```

## 🔒 Security

- Environment variables for sensitive data
- Database connection pooling
- Input validation and sanitization
- Rate limiting on bot commands
- Secure payment processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the `USER_GUIDE.md` for detailed instructions
- Review `TEST_INSTRUCTIONS.md` for troubleshooting
- Contact the development team

## 🔄 Updates

The bot is actively maintained with regular updates for:
- Security patches
- New features
- Performance improvements
- Bug fixes

---

**Note**: This bot is designed for legitimate advertising purposes. Please ensure compliance with Telegram's Terms of Service and local regulations. 