#!/usr/bin/env python3
"""
Fix database deadlock in DatabaseManager - Version 2
"""

def fix_database_deadlock():
    """Fix the database deadlock issue in DatabaseManager."""
    print("🔧 Fixing Database Deadlock Issue...")
    
    db_manager_path = "src/database/manager.py"
    
    try:
        # Read the current file
        with open(db_manager_path, 'r') as f:
            content = f.read()
        
        print("📖 Reading current DatabaseManager...")
        
        # Find the get_user_subscription method
        if 'async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:' in content:
            print("✅ Found get_user_subscription method")
            
            # Check if it uses the lock
            if 'async with self._get_lock():' in content:
                print("⚠️ Found lock usage in get_user_subscription")
                
                # Create a new version without the lock for internal calls
                new_method = '''    async def get_user_subscription(self, user_id: int, use_lock: bool = True) -> Optional[Dict[str, Any]]:
        """Get user's subscription information."""
        if use_lock:
            async with self._get_lock():
                return await self._get_user_subscription_internal(user_id)
        else:
            return await self._get_user_subscription_internal(user_id)
    
    async def _get_user_subscription_internal(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Internal method to get user subscription without lock."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # First check if user exists and has subscription data
            cursor.execute("SELECT subscription_tier, subscription_expires FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row or not row['subscription_tier'] or not row['subscription_expires']:
                return None
            
            # Check if subscription is still active
            expires_at = datetime.fromisoformat(row['subscription_expires'])
            if expires_at > datetime.now():
                return {
                    'tier': row['subscription_tier'],
                    'expires': row['subscription_expires'],
                    'is_active': True
                }
            else:
                return {
                    'tier': row['subscription_tier'],
                    'expires': row['subscription_expires'],
                    'is_active': False
                }
                
        except Exception as e:
            self.logger.error(f"Error getting user subscription for {user_id}: {e}")
            return None'''
                
                # Replace the old method
                old_method_start = '    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:'
                
                # Find the start of the old method
                start_idx = content.find(old_method_start)
                if start_idx != -1:
                    # Find the end of the method (next method or end of class)
                    end_markers = [
                        '\n    async def ',
                        '\n    def ',
                        '\n\nclass ',
                        '\n\n#',
                        '\n\n"""',
                        '\n\n    """'
                    ]
                    
                    end_idx = len(content)
                    for marker in end_markers:
                        marker_idx = content.find(marker, start_idx + 1)
                        if marker_idx != -1 and marker_idx < end_idx:
                            end_idx = marker_idx
                    
                    # Replace the method
                    new_content = content[:start_idx] + new_method + content[end_idx:]
                    
                    # Write the updated file
                    with open(db_manager_path, 'w') as f:
                        f.write(new_content)
                    
                    print("✅ Successfully updated get_user_subscription method")
                    print("   - Added use_lock parameter")
                    print("   - Created internal method without lock")
                    print("   - Fixed deadlock issue")
                    
                    # Now update the activate_subscription method to use the internal method
                    if 'await self.get_user_subscription(user_id)' in new_content:
                        new_content = new_content.replace(
                            'await self.get_user_subscription(user_id)',
                            'await self.get_user_subscription(user_id, use_lock=False)'
                        )
                        
                        with open(db_manager_path, 'w') as f:
                            f.write(new_content)
                        
                        print("✅ Updated activate_subscription to use internal method")
                    
                    return True
                else:
                    print("❌ Could not find get_user_subscription method")
                    return False
            else:
                print("✅ get_user_subscription method does not use lock")
                return True
        else:
            print("❌ get_user_subscription method not found")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing database deadlock: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_database_deadlock()
    if success:
        print("\n🎉 Database deadlock fix completed!")
        print("   The subscription activation should now work without timeouts.")
    else:
        print("\n❌ Database deadlock fix failed!")
