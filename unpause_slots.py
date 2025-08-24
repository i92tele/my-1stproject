#!/usr/bin/env python3
"""
Script to unpause slots that were manually paused
"""

import sqlite3
from datetime import datetime

def unpause_slots():
    """Unpause slots that were manually paused."""
    try:
        with sqlite3.connect("bot_database.db") as conn:
            cursor = conn.cursor()
            
            print("🔄 Unpausing slots to allow posting...")
            
            # Check for paused slots
            cursor.execute("""
                SELECT id, user_id, pause_reason, pause_time 
                FROM ad_slots 
                WHERE is_paused = 1 AND is_active = 1
            """)
            paused_slots = cursor.fetchall()
            
            if not paused_slots:
                print("✅ No paused user slots found")
            else:
                print(f"📊 Found {len(paused_slots)} paused user slots:")
                for slot_id, user_id, reason, pause_time in paused_slots:
                    print(f"  Slot {slot_id} (User {user_id}): {reason} at {pause_time}")
                    
                    # Unpause the slot
                    cursor.execute("""
                        UPDATE ad_slots 
                        SET is_paused = 0, 
                            pause_reason = NULL,
                            pause_time = NULL
                        WHERE id = ?
                    """, (slot_id,))
                    
                    print(f"    ✅ Unpaused slot {slot_id}")
            
            # Check for paused admin slots (handle missing columns)
            try:
                # First check if admin_ad_slots table has is_paused column
                cursor.execute("PRAGMA table_info(admin_ad_slots)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'is_paused' in columns:
                    cursor.execute("""
                        SELECT id, pause_reason, pause_time 
                        FROM admin_ad_slots 
                        WHERE is_paused = 1 AND is_active = 1
                    """)
                    paused_admin_slots = cursor.fetchall()
                    
                    if not paused_admin_slots:
                        print("✅ No paused admin slots found")
                    else:
                        print(f"📊 Found {len(paused_admin_slots)} paused admin slots:")
                        for slot_id, reason, pause_time in paused_admin_slots:
                            print(f"  Admin Slot {slot_id}: {reason} at {pause_time}")
                            
                            # Unpause the slot
                            cursor.execute("""
                                UPDATE admin_ad_slots 
                                SET is_paused = 0, 
                                    pause_reason = NULL,
                                    pause_time = NULL
                                WHERE id = ?
                            """, (slot_id,))
                            
                            print(f"    ✅ Unpaused admin slot {slot_id}")
                else:
                    print("ℹ️ Admin slots table doesn't have pause columns - no admin slots to unpause")
                    
            except Exception as e:
                print(f"ℹ️ Admin slots table doesn't have pause columns: {e}")
            
            # Force commit the changes
            conn.commit()
            print("\n🔍 Verifying changes...")
            
            # Check if slots are still paused
            cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1 AND is_paused = 1")
            still_paused_count = cursor.fetchone()[0]
            
            if still_paused_count == 0:
                print("✅ SUCCESS: All slots are now unpaused!")
            else:
                print(f"⚠️ WARNING: {still_paused_count} slots are still paused")
                cursor.execute("SELECT id, user_id FROM ad_slots WHERE is_active = 1 AND is_paused = 1")
                still_paused = cursor.fetchall()
                for slot_id, user_id in still_paused:
                    print(f"  Slot {slot_id} (User {user_id}) is still paused")
            
            # Verify all slots are now active
            cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1 AND (is_paused = 0 OR is_paused IS NULL)")
            active_count = cursor.fetchone()[0]
            
            # Check admin slots (without pause columns)
            cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1")
            admin_active_count = cursor.fetchone()[0]
            
            print(f"📊 Active user slots: {active_count}")
            print(f"📊 Active admin slots: {admin_active_count}")
            
            if active_count > 0 or admin_active_count > 0:
                print("✅ SUCCESS: Slots are now active and ready for posting!")
            else:
                print("⚠️ WARNING: No active slots found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    unpause_slots()
