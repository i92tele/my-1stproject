#!/usr/bin/env python3
"""
Emergency script to pause the 3 active slots that are still posting
"""

import sqlite3
from datetime import datetime

def pause_active_slots():
    """Pause the 3 active slots that are still posting."""
    try:
        # Active slots that need to be paused
        active_slots = [11, 16, 52]
        
        with sqlite3.connect("bot_database.db") as conn:
            cursor = conn.cursor()
            
            print("🛑 Pausing active slots to stop posting...")
            
            for slot_id in active_slots:
                # Check current status
                cursor.execute("SELECT id, user_id, is_active, is_paused FROM ad_slots WHERE id = ?", (slot_id,))
                result = cursor.fetchone()
                
                if result:
                    slot_id_db, user_id, is_active, is_paused = result
                    print(f"  Slot {slot_id_db} (User {user_id}): Active={is_active}, Paused={is_paused}")
                    
                    if is_active and not is_paused:
                        # Pause the slot
                        cursor.execute("""
                            UPDATE ad_slots 
                            SET is_paused = 1, 
                                pause_reason = 'Emergency pause - manual stop',
                                pause_time = ?
                            WHERE id = ?
                        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), slot_id))
                        
                        print(f"    ✅ Paused slot {slot_id}")
                    else:
                        print(f"    ⚠️ Slot {slot_id} already paused or inactive")
                else:
                    print(f"    ❌ Slot {slot_id} not found")
            
            conn.commit()
            print("\n🔍 Checking final status...")
            
            # Verify all slots are now paused
            cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1 AND (is_paused = 0 OR is_paused IS NULL)")
            active_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1")
            admin_active_count = cursor.fetchone()[0]
            
            print(f"📊 Active user slots remaining: {active_count}")
            print(f"📊 Active admin slots remaining: {admin_active_count}")
            
            if active_count == 0 and admin_active_count == 0:
                print("✅ SUCCESS: All slots are now paused/inactive!")
                print("🛡️ No more posting should occur until slots are manually activated")
            else:
                print("⚠️ WARNING: Some slots may still be active")
                
                if active_count > 0:
                    cursor.execute("SELECT id, user_id FROM ad_slots WHERE is_active = 1 AND (is_paused = 0 OR is_paused IS NULL)")
                    remaining = cursor.fetchall()
                    print(f"  Remaining active user slots: {remaining}")
                
                if admin_active_count > 0:
                    cursor.execute("SELECT id FROM admin_ad_slots WHERE is_active = 1")
                    remaining_admin = cursor.fetchall()
                    print(f"  Remaining active admin slots: {remaining_admin}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    pause_active_slots()

