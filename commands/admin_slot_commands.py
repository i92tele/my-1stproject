#!/usr/bin/env python3
"""
Admin Ad Slot Commands
Handles admin-specific ad slots for promotional content
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import json

logger = logging.getLogger(__name__)

def get_display_category(category: str) -> str:
    """Convert database category to display category with emoji."""
    category_mapping = {
        'exchange services': "💱 Exchange Services",
        'telegram': "📱 Telegram",
        'discord': "🎮 Discord",
        'instagram': "📸 Instagram",
        'x/twitter': "𝕏 Twitter/X",
        'tiktok': "🎵 TikTok",
        'facebook': "📘 Facebook",
        'youtube': "▶️ YouTube",
        'steam': "🎮 Steam",
        'twitch': "🟣 Twitch",
        'telegram gifts': "🎁 Telegram Gifts",
        'other social media': "🌐 Other Social Media",
        'gaming accounts': "🕹️ Gaming Accounts",
        'gaming services': "🛠️ Gaming Services",
        'other services': "🧩 Other Services",
        'other accounts': "👥 Other Accounts",
        'meme coins': "🪙 Meme Coins",
        'usernames': "🔤 Usernames",
        'gaming currencies': "💰 Gaming Currencies",
        'bots and tools': "🤖 Bots & Tools",
        'account upgrade': "⬆️ Account Upgrade"
    }
    return category_mapping.get(category, f"📋 {category.title()}")

def get_database_category(display_category: str) -> str:
    """Convert display category back to database category."""
    reverse_mapping = {
        "💱 Exchange Services": "exchange services",
        "📱 Telegram": "telegram",
        "🎮 Discord": "discord",
        "📸 Instagram": "instagram",
        "𝕏 Twitter/X": "x/twitter",
        "🎵 TikTok": "tiktok",
        "📘 Facebook": "facebook",
        "▶️ YouTube": "youtube",
        "🎮 Steam": "steam",
        "🟣 Twitch": "twitch",
        "🎁 Telegram Gifts": "telegram gifts",
        "🌐 Other Social Media": "other social media",
        "🕹️ Gaming Accounts": "gaming accounts",
        "🛠️ Gaming Services": "gaming services",
        "🧩 Other Services": "other services",
        "👥 Other Accounts": "other accounts",
        "🪙 Meme Coins": "meme coins",
        "🔤 Usernames": "usernames",
        "💰 Gaming Currencies": "gaming currencies",
        "🤖 Bots & Tools": "bots and tools",
        "⬆️ Account Upgrade": "account upgrade"
    }
    return reverse_mapping.get(display_category, display_category.replace("📋 ", "").lower())

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

async def admin_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage admin ad slots."""
    if not await check_admin(update, context):
        # Handle both command and callback query calls
        if update.callback_query:
            await update.callback_query.answer("❌ Admin access required.")
        else:
            await update.message.reply_text("❌ Admin access required.")
        return
    
    # Clear any conversation state when navigating to slots overview
    context.user_data.clear()
        
    try:
        db = context.bot_data['db']
        
        # Get admin slots
        admin_slots = await db.get_admin_ad_slots()
        
        if not admin_slots:
            # Create initial admin slots if none exist
            await db.create_admin_ad_slots()
            admin_slots = await db.get_admin_ad_slots()
        
        message_text = "🎯 **Admin Ad Slots**\n\n"
        message_text += f"**Total Slots:** {len(admin_slots)} (Unlimited)\n"
        message_text += "**Purpose:** Promotional content and announcements\n\n"
        message_text += "Select a slot to manage:"
        
        keyboard = []
        
        # Create slot buttons (5 per row)
        for i in range(0, len(admin_slots), 5):
            row = []
            for j in range(5):
                if i + j < len(admin_slots):
                    slot = admin_slots[i + j]
                    slot_number = slot['slot_number']
                    status = "✅" if slot['is_active'] else "⏸️"
                    row.append(InlineKeyboardButton(
                        f"{status} {slot_number}", 
                        callback_data=f"admin_slot:{slot_number}"
                    ))
            keyboard.append(row)
        
        # Add management buttons
        keyboard.append([
            InlineKeyboardButton("📝 Quick Post", callback_data="admin_quick_post"),
            InlineKeyboardButton("📊 Slot Stats", callback_data="admin_slot_stats")
        ])
        keyboard.append([
            InlineKeyboardButton("🧹 Clear All Content", callback_data="admin_clear_all_content"),
            InlineKeyboardButton("🗑️ Clear All Destinations", callback_data="admin_clear_all_destinations")
        ])
        keyboard.append([
            InlineKeyboardButton("💥 Purge All Slots", callback_data="admin_purge_all_slots"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_slots_refresh")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="cmd:admin_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Handle both command and callback query calls
        if update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_slots: {e}")
        # Handle both command and callback query calls
        if update.callback_query:
            await update.callback_query.answer("❌ Error loading admin slots. Please try again.")
        else:
            await update.message.reply_text("❌ Error loading admin slots. Please try again.")

async def admin_slot_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int):
    """Show detailed information about a specific admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
    
    # Clear any conversation state when navigating back
    context.user_data.clear()
        
    try:
        db = context.bot_data['db']
        
        # Get slot details
        slot = await db.get_admin_ad_slot(slot_number)
        if not slot:
            await update.callback_query.answer("❌ Slot not found")
            return
        
        # Get destinations
        destinations = await db.get_admin_slot_destinations(slot['id'])
        
        # Safely format content to avoid Markdown parsing issues
        content = slot.get('content', '')
        if content:
            # Escape special characters and limit length
            safe_content = content.replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('`', '\\`').replace('~', '\\~')
            if len(safe_content) > 100:
                safe_content = safe_content[:97] + '...'
            content_status = f"✅ Set: {safe_content}"
        else:
            content_status = "❌ Not Set"
        
        message_text = f"🎯 **Admin Slot {slot_number}**\n\n"
        message_text += f"**Status:** {'✅ Active' if slot['is_active'] else '⏸️ Paused'}\n"
        message_text += f"**Content:** {content_status}\n"
        message_text += f"**Destinations:** {len(destinations)} groups\n"
        message_text += f"**Created:** {slot['created_at']}\n"
        message_text += f"**Updated:** {slot['updated_at']}\n\n"
        
        if destinations:
            message_text += "**Current Destinations:**\n"
            for i, dest in enumerate(destinations[:5], 1):
                # Safely escape destination names
                safe_name = dest['destination_name'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('`', '\\`').replace('~', '\\~')
                message_text += f"{i}. {safe_name}\n"
            if len(destinations) > 5:
                message_text += f"... and {len(destinations) - 5} more\n"
        
        keyboard = [
            [
                InlineKeyboardButton("📝 Set Content", callback_data=f"admin_set_content:{slot_number}"),
                InlineKeyboardButton("🎯 Set Destinations", callback_data=f"admin_set_destinations:{slot_number}")
            ],
            [
                InlineKeyboardButton("⚡ Toggle Active", callback_data=f"admin_toggle_slot:{slot_number}"),
                InlineKeyboardButton("📤 Post Now", callback_data=f"admin_post_slot:{slot_number}")
            ],
            [
                InlineKeyboardButton("🗑️ Delete Slot", callback_data=f"admin_delete_slot:{slot_number}"),
                InlineKeyboardButton("📊 Slot Analytics", callback_data=f"admin_slot_analytics:{slot_number}")
            ],
            [
                InlineKeyboardButton("🔙 Back to Slots", callback_data="admin_slots")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_slot_detail: {e}")
        await update.callback_query.answer("❌ Error loading slot details")

async def admin_quick_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick posting interface for admin."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        message_text = (
            "📤 **Quick Admin Post**\n\n"
            "This will post your message to all managed groups.\n\n"
            "**Features:**\n"
            "• Instant posting to all groups\n"
            "• No scheduling required\n"
            "• Perfect for announcements\n\n"
            "Send your message now to post it immediately!"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📝 Send Message", callback_data="admin_quick_post_send"),
                InlineKeyboardButton("📋 Use Template", callback_data="admin_quick_post_template")
            ],
            [
                InlineKeyboardButton("🔙 Back to Slots", callback_data="admin_slots")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_quick_post: {e}")
        await update.callback_query.answer("❌ Error loading quick post interface")

async def admin_post_slot(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int):
    """Post content from a specific admin slot immediately."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get slot details
        slot = await db.get_admin_ad_slot(slot_number)
        if not slot:
            await update.callback_query.answer("❌ Slot not found")
            return
        
        if not slot['content']:
            await update.callback_query.answer("❌ No content set for this slot")
            return
        
        if not slot['is_active']:
            await update.callback_query.answer("❌ Slot is not active")
            return
        
        # Get destinations
        destinations = await db.get_admin_slot_destinations(slot['id'])
        if not destinations:
            await update.callback_query.answer("❌ No destinations set for this slot")
            return
        
        # Trigger immediate posting
        posting_service = context.bot_data.get('posting_service')
        if posting_service:
            # Create a mock ad slot for posting
            mock_ad_slot = {
                'id': f"admin_{slot['id']}",
                'content': slot['content'],
                'user_id': 0,  # Admin user ID
                'slot_number': slot_number
            }
            
            # Post to all destinations
            success_count = 0
            total_count = len(destinations)
            
            for dest in destinations:
                try:
                    # Use the posting service to post
                    success = await posting_service._post_single_ad(
                        mock_ad_slot, 
                        dest, 
                        context.bot_data.get('workers', [None])[0] if context.bot_data.get('workers') else None
                    )
                    if success:
                        success_count += 1
                except Exception as e:
                    logger.error(f"Error posting admin slot {slot_number} to {dest['destination_name']}: {e}")
            
            await update.callback_query.answer(
                f"✅ Posted to {success_count}/{total_count} groups"
            )
        else:
            await update.callback_query.answer("❌ Posting service not available")
        
    except Exception as e:
        logger.error(f"Error in admin_post_slot: {e}")
        await update.callback_query.answer("❌ Error posting slot")

async def handle_admin_content_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle content messages for admin slots."""
    try:
        # Check if we're waiting for admin content
        if not context.user_data.get('awaiting_admin_content'):
            return False  # Not handling this message, let other handlers process it
            
        # Check admin status
        config = context.bot_data.get('config')
        if not config or not config.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Admin access required.")
            return True
            
        slot_number = context.user_data.get('admin_slot_number')
        if not slot_number:
            await update.message.reply_text("❌ Error: No slot number found. Please try again.")
            context.user_data.clear()
            return True
            
        db = context.bot_data['db']
        
        # Get the slot
        slot = await db.get_admin_ad_slot(slot_number)
        if not slot:
            await update.message.reply_text("❌ Slot not found. Please try again.")
            context.user_data.clear()
            return True
            
        # Extract content from message
        content = ""
        if update.message.text:
            content = update.message.text
        elif update.message.caption:
            content = update.message.caption
        
        # Update slot content
        success = await db.update_admin_slot_content(slot_number, content)
        
        if success:
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Slot", callback_data=f"admin_slot:{slot_number}")],
                [InlineKeyboardButton("🎯 Admin Slots", callback_data="admin_slots")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **Content saved for Admin Slot {slot_number}!**\n\n"
                f"**Content Preview:**\n{content[:200]}{'...' if len(content) > 200 else ''}\n\n"
                f"Your content has been successfully saved and is ready for posting.\n"
                f"📊 **Next Steps:**\n"
                f"• Set destinations for this slot\n"
                f"• Toggle slot to Active\n"
                f"• Use 'Post Now' to test immediately",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ **Failed to save content for Admin Slot {slot_number}**\n\n"
                f"Please try again or contact support."
            )
        
        # Clear conversation state
        context.user_data.clear()
        return True
        
    except Exception as e:
        logger.error(f"Error in handle_admin_content_message: {e}")
        await update.message.reply_text("❌ Error saving content. Please try again.")
        context.user_data.clear()
        return True

async def admin_set_slot_content(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int):
    """Set content for an admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        # Store the slot number in context for the conversation
        context.user_data['admin_slot_number'] = slot_number
        
        message_text = (
            f"📝 **Set Content for Admin Slot {slot_number}**\n\n"
            "Send the message content you want to post from this slot.\n\n"
            "**Supported formats:**\n"
            "• Text messages\n"
            "• Text with formatting (Markdown)\n"
            "• Media messages (photos, videos, documents)\n\n"
            "Send your content now, or /cancel to abort."
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📋 Use Template", callback_data=f"admin_content_template:{slot_number}"),
                InlineKeyboardButton("🗑️ Clear Content", callback_data=f"admin_clear_content:{slot_number}")
            ],
            [
                InlineKeyboardButton("🔙 Back to Slot", callback_data=f"admin_slot:{slot_number}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Set conversation state
        context.user_data['awaiting_admin_content'] = True
        
    except Exception as e:
        logger.error(f"Error in admin_set_slot_content: {e}")
        await update.callback_query.answer("❌ Error setting up content input")

async def admin_set_slot_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int):
    """Set destinations for an admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all managed groups
        all_groups = await db.get_managed_groups()
        
        if not all_groups:
            await update.callback_query.answer("❌ No managed groups available")
            return
        
        # Get current destinations for this slot
        slot = await db.get_admin_ad_slot(slot_number)
        current_destinations = await db.get_admin_slot_destinations(slot['id']) if slot else []
        current_dest_ids = {dest['destination_id'] for dest in current_destinations}
        
        # Organize groups by their actual database categories
        categories = {}
        for group in all_groups:
            category = group.get('category', 'other')
            display_category = get_display_category(category)
            
            if display_category not in categories:
                categories[display_category] = []
            categories[display_category].append(group)
        
        # Add timestamp to avoid "message not modified" errors
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M:%S")
        
        message_text = f"🎯 **Choose Posting Destinations for Admin Slot {slot_number}**\n\n"
        message_text += f"📢 **What this does:** Select which groups this admin slot will post to when activated.\n\n"
        message_text += f"**Currently Selected:** {len(current_destinations)} groups\n"
        message_text += f"**Available Groups:** {len(all_groups)} total groups in your database\n\n"
        message_text += "**📁 Groups by Category:**\n"
        
        for category, groups in categories.items():
            selected_count = sum(1 for group in groups if (group['group_id'] or group['group_name']) in current_dest_ids)
            message_text += f"• {category}: {selected_count}/{len(groups)} selected\n"
        
        message_text += f"\n**👆 Tap a category below to select/deselect groups for posting:**\n"
        message_text += f"⏰ *Updated: {current_time}*"
        
        keyboard = []
        
        # Create category selection buttons (2 per row)
        for i, (category, groups) in enumerate(categories.items()):
            if i % 2 == 0:
                row = []
            
            selected_count = sum(1 for group in groups if (group['group_id'] or group['group_name']) in current_dest_ids)
            row.append(InlineKeyboardButton(
                f"📁 {category} ({selected_count}/{len(groups)})", 
                callback_data=f"admin_category:{slot_number}:{category}"
            ))
            
            if i % 2 == 1 or i == len(categories) - 1:
                keyboard.append(row)
        
        # Add management buttons
        keyboard.append([
            InlineKeyboardButton("✅ Select All", callback_data=f"admin_select_all:{slot_number}"),
            InlineKeyboardButton("❌ Clear All", callback_data=f"admin_clear_all:{slot_number}")
        ])
        keyboard.append([
            InlineKeyboardButton("💾 Save Changes", callback_data=f"admin_save_destinations:{slot_number}"),
            InlineKeyboardButton("🔙 Back to Slot", callback_data=f"admin_slot:{slot_number}")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_set_slot_destinations: {e}")
        await update.callback_query.answer("❌ Error loading destinations")

async def admin_category_view(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int, category: str):
    """Show groups within a specific category for admin slot destination selection."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all managed groups
        all_groups = await db.get_managed_groups()
        
        # Get current destinations for this slot
        slot = await db.get_admin_ad_slot(slot_number)
        current_destinations = await db.get_admin_slot_destinations(slot['id']) if slot else []
        current_dest_ids = {dest['destination_id'] for dest in current_destinations}
        
        # Filter groups by category
        category_groups = []
        for group in all_groups:
            group_category = group.get('category', 'other')
            target_category = get_database_category(category)
            
            if group_category == target_category:
                category_groups.append(group)
        
        selected_count = sum(1 for group in category_groups if (group['group_id'] or group['group_name']) in current_dest_ids)
        
        # Add timestamp to avoid "message not modified" errors
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M:%S")
        
        message_text = f"📁 **{category}** - Admin Slot {slot_number}\n\n"
        message_text += f"📢 **Posting Destinations:** Choose which groups in this category will receive your admin slot content.\n\n"
        message_text += f"**Selected:** {selected_count}/{len(category_groups)} groups\n\n"
        message_text += "**👆 Tap groups below to add/remove them as posting destinations:**\n"
        message_text += f"⏰ *Updated: {current_time}*"
        
        keyboard = []
        
        # Create group selection buttons (2 per row)
        for i in range(0, len(category_groups), 2):
            row = []
            for j in range(2):
                if i + j < len(category_groups):
                    group = category_groups[i + j]
                    group_id = group['group_id'] or group['group_name']
                    is_selected = group_id in current_dest_ids
                    status = "✅" if is_selected else "⬜"
                    display_name = group['group_name'][:20] + "..." if len(group['group_name']) > 20 else group['group_name']
                    row.append(InlineKeyboardButton(
                        f"{status} {display_name}", 
                        callback_data=f"admin_toggle_dest:{slot_number}:{group_id}"
                    ))
            keyboard.append(row)
        
        # Add category management buttons
        keyboard.append([
            InlineKeyboardButton("✅ Select All in Category", callback_data=f"admin_select_category:{slot_number}:{category}"),
            InlineKeyboardButton("❌ Clear Category", callback_data=f"admin_clear_category:{slot_number}:{category}")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Categories", callback_data=f"admin_set_destinations:{slot_number}"),
            InlineKeyboardButton("🔙 Back to Slot", callback_data=f"admin_slot:{slot_number}")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_category_view: {e}")
        await update.callback_query.answer("❌ Error loading category view")

async def admin_toggle_destination(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int, group_id: str):
    """Toggle a destination for an admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get current destinations for this slot
        slot = await db.get_admin_ad_slot(slot_number)
        if not slot:
            await update.callback_query.answer("❌ Slot not found")
            return
        
        current_destinations = await db.get_admin_slot_destinations(slot['id'])
        current_dest_ids = {dest['destination_id'] for dest in current_destinations}
        
        # Toggle the destination
        if group_id in current_dest_ids:
            # Remove destination
            success = await db.remove_admin_slot_destination(slot['id'], group_id)
            if success:
                await update.callback_query.answer("❌ Destination removed")
            else:
                await update.callback_query.answer("❌ Failed to remove destination")
        else:
            # Add destination
            # Get group info
            all_groups = await db.get_managed_groups()
            group_info = next((g for g in all_groups if (g['group_id'] or g['group_name']) == group_id), None)
            
            if group_info:
                destination_data = {
                    'destination_id': group_id,
                    'destination_name': group_info['group_name'],
                    'destination_type': 'group'
                }
                success = await db.add_admin_slot_destination(slot['id'], destination_data)
                if success:
                    await update.callback_query.answer("✅ Destination added")
                else:
                    await update.callback_query.answer("❌ Failed to add destination")
            else:
                await update.callback_query.answer("❌ Group not found")
        
        # Refresh the current view
        # Determine if we're in category view or main destinations view
        message_text = update.callback_query.message.text
        if "📁" in message_text and "Admin Slot" in message_text:
            # We're in category view, extract category
            lines = message_text.split('\n')
            for line in lines:
                if line.startswith("📁 **") and "** - Admin Slot" in line:
                    category = line.split("📁 **")[1].split("** - Admin Slot")[0]
                    await admin_category_view(update, context, slot_number, category)
                    break
        else:
            # We're in main destinations view
            await admin_set_slot_destinations(update, context, slot_number)
        
    except Exception as e:
        logger.error(f"Error in admin_toggle_destination: {e}")
        await update.callback_query.answer("❌ Error toggling destination")

async def admin_select_category(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int, category: str):
    """Select all groups in a category for an admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all managed groups
        all_groups = await db.get_managed_groups()
        
        # Get current destinations for this slot
        slot = await db.get_admin_ad_slot(slot_number)
        if not slot:
            await update.callback_query.answer("❌ Slot not found")
            return
        
        # Filter groups by category
        category_groups = []
        for group in all_groups:
            group_category = group.get('category', 'other')
            target_category = get_database_category(category)
            
            if group_category == target_category:
                category_groups.append(group)
        
        # Add all groups in category
        added_count = 0
        for group in category_groups:
            group_id = group['group_id'] or group['group_name']
            destination_data = {
                'destination_id': group_id,
                'destination_name': group['group_name'],
                'destination_type': 'group'
            }
            success = await db.add_admin_slot_destination(slot['id'], destination_data)
            if success:
                added_count += 1
        
        await update.callback_query.answer(f"✅ Added {added_count} groups from {category}")
        
        # Refresh the category view
        await admin_category_view(update, context, slot_number, category)
        
    except Exception as e:
        logger.error(f"Error in admin_select_category: {e}")
        await update.callback_query.answer("❌ Error selecting category")

async def admin_clear_category(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int, category: str):
    """Clear all groups in a category for an admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all managed groups
        all_groups = await db.get_managed_groups()
        
        # Get current destinations for this slot
        slot = await db.get_admin_ad_slot(slot_number)
        if not slot:
            await update.callback_query.answer("❌ Slot not found")
            return
        
        # Filter groups by category
        category_groups = []
        for group in all_groups:
            group_category = group.get('category', 'other')
            target_category = get_database_category(category)
            
            if group_category == target_category:
                category_groups.append(group)
        
        # Remove all groups in category
        removed_count = 0
        for group in category_groups:
            group_id = group['group_id'] or group['group_name']
            success = await db.remove_admin_slot_destination(slot['id'], group_id)
            if success:
                removed_count += 1
        
        await update.callback_query.answer(f"❌ Removed {removed_count} groups from {category}")
        
        # Refresh the category view
        await admin_category_view(update, context, slot_number, category)
        
    except Exception as e:
        logger.error(f"Error in admin_clear_category: {e}")
        await update.callback_query.answer("❌ Error clearing category")

async def admin_select_all_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int):
    """Select all destinations for an admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all managed groups
        all_groups = await db.get_managed_groups()
        
        # Get current destinations for this slot
        slot = await db.get_admin_ad_slot(slot_number)
        if not slot:
            await update.callback_query.answer("❌ Slot not found")
            return
        
        # Add all groups
        added_count = 0
        for group in all_groups:
            group_id = group['group_id'] or group['group_name']
            destination_data = {
                'destination_id': group_id,
                'destination_name': group['group_name'],
                'destination_type': 'group'
            }
            success = await db.add_admin_slot_destination(slot['id'], destination_data)
            if success:
                added_count += 1
        
        await update.callback_query.answer(f"✅ Added {added_count} groups")
        
        # Refresh the destinations view
        await admin_set_slot_destinations(update, context, slot_number)
        
    except Exception as e:
        logger.error(f"Error in admin_select_all_destinations: {e}")
        await update.callback_query.answer("❌ Error selecting all destinations")

async def admin_clear_all_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int):
    """Clear all destinations for an admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get current destinations for this slot
        slot = await db.get_admin_ad_slot(slot_number)
        if not slot:
            await update.callback_query.answer("❌ Slot not found")
            return
        
        # Clear all destinations
        success = await db.clear_admin_slot_destinations(slot['id'])
        
        if success:
            await update.callback_query.answer("❌ All destinations cleared")
        else:
            await update.callback_query.answer("❌ Failed to clear destinations")
        
        # Refresh the destinations view
        await admin_set_slot_destinations(update, context, slot_number)
        
    except Exception as e:
        logger.error(f"Error in admin_clear_all_destinations: {e}")
        await update.callback_query.answer("❌ Error clearing all destinations")

async def admin_save_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int):
    """Save destination changes for an admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        await update.callback_query.answer("✅ Destinations saved successfully!")
        
        # Go back to slot detail view
        await admin_slot_detail(update, context, slot_number)
        
    except Exception as e:
        logger.error(f"Error in admin_save_destinations: {e}")
        await update.callback_query.answer("❌ Error saving destinations")

async def admin_toggle_slot(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int):
    """Toggle admin slot active status."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get current slot status
        slot = await db.get_admin_ad_slot(slot_number)
        if not slot:
            await update.callback_query.answer("❌ Slot not found")
            return
        
        # Toggle status
        new_status = not slot['is_active']
        success = await db.update_admin_slot_status(slot_number, new_status)
        
        if success:
            status_text = "activated ✅" if new_status else "deactivated ⏸️"
            await update.callback_query.answer(f"Slot {status_text}")
            
            # Refresh the slot detail view
            await admin_slot_detail(update, context, slot_number)
        else:
            await update.callback_query.answer("❌ Failed to update slot status")
        
    except Exception as e:
        logger.error(f"Error in admin_toggle_slot: {e}")
        await update.callback_query.answer("❌ Error toggling slot status")

async def admin_slot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics for admin slots."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get admin slots statistics
        stats = await db.get_admin_slots_stats()
        
        message_text = "📊 **Admin Slots Statistics**\n\n"
        message_text += f"**Total Slots:** {stats.get('total_slots', 0)}\n"
        message_text += f"**Active Slots:** {stats.get('active_slots', 0)}\n"
        message_text += f"**Slots with Content:** {stats.get('slots_with_content', 0)}\n"
        message_text += f"**Slots with Destinations:** {stats.get('slots_with_destinations', 0)}\n"
        message_text += f"**Total Posts Today:** {stats.get('posts_today', 0)}\n"
        message_text += f"**Total Posts This Week:** {stats.get('posts_week', 0)}\n"
        message_text += f"**Total Posts This Month:** {stats.get('posts_month', 0)}\n\n"
        
        # Show top performing slots
        top_slots = stats.get('top_slots', [])
        if top_slots:
            message_text += "**Top Performing Slots:**\n"
            for i, slot in enumerate(top_slots[:5], 1):
                message_text += f"{i}. Slot {slot['slot_number']}: {slot['post_count']} posts\n"
        
        keyboard = [
            [
                InlineKeyboardButton("📈 Detailed Analytics", callback_data="admin_detailed_analytics"),
                InlineKeyboardButton("📊 Export Data", callback_data="admin_export_stats")
            ],
            [
                InlineKeyboardButton("🔙 Back to Slots", callback_data="admin_slots")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_slot_stats: {e}")
        await update.callback_query.answer("❌ Error loading statistics")

async def handle_admin_slot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin slot related callbacks."""
    query = update.callback_query
    await query.answer()
    
    try:
        data = query.data
        
        if data.startswith("admin_slot:"):
            slot_number = int(data.split(":")[1])
            await admin_slot_detail(update, context, slot_number)
            
        elif data.startswith("admin_quick_post"):
            await admin_quick_post(update, context)
            
        elif data.startswith("admin_post_slot:"):
            slot_number = int(data.split(":")[1])
            await admin_post_slot(update, context, slot_number)
            
        elif data.startswith("admin_set_content:"):
            slot_number = int(data.split(":")[1])
            await admin_set_slot_content(update, context, slot_number)
            
        elif data.startswith("admin_set_destinations:"):
            slot_number = int(data.split(":")[1])
            await admin_set_slot_destinations(update, context, slot_number)
            
        elif data.startswith("admin_category:"):
            parts = data.split(":")
            slot_number = int(parts[1])
            category = parts[2]
            await admin_category_view(update, context, slot_number, category)
            
        elif data.startswith("admin_toggle_dest:"):
            parts = data.split(":")
            slot_number = int(parts[1])
            group_id = parts[2]
            await admin_toggle_destination(update, context, slot_number, group_id)
            
        elif data.startswith("admin_select_category:"):
            parts = data.split(":")
            slot_number = int(parts[1])
            category = parts[2]
            await admin_select_category(update, context, slot_number, category)
            
        elif data.startswith("admin_clear_category:"):
            parts = data.split(":")
            slot_number = int(parts[1])
            category = parts[2]
            await admin_clear_category(update, context, slot_number, category)
            
        elif data.startswith("admin_select_all:"):
            slot_number = int(data.split(":")[1])
            await admin_select_all_destinations(update, context, slot_number)
            
        elif data.startswith("admin_clear_all:"):
            slot_number = int(data.split(":")[1])
            await admin_clear_all_destinations(update, context, slot_number)
            
        elif data.startswith("admin_save_destinations:"):
            slot_number = int(data.split(":")[1])
            await admin_save_destinations(update, context, slot_number)
            
        elif data.startswith("admin_toggle_slot:"):
            slot_number = int(data.split(":")[1])
            await admin_toggle_slot(update, context, slot_number)
            
        elif data.startswith("admin_slot_stats"):
            await admin_slot_stats(update, context)
            
        elif data == "admin_slots_refresh":
            await admin_slots(update, context)
            
        elif data == "admin_slots" or data == "cmd:admin_slots":
            await admin_slots(update, context)
            
        elif data == "admin_clear_all_content":
            await admin_clear_all_content(update, context)
            
        elif data == "admin_clear_all_destinations":
            await admin_clear_all_destinations_bulk(update, context)
            
        elif data == "admin_purge_all_slots":
            await admin_purge_all_slots(update, context)
            
        elif data == "admin_confirm_purge_all_slots":
            await admin_confirm_purge_all_slots(update, context)
            
        else:
            await query.answer("Unknown admin slot action")
            
    except Exception as e:
        logger.error(f"Error in handle_admin_slot_callback: {e}")
        await query.answer("❌ Error processing admin slot action")

async def admin_clear_all_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear content from all admin slots."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all admin slots
        admin_slots = await db.get_admin_ad_slots()
        if not admin_slots:
            await update.callback_query.answer("❌ No admin slots found")
            return
        
        # Clear content from all slots
        cleared_count = 0
        for slot in admin_slots:
            success = await db.update_admin_slot_content(slot['id'], "")
            if success:
                cleared_count += 1
        
        message_text = f"🧹 **Content Cleared**\n\n"
        message_text += f"✅ Cleared content from {cleared_count}/{len(admin_slots)} admin slots"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Admin Slots", callback_data="admin_slots")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer(f"✅ Cleared {cleared_count} slots")
        
    except Exception as e:
        logger.error(f"Error in admin_clear_all_content: {e}")
        await update.callback_query.answer("❌ Error clearing content")

async def admin_clear_all_destinations_bulk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear destinations from all admin slots."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all admin slots
        admin_slots = await db.get_admin_ad_slots()
        if not admin_slots:
            await update.callback_query.answer("❌ No admin slots found")
            return
        
        # Clear destinations from all slots
        cleared_count = 0
        for slot in admin_slots:
            success = await db.clear_admin_slot_destinations(slot['id'])
            if success:
                cleared_count += 1
        
        message_text = f"🗑️ **Destinations Cleared**\n\n"
        message_text += f"✅ Cleared destinations from {cleared_count}/{len(admin_slots)} admin slots"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Admin Slots", callback_data="admin_slots")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer(f"✅ Cleared {cleared_count} slots")
        
    except Exception as e:
        logger.error(f"Error in admin_clear_all_destinations_bulk: {e}")
        await update.callback_query.answer("❌ Error clearing destinations")

async def admin_purge_all_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Purge (delete) all admin slots - with confirmation."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all admin slots
        admin_slots = await db.get_admin_ad_slots()
        if not admin_slots:
            await update.callback_query.answer("❌ No admin slots found")
            return
        
        message_text = f"💥 **DANGER: Purge All Admin Slots**\n\n"
        message_text += f"⚠️ This will **permanently delete** all {len(admin_slots)} admin slots and their:\n"
        message_text += f"• Content\n"
        message_text += f"• Destinations\n"
        message_text += f"• Configuration\n"
        message_text += f"• Post history\n\n"
        message_text += f"**This action CANNOT be undone!**\n\n"
        message_text += f"Are you absolutely sure?"
        
        keyboard = [
            [
                InlineKeyboardButton("❌ Cancel", callback_data="admin_slots"),
                InlineKeyboardButton("💥 YES, DELETE ALL", callback_data="admin_confirm_purge_all_slots")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_purge_all_slots: {e}")
        await update.callback_query.answer("❌ Error preparing purge")

async def admin_confirm_purge_all_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute purge of all admin slots."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all admin slots before deletion
        admin_slots = await db.get_admin_ad_slots()
        if not admin_slots:
            await update.callback_query.answer("❌ No admin slots found")
            return
        
        # Delete all admin slots and their data
        deleted_count = 0
        for slot in admin_slots:
            try:
                # Clear destinations first
                await db.clear_admin_slot_destinations(slot['id'])
                # Delete the slot itself
                success = await db.delete_admin_slot(slot['id'])
                if success:
                    deleted_count += 1
            except Exception as slot_error:
                logger.warning(f"Failed to delete slot {slot['slot_number']}: {slot_error}")
        
        message_text = f"💥 **Purge Completed**\n\n"
        message_text += f"✅ Successfully deleted {deleted_count}/{len(admin_slots)} admin slots\n\n"
        message_text += f"**Removed:**\n"
        message_text += f"• {deleted_count} admin slots\n"
        message_text += f"• All associated content\n"
        message_text += f"• All destination assignments\n"
        message_text += f"• All post history\n\n"
        message_text += f"The admin slots system has been reset."
        
        keyboard = [
            [
                InlineKeyboardButton("🆕 Create New Slots", callback_data="admin_slots"),
                InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="cmd:admin_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer(f"💥 Purged {deleted_count} slots")
        
    except Exception as e:
        logger.error(f"Error in admin_confirm_purge_all_slots: {e}")
        await update.callback_query.answer("❌ Error during purge")

async def admin_delete_slot(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int):
    """Delete an admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Delete the slot
        success = await db.delete_admin_slot(slot_number)
        
        if success:
            await update.callback_query.answer("✅ Slot deleted successfully")
            # Go back to admin slots overview
            await admin_slots(update, context)
        else:
            await update.callback_query.answer("❌ Failed to delete slot")
        
    except Exception as e:
        logger.error(f"Error in admin_delete_slot: {e}")
        await update.callback_query.answer("❌ Error deleting slot")


async def admin_slot_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_number: int):
    """Show analytics for a specific admin slot."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get slot details
        slot = await db.get_admin_ad_slot(slot_number)
        if not slot:
            await update.callback_query.answer("❌ Slot not found")
            return
        
        # Get destinations
        destinations = await db.get_admin_slot_destinations(slot_number)
        
        message_text = f"📊 **Analytics for Admin Slot {slot_number}**\n\n"
        message_text += f"**Status:** {'✅ Active' if slot['is_active'] else '⏸️ Paused'}\n"
        message_text += f"**Content:** {'Set' if slot['content'] else 'Not Set'}\n"
        message_text += f"**Destinations:** {len(destinations)} groups\n"
        message_text += f"**Created:** {slot['created_at']}\n"
        message_text += f"**Last Updated:** {slot['updated_at']}\n\n"
        message_text += "**📈 Performance:**\n"
        message_text += "• Posts Today: 0\n"
        message_text += "• Posts This Week: 0\n"
        message_text += "• Posts This Month: 0\n"
        message_text += "• Total Posts: 0\n\n"
        message_text += "**🎯 Engagement:**\n"
        message_text += "• Average Views: 0\n"
        message_text += "• Average Clicks: 0\n"
        message_text += "• Conversion Rate: 0%\n"
        
        keyboard = [
            [
                InlineKeyboardButton("📈 Detailed Stats", callback_data=f"admin_detailed_analytics:{slot_number}"),
                InlineKeyboardButton("📊 Export Data", callback_data=f"admin_export_analytics:{slot_number}")
            ],
            [
                InlineKeyboardButton("🔙 Back to Slot", callback_data=f"admin_slot:{slot_number}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_slot_analytics: {e}")
        await update.callback_query.answer("❌ Error loading analytics")
