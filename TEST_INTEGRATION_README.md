# AutoFarming Bot Integration Test Suite

This comprehensive integration test suite validates all major components of the AutoFarming Bot system, ensuring everything works together correctly.

## 🎯 What It Tests

### 1. **Worker Rotation** (`test_worker_rotation`)
- ✅ Worker availability checking
- ✅ Worker usage tracking
- ✅ Cooldown management
- ✅ Rotation logic
- ✅ Worker health monitoring

### 2. **Test Group Posting** (`test_test_group_posting`)
- ✅ Managed group retrieval
- ✅ Test ad slot creation
- ✅ Content management
- ✅ Posting simulation (without actual posting)
- ✅ Post logging

### 3. **Payment Creation & Verification** (`test_payment_creation_and_verification`)
- ✅ Payment creation with unique IDs
- ✅ Payment retrieval and status checking
- ✅ Pending payment monitoring
- ✅ Payment verification simulation
- ✅ Subscription activation after payment

### 4. **Complete User Flow** (`test_complete_user_flow`)
- ✅ User registration
- ✅ Subscription selection
- ✅ Payment processing
- ✅ Subscription activation
- ✅ Ad slot creation
- ✅ Content setup
- ✅ Destination configuration
- ✅ Posting cycle simulation

### 5. **Database Operations** (`test_database_operations`)
- ✅ User CRUD operations
- ✅ Subscription management
- ✅ Ad slot operations
- ✅ Group management
- ✅ Statistics retrieval

## 🚀 How to Run

### Basic Usage
```bash
# Run all tests
python3 test_integration.py

# Or use the test runner
python3 run_integration_tests.py
```

### Advanced Usage
```bash
# Run specific test category
python3 run_integration_tests.py --test worker
python3 run_integration_tests.py --test payment
python3 run_integration_tests.py --test posting
python3 run_integration_tests.py --test flow

# Run with verbose logging
python3 run_integration_tests.py --verbose

# Run quick tests only
python3 run_integration_tests.py --quick
```

## 📊 Understanding Results

### Test Output
The test suite provides detailed logging for each step:

```
🧪 AutoFarming Bot Integration Test Suite
==================================================
🚀 Initializing Integration Test Suite...
✅ Configuration loaded successfully
✅ Database initialized successfully
✅ All components initialized successfully
🎯 Integration test suite ready!
🔄 Testing Worker Rotation...
📊 Found 5 available workers
🧪 Testing worker 1
✅ Worker usage updated
⏰ Worker cooldown status: False
✅ Worker rotation completed
✅ Worker rotation test completed successfully
```

### Test Report
At the end, you'll get a comprehensive report:

```
📈 TEST RESULTS SUMMARY:
Total Tests: 5
Passed: 5
Failed: 0
Success Rate: 100.0%

📋 DETAILED RESULTS:
✅ worker_rotation: PASS
✅ payment_creation_verification: PASS
✅ test_group_posting: PASS
✅ complete_user_flow: PASS
✅ database_operations: PASS

🎉 ALL TESTS PASSED! Integration test suite completed successfully.
```

## 📁 Files Created

### Log Files
- `test_integration.log` - Detailed test execution logs
- Console output - Real-time test progress

### Test Data
The tests create temporary test data in your database:
- Test users (IDs: 123456789, 987654321, 555666777, 111222333)
- Test payments with unique IDs
- Test ad slots and content
- Test group entries

## 🔧 Configuration Requirements

### Environment Variables
Make sure these are set in your `.env` file:
```env
BOT_TOKEN=your_bot_token
DATABASE_URL=your_database_url
ADMIN_ID=your_admin_id
```

### Dependencies
The test suite requires:
- `python-dotenv` - For environment variable loading
- `asyncpg` - For database operations
- `python-telegram-bot` - For bot functionality
- All your custom modules (config, database, commands, etc.)

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
   ```
   ❌ Error importing test modules: No module named 'config'
   ```
   **Solution**: Make sure you're running from the project root directory.

2. **Database Connection Errors**
   ```
   ❌ Database initialization error: connection failed
   ```
   **Solution**: Check your `DATABASE_URL` in the `.env` file.

3. **Missing Components**
   ```
   ⚠️ Some components not available - limited testing
   ```
   **Solution**: Install missing dependencies or check file paths.

### Debug Mode
Run with verbose logging to see detailed information:
```bash
python3 run_integration_tests.py --verbose
```

## 📈 Test Coverage

### What's Tested
- ✅ Database operations and connections
- ✅ Worker management and rotation
- ✅ Payment processing workflow
- ✅ User subscription flow
- ✅ Ad slot management
- ✅ Content posting simulation
- ✅ Error handling and logging

### What's NOT Tested
- ❌ Actual Telegram API calls (to avoid spam)
- ❌ Real blockchain transactions
- ❌ Actual worker account authentication
- ❌ Real group joining/posting

## 🔄 Continuous Integration

### Automated Testing
You can integrate this into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run Integration Tests
  run: |
    python3 run_integration_tests.py --verbose
    if [ $? -ne 0 ]; then
      echo "Integration tests failed"
      exit 1
    fi
```

### Pre-deployment Testing
Run before deploying to production:
```bash
# Quick test before deployment
python3 run_integration_tests.py --quick

# Full test for major releases
python3 run_integration_tests.py --verbose
```

## 📝 Customization

### Adding New Tests
To add a new test, modify `test_integration.py`:

```python
async def test_your_new_feature(self):
    """Test your new feature."""
    logger.info("🧪 Testing Your New Feature...")
    
    try:
        # Your test logic here
        self.test_results['your_new_feature'] = 'PASS'
        logger.info("✅ Your new feature test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Your new feature test failed: {e}")
        self.test_results['your_new_feature'] = 'FAIL'
```

### Modifying Test Data
Adjust test user IDs, content, or other parameters in the test methods to match your specific requirements.

## 🎯 Best Practices

1. **Run tests before deployment** - Always test before pushing to production
2. **Check logs** - Review `test_integration.log` for detailed information
3. **Clean test data** - Remove test data from production databases
4. **Monitor performance** - Watch for slow database operations
5. **Update tests** - Keep tests in sync with code changes

## 📞 Support

If you encounter issues with the integration tests:

1. Check the logs in `test_integration.log`
2. Verify your environment configuration
3. Ensure all dependencies are installed
4. Run with `--verbose` for detailed debugging

The test suite is designed to be comprehensive yet safe, providing confidence that your bot system is working correctly without interfering with production data. 