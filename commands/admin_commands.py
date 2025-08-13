from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import re
import sqlite3
from typing import Dict, List, Set, Optional
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

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
                    await update.message.reply_text(f"✅ Category for `{group_id}` set to '{text}'.", parse_mode='Markdown')
                else:
                    await update.message.reply_text("❌ Failed to update category.")
            return

        # Bulk add groups: category -> list of chats
        if context.user_data.get('awaiting_bulk_groups'):
            context.user_data.pop('awaiting_bulk_groups', None)
            if not db:
                await update.message.reply_text("❌ Database not available.")
                return
            parsed = _parse_bulk_groups_text(text)
            if not parsed:
                await update.message.reply_text("❌ Could not parse any categories or chats.")
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
            await update.message.reply_text(
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
                await update.message.reply_text("❌ Database not available.")
                return
            # Split by commas or whitespace
            tokens = [t for t in [s.strip() for s in text.replace(',', ' ').split()] if t]
            if not tokens:
                await update.message.reply_text("❌ No chats provided.")
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
            await update.message.reply_text(f"➕ Added {added} chats to category '{category}'.{' Errors: ' + str(errors) if errors else ''}")
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
                await update.message.reply_text("❌ Error processing admin content.")
                context.user_data.clear()
                return

    except Exception as e:
        logger.error(f"Error in handle_admin_text: {e}")
        await update.message.reply_text("❌ Error processing input.")

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
        await update.message.reply_text("❌ Admin access required.")
        return
    context.user_data['awaiting_bulk_groups'] = True
    await update.message.reply_text(
        "📥 Send the list in this format:\n\n"
        "Category A:\nhttps://t.me/username1\nhttps://t.me/username2/123\n\n"
        "Category B:\nhttps://t.me/another_chat\n...\n\n"
        "I will parse categories and add the chats. Duplicates are skipped."
    )

async def system_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run end-to-end health checks (no terminal required). Admin only."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
    db = context.bot_data.get('db')
    if not db:
        await update.message.reply_text("❌ Database not available in context.")
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

    report_lines.append("")
    report_lines.append(f"Result: {passed} passed, {failed} failed")
    await update.message.reply_text("\n".join(report_lines))

async def scheduler_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick DB-driven scheduler readiness check."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
    db = context.bot_data.get('db')
    due = await db.get_active_ads_to_send()
    workers = await db.get_available_workers()
    lines = ["🗓 Scheduler Check", f"Due ads now: {len(due)}", f"Available workers: {len(workers)}"]
    await update.message.reply_text("\n".join(lines))

async def schema_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check database schema health and report any issues."""
    if not await check_admin(update, context):
        return
    
    try:
        db = context.bot_data['db']
        if not db:
            await update.message.reply_text("❌ Database not available")
            return
        
        await update.message.reply_text("🔍 Checking database schema...")
        
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
        await update.message.reply_text(report_text)
        
    except Exception as e:
        logger.error(f"Error in schema_check: {e}")
        await update.message.reply_text(f"❌ Schema check failed: {e}")



async def fix_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fix a completed payment that didn't activate subscription. Usage: /fix_payment <payment_id>"""
    if not await check_admin(update, context):
        return
    
    try:
        text = update.message.text.strip()
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text(
                "❌ Usage: /fix_payment <payment_id>\n\n"
                "Example: /fix_payment TON_f900f42b94f74f14"
            )
            return
        
        payment_id = parts[1]
        db = context.bot_data['db']
        
        # Get the payment
        payment = await db.get_payment(payment_id)
        if not payment:
            await update.message.reply_text(f"❌ Payment not found: {payment_id}")
            return
        
        user_id = payment.get('user_id')
        amount = payment.get('amount', 0)
        crypto_type = payment.get('crypto_type', 'TON')
        
        await update.message.reply_text(
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
            await update.message.reply_text(f"⚠️ Could not determine tier automatically, using Basic as fallback")
        
        # Activate subscription
        success = await db.activate_subscription(user_id, tier, 30)
        
        if success:
            await update.message.reply_text(
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
            await update.message.reply_text(f"❌ Failed to activate subscription for user {user_id}")
    
    except Exception as e:
        logger.error(f"Error in fix_payment: {e}")
        await update.message.reply_text(f"❌ Error fixing payment: {e}")

async def test_pricing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test crypto pricing and tier determination. Usage: /test_pricing <amount> <crypto>"""
    if not await check_admin(update, context):
        return
    
    try:
        text = update.message.text.strip()
        parts = text.split()
        if len(parts) != 3:
            await update.message.reply_text(
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
        
        await update.message.reply_text(f"🔍 Testing pricing for {amount} {crypto_type}...")
        
        # Get current price
        price = await payment_processor._get_crypto_price(crypto_type)
        if price:
            usd_value = amount * price
            await update.message.reply_text(
                f"💰 Current Price Data:\n"
                f"{crypto_type}: ${price:.2f} USD\n"
                f"Payment Value: {amount} {crypto_type} = ${usd_value:.2f} USD"
            )
        else:
            await update.message.reply_text(f"❌ Could not fetch {crypto_type} price")
        
        # Determine tier
        tier = await payment_processor._determine_tier_from_amount(amount, crypto_type)
        
        if tier:
            tier_config = payment_processor.tiers[tier]
            await update.message.reply_text(
                f"🎯 Tier Determination:\n"
                f"Result: {tier.title()}\n"
                f"Target Price: ${tier_config['price_usd']} USD\n"
                f"Actual Value: ${usd_value:.2f} USD\n"
                f"Difference: ${abs(usd_value - tier_config['price_usd']):.2f}"
            )
        else:
            await update.message.reply_text("❌ Could not determine tier for this amount")
    
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please use a number.")
    except Exception as e:
        logger.error(f"Error in test_pricing: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def fix_user_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fix a user's ad slots to match their correct subscription tier."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return

    try:
        # Parse command: /fix_user_slots <user_id> <correct_tier>
        command_parts = update.message.text.split()
        if len(command_parts) != 3:
            await update.message.reply_text(
                "❌ **Usage:** /fix_user_slots <user_id> <tier>\n\n"
                "**Example:** /fix_user_slots 7172873873 basic\n\n"
                "**Tiers:** basic, pro, enterprise",
                parse_mode='Markdown'
            )
            return
        
        user_id = int(command_parts[1])
        correct_tier = command_parts[2].lower()
        
        if correct_tier not in ['basic', 'pro', 'enterprise']:
            await update.message.reply_text("❌ Invalid tier. Use: basic, pro, or enterprise")
            return
        
        db = context.bot_data['db']
        
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
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a valid number.")
    except Exception as e:
        logger.error(f"Error fixing user slots: {e}")
        await update.message.reply_text("❌ Error fixing user slots.")

async def delete_test_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a test/bogus user and their data. Admin only.

    Usage: /delete_test_user <user_id>
    """
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /delete_test_user <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except Exception:
        await update.message.reply_text("❌ Invalid user_id")
        return
    db = context.bot_data.get('db')
    ok = await db.delete_user_and_data(user_id)
    if ok:
        await update.message.reply_text(f"✅ Deleted user {user_id} and associated data.")
    else:
        await update.message.reply_text(f"❌ Failed to delete user {user_id}.")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all registered users with their subscription status."""
    if not await check_admin(update, context):
        return
        
    try:
        db = context.bot_data.get('db')
        if not db:
            await update.message.reply_text("❌ Database not available")
            return
            
        users = await db.get_all_users()
        
        if not users:
            await update.message.reply_text("📋 No users found in the database.")
            return
            
        # Format user list (compact for easy viewing, plain text to avoid parse errors)
        lines = ["👥 Registered Users:\n"]
        
        for user in users:
            user_id = user['user_id']
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
            current_chunk = ["👥 Registered Users:\n"]
            
            for user in users:
                user_id = user['user_id']
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
                    current_chunk = ["👥 Users (continued):\n"]
                    
            if current_chunk and len(current_chunk) > 1:
                chunks.append("\n".join(current_chunk))
                    
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(text)
            
        # Add quick delete buttons for easy management (only for small lists)
        if len(users) <= 10:
            keyboard = []
            for user in users:
                user_id = user['user_id']
                username = user.get('username', f"ID{user_id}")
                keyboard.append([InlineKeyboardButton(
                    f"🗑️ Delete {username}", 
                    callback_data=f"admin:delete_user:{user_id}"
                )])
                
            if keyboard:
                await update.message.reply_text(
                    "Quick Actions:", 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
    except Exception as e:
        logger.error(f"Error in list_users: {e}")
        await update.message.reply_text("❌ Error retrieving users")

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin menu with available options."""
    if not await check_admin(update, context):
        if update.callback_query:
            await update.callback_query.answer("❌ Admin access required.")
        else:
            await update.message.reply_text("❌ Admin access required.")
        return
        
    try:
        message_text = "🔧 **Admin Menu**\n\nSelect an admin option:"
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 Admin Slots", callback_data="cmd:admin_slots"),
                InlineKeyboardButton("📊 Admin Stats", callback_data="cmd:admin_stats")
            ],
            [
                InlineKeyboardButton("📋 List Groups", callback_data="cmd:list_groups"),
                InlineKeyboardButton("👥 List Users", callback_data="cmd:list_users")
            ],
            [
                InlineKeyboardButton("🔧 System Check", callback_data="cmd:system_check"),
                InlineKeyboardButton("📡 Posting Status", callback_data="cmd:posting_status")
            ],
            [
                InlineKeyboardButton("⚠️ Failed Groups", callback_data="cmd:failed_groups"),
                InlineKeyboardButton("⏸️ Paused Slots", callback_data="cmd:paused_slots")
            ],
            [
                InlineKeyboardButton("💰 Revenue Stats", callback_data="cmd:revenue_stats"),
                InlineKeyboardButton("🤖 Worker Status", callback_data="cmd:worker_status")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in admin_menu: {e}")
        if update.callback_query:
            await update.callback_query.answer("❌ Error loading admin menu")
        else:
            await update.message.reply_text("❌ Error loading admin menu")

async def test_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test admin command to verify admin functionality."""
    user_id = update.effective_user.id
    await update.message.reply_text(f"🔧 Testing admin command functionality for user {user_id}...")
    
    try:
        # Test config access
        config = context.bot_data.get('config')
        if config:
            await update.message.reply_text(f"✅ Config loaded: {config.bot_name}")
            
            # Show current admin ID
            current_admin_id = config.admin_id
            await update.message.reply_text(f"🔑 Current ADMIN_ID: {current_admin_id}")
            
            # Test admin check
            is_admin = await check_admin(update, context)
            await update.message.reply_text(f"👤 Admin check result: {is_admin}")
            
            if not is_admin:
                await update.message.reply_text(f"❌ You are not admin. Your ID: {user_id}, Admin ID: {current_admin_id}")
                await update.message.reply_text("💡 To fix: Set ADMIN_ID in your .env file to your Telegram user ID")
        else:
            await update.message.reply_text("❌ Config not available")
            
        # Test database access
        db = context.bot_data.get('db')
        if db:
            await update.message.reply_text("✅ Database available")
        else:
            await update.message.reply_text("❌ Database not available")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error in test: {str(e)}")
        logger.error(f"Error in test_admin: {e}")

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new group to the managed groups list."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /add_group <group_id> <group_name> [category]\n"
            "Example: /add_group -1001234567890 'My Group' general"
        )
        return
    
    try:
        group_id = context.args[0]
        group_name = context.args[1]
        category = context.args[2] if len(context.args) > 2 else "general"
        
        db = context.bot_data['db']
        success = await db.add_managed_group(group_id, group_name, category)
        
        if success:
            await update.message.reply_text(f"✅ Group '{group_name}' added successfully!")
        else:
            await update.message.reply_text("❌ Failed to add group. Please try again.")
            
    except Exception as e:
        logger.error(f"Error adding group: {e}")
        await update.message.reply_text("❌ Error adding group. Please check the format.")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all managed groups."""
    if not await check_admin(update, context):
        # Handle both command and callback query calls
        if update.callback_query:
            await update.callback_query.answer("❌ Admin access required.")
        else:
            await update.message.reply_text("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
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
                await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(rows))
            return
        # Fallback to full list if no categories
        groups = await db.get_managed_groups()
        admin_all = await db.get_managed_groups("admin_all")
        
        if not groups:
            # Handle both command and callback query calls
            if update.callback_query:
                await update.callback_query.edit_message_text("📋 No managed groups found.")
            else:
                await update.message.reply_text("📋 No managed groups found.")
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
            await update.message.reply_text("\n".join(text_lines), reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        # Handle both command and callback query calls
        if update.callback_query:
            await update.callback_query.answer("❌ Error listing groups.")
        else:
            await update.message.reply_text("❌ Error listing groups.")

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
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if not context.args:
        await update.message.reply_text(
            "Usage: /remove_group <group_name>\n"
            "Example: /remove_group 'My Group'"
        )
        return
    
    try:
        group_name = " ".join(context.args)
        db = context.bot_data['db']
        success = await db.remove_managed_group(group_name)
        
        if success:
            await update.message.reply_text(f"✅ Group '{group_name}' removed successfully!")
        else:
            await update.message.reply_text("❌ Failed to remove group. Please check the name.")
            
    except Exception as e:
        logger.error(f"Error removing group: {e}")
        await update.message.reply_text("❌ Error removing group.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin statistics."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    try:
        # First, let's test if the command is working at all
        await update.message.reply_text("✅ Admin command received! Testing database connection...")
        
        db = context.bot_data['db']
        if not db:
            await update.message.reply_text("❌ Database not available in context.")
            return
            
        stats = await db.get_stats()
        
        text = "📊 **Admin Statistics:**\n\n"
        text += f"👥 **Users:** {stats['total_users']}\n"
        text += f"💎 **Active Subscriptions:** {stats['active_subscriptions']}\n"
        text += f"📨 **Messages Today:** {stats['messages_today']}\n"
        text += f"💰 **Revenue This Month:** ${stats['revenue_this_month']:.2f}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        await update.message.reply_text(f"❌ Error getting statistics: {str(e)}")

async def posting_service_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Concise, DB-sourced status to avoid duplicating other menus."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return

    try:
        db = context.bot_data.get('db')
        if not db:
            await update.message.reply_text("❌ Database not available.")
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
        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        logger.error(f"Error getting posting service status: {e}")
        await update.message.reply_text("❌ Error getting service status.")

async def failed_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show failed group joins."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get filter from command arguments
        filter_type = context.args[0] if context.args else None
        
        if filter_type and filter_type not in ['high', 'medium', 'low', 'privacy', 'invite', 'banned']:
            await update.message.reply_text(
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
            await update.message.reply_text("✅ No failed group joins found!")
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
        response_text += f"📊 **Total: {total_failed} failed groups**\n"
        response_text += "💡 Use /failed_groups [type] to filter by priority or reason"
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting failed groups: {e}")
        await update.message.reply_text("❌ Error getting failed groups.")

async def paused_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show paused ad slots for monitoring."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        paused_slots = await db.get_paused_slots()
        
        if not paused_slots:
            await update.message.reply_text("✅ No paused ad slots found.")
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
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting paused slots: {e}")
        await update.message.reply_text("❌ Error getting paused slots.")

async def retry_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually retry joining a specific group."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if not context.args:
        await update.message.reply_text(
            "Usage: /retry_group @username\n"
            "Example: /retry_group @crypto_trading"
        )
        return
        
    group_username = context.args[0]
    
    try:
        db = context.bot_data['db']
        
        # Remove from failed groups list
        success = await db.remove_failed_group_join(group_username)
        
        if success:
            await update.message.reply_text(
                f"✅ Removed {group_username} from failed groups list.\n"
                f"🔄 The system will try to join this group again during the next posting cycle."
            )
        else:
            await update.message.reply_text(
                f"❌ {group_username} not found in failed groups list."
            )
            
    except Exception as e:
        logger.error(f"Error retrying group {group_username}: {e}")
        await update.message.reply_text("❌ Error retrying group.")

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
                await query.answer("User deleted")
                await query.edit_message_text(f"✅ Successfully deleted user {user_id} and all associated data")
            else:
                await query.answer("Delete failed")
                await query.edit_message_text(f"❌ Failed to delete user {user_id}")
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
    except Exception as e:
        logger.error(f"Admin callback handling error: {e}")
        try:
            await query.answer("Error")
        except:
            pass

async def restart_posting_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the posting service."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
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
        await update.message.reply_text("❌ Admin access required.")
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
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if not context.args:
        await update.message.reply_text(
            "Usage: /verify_payment <payment_id>\n"
            "Example: /verify_payment TON_abc123def456"
        )
        return
    
    try:
        payment_id = context.args[0]
        payment_processor = context.bot_data.get('payment_processor')
        
        if not payment_processor:
            await update.message.reply_text("❌ Payment processor not available.")
            return
        
        # Verify the payment
        verification = await payment_processor.verify_payment(payment_id)
        
        if verification.get('payment_verified'):
            # Process the payment
            result = await payment_processor.process_successful_payment(payment_id)
            
            if result['success']:
                await update.message.reply_text(
                    f"✅ Payment verified and processed!\n"
                    f"User: {result['user_id']}\n"
                    f"Tier: {result['tier']}\n"
                    f"Slots: {result['slots']}"
                )
            else:
                await update.message.reply_text(f"❌ Payment verification failed: {result.get('error')}")
        else:
            await update.message.reply_text("❌ Payment not verified. Please check the payment ID.")
            
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        await update.message.reply_text("❌ Error verifying payment.")

async def revenue_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show revenue statistics."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
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
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting revenue stats: {e}")
        await update.message.reply_text("❌ Error getting revenue statistics.")

async def pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending payments."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        payment_processor = context.bot_data.get('payment_processor')
        
        if not payment_processor:
            await update.message.reply_text("❌ Payment processor not available.")
            return
        
        # Get pending payments
        pending_payments = await db.get_pending_payments(30)  # Last 30 minutes
        
        if not pending_payments:
            await update.message.reply_text("📋 No pending payments found.")
            return
        
        text = "⏳ **Pending Payments:**\n\n"
        for payment in pending_payments:
            text += f"**Payment ID:** `{payment['payment_id']}`\n"
            text += f"**User:** {payment['user_id']}\n"
            text += f"**Amount:** {payment['amount']} {payment['currency']}\n"
            text += f"**Created:** {payment['created_at']}\n"
            text += f"**Expires:** {payment['expires_at']}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting pending payments: {e}")
        await update.message.reply_text("❌ Error getting pending payments.")

async def worker_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show worker status and usage."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        db = context.bot_data['db']
        workers = await db.get_all_workers()
        if not workers:
            await update.message.reply_text("🤖 No workers found.")
            return
        lines = ["🤖 Worker Status:\n"]
        total_hourly_posts = 0
        total_daily_posts = 0
        total_safety_score = 0
        for worker in workers:
            usage = await db.get_worker_usage(worker['worker_id']) or {}
            hourly_posts = usage.get('hourly_posts', 0)
            daily_posts = usage.get('daily_posts', 0)
            safety_score = usage.get('safety_score', 100.0)
            total_hourly_posts += hourly_posts
            total_daily_posts += daily_posts
            total_safety_score += safety_score
            status = "Available" if usage.get('is_available', True) else "Unavailable"
            lines.append(
                f"Worker {worker['worker_id']} | Hourly {hourly_posts}/{usage.get('hourly_limit', 15)} ({usage.get('hourly_usage_percent', 0):.1f}%) | "
                f"Daily {daily_posts}/{usage.get('daily_limit', 150)} ({usage.get('daily_usage_percent', 0):.1f}%) | "
                f"Safety {safety_score:.1f} | {status}"
            )
        if workers:
            avg_safety = total_safety_score / len(workers)
            lines.append("")
            lines.append(f"Totals: Hourly={total_hourly_posts}, Daily={total_daily_posts}, AvgSafety={avg_safety:.1f}")
            
            # Add workload information
            due_slots = await db.get_active_ads_to_send()
            user_slots = [slot for slot in due_slots if slot.get('slot_type') == 'user']
            admin_slots = [slot for slot in due_slots if slot.get('slot_type') == 'admin']
            
            lines.append("")
            lines.append(f"**Current Workload:**")
            lines.append(f"  • User ads pending: {len(user_slots)}")
            lines.append(f"  • Admin ads pending: {len(admin_slots)}")
            lines.append(f"  • Total workload: {len(due_slots)}")
            
        await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting worker status: {e}")
        await update.message.reply_text("❌ Error getting worker status.")

async def admin_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active admin warnings."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        db = context.bot_data['db']
        warnings = await db.get_unresolved_warnings()
        if not warnings:
            await update.message.reply_text("✅ No active warnings.")
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
        await update.message.reply_text("\n".join(lines))
        
    except Exception as e:
        logger.error(f"Error getting admin warnings: {e}")
        await update.message.reply_text("❌ Error getting admin warnings.")

async def increase_worker_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Increase worker limits for all workers."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        db = context.bot_data['db']
        workers = await db.get_all_workers()
        
        if not workers:
            await update.message.reply_text("🤖 No workers found.")
            return
        
        updated_count = 0
        for worker in workers:
            success = await db.increase_worker_limits(worker['worker_id'])
            if success:
                updated_count += 1
        
        await update.message.reply_text(f"✅ Increased limits for {updated_count}/{len(workers)} workers.")
        
    except Exception as e:
        logger.error(f"Error increasing worker limits: {e}")
        await update.message.reply_text("❌ Error increasing worker limits.")

async def worker_capacity_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check worker capacity and load."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        db = context.bot_data['db']
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
        
        await update.message.reply_text(text)
        
    except Exception as e:
        logger.error(f"Error checking worker capacity: {e}")
        await update.message.reply_text("❌ Error checking worker capacity.")

async def activate_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate a subscription for a user manually."""
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /activate_subscription <user_id> <tier> <days>\n"
            "Example: /activate_subscription 123456789 enterprise 30\n"
            "Tiers: basic, pro, enterprise"
        )
        return
    
    try:
        user_id = int(context.args[0])
        tier = context.args[1].lower()
        days = int(context.args[2])
        
        await update.message.reply_text(f"🔧 Processing activation for user {user_id}, tier {tier}, {days} days...")
        
        # Validate tier
        valid_tiers = ['basic', 'pro', 'enterprise']
        if tier not in valid_tiers:
            await update.message.reply_text(f"❌ Invalid tier. Valid tiers: {', '.join(valid_tiers)}")
            return
        
        # Validate days
        if days <= 0 or days > 365:
            await update.message.reply_text("❌ Invalid days. Must be between 1 and 365.")
            return
        
        db = context.bot_data['db']
        if not db:
            await update.message.reply_text("❌ Database not available.")
            return
        
        await update.message.reply_text("✅ Database connection verified.")
        
        # Check if user exists
        try:
            user = await asyncio.wait_for(db.get_user(user_id), timeout=10)
        except Exception as e:
            await update.message.reply_text(f"❌ Database busy/error on get_user: {e}")
            return
        if not user:
            await update.message.reply_text(f"❌ User {user_id} not found in database.")
            await update.message.reply_text("💡 Creating user first...")
            
            # Create user if doesn't exist
            try:
                success = await asyncio.wait_for(db.create_or_update_user(
                user_id=user_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name
            ), timeout=10)
            except Exception as e:
                await update.message.reply_text(f"❌ Database error creating user: {e}")
                return
            if not success:
                await update.message.reply_text("❌ Failed to create user.")
                return
            await update.message.reply_text("✅ User created successfully.")
        
        # Activate subscription
        await update.message.reply_text("🔄 Activating subscription...")
        try:
            success = await asyncio.wait_for(db.activate_subscription(user_id, tier, days), timeout=15)
        except Exception as e:
            await update.message.reply_text(f"❌ Database busy/error on activation: {e}")
            return
        
        if success:
            await update.message.reply_text(
                f"✅ Subscription activated successfully!\n"
                f"**User:** {user_id}\n"
                f"**Tier:** {tier.capitalize()}\n"
                f"**Duration:** {days} days"
            )
        else:
            await update.message.reply_text("❌ Failed to activate subscription.")
            
    except ValueError as e:
        await update.message.reply_text(f"❌ Invalid user_id or days. Must be numbers. Error: {e}")
    except Exception as e:
        logger.error(f"Error activating subscription: {e}")
        await update.message.reply_text(f"❌ Error activating subscription: {str(e)}")