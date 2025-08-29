#!/usr/bin/env python3
"""
Fix Payment Button Callback Issue
"""

import re

def fix_payment_button_callback():
    """Fix the payment button callback to ensure it responds properly."""
    
    try:
        with open('commands/user_commands.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find and fix the check_payment_status_callback method
        # Add better error handling and ensure callback is always answered
        
        fixed_callback = '''
async def check_payment_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
    """Check payment status and process if completed."""
    query = update.callback_query
    
    try:
        # Always answer the callback query first to prevent hanging
        await query.answer("Checking payment status...")
        
        # Get payment status using multi-crypto processor
        from multi_crypto_payments import MultiCryptoPaymentProcessor
        payment_processor = MultiCryptoPaymentProcessor(context.bot_data['config'], context.bot_data['db'], context.bot_data['logger'])
        
        # Get payment status
        status = await payment_processor.get_payment_status(payment_id)
        
        if status['status'] == 'not_found':
            await query.edit_message_text(f"❌ Payment not found: {status.get('message', 'Unknown error')}")
            return
        
        if status['status'] == 'error':
            await query.edit_message_text(f"❌ Error checking payment: {status.get('message', 'Unknown error')}")
            return
        
        if status['status'] == 'completed':
            # Payment already completed
            keyboard = [
                [InlineKeyboardButton("📊 My Status", callback_data="cmd:status")],
                [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
            ]
            text = (
                "✅ Payment Completed!\\n\\n"
                f"Your subscription has been activated.\\n"
                f"Payment ID: {payment_id}\\n\\n"
                "You can now use your ad slots."
            )
        elif status['status'] == 'pending':
            # Check if payment has been received
            verification = await payment_processor.verify_payment_on_blockchain(payment_id)
            
            if verification:
                # Payment verified - subscription is automatically activated
                keyboard = [
                    [InlineKeyboardButton("📊 My Status", callback_data="cmd:status")],
                    [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
                ]
                text = (
                    "🎉 Payment Verified!\\n\\n"
                    f"✅ Subscription activated successfully!\\n"
                    f"🆔 Payment ID: {payment_id}\\n\\n"
                    "You can now use your ad slots!"
                )
            else:
                # Payment still pending
                from datetime import datetime
                check_time = datetime.now().strftime("%H:%M:%S")
                keyboard = [
                    [InlineKeyboardButton("🔄 Check Again", callback_data=f"check_payment:{payment_id}")],
                    [InlineKeyboardButton("❌ Cancel Payment", callback_data=f"cancel_payment:{payment_id}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
                ]
                text = (
                    "⏳ Payment Pending\\n\\n"
                    f"We're still waiting for your payment.\\n"
                    f"Payment ID: {payment_id}\\n"
                    f"Last checked: {check_time}\\n\\n"
                    "Please ensure you sent the correct amount.\\n"
                    "Click 'Check Again' in 30 seconds."
                )
        elif status['status'] == 'expired':
            keyboard = [
                [InlineKeyboardButton("💳 Create New Payment", callback_data="cmd:subscribe")],
                [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
            ]
            text = (
                "⏰ Payment Expired\\n\\n"
                f"Payment ID: {payment_id}\\n\\n"
                "Please create a new payment request."
            )
        else:
            keyboard = [
                [InlineKeyboardButton("💳 Create New Payment", callback_data="cmd:subscribe")],
                [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
            ]
            text = (
                f"❓ Payment Status: {status['status']}\\n\\n"
                f"Payment ID: {payment_id}\\n\\n"
                "Please contact support for assistance."
            )
        
        # Remove markdown formatting to avoid parsing issues
        clean_text = text.replace("**", "").replace("`", "")
        
        try:
            await query.edit_message_text(clean_text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as edit_error:
            # If message editing fails, try to send a new message
            logger.warning(f"Failed to edit message: {edit_error}")
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=clean_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
    except Exception as e:
        logger.error(f"Error in check_payment_status_callback: {e}")
        try:
            await query.edit_message_text(f"❌ Error checking payment: {str(e)}")
        except:
            # If editing fails, send new message
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=f"❌ Error checking payment: {str(e)}"
            )
'''
        
        # Replace the existing method
        if 'async def check_payment_status_callback' in content:
            # Find the method start and end
            start_pattern = r'async def check_payment_status_callback\(.*?\):'
            end_pattern = r'async def cancel_payment_callback'
            
            # Replace the method
            new_content = re.sub(
                start_pattern + r'.*?' + end_pattern,
                fixed_callback.strip() + '\n\n    ' + end_pattern,
                content,
                flags=re.DOTALL
            )
            
            content = new_content
            print("✅ Fixed check_payment_status_callback method")
        else:
            print("❌ Could not find check_payment_status_callback method")
            return False
        
        # Write the fixed content back
        with open('commands/user_commands.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Payment button callback fix applied successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix payment button callback: {e}")
        return False

if __name__ == "__main__":
    print("🔧 FIXING PAYMENT BUTTON CALLBACK")
    print("=" * 50)
    
    if fix_payment_button_callback():
        print("✅ Payment button callback fix completed")
        print("📋 Changes made:")
        print("1. Added immediate callback answer to prevent hanging")
        print("2. Improved error handling")
        print("3. Added fallback message sending if editing fails")
        print("4. Removed markdown formatting that could cause issues")
    else:
        print("❌ Failed to fix payment button callback")
