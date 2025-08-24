#!/usr/bin/env python3
"""
Fix Admin UI Issues

This script fixes the missing admin UI functions that are causing the interface to freeze.
"""

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def add_missing_admin_functions():
    """Add missing admin functions to the database manager."""
    logger.info("🔧 Adding missing admin functions to database manager...")
    
    try:
        # Read the current database manager
        with open("src/database/manager.py", "r") as file:
            content = file.read()
        
        # Check if functions already exist
        if "async def get_admin_ad_slot" in content:
            logger.info("✅ get_admin_ad_slot function already exists")
            return True
        
        # Find the end of the get_admin_ad_slots function
        if "async def get_admin_ad_slots" not in content:
            logger.error("❌ get_admin_ad_slots function not found")
            return False
        
        # Add the missing functions after get_admin_ad_slots
        functions_to_add = '''
    async def get_admin_ad_slot(self, slot_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific admin ad slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, slot_number, content, destinations, is_active, created_at, updated_at
                    FROM admin_ad_slots
                    WHERE slot_number = ?
                ''', (slot_number,))
                
                row = cursor.fetchone()
                if row:
                    slot = dict(row)
                    # Parse destinations JSON
                    try:
                        import json
                        slot['destinations'] = json.loads(slot['destinations']) if slot['destinations'] else []
                    except:
                        slot['destinations'] = []
                    conn.close()
                    return slot
                
                conn.close()
                return None
                
            except Exception as e:
                self.logger.error(f"Error getting admin ad slot {slot_number}: {e}")
                return None

    async def get_admin_slot_destinations(self, slot_id: int) -> List[Dict[str, Any]]:
        """Get destinations for a specific admin slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT destination_id, destination_name, slot_id, slot_type
                    FROM slot_destinations
                    WHERE slot_id = ? AND slot_type = 'admin'
                ''', (slot_id,))
                
                destinations = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return destinations
                
            except Exception as e:
                self.logger.error(f"Error getting admin slot destinations: {e}")
                return []

    async def update_admin_slot_content(self, slot_id: int, content: str) -> bool:
        """Update content for an admin slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE admin_ad_slots
                    SET content = ?, updated_at = ?
                    WHERE id = ?
                ''', (content, datetime.now(), slot_id))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Updated content for admin slot {slot_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating admin slot content: {e}")
                return False

    async def update_admin_slot_status(self, slot_id: int, is_active: bool) -> bool:
        """Update active status for an admin slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE admin_ad_slots
                    SET is_active = ?, updated_at = ?
                    WHERE id = ?
                ''', (is_active, datetime.now(), slot_id))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Updated status for admin slot {slot_id} to {is_active}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating admin slot status: {e}")
                return False

    async def delete_admin_slot(self, slot_id: int) -> bool:
        """Delete an admin slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM admin_ad_slots WHERE id = ?', (slot_id,))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Deleted admin slot {slot_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error deleting admin slot: {e}")
                return False
'''
        
        # Find the end of get_admin_ad_slots function
        import re
        pattern = r'(async def get_admin_ad_slots\(self\) -> List\[Dict\[str, Any\]\]:.*?return \[\])'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            logger.error("❌ Could not find get_admin_ad_slots function")
            return False
        
        # Insert the new functions after get_admin_ad_slots
        insert_position = content.find(match.group(0)) + len(match.group(0))
        
        # Add the missing import for datetime
        if "from datetime import datetime" not in content:
            # Find the imports section
            import_pattern = r'(from typing import.*?\n)'
            import_match = re.search(import_pattern, content)
            if import_match:
                import_position = content.find(import_match.group(0)) + len(import_match.group(0))
                content = content[:import_position] + "from datetime import datetime\n" + content[import_position:]
        
        # Insert the new functions
        content = content[:insert_position] + functions_to_add + content[insert_position:]
        
        # Write the updated content
        with open("src/database/manager.py", "w") as file:
            file.write(content)
        
        logger.info("✅ Added missing admin functions to database manager")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error adding admin functions: {e}")
        return False

def verify_admin_functions():
    """Verify that all admin functions are present."""
    logger.info("🔍 Verifying admin functions...")
    
    try:
        with open("src/database/manager.py", "r") as file:
            content = file.read()
        
        required_functions = [
            "async def get_admin_ad_slot",
            "async def get_admin_slot_destinations", 
            "async def update_admin_slot_content",
            "async def update_admin_slot_status",
            "async def delete_admin_slot"
        ]
        
        missing_functions = []
        for func in required_functions:
            if func not in content:
                missing_functions.append(func)
        
        if missing_functions:
            logger.warning(f"⚠️ Missing functions: {missing_functions}")
            return False
        else:
            logger.info("✅ All admin functions are present")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error verifying admin functions: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🔧 FIX ADMIN UI ISSUES")
    logger.info("=" * 60)
    
    # Step 1: Add missing functions
    if add_missing_admin_functions():
        logger.info("✅ Admin functions added successfully")
    else:
        logger.error("❌ Failed to add admin functions")
        return
    
    # Step 2: Verify functions
    if verify_admin_functions():
        logger.info("✅ All admin functions verified")
    else:
        logger.warning("⚠️ Some functions may still be missing")
    
    logger.info("=" * 60)
    logger.info("📊 SUMMARY")
    logger.info("=" * 60)
    logger.info("✅ Admin UI functions added to database manager")
    logger.info("✅ This should fix the freezing issue when clicking on ads")
    logger.info("")
    logger.info("🔄 Next steps:")
    logger.info("1. Restart the bot to apply changes")
    logger.info("2. Test the admin UI - clicking on ads should work now")
    logger.info("3. Check that ad modification features are functional")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
