# AutoFarming Bot Health Check System

This comprehensive health check system helps you identify and fix issues with your AutoFarming bot before they cause problems in production.

## 🚀 Quick Start

### 1. Quick Health Check (Recommended First Step)
```bash
python3 quick_health_check.py
```
This checks for critical issues that would prevent your bot from starting.

### 2. Comprehensive Health Check
```bash
python3 health_check.py
```
This runs a full diagnostic of all bot components.

## 📋 What Gets Checked

### Quick Health Check
- ✅ Environment file existence
- ✅ Required environment variables
- ✅ Critical dependencies
- ✅ Critical files existence
- ✅ Syntax errors in core files
- ✅ Import errors
- ✅ Commands directory structure

### Comprehensive Health Check
- ✅ Environment variables (required & optional)
- ✅ All dependencies (required & optional)
- ✅ Module imports
- ✅ Database connection and tables
- ✅ Bot configuration and token
- ✅ Command handlers
- ✅ Critical user flows
- ✅ File structure
- ✅ Syntax errors

## 🔧 Environment Variables Required

Create `config/.env` file with:

```env
# Required
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_ID=your_telegram_user_id
DATABASE_URL=postgresql://user:password@localhost/dbname

# Optional (for full functionality)
BTC_ADDRESS=your_btc_address
ETH_ADDRESS=your_eth_address
TON_ADDRESS=your_ton_address
ETHERSCAN_API_KEY=your_etherscan_key
BLOCKCYPHER_API_KEY=your_blockcypher_key
ENCRYPTION_KEY=your_encryption_key
SECRET_KEY=your_secret_key
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=production
```

## 📦 Dependencies

Install all required dependencies:

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or install manually
pip install python-telegram-bot==20.6 python-dotenv==1.0.0 aiohttp==3.9.1 asyncpg==0.29.0
```

## 📊 Understanding Results

### Quick Health Check Output
```
🔍 Quick Health Check for AutoFarming Bot
==================================================
📁 Checking config/.env file...
   ✅ config/.env file exists

🔧 Checking environment variables...
   ✅ All required environment variables are set

📦 Checking critical dependencies...
   ✅ All critical packages are installed

📄 Checking critical files...
   ✅ All critical files exist

🔍 Checking for syntax errors...
   ✅ No syntax errors found

📚 Checking critical imports...
   ✅ Critical modules can be imported

⌨️ Checking commands directory...
   ✅ commands directory structure looks good

==================================================
📊 QUICK HEALTH CHECK SUMMARY
==================================================
✅ No critical issues found!
🎉 Your bot should be able to start successfully
```

### Comprehensive Health Check Output
```
🏥 HEALTH CHECK SUMMARY
Overall Status: HEALTHY
Passed: 9/9
Failed: 0/9

📋 DETAILED RESULTS:
✅ environment_variables: PASS
✅ dependencies: PASS
✅ imports: PASS
✅ database: PASS
✅ bot_configuration: PASS
✅ command_handlers: PASS
✅ critical_user_flows: PASS
✅ file_structure: PASS
✅ syntax_errors: PASS

✅ Bot appears healthy - Ready for deployment!
```

## 🚨 Common Issues and Fixes

### 1. Missing Environment Variables
**Issue**: `❌ Missing required environment variables: BOT_TOKEN, ADMIN_ID`
**Fix**: 
```bash
# Create config/.env file
cp config/env_template.txt config/.env
# Edit config/.env with your values
```

### 2. Missing Dependencies
**Issue**: `❌ Missing critical packages: python-telegram-bot`
**Fix**:
```bash
pip install python-telegram-bot==20.6
```

### 3. Database Connection Issues
**Issue**: `❌ Database connection failed`
**Fix**:
```bash
# Check your DATABASE_URL in config/.env
# Ensure database server is running
# Verify credentials and permissions
```

### 4. Import Errors
**Issue**: `❌ Failed to import config: No module named 'config'`
**Fix**:
```bash
# Ensure you're running from project root
# Check file paths and __init__.py files
# Verify syntax in imported modules
```

### 5. Syntax Errors
**Issue**: `❌ Syntax error in bot.py: invalid syntax`
**Fix**:
```bash
# Check for missing colons, brackets, quotes
# Verify proper indentation
# Use a Python linter
```

## 📁 Generated Files

### Log Files
- `health_check.log` - Detailed execution logs
- `health_report.json` - Structured health report

### Report Structure
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "overall_status": "HEALTHY",
  "checks": {
    "environment_variables": {
      "status": "PASS",
      "missing_required": [],
      "missing_optional": ["BTC_ADDRESS"],
      "issues": [],
      "fixes": []
    }
  },
  "warnings": ["Missing optional variables: BTC_ADDRESS"],
  "success_count": 9,
  "total_checks": 9
}
```

## 🔄 Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Health Check
  run: |
    python3 quick_health_check.py
    if [ $? -ne 0 ]; then
      echo "Critical issues found - stopping deployment"
      exit 1
    fi
    
    python3 health_check.py
    if [ $? -ne 0 ]; then
      echo "Health check failed - review issues"
      exit 1
    fi
```

### Pre-deployment Script
```bash
#!/bin/bash
echo "Running pre-deployment health checks..."

# Quick check first
python3 quick_health_check.py
if [ $? -ne 0 ]; then
    echo "❌ Critical issues found - aborting deployment"
    exit 1
fi

# Full health check
python3 health_check.py
if [ $? -ne 0 ]; then
    echo "⚠️ Health check issues - review before deployment"
    exit 1
fi

echo "✅ Health checks passed - proceeding with deployment"
```

## 🎯 Best Practices

### 1. Run Health Checks Regularly
- Before each deployment
- After configuration changes
- When adding new features
- After dependency updates

### 2. Monitor Health Reports
- Review `health_report.json` for trends
- Track issues over time
- Use warnings to plan improvements

### 3. Fix Issues Promptly
- Address critical issues immediately
- Plan fixes for warnings
- Document solutions for team

### 4. Customize Checks
- Add project-specific checks
- Modify thresholds for your needs
- Include custom validation logic

## 🛠️ Troubleshooting

### Health Check Fails to Run
```bash
# Check Python version
python3 --version

# Check if running from correct directory
pwd
ls -la

# Check file permissions
chmod +x health_check.py
```

### Import Errors in Health Check
```bash
# Add project root to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run with module path
python3 -m health_check
```

### Database Connection Issues
```bash
# Test database connection manually
psql $DATABASE_URL -c "SELECT 1;"

# Check database server status
sudo systemctl status postgresql
```

## 📞 Support

If you encounter issues with the health check system:

1. **Check the logs**: Review `health_check.log` for detailed information
2. **Verify environment**: Ensure all required variables are set
3. **Test manually**: Try importing modules individually
4. **Check dependencies**: Verify all packages are installed correctly

The health check system is designed to catch issues early and provide clear guidance on how to fix them, helping you maintain a robust and reliable bot system. 