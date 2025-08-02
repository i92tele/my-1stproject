# 🤖 AutoFarming Bot - User Guide

## 🚀 Quick Start

### 1. **Start Your Bot**
```bash
./start_all_services.sh
```

### 2. **Test Your Bot**
1. Open Telegram
2. Search for your bot username
3. Send `/start` to begin

## 📱 Bot Commands

### **For Users:**
- `/start` - Welcome message and main menu
- `/help` - Show available commands
- `/my_ads` - Manage your ad campaigns
- `/subscribe` - View subscription plans
- `/analytics` - View your performance stats
- `/referral` - Get your referral code

### **For Admins:**
- `/add_group` - Add a group for ads
- `/list_groups` - View all managed groups
- `/remove_group` - Remove a group
- `/admin_stats` - View bot statistics
- `/verify_payment` - Manually verify payments
- `/revenue_stats` - View revenue data
- `/pending_payments` - Check pending payments

## 💰 Subscription Plans

### **Basic Plan** - $9.99/month
- 1 ad slot
- Basic analytics
- Email support

### **Pro Plan** - $39.99/month
- 5 ad slots
- Advanced analytics
- Priority support
- Custom scheduling

### **Enterprise Plan** - $99.99/month
- 15 ad slots
- Full analytics suite
- Dedicated support
- Custom features

## 🔧 Management Commands

### **Start All Services:**
```bash
./start_all_services.sh
```

### **Stop All Services:**
```bash
pkill -f 'python.*\.py'
```

### **View Logs:**
```bash
# Main bot logs
tail -f bot_output.log

# All service logs
tail -f logs/*.log

# Specific service logs
tail -f logs/scheduler.log
tail -f logs/payment_monitor.log
tail -f logs/maintenance.log
```

### **Restart Services:**
```bash
# Stop all
pkill -f 'python.*\.py'

# Start all
./start_all_services.sh
```

## 📊 Monitoring

### **Check Service Status:**
```bash
ps aux | grep python | grep -v grep
```

### **View Recent Activity:**
```bash
tail -20 bot_output.log
```

### **Check Database:**
```bash
# Test database connection
python3 -c "from database import DatabaseManager; from config import BotConfig; print('Database OK')"
```

## 🛠️ Troubleshooting

### **Bot Not Responding:**
1. Check if services are running: `ps aux | grep python`
2. View error logs: `tail -f bot_output.log`
3. Restart services: `./start_all_services.sh`

### **Database Issues:**
1. Check PostgreSQL is running: `sudo systemctl status postgresql`
2. Test connection: `python3 -c "from database import DatabaseManager; print('DB OK')"`

### **Payment Issues:**
1. Check TON wallet configuration in `config/.env`
2. View payment logs: `tail -f logs/payment_monitor.log`

## 📈 Analytics

### **User Analytics:**
- Total users
- Active subscriptions
- Revenue generated
- Ad performance

### **System Analytics:**
- Service uptime
- Error rates
- Database performance
- Payment success rates

## 🔐 Security

### **Environment Variables:**
All sensitive data is stored in `config/.env`:
- Bot token
- Database credentials
- TON wallet address
- Worker account credentials

### **Backup:**
- Database backups in `backups/` directory
- Log files in `logs/` directory
- Configuration backups in `config/.env.backup`

## 📞 Support

### **For Technical Issues:**
1. Check logs first
2. Restart services
3. Verify configuration
4. Check database connection

### **For User Support:**
- Users can contact you through the bot
- Admin commands for manual assistance
- Payment verification tools

## 🎯 Next Steps

1. **Test the bot** with `/start`
2. **Add some groups** for ads using `/add_group`
3. **Create test subscriptions** using the activation script
4. **Monitor performance** with analytics
5. **Scale up** as you get more users

---

**Your bot is now ready for production! 🚀** 