# PaymentProcessor Documentation

## Overview

The `PaymentProcessor` class provides a comprehensive TON cryptocurrency payment system for ad slot subscriptions. It integrates with your existing database and subscription system to handle payment creation, verification, and subscription activation.

## Features

- **💰 TON Integration** - Native TON blockchain payments
- **🎯 Tier System** - Basic (1 slot), Pro (3 slots), Enterprise (5 slots)
- **⏰ Payment Expiry** - 30-minute payment timeouts
- **🔍 Blockchain Verification** - Real-time payment verification
- **🔄 Auto Cleanup** - Background cleanup of expired payments
- **📊 Price Caching** - Cached TON price updates
- **🛡️ Error Handling** - Comprehensive error handling and logging

## Tier System

| Tier | Slots | Price | Duration |
|------|-------|-------|----------|
| Basic | 1 | $15 | 30 days |
| Pro | 3 | $45 | 30 days |
| Enterprise | 5 | $75 | 30 days |

## Environment Variables

Set these environment variables for TON integration:

```bash
# TON Merchant Wallet (where payments are received)
TON_MERCHANT_WALLET=EQD4FPq-PRDieyQKkizFTRtSDyucUIqrj0v_zXJmqaDp6_0t

# TON API Key (get from https://toncenter.com/)
TON_API_KEY=your_ton_api_key_here
```

## Installation

Install required dependencies:

```bash
pip install pytonlib aiohttp
```

## Usage

### Basic Initialization

```python
from src.payment_processor import PaymentProcessor
from src.database import DatabaseManager
import logging

# Initialize
db_manager = DatabaseManager('data/bot.db', logger)
payment_processor = PaymentProcessor(db_manager, logger)
await payment_processor.initialize()
```

### Create Payment Request

```python
# Create a payment request for basic tier
payment_request = await payment_processor.create_payment_request(
    user_id=12345,
    tier='basic',
    amount_usd=15
)

if payment_request.get('success') is False:
    print(f"Error: {payment_request.get('error')}")
else:
    print(f"Payment ID: {payment_request['payment_id']}")
    print(f"Amount: {payment_request['amount_ton']} TON")
    print(f"Payment URL: {payment_request['payment_url']}")
```

### Verify Payment

```python
# Verify if payment has been received
verification = await payment_processor.verify_payment(payment_id)

if verification['success'] and verification.get('payment_verified'):
    print("✅ Payment verified on blockchain")
else:
    print("❌ Payment not yet received")
```

### Process Successful Payment

```python
# Process a successful payment and activate subscription
result = await payment_processor.process_successful_payment(payment_id)

if result['success']:
    print(f"✅ Subscription activated for user {result['user_id']}")
    print(f"Tier: {result['tier']}")
    print(f"Slots: {result['slots']}")
else:
    print(f"❌ Error: {result.get('error')}")
```

### Check Payment Status

```python
# Get detailed payment status
status = await payment_processor.get_payment_status(payment_id)

print(f"Status: {status['payment']['status']}")
print(f"Expired: {status['is_expired']}")
print(f"Verification: {status.get('verification')}")
```

### Cleanup Expired Payments

```python
# Clean up expired payments
cleanup_result = await payment_processor.cleanup_expired_payments()

print(f"Cleaned {cleanup_result.get('cleaned_count', 0)} expired payments")
```

## Core Methods

### `async def create_payment_request(user_id, tier, amount_usd=15)`
Creates a new TON payment request:
- Validates tier and amount
- Gets current TON price
- Calculates TON amount
- Creates payment URL
- Records payment in database
- Creates ad slots for user

### `async def verify_payment(payment_id)`
Verifies payment on TON blockchain:
- Checks payment exists and is pending
- Verifies payment hasn't expired
- Queries blockchain for transactions
- Returns verification status

### `async def process_successful_payment(payment_id)`
Processes successful payment:
- Updates payment status to completed
- Determines tier from amount
- Activates user subscription
- Returns processing result

### `async def cleanup_expired_payments()`
Cleans up expired payments:
- Finds expired pending payments
- Marks them as expired
- Returns cleanup statistics

## Database Integration

### Payment Flow

1. **Create Payment** → `record_payment()` → `payments` table
2. **Verify Payment** → `get_payment()` → Check blockchain
3. **Process Payment** → `update_payment_status()` → `activate_subscription()`
4. **Cleanup** → `get_pending_payments()` → Mark expired

### Tables Used

- **`payments`** - Payment records and status
- **`users`** - User subscription information
- **`ad_slots`** - Created ad slots for users

## TON Integration

### Payment URLs

Payment URLs are created in format:
```
ton://transfer/{merchant_wallet}?amount={ton_amount}&text={payment_id}
```

### Blockchain Verification

The system verifies payments by:
1. Getting merchant wallet balance
2. Checking recent transactions
3. Matching payment amount and timestamp
4. Verifying payment ID in transaction text

### Price Updates

TON price is fetched from CoinGecko API and cached for 5 minutes to reduce API calls.

## Error Handling

### Common Errors

1. **TON API Unavailable** - Falls back to mock mode
2. **Price Fetch Failed** - Uses cached price or fallback
3. **Payment Expired** - Automatic cleanup
4. **Blockchain Verification Failed** - Retry logic

### Error Responses

```python
{
    'success': False,
    'error': 'Error description'
}
```

## Configuration

### Tier Configuration

```python
tiers = {
    'basic': {
        'slots': 1,
        'price_usd': 15,
        'duration_days': 30
    },
    'pro': {
        'slots': 3,
        'price_usd': 45,
        'duration_days': 30
    },
    'enterprise': {
        'slots': 5,
        'price_usd': 75,
        'duration_days': 30
    }
}
```

### Timeout Settings

```python
payment_timeout_minutes = 30  # Payment expiry
cleanup_interval = 3600       # Cleanup frequency (1 hour)
price_cache_duration = 300    # Price cache (5 minutes)
```

## Background Tasks

### Automatic Cleanup

The PaymentProcessor runs a background task that:
- Checks for expired payments every hour
- Marks expired payments as failed
- Logs cleanup statistics

### Price Caching

TON price is automatically cached to:
- Reduce API calls
- Improve performance
- Handle API failures gracefully

## Integration with Bot

### Bot Commands

```python
# In your bot command handlers
async def subscribe_command(update, context):
    user_id = update.effective_user.id
    
    # Create payment request
    payment_request = await payment_processor.create_payment_request(
        user_id=user_id,
        tier='basic'
    )
    
    # Send payment URL to user
    await update.message.reply_text(
        f"💳 Please pay {payment_request['amount_ton']} TON:\n"
        f"{payment_request['payment_url']}\n\n"
        f"⏰ Expires in 30 minutes"
    )
```

### Payment Monitoring

```python
# Monitor payments in background
async def monitor_payments():
    while True:
        # Get pending payments
        pending_payments = await db_manager.get_pending_payments(30)
        
        for payment in pending_payments:
            # Verify payment
            verification = await payment_processor.verify_payment(payment['payment_id'])
            
            if verification.get('payment_verified'):
                # Process successful payment
                await payment_processor.process_successful_payment(payment['payment_id'])
                
                # Notify user
                await bot.send_message(
                    chat_id=payment['user_id'],
                    text="✅ Payment received! Your subscription is now active."
                )
        
        await asyncio.sleep(60)  # Check every minute
```

## Testing

### Mock Mode

When TON API is unavailable, the system runs in mock mode:
- Payment verification always succeeds
- No actual blockchain queries
- Useful for development and testing

### Test Environment

```python
# Set test environment variables
os.environ['TON_MERCHANT_WALLET'] = 'test_wallet_address'
os.environ['TON_API_KEY'] = 'test_api_key'

# Initialize in test mode
payment_processor = PaymentProcessor(db_manager, logger)
await payment_processor.initialize()
```

## Security Considerations

### Wallet Security

- Use a dedicated merchant wallet
- Never share private keys
- Monitor wallet for suspicious activity
- Use hardware wallets for large amounts

### API Security

- Secure your TON API key
- Use HTTPS for all API calls
- Implement rate limiting
- Monitor API usage

### Payment Validation

- Verify payment amounts match exactly
- Check payment timestamps
- Validate payment IDs
- Implement duplicate payment detection

## Troubleshooting

### Common Issues

1. **Payment Not Verified**
   - Check merchant wallet address
   - Verify TON API key
   - Check network connectivity
   - Review transaction details

2. **Price Fetch Failed**
   - Check internet connectivity
   - Verify CoinGecko API status
   - Review API rate limits
   - Check cached price

3. **Subscription Not Activated**
   - Verify payment status
   - Check database connectivity
   - Review user permissions
   - Check tier configuration

### Debug Mode

```python
import logging
logging.getLogger('payment_processor').setLevel(logging.DEBUG)
```

This PaymentProcessor provides a robust, secure solution for TON cryptocurrency payments with comprehensive error handling, monitoring, and integration capabilities. 