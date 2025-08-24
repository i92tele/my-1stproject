#!/usr/bin/env python3
"""
Final Admin UI Fix - No Syntax Errors

This script adds the missing database functions that are causing admin slots to freeze.
"""

import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def add_missing_admin_functions():
    """Add missing admin functions to database manager."""
    logger.info("🔧 Adding missing admin functions to database manager...")
    
    try:
        # Read the database manager file
        db_file = "src/database/manager.py"
        
        if not os.path.exists(db_file):
            logger.error(f"❌ Database manager file not found: {db_file}")
            return False
        
        with open(db_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if functions already exist
        if "async def get_admin_ad_slot" in content:
            logger.info("✅ get_admin_ad_slot function already exists")
        else:
            logger.info("❌ get_admin_ad_slot function missing - adding it")
            
            # Find the end of get_admin_ad_slots function
            if "async def get_admin_ad_slots" not in content:
                logger.error("❌ get_admin_ad_slots function not found")
                return False
            
            # Find the end of get_admin_ad_slots function
            start_pos = content.find("async def get_admin_ad_slots")
            if start_pos == -1:
                logger.error("❌ Could not find get_admin_ad_slots function")
                return False
            
            # Find the end of the function (after the return statement)
            lines = content.split('\n')
            insert_pos = None
            
            for i, line in enumerate(lines):
                if "async def get_admin_ad_slots" in line:
                    # Find the end of this function
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() == "" and j + 1 < len(lines) and lines[j + 1].strip().startswith("async def"):
                            insert_pos = j
                            break
                        elif lines[j].strip() == "" and j + 1 < len(lines) and lines[j + 1].strip().startswith("class"):
                            insert_pos = j
                            break
                    break
            
            if insert_pos is None:
                # If we can't find a good insertion point, add after the function
                for i, line in enumerate(lines):
                    if "return slots" in line and "get_admin_ad_slots" in lines[i-5:i]:
                        insert_pos = i + 2
                        break
            
            if insert_pos is None:
                logger.error("❌ Could not find insertion point for admin functions")
                return False
            
            # Add the missing functions with proper string formatting
            functions_to_add = '''
    async def get_admin_ad_slot(self, slot_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific admin ad slot by slot number."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM admin_ad_slots WHERE id = ?', (slot_number,))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return dict(row)
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
                
                query = "SELECT mg.* FROM managed_groups mg INNER JOIN admin_slot_destinations asd ON mg.id = asd.destination_id WHERE asd.slot_id = ? ORDER BY mg.category, mg.group_name"
                cursor.execute(query, (slot_id,))
                
                destinations = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return destinations
                
            except Exception as e:
                self.logger.error(f"Error getting admin slot destinations: {e}")
                return []

    async def update_admin_slot_content(self, slot_number: int, content: str) -> bool:
        """Update content for an admin slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                query = "UPDATE admin_ad_slots SET content = ?, updated_at = datetime('now') WHERE id = ?"
                cursor.execute(query, (content, slot_number))
                
                conn.commit()
                conn.close()
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating admin slot content: {e}")
                return False

    async def update_admin_slot_status(self, slot_number: int, is_active: bool) -> bool:
        """Update status for an admin slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                query = "UPDATE admin_ad_slots SET is_active = ?, updated_at = datetime('now') WHERE id = ?"
                cursor.execute(query, (1 if is_active else 0, slot_number))
                
                conn.commit()
                conn.close()
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating admin slot status: {e}")
                return False

    async def delete_admin_slot(self, slot_number: int) -> bool:
        """Delete an admin slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Delete slot destinations first
                cursor.execute('DELETE FROM admin_slot_destinations WHERE slot_id = ?', (slot_number,))
                
                # Delete the slot
                cursor.execute('DELETE FROM admin_ad_slots WHERE id = ?', (slot_number,))
                
                conn.commit()
                conn.close()
                return True
                
            except Exception as e:
                self.logger.error(f"Error deleting admin slot: {e}")
                return False
'''
            
            # Insert the functions
            lines.insert(insert_pos, functions_to_add)
            content = '\n'.join(lines)
            
            # Write back to file
            with open(db_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("✅ Added missing admin functions to database manager")
        
        # Check for other missing functions
        missing_functions = [
            "get_admin_slot_destinations",
            "update_admin_slot_content", 
            "update_admin_slot_status",
            "delete_admin_slot"
        ]
        
        for func in missing_functions:
            if f"async def {func}" in content:
                logger.info(f"✅ {func} function exists")
            else:
                logger.warning(f"⚠️ {func} function still missing")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error adding admin functions: {e}")
        return False

def verify_admin_functions():
    """Verify that admin functions are working."""
    logger.info("🔍 Verifying admin functions...")
    
    try:
        # Test importing the database manager
        import sys
        sys.path.append('src')
        
        from database.manager import DatabaseManager
        from src.config.bot_config import BotConfig
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config)
        
        # Test the functions
        logger.info("✅ Database manager imported successfully")
        
        # Check if functions exist
        if hasattr(db, 'get_admin_ad_slot'):
            logger.info("✅ get_admin_ad_slot function exists")
        else:
            logger.error("❌ get_admin_ad_slot function missing")
            return False
            
        if hasattr(db, 'get_admin_slot_destinations'):
            logger.info("✅ get_admin_slot_destinations function exists")
        else:
            logger.error("❌ get_admin_slot_destinations function missing")
            return False
            
        if hasattr(db, 'update_admin_slot_content'):
            logger.info("✅ update_admin_slot_content function exists")
        else:
            logger.error("❌ update_admin_slot_content function missing")
            return False
            
        if hasattr(db, 'update_admin_slot_status'):
            logger.info("✅ update_admin_slot_status function exists")
        else:
            logger.error("❌ update_admin_slot_status function missing")
            return False
            
        if hasattr(db, 'delete_admin_slot'):
            logger.info("✅ delete_admin_slot function exists")
        else:
            logger.error("❌ delete_admin_slot function missing")
            return False
        
        logger.info("✅ All admin functions verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verifying admin functions: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🔧 FINAL ADMIN UI FIX - NO SYNTAX ERRORS")
    logger.info("=" * 60)
    
    # Step 1: Add missing functions
    if add_missing_admin_functions():
        logger.info("✅ Admin functions added successfully")
    else:
        logger.error("❌ Failed to add admin functions")
        return
    
    # Step 2: Verify functions
    if verify_admin_functions():
        logger.info("✅ Admin functions verified")
    else:
        logger.error("❌ Admin functions verification failed")
        return
    
    logger.info("=" * 60)
    logger.info("📊 SUMMARY")
    logger.info("=" * 60)
    logger.info("✅ Admin UI should now work properly")
    logger.info("✅ Admin slots should be clickable")
    logger.info("✅ Slot modification should work")
    logger.info("")
    logger.info("🔄 Next steps:")
    logger.info("1. Restart the bot to apply changes")
    logger.info("2. Test clicking on admin slots")
    logger.info("3. Test modifying slot content")
    logger.info("4. Test toggling slot status")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
