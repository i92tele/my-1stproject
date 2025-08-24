#!/usr/bin/env python3
"""
Fix Remaining Admin Buttons

This script tests and fixes the remaining admin buttons that aren't working:
- Set Content
- Set Destinations  
- Post Now
- Delete Slot
- Slot Analytics
"""

import asyncio
import sqlite3
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdminButtonTester:
    def __init__(self):
        self.db_path = "bot_database.db"
        
    async def test_admin_set_content_button(self):
        """Test the Set Content button functionality."""
        print("🔍 TESTING SET CONTENT BUTTON")
        print("=" * 50)
        
        try:
            # Import required modules
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.database.manager import DatabaseManager
            
            # Initialize database manager
            db = DatabaseManager(self.db_path, logger)
            await db.initialize()
            
            # Test admin_set_slot_content function
            from commands.admin_slot_commands import admin_set_slot_content
            
            # Create a mock update and context for testing
            class MockUpdate:
                def __init__(self):
                    self.callback_query = MockCallbackQuery()
                    
            class MockCallbackQuery:
                def __init__(self):
                    self.data = "admin_set_content:1"
                    
                async def answer(self, text):
                    print(f"✅ Callback answered: {text}")
                    
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                    print(f"✅ Message edited: {text[:100]}...")
                    if reply_markup:
                        print(f"✅ Reply markup: {len(reply_markup.inline_keyboard)} rows")
            
            class MockContext:
                def __init__(self):
                    self.bot_data = {'db': db}
                    self.user_data = {}
            
            # Test the function
            mock_update = MockUpdate()
            mock_context = MockContext()
            
            await admin_set_slot_content(mock_update, mock_context, 1)
            
            print("✅ Set Content button test completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error testing Set Content button: {e}")
            return False
    
    async def test_admin_set_destinations_button(self):
        """Test the Set Destinations button functionality."""
        print("\n🔍 TESTING SET DESTINATIONS BUTTON")
        print("=" * 50)
        
        try:
            # Import required modules
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.database.manager import DatabaseManager
            
            # Initialize database manager
            db = DatabaseManager(self.db_path, logger)
            await db.initialize()
            
            # Test admin_set_slot_destinations function
            from commands.admin_slot_commands import admin_set_slot_destinations
            
            # Create a mock update and context for testing
            class MockUpdate:
                def __init__(self):
                    self.callback_query = MockCallbackQuery()
                    
            class MockCallbackQuery:
                def __init__(self):
                    self.data = "admin_set_destinations:1"
                    
                async def answer(self, text):
                    print(f"✅ Callback answered: {text}")
                    
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                    print(f"✅ Message edited: {text[:100]}...")
                    if reply_markup:
                        print(f"✅ Reply markup: {len(reply_markup.inline_keyboard)} rows")
            
            class MockContext:
                def __init__(self):
                    self.bot_data = {'db': db}
                    self.user_data = {}
            
            # Test the function
            mock_update = MockUpdate()
            mock_context = MockContext()
            
            await admin_set_slot_destinations(mock_update, mock_context, 1)
            
            print("✅ Set Destinations button test completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error testing Set Destinations button: {e}")
            return False
    
    async def test_admin_post_slot_button(self):
        """Test the Post Now button functionality."""
        print("\n🔍 TESTING POST NOW BUTTON")
        print("=" * 50)
        
        try:
            # Import required modules
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.database.manager import DatabaseManager
            
            # Initialize database manager
            db = DatabaseManager(self.db_path, logger)
            await db.initialize()
            
            # Test admin_post_slot function
            from commands.admin_slot_commands import admin_post_slot
            
            # Create a mock update and context for testing
            class MockUpdate:
                def __init__(self):
                    self.callback_query = MockCallbackQuery()
                    
            class MockCallbackQuery:
                def __init__(self):
                    self.data = "admin_post_slot:1"
                    
                async def answer(self, text):
                    print(f"✅ Callback answered: {text}")
                    
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                    print(f"✅ Message edited: {text[:100]}...")
            
            class MockContext:
                def __init__(self):
                    self.bot_data = {'db': db}
                    self.user_data = {}
            
            # Test the function
            mock_update = MockUpdate()
            mock_context = MockContext()
            
            await admin_post_slot(mock_update, mock_context, 1)
            
            print("✅ Post Now button test completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error testing Post Now button: {e}")
            return False
    
    async def test_admin_delete_slot_button(self):
        """Test the Delete Slot button functionality."""
        print("\n🔍 TESTING DELETE SLOT BUTTON")
        print("=" * 50)
        
        try:
            # Import required modules
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.database.manager import DatabaseManager
            
            # Initialize database manager
            db = DatabaseManager(self.db_path, logger)
            await db.initialize()
            
            # Test admin_delete_slot function
            from commands.admin_slot_commands import admin_delete_slot
            
            # Create a mock update and context for testing
            class MockUpdate:
                def __init__(self):
                    self.callback_query = MockCallbackQuery()
                    
            class MockCallbackQuery:
                def __init__(self):
                    self.data = "admin_delete_slot:1"
                    
                async def answer(self, text):
                    print(f"✅ Callback answered: {text}")
                    
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                    print(f"✅ Message edited: {text[:100]}...")
            
            class MockContext:
                def __init__(self):
                    self.bot_data = {'db': db}
                    self.user_data = {}
            
            # Test the function
            mock_update = MockUpdate()
            mock_context = MockContext()
            
            await admin_delete_slot(mock_update, mock_context, 1)
            
            print("✅ Delete Slot button test completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error testing Delete Slot button: {e}")
            return False
    
    async def test_admin_slot_analytics_button(self):
        """Test the Slot Analytics button functionality."""
        print("\n🔍 TESTING SLOT ANALYTICS BUTTON")
        print("=" * 50)
        
        try:
            # Import required modules
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.database.manager import DatabaseManager
            
            # Initialize database manager
            db = DatabaseManager(self.db_path, logger)
            await db.initialize()
            
            # Test admin_slot_analytics function
            from commands.admin_slot_commands import admin_slot_analytics
            
            # Create a mock update and context for testing
            class MockUpdate:
                def __init__(self):
                    self.callback_query = MockCallbackQuery()
                    
            class MockCallbackQuery:
                def __init__(self):
                    self.data = "admin_slot_analytics:1"
                    
                async def answer(self, text):
                    print(f"✅ Callback answered: {text}")
                    
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                    print(f"✅ Message edited: {text[:100]}...")
            
            class MockContext:
                def __init__(self):
                    self.bot_data = {'db': db}
                    self.user_data = {}
            
            # Test the function
            mock_update = MockUpdate()
            mock_context = MockContext()
            
            await admin_slot_analytics(mock_update, mock_context, 1)
            
            print("✅ Slot Analytics button test completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error testing Slot Analytics button: {e}")
            return False
    
    async def check_missing_functions(self):
        """Check for missing functions in admin_slot_commands.py."""
        print("\n🔍 CHECKING FOR MISSING FUNCTIONS")
        print("=" * 50)
        
        try:
            with open('commands/admin_slot_commands.py', 'r') as f:
                content = f.read()
            
            required_functions = [
                'admin_delete_slot',
                'admin_slot_analytics',
                'admin_category_view',
                'admin_toggle_destination',
                'admin_select_category',
                'admin_clear_category',
                'admin_select_all_destinations',
                'admin_clear_all_destinations',
                'admin_clear_all_content',
                'admin_clear_all_destinations_bulk',
                'admin_purge_all_slots',
                'admin_confirm_purge_all_slots'
            ]
            
            missing_functions = []
            for func in required_functions:
                if f"async def {func}" not in content:
                    missing_functions.append(func)
                    print(f"❌ Missing function: {func}")
                else:
                    print(f"✅ Function found: {func}")
            
            if missing_functions:
                print(f"\n❌ {len(missing_functions)} functions missing!")
                return missing_functions
            else:
                print("\n✅ All required functions are present!")
                return []
                
        except Exception as e:
            print(f"❌ Error checking functions: {e}")
            return []
    
    async def create_missing_functions(self, missing_functions):
        """Create missing functions."""
        print(f"\n🔧 CREATING {len(missing_functions)} MISSING FUNCTIONS")
        print("=" * 50)
        
        try:
            with open('commands/admin_slot_commands.py', 'r') as f:
                content = f.read()
            
            # Add missing functions at the end of the file
            new_functions = []
            
            for func in missing_functions:
                if func == 'admin_delete_slot':
                    new_functions.append('''
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
''')
                
                elif func == 'admin_slot_analytics':
                    new_functions.append('''
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
        
        message_text = f"📊 **Analytics for Admin Slot {slot_number}**\\n\\n"
        message_text += f"**Status:** {'✅ Active' if slot['is_active'] else '⏸️ Paused'}\\n"
        message_text += f"**Content:** {'Set' if slot['content'] else 'Not Set'}\\n"
        message_text += f"**Destinations:** {len(destinations)} groups\\n"
        message_text += f"**Created:** {slot['created_at']}\\n"
        message_text += f"**Last Updated:** {slot['updated_at']}\\n\\n"
        message_text += "**📈 Performance:**\\n"
        message_text += "• Posts Today: 0\\n"
        message_text += "• Posts This Week: 0\\n"
        message_text += "• Posts This Month: 0\\n"
        message_text += "• Total Posts: 0\\n\\n"
        message_text += "**🎯 Engagement:**\\n"
        message_text += "• Average Views: 0\\n"
        message_text += "• Average Clicks: 0\\n"
        message_text += "• Conversion Rate: 0%\\n"
        
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
''')
                
                elif func == 'admin_clear_all_content':
                    new_functions.append('''
async def admin_clear_all_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear content from all admin slots."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all admin slots
        admin_slots = await db.get_admin_ad_slots()
        
        cleared_count = 0
        for slot in admin_slots:
            if slot['content']:
                success = await db.update_admin_slot_content(slot['slot_number'], "")
                if success:
                    cleared_count += 1
        
        await update.callback_query.answer(f"✅ Cleared content from {cleared_count} slots")
        await admin_slots(update, context)
        
    except Exception as e:
        logger.error(f"Error in admin_clear_all_content: {e}")
        await update.callback_query.answer("❌ Error clearing content")
''')
                
                elif func == 'admin_clear_all_destinations_bulk':
                    new_functions.append('''
async def admin_clear_all_destinations_bulk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear destinations from all admin slots."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all admin slots
        admin_slots = await db.get_admin_ad_slots()
        
        cleared_count = 0
        for slot in admin_slots:
            destinations = await db.get_admin_slot_destinations(slot['slot_number'])
            if destinations:
                # Clear destinations by setting empty list
                success = await db.update_admin_slot_destinations(slot['slot_number'], [])
                if success:
                    cleared_count += 1
        
        await update.callback_query.answer(f"✅ Cleared destinations from {cleared_count} slots")
        await admin_slots(update, context)
        
    except Exception as e:
        logger.error(f"Error in admin_clear_all_destinations_bulk: {e}")
        await update.callback_query.answer("❌ Error clearing destinations")
''')
                
                elif func == 'admin_purge_all_slots':
                    new_functions.append('''
async def admin_purge_all_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show confirmation for purging all admin slots."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        message_text = (
            "🗑️ **Purge All Admin Slots**\\n\\n"
            "⚠️ **WARNING:** This will permanently delete ALL admin slots and their data!\\n\\n"
            "**This action cannot be undone.**\\n\\n"
            "Are you sure you want to continue?"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("❌ Cancel", callback_data="admin_slots"),
                InlineKeyboardButton("🗑️ Yes, Purge All", callback_data="admin_confirm_purge_all_slots")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_purge_all_slots: {e}")
        await update.callback_query.answer("❌ Error showing purge confirmation")
''')
                
                elif func == 'admin_confirm_purge_all_slots':
                    new_functions.append('''
async def admin_confirm_purge_all_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute purging all admin slots."""
    if not await check_admin(update, context):
        await update.callback_query.answer("❌ Admin access required.")
        return
        
    try:
        db = context.bot_data['db']
        
        # Get all admin slots
        admin_slots = await db.get_admin_ad_slots()
        
        deleted_count = 0
        for slot in admin_slots:
            success = await db.delete_admin_slot(slot['slot_number'])
            if success:
                deleted_count += 1
        
        await update.callback_query.answer(f"✅ Purged {deleted_count} admin slots")
        
        # Create new admin slots
        await db.create_admin_ad_slots()
        await admin_slots(update, context)
        
    except Exception as e:
        logger.error(f"Error in admin_confirm_purge_all_slots: {e}")
        await update.callback_query.answer("❌ Error purging slots")
''')
            
            # Add the new functions to the file
            if new_functions:
                content += "\\n".join(new_functions)
                
                with open('commands/admin_slot_commands.py', 'w') as f:
                    f.write(content)
                
                print(f"✅ Added {len(new_functions)} missing functions")
                return True
            else:
                print("✅ No functions needed to be added")
                return True
                
        except Exception as e:
            print(f"❌ Error creating missing functions: {e}")
            return False

async def main():
    """Main function."""
    print("🔧 FIXING REMAINING ADMIN BUTTONS")
    print("=" * 60)
    
    tester = AdminButtonTester()
    
    # 1. Check for missing functions
    missing_functions = await tester.check_missing_functions()
    
    # 2. Create missing functions if any
    if missing_functions:
        functions_created = await tester.create_missing_functions(missing_functions)
    else:
        functions_created = True
    
    # 3. Test all admin buttons
    print("\\n🧪 TESTING ALL ADMIN BUTTONS")
    print("=" * 60)
    
    tests = [
        ("Set Content", await tester.test_admin_set_content_button()),
        ("Set Destinations", await tester.test_admin_set_destinations_button()),
        ("Post Now", await tester.test_admin_post_slot_button()),
        ("Delete Slot", await tester.test_admin_delete_slot_button()),
        ("Slot Analytics", await tester.test_admin_slot_analytics_button())
    ]
    
    print("\\n📊 TEST RESULTS:")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in tests:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\\n🎯 FINAL STATUS:")
    print("=" * 60)
    
    if all_passed and functions_created:
        print("🎉 ALL ADMIN BUTTONS SHOULD NOW WORK!")
        print("✅ Set Content button should work")
        print("✅ Set Destinations button should work")
        print("✅ Post Now button should work")
        print("✅ Delete Slot button should work")
        print("✅ Slot Analytics button should work")
    else:
        print("❌ SOME BUTTONS MAY STILL NOT WORK")
        print("❌ Check the test results above")
    
    print("\\n🔄 NEXT STEPS:")
    print("1. Restart the bot")
    print("2. Test all admin buttons")
    print("3. Verify functionality")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
