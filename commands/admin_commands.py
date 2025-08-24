from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import re
import sqlite3
from typing import Dict, List, Set, Optional
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Utility function to handle both callback and message contexts
async def send_admin_message(update: Update, text: str, reply_markup=None, parse_mode=None):
    """Send message handling both callback query and direct message contexts."""
    if update.callback_query:
        if reply_markup:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await update.callback_query.edit_message_text(text, parse_mode=parse_mode)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

# Import suggestions system if available
try:
    from commands.suggestion_commands import suggestion_manager
    SUGGESTIONS_AVAILABLE = True
except ImportError:
    SUGGESTIONS_AVAILABLE = False
    logger.warning("Suggestions system not available for admin commands")

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is an admin."""
    try:
        config = context.bot_data.get('config')
        if not config:
            logger.error("Config not available in context")
            return False
            
        user = update.effective_user
        if not user:
            logger.error("No effective user in update")
            return False
            
        user_id = user.id
        is_admin = config.is_admin(user_id)
        
        if is_admin:
            logger.info(f"Admin access granted to user {user_id}")
        else:
            logger.warning(f"Admin access denied to user {user_id}")
            
        return is_admin
        
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

def _parse_id_or_username(token: str) -> str:
    return token.strip()

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text replies for admin flows (custom category, add to category)."""
    try:
        if not await check_admin(update, context):
            return

        db = context.bot_data.get('db')
        text = (update.message.text or '').strip()

        # Custom category input
        if 'awaiting_custom_group_category' in context.user_data:
            group_id = context.user_data.pop('awaiting_custom_group_category')
            if db and text:
                ok = await db.update_managed_group_category(group_id, text)
                if ok:
                    await send_admin_message(update, f"✅ Category for `{group_id}` set to '{text}'.", parse_mode='Markdown')
                else:
                    await send_admin_message(update, "❌ Failed to update category.")
            return

        # Bulk add groups: category -> list of chats
        if context.user_data.get('awaiting_bulk_groups'):
            context.user_data.pop('awaiting_bulk_groups', None)
            if not db:
                await send_admin_message(update, "❌ Database not available.")
                return
            parsed = _parse_bulk_groups_text(text)
            if not parsed:
                await send_admin_message(update, "❌ Could not parse any categories or chats.")
                return
            total_added = 0
            total_skipped = 0
            duplicate_skips = 0
            # Track already-added group_ids to avoid reassigning category for duplicates
            seen_group_ids: Set[str] = set()
            for category, usernames in parsed.items():
                for uname in usernames:
                    gid = f"@{uname}" if not uname.startswith('@') else uname
                    if gid in seen_group_ids:
                        duplicate_skips += 1
                        continue
                    ok = await db.add_managed_group(gid, uname, category)
                    if ok:
                        total_added += 1
                        seen_group_ids.add(gid)
                    else:
                        total_skipped += 1
            await send_admin_message(update, 
                f"✅ Bulk import complete.\n"
                f"• Categories: {len(parsed)}\n"
                f"• Groups added: {total_added}\n"
                f"• Duplicates skipped: {duplicate_skips}\n"
                f"• Errors: {total_skipped}"
            )
            return

        # Add chats to category
        if 'awaiting_add_to_category' in context.user_data:
            category = context.user_data.pop('awaiting_add_to_category')
            if not db:
                await send_admin_message(update, "❌ Database not available.")
                return
            # Split by commas or whitespace
            tokens = [t for t in [s.strip() for s in text.replace(',', ' ').split()] if t]
            if not tokens:
                await send_admin_message(update, "❌ No chats provided.")
                return
            added = 0
            errors = 0
            for token in tokens:
                gid = _parse_id_or_username(token)
                # Use the token also as name if none; admin can rename later
                ok = await db.add_managed_group(gid, gid, category)
                if ok:
                    added += 1
                else:
                    errors += 1
            await send_admin_message(update, f"➕ Added {added} chats to category '{category}'.{' Errors: ' + str(errors) if errors else ''}")
            return

        # Admin slot content setting
        if 'awaiting_admin_content' in context.user_data:
            try:
                from commands import admin_slot_commands
                if hasattr(admin_slot_commands, 'handle_admin_content_message'):
                    handled = await admin_slot_commands.handle_admin_content_message(update, context)
                    if handled:
                        return
            except Exception as e:
                logger.error(f"Error handling admin content: {e}")
                await send_admin_message(update, "❌ Error processing admin content.")
                context.user_data.clear()
            return

    except Exception as e:
        logger.error(f"Error in handle_admin_text: {e}")
        await send_admin_message(update, "❌ Error processing input.")

def _parse_bulk_groups_text(text: str) -> Dict[str, Set[str]]:
    """Parses a pasted list of categories and t.me links into a map.

    Returns: {category_name: {username, ...}, ...}
    """
    results: Dict[str, Set[str]] = {}
    current_category: str = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Category lines end with ':'
        if line.endswith(':') and len(line) > 1:
            current_category = line[:-1].strip()
            if current_category not in results:
                results[current_category] = set()
            continue
        if not current_category:
            # Ignore lines before first category
            continue
        # Extract usernames from any t.me links in the line, preserving topic IDs
        for match in re.findall(r"(?:https?://)?t\.me/([A-Za-z0-9_]+(?:/\d+)?)", line):
            # Store username with topic ID if present
            if match and not match.isdigit():  # Ignore numeric-only IDs
                results[current_category].add(match)
    # Drop empty categories
    return {cat: users for cat, users in results.items() if users}

async def bulk_add_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts bulk import of groups by pasted list.

    Flow: admin sends /bulk_add_groups, then pastes the list in next message.
    """
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    context.user_data['awaiting_bulk_groups'] = True
    await send_admin_message(update, 
        "📥 Send the list in this format:\n\n"
        "Category A:\nhttps://t.me/username1\nhttps://t.me/username2/123\n\n"
        "Category B:\nhttps://t.me/another_chat\n...\n\n"
        "I will parse categories and add the chats. Duplicates are skipped."
    )

async def system_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run end-to-end health checks (no terminal required). Admin only."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    db = context.bot_data.get('db')
    if not db:
        await send_admin_message(update, "❌ Database not available in context.")
        return
    report_lines: List[str] = ["🧪 System Check Report"]
    passed = 0
    failed = 0
    async def step(desc: str, coro) -> None:
        nonlocal passed, failed
        try:
            res = await coro
            report_lines.append(f"✔ {desc}")
            passed += 1
            return res
        except Exception as e:
            report_lines.append(f"✖ {desc} -> {e}")
            failed += 1
            return None

    # 1) Schema sanity
    async def _schema_probe():
        # Light selects to ensure tables exist
        await db.get_all_users()
        await db.get_managed_groups()
        await db.get_active_ads_to_send()
    await step("Schema and tables reachable", _schema_probe())

    # 2) Create test user and subscription
    test_user_id = 987654321  # isolated test user id
    await step("Create/Update test user", db.create_or_update_user(test_user_id, username="system_check", first_name="System"))
    await step("Activate basic subscription (1 day)", db.activate_subscription(test_user_id, "basic", 1))
    sub = await step("Read back subscription", db.get_user_subscription(test_user_id))

    # 3) Create/get ad slots
    slots: Optional[List[Dict[str, object]]] = await step("Get or create ad slots for tier", db.get_or_create_ad_slots(test_user_id, "basic"))
    slot_id = None
    if isinstance(slots, list) and slots:
        slot_id = slots[0].get('id')
    if not slot_id:
        report_lines.append("✖ No slot available for testing")
        failed += 1
    else:
        # 4) Update content and schedule
        await step("Update ad content", db.update_ad_slot_content(int(slot_id), "System check content", None))
        await step("Set schedule 60 min", db.update_ad_slot_schedule(int(slot_id), 60))

        # 5) Set destinations from admin_all (up to 5)
        groups = await db.get_managed_groups("admin_all")
        destinations = []
        for g in (groups or [])[:5]:
            destinations.append({
                'destination_type': 'chat',
                'destination_id': g.get('group_id') or g.get('group_name'),
                'destination_name': g.get('group_name'),
                'alias': None,
            })
        if destinations:
            await step("Set destinations from admin_all", db.update_destinations_for_slot(int(slot_id), destinations))
        else:
            report_lines.append("ℹ No groups in admin_all; skipped destinations step")

        # 6) Activate slot
        await step("Activate slot", db.update_ad_slot_status(int(slot_id), True))

    # 7) Scheduler-facing probes
    await step("Fetch due active ads", db.get_active_ads_to_send())
    await step("Fetch available workers", db.get_available_workers())
    
    # 8) Price service check
    try:
        price_service = context.bot_data.get('price_service')
        if price_service:
            status = price_service.get_status()
            report_lines.append(f"✔ Price Service: Running (interval: {status['update_interval_minutes']}m)")
            if status['cached_prices']:
                report_lines.append(f"📊 Cached prices: {len(status['cached_prices'])} cryptos")
            
            # Show API status
            if 'api_status' in status:
                report_lines.append("🔌 API Status:")
                for api_name, api_info in status['api_status'].items():
                    if api_info['disabled_until']:
                        report_lines.append(f"  🚫 {api_name}: Disabled until {api_info['disabled_until'].strftime('%H:%M')}")
                    elif api_info['last_success']:
                        report_lines.append(f"  ✅ {api_name}: Last success {api_info['last_success'].strftime('%H:%M')}")
                    else:
                        report_lines.append(f"  ⚠️  {api_name}: No recent success")
            
            passed += 1
        else:
            report_lines.append("✖ Price Service: Not available")
            failed += 1
    except Exception as e:
        report_lines.append(f"✖ Price Service: Error - {e}")
        failed += 1

    report_lines.append("")
    report_lines.append(f"Result: {passed} passed, {failed} failed")
    await send_admin_message(update, "\n".join(report_lines))

async def scheduler_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick DB-driven scheduler readiness check."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    db = context.bot_data.get('db')
    due = await db.get_active_ads_to_send()
    workers = await db.get_available_workers()
    lines = ["🗓 Scheduler Check", f"Due ads now: {len(due)}", f"Available workers: {len(workers)}"]
    await send_admin_message(update, "\n".join(lines))

async def schema_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check database schema health and report any issues."""
    if not await check_admin(update, context):
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        if not db:
            await send_admin_message(update, "❌ Database not available")
            return
        
        await send_admin_message(update, "🔍 Checking database schema...")
        
        # Validate schema
        result = await db.validate_schema()
        
        status_emoji = {
            'healthy': '✅',
            'issues_found': '⚠️', 
            'error': '❌'
        }
        
        emoji = status_emoji.get(result['status'], '❓')
        
        report_lines = [
            f"{emoji} Database Schema Report",
            f"Status: {result['status'].replace('_', ' ').title()}",
            f"Tables: {result.get('tables_count', 0)}/{result.get('required_tables_count', 0)}"
        ]
        
        if result.get('issues'):
            report_lines.append("\nIssues Found:")
            for issue in result['issues']:
                report_lines.append(f"• {issue}")
        
        if result.get('warnings'):
            report_lines.append("\nWarnings:")
            for warning in result['warnings']:
                report_lines.append(f"• {warning}")
        
        if result['status'] == 'healthy':
            report_lines.append("\n✅ All required tables and columns are present.")
        elif result['status'] == 'issues_found':
            report_lines.append("\n💡 Tip: Restart the bot to apply automatic schema migrations.")
        
        if result.get('error'):
            report_lines.append(f"\nError Details: {result['error']}")
        
        # Send the report
        report_text = "\n".join(report_lines)
        await send_admin_message(update, report_text)
        
    except Exception as e:
        logger.error(f"Error in schema_check: {e}")
        await send_admin_message(update, f"❌ Schema check failed: {e}")



async def fix_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fix a completed payment that didn't activate subscription. Usage: /fix_payment <payment_id>"""
    if not await check_admin(update, context):
        return
    
    try:
        text = update.message.text.strip()
        parts = text.split()
        if len(parts) != 2:
            await send_admin_message(update, 
                "❌ Usage: /fix_payment <payment_id>\n\n"
                "Example: /fix_payment TON_f900f42b94f74f14"
            )
            return
        
        payment_id = parts[1]
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get the payment
        payment = await db.get_payment(payment_id)
        if not payment:
            await send_admin_message(update, f"❌ Payment not found: {payment_id}")
            return
        
        user_id = payment.get('user_id')
        amount = payment.get('amount', 0)
        crypto_type = payment.get('crypto_type', 'TON')
        
        await send_admin_message(update, 
            f"🔍 Payment Details:\n"
            f"ID: {payment_id}\n"
            f"User: {user_id}\n"
            f"Amount: {amount} {crypto_type}\n"
            f"Status: {payment.get('status')}\n\n"
            f"Determining tier and activating subscription..."
        )
        
        # Use the payment processor to determine tier with real-time prices
        from multi_crypto_payments import MultiCryptoPaymentProcessor
        payment_processor = MultiCryptoPaymentProcessor(context.bot_data['config'], db, context.bot_data['logger'])
        
        tier = await payment_processor._determine_tier_from_amount(amount, crypto_type)
        if not tier:
            tier = 'basic'  # fallback
            await send_admin_message(update, f"⚠️ Could not determine tier automatically, using Basic as fallback")
        
        # Activate subscription
        success = await db.activate_subscription(user_id, tier, 30)
        
        if success:
            await send_admin_message(update, 
                f"✅ Payment fixed successfully!\n\n"
                f"User: {user_id}\n"
                f"Tier: {tier.title()}\n"
                f"Duration: 30 days\n\n"
                f"Subscription is now active!"
            )
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ Payment Confirmed!\n\nYour {tier.title()} subscription is now active!\nUse /my_ads to start creating your campaigns."
                )
            except Exception as e:
                logger.warning(f"Could not notify user {user_id}: {e}")
        else:
            await send_admin_message(update, f"❌ Failed to activate subscription for user {user_id}")
    
    except Exception as e:
        logger.error(f"Error in fix_payment: {e}")
        await send_admin_message(update, f"❌ Error fixing payment: {e}")

async def test_pricing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test crypto pricing and tier determination. Usage: /test_pricing <amount> <crypto>"""
    if not await check_admin(update, context):
        return
    
    try:
        text = update.message.text.strip()
        parts = text.split()
        if len(parts) != 3:
            await send_admin_message(update, 
                "❌ Usage: /test_pricing <amount> <crypto>\n\n"
                "Examples:\n"
                "/test_pricing 4.491 TON\n"
                "/test_pricing 0.0005 BTC\n"
                "/test_pricing 45 USDT"
            )
            return
        
        amount = float(parts[1])
        crypto_type = parts[2].upper()
        
        # Use the payment processor to test pricing
        from multi_crypto_payments import MultiCryptoPaymentProcessor
        payment_processor = MultiCryptoPaymentProcessor(context.bot_data['config'], context.bot_data['db'], context.bot_data['logger'])
        
        await send_admin_message(update, f"🔍 Testing pricing for {amount} {crypto_type}...")
        
        # Get current price
        price = await payment_processor._get_crypto_price(crypto_type)
        if price:
            usd_value = amount * price
            await send_admin_message(update, 
                f"💰 Current Price Data:\n"
                f"{crypto_type}: ${price:.2f} USD\n"
                f"Payment Value: {amount} {crypto_type} = ${usd_value:.2f} USD"
            )
        else:
            await send_admin_message(update, f"❌ Could not fetch {crypto_type} price")
        
        # Determine tier
        tier = await payment_processor._determine_tier_from_amount(amount, crypto_type)
        
        if tier:
            tier_config = payment_processor.tiers[tier]
            await send_admin_message(update, 
                f"🎯 Tier Determination:\n"
                f"Result: {tier.title()}\n"
                f"Target Price: ${tier_config['price_usd']} USD\n"
                f"Actual Value: ${usd_value:.2f} USD\n"
                f"Difference: ${abs(usd_value - tier_config['price_usd']):.2f}"
            )
        else:
            await send_admin_message(update, "❌ Could not determine tier for this amount")
    
    except ValueError:
        await send_admin_message(update, "❌ Invalid amount. Please use a number.")
    except Exception as e:
        logger.error(f"Error in test_pricing: {e}")
        await send_admin_message(update, f"❌ Error: {e}")

async def fix_user_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fix a user's ad slots to match their correct subscription tier."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return

    try:
        # Parse command: /fix_user_slots <user_id> <correct_tier>
        command_parts = update.message.text.split()
        if len(command_parts) != 3:
            await send_admin_message(update, 
                "❌ **Usage:** /fix_user_slots <user_id> <tier>\n\n"
                "**Example:** /fix_user_slots 7172873873 basic\n\n"
                "**Tiers:** basic, pro, enterprise",
                parse_mode='Markdown'
            )
            return
        
        user_id = int(command_parts[1])
        correct_tier = command_parts[2].lower()
        
        if correct_tier not in ['basic', 'pro', 'enterprise']:
            await send_admin_message(update, "❌ Invalid tier. Use: basic, pro, or enterprise")
            return
        
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get current subscription info
        current_subscription = await db.get_user_subscription(user_id)
        current_slots = await db.get_or_create_ad_slots(user_id, current_subscription.get('tier', 'basic') if current_subscription else 'basic')
        
        message = f"🔧 **Fixing User {user_id} Ad Slots**\n\n"
        message += f"**Current Status:**\n"
        message += f"• Subscription: {current_subscription.get('tier', 'none') if current_subscription else 'none'}\n"
        message += f"• Current Slots: {len(current_slots)}\n"
        message += f"• Target Tier: {correct_tier}\n\n"
        
        # Fix the slots
        success = await db.fix_user_ad_slots(user_id, correct_tier)
        
        if success:
            # Get updated info
            updated_subscription = await db.get_user_subscription(user_id)
            updated_slots = await db.get_or_create_ad_slots(user_id, correct_tier)
            
            message += f"✅ **Fixed Successfully!**\n\n"
            message += f"**New Status:**\n"
            message += f"• Subscription: {updated_subscription.get('tier', 'none') if updated_subscription else 'none'}\n"
            message += f"• Current Slots: {len(updated_slots)}\n"
            message += f"• Slot Numbers: {[slot.get('slot_number') for slot in updated_slots]}\n"
        else:
            message += "❌ **Failed to fix ad slots.**"
        
        await send_admin_message(update, message, parse_mode='Markdown')
        
    except ValueError:
        await send_admin_message(update, "❌ Invalid user ID. Please provide a valid number.")
    except Exception as e:
        logger.error(f"Error fixing user slots: {e}")
        await send_admin_message(update, "❌ Error fixing user slots.")

async def delete_test_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a test/bogus user and their data. Admin only.

    Usage: /delete_test_user <user_id>
    """
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    if not context.args:
        await send_admin_message(update, "Usage: /delete_test_user <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except Exception:
        await send_admin_message(update, "❌ Invalid user_id")
        return
    db = context.bot_data.get('db')
    ok = await db.delete_user_and_data(user_id)
    if ok:
        await send_admin_message(update, f"✅ Deleted user {user_id} and associated data.")
    else:
        await send_admin_message(update, f"❌ Failed to delete user {user_id}.")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all registered users with their subscription status."""
    if not await check_admin(update, context):
        return
        
    try:
        db = context.bot_data.get('db')
        if not db:
            message_text = "❌ Database not available"
            if update.callback_query:
                await update.callback_query.edit_message_text(message_text)
            else:
                await send_admin_message(update, message_text)
            return
            
        users = await db.get_all_users()
        
        # Safety check for None return
        if users is None:
            users = []
        
        if not users:
            message_text = "📋 No users found in the database."
            if update.callback_query:
                await update.callback_query.edit_message_text(message_text)
            else:
                await send_admin_message(update, message_text)
            return
            
        # Additional safety check to ensure users is a list
        if not isinstance(users, list):
            await send_admin_message(update, "❌ Error: Invalid user data format")
            return
            
        # Format user list (compact for easy viewing, plain text to avoid parse errors)
        from datetime import datetime
        current_time = datetime.now().strftime('%H:%M:%S')
        lines = [f"👥 Registered Users (Updated: {current_time}):\n"]
        
        for user in users:
            if not user:  # Skip None users
                continue
            user_id = user.get('user_id', 'Unknown')
            username = user.get('username', 'N/A')
            first_name = user.get('first_name', 'N/A')
            tier = user.get('subscription_tier', 'None')
            is_active = user.get('is_active', 0)
            
            status = "✅" if is_active else "❌"
            
            # Clean text to avoid markdown issues
            clean_username = str(username).replace('*', '').replace('_', '').replace('[', '').replace(']', '')
            clean_first_name = str(first_name).replace('*', '').replace('_', '').replace('[', '').replace(']', '')
            clean_tier = str(tier).replace('*', '').replace('_', '').replace('[', '').replace(']', '')
            
            lines.append(f"{user_id} (@{clean_username}) | {clean_first_name} | {clean_tier} {status}")
            
        # Split into chunks if too long
        text = "\n".join(lines)
        if len(text) > 4000:
            # Send in chunks
            chunks = []
            current_chunk = [f"👥 Registered Users (Updated: {current_time}):\n"]
            
            for user in users:
                if not user:  # Skip None users
                    continue
                user_id = user.get('user_id', 'Unknown')
                username = user.get('username', 'N/A')
                tier = user.get('subscription_tier', 'None')
                is_active = user.get('is_active', 0)
                status = "✅" if is_active else "❌"
                
                # Clean text
                clean_username = str(username).replace('*', '').replace('_', '').replace('[', '').replace(']', '')
                clean_tier = str(tier).replace('*', '').replace('_', '').replace('[', '').replace(']', '')
                
                line = f"{user_id} (@{clean_username}) | {clean_tier} {status}"
                current_chunk.append(line)
                
                if len("\n".join(current_chunk)) > 3800:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [f"👥 Users (continued - {current_time}):\n"]
                    
            if current_chunk and len(current_chunk) > 1:
                chunks.append("\n".join(current_chunk))
                    
            for chunk in chunks:
                if update.callback_query:
                    await update.callback_query.edit_message_text(chunk)
                else:
                    await send_admin_message(update, chunk)
        else:
            # Always show delete buttons (but limit to first 20 users for performance)
            keyboard = []
            users_to_show = users[:20] if len(users) > 20 else users
            
            for user in users_to_show:
                if not user:  # Skip None users
                    continue
                user_id = user.get('user_id', 'Unknown')
                username = user.get('username', f"ID{user_id}")
                first_name = user.get('first_name', '')
                # Create a shorter display name
                display_name = username if len(str(username)) <= 15 else f"{str(username)[:12]}..."
                keyboard.append([InlineKeyboardButton(
                    f"🗑️ Delete {display_name}", 
                    callback_data=f"admin:delete_user:{user_id}"
                )])
                
            # Add navigation buttons
            keyboard.append([InlineKeyboardButton("🔄 Refresh List", callback_data="cmd:list_users")])
            keyboard.append([InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="cmd:admin_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await send_admin_message(update, text, reply_markup=reply_markup)
                
    except Exception as e:
        logger.error(f"Error in list_users: {e}")
        error_message = "❌ Error retrieving users"
        if update.callback_query:
            await update.callback_query.edit_message_text(error_message)
        else:
            await send_admin_message(update, error_message)

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin menu with available options."""
    if not await check_admin(update, context):
        if update.callback_query:
            await update.callback_query.answer("❌ Admin access required.")
        else:
            await send_admin_message(update, "❌ Admin access required.")
        return
        
    try:
        message_text = "🔧 **Admin Menu**\n\nSelect an admin option:"
        
        keyboard = [
            [
                InlineKeyboardButton("👥 User Management", callback_data="cmd:list_users"),
                InlineKeyboardButton("🎯 Admin Slots", callback_data="cmd:admin_slots")
            ],
            [
                InlineKeyboardButton("📊 Ads Analysis", callback_data="cmd:admin_ads_analysis"),
                InlineKeyboardButton("📋 List Groups", callback_data="cmd:list_groups")
            ],
            [
                InlineKeyboardButton("📊 Admin Stats", callback_data="cmd:admin_stats"),
                InlineKeyboardButton("🔧 System Check", callback_data="cmd:system_check")
            ],
            [
                InlineKeyboardButton("📡 Posting Status", callback_data="cmd:posting_status"),
                InlineKeyboardButton("⚠️ Failed Groups", callback_data="cmd:failed_groups")
            ],
            [
                InlineKeyboardButton("⏸️ Paused Slots", callback_data="cmd:paused_slots"),
                InlineKeyboardButton("💰 Revenue Stats", callback_data="cmd:revenue_stats")
            ],
            [
                InlineKeyboardButton("🤖 Worker Status", callback_data="cmd:worker_status"),
                InlineKeyboardButton("📈 System Status", callback_data="cmd:system_status")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await send_admin_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in admin_menu: {e}")
        if update.callback_query:
            await update.callback_query.answer("❌ Error loading admin menu")
        else:
            await send_admin_message(update, "❌ Error loading admin menu")

async def test_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test admin command to verify admin functionality."""
    user_id = update.effective_user.id
    await send_admin_message(update, f"🔧 Testing admin command functionality for user {user_id}...")
    
    try:
        # Test config access
        config = context.bot_data.get('config')
        if config:
            await send_admin_message(update, f"✅ Config loaded: {config.bot_name}")
            
            # Show current admin ID
            current_admin_id = config.admin_id
            await send_admin_message(update, f"🔑 Current ADMIN_ID: {current_admin_id}")
            
            # Test admin check
            is_admin = await check_admin(update, context)
            await send_admin_message(update, f"👤 Admin check result: {is_admin}")
            
            if not is_admin:
                await send_admin_message(update, f"❌ You are not admin. Your ID: {user_id}, Admin ID: {current_admin_id}")
                await send_admin_message(update, "💡 To fix: Set ADMIN_ID in your .env file to your Telegram user ID")
        else:
            await send_admin_message(update, "❌ Config not available")
            
        # Test database access
        db = context.bot_data.get('db')
        if db:
            await send_admin_message(update, "✅ Database available")
        else:
            await send_admin_message(update, "❌ Database not available")
            
    except Exception as e:
        await send_admin_message(update, f"❌ Error in test: {str(e)}")
        logger.error(f"Error in test_admin: {e}")

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new group to the managed groups list."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    if not context.args or len(context.args) < 2:
        await send_admin_message(update, 
            "Usage: /add_group <group_id> <group_name> [category]\n"
            "Example: /add_group -1001234567890 'My Group' general"
        )
        return
    
    try:
        group_id = context.args[0]
        group_name = context.args[1]
        category = context.args[2] if len(context.args) > 2 else "general"
        
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        success = await db.add_managed_group(group_id, group_name, category)
        
        if success:
            await send_admin_message(update, f"✅ Group '{group_name}' added successfully!")
        else:
            await send_admin_message(update, "❌ Failed to add group. Please try again.")
            
    except Exception as e:
        logger.error(f"Error adding group: {e}")
        await send_admin_message(update, "❌ Error adding group. Please check the format.")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all managed groups."""
    if not await check_admin(update, context):
        # Handle both command and callback query calls
        if update.callback_query:
            await update.callback_query.answer("❌ Admin access required.")
        else:
            await send_admin_message(update, "❌ Admin access required.")
        return
        
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        # Show category summary first
        cat_counts = await db.get_managed_group_category_counts()
        if cat_counts:
            lines = ["📚 Categories (tap to view groups):\n"]
            rows = []
            for cc in cat_counts:
                cat = cc['category']
                cnt = cc['count']
                rows.append([InlineKeyboardButton(f"{cat.title()} ({cnt})", callback_data=f"admin:list_cat:{cat}")])
            rows.append([InlineKeyboardButton("🔐 Admin All (virtual)", callback_data="admin:show_admin_all")])
            rows.append([InlineKeyboardButton("➕ Add Chats to Category", callback_data="admin:add_to_category_menu")])
            rows.append([
                InlineKeyboardButton("🔥 Purge Category", callback_data="admin:purge_menu:category"),
                InlineKeyboardButton("🧨 Purge Group", callback_data="admin:purge_menu:group")
            ])
            rows.append([InlineKeyboardButton("💥 Purge ALL Groups", callback_data="admin:purge_all_groups")])
            # Handle both command and callback query calls
            if update.callback_query:
                await update.callback_query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(rows))
            else:
                await send_admin_message(update, "\n".join(lines), reply_markup=InlineKeyboardMarkup(rows))
            return
        # Fallback to full list if no categories
        groups = await db.get_managed_groups()
        admin_all = await db.get_managed_groups("admin_all")
        
        if not groups:
            # Handle both command and callback query calls
            if update.callback_query:
                await update.callback_query.edit_message_text("📋 No managed groups found.")
            else:
                await send_admin_message(update, "📋 No managed groups found.")
            return
        
        # Paginate to avoid long messages
        PAGE_SIZE = 40
        total_pages = max(1, (len(groups) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = 0
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        subset = groups[start:end]
        text_lines: List[str] = [f"📋 Managed Groups (page {page+1}/{total_pages}):\n"]
        keyboard = []
        for group in subset:
            text_lines.append(f"{group['group_name']}  |  {group['group_id']}  |  {group['category']}")
            keyboard.append([
                InlineKeyboardButton("✏️ Edit Category", callback_data=f"admin:edit_group_cat:{group['group_id']}"),
                InlineKeyboardButton("🗑️ Remove", callback_data=f"admin:remove_group:{group['group_name']}")
            ])
        nav = []
        if end < len(groups):
            nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin:groups_page:{page+1}"))
        if nav:
            keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("🔐 Admin All (virtual)", callback_data="admin:show_admin_all")])
        keyboard.append([InlineKeyboardButton("➕ Add Chats to Category", callback_data="admin:add_to_category_menu")])
        keyboard.append([
            InlineKeyboardButton("🔥 Purge Category", callback_data="admin:purge_menu:category"),
            InlineKeyboardButton("🧨 Purge Group", callback_data="admin:purge_menu:group")
        ])
        keyboard.append([InlineKeyboardButton("💥 Purge ALL Groups", callback_data="admin:purge_all_groups")])

        # Handle both command and callback query calls
        if update.callback_query:
            await update.callback_query.edit_message_text("\n".join(text_lines), reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await send_admin_message(update, "\n".join(text_lines), reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        # Handle both command and callback query calls
        if update.callback_query:
            await update.callback_query.answer("❌ Error listing groups.")
        else:
            await send_admin_message(update, "❌ Error listing groups.")

async def _render_admin_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    db = context.bot_data['db']
    chats = await db.get_managed_groups("admin_all")
    count = len(chats)
    lines = [f"🔐 Admin-only category: {count} unique chats\n"]
    # Show first 50 names only, avoid long messages
    for g in chats[:50]:
        lines.append(f"• {g.get('group_name') or g.get('group_id')}")
    if count > 50:
        lines.append(f"… and {count-50} more")
    await query.edit_message_text("\n".join(lines))

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a group from the managed groups list."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    if not context.args:
        await send_admin_message(update, 
            "Usage: /remove_group <group_name>\n"
            "Example: /remove_group 'My Group'"
        )
        return
    
    try:
        group_name = " ".join(context.args)
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        success = await db.remove_managed_group(group_name)
        
        if success:
            await send_admin_message(update, f"✅ Group '{group_name}' removed successfully!")
        else:
            await send_admin_message(update, "❌ Failed to remove group. Please check the name.")
            
    except Exception as e:
        logger.error(f"Error removing group: {e}")
        await send_admin_message(update, "❌ Error removing group.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin statistics."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    try:
        # First, let's test if the command is working at all
        await send_admin_message(update, "✅ Admin command received! Testing database connection...")
        
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        if not db:
            await send_admin_message(update, "❌ Database not available in context.")
            return
            
        stats = await db.get_stats()
        
        text = "📊 **Admin Statistics:**\n\n"
        text += f"👥 **Users:** {stats['total_users']}\n"
        text += f"💎 **Active Subscriptions:** {stats['active_subscriptions']}\n"
        text += f"📨 **Messages Today:** {stats['messages_today']}\n"
        text += f"💰 **Revenue This Month:** ${stats['revenue_this_month']:.2f}\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        await send_admin_message(update, f"❌ Error getting statistics: {str(e)}")

async def posting_service_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Concise, DB-sourced status to avoid duplicating other menus."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return

    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        due_slots = await db.get_active_ads_to_send()
        workers = await db.get_all_workers()
        available_workers = await db.get_available_workers()

        # Separate user and admin slots
        user_slots = [slot for slot in due_slots if slot.get('slot_type') == 'user']
        admin_slots = [slot for slot in due_slots if slot.get('slot_type') == 'admin']

        lines = ["📡 Posting Service Status", ""]
        lines.append(f"Workers available: {len(available_workers)}/{len(workers)}")
        lines.append(f"**Total ads due now: {len(due_slots)}**")
        lines.append(f"  • User ads: {len(user_slots)}")
        lines.append(f"  • Admin ads: {len(admin_slots)}")
        lines.append("")
        if available_workers:
            lines.append("Top available workers (ID | hourly/daily):")
            for w in available_workers[:5]:
                hp = w.get('hourly_posts', 0); dp = w.get('daily_posts', 0)
                hl = w.get('hourly_limit', 15); dl = w.get('daily_limit', 150)
                lines.append(f"• {w['worker_id']} | {hp}/{hl} h, {dp}/{dl} d")
        await send_admin_message(update, "\n".join(lines))

    except Exception as e:
        logger.error(f"Error getting posting service status: {e}")
        await send_admin_message(update, "❌ Error getting service status.")

async def failed_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show failed group joins."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get filter from command arguments
        filter_type = context.args[0] if context.args else None
        
        if filter_type and filter_type not in ['high', 'medium', 'low', 'privacy', 'invite', 'banned']:
            await send_admin_message(update, 
                "Usage: /failed_groups [high|medium|low|privacy|invite|banned]\n"
                "Examples:\n"
                "/failed_groups - Show all failed groups\n"
                "/failed_groups high - Show high priority failures\n"
                "/failed_groups privacy - Show privacy-restricted groups"
            )
            return
        
        # Get failed groups
        failed_groups = await db.get_failed_group_joins(priority=filter_type, limit=20)
        
        if not failed_groups:
            await send_admin_message(update, "✅ No failed group joins found!")
            return
        
        # Format the response
        if filter_type:
            title = f"🚫 Failed Groups ({filter_type.upper()})"
        else:
            title = "🚫 Failed Group Joins"
        
        response_text = f"{title}\n\n"
        
        for group in failed_groups:
            priority_emoji = {
                'high': '🔴',
                'medium': '🟡', 
                'low': '🟢'
            }.get(group['priority'], '⚪')
            
            fail_reason_emoji = {
                'privacy_restricted': '🔒',
                'invite_only': '🔗',
                'banned': '🚫',
                'all_formats_failed': '❌',
                'join_limit_exceeded': '⏰'
            }.get(group['fail_reason'], '❓')
            
            # Escape special characters to prevent parsing errors
            group_name = str(group['group_name']).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
            group_username = str(group['group_username']).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
            workers_tried = str(group['workers_tried']).replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
            last_attempt = str(group['last_attempt'])[:16] if group['last_attempt'] else 'Unknown'
            
            response_text += f"{priority_emoji} **{group_name}**\n"
            response_text += f"   {fail_reason_emoji} `{group_username}`\n"
            response_text += f"   📊 Fails: {group['fail_count']} | Workers: {workers_tried}\n"
            response_text += f"   ⏰ Last: {last_attempt}\n\n"
        
        # Add summary
        total_failed = len(failed_groups)
        response_text += f"📊 Total: {total_failed} failed groups\n"
        response_text += "💡 Use /failed_groups [type] to filter by priority or reason"
        
        await send_admin_message(update, response_text)
        
    except Exception as e:
        logger.error(f"Error getting failed groups: {e}")
        await send_admin_message(update, "❌ Error getting failed groups.")

async def paused_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show paused ad slots for monitoring."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        paused_slots = await db.get_paused_slots()
        
        if not paused_slots:
            await send_admin_message(update, "✅ No paused ad slots found.")
            return
        
        response_text = "⏸️ **Paused Ad Slots**\n\n"
        
        for slot in paused_slots:
            user_name = slot.get('username') or slot.get('first_name') or f"User {slot['user_id']}"
            pause_reason = slot.get('pause_reason', 'unknown')
            pause_time = slot.get('pause_time', 'Unknown')
            
            response_text += f"**Slot {slot['slot_number']}** (User: {user_name})\n"
            response_text += f"   🎯 Reason: {pause_reason}\n"
            response_text += f"   ⏰ Paused: {pause_time}\n\n"
        
        response_text += f"📊 **Total: {len(paused_slots)} paused slots**"
        
        await send_admin_message(update, response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting paused slots: {e}")
        await send_admin_message(update, "❌ Error getting paused slots.")

async def retry_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually retry joining a specific group."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    if not context.args:
        await send_admin_message(update, 
            "Usage: /retry_group @username\n"
            "Example: /retry_group @crypto_trading"
        )
        return
        
    group_username = context.args[0]
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Remove from failed groups list
        success = await db.remove_failed_group_join(group_username)
        
        if success:
            await send_admin_message(update, 
                f"✅ Removed {group_username} from failed groups list.\n"
                f"🔄 The system will try to join this group again during the next posting cycle."
            )
        else:
            await send_admin_message(update, 
                f"❌ {group_username} not found in failed groups list."
            )
            
    except Exception as e:
        logger.error(f"Error retrying group {group_username}: {e}")
        await send_admin_message(update, "❌ Error retrying group.")

async def _show_category_choice(query, group_id: str):
    """Internal helper to show preset categories and a custom option."""
    categories = [
        [InlineKeyboardButton("general", callback_data=f"admin:set_group_cat:{group_id}:general"),
         InlineKeyboardButton("premium", callback_data=f"admin:set_group_cat:{group_id}:premium")],
        [InlineKeyboardButton("test", callback_data=f"admin:set_group_cat:{group_id}:test"),
         InlineKeyboardButton("Custom…", callback_data=f"admin:edit_group_cat_custom:{group_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin:back_to_groups")]
    ]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(categories))

async def _render_admin_all(query, db):
    """Show the virtual admin_all category with all unique groups."""
    try:
        # Get all unique groups across categories
        all_groups = await db.get_managed_groups()
        if not all_groups:
            await query.edit_message_text("🔐 Admin All (virtual)\n\nNo groups found.")
            return
        
        # Remove duplicates by group_id while preserving the first occurrence
        seen = set()
        unique_groups = []
        for group in all_groups:
            if group['group_id'] not in seen:
                seen.add(group['group_id'])
                unique_groups.append(group)
        
        PAGE_SIZE = 40
        total_pages = max(1, (len(unique_groups) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = 0
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        subset = unique_groups[start:end]
        
        lines = [f"🔐 Admin All (virtual) - All unique groups (page {page+1}/{total_pages}):\n"]
        keyboard = []
        for group in subset:
            lines.append(f"{group['group_name']} | {group['group_id']} | Category: {group['category']}")
        
        nav = []
        if end < len(unique_groups):
            nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin:admin_all_page:1"))
        keyboard.append(nav) if nav else None
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:back_to_groups")])
        
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error rendering admin_all: {e}")
        await query.edit_message_text("❌ Error loading admin view.")

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, parts: list):
    """Entry point called by bot callback router for admin:* actions beyond restart/pause."""
    query = update.callback_query
    db = context.bot_data.get('db')
    try:
        if action == "edit_group_cat" and len(parts) >= 3:
            group_id = parts[2]
            await _show_category_choice(query, group_id)
            return
        if action == "set_group_cat" and len(parts) >= 4:
            group_id = parts[2]
            new_cat = parts[3]
            if db:
                ok = await db.update_managed_group_category(group_id, new_cat)
                if ok:
                    await query.answer("Category updated")
                    await query.edit_message_text(f"✅ Category updated to '{new_cat}' for group `{group_id}`", parse_mode='Markdown')
                else:
                    await query.answer("Update failed")
            return
        if action == "edit_group_cat_custom" and len(parts) >= 3:
            group_id = parts[2]
            # Store awaiting custom input state
            context.user_data['awaiting_custom_group_category'] = group_id
            await query.answer()
            await query.edit_message_text(
                f"✏️ Send the new category for group `{group_id}` as a message.", parse_mode='Markdown'
            )
            return
        if action == "remove_group" and len(parts) >= 3:
            group_name = parts[2]
            if db:
                ok = await db.remove_managed_group(group_name)
                if ok:
                    await query.answer("Removed")
                    await query.edit_message_text(f"🗑️ Removed group '{group_name}'.")
                else:
                    await query.answer("Remove failed")
            return
        if action == "back_to_groups":
            # Re-render groups list using callback query
            await list_groups(update, context)
            return
        if action == "show_admin_all":
            await _render_admin_all(query, db)
            return
        if action == "delete_user" and len(parts) >= 3:
            user_id = int(parts[2])
            success = await db.delete_user_and_data(user_id)
            if success:
                await query.answer("User deleted successfully!")
                # Show success message with option to go back to user list
                keyboard = [[InlineKeyboardButton("📋 Back to User List", callback_data="cmd:list_users")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"✅ Successfully deleted user {user_id} and all associated data\n\n"
                    f"🗑️ User removed from database\n"
                    f"📊 All user's ad slots deleted\n"
                    f"💰 Payment records cleared",
                    reply_markup=reply_markup
                )
            else:
                await query.answer("Delete failed!")
                keyboard = [[InlineKeyboardButton("📋 Back to User List", callback_data="cmd:list_users")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"❌ Failed to delete user {user_id}\n\n"
                    f"This user may not exist or there was a database error.",
                    reply_markup=reply_markup
                )
            return
        if action == "list_cat" and len(parts) >= 3:
            category = parts[2]
            groups = await context.bot_data['db'].get_managed_groups(category)
            # Render limited page for this category
            PAGE_SIZE = 40
            total_pages = max(1, (len(groups) + PAGE_SIZE - 1) // PAGE_SIZE)
            page = 0
            start = page * PAGE_SIZE
            end = start + PAGE_SIZE
            subset = groups[start:end]
            lines = [f"📋 {category.title()} (page {page+1}/{total_pages}):\n"]
            keyboard = []
            for group in subset:
                lines.append(f"{group['group_name']}  |  {group['group_id']}")
                keyboard.append([
                    InlineKeyboardButton("✏️ Edit Category", callback_data=f"admin:edit_group_cat:{group['group_id']}"),
                    InlineKeyboardButton("🗑️ Remove", callback_data=f"admin:remove_group:{group['group_name']}")
                ])
            nav = []
            if end < len(groups):
                nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin:list_cat_page:{category}:1"))
            keyboard.append(nav) if nav else None
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:back_to_groups")])
            await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))
            return
        if action == "list_cat_page" and len(parts) >= 4:
            category = parts[2]
            try:
                page = int(parts[3])
            except Exception:
                page = 0
            groups = await context.bot_data['db'].get_managed_groups(category)
            PAGE_SIZE = 40
            total_pages = max(1, (len(groups) + PAGE_SIZE - 1) // PAGE_SIZE)
            page = max(0, min(page, total_pages - 1))
            start = page * PAGE_SIZE
            end = start + PAGE_SIZE
            subset = groups[start:end]
            lines = [f"📋 {category.title()} (page {page+1}/{total_pages}):\n"]
            keyboard = []
            for group in subset:
                lines.append(f"{group['group_name']}  |  {group['group_id']}")
                keyboard.append([
                    InlineKeyboardButton("✏️ Edit Category", callback_data=f"admin:edit_group_cat:{group['group_id']}"),
                    InlineKeyboardButton("🗑️ Remove", callback_data=f"admin:remove_group:{group['group_name']}")
                ])
            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin:list_cat_page:{category}:{page-1}"))
            if end < len(groups):
                nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin:list_cat_page:{category}:{page+1}"))
            keyboard.append(nav) if nav else None
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:back_to_groups")])
            await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))
            return
        if action == "groups_page" and len(parts) >= 3:
            try:
                page = int(parts[2])
            except Exception:
                page = 0
            groups = await context.bot_data['db'].get_managed_groups()
            # Build and edit message
            PAGE_SIZE = 40
            total_pages = max(1, (len(groups) + PAGE_SIZE - 1) // PAGE_SIZE)
            page = max(0, min(page, total_pages - 1))
            start = page * PAGE_SIZE
            end = start + PAGE_SIZE
            subset = groups[start:end]
            lines = [f"📋 Managed Groups (page {page+1}/{total_pages}):\n"]
            keyboard = []
            for group in subset:
                lines.append(f"{group['group_name']}  |  {group['group_id']}  |  {group['category']}")
                keyboard.append([
                    InlineKeyboardButton("✏️ Edit Category", callback_data=f"admin:edit_group_cat:{group['group_id']}"),
                    InlineKeyboardButton("🗑️ Remove", callback_data=f"admin:remove_group:{group['group_name']}")
                ])
            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin:groups_page:{page-1}"))
            if end < len(groups):
                nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin:groups_page:{page+1}"))
            if nav:
                keyboard.append(nav)
            keyboard.append([InlineKeyboardButton("🔐 Admin All (virtual)", callback_data="admin:show_admin_all")])
            keyboard.append([InlineKeyboardButton("➕ Add Chats to Category", callback_data="admin:add_to_category_menu")])
            keyboard.append([
                InlineKeyboardButton("🔥 Purge Category", callback_data="admin:purge_menu:category"),
                InlineKeyboardButton("🧨 Purge Group", callback_data="admin:purge_menu:group")
            ])
            keyboard.append([InlineKeyboardButton("💥 Purge ALL Groups", callback_data="admin:purge_all_groups")])
            await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))
            return
        if action == "purge_menu" and len(parts) >= 3:
            mode = parts[2]  # 'category' or 'group'
            if mode == 'category':
                categories = await db.get_managed_group_categories()
                if not categories:
                    await query.answer("No categories")
                    return
                rows = []
                for c in categories:
                    rows.append([InlineKeyboardButton(c, callback_data=f"admin:purge_category:{c}")])
                rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:back_to_groups")])
                await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))
                return
            if mode == 'group':
                groups = await db.get_managed_groups()
                if not groups:
                    await query.answer("No groups")
                    return
                rows = []
                for g in groups[:60]:
                    label = (g['group_name'] or g['group_id'])[:35]
                    rows.append([InlineKeyboardButton(label, callback_data=f"admin:purge_group:{g['group_id']}")])
                rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:back_to_groups")])
                await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))
                return
        if action == "purge_category" and len(parts) >= 3:
            category = parts[2]
            keyboard = [
                [InlineKeyboardButton("✅ Confirm", callback_data=f"admin:confirm_purge_category:{category}")],
                [InlineKeyboardButton("⬅️ Cancel", callback_data="admin:back_to_groups")]
            ]
            await query.edit_message_text(
                f"⚠️ Are you sure you want to purge ALL groups in category '{category}'?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        if action == "confirm_purge_category" and len(parts) >= 3:
            category = parts[2]
            if db:
                ok = await db.purge_managed_groups_by_category(category)
                if ok:
                    await query.edit_message_text(f"🔥 Purged all groups in category '{category}'.")
                else:
                    await query.answer("Purge failed")
            return
        if action == "purge_group" and len(parts) >= 3:
            gid = parts[2]
            if db:
                ok = await db.purge_managed_group_by_id(gid)
                if ok:
                    await query.edit_message_text(f"🧨 Purged group `{gid}`.", parse_mode='Markdown')
                else:
                    await query.answer("Purge failed")
            return
        if action == "purge_all_groups":
            keyboard = [
                [InlineKeyboardButton("🧨 YES, Purge ALL", callback_data="admin:confirm_purge_all")],
                [InlineKeyboardButton("⬅️ Cancel", callback_data="admin:back_to_groups")]
            ]
            await query.edit_message_text(
                "⚠️ Are you absolutely sure you want to purge ALL managed groups?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        if action == "confirm_purge_all":
            if db:
                ok = await db.purge_all_managed_groups()
                if ok:
                    await query.edit_message_text("💥 Purged ALL managed groups.")
                else:
                    await query.answer("Purge failed")
            return
        if action == "add_to_category_menu":
            categories = await db.get_managed_group_categories()
            if not categories:
                await query.answer("No categories")
                return
            rows = []
            for c in categories:
                rows.append([InlineKeyboardButton(c, callback_data=f"admin:add_to_category:{c}")])
            rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin:back_to_groups")])
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))
            return
        if action == "add_to_category" and len(parts) >= 3:
            category = parts[2]
            # Prompt user to paste multiple chat IDs/usernames separated by commas or spaces
            context.user_data['awaiting_add_to_category'] = category
            await query.edit_message_text(
                f"➕ Send the chat IDs or @usernames to add to category '{category}'.\n"
                "You can paste multiple separated by spaces or commas.\n"
                "Example: -10012345 @channel1 -10098765",
            )
            return
        # Add missing command handlers for admin commands
        if action == "system_check":
            await system_check(update, context)
            return
        if action == "admin_menu":
            await admin_menu(update, context)
            return
        if action == "list_users":
            await list_users(update, context)
            return
        if action == "admin_stats":
            await admin_stats(update, context)
            return
        if action == "posting_status":
            await posting_service_status(update, context)
            return
        if action == "failed_groups":
            await failed_groups(update, context)
            return
        if action == "paused_slots":
            await paused_slots(update, context)
            return
        if action == "revenue_stats":
            await revenue_stats(update, context)
            return
        if action == "worker_status":
            await worker_status(update, context)
            return
        if action == "system_status":
            await system_status(update, context)
            return
        if action == "list_groups":
            await list_groups(update, context)
            return
        if action == "admin_ads_analysis":
            # Route to admin stats for now since ads analysis is not implemented
            await admin_stats(update, context)
            return
        if action == "admin_warnings":
            await admin_warnings(update, context)
            return
        if action == "admin_suggestions":
            await admin_suggestions(update, context)
            return
        # If no handler found, log and show error
        logger.warning(f"Unknown admin callback action: {action}")
        await query.answer("❌ Unknown admin action")
        await query.edit_message_text("❌ Unknown admin action. Please try again.")
        return
    except Exception as e:
        logger.error(f"Admin callback handling error: {e}")
        try:
            await query.answer("Error")
        except:
            pass

async def restart_posting_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the posting service."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    try:
        posting_service = context.bot_data.get('posting_service')
        if not posting_service:
            await update.callback_query.answer("❌ Posting service not available.")
            return
        
        await update.callback_query.answer("🔄 Restarting posting service...")
        
        # Restart the service
        await posting_service.restart_service()
        
        await update.callback_query.edit_message_text(
            "✅ Posting service restarted successfully!"
        )
        
    except Exception as e:
        logger.error(f"Error restarting posting service: {e}")
        await update.callback_query.answer("❌ Error restarting service.")

async def pause_posting_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause the posting service."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    try:
        posting_service = context.bot_data.get('posting_service')
        if not posting_service:
            await update.callback_query.answer("❌ Posting service not available.")
            return
        
        if not posting_service.is_running:
            await update.callback_query.answer("⏸️ Service is already paused.")
            return
        
        await update.callback_query.answer("⏸️ Pausing posting service...")
        
        # Stop the service
        await posting_service.stop_service()
        
        await update.callback_query.edit_message_text(
            "⏸️ Posting service paused successfully!"
        )
        
    except Exception as e:
        logger.error(f"Error pausing posting service: {e}")
        await update.callback_query.answer("❌ Error pausing service.")

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify a payment manually."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    if not context.args:
        await send_admin_message(update, 
            "Usage: /verify_payment <payment_id>\n"
            "Example: /verify_payment TON_abc123def456"
        )
        return
    
    try:
        payment_id = context.args[0]
        payment_processor = context.bot_data.get('payment_processor')
        
        if not payment_processor:
            await send_admin_message(update, "❌ Payment processor not available.")
            return
        
        # Verify the payment
        verification = await payment_processor.verify_payment(payment_id)
        
        if verification.get('payment_verified'):
            # Process the payment
            result = await payment_processor.process_successful_payment(payment_id)
            
            if result['success']:
                await send_admin_message(update, 
                    f"✅ Payment verified and processed!\n"
                    f"User: {result['user_id']}\n"
                    f"Tier: {result['tier']}\n"
                    f"Slots: {result['slots']}"
                )
            else:
                await send_admin_message(update, f"❌ Payment verification failed: {result.get('error')}")
        else:
            await send_admin_message(update, "❌ Payment not verified. Please check the payment ID.")
            
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        await send_admin_message(update, "❌ Error verifying payment.")

async def revenue_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show revenue statistics."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get all completed payments from the database
        conn = sqlite3.connect(db.db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout=30000;")
        cursor = conn.cursor()
        
        # Get total revenue and payment counts
        cursor.execute('''
            SELECT 
                COUNT(*) as total_payments,
                SUM(amount) as total_revenue,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_payments,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_payments,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_payments
            FROM payments
        ''')
        stats = cursor.fetchone()
        
        # Get revenue by crypto type
        cursor.execute('''
            SELECT 
                crypto_type,
                COUNT(*) as count,
                SUM(amount) as revenue
            FROM payments 
            WHERE status = 'completed'
            GROUP BY crypto_type
        ''')
        crypto_stats = cursor.fetchall()
        
        # Get recent payments (last 7 days)
        cursor.execute('''
            SELECT 
                COUNT(*) as recent_count,
                SUM(amount) as recent_revenue
            FROM payments 
            WHERE status = 'completed' 
            AND created_at >= datetime('now', '-7 days')
        ''')
        recent_stats = cursor.fetchone()
        
        conn.close()
        
        # Build the statistics message
        text = "💰 **Revenue Statistics:**\n\n"
        
        if stats and stats[0] > 0:
            total_payments, total_revenue, completed, pending, cancelled = stats
            
            text += f"📊 **Overall Statistics:**\n"
            text += f"• Total Payments: {total_payments}\n"
            text += f"• Completed: {completed}\n"
            text += f"• Pending: {pending}\n"
            text += f"• Cancelled: {cancelled}\n"
            text += f"• Success Rate: {(completed/total_payments*100):.1f}%\n\n"
            
            if total_revenue:
                text += f"💵 **Total Revenue:** ${total_revenue:.2f}\n\n"
            
            # Recent revenue
            if recent_stats and recent_stats[0] > 0:
                text += f"📈 **Last 7 Days:**\n"
                text += f"• Payments: {recent_stats[0]}\n"
                text += f"• Revenue: ${recent_stats[1]:.2f}\n\n"
            
            # Revenue by crypto type
            if crypto_stats:
                text += f"🪙 **Revenue by Cryptocurrency:**\n"
                for crypto_type, count, revenue in crypto_stats:
                    if revenue:
                        text += f"• {crypto_type}: {count} payments, ${revenue:.2f}\n"
                text += "\n"
        else:
            text += "📊 **No payment data available yet.**\n\n"
            text += "Revenue tracking will show:\n"
            text += "• Total revenue and payment counts\n"
            text += "• Revenue by cryptocurrency\n"
            text += "• Recent payment trends\n"
            text += "• Payment success rates\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting revenue stats: {e}")
        await send_admin_message(update, "❌ Error getting revenue statistics.")

async def pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending payments."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
        
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        payment_processor = context.bot_data.get('payment_processor')
        
        if not payment_processor:
            await send_admin_message(update, "❌ Payment processor not available.")
            return
        
        # Get pending payments
        pending_payments = await db.get_pending_payments(30)  # Last 30 minutes
        
        if not pending_payments:
            await send_admin_message(update, "📋 No pending payments found.")
            return
        
        text = "⏳ **Pending Payments:**\n\n"
        for payment in pending_payments:
            text += f"**Payment ID:** `{payment['payment_id']}`\n"
            text += f"**User:** {payment['user_id']}\n"
            text += f"**Amount:** {payment['amount']} {payment['currency']}\n"
            text += f"**Created:** {payment['created_at']}\n"
            text += f"**Expires:** {payment['expires_at']}\n\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting pending payments: {e}")
        await send_admin_message(update, "❌ Error getting pending payments.")

async def worker_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show worker status and usage."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        workers = await db.get_all_workers()
        if not workers:
            await send_admin_message(update, "🤖 No workers found.")
            return
        
        # Show summary first
        lines = ["🤖 **Worker Status Summary**\n"]
        total_hourly_posts = 0
        total_daily_posts = 0
        total_safety_score = 0
        available_workers = 0
        
        # Calculate totals
        for worker in workers:
            usage = await db.get_worker_usage(worker['worker_id']) or {}
            hourly_posts = usage.get('hourly_posts', 0)
            daily_posts = usage.get('daily_posts', 0)
            safety_score = usage.get('safety_score', 100.0)
            total_hourly_posts += hourly_posts
            total_daily_posts += daily_posts
            total_safety_score += safety_score
            if usage.get('is_available', True):
                available_workers += 1
        
        if workers:
            avg_safety = total_safety_score / len(workers)
            lines.append(f"📊 **Overview:**")
            lines.append(f"• Total Workers: {len(workers)}")
            lines.append(f"• Available: {available_workers}")
            lines.append(f"• Total Hourly Posts: {total_hourly_posts}")
            lines.append(f"• Total Daily Posts: {total_daily_posts}")
            lines.append(f"• Avg Safety Score: {avg_safety:.1f}")
            
            # Add workload information
            due_slots = await db.get_active_ads_to_send()
            user_slots = [slot for slot in due_slots if slot.get('slot_type') == 'user']
            admin_slots = [slot for slot in due_slots if slot.get('slot_type') == 'admin']
            
            lines.append("")
            lines.append(f"📋 **Current Workload:**")
            lines.append(f"• User ads pending: {len(user_slots)}")
            lines.append(f"• Admin ads pending: {len(admin_slots)}")
            lines.append(f"• Total workload: {len(due_slots)}")
            
            # Show top 10 workers only to avoid message length issues
            lines.append("")
            lines.append(f"🔝 **Top 10 Workers (by usage):**")
            
            # Get worker usage data and sort by usage
            worker_data = []
            for worker in workers:
                usage = await db.get_worker_usage(worker['worker_id']) or {}
                hourly_posts = usage.get('hourly_posts', 0)
                daily_posts = usage.get('daily_posts', 0)
                safety_score = usage.get('safety_score', 100.0)
                status = "✅" if usage.get('is_available', True) else "❌"
                worker_data.append({
                    'id': worker['worker_id'],
                    'hourly': hourly_posts,
                    'daily': daily_posts,
                    'safety': safety_score,
                    'status': status,
                    'total_usage': hourly_posts + daily_posts
                })
            
            # Sort by total usage and show top 10
            worker_data.sort(key=lambda x: x['total_usage'], reverse=True)
            for i, worker in enumerate(worker_data[:10]):
                lines.append(f"{i+1}. Worker {worker['id']} {worker['status']} | H:{worker['hourly']} D:{worker['daily']} | Safety:{worker['safety']:.1f}")
            
            if len(workers) > 10:
                lines.append(f"... and {len(workers) - 10} more workers")
            
        await send_admin_message(update, "\n".join(lines), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting worker status: {e}")
        await send_admin_message(update, "❌ Error getting worker status.")

async def admin_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active admin warnings."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        warnings = await db.get_unresolved_warnings()
        if not warnings:
            await send_admin_message(update, "✅ No active warnings.")
            return
        # Group and truncate
        grouped = {}
        for w in warnings:
            key = (w['warning_type'], w['severity'])
            grouped.setdefault(key, []).append(w)
        lines = ["⚠️ Admin Warnings (latest 5 per type):\n"]
        for (wtype, sev), items in grouped.items():
            lines.append(f"• {wtype} [{sev}] — {len(items)} total")
            for w in items[:5]:
                lines.append(f"  - {w['message']} ({w['created_at']})")
        await send_admin_message(update, "\n".join(lines))
        
    except Exception as e:
        logger.error(f"Error getting admin warnings: {e}")
        await send_admin_message(update, "❌ Error getting admin warnings.")

async def increase_worker_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Increase worker limits for all workers."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        workers = await db.get_all_workers()
        
        if not workers:
            await send_admin_message(update, "🤖 No workers found.")
            return
        
        updated_count = 0
        for worker in workers:
            success = await db.increase_worker_limits(worker['worker_id'])
            if success:
                updated_count += 1
        
        await send_admin_message(update, f"✅ Increased limits for {updated_count}/{len(workers)} workers.")
        
    except Exception as e:
        logger.error(f"Error increasing worker limits: {e}")
        await send_admin_message(update, "❌ Error increasing worker limits.")

async def worker_capacity_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check worker capacity and load."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        available_workers = await db.get_available_workers()
        all_workers = await db.get_all_workers()
        due_slots = await db.get_active_ads_to_send()
        
        # Separate user and admin slots
        user_slots = [slot for slot in due_slots if slot.get('slot_type') == 'user']
        admin_slots = [slot for slot in due_slots if slot.get('slot_type') == 'admin']
        
        pending_ads = len(due_slots)
        num_available = len(available_workers)
        load_ratio = (pending_ads / num_available) if num_available else 0

        text = "📊 Capacity Check:\n\n"
        text += f"Workers: {num_available}/{len(all_workers)} available\n"
        text += f"**Total Pending Ads: {pending_ads}**\n"
        text += f"  • User ads: {len(user_slots)}\n"
        text += f"  • Admin ads: {len(admin_slots)}\n"
        text += f"Load Ratio: {load_ratio:.1f} ads/available worker\n"
        if pending_ads == 0:
            text += "Status: ✅ Idle\n"
        elif load_ratio > 5:
            text += "Status: 🔴 High Load\n"
        elif load_ratio > 2:
            text += "Status: 🟠 Moderate Load\n"
        else:
            text += "Status: 🟢 Normal\n"
        
        await send_admin_message(update, text)
        
    except Exception as e:
        logger.error(f"Error checking worker capacity: {e}")
        await send_admin_message(update, "❌ Error checking worker capacity.")

async def activate_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate a subscription for a user manually."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    if not context.args or len(context.args) < 3:
        await send_admin_message(update, 
            "Usage: /activate_subscription <user_id> <tier> <days>\n"
            "Example: /activate_subscription 123456789 enterprise 30\n"
            "Tiers: basic, pro, enterprise"
        )
        return
    
    try:
        user_id = int(context.args[0])
        tier = context.args[1].lower()
        days = int(context.args[2])
        
        await send_admin_message(update, f"🔧 Processing activation for user {user_id}, tier {tier}, {days} days...")
        
        # Validate tier
        valid_tiers = ['basic', 'pro', 'enterprise']
        if tier not in valid_tiers:
            await send_admin_message(update, f"❌ Invalid tier. Valid tiers: {', '.join(valid_tiers)}")
            return
        
        # Validate days
        if days <= 0 or days > 365:
            await send_admin_message(update, "❌ Invalid days. Must be between 1 and 365.")
            return
        
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        await send_admin_message(update, "✅ Database connection verified.")
        
        # Check if user exists
        try:
            user = await asyncio.wait_for(db.get_user(user_id), timeout=10)
        except Exception as e:
            await send_admin_message(update, f"❌ Database busy/error on get_user: {e}")
            return
        if not user:
            await send_admin_message(update, f"❌ User {user_id} not found in database.")
            await send_admin_message(update, "💡 Creating user first...")
            
            # Create user if doesn't exist
            try:
                success = await asyncio.wait_for(db.create_or_update_user(
                user_id=user_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name
            ), timeout=10)
            except Exception as e:
                await send_admin_message(update, f"❌ Database error creating user: {e}")
                return
            if not success:
                await send_admin_message(update, "❌ Failed to create user.")
                return
            await send_admin_message(update, "✅ User created successfully.")
        
        # Activate subscription
        await send_admin_message(update, "🔄 Activating subscription...")
        try:
            success = await asyncio.wait_for(db.activate_subscription(user_id, tier, days), timeout=15)
        except Exception as e:
            await send_admin_message(update, f"❌ Database busy/error on activation: {e}")
            return
        
        if success:
            await send_admin_message(update, 
                f"✅ Subscription activated successfully!\n"
                f"**User:** {user_id}\n"
                f"**Tier:** {tier.capitalize()}\n"
                f"**Duration:** {days} days"
            )
        else:
            await send_admin_message(update, "❌ Failed to activate subscription.")
            
    except ValueError as e:
        await send_admin_message(update, f"❌ Invalid user_id or days. Must be numbers. Error: {e}")
    except Exception as e:
        logger.error(f"Error activating subscription: {e}")
        await send_admin_message(update, f"❌ Error activating subscription: {str(e)}")

async def worker_bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show overview of worker bans."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get ban summary
        ban_summary = await db.get_banned_workers_summary()
        
        text = "🚫 **Worker Ban Overview**\n\n"
        text += f"📊 **Total Active Bans:** {ban_summary['total_active_bans']}\n\n"
        
        if ban_summary['bans_by_worker']:
            text += "🤖 **Bans by Worker:**\n"
            for worker in ban_summary['bans_by_worker']:
                text += f"• Worker {worker['worker_id']}: {worker['ban_count']} bans\n"
            text += "\n"
        
        if ban_summary['bans_by_type']:
            text += "🚫 **Bans by Type:**\n"
            for ban_type in ban_summary['bans_by_type']:
                text += f"• {ban_type['ban_type']}: {ban_type['ban_count']} bans\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting worker bans: {e}")
        await send_admin_message(update, f"❌ Error getting worker bans: {str(e)}")

async def ban_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed ban information for a specific worker."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    if not context.args:
        await send_admin_message(update, 
            "Usage: /ban_details <worker_id>\n"
            "Example: /ban_details 1"
        )
        return
    
    try:
        worker_id = int(context.args[0])
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get bans for specific worker
        bans = await db.get_worker_bans(worker_id=worker_id, active_only=True)
        
        if not bans:
            await send_admin_message(update, f"✅ Worker {worker_id} has no active bans.")
            return
        
        text = f"🚫 **Ban Details for Worker {worker_id}**\n\n"
        
        for i, ban in enumerate(bans, 1):
            text += f"**Ban {i}:**\n"
            text += f"• Destination: `{ban['destination_id']}`\n"
            text += f"• Type: {ban['ban_type']}\n"
            text += f"• Reason: {ban['ban_reason'][:100]}...\n"
            text += f"• Banned at: {ban['banned_at']}\n"
            if ban.get('estimated_unban_time'):
                text += f"• Estimated unban: {ban['estimated_unban_time']}\n"
            text += "\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except ValueError:
        await send_admin_message(update, "❌ Invalid worker ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error getting ban details: {e}")
        await send_admin_message(update, f"❌ Error getting ban details: {str(e)}")

async def clear_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear a ban for a specific worker and destination."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    if len(context.args) < 2:
        await send_admin_message(update, 
            "Usage: /clear_ban <worker_id> <destination_id>\n"
            "Example: /clear_ban 1 @testgroup"
        )
        return
    
    try:
        worker_id = int(context.args[0])
        destination_id = context.args[1]
        
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Clear the ban
        success = await db.clear_worker_ban(worker_id, destination_id)
        
        if success:
            await send_admin_message(update, 
                f"✅ Ban cleared successfully!\n"
                f"**Worker:** {worker_id}\n"
                f"**Destination:** `{destination_id}`"
            )
        else:
            await send_admin_message(update, "❌ Failed to clear ban or ban not found.")
        
    except ValueError:
        await send_admin_message(update, "❌ Invalid worker ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error clearing ban: {e}")
        await send_admin_message(update, f"❌ Error clearing ban: {str(e)}")

async def ban_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed ban statistics and trends."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get recent posting activity with ban detections
        activity = await db.get_recent_posting_activity(hours=24)
        
        # Get all active bans
        all_bans = await db.get_worker_bans(active_only=True)
        
        # Calculate ban statistics
        total_bans = len(all_bans)
        ban_types = {}
        worker_bans = {}
        
        for ban in all_bans:
            # Count by type
            ban_type = ban['ban_type']
            ban_types[ban_type] = ban_types.get(ban_type, 0) + 1
            
            # Count by worker
            worker_id = ban['worker_id']
            worker_bans[worker_id] = worker_bans.get(worker_id, 0) + 1
        
        text = "📊 **Ban Statistics (24h)**\n\n"
        text += f"🚫 **Total Active Bans:** {total_bans}\n"
        text += f"📈 **Ban Detections (24h):** {activity.get('ban_detections', 0)}\n"
        text += f"📊 **Total Posts (24h):** {activity.get('total_posts', 0)}\n"
        text += f"📉 **Ban Rate:** {(activity.get('ban_detections', 0) / max(activity.get('total_posts', 1), 1) * 100):.1f}%\n\n"
        
        if ban_types:
            text += "🚫 **Bans by Type:**\n"
            for ban_type, count in sorted(ban_types.items(), key=lambda x: x[1], reverse=True):
                text += f"• {ban_type}: {count} bans\n"
            text += "\n"
        
        if worker_bans:
            text += "🤖 **Most Banned Workers:**\n"
            sorted_workers = sorted(worker_bans.items(), key=lambda x: x[1], reverse=True)
            for worker_id, ban_count in sorted_workers[:5]:
                text += f"• Worker {worker_id}: {ban_count} bans\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting ban stats: {e}")
        await send_admin_message(update, f"❌ Error getting ban statistics: {str(e)}")

async def destination_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show destination health overview."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get destination health summary
        health_summary = await db.get_destination_health_summary()
        
        text = "🏥 **Destination Health Overview**\n\n"
        text += f"📊 **Total Destinations:** {health_summary['total_destinations']}\n"
        text += f"📈 **Average Success Rate:** {health_summary['average_success_rate']:.1f}%\n\n"
        
        if health_summary['health_categories']:
            text += "🏥 **Health Categories:**\n"
            for category in health_summary['health_categories']:
                text += f"• {category['category']}: {category['count']} destinations\n"
            text += "\n"
        
        if health_summary.get('worst_destinations'):
            text += "🚨 **Worst Performing Destinations:**\n"
            for dest in health_summary['worst_destinations'][:5]:
                text += f"• `{dest['destination_id']}`: {dest['success_rate']:.1f}% success rate\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting destination health: {e}")
        await send_admin_message(update, f"❌ Error getting destination health: {str(e)}")

async def destination_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed health information for a specific destination."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    if not context.args:
        await send_admin_message(update, 
            "Usage: /destination_details <destination_id>\n"
            "Example: /destination_details @testgroup"
        )
        return
    
    try:
        destination_id = context.args[0]
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get destination health
        health_data = await db.get_destination_health(destination_id)
        
        if not health_data:
            await send_admin_message(update, f"❌ Destination `{destination_id}` not found in health data.")
            return
        
        text = f"🏥 **Destination Health: `{destination_id}`**\n\n"
        text += f"📊 **Success Rate:** {health_data['success_rate']:.1f}%\n"
        text += f"📈 **Total Attempts:** {health_data['total_attempts']}\n"
        text += f"✅ **Successful Posts:** {health_data['successful_posts']}\n"
        text += f"❌ **Failed Posts:** {health_data['failed_posts']}\n\n"
        
        if health_data.get('last_success'):
            text += f"✅ **Last Success:** {health_data['last_success']}\n"
        if health_data.get('last_failure'):
            text += f"❌ **Last Failure:** {health_data['last_failure']}\n"
        
        text += f"\n🕐 **Last Updated:** {health_data['updated_at']}\n"
        
        # Add health status
        if health_data['success_rate'] >= 80:
            status = "🟢 Excellent"
        elif health_data['success_rate'] >= 60:
            status = "🟡 Good"
        elif health_data['success_rate'] >= 40:
            status = "🟠 Fair"
        else:
            status = "🔴 Poor"
        
        text += f"🏥 **Health Status:** {status}\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting destination details: {e}")
        await send_admin_message(update, f"❌ Error getting destination details: {str(e)}")

async def problematic_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show problematic destinations that need attention."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get problematic destinations
        problematic = await db.get_problematic_destinations(min_failures=1)
        
        if not problematic:
            await send_admin_message(update, "✅ No problematic destinations found!")
            return
        
        text = "🚨 **Problematic Destinations**\n\n"
        text += f"📊 **Found {len(problematic)} destinations needing attention:**\n\n"
        
        for i, dest in enumerate(problematic, 1):
            text += f"**{i}. `{dest['destination_id']}`**\n"
            text += f"• Success Rate: {dest['success_rate']:.1f}%\n"
            text += f"• Total Attempts: {dest['total_attempts']}\n"
            text += f"• Failed Posts: {dest['failed_posts']}\n"
            
            # Add recommendation
            if dest['success_rate'] < 30:
                recommendation = "🔴 Consider removal"
            elif dest['success_rate'] < 50:
                recommendation = "🟠 Monitor closely"
            else:
                recommendation = "🟡 Watch for trends"
            
            text += f"• Recommendation: {recommendation}\n\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting problematic destinations: {e}")
        await send_admin_message(update, f"❌ Error getting problematic destinations: {str(e)}")

async def health_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed health statistics and trends."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get destination health summary
        health_summary = await db.get_destination_health_summary()
        
        # Get problematic destinations
        problematic = await db.get_problematic_destinations(min_failures=1)
        
        # Get recent posting activity
        activity = await db.get_recent_posting_activity(hours=24)
        
        text = "📊 **Health Statistics (24h)**\n\n"
        text += f"🏥 **Overall Health:**\n"
        text += f"• Total destinations: {health_summary['total_destinations']}\n"
        text += f"• Average success rate: {health_summary['average_success_rate']:.1f}%\n"
        text += f"• Problematic destinations: {len(problematic)}\n\n"
        
        text += f"📈 **Recent Activity:**\n"
        text += f"• Total posts: {activity.get('total_posts', 0)}\n"
        text += f"• Successful posts: {activity.get('successful_posts', 0)}\n"
        text += f"• Failed posts: {activity.get('failed_posts', 0)}\n"
        text += f"• Success rate: {activity.get('success_rate', 0):.1f}%\n\n"
        
        if health_summary['health_categories']:
            text += "🏥 **Health Distribution:**\n"
            for category in health_summary['health_categories']:
                percentage = (category['count'] / health_summary['total_destinations']) * 100
                text += f"• {category['category']}: {category['count']} ({percentage:.1f}%)\n"
            text += "\n"
        
        if problematic:
            text += "🚨 **Top Problematic Destinations:**\n"
            for dest in problematic[:5]:
                text += f"• `{dest['destination_id']}`: {dest['success_rate']:.1f}% success rate\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting health stats: {e}")
        await send_admin_message(update, f"❌ Error getting health statistics: {str(e)}")

async def posting_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent posting history."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get recent posting history
        limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
        history = await db.get_posting_history(limit=limit)
        
        if not history:
            await send_admin_message(update, "📋 No posting history found.")
            return
        
        text = f"📋 **Recent Posting History (Last {len(history)} posts)**\n\n"
        
        for i, record in enumerate(history, 1):
            status = "✅" if record['success'] else "❌"
            text += f"**{i}. {status} {record['destination_id']}**\n"
            text += f"• Worker: {record['worker_id']}\n"
            text += f"• Slot: {record['slot_id']} ({record['slot_type']})\n"
            text += f"• Posted: {record['posted_at']}\n"
            
            if not record['success'] and record['error_message']:
                text += f"• Error: {record['error_message'][:50]}...\n"
            
            if record['ban_detected']:
                text += f"• 🚫 Ban detected: {record['ban_type']}\n"
            
            text += "\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting posting history: {e}")
        await send_admin_message(update, f"❌ Error getting posting history: {str(e)}")

async def posting_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show posting activity statistics."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get recent posting activity
        hours = int(context.args[0]) if context.args and context.args[0].isdigit() else 24
        activity = await db.get_recent_posting_activity(hours=hours)
        
        text = f"📈 **Posting Activity (Last {hours}h)**\n\n"
        text += f"📊 **Total Posts:** {activity['total_posts']}\n"
        text += f"✅ **Successful Posts:** {activity['successful_posts']}\n"
        text += f"❌ **Failed Posts:** {activity['failed_posts']}\n"
        text += f"🚫 **Ban Detections:** {activity['ban_detections']}\n"
        text += f"📈 **Success Rate:** {activity['success_rate']:.1f}%\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting posting activity: {e}")
        await send_admin_message(update, f"❌ Error getting posting activity: {str(e)}")

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show comprehensive system status."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get all status data
        activity = await db.get_recent_posting_activity(hours=24)
        ban_summary = await db.get_banned_workers_summary()
        health_summary = await db.get_destination_health_summary()
        
        text = "🖥️ **System Status Overview**\n\n"
        
        # Posting activity
        text += "📈 **Posting Activity (24h):**\n"
        text += f"• Total posts: {activity['total_posts']}\n"
        text += f"• Success rate: {activity['success_rate']:.1f}%\n"
        text += f"• Ban detections: {activity['ban_detections']}\n\n"
        
        # Worker bans
        text += "🚫 **Worker Bans:**\n"
        text += f"• Active bans: {ban_summary['total_active_bans']}\n"
        text += f"• Workers affected: {len(ban_summary['bans_by_worker'])}\n\n"
        
        # Destination health
        text += "🏥 **Destination Health:**\n"
        text += f"• Total destinations: {health_summary['total_destinations']}\n"
        text += f"• Average success rate: {health_summary['average_success_rate']:.1f}%\n"
        
        problematic = await db.get_problematic_destinations(min_failures=1)
        text += f"• Problematic destinations: {len(problematic)}\n\n"
        
        # Overall system health
        if activity['success_rate'] >= 80 and ban_summary['total_active_bans'] == 0:
            system_health = "🟢 Excellent"
        elif activity['success_rate'] >= 60 and ban_summary['total_active_bans'] <= 2:
            system_health = "🟡 Good"
        elif activity['success_rate'] >= 40:
            system_health = "🟠 Fair"
        else:
            system_health = "🔴 Poor"
        
        text += f"🏥 **Overall System Health:** {system_health}\n"
        
        # Add back button
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="cmd:admin_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_admin_message(update, text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        await send_admin_message(update, f"❌ Error getting system status: {str(e)}")

async def admin_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view all suggestions."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    if not SUGGESTIONS_AVAILABLE:
        await send_admin_message(update, "❌ Suggestions system not available.")
        return
    
    try:
        suggestions = suggestion_manager.get_all_suggestions(limit=20)
        
        if not suggestions:
            await send_admin_message(update, "📋 No suggestions found.")
            return
        
        text = f"📋 **All Suggestions** (Last {len(suggestions)})\n\n"
        
        for suggestion in suggestions:
            timestamp = datetime.fromisoformat(suggestion["timestamp"]).strftime("%Y-%m-%d %H:%M")
            status_emoji = "⏳" if suggestion["status"] == "pending" else "✅" if suggestion["status"] == "approved" else "❌"
            
            text += f"**ID {suggestion['id']}:** {status_emoji} {suggestion['status'].title()}\n"
            text += f"👤 @{suggestion['username']} (ID: {suggestion['user_id']})\n"
            text += f"📅 {timestamp}\n"
            text += f"💬 {suggestion['suggestion'][:150]}{'...' if len(suggestion['suggestion']) > 150 else ''}\n\n"
        
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_suggestions: {e}")
        await send_admin_message(update, "❌ Error loading suggestions.")

async def redistribute_workers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redistribute all ad slots across all available workers."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        await send_admin_message(update, "🔄 Redistributing workers across all ad slots...")
        
        # Get current worker count
        worker_count = await db._get_available_worker_count()
        
        # Redistribute workers
        success = await db.redistribute_workers_for_all_slots()
        
        if success:
            await send_admin_message(update, 
                f"✅ Successfully redistributed all ad slots across {worker_count} workers!\n\n"
                f"🔄 Workers are now distributed using round-robin allocation.\n"
                f"📊 New ad slots will automatically use all available workers."
            )
        else:
            await send_admin_message(update, "❌ Failed to redistribute workers. Check logs for details.")
        
    except Exception as e:
        logger.error(f"Error redistributing workers: {e}")
        await send_admin_message(update, f"❌ Error redistributing workers: {str(e)}")

async def worker_distribution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current worker distribution across ad slots."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        # Get worker distribution
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # Count slots per worker
        cursor.execute('''
            SELECT assigned_worker_id, COUNT(*) as slot_count, 
                   COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_slots
            FROM ad_slots 
            GROUP BY assigned_worker_id
            ORDER BY assigned_worker_id
        ''')
        
        distribution = cursor.fetchall()
        
        # Get total workers available
        available_workers = await db._get_available_worker_count()
        
        text = f"🤖 **Worker Distribution**\n\n"
        text += f"📊 **Available Workers:** {available_workers}\n"
        text += f"📈 **Workers with Slots:** {len(distribution)}\n\n"
        
        total_slots = 0
        total_active = 0
        
        for worker_id, slot_count, active_slots in distribution:
            text += f"🤖 **Worker {worker_id}:** {slot_count} slots ({active_slots} active)\n"
            total_slots += slot_count
            total_active += active_slots
        
        text += f"\n📊 **Totals:** {total_slots} slots ({total_active} active)\n"
        
        # Check if distribution is balanced
        if len(distribution) < available_workers:
            text += f"\n⚠️ **Warning:** Only {len(distribution)} workers have slots assigned.\n"
            text += f"Use /redistribute_workers to distribute across all {available_workers} workers."
        
        conn.close()
        await send_admin_message(update, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting worker distribution: {e}")
        await send_admin_message(update, f"❌ Error getting worker distribution: {str(e)}")

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show comprehensive admin statistics."""
    try:
        if not await check_admin(update, context):
            return

        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return

        # Get statistics
        try:
            # Get user count
            users = await db.get_all_users()
            total_users = len(users) if users else 0
            
            # Get subscription count
            subscriptions = await db.get_all_subscriptions()
            active_subscriptions = len([s for s in subscriptions if s.get('is_active', False)]) if subscriptions else 0
            
            # Get payment count
            payments = await db.get_all_payments()
            total_payments = len(payments) if payments else 0
            completed_payments = len([p for p in payments if p.get('status') == 'completed']) if payments else 0
            
            # Get ad slots count
            ad_slots = await db.get_ad_slots()
            total_slots = len(ad_slots) if ad_slots else 0
            active_slots = len([s for s in ad_slots if s.get('is_active', False)]) if ad_slots else 0
            
            # Get worker count
            workers = await db.get_available_workers()
            total_workers = len(workers) if workers else 0
            
            # Calculate revenue
            revenue = sum([float(p.get('amount_usd', 0)) for p in payments if p.get('status') == 'completed']) if payments else 0
            
            stats_text = f"""📊 **Admin Statistics**

👥 **Users:**
• Total Users: {total_users}
• Active Subscriptions: {active_subscriptions}

💰 **Payments:**
• Total Payments: {total_payments}
• Completed: {completed_payments}
• Revenue: ${revenue:.2f}

📢 **Advertising:**
• Total Ad Slots: {total_slots}
• Active Slots: {active_slots}

🤖 **Workers:**
• Available Workers: {total_workers}

📈 **Success Rate:**
• Payment Success: {(completed_payments/total_payments*100) if total_payments > 0 else 0:.1f}%
• Slot Utilization: {(active_slots/total_slots*100) if total_slots > 0 else 0:.1f}%"""

            keyboard = [
                [InlineKeyboardButton("📊 Detailed Analytics", callback_data="admin_detailed_stats")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
                [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await send_admin_message(update, stats_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            await send_admin_message(update, f"❌ Error loading statistics: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in show_admin_stats: {e}")
        await send_admin_message(update, "❌ Error displaying admin statistics.")

async def show_posting_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show posting statistics and performance metrics."""
    try:
        if not await check_admin(update, context):
            return

        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return

        try:
            # Get posting history
            posting_history = await db.get_posting_history()
            total_posts = len(posting_history) if posting_history else 0
            successful_posts = len([p for p in posting_history if p.get('success', False)]) if posting_history else 0
            failed_posts = total_posts - successful_posts
            
            # Get worker usage
            workers = await db.get_available_workers()
            total_workers = len(workers) if workers else 0
            active_workers = len([w for w in workers if w.get('hourly_usage', 0) > 0]) if workers else 0
            
            # Get recent activity
            recent_posts = [p for p in posting_history if p.get('created_at')] if posting_history else []
            recent_posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            last_24h_posts = len([p for p in recent_posts[:100] if p.get('created_at')])  # Approximate
            
            # Calculate success rate
            success_rate = (successful_posts / total_posts * 100) if total_posts > 0 else 0
            
            stats_text = f"""📈 **Posting Statistics**

📨 **Posts:**
• Total Posts: {total_posts}
• Successful: {successful_posts}
• Failed: {failed_posts}
• Success Rate: {success_rate:.1f}%

🤖 **Workers:**
• Total Workers: {total_workers}
• Active Workers: {active_workers}
• Utilization: {(active_workers/total_workers*100) if total_workers > 0 else 0:.1f}%

⏰ **Recent Activity:**
• Last 24h Posts: ~{last_24h_posts}

📊 **Performance:**
• Average Posts/Hour: {last_24h_posts/24:.1f}"""

            keyboard = [
                [InlineKeyboardButton("📊 Detailed Posting", callback_data="admin_posting_details")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="posting_stats")],
                [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await send_admin_message(update, stats_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting posting stats: {e}")
            await send_admin_message(update, f"❌ Error loading posting statistics: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in show_posting_stats: {e}")
        await send_admin_message(update, "❌ Error displaying posting statistics.")

async def show_slot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show ad slot statistics and management."""
    try:
        if not await check_admin(update, context):
            return

        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return

        try:
            # Get ad slots
            ad_slots = await db.get_ad_slots()
            total_slots = len(ad_slots) if ad_slots else 0
            active_slots = len([s for s in ad_slots if s.get('is_active', False)]) if ad_slots else 0
            paused_slots = total_slots - active_slots
            
            # Get slot usage by tier
            subscriptions = await db.get_all_subscriptions()
            tier_counts = {}
            if subscriptions:
                for sub in subscriptions:
                    tier = sub.get('tier', 'unknown')
                    tier_counts[tier] = tier_counts.get(tier, 0) + 1
            
            # Get recent slot activity
            recent_slots = [s for s in ad_slots if s.get('last_sent_at')] if ad_slots else []
            recent_slots.sort(key=lambda x: x.get('last_sent_at', ''), reverse=True)
            active_recently = len([s for s in recent_slots[:10] if s.get('is_active', False)])
            
            stats_text = f"""📋 **Ad Slot Statistics**

🎯 **Slots:**
• Total Slots: {total_slots}
• Active: {active_slots}
• Paused: {paused_slots}
• Utilization: {(active_slots/total_slots*100) if total_slots > 0 else 0:.1f}%

💎 **By Tier:**
"""
            for tier, count in tier_counts.items():
                stats_text += f"• {tier.title()}: {count}\n"
            
            stats_text += f"""
⏰ **Recent Activity:**
• Recently Active: {active_recently}/10

📊 **Management:**
• Paused Rate: {(paused_slots/total_slots*100) if total_slots > 0 else 0:.1f}%"""

            keyboard = [
                [InlineKeyboardButton("📋 Manage Slots", callback_data="admin_slots")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="slot_stats")],
                [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await send_admin_message(update, stats_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting slot stats: {e}")
            await send_admin_message(update, f"❌ Error loading slot statistics: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in show_slot_stats: {e}")
        await send_admin_message(update, "❌ Error displaying slot statistics.")

async def show_system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system status and health metrics."""
    try:
        if not await check_admin(update, context):
            return

        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return

        try:
            # Get system health metrics
            workers = await db.get_available_workers()
            total_workers = len(workers) if workers else 0
            healthy_workers = len([w for w in workers if w.get('is_active', True)]) if workers else 0
            
            # Get database status
            db_status = "✅ Healthy"
            try:
                # Test database connection
                await db.get_available_workers()
            except Exception:
                db_status = "❌ Error"
            
            # Get posting service status
            posting_status = "✅ Active"
            try:
                # Check if posting service is running
                posting_history = await db.get_posting_history()
                if not posting_history:
                    posting_status = "⚠️ No Activity"
            except Exception:
                posting_status = "❌ Error"
            
            # Get payment system status
            payment_status = "✅ Active"
            try:
                payments = await db.get_all_payments()
                if not payments:
                    payment_status = "⚠️ No Payments"
            except Exception:
                payment_status = "❌ Error"
            
            # Calculate overall health
            health_score = 0
            if db_status == "✅ Healthy":
                health_score += 25
            if posting_status == "✅ Active":
                health_score += 25
            if payment_status == "✅ Active":
                health_score += 25
            if healthy_workers == total_workers:
                health_score += 25
            
            overall_status = "🟢 Excellent" if health_score >= 90 else "🟡 Good" if health_score >= 70 else "🟠 Fair" if health_score >= 50 else "🔴 Poor"
            
            stats_text = f"""🖥️ **System Status**

📊 **Overall Health:** {overall_status} ({health_score}%)

🗄️ **Database:** {db_status}
📨 **Posting Service:** {posting_status}
💳 **Payment System:** {payment_status}

🤖 **Workers:**
• Total: {total_workers}
• Healthy: {healthy_workers}
• Status: {"✅ All Healthy" if healthy_workers == total_workers else "⚠️ Some Issues"}

⚡ **Performance:**
• Worker Utilization: {(healthy_workers/total_workers*100) if total_workers > 0 else 0:.1f}%
• System Load: {"🟢 Low" if health_score >= 90 else "🟡 Medium" if health_score >= 70 else "🟠 High" if health_score >= 50 else "🔴 Critical"}"""

            keyboard = [
                [InlineKeyboardButton("🔍 Detailed Check", callback_data="system_check")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="system_status")],
                [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await send_admin_message(update, stats_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            await send_admin_message(update, f"❌ Error loading system status: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in show_system_status: {e}")
        await send_admin_message(update, "❌ Error displaying system status.")
async def show_revenue_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show revenue statistics."""
    try:
        query = update.callback_query
        await query.answer()
        
        # Get database manager
        db = context.bot_data.get('db')
        if not db:
            await query.edit_message_text("Database not available")
            return
        
        # Get revenue stats
        try:
            stats = await db.get_revenue_stats()
        except Exception as e:
            logger.error(f"Error getting revenue stats: {e}")
            stats = {
                'total_revenue': 0,
                'monthly_revenue': 0,
                'weekly_revenue': 0,
                'daily_revenue': 0,
                'active_subscriptions': 0,
                'total_transactions': 0
            }
        
        # Format message
        message = "💰 Revenue Statistics\n\n"
        message += f"Total Revenue: ${stats.get('total_revenue', 0):.2f}\n"
        message += f"This Month: ${stats.get('monthly_revenue', 0):.2f}\n"
        message += f"This Week: ${stats.get('weekly_revenue', 0):.2f}\n"
        message += f"Today: ${stats.get('daily_revenue', 0):.2f}\n\n"
        
        message += f"Active Subscriptions: {stats.get('active_subscriptions', 0)}\n"
        message += f"Total Transactions: {stats.get('total_transactions', 0)}\n"
        
        # Add back button
        keyboard = [
            [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error showing revenue stats: {e}")
        if update.callback_query:
            await update.callback_query.answer("Error getting revenue stats")
            await update.callback_query.edit_message_text(
                f"Error getting revenue stats: {e}\n\n"
                "Please try again later or contact support.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin_menu")]
                ])
            )

async def show_worker_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show worker status."""
    try:
        query = update.callback_query
        await query.answer()
        
        # Get database manager
        db = context.bot_data.get('db')
        if not db:
            await query.edit_message_text("Database not available")
            return
        
        # Get available workers
        try:
            workers = await db.get_available_workers()
        except Exception as e:
            logger.error(f"Error getting available workers: {e}")
            workers = []
        
        # Format message
        message = "👷 Worker Status\n\n"
        message += f"Total Workers: {len(workers)}\n\n"
        
        # Show all workers with their status
        message += "Worker status (ID | hourly/daily):\n"
        for worker in workers:
            worker_id = worker.get('worker_id', 'N/A')
            hourly_posts = worker.get('hourly_posts', worker.get('hourly_usage', 0))
            daily_posts = worker.get('daily_posts', worker.get('daily_usage', 0))
            hourly_limit = worker.get('hourly_limit', 15)
            daily_limit = worker.get('daily_limit', 100)
            is_active = worker.get('is_active', 1) == 1
            
            status = "✅ Active" if is_active else "❌ Inactive"
            message += f"• {worker_id} | {hourly_posts}/{hourly_limit} h, {daily_posts}/{daily_limit} d - {status}\n"
        
        # Add back button
        keyboard = [
            [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error showing worker status: {e}")
        if update.callback_query:
            await update.callback_query.answer("Error getting worker status")
            await update.callback_query.edit_message_text(
                f"Error getting worker status: {e}\n\n"
                "Please try again later or contact support.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin_menu")]
                ])
            )
