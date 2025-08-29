#!/usr/bin/env python3
"""
Fix the specific call in activate_subscription that's causing deadlock
"""

def fix_activate_subscription_call():
    """Fix the get_user_subscription call in activate_subscription method."""
    print("🔧 Fixing activate_subscription call...")
    
    db_manager_path = "src/database/manager.py"
    
    try:
        # Read the current file
        with open(db_manager_path, 'r') as f:
            content = f.read()
        
        print("📖 Reading current DatabaseManager...")
        
        # Find the problematic line
        old_call = "current_sub = await asyncio.wait_for(self.get_user_subscription(user_id), timeout=10.0)"
        new_call = "current_sub = await asyncio.wait_for(self.get_user_subscription(user_id, use_lock=False), timeout=10.0)"
        
        if old_call in content:
            print("✅ Found the problematic call")
            
            # Replace the call
            new_content = content.replace(old_call, new_call)
            
            # Write the updated file
            with open(db_manager_path, 'w') as f:
                f.write(new_content)
            
            print("✅ Successfully updated activate_subscription call")
            print("   - Changed: self.get_user_subscription(user_id)")
            print("   - To: self.get_user_subscription(user_id, use_lock=False)")
            print("   - This will prevent the deadlock")
            
            return True
        else:
            print("❌ Could not find the problematic call")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing activate_subscription call: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_activate_subscription_call()
    if success:
        print("\n🎉 activate_subscription call fix completed!")
        print("   The deadlock should now be completely resolved.")
    else:
        print("\n❌ activate_subscription call fix failed!")
