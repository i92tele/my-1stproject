#!/usr/bin/env python3
"""
Manual Ad Slot Fix Script
Directly fixes the ad slot issues without database locks
"""

import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_ad_slots_manual():
    """Manually fix the ad slot issues."""
    print("🔧 Manual Ad Slot Fix")
    print("=" * 50)
    
    user_id = 7172873873
    correct_tier = 'basic'
    expected_slots = 1
    
    try:
        # Connect to database directly
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        print(f"📊 Fixing user {user_id} ad slots...")
        
        # Step 1: Show current status
        print("\n1️⃣ Current Status:")
        cursor.execute("SELECT subscription_tier FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        if user_row:
            current_tier = user_row[0]
            print(f"   Subscription Tier: {current_tier}")
        else:
            print("   ❌ User not found in database")
            return False
        
        cursor.execute("SELECT id, slot_number, is_active FROM ad_slots WHERE user_id = ? ORDER BY id", (user_id,))
        current_slots = cursor.fetchall()
        print(f"   Current Slots: {len(current_slots)}")
        for slot in current_slots:
            print(f"     Slot ID: {slot[0]}, Number: {slot[1]}, Active: {slot[2]}")
        
        # Step 2: Update subscription tier if needed
        if current_tier != correct_tier:
            print(f"\n2️⃣ Updating subscription tier: {current_tier} → {correct_tier}")
            cursor.execute("UPDATE users SET subscription_tier = ? WHERE user_id = ?", (correct_tier, user_id))
            print("   ✅ Subscription tier updated")
        else:
            print(f"\n2️⃣ Subscription tier already correct: {correct_tier}")
        
        # Step 3: Fix slot numbers and remove excess slots
        print(f"\n3️⃣ Fixing slot numbers and removing excess slots...")
        
        if len(current_slots) > expected_slots:
            # Keep the first slot, delete the rest
            slots_to_keep = current_slots[:expected_slots]
            slots_to_delete = current_slots[expected_slots:]
            
            print(f"   Keeping {len(slots_to_keep)} slots, deleting {len(slots_to_delete)} slots")
            
            # Delete excess slots
            for slot in slots_to_delete:
                slot_id = slot[0]
                print(f"     Deleting slot ID: {slot_id}")
                
                # Delete destinations for this slot first
                cursor.execute("DELETE FROM slot_destinations WHERE slot_id = ?", (slot_id,))
                
                # Delete the slot
                cursor.execute("DELETE FROM ad_slots WHERE id = ?", (slot_id,))
            
            # Fix slot numbers for remaining slots
            for i, slot in enumerate(slots_to_keep, 1):
                slot_id = slot[0]
                current_number = slot[1]
                if current_number != i:
                    print(f"     Fixing slot {slot_id}: {current_number} → {i}")
                    cursor.execute("UPDATE ad_slots SET slot_number = ? WHERE id = ?", (i, slot_id))
                else:
                    print(f"     Slot {slot_id} already has correct number: {i}")
        else:
            print(f"   Slot count is already correct: {len(current_slots)}")
        
        # Step 4: Commit changes
        conn.commit()
        print("\n4️⃣ Changes committed to database")
        
        # Step 5: Verify the fix
        print("\n5️⃣ Verifying the fix...")
        cursor.execute("SELECT subscription_tier FROM users WHERE user_id = ?", (user_id,))
        updated_tier = cursor.fetchone()[0]
        print(f"   Updated Subscription: {updated_tier}")
        
        cursor.execute("SELECT id, slot_number, is_active FROM ad_slots WHERE user_id = ? ORDER BY slot_number", (user_id,))
        updated_slots = cursor.fetchall()
        print(f"   Updated Slots: {len(updated_slots)}")
        for slot in updated_slots:
            print(f"     Slot ID: {slot[0]}, Number: {slot[1]}, Active: {slot[2]}")
        
        # Step 6: Validate the fix
        print("\n6️⃣ Validation:")
        
        # Check subscription tier
        if updated_tier == correct_tier:
            print("   ✅ Subscription tier is correct")
            tier_ok = True
        else:
            print(f"   ❌ Subscription tier incorrect: {updated_tier} (expected: {correct_tier})")
            tier_ok = False
        
        # Check slot count
        if len(updated_slots) == expected_slots:
            print(f"   ✅ Slot count is correct: {len(updated_slots)}")
            count_ok = True
        else:
            print(f"   ❌ Slot count incorrect: {len(updated_slots)} (expected: {expected_slots})")
            count_ok = False
        
        # Check slot numbers
        slot_numbers = [slot[1] for slot in updated_slots]
        expected_numbers = list(range(1, expected_slots + 1))
        if slot_numbers == expected_numbers:
            print(f"   ✅ Slot numbers are correct: {slot_numbers}")
            numbers_ok = True
        else:
            print(f"   ❌ Slot numbers incorrect: {slot_numbers} (expected: {expected_numbers})")
            numbers_ok = False
        
        conn.close()
        
        # Overall result
        overall_success = tier_ok and count_ok and numbers_ok
        
        if overall_success:
            print(f"\n🎉 AD SLOT FIX COMPLETED SUCCESSFULLY!")
            print(f"   User {user_id} now has {correct_tier} subscription with {len(updated_slots)} properly numbered slots")
        else:
            print(f"\n⚠️ SOME ISSUES REMAIN - Manual review needed")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Error during manual fix: {e}")
        logger.error(f"Manual fix error: {e}")
        return False

def main():
    """Main function."""
    print("🚀 Manual Ad Slot Fix Script")
    print("=" * 60)
    
    success = fix_ad_slots_manual()
    
    if success:
        print("\n✅ Manual fix completed successfully!")
        print("   The ad slot issues have been resolved")
        print("   You can now run the automated tests again")
    else:
        print("\n❌ Manual fix failed!")
        print("   Please check the error messages above")
        print("   Manual database intervention may be required")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
